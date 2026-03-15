import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Event, Location, Category, HistoryShift } from '../types'

// Camera mode types
// CHALDEAS = orbit (3D globe), SHEBA = map (2D Leaflet), Fly = WASD navigation
export type CameraMode = 'orbit' | 'fly' | 'map'

// View mode: 3D globe or 2D map
export type ViewMode = 'globe' | 'map'

// Zoom level derived from altitude (4-level system)
export type ZoomLevel = 'cosmic' | 'continental' | 'regional' | 'local'

// Globe → Map transition removed: manual camera mode switching only

export const ZOOM_THRESHOLDS = {
  COSMIC: 2.5,
  CONTINENTAL: 1.0,
  REGIONAL: 0.3,
  LOCAL: 0,
} as const

// Globe marker type (shared between Globe and Map views)
export interface GlobeMarkerData {
  id: number
  type: 'event' | 'person' | 'location'
  lat: number
  lng: number
  year: number | null
  year_end: number | null
  category: string | null
  title: string
  description: string | null
  certainty: string | null
  color: string | null
  importance: number | null
}

// Convert globe altitude to Leaflet zoom level
export function altitudeToLeafletZoom(altitude: number): number {
  // Mapping: altitude 0.15 → zoom 8, 0.10 → 11, 0.05 → 14, 0.02 → 16
  // Using logarithmic mapping: zoom ≈ -14.5 * ln(altitude) + 5.5
  const zoom = -14.5 * Math.log(altitude) + 5.5
  return Math.max(3, Math.min(18, Math.round(zoom)))
}

// Convert Leaflet zoom level to approximate globe altitude
export function leafletZoomToAltitude(zoom: number): number {
  // Inverse of above: altitude ≈ exp((5.5 - zoom) / 14.5)
  return Math.exp((5.5 - zoom) / 14.5)
}

export function getZoomLevel(altitude: number): ZoomLevel {
  if (altitude > ZOOM_THRESHOLDS.COSMIC) return 'cosmic'
  if (altitude > ZOOM_THRESHOLDS.CONTINENTAL) return 'continental'
  if (altitude > ZOOM_THRESHOLDS.REGIONAL) return 'regional'
  return 'local'
}

interface CameraPosition {
  lat: number
  lng: number
  altitude: number
}

// Fly mode state for WASD navigation
interface FlyState {
  heading: number  // degrees, 0 = north
  pitch: number    // degrees, 0 = level
  speed: number    // movement speed multiplier
}

interface FlyTarget {
  lat: number
  lng: number
  altitude: number
  ts: number  // timestamp to detect new fly commands
}

interface HighlightedLocation {
  title: string
  lat: number
  lng: number
  year?: number
}

export interface PinnedEvent {
  id: number
  title: string
  title_ko?: string
  title_ja?: string
  lat: number
  lng: number
  year?: number
  category?: string
  importance: number
}

export interface ViewportBounds {
  north: number
  south: number
  east: number
  west: number
}

interface GlobeState {
  // Data
  events: Event[]
  locations: Location[]
  categories: Category[]

  // UI State
  selectedEvent: Event | null
  hoveredEvent: Event | null
  cameraPosition: CameraPosition
  autoRotate: boolean
  highlightedLocations: HighlightedLocation[]
  cameraMode: CameraMode
  flyState: FlyState

  // View mode (globe/map)
  viewMode: ViewMode
  globeMarkers: GlobeMarkerData[]

  // Viewport tracking
  viewportBounds: ViewportBounds | null
  zoomLevel: ZoomLevel

  // Fly-to target (consumed by GlobeContainer)
  flyTarget: FlyTarget | null

  // Pinned event (clicked from badge modal → shown as solo hero on globe)
  pinnedEvent: PinnedEvent | null

  // Rayshift steps overlay
  rayshiftSteps: { lat: number; lng: number; label: string }[] | null

  // History Shift state
  activeShift: HistoryShift | null
  activePageIndex: number
  shiftMaxAltitude: number | null  // zoom-out limit when shift is active

  // Filters
  selectedCategories: number[]
  minImportance: number
  showMinorMarkers: boolean

