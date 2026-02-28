import { usePortalStore } from '../../store/portalStore'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import type { PortalItemSummary } from '../../types'

interface Props {
  items: PortalItemSummary[]
}

const SUBSECTIONS = [
  { type: 'singularity', label: 'Singularities', colorClass: 'singularity' },
  { type: 'lostbelt', label: 'Lostbelts', colorClass: 'lostbelt' },
  { type: 'servant_column', label: 'Servant Columns', colorClass: 'servant_column' },
] as const

export function FgoSection({ items }: Props) {
  const openPreview = usePortalStore((s) => s.openPreview)
  const pushCollection = usePortalStore((s) => s.pushCollection)
  const { preferredLanguage } = useSettingsStore()

  return (
    <div className="portal-section">
      <div className="portal-section__title">Fate/Grand Order</div>
      {SUBSECTIONS.map(({ type, label, colorClass }) => {
        const filtered = items.filter((item) => item.item_type === type)
        if (!filtered.length) return null

        return (
          <div key={type} className="portal-fgo-subsection">
            <div className={`portal-fgo-subsection__title portal-fgo-subsection__title--${colorClass}`}>
              {label}
            </div>
            <div className="portal-fgo-scroll">
              {filtered.map((item) => {
                const title = getLocalizedText(item, 'title', preferredLanguage)
                return (
                  <div
                    key={item.slug}
                    className="portal-fgo-card"
                    onClick={() => openPreview(item.slug)}
                  >
                    {item.chapter && (
                      <div className="portal-fgo-card__chapter">{item.chapter}</div>
                    )}
                    <div className="portal-fgo-card__title">{title}</div>
                    {item.era && (
                      <div className="portal-fgo-card__meta">{item.era}</div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}
      <span
        className="portal-fgo-link"
        onClick={() => pushCollection('fgo-main-story')}
      >
        FGO Main Story Collection {'\u2192'}
      </span>
    </div>
  )
}
