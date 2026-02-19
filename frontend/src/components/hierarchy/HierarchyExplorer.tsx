/**
 * HierarchyExplorer - Fullscreen era drill-down browser
 *
 * Navigation: Eras -> Events (sorted by importance)
 * If aggregate events exist, shows them with drill-down to children.
 * Otherwise, shows top events for the era directly.
 */
import { useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import type { Event } from '../../types'
import './HierarchyExplorer.css'

interface HierarchyExplorerProps {
  isOpen: boolean
  onClose: () => void
  onEventClick: (event: Event) => void
  onFlyToLocation?: (lat: number, lng: number) => void
  onSetCurrentYear?: (year: number) => void
  /** If provided, opens directly to a specific event's children */
  initialEventId?: number
}

interface EraDefinition {
  id: number
  name: string
  name_ko: string
  start_year: number
  end_year: number
}

interface EventItem {
  id: number
  title: string
  title_ko?: string
  date_start: number
  date_end?: number
  importance: number
  hierarchy_level?: number
  aggregate_type?: string
  is_aggregate?: boolean
  child_count?: number
  latitude?: number
  longitude?: number
  location?: { id: number; name: string; latitude?: number | null; longitude?: number | null } | null
  category?: { slug: string; name: string } | null
}

type NavigationLevel = 'eras' | 'events' | 'children'

interface BreadcrumbItem {
  level: NavigationLevel
  label: string
  eraId?: number
  eventId?: number
}

const DEFAULT_ERAS: EraDefinition[] = [
  { id: 1, name: 'Ancient', name_ko: '\uace0\ub300', start_year: -3000, end_year: 500 },
  { id: 2, name: 'Medieval', name_ko: '\uc911\uc138', start_year: 500, end_year: 1500 },
  { id: 3, name: 'Renaissance', name_ko: '\ub974\ub124\uc0c1\uc2a4', start_year: 1400, end_year: 1600 },
  { id: 4, name: 'Early Modern', name_ko: '\uadfc\uc138', start_year: 1500, end_year: 1800 },
  { id: 5, name: 'Modern', name_ko: '\uadfc\ub300', start_year: 1800, end_year: 1945 },
  { id: 6, name: 'Contemporary', name_ko: '\ud604\ub300', start_year: 1945, end_year: 2025 },
]

const AGGREGATE_TYPE_ICONS: Record<string, string> = {
  war: '\u2694\ufe0f',
  movement: '\ud83c\udf0a',
  dynasty: '\ud83d\udc51',
  expedition: '\ud83d\udea2',
  revolution: '\ud83d\udd25',
  crisis: '\u26a0\ufe0f',
  artistic_period: '\ud83c\udfa8',
  philosophical_school: '\ud83d\udcad',
  scientific_era: '\ud83d\udd2c',
  religious: '\u271d\ufe0f',
}

const ERA_ICONS: Record<string, string> = {
  Ancient: '\ud83c\udfdb\ufe0f',
  Medieval: '\ud83c\udff0',
  Renaissance: '\ud83c\udfa8',
  'Early Modern': '\ud83d\uddfa\ufe0f',
  Modern: '\ud83c\udfed',
  Contemporary: '\ud83c\udf10',
}

function formatYear(year: number): string {
  const absYear = Math.abs(year)
  return year < 0 ? `${absYear} BCE` : `${absYear} CE`
}

function formatDateRange(start: number, end?: number): string {
  if (!end || end === start) return formatYear(start)
  return `${formatYear(start)} \u2013 ${formatYear(end)}`
}

export function HierarchyExplorer({
  isOpen,
  onClose,
  onEventClick,
  onFlyToLocation,
  onSetCurrentYear,
  initialEventId,
}: HierarchyExplorerProps) {
  const [currentLevel, setCurrentLevel] = useState<NavigationLevel>(
    initialEventId ? 'children' : 'eras'
  )
  const [selectedEra, setSelectedEra] = useState<EraDefinition | null>(null)
  const [selectedParent, setSelectedParent] = useState<EventItem | null>(null)
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbItem[]>([
    { level: 'eras', label: 'All Eras' }
  ])

  // ── Level 2: Era events ──
  // First try aggregates; if none, fall back to regular events
  const { data: aggregatesData, isLoading: aggregatesLoading } = useQuery({
    queryKey: ['he-aggregates', selectedEra?.start_year, selectedEra?.end_year],
    queryFn: () => api.get('/events/aggregates', {
      params: {
        year_start: selectedEra!.start_year,
        year_end: selectedEra!.end_year,
        limit: 200,
      }
    }),
    enabled: currentLevel === 'events' && !!selectedEra,
    select: (res) => res.data,
  })

  const hasAggregates = (aggregatesData?.total ?? 0) > 0

  // Fallback: fetch regular events sorted by importance when no aggregates
  const { data: eraEventsData, isLoading: eraEventsLoading } = useQuery({
    queryKey: ['he-era-events', selectedEra?.start_year, selectedEra?.end_year],
    queryFn: () => api.get('/events', {
      params: {
        year_start: selectedEra!.start_year,
        year_end: selectedEra!.end_year,
        sort_by: 'importance',
        limit: 100,
      }
    }),
    enabled: currentLevel === 'events' && !!selectedEra && !aggregatesLoading && !hasAggregates,
    select: (res) => res.data,
  })

  // ── Level 3: Children of a specific event ──
  const childrenEventId = selectedParent?.id ?? initialEventId
  const { data: childrenData, isLoading: childrenLoading } = useQuery({
    queryKey: ['he-children', childrenEventId],
    queryFn: () => api.get(`/events/${childrenEventId}/children`, {
      params: { limit: 200 }
    }),
    enabled: currentLevel === 'children' && !!childrenEventId,
    select: (res) => res.data,
  })

  // ── Era card counts ──
  const { data: eraCountsData } = useQuery({
    queryKey: ['he-era-counts'],
    queryFn: async () => {
      const counts: Record<number, number> = {}
      // Single batch: just count events per era range
      for (const era of DEFAULT_ERAS) {
        try {
          const res = await api.get('/events', {
            params: {
              year_start: era.start_year,
              year_end: era.end_year,
              limit: 1,
            }
          })
          counts[era.id] = res.data?.total ?? 0
        } catch {
          counts[era.id] = 0
        }
      }
      return counts
    },
    enabled: isOpen && currentLevel === 'eras',
    staleTime: 5 * 60 * 1000,
  })

  // ── Navigation handlers ──
  const handleEraClick = useCallback((era: EraDefinition) => {
    setSelectedEra(era)
    setSelectedParent(null)
    setCurrentLevel('events')
    setBreadcrumbs([
      { level: 'eras', label: 'All Eras' },
      { level: 'events', label: era.name, eraId: era.id },
    ])
  }, [])

  const handleEventItemClick = useCallback((ev: EventItem) => {
    // If this event is an aggregate with children, drill down
    if (ev.is_aggregate || (ev.child_count && ev.child_count > 0)) {
      setSelectedParent(ev)
      setCurrentLevel('children')
      setBreadcrumbs(prev => [
        ...prev.slice(0, 2),
        { level: 'children', label: ev.title, eventId: ev.id },
      ])
      return
    }
    // Otherwise, select it and fly to globe
    selectAndFly(ev)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const selectAndFly = useCallback((ev: EventItem) => {
    const lat = ev.latitude ?? ev.location?.latitude
    const lng = ev.longitude ?? ev.location?.longitude
    if (lat != null && lng != null && onFlyToLocation) {
      onFlyToLocation(lat, lng)
    }
    if (onSetCurrentYear) {
      onSetCurrentYear(ev.date_start)
    }
    onEventClick(ev as unknown as Event)
  }, [onEventClick, onFlyToLocation, onSetCurrentYear])

  const handleBreadcrumbClick = useCallback((crumb: BreadcrumbItem) => {
    if (crumb.level === 'eras') {
      setCurrentLevel('eras')
      setSelectedEra(null)
      setSelectedParent(null)
      setBreadcrumbs([{ level: 'eras', label: 'All Eras' }])
    } else if (crumb.level === 'events' && crumb.eraId) {
      const era = DEFAULT_ERAS.find(e => e.id === crumb.eraId)
      if (era) {
        setSelectedEra(era)
        setSelectedParent(null)
        setCurrentLevel('events')
        setBreadcrumbs([
          { level: 'eras', label: 'All Eras' },
          { level: 'events', label: era.name, eraId: era.id },
        ])
      }
    }
  }, [])

  const handleOverlayClick = useCallback((e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose()
  }, [onClose])

  if (!isOpen) return null

  // Decide which list to show on level 2
  const level2Loading = aggregatesLoading || (!hasAggregates && eraEventsLoading)
  const level2Items: EventItem[] = hasAggregates
    ? (aggregatesData?.items ?? [])
    : (eraEventsData?.items ?? [])
  const level2Total = hasAggregates
    ? (aggregatesData?.total ?? 0)
    : (eraEventsData?.total ?? 0)

  const childrenList: EventItem[] = childrenData?.items ?? []

  return (
    <div className="hierarchy-explorer-overlay" onClick={handleOverlayClick}>
      <div className="hierarchy-explorer" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <header className="he-header">
          <div className="he-header-left">
            <span className="he-title">EXPLORE ERAS</span>
          </div>
          <button className="he-close" onClick={onClose}>{'\u2715'}</button>
        </header>

        {/* Breadcrumbs */}
        <nav className="he-breadcrumbs">
          {breadcrumbs.map((crumb, i) => (
            <span key={i} className="he-breadcrumb-item">
              {i > 0 && <span className="he-breadcrumb-sep">{'\u203a'}</span>}
              <button
                className={`he-breadcrumb-btn ${i === breadcrumbs.length - 1 ? 'active' : ''}`}
                onClick={() => handleBreadcrumbClick(crumb)}
                disabled={i === breadcrumbs.length - 1}
              >
                {crumb.label}
              </button>
            </span>
          ))}
        </nav>

        {/* Content */}
        <div className="he-content">
          {/* Level 1: Era Cards */}
          {currentLevel === 'eras' && (
            <div className="he-era-grid">
              {DEFAULT_ERAS.map((era) => (
                <button
                  key={era.id}
                  className="he-era-card"
                  onClick={() => handleEraClick(era)}
                >
                  <span className="he-era-icon">{ERA_ICONS[era.name] || '\ud83d\udcc5'}</span>
                  <span className="he-era-name">{era.name}</span>
                  <span className="he-era-range">
                    {formatDateRange(era.start_year, era.end_year)}
                  </span>
                  <span className="he-era-count">
                    {eraCountsData?.[era.id] !== undefined
                      ? `${eraCountsData[era.id].toLocaleString()} events`
                      : '\u2026'}
                  </span>
                </button>
              ))}
            </div>
          )}

          {/* Level 2: Events List (aggregates or regular events) */}
          {currentLevel === 'events' && (
            <div className="he-events-list">
              {level2Loading && (
                <div className="he-loading">Loading events...</div>
              )}
              {!level2Loading && level2Items.length === 0 && (
                <div className="he-empty">No events found for this era.</div>
              )}
              {!level2Loading && level2Items.map((ev) => {
                const icon = ev.aggregate_type
                  ? (AGGREGATE_TYPE_ICONS[ev.aggregate_type] || '\ud83d\udcc5')
                  : '\ud83d\udcc5'
                const isAggregate = ev.is_aggregate || (ev.child_count && ev.child_count > 0)

                return (
                  <button
                    key={ev.id}
                    className={`he-event-item ${isAggregate ? 'aggregate' : ''}`}
                    onClick={() => handleEventItemClick(ev)}
                  >
                    <span className="he-event-icon">{icon}</span>
                    <div className="he-event-info">
                      <span className="he-event-title">{ev.title}</span>
                      <span className="he-event-dates">
                        {formatDateRange(ev.date_start, ev.date_end ?? undefined)}
                        {ev.location && <> &middot; {ev.location.name}</>}
                      </span>
                    </div>
                    {ev.aggregate_type && (
                      <span className="he-event-type">{ev.aggregate_type}</span>
                    )}
                    {isAggregate ? (
                      <span className="he-event-arrow">{'\u203a'}</span>
                    ) : (
                      <span className="he-event-importance">
                        {'★'.repeat(Math.min(ev.importance || 1, 5))}
                      </span>
                    )}
                  </button>
                )
              })}
              {!level2Loading && level2Total > level2Items.length && (
                <div className="he-list-footer">
                  Showing {level2Items.length} of {level2Total.toLocaleString()}
                </div>
              )}
            </div>
          )}

          {/* Level 3: Child Events List */}
          {currentLevel === 'children' && (
            <div className="he-events-list">
              {childrenLoading && (
                <div className="he-loading">Loading sub-events...</div>
              )}
              {!childrenLoading && childrenList.length === 0 && (
                <div className="he-empty">No sub-events found.</div>
              )}
              {!childrenLoading && childrenList.map((child) => (
                <button
                  key={child.id}
                  className="he-event-item"
                  onClick={() => selectAndFly(child)}
                >
                  <span className="he-event-icon">{'\ud83d\udcc5'}</span>
                  <div className="he-event-info">
                    <span className="he-event-title">{child.title}</span>
                    <span className="he-event-dates">
                      {formatYear(child.date_start)}
                      {child.location && <> &middot; {child.location.name}</>}
                    </span>
                  </div>
                  <span className="he-event-importance">
                    {'★'.repeat(Math.min(child.importance || 1, 5))}
                  </span>
                </button>
              ))}
              {!childrenLoading && (childrenData?.count ?? 0) > childrenList.length && (
                <div className="he-list-footer">
                  Showing {childrenList.length} of {childrenData?.count}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <footer className="he-footer">
          <span className="he-footer-hint">
            {currentLevel === 'eras' && 'Select an era to explore its events'}
            {currentLevel === 'events' && `${level2Total.toLocaleString()} events in ${selectedEra?.name ?? 'era'}`}
            {currentLevel === 'children' && `${childrenData?.count ?? 0} sub-events of ${selectedParent?.title ?? 'event'}`}
          </span>
        </footer>
      </div>
    </div>
  )
}

export default HierarchyExplorer
