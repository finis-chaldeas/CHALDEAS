/**
 * TimelineModal - Fullscreen timeline explorer with 3-level drilldown
 *
 * Level 1: Era Overview (click era name → right panel shows top events/persons)
 * Level 2: Sub-period Grid (click "View Periods" → grid of 50-year periods)
 * Level 3: Period Detail (click period card → PeriodDetailPanel with sub-events)
 */
import { useState, useMemo, useEffect, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { timelineApi, api } from '../../api/client'
import { PeriodDetailPanel } from './PeriodDetailPanel'
import { LAPLACE_ERAS } from '../../data/laplaceTimeline'
import type { PeriodSummary } from '../../types'
import './TimelineModal.css'

interface TimelineModalProps {
  isOpen: boolean
  onClose: () => void
  onEventClick?: (eventId: number) => void
  onPersonClick?: (personId: number) => void
  onFlyToLocation?: (lat: number, lng: number) => void
  onSetCurrentYear?: (year: number) => void
}

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

function formatRange(start: number, end: number): string {
  if (start === end) return formatYear(start)
  const startBCE = start < 0
  const endBCE = end < 0
  if (startBCE && endBCE) {
    return `${Math.abs(start)}\u2013${Math.abs(end)} BCE`
  }
  if (!startBCE && !endBCE) {
    return `${start}\u2013${end} CE`
  }
  return `${formatYear(start)} \u2013 ${formatYear(end)}`
}

const ERA_DEFS = [
  { id: 'ancient', name: 'Ancient World', name_ko: '\uACE0\uB300', start: -3500, end: -500 },
  { id: 'classical', name: 'Classical Era', name_ko: '\uACE0\uC804', start: -500, end: 500 },
  { id: 'medieval', name: 'Medieval Period', name_ko: '\uC911\uC138', start: 500, end: 1500 },
  { id: 'early-modern', name: 'Early Modern', name_ko: '\uADFC\uC138', start: 1500, end: 1800 },
  { id: 'modern', name: 'Modern Era', name_ko: '\uADFC\uB300', start: 1800, end: 1945 },
  { id: 'contemporary', name: 'Contemporary', name_ko: '\uD604\uB300', start: 1945, end: 2030 },
]

interface EraGroup {
  id: string
  name: string
  name_ko: string
  start: number
  end: number
  periods: PeriodSummary[]
}

type RightPanelView =
  | { type: 'placeholder' }
  | { type: 'era-overview'; era: EraGroup }
  | { type: 'period-grid'; era: EraGroup }
  | { type: 'period-detail'; periodStart: number; era?: EraGroup }

function groupByEra(periods: PeriodSummary[]): EraGroup[] {
  const groups: EraGroup[] = ERA_DEFS.map(era => ({
    ...era,
    periods: [],
  }))

  for (const period of periods) {
    const era = groups.find(g =>
      period.period_start >= g.start && period.period_start < g.end
    )
    if (era) {
      era.periods.push(period)
    }
  }

  return groups.filter(g => g.periods.length > 0)
}

function getImportanceStars(importance: number): string {
  const filled = Math.min(Math.round(importance), 5)
  const empty = 5 - filled
  return '\u2605'.repeat(filled) + '\u2606'.repeat(empty)
}

export function TimelineModal({
  isOpen,
  onClose,
  onEventClick,
  onPersonClick,
  onFlyToLocation,
  onSetCurrentYear,
}: TimelineModalProps) {
  const [expandedEras, setExpandedEras] = useState<Set<string>>(new Set(['classical']))
  const [search, setSearch] = useState('')
  const [rightPanel, setRightPanel] = useState<RightPanelView>({ type: 'placeholder' })

  // Close on Escape key
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose()
  }, [onClose])

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [isOpen, handleKeyDown])

  // Fetch periods from API
  const { data: apiPeriods, isLoading, isError } = useQuery({
    queryKey: ['timeline-periods'],
    queryFn: () => timelineApi.listPeriods({ min_score: 70, limit: 500 }),
    select: (res) => (res.data?.items || []) as PeriodSummary[],
    staleTime: 5 * 60 * 1000,
    enabled: isOpen,
  })

  const toggleEra = (eraId: string) => {
    setExpandedEras(prev => {
      const next = new Set(prev)
      if (next.has(eraId)) {
        next.delete(eraId)
      } else {
        next.add(eraId)
      }
      return next
    })
  }

  const handleEraClick = (era: EraGroup) => {
    // Toggle expand and show era overview
    toggleEra(era.id)
    setRightPanel({ type: 'era-overview', era })
  }

  const handlePeriodClick = (period: PeriodSummary, era?: EraGroup) => {
    if (onSetCurrentYear) {
      const midYear = Math.round((period.period_start + period.period_end) / 2)
      onSetCurrentYear(midYear)
    }
    setRightPanel({ type: 'period-detail', periodStart: period.period_start, era })
  }

  const handleEventClick = (eventId: number) => {
    onEventClick?.(eventId)
    onClose()
  }

  const handlePersonClick = (personId: number) => {
    onPersonClick?.(personId)
    onClose()
  }

  // Group periods by era
  const eraGroups = useMemo(() => {
    if (!apiPeriods) return []
    return groupByEra(apiPeriods)
  }, [apiPeriods])

  // Filter by search
  const filteredGroups = useMemo(() => {
    if (!search.trim()) return eraGroups
    const q = search.toLowerCase()
    return eraGroups
      .map(era => ({
        ...era,
        periods: era.periods.filter(p =>
          (p.headline && p.headline.toLowerCase().includes(q)) ||
          (p.headline_ko && p.headline_ko.includes(q)) ||
          p.date_display?.toLowerCase().includes(q)
        ),
      }))
      .filter(era => era.periods.length > 0)
  }, [eraGroups, search])

  // Use fallback data
  const useFallback = isError || (!isLoading && (!apiPeriods || apiPeriods.length === 0))

  if (!isOpen) return null

  return (
    <div className="timeline-modal-overlay" onClick={onClose}>
      <div className="timeline-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="timeline-modal-header">
          <button className="timeline-modal-close" onClick={onClose}>
            {'\u2715'}
          </button>
          <h2 className="timeline-modal-title">Timeline Explorer</h2>
          <input
            type="text"
            className="timeline-modal-search"
            placeholder="Search periods..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* Body: Left nav + Right content */}
        <div className="timeline-modal-body">
          {/* Left: Era navigation */}
          <aside className="timeline-modal-nav">
            {isLoading && (
              <div className="timeline-modal-loading">Loading timeline...</div>
            )}

            {!isLoading && !useFallback && filteredGroups.map(era => {
              const isExpanded = expandedEras.has(era.id) || search.trim().length > 0
              return (
                <div key={era.id} className="tm-era">
                  <button
                    className={`tm-era-header ${isExpanded ? 'expanded' : ''}`}
                    onClick={() => handleEraClick(era)}
                  >
                    <span className="tm-era-toggle">
                      {isExpanded ? '\u25BC' : '\u25B6'}
                    </span>
                    <div className="tm-era-info">
                      <span className="tm-era-name">
                        {era.name}
                        <span className="tm-era-name-ko"> {era.name_ko}</span>
                      </span>
                      <span className="tm-era-range">
                        {formatRange(era.start, era.end)}
                      </span>
                    </div>
                    <span className="tm-era-count">{era.periods.length}</span>
                  </button>

                  {isExpanded && (
                    <div className="tm-era-entries">
                      {era.periods.map(period => (
                        <button
                          key={period.period_start}
                          className={`tm-entry ${
                            rightPanel.type === 'period-detail' &&
                            rightPanel.periodStart === period.period_start
                              ? 'active'
                              : ''
                          } ${period.has_narrative ? 'has-narrative' : ''}`}
                          onClick={() => handlePeriodClick(period, era)}
                        >
                          <div className="tm-entry-line" />
                          <div className="tm-entry-body">
                            <div className="tm-entry-date">
                              {formatRange(period.period_start, period.period_end)}
                              {period.has_narrative && (
                                <span className="tm-narrative-badge">AI</span>
                              )}
                            </div>
                            {period.headline && (
                              <div className="tm-entry-title">{period.headline}</div>
                            )}
                            <div className="tm-entry-meta">
                              {period.event_count > 0 && (
                                <span>{period.event_count} events</span>
                              )}
                              {period.person_count > 0 && (
                                <span>{period.person_count} figures</span>
                              )}
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}

            {/* Fallback: hardcoded eras */}
            {!isLoading && useFallback && LAPLACE_ERAS.map(era => {
              const isExpanded = expandedEras.has(era.id)
              return (
                <div key={era.id} className="tm-era">
                  <button
                    className={`tm-era-header ${isExpanded ? 'expanded' : ''}`}
                    onClick={() => toggleEra(era.id)}
                  >
                    <span className="tm-era-toggle">
                      {isExpanded ? '\u25BC' : '\u25B6'}
                    </span>
                    <div className="tm-era-info">
                      <span className="tm-era-name">
                        {era.name}
                        {era.name_ko && <span className="tm-era-name-ko"> {era.name_ko}</span>}
                      </span>
                      <span className="tm-era-range">
                        {formatRange(era.start_year, era.end_year)}
                      </span>
                    </div>
                    <span className="tm-era-count">{era.entries.length}</span>
                  </button>
                  {isExpanded && (
                    <div className="tm-era-entries">
                      {era.entries.map(entry => (
                        <button
                          key={entry.id}
                          className="tm-entry"
                          onClick={() => {
                            if (entry.latitude != null && entry.longitude != null && onFlyToLocation) {
                              onFlyToLocation(entry.latitude, entry.longitude)
                            }
                            if (onSetCurrentYear) {
                              onSetCurrentYear(Math.round((entry.dateRange.start + entry.dateRange.end) / 2))
                            }
                          }}
                        >
                          <div className="tm-entry-line" />
                          <div className="tm-entry-body">
                            <div className="tm-entry-title">{entry.title}</div>
                            <div className="tm-entry-desc">{entry.description}</div>
                            <div className="tm-entry-meta">
                              <span>{formatRange(entry.dateRange.start, entry.dateRange.end)}</span>
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </aside>

          {/* Right: Content panel */}
          <main className="timeline-modal-content">
            {rightPanel.type === 'placeholder' && (
              <div className="timeline-modal-placeholder">
                <div className="placeholder-icon">{'\u231B'}</div>
                <div className="placeholder-text">Select an era or period to explore</div>
                <div className="placeholder-hint">
                  Click an era name to see its overview, or expand and click a period for details.
                </div>
              </div>
            )}

            {rightPanel.type === 'era-overview' && (
              <EraOverview
                era={rightPanel.era}
                onEventClick={handleEventClick}
                onPersonClick={handlePersonClick}
                onViewPeriods={() => setRightPanel({ type: 'period-grid', era: rightPanel.era })}
              />
            )}

            {rightPanel.type === 'period-grid' && (
              <PeriodGrid
                era={rightPanel.era}
                onBack={() => setRightPanel({ type: 'era-overview', era: rightPanel.era })}
                onSelectPeriod={(p) => handlePeriodClick(p, rightPanel.era)}
              />
            )}

            {rightPanel.type === 'period-detail' && (
              <PeriodDetailPanel
                periodStart={rightPanel.periodStart}
                onClose={() => {
                  if (rightPanel.era) {
                    setRightPanel({ type: 'period-grid', era: rightPanel.era })
                  } else {
                    setRightPanel({ type: 'placeholder' })
                  }
                }}
                onEventClick={handleEventClick}
                onPersonClick={handlePersonClick}
                onFlyToLocation={onFlyToLocation}
                onSetCurrentYear={onSetCurrentYear}
                layout="wide"
              />
            )}
          </main>
        </div>
      </div>
    </div>
  )
}

/** Level 1: Era Overview - Top events and persons for a whole era */
function EraOverview({
  era,
  onEventClick,
  onPersonClick,
  onViewPeriods,
}: {
  era: EraGroup
  onEventClick: (eventId: number) => void
  onPersonClick: (personId: number) => void
  onViewPeriods: () => void
}) {
  // Fetch top events for this era
  const { data: topEvents } = useQuery({
    queryKey: ['era-top-events', era.id, era.start, era.end],
    queryFn: () => api.get('/events', {
      params: {
        year_start: era.start,
        year_end: era.end,
        sort_by: 'importance',
        limit: 10,
      }
    }),
    select: (res) => res.data?.items || res.data || [],
    staleTime: 5 * 60 * 1000,
  })

  // Fetch top persons for this era
  const { data: topPersons } = useQuery({
    queryKey: ['era-top-persons', era.id, era.start, era.end],
    queryFn: () => api.get('/feed', {
      params: {
        year_start: era.start,
        year_end: era.end,
        limit: 10,
      }
    }),
    select: (res) => {
      const items = res.data?.items || []
      return items.filter((i: { type: string }) => i.type === 'person').slice(0, 8)
    },
    staleTime: 5 * 60 * 1000,
  })

  const events = topEvents || []
  const persons = topPersons || []

  return (
    <div className="era-overview-panel">
      <div className="era-overview-header">
        <div className="era-overview-name-ko">{era.name_ko}</div>
        <h2 className="era-overview-title">{era.name}</h2>
        <div className="era-overview-range">{formatRange(era.start, era.end)}</div>
      </div>

      {/* Defining Events */}
      {events.length > 0 && (
        <div className="era-overview-section">
          <h4 className="era-section-title">{'\u2605'} DEFINING EVENTS</h4>
          <div className="era-events-list">
            {events.map((event: { id: number; title: string; date_start?: number; importance?: number }) => (
              <button
                key={event.id}
                className="era-event-item"
                onClick={() => onEventClick(event.id)}
              >
                <span className="era-event-stars" style={{ color: (event.importance || 3) >= 5 ? '#ffd700' : '#8ba4b4' }}>
                  {getImportanceStars(event.importance || 3)}
                </span>
                <span className="era-event-title">{event.title}</span>
                {event.date_start != null && (
                  <span className="era-event-year">{formatYear(event.date_start)}</span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Key Figures */}
      {persons.length > 0 && (
        <div className="era-overview-section">
          <h4 className="era-section-title">{'\u2605'} KEY FIGURES</h4>
          <div className="era-persons-chips">
            {persons.map((person: { id: number; name?: string; title?: string; role?: string }) => (
              <button
                key={person.id}
                className="era-person-chip"
                onClick={() => onPersonClick(person.id)}
              >
                <span className="era-person-name">{person.name || person.title}</span>
                {person.role && <span className="era-person-role">{person.role}</span>}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* View periods button */}
      <div className="era-overview-actions">
        <button className="era-view-periods-btn" onClick={onViewPeriods}>
          {'\uD83D\uDCC5'} View {era.periods.length} periods in detail {'\u2192'}
        </button>
      </div>
    </div>
  )
}

/** Level 2: Period Grid - Grid of 50-year period cards */
function PeriodGrid({
  era,
  onBack,
  onSelectPeriod,
}: {
  era: EraGroup
  onBack: () => void
  onSelectPeriod: (period: PeriodSummary) => void
}) {
  return (
    <div className="period-grid-panel">
      <div className="period-grid-header">
        <button className="period-grid-back" onClick={onBack}>
          {'\u2190'} {era.name}
        </button>
        <div className="period-grid-subtitle">
          {era.periods.length} periods | {formatRange(era.start, era.end)}
        </div>
      </div>

      <div className="period-grid">
        {era.periods.map(period => (
          <button
            key={period.period_start}
            className={`period-grid-card ${period.has_narrative ? 'has-narrative' : ''}`}
            onClick={() => onSelectPeriod(period)}
          >
            <div className="period-grid-card-range">
              {formatRange(period.period_start, period.period_end)}
            </div>
            <div className="period-grid-card-counts">
              {period.event_count > 0 && <span>{period.event_count} events</span>}
              {period.person_count > 0 && <span>{period.person_count} figures</span>}
            </div>
            {period.headline && (
              <div className="period-grid-card-headline">{period.headline}</div>
            )}
            {period.has_narrative && (
              <span className="period-grid-narrative-badge">AI</span>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}
