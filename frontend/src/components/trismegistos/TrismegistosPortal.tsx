import { useEffect, useCallback } from 'react'
import { usePortalStore } from '../../store/portalStore'
import { MagazineHome } from './MagazineHome'
import { CollectionPage } from './CollectionPage'
import { PortalItemDetail } from './PortalItemDetail'
import { PreviewPanel } from './PreviewPanel'
import './portal.css'

interface GlobeViewOptions {
  year: number
  eventId?: number
}

interface Props {
  onEventClick: (eventId: number) => void
  onPersonClick: (personId: number) => void
  onFlyToLocation: (lat: number, lng: number) => void
  onGlobeView: (opts: GlobeViewOptions) => void
  onOpenShift: (shiftId: number) => void
}

export default function TrismegistosPortal({
  onEventClick,
  onPersonClick,
  onFlyToLocation,
  onGlobeView,
  onOpenShift,
}: Props) {
  const layers = usePortalStore((s) => s.layers)
  const pop = usePortalStore((s) => s.pop)
  const close = usePortalStore((s) => s.close)
  const previewSlug = usePortalStore((s) => s.previewSlug)
  const closePreview = usePortalStore((s) => s.closePreview)

  // Escape key handler — preview first, then layers, then close
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      if (previewSlug) {
        closePreview()
      } else if (layers.length > 1) {
        pop()
      } else {
        close()
      }
    }
  }, [previewSlug, layers.length, closePreview, pop, close])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  // Restore scroll position when popping back
  useEffect(() => {
    const topLayer = layers[layers.length - 1]
    if (topLayer?.scrollY) {
      requestAnimationFrame(() => {
        const el = document.querySelector('.portal-scroll')
        if (el) el.scrollTop = topLayer.scrollY!
      })
    }
  }, [layers.length]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="portal-backdrop">
      <div className="portal-layer-stack">
        {layers.map((layer, i) => {
          const isTop = i === layers.length - 1
          const className = `portal-layer ${isTop ? 'portal-layer--top' : 'portal-layer--dimmed'}`

          return (
            <div key={`${layer.type}-${layer.slug || 'home'}-${i}`} className={className}>
              {layer.type === 'home' && (
                <MagazineHome
                  onGlobeView={onGlobeView}
                  onOpenShift={onOpenShift}
                />
              )}
              {layer.type === 'collection' && layer.slug && (
                <CollectionPage
                  slug={layer.slug}
                  onEventClick={onEventClick}
                  onPersonClick={onPersonClick}
                  onOpenShift={onOpenShift}
                />
              )}
              {layer.type === 'detail' && layer.slug && (
                <PortalItemDetail
                  slug={layer.slug}
                  onFlyToLocation={onFlyToLocation}
                  onGlobeView={onGlobeView}
                />
              )}
            </div>
          )
        })}
      </div>

      {/* Preview Panel — slide-in from right */}
      {previewSlug && (
        <PreviewPanel
          slug={previewSlug}
          onGlobeView={onGlobeView}
        />
      )}
    </div>
  )
}
