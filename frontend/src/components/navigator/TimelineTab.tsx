/**
 * TimelineTab - Dynamic period-based timeline with DB data + AI narratives
 *
 * Fetches 50-year periods from the API, grouped by era.
 * Falls back to hardcoded LAPLACE_ERAS if API is unavailable.
 * Clicking a period opens PeriodDetailPanel with full narrative + events/persons.
 */
import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { timelineApi } from '../../api/client'
import { PeriodDetailPanel } from './PeriodDetailPanel'
import { LAPLACE_ERAS } from '../../data/laplaceTimeline'
import type { PeriodSummary } from '../../types'

interface TimelineTabProps {
  onFlyToLocation?: (lat: number, lng: number) => void
  onSetCurrentYear?: (year: number) => void
  onEventClick?: (eventId: number) => void
  onPersonClick?: (personId: number) => void
}

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

function formatRange(start: number, end: number): string {
  if (start === end) return formatYear(start)
  // Compact: for same-era ranges, abbreviate second year
  const startStr = formatYear(start)
  const endStr = formatYear(end)
  const startBCE = start < 0
  const endBCE = end < 0
  if (startBCE && endBCE) {
    return `${Math.abs(start)}\u2013${Math.abs(end)} BCE`
  }
  if (!startBCE && !endBCE) {
    return `${start}\u2013${end} CE`
  }
  return `${startStr} \u2013 ${endStr}`
}

// Era definitions for grouping
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

