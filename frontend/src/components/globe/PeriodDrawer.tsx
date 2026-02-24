import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { timelineApi } from '../../api/client'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import type { PeriodEvent, PeriodPerson } from '../../types'

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

function ImportanceStars({ score }: { score: number }) {
  const stars = Math.min(Math.max(Math.round(score), 1), 5)
  return (
    <span className="inline-flex gap-px text-chaldea-gold text-[9px]">
      {Array.from({ length: stars }).map((_, i) => (
        <span key={i}>*</span>
      ))}
    </span>
  )
}

function Lifespan({ birth, death }: { birth?: number; death?: number }) {
  if (birth == null && death == null) return null
  const parts: string[] = []
  if (birth != null) parts.push(formatYear(birth))
  if (death != null) parts.push(formatYear(death))
  return (
    <span className="text-[9px] text-chaldea-text/60">
      {parts.join(' \u2013 ')}
    </span>
  )
}

interface PeriodDrawerProps {
  periodStart: number
  onClose: () => void
  onEventClick: (eventId: number) => void
  onPersonClick: (personId: number) => void
}

export default function PeriodDrawer({ periodStart, onClose, onEventClick, onPersonClick }: PeriodDrawerProps) {
  const { preferredLanguage } = useSettingsStore()
  const drawerRef = useRef<HTMLDivElement>(null)

  const { data: events, isLoading: eventsLoading } = useQuery({
    queryKey: ['period-events', periodStart],
    queryFn: () => timelineApi.getPeriodEvents(periodStart, { limit: 15 }),
    select: (res) => {
      const data = res.data
      return ((data?.items ?? data) as PeriodEvent[]).sort(
        (a, b) => (b.importance_score ?? 0) - (a.importance_score ?? 0)
      )
    },
  })

  const { data: persons, isLoading: personsLoading } = useQuery({
    queryKey: ['period-persons', periodStart],
    queryFn: () => timelineApi.getPeriodPersons(periodStart, { limit: 10 }),
    select: (res) => {
      const data = res.data
      return (data?.items ?? data) as PeriodPerson[]
    },
  })

  // Close on Escape
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  // Click outside to close
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (drawerRef.current && !drawerRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    const timer = setTimeout(() => {
      window.addEventListener('mousedown', handleClick)
    }, 100)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('mousedown', handleClick)
    }
  }, [onClose])

  const periodEnd = periodStart + 50

  return (
    <div
      ref={drawerRef}
      className="fixed z-30 period-drawer-enter"
      style={{
        left: '320px',
        right: 0,
        top: '110px',
        maxHeight: '60vh',
      }}
    >
      <div
        className="max-w-5xl mx-auto rounded-b-xl border border-t-0 border-chaldea-border overflow-hidden"
        style={{
          background: 'rgba(10, 16, 24, 0.95)',
          backdropFilter: 'blur(16px)',
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-chaldea-border">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-chaldea-cyan">
              Period Detail
            </div>
            <h2 className="text-sm font-semibold text-chaldea-text-bright">
              {formatYear(periodStart)} &ndash; {formatYear(periodEnd)}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded
                       border border-chaldea-border text-chaldea-text hover:text-chaldea-cyan
                       hover:border-chaldea-cyan/50 transition-colors text-xs"
            title="Close"
          >
            &#x2715;
          </button>
        </div>

        {/* Two-column content */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-0 md:gap-0 overflow-y-auto" style={{ maxHeight: 'calc(60vh - 56px)' }}>
          {/* Left: Top Events */}
          <div className="border-r border-chaldea-border/50 px-4 py-3 overflow-y-auto" style={{ maxHeight: 'calc(60vh - 56px)' }}>
            <div className="text-[10px] uppercase tracking-wider text-chaldea-cyan mb-2.5 font-medium">
              Top Events
            </div>
            {eventsLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="animate-pulse">
                    <div className="h-3 bg-chaldea-border rounded w-4/5 mb-1" />
                    <div className="h-2 bg-chaldea-border rounded w-1/2" />
                  </div>
                ))}
              </div>
            ) : !events || events.length === 0 ? (
              <div className="text-[10px] text-chaldea-text/40 py-4">No events found for this period.</div>
            ) : (
              <div className="space-y-1">
                {events.map((event) => (
                  <button
                    key={event.id}
                    onClick={() => {
                      onEventClick(event.id)
                      onClose()
                    }}
                    className="w-full text-left px-3 py-2 rounded-md border border-transparent
                               hover:border-chaldea-border hover:bg-chaldea-panel/60
                               transition-all duration-150 group"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="text-[11px] text-chaldea-text-bright group-hover:text-white leading-tight flex-1">
                        {getLocalizedText(event as unknown as Record<string, unknown>, 'title', preferredLanguage) || event.title}
                      </div>
                      {event.importance_score != null && (
                        <ImportanceStars score={event.importance_score} />
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      {event.date_display ? (
                        <span className="text-[9px] text-chaldea-text/60">{event.date_display}</span>
                      ) : event.date_start != null ? (
                        <span className="text-[9px] text-chaldea-text/60">{formatYear(event.date_start)}</span>
                      ) : null}
                      {event.location_name && (
                        <span className="text-[9px] text-chaldea-text/40">{event.location_name}</span>
                      )}
                    </div>
                    {event.description && (
                      <div className="text-[9px] text-chaldea-text/40 mt-1 line-clamp-2 leading-relaxed">
                        {event.description}
                      </div>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Right: Key Figures */}
          <div className="px-4 py-3 overflow-y-auto" style={{ maxHeight: 'calc(60vh - 56px)' }}>
            <div className="text-[10px] uppercase tracking-wider text-chaldea-orange mb-2.5 font-medium">
              Key Figures
            </div>
            {personsLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="animate-pulse">
                    <div className="h-3 bg-chaldea-border rounded w-3/5 mb-1" />
                    <div className="h-2 bg-chaldea-border rounded w-2/5" />
                  </div>
                ))}
              </div>
            ) : !persons || persons.length === 0 ? (
              <div className="text-[10px] text-chaldea-text/40 py-4">No figures found for this period.</div>
            ) : (
              <div className="space-y-1">
                {persons.map((person) => (
                  <button
                    key={person.id}
                    onClick={() => {
                      onPersonClick(person.id)
                      onClose()
                    }}
                    className="w-full text-left px-3 py-2 rounded-md border border-transparent
                               hover:border-chaldea-border hover:bg-chaldea-panel/60
                               transition-all duration-150 group"
                  >
                    <div className="text-[11px] text-chaldea-text-bright group-hover:text-white leading-tight">
                      {getLocalizedText(person as unknown as Record<string, unknown>, 'name', preferredLanguage) || person.name}
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <Lifespan birth={person.birth_year} death={person.death_year} />
                      {person.role && person.role !== 'occupation' && person.role !== 'None' && (
                        <span className="text-[9px] text-chaldea-cyan/60">{person.role}</span>
                      )}
                      {person.domain && (
                        <span className="text-[9px] text-chaldea-text/40">{person.domain}</span>
                      )}
                    </div>
                    {person.significance && (
                      <div className="text-[9px] text-chaldea-text/40 mt-1 line-clamp-2 leading-relaxed">
                        {person.significance}
                      </div>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
