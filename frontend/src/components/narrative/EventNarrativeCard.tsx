import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { eventsApi, historiesApi } from '../../api/client'
import type { Event, EventRelationship, EventHierarchyNode, HistoryListItem } from '../../types'
import { ReportButton } from './ReportButton'

function formatYear(year: number | undefined): string {
  if (year === undefined || year === null) return ''
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

// ─── Event Hierarchy Section ────────────────────────────────

function EventHierarchySection({
  eventId,
  event,
  onEventClick,
}: {
  eventId: number
  event: Event
  onEventClick: (eventId: number) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const hasHierarchy = !!event.parent_event_id || (event.child_count && event.child_count > 0)

  const { data: children } = useQuery({
    queryKey: ['event-children', eventId],
    queryFn: () => eventsApi.getChildren(eventId).catch(() => ({ data: { children: [] } })),
    select: (res) => res.data?.children as EventHierarchyNode[] | undefined,
    enabled: hasHierarchy === true,
    retry: false,
  })

  if (!hasHierarchy) return null

  // Extract parent info - handle the case where parent might be on the event object
  const parentInfo = (event as Event & { parent?: { id: number; title: string; title_ko?: string } }).parent

  return (
    <div>
      <h4 className="text-[10px] uppercase tracking-wider text-chaldea-text mb-1.5">
        Event Hierarchy
      </h4>

      {/* Parent link */}
      {parentInfo && (
        <button
          onClick={() => onEventClick(parentInfo.id)}
          className="w-full text-left px-3 py-1.5 rounded text-xs border border-chaldea-border
                     hover:bg-chaldea-cyan/10 transition-colors flex items-center gap-2 mb-1"
        >
          <span className="text-chaldea-gold text-[10px]">Parent</span>
          <span className="text-chaldea-text-bright flex-1 truncate">
            {parentInfo.title}
          </span>
        </button>
      )}

      {/* Children */}
      {children && children.length > 0 && (
        <div>
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-chaldea-text hover:text-chaldea-text-bright
                       transition-colors mb-1"
          >
            <span className="text-[10px]">{expanded ? '\u25BC' : '\u25B6'}</span>
            <span>
              {children.length} sub-event{children.length !== 1 ? 's' : ''}
            </span>
          </button>
          {expanded && (
            <div className="space-y-0.5 ml-2 border-l border-chaldea-border pl-2">
              {children.map((child) => (
                <button
                  key={child.id}
                  onClick={() => onEventClick(child.id)}
                  className="w-full text-left px-2 py-1 rounded text-xs
                             hover:bg-chaldea-cyan/10 transition-colors flex items-center gap-2"
                >
                  <span className="text-chaldea-cyan text-[10px] w-14 text-right shrink-0">
                    {formatYear(child.date_start)}
                  </span>
                  <span className="text-chaldea-text-bright flex-1 truncate">
                    {child.title}
                  </span>
                  {child.child_count && child.child_count > 0 && (
                    <span className="text-chaldea-text text-[10px]">
                      +{child.child_count}
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Related Reading (Histories) ─────────────────────────────

function RelatedReading({ entityType, entityId }: { entityType: 'event' | 'person'; entityId: number }) {
  const { data: histories } = useQuery({
    queryKey: ['related-histories', entityType, entityId],
    queryFn: () => historiesApi.list({ entity_type: entityType, entity_id: entityId, limit: 3 }),
    select: (res) => (res.data?.items ?? []) as HistoryListItem[],
    retry: false,
  })

  if (!histories || histories.length === 0) return null

  return (
    <div className="border-t border-chaldea-border pt-3">
      <h4 className="text-[10px] uppercase tracking-wider text-chaldea-text mb-1.5">
        Related Reading
      </h4>
      <div className="space-y-1.5">
        {histories.map((h) => (
          <div key={h.id} className="p-2 rounded border border-chaldea-border/50 hover:border-chaldea-gold/30 transition-colors">
            <p className="text-[11px] text-chaldea-text-bright">{h.title}</p>
            {h.summary && (
              <p className="text-[9px] text-chaldea-text mt-0.5 line-clamp-2">{h.summary}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── EventNarrativeCard ─────────────────────────────────────

interface EventNarrativeCardProps {
  eventId: number
  onEventClick: (eventId: number) => void
  onPersonClick: (personId: number) => void
}

export function EventNarrativeCard({ eventId, onEventClick, onPersonClick }: EventNarrativeCardProps) {
  const { data: event, isLoading } = useQuery({
    queryKey: ['event', eventId],
    queryFn: () => eventsApi.get(eventId),
    select: (res) => res.data as Event,
  })

  const { data: relationships } = useQuery({
    queryKey: ['event-relationships', eventId],
    queryFn: () => eventsApi.getRelationships(eventId).catch(() => ({ data: { relationships: [] } })),
    select: (res) => res.data?.relationships as EventRelationship[] | undefined,
    retry: false,
  })

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-3">
          <div className="h-5 bg-chaldea-border rounded w-3/4" />
          <div className="h-3 bg-chaldea-border rounded w-1/2" />
          <div className="h-20 bg-chaldea-border rounded" />
        </div>
      </div>
    )
  }

  if (!event) return null

  const narrative = (event as Event & { narrative?: string }).narrative
  const significance = (event as Event & { significance?: string }).significance
  const causes = (event as Event & { causes?: string | string[] }).causes
  const consequences = (event as Event & { consequences?: string | string[] }).consequences
  const hasNarrative = !!narrative

  return (
    <div className="p-5 space-y-4">
      {/* Title + spacetime */}
      <div>
        <h2 className="text-lg font-semibold text-chaldea-text-bright leading-tight">
          {event.title}
        </h2>
        {event.title_ko && (
          <p className="text-sm text-chaldea-text mt-0.5">{event.title_ko}</p>
        )}
        <div className="flex items-center gap-3 mt-2 text-xs text-chaldea-text">
          <span className="text-chaldea-cyan">{formatYear(event.date_start)}</span>
          {event.location && <span>{event.location.name}</span>}
          {event.category && (
            <span className="px-1.5 py-0.5 rounded bg-chaldea-panel-alt border border-chaldea-border text-[10px]">
              {typeof event.category === 'string' ? event.category : event.category.name}
            </span>
          )}
        </div>
      </div>

      {/* Narrative (V4 core) */}
      {hasNarrative ? (
        <div className="space-y-3">
          <p className="text-sm text-chaldea-text-bright leading-relaxed">
            {narrative}
          </p>
          {significance && (
            <p className="text-xs text-chaldea-orange italic border-l-2 border-chaldea-orange pl-3">
              {significance}
            </p>
          )}
          {causes && (
            <div>
              <h4 className="text-[10px] uppercase tracking-wider text-chaldea-text mb-1">
                Causes
              </h4>
              {Array.isArray(causes) ? (
                <ul className="text-xs text-chaldea-text-bright space-y-0.5 list-disc list-inside">
                  {causes.map((c: string, i: number) => <li key={i}>{c}</li>)}
                </ul>
              ) : (
                <p className="text-xs text-chaldea-text-bright">{causes}</p>
              )}
            </div>
          )}
          {consequences && (
            <div>
              <h4 className="text-[10px] uppercase tracking-wider text-chaldea-text mb-1">
                Consequences
              </h4>
              {Array.isArray(consequences) ? (
                <ul className="text-xs text-chaldea-text-bright space-y-0.5 list-disc list-inside">
                  {consequences.map((c: string, i: number) => <li key={i}>{c}</li>)}
                </ul>
              ) : (
                <p className="text-xs text-chaldea-text-bright">{consequences}</p>
              )}
            </div>
          )}
        </div>
      ) : (
        /* Fallback to description */
        event.description && (
          <p className="text-sm text-chaldea-text leading-relaxed">
            {event.description}
          </p>
        )
      )}

      {/* Participants */}
      {event.persons && event.persons.length > 0 && (
        <div>
          <h4 className="text-[10px] uppercase tracking-wider text-chaldea-text mb-1.5">
            Key Figures
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {event.persons.map((p) => (
              <button
                key={p.id}
                onClick={() => onPersonClick(typeof p.id === 'number' ? p.id : parseInt(String(p.id), 10))}
                className="px-2 py-1 text-xs rounded border border-chaldea-border
                           text-chaldea-cyan hover:bg-chaldea-cyan/10 transition-colors"
              >
                {p.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Causal relationships */}
      {relationships && relationships.length > 0 && (
        <div>
          <h4 className="text-[10px] uppercase tracking-wider text-chaldea-text mb-1.5">
            Connected Events
          </h4>
          <div className="space-y-1">
            {relationships.slice(0, 5).map((r) => (
              <button
                key={r.id}
                onClick={() => onEventClick(r.related_event_id)}
                className="w-full text-left px-3 py-1.5 rounded text-xs border border-chaldea-border
                           hover:bg-chaldea-cyan/10 transition-colors flex items-center gap-2"
              >
                <span className="text-chaldea-text">
                  {r.direction === 'incoming' ? '\u2190' : '\u2192'}
                </span>
                <span className="text-chaldea-text-bright flex-1 truncate">
                  {r.related_event_title}
                </span>
                <span className="text-chaldea-cyan text-[10px]">
                  {formatYear(r.related_event_date_start)}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Event Hierarchy */}
      {event && <EventHierarchySection eventId={eventId} event={event} onEventClick={onEventClick} />}

      {/* Related Reading (Histories) */}
      <RelatedReading entityType="event" entityId={eventId} />

      {/* Rayshift entry point */}
      {relationships && relationships.length > 0 && (
        <div className="border-t border-chaldea-border pt-3">
          <button
            onClick={() => onEventClick(eventId)}
            className="text-[10px] px-3 py-1.5 rounded border border-chaldea-magenta/30
                       text-chaldea-magenta hover:bg-chaldea-magenta/10 transition-colors"
          >
            Follow Causal Chain &rarr;
          </button>
        </div>
      )}

      {/* Sources */}
      {event.sources && event.sources.length > 0 && (
        <div className="border-t border-chaldea-border pt-3">
          <h4 className="text-[10px] uppercase tracking-wider text-chaldea-text mb-1">
            Sources
          </h4>
          {event.sources.slice(0, 3).map((s) => (
            <p key={s.id} className="text-[10px] text-chaldea-text">
              {s.url ? (
                <a
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-chaldea-cyan"
                >
                  {s.name || s.type}
                </a>
              ) : (
                s.name || s.type
              )}
            </p>
          ))}
        </div>
      )}

      {/* Wikipedia link */}
      {event.wikipedia_url && (
        <a
          href={event.wikipedia_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block text-xs text-chaldea-cyan hover:underline"
        >
          Read on Wikipedia
        </a>
      )}

      {/* Report */}
      <div className="border-t border-chaldea-border pt-3">
        <ReportButton entityType="event" entityId={eventId} />
      </div>
    </div>
  )
}
