/**
 * EraStory - Historical period overview
 *
 * Shows overview of a historical era including:
 * - Period info and characteristics
 * - Key persons of the era
 * - Major events
 * - Important locations
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'

interface EraStoryProps {
  periodId?: number
  yearStart: number
  yearEnd: number
  title?: string
  onClose: () => void
  onEventClick?: (eventId: number) => void
  onPersonClick?: (personId: number) => void
  // onLocationClick reserved for future use
}

interface Person {
  id: number
  name: string
  name_ko?: string
  birth_year?: number
  death_year?: number
  role?: string
}

interface Event {
  id: number
  title: string
  title_ko?: string
  date_start: number
  importance?: number
}

// Location interface for future use
// interface Location {
//   id: number
//   name: string
//   name_ko?: string
//   country?: string
// }

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

export function EraStory({
  yearStart,
  yearEnd,
  title,
  onClose,
  onEventClick,
  onPersonClick
}: EraStoryProps) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language
  const [activeTab, setActiveTab] = useState<'events' | 'persons' | 'locations'>('events')

  // Fetch events in this era
  const { data: eventsData, isLoading: loadingEvents } = useQuery({
    queryKey: ['era-events', yearStart, yearEnd],
    queryFn: async () => {
      const res = await api.get('/events', {
        params: {
          year_start: yearStart,
          year_end: yearEnd,
          limit: 100,
        }
      })
      return res.data
    },
  })

  // Fetch persons active in this era
  const { data: personsData, isLoading: loadingPersons } = useQuery({
    queryKey: ['era-persons', yearStart, yearEnd],
    queryFn: async () => {
      const res = await api.get('/persons', {
        params: {
          year_start: yearStart,
          year_end: yearEnd,
          limit: 50,
        }
      })
      return res.data
    },
  })

  const isLoading = loadingEvents || loadingPersons
  const events: Event[] = eventsData?.items || []
  const persons: Person[] = personsData?.items || []

  const eraTitle = title || `${formatYear(yearStart)} - ${formatYear(yearEnd)}`

  return (
    <>
      {/* Header */}
      <div className="story-panel-header">
        <div className="story-panel-title">
          <span>🏛️</span>
          {eraTitle}
        </div>
        <button className="story-panel-close" onClick={onClose}>✕</button>
      </div>

      {/* Content */}
      <div className="story-panel-content">
        {/* Era Info */}
        <div className="era-story-header">
          <div className="era-story-period">
            {formatYear(yearStart)} - {formatYear(yearEnd)}
          </div>
          <div className="era-story-duration">
            {Math.abs(yearEnd - yearStart)} years
          </div>
        </div>

        {/* Stats */}
        <div className="era-story-stats">
          <div className="era-stat">
            <span className="era-stat-value">{events.length}</span>
            <span className="era-stat-label">{t('era.events', 'Events')}</span>
          </div>
          <div className="era-stat">
            <span className="era-stat-value">{persons.length}</span>
            <span className="era-stat-label">{t('era.persons', 'Persons')}</span>
          </div>
        </div>

        {/* Tabs */}
        <div className="era-story-tabs">
          <button
            className={`era-tab ${activeTab === 'events' ? 'active' : ''}`}
            onClick={() => setActiveTab('events')}
          >
            {t('era.majorEvents', 'Major Events')}
          </button>
          <button
            className={`era-tab ${activeTab === 'persons' ? 'active' : ''}`}
            onClick={() => setActiveTab('persons')}
          >
            {t('era.keyFigures', 'Key Figures')}
          </button>
        </div>

        {/* Tab Content */}
        <div className="era-story-content">
          {isLoading && (
            <div className="story-loading">
              <div className="story-loading-spinner" />
            </div>
          )}

          {/* Events Tab */}
          {activeTab === 'events' && !loadingEvents && (
            <div className="era-events-list">
              {events.length === 0 ? (
                <div className="story-no-nodes">{t('era.noEvents', 'No events found')}</div>
              ) : (
                events.slice(0, 20).map(event => (
                  <button
                    key={event.id}
                    className="era-event-item"
                    onClick={() => onEventClick?.(event.id)}
                  >
                    <span className="era-event-year">{formatYear(event.date_start)}</span>
                    <span className="era-event-title">
                      {(lang === 'ko' && event.title_ko) ? event.title_ko : event.title}
                    </span>
                    {event.importance && event.importance >= 4 && (
                      <span className="era-event-important">⭐</span>
                    )}
                  </button>
                ))
              )}
              {events.length > 20 && (
                <div className="era-more">
                  {t('era.andMore', 'and {{count}} more...', { count: events.length - 20 })}
                </div>
              )}
            </div>
          )}

          {/* Persons Tab */}
          {activeTab === 'persons' && !loadingPersons && (
            <div className="era-persons-list">
              {persons.length === 0 ? (
                <div className="story-no-nodes">{t('era.noPersons', 'No persons found')}</div>
              ) : (
                persons.slice(0, 20).map(person => (
                  <button
                    key={person.id}
                    className="era-person-item"
                    onClick={() => onPersonClick?.(person.id)}
                  >
                    <span className="era-person-icon">👤</span>
                    <div className="era-person-info">
                      <span className="era-person-name">
                        {(lang === 'ko' && person.name_ko) ? person.name_ko : person.name}
                      </span>
                      {person.role && (
                        <span className="era-person-role">{person.role}</span>
                      )}
                    </div>
                    {person.birth_year && (
                      <span className="era-person-years">
                        {formatYear(person.birth_year)}
                        {person.death_year && ` - ${formatYear(person.death_year)}`}
                      </span>
                    )}
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </>
  )
}

export default EraStory
