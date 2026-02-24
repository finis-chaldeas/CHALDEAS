/**
 * MobileLayout - Responsive layout for screens < 768px
 *
 * Top: 2D Map (50%)
 * Bottom: Feed/content (50%)
 * Bottom tab bar: Map / Feed / Search / TRISMEGISTUS / Menu
 */
import { useState, lazy, Suspense } from 'react'
import { useTranslation } from 'react-i18next'
import ViewportFeed from '../globe/ViewportFeed'
import WorldBriefing from '../globe/WorldBriefing'
import { HeroCardDeck } from './HeroCardDeck'
import type { Event } from '../../types'
import type { GlobeMarkerData } from '../../store/globeStore'

const MapView = lazy(() => import('../map/MapContainer').then(m => ({ default: m.MapView })))

type MobileTab = 'map' | 'feed' | 'search' | 'showcase' | 'menu'

interface MobileLayoutProps {
  markers: GlobeMarkerData[]
  onEventClick: (event: Event) => void
  onPersonClick: (personId: number) => void
  onLocationClick: (locationId: number) => void
  onNarrativeEventClick: (eventId: number) => void
  onNarrativePersonClick: (personId: number) => void
  onSearchOpen: () => void
  onShowcaseOpen: () => void
  onMenuOpen: () => void
  onDeepReadOpen: () => void
  selectedEvent: Event | null
}

export function MobileLayout({
  markers,
  onEventClick,
  onPersonClick,
  onLocationClick,
  onNarrativeEventClick,
  onNarrativePersonClick,
  onSearchOpen,
  onShowcaseOpen,
  onMenuOpen,
  onDeepReadOpen,
  selectedEvent,
}: MobileLayoutProps) {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState<MobileTab>('map')

  const TABS: { id: MobileTab; icon: string; label: string }[] = [
    { id: 'map', icon: '\uD83C\uDF0D', label: t('mobile.map', 'Map') },
    { id: 'feed', icon: '\u2261', label: t('mobile.feed', 'Feed') },
    { id: 'search', icon: '\u2315', label: t('mobile.search', 'Search') },
    { id: 'showcase', icon: '\u2606', label: 'Archive' },
    { id: 'menu', icon: '\u2699', label: t('mobile.menu', 'Menu') },
  ]

  const handleTabClick = (tab: MobileTab) => {
    if (tab === 'search') {
      onSearchOpen()
      return
    }
    if (tab === 'showcase') {
      onShowcaseOpen()
      return
    }
    if (tab === 'menu') {
      onMenuOpen()
      return
    }
    setActiveTab(tab)
  }

  return (
    <div className="mobile-layout">
      {/* Top section: Map */}
      <div className="mobile-map-section">
        {activeTab === 'map' && (
          <>
            <WorldBriefing
              onEventClick={onNarrativeEventClick}
              onPersonClick={onNarrativePersonClick}
              onOpenDeepRead={onDeepReadOpen}
            />
            <HeroCardDeck onEventClick={onNarrativeEventClick} />
            <Suspense fallback={<div className="mobile-loading">Loading map...</div>}>
              <MapView
                markers={markers}
                onEventClick={onEventClick}
                onPersonClick={onPersonClick}
                onLocationClick={onLocationClick}
                isShifted={!!selectedEvent}
              />
            </Suspense>
          </>
        )}
        {activeTab === 'feed' && (
          <Suspense fallback={<div className="mobile-loading">Loading map...</div>}>
            <MapView
              markers={markers}
              onEventClick={onEventClick}
              onPersonClick={onPersonClick}
              onLocationClick={onLocationClick}
              isShifted={false}
            />
          </Suspense>
        )}
      </div>

      {/* Bottom section: Feed content */}
      {activeTab === 'feed' && (
        <div className="mobile-feed-section">
          <ViewportFeed
            onEventClick={onNarrativeEventClick}
            onPersonClick={onNarrativePersonClick}
          />
        </div>
      )}

      {/* Bottom Tab Bar */}
      <div className="mobile-tab-bar">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`mobile-tab-btn ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => handleTabClick(tab.id)}
          >
            <span className="mobile-tab-icon">{tab.icon}</span>
            <span className="mobile-tab-label">{tab.label}</span>
          </button>
        ))}
      </div>

      <style>{`
        .mobile-layout {
          display: flex;
          flex-direction: column;
          height: 100vh;
          width: 100vw;
          overflow: hidden;
          background: var(--chaldea-bg, #0a0e17);
        }

        .mobile-map-section {
          flex: 1;
          position: relative;
          overflow: hidden;
          min-height: 0;
        }

        .mobile-map-section .world-briefing-container {
          left: 0 !important;
          right: 0 !important;
          top: 0 !important;
          max-width: 100% !important;
        }

        .mobile-feed-section {
          height: 45vh;
          overflow-y: auto;
          border-top: 1px solid var(--chaldea-border, rgba(0, 212, 255, 0.15));
          background: var(--chaldea-bg, #0a0e17);
          position: relative;
        }

        .mobile-feed-section .viewport-feed {
          position: static !important;
          width: 100% !important;
          max-height: none !important;
          left: 0 !important;
          top: 0 !important;
        }

        .mobile-tab-bar {
          display: flex;
          align-items: stretch;
          background: rgba(5, 8, 16, 0.98);
          border-top: 1px solid var(--chaldea-border, rgba(0, 212, 255, 0.15));
          padding: 0.25rem 0;
          flex-shrink: 0;
          z-index: 50;
        }

        .mobile-tab-btn {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.125rem;
          padding: 0.5rem 0.25rem;
          background: transparent;
          border: none;
          color: var(--chaldea-text, #8ba4b4);
          cursor: pointer;
          transition: color 0.2s;
        }

        .mobile-tab-btn.active {
          color: var(--chaldea-cyan, #00d4ff);
        }

        .mobile-tab-btn:hover {
          color: var(--chaldea-text-bright, #d0e8f0);
        }

        .mobile-tab-icon {
          font-size: 1.1rem;
        }

        .mobile-tab-label {
          font-size: 0.6rem;
          letter-spacing: 0.03em;
        }

        .mobile-loading {
          display: flex;
          align-items: center;
          justify-content: center;
          height: 100%;
          font-size: 0.75rem;
          color: var(--chaldea-text, #8ba4b4);
        }
      `}</style>
    </div>
  )
}
