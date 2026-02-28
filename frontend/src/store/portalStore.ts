import { create } from 'zustand'
import type { PortalLayer } from '../types'

export type PageKey = 'front' | 'fgo' | 'reading' | 'collections'

interface PortalStore {
  isOpen: boolean
  layers: PortalLayer[]
  activePage: PageKey
  previewSlug: string | null

  // Suspend/resume for Globe View round-trips
  isSuspended: boolean
  suspendedLayers: PortalLayer[]
  suspendedPage: PageKey
  suspendedPreview: string | null

  // Globe context passed on open
  globeContext: GlobeContext | null

  open: (context?: GlobeContext) => void
  close: () => void
  suspend: () => void
  resume: () => void
  setActivePage: (page: PageKey) => void
  pushCollection: (slug: string) => void
  pushDetail: (slug: string) => void
  pop: () => void
  popToHome: () => void
  openPreview: (slug: string) => void
  closePreview: () => void
}

export interface GlobeContext {
  lat: number
  lng: number
  year: number
}

const SCROLL_CONTAINER_CLASS = 'portal-scroll'

function getCurrentScrollY(): number {
  const el = document.querySelector(`.${SCROLL_CONTAINER_CLASS}`)
  return el ? el.scrollTop : 0
}

export const usePortalStore = create<PortalStore>((set, get) => ({
  isOpen: false,
  layers: [],
  activePage: 'front',
  previewSlug: null,

  isSuspended: false,
  suspendedLayers: [],
  suspendedPage: 'front',
  suspendedPreview: null,

  globeContext: null,

  open: (context?: GlobeContext) => {
    const { isSuspended } = get()
    if (isSuspended) {
      // Resume from suspended state
      get().resume()
    } else {
      set({
        isOpen: true,
        layers: [{ type: 'home' }],
        activePage: 'front',
        previewSlug: null,
        globeContext: context || null,
      })
    }
  },

  close: () => set({
    isOpen: false,
    layers: [],
    activePage: 'front',
    previewSlug: null,
    isSuspended: false,
    suspendedLayers: [],
    suspendedPage: 'front',
    suspendedPreview: null,
    globeContext: null,
  }),

  suspend: () => {
    const { layers, activePage, previewSlug } = get()
    set({
      isOpen: false,
      isSuspended: true,
      suspendedLayers: layers,
      suspendedPage: activePage,
      suspendedPreview: previewSlug,
      previewSlug: null,
    })
  },

  resume: () => {
    const { suspendedLayers, suspendedPage, suspendedPreview } = get()
    set({
      isOpen: true,
      isSuspended: false,
      layers: suspendedLayers.length > 0 ? suspendedLayers : [{ type: 'home' }],
      activePage: suspendedPage,
      previewSlug: suspendedPreview,
      suspendedLayers: [],
      suspendedPage: 'front',
      suspendedPreview: null,
    })
  },

  setActivePage: (page: PageKey) => set({ activePage: page }),

  pushCollection: (slug: string) => {
    const { layers } = get()
    const updated = layers.map((l, i) =>
      i === layers.length - 1 ? { ...l, scrollY: getCurrentScrollY() } : l
    )
    set({ layers: [...updated, { type: 'collection' as const, slug }] })
  },

  pushDetail: (slug: string) => {
    const { layers } = get()
    const updated = layers.map((l, i) =>
      i === layers.length - 1 ? { ...l, scrollY: getCurrentScrollY() } : l
    )
    set({ layers: [...updated, { type: 'detail' as const, slug }] })
  },

  pop: () => {
    const { layers, close } = get()
    if (layers.length <= 1) {
      close()
    } else {
      set({ layers: layers.slice(0, -1) })
    }
  },

  popToHome: () => set({ layers: [{ type: 'home' }], previewSlug: null }),

  openPreview: (slug: string) => set({ previewSlug: slug }),

  closePreview: () => set({ previewSlug: null }),
}))
