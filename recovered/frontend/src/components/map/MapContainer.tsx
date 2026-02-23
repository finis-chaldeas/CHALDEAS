import { useEffect, useRef, useCallback, useMemo } from 'react'
import { MapContainer as LeafletMapContainer, TileLayer, CircleMarker, Tooltip, useMap, useMapEvents } from 'react-leaflet'
import { useGlobeStore, altitudeToLeafletZoom, leafletZoomToAltitude } from '../../store/globeStore'
import type { GlobeMarkerData } from '../../store/globeStore'
import type { Event } from '../../types'
import 'leaflet/dist/leaflet.css'
import './MapContainer.css'

// Category-based colors (matches GlobeContainer scheme)
const CATEGORY_COLORS: Record<string, string> = {
  battle: '#ff3366',
  war: '#ff3366',
  politics: '#4a9eff',
  political: '#4a9eff',
  religion: '#ffa500',
  religious: '#ffa500',
  philosophy: '#9966ff',
  science: '#00ff88',
  discovery: '#00ff88',
  civilization: '#00d4ff',
  cultural: '#a855f7',
  evenementielle: '#00d4ff',
  conjoncture: '#22c55e',
  longue_duree: '#f59e0b',
}

const TYPE_COLORS: Record<string, string> = {
  event: '#00d4ff',
  person: '#fbbf24',
  location: '#34d399',
}

function getMarkerColor(marker: GlobeMarkerData): string {
  if (marker.type === 'person') return TYPE_COLORS.person
  if (marker.type === 'location') return TYPE_COLORS.location
  const cat = marker.category?.toLowerCase() || ''
  return CATEGORY_COLORS[cat] || marker.color || TYPE_COLORS.event
}

function getMarkerRadius(marker: GlobeMarkerData, zoom: number): number {
  const base = marker.type === 'person' ? 6 : marker.type === 'location' ? 5 : 4
  // Scale with zoom: larger at higher zoom levels
  const scale = Math.max(0.8, Math.min(2, zoom / 10))
  return base * scale
}

interface MapSyncProps {
  center: [number, number]
  zoom: number
  onZoomChange: (zoom: number) => void
  onMoveEnd: (lat: number, lng: number) => void
}

// Internal component to sync external state with Leaflet
function MapSync({ center, zoom, onZoomChange, onMoveEnd }: MapSyncProps) {
  const map = useMap()
  const isExternalUpdate = useRef(false)

  // Sync external center/zoom → Leaflet
  useEffect(() => {
    isExternalUpdate.current = true
    map.setView(center, zoom, { animate: false })
    // Reset flag after Leaflet processes the update
    requestAnimationFrame(() => {
      isExternalUpdate.current = false
    })
  }, [map, center, zoom])

  // Leaflet zoom/move → external state
  useMapEvents({
    zoomend: () => {
      if (!isExternalUpdate.current) {
        onZoomChange(map.getZoom())
      }
    },
    moveend: () => {
      if (!isExternalUpdate.current) {
        const c = map.getCenter()
        onMoveEnd(c.lat, c.lng)
      }
    },
  })

  return null
}

interface MapViewProps {
  markers: GlobeMarkerData[]
  onEventClick: (event: Event) => void
  onPersonClick?: (personId: number) => void
  onLocationClick?: (locationId: number) => void
  isShifted?: boolean
}

