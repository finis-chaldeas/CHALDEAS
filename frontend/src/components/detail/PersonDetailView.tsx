/**
 * PersonDetailView - FGO-style Person Detail with Timeline
 *
 * Shows a person's biography, timeline of events, and connected persons.
 */
import { useState, useMemo, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, personsApi, servantsApi } from '../../api/client'
import { StoryModal } from '../story'
import { ReportButton, SourceBadge } from '../common'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import { trackEvent, AnalyticsEvents } from '../../lib/analytics'
import type { Event, PersonSourceList } from '../../types'
import './EntityDetailView.css'

interface PersonName {
  id: number
  name: string
  name_ko?: string
  name_ja?: string
  language: string
  name_type: string
  is_primary: boolean
  valid_from?: number
  valid_until?: number
}

interface PersonInfo {
  id: number
  name: string
  name_ko?: string
  name_ja?: string
  birth_year?: number
  death_year?: number
  role?: string
  certainty?: string
  details?: {
    biography?: string
    biography_ko?: string
    biography_ja?: string
    biography_source?: string
    biography_source_url?: string
    image_url?: string
    wikipedia_url?: string
  }
  names?: PersonName[]
}

interface ChainEvent {
  id: number
  title: string
  year: number | null
}

interface ChainConnection {
  id: number
  event_a: ChainEvent
  event_b: ChainEvent
  direction: string
  type: string | null
  strength: number
}

interface PersonRelation {
  id: number
  name: string
  name_ko?: string
  birth_year?: number
  death_year?: number
  strength: number
  time_distance?: number
  relationship_type?: string
  is_bidirectional: number
}

interface Props {
  personId: number
  onClose: () => void
  onEventClick: (event: Event) => void
  onPersonClick: (personId: number) => void
}