  // Actions
  setEvents: (events: Event[]) => void
  setLocations: (locations: Location[]) => void
  setCategories: (categories: Category[]) => void
  setSelectedEvent: (event: Event | null) => void
  setHoveredEvent: (event: Event | null) => void
  setCameraPosition: (position: Partial<CameraPosition>) => void
  setAutoRotate: (rotate: boolean) => void
  toggleCategory: (categoryId: number) => void
  setMinImportance: (importance: number) => void
  toggleMinorMarkers: () => void
  flyToLocation: (lat: number, lng: number) => void
  clearFlyTarget: () => void
  setHighlightedLocations: (locs: HighlightedLocation[]) => void
  clearHighlightedLocations: () => void
  setCameraMode: (mode: CameraMode) => void
  updateFlyState: (state: Partial<FlyState>) => void
  setViewportBounds: (bounds: ViewportBounds | null) => void
  setViewMode: (mode: ViewMode) => void
  setGlobeMarkers: (markers: GlobeMarkerData[]) => void
  setPinnedEvent: (event: PinnedEvent) => void
  clearPinnedEvent: () => void
  setRayshiftSteps: (steps: { lat: number; lng: number; label: string }[]) => void
  clearRayshiftSteps: () => void
  returnToCosmic: () => void

  // Shift actions
  openShift: (shift: HistoryShift) => void
  closeShift: () => void
  goToPage: (index: number) => void
  nextPage: () => void
  prevPage: () => void
}