export function MapView({ markers, onEventClick, onPersonClick, onLocationClick, isShifted }: MapViewProps) {
  const { cameraPosition, setCameraPosition, setCameraMode, setViewportBounds } = useGlobeStore()

  const center = useMemo<[number, number]>(
    () => [cameraPosition.lat, cameraPosition.lng],
    [cameraPosition.lat, cameraPosition.lng]
  )
  const zoom = useMemo(
    () => altitudeToLeafletZoom(cameraPosition.altitude),
    [cameraPosition.altitude]
  )

  // Filter markers within reasonable time range (same as globe)
  const visibleMarkers = useMemo(() => {
    return markers.filter(m => m.lat !== 0 || m.lng !== 0) // Filter out zero-coord markers
  }, [markers])

  const handleZoomChange = useCallback((newZoom: number) => {
    const newAltitude = leafletZoomToAltitude(newZoom)
    setCameraPosition({ altitude: newAltitude })

    // Update viewport bounds
    const latSpan = Math.min(90, newAltitude * 40)
    const lngSpan = Math.min(180, newAltitude * 50)
    setViewportBounds({
      north: Math.min(90, cameraPosition.lat + latSpan),
      south: Math.max(-90, cameraPosition.lat - latSpan),
      east: cameraPosition.lng + lngSpan,
      west: cameraPosition.lng - lngSpan,
    })
  }, [setCameraPosition, setViewportBounds, cameraPosition.lat, cameraPosition.lng])

  const handleMoveEnd = useCallback((lat: number, lng: number) => {
    setCameraPosition({ lat, lng })
  }, [setCameraPosition])

  const handleMarkerClick = useCallback((marker: GlobeMarkerData) => {
    if (marker.type === 'event') {
      // Create a minimal Event object for the click handler
      const event: Event = {
        id: marker.id,
        title: marker.title,
        date_start: marker.year || 0,
        date_end: marker.year_end || undefined,
        importance: marker.importance || 1,
        latitude: marker.lat,
        longitude: marker.lng,
        category: marker.category || undefined,
        description: marker.description || undefined,
      }
      onEventClick(event)
    } else if (marker.type === 'person' && onPersonClick) {
      onPersonClick(marker.id)
    } else if (marker.type === 'location' && onLocationClick) {
      onLocationClick(marker.id)
    }
  }, [onEventClick, onPersonClick, onLocationClick])

  const handleReturnToGlobe = useCallback(() => {
    setCameraPosition({ altitude: 0.3 })
    setCameraMode('orbit')
  }, [setCameraPosition, setCameraMode])

  return (
    <div className={`map-view-container ${isShifted ? 'shifted' : ''}`}>
      <LeafletMapContainer
        center={center}
        zoom={zoom}
        minZoom={3}
        maxZoom={18}
        className="leaflet-map"
        zoomControl={false}
        attributionControl={true}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>'
          maxZoom={19}
        />

        <MapSync
          center={center}
          zoom={zoom}
          onZoomChange={handleZoomChange}
          onMoveEnd={handleMoveEnd}
        />

        {visibleMarkers.map((marker) => (
          <CircleMarker
            key={`${marker.type}-${marker.id}`}
            center={[marker.lat, marker.lng]}
            radius={getMarkerRadius(marker, zoom)}
            pathOptions={{
              color: getMarkerColor(marker),
              fillColor: getMarkerColor(marker),
              fillOpacity: 0.7,
              weight: 1,
              opacity: 0.9,
            }}
            eventHandlers={{
              click: () => handleMarkerClick(marker),
            }}
          >
            <Tooltip
              direction="top"
              offset={[0, -8]}
              className="map-marker-tooltip"
            >
              <div className="map-tooltip-content">
                <span className="map-tooltip-type" data-type={marker.type}>
                  {marker.type === 'person' ? '\uD83D\uDC64' : marker.type === 'location' ? '\uD83D\uDCCD' : '\uD83D\uDCDC'}
                  {' '}{marker.type}
                </span>
                <div className="map-tooltip-title">{marker.title}</div>
                {marker.year !== null && (
                  <div className="map-tooltip-year">
                    {Math.abs(marker.year)} {marker.year < 0 ? 'BCE' : 'CE'}
                  </div>
                )}
              </div>
            </Tooltip>
          </CircleMarker>
        ))}
      </LeafletMapContainer>

      {/* Mode indicator */}
      <div className="map-mode-indicator">
        <span className="map-mode-badge">2D MAP VIEW</span>
        <button className="map-return-btn" onClick={handleReturnToGlobe}>
          Zoom out to Globe
        </button>
      </div>
    </div>
  )
}