export function TimelineTab({
  onFlyToLocation,
  onSetCurrentYear,
  onEventClick,
  onPersonClick,
}: TimelineTabProps) {
  const [expandedEras, setExpandedEras] = useState<Set<string>>(new Set(['classical']))
  const [search, setSearch] = useState('')
  const [selectedPeriod, setSelectedPeriod] = useState<number | null>(null)

  // Fetch periods from API
  const { data: apiPeriods, isLoading, isError } = useQuery({
    queryKey: ['timeline-periods'],
    queryFn: () => timelineApi.listPeriods({ min_score: 70, limit: 500 }),
    select: (res) => (res.data?.items || []) as PeriodSummary[],
    staleTime: 5 * 60 * 1000, // 5 min cache
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

  const handlePeriodClick = (period: PeriodSummary) => {
    if (onSetCurrentYear) {
      const midYear = Math.round((period.period_start + period.period_end) / 2)
      onSetCurrentYear(midYear)
    }
    setSelectedPeriod(period.period_start)
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

  // If period detail is selected, show it
  if (selectedPeriod !== null) {
    return (
      <PeriodDetailPanel
        periodStart={selectedPeriod}
        onClose={() => setSelectedPeriod(null)}
        onEventClick={onEventClick}
        onPersonClick={onPersonClick}
        onFlyToLocation={onFlyToLocation}
        onSetCurrentYear={onSetCurrentYear}
      />
    )
  }

  // Fallback to hardcoded data if API fails
  if (isError || (!isLoading && (!apiPeriods || apiPeriods.length === 0))) {
    return <FallbackTimeline onFlyToLocation={onFlyToLocation} onSetCurrentYear={onSetCurrentYear} />
  }

  return (
    <div className="navigator-tab-content">
      {/* Search */}
      <div className="navigator-search">
        <input
          type="text"
          className="navigator-search-input"
          placeholder="Search timeline..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="nav-list">
          <div className="timeline-loading">Loading timeline data...</div>
        </div>
      )}

      {/* Period list grouped by era */}
      {!isLoading && (
        <div className="nav-list">
          {filteredGroups.map(era => {
            const isExpanded = expandedEras.has(era.id) || search.trim().length > 0

            return (
              <div key={era.id} className="timeline-era">
                {/* Era Header */}
                <button
                  className={`timeline-era-header ${isExpanded ? 'expanded' : ''}`}
                  onClick={() => toggleEra(era.id)}
                >
                  <span className="timeline-era-toggle">
                    {isExpanded ? '\u25BC' : '\u25B6'}
                  </span>
                  <div className="timeline-era-info">
                    <span className="timeline-era-name">
                      {era.name}
                      <span className="timeline-era-name-ko"> {era.name_ko}</span>
                    </span>
                    <span className="timeline-era-range">
                      {formatRange(era.start, era.end)}
                    </span>
                  </div>
                  <span className="timeline-era-count">{era.periods.length}</span>
                </button>

                {/* Period Entries */}
                {isExpanded && (
                  <div className="timeline-era-entries">
                    {era.periods.map(period => (
                      <button
                        key={period.period_start}
                        className={`timeline-entry ${period.has_narrative ? 'has-narrative' : ''}`}
                        onClick={() => handlePeriodClick(period)}
                      >
                        <div className="timeline-entry-line" />
                        <div className="timeline-entry-body">
                          <div className="timeline-entry-date">
                            {formatRange(period.period_start, period.period_end)}
                            {period.has_narrative && (
                              <span className="timeline-narrative-badge">AI</span>
                            )}
                          </div>
                          {period.headline && (
                            <div className="timeline-entry-title">
                              {period.headline}
                            </div>
                          )}
                          <div className="timeline-entry-meta">
                            {period.event_count > 0 && (
                              <span className="timeline-entry-stat">{period.event_count} events</span>
                            )}
                            {period.person_count > 0 && (
                              <span className="timeline-entry-stat">{period.person_count} figures</span>
                            )}
                            {(period.region_count ?? 0) > 0 && (
                              <span className="timeline-entry-stat">{period.region_count} regions</span>
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
        </div>
      )}
    </div>
  )
}

/**
 * Fallback to hardcoded LAPLACE_ERAS when API is unavailable
 */
function FallbackTimeline({
  onFlyToLocation,
  onSetCurrentYear,
}: {
  onFlyToLocation?: (lat: number, lng: number) => void
  onSetCurrentYear?: (year: number) => void
}) {
  const [expandedEras, setExpandedEras] = useState<Set<string>>(new Set(['ancient']))

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

  return (
    <div className="navigator-tab-content">
      <div className="nav-list">
        {LAPLACE_ERAS.map(era => {
          const isExpanded = expandedEras.has(era.id)
          return (
            <div key={era.id} className="timeline-era">
              <button
                className={`timeline-era-header ${isExpanded ? 'expanded' : ''}`}
                onClick={() => toggleEra(era.id)}
              >
                <span className="timeline-era-toggle">
                  {isExpanded ? '\u25BC' : '\u25B6'}
                </span>
                <span className="timeline-era-diamond">{'\u25C6'}</span>
                <div className="timeline-era-info">
                  <span className="timeline-era-name">
                    {era.name}
                    {era.name_ko && <span className="timeline-era-name-ko"> {era.name_ko}</span>}
                  </span>
                  <span className="timeline-era-range">
                    {formatRange(era.start_year, era.end_year)}
                  </span>
                </div>
                <span className="timeline-era-count">{era.entries.length}</span>
              </button>
              {isExpanded && (
                <div className="timeline-era-entries">
                  {era.entries.map(entry => (
                    <button
                      key={entry.id}
                      className="timeline-entry"
                      onClick={() => {
                        if (entry.latitude != null && entry.longitude != null && onFlyToLocation) {
                          onFlyToLocation(entry.latitude, entry.longitude)
                        }
                        if (onSetCurrentYear) {
                          onSetCurrentYear(Math.round((entry.dateRange.start + entry.dateRange.end) / 2))
                        }
                      }}
                    >
                      <div className="timeline-entry-line" />
                      <div className="timeline-entry-body">
                        <div className="timeline-entry-title">{entry.title}</div>
                        <div className="timeline-entry-desc">{entry.description}</div>
                        <div className="timeline-entry-meta">
                          <span className="timeline-entry-range">
                            {formatRange(entry.dateRange.start, entry.dateRange.end)}
                          </span>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
