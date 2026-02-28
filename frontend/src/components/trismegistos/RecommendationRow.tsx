import { usePortalStore } from '../../store/portalStore'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import type { RecommendationItem } from '../../types'

interface Props {
  items: RecommendationItem[]
  onOpenShift: (shiftId: number) => void
}

export function RecommendationRow({ items, onOpenShift }: Props) {
  const close = usePortalStore((s) => s.close)
  const openPreview = usePortalStore((s) => s.openPreview)
  const pushCollection = usePortalStore((s) => s.pushCollection)
  const { preferredLanguage } = useSettingsStore()

  const handleClick = (item: RecommendationItem) => {
    if (item.type === 'portal_item' && item.slug) {
      openPreview(item.slug)
    } else if (item.type === 'collection' && item.slug) {
      pushCollection(item.slug)
    } else if (item.type === 'shift' && item.id) {
      close()
      onOpenShift(item.id)
    }
  }

  return (
    <div className="portal-rec-row">
      {items.map((item, i) => {
        const title = getLocalizedText(item, 'title', preferredLanguage)
        const typeLabel = item.type === 'shift'
          ? (item.chain_type?.replace('_', ' ') || 'shift')
          : item.type === 'collection'
            ? 'collection'
            : (item.item_type?.replace('_', ' ') || 'article')

        const subtitle = item.type === 'shift' && item.segment_count
          ? `${item.segment_count} pages`
          : item.subtitle
            ? getLocalizedText(item, 'subtitle', preferredLanguage)
            : undefined

        return (
          <div
            key={`${item.type}-${item.id || item.slug}-${i}`}
            className="portal-rec-card"
            onClick={() => handleClick(item)}
          >
            <div className="portal-rec-card__type">{typeLabel}</div>
            <div className="portal-rec-card__title">{title}</div>
            {subtitle && <div className="portal-rec-card__subtitle">{subtitle}</div>}
          </div>
        )
      })}
    </div>
  )
}
