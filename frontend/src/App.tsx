import { useState, useEffect, lazy, Suspense } from 'react'
import { useTranslation } from 'react-i18next'
import { MobileLayout } from './components/mobile/MobileLayout'
import { ChatPanel } from './components/chat'
import { ShowcaseModal } from './components/showcase'
import type { ShowcaseContent } from './components/showcase'
import { SearchAutocomplete } from './components/search'
import { UnifiedTimeline } from './components/timeline'
import { SettingsPage } from './components/settings'
import { TermsPage, PrivacyPage } from './pages'
import { FeaturedPersons } from './components/landing'
import { StoryModal } from './components/story/StoryModal'
import { TimelineModal } from './components/navigator/TimelineModal'
import { TourOverlay } from './components/tour'
import { HistoryViewer, HistoryEditor } from './components/history'
import { NarrativePanel } from './components/narrative'
import { SourceBrowser } from './components/sources'
import { loadJourney } from './utils/journeyLoader'
import WorldBriefing from './components/globe/WorldBriefing'
import ViewportFeed from './components/globe/ViewportFeed'
import FloatingButtons from './components/globe/FloatingButtons'
import EraFeed from './components/globe/EraFeed'
import DeepReadModal from './components/navigator/DeepReadModal'
import type { ShebaEpisode } from './data/shebaEpisodes'
import { useTimelineStore } from './store/timelineStore'
import { useGlobeStore } from './store/globeStore'
import { useSettingsStore } from './store/settingsStore'
import { useObservationStore, getEraFromYear } from './store/observationStore'
import { useQuery } from '@tanstack/react-query'
import { api, locationsApi, shiftsApi } from './api/client'
import type { Event } from './types'

// Lazy load heavy components (Three.js/Globe, panels)
const GlobeContainer = lazy(() => import('./components/globe/GlobeContainer').then(m => ({ default: m.GlobeContainer })))
// MapView removed — 2D map view disabled (no proper support yet)
const LocationDetailView = lazy(() => import('./components/detail/LocationDetailView').then(m => ({ default: m.LocationDetailView })))
const ChainPanel = lazy(() => import('./components/chain/ChainPanel'))
const HierarchyExplorer = lazy(() => import('./components/hierarchy/HierarchyExplorer').then(m => ({ default: m.HierarchyExplorer })))
const ShiftPanel = lazy(() => import('./components/shift/ShiftPanel'))
const ShiftBrowser = lazy(() => import('./components/shift/ShiftBrowser'))

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

