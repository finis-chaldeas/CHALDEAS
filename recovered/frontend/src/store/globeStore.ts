import { create } from 'zustand'
import type { Event, Location, Category } from '../types'

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

  // Filters
  selectedCategories: number[]
  minImportance: number

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
  flyToLocation: (lat: number, lng: number) => void
  clearFlyTarget: () => void
  setHighlightedLocations: (locs: HighlightedLocation[]) => void
  clearHighlightedLocations: () => void
  setCameraMode: (mode: CameraMode) => void
  updateFlyState: (state: Partial<FlyState>) => void
  setViewportBounds: (bounds: ViewportBounds | null) => void
  setViewMode: (mode: ViewMode) => void
  setGlobeMarkers: (markers: GlobeMarkerData[]) => void
  returnToCosmic: () => void
}

export const useGlobeStore = create<GlobeState>((set, get) => ({
  // Initial state
  events: [],
  locations: [],
  categories: [],
  selectedEvent: null,
  hoveredEvent: null,
  cameraPosition: { lat: 30, lng: 20, altitude: 3.0 },
  autoRotate: true,
  highlightedLocations: [],
  cameraMode: 'orbit',
  flyState: { heading: 0, pitch: 0, speed: 1.0 },
  viewMode: 'globe',
  globeMarkers: [],
  viewportBounds: null,
  zoomLevel: 'cosmic',
  flyTarget: null,
  selectedCategories: [],
  minImportance: 1,

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

  returnToCosmic: () =>
    set({
      cameraPosition: { lat: 30, lng: 20, altitude: 3.0 },
      autoRotate: true,
      zoomLevel: 'cosmic',
      viewMode: 'globe',
    }),
}))
