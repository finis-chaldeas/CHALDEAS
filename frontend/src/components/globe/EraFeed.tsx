import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { timelineApi } from '../../api/client'
import { useTimelineStore } from '../../store/timelineStore'
import { useGlobeStore } from '../../store/globeStore'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import type { PeriodEvent, PeriodPerson } from '../../types'

type EraTab = 'events' | 'figures'
type SortMode = 'importance' | 'time'

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

interface EraFeedProps {
  onEventClick: (eventId: number) => void
  onPersonClick: (personId: number) => void
}

export default function EraFeed({ onEventClick, onPersonClick }: EraFeedProps) {
  const currentYear = useTimelineStore((s) => s.currentYear)
  const cameraPosition = useGlobeStore((s) => s.cameraPosition)
  const viewMode = useGlobeStore((s) => s.viewMode)
  const rayshiftSteps = useGlobeStore((s) => s.rayshiftSteps)
  const { preferredLanguage } = useSettingsStore()

  const [collapsed, setCollapsed] = useState(true)
  const [activeTab, setActiveTab] = useState<EraTab>('events')
  const [sortMode, setSortMode] = useState<SortMode>('importance')
  const [viewportOnly, setViewportOnly] = useState(false)

  // Compute 50-year period
  const periodStart = Math.floor(currentYear / 50) * 50

  const { data: events, isLoading: eventsLoading } = useQuery({
    queryKey: ['era-feed-events', periodStart],
    queryFn: () => timelineApi.getPeriodEvents(periodStart, { limit: 30 }),
    select: (res) => {
      const data = res.data
      return (data?.items ?? data) as PeriodEvent[]
    },
    enabled: !collapsed && viewMode === 'globe',
    staleTime: 60000,
  })

  const { data: persons, isLoading: personsLoading } = useQuery({
    queryKey: ['era-feed-persons', periodStart],
    queryFn: () => timelineApi.getPeriodPersons(periodStart, { limit: 20 }),
    select: (res) => {
      const data = res.data
      return (data?.items ?? data) as PeriodPerson[]
    },
    enabled: !collapsed && activeTab === 'figures' && viewMode === 'globe',
    staleTime: 60000,
  })

  // Viewport filtering for events
  const filteredEvents = useMemo(() => {
    if (!events) return []
    let items = [...events]

    if (viewportOnly && cameraPosition) {
      const latRange = (cameraPosition.altitude || 2) * 30
      const lngRange = latRange * 1.5
      const bounds = {
        north: cameraPosition.lat + latRange / 2,
        south: cameraPosition.lat - latRange / 2,
        east: cameraPosition.lng + lngRange / 2,
        west: cameraPosition.lng - lngRange / 2,
      }
      items = items.filter(e => {
        if (!e.latitude || !e.longitude) return false
        return e.latitude >= bounds.south && e.latitude <= bounds.north
          && e.longitude >= bounds.west && e.longitude <= bounds.east
      })
    }

    if (sortMode === 'importance') {
      items.sort((a, b) => (b.importance_score ?? 0) - (a.importance_score ?? 0))
    } else {
      items.sort((a, b) => (a.date_start ?? 0) - (b.date_start ?? 0))
    }

    return items
  }, [events, viewportOnly, cameraPosition, sortMode])

  // Hide in map mode or during Rayshift
  if (viewMode !== 'globe') return null
  if (rayshiftSteps && rayshiftSteps.length > 0) return null

  const periodEnd = periodStart + 50

  // Collapsed: show tab on left edge
  if (collapsed) {
    return (
      <button onClick={() => setCollapsed(false)} className="era-feed-tab">
        <span className="era-feed-tab-year">{formatYear(periodStart)}</span>
        <span className="era-feed-tab-label">Era</span>
      </button>
    )
  }

  return (
    <div className="era-feed">
      {/* Header */}
      <div className="era-feed-header">
        <div className="era-feed-title-row">
          <div>
            <div className="era-feed-period">{formatYear(periodStart)} &ndash; {formatYear(periodEnd)}</div>
          </div>
          <button onClick={() => setCollapsed(true)} className="era-feed-close">{'\u2715'}</button>
        </div>

        {/* Tabs */}
        <div className="era-feed-tabs">
          <button onClick={() => setActiveTab('events')}
            className={`era-feed-tab-btn ${activeTab === 'events' ? 'active' : ''}`}>
            Events
          </button>
          <button onClick={() => setActiveTab('figures')}
            className={`era-feed-tab-btn ${activeTab === 'figures' ? 'active' : ''}`}>
            Figures
          </button>
        </div>
      </div>

      {/* Controls */}
      {activeTab === 'events' && (
        <div className="era-feed-controls">
          <div className="era-feed-sort">
            <button onClick={() => setSortMode('importance')}
              className={`era-feed-sort-btn ${sortMode === 'importance' ? 'active' : ''}`}>
              Importance
            </button>
            <button onClick={() => setSortMode('time')}
              className={`era-feed-sort-btn ${sortMode === 'time' ? 'active' : ''}`}>
              Time
            </button>
          </div>
          <button onClick={() => setViewportOnly(!viewportOnly)}
            className={`era-feed-viewport-btn ${viewportOnly ? 'active' : ''}`}>
            {viewportOnly ? 'In View' : 'All'}
          </button>
        </div>
      )}

      {/* List */}
      <div className="era-feed-list">
        {activeTab === 'events' && (
          eventsLoading ? (
            <div className="era-feed-loading">Loading events...</div>
          ) : filteredEvents.length === 0 ? (
            <div className="era-feed-empty">
              {viewportOnly ? 'No events in current view' : 'No events in this period'}
            </div>
          ) : (
            filteredEvents.map((event) => (
              <button key={event.id} onClick={() => onEventClick(event.id)}
                className="era-feed-item">
                <div className="era-feed-item-title">
                  {getLocalizedText(event as unknown as Record<string, unknown>, 'title', preferredLanguage) || event.title}
                </div>
                <div className="era-feed-item-meta">
                  {event.date_start != null && (
                    <span className="era-feed-item-year">{formatYear(event.date_start)}</span>
                  )}
                  {event.location_name && (
                    <span className="era-feed-item-location">{event.location_name}</span>
                  )}
                  {event.importance_score != null && event.importance_score >= 4 && (
                    <span className="era-feed-item-star">{'\u2605'}</span>
                  )}
                </div>
              </button>
            ))
          )
        )}

        {activeTab === 'figures' && (
          personsLoading ? (
            <div className="era-feed-loading">Loading figures...</div>
          ) : !persons || persons.length === 0 ? (
            <div className="era-feed-empty">No figures in this period</div>
          ) : (
            persons.map((person) => (
              <button key={person.id} onClick={() => onPersonClick(person.id)}
                className="era-feed-item">
                <div className="era-feed-item-title">
                  {getLocalizedText(person as unknown as Record<string, unknown>, 'name', preferredLanguage) || person.name}
                </div>
                <div className="era-feed-item-meta">
                  {person.birth_year != null && (
                    <span className="era-feed-item-year">
                      {formatYear(person.birth_year)}
                      {person.death_year != null && ` \u2013 ${formatYear(person.death_year)}`}
                    </span>
                  )}
                  {person.role && person.role !== 'occupation' && person.role !== 'None' && (
                    <span className="era-feed-item-role">{person.role}</span>
                  )}
                </div>
              </button>
            ))
          )
        )}
      </div>
    </div>
  )
}