function useIsMobile(breakpoint = 768) {
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < breakpoint)
  useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${breakpoint - 1}px)`)
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches)
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [breakpoint])
  return isMobile
}

function App() {
  const { t } = useTranslation()
  const isMobile = useIsMobile()
  const { currentYear, setCurrentYear } = useTimelineStore()
  const { selectedEvent, setSelectedEvent, flyToLocation, globeMarkers, activeShift, openShift } = useGlobeStore()
  const { globeStyle } = useSettingsStore()
  const { recordEventView, recordPersonView } = useObservationStore()
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isTermsOpen, setIsTermsOpen] = useState(false)
  const [isPrivacyOpen, setIsPrivacyOpen] = useState(false)
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [initialChatQuery, setInitialChatQuery] = useState<string | null>(null)
  const [isChainOpen, setIsChainOpen] = useState(false)
  const [, setPersonDetailId] = useState<number | null>(null)
  const [locationDetailId, setLocationDetailId] = useState<number | null>(null)
  const [showLanding, setShowLanding] = useState(() => !localStorage.getItem('chaldeas-explored'))
  const [showcaseContent, setShowcaseContent] = useState<ShowcaseContent | null>(null)
  const [showShowcase, setShowShowcase] = useState(false)
  const [isTimelineOpen, setIsTimelineOpen] = useState(false)
  const [storyPersonId, setStoryPersonId] = useState<number | null>(null)
  const [tourEpisode, setTourEpisode] = useState<ShebaEpisode | null>(null)
  const [isHierarchyOpen, setIsHierarchyOpen] = useState(false)
  const [hierarchyEventId] = useState<number | undefined>(undefined)
  const [historyViewId, setHistoryViewId] = useState<number | null>(null)
  const [isHistoryEditorOpen, setIsHistoryEditorOpen] = useState(false)
  const [editingHistoryId, setEditingHistoryId] = useState<number | null>(null)
  const [isDeepReadOpen, setIsDeepReadOpen] = useState(false)
  const [isSourceBrowserOpen, setIsSourceBrowserOpen] = useState(false)
  const [sourceBrowserSourceId, setSourceBrowserSourceId] = useState<number | null>(null)
  const [narrativeEventId, setNarrativeEventId] = useState<number | null>(null)
  const [narrativePersonId, setNarrativePersonId] = useState<number | null>(null)
  const [isSearchOpen, setIsSearchOpen] = useState(false)

  // Shift browser state
  const [isShiftBrowserOpen, setIsShiftBrowserOpen] = useState(false)

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

  // Narrative panel location click: close event modal + fly to location + open LocationDetailView
  const handleNarrativeLocationClick = async (locationId: number) => {
    try {
      // Close event/person panels
      setNarrativeEventId(null)
      setNarrativePersonId(null)
      setSelectedEvent(null)
      // Open LocationDetailView on the right
      setLocationDetailId(locationId)
      // Fly globe to location
      const res = await locationsApi.get(locationId)
      const loc = res.data
      if (loc?.latitude && loc?.longitude) {
        flyToLocation(loc.latitude, loc.longitude)
      }
    } catch (err) {
      console.error('Failed to fetch location:', err)
    }
  }

  const handleCloseEntityView = () => {
    setPersonDetailId(null)
    setLocationDetailId(null)
  }

  // handleOpenStory moved inline where needed

  const handleEventClick = (event: Event) => {
    const numericId = typeof event.id === 'number' ? event.id : parseInt(String(event.id), 10)
    setNarrativeEventId(numericId)
    setNarrativePersonId(null)
    setPersonDetailId(null)
    setLocationDetailId(null)
    setSelectedEvent(event)
    setCurrentYear(event.date_start)
    recordEventView(
      numericId,
      typeof event.category === 'string' ? event.category : event.category?.name,
      undefined,
      getEraFromYear(event.date_start)
    )
  }

  // Narrative panel: event click by ID
  const handleNarrativeEventClick = async (eventId: number) => {
    try {
      const res = await api.get(`/events/${eventId}`)
      if (res.data) handleEventClick(res.data)
    } catch (err) {
      console.error('Failed to fetch event:', err)
    }
  }

  // Narrative panel: person click
  const handleNarrativePersonClick = (personId: number) => {
    setNarrativePersonId(personId)
    setNarrativeEventId(null)
    setSelectedEvent(null)
    setPersonDetailId(null)
    setLocationDetailId(null)
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

  // Fetch events for timeline
  const { data: timelineEvents } = useQuery({
    queryKey: ['timeline-events', Math.round(currentYear / 50) * 50],
    queryFn: () => api.get('/events', {
      params: { year_start: currentYear - 50, year_end: currentYear + 50, limit: 500 }
    }),
    select: (res) => res.data?.items || [],
  })

  return (
    <div className="app-container" role="application" aria-label="CHALDEAS Historical Knowledge System">
      {/* Mobile Layout */}
      {isMobile && (
        <MobileLayout
          markers={globeMarkers}
          onEventClick={handleEventClick}
          onPersonClick={handlePersonClick}
          onLocationClick={handleLocationClick}
          onNarrativeEventClick={handleNarrativeEventClick}
          onNarrativePersonClick={handleNarrativePersonClick}
          onSearchOpen={() => setIsSearchOpen(true)}
          onShowcaseOpen={() => setShowShowcase(true)}
          onMenuOpen={() => setIsSettingsOpen(true)}
          onDeepReadOpen={() => setIsDeepReadOpen(true)}
          selectedEvent={selectedEvent}
        />
      )}

      {/* Desktop Layout */}
      {!isMobile && (
        <>
          {/* Globe / Map (fullscreen) */}
          <main className="globe-section" role="main">
            <div className="view-layer view-active">
              <Suspense fallback={<GlobeLoader />}>
                <GlobeContainer
                  onEventClick={handleEventClick}
                  onPersonClick={handlePersonClick}
                  onLocationClick={handleLocationClick}
                  globeStyle={globeStyle}
                />
              </Suspense>
            </div>
            {!activeShift && (
              <div className="unified-timeline-wrapper">
                <UnifiedTimeline events={timelineEvents || []} />
              </div>
            )}
          </main>

          {/* Overlays - outside main so Tailwind fixed works */}
          <WorldBriefing
            onEventClick={handleNarrativeEventClick}
            onPersonClick={handleNarrativePersonClick}
            onOpenDeepRead={() => setIsDeepReadOpen(true)}
          />
          <ViewportFeed
            onEventClick={handleNarrativeEventClick}
            onPersonClick={handleNarrativePersonClick}
          />
          <FloatingButtons
            onSearchClick={() => setIsSearchOpen(true)}
            onShowcaseClick={() => setShowShowcase(true)}
            onRayshiftClick={() => {
              if (activeShift) {
                useGlobeStore.getState().closeShift()
              } else {
                setIsShiftBrowserOpen(true)
              }
            }}
            onChatClick={() => setIsChatOpen(true)}
            onMenuClick={() => setIsSettingsOpen(true)}
          />
          <EraFeed
            onEventClick={handleNarrativeEventClick}
            onPersonClick={handleNarrativePersonClick}
          />
        </>
      )}

      {/* Search Overlay */}
      {isSearchOpen && (
        <div className="search-overlay" onClick={() => setIsSearchOpen(false)}>
          <div className="search-overlay-content" onClick={(e) => e.stopPropagation()}>
            <SearchAutocomplete
              placeholder={t('sidebar.searchPlaceholder', 'Search events, persons, locations...')}
              onSelectEvent={async (eventId) => {
                try {
                  const res = await api.get(`/events/${eventId}`)
                  if (res.data) handleEventClick(res.data)
                  setIsSearchOpen(false)
                } catch (err) {
                  console.error('Failed to fetch event:', err)
                }
              }}
              onSelectPerson={(personId) => {
                handlePersonClick(personId)
                setIsSearchOpen(false)
              }}
              onSelectLocation={(locationId) => {
                handleLocationClick(locationId)
                setIsSearchOpen(false)
              }}
              onSearch={() => {}}
              autoFocus
            />
            <button
              className="search-overlay-close"
              onClick={() => setIsSearchOpen(false)}
            >
              {'\u2715'}
            </button>
          </div>
        </div>
      )}

      {/* Right Panel - Narrative Mode */}
      <NarrativePanel
        selectedEventId={narrativeEventId}
        selectedPersonId={narrativePersonId}
        onClose={() => {
          setNarrativeEventId(null)
          setNarrativePersonId(null)
          setSelectedEvent(null)
        }}
        onEventClick={handleNarrativeEventClick}
        onPersonClick={handleNarrativePersonClick}
        onLocationClick={handleNarrativeLocationClick}
        onSourceClick={(sourceId) => {
          setSourceBrowserSourceId(sourceId)
          setIsSourceBrowserOpen(true)
        }}
        onRayshift={async (mode, entityId) => {
          // Hierarchy: try DB shift first, fallback to on-the-fly
          if (mode === 'hierarchy') {
            try {
              const res = await shiftsApi.list({ chain_type: 'aggregate', limit: 1, focal_event_id: entityId })
              const shifts = res.data?.items || []
              if (shifts.length > 0) {
                const detail = await shiftsApi.get(shifts[0].id)
                if (detail.data?.pages?.length > 0) {
                  openShift(detail.data)
                  return
                }
              }
            } catch { /* fall through */ }
          }
          // All modes: load journey data → open as shift
          try {
            const shift = await loadJourney(mode as 'causal' | 'life' | 'hierarchy', entityId)
            if (shift && shift.pages.length > 0) {
              openShift(shift)
            }
          } catch (err) {
            console.error('Failed to load journey:', err)
          }
        }}
      />

      {/* LAPLACE Chat Interface */}
      <ChatPanel
        isOpen={isChatOpen}
        onClose={() => {
          setIsChatOpen(false)
          setInitialChatQuery(null)
        }}
        initialQuery={initialChatQuery}
        onQueryProcessed={() => setInitialChatQuery(null)}
      />

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

      {/* Showcase Modal (TRISMEGISTUS - FGO content + Era + Reading + Explore) */}
      <ShowcaseModal
        isOpen={showShowcase}
        content={showcaseContent}
        onClose={() => { setShowShowcase(false); setShowcaseContent(null) }}
        onEventClick={handleShowcaseEventClick}
        onPersonClick={handlePersonClick}
        onFlyToLocation={flyToLocation}
        onSetCurrentYear={setCurrentYear}
        onHistoryClick={(historyId) => {
          setHistoryViewId(historyId)
          setShowShowcase(false)
        }}
        onCreateHistory={() => {
          setIsHistoryEditorOpen(true)
          setEditingHistoryId(null)
          setShowShowcase(false)
        }}
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
          onExplore={() => {
            setShowLanding(false)
            localStorage.setItem('chaldeas-explored', '1')
            flyToLocation(37.97, 23.72)
            setCurrentYear(-480)
          }}
          onReadStories={() => {
            setShowLanding(false)
            localStorage.setItem('chaldeas-explored', '1')
            setShowShowcase(true)
          }}
          onClose={() => {
            setShowLanding(false)
            localStorage.setItem('chaldeas-explored', '1')
          }}
        />
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

      {/* History Viewer (right overlay) */}
      {historyViewId && (
        <HistoryViewer
          historyId={historyViewId}
          onClose={() => setHistoryViewId(null)}
          onPersonClick={handlePersonClick}
          onEventClick={(eventId) => {
            api.get(`/events/${eventId}`).then(res => {
              if (res.data) handleEventClick(res.data)
            }).catch(err => console.error('Failed to fetch event:', err))
          }}
          onLocationClick={handleLocationClick}
          onEdit={(id) => {
            setEditingHistoryId(id)
            setIsHistoryEditorOpen(true)
          }}
        />
      )}

      {/* History Editor (modal) */}
      {isHistoryEditorOpen && (
        <HistoryEditor
          historyId={editingHistoryId}
          onClose={() => { setIsHistoryEditorOpen(false); setEditingHistoryId(null) }}
          onSaved={(id) => {
            setHistoryViewId(id)
            setIsHistoryEditorOpen(false)
            setEditingHistoryId(null)
          }}
        />
      )}

      {/* DeepRead Modal */}
      <DeepReadModal
        isOpen={isDeepReadOpen}
        onClose={() => setIsDeepReadOpen(false)}
        onEventClick={(eventId) => {
          handleNarrativeEventClick(eventId)
          setIsDeepReadOpen(false)
        }}
        onPersonClick={(personId) => {
          handleNarrativePersonClick(personId)
          setIsDeepReadOpen(false)
        }}
      />

      {/* Source Browser */}
      <SourceBrowser
        isOpen={isSourceBrowserOpen}
        onClose={() => { setIsSourceBrowserOpen(false); setSourceBrowserSourceId(null) }}
        onPersonClick={(personId) => {
          handleNarrativePersonClick(personId)
        }}
        initialSourceId={sourceBrowserSourceId}
      />

      {/* Shift Panel Modal */}
      {activeShift && (
        <Suspense fallback={<PanelLoader />}>
          <ShiftPanel />
        </Suspense>
      )}

      {/* Shift Browser Modal */}
      <Suspense fallback={null}>
        <ShiftBrowser
          isOpen={isShiftBrowserOpen}
          onClose={() => setIsShiftBrowserOpen(false)}
        />
      </Suspense>

      {/* (Rayshift removed — unified into History Shift system) */}

      {/* Hierarchy Explorer */}
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
