import { useState, useMemo, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { timelineApi, feedApi } from '../../api/client'
import { useTimelineStore } from '../../store/timelineStore'
import type { PeriodDetail, PeriodEvent, PeriodPerson, FeedItem } from '../../types'

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

const PERIOD_PRESETS = [
  { year: -3000, label: '3000 BCE', era: 'Ancient' },
  { year: -2500, label: '2500 BCE', era: 'Ancient' },
  { year: -2000, label: '2000 BCE', era: 'Ancient' },
  { year: -1500, label: '1500 BCE', era: 'Ancient' },
  { year: -1000, label: '1000 BCE', era: 'Ancient' },
  { year: -500, label: '500 BCE', era: 'Classical' },
  { year: -200, label: '200 BCE', era: 'Classical' },
  { year: 0, label: '1 CE', era: 'Classical' },
  { year: 200, label: '200 CE', era: 'Classical' },
  { year: 500, label: '500 CE', era: 'Medieval' },
  { year: 800, label: '800 CE', era: 'Medieval' },
  { year: 1000, label: '1000 CE', era: 'Medieval' },
  { year: 1200, label: '1200 CE', era: 'Medieval' },
  { year: 1400, label: '1400 CE', era: 'Early Modern' },
  { year: 1500, label: '1500 CE', era: 'Early Modern' },
  { year: 1600, label: '1600 CE', era: 'Early Modern' },
  { year: 1700, label: '1700 CE', era: 'Early Modern' },
  { year: 1800, label: '1800 CE', era: 'Modern' },
  { year: 1850, label: '1850 CE', era: 'Modern' },
  { year: 1900, label: '1900 CE', era: 'Modern' },
  { year: 1950, label: '1950 CE', era: 'Modern' },
  { year: 2000, label: '2000 CE', era: 'Modern' },
]

type DeepReadTab = 'narrative' | 'events' | 'persons' | 'feed'

interface DeepReadModalProps {
  isOpen: boolean
  onClose: () => void
  onEventClick: (eventId: number) => void
  onPersonClick: (personId: number) => void
}

export default function DeepReadModal({ isOpen, onClose, onEventClick, onPersonClick }: DeepReadModalProps) {
  const setCurrentYear = useTimelineStore((s) => s.setCurrentYear)
  const [selectedPeriod, setSelectedPeriod] = useState(-500)
  const [activeTab, setActiveTab] = useState<DeepReadTab>('narrative')
  const [eraFilter, setEraFilter] = useState<string | null>(null)

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  const filteredPresets = useMemo(() => {
    if (!eraFilter) return PERIOD_PRESETS
    return PERIOD_PRESETS.filter(p => p.era === eraFilter)
  }, [eraFilter])

  const eras = [...new Set(PERIOD_PRESETS.map(p => p.era))]

  const { data: period } = useQuery({
    queryKey: ['period-detail', selectedPeriod],
    queryFn: () => timelineApi.getPeriodDetail(selectedPeriod, { event_limit: 10, person_limit: 10 }),
    select: (res) => res.data as PeriodDetail,
    enabled: isOpen,
  })

  const { data: periodEvents } = useQuery({
    queryKey: ['period-events', selectedPeriod],
    queryFn: () => timelineApi.getPeriodEvents(selectedPeriod, { limit: 20 }),
    select: (res) => (res.data.items || []) as PeriodEvent[],
    enabled: isOpen && activeTab === 'events',
  })

  const { data: periodPersons } = useQuery({
    queryKey: ['period-persons', selectedPeriod],
    queryFn: () => timelineApi.getPeriodPersons(selectedPeriod, { limit: 20 }),
    select: (res) => (res.data.items || []) as PeriodPerson[],
    enabled: isOpen && activeTab === 'persons',
  })

  const { data: feedItems } = useQuery({
    queryKey: ['feed', selectedPeriod],
    queryFn: () => feedApi.get({
      year_start: selectedPeriod,
      year_end: selectedPeriod + 50,
      limit: 30,
    }),
    select: (res) => (res.data.items || []) as FeedItem[],
    enabled: isOpen && activeTab === 'feed',
  })

  const handleSelectPeriod = (year: number) => {
    setSelectedPeriod(year)
    setCurrentYear(year)
  }

  const goToGlobe = (eventId?: number, personId?: number) => {
    if (eventId) onEventClick(eventId)
    if (personId) onPersonClick(personId)
    onClose()
  }

  if (!isOpen) return null

  const tabs: { key: DeepReadTab; label: string }[] = [
    { key: 'narrative', label: 'Narrative' },
    { key: 'events', label: 'Events' },
    { key: 'persons', label: 'Figures' },
    { key: 'feed', label: 'Feed' },
  ]

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto" style={{ background: '#050810' }}>
      {/* Header */}
      <div className="sticky top-0 z-10 border-b border-chaldea-border px-6 py-3 flex items-center gap-4"
           style={{ background: '#050810ee', backdropFilter: 'blur(8px)' }}>
        <button
          onClick={onClose}
          className="text-chaldea-text hover:text-chaldea-cyan text-sm transition-colors"
        >
          &larr; Back
        </button>
        <h1 className="text-chaldea-cyan font-semibold text-sm tracking-wider">CHALDEAS</h1>
        <span className="text-chaldea-text text-xs">Deep Read Mode</span>
        <div className="flex-1" />
        <button
          onClick={onClose}
          className="px-3 py-1 rounded border border-chaldea-cyan/30 text-xs text-chaldea-cyan
                     hover:bg-chaldea-cyan/10 transition-colors"
        >
          Globe View
        </button>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-6">
        {/* Era filter */}
        <div className="flex gap-2 mb-3">
          <button
            onClick={() => setEraFilter(null)}
            className={`px-2 py-0.5 text-[10px] rounded border transition-colors ${
              !eraFilter
                ? 'border-chaldea-cyan text-chaldea-cyan bg-chaldea-cyan/10'
                : 'border-chaldea-border text-chaldea-text hover:text-chaldea-text-bright'
            }`}
          >
            All
          </button>
          {eras.map(era => (
            <button
              key={era}
              onClick={() => setEraFilter(era === eraFilter ? null : era)}
              className={`px-2 py-0.5 text-[10px] rounded border transition-colors ${
                era === eraFilter
                  ? 'border-chaldea-cyan text-chaldea-cyan bg-chaldea-cyan/10'
                  : 'border-chaldea-border text-chaldea-text hover:text-chaldea-text-bright'
              }`}
            >
              {era}
            </button>
          ))}
        </div>

        {/* Period selector */}
        <div className="flex gap-1.5 flex-wrap mb-6">
          {filteredPresets.map((p) => (
            <button
              key={p.year}
              onClick={() => handleSelectPeriod(p.year)}
              className={`px-2.5 py-1 text-xs rounded border transition-colors ${
                selectedPeriod === p.year
                  ? 'border-chaldea-cyan text-chaldea-cyan bg-chaldea-cyan/10'
                  : 'border-chaldea-border text-chaldea-text hover:text-chaldea-text-bright'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Period header */}
        {period && (
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-chaldea-text-bright">
              {period.headline || `${formatYear(period.period_start)} \u2013 ${formatYear(period.period_end)}`}
            </h2>
            {period.headline_ko && (
              <p className="text-sm text-chaldea-text mt-1">{period.headline_ko}</p>
            )}
          </div>
        )}

        {/* Tab bar */}
        <div className="flex gap-1 mb-6 border-b border-chaldea-border">
          {tabs.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-xs font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-chaldea-cyan text-chaldea-cyan'
                  : 'border-transparent text-chaldea-text hover:text-chaldea-text-bright'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === 'narrative' && period && (
          <div className="space-y-6">
            {period.narrative && (
              <p className="text-sm text-chaldea-text leading-relaxed">{period.narrative}</p>
            )}
            {period.defining_moment && (
              <p className="text-sm text-chaldea-orange italic border-l-2 border-chaldea-orange pl-3">
                {period.defining_moment}
              </p>
            )}

            {period.events.length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-chaldea-text-bright mb-2 uppercase tracking-wider">
                  Key Events
                </h3>
                <div className="space-y-2">
                  {period.events.slice(0, 5).map(evt => (
                    <button
                      key={evt.id}
                      onClick={() => goToGlobe(evt.id)}
                      className="w-full text-left p-3 rounded border border-chaldea-border
                                 hover:border-chaldea-cyan/30 transition-colors bg-chaldea-panel/30"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-chaldea-cyan text-[10px] w-16 text-right shrink-0">
                          {evt.date_display || formatYear(evt.date_start)}
                        </span>
                        <span className="text-sm text-chaldea-text-bright flex-1">{evt.title}</span>
                        {evt.importance_score && (
                          <span className="text-[10px] text-chaldea-gold">
                            {'*'.repeat(Math.min(5, Math.round(evt.importance_score)))}
                          </span>
                        )}
                      </div>
                      {evt.narrative && (
                        <p className="text-xs text-chaldea-text mt-1 ml-[72px] line-clamp-2">{evt.narrative}</p>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {period.persons.length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-chaldea-text-bright mb-2 uppercase tracking-wider">
                  Key Figures
                </h3>
                <div className="grid grid-cols-2 gap-2">
                  {period.persons.slice(0, 6).map(p => (
                    <button
                      key={p.id}
                      onClick={() => goToGlobe(undefined, p.id)}
                      className="text-left p-3 rounded border border-chaldea-border
                                 hover:border-chaldea-orange/30 transition-colors bg-chaldea-panel/30"
                    >
                      <div className="text-sm text-chaldea-text-bright">{p.name}</div>
                      {p.name_ko && <div className="text-[10px] text-chaldea-text">{p.name_ko}</div>}
                      <div className="text-[10px] text-chaldea-text mt-1">
                        {p.birth_year ? formatYear(p.birth_year) : '?'} - {p.death_year ? formatYear(p.death_year) : '?'}
                      </div>
                      {p.role && <div className="text-[10px] text-chaldea-orange mt-0.5">{p.role}</div>}
                      {p.significance && (
                        <p className="text-[10px] text-chaldea-text mt-1 line-clamp-2 italic">{p.significance}</p>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {period.regions.length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-chaldea-text-bright mb-2 uppercase tracking-wider">
                  Regional Breakdown
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  {period.regions.map((r) => (
                    <div key={r.region} className="p-3 rounded border border-chaldea-border bg-chaldea-panel/50">
                      <h4 className="text-xs text-chaldea-cyan font-medium">{r.region_name}</h4>
                      {r.headline && <p className="text-xs text-chaldea-text-bright mt-1">{r.headline}</p>}
                      {r.narrative && (
                        <p className="text-[11px] text-chaldea-text mt-1 line-clamp-4">{r.narrative}</p>
                      )}
                      <div className="text-[9px] text-chaldea-text mt-2">
                        {r.event_count} events / {r.person_count} figures
                      </div>
                      {r.quote && (
                        <blockquote className="mt-2 text-[10px] text-chaldea-gold italic border-l border-chaldea-gold pl-2">
                          &ldquo;{r.quote}&rdquo;
                          {r.quote_source && <span className="text-chaldea-text"> &mdash; {r.quote_source}</span>}
                        </blockquote>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'events' && (
          <div className="space-y-2">
            {periodEvents && periodEvents.length > 0 ? (
              periodEvents.map(evt => (
                <button
                  key={evt.id}
                  onClick={() => goToGlobe(evt.id)}
                  className="w-full text-left p-3 rounded border border-chaldea-border
                             hover:border-chaldea-cyan/30 transition-colors bg-chaldea-panel/30"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-chaldea-cyan/10 text-chaldea-cyan">
                      event
                    </span>
                    <span className="text-sm text-chaldea-text-bright flex-1">{evt.title}</span>
                    <span className="text-[10px] text-chaldea-text">
                      {evt.date_display || formatYear(evt.date_start)}
                    </span>
                  </div>
                  {evt.location_name && (
                    <div className="text-[10px] text-chaldea-text mt-1 ml-14">{evt.location_name}</div>
                  )}
                  {evt.description && (
                    <p className="text-xs text-chaldea-text mt-1 ml-14 line-clamp-2">{evt.description}</p>
                  )}
                </button>
              ))
            ) : (
              <p className="text-xs text-chaldea-text">No events for this period.</p>
            )}
          </div>
        )}

        {activeTab === 'persons' && (
          <div className="grid grid-cols-2 gap-2">
            {periodPersons && periodPersons.length > 0 ? (
              periodPersons.map(p => (
                <button
                  key={p.id}
                  onClick={() => goToGlobe(undefined, p.id)}
                  className="text-left p-3 rounded border border-chaldea-border
                             hover:border-chaldea-orange/30 transition-colors bg-chaldea-panel/30"
                >
                  <div className="text-sm text-chaldea-text-bright">{p.name}</div>
                  <div className="text-[10px] text-chaldea-text mt-0.5">
                    {p.birth_year ? formatYear(p.birth_year) : '?'} - {p.death_year ? formatYear(p.death_year) : '?'}
                  </div>
                  {p.role && <div className="text-[10px] text-chaldea-orange mt-0.5">{p.role}</div>}
                  {p.domain && <div className="text-[10px] text-chaldea-text">{p.domain}</div>}
                  {p.narrative && (
                    <p className="text-[10px] text-chaldea-text mt-1 line-clamp-3">{p.narrative}</p>
                  )}
                </button>
              ))
            ) : (
              <p className="text-xs text-chaldea-text col-span-2">No figures for this period.</p>
            )}
          </div>
        )}

        {activeTab === 'feed' && (
          <div className="space-y-2">
            {feedItems && feedItems.length > 0 ? (
              feedItems.map((item) => (
                <button
                  key={`${item.type}-${item.id}`}
                  onClick={() => {
                    if (item.type === 'event') goToGlobe(item.id)
                    else goToGlobe(undefined, item.id)
                  }}
                  className="w-full text-left p-3 rounded border border-chaldea-border
                             hover:border-chaldea-cyan/30 transition-colors bg-chaldea-panel/30"
                >
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                      item.type === 'event'
                        ? 'bg-chaldea-cyan/10 text-chaldea-cyan'
                        : 'bg-chaldea-orange/10 text-chaldea-orange'
                    }`}>
                      {item.type}
                    </span>
                    <span className="text-sm text-chaldea-text-bright flex-1">{item.title || item.name}</span>
                    {item.date_display && (
                      <span className="text-[10px] text-chaldea-text">{item.date_display}</span>
                    )}
                  </div>
                  {item.context && (
                    <div className="text-[10px] text-chaldea-gold mt-1 ml-14">{item.context}</div>
                  )}
                  {item.description && (
                    <p className="text-xs text-chaldea-text mt-1 ml-14 line-clamp-2">{item.description}</p>
                  )}
                  {item.participants && item.participants.length > 0 && (
                    <div className="text-[10px] text-chaldea-text mt-1 ml-14">
                      with {item.participants.slice(0, 3).join(', ')}
                      {item.participant_count && item.participant_count > 3 && ` +${item.participant_count - 3} more`}
                    </div>
                  )}
                </button>
              ))
            ) : (
              <p className="text-xs text-chaldea-text">Loading feed...</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
