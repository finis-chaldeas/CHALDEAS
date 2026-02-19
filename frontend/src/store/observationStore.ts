/**
 * Observation Store - Tracks what the user has viewed for personalized recommendations.
 *
 * Records categories, regions, eras, and recent view history using Zustand persist.
 * Used by FeedInterest to generate context-aware recommendations.
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ViewRecord {
  type: 'event' | 'person'
  id: number
  timestamp: number
}

interface ObservationState {
  // Aggregated view counts
  viewedCategories: Record<string, number>
  viewedRegions: Record<string, number>
  viewedEras: Record<string, number>

  // Recent views (last 100)
  recentViews: ViewRecord[]

  // Actions
  recordEventView: (eventId: number, category?: string, region?: string, era?: string) => void
  recordPersonView: (personId: number, region?: string, era?: string) => void
  hasViewed: (type: 'event' | 'person', id: number) => boolean
  getTopRegion: () => string | null
  getTopCategory: () => string | null
  getTopEra: () => string | null
  clearHistory: () => void
}

const MAX_RECENT = 100

function getEraFromYear(year: number): string {
  if (year < -500) return 'ancient'
  if (year < 500) return 'classical'
  if (year < 1500) return 'medieval'
  if (year < 1800) return 'early_modern'
  if (year < 1945) return 'modern'
  return 'contemporary'
}

function incrementCount(record: Record<string, number>, key: string): Record<string, number> {
  return { ...record, [key]: (record[key] || 0) + 1 }
}

function getTopKey(record: Record<string, number>): string | null {
  const entries = Object.entries(record)
  if (entries.length === 0) return null
  entries.sort((a, b) => b[1] - a[1])
  return entries[0][0]
}

export { getEraFromYear }

export const useObservationStore = create<ObservationState>()(
  persist(
    (set, get) => ({
      viewedCategories: {},
      viewedRegions: {},
      viewedEras: {},
      recentViews: [],

      recordEventView: (eventId, category, region, era) => {
        set((state) => {
          const newRecent: ViewRecord = { type: 'event', id: eventId, timestamp: Date.now() }
          const recentViews = [newRecent, ...state.recentViews].slice(0, MAX_RECENT)
          let viewedCategories = state.viewedCategories
          let viewedRegions = state.viewedRegions
          let viewedEras = state.viewedEras
          if (category) viewedCategories = incrementCount(viewedCategories, category)
          if (region) viewedRegions = incrementCount(viewedRegions, region)
          if (era) viewedEras = incrementCount(viewedEras, era)
          return { recentViews, viewedCategories, viewedRegions, viewedEras }
        })
      },

      recordPersonView: (personId, region, era) => {
        set((state) => {
          const newRecent: ViewRecord = { type: 'person', id: personId, timestamp: Date.now() }
          const recentViews = [newRecent, ...state.recentViews].slice(0, MAX_RECENT)
          let viewedRegions = state.viewedRegions
          let viewedEras = state.viewedEras
          if (region) viewedRegions = incrementCount(viewedRegions, region)
          if (era) viewedEras = incrementCount(viewedEras, era)
          return { recentViews, viewedRegions, viewedEras }
        })
      },

      hasViewed: (type, id) => {
        return get().recentViews.some(v => v.type === type && v.id === id)
      },

      getTopRegion: () => getTopKey(get().viewedRegions),
      getTopCategory: () => getTopKey(get().viewedCategories),
      getTopEra: () => getTopKey(get().viewedEras),

      clearHistory: () => set({
        viewedCategories: {},
        viewedRegions: {},
        viewedEras: {},
        recentViews: [],
      }),
    }),
    {
      name: 'chaldeas-observations',
      version: 1,
    }
  )
)
