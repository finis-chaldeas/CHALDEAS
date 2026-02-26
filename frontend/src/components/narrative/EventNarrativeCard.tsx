import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { eventsApi } from '../../api/client'
import type { Event, EventRelationship, EventHierarchyNode } from '../../types'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import { ReportButton } from './ReportButton'

function formatYear(year: number | undefined): string {
  if (year === undefined || year === null) return ''
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

// ─── Event Story Section (Hierarchy as Story) ────────────────

function EventStorySection({
  eventId,
  event,
  onEventClick,
  onRayshiftHierarchy,
}: {
  eventId: number
  event: Event
  onEventClick: (eventId: number) => void
  onRayshiftHierarchy?: (eventId: number) => void
}) {
  // Always try to fetch children — don't gate on child_count
  const { data: children } = useQuery({
    queryKey: ['event-children', eventId],
    queryFn: () => eventsApi.getChildren(eventId).catch(() => ({ data: { children: [] } })),
    select: (res) => (res.data?.items ?? res.data?.children ?? []) as EventHierarchyNode[],
    retry: false,
  })

  const { t } = useTranslation()
  const { preferredLanguage } = useSettingsStore()
  const parentInfo = (event as Event & { parent?: { id: number; title: string; title_ko?: string } }).parent
  const hasParent = !!event.parent_event_id
  const hasChildren = children && children.length > 0

  if (!hasParent && !hasChildren) return null

  return (
    <div className="nc-section">
      {/* Parent link */}
      {hasParent && parentInfo && (
        <div>
          <div className="nc-section-header">{t('narrative.partOf')}</div>
          <button onClick={() => onEventClick(parentInfo.id)}
            className="nc-link-item" style={{ borderLeft: '3px solid var(--chaldea-gold)' }}>
            <span className="nc-link-arrow">{'\u2191'}</span>
            <span className="nc-link-title">{getLocalizedText(parentInfo as unknown as Record<string, unknown>, 'title', preferredLanguage) || parentInfo.title}</span>
          </button>
        </div>
      )}

      {/* Children as story timeline */}
      {hasChildren && (
        <div style={{ marginTop: hasParent && parentInfo ? '0.75rem' : 0 }}>
          <div className="nc-section-header">{t('narrative.story')} ({children.length} {t('narrative.events')})</div>
          <div className="nc-story-list">
            {children.map((child) => (
              <button key={child.id} onClick={() => onEventClick(child.id)} className="nc-story-item">
                <span className="nc-story-item-year">{formatYear(child.date_start)}</span>
                <span className="nc-story-item-title">{getLocalizedText(child as unknown as Record<string, unknown>, 'title', preferredLanguage) || child.title}</span>
                {child.child_count != null && child.child_count > 0 && (
                  <span className="nc-story-item-meta">+{child.child_count} {t('narrative.subEvents')}</span>
                )}
              </button>
            ))}
          </div>
          {onRayshiftHierarchy && children.length > 1 && (
            <button onClick={() => onRayshiftHierarchy(eventId)}
              className="nc-rayshift-btn nc-rayshift-btn--hierarchy" style={{ marginTop: '0.5rem' }}>
              {t('narrative.rayshiftStory')} &rarr;
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// ─── EventNarrativeCard ─────────────────────────────────────

interface EventNarrativeCardProps {
  eventId: number
  onEventClick: (eventId: number) => void
  onPersonClick: (personId: number) => void
  onLocationClick?: (locationId: number) => void
  onSourceClick?: (sourceId: number) => void
  onRayshift?: (eventId: number) => void
  onRayshiftHierarchy?: (eventId: number) => void
}

export function EventNarrativeCard({ eventId, onEventClick, onPersonClick, onLocationClick, onSourceClick, onRayshift, onRayshiftHierarchy }: EventNarrativeCardProps) {
  const { t } = useTranslation()
  const { preferredLanguage } = useSettingsStore()
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
      <div className="nc-loading">
        <div className="nc-loading-bar nc-loading-bar--wide" />
        <div className="nc-loading-bar nc-loading-bar--mid" />
        <div className="nc-loading-bar nc-loading-bar--tall" />
      </div>
    )
  }

  if (!event) return null

  // Localized narrative fields from entity_narratives
  const eventAny = event as Event & {
    narrative?: string; narrative_ko?: string; narrative_ja?: string
    significance?: string; significance_ko?: string; significance_ja?: string
    causes?: string | string[]; causes_ko?: string | string[]; causes_ja?: string | string[]
    consequences?: string | string[]; consequences_ko?: string | string[]; consequences_ja?: string | string[]
    details?: { description_ko?: string; description_ja?: string; description?: string }
  }
  const pick = <T,>(en: T | undefined, ko: T | undefined, ja: T | undefined): T | undefined =>
    preferredLanguage === 'ko' ? (ko || en) : preferredLanguage === 'ja' ? (ja || en) : en

  const narrative = pick(eventAny.narrative, eventAny.narrative_ko, eventAny.narrative_ja)
    || pick(eventAny.details?.description, eventAny.details?.description_ko, eventAny.details?.description_ja)
  const significance = pick(eventAny.significance, eventAny.significance_ko, eventAny.significance_ja)
  const causes = pick(eventAny.causes, eventAny.causes_ko, eventAny.causes_ja)
  const consequences = pick(eventAny.consequences, eventAny.consequences_ko, eventAny.consequences_ja)
  const hasNarrative = !!narrative

  return (
    <div className="nc-content">
      {/* Title + spacetime */}
      <div>
        <h2 className="nc-title">{getLocalizedText(event as unknown as Record<string, unknown>, 'title', preferredLanguage) || event.title}</h2>
        <div className="nc-spacetime">
          <span className="nc-year">{formatYear(event.date_start)}</span>
          {event.location && (
            <span
              className="nc-location-link"
              onClick={(e) => {
                e.stopPropagation()
                if (onLocationClick && event.location?.id) {
                  onLocationClick(event.location.id)
                }
              }}
              style={{ cursor: onLocationClick ? 'pointer' : 'default' }}
            >
              {getLocalizedText(event.location as unknown as Record<string, unknown>, 'name', preferredLanguage) || event.location.name}
            </span>
          )}
          {event.category && (
            <span className="nc-category">
              {typeof event.category === 'string' ? event.category : event.category.name}
            </span>
          )}
        </div>
      </div>

      {/* Narrative (V4 core) */}
      {hasNarrative ? (
        <div>
          <p className="nc-narrative">{narrative}</p>
          {significance && <p className="nc-significance">{significance}</p>}
          {causes && (
            <div style={{ marginTop: '0.75rem' }}>
              <div className="nc-cause-title">{t('narrative.causes')}</div>
              {Array.isArray(causes) ? (
                <ul className="nc-cause-list">
                  {causes.map((c: string, i: number) => <li key={i}>{c}</li>)}
                </ul>
              ) : (
                <p className="nc-cause-text">{causes}</p>
              )}
            </div>
          )}
          {consequences && (
            <div style={{ marginTop: '0.75rem' }}>
              <div className="nc-cause-title">{t('narrative.consequences')}</div>
              {Array.isArray(consequences) ? (
                <ul className="nc-cause-list">
                  {consequences.map((c: string, i: number) => <li key={i}>{c}</li>)}
                </ul>
              ) : (
                <p className="nc-cause-text">{consequences}</p>
              )}
            </div>
          )}
        </div>
      ) : (
        event.description && <p className="nc-description">{pick(eventAny.details?.description, eventAny.details?.description_ko, eventAny.details?.description_ja) || event.description}</p>
      )}

      {/* Key Figures */}
      {event.persons && event.persons.length > 0 && (
        <div>
          <div className="nc-section-header">{t('narrative.keyFigures')}</div>
          <div className="nc-person-tags">
            {event.persons.map((p) => (
              <button
                key={p.id}
                onClick={() => onPersonClick(typeof p.id === 'number' ? p.id : parseInt(String(p.id), 10))}
                className="nc-person-tag"
              >
                {getLocalizedText(p as unknown as Record<string, unknown>, 'name', preferredLanguage) || p.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Connected Events */}
      {relationships && relationships.length > 0 && (
        <div>
          <div className="nc-section-header">{t('narrative.connectedEvents')}</div>
          <div className="nc-link-list">
            {relationships.slice(0, 5).map((r) => (
              <button key={r.id} onClick={() => onEventClick(r.related_event_id)} className="nc-link-item">
                <span className="nc-link-arrow">
                  {r.direction === 'incoming' ? '\u2190' : '\u2192'}
                </span>
                <span className="nc-link-title">{getLocalizedText(r as unknown as Record<string, unknown>, 'related_event_title', preferredLanguage) || r.related_event_title}</span>
                <span className="nc-link-year">{formatYear(r.related_event_date_start)}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Story (hierarchy children as timeline) */}
      <EventStorySection eventId={eventId} event={event} onEventClick={onEventClick} onRayshiftHierarchy={onRayshiftHierarchy} />

      {/* Rayshift */}
      {relationships && relationships.length > 0 && onRayshift && (
        <div className="nc-section">
          <button onClick={() => onRayshift(eventId)} className="nc-rayshift-btn nc-rayshift-btn--causal">
            {t('narrative.rayshiftCausal')} &rarr;
          </button>
        </div>
      )}

      {/* Sources — open in modal */}
      {event.sources && event.sources.length > 0 && (
        <div className="nc-section">
          <div className="nc-section-header">{t('narrative.sources')} ({event.sources.length})</div>
          <div className="nc-sources-list">
            {event.sources.slice(0, 5).map((s) => {
              const displayTitle = s.title || s.name || s.type
              return (
                <button key={s.id}
                  onClick={() => onSourceClick?.(s.id)}
                  className="nc-source-link">
                  <span className="nc-source-link-title">{displayTitle}</span>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Report */}
      <div className="nc-section">
        <ReportButton entityType="event" entityId={eventId} />
      </div>
    </div>
  )
}
