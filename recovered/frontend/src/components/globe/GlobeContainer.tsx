import { useRef, useMemo, useEffect, useState, useCallback } from 'react'
import Globe, { GlobeMethods } from 'react-globe.gl'
import { useGlobeStore, getZoomLevel } from '../../store/globeStore'
import { useTimelineStore } from '../../store/timelineStore'
import { useDebounce } from '../../hooks/useDebounce'
import { useFlyMode } from '../../hooks/useFlyMode'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, eventsApi, personsApi, locationsApi, nodesApi } from '../../api/client'
import type { Event } from '../../types'
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

// Globe texture URLs for different styles
const GLOBE_TEXTURES: Record<string, string> = {
  default: '//unpkg.com/three-globe/example/img/earth-blue-marble.jpg',
  // FGO Part 1 style - dark with visible land
  holo: '//unpkg.com/three-globe/example/img/earth-dark.jpg',
  // Night lights style
  night: '//unpkg.com/three-globe/example/img/earth-night.jpg',
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
    highlightedLocations,
    cameraMode,
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
  const debouncedYear = useDebounce(currentYear, 150) // Debounce API calls during timeline drag (150ms for snappier response)
  const [focusedLocation, setFocusedLocation] = useState<{ lat: number; lng: number } | null>(null)
  const [countries, setCountries] = useState<GeoJSONFeature[]>([])
  const [internalShowHeatmap, setInternalShowHeatmap] = useState(false)
  const [altitude, setAltitude] = useState(2.5) // Track zoom level for clustering
  const currentZoomLevel = useMemo(() => getZoomLevel(altitude), [altitude])
  const [, setLoadingMarkerId] = useState<number | null>(null)

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
  const handleZoom = useCallback(() => {
    if (globeRef.current) {
      const pov = globeRef.current.pointOfView()
      if (pov && typeof pov.altitude === 'number') {
        setAltitude(pov.altitude)

        // Update camera position in store
        setCameraPosition({ lat: pov.lat, lng: pov.lng, altitude: pov.altitude })

        // Compute approximate viewport bounds from altitude and center point
        // Rough: visible degrees ~ altitude * 40 (at altitude 2.5 ~ ±100 degrees)
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
    }
  }, [eventsData, setEvents])

  // Auto-rotate globe (only in orbit mode + cosmic/continental zoom)
  useEffect(() => {
    if (globeRef.current) {
      const controls = globeRef.current.controls()
      if (cameraMode === 'orbit') {
        // Auto-rotate only at cosmic zoom
        const shouldAutoRotate = currentZoomLevel === 'cosmic'
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
  }, [cameraMode, currentZoomLevel])

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
  }, [flyTarget, cameraMode, clearFlyTarget])

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

        // Rotate globe to focus on the location
        globeRef.current.pointOfView({ lat, lng, altitude: 2 }, 1000)

        // Set focused location for ring effect
        setFocusedLocation({ lat, lng })
      }
    } else {
      // Resume auto-rotate when no selection (only in orbit mode)
      if (globeRef.current && cameraMode === 'orbit') {
        globeRef.current.controls().autoRotate = true
      }
      setFocusedLocation(null)
    }
  }, [selectedEvent, cameraMode])

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
  const visibleAnchors = useMemo(() => {
    if (!anchorLocations) return []
    // Show tier 1 always, tier 2 only when zoomed in
    const maxTier = altitude > 2.0 ? 1 : altitude > 0.8 ? 2 : 3
    return anchorLocations.filter(loc => loc.tier <= maxTier)
  }, [anchorLocations, altitude])

  // Visible location nodes filtered by zoom + activity
  const visibleNodes = useMemo(() => {
    if (!locationNodes) return []
    return locationNodes.filter(node => {
      // At cosmic/continental zoom: only show nodes with events in current time range
      if (currentZoomLevel === 'cosmic') {
        return node.active_event_count > 0 && node.event_count >= 20
      }
      if (currentZoomLevel === 'continental') {
        return node.active_event_count > 0 && node.event_count >= 5
      }
      // At regional zoom: show active nodes, plus inactive with many total events
      if (currentZoomLevel === 'regional') {
        if (node.active_event_count > 0) return node.event_count >= 1
        return node.event_count >= 20 // Only show major inactive cities
      }
      // Local zoom: show all
      return true
    })
  }, [locationNodes, currentZoomLevel])

  // Merge anchor locations + nodes + SHEBA highlighted locations for htmlElementsData
  const htmlElements = useMemo(() => {
    // SHEBA highlights take priority
    if (highlightedLocations.length > 0) {
      return highlightedLocations.map(loc => ({
        ...loc,
        kind: 'highlight' as const,
      }))
    }

    // Use location nodes as primary labels (with event counts)
    if (visibleNodes.length > 0) {
      return visibleNodes.map(node => ({
        lat: node.lat,
        lng: node.lng,
        title: node.name,
        event_count: node.event_count,
        active_count: node.active_event_count,
        tier: node.tier,
        node_id: node.id,
        top_event: node.top_event,
        kind: 'node' as const,
      }))
    }

    // Fallback to anchor locations
    return visibleAnchors.map(loc => ({
      lat: loc.lat,
      lng: loc.lng,
      title: loc.name,
      event_count: loc.event_count,
      tier: loc.tier,
      kind: 'anchor' as const,
    }))
  }, [highlightedLocations, visibleNodes, visibleAnchors])

  // Points layer disabled - location nodes only

  // Note: Arc particle effects are achieved through dynamic arcDashLength,
  // arcDashGap, and arcDashAnimateTime props based on connection strength

  const globeTexture = GLOBE_TEXTURES[globeStyle] || GLOBE_TEXTURES.default
  const isHoloStyle = globeStyle === 'holo'

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
        htmlAltitude={0.02}
        htmlElement={(d) => {
          const item = d as (typeof htmlElements)[0]
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
              const event = events.find(e =>
                Math.abs((e.latitude || 0) - item.lat) < 0.1 &&
                Math.abs((e.longitude || 0) - item.lng) < 0.1
              )
              if (event) onEventClick(event)
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
            el.onclick = () => {
              if (onLocationClick) {
                onLocationClick(nodeItem.node_id)
              }
            }
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
              if (onLocationClick) {
                // Find the location id from anchor data
                const anchor = anchorLocations?.find(a => a.lat === anchorItem.lat && a.lng === anchorItem.lng)
                if (anchor) onLocationClick(anchor.id)
              }
            }
          }
          return el
        }}
        // Historical Chain Arcs - connections between events with particle animation
        arcsData={eventArcs || []}
        arcStartLat={(d) => (d as GlobeArc).source_lat}
        arcStartLng={(d) => (d as GlobeArc).source_lng}
        arcEndLat={(d) => (d as GlobeArc).target_lat}
        arcEndLng={(d) => (d as GlobeArc).target_lng}
        arcColor={(d: object) => {
          const arc = d as GlobeArc
          const color = LAYER_COLORS[arc.layer_type] || '#00d4ff'
          // Create glowing gradient effect
          return [`${color}ff`, `${color}88`, `${color}ff`]
        }}
        arcStroke={(d: object) => {
          const arc = d as GlobeArc
          // Dynamic stroke width based on strength (1.0 to 3.5)
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
        className={`absolute bottom-20 right-16 z-10 flex items-center gap-1.5
                    bg-chaldea-panel/80 backdrop-blur-xl border rounded-lg px-3 py-1.5
                    text-[10px] font-medium transition-all
                    ${showHeatmap
                      ? 'border-chaldea-cyan/30 text-chaldea-cyan'
                      : 'border-chaldea-border/30 text-chaldea-text/60 hover:border-chaldea-cyan/20 hover:text-chaldea-text'}`}
      >
        {showHeatmap ? 'Heatmap ON' : 'Heatmap'}
      </button>

      {/* Camera Mode Toggle */}
      <CameraModeToggle className="absolute top-3 left-3 z-10" />


    </div>
  )
}
