/**
 * Navigator - Left panel with modal triggers + 3 content tabs
 *
 * Modal triggers:
 * - Timeline Explorer (fullscreen modal)
 * - Trismegistus Archive (showcase modal)
 *
 * Tabs:
 * - Events (SHEBA): Curated episodes + importance-ranked events/persons
 * - People (PAPERMOON): Person gallery with viewport awareness
 * - Places: Location list with viewport awareness
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { FeedTab } from './FeedTab'
import { PersonTab } from './PersonTab'
import { LocationTab } from './LocationTab'
import { useSettingsStore } from '../../store/settingsStore'
import type { ShebaEpisode } from '../../data/shebaEpisodes'
import type { Event } from '../../types'
import type { ViewportBounds, ZoomLevel } from '../../store/globeStore'
import './navigator.css'

type TabId = 'events' | 'people' | 'places'

interface NavigatorProps {
  currentYear: number
  viewportBounds: ViewportBounds | null
  zoomLevel: ZoomLevel
  selectedEventId?: number | string | null
  onEventClick: (event: Event) => void
  onPersonClick: (personId: number) => void
  onLocationClick: (locationId: number) => void
  onOpenStory?: (personId: number) => void
  onFlyToLocation?: (lat: number, lng: number) => void
  onSetCurrentYear?: (year: number) => void
  onStartTour?: (episode: ShebaEpisode) => void
  onOpenTimeline?: () => void
  onOpenShowcase?: () => void
}

const TABS: { id: TabId; icon: string; labelKey: string }[] = [
  { id: 'events', icon: '\u25CE', labelKey: 'navigator.events' },
  { id: 'people', icon: '\u263E', labelKey: 'navigator.people' },
  { id: 'places', icon: '\uD83D\uDCCD', labelKey: 'navigator.places' },
]

export function Navigator({
  currentYear,
  viewportBounds,
  zoomLevel,
  onEventClick,
  onPersonClick,
  onLocationClick,
  onOpenStory,
  onFlyToLocation,
  onSetCurrentYear,
  onStartTour,
  onOpenTimeline,
  onOpenShowcase,
}: NavigatorProps) {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState<TabId>('events')
  const { experienceLevel, setExperienceLevel } = useSettingsStore()

  const handleOpenStory = onOpenStory || onPersonClick

  return (
    <div className="navigator">
      {/* Modal Trigger Buttons */}
      <div className="navigator-triggers">
        <button
          className="navigator-trigger-btn trigger-timeline"
          onClick={onOpenTimeline}
        >
          <span className="trigger-icon">{'\u231B'}</span>
          <span className="trigger-label">Timeline</span>
        </button>
        <button
          className="navigator-trigger-btn trigger-fgo"
          onClick={onOpenShowcase}
        >
          <span className="trigger-icon">{'\u2726'}</span>
          <span className="trigger-label">Trismegistus</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="navigator-tabs">
        {TABS.map(tab => (
          <button
            key={tab.id}
            className={`navigator-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
            title={t(tab.labelKey, tab.id)}
          >
            <span className="navigator-tab-icon">{tab.icon}</span>
            <span className="navigator-tab-label">{t(tab.labelKey, tab.id)}</span>
          </button>
        ))}
      </div>

      {/* Zoom indicator */}
      {zoomLevel !== 'cosmic' && (
        <div className="navigator-viewport-indicator">
          <span className="viewport-badge">
            {zoomLevel === 'continental' ? 'CONTINENTAL' : zoomLevel === 'regional' ? 'REGIONAL' : 'LOCAL'}
          </span>
          <span className="viewport-hint">Showing visible area</span>
        </div>
      )}

      {/* Tab Content */}
      <div className="navigator-content">
        {activeTab === 'events' && (
          <FeedTab
            currentYear={currentYear}
            viewportBounds={viewportBounds}
            zoomLevel={zoomLevel}
            onEventClick={onEventClick}
            onPersonClick={onPersonClick}
            onOpenStory={handleOpenStory}
            onFlyToLocation={onFlyToLocation}
            onSetCurrentYear={onSetCurrentYear}
            onStartTour={onStartTour}
            onOpenTimeline={onOpenTimeline}
          />
        )}
        {activeTab === 'people' && (
          <PersonTab
            currentYear={currentYear}
            viewportBounds={viewportBounds}
            zoomLevel={zoomLevel}
            onPersonClick={onPersonClick}
          />
        )}
        {activeTab === 'places' && (
          <LocationTab
            viewportBounds={viewportBounds}
            zoomLevel={zoomLevel}
            onLocationClick={onLocationClick}
          />
        )}
      </div>

      {/* Experience Level Toggle */}
      <div className="navigator-mode-toggle">
        <button
          className={`mode-toggle-btn ${experienceLevel === 'interest' ? 'active' : ''}`}
          onClick={() => setExperienceLevel('interest')}
          title="Simplified view with curated recommendations"
        >
          {'\u2605'} Interest
        </button>
        <button
          className={`mode-toggle-btn ${experienceLevel === 'expert' ? 'active' : ''}`}
          onClick={() => setExperienceLevel('expert')}
          title="Full data view with filters and sorting"
        >
          {'\u2699'} Expert
        </button>
      </div>
    </div>
  )
}

export default Navigator
