/**
 * PeriodDetailPanel - Period detail with regional narrative cards
 *
 * Shows a global overview + per-region narrative cards (sorted by activity),
 * each with headline, narrative, keywords, quote, and top entities.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { timelineApi } from '../../api/client'
import { FeedbackModal } from './FeedbackModal'
import type { PeriodDetail, PeriodEvent, RegionNarrative } from '../../types'

interface PeriodDetailPanelProps {
  periodStart: number
  onClose: () => void
  onEventClick?: (eventId: number) => void
  onPersonClick?: (personId: number) => void
  onFlyToLocation?: (lat: number, lng: number) => void
  onSetCurrentYear?: (year: number) => void
  layout?: 'sidebar' | 'wide'
}

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

const REGION_COLORS: Record<string, string> = {
  europe: '#4fc3f7',
  near_east: '#ffb74d',
  south_asia: '#81c784',
  east_asia: '#e57373',
  africa: '#ce93d8',
  americas: '#a1887f',
}

export function PeriodDetailPanel({
  periodStart,
  onClose,
  onEventClick,
  onPersonClick,
  onFlyToLocation,
  onSetCurrentYear,
  layout = 'sidebar',
}: PeriodDetailPanelProps) {
  const [feedbackTarget, setFeedbackTarget] = useState<{
    type: string
    id: number
  } | null>(null)
  // In wide layout, auto-expand the first region
  const [expandedRegion, setExpandedRegion] = useState<string | null>(null)
  const isWide = layout === 'wide'

  const { data: period, isLoading } = useQuery({
    queryKey: ['period-detail', periodStart],
    queryFn: () => timelineApi.getPeriodDetail(periodStart),
    select: (res) => res.data as PeriodDetail,
  })

  const handleEventFly = (event: PeriodEvent) => {
    if (event.latitude != null && event.longitude != null && onFlyToLocation) {
      onFlyToLocation(event.latitude, event.longitude)
    }
    if (event.date_start && onSetCurrentYear) {
      onSetCurrentYear(event.date_start)
    }
    if (onEventClick) {
      onEventClick(event.id)
    }
  }

  if (isLoading) {
    return (
      <div className="period-detail-panel">
        <div className="period-detail-loading">Loading period data...</div>
      </div>
    )
  }

  if (!period) {
    return (
      <div className="period-detail-panel">
        <div className="period-detail-empty">No data available for this period.</div>
      </div>
    )
  }

  return (
    <div className="period-detail-panel">
      {/* Header */}
      <div className="period-detail-header">
        {!isWide && (
          <button className="period-detail-back" onClick={onClose}>
            {'\u2190'} Back
          </button>
        )}
        <div className="period-detail-title">
          <span className="period-detail-range">
            {formatYear(period.period_start)} ~ {formatYear(period.period_end)}
          </span>
          {period.headline && (
            <h3 className="period-detail-headline">{period.headline}</h3>
          )}
        </div>
      </div>

      {/* Global Overview */}
      {period.narrative && (
        <div className="period-detail-narrative">
          <p>{period.narrative}</p>
          {period.defining_moment && (
            <div className="period-detail-moment">
              <span className="moment-label">Defining Moment:</span> {period.defining_moment}
            </div>
          )}
        </div>
      )}

      {/* Regional Narratives */}
      {period.regions.length > 0 && (
        <div className="period-regions">
          <h4 className="period-section-title">By Region</h4>
          {period.regions.map((region) => (
            <RegionCard
              key={region.region}
              region={region}
              isExpanded={expandedRegion === region.region}
              onToggle={() => setExpandedRegion(
                expandedRegion === region.region ? null : region.region
              )}
              onPersonClick={onPersonClick}
            />
          ))}
        </div>
      )}

      {/* Flat Event List (from DB, not narrative) */}
      {period.events.length > 0 && (
        <div className="period-detail-section">
          <h4 className="period-section-title">All Events</h4>
          {period.events.map((event) => (
            <button
              key={event.id}
              className="period-entity-card"
              onClick={() => handleEventFly(event)}
            >
              <div className="period-entity-header">
                <span className="period-entity-name">{event.title}</span>
                <span className="period-entity-score">{event.importance_score}</span>
              </div>
              <div className="period-entity-meta">
                <span>{event.date_display}</span>
                {event.location_name && <span> | {event.location_name}</span>}
              </div>
              {event.description && (
                <p className="period-entity-desc">{event.description}</p>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Flat Person List */}
      {period.persons.length > 0 && (
        <div className="period-detail-section">
          <h4 className="period-section-title">Key Figures</h4>
          {period.persons.map((person) => (
            <button
              key={person.id}
              className="period-entity-card person-card"
              onClick={() => onPersonClick?.(person.id)}
            >
              <div className="period-entity-header">
                <span className="period-entity-name">{person.name}</span>
                <span className="period-entity-score">{person.score}</span>
              </div>
              <div className="period-entity-meta">
                <span>{person.date_display}</span>
                {person.domain && (
                  <span className="period-person-domain">{person.domain}</span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Feedback */}
      <div className="period-detail-feedback">
        <button
          className="period-feedback-btn"
          onClick={() => setFeedbackTarget({
            type: 'period_narrative',
            id: period.narrative_id || period.period_start,
          })}
        >
          {'\u26A0'} Report an issue with this content
        </button>
      </div>

      {/* Feedback Modal */}
      {feedbackTarget && (
        <FeedbackModal
          targetType={feedbackTarget.type}
          targetId={feedbackTarget.id}
          onClose={() => setFeedbackTarget(null)}
        />
      )}
    </div>
  )
}


/** Region card with expandable narrative */
function RegionCard({
  region,
  isExpanded,
  onToggle,
}: {
  region: RegionNarrative
  isExpanded: boolean
  onToggle: () => void
  onPersonClick?: (personId: number) => void
}) {
  const color = REGION_COLORS[region.region] || '#9e9e9e'

  return (
    <div
      className={`region-card ${isExpanded ? 'region-card--expanded' : ''}`}
      style={{ '--region-color': color } as React.CSSProperties}
    >
      <button className="region-card-header" onClick={onToggle}>
        <span className="region-card-tag" style={{ borderColor: color, color }}>
          {region.region_name}
        </span>
        <span className="region-card-counts">
          {region.event_count > 0 && <span>{region.event_count} events</span>}
          {region.person_count > 0 && <span>{region.person_count} figures</span>}
        </span>
        <span className="region-card-chevron">{isExpanded ? '\u25B2' : '\u25BC'}</span>
      </button>

      {region.headline && (
        <div className="region-card-headline">{region.headline}</div>
      )}

      {isExpanded && (
        <div className="region-card-body">
          {region.narrative && (
            <p className="region-card-narrative">{region.narrative}</p>
          )}

          {region.keywords && region.keywords.length > 0 && (
            <div className="period-detail-keywords">
              {region.keywords.map((kw, i) => (
                <span key={i} className="period-keyword-tag">{kw}</span>
              ))}
            </div>
          )}

          {region.quote && (
            <blockquote className="region-card-quote">
              "{region.quote}"
              {region.quote_source && (
                <cite> — {region.quote_source}</cite>
              )}
            </blockquote>
          )}

          {/* Top events from narrative data */}
          {region.top_events && region.top_events.length > 0 && (
            <div className="region-card-entities">
              <span className="region-entity-label">Events:</span>
              {region.top_events.map((e, i) => (
                <span key={i} className="region-entity-chip">
                  {e.title} ({e.date})
                </span>
              ))}
            </div>
          )}

          {/* Top persons from narrative data */}
          {region.top_persons && region.top_persons.length > 0 && (
            <div className="region-card-entities">
              <span className="region-entity-label">Figures:</span>
              {region.top_persons.map((p, i) => (
                <button
                  key={i}
                  className="region-entity-chip region-entity-chip--person"
                  onClick={(e) => {
                    e.stopPropagation()
                    // top_persons from narrative don't have DB ids, so just display
                  }}
                >
                  {p.name}
                  {p.domain && <span className="region-entity-domain">{p.domain}</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