export const useGlobeStore = create<GlobeState>()(
  persist(
    (set, get) => ({
  // Initial state
  events: [],
  locations: [],
  categories: [],
  selectedEvent: null,
  hoveredEvent: null,
  cameraPosition: { lat: 30, lng: 20, altitude: 3.0 },
  autoRotate: false,
  highlightedLocations: [],
  cameraMode: 'orbit',
  flyState: { heading: 0, pitch: 0, speed: 1.0 },
  viewMode: 'globe',
  globeMarkers: [],
  viewportBounds: null,
  zoomLevel: 'cosmic',
  flyTarget: null,
  pinnedEvent: null,
  rayshiftSteps: null,
  activeShift: null,
  activePageIndex: 0,
  shiftMaxAltitude: null,
  selectedCategories: [],
  minImportance: 1,
  showMinorMarkers: false,

  // Actions
  setEvents: (events) => set({ events }),

  setLocations: (locations) => set({ locations }),

  setCategories: (categories) => set({ categories }),

  setSelectedEvent: (event) => {
    set({ selectedEvent: event, autoRotate: false })
    if (event?.location) {
      get().flyToLocation(event.location.latitude, event.location.longitude)
    }
  },

  setHoveredEvent: (event) => set({ hoveredEvent: event }),

  setCameraPosition: (position) =>
    set((state) => ({
      cameraPosition: { ...state.cameraPosition, ...position },
    })),

  setAutoRotate: (rotate) => set({ autoRotate: rotate }),

  toggleCategory: (categoryId) =>
    set((state) => {
      const categories = state.selectedCategories.includes(categoryId)
        ? state.selectedCategories.filter((id) => id !== categoryId)
        : [...state.selectedCategories, categoryId]
      return { selectedCategories: categories }
    }),

  setMinImportance: (importance) => set({ minImportance: importance }),

  toggleMinorMarkers: () => set((state) => ({ showMinorMarkers: !state.showMinorMarkers })),

  flyToLocation: (lat, lng) =>
    set({
      cameraPosition: { lat, lng, altitude: 1.5 },
      flyTarget: { lat, lng, altitude: 1.5, ts: Date.now() },
    }),

  clearFlyTarget: () => set({ flyTarget: null }),

  setHighlightedLocations: (locs) => {
    set({ highlightedLocations: locs })
    // Auto fly to first highlighted location
    if (locs.length > 0) {
      set({
        cameraPosition: { lat: locs[0].lat, lng: locs[0].lng, altitude: 1.5 },
        autoRotate: false,
      })
    }
  },

  clearHighlightedLocations: () => set({ highlightedLocations: [] }),

  setCameraMode: (mode) => {
    // Map mode = 2D Leaflet view, orbit/fly = 3D globe
    const newViewMode = mode === 'map' ? 'map' : 'globe'
    set({ cameraMode: mode, viewMode: newViewMode })
    if (mode === 'fly' || mode === 'map') {
      set({ autoRotate: false })
    }
  },

  updateFlyState: (state) =>
    set((prev) => ({
      flyState: { ...prev.flyState, ...state },
    })),

  setViewportBounds: (bounds) => {
    const altitude = get().cameraPosition.altitude
    const zoomLevel = getZoomLevel(altitude)
    // No auto viewMode transition — manual camera mode switching only
    set({ viewportBounds: bounds, zoomLevel })
  },

  setViewMode: (mode) => set({ viewMode: mode }),

  setGlobeMarkers: (markers) => set({ globeMarkers: markers }),

  setPinnedEvent: (event) => set({ pinnedEvent: event }),

  clearPinnedEvent: () => set({ pinnedEvent: null }),

  setRayshiftSteps: (steps) => set({ rayshiftSteps: steps }),

  clearRayshiftSteps: () => set({ rayshiftSteps: null }),

  returnToCosmic: () =>
    set({
      cameraPosition: { lat: 30, lng: 20, altitude: 3.0 },
      autoRotate: false,
      zoomLevel: 'cosmic',
      viewMode: 'globe',
    }),

  // Shift actions
  openShift: (shift) => {
    set({ activeShift: shift, activePageIndex: 0, autoRotate: false })
    // Fly to fit all page locations
    const coords = (shift.pages || [])
      .filter(p => p.lat != null && p.lng != null)
      .map(p => ({ lat: p.lat!, lng: p.lng! }))
    if (coords.length === 0) return

    // Calculate bounding box
    const lats = coords.map(c => c.lat)
    const lngs = coords.map(c => c.lng)
    const centerLat = (Math.min(...lats) + Math.max(...lats)) / 2
    const centerLng = (Math.min(...lngs) + Math.max(...lngs)) / 2
    const latSpan = Math.max(...lats) - Math.min(...lats)
    const lngSpan = Math.max(...lngs) - Math.min(...lngs)
    const maxSpan = Math.max(latSpan, lngSpan)

    // Altitude formula: events should fill ~60% of the visible globe face
    // At altitude a, visible cone ≈ 2·arccos(1/(1+a))
    // Linear mapping: span → altitude, tuned so events dominate the screen
    //   span  0° → 0.08  (same-location: close regional view)
    //   span 10° → 0.12  (single country)
    //   span 30° → 0.26  (continental)
    //   span 45° → 0.37  (Punic Wars: Mediterranean fills screen)
    //   span 90° → 0.68  (global)
    //   span 180° → 1.31  (whole world)
    const altitude = Math.max(0.08, Math.min(1.5, 0.05 + maxSpan * 0.007))

    set({
      shiftMaxAltitude: altitude,
      cameraPosition: { lat: centerLat, lng: centerLng, altitude },
      flyTarget: { lat: centerLat, lng: centerLng, altitude, ts: Date.now() },
    })
  },

  closeShift: () => set({ activeShift: null, activePageIndex: 0, shiftMaxAltitude: null }),

  goToPage: (index) => {
    const shift = get().activeShift
    if (!shift?.pages) return
    const clamped = Math.max(0, Math.min(index, shift.pages.length - 1))
    set({ activePageIndex: clamped })
    const page = shift.pages[clamped]
    if (page?.lat != null && page?.lng != null) {
      // Use page-specific altitude if provided, otherwise keep current
      const altitude = page.camera_altitude ?? get().cameraPosition.altitude
      // Raise shiftMaxAltitude if page needs a higher zoom-out
      const currentMax = get().shiftMaxAltitude
      if (currentMax != null && altitude > currentMax) {
        set({ shiftMaxAltitude: altitude })
      }
      set({
        flyTarget: { lat: page.lat, lng: page.lng, altitude, ts: Date.now() },
      })
    }
  },

  nextPage: () => {
    const { activeShift, activePageIndex } = get()
    if (!activeShift?.pages) return
    if (activePageIndex < activeShift.pages.length - 1) {
      get().goToPage(activePageIndex + 1)
    }
  },

  prevPage: () => {
    const { activePageIndex } = get()
    if (activePageIndex > 0) {
      get().goToPage(activePageIndex - 1)
    }
  },
    }),
    {
      name: 'chaldeas-globe',
      partialize: (state) => ({
        cameraPosition: state.cameraPosition,
        cameraMode: state.cameraMode,
      }),
    }
  )
)
