import { useQuery } from '@tanstack/react-query'
import { usePortalStore } from '../../store/portalStore'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import { portalApi } from '../../api/client'
import type { PortalItemDetail } from '../../types'

interface GlobeViewOptions {
  year: number
  eventId?: number
}

interface Props {
  slug: string
  onGlobeView: (opts: GlobeViewOptions) => void
}

export function PreviewPanel({ slug, onGlobeView }: Props) {
  const closePreview = usePortalStore((s) => s.closePreview)
  const pushDetail = usePortalStore((s) => s.pushDetail)
  const suspend = usePortalStore((s) => s.suspend)
  const { preferredLanguage } = useSettingsStore()

  const { data: item, isLoading } = useQuery<PortalItemDetail>({
    queryKey: ['portal-item', slug],
    queryFn: async () => {
      const res = await portalApi.getItem(slug)
      return res.data
    },
  })

  const handleReadFull = () => {
    closePreview()
    pushDetail(slug)
  }

  const handleGlobeView = () => {
    if (item?.year) {
      suspend()
      onGlobeView({
        year: item.year,
        eventId: item.related_event_ids?.[0],
      })
    }
  }

  if (isLoading) {
    return (
      <div className="portal-preview">
        <div className="portal-preview__header">
          <span className="portal-preview__badge" style={{ background: 'rgba(26,58,74,0.3)' }}>...</span>
          <button className="portal-preview__close" onClick={closePreview}>{'\u2715'}</button>
        </div>
        <div className="portal-preview__body">
          <div className="portal-skeleton" style={{ height: 20, width: '60%', marginBottom: 12 }} />
          <div className="portal-skeleton" style={{ height: 14, width: '40%', marginBottom: 16 }} />
          <div className="portal-skeleton" style={{ height: 80, width: '100%' }} />
        </div>
      </div>
    )
  }

  if (!item) return null

  const title = getLocalizedText(item, 'title', preferredLanguage)
  const subtitle = item.subtitle ? getLocalizedText(item, 'subtitle', preferredLanguage) : undefined
  const description = getLocalizedText(item, 'description', preferredLanguage)
  const typeLabel = item.item_type.replace('_', ' ')
  const meta = [item.era, item.year ? formatYear(item.year) : null]
    .filter(Boolean)
    .join(' \u00B7 ')

  return (
    <div className="portal-preview">
      <div className="portal-preview__header">
        <span className={`portal-preview__badge portal-hero-badge--${item.item_type}`}>
          {typeLabel}
        </span>
        <button className="portal-preview__close" onClick={closePreview}>{'\u2715'}</button>
      </div>

      <div className="portal-preview__body">
        <div className="portal-preview__title">{title}</div>
        {subtitle && <div className="portal-preview__subtitle">{subtitle}</div>}
        {meta && <div className="portal-preview__meta">{meta}</div>}
        {item.location && <div className="portal-preview__location">{item.location}</div>}
        {description && <div className="portal-preview__excerpt">{description}</div>}
      </div>

      <div className="portal-preview__actions">
        <button className="portal-btn portal-btn--primary" onClick={handleReadFull}>
          Read Full {'\u2192'}
        </button>
        {item.year && (
          <button className="portal-btn portal-btn--secondary" onClick={handleGlobeView}>
            Globe View ({formatYear(item.year)})
          </button>
        )}
      </div>
    </div>
  )
}

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}
