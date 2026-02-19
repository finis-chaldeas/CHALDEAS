import { useState, lazy, Suspense } from 'react'
import { useTranslation } from 'react-i18next'
import { ChatPanel } from './components/chat'
import { EventDetailPanel } from './components/detail'
import { ShowcaseModal } from './components/showcase'
import type { ShowcaseContent } from './components/showcase'
import { Navigator } from './components/navigator'
import { SearchAutocomplete } from './components/search'
import { UnifiedTimeline } from './components/timeline'
import { LanguageSelector } from './components/common'
import { SettingsPage } from './components/settings'
import { TermsPage, PrivacyPage } from './pages'
import { FeaturedPersons } from './components/landing'
import { StoryModal } from './components/story/StoryModal'
import { TimelineModal } from './components/navigator/TimelineModal'
import { TourOverlay } from './components/tour'
import type { ShebaEpisode } from './data/shebaEpisodes'
import { useTimelineStore } from './store/timelineStore'
import { useGlobeStore } from './store/globeStore'
// import { useBookmarkStore } from './store/bookmarkStore'
import { useSettingsStore } from './store/settingsStore'
import { useObservationStore, getEraFromYear } from './store/observationStore'
import { useQuery } from '@tanstack/react-query'
import { api } from './api/client'
import type { Event } from './types'

// Lazy load heavy components (Three.js/Globe, panels)
const GlobeContainer = lazy(() => import('./components/globe/GlobeContainer').then(m => ({ default: m.GlobeContainer })))
const MapView = lazy(() => import('./components/map/MapContainer').then(m => ({ default: m.MapView })))
const PersonDetailView = lazy(() => import('./components/detail/PersonDetailView').then(m => ({ default: m.PersonDetailView })))
const LocationDetailView = lazy(() => import('./components/detail/LocationDetailView').then(m => ({ default: m.LocationDetailView })))
const ChainPanel = lazy(() => import('./components/chain/ChainPanel'))
const HierarchyExplorer = lazy(() => import('./components/hierarchy/HierarchyExplorer').then(m => ({ default: m.HierarchyExplorer })))

// Loading fallback components
const GlobeLoader = () => (
  <div className="globe-loading">
    <div className="globe-loading-spinner" />
    <span>Initializing CHALDEAS Globe...</span>
  </div>
)

const PanelLoader = () => (
  <div className="panel-loading">
    <div className="panel-loading-spinner" />
  </div>
)

const GLOBE_STYLE_KEYS = ['default', 'holo', 'night'] as const

