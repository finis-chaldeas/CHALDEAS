import { useRef, useMemo, useEffect, useState, useCallback } from 'react'
import Globe, { GlobeMethods } from 'react-globe.gl'
import { useGlobeStore, getZoomLevel } from '../../store/globeStore'
import { useTimelineStore } from '../../store/timelineStore'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import { useDebounce } from '../../hooks/useDebounce'
import { useFlyMode } from '../../hooks/useFlyMode'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, eventsApi, personsApi, locationsApi, nodesApi, smartMarkersApi } from '../../api/client'
import type { Event, SmartMarkersResponse, ClusterEvent } from '../../types'
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
    cameraMode,
    autoRotate: storeAutoRotate,
    setViewportBounds,
    setCameraPosition,
    flyTarget,
    clearFlyTarget,
    setGlobeMarkers,
    viewMode,
  } = useGlobeStore()

  // Fly mode controls (WASD navigation)
  useFlyMode({ globeRef, enabled: cameraMode === 'fly' })
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
  const [currentZoomLevel, setCurrentZoomLevel] = useState<ReturnType<typeof getZoomLevel>>('cosmic')
  const [, setLoadingMarkerId] = useState<number | null>(null)
  const [clusterPanel, setClusterPanel] = useState<{ events: ClusterEvent[]; lat: number; lng: number; locationName?: string } | null>(null)
  const clusterPanelRef = useRef(clusterPanel)
  clusterPanelRef.current = clusterPanel
  const setClusterPanelRef = useRef(setClusterPanel)
  setClusterPanelRef.current = setClusterPanel

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
  const anchorLocationsRef = useRef<AnchorLocation[] | undefined>(undefined)
  const setSelectedEventRef = useRef(setSelectedEvent)
  setSelectedEventRef.current = setSelectedEvent
  const debouncedYearRef = useRef(debouncedYear)
  debouncedYearRef.current = debouncedYear
  const preferredLanguageRef = useRef(preferredLanguage)
  preferredLanguageRef.current = preferredLanguage

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
        altitudeRef.current = pov.altitude

        // Only trigger state update when zoom level actually changes
        const newZoom = getZoomLevel(pov.altitude)
        setCurrentZoomLevel(prev => prev === newZoom ? prev : newZoom)

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
        year_start: debouncedYear - 200,
        year_end: debouncedYear + 200,
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

  // Auto-rotate globe (only in orbit mode + cosmic zoom + store toggle)
  useEffect(() => {
    if (globeRef.current) {
      const controls = globeRef.current.controls()
      if (cameraMode === 'orbit') {
        // Auto-rotate only at cosmic zoom AND if store allows it
        const shouldAutoRotate = currentZoomLevel === 'cosmic' && storeAutoRotate
        controls.autoRotate = shouldAutoRotate
        controls.autoRotateSpeed = 0.3
        controls.enableRotate = true
        controls.enableZoom = true
      } else {
        // Disable orbit controls in fly mode
        controls.autoRotate = false
        controls.enableRotate = false
        controls.enableZoom = false
      }
    }
  }, [cameraMode, currentZoomLevel, storeAutoRotate])

  // Fly to location when flyTarget changes (from Navigator tabs, SHEBA episodes, etc.)
  useEffect(() => {
    if (flyTarget && globeRef.current) {
      // Stop auto-rotate when flying to a location
      if (cameraMode === 'orbit') {
        globeRef.current.controls().autoRotate = false
      }
      globeRef.current.pointOfView(
        { lat: flyTarget.lat, lng: flyTarget.lng, altitude: flyTarget.altitude },
        1000
      )
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
        // Stop auto-rotate when focusing (only in orbit mode)
        if (cameraMode === 'orbit') {
          globeRef.current.controls().autoRotate = false
        }

        // Rotate globe to focus on the location (0.8 = regional zoom, clearly focused but shows context)
        globeRef.current.pointOfView({ lat, lng, altitude: 0.8 }, 1000)

        // Set focused location for ring effect
        setFocusedLocation({ lat, lng })
      }
    } else {
      // Resume auto-rotate when no selection (only in orbit mode + store allows it)
      if (globeRef.current && cameraMode === 'orbit' && storeAutoRotate) {
        globeRef.current.controls().autoRotate = currentZoomLevel === 'cosmic'
      }
      setFocusedLocation(null)
    }
  }, [selectedEvent, cameraMode, storeAutoRotate, currentZoomLevel])

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

  // Sync globe markers to store (for Map view to consume)
  useEffect(() => {
    if (globeMarkers) setGlobeMarkers(globeMarkers)
  }, [globeMarkers, setGlobeMarkers])

  // Pause Three.js renderer when in map mode (performance)
  useEffect(() => {
    if (globeRef.current) {
      const renderer = globeRef.current.renderer()
      if (renderer) {
        if (viewMode === 'map') {
          renderer.setAnimationLoop(null)
        } else {
          // Re-enable - the globe library manages its own animation loop
          // Just trigger a re-render by changing POV slightly
          const pov = globeRef.current.pointOfView()
          if (pov) {
            globeRef.current.pointOfView(pov, 0)
          }
        }
      }
    }
  }, [viewMode])

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
        return showAllCities ? node.event_count >= 10 : node.event_count >= 20
      }
      if (currentZoomLevel === 'continental') {
        return showAllCities ? node.event_count >= 3 : node.event_count >= 5
      }
      if (currentZoomLevel === 'regional') {
        return node.event_count >= 1
      }
      // Local zoom: show all active
      return true
    })
  }, [locationNodes, currentZoomLevel, showAllCities])

  // Merge all marker types for htmlElementsData
  // Priority: SHEBA highlights > Hero cards > Cluster bubbles > Location nodes > Anchors
  const htmlElements = useMemo(() => {
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
        kind: 'hero' as const,
      })))
    }

    // 2b. Arc target events (connected events shown as hero cards even if low importance)
    if (eventArcs && eventArcs.length > 0) {
      const heroIds = new Set(smartMarkers?.heroes?.map(h => h.id) || [])
      eventArcs.forEach(arc => {
        // Add both source and target if not already in heroes
        if (!heroIds.has(arc.target_event_id)) {
          heroIds.add(arc.target_event_id)
          elements.push({
            id: arc.target_event_id,
            type: 'event',
            lat: arc.target_lat,
            lng: arc.target_lng,
            title: arc.target_title,
            year: arc.target_year,
            importance: 3,
            child_count: 0,
            kind: 'hero' as const,
            is_arc_target: true,
          })
        }
        if (!heroIds.has(arc.source_event_id)) {
          heroIds.add(arc.source_event_id)
          elements.push({
            id: arc.source_event_id,
            type: 'event',
            lat: arc.source_lat,
            lng: arc.source_lng,
            title: arc.source_title,
            year: arc.source_year,
            importance: 3,
            child_count: 0,
            kind: 'hero' as const,
            is_arc_target: true,
          })
        }
      })
    }

    // 3. Cluster bubbles (with top_events for browse panel)
    if (smartMarkers?.clusters) {
      elements.push(...smartMarkers.clusters.map(c => ({
        ...c,
        top_events: c.top_events || [],
        kind: 'cluster' as const,
      })))
    }

    // 4. Location nodes (city labels)
    if (visibleNodes.length > 0) {
      elements.push(...visibleNodes.map(node => ({
        lat: node.lat,
        lng: node.lng,
        title: getLocalizedText(node as unknown as Record<string, unknown>, 'name', preferredLanguage) || node.name,
        event_count: node.event_count,
        active_count: node.active_event_count,
        tier: node.tier,
        node_id: node.id,
        top_event: node.top_event,
        kind: 'node' as const,
      })))
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
    if (clusterPanel && clusterPanel.events.length > 0) {
      elements.push({
        lat: clusterPanel.lat,
        lng: clusterPanel.lng,
        events: clusterPanel.events,
        locationName: clusterPanel.locationName,
        kind: 'event-panel' as const,
      })
    }

    return elements
  }, [highlightedLocations, smartMarkers, eventArcs, visibleNodes, visibleAnchors, preferredLanguage, clusterPanel])

  // Stable htmlElement callback - uses refs to avoid function reference changes
  // that would cause three-globe to destroy and recreate all DOM elements
  const htmlElementFn = useCallback((d: object) => {
    const item = d as Record<string, unknown>
    const el = document.createElement('div')

    if (item.kind === 'highlight') {
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
      // Hero card: important event displayed as floating card
      const heroItem = item as { id: number; title: string; title_ko?: string; title_ja?: string; year?: number; year_end?: number; category?: string; importance: number; location_name?: string; location_name_ko?: string; location_name_ja?: string; location_id?: number; lat: number; lng: number; child_count: number; kind: 'hero' }
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

      // Fade/highlight is handled via CSS (.shifted .hero-card) + useEffect (.hero-selected)
      el.innerHTML = `
        <div class="hero-card ${categoryClass}" data-hero-id="${heroItem.id}">
          <div class="hero-card-title">${heroTitle}</div>
          <div class="hero-card-meta">
            <span class="hero-card-year">${formatYear(heroItem.year)}</span>
            ${locName ? `<span class="hero-card-location" data-location-id="${heroItem.location_id || ''}">${locName}</span>` : ''}
          </div>
          <div class="hero-card-importance">${stars}</div>
        </div>
      `
      el.style.pointerEvents = 'auto'

      el.onclick = async (e) => {
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
            const events = (res.data?.events || []).map((ev: Record<string, unknown>) => ({
              id: ev.id as number,
              title: ev.title as string,
              title_ko: ev.title_ko as string | undefined,
              title_ja: ev.title_ja as string | undefined,
              year: ev.date_start as number | undefined,
              importance: ev.importance as number | undefined,
              category: ev.category as string | undefined,
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
    } else if (item.kind === 'cluster') {
      // Cluster bubble: grouped events
      const clusterItem = item as { lat: number; lng: number; count: number; top_events?: ClusterEvent[]; kind: 'cluster' }
      const size = Math.max(28, Math.min(52, 20 + Math.log2(clusterItem.count) * 8))
      // Fade handled via CSS (.shifted .cluster-bubble)
      el.innerHTML = `
        <div class="cluster-bubble" style="
          width: ${size}px;
          height: ${size}px;
          transform: translate(-${size / 2}px, -${size / 2}px);
        ">
          ${clusterItem.count}
        </div>
      `
      el.style.pointerEvents = 'auto'
      el.onclick = () => {
        if (globeRef.current) {
          // Always zoom in by 40% (guaranteed to never zoom out)
          const currentAlt = altitudeRef.current
          const targetAlt = Math.max(0.08, currentAlt * 0.6)
          globeRef.current.pointOfView(
            { lat: clusterItem.lat, lng: clusterItem.lng, altitude: targetAlt },
            800
          )
          // Show mini modal with events above the cluster
          if (clusterItem.top_events && clusterItem.top_events.length > 0) {
            setClusterPanelRef.current({
              events: clusterItem.top_events,
              lat: clusterItem.lat,
              lng: clusterItem.lng,
            })
          }
        }
      }
    } else if (item.kind === 'node') {
      // Location node with event count badge
      const nodeItem = item as { tier: number; event_count: number; active_count: number; title: string; lat: number; lng: number; node_id: number; top_event: string | null; kind: 'node' }
      const isTier1 = nodeItem.tier === 1
      const hasActive = nodeItem.active_count > 0
      const textColor = hasActive
        ? (isTier1 ? 'rgba(0, 212, 255, 0.95)' : 'rgba(200, 220, 230, 0.85)')
        : 'rgba(120, 140, 150, 0.5)'
      const fontSize = isTier1 ? '11px' : '9px'
      const badgeColor = hasActive ? '#00d4ff' : '#3a4a5a'
      const countText = nodeItem.active_count > 0
        ? nodeItem.active_count
        : nodeItem.event_count
      el.innerHTML = `
        <div style="
          display: flex;
          align-items: center;
          gap: 4px;
          white-space: nowrap;
          pointer-events: auto;
          cursor: pointer;
          transform: translateY(-8px);
        ">
          <span style="
            color: ${textColor};
            font-size: ${fontSize};
            font-weight: ${isTier1 ? '700' : '500'};
            text-shadow: 0 0 4px rgba(0,0,0,0.9), 0 0 8px rgba(0,0,0,0.7);
            letter-spacing: 0.02em;
          ">${nodeItem.title}</span>
          <span style="
            background: ${badgeColor};
            color: ${hasActive ? '#000' : '#8a9ab0'};
            font-size: 9px;
            font-weight: 700;
            padding: 1px 5px;
            border-radius: 8px;
            min-width: 16px;
            text-align: center;
          ">${countText}</span>
        </div>
      `
      el.style.pointerEvents = 'auto'
      el.onclick = async () => {
        // Close any open event detail panel so mini modal isn't faded
        if (selectedEventRef.current) {
          setSelectedEventRef.current(null)
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
          const events = (res.data?.events || []).map((e: Record<string, unknown>) => ({
            id: e.id as number,
            title: e.title as string,
            title_ko: e.title_ko as string | undefined,
            title_ja: e.title_ja as string | undefined,
            year: e.date_start as number | undefined,
            importance: e.importance as number | undefined,
            category: e.category as string | undefined,
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
      // Mini modal floating above a city on the globe
      const panelItem = item as { lat: number; lng: number; events: ClusterEvent[]; locationName?: string; kind: 'event-panel' }
      const evtList = panelItem.events
      const formatYear = (y?: number) => {
        if (y === undefined || y === null) return ''
        return y < 0 ? `${Math.abs(y)} BCE` : `${y} CE`
      }
      const lang = preferredLanguageRef.current
      const eventCards = evtList.map(evt => {
        const title = (lang === 'ko' && evt.title_ko) ? evt.title_ko
          : (lang === 'ja' && evt.title_ja) ? evt.title_ja
          : evt.title
        const cat = (evt.category || 'default').toLowerCase()
        const stars = evt.importance ? '★'.repeat(Math.min(evt.importance, 5)) : ''
        return `
          <div class="globe-mini-modal-item globe-mini-modal-item--${cat}" data-event-id="${evt.id}">
            <div class="globe-mini-modal-item-title">${title}</div>
            <div class="globe-mini-modal-item-meta">
              <span class="globe-mini-modal-item-year">${formatYear(evt.year)}</span>
              ${stars ? `<span class="globe-mini-modal-item-stars">${stars}</span>` : ''}
            </div>
          </div>
        `
      }).join('')

      const headerText = panelItem.locationName
        ? `${panelItem.locationName} · ${evtList.length}`
        : `${evtList.length} Events`

      el.innerHTML = `
        <div class="globe-mini-modal">
          <div class="globe-mini-modal-header">
            <span class="globe-mini-modal-title">${headerText}</span>
            <button class="globe-mini-modal-close" data-close="true">✕</button>
          </div>
          <div class="globe-mini-modal-list">
            ${eventCards}
          </div>
          <div class="globe-mini-modal-arrow"></div>
        </div>
      `
      el.style.pointerEvents = 'auto'

      // Close button
      const closeBtn = el.querySelector('[data-close]')
      if (closeBtn) {
        (closeBtn as HTMLElement).onclick = (e) => {
          e.stopPropagation()
          setClusterPanelRef.current(null)
        }
      }

      // Event item clicks
      el.querySelectorAll('[data-event-id]').forEach(itemEl => {
        (itemEl as HTMLElement).onclick = async (e) => {
          e.stopPropagation()
          const eventId = parseInt((itemEl as HTMLElement).dataset.eventId || '0')
          if (eventId) {
            try {
              const res = await eventsApi.get(eventId)
              onEventClickRef.current(res.data)
              setClusterPanelRef.current(null)
            } catch (err) {
              console.error('Failed to fetch event:', eventId, err)
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

  // LOD texture: use high-res when zoomed in, low-res when zoomed out
  const isZoomedIn = currentZoomLevel === 'regional' || currentZoomLevel === 'local'
  const globeTexture = isZoomedIn
    ? (GLOBE_TEXTURES_HI[globeStyle] || GLOBE_TEXTURES_LO[globeStyle] || GLOBE_TEXTURES_LO.default)
    : (GLOBE_TEXTURES_LO[globeStyle] || GLOBE_TEXTURES_LO.default)
  const isHoloStyle = globeStyle === 'holo'

  // Preload high-res texture at continental zoom so it's ready when user zooms in further
  useEffect(() => {
    if (currentZoomLevel === 'continental') {
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

  const isShifted = !!selectedEvent

  return (
    <div className={`globe-container style-${globeStyle} ${isShifted ? 'shifted' : ''}`} key={globeStyle}>
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
        pathsData={isHoloStyle ? GRATICULES : []}
        pathPoints="coords"
        pathColor={() => 'rgba(0, 212, 255, 0.5)'}
        pathStroke={1.5}
        // Polygons Layer (Countries) - for HOLO mode
        polygonsData={isHoloStyle ? countries : []}
        polygonCapColor={() => 'rgba(0, 180, 220, 0.6)'}
        polygonSideColor={() => 'rgba(0, 212, 255, 0.2)'}
        polygonStrokeColor={() => 'rgba(0, 212, 255, 0.8)'}
        polygonAltitude={0.01}
        // Points Layer - disabled (location nodes only)
        pointsData={[]}
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
        labelsData={[]}
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
        ringsData={[
          ...(focusedLocation ? [{ ...focusedLocation, type: 'focused' }] : []),
          ...highlightedLocations.map(loc => ({ lat: loc.lat, lng: loc.lng, title: loc.title, type: 'highlighted' })),
          ...(isHoloStyle && !focusedLocation && highlightedLocations.length === 0 ? [{ lat: 0, lng: 0, type: 'ambient' }] : [])
        ]}
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
          const item = d as Record<string, unknown>
          if (item.kind === 'event-panel') return 0.08  // floating mini modal - highest
          if (item.kind === 'highlight') return 0.06
          if (item.kind === 'hero') return 0.04
          if (item.kind === 'cluster') return 0.03
          return 0.01 // nodes and anchors below heroes
        }}
        htmlTransitionDuration={0}
        htmlElement={htmlElementFn}
        // Historical Chain Arcs - connections between events with particle animation
        arcsData={eventArcs || []}
        arcStartLat={(d) => (d as GlobeArc).source_lat}
        arcStartLng={(d) => (d as GlobeArc).source_lng}
        arcEndLat={(d) => (d as GlobeArc).target_lat}
        arcEndLng={(d) => (d as GlobeArc).target_lng}
        arcColor={(d: object) => {
          const arc = d as GlobeArc
          const color = LAYER_COLORS[arc.layer_type] || '#00d4ff'
          return [`${color}ff`, `${color}88`, `${color}ff`]
        }}
        arcStroke={(d: object) => {
          const arc = d as GlobeArc
          return Math.min(3.5, Math.max(1.0, arc.strength / 7))
        }}
        arcDashLength={(d: object) => {
          const arc = d as GlobeArc
          // Dynamic dash length - shorter for person links, longer for causal
          const baseLength = arc.layer_type === 'person' ? 0.15 : arc.layer_type === 'causal' ? 0.4 : 0.25
          return baseLength + (arc.strength / 50)
        }}
        arcDashGap={(d: object) => {
          const arc = d as GlobeArc
          // Dynamic gap - creates particle-like effect
          const baseGap = arc.layer_type === 'person' ? 0.3 : 0.15
          return baseGap
        }}
        arcDashAnimateTime={(d: object) => {
          const arc = d as GlobeArc
          // Faster animation for stronger connections (600-2500ms)
          const baseSpeed = 2500 - (arc.strength * 80)
          return Math.max(600, Math.min(2500, baseSpeed))
        }}
        arcAltitudeAutoScale={(d: object) => {
          const arc = d as GlobeArc
          // Higher arcs for stronger/longer connections
          return 0.3 + (arc.strength / 50)
        }}
        arcLabel={(d: object) => {
          const arc = d as GlobeArc
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
        hexBinPointsData={showHeatmap ? visibleMarkers : []}
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

    </div>
  )
}
