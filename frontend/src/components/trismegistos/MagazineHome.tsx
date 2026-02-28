import { useQuery } from '@tanstack/react-query'
import { usePortalStore, type PageKey } from '../../store/portalStore'
import { portalApi } from '../../api/client'
import type { PortalFeaturedResponse, PortalItemSummary, CollectionSummary } from '../../types'
import { TodayHero } from './TodayHero'
import { RecommendationRow } from './RecommendationRow'
import { FgoSection } from './FgoSection'
import { ReadingSection } from './ReadingSection'
import { CollectionGrid } from './CollectionGrid'

const PAGES: { key: PageKey; label: string }[] = [
  { key: 'front', label: 'Front Page' },
  { key: 'fgo', label: 'Fate/Grand Order' },
  { key: 'reading', label: 'Reading' },
  { key: 'collections', label: 'Collections' },
]

interface GlobeViewOptions {
  year: number
  eventId?: number
}

interface Props {
  onGlobeView: (opts: GlobeViewOptions) => void
  onOpenShift: (shiftId: number) => void
}

export function MagazineHome({ onGlobeView, onOpenShift }: Props) {
  const activePage = usePortalStore((s) => s.activePage)
  const setActivePage = usePortalStore((s) => s.setActivePage)
  const close = usePortalStore((s) => s.close)
  const suspend = usePortalStore((s) => s.suspend)
  const globeContext = usePortalStore((s) => s.globeContext)

  // Featured data (hero + recommendations)
  const { data: featured } = useQuery<PortalFeaturedResponse>({
    queryKey: ['portal-featured'],
    queryFn: async () => {
      const res = await portalApi.getFeatured()
      return res.data
    },
    staleTime: 5 * 60 * 1000,
  })

  // FGO items
  const { data: fgoItems } = useQuery<PortalItemSummary[]>({
    queryKey: ['portal-items-fgo'],
    queryFn: async () => {
      const res = await portalApi.listItems({ item_type: 'singularity,lostbelt,servant_column' })
      return res.data
    },
    staleTime: 5 * 60 * 1000,
  })

  // Reading items
  const { data: readingItems } = useQuery<PortalItemSummary[]>({
    queryKey: ['portal-items-reading'],
    queryFn: async () => {
      const res = await portalApi.listItems({ item_type: 'history,literature,music' })
      return res.data
    },
    staleTime: 5 * 60 * 1000,
  })

  // Collections
  const { data: collections } = useQuery<CollectionSummary[]>({
    queryKey: ['portal-collections'],
    queryFn: async () => {
      const res = await portalApi.listCollections()
      return res.data
    },
    staleTime: 5 * 60 * 1000,
  })

  return (
    <div className="portal-modal">
      <div className="portal-header">
        <div className="portal-header__left">
          <span className="portal-header__title">Trismegistos</span>
        </div>
        <button className="portal-header__close" onClick={close}>{'\u2715'}</button>
      </div>

      {/* Newspaper section tabs */}
      <div className="portal-tabs-border">
        <div className="portal-tabs">
          {PAGES.map(({ key, label }) => (
            <button
              key={key}
              className={`portal-tab ${activePage === key ? 'portal-tab--active' : ''}`}
              onClick={() => setActivePage(key)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="portal-scroll">
        <div className="portal-magazine">
          {activePage === 'front' && (
            <>
              {globeContext && (
                <div className="portal-context-banner">
                  <span className="portal-context-banner__text">
                    Viewing: {formatYear(globeContext.year)}
                  </span>
                  <button
                    className="portal-context-banner__return"
                    onClick={() => suspend()}
                  >
                    Return to Globe {'\u2192'}
                  </button>
                </div>
              )}
              <TodayHero
                items={featured?.items || []}
                onGlobeView={onGlobeView}
              />
              {featured?.recommendations && featured.recommendations.length > 0 && (
                <div className="portal-section">
                  <div className="portal-section__title">Recommended</div>
                  <RecommendationRow
                    items={featured.recommendations}
                    onOpenShift={onOpenShift}
                  />
                </div>
              )}
            </>
          )}

          {activePage === 'fgo' && fgoItems && fgoItems.length > 0 && (
            <FgoSection items={fgoItems} />
          )}

          {activePage === 'reading' && readingItems && readingItems.length > 0 && (
            <div className="portal-section">
              <div className="portal-section__title">Reading</div>
              <ReadingSection items={readingItems} />
            </div>
          )}

          {activePage === 'collections' && collections && collections.length > 0 && (
            <div className="portal-section">
              <div className="portal-section__title">Collections</div>
              <CollectionGrid collections={collections} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}