function App() {
  const { t } = useTranslation()
  const { currentYear, setCurrentYear } = useTimelineStore()
  const { selectedEvent, setSelectedEvent, viewportBounds, zoomLevel, flyToLocation, viewMode, globeMarkers } = useGlobeStore()
  // Bookmarks available if needed in future
  const { globeStyle: settingsGlobeStyle, setGlobeStyle: setSettingsGlobeStyle } = useSettingsStore()
  const { recordEventView, recordPersonView } = useObservationStore()
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isTermsOpen, setIsTermsOpen] = useState(false)
  const [isPrivacyOpen, setIsPrivacyOpen] = useState(false)
  const globeStyle = settingsGlobeStyle
  const setGlobeStyle = setSettingsGlobeStyle
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [initialChatQuery, setInitialChatQuery] = useState<string | null>(null)
  const [isChainOpen, setIsChainOpen] = useState(false)
  const [personDetailId, setPersonDetailId] = useState<number | null>(null)
  const [locationDetailId, setLocationDetailId] = useState<number | null>(null)
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)  // Mobile sidebar toggle
  const [showLanding, setShowLanding] = useState(() => !localStorage.getItem('chaldeas-explored'))
  const [showcaseContent, setShowcaseContent] = useState<ShowcaseContent | null>(null)
  const [showShowcase, setShowShowcase] = useState(false)
  const [isTimelineOpen, setIsTimelineOpen] = useState(false)
  const [storyPersonId, setStoryPersonId] = useState<number | null>(null)
  const [tourEpisode, setTourEpisode] = useState<ShebaEpisode | null>(null)
  const [isHierarchyOpen, setIsHierarchyOpen] = useState(false)
  const [hierarchyEventId, setHierarchyEventId] = useState<number | undefined>(undefined)

  // Handlers for entity detail views
  const handlePersonClick = (personId: number) => {
    setLocationDetailId(null)
    setPersonDetailId(personId)
    recordPersonView(personId, undefined, getEraFromYear(currentYear))
  }

  const handleLocationClick = (locationId: number) => {
    setPersonDetailId(null)
    setLocationDetailId(locationId)
  }

  const handleCloseEntityView = () => {
    setPersonDetailId(null)
    setLocationDetailId(null)
  }

  const handleOpenStory = (personId: number) => {
    setStoryPersonId(personId)
  }

  const handleEventClick = (event: Event) => {
    setSelectedEvent(event)
    setCurrentYear(event.date_start)
    setIsSidebarOpen(false)
    recordEventView(
      typeof event.id === 'number' ? event.id : parseInt(String(event.id), 10),
      typeof event.category === 'string' ? event.category : event.category?.name,
      undefined,
      getEraFromYear(event.date_start)
    )
  }

  const handleClosePanel = () => {
    setSelectedEvent(null)
  }

  const handleShowcaseEventClick = async (eventId: number) => {
    try {
      const res = await api.get(`/events/${eventId}`)
      if (res.data) {
        handleEventClick(res.data)
        setShowShowcase(false)
      }
    } catch (err) {
      console.error('Failed to fetch event from showcase:', err)
    }
  }

  // Fetch events for timeline (still needed by UnifiedTimeline and EventDetailPanel)
  const { data: timelineEvents } = useQuery({
    queryKey: ['timeline-events', Math.round(currentYear / 50) * 50],
    queryFn: () => api.get('/events', {
      params: { year_start: currentYear - 50, year_end: currentYear + 50, limit: 500 }
    }),
    select: (res) => res.data?.items || [],
  })

  return (
    <div className="app-container" role="application" aria-label="CHALDEAS Historical Knowledge System">
      {/* Mobile Menu Toggle Button */}
      <button
        className="mobile-menu-btn"
        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
        aria-label="Toggle menu"
      >
        {isSidebarOpen ? '\u2715' : '\u2630'}
      </button>

      {/* Mobile Overlay */}
      {isSidebarOpen && (
        <div
          className="mobile-overlay"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Left Sidebar */}
      <aside className={`sidebar ${isSidebarOpen ? 'sidebar-open' : ''}`} role="navigation" aria-label="Main navigation">
        {/* Header: Logo + Language */}
        <div className="sidebar-header">
          <div className="logo">
            <div className="logo-icon">{'\u2295'}</div>
            <div>
              <div className="logo-text">{t('app.name')}</div>
              <div className="system-status">
                <span className="status-dot"></span>
                {t('app.systemOnline')}
              </div>
            </div>
          </div>
          <LanguageSelector />
        </div>

        {/* Search */}
        <div className="search-container">
          <SearchAutocomplete
            placeholder={t('sidebar.searchPlaceholder')}
            onSelectEvent={async (eventId) => {
              try {
                const res = await api.get(`/events/${eventId}`)
                if (res.data) handleEventClick(res.data)
              } catch (err) {
                console.error('Failed to fetch event:', err)
              }
            }}
            onSelectPerson={handlePersonClick}
            onSelectLocation={handleLocationClick}
            onSearch={() => {}}
          />
        </div>

        {/* Navigator Tabs (replaces category filters, era toggle, event list, chain stats) */}
        <Navigator
          currentYear={currentYear}
          viewportBounds={viewportBounds}
          zoomLevel={zoomLevel}
          selectedEventId={selectedEvent?.id}
          onEventClick={handleEventClick}
          onPersonClick={handlePersonClick}
          onLocationClick={handleLocationClick}
          onOpenStory={handleOpenStory}
          onFlyToLocation={flyToLocation}
          onSetCurrentYear={setCurrentYear}
          onStartTour={(episode) => setTourEpisode(episode)}
          onOpenTimeline={() => setIsTimelineOpen(true)}
          onOpenShowcase={() => setShowShowcase(true)}
        />

        {/* Footer */}
        <div className="sidebar-footer">
          <div className="footer-links">
            <button onClick={() => setIsTermsOpen(true)}>{t('legal.terms.link', 'Terms')}</button>
            <span className="footer-divider">|</span>
            <button onClick={() => setIsPrivacyOpen(true)}>{t('legal.privacy.link', 'Privacy')}</button>
            <span className="footer-divider">|</span>
            <span className="footer-attribution">Data: Wikipedia (CC BY-SA)</span>
          </div>
        </div>
      </aside>

      {/* Center - Globe / Map */}
      <main className="globe-section" role="main" aria-label="Interactive historical globe">
        <div className="globe-overlay-top">
          <div className="globe-control-group">
            <div className="globe-control">
              {t('globe.camMode')}: <span>{t('globe.orbit')}</span>
            </div>
            <button
              className="hierarchy-explore-btn"
              onClick={() => { setHierarchyEventId(undefined); setIsHierarchyOpen(true) }}
            >
              Explore Eras
            </button>
          </div>
          <div className="globe-style-selector">
            {GLOBE_STYLE_KEYS.map((styleKey) => (
              <button
                key={styleKey}
                className={`globe-style-btn ${globeStyle === styleKey ? 'active' : ''}`}
                onClick={() => setGlobeStyle(styleKey)}
              >
                {t(`globe.styles.${styleKey}`)}
              </button>
            ))}
          </div>
        </div>

        {/* Globe view layer */}
        <div className={`view-layer ${viewMode === 'globe' ? 'view-active' : 'view-hidden'}`}>
          <Suspense fallback={<GlobeLoader />}>
            <GlobeContainer
              onEventClick={handleEventClick}
              onPersonClick={handlePersonClick}
              onLocationClick={handleLocationClick}
              globeStyle={globeStyle}
            />
          </Suspense>
        </div>

        {/* Map view layer */}
        <div className={`view-layer ${viewMode === 'map' ? 'view-active' : 'view-hidden'}`}>
          {viewMode === 'map' && (
            <Suspense fallback={<GlobeLoader />}>
              <MapView
                markers={globeMarkers}
                onEventClick={handleEventClick}
                onPersonClick={handlePersonClick}
                onLocationClick={handleLocationClick}
                isShifted={!!selectedEvent}
              />
            </Suspense>
          )}
        </div>

        <div className="globe-overlay-bottom" style={{ bottom: '100px' }}>
          <div className="system-spec">{t('app.systemSpec')}</div>
        </div>

        {/* Unified Timeline */}
        <div className="unified-timeline-wrapper">
          <UnifiedTimeline events={timelineEvents || []} />
        </div>
      </main>

      {/* Right Panel - Event Detail (FGO Style) */}
      <EventDetailPanel
        event={selectedEvent}
        allEvents={timelineEvents || []}
        onClose={handleClosePanel}
        onEventClick={handleEventClick}
        onAskSheba={(query) => {
          setInitialChatQuery(query)
          setIsChatOpen(true)
        }}
        onPersonClick={handlePersonClick}
        onLocationClick={handleLocationClick}
        onOpenHierarchy={(rootEventId) => {
          setHierarchyEventId(rootEventId)
          setIsHierarchyOpen(true)
        }}
      />

      {/* SHEBA Chat Interface */}
      <ChatPanel
        isOpen={isChatOpen}
        onClose={() => {
          setIsChatOpen(false)
          setInitialChatQuery(null)
        }}
        initialQuery={initialChatQuery}
        onQueryProcessed={() => setInitialChatQuery(null)}
      />

      {/* Chat Toggle Button */}
      {!isChatOpen && (
        <button
          className="chat-toggle-btn"
          onClick={() => setIsChatOpen(true)}
          title="Open SHEBA Chat"
          aria-label="Open SHEBA AI Chat"
        >
          {'\u25CE'}
        </button>
      )}

      {/* Settings Page Modal */}
      <SettingsPage
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />

      {/* Legal Pages */}
      {isTermsOpen && <TermsPage onClose={() => setIsTermsOpen(false)} />}
      {isPrivacyOpen && <PrivacyPage onClose={() => setIsPrivacyOpen(false)} />}

      {/* Historical Chain Panel */}
      {isChainOpen && (
        <div className="chain-panel-overlay">
          <div className="chain-panel-container">
            <button
              className="chain-panel-close"
              onClick={() => setIsChainOpen(false)}
            >
              {'\u2715'}
            </button>
            <Suspense fallback={<PanelLoader />}>
              <ChainPanel />
            </Suspense>
          </div>
        </div>
      )}

      {/* Showcase Modal (FGO content viewer) */}
      <ShowcaseModal
        isOpen={showShowcase}
        content={showcaseContent}
        onClose={() => { setShowShowcase(false); setShowcaseContent(null) }}
        onEventClick={handleShowcaseEventClick}
        onPersonClick={handlePersonClick}
        onFlyToLocation={flyToLocation}
        onSetCurrentYear={setCurrentYear}
      />

      {/* Timeline Modal (fullscreen period explorer) */}
      <TimelineModal
        isOpen={isTimelineOpen}
        onClose={() => setIsTimelineOpen(false)}
        onEventClick={async (eventId) => {
          try {
            const res = await api.get(`/events/${eventId}`)
            if (res.data) {
              handleEventClick(res.data)
              setIsTimelineOpen(false)
            }
          } catch (err) {
            console.error('Failed to fetch event from timeline:', err)
          }
        }}
        onPersonClick={(personId) => {
          handlePersonClick(personId)
          setIsTimelineOpen(false)
        }}
        onFlyToLocation={flyToLocation}
        onSetCurrentYear={setCurrentYear}
      />

      {/* Landing Page Overlay (Welcome Experience) */}
      {showLanding && (
        <FeaturedPersons
          onPersonClick={(id) => {
            handlePersonClick(id)
            setShowLanding(false)
            localStorage.setItem('chaldeas-explored', '1')
          }}
          onClose={() => {
            setShowLanding(false)
            localStorage.setItem('chaldeas-explored', '1')
          }}
          onStartTour={(episode) => {
            setTourEpisode(episode)
            setShowLanding(false)
            localStorage.setItem('chaldeas-explored', '1')
          }}
        />
      )}

      {/* Person Detail View */}
      {personDetailId && (
        <Suspense fallback={<PanelLoader />}>
          <PersonDetailView
            personId={personDetailId}
            onClose={handleCloseEntityView}
            onEventClick={handleEventClick}
            onPersonClick={handlePersonClick}
          />
        </Suspense>
      )}

      {/* Location Detail View */}
      {locationDetailId && (
        <Suspense fallback={<PanelLoader />}>
          <LocationDetailView
            locationId={locationDetailId}
            onClose={handleCloseEntityView}
            onEventClick={handleEventClick}
            onLocationClick={handleLocationClick}
          />
        </Suspense>
      )}

      {/* Tour Overlay (Episode Guided Tour) */}
      {tourEpisode && (
        <TourOverlay
          episode={tourEpisode}
          onClose={() => setTourEpisode(null)}
          onFlyToLocation={flyToLocation}
          onSetCurrentYear={setCurrentYear}
        />
      )}

      {/* Story Modal (Person 3D Globe Journey) */}
      {storyPersonId && (
        <StoryModal
          isOpen={true}
          personId={storyPersonId}
          onClose={() => setStoryPersonId(null)}
          onEventClick={(eventId) => {
            handleShowcaseEventClick(eventId)
            setStoryPersonId(null)
          }}
        />
      )}

      {/* Hierarchy Explorer (Fullscreen Era Drill-down) */}
      {isHierarchyOpen && (
        <Suspense fallback={<PanelLoader />}>
          <HierarchyExplorer
            isOpen={isHierarchyOpen}
            onClose={() => setIsHierarchyOpen(false)}
            onEventClick={(event) => {
              handleEventClick(event)
              setIsHierarchyOpen(false)
            }}
            onFlyToLocation={flyToLocation}
            onSetCurrentYear={setCurrentYear}
            initialEventId={hierarchyEventId}
          />
        </Suspense>
      )}
    </div>
  )
}

export default App
