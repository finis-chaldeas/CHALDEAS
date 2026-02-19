/**
 * StoryPanel - Right panel container for story views
 *
 * Views:
 * - Event Detail (current selection)
 * - Person Story (person's life events)
 * - Place Story (location's history)
 * - Era Story (period overview)
 * - Causal Chain (cause-effect relationships)
 */
import { useTranslation } from 'react-i18next'
import { EventDetailPanel } from '../detail'
import type { Event } from '../../types'

export type StoryViewType = 'event' | 'person' | 'place' | 'era' | 'causal' | 'none'

interface StoryPanelProps {
  // Current view
  viewType: StoryViewType
  // Event detail props
  event: Event | null
  allEvents: Event[]
  onEventClick: (event: Event) => void
  onAskSheba: (query: string) => void
  onPersonClick: (personId: number) => void
  onLocationClick: (locationId: number) => void
  onClose: () => void
}

export function StoryPanel({
  viewType,
  event,
  allEvents,
  onEventClick,
  onAskSheba,
  onPersonClick,
  onLocationClick,
  onClose
}: StoryPanelProps) {
  const { t } = useTranslation()

  // Empty state
  if (viewType === 'none' && !event) {
    return (
      <>
        <div className="story-panel-header">
          <div className="story-panel-title">
            <span>📜</span>
            {t('story.title', 'Story')}
          </div>
        </div>
        <div className="story-panel-content">
          <div className="story-empty">
            <div className="story-empty-icon">🌍</div>
            <div className="story-empty-text">
              {t('story.selectEvent', 'Select an event on the globe or from the list to view its story')}
            </div>
          </div>
        </div>
      </>
    )
  }

  // Event detail view (default)
  if (viewType === 'event' || event) {
    return (
      <EventDetailPanel
        event={event}
        allEvents={allEvents}
        onClose={onClose}
        onEventClick={onEventClick}
        onAskSheba={onAskSheba}
        onPersonClick={onPersonClick}
        onLocationClick={onLocationClick}
      />
    )
  }

  // Person Story view (Phase 4)
  if (viewType === 'person') {
    return (
      <>
        <div className="story-panel-header">
          <div className="story-panel-title">
            <span>👤</span>
            {t('story.personStory', 'Person Story')}
          </div>
          <button className="story-panel-close" onClick={onClose}>✕</button>
        </div>
        <div className="story-panel-content">
          <div className="story-coming-soon">
            {t('story.comingSoon', 'Coming soon in Phase 4')}
          </div>
        </div>
      </>
    )
  }

  // Place Story view (Phase 4)
  if (viewType === 'place') {
    return (
      <>
        <div className="story-panel-header">
          <div className="story-panel-title">
            <span>📍</span>
            {t('story.placeStory', 'Place Story')}
          </div>
          <button className="story-panel-close" onClick={onClose}>✕</button>
        </div>
        <div className="story-panel-content">
          <div className="story-coming-soon">
            {t('story.comingSoon', 'Coming soon in Phase 4')}
          </div>
        </div>
      </>
    )
  }

  // Era Story view (Phase 4)
  if (viewType === 'era') {
    return (
      <>
        <div className="story-panel-header">
          <div className="story-panel-title">
            <span>🏛️</span>
            {t('story.eraStory', 'Era Story')}
          </div>
          <button className="story-panel-close" onClick={onClose}>✕</button>
        </div>
        <div className="story-panel-content">
          <div className="story-coming-soon">
            {t('story.comingSoon', 'Coming soon in Phase 4')}
          </div>
        </div>
      </>
    )
  }

  // Causal Chain view (Phase 4)
  if (viewType === 'causal') {
    return (
      <>
        <div className="story-panel-header">
          <div className="story-panel-title">
            <span>🔗</span>
            {t('story.causalChain', 'Causal Chain')}
          </div>
          <button className="story-panel-close" onClick={onClose}>✕</button>
        </div>
        <div className="story-panel-content">
          <div className="story-coming-soon">
            {t('story.comingSoon', 'Coming soon in Phase 4')}
          </div>
        </div>
      </>
    )
  }

  return null
}

export default StoryPanel
