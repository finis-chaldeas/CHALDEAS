import { create } from 'zustand'

export type CardType = 'person' | 'event' | 'location' | 'servant' | 'shift'
export type CardMode = 'compact' | 'expanded'

interface CardPopupState {
  isOpen: boolean
  type: CardType | null
  entityId: number | null
  mode: CardMode
  position: { x: number; y: number } | null

  openCard: (
    type: CardType,
    id: number,
    opts?: { mode?: CardMode; position?: { x: number; y: number } }
  ) => void
  expandCard: () => void
  closeCard: () => void
}

export const useCardPopup = create<CardPopupState>()((set) => ({
  isOpen: false,
  type: null,
  entityId: null,
  mode: 'compact',
  position: null,

  openCard: (type, id, opts) =>
    set({
      isOpen: true,
      type,
      entityId: id,
      mode: opts?.mode ?? 'compact',
      position: opts?.position ?? null,
    }),

  expandCard: () => set({ mode: 'expanded' }),

  closeCard: () =>
    set({
      isOpen: false,
      type: null,
      entityId: null,
      mode: 'compact',
      position: null,
    }),
}))
