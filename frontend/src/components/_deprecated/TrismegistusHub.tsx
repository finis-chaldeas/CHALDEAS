/**
 * TrismegistusHub - 5-section curated history content hub
 *
 * Sections:
 * 1. Guided Tours - SHEBA episodes as readable text
 * 2. Person Stories - Person chronological flow
 * 3. Domain Stories - Domain-based history exploration
 * 4. Era Narratives - Period narratives by era
 * 5. FGO Archive - Existing Singularity/Lostbelt/Servants
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { personsApi, timelineApi, api } from '../../api/client'
import { SHEBA_EPISODES, type ShebaEpisode, type TourStep } from '../../data/shebaEpisodes'
import './TrismegistusHub.css'

type Section = 'hub' | 'tours' | 'tour-detail' | 'persons' | 'person-detail' | 'domains' | 'eras' | 'fgo'

interface TrismegistusHubProps {
  onClose: () => void
  onPersonClick?: (personId: number) => void
  onEventClick?: (eventId: number) => void
  onFlyToLocation?: (lat: number, lng: number) => void
  onSetCurrentYear?: (year: number) => void
  onStartTour?: (episode: ShebaEpisode) => void
  onOpenShowcaseContent?: () => void
}

interface PersonFlowEvent {
  id: number
  title: string
  date_start: number
  date_end?: number
  date_display?: string
  importance?: number
  latitude?: number
  longitude?: number
}

interface PersonFlowData {
  person: {
    id: number
    name: string
    name_ko?: string
    birth_year?: number
    death_year?: number
    role?: string
    domain?: string
  }
  events: PersonFlowEvent[]
}

// Featured persons for Person Stories (curated list)
const FEATURED_PERSONS = [
  { id: 3, name: 'Alexander the Great', era: 'Classical' },
  { id: 5, name: 'Julius Caesar', era: 'Classical' },
  { id: 1, name: 'Napoleon Bonaparte', era: 'Modern' },
  { id: 12, name: 'Socrates', era: 'Classical' },
  { id: 7, name: 'Cleopatra VII', era: 'Classical' },
  { id: 15, name: 'Genghis Khan', era: 'Medieval' },
  { id: 9, name: 'Leonardo da Vinci', era: 'Early Modern' },
  { id: 20, name: 'Galileo Galilei', era: 'Early Modern' },
]

// Domain definitions (same as DomainTimelineModal)
const DOMAINS = [
  { key: 'science', label: 'Science', icon: '\uD83D\uDD2C', color: '#4fc3f7' },
  { key: 'philosophy', label: 'Philosophy', icon: '\uD83E\uDDD0', color: '#ce93d8' },
  { key: 'literature', label: 'Literature', icon: '\uD83D\uDCDA', color: '#a5d6a7' },
  { key: 'military', label: 'Military', icon: '\u2694\uFE0F', color: '#ef5350' },
  { key: 'statecraft', label: 'Statecraft', icon: '\uD83D\uDC51', color: '#ffd54f' },
  { key: 'visual_arts', label: 'Visual Arts', icon: '\uD83C\uDFA8', color: '#ff8a65' },
  { key: 'music', label: 'Music', icon: '\uD83C\uDFB5', color: '#f48fb1' },
  { key: 'religion', label: 'Religion', icon: '\u2721', color: '#fff176' },
]

const ERA_DEFS = [
  { id: 'ancient', name: 'Ancient World', start: -3500, end: -500 },
  { id: 'classical', name: 'Classical Era', start: -500, end: 500 },
  { id: 'medieval', name: 'Medieval Period', start: 500, end: 1500 },
  { id: 'early-modern', name: 'Early Modern', start: 1500, end: 1800 },
  { id: 'modern', name: 'Modern Era', start: 1800, end: 1945 },
  { id: 'contemporary', name: 'Contemporary', start: 1945, end: 2030 },
]

function formatYear(year: number | null | undefined): string {
  if (year == null) return '?'
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

export function TrismegistusHub({
  onClose,
  onPersonClick,
  onFlyToLocation,
  onSetCurrentYear,
  onStartTour,
  onOpenShowcaseContent,
}: TrismegistusHubProps) {
  const [section, setSection] = useState<Section>('hub')
  const [selectedEpisode, setSelectedEpisode] = useState<ShebaEpisode | null>(null)
  const [selectedPersonId, setSelectedPersonId] = useState<number | null>(null)

  const goBack = () => {
    if (section === 'tour-detail') setSection('tours')
    else if (section === 'person-detail') setSection('persons')
    else setSection('hub')
  }

  return (
    <div className="trismegistus-overlay" onClick={onClose}>
      <div className="trismegistus-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="trismegistus-header">
          <div className="trismegistus-title-row">
            {section !== 'hub' && (
              <button className="trismegistus-back" onClick={goBack}>
                {'\u2190'}
              </button>
            )}
            <h2 className="trismegistus-title">
              {section === 'hub' && 'TRISMEGISTUS'}
              {section === 'tours' && 'Guided Tours'}
              {section === 'tour-detail' && selectedEpisode?.title}
              {section === 'persons' && 'Person Stories'}
              {section === 'person-detail' && 'Person Story'}
              {section === 'domains' && 'Domain Stories'}
              {section === 'eras' && 'Era Narratives'}
              {section === 'fgo' && 'FGO Archive'}
            </h2>
            <button className="trismegistus-close" onClick={onClose}>
              {'\u2715'}
            </button>
          </div>
          {section === 'hub' && (
            <p className="trismegistus-subtitle">
              Curated history archive. Read, explore, and discover.
            </p>
          )}
        </div>

        {/* Content */}
        <div className="trismegistus-content">
          {section === 'hub' && (
            <HubGrid
              onSelectSection={setSection}
              onOpenFgo={onOpenShowcaseContent}
            />
          )}

          {section === 'tours' && (
            <ToursList
              onSelectEpisode={(ep) => {
                setSelectedEpisode(ep)
                setSection('tour-detail')
              }}
            />
          )}

          {section === 'tour-detail' && selectedEpisode && (
            <TourDetail
              episode={selectedEpisode}
              onFlyToLocation={onFlyToLocation}
              onSetCurrentYear={onSetCurrentYear}
              onStartTour={onStartTour}
            />
          )}

          {section === 'persons' && (
            <PersonsList
              onSelectPerson={(id) => {
                setSelectedPersonId(id)
                setSection('person-detail')
              }}
            />
          )}

          {section === 'person-detail' && selectedPersonId && (
            <PersonStory
              personId={selectedPersonId}
              onPersonClick={onPersonClick}
              onFlyToLocation={onFlyToLocation}
              onSetCurrentYear={onSetCurrentYear}
            />
          )}

          {section === 'domains' && (
            <DomainsList onPersonClick={onPersonClick} />
          )}

          {section === 'eras' && (
            <ErasList />
          )}
        </div>
      </div>
    </div>
  )
}


