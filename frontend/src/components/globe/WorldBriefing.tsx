import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { timelineApi } from '../../api/client'
import { useTimelineStore } from '../../store/timelineStore'
import { useGlobeStore } from '../../store/globeStore'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import type { PeriodDetail, PeriodEvent, PeriodPerson } from '../../types'
import PeriodDrawer from './PeriodDrawer'

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

interface WorldBriefingProps {
  onEventClick: (eventId: number) => void
  onPersonClick: (personId: number) => void
  onOpenDeepRead?: () => void
}

export default function WorldBriefing({ onEventClick, onPersonClick, onOpenDeepRead }: WorldBriefingProps) {
  const currentYear = useTimelineStore((s) => s.currentYear)
  const zoomLevel = useGlobeStore((s) => s.zoomLevel)
  const { preferredLanguage } = useSettingsStore()

  const [expanded, setExpanded] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [feedbackSent, setFeedbackSent] = useState<'up' | 'down' | null>(null)

  const periodStart = useMemo(() => Math.floor(currentYear / 50) * 50, [currentYear])

  const { data: period, isLoading } = useQuery({
    queryKey: ['period-detail', periodStart],
    queryFn: () => timelineApi.getPeriodDetail(periodStart, { event_limit: 5, person_limit: 5 }),
    select: (res) => res.data as PeriodDetail,
  })

  useEffect(() => { setFeedbackSent(null) }, [periodStart])
  useEffect(() => { setExpanded(false) }, [periodStart])

  async function handleFeedback(rating: number) {
    const direction = rating > 0 ? 'up' : 'down'
    if (feedbackSent === direction) return
    try {
      await timelineApi.submitFeedback({
        target_type: 'period_narrative',
        target_id: periodStart,
        feedback_type: direction === 'up' ? 'helpful' : 'incorrect',
      })
      setFeedbackSent(direction)
    } catch { /* silently fail */ }
  }

  const topEvents = (period?.events ?? []).slice(0, 3) as PeriodEvent[]
  const topPersons = (period?.persons ?? []).slice(0, 3) as PeriodPerson[]
  const isCompact = zoomLevel === 'cosmic' || zoomLevel === 'continental'
  // Language-aware headline
  const rawHeadline = preferredLanguage === 'ko'
    ? (period?.headline_ko || period?.headline)
    : period?.headline
  const headline = rawHeadline || `${formatYear(periodStart)} \u2013 ${formatYear(periodStart + 50)}`

  // Language-aware narrative
  const rawNarrative = preferredLanguage === 'ko'
    ? ((period as unknown as Record<string, string>)?.narrative_ko || period?.narrative)
    : period?.narrative

  return (
    <>
      <div className="world-briefing">
        {/* Single-line bar */}
        <button
          onClick={() => !isCompact && setExpanded((e) => !e)}
          className="world-briefing-bar"
        >
          <span className="world-briefing-year">
            {formatYear(periodStart)}
          </span>
          <span className="world-briefing-headline">
            {isLoading ? '...' : headline}
          </span>
          {!isCompact && (
            <span className="text-[9px] text-chaldea-text/40 shrink-0">
              {expanded ? '\u25B2' : '\u25BC'}
            </span>
          )}
        </button>

        {/* Expanded detail */}
        {expanded && !isCompact && (
          <div className="world-briefing-expanded">
            {rawNarrative && (
              <p className="world-briefing-narrative">{rawNarrative}</p>
            )}
            {period?.defining_moment && (
              <p className="world-briefing-moment">{period.defining_moment}</p>
            )}

            {topEvents.length > 0 && (
              <div className="flex flex-wrap items-center gap-1 mb-1.5">
                <span className="text-[9px] text-chaldea-cyan/40 uppercase tracking-wide">Events</span>
                {topEvents.map((evt) => (
                  <button key={evt.id}
                    onClick={(e) => { e.stopPropagation(); onEventClick(evt.id) }}
                    className="world-briefing-tag">
                    {getLocalizedText(evt as unknown as Record<string, unknown>, 'title', preferredLanguage) || evt.title}
                  </button>
                ))}
              </div>
            )}

            {topPersons.length > 0 && (
              <div className="flex flex-wrap items-center gap-1 mb-2">
                <span className="text-[9px] text-chaldea-orange/40 uppercase tracking-wide">Figures</span>
                {topPersons.map((person) => (
                  <button key={person.id}
                    onClick={(e) => { e.stopPropagation(); onPersonClick(person.id) }}
                    className="world-briefing-tag world-briefing-tag--person">
                    {getLocalizedText(person as unknown as Record<string, unknown>, 'name', preferredLanguage) || person.name}
                  </button>
                ))}
              </div>
            )}

            <div className="world-briefing-actions">
              <button
                onClick={(e) => { e.stopPropagation(); setDrawerOpen((o) => !o) }}
                className={`world-briefing-action-btn ${drawerOpen ? 'active' : ''}`}>
                {drawerOpen ? 'Close Details' : 'View Details'}
              </button>
              {onOpenDeepRead && (
                <button
                  onClick={(e) => { e.stopPropagation(); onOpenDeepRead() }}
                  className="world-briefing-action-btn">
                  Deep Read
                </button>
              )}
              <div className="flex-1" />
              <button onClick={(e) => { e.stopPropagation(); handleFeedback(1) }}
                disabled={feedbackSent !== null}
                className={`world-briefing-feedback ${feedbackSent === 'up' ? 'active-up' : ''}`}>
                &#x25B2;
              </button>
              <button onClick={(e) => { e.stopPropagation(); handleFeedback(-1) }}
                disabled={feedbackSent !== null}
                className={`world-briefing-feedback ${feedbackSent === 'down' ? 'active-down' : ''}`}>
                &#x25BC;
              </button>
            </div>
          </div>
        )}
      </div>

      {drawerOpen && (
        <PeriodDrawer periodStart={periodStart} onClose={() => setDrawerOpen(false)}
          onEventClick={onEventClick} onPersonClick={onPersonClick} />
      )}
    </>
  )
}
