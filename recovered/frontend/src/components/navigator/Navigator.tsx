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
import { HistoryTab } from './HistoryTab'

import type { ShebaEpisode } from '../../data/shebaEpisodes'
import type { Event } from '../../types'
import type { ViewportBounds, ZoomLevel } from '../../store/globeStore'
import './navigator.css'

type TabId = 'events' | 'people' | 'places' | 'history'

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
  onHistoryClick?: (historyId: number) => void
  onCreateHistory?: () => void
}

const TABS: { id: TabId; icon: string; labelKey: string }[] = [
  { id: 'events', icon: '\u25CE', labelKey: 'navigator.events' },
  { id: 'people', icon: '\u263E', labelKey: 'navigator.people' },
  { id: 'places', icon: '\uD83D\uDCCD', labelKey: 'navigator.places' },
  { id: 'history', icon: '\uD83D\uDCDC', labelKey: 'navigator.history' },
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
  onHistoryClick,
  onCreateHistory,
}: NavigatorProps) {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState<TabId>('events')
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
        {activeTab === 'history' && (
          <HistoryTab
            onHistoryClick={onHistoryClick || (() => {})}
            onCreateHistory={onCreateHistory || (() => {})}
          />
        )}
      </div>

    </div>
  )
}

export default Navigator
