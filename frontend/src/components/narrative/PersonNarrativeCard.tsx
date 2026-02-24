import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { personsApi, servantsApi, historiesApi } from '../../api/client'
import type { Person, PersonNarrative, PersonRelation, PersonSource, PersonNameEntry, HistoryListItem } from '../../types'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import { ReportButton } from './ReportButton'

function formatYear(year: number | undefined): string {
  if (year === undefined || year === null) return ''
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

type PersonTab = 'story' | 'network' | 'sources'

// ─── Quick Facts ────────────────────────────────────────────

function PersonQuickFacts({ person }: { person: Person }) {
  const { preferredLanguage } = useSettingsStore()
  const facts: { label: string; value: string }[] = []

  if (person.birth_year) facts.push({ label: 'Born', value: formatYear(person.birth_year) })
  if (person.death_year) facts.push({ label: 'Died', value: formatYear(person.death_year) })
  if (person.details?.era) facts.push({ label: 'Era', value: person.details.era })
  if (person.birthplace) {
    const bpName = getLocalizedText(person.birthplace as unknown as Record<string, unknown>, 'name', preferredLanguage) || person.birthplace.name
    if (bpName) facts.push({ label: 'Birthplace', value: bpName })
  }
  if (person.deathplace) {
    const dpName = getLocalizedText(person.deathplace as unknown as Record<string, unknown>, 'name', preferredLanguage) || person.deathplace.name
    if (dpName) facts.push({ label: 'Deathplace', value: dpName })
  }
  if (person.wikidata_id) facts.push({ label: 'Wikidata', value: person.wikidata_id })

  if (facts.length === 0) return null

  return (
    <div>
      <div className="nc-section-header">Quick Facts</div>
      <div className="nc-facts-grid">
        {facts.map((fact) => (
          <div key={fact.label} className="nc-fact">
            <span className="nc-fact-label">{fact.label}:</span>
            {fact.label === 'Wikidata' ? (
              <a
                href={`https://www.wikidata.org/wiki/${fact.value}`}
                target="_blank"
                rel="noopener noreferrer"
                className="nc-fact-link"
              >
                {fact.value}
              </a>
            ) : (
              <span className="nc-fact-value">{fact.value}</span>
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
  const { preferredLanguage } = useSettingsStore()
  const { data: relations, isLoading } = useQuery({
    queryKey: ['person-relations', personId],
    queryFn: () => personsApi.getRelations(personId, { limit: 8 }).catch(() => ({ data: { relations: [] } })),
    select: (res) => (res.data?.relations ?? []) as PersonRelation[],
    retry: false,
  })

  if (isLoading) {
    return (
      <div className="nc-loading">
        <div className="nc-loading-bar" style={{ width: '100%' }} />
        <div className="nc-loading-bar" style={{ width: '100%' }} />
        <div className="nc-loading-bar" style={{ width: '100%' }} />
      </div>
    )
  }

  if (!relations || relations.length === 0) return null

  const maxStrength = Math.max(...relations.map((r) => r.strength), 1)

  return (
    <div>
      <div className="nc-section-header">Related Persons</div>
      <div className="nc-link-list">
        {relations.map((rel) => (
          <button key={rel.id} onClick={() => onPersonClick(rel.id)} className="nc-link-item"
            style={{ flexDirection: 'column', alignItems: 'stretch' }}>
            <div className="nc-relation-info" style={{ width: '100%', display: 'flex', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.375rem', minWidth: 0, flex: 1 }}>
                <span className="nc-relation-name">{getLocalizedText(rel as unknown as Record<string, unknown>, 'name', preferredLanguage) || rel.name}</span>
                {rel.relationship_type && rel.relationship_type !== 'related_to' && (
                  <span className="nc-relation-type">({rel.relationship_type})</span>
                )}
              </div>
              <span className="nc-relation-str">str {rel.strength}</span>
            </div>
            <div className="nc-bar-track">
              <div className="nc-bar-fill" style={{ width: `${(rel.strength / maxStrength) * 100}%` }} />
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
      <div className="nc-loading">
        <div className="nc-loading-bar" style={{ width: '100%', height: '32px' }} />
        <div className="nc-loading-bar" style={{ width: '100%', height: '32px' }} />
        <div className="nc-loading-bar" style={{ width: '100%', height: '32px' }} />
      </div>
    )
  }

  if (!sources || sources.length === 0) return null

  return (
    <div>
      {!expanded && <div className="nc-section-header">Sources ({sources.length})</div>}
      <div className="nc-sources-list">
        {sources.map((src) => (
          <button key={src.id} onClick={() => onSourceClick?.(src.id)} className="nc-source-link">
            <span className="nc-source-link-title">{src.title || src.name}</span>
            {src.mentions && src.mentions.length > 0 && src.mentions[0].context_text && (
              <span className="nc-source-context">"...{src.mentions[0].context_text}..."</span>
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
      <div className="nc-section-header">Names in Other Languages</div>
      <div className="nc-name-tags">
        {displayNames.map((n, i) => (
          <span key={i} className="nc-name-tag">
            <span className="nc-name-lang">{langLabel[n.lang] || n.lang}</span>
            <span className="nc-name-value">{n.name}</span>
          </span>
        ))}
      </div>
      {nameList.length > 4 && (
        <button onClick={() => setExpanded(!expanded)} className="nc-more-link">
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
    <div className="nc-section">
      <div className="nc-section-header" style={{ color: 'var(--chaldea-orange)' }}>FGO Servant</div>
      <div className="nc-fgo-servant">
        <div className="nc-fgo-name">{servant.fgo_name || servant.name}</div>
        {servant.class_name && (
          <div className="nc-fgo-class">
            Class: {servant.class_name} | Rarity: {'*'.repeat(servant.rarity || 0)}
          </div>
        )}
        {servant.noble_phantasm && (
          <div className="nc-fgo-np">NP: {servant.noble_phantasm}</div>
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
    <div className="nc-section">
      <div className="nc-section-header">Related Reading</div>
      <div className="nc-reading-list">
        {histories.map((h) => (
          <div key={h.id} className="nc-reading-item">
            <div className="nc-reading-title">{h.title}</div>
            {h.summary && <div className="nc-reading-summary">{h.summary}</div>}
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
  onRayshift?: (personId: number) => void
}

export function PersonNarrativeCard({ personId, onEventClick, onPersonClick, onSourceClick, onRayshift }: PersonNarrativeCardProps) {
  const { preferredLanguage } = useSettingsStore()
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
      <div className="nc-loading">
        <div className="nc-loading-bar nc-loading-bar--wide" />
        <div className="nc-loading-bar nc-loading-bar--mid" />
        <div className="nc-loading-bar nc-loading-bar--tall" />
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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div className="nc-person-header">
        <div className="nc-person-identity">
          {person.details?.image_url && (
            <img
              src={person.details.image_url}
              alt={person.name}
              className="nc-person-image"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
            />
          )}
          <div className="nc-person-info">
            <h2 className="nc-title">{getLocalizedText(person as unknown as Record<string, unknown>, 'name', preferredLanguage) || person.name}</h2>
            <div className="nc-spacetime">
              <span className="nc-year">
                {person.lifespan_display ||
                  `${formatYear(person.birth_year)} - ${formatYear(person.death_year)}`}
              </span>
              {displayRole && <span>{displayRole}</span>}
            </div>
            {biography && !hasNarrative && (
              <div className="nc-person-bio-preview">{biography}</div>
            )}
          </div>
        </div>

        {/* Tab bar */}
        <div className="nc-tab-bar">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`nc-tab ${activeTab === tab.key ? 'active' : ''}`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="nc-tab-content">
        {activeTab === 'story' && (
          <>
            {/* LLM Narrative */}
            {hasNarrative && (
              <div>
                <p className="nc-narrative">{narrative.narrative}</p>
                {narrative.significance && (
                  <p className="nc-significance">{narrative.significance}</p>
                )}
              </div>
            )}

            {!hasNarrative && biography && biography.length > 60 && (
              <p className="nc-description">{biography}</p>
            )}

            <PersonQuickFacts person={person} />

            {person.names && person.names.length > 0 && (
              <PersonNamesSection names={person.names} />
            )}

            {/* Life Events */}
            {flowData?.flow && flowData.flow.length > 0 && (
              <div>
                <div className="nc-section-header">Life Events</div>
                <div className="nc-link-list">
                  {flowData.flow
                    .slice(0, 8)
                    .map(
                      (evt: {
                        event_id: number
                        title: string
                        title_ko?: string
                        title_ja?: string
                        year?: number
                        location?: string
                      }) => (
                        <button
                          key={evt.event_id}
                          onClick={() => onEventClick(evt.event_id)}
                          className="nc-link-item"
                        >
                          <span className="nc-link-year">
                            {evt.year ? formatYear(evt.year) : ''}
                          </span>
                          <span className="nc-link-title">{getLocalizedText(evt as unknown as Record<string, unknown>, 'title', preferredLanguage) || evt.title}</span>
                          {evt.location && (
                            <span className="nc-link-meta">{evt.location}</span>
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
            <div className="nc-section nc-external-links">
              {person.details?.wikipedia_url && (
                <a href={person.details.wikipedia_url} target="_blank" rel="noopener noreferrer"
                  className="nc-external-link">
                  Wikipedia
                </a>
              )}
              {person.wikidata_id && (
                <a href={`https://www.wikidata.org/wiki/${person.wikidata_id}`} target="_blank"
                  rel="noopener noreferrer" className="nc-external-link">
                  Wikidata
                </a>
              )}
            </div>

            {/* FGO Servant */}
            <FGOServantSection personId={personId} />

            {/* Related Reading */}
            <PersonRelatedReading personId={personId} />

            {/* Rayshift: Life Journey */}
            {flowData?.flow && flowData.flow.length > 1 && onRayshift && (
              <div className="nc-section">
                <button onClick={() => onRayshift(personId)}
                  className="nc-rayshift-btn nc-rayshift-btn--life">
                  Rayshift: Follow Life Journey &rarr;
                </button>
              </div>
            )}

            {/* Report */}
            <div className="nc-section">
              <ReportButton entityType="person" entityId={personId} />
            </div>
          </>
        )}

        {activeTab === 'network' && (
          <>
            <PersonRelationsSection personId={personId} onPersonClick={onPersonClick} />
            {flowData?.flow && flowData.flow.length > 0 && (
              <div>
                <div className="nc-section-header">Events ({flowData.flow.length})</div>
                <div className="nc-link-list">
                  {flowData.flow.map(
                    (evt: { event_id: number; title: string; title_ko?: string; title_ja?: string; year?: number }) => (
                      <button key={evt.event_id} onClick={() => onEventClick(evt.event_id)}
                        className="nc-link-item">
                        <span className="nc-link-year">
                          {evt.year ? formatYear(evt.year) : ''}
                        </span>
                        <span className="nc-link-title">{getLocalizedText(evt as unknown as Record<string, unknown>, 'title', preferredLanguage) || evt.title}</span>
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
            <div className="nc-section-header">Source References</div>
            <PersonSourcesSection personId={personId} expanded onSourceClick={onSourceClick} />
          </div>
        )}
      </div>
    </div>
  )
}