export function PersonDetailView({ personId, onClose, onEventClick, onPersonClick }: Props) {
  const [isStoryOpen, setIsStoryOpen] = useState(false)
  const [wikiExpanded, setWikiExpanded] = useState(false)
  const { preferredLanguage } = useSettingsStore()

  // Track person view
  useEffect(() => {
    trackEvent(AnalyticsEvents.PERSON_VIEWED, { person_id: personId })
  }, [personId])

  // Fetch person details
  const { data: person, isLoading: personLoading } = useQuery<PersonInfo>({
    queryKey: ['person-detail', personId],
    queryFn: async () => {
      const res = await api.get(`/persons/${personId}`)
      return res.data
    },
  })

  // Fetch person chain (connections)
  const { data: chainData } = useQuery({
    queryKey: ['person-chain', personId],
    queryFn: async () => {
      const res = await api.get(`/chains/person/${personId}`)
      return res.data
    },
  })

  // Fetch related persons with strength
  const { data: relationsData } = useQuery<{ relations: PersonRelation[]; total: number }>({
    queryKey: ['person-relations', personId],
    queryFn: async () => {
      const res = await api.get(`/persons/${personId}/relations?limit=30&min_strength=0`)
      return res.data
    },
  })

  // Fetch key Wikidata properties
  const { data: propsData } = useQuery<{ person_id: number; properties: Array<{ property: string; label: string; values: string[] }> }>({
    queryKey: ['person-properties', personId],
    queryFn: async () => {
      const res = await api.get(`/persons/${personId}/properties`)
      return res.data
    },
    staleTime: 300000,
  })

  // Fetch FGO servant connection
  const { data: servantData } = useQuery<{ fgo_name: string; fgo_class?: string; rarity?: number } | null>({
    queryKey: ['person-servant', personId],
    queryFn: async () => {
      try {
        const res = await servantsApi.getByPerson(personId)
        const servants = res.data
        return Array.isArray(servants) && servants.length > 0 ? servants[0] : null
      } catch {
        return null
      }
    },
    staleTime: 300000,
  })

  // Fetch sources (books) mentioning this person
  const { data: sourcesData } = useQuery<PersonSourceList>({
    queryKey: ['person-sources', personId],
    queryFn: async () => {
      const res = await personsApi.getSources(personId, { limit: 10, include_contexts: true, max_contexts: 2 })
      return res.data
    },
  })

  // Fetch Wikipedia content from person_sources
  const { data: wikiData } = useQuery<{
    person_id: number
    has_wikipedia: boolean
    source_id?: number
    title?: string
    url?: string
    content_excerpt?: string
    full_length?: number
  }>({
    queryKey: ['person-wikipedia', personId],
    queryFn: async () => {
      const res = await api.get(`/persons/${personId}/wikipedia`)
      return res.data
    },
    staleTime: 300000,
  })

  // Extract unique events from chain, sorted by year
  const timelineEvents = useMemo(() => {
    if (!chainData?.connections) return []

    const eventsMap = new Map<number, ChainEvent>()
    for (const conn of chainData.connections as ChainConnection[]) {
      if (!eventsMap.has(conn.event_a.id)) {
        eventsMap.set(conn.event_a.id, conn.event_a)
      }
      if (!eventsMap.has(conn.event_b.id)) {
        eventsMap.set(conn.event_b.id, conn.event_b)
      }
    }

    return Array.from(eventsMap.values())
      .sort((a, b) => (a.year || 0) - (b.year || 0))
  }, [chainData])

  // Group relations by relationship type category
  const groupedRelations = useMemo(() => {
    if (!relationsData?.relations) return { family: [], spouse: [], academic: [], other: [] }

    const familyTypes = ['father', 'mother', 'child', 'sibling', 'parent', 'brother', 'sister', 'son', 'daughter', 'uncle', 'aunt', 'nephew', 'niece', 'grandparent', 'grandchild', 'cousin', 'half-sibling', 'stepparent', 'stepchild']
    const spouseTypes = ['spouse', 'partner', 'consort', 'wife', 'husband']
    const academicTypes = ['student_of', 'doctoral_advisor', 'influenced_by', 'teacher', 'mentor', 'pupil', 'disciple', 'master']

    const groups: { family: PersonRelation[]; spouse: PersonRelation[]; academic: PersonRelation[]; other: PersonRelation[] } = {
      family: [], spouse: [], academic: [], other: []
    }

    for (const rel of relationsData.relations) {
      const rt = rel.relationship_type?.toLowerCase() || ''
      if (spouseTypes.some(t => rt.includes(t))) {
        groups.spouse.push(rel)
      } else if (familyTypes.some(t => rt.includes(t))) {
        groups.family.push(rel)
      } else if (academicTypes.some(t => rt.includes(t))) {
        groups.academic.push(rel)
      } else {
        groups.other.push(rel)
      }
    }

    return groups
  }, [relationsData])

  // Flat list for stats count
  const relatedPersons = useMemo(() => {
    if (!relationsData?.relations) return []
    return relationsData.relations
  }, [relationsData])

  // Format strength for display
  const formatStrength = (strength: number): string => {
    if (strength >= 1000) return `${(strength / 1000).toFixed(1)}k`
    if (strength >= 100) return strength.toFixed(0)
    return strength.toFixed(1)
  }

  // Get strength level for styling
  const getStrengthLevel = (strength: number): string => {
    if (strength >= 100) return 'very-strong'
    if (strength >= 30) return 'strong'
    if (strength >= 10) return 'medium'
    return 'weak'
  }

  // Get relation type CSS class
  const getRelTypeClass = (type?: string): string => {
    if (!type) return 'other'
    const t = type.toLowerCase()
    const spouseTypes = ['spouse', 'partner', 'consort', 'wife', 'husband']
    const familyTypes = ['father', 'mother', 'child', 'sibling', 'parent', 'brother', 'sister', 'son', 'daughter', 'uncle', 'aunt', 'nephew', 'niece', 'grandparent', 'grandchild', 'cousin']
    const academicTypes = ['student_of', 'doctoral_advisor', 'influenced_by', 'teacher', 'mentor', 'pupil', 'disciple', 'master']
    if (spouseTypes.some(s => t.includes(s))) return 'spouse'
    if (familyTypes.some(s => t.includes(s))) return 'family'
    if (academicTypes.some(s => t.includes(s))) return 'academic'
    return 'other'
  }

  // Format relationship type for display
  const formatRelType = (type?: string): string => {
    if (!type) return ''
    return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  }

  const formatYear = (year: number | null | undefined) => {
    if (year === null || year === undefined) return '?'
    if (year < 0) return `${Math.abs(year)} BCE`
    return `${year} CE`
  }

  const handleEventClick = async (eventId: number) => {
    try {
      const res = await api.get(`/events/${eventId}`)
      if (res.data) {
        onEventClick(res.data)
      }
    } catch (err) {
      console.error('Failed to fetch event:', eventId, err)
    }
  }

  if (personLoading) {
    return (
      <div className="entity-detail-view">
        <div className="entity-loading">Loading...</div>
      </div>
    )
  }

  if (!person) {
    return (
      <div className="entity-detail-view">
        <div className="entity-error">Person not found</div>
      </div>
    )
  }

  // Extract biography from details
  const details = person.details
  const biographyObj = details ? {
    biography: details.biography,
    biography_ko: details.biography_ko,
    biography_ja: details.biography_ja,
  } : null

  const biography = biographyObj
    ? getLocalizedText(biographyObj as unknown as Record<string, unknown>, 'biography', preferredLanguage)
    : null

  return (
    <div className="entity-detail-view person-view">
      {/* Header */}
      <div className="entity-header">
        <button className="entity-close" onClick={onClose}>✕</button>
        <div className="entity-icon person">👤</div>
        <div className="entity-title-section">
          <h2 className="entity-name">{person.name}</h2>
          {person.name_ko && <div className="entity-name-alt">{person.name_ko}</div>}
          {servantData && (
            <div className="fgo-servant-badge">
              FGO Servant: {servantData.fgo_name}
              {servantData.fgo_class && ` (${servantData.fgo_class}`}
              {servantData.rarity && `, ${'★'.repeat(servantData.rarity)}`}
              {servantData.fgo_class && ')'}
            </div>
          )}
        </div>
      </div>

      {/* Life Span */}
      <div className="entity-lifespan">
        <div className="lifespan-dates">
          <span className="lifespan-birth">{formatYear(person.birth_year)}</span>
          <span className="lifespan-separator">—</span>
          <span className="lifespan-death">{formatYear(person.death_year)}</span>
        </div>
        {person.role && <div className="entity-role">{person.role}</div>}
      </div>

      {/* Stats */}
      <div className="entity-stats">
        <div className="stat-item">
          <span className="stat-value">{timelineEvents.length}</span>
          <span className="stat-label">Events</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{relatedPersons.length}</span>
          <span className="stat-label">Relations</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{chainData?.total_connections || 0}</span>
          <span className="stat-label">Links</span>
        </div>
      </div>

      {/* Story Button - always shown (multi-source story builder) */}
      <button
        className="entity-story-btn"
        onClick={() => setIsStoryOpen(true)}
      >
        <span className="story-btn-icon">🗺</span>
        <span className="story-btn-text">View Story</span>
        <span className="story-btn-arrow">→</span>
      </button>

      {/* Biography (from details) */}
      {biography && (
        <div className="entity-description">
          <p>{biography}</p>
          <div className="description-meta">
            {details && (
              <div className="description-source">
                <SourceBadge
                  source={details.biography_source}
                  sourceUrl={details.biography_source_url}
                />
              </div>
            )}
            {details?.wikipedia_url && (
              <a
                href={details.wikipedia_url}
                target="_blank"
                rel="noopener noreferrer"
                className="wikipedia-link"
              >
                <span className="wikipedia-icon">W</span>
                Wikipedia
              </a>
            )}
          </div>
        </div>
      )}
      {/* Wikipedia link when no biography */}
      {!biography && details?.wikipedia_url && (
        <div className="entity-description">
          <a
            href={details.wikipedia_url}
            target="_blank"
            rel="noopener noreferrer"
            className="wikipedia-link"
          >
            <span className="wikipedia-icon">W</span>
            Wikipedia
          </a>
        </div>
      )}

      {/* Wikipedia Source Content */}
      {wikiData?.has_wikipedia && wikiData.content_excerpt && (
        <div className="entity-section">
          <div className="section-header">
            <span className="section-icon">W</span>
            <span className="section-title">Wikipedia</span>
            {wikiData.full_length && (
              <span className="section-count">{Math.round(wikiData.full_length / 1000)}k chars</span>
            )}
          </div>
          <div className="wiki-content">
            <p className="wiki-excerpt">
              {wikiExpanded
                ? wikiData.content_excerpt
                : wikiData.content_excerpt.slice(0, 600) + (wikiData.content_excerpt.length > 600 ? '...' : '')}
            </p>
            {wikiData.content_excerpt.length > 600 && (
              <button
                className="wiki-expand-btn"
                onClick={() => setWikiExpanded(!wikiExpanded)}
              >
                {wikiExpanded ? 'Show less' : 'Read more'}
              </button>
            )}
            {wikiData.url && (
              <a
                href={wikiData.url}
                target="_blank"
                rel="noopener noreferrer"
                className="wikipedia-link"
              >
                <span className="wikipedia-icon">W</span>
                Full article on Wikipedia
              </a>
            )}
          </div>
        </div>
      )}

      {/* Also Known As (Names) */}
      {person.names && person.names.length > 0 && (
        <div className="entity-section">
          <div className="section-header">
            <span className="section-icon">🏷</span>
            <span className="section-title">Also Known As</span>
            <span className="section-count">{person.names.filter(n => !n.is_primary).length}</span>
          </div>
          <div className="names-list">
            {person.names
              .filter(n => !n.is_primary)
              .slice(0, 20)
              .map((n) => (
                <div key={n.id} className="name-item">
                  <div className="name-main">
                    <span className="name-text">{n.name}</span>
                    {(n.name_ko || n.name_ja) && (
                      <span className="name-localized">
                        {n.name_ko || n.name_ja}
                      </span>
                    )}
                  </div>
                  <div className="name-meta">
                    <span className={`name-type-badge ${n.name_type}`}>{n.name_type}</span>
                    <span className="name-lang">{n.language}</span>
                    {(n.valid_from || n.valid_until) && (
                      <span className="name-period">
                        {n.valid_from ? formatYear(n.valid_from) : '?'} ~ {n.valid_until ? formatYear(n.valid_until) : ''}
                      </span>
                    )}
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Facts (Wikidata Properties) */}
      {propsData && propsData.properties.length > 0 && (
        <div className="entity-section">
          <div className="section-header">
            <span className="section-icon">📋</span>
            <span className="section-title">Facts</span>
          </div>
          <div className="facts-grid">
            {propsData.properties.map((prop) => (
              <div key={prop.property} className="fact-item">
                <span className="fact-label">{prop.label}</span>
                <span className="fact-value">{prop.values.slice(0, 3).join(', ')}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Timeline */}
      <div className="entity-section">
        <div className="section-header">
          <span className="section-icon">📅</span>
          <span className="section-title">Timeline</span>
        </div>
        <div className="timeline-list">
          {timelineEvents.length > 0 ? (
            timelineEvents.map((event, index) => (
              <div
                key={event.id}
                className="timeline-item"
                onClick={() => handleEventClick(event.id)}
                style={{ animationDelay: `${index * 0.05}s` }}
              >
                <div className="timeline-dot" />
                <div className="timeline-year">{formatYear(event.year)}</div>
                <div className="timeline-title">{event.title}</div>
              </div>
            ))
          ) : (
            <div className="timeline-empty">No events found</div>
          )}
        </div>
      </div>

      {/* Related Persons with Strength - Grouped by Relationship Type */}
      {relatedPersons.length > 0 && (
        <div className="entity-section">
          <div className="section-header">
            <span className="section-icon">🔗</span>
            <span className="section-title">Related Figures</span>
            <span className="section-count">{relatedPersons.length}</span>
          </div>
          <div className="connected-list">
            {/* Family */}
            {groupedRelations.family.length > 0 && (
              <div className="relation-group">
                <div className="relation-group-label family">Family</div>
                {groupedRelations.family.map((p) => (
                  <div
                    key={p.id}
                    className={`connected-item person strength-${getStrengthLevel(p.strength)}`}
                    onClick={() => onPersonClick(p.id)}
                  >
                    <div className="connected-main">
                      <span className="connected-name">{p.name}</span>
                      {p.relationship_type && (
                        <span className={`rel-type-badge ${getRelTypeClass(p.relationship_type)}`}>
                          {formatRelType(p.relationship_type)}
                        </span>
                      )}
                    </div>
                    {p.strength > 0 && (
                      <div className="connected-strength">
                        <span className="strength-value">{formatStrength(p.strength)}</span>
                        <span className="strength-bar">
                          <span className="strength-fill" style={{ width: `${Math.min(100, (p.strength / 100) * 100)}%` }} />
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            {/* Spouse/Partner */}
            {groupedRelations.spouse.length > 0 && (
              <div className="relation-group">
                <div className="relation-group-label spouse">Spouse / Partner</div>
                {groupedRelations.spouse.map((p) => (
                  <div
                    key={p.id}
                    className={`connected-item person strength-${getStrengthLevel(p.strength)}`}
                    onClick={() => onPersonClick(p.id)}
                  >
                    <div className="connected-main">
                      <span className="connected-name">{p.name}</span>
                      {p.relationship_type && (
                        <span className={`rel-type-badge ${getRelTypeClass(p.relationship_type)}`}>
                          {formatRelType(p.relationship_type)}
                        </span>
                      )}
                    </div>
                    {p.strength > 0 && (
                      <div className="connected-strength">
                        <span className="strength-value">{formatStrength(p.strength)}</span>
                        <span className="strength-bar">
                          <span className="strength-fill" style={{ width: `${Math.min(100, (p.strength / 100) * 100)}%` }} />
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            {/* Academic */}
            {groupedRelations.academic.length > 0 && (
              <div className="relation-group">
                <div className="relation-group-label academic">Academic / Intellectual</div>
                {groupedRelations.academic.map((p) => (
                  <div
                    key={p.id}
                    className={`connected-item person strength-${getStrengthLevel(p.strength)}`}
                    onClick={() => onPersonClick(p.id)}
                  >
                    <div className="connected-main">
                      <span className="connected-name">{p.name}</span>
                      {p.relationship_type && (
                        <span className={`rel-type-badge ${getRelTypeClass(p.relationship_type)}`}>
                          {formatRelType(p.relationship_type)}
                        </span>
                      )}
                    </div>
                    {p.strength > 0 && (
                      <div className="connected-strength">
                        <span className="strength-value">{formatStrength(p.strength)}</span>
                        <span className="strength-bar">
                          <span className="strength-fill" style={{ width: `${Math.min(100, (p.strength / 100) * 100)}%` }} />
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            {/* Other */}
            {groupedRelations.other.length > 0 && (
              <div className="relation-group">
                {(groupedRelations.family.length > 0 || groupedRelations.spouse.length > 0 || groupedRelations.academic.length > 0) && (
                  <div className="relation-group-label other">Other</div>
                )}
                {groupedRelations.other.map((p) => (
                  <div
                    key={p.id}
                    className={`connected-item person strength-${getStrengthLevel(p.strength)}`}
                    onClick={() => onPersonClick(p.id)}
                  >
                    <div className="connected-main">
                      <span className="connected-name">{p.name}</span>
                      {p.relationship_type && (
                        <span className={`rel-type-badge ${getRelTypeClass(p.relationship_type)}`}>
                          {formatRelType(p.relationship_type)}
                        </span>
                      )}
                      {!p.relationship_type && p.time_distance && p.time_distance > 0 && (
                        <span className="connected-era historical">historical ref</span>
                      )}
                    </div>
                    {p.strength > 0 && (
                      <div className="connected-strength">
                        <span className="strength-value">{formatStrength(p.strength)}</span>
                        <span className="strength-bar">
                          <span className="strength-fill" style={{ width: `${Math.min(100, (p.strength / 100) * 100)}%` }} />
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Sources (Books) mentioning this person */}
      {sourcesData && sourcesData.sources.length > 0 && (
        <div className="entity-section">
          <div className="section-header">
            <span className="section-icon">📚</span>
            <span className="section-title">Mentioned in Books</span>
            <span className="section-count">{sourcesData.total}</span>
          </div>
          <div className="sources-list">
            {sourcesData.sources.map((source) => (
              <div key={source.id} className="source-item">
                <div className="source-header">
                  <span className="source-title">{source.title || source.name}</span>
                  <span className="source-mentions">{source.mention_count}x</span>
                </div>
                {source.author && (
                  <div className="source-author">by {source.author}</div>
                )}
                {source.mentions.length > 0 && (
                  <div className="source-contexts">
                    {source.mentions.slice(0, 2).map((mention, idx) => (
                      <div key={idx} className="mention-context">
                        <span className="mention-quote">"{mention.context_text?.slice(0, 150)}..."</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="entity-footer">
        <span className="entity-id">PERSON #{personId}</span>
        {person.certainty && (
          <span className={`entity-certainty ${person.certainty}`}>
            {person.certainty}
          </span>
        )}
        <ReportButton entityType="person" entityId={personId} />
      </div>

      {/* Story Modal */}
      <StoryModal
        isOpen={isStoryOpen}
        personId={personId}
        onClose={() => setIsStoryOpen(false)}
        onEventClick={(eventId) => {
          setIsStoryOpen(false)
          handleEventClick(eventId)
        }}
      />
    </div>
  )
}
