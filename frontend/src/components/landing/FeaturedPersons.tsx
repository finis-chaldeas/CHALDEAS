/**
 * FeaturedPersons (Welcome Experience) - Landing page for first-time visitors.
 *
 * 3 entry paths:
 * 1. Free Explore - Close overlay, show tooltip sequence
 * 2. Guided Tour - Pick a SHEBA episode with tourSteps
 * 3. Recommended Persons - Original person grid
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import { SHEBA_EPISODES } from '../../data/shebaEpisodes'
import type { ShebaEpisode } from '../../data/shebaEpisodes'
import './Landing.css'

interface FeaturedPerson {
  id: number
  name: string
  name_ko?: string
  birth_year?: number
  death_year?: number
  role?: string
  biography?: string
  image_url?: string
  importance: number
}

interface Props {
  onPersonClick: (personId: number) => void
  onClose: () => void
  onOpenServantPanel?: () => void
  onOpenShowcase?: () => void
  onStartTour?: (episode: ShebaEpisode) => void
}

type WelcomeView = 'welcome' | 'guided-tours' | 'persons'

const ERA_TABS = [
  { key: null, label: 'All' },
  { key: 'ancient', label: 'Ancient' },
  { key: 'medieval', label: 'Medieval' },
  { key: 'early_modern', label: 'Early Modern' },
  { key: 'modern', label: 'Modern' },
] as const

function formatYear(year: number | null | undefined): string {
  if (year === null || year === undefined) return '?'
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

// Only episodes with tourSteps for guided tour selection
const TOUR_EPISODES = SHEBA_EPISODES.filter(ep => ep.tourSteps && ep.tourSteps.length > 0)

export function FeaturedPersons({ onPersonClick, onClose, onStartTour }: Props) {
  const [view, setView] = useState<WelcomeView>('welcome')
  const [selectedEra, setSelectedEra] = useState<string | null>(null)

  const { data, isLoading } = useQuery<{ items: FeaturedPerson[]; total: number }>({
    queryKey: ['featured-persons', selectedEra],
    queryFn: async () => {
      const params: Record<string, unknown> = { limit: 12 }
      if (selectedEra) params.era = selectedEra
      const res = await api.get('/featured/persons', { params })
      return res.data
    },
    staleTime: 300000,
    enabled: view === 'persons',
  })

  // Welcome screen - 3 entry paths
  if (view === 'welcome') {
    return (
      <div className="landing-overlay" onClick={onClose}>
        <div className="welcome-container" onClick={(e) => e.stopPropagation()}>
          <div className="welcome-header">
            <div className="welcome-logo">C H A L D E A S</div>
            <div className="welcome-tagline">Observe the interconnected history of our world</div>
          </div>

          <div className="welcome-paths">
            {/* Free Explore */}
            <button className="welcome-path-card welcome-path-explore" onClick={onClose}>
              <div className="welcome-path-icon">{'\uD83C\uDF0D'}</div>
              <div className="welcome-path-title">Free Explore</div>
              <div className="welcome-path-desc">
                Spin the globe, move through time, and discover history on your own.
              </div>
            </button>

            {/* Guided Tour */}
            <button className="welcome-path-card welcome-path-tour" onClick={() => setView('guided-tours')}>
              <div className="welcome-path-icon">{'\uD83D\uDCD6'}</div>
              <div className="welcome-path-title">Guided Tour</div>
              <div className="welcome-path-desc">
                Follow a curated episode as the globe moves through key moments in history.
              </div>
              <div className="welcome-path-count">{TOUR_EPISODES.length} episodes available</div>
            </button>
          </div>

          {/* Recommended Persons - bottom row */}
          <button
            className="welcome-path-wide"
            onClick={() => setView('persons')}
          >
            <span className="welcome-path-icon-sm">{'\uD83D\uDC64'}</span>
            <span className="welcome-path-title-sm">Browse Recommended Figures</span>
            <span className="welcome-path-arrow">{'\u2192'}</span>
          </button>
        </div>
      </div>
    )
  }

  // Guided Tour selection
  if (view === 'guided-tours') {
    return (
      <div className="landing-overlay" onClick={onClose}>
        <div className="landing-container" onClick={(e) => e.stopPropagation()}>
          <div className="landing-header">
            <div className="landing-brand">
              <button className="welcome-back-btn" onClick={() => setView('welcome')}>
                {'\u2190'} Back
              </button>
              <div className="landing-subtitle">Choose an episode to begin</div>
            </div>
            <button className="landing-close" onClick={onClose}>
              Skip to Globe
            </button>
          </div>

          <div className="tour-selection-grid">
            {TOUR_EPISODES.map(episode => (
              <button
                key={episode.id}
                className="tour-selection-card"
                onClick={() => {
                  onStartTour?.(episode)
                  onClose()
                }}
              >
                <div className="tour-card-region">{episode.region}</div>
                <div className="tour-card-title">{episode.title}</div>
                {episode.title_ko && (
                  <div className="tour-card-title-ko">{episode.title_ko}</div>
                )}
                <div className="tour-card-desc">{episode.description}</div>
                <div className="tour-card-meta">
                  <span className="tour-card-date">
                    {formatYear(episode.dateRange.start)}
                    {episode.dateRange.end !== episode.dateRange.start && ` ~ ${formatYear(episode.dateRange.end)}`}
                  </span>
                  <span className="tour-card-steps">{episode.tourSteps!.length} steps</span>
                </div>
                {episode.relatedServants && episode.relatedServants.length > 0 && (
                  <div className="tour-card-servants">
                    {'\u2726'} {episode.relatedServants.join(', ')}
                  </div>
                )}
                <div className="tour-card-action">Start Tour {'\u2192'}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // Recommended Persons grid (original behavior)
  return (
    <div className="landing-overlay" onClick={onClose}>
      <div className="landing-container" onClick={(e) => e.stopPropagation()}>
        <div className="landing-header">
          <div className="landing-brand">
            <button className="welcome-back-btn" onClick={() => setView('welcome')}>
              {'\u2190'} Back
            </button>
            <div className="landing-subtitle">Explore the key figures of history</div>
          </div>
          <button className="landing-close" onClick={onClose}>
            Enter Globe View
          </button>
        </div>

        {/* Era Filter Tabs */}
        <div className="landing-tabs">
          {ERA_TABS.map((tab) => (
            <button
              key={tab.key ?? 'all'}
              className={`landing-tab ${selectedEra === tab.key ? 'active' : ''}`}
              onClick={() => setSelectedEra(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Person Grid */}
        <div className="landing-grid">
          {isLoading && (
            <div className="landing-loading">
              <div className="landing-spinner" />
              <span>Loading featured persons...</span>
            </div>
          )}

          {data?.items.map((person) => (
            <div
              key={person.id}
              className="person-card"
              onClick={() => onPersonClick(person.id)}
            >
              <div className="person-card-header">
                <div className="person-card-icon">
                  {person.image_url ? (
                    <img src={person.image_url} alt={person.name} />
                  ) : (
                    <span className="person-card-avatar">
                      {person.name.charAt(0)}
                    </span>
                  )}
                </div>
                <div className="person-card-info">
                  <h3 className="person-card-name">{person.name}</h3>
                  {person.name_ko && (
                    <div className="person-card-name-ko">{person.name_ko}</div>
                  )}
                </div>
              </div>

              <div className="person-card-meta">
                <span className="person-card-dates">
                  {formatYear(person.birth_year)} — {formatYear(person.death_year)}
                </span>
                {person.role && (
                  <span className="person-card-role">{person.role}</span>
                )}
              </div>

              {person.biography && (
                <p className="person-card-bio">
                  {person.biography.length > 120
                    ? person.biography.slice(0, 120) + '...'
                    : person.biography}
                </p>
              )}
            </div>
          ))}
        </div>

        {data && data.total > 12 && (
          <div className="landing-footer-info">
            Showing 12 of {data.total.toLocaleString()} historical figures
          </div>
        )}
      </div>
    </div>
  )
}
