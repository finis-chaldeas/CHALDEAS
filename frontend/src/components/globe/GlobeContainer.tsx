import { useRef, useMemo, useEffect, useState, useCallback } from 'react'
import Globe, { GlobeMethods } from 'react-globe.gl'
import { useGlobeStore, getZoomLevel } from '../../store/globeStore'
import { useTimelineStore } from '../../store/timelineStore'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import { useDebounce } from '../../hooks/useDebounce'
import { useFlyMode } from '../../hooks/useFlyMode'
import { useGlobeTiles, type TileData } from '../../hooks/useGlobeTiles'
import { useHeroOverlapResolver } from '../../hooks/useHeroOverlapResolver'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, eventsApi, personsApi, locationsApi, nodesApi, smartMarkersApi } from '../../api/client'
import type { Event, SmartMarkersResponse, ClusterEvent, NearbyEvent, NearbyPerson } from '../../types'
import { CameraModeToggle } from './CameraModeToggle'
import './GlobeHeatmap.css'

// Globe marker from new API
interface GlobeMarker {
  id: number
  type: 'event' | 'person' | 'location'
  lat: number
  lng: number
  year: number | null
  year_end: number | null
  category: string | null
  title: string
  description: string | null
  certainty: string | null
  color: string | null
  importance: number | null
}

// Anchor location from API (always-visible cities)
interface AnchorLocation {
  id: number
  name: string
  name_ko: string | null
  lat: number
  lng: number
  event_count: number
  tier: number // 1=always, 2=regional, 3=local
}

// Location node from Node API
interface LocationNode {
  id: number
  name: string
  name_ko: string | null
  lat: number
  lng: number
  event_count: number
  active_event_count: number
  tier: number
  top_event: string | null
  top_importance: number | null
}

// Globe arc from Historical Chain API
interface GlobeArc {
  connection_id: number
  source_event_id: number
  target_event_id: number
  source_title: string
  target_title: string
  source_title_ko?: string | null
  target_title_ko?: string | null
  source_title_ja?: string | null
  target_title_ja?: string | null
  source_lat: number
  source_lng: number
  target_lat: number
  target_lng: number
  source_year: number | null
  target_year: number | null
  layer_type: string
  connection_type: string | null
  direction: string
  strength: number
}

// Layer colors for Historical Chain
const LAYER_COLORS: Record<string, string> = {
  person: '#fbbf24',    // Gold
  location: '#34d399',  // Emerald
  causal: '#f472b6',    // Pink
  thematic: '#a78bfa',  // Purple
  connector: '#64748b', // Slate (nearby event connector)
}

// GeoJSON type
interface GeoJSONFeature {
  type: string
  properties: Record<string, unknown>
  geometry: {
    type: string
    coordinates: number[][][] | number[][][][]
  }
}

interface GeoJSONData {
  type: string
  features: GeoJSONFeature[]
}

interface GlobeContainerProps {
  onEventClick: (event: Event) => void
  onPersonClick?: (personId: number) => void
  onLocationClick?: (locationId: number) => void
  globeStyle?: string
  selectedEventId?: string | number | null
  showHeatmap?: boolean
  onHeatmapToggle?: (show: boolean) => void
}

// Globe texture URLs - LOD system: low-res for zoomed out, high-res for zoomed in
const GLOBE_TEXTURES_LO: Record<string, string> = {
  default: '//unpkg.com/three-globe/example/img/earth-blue-marble.jpg', // ~2k, fast load
  holo: '//unpkg.com/three-globe/example/img/earth-dark.jpg',
  night: '//unpkg.com/three-globe/example/img/earth-night.jpg',
}
const GLOBE_TEXTURES_HI: Record<string, string> = {
  default: '/textures/8k_earth_daymap.jpg',  // 8k, self-hosted
  night: '/textures/8k_earth_nightmap.jpg',   // 8k, self-hosted
}

// Generate graticule (lat/long grid lines) data
function generateGraticules() {
  const graticules: Array<{ coords: [number, number][] }> = []

  // Latitude lines (every 20 degrees)
  for (let lat = -80; lat <= 80; lat += 20) {
    const line: [number, number][] = []
    for (let lng = -180; lng <= 180; lng += 5) {
      line.push([lng, lat])
    }
    graticules.push({ coords: line })
  }

  // Longitude lines (every 20 degrees)
  for (let lng = -180; lng < 180; lng += 20) {
    const line: [number, number][] = []
    for (let lat = -90; lat <= 90; lat += 5) {
      line.push([lng, lat])
    }
    graticules.push({ coords: line })
  }

  return graticules
}

const GRATICULES = generateGraticules()
const EMPTY_ARRAY: never[] = []

