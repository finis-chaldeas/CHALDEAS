import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { usePortalStore, type PageKey } from '../../store/portalStore'
import { portalApi } from '../../api/client'
import type { PortalFeaturedResponse, PortalItemSummary } from '../../types'
import { TodayHero } from './TodayHero'
import { RecommendationRow } from './RecommendationRow'
import { FgoSection } from './FgoSection'
import { HistoryMagazine } from './HistoryMagazine'
import { EraExplorer } from './EraExplorer'

const TAB_KEYS: { key: PageKey; i18nKey: string }[] = [
  { key: 'front', i18nKey: 'trismegistos.tabs.frontPage' },
  { key: 'fgo', i18nKey: 'trismegistos.tabs.fgo' },
  { key: 'magazine', i18nKey: 'trismegistos.tabs.magazine' },
  { key: 'eraExplorer', i18nKey: 'trismegistos.tabs.eraExplorer' },
]

interface GlobeViewOptions {
  year: number
  eventId?: number
}

interface Props {
  onGlobeView: (opts: GlobeViewOptions) => void
  onOpenShift: (shiftId: number) => void
  onEventClick?: (eventId: number) => void
  onPersonClick?: (personId: number) => void
}

export function MagazineHome({ onGlobeView, onOpenShift, onEventClick, onPersonClick }: Props) {
  const { t } = useTranslation()
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
          {TAB_KEYS.map(({ key, i18nKey }) => (
            <button
              key={key}
              className={`portal-tab ${activePage === key ? 'portal-tab--active' : ''}`}
              onClick={() => setActivePage(key)}
            >
              {t(i18nKey)}
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
            <FgoSection items={fgoItems} onOpenShift={onOpenShift} />
          )}

          {activePage === 'magazine' && (
            <HistoryMagazine
              onGlobeView={onGlobeView}
              onOpenShift={onOpenShift}
              onPersonClick={onPersonClick}
            />
          )}

          {activePage === 'eraExplorer' && (
            <EraExplorer
              onGlobeView={onGlobeView}
              onOpenShift={onOpenShift}
              onEventClick={onEventClick}
              onPersonClick={onPersonClick}
            />
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