/** Main hub grid - 5 sections */
function HubGrid({
  onSelectSection,
  onOpenFgo,
}: {
  onSelectSection: (section: Section) => void
  onOpenFgo?: () => void
}) {
  const episodesWithTours = SHEBA_EPISODES.filter(e => e.tourSteps && e.tourSteps.length > 0)

  return (
    <div className="hub-grid">
      <button className="hub-card" onClick={() => onSelectSection('tours')}>
        <span className="hub-card-icon">{'\uD83D\uDCCD'}</span>
        <span className="hub-card-title">Guided Tours</span>
        <span className="hub-card-desc">
          {episodesWithTours.length} curated historical journeys with step-by-step narration
        </span>
      </button>

      <button className="hub-card" onClick={() => onSelectSection('persons')}>
        <span className="hub-card-icon">{'\uD83D\uDC64'}</span>
        <span className="hub-card-title">Person Stories</span>
        <span className="hub-card-desc">
          Follow the life and events of history's key figures
        </span>
      </button>

      <button className="hub-card" onClick={() => onSelectSection('domains')}>
        <span className="hub-card-icon">{'\uD83D\uDD2C'}</span>
        <span className="hub-card-title">Domain Stories</span>
        <span className="hub-card-desc">
          Science, philosophy, literature, military history by field
        </span>
      </button>

      <button className="hub-card" onClick={() => onSelectSection('eras')}>
        <span className="hub-card-icon">{'\u231B'}</span>
        <span className="hub-card-title">Era Narratives</span>
        <span className="hub-card-desc">
          AI-generated summaries for each 50-year period in history
        </span>
      </button>

      <button
        className="hub-card hub-card-fgo"
        onClick={() => {
          if (onOpenFgo) onOpenFgo()
        }}
      >
        <span className="hub-card-icon">{'\u2726'}</span>
        <span className="hub-card-title">FGO Archive</span>
        <span className="hub-card-desc">
          Singularities, Lostbelts, and Servant profiles
        </span>
      </button>
    </div>
  )
}


