import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { personsApi, servantsApi, historiesApi } from '../../api/client'
import type { Person, PersonNarrative, PersonRelation, PersonSource, PersonNameEntry, HistoryListItem } from '../../types'
import { ReportButton } from './ReportButton'

function formatYear(year: number | undefined): string {
  if (year === undefined || year === null) return ''
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

type PersonTab = 'story' | 'network' | 'sources'

// ─── Quick Facts ────────────────────────────────────────────

function PersonQuickFacts({ person }: { person: Person }) {
  const facts: { label: string; value: string }[] = []

  if (person.birth_year) facts.push({ label: 'Born', value: formatYear(person.birth_year) })
  if (person.death_year) facts.push({ label: 'Died', value: formatYear(person.death_year) })
  if (person.details?.era) facts.push({ label: 'Era', value: person.details.era })
  if (person.birthplace?.name) facts.push({ label: 'Birthplace', value: person.birthplace.name })
  if (person.deathplace?.name) facts.push({ label: 'Deathplace', value: person.deathplace.name })
  if (person.wikidata_id) facts.push({ label: 'Wikidata', value: person.wikidata_id })

  if (facts.length === 0) return null

  return (
    <div>
      <h4 className="text-[10px] uppercase tracking-wider text-chaldea-text mb-1.5">
        Quick Facts
      </h4>
      <div className="grid grid-cols-1 gap-1">
        {facts.map((fact) => (
          <div key={fact.label} className="flex items-baseline gap-2 text-xs">
            <span className="text-chaldea-text shrink-0">{fact.label}:</span>
            {fact.label === 'Wikidata' ? (
              <a
                href={`https://www.wikidata.org/wiki/${fact.value}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-chaldea-cyan hover:underline truncate"
              >
                {fact.value}
              </a>
            ) : (
              <span className="text-chaldea-text-bright truncate">{fact.value}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Relations Section ──────────────────────────────────────

function PersonRelationsSection({
  personId,
  onPersonClick,
}: {
  personId: number
  onPersonClick: (id: number) => void
}) {
  const { data: relations, isLoading } = useQuery({
    queryKey: ['person-relations', personId],
    queryFn: () => personsApi.getRelations(personId, { limit: 8 }).catch(() => ({ data: { relations: [] } })),
    select: (res) => (res.data?.relations ?? []) as PersonRelation[],
    retry: false,
  })

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-1">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-6 bg-chaldea-border rounded" />
        ))}
      </div>
    )
  }

  if (!relations || relations.length === 0) return null

  const maxStrength = Math.max(...relations.map((r) => r.strength), 1)

  return (
    <div>
      <h4 className="text-[10px] uppercase tracking-wider text-chaldea-text mb-1.5">
        Related Persons
      </h4>
      <div className="space-y-1">
        {relations.map((rel) => (
          <button
            key={rel.id}
            onClick={() => onPersonClick(rel.id)}
            className="w-full text-left px-3 py-1.5 rounded text-xs border border-chaldea-border
                       hover:bg-chaldea-cyan/10 transition-colors group"
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-baseline gap-1.5 min-w-0 flex-1">
                <span className="text-chaldea-text-bright truncate group-hover:text-chaldea-cyan transition-colors">
                  {rel.name}
                </span>
                {rel.relationship_type && rel.relationship_type !== 'related_to' && (
                  <span className="text-chaldea-text text-[10px] shrink-0">
                    ({rel.relationship_type})
                  </span>
                )}
              </div>
              <span className="text-chaldea-text text-[10px] shrink-0">
                str {rel.strength}
              </span>
            </div>
            {/* Strength bar */}
            <div className="mt-1 h-[2px] bg-chaldea-border rounded-full overflow-hidden">
              <div
                className="h-full bg-chaldea-cyan rounded-full transition-all"
                style={{ width: `${(rel.strength / maxStrength) * 100}%` }}
              />
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

// ─── Sources Section ────────────────────────────────────────

function PersonSourcesSection({
  personId,
  expanded = false,
  onSourceClick,
}: {
  personId: number
  expanded?: boolean
  onSourceClick?: (sourceId: number) => void
}) {
  const limit = expanded ? 20 : 5
  const maxContexts = expanded ? 3 : 1

  const { data: sources, isLoading } = useQuery({
    queryKey: ['person-sources', personId, limit, maxContexts],
    queryFn: () =>
      personsApi.getSources(personId, {
        limit,
        include_contexts: true,
        max_contexts: maxContexts,
      }).catch(() => ({ data: { sources: [] } })),
    select: (res) => (res.data?.sources ?? []) as PersonSource[],
    retry: false,
  })

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-8 bg-chaldea-border rounded" />
        ))}
      </div>
    )
  }

  if (!sources || sources.length === 0) return null

  const typeBadgeColor: Record<string, string> = {
    book: 'text-chaldea-gold border-chaldea-gold',
    wikipedia: 'text-chaldea-cyan border-chaldea-cyan',
    wikidata: 'text-chaldea-green border-chaldea-green',
    article: 'text-chaldea-magenta border-chaldea-magenta',
  }

  return (
    <div>
      {!expanded && (
        <h4 className="text-[10px] uppercase tracking-wider text-chaldea-text mb-1.5">
          Sources
        </h4>
      )}
      <div className="space-y-1.5">
        {sources.map((src) => (
          <button
            key={src.id}
            onClick={() => onSourceClick?.(src.id)}
            className="w-full text-left px-3 py-2 rounded text-xs border border-chaldea-border
                       hover:bg-chaldea-cyan/10 transition-colors group"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-chaldea-text-bright truncate flex-1 group-hover:text-chaldea-cyan transition-colors">
                {src.title || src.name}
              </span>
              <span
                className={`shrink-0 px-1 py-0.5 rounded border text-[9px] uppercase ${
                  typeBadgeColor[src.type] || 'text-chaldea-text border-chaldea-border'
                }`}
              >
                {src.type}
              </span>
            </div>
            {src.author && (
              <p className="text-[10px] text-chaldea-text mt-0.5 truncate">
                by {src.author}
              </p>
            )}
            {/* Context snippet from text_mentions */}
            {src.mentions && src.mentions.length > 0 && src.mentions[0].context_text && (
              <p className="mt-1 text-[10px] text-chaldea-text leading-relaxed line-clamp-2 italic">
                "...{src.mentions[0].context_text}..."
              </p>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}

// ─── Names Section ──────────────────────────────────────────

function PersonNamesSection({ names }: { names: PersonNameEntry[] }) {
  const [expanded, setExpanded] = useState(false)

  if (!names || names.length === 0) return null

  const uniqueNames = new Map<string, { name: string; lang: string; type: string }>()
  for (const n of names) {
    const key = `${n.language}:${n.name}`
    if (!uniqueNames.has(key)) {
      uniqueNames.set(key, { name: n.name, lang: n.language, type: n.name_type })
    }
  }

  const nameList = Array.from(uniqueNames.values())
  const displayNames = expanded ? nameList : nameList.slice(0, 4)

  const langLabel: Record<string, string> = {
    en: 'EN', ko: 'KO', ja: 'JA', zh: 'ZH', ar: 'AR', grc: 'GRC',
    la: 'LA', el: 'EL', fa: 'FA', he: 'HE', ru: 'RU', fr: 'FR',
    de: 'DE', es: 'ES', tr: 'TR', sa: 'SA',
  }

  return (
    <div>
      <h4 className="text-[10px] uppercase tracking-wider text-chaldea-text mb-1.5">
        Names in Other Languages
      </h4>
      <div className="flex flex-wrap gap-1.5">
        {displayNames.map((n, i) => (
          <span
            key={i}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-chaldea-border text-[11px]"
          >
            <span className="text-chaldea-text text-[9px] uppercase">
              {langLabel[n.lang] || n.lang}
            </span>
            <span className="text-chaldea-text-bright">{n.name}</span>
          </span>
        ))}
      </div>
      {nameList.length > 4 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-1 text-[10px] text-chaldea-cyan hover:underline"
        >
          {expanded ? 'Show less' : `+${nameList.length - 4} more`}
        </button>
      )}
    </div>
  )
}

// ─── FGO Servant Section ────────────────────────────────────

function FGOServantSection({ personId }: { personId: number }) {
  const { data: servant } = useQuery({
    queryKey: ['servant-by-person', personId],
    queryFn: () => servantsApi.getByPerson(personId),
    select: (res) => res.data,
    retry: false,
  })

  if (!servant) return null

  return (
    <div className="border-t border-chaldea-border pt-3">
      <h4 className="text-[10px] uppercase tracking-wider text-chaldea-orange mb-1.5">
        FGO Servant
      </h4>
      <div className="p-2 rounded border border-chaldea-orange/20 bg-chaldea-orange/5">
        <p className="text-[11px] text-chaldea-text-bright font-medium">
          {servant.fgo_name || servant.name}
        </p>
        {servant.class_name && (
          <p className="text-[9px] text-chaldea-orange mt-0.5">
            Class: {servant.class_name} | Rarity: {'*'.repeat(servant.rarity || 0)}
          </p>
        )}
        {servant.noble_phantasm && (
          <p className="text-[9px] text-chaldea-text mt-0.5 italic">
            NP: {servant.noble_phantasm}
          </p>
        )}
      </div>
    </div>
  )
}

// ─── Person Related Reading ─────────────────────────────────

function PersonRelatedReading({ personId }: { personId: number }) {
  const { data: histories } = useQuery({
    queryKey: ['related-histories', 'person', personId],
    queryFn: () => historiesApi.list({ entity_type: 'person', entity_id: personId, limit: 3 }),
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

// ─── PersonNarrativeCard ────────────────────────────────────

interface PersonNarrativeCardProps {
  personId: number
  onEventClick: (eventId: number) => void
  onPersonClick: (personId: number) => void
  onSourceClick?: (sourceId: number) => void
}

export function PersonNarrativeCard({ personId, onEventClick, onPersonClick, onSourceClick }: PersonNarrativeCardProps) {
  const [activeTab, setActiveTab] = useState<PersonTab>('story')

  const { data: person, isLoading } = useQuery({
    queryKey: ['person', personId],
    queryFn: () => personsApi.get(personId),
    select: (res) => res.data as Person,
  })

  const { data: narrative } = useQuery({
    queryKey: ['person-narrative', personId],
    queryFn: () => personsApi.getNarrative(personId).catch(() => ({ data: { person_id: personId, has_narrative: false } })),
    select: (res) => res.data as PersonNarrative,
    retry: false,
  })

  const { data: flowData } = useQuery({
    queryKey: ['person-flow', personId],
    queryFn: () => personsApi.getFlow(personId).catch(() => ({ data: { flow: [] } })),
    select: (res) => res.data,
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

  if (!person) return null

  const hasNarrative = narrative?.has_narrative
  const displayRole =
    person.role && person.role !== 'occupation' && person.role !== 'None'
      ? person.role
      : null
  const biography = person.details?.biography

  const tabs: { key: PersonTab; label: string }[] = [
    { key: 'story', label: 'Story' },
    { key: 'network', label: 'Network' },
    { key: 'sources', label: 'Sources' },
  ]

  return (
    <div className="flex flex-col h-full">
      {/* Header: always visible */}
      <div className="p-5 pb-0 space-y-3">
        <div className="flex gap-3">
          {/* Image */}
          {person.details?.image_url && (
            <div className="shrink-0">
              <img
                src={person.details.image_url}
                alt={person.name}
                className="w-16 h-16 rounded-lg object-cover border border-chaldea-border"
                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
              />
            </div>
          )}

          {/* Name + dates */}
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-semibold text-chaldea-text-bright leading-tight">
              {person.name}
            </h2>
            {person.name_ko && (
              <p className="text-sm text-chaldea-text mt-0.5">{person.name_ko}</p>
            )}
            <div className="flex items-center gap-3 mt-1 text-xs text-chaldea-text">
              <span className="text-chaldea-cyan">
                {person.lifespan_display ||
                  `${formatYear(person.birth_year)} - ${formatYear(person.death_year)}`}
              </span>
              {displayRole && <span>{displayRole}</span>}
            </div>
            {biography && !hasNarrative && (
              <p className="text-[11px] text-chaldea-text mt-1 line-clamp-2">
                {biography}
              </p>
            )}
          </div>
        </div>

        {/* Tab bar */}
        <div className="flex border-b border-chaldea-border">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-xs font-medium transition-colors border-b-2 -mb-px ${
                activeTab === tab.key
                  ? 'text-chaldea-cyan border-chaldea-cyan'
                  : 'text-chaldea-text border-transparent hover:text-chaldea-text-bright hover:border-chaldea-border'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content: scrollable */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {activeTab === 'story' && (
          <>
            {/* LLM Narrative */}
            {hasNarrative && (
              <div className="space-y-3">
                <p className="text-sm text-chaldea-text-bright leading-relaxed">
                  {narrative.narrative}
                </p>
                {narrative.significance && (
                  <p className="text-xs text-chaldea-orange italic border-l-2 border-chaldea-orange pl-3">
                    {narrative.significance}
                  </p>
                )}
              </div>
            )}

            {!hasNarrative && biography && biography.length > 60 && (
              <p className="text-sm text-chaldea-text leading-relaxed">
                {biography}
              </p>
            )}

            <PersonQuickFacts person={person} />

            {person.names && person.names.length > 0 && (
              <PersonNamesSection names={person.names} />
            )}

            {/* Event flow */}
            {flowData?.flow && flowData.flow.length > 0 && (
              <div>
                <h4 className="text-[10px] uppercase tracking-wider text-chaldea-text mb-1.5">
                  Life Events
                </h4>
                <div className="space-y-1">
                  {flowData.flow
                    .slice(0, 8)
                    .map(
                      (evt: {
                        event_id: number
                        title: string
                        year?: number
                        location?: string
                      }) => (
                        <button
                          key={evt.event_id}
                          onClick={() => onEventClick(evt.event_id)}
                          className="w-full text-left px-3 py-1.5 rounded text-xs border border-chaldea-border
                                     hover:bg-chaldea-cyan/10 transition-colors flex items-center gap-2"
                        >
                          <span className="text-chaldea-cyan text-[10px] w-14 text-right shrink-0">
                            {evt.year ? formatYear(evt.year) : ''}
                          </span>
                          <span className="text-chaldea-text-bright flex-1 truncate">
                            {evt.title}
                          </span>
                          {evt.location && (
                            <span className="text-chaldea-text text-[10px] truncate max-w-[80px]">
                              {evt.location}
                            </span>
                          )}
                        </button>
                      )
                    )}
                </div>
              </div>
            )}

            <PersonRelationsSection personId={personId} onPersonClick={onPersonClick} />
            <PersonSourcesSection personId={personId} onSourceClick={onSourceClick} />

            {/* External links */}
            <div className="flex items-center gap-4 border-t border-chaldea-border pt-3">
              {person.details?.wikipedia_url && (
                <a
                  href={person.details.wikipedia_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-chaldea-cyan hover:underline"
                >
                  Wikipedia
                </a>
              )}
              {person.wikidata_id && (
                <a
                  href={`https://www.wikidata.org/wiki/${person.wikidata_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-chaldea-cyan hover:underline"
                >
                  Wikidata
                </a>
              )}
            </div>

            {/* FGO Servant */}
            <FGOServantSection personId={personId} />

            {/* Related Reading (Histories) */}
            <PersonRelatedReading personId={personId} />

            {/* Rayshift: Life Journey */}
            {flowData?.flow && flowData.flow.length > 1 && (
              <div className="border-t border-chaldea-border pt-3">
                <button
                  className="text-[10px] px-3 py-1.5 rounded border border-chaldea-gold/30
                             text-chaldea-gold hover:bg-chaldea-gold/10 transition-colors"
                >
                  Follow Life Journey &rarr;
                </button>
              </div>
            )}

            {/* Report */}
            <div className="border-t border-chaldea-border pt-3">
              <ReportButton entityType="person" entityId={personId} />
            </div>
          </>
        )}

        {activeTab === 'network' && (
          <>
            <PersonRelationsSection personId={personId} onPersonClick={onPersonClick} />
            {flowData?.flow && flowData.flow.length > 0 && (
              <div>
                <h4 className="text-[10px] uppercase tracking-wider text-chaldea-text mb-1.5">
                  Events ({flowData.flow.length})
                </h4>
                <div className="space-y-1">
                  {flowData.flow.map(
                    (evt: { event_id: number; title: string; year?: number }) => (
                      <button
                        key={evt.event_id}
                        onClick={() => onEventClick(evt.event_id)}
                        className="w-full text-left px-3 py-1.5 rounded text-xs border border-chaldea-border
                                   hover:bg-chaldea-cyan/10 transition-colors flex items-center gap-2"
                      >
                        <span className="text-chaldea-cyan text-[10px] w-14 text-right shrink-0">
                          {evt.year ? formatYear(evt.year) : ''}
                        </span>
                        <span className="text-chaldea-text-bright flex-1 truncate">
                          {evt.title}
                        </span>
                      </button>
                    )
                  )}
                </div>
              </div>
            )}
          </>
        )}

        {activeTab === 'sources' && (
          <div>
            <h4 className="text-[10px] uppercase tracking-wider text-chaldea-text mb-3">
              Source References
            </h4>
            <PersonSourcesSection personId={personId} expanded onSourceClick={onSourceClick} />
          </div>
        )}
      </div>
    </div>
  )
}
