/**
 * PlaceStory - Location's history as a chain of events
 *
 * Shows all events that occurred at a specific location
 * in chronological order.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import { StoryNode, StoryNodeData } from './StoryNode'

interface PlaceStoryProps {
  locationId: number
  onClose: () => void
  onEventClick?: (eventId: number) => void
}

interface LocationData {
  id: number
  name: string
  name_ko?: string
  name_ja?: string
  location_type?: string
  latitude?: number
  longitude?: number
  wikidata_id?: string
  parent_location_id?: number
}

interface LocationEvent {
  id: number
  title: string
  title_ko?: string
  date_start: number | null
  date_end?: number | null
  description?: string
  description_ko?: string
  importance?: number
}

export function PlaceStory({
  locationId,
  onClose,
  onEventClick
}: PlaceStoryProps) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language
  const [activeNodeIndex, setActiveNodeIndex] = useState<number | null>(null)

  // Fetch location data
  const { data: locationData, isLoading: loadingLocation } = useQuery({
    queryKey: ['location', locationId],
    queryFn: async () => {
      const res = await api.get(`/locations/${locationId}`)
      return res.data as LocationData
    },
  })

  // Fetch events at this location
  const { data: eventsData, isLoading: loadingEvents } = useQuery({
    queryKey: ['location-events', locationId],
    queryFn: async () => {
      const res = await api.get(`/locations/${locationId}/events`)
      return res.data
    },
  })

  const isLoading = loadingLocation || loadingEvents
  const location = locationData
  const events: LocationEvent[] = eventsData?.items || []

  // Convert events to StoryNode format
  const nodes: StoryNodeData[] = events.map((event, index) => ({
    order: index + 1,
    title: event.title,
    title_ko: event.title_ko,
    year: event.date_start,
    year_end: event.date_end,
    narrative: event.description || '',
    narrative_ko: event.description_ko,
    event_id: event.id,
    sources: [],
  }))

  const locationName = location ? ((lang === 'ko' && location.name_ko) ? location.name_ko : location.name) : ''

  return (
    <>
      {/* Header */}
      <div className="story-panel-header">
        <div className="story-panel-title">
          <span>📍</span>
          {isLoading ? t('common.loading', 'Loading...') : locationName}
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

        {location && (
          <>
            {/* Location Info */}
            <div className="place-story-header">
              <h2 className="place-story-name">{locationName}</h2>
              {location.location_type && (
                <div className="place-story-type">{location.location_type}</div>
              )}
            </div>

            {/* Events Timeline */}
            <div className="place-story-timeline">
              <h3 className="story-section-title">
                {t('story.eventsAtLocation', 'Events at this location')}
                <span className="story-node-count">({nodes.length})</span>
              </h3>

              {nodes.length === 0 ? (
                <div className="story-no-nodes">
                  {t('story.noEventsAtLocation', 'No events recorded at this location')}
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

export default PlaceStory
