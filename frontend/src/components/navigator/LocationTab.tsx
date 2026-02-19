/**
 * LocationTab - Viewport-aware historical places list
 *
 * - Global: major locations
 * - Regional/Local: locations within viewport bounds
 * - Shows type, event count, and [History] button
 */
import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { useDebounce } from '../../hooks/useDebounce'
import { api } from '../../api/client'
import type { ViewportBounds, ZoomLevel } from '../../store/globeStore'

interface LocationTabProps {
  viewportBounds: ViewportBounds | null
  zoomLevel: ZoomLevel
  onLocationClick: (locationId: number) => void
}

interface Location {
  id: number
  name: string
  name_ko?: string
  location_type?: string
  latitude?: number
  longitude?: number
  event_count?: number
}

type SortOption = 'default' | 'events'

function getTypeIcon(type?: string): string {
  const icons: Record<string, string> = {
    point: '\u{1F4CD}',
    natural: '\u{1F30D}',
    sea: '\u{1F30A}',
  }
  return icons[type || ''] || '\u{1F4CD}'
}

function getTypeLabel(type?: string): string {
  if (!type) return ''
  return type.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export function LocationTab({ viewportBounds, zoomLevel, onLocationClick }: LocationTabProps) {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<SortOption>('events')
  const debouncedBounds = useDebounce(viewportBounds, 300)

  const queryParams = useMemo(() => {
    const params: Record<string, unknown> = {
      limit: 100,
      sort_by: sortBy,
    }

    if (searchQuery) {
      params.q = searchQuery
    } else if (zoomLevel !== 'cosmic' && debouncedBounds) {
      params.lat_min = debouncedBounds.south
      params.lat_max = debouncedBounds.north
      params.lng_min = debouncedBounds.west
      params.lng_max = debouncedBounds.east
    }

    return params
  }, [searchQuery, zoomLevel, debouncedBounds, sortBy])

  const { data, isLoading } = useQuery({
    queryKey: ['navigator-locations', queryParams],
    queryFn: () => api.get('/locations', { params: queryParams }),
    select: (res) => res.data,
  })

  const locations: Location[] = data?.items || []

  return (
    <div className="navigator-tab-content">
      {/* Controls */}
      <div className="nav-controls">
        <div className="nav-controls-row">
          <input
            type="text"
            placeholder={t('navigator.searchLocations', 'Search locations...')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="nav-search-input"
          />
          <select
            className="nav-select nav-select-sm"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortOption)}
          >
            <option value="events">By Events</option>
            <option value="default">Default</option>
          </select>
        </div>
        <div className="nav-result-count">
          {locations.length} {t('navigator.locations', 'locations')}
          {zoomLevel !== 'cosmic' && <span className="nav-viewport-tag">viewport</span>}
        </div>
      </div>

      {/* List */}
      <div className="nav-list">
        {isLoading ? (
          <div className="navigator-loading">{t('common.loading', 'Loading...')}</div>
        ) : locations.length === 0 ? (
          <div className="navigator-empty">{t('navigator.noLocations', 'No locations found')}</div>
        ) : (
          locations.map((location) => (
            <div key={location.id} className="nav-location-card">
              <div className="nav-location-icon" onClick={() => onLocationClick(location.id)}>
                {getTypeIcon(location.location_type)}
              </div>
              <div className="nav-location-body" onClick={() => onLocationClick(location.id)}>
                <div className="nav-location-name">{location.name}</div>
                <div className="nav-location-meta">
                  {location.location_type && (
                    <span className="nav-location-type">{getTypeLabel(location.location_type)}</span>
                  )}
                </div>
              </div>
              {(location.event_count != null && location.event_count > 0) ? (
                <div className="nav-location-event-count" title={`${location.event_count} events`}>
                  {location.event_count}
                </div>
              ) : location.latitude != null && location.longitude != null ? (
                <div className="nav-location-coords" title="Coordinates">
                  {location.latitude.toFixed(1)}, {location.longitude.toFixed(1)}
                </div>
              ) : null}
              <button
                className="nav-location-history-btn"
                onClick={() => onLocationClick(location.id)}
                title="View History"
              >
                History &#9654;
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