export function GlobeContainer({
  onEventClick,
  onPersonClick,
  onLocationClick,
  globeStyle = 'default',
  showHeatmap: externalShowHeatmap,
  onHeatmapToggle,
}: GlobeContainerProps) {
  const globeRef = useRef<GlobeMethods>()
  const queryClient = useQueryClient()
  const {
    events,
    setEvents,
    selectedEvent,
    setSelectedEvent,
    highlightedLocations,
    autoRotate: storeAutoRotate,
    setViewportBounds,
    setCameraPosition,
    cameraPosition,
    flyTarget,
    clearFlyTarget,
    setGlobeMarkers,
    activeShift,
    activePageIndex,
    shiftMaxAltitude,
  } = useGlobeStore()

  const pinnedEvent = useGlobeStore(state => state.pinnedEvent)

  // WASD navigation (always active in globe view)
  useFlyMode({ globeRef, enabled: true })
  // Screen-coordinate overlap resolver for hero cards (disabled during shift mode)
  useHeroOverlapResolver(!activeShift)
  const { currentYear } = useTimelineStore()
  const { preferredLanguage } = useSettingsStore()
  const debouncedYear = useDebounce(currentYear, 150) // Debounce API calls during timeline drag (150ms for snappier response)
  const [focusedLocation, setFocusedLocation] = useState<{ lat: number; lng: number } | null>(null)
  const [countries, setCountries] = useState<GeoJSONFeature[]>([])
  const [internalShowHeatmap, setInternalShowHeatmap] = useState(false)
  const [showAllCities, setShowAllCities] = useState(false)
  // Use ref for continuous altitude (avoids re-render every frame)
  // Only update state-based zoom level when it actually changes threshold
  const altitudeRef = useRef(2.5)
  const shiftMaxAltRef = useRef<number | null>(null)
  // Flag to suppress store updates during pointOfView animations
  // (prevents re-renders that interfere with three-globe transitions)
  const isAnimatingRef = useRef(false)
  const [currentZoomLevel, setCurrentZoomLevel] = useState<ReturnType<typeof getZoomLevel>>('cosmic')
  const [, setLoadingMarkerId] = useState<number | null>(null)
  const [clusterPanel, setClusterPanel] = useState<{ events: ClusterEvent[]; persons?: NearbyPerson[]; lat: number; lng: number; locationName?: string } | null>(null)
  const clusterPanelRef = useRef(clusterPanel)
  clusterPanelRef.current = clusterPanel
  const setClusterPanelRef = useRef(setClusterPanel)
  setClusterPanelRef.current = setClusterPanel

  // High-resolution tile loading from CONTINENTAL zoom onwards
  const tilesEnabled = currentZoomLevel === 'continental' || currentZoomLevel === 'regional' || currentZoomLevel === 'local'
  const { tilesData: globeTilesData } = useGlobeTiles(
    cameraPosition.lat, cameraPosition.lng, cameraPosition.altitude,
    globeStyle, tilesEnabled,
  )

  // Ref for activePageIndex — used inside htmlElementFn to avoid
  // including activePageIndex in htmlElements useMemo deps (which would
  // cause three-globe to destroy+recreate all DOM elements on every page change)
  const activePageIndexRef = useRef(activePageIndex)
  activePageIndexRef.current = activePageIndex

  // Refs for values used inside htmlElement callback
  // Keeps the callback reference stable to prevent three-globe from
  // destroying and recreating DOM elements on every re-render
  const selectedEventRef = useRef(selectedEvent)
  selectedEventRef.current = selectedEvent
  const eventsRef = useRef(events)
  eventsRef.current = events
  const eventsDataRef = useRef<Event[] | undefined>(undefined)
  const onEventClickRef = useRef(onEventClick)
  onEventClickRef.current = onEventClick
  const onLocationClickRef = useRef(onLocationClick)
  onLocationClickRef.current = onLocationClick
  const onPersonClickRef = useRef(onPersonClick)
  onPersonClickRef.current = onPersonClick
  const anchorLocationsRef = useRef<AnchorLocation[] | undefined>(undefined)
  const setSelectedEventRef = useRef(setSelectedEvent)
  setSelectedEventRef.current = setSelectedEvent
  const debouncedYearRef = useRef(debouncedYear)
  debouncedYearRef.current = debouncedYear
  const preferredLanguageRef = useRef(preferredLanguage)
  preferredLanguageRef.current = preferredLanguage
  const currentZoomLevelRef = useRef(currentZoomLevel)
  currentZoomLevelRef.current = currentZoomLevel

  // Use external control if provided, otherwise use internal state
  const showHeatmap = externalShowHeatmap !== undefined ? externalShowHeatmap : internalShowHeatmap

  const handleHeatmapToggle = useCallback(() => {
    const newValue = !showHeatmap
    if (onHeatmapToggle) {
      onHeatmapToggle(newValue)
    } else {
      setInternalShowHeatmap(newValue)
    }
  }, [showHeatmap, onHeatmapToggle])

  // Track altitude changes + viewport bounds
  // Uses ref for altitude to avoid re-render every frame during rotation
  const handleZoom = useCallback(() => {
    if (globeRef.current) {
      const pov = globeRef.current.pointOfView()
      if (pov && typeof pov.altitude === 'number') {
        // Enforce shift zoom-out limit
        const maxAlt = shiftMaxAltRef.current
        if (maxAlt != null && pov.altitude > maxAlt) {
          globeRef.current.pointOfView(
            { lat: pov.lat, lng: pov.lng, altitude: maxAlt },
            300
          )
          return
        }

        altitudeRef.current = pov.altitude

        // Always update zoom level — controls tilesEnabled and LOD texture selection
        // (changes infrequently so won't cause excessive re-renders)
        const newZoom = getZoomLevel(pov.altitude)
        setCurrentZoomLevel(prev => prev === newZoom ? prev : newZoom)

        // During pointOfView animations, skip heavier store updates to prevent
        // re-renders that cause map/markers/camera to desync
        if (isAnimatingRef.current) return

        // Update camera position in store
        setCameraPosition({ lat: pov.lat, lng: pov.lng, altitude: pov.altitude })

        // Compute approximate viewport bounds from altitude and center point
        const latSpan = Math.min(90, pov.altitude * 40)
        const lngSpan = Math.min(180, pov.altitude * 50)
        setViewportBounds({
          north: Math.min(90, pov.lat + latSpan),
          south: Math.max(-90, pov.lat - latSpan),
          east: pov.lng + lngSpan,
          west: pov.lng - lngSpan,
        })
      }
    }
  }, [setCameraPosition, setViewportBounds])

  // Load countries GeoJSON only for HOLO mode (conditional load for performance)
  useEffect(() => {
    if (globeStyle !== 'holo') {
      setCountries([]) // Clear if not in holo mode
      return
    }
    fetch('https://raw.githubusercontent.com/vasturiano/react-globe.gl/master/example/datasets/ne_110m_admin_0_countries.geojson')
      .then(res => res.json())
      .then((data: GeoJSONData) => {
        // Filter out Antarctica
        setCountries(data.features.filter(d => d.properties.ISO_A2 !== 'AQ'))
      })
  }, [globeStyle])

  // Fetch globe markers from new API (events with coordinates)
  // Using debouncedYear to prevent API spam during timeline drag
  const { data: globeMarkers } = useQuery<GlobeMarker[]>({
    queryKey: ['globe-markers', debouncedYear],
    queryFn: async () => {
      const res = await api.get('/globe/markers', {
        params: {
          types: 'event',
          year_start: debouncedYear - 100,
          year_end: debouncedYear + 100,
          limit: 5000, // Backend max is 5000
        },
      })
      return res.data
    },
    placeholderData: undefined,
  })

  // Fetch events from API (for marker click -> event detail)
  const { data: eventsData } = useQuery({
    queryKey: ['events', debouncedYear],
    queryFn: () =>
      api.get('/events', {
        params: {
          year_start: debouncedYear - 100,
          year_end: debouncedYear + 100,
          limit: 1000,
        },
      }),
    select: (res) => res.data.items,
    placeholderData: undefined,
  })

  // Fetch anchor locations (always-visible major cities)
  const { data: anchorLocations } = useQuery<AnchorLocation[]>({
    queryKey: ['anchor-locations'],
    queryFn: async () => {
      const res = await api.get('/globe/anchor-locations', {
        params: { tier: 2, limit: 200 },
      })
      return res.data
    },
    staleTime: 10 * 60 * 1000, // 10 minutes - locations don't change often
  })
  anchorLocationsRef.current = anchorLocations

  // Fetch location nodes for node-based display
  const zoomParam = currentZoomLevel === 'cosmic' ? 'cosmic'
    : currentZoomLevel === 'continental' ? 'continental'
    : currentZoomLevel === 'regional' ? 'regional' : 'local'

  const { data: locationNodes } = useQuery<LocationNode[]>({
    queryKey: ['location-nodes', zoomParam, debouncedYear],
    queryFn: async () => {
      const res = await nodesApi.list({
        zoom: zoomParam,
        year_start: debouncedYear - 100,
        year_end: debouncedYear + 100,
        limit: zoomParam === 'cosmic' ? 200 : zoomParam === 'continental' ? 500 : 2000,
      })
      return res.data
    },
    staleTime: 30 * 1000, // 30s - changes with year
  })

  // Fetch smart markers (hero cards + cluster bubbles) for zoom-aware display
  const { data: smartMarkers } = useQuery<SmartMarkersResponse>({
    queryKey: ['smart-markers', debouncedYear, currentZoomLevel],
    queryFn: async () => {
      const timeRange = 100 // Uniform ±100yr across all zoom levels
      const res = await smartMarkersApi.get({
        year_start: debouncedYear - timeRange,
        year_end: debouncedYear + timeRange,
        zoom: currentZoomLevel,
      })
      return res.data
    },
    staleTime: 30 * 1000,
    placeholderData: (prev) => prev, // Keep previous data during refetch to prevent flicker
  })

  // Fetch arcs for selected event (Historical Chain connections)
  const { data: eventArcs } = useQuery<GlobeArc[]>({
    queryKey: ['globe-arcs', selectedEvent?.id],
    queryFn: async () => {
      if (!selectedEvent?.id) return []
      const res = await api.get(`/globe/arcs/${selectedEvent.id}`, {
        params: { min_strength: 3.0, limit: 30 },
      })
      return res.data
    },
    enabled: !!selectedEvent?.id,
    placeholderData: [],
  })

  // Clear events when year changes, then set new data when it arrives
  useEffect(() => {
    setEvents([])  // Clear immediately on year change
  }, [currentYear, setEvents])

  useEffect(() => {
    if (eventsData) {
      setEvents(eventsData)
      eventsDataRef.current = eventsData
    }
  }, [eventsData, setEvents])

  // Auto-rotate globe (cosmic zoom + store toggle)
  useEffect(() => {
    if (globeRef.current) {
      const controls = globeRef.current.controls()
      const shouldAutoRotate = currentZoomLevel === 'cosmic' && storeAutoRotate
      controls.autoRotate = shouldAutoRotate
      controls.autoRotateSpeed = 0.3
      controls.enableRotate = true
      controls.enableZoom = true
    }
  }, [currentZoomLevel, storeAutoRotate])

  // Shift mode: lock max zoom-out to fit-all altitude
  useEffect(() => {
    shiftMaxAltRef.current = shiftMaxAltitude
    if (globeRef.current) {
      const controls = globeRef.current.controls() as unknown as { maxDistance?: number; minDistance?: number }
      if (shiftMaxAltitude != null) {
        // react-globe.gl: distance ≈ (1 + altitude) * GLOBE_RADIUS
        // GLOBE_RADIUS default = 100 in three-globe
        controls.maxDistance = (1 + shiftMaxAltitude) * 100
      } else {
        // Reset to default (very far)
        controls.maxDistance = Infinity
      }
    }
  }, [shiftMaxAltitude])

  // Fly to location when flyTarget changes (from Navigator tabs, SHEBA episodes, etc.)
  useEffect(() => {
    if (flyTarget && globeRef.current) {
      globeRef.current.controls().autoRotate = false
      isAnimatingRef.current = true

      const duration = 1000
      globeRef.current.pointOfView(
        { lat: flyTarget.lat, lng: flyTarget.lng, altitude: flyTarget.altitude },
        duration
      )

      // After animation completes, sync store
      setTimeout(() => {
        isAnimatingRef.current = false
        if (globeRef.current) {
          const pov = globeRef.current.pointOfView()
          if (pov) {
            setCameraPosition({ lat: pov.lat, lng: pov.lng, altitude: pov.altitude })
          }
        }
      }, duration + 50)
      clearFlyTarget()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flyTarget])

  // Focus on selected event - rotate globe to that location
  useEffect(() => {
    if (selectedEvent && globeRef.current) {
      const lat = selectedEvent.latitude || selectedEvent.location?.latitude
      const lng = selectedEvent.longitude || selectedEvent.location?.longitude

      if (lat && lng) {
        globeRef.current.controls().autoRotate = false

        // Rotate globe to focus on the location — never zoom OUT from current position
        const targetAlt = Math.min(altitudeRef.current, 0.8)
        globeRef.current.pointOfView({ lat, lng, altitude: targetAlt }, 1000)

        // Set focused location for ring effect
        setFocusedLocation({ lat, lng })
      }
    } else {
      // Resume auto-rotate when no selection
      if (globeRef.current && storeAutoRotate) {
        globeRef.current.controls().autoRotate = currentZoomLevel === 'cosmic'
      }
      setFocusedLocation(null)
    }
  }, [selectedEvent, storeAutoRotate, currentZoomLevel])

  // Update hero card highlight state via DOM when selection changes
  // Uses CSS classes instead of recreating DOM elements
  // Also re-applies when htmlElements changes (zoom triggers new DOM elements)
  useEffect(() => {
    const applyClasses = () => {
      const container = document.querySelector('.globe-container')
      if (!container) return

      // Clear previous selection highlights
      container.querySelectorAll('.hero-selected, .hero-arc-target').forEach(el => {
        el.classList.remove('hero-selected')
        el.classList.remove('hero-arc-target')
      })

      if (selectedEvent) {
        // Highlight the selected hero card
        const heroEl = container.querySelector(`[data-hero-id="${selectedEvent.id}"]`)
        if (heroEl) heroEl.classList.add('hero-selected')

        // Mark arc-connected events as visible
        if (eventArcs) {
          const arcEventIds = new Set<number>()
          eventArcs.forEach(arc => {
            arcEventIds.add(arc.source_event_id)
            arcEventIds.add(arc.target_event_id)
          })
          arcEventIds.delete(selectedEvent.id as number)
          arcEventIds.forEach(id => {
            const arcEl = container.querySelector(`[data-hero-id="${id}"]`)
            if (arcEl) arcEl.classList.add('hero-arc-target')
          })
        }
      }
    }

    // Apply immediately + after short delay (three-globe DOM update is async)
    applyClasses()
    const timer = setTimeout(applyClasses, 100)
    return () => clearTimeout(timer)
  }, [selectedEvent, eventArcs, smartMarkers, currentZoomLevel])

  // Clear pinned event if it now appears as a regular hero in smart markers
  useEffect(() => {
    const pinned = useGlobeStore.getState().pinnedEvent
    if (pinned && smartMarkers?.heroes?.some(h => h.id === pinned.id)) {
      useGlobeStore.getState().clearPinnedEvent()
    }
  }, [smartMarkers])

  // Update shift marker highlight via DOM when activePageIndex changes
  // This avoids recreating all markers (which causes floating/jumping)
  useEffect(() => {
    if (!activeShift) return
    const container = document.querySelector('.globe-container')
    if (!container) return

    container.querySelectorAll('[data-page-index]').forEach(el => {
      const idx = parseInt((el as HTMLElement).dataset.pageIndex || '-1')
      if (idx === activePageIndex) {
        el.className = 'shift-marker shift-marker--active'
      } else {
        el.className = 'shift-marker shift-marker--inactive'
      }
    })
  }, [activeShift, activePageIndex])

  // Sync globe markers to store (for Map view to consume)
  useEffect(() => {
    if (globeMarkers) setGlobeMarkers(globeMarkers)
  }, [globeMarkers, setGlobeMarkers])

  // (Map mode removed — globe always active)

  // Filter globe markers for current time (from new API)
  const visibleMarkers = useMemo(() => {
    if (!globeMarkers) return []
    const TIME_RANGE = 20 // Show markers within ±20 years

    return globeMarkers.filter((marker) => {
      const start = marker.year
      if (start === null) return true // Show markers without year info

      const end = marker.year_end || start

      // Check time range
      if (currentYear < start - TIME_RANGE || currentYear > end + TIME_RANGE) {
        return false
      }

      return true
    })
  }, [globeMarkers, currentYear])

  // Clustering disabled - location nodes only

  // Visible anchor locations filtered by zoom level (tier system)
  // Use discrete currentZoomLevel instead of continuous altitude to avoid recalc every frame
  const visibleAnchors = useMemo(() => {
    if (!anchorLocations) return []
    const maxTier = currentZoomLevel === 'cosmic' ? 1
      : currentZoomLevel === 'continental' ? 2 : 3
    return anchorLocations.filter(loc => loc.tier <= maxTier)
  }, [anchorLocations, currentZoomLevel])

  // Visible location nodes filtered by zoom + activity
  // By default only show cities with events in the current time range
  // Toggle showAllCities to see all cities regardless
  const visibleNodes = useMemo(() => {
    if (!locationNodes) return []
    return locationNodes.filter(node => {
      if (!showAllCities && node.active_event_count === 0) return false

      if (currentZoomLevel === 'cosmic') {
        // Far zoom: only tier 1 cities with many events
        if (node.tier !== 1) return false
        return showAllCities ? node.event_count >= 10 : node.event_count >= 20
      }
      if (currentZoomLevel === 'continental') {
        // Mid zoom: tier 1 always, tier 2 only with high event count
        if (node.tier !== 1) {
          return showAllCities ? node.event_count >= 8 : node.event_count >= 12
        }
        return showAllCities ? node.event_count >= 3 : node.event_count >= 5
      }
      if (currentZoomLevel === 'regional') {
        return node.event_count >= 1
      }
      // Local zoom: show all active
      return true
    })
  }, [locationNodes, currentZoomLevel, showAllCities])

  // ── SHIFT MODE markers — separate useMemo with minimal deps ──
  // Only depends on activeShift (not smartMarkers, visibleNodes, etc.)
  // so page navigation won't trigger new array references that cause
  // three-globe to re-process and desync map/markers/camera.
  const shiftHtmlElements = useMemo(() => {
    if (!activeShift) return null
    const pages = activeShift.pages || []
    const elements: Array<Record<string, unknown>> = []
    pages.forEach((page, idx) => {
      if (page.lat == null || page.lng == null) return
      elements.push({
        lat: page.lat,
        lng: page.lng,
        title: page.title || `${idx + 1}`,
        title_ko: page.title_ko,
        year_start: page.year_start,
        page_index: idx,
        kind: 'shift-page' as const,
      })
    })
    return elements
  }, [activeShift])

  // ── NORMAL MODE markers ──
  const normalHtmlElements = useMemo(() => {
    if (activeShift) return EMPTY_ARRAY
    const elements: Array<Record<string, unknown>> = []

    // 1. SHEBA highlights (highest priority)
    if (highlightedLocations.length > 0) {
      elements.push(...highlightedLocations.map(loc => ({
        ...loc,
        kind: 'highlight' as const,
      })))
    }

    // 2. Hero cards (important events)
    if (smartMarkers?.heroes) {
      elements.push(...smartMarkers.heroes.map(h => ({
        ...h,
        title: getLocalizedText(h as unknown as Record<string, unknown>, 'title', preferredLanguage) || h.title,
        nearby_events: h.nearby_events || [],
        nearby_persons: h.nearby_persons || [],
        kind: 'hero' as const,
      })))
    }

    // 2b. Arc target events (connected events shown as hero cards even if low importance)
    // Track hero positions for proximity checks
    const heroCoords = elements
      .filter(e => (e as Record<string, unknown>).kind === 'hero')
      .map(e => ({ lat: e.lat as number, lng: e.lng as number }))

    if (eventArcs && eventArcs.length > 0) {
      const heroIds = new Set(smartMarkers?.heroes?.map(h => h.id) || [])
      eventArcs.forEach(arc => {
        // Add target if not already in heroes and not too close to existing hero
        if (!heroIds.has(arc.target_event_id)) {
          const tooClose = heroCoords.some(c =>
            Math.sqrt((c.lat - arc.target_lat) ** 2 + (c.lng - arc.target_lng) ** 2) < 2
          )
          if (!tooClose) {
            heroIds.add(arc.target_event_id)
            heroCoords.push({ lat: arc.target_lat, lng: arc.target_lng })
            elements.push({
              id: arc.target_event_id,
              type: 'event',
              lat: arc.target_lat,
              lng: arc.target_lng,
              title: arc.target_title,
              title_ko: arc.target_title_ko,
              title_ja: arc.target_title_ja,
              year: arc.target_year,
              importance: 3,
              child_count: 0,
              kind: 'hero' as const,
              is_arc_target: true,
            })
          }
        }
        // Add source if not already in heroes and not too close
        if (!heroIds.has(arc.source_event_id)) {
          const tooClose = heroCoords.some(c =>
            Math.sqrt((c.lat - arc.source_lat) ** 2 + (c.lng - arc.source_lng) ** 2) < 2
          )
          if (!tooClose) {
            heroIds.add(arc.source_event_id)
            heroCoords.push({ lat: arc.source_lat, lng: arc.source_lng })
            elements.push({
              id: arc.source_event_id,
              type: 'event',
              lat: arc.source_lat,
              lng: arc.source_lng,
              title: arc.source_title,
              title_ko: arc.source_title_ko,
              title_ja: arc.source_title_ja,
              year: arc.source_year,
              importance: 3,
              child_count: 0,
              kind: 'hero' as const,
              is_arc_target: true,
            })
          }
        }
      })
    }

    // 2c. Pinned event (clicked from badge modal → solo hero on globe)
    if (pinnedEvent) {
      const heroIds = new Set(elements.filter(e => e.kind === 'hero').map(e => e.id as number))
      if (!heroIds.has(pinnedEvent.id)) {
        elements.push({
          id: pinnedEvent.id,
          type: 'event',
          lat: pinnedEvent.lat,
          lng: pinnedEvent.lng,
          title: pinnedEvent.title,
          title_ko: pinnedEvent.title_ko,
          title_ja: pinnedEvent.title_ja,
          year: pinnedEvent.year,
          importance: pinnedEvent.importance,
          category: pinnedEvent.category,
          child_count: 0,
          kind: 'hero' as const,
          is_pinned: true,
        })
        heroCoords.push({ lat: pinnedEvent.lat, lng: pinnedEvent.lng })
      }
    }

    // 3. Location nodes (city labels) — suppress where heroes exist (by id or proximity)
    const heroLocationIds = new Set(
      (smartMarkers?.heroes || [])
        .map(h => h.location_id)
        .filter((id): id is number => id != null)
    )
    // heroCoords already built above (includes arc targets)
    if (visibleNodes.length > 0) {
      elements.push(...visibleNodes
        .filter(node => {
          if (heroLocationIds.has(node.id)) return false
          // Geographic proximity check: suppress nodes too close to any hero
          return !heroCoords.some(hp =>
            Math.sqrt((hp.lat - node.lat) ** 2 + (hp.lng - node.lng) ** 2) < 1.5
          )
        })
        .map(node => ({
          lat: node.lat,
          lng: node.lng,
          title: getLocalizedText(node as unknown as Record<string, unknown>, 'name', preferredLanguage) || node.name,
          event_count: node.event_count,
          active_count: node.active_event_count,
          tier: node.tier,
          node_id: node.id,
          top_event: node.top_event,
          kind: 'node' as const,
        }))
      )
    }

    // 5. Anchor locations (fallback if no nodes)
    if (elements.length === 0) {
      elements.push(...visibleAnchors.map(loc => ({
        lat: loc.lat,
        lng: loc.lng,
        title: getLocalizedText(loc as unknown as Record<string, unknown>, 'name', preferredLanguage) || loc.name,
        event_count: loc.event_count,
        tier: loc.tier,
        kind: 'anchor' as const,
      })))
    }

    // 6. Event browse mini modal (anchored to globe coordinates)
    if (clusterPanel && (clusterPanel.events.length > 0 || (clusterPanel.persons && clusterPanel.persons.length > 0))) {
      elements.push({
        lat: clusterPanel.lat,
        lng: clusterPanel.lng,
        events: clusterPanel.events,
        persons: clusterPanel.persons,
        locationName: clusterPanel.locationName,
        kind: 'event-panel' as const,
      })
    }

    return elements
  }, [activeShift, highlightedLocations, smartMarkers, eventArcs, visibleNodes, visibleAnchors, preferredLanguage, clusterPanel, pinnedEvent])

  // Use shift markers (stable ref) or normal markers
  // NOTE: activePageIndex intentionally excluded — tracked via ref + DOM updates
  // to prevent three-globe from destroying/recreating all marker DOM elements
  const htmlElements = shiftHtmlElements || normalHtmlElements

  // Stable htmlElement callback - uses refs to avoid function reference changes
  // that would cause three-globe to destroy and recreate all DOM elements
  const htmlElementFn = useCallback((d: object) => {
    const item = d as Record<string, unknown>
    const el = document.createElement('div')
    // CRITICAL: CSS2DRenderer sets el.style.transform every frame.
    // Any CSS transition on transform causes DOM elements to lag behind
    // the WebGL globe surface. Force no transitions on the root element.
    el.style.transition = 'none'

    if (item.kind === 'shift-page') {
      // History Shift page marker — mini card styling, updated via DOM in useEffect
      const sp = item as { lat: number; lng: number; title: string; title_ko?: string; year_start?: number; page_index: number }
      const isCurrent = sp.page_index === activePageIndexRef.current
      const formatYear = (y?: number) => {
        if (y == null) return ''
        return y < 0 ? `${Math.abs(y)} BCE` : `${y} CE`
      }
      const yearStr = formatYear(sp.year_start)
      // Use localized title based on preferred language
      const lang = useSettingsStore.getState().preferredLanguage
      const rawTitle = (lang === 'ko' && sp.title_ko) ? sp.title_ko : (sp.title || '')
      const safeTitle = rawTitle.replace(/</g, '&lt;').replace(/>/g, '&gt;')
      const truncTitle = safeTitle.length > 28 ? safeTitle.slice(0, 26) + '…' : safeTitle
      el.setAttribute('data-page-index', String(sp.page_index))
      el.className = `shift-marker ${isCurrent ? 'shift-marker--active' : 'shift-marker--inactive'}`
      el.innerHTML = `
        <div class="shift-card">
          <div class="shift-card-badge">${sp.page_index + 1}</div>
          <div class="shift-card-body">
            <span class="shift-card-title">${truncTitle}</span>
            ${yearStr ? `<span class="shift-card-year">${yearStr}</span>` : ''}
          </div>
        </div>
      `
      el.style.pointerEvents = 'auto'
      el.onclick = () => {
        const store = useGlobeStore.getState()
        store.goToPage(sp.page_index)
      }
    } else if (item.kind === 'highlight') {
      // SHEBA search highlight (pulsing gold)
      el.innerHTML = `
        <div style="
          background: rgba(255, 215, 0, 0.9);
          color: #000;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: bold;
          white-space: nowrap;
          cursor: pointer;
          box-shadow: 0 0 10px rgba(255, 215, 0, 0.8);
          animation: pulse 1.5s infinite;
        ">
          ${item.title}
        </div>
      `
      el.style.pointerEvents = 'auto'
      el.onclick = () => {
        const event = eventsRef.current.find(e =>
          Math.abs((e.latitude || 0) - (item.lat as number)) < 0.1 &&
          Math.abs((e.longitude || 0) - (item.lng as number)) < 0.1
        )
        if (event) onEventClickRef.current(event)
      }
    } else if (item.kind === 'hero') {
      // Hero card: important event displayed as floating card with region badge
      const heroItem = item as { id: number; title: string; title_ko?: string; title_ja?: string; year?: number; year_end?: number; category?: string; importance: number; location_name?: string; location_name_ko?: string; location_name_ja?: string; location_id?: number; lat: number; lng: number; child_count: number; nearby_events?: NearbyEvent[]; nearby_event_count?: number; nearby_persons?: NearbyPerson[]; nearby_person_count?: number; kind: 'hero' }
      const categoryClass = heroItem.category ? `hero-card--${heroItem.category.toLowerCase()}` : ''
      const formatYear = (y?: number) => {
        if (y === undefined || y === null) return ''
        return y < 0 ? `${Math.abs(y)} BCE` : `${y} CE`
      }
      const stars = Array.from({ length: 5 }, (_, i) =>
        i < heroItem.importance
          ? '<span class="star">\u2605</span>'
          : '<span class="star-empty">\u2605</span>'
      ).join('')

      // Localize location name
      const lang = preferredLanguageRef.current
      const locName = (lang === 'ko' && heroItem.location_name_ko) ? heroItem.location_name_ko
        : (lang === 'ja' && heroItem.location_name_ja) ? heroItem.location_name_ja
        : heroItem.location_name

      // Localize hero title
      const heroTitle = (lang === 'ko' && heroItem.title_ko) ? heroItem.title_ko
        : (lang === 'ja' && heroItem.title_ja) ? heroItem.title_ja
        : heroItem.title

      const nearbyEvents = heroItem.nearby_events || []
      const nearbyPersons = heroItem.nearby_persons || []

      // Companion lines: high-importance nearby events shown directly on card
      const companions = nearbyEvents.filter(e =>
        e.importance >= heroItem.importance - 1 && e.importance >= 4
      ).slice(0, 2)

      // Use real counts (may exceed list length due to cap)
      const eventCount = heroItem.nearby_event_count ?? nearbyEvents.length
      const personCount = heroItem.nearby_person_count ?? nearbyPersons.length
      const totalNearby = eventCount + personCount

      // Category color map for chip borders
      const catColors: Record<string, string> = {
        battle: '#ef4444', war: '#dc2626', treaty: '#3b82f6',
        discovery: '#22c55e', cultural: '#a855f7', political: '#f59e0b',
        religious: '#8b5cf6', science: '#00d4ff',
      }

      // Build region badge HTML (stacked chip design)
      // Hide badge if companions cover everything and no persons
      let badgeHtml = ''
      if (totalNearby > 0 && (eventCount > 0 || personCount > 0)) {
        // Extract top category colors from nearby_events
        const topCats = nearbyEvents.slice(0, 3).map(e => (e.category || '').toLowerCase())
        const cat1Color = catColors[topCats[0]] || 'rgba(0, 212, 255, 0.4)'
        const cat2Color = catColors[topCats[1]] || catColors[topCats[0]] || 'rgba(0, 212, 255, 0.4)'
        const cat3Color = catColors[topCats[2]] || catColors[topCats[1]] || catColors[topCats[0]] || 'rgba(0, 212, 255, 0.4)'

        // Back chips: 0 if total=1, 1 if total=2, 2 if total>=3
        const chip2 = totalNearby >= 3 ? `<div class="hero-region-chip hero-region-chip--2" style="border-color:${cat3Color}"></div>` : ''
        const chip1 = totalNearby >= 2 ? `<div class="hero-region-chip hero-region-chip--1" style="border-color:${cat2Color}"></div>` : ''

        // Count text
        const countParts: string[] = []
        if (eventCount > 0) countParts.push(`\ud83d\udccb${eventCount}`)
        if (personCount > 0) countParts.push(`\ud83d\udc64${personCount}`)

        badgeHtml = `
          <div class="hero-region-badge" data-region-badge="true">
            ${chip2}
            ${chip1}
            <div class="hero-region-chip hero-region-chip--front" style="border-color:${cat1Color}">
              ${countParts.map(c => `<span class="hero-region-count">${c}</span>`).join('')}
            </div>
          </div>
        `
      }

      // Build companion lines HTML
      let companionHtml = ''
      if (companions.length > 0) {
        const companionItems = companions.map(c => {
          const cTitle = (lang === 'ko' && c.title_ko) ? c.title_ko
            : (lang === 'ja' && c.title_ja) ? c.title_ja
            : c.title
          const safeCTitle = cTitle.replace(/</g, '&lt;').replace(/>/g, '&gt;')
          return `<div class="hero-card-companion" data-event-id="${c.id}">+ ${safeCTitle}</div>`
        }).join('')
        companionHtml = `<div class="hero-card-companions">${companionItems}</div>`
      }

      // Compact mode at cosmic/continental zoom: smaller card, fewer details
      const zoomLevel = currentZoomLevelRef.current
      const isCompact = zoomLevel === 'cosmic' || zoomLevel === 'continental'
      const isPinned = !!(heroItem as Record<string, unknown>).is_pinned
      const compactClass = isCompact && !isPinned ? 'hero-card--compact' : ''
      const pinnedClass = isPinned ? 'hero-card--pinned' : ''
      // Truncate title in compact mode (never truncate pinned)
      const displayTitle = isCompact && !isPinned && heroTitle.length > 14
        ? heroTitle.slice(0, 13) + '…'
        : heroTitle

      el.innerHTML = `
        <div class="hero-card ${categoryClass} ${compactClass} ${pinnedClass}" data-hero-id="${heroItem.id}" data-importance="${heroItem.importance}">
          <div class="hero-card-title">${displayTitle}</div>
          <div class="hero-card-meta">
            <span class="hero-card-year">${formatYear(heroItem.year)}</span>
            ${!isCompact && locName ? `<span class="hero-card-location" data-location-id="${heroItem.location_id || ''}">${locName}</span>` : ''}
          </div>
          ${!isCompact ? `<div class="hero-card-importance">${stars}</div>` : ''}
          ${!isCompact ? companionHtml : ''}
          ${badgeHtml}
        </div>
      `
      el.style.pointerEvents = 'auto'

      el.onclick = async (e) => {
        // Check if companion line was clicked → open that event
        const companionEl = (e.target as HTMLElement).closest?.('.hero-card-companion') as HTMLElement | null
        if (companionEl) {
          e.stopPropagation()
          const eventId = parseInt(companionEl.dataset.eventId || '0')
          if (eventId) {
            try {
              const res = await eventsApi.get(eventId)
              onEventClickRef.current(res.data)
            } catch (err) {
              console.error('Failed to fetch companion event:', eventId, err)
            }
          }
          return
        }

        // Check if region badge was clicked → open region modal
        const badge = (e.target as HTMLElement).closest?.('[data-region-badge]') as HTMLElement | null
        if (badge) {
          e.stopPropagation()
          // Convert nearby_events to ClusterEvent format for the mini modal
          const clusterEvents: ClusterEvent[] = nearbyEvents
            .map(ne => ({
              id: ne.id,
              title: ne.title,
              title_ko: ne.title_ko,
              title_ja: ne.title_ja,
              year: ne.year,
              importance: ne.importance,
              category: ne.category,
              location_name: ne.location_name,
              location_name_ko: ne.location_name_ko,
              location_name_ja: ne.location_name_ja,
              lat: ne.lat,
              lng: ne.lng,
            }))
          setClusterPanelRef.current({
            events: clusterEvents,
            persons: nearbyPersons.length > 0 ? nearbyPersons : undefined,
            lat: heroItem.lat,
            lng: heroItem.lng,
            locationName: locName || undefined,
          })
          return
        }

        // Check if location name was clicked (using closest for reliable detection)
        const clickedLoc = (e.target as HTMLElement).closest?.('[data-location-id]') as HTMLElement | null
        if (clickedLoc && heroItem.location_id) {
          // Location name click → close event panel + show location mini modal
          if (selectedEventRef.current) {
            setSelectedEventRef.current(null)
          }
          // Pan to location
          if (globeRef.current) {
            globeRef.current.pointOfView(
              { lat: heroItem.lat, lng: heroItem.lng, altitude: altitudeRef.current },
              600
            )
          }
          // Fetch events at this location
          try {
            const year = debouncedYearRef.current
            const params: Record<string, number> = { limit: 10, year_start: year - 100, year_end: year + 100 }
            const res = await nodesApi.getEvents(heroItem.location_id, params)
            const locLabel = (res.data?.location_name as string) || locName
            const events = (res.data?.events || []).map((ev: Record<string, unknown>) => ({
              id: ev.id as number,
              title: ev.title as string,
              title_ko: ev.title_ko as string | undefined,
              title_ja: ev.title_ja as string | undefined,
              year: ev.date_start as number | undefined,
              importance: ev.importance as number | undefined,
              category: ev.category as string | undefined,
              location_name: locLabel,
            }))
            if (events.length > 0) {
              setClusterPanelRef.current({
                events,
                lat: heroItem.lat,
                lng: heroItem.lng,
                locationName: locName || undefined,
              })
            }
          } catch (err) {
            console.error('Failed to fetch location events:', heroItem.location_id, err)
          }
          return
        }

        // Card body click → open event detail
        try {
          setLoadingMarkerId(heroItem.id)
          const cached = eventsDataRef.current?.find((ev: Event) => ev.id === heroItem.id)
          if (cached) {
            onEventClickRef.current(cached)
          } else {
            const res = await eventsApi.get(heroItem.id)
            onEventClickRef.current(res.data)
          }
        } catch (err) {
          console.error('Failed to fetch hero event:', heroItem.id, err)
        } finally {
          setLoadingMarkerId(null)
        }
      }
    } else if (item.kind === 'node') {
      // City pin: pin-head + stem + label
      const nodeItem = item as { tier: number; event_count: number; active_count: number; title: string; lat: number; lng: number; node_id: number; top_event: string | null; kind: 'node' }
      const isTier1 = nodeItem.tier === 1
      const hasActive = nodeItem.active_count > 0
      const tierClass = isTier1 ? 'city-pin--tier1' : 'city-pin--tier2'
      const activeClass = hasActive ? 'city-pin--active' : 'city-pin--inactive'
      const countText = nodeItem.active_count > 0
        ? nodeItem.active_count
        : nodeItem.event_count
      el.innerHTML = `
        <div class="city-pin ${tierClass} ${activeClass}">
          <div class="city-pin-label">
            ${nodeItem.title} <span class="city-pin-count">${countText}</span>
          </div>
          <div class="city-pin-stem"></div>
          <div class="city-pin-head">
            ${hasActive ? '<div class="city-pin-pulse"></div>' : ''}
          </div>
        </div>
      `
      el.style.pointerEvents = 'auto'
      el.onclick = async () => {
        // Close any open event detail panel so mini modal isn't faded
        if (selectedEventRef.current) {
          setSelectedEventRef.current(null)
        }
        // Open LocationDetailView on the right
        if (onLocationClickRef.current) {
          onLocationClickRef.current(nodeItem.node_id)
        }
        // Pan to location center
        if (globeRef.current) {
          const currentAlt = altitudeRef.current
          globeRef.current.pointOfView(
            { lat: nodeItem.lat, lng: nodeItem.lng, altitude: currentAlt },
            600
          )
        }
        // Always fetch events at this location (regardless of importance)
        try {
          const year = debouncedYearRef.current
          const hasActive = nodeItem.active_count > 0
          // If there are active events in the time range, use time filter
          // Otherwise, fetch ALL events at this location (no time filter)
          const params: Record<string, number> = { limit: 10 }
          if (hasActive) {
            params.year_start = year - 100
            params.year_end = year + 100
          }
          const res = await nodesApi.getEvents(nodeItem.node_id, params)
          const nodeLoc = (res.data?.location_name as string) || nodeItem.title
          const events = (res.data?.events || []).map((e: Record<string, unknown>) => ({
            id: e.id as number,
            title: e.title as string,
            title_ko: e.title_ko as string | undefined,
            title_ja: e.title_ja as string | undefined,
            year: e.date_start as number | undefined,
            importance: e.importance as number | undefined,
            category: e.category as string | undefined,
            location_name: nodeLoc,
          }))
          if (events.length > 0) {
            setClusterPanelRef.current({
              events,
              lat: nodeItem.lat,
              lng: nodeItem.lng,
              locationName: nodeItem.title,
            })
          }
        } catch (err) {
          console.error('Failed to fetch node events:', nodeItem.node_id, err)
        }
      }
    } else if (item.kind === 'event-panel') {
      // Mini modal floating above a city on the globe (events + persons)
      const panelItem = item as { lat: number; lng: number; events: ClusterEvent[]; persons?: NearbyPerson[]; locationName?: string; kind: 'event-panel' }
      const evtList = panelItem.events
      const personList = panelItem.persons || []
      const formatYear = (y?: number) => {
        if (y === undefined || y === null) return ''
        return y < 0 ? `${Math.abs(y)} BCE` : `${y} CE`
      }
      const lang = preferredLanguageRef.current
      const heroLocName = panelItem.locationName || ''

      // Helper: localized location name for an event
      const evtLocName = (evt: ClusterEvent) =>
        (lang === 'ko' && evt.location_name_ko) ? evt.location_name_ko
        : (lang === 'ja' && evt.location_name_ja) ? evt.location_name_ja
        : evt.location_name || ''

      // Helper: render a single event card
      const renderEventCard = (evt: ClusterEvent) => {
        const title = (lang === 'ko' && evt.title_ko) ? evt.title_ko
          : (lang === 'ja' && evt.title_ja) ? evt.title_ja
          : evt.title
        const cat = (evt.category || 'default').toLowerCase()
        const stars = evt.importance ? '\u2605'.repeat(Math.min(evt.importance, 5)) : ''
        return `
          <div class="globe-mini-modal-item globe-mini-modal-item--${cat}" data-event-id="${evt.id}">
            <div class="globe-mini-modal-item-title">${title}</div>
            <div class="globe-mini-modal-item-meta">
              <span class="globe-mini-modal-item-year">${formatYear(evt.year)}</span>
              ${stars ? `<span class="globe-mini-modal-item-stars">${stars}</span>` : ''}
            </div>
          </div>
        `
      }

      // Group events by location_name
      // If location_name is missing: use hero's location ONLY if event has no
      // separate coordinates, otherwise use "Nearby"
      const locationGroups = new Map<string, ClusterEvent[]>()
      for (const evt of evtList) {
        let locKey = evtLocName(evt)
        if (!locKey) {
          // No location name: check if event is at a different position from hero
          if (evt.lat != null && evt.lng != null) {
            const dist = Math.sqrt((evt.lat - panelItem.lat) ** 2 + (evt.lng - panelItem.lng) ** 2)
            locKey = dist < 0.5 ? (heroLocName || 'Nearby') : 'Nearby'
          } else {
            locKey = heroLocName || 'Nearby'
          }
        }
        if (!locationGroups.has(locKey)) locationGroups.set(locKey, [])
        locationGroups.get(locKey)!.push(evt)
      }

      // Distance helper (haversine approximation for sorting)
      const degDist = (lat1: number, lng1: number, lat2: number, lng2: number) => {
        const dlat = lat1 - lat2, dlng = lng1 - lng2
        return dlat * dlat + dlng * dlng
      }
      const avgDist = (events: ClusterEvent[], refLat: number, refLng: number) => {
        let sum = 0, count = 0
        for (const e of events) {
          if (e.lat != null && e.lng != null) { sum += degDist(e.lat, e.lng, refLat, refLng); count++ }
        }
        return count > 0 ? sum / count : 9999
      }

      // Sort: hero location first, then by distance from hero
      const sortedGroups = [...locationGroups.entries()].sort((a, b) => {
        const aIsHero = a[0] === heroLocName
        const bIsHero = b[0] === heroLocName
        if (aIsHero && !bIsHero) return -1
        if (!aIsHero && bIsHero) return 1
        return avgDist(a[1], panelItem.lat, panelItem.lng) - avgDist(b[1], panelItem.lat, panelItem.lng)
      })

      // Render grouped event cards
      const groupedEventsHtml = sortedGroups.map(([locName, events]) => {
        const isHeroLoc = locName === heroLocName
        const remoteClass = isHeroLoc ? '' : ' globe-mini-modal-loc-group--remote'
        const header = `<div class="globe-mini-modal-loc-group${remoteClass}">\ud83d\udccd ${locName} <span class="globe-mini-modal-loc-count">(${events.length})</span></div>`
        return header + events.map(renderEventCard).join('')
      }).join('')

      // Person section (only if there are persons)
      const personSectionLabel = personList.length > 0 ? `<div class="globe-mini-modal-section-label">\ud83d\udc64 Persons</div>` : ''
      const personCards = personList.map(p => {
        const name = (lang === 'ko' && p.name_ko) ? p.name_ko
          : (lang === 'ja' && p.name_ja) ? p.name_ja
          : p.name
        const years = (p.birth_year != null || p.death_year != null)
          ? `${formatYear(p.birth_year)}\u2013${formatYear(p.death_year)}`
          : ''
        return `
          <div class="globe-mini-modal-person" data-person-id="${p.id}">
            <div class="globe-mini-modal-person-name">${name}</div>
            <div class="globe-mini-modal-person-meta">
              ${p.role ? `<span class="globe-mini-modal-person-role">${p.role}</span>` : ''}
              ${years ? `<span class="globe-mini-modal-person-years">${years}</span>` : ''}
            </div>
          </div>
        `
      }).join('')

      const totalCount = evtList.length + personList.length
      const headerText = panelItem.locationName
        ? `${panelItem.locationName} \u00b7 ${totalCount}`
        : `${totalCount} Items`

      el.innerHTML = `
        <div class="globe-mini-modal">
          <div class="globe-mini-modal-header">
            <span class="globe-mini-modal-title">${headerText}</span>
            <button class="globe-mini-modal-close" data-close="true">\u2715</button>
          </div>
          <div class="globe-mini-modal-list">
            ${groupedEventsHtml}
            ${personSectionLabel}
            ${personCards}
          </div>
          <div class="globe-mini-modal-arrow"></div>
        </div>
      `
      el.style.pointerEvents = 'auto'
      el.style.zIndex = '10000'  // Always above hero cards

      // Close button
      const closeBtn = el.querySelector('[data-close]')
      if (closeBtn) {
        (closeBtn as HTMLElement).onclick = (e) => {
          e.stopPropagation()
          setClusterPanelRef.current(null)
        }
      }

      // Build event lookup for fly+pin
      const evtById = new Map(evtList.map(ev => [ev.id, ev]))

      // Event item clicks → fly to event + pin on globe + open NarrativePanel
      el.querySelectorAll('[data-event-id]').forEach(itemEl => {
        (itemEl as HTMLElement).onclick = async (e) => {
          e.stopPropagation()
          const eventId = parseInt((itemEl as HTMLElement).dataset.eventId || '0')
          if (!eventId) return
          const clusterEvt = evtById.get(eventId)
          try {
            const res = await eventsApi.get(eventId)
            onEventClickRef.current(res.data)
            setClusterPanelRef.current(null)
            // Pin event on globe + fly to it
            if (clusterEvt?.lat != null && clusterEvt?.lng != null) {
              useGlobeStore.getState().setPinnedEvent({
                id: eventId,
                title: clusterEvt.title,
                title_ko: clusterEvt.title_ko,
                title_ja: clusterEvt.title_ja,
                lat: clusterEvt.lat,
                lng: clusterEvt.lng,
                year: clusterEvt.year,
                category: clusterEvt.category,
                importance: clusterEvt.importance || 3,
              })
              useGlobeStore.getState().flyToLocation(clusterEvt.lat, clusterEvt.lng)
            } else if (res.data?.latitude != null && res.data?.longitude != null) {
              // Fallback: use coordinates from full event data
              useGlobeStore.getState().setPinnedEvent({
                id: eventId,
                title: res.data.title,
                title_ko: res.data.title_ko,
                lat: res.data.latitude,
                lng: res.data.longitude,
                year: res.data.date_start,
                importance: res.data.importance || 3,
              })
              useGlobeStore.getState().flyToLocation(res.data.latitude, res.data.longitude)
            }
          } catch (err) {
            console.error('Failed to fetch event:', eventId, err)
          }
        }
      })

      // Person item clicks
      el.querySelectorAll('[data-person-id]').forEach(itemEl => {
        (itemEl as HTMLElement).onclick = async (e) => {
          e.stopPropagation()
          const personId = parseInt((itemEl as HTMLElement).dataset.personId || '0')
          if (!personId) return
          setClusterPanelRef.current(null)
          if (onPersonClickRef.current) {
            onPersonClickRef.current(personId)
          } else {
            // Fallback: fetch person's events and open first one
            try {
              const res = await personsApi.getEvents(personId)
              if (res.data?.length > 0) {
                onEventClickRef.current(res.data[0])
              }
            } catch (err) {
              console.error('Failed to fetch person events:', personId, err)
            }
          }
        }
      })
    } else {
      // Anchor location fallback (subtle, always-visible city label)
      const anchorItem = item as { tier: number; event_count: number; title: string; lat: number; lng: number; kind: 'anchor' }
      const isTier1 = anchorItem.tier === 1
      const opacity = isTier1 ? 0.85 : 0.65
      const fontSize = isTier1 ? '10px' : '9px'
      el.innerHTML = `
        <div style="
          color: rgba(200, 220, 230, ${opacity});
          font-size: ${fontSize};
          font-weight: ${isTier1 ? '600' : '400'};
          white-space: nowrap;
          text-shadow: 0 0 4px rgba(0, 0, 0, 0.9), 0 0 8px rgba(0, 0, 0, 0.7);
          pointer-events: auto;
          cursor: pointer;
          letter-spacing: 0.02em;
          transform: translateY(-6px);
        ">
          ${anchorItem.title}
        </div>
      `
      el.style.pointerEvents = 'auto'
      el.onclick = () => {
        if (onLocationClickRef.current) {
          const anchor = anchorLocationsRef.current?.find(a => a.lat === anchorItem.lat && a.lng === anchorItem.lng)
          if (anchor) onLocationClickRef.current(anchor.id)
        }
      }
    }
    return el
  }, []) // Empty deps = stable function reference, uses refs for all mutable values

  // Points layer disabled - location nodes only

  // Note: Arc particle effects are achieved through dynamic arcDashLength,
  // arcDashGap, and arcDashAnimateTime props based on connection strength

  // LOD texture: use high-res from continental zoom onwards
  // When tiles are active, keep low-res background (tiles overlay on top)
  const isZoomedIn = currentZoomLevel === 'continental' || currentZoomLevel === 'regional' || currentZoomLevel === 'local'
  const hasTiles = tilesEnabled && globeTilesData.length > 0
  const globeTexture = hasTiles
    ? (GLOBE_TEXTURES_LO[globeStyle] || GLOBE_TEXTURES_LO.default)
    : isZoomedIn
      ? (GLOBE_TEXTURES_HI[globeStyle] || GLOBE_TEXTURES_LO[globeStyle] || GLOBE_TEXTURES_LO.default)
      : (GLOBE_TEXTURES_LO[globeStyle] || GLOBE_TEXTURES_LO.default)
  const isHoloStyle = globeStyle === 'holo'

  // Preload high-res texture at cosmic zoom so it's ready when user zooms in
  useEffect(() => {
    if (currentZoomLevel === 'cosmic' || currentZoomLevel === 'continental') {
      const hiUrl = GLOBE_TEXTURES_HI[globeStyle]
      if (hiUrl) {
        const img = new Image()
        img.src = hiUrl
      }
    }
  }, [currentZoomLevel, globeStyle])

  // Dismiss mini modal on time change (not zoom - zoom animation would close it)
  useEffect(() => {
    setClusterPanel(null)
  }, [debouncedYear])

  // Atmosphere color based on style
  const atmosphereColor = '#00d4ff'

  // Memoize ringsData to prevent new array references on every render
  const ringsData = useMemo(() => [
    ...(focusedLocation ? [{ ...focusedLocation, type: 'focused' }] : []),
    ...highlightedLocations.map(loc => ({ lat: loc.lat, lng: loc.lng, title: loc.title, type: 'highlighted' })),
    ...(isHoloStyle && !focusedLocation && highlightedLocations.length === 0 ? [{ lat: 0, lng: 0, type: 'ambient' }] : [])
  ], [focusedLocation, highlightedLocations, isHoloStyle])

  // Memoize other array props to prevent unnecessary three-globe re-processing
  const pathsData = useMemo(() => isHoloStyle ? GRATICULES : EMPTY_ARRAY, [isHoloStyle])
  const polygonsData = useMemo(() => isHoloStyle ? countries : EMPTY_ARRAY, [isHoloStyle, countries])
  const hexBinData = useMemo(() => showHeatmap ? visibleMarkers : EMPTY_ARRAY, [showHeatmap, visibleMarkers])
  // Connector arcs: hero → distant nearby event original positions
  const connectorArcs = useMemo(() => {
    if (!smartMarkers?.heroes || activeShift) return EMPTY_ARRAY
    const arcs: GlobeArc[] = []
    for (const hero of smartMarkers.heroes) {
      for (const ne of (hero.nearby_events || [])) {
        if (ne.lat == null || ne.lng == null) continue
        const dist = Math.sqrt((hero.lat - ne.lat) ** 2 + (hero.lng - ne.lng) ** 2)
        if (dist < 0.5) continue // same location — no arc needed
        arcs.push({
          connection_id: -ne.id, // negative to avoid collision with real arcs
          source_event_id: hero.id,
          target_event_id: ne.id,
          source_title: hero.title,
          target_title: ne.title,
          source_lat: hero.lat,
          source_lng: hero.lng,
          target_lat: ne.lat,
          target_lng: ne.lng,
          source_year: hero.year ?? null,
          target_year: ne.year ?? null,
          layer_type: 'connector',
          connection_type: null,
          direction: 'none',
          strength: 1,
        })
      }
    }
    return arcs
  }, [smartMarkers, activeShift])

  const arcsDataMemo = useMemo(() => {
    const base = eventArcs || EMPTY_ARRAY
    return connectorArcs.length ? [...base, ...connectorArcs] : base
  }, [eventArcs, connectorArcs])

  const isShifted = !!selectedEvent
  const isInShiftMode = !!activeShift

  return (
    <div className={`globe-container style-${globeStyle} ${isShifted ? 'shifted' : ''} ${isInShiftMode ? 'shift-mode' : ''}`} key={globeStyle}>
      <Globe
        ref={globeRef}
        // Globe appearance based on style
        globeImageUrl={isHoloStyle ? undefined : globeTexture}
        bumpImageUrl={isHoloStyle ? undefined : "//unpkg.com/three-globe/example/img/earth-topology.png"}
        backgroundImageUrl="//unpkg.com/three-globe/example/img/night-sky.png"
        showGlobe={true}
        showAtmosphere={true}
        atmosphereColor={atmosphereColor}
        atmosphereAltitude={isHoloStyle ? 0.25 : 0.22}
        // For holo: show graticule lines
        pathsData={pathsData}
        pathPoints="coords"
        pathColor={() => 'rgba(0, 212, 255, 0.5)'}
        pathStroke={1.5}
        // Polygons Layer (Countries) - for HOLO mode
        polygonsData={polygonsData}
        polygonCapColor={() => 'rgba(0, 180, 220, 0.6)'}
        polygonSideColor={() => 'rgba(0, 212, 255, 0.2)'}
        polygonStrokeColor={() => 'rgba(0, 212, 255, 0.8)'}
        polygonAltitude={0.01}
        // Points Layer - disabled (location nodes only)
        pointsData={EMPTY_ARRAY}
        pointLat={(d) => (d as GlobeMarker).lat}
        pointLng={(d) => (d as GlobeMarker).lng}
        pointColor={() => '#00d4ff'}
        pointAltitude={() => 0.03}
        pointRadius={() => 0.8}
        pointLabel={() => ''}
        onPointClick={async (point) => {
          const marker = point as GlobeMarker
          const markerType = marker.type || 'event'
          const markerId = marker.id

          // For events: try cache first, then fetch
          if (markerType === 'event') {
            const matchingEvent = eventsData?.find((e: Event) => e.id === markerId)
            if (matchingEvent) {
              onEventClick(matchingEvent)
              return
            }

            // Cache miss - fetch individual event
            try {
              setLoadingMarkerId(markerId)
              const res = await eventsApi.get(markerId)
              onEventClick(res.data)
            } catch (err) {
              console.error('Failed to fetch event:', markerId, err)
            } finally {
              setLoadingMarkerId(null)
            }
            return
          }

          // Person marker - open person detail panel
          if (markerType === 'person') {
            if (onPersonClick) {
              onPersonClick(markerId)
            } else {
              // Fallback: find related events
              try {
                setLoadingMarkerId(markerId)
                const eventsRes = await personsApi.getEvents(markerId)
                if (eventsRes.data?.length > 0) {
                  onEventClick(eventsRes.data[0])
                }
              } catch (err) {
                console.error('Failed to fetch person events:', markerId, err)
              } finally {
                setLoadingMarkerId(null)
              }
            }
            return
          }

          // Location marker - open location detail panel
          if (markerType === 'location') {
            if (onLocationClick) {
              onLocationClick(markerId)
            } else {
              // Fallback: find related events
              try {
                setLoadingMarkerId(markerId)
                const eventsRes = await locationsApi.getEvents(markerId, { limit: 1 })
                if (eventsRes.data?.items?.length > 0) {
                  onEventClick(eventsRes.data.items[0])
                }
              } catch (err) {
                console.error('Failed to fetch location events:', markerId, err)
              } finally {
                setLoadingMarkerId(null)
              }
            }
            return
          }
        }}
        // Labels Layer removed - location nodes provide context instead
        labelsData={EMPTY_ARRAY}
        onPointHover={(point) => {
          if (!point) return
          const marker = point as GlobeMarker
          const markerType = marker.type || 'event'
          const markerId = marker.id

          // Prefetch based on type
          if (markerType === 'event') {
            queryClient.prefetchQuery({
              queryKey: ['event', markerId],
              queryFn: () => eventsApi.get(markerId),
              staleTime: 5 * 60 * 1000, // 5 minutes
            })
          } else if (markerType === 'person') {
            queryClient.prefetchQuery({
              queryKey: ['person', markerId],
              queryFn: () => personsApi.get(markerId),
              staleTime: 5 * 60 * 1000,
            })
          } else if (markerType === 'location') {
            queryClient.prefetchQuery({
              queryKey: ['location', markerId],
              queryFn: () => locationsApi.get(markerId),
              staleTime: 5 * 60 * 1000,
            })
          }
        }}
        onZoom={handleZoom}
        // Ring effect - for focused location and highlighted locations from SHEBA search
        ringsData={ringsData}
        ringColor={(d: { type?: string }) =>
          d.type === 'focused' ? 'rgba(255, 51, 102, 0.6)' :
          d.type === 'highlighted' ? 'rgba(255, 215, 0, 0.8)' :  // Golden glow for SHEBA results
          'rgba(0, 212, 255, 0.3)'
        }
        ringMaxRadius={(d: { type?: string }) => d.type === 'ambient' ? 90 : 8}
        ringPropagationSpeed={(d: { type?: string }) => d.type === 'ambient' ? 2 : 3}
        ringRepeatPeriod={(d: { type?: string }) => d.type === 'ambient' ? 2000 : 800}
        // Custom HTML elements for location anchors + SHEBA highlighted locations
        htmlElementsData={htmlElements}
        htmlLat={(d) => (d as { lat: number }).lat}
        htmlLng={(d) => (d as { lng: number }).lng}
        htmlAltitude={(d) => {
          const item = d as { kind?: string }
          if (item.kind === 'event-panel') return 0.012
          if (item.kind === 'highlight') return 0.01
          if (item.kind === 'shift-page') return 0.008
          if (item.kind === 'hero') return 0.005
          if (item.kind === 'node') return 0.002
          return 0 // anchor
        }}
        htmlTransitionDuration={1}
        htmlElement={htmlElementFn}
        // Historical Chain Arcs - connections between events with particle animation
        arcsData={arcsDataMemo}
        arcStartLat={(d) => (d as GlobeArc).source_lat}
        arcStartLng={(d) => (d as GlobeArc).source_lng}
        arcEndLat={(d) => (d as GlobeArc).target_lat}
        arcEndLng={(d) => (d as GlobeArc).target_lng}
        arcColor={(d: object) => {
          const arc = d as GlobeArc
          if (arc.layer_type === 'connector') return ['#64748b44', '#64748b22', '#64748b44']
          const color = LAYER_COLORS[arc.layer_type] || '#00d4ff'
          return [`${color}ff`, `${color}88`, `${color}ff`]
        }}
        arcStroke={(d: object) => {
          const arc = d as GlobeArc
          if (arc.layer_type === 'connector') return 0.4
          return Math.min(3.5, Math.max(1.0, arc.strength / 7))
        }}
        arcDashLength={(d: object) => {
          const arc = d as GlobeArc
          if (arc.layer_type === 'connector') return 0.8
          // Dynamic dash length - shorter for person links, longer for causal
          const baseLength = arc.layer_type === 'person' ? 0.15 : arc.layer_type === 'causal' ? 0.4 : 0.25
          return baseLength + (arc.strength / 50)
        }}
        arcDashGap={(d: object) => {
          const arc = d as GlobeArc
          if (arc.layer_type === 'connector') return 0.01
          // Dynamic gap - creates particle-like effect
          const baseGap = arc.layer_type === 'person' ? 0.3 : 0.15
          return baseGap
        }}
        arcDashAnimateTime={(d: object) => {
          const arc = d as GlobeArc
          if (arc.layer_type === 'connector') return 0 // no animation
          // Faster animation for stronger connections (600-2500ms)
          const baseSpeed = 2500 - (arc.strength * 80)
          return Math.max(600, Math.min(2500, baseSpeed))
        }}
        arcAltitudeAutoScale={(d: object) => {
          const arc = d as GlobeArc
          if (arc.layer_type === 'connector') return 0.03
          // Higher arcs for stronger/longer connections
          return 0.3 + (arc.strength / 50)
        }}
        arcLabel={(d: object) => {
          const arc = d as GlobeArc
          if (arc.layer_type === 'connector') return ''
          const formatYear = (y: number | null) => {
            if (y === null) return '?'
            return y < 0 ? `${Math.abs(y)} BCE` : `${y} CE`
          }
          return `
            <div style="
              background: rgba(10, 14, 23, 0.95);
              border: 1px solid ${LAYER_COLORS[arc.layer_type] || '#00d4ff'};
              border-radius: 6px;
              padding: 10px 14px;
              font-size: 12px;
              color: #e2e8f0;
              max-width: 300px;
            ">
              <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                <span style="
                  background: ${LAYER_COLORS[arc.layer_type] || '#00d4ff'};
                  padding: 2px 6px;
                  border-radius: 3px;
                  font-size: 10px;
                  font-weight: 600;
                  color: #000;
                  text-transform: uppercase;
                ">${arc.layer_type}</span>
                ${arc.connection_type ? `<span style="color: #64748b; font-size: 10px;">${arc.connection_type}</span>` : ''}
                <span style="color: #fbbf24; font-size: 11px; margin-left: auto;">⚡ ${arc.strength.toFixed(1)}</span>
              </div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <div style="flex: 1; text-align: left;">
                  <div style="color: #00d4ff; font-weight: 500;">${arc.source_title}</div>
                  <div style="color: #64748b; font-size: 10px;">${formatYear(arc.source_year)}</div>
                </div>
                <div style="color: #64748b; font-size: 16px;">→</div>
                <div style="flex: 1; text-align: right;">
                  <div style="color: #00d4ff; font-weight: 500;">${arc.target_title}</div>
                  <div style="color: #64748b; font-size: 10px;">${formatYear(arc.target_year)}</div>
                </div>
              </div>
            </div>
          `
        }}
        onArcClick={(arc: object) => {
          const arcData = arc as GlobeArc
          // Click on arc navigates to the target event
          const targetEvent = eventsData?.find((e: Event) => e.id === arcData.target_event_id)
          if (targetEvent) {
            onEventClick(targetEvent)
          }
        }}
        // Heatmap Layer - Event density visualization using hex bins
        hexBinPointsData={hexBinData}
        hexBinPointLat={(d: object) => (d as GlobeMarker).lat}
        hexBinPointLng={(d: object) => (d as GlobeMarker).lng}
        hexBinPointWeight={() => 1}
        hexBinResolution={3}
        hexTopColor={(d: object) => {
          // FGO-style gradient based on point density
          const { sumWeight } = d as { sumWeight: number }
          const maxDensity = 20 // Adjust based on expected max density
          const t = Math.min(1, Math.pow(sumWeight / maxDensity, 0.6))
          if (t < 0.33) {
            return `rgba(0, 212, 255, ${0.3 + 0.3 * t * 3})`
          } else if (t < 0.66) {
            const s = (t - 0.33) / 0.33
            return `rgba(${Math.round(100 * s)}, ${Math.round(150 - 50 * s)}, 220, ${0.6 + 0.2 * s})`
          } else {
            const s = (t - 0.66) / 0.34
            return `rgba(${Math.round(100 + 155 * s)}, ${Math.round(100 - 68 * s)}, ${Math.round(220 + 35 * s)}, ${0.8 + 0.2 * s})`
          }
        }}
        hexSideColor={(d: object) => {
          const { sumWeight } = d as { sumWeight: number }
          const maxDensity = 20
          const t = Math.min(1, Math.pow(sumWeight / maxDensity, 0.6))
          return `rgba(0, 180, 220, ${0.2 + 0.3 * t})`
        }}
        hexAltitude={(d: object) => {
          const { sumWeight } = d as { sumWeight: number }
          const maxDensity = 20
          return Math.min(0.5, 0.02 + 0.48 * Math.pow(sumWeight / maxDensity, 0.5))
        }}
        hexBinMerge={true}
        hexLabel={(d: object) => {
          const { sumWeight, center } = d as { sumWeight: number; center: { lat: number; lng: number } }
          return `
            <div style="
              background: rgba(10, 14, 23, 0.95);
              border: 1px solid rgba(0, 212, 255, 0.5);
              border-radius: 6px;
              padding: 8px 12px;
              font-size: 12px;
              color: #e2e8f0;
            ">
              <div style="color: #00d4ff; font-weight: 600; margin-bottom: 4px;">
                Event Cluster
              </div>
              <div style="color: #8ba4b4;">${Math.round(sumWeight)} events</div>
              <div style="color: #64748b; font-size: 10px; margin-top: 4px;">
                ${center.lat.toFixed(1)}°, ${center.lng.toFixed(1)}°
              </div>
            </div>
          `
        }}
        // Tiles Layer - high-resolution slippy map tiles for REGIONAL/LOCAL zoom
        tilesData={globeTilesData}
        tileLat={(d: object) => (d as TileData).lat}
        tileLng={(d: object) => (d as TileData).lng}
        tileWidth={(d: object) => (d as TileData).widthDeg}
        tileHeight={(d: object) => (d as TileData).heightDeg}
        tileAltitude={0.0001}
        tileMaterial={(d: object) => (d as TileData).material}
        tileCurvatureResolution={(d: object) => {
          // Degrees per segment — lower = more segments = smoother sphere conformance
          // Large tiles (z=2, ~90°) need very fine resolution; small tiles (z=9+) can be coarser
          const w = (d as TileData).widthDeg
          if (w > 45) return 0.3   // z=2: ~90° tiles, need many segments
          if (w > 20) return 0.5   // z=3-4: ~45° tiles
          if (w > 5) return 1      // z=5-6: ~10-20 segments
          return 2                  // z=7+: tiles small enough
        }}
        tileUseGlobeProjection={true}
        tilesTransitionDuration={0}
      />

      {/* Heatmap Toggle */}
      <button
        onClick={handleHeatmapToggle}
        title={showHeatmap ? 'Hide heatmap' : 'Show heatmap'}
        className={`heatmap-toggle ${showHeatmap ? 'active' : ''}`}
      >
        {showHeatmap ? 'Heatmap ON' : 'Heatmap'}
      </button>

      {/* Show All Cities Toggle */}
      <button
        onClick={() => setShowAllCities(prev => !prev)}
        title={showAllCities ? 'Show only active cities' : 'Show all cities'}
        className={`globe-overlay-btn ${showAllCities ? 'active' : ''}`}
      >
        {showAllCities ? 'Cities ON' : 'Cities'}
      </button>

      {/* Camera Mode Toggle */}
      <CameraModeToggle />

      {/* Zoom Controls */}
      <div className="globe-zoom-controls">
        <button
          className="globe-zoom-btn"
          onClick={() => {
            if (globeRef.current) {
              const pov = globeRef.current.pointOfView()
              const newAlt = Math.max(0.05, pov.altitude * 0.6)
              globeRef.current.pointOfView({ ...pov, altitude: newAlt }, 500)
            }
          }}
          title="Zoom in"
        >+</button>
        <button
          className="globe-zoom-btn"
          onClick={() => {
            if (globeRef.current) {
              const pov = globeRef.current.pointOfView()
              const maxAlt = shiftMaxAltRef.current
              const newAlt = Math.min(maxAlt ?? 4.0, pov.altitude * 1.7)
              globeRef.current.pointOfView({ ...pov, altitude: newAlt }, 500)
            }
          }}
          title="Zoom out"
        >&minus;</button>
      </div>

    </div>
  )
}
