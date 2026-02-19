/**
 * ThreadsTab - Event threads grouped by connecting person
 *
 * Shows "story arcs": sets of events linked by a common person.
 * Each thread can be expanded to show chronological events,
 * and has a [Story] button to open StoryModal.
 */
import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { useDebounce } from '../../hooks/useDebounce'
import { api } from '../../api/client'
import type { ViewportBounds, ZoomLevel } from '../../store/globeStore'

interface ThreadsTabProps {
  currentYear: number
  viewportBounds: ViewportBounds | null
  zoomLevel: ZoomLevel
  onPersonClick: (personId: number) => void
  onOpenStory: (personId: number) => void
}

interface Thread {
  person_id: number
  person_name: string
  person_name_ko?: string
  birth_year?: number
  death_year?: number
  role?: string
  event_count: number
  year_start: number
  year_end: number
  sample_titles: string[]
}

interface ThreadEvent {
  id: number
  title: string
  title_ko?: string
  date_start: number
  date_end?: number
  importance: number
  location_name?: string
}

const TIME_RANGE = 200

function formatYear(year: number | null | undefined): string {
  if (year === null || year === undefined) return '?'
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

function ThreadEventsList({ personId, yearStart, yearEnd }: {
  personId: number
  yearStart?: number
  yearEnd?: number
}) {
  const { data, isLoading } = useQuery({
    queryKey: ['thread-events', personId, yearStart, yearEnd],
    queryFn: () => api.get(`/threads/${personId}/events`, {
      params: { year_start: yearStart, year_end: yearEnd }
    }),
    select: (res) => res.data,
  })

  const events: ThreadEvent[] = data?.events || []

  if (isLoading) return <div className="thread-events-loading">Loading...</div>

  return (
    <div className="thread-events">
      {events.map((event) => (
        <div key={event.id} className="thread-event-item">
          <span className="thread-event-year">{formatYear(event.date_start)}</span>
          <span className="thread-event-title">{event.title}</span>
          {event.location_name && (
            <span className="thread-event-location">{event.location_name}</span>
          )}
        </div>
      ))}
    </div>
  )
}

export function ThreadsTab({
  currentYear,
  viewportBounds,
  zoomLevel,
  onPersonClick,
  onOpenStory,
}: ThreadsTabProps) {
  const { t } = useTranslation()
  const [expandedThread, setExpandedThread] = useState<number | null>(null)
  const debouncedYear = useDebounce(currentYear, 150)
  const debouncedBounds = useDebounce(viewportBounds, 300)

  const queryParams = useMemo(() => {
    const params: Record<string, unknown> = {
      year_start: debouncedYear - TIME_RANGE,
      year_end: debouncedYear + TIME_RANGE,
      limit: 20,
    }

    if (zoomLevel !== 'cosmic' && debouncedBounds) {
      params.lat_min = debouncedBounds.south
      params.lat_max = debouncedBounds.north
      params.lng_min = debouncedBounds.west
      params.lng_max = debouncedBounds.east
    }

    return params
  }, [debouncedYear, zoomLevel, debouncedBounds])

  const { data, isLoading } = useQuery({
    queryKey: ['navigator-threads', queryParams],
    queryFn: () => api.get('/threads', { params: queryParams }),
    select: (res) => res.data,
  })

  const threads: Thread[] = data?.items || []

  const toggleExpand = (personId: number) => {
    setExpandedThread(prev => prev === personId ? null : personId)
  }

  return (
    <div className="navigator-tab-content">
      {/* Controls */}
      <div className="nav-controls">
        <div className="nav-result-count">
          {threads.length} {t('navigator.threads', 'threads')}
          {zoomLevel !== 'cosmic' && <span className="nav-viewport-tag">viewport</span>}
        </div>
      </div>

      {/* List */}
      <div className="nav-list">
        {isLoading ? (
          <div className="navigator-loading">{t('common.loading', 'Loading...')}</div>
        ) : threads.length === 0 ? (
          <div className="navigator-empty">{t('navigator.noThreads', 'No threads found for this era')}</div>
        ) : (
          threads.map((thread) => {
            const isExpanded = expandedThread === thread.person_id
            return (
              <div key={thread.person_id} className={`thread-card ${isExpanded ? 'expanded' : ''}`}>
                <div className="thread-card-header" onClick={() => toggleExpand(thread.person_id)}>
                  <span className="thread-expand-icon">{isExpanded ? '\u25BE' : '\u25B8'}</span>
                  <div className="thread-card-body">
                    <div className="thread-card-top">
                      <span
                        className="thread-person-name"
                        onClick={(e) => { e.stopPropagation(); onPersonClick(thread.person_id) }}
                      >
                        {thread.person_name}
                      </span>
                      <span className="thread-event-count">{thread.event_count} events</span>
                    </div>
                    <div className="thread-card-meta">
                      <span className="thread-year-range">
                        {formatYear(thread.year_start)} &ndash; {formatYear(thread.year_end)}
                      </span>
                      {thread.role && <span className="thread-role">{thread.role}</span>}
                    </div>
                    {!isExpanded && thread.sample_titles.length > 0 && (
                      <div className="thread-preview">
                        {thread.sample_titles.slice(0, 3).join(' \u2192 ')}
                        {thread.sample_titles.length > 3 && ' \u2192 ...'}
                      </div>
                    )}
                  </div>
                  <button
                    className="thread-story-btn"
                    onClick={(e) => { e.stopPropagation(); onOpenStory(thread.person_id) }}
                    title="Open Story"
                  >
                    Story &#9654;
                  </button>
                </div>

                {isExpanded && (
                  <ThreadEventsList
                    personId={thread.person_id}
                    yearStart={queryParams.year_start as number}
                    yearEnd={queryParams.year_end as number}
                  />
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
