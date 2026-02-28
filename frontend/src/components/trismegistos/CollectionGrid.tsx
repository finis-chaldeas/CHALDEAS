import { usePortalStore } from '../../store/portalStore'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import type { CollectionSummary } from '../../types'

interface Props {
  collections: CollectionSummary[]
}

export function CollectionGrid({ collections }: Props) {
  const pushCollection = usePortalStore((s) => s.pushCollection)
  const { preferredLanguage } = useSettingsStore()

  return (
    <div className="portal-collection-grid">
      {collections.map((col) => {
        const title = getLocalizedText(col, 'title', preferredLanguage)
        return (
          <div
            key={col.slug}
            className="portal-collection-card"
            onClick={() => pushCollection(col.slug)}
          >
            {col.icon && <div className="portal-collection-card__icon">{col.icon}</div>}
            <div className="portal-collection-card__title">{title}</div>
            <div className="portal-collection-card__count">
              {col.entry_count} {col.entry_count === 1 ? 'item' : 'items'}
            </div>
          </div>
        )
      })}
    </div>
  )
}