/** Section 1: Guided Tours list */
function ToursList({
  onSelectEpisode,
}: {
  onSelectEpisode: (episode: ShebaEpisode) => void
}) {
  const episodesWithTours = SHEBA_EPISODES.filter(e => e.tourSteps && e.tourSteps.length > 0)
  const episodesWithout = SHEBA_EPISODES.filter(e => !e.tourSteps || e.tourSteps.length === 0)

  return (
    <div className="tours-list">
      <div className="tours-section-label">Full guided tours</div>
      {episodesWithTours.map(ep => (
        <button
          key={ep.id}
          className="tour-card"
          onClick={() => onSelectEpisode(ep)}
        >
          <div className="tour-card-title">{ep.title}</div>
          <div className="tour-card-meta">
            {formatYear(ep.dateRange.start)}
            {ep.dateRange.end !== ep.dateRange.start && ` ~ ${formatYear(ep.dateRange.end)}`}
            {' | '}{ep.region}
            {' | '}{ep.tourSteps?.length} steps
          </div>
          <div className="tour-card-desc">{ep.description}</div>
        </button>
      ))}

      {episodesWithout.length > 0 && (
        <>
          <div className="tours-section-label" style={{ marginTop: '1rem' }}>
            Quick observations (no guided tour yet)
          </div>
          {episodesWithout.map(ep => (
            <div key={ep.id} className="tour-card tour-card-disabled">
              <div className="tour-card-title">{ep.title}</div>
              <div className="tour-card-meta">
                {formatYear(ep.dateRange.start)} | {ep.region}
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  )
}


/** Section 1 detail: Tour step-by-step */
function TourDetail({
  episode,
  onFlyToLocation,
  onSetCurrentYear,
  onStartTour,
}: {
  episode: ShebaEpisode
  onFlyToLocation?: (lat: number, lng: number) => void
  onSetCurrentYear?: (year: number) => void
  onStartTour?: (episode: ShebaEpisode) => void
}) {
  const steps = episode.tourSteps || []

  const handleObserveStep = (step: TourStep) => {
    onFlyToLocation?.(step.latitude, step.longitude)
    onSetCurrentYear?.(step.year)
  }

  return (
    <div className="tour-detail">
      <div className="tour-detail-header">
        <div className="tour-detail-meta">
          {formatYear(episode.dateRange.start)}
          {episode.dateRange.end !== episode.dateRange.start && ` ~ ${formatYear(episode.dateRange.end)}`}
          {' | '}{episode.region}
        </div>
        <p className="tour-detail-desc">{episode.description}</p>
      </div>

      <div className="tour-steps">
        {steps.map((step, i) => (
          <div key={i} className="tour-step">
            <div className="tour-step-marker">
              <span className="tour-step-dot" />
              {i < steps.length - 1 && <span className="tour-step-line" />}
            </div>
            <div className="tour-step-content">
              <div className="tour-step-year">{formatYear(step.year)}</div>
              <div className="tour-step-title">{step.title}</div>
              <p className="tour-step-desc">{step.description}</p>
              <button
                className="tour-step-observe"
                onClick={() => handleObserveStep(step)}
              >
                {'\uD83C\uDF0D'} Observe on Globe
              </button>
            </div>
          </div>
        ))}
      </div>

      {onStartTour && (
        <div className="tour-detail-footer">
          <button
            className="tour-start-btn"
            onClick={() => onStartTour(episode)}
          >
            {'\u25B6'} Start Guided Tour on Globe
          </button>
        </div>
      )}
    </div>
  )
}


/** Section 2: Person Stories list */
function PersonsList({
  onSelectPerson,
}: {
  onSelectPerson: (personId: number) => void
}) {
  // Fetch top persons by importance
  const { data: topPersons } = useQuery({
    queryKey: ['trismegistus-top-persons'],
    queryFn: () => personsApi.list({
      sort_by: 'importance',
      limit: 30,
    }),
    select: (res) => (res.data?.items || []) as Array<{
      id: number
      name: string
      name_ko?: string
      birth_year?: number
      death_year?: number
      role?: string
      domain?: string
    }>,
    staleTime: 5 * 60 * 1000,
  })

  const persons = topPersons || FEATURED_PERSONS

  return (
    <div className="persons-list">
      <div className="tours-section-label">Top historical figures by importance</div>
      {persons.map((p) => (
        <button
          key={p.id}
          className="person-story-card"
          onClick={() => onSelectPerson(p.id)}
        >
          <div className="person-story-name">{p.name}</div>
          <div className="person-story-meta">
            {'birth_year' in p && p.birth_year != null && formatYear(p.birth_year)}
            {'death_year' in p && p.death_year != null && ` ~ ${formatYear(p.death_year)}`}
            {'role' in p && p.role && ` | ${p.role}`}
            {'domain' in p && p.domain && (
              <span className="person-story-domain">{p.domain}</span>
            )}
          </div>
        </button>
      ))}
    </div>
  )
}


/** Section 2 detail: Person flow/story */
function PersonStory({
  personId,
  onPersonClick,
  onFlyToLocation,
  onSetCurrentYear,
}: {
  personId: number
  onPersonClick?: (personId: number) => void
  onFlyToLocation?: (lat: number, lng: number) => void
  onSetCurrentYear?: (year: number) => void
}) {
  const { data: flowData, isLoading } = useQuery({
    queryKey: ['person-flow', personId],
    queryFn: () => personsApi.getFlow(personId),
    select: (res) => res.data as PersonFlowData,
    staleTime: 5 * 60 * 1000,
  })

  // Also fetch related persons
  const { data: relatedData } = useQuery({
    queryKey: ['person-relations', personId],
    queryFn: () => api.get(`/persons/${personId}/relations`),
    select: (res) => (res.data?.items || res.data || []) as Array<{
      id: number
      name: string
      relationship_type?: string
    }>,
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) return <div className="trismegistus-loading">Loading story...</div>
  if (!flowData) return <div className="trismegistus-empty">No data available.</div>

  const { person, events } = flowData
  const related = relatedData || []

  const handleEventObserve = (event: PersonFlowEvent) => {
    if (event.latitude != null && event.longitude != null) {
      onFlyToLocation?.(event.latitude, event.longitude)
    }
    onSetCurrentYear?.(event.date_start)
  }

  return (
    <div className="person-story">
      <div className="person-story-header">
        <h3 className="person-story-title">{person.name}</h3>
        {person.name_ko && <div className="person-story-name-ko">{person.name_ko}</div>}
        <div className="person-story-lifespan">
          {formatYear(person.birth_year)} ~ {formatYear(person.death_year)}
          {person.role && ` | ${person.role}`}
        </div>
      </div>

      {/* Event flow timeline */}
      <div className="person-flow">
        {events.length === 0 && (
          <div className="trismegistus-empty">No events recorded for this person.</div>
        )}
        {events.map((event, i) => (
          <div key={event.id} className="person-flow-entry">
            <div className="person-flow-marker">
              <span className="person-flow-dot" />
              {i < events.length - 1 && <span className="person-flow-line" />}
            </div>
            <div className="person-flow-content">
              <button
                className="person-flow-btn"
                onClick={() => handleEventObserve(event)}
              >
                <span className="person-flow-year">
                  {event.date_display || formatYear(event.date_start)}
                </span>
                <span className="person-flow-title">{event.title}</span>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Related persons */}
      {related.length > 0 && (
        <div className="person-story-related">
          <div className="tours-section-label">Related Figures</div>
          <div className="person-related-chips">
            {related.slice(0, 10).map(r => (
              <button
                key={r.id}
                className="person-related-chip"
                onClick={() => onPersonClick?.(r.id)}
              >
                {r.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}


/** Section 3: Domain Stories - links to DomainTimeline content */
function DomainsList({
  onPersonClick,
}: {
  onPersonClick?: (personId: number) => void
}) {
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null)

  const { data: persons } = useQuery({
    queryKey: ['domain-top', selectedDomain],
    queryFn: () => personsApi.list({
      domain: selectedDomain,
      sort_by: 'importance',
      limit: 15,
    }),
    select: (res) => (res.data?.items || []) as Array<{
      id: number
      name: string
      birth_year?: number
      death_year?: number
      role?: string
    }>,
    enabled: !!selectedDomain,
    staleTime: 5 * 60 * 1000,
  })

  if (!selectedDomain) {
    return (
      <div className="domains-grid">
        {DOMAINS.map(d => (
          <button
            key={d.key}
            className="domain-card"
            onClick={() => setSelectedDomain(d.key)}
            style={{ '--domain-color': d.color } as React.CSSProperties}
          >
            <span className="domain-card-icon">{d.icon}</span>
            <span className="domain-card-label">{d.label}</span>
          </button>
        ))}
      </div>
    )
  }

  const domainInfo = DOMAINS.find(d => d.key === selectedDomain)

  return (
    <div className="domain-detail">
      <button className="trismegistus-section-back" onClick={() => setSelectedDomain(null)}>
        {'\u2190'} All domains
      </button>
      <h3 className="domain-detail-title">
        {domainInfo?.icon} History of {domainInfo?.label}
      </h3>
      <div className="domain-persons-list">
        {persons?.map(p => (
          <button
            key={p.id}
            className="person-story-card"
            onClick={() => onPersonClick?.(p.id)}
          >
            <div className="person-story-name">{p.name}</div>
            <div className="person-story-meta">
              {p.birth_year != null && formatYear(p.birth_year)}
              {p.death_year != null && ` ~ ${formatYear(p.death_year)}`}
              {p.role && ` | ${p.role}`}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}


/** Section 4: Era Narratives - period narratives by era */
function ErasList() {
  const [selectedEra, setSelectedEra] = useState<string | null>(null)

  const era = ERA_DEFS.find(e => e.id === selectedEra)

  const { data: periods } = useQuery({
    queryKey: ['era-periods', selectedEra],
    queryFn: () => timelineApi.listPeriods({ era_id: selectedEra!, limit: 50 }),
    select: (res) => (res.data?.items || []) as Array<{
      period_start: number
      period_end: number
      headline?: string
      has_narrative: boolean
      event_count: number
      person_count: number
    }>,
    enabled: !!selectedEra,
    staleTime: 5 * 60 * 1000,
  })

  const [selectedPeriod, setSelectedPeriod] = useState<number | null>(null)

  const { data: periodDetail } = useQuery({
    queryKey: ['period-narrative', selectedPeriod],
    queryFn: () => timelineApi.getPeriodDetail(selectedPeriod!),
    select: (res) => res.data as {
      headline?: string
      narrative?: string
      defining_moment?: string
      regions?: Array<{
        region: string
        region_name: string
        headline?: string
        narrative?: string
      }>
    },
    enabled: selectedPeriod != null,
    staleTime: 5 * 60 * 1000,
  })

  if (!selectedEra) {
    return (
      <div className="eras-grid">
        {ERA_DEFS.map(e => (
          <button
            key={e.id}
            className="era-card"
            onClick={() => setSelectedEra(e.id)}
          >
            <span className="era-card-name">{e.name}</span>
            <span className="era-card-range">
              {formatYear(e.start)} ~ {formatYear(e.end)}
            </span>
          </button>
        ))}
      </div>
    )
  }

  if (selectedPeriod != null && periodDetail) {
    return (
      <div className="era-narrative-detail">
        <button className="trismegistus-section-back" onClick={() => setSelectedPeriod(null)}>
          {'\u2190'} {era?.name}
        </button>
        <h3 className="era-narrative-title">
          {formatYear(selectedPeriod)} ~ {formatYear(selectedPeriod + 49)}
        </h3>
        {periodDetail.headline && (
          <h4 className="era-narrative-headline">{periodDetail.headline}</h4>
        )}
        {periodDetail.narrative ? (
          <div className="era-narrative-text">{periodDetail.narrative}</div>
        ) : (
          <div className="trismegistus-empty">No narrative available for this period yet.</div>
        )}
        {periodDetail.defining_moment && (
          <div className="era-narrative-moment">
            <strong>Defining Moment:</strong> {periodDetail.defining_moment}
          </div>
        )}
        {periodDetail.regions && periodDetail.regions.length > 0 && (
          <div className="era-narrative-regions">
            <div className="tours-section-label">By Region</div>
            {periodDetail.regions.map(r => (
              <div key={r.region} className="era-region-item">
                <div className="era-region-name">{r.region_name}</div>
                {r.headline && <div className="era-region-headline">{r.headline}</div>}
                {r.narrative && <p className="era-region-narrative">{r.narrative}</p>}
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="era-periods-list">
      <button className="trismegistus-section-back" onClick={() => setSelectedEra(null)}>
        {'\u2190'} All eras
      </button>
      <h3 className="domain-detail-title">{era?.name}</h3>
      {periods?.map(p => (
        <button
          key={p.period_start}
          className={`era-period-card ${p.has_narrative ? 'has-narrative' : ''}`}
          onClick={() => setSelectedPeriod(p.period_start)}
        >
          <div className="era-period-range">
            {formatYear(p.period_start)} ~ {formatYear(p.period_end)}
          </div>
          {p.headline && (
            <div className="era-period-headline">{p.headline}</div>
          )}
          <div className="era-period-meta">
            {p.event_count > 0 && <span>{p.event_count} events</span>}
            {p.person_count > 0 && <span>{p.person_count} figures</span>}
            {p.has_narrative && <span className="era-narrative-badge">AI</span>}
          </div>
        </button>
      ))}
    </div>
  )
}
