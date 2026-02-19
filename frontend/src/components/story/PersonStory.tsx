/**
 * PersonStory - Person's life story as a chain of nodes
 *
 * Displays a person's life events in chronological order
 * with narrative, locations, and source citations.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import { StoryNode, StoryNodeData } from './StoryNode'
import { SourceViewer } from './SourceViewer'

interface PersonStoryProps {
  personId: number
  onClose: () => void
  onEventClick?: (eventId: number) => void
  onLocationClick?: (locationId: number) => void
}

interface PersonData {
  id: number
  name: string
  name_ko?: string
  birth_year?: number
  death_year?: number
  role?: string
}

interface PersonStoryData {
  person: PersonData
  nodes: Array<{
    order: number
    event_id: number
    title: string
    title_ko?: string
    year: number | null
    year_end?: number | null
    description?: string
    description_ko?: string
    location?: {
      id: number
      name: string
      name_ko?: string
      latitude?: number
      longitude?: number
    }
  }>
  total_nodes: number
}

function formatLifespan(birthYear?: number, deathYear?: number): string {
  if (!birthYear && !deathYear) return ''

  const formatYear = (y: number) => y < 0 ? `${Math.abs(y)} BCE` : `${y} CE`

  if (birthYear && deathYear) {
    return `${formatYear(birthYear)} - ${formatYear(deathYear)}`
  }
  if (birthYear) {
    return `b. ${formatYear(birthYear)}`
  }
  if (deathYear) {
    return `d. ${formatYear(deathYear)}`
  }
  return ''
}

export function PersonStory({
  personId,
  onClose,
  onEventClick,
  onLocationClick
}: PersonStoryProps) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language
  const [activeNodeIndex, setActiveNodeIndex] = useState<number | null>(null)
  const [viewingSourceId, setViewingSourceId] = useState<number | null>(null)

  // Fetch person story
  const { data: storyData, isLoading, error } = useQuery<PersonStoryData>({
    queryKey: ['person-story', personId],
    queryFn: async () => {
      const res = await api.get(`/story/person/${personId}`)
      return res.data
    },
  })

  // Convert API nodes to StoryNodeData format
  const nodes: StoryNodeData[] = storyData?.nodes.map(node => ({
    order: node.order,
    title: node.title,
    title_ko: node.title_ko,
    year: node.year,
    year_end: node.year_end,
    narrative: node.description || '',
    narrative_ko: node.description_ko,
    location: node.location,
    event_id: node.event_id,
    // Sources would come from event data
    sources: [],
  })) || []

  const person = storyData?.person
  const personName = person ? ((lang === 'ko' && person.name_ko) ? person.name_ko : person.name) : ''

  // If viewing a source, show SourceViewer
  if (viewingSourceId !== null) {
    return (
      <SourceViewer
        sourceId={viewingSourceId}
        onClose={() => setViewingSourceId(null)}
      />
    )
  }

  return (
    <>
      {/* Header */}
      <div className="story-panel-header">
        <div className="story-panel-title">
          <span>👤</span>
          {isLoading ? t('common.loading', 'Loading...') : personName}
        </div>
        <button className="story-panel-close" onClick={onClose}>✕</button>
      </div>

      {/* Content */}
      <div className="story-panel-content">
        {isLoading && (
          <div className="story-loading">
            <div className="story-loading-spinner" />
            <span>{t('story.loadingStory', 'Loading story...')}</span>
          </div>
        )}

        {error && (
          <div className="story-error">
            <span className="error-icon">⚠️</span>
            <span>{t('story.errorLoading', 'Failed to load story')}</span>
          </div>
        )}

        {storyData && (
          <>
            {/* Person Info */}
            <div className="person-story-header">
              <div className="person-story-info">
                <h2 className="person-story-name">{personName}</h2>
                <div className="person-story-lifespan">
                  {formatLifespan(person?.birth_year, person?.death_year)}
                </div>
                {person?.role && (
                  <div className="person-story-role">{person.role}</div>
                )}
              </div>
            </div>

            {/* Story Nodes */}
            <div className="person-story-timeline">
              <h3 className="story-section-title">
                {t('story.lifeEvents', 'Life Events')}
                <span className="story-node-count">({nodes.length})</span>
              </h3>

              {nodes.length === 0 ? (
                <div className="story-no-nodes">
                  {t('story.noEventsFound', 'No events found for this person')}
                </div>
              ) : (
                <div className="story-nodes-list">
                  {nodes.map((node, index) => (
                    <StoryNode
                      key={node.event_id || index}
                      node={node}
                      isActive={activeNodeIndex === index}
                      onClick={() => {
                        setActiveNodeIndex(index)
                        if (onEventClick && node.event_id) {
                          onEventClick(node.event_id)
                        }
                      }}
                      onLocationClick={onLocationClick}
                      onSourceClick={setViewingSourceId}
                    />
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </>
  )
}

export default PersonStory
