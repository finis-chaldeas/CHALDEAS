/**
 * EventTab - Viewport-aware event list with multiple sort options
 *
 * - Global: top events for current era, sorted by importance/connections/date
 * - Regional/Local: events within viewport bounds
 * - Rich card display with importance dots, connection count, location
 */
import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { useDebounce } from '../../hooks/useDebounce'
import { api } from '../../api/client'
import type { Event } from '../../types'
import type { ViewportBounds, ZoomLevel } from '../../store/globeStore'

interface EventTabProps {
  currentYear: number
  viewportBounds: ViewportBounds | null
  zoomLevel: ZoomLevel
  selectedEventId?: number | string | null
  onEventClick: (event: Event) => void
}

const TIME_RANGE = 50

type SortOption = 'importance' | 'date'

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'importance', label: 'Importance' },
  { value: 'date', label: 'Date' },
]

const CATEGORY_OPTIONS = [
  { value: 'all', label: 'All Categories' },
  { value: 'battle', label: 'Battle' },
  { value: 'war', label: 'War' },
  { value: 'politics', label: 'Politics' },
  { value: 'religion', label: 'Religion' },
  { value: 'philosophy', label: 'Philosophy' },
  { value: 'science', label: 'Science' },
  { value: 'culture', label: 'Culture' },
  { value: 'civilization', label: 'Civilization' },
  { value: 'discovery', label: 'Discovery' },
]

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

function getImportanceDots(importance: number): string {
  const filled = Math.min(importance, 5)
  const empty = 5 - filled
  return '\u2B24'.repeat(filled) + '\u25CB'.repeat(empty)
}

function getImportanceColor(importance: number): string {
  if (importance >= 5) return '#ffd700'
  if (importance >= 4) return '#00d4ff'
  if (importance >= 3) return '#8ba4b4'
  return '#4a5568'
}

function getCategoryColor(slug: string): string {
  const colors: Record<string, string> = {
    battle: '#ef4444',
    war: '#ef4444',
    politics: '#3b82f6',
    religion: '#a855f7',
    philosophy: '#ec4899',
    science: '#22c55e',
    culture: '#fbbf24',
    civilization: '#00d4ff',
    discovery: '#34d399',
  }
  return colors[slug] || '#6b7280'
}

export function EventTab({
  currentYear,
  viewportBounds,
  zoomLevel,
  selectedEventId,
  onEventClick,
}: EventTabProps) {
  const { t } = useTranslation()
  const [sortBy, setSortBy] = useState<SortOption>('importance')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const debouncedYear = useDebounce(currentYear, 150)
  const debouncedBounds = useDebounce(viewportBounds, 300)

  const queryParams = useMemo(() => {
    const params: Record<string, unknown> = {
      year_start: debouncedYear - TIME_RANGE,
      year_end: debouncedYear + TIME_RANGE,
      sort_by: sortBy,
      limit: 200,
    }

    if (zoomLevel !== 'cosmic' && debouncedBounds) {
      params.lat_min = debouncedBounds.south
      params.lat_max = debouncedBounds.north
      params.lng_min = debouncedBounds.west
      params.lng_max = debouncedBounds.east
      params.limit = 500
    }

    if (categoryFilter !== 'all') {
      params.category = categoryFilter
    }

    return params
  }, [debouncedYear, zoomLevel, debouncedBounds, categoryFilter, sortBy])

  const { data: response, isLoading } = useQuery({
    queryKey: ['navigator-events', queryParams],
    queryFn: () => api.get('/events', { params: queryParams }),
    select: (res) => res.data,
  })

  const events: Event[] = response?.items || []

  return (
    <div className="navigator-tab-content">
      {/* Controls row */}
      <div className="nav-controls">
        <div className="nav-controls-row">
          <select
            className="nav-select"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortOption)}
          >
            {SORT_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <select
            className="nav-select"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            {CATEGORY_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div className="nav-result-count">
          {events.length} {t('navigator.events', 'events')}
          {zoomLevel !== 'cosmic' && <span className="nav-viewport-tag">viewport</span>}
        </div>
      </div>

      {/* Event list */}
      <div className="nav-list">
        {isLoading ? (
          <div className="navigator-loading">{t('common.loading', 'Loading...')}</div>
        ) : events.length === 0 ? (
          <div className="navigator-empty">{t('navigator.noEvents', 'No events found')}</div>
        ) : (
          events.map((event) => {
            const catSlug = typeof event.category === 'string'
              ? event.category
              : event.category?.slug || 'general'
            const catName = typeof event.category === 'object' && event.category?.name
              ? event.category.name
              : catSlug
            const imp = event.importance || 3
            const locationName = event.location?.name
            const isSelected = selectedEventId === event.id

            return (
              <button
                key={event.id}
                className={`nav-event-card ${isSelected ? 'selected' : ''} imp-${Math.min(imp, 5)}`}
                onClick={() => onEventClick(event)}
              >
                {/* Importance bar */}
                <div className="nav-event-imp-bar" style={{ backgroundColor: getImportanceColor(imp) }} />

                <div className="nav-event-body">
                  {/* Top: year + category */}
                  <div className="nav-event-top">
                    <span className="nav-event-year">{formatYear(event.date_start)}</span>
                    <span
                      className="nav-event-cat"
                      style={{
                        backgroundColor: getCategoryColor(catSlug) + '20',
                        color: getCategoryColor(catSlug),
                      }}
                    >
                      {catName}
                    </span>
                  </div>

                  {/* Title */}
                  <div className="nav-event-title">{event.title}</div>

                  {/* Bottom: importance + connections + location */}
                  <div className="nav-event-bottom">
                    <span
                      className="nav-event-dots"
                      title={`Importance: ${imp}/5`}
                      style={{ color: getImportanceColor(imp) }}
                    >
                      {getImportanceDots(imp)}
                    </span>
                    {locationName && (
                      <span className="nav-event-loc" title={locationName}>
                        {locationName}
                      </span>
                    )}
                  </div>
                </div>
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}
