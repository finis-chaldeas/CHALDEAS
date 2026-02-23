import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { timelineApi } from '../../api/client'
import { useTimelineStore } from '../../store/timelineStore'
import { useGlobeStore } from '../../store/globeStore'
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
  const headline = period?.headline || `${formatYear(periodStart)} \u2013 ${formatYear(periodStart + 50)}`

  return (
    <>
      <div className="fixed top-2 left-1/2 -translate-x-1/2 z-20 max-w-[560px] w-[calc(100vw-2rem)] pointer-events-none">
        {/* Single-line bar */}
        <button
          onClick={() => !isCompact && setExpanded((e) => !e)}
          className="pointer-events-auto w-full flex items-center justify-center gap-3
                     bg-chaldea-panel/80 backdrop-blur-xl rounded-lg border border-chaldea-border/30
                     px-4 py-1.5 transition-all hover:border-chaldea-cyan/20"
        >
          <span className="text-[10px] text-chaldea-cyan/60 tracking-widest uppercase shrink-0">
            {formatYear(periodStart)}
          </span>
          <span className="text-xs text-chaldea-text-bright font-medium truncate">
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
          <div className="pointer-events-auto bg-chaldea-panel/90 backdrop-blur-xl
                          rounded-b-lg border border-t-0 border-chaldea-border/30
                          px-4 py-3 max-h-[260px] overflow-y-auto">
            {period?.narrative && (
              <p className="text-[11px] text-chaldea-text leading-relaxed mb-2">{period.narrative}</p>
            )}
            {period?.defining_moment && (
              <p className="text-[10px] text-chaldea-orange italic mb-2">{period.defining_moment}</p>
            )}

            {topEvents.length > 0 && (
              <div className="flex flex-wrap items-center gap-1 mb-1.5">
                <span className="text-[9px] text-chaldea-cyan/40 uppercase tracking-wide">Events</span>
                {topEvents.map((evt) => (
                  <button key={evt.id}
                    onClick={(e) => { e.stopPropagation(); onEventClick(evt.id) }}
                    className="text-[10px] text-chaldea-text-bright bg-chaldea-cyan/5
                               border border-chaldea-cyan/10 rounded px-1.5 py-px
                               hover:bg-chaldea-cyan/10 hover:border-chaldea-cyan/20 transition-colors">
                    {evt.title}
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
                    className="text-[10px] text-chaldea-text-bright bg-chaldea-orange/5
                               border border-chaldea-orange/10 rounded px-1.5 py-px
                               hover:bg-chaldea-orange/10 hover:border-chaldea-orange/20 transition-colors">
                    {person.name}
                  </button>
                ))}
              </div>
            )}

            <div className="flex items-center gap-2 pt-2 border-t border-white/5">
              <button
                onClick={(e) => { e.stopPropagation(); setDrawerOpen((o) => !o) }}
                className={`text-[9px] uppercase tracking-wide px-2 py-1 rounded border transition-colors
                  ${drawerOpen
                    ? 'bg-chaldea-cyan/10 border-chaldea-cyan/20 text-chaldea-cyan'
                    : 'border-white/10 text-chaldea-text hover:text-chaldea-cyan hover:border-chaldea-cyan/20'}`}>
                {drawerOpen ? 'Close Details' : 'View Details'}
              </button>
              {onOpenDeepRead && (
                <button
                  onClick={(e) => { e.stopPropagation(); onOpenDeepRead() }}
                  className="text-[9px] uppercase tracking-wide px-2 py-1 rounded
                             border border-white/10 text-chaldea-text
                             hover:text-chaldea-orange hover:border-chaldea-orange/20 transition-colors">
                  Deep Read
                </button>
              )}
              <div className="flex-1" />
              <button onClick={(e) => { e.stopPropagation(); handleFeedback(1) }}
                disabled={feedbackSent !== null}
                className={`w-5 h-5 flex items-center justify-center text-[9px] rounded border transition-colors
                  ${feedbackSent === 'up' ? 'border-chaldea-green/40 bg-chaldea-green/10 text-chaldea-green' : 'border-white/10 text-chaldea-text/50 hover:text-chaldea-green'}`}>
                &#x25B2;
              </button>
              <button onClick={(e) => { e.stopPropagation(); handleFeedback(-1) }}
                disabled={feedbackSent !== null}
                className={`w-5 h-5 flex items-center justify-center text-[9px] rounded border transition-colors
                  ${feedbackSent === 'down' ? 'border-chaldea-magenta/40 bg-chaldea-magenta/10 text-chaldea-magenta' : 'border-white/10 text-chaldea-text/50 hover:text-chaldea-magenta'}`}>
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
