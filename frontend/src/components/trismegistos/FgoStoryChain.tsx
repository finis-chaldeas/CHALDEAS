import { useTranslation } from 'react-i18next'
import { usePortalStore } from '../../store/portalStore'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import type { PortalItemSummary } from '../../types'

interface Props {
  items: PortalItemSummary[]
}

export function FgoStoryChain({ items }: Props) {
  const { t } = useTranslation()
  const openPreview = usePortalStore((s) => s.openPreview)
  const { preferredLanguage } = useSettingsStore()

  const singularities = items
    .filter((i) => i.item_type === 'singularity')
    .sort((a, b) => a.sort_order - b.sort_order)
  const lostbelts = items
    .filter((i) => i.item_type === 'lostbelt')
    .sort((a, b) => a.sort_order - b.sort_order)

  return (
    <div className="fgo-story">
      {/* Grand Order arc */}
      {singularities.length > 0 && (
        <div className="fgo-story__arc">
          <div className="fgo-story__arc-label">{t('trismegistos.fgo.grandOrder')}</div>
          <div className="fgo-story__chain">
            {singularities.map((item) => {
              const title = getLocalizedText(item, 'title', preferredLanguage)
              const sub = item.subtitle ? getLocalizedText(item, 'subtitle', preferredLanguage) : undefined
              const meta = [
                item.year ? formatYear(item.year) : null,
                item.location,
              ].filter(Boolean).join(' \u00B7 ')

              return (
                <button
                  key={item.slug}
                  className="fgo-story__card fgo-story__card--singularity"
                  onClick={() => openPreview(item.slug)}
                >
                  <div className="fgo-story__card-header">
                    {item.chapter && (
                      <span className="fgo-story__chapter">{item.chapter}</span>
                    )}
                    <span className="fgo-story__title">{title}</span>
                  </div>
                  {meta && <div className="fgo-story__meta">{meta}</div>}
                  {sub && <div className="fgo-story__sub">{sub}</div>}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Cosmos Denial arc */}
      {lostbelts.length > 0 && (
        <div className="fgo-story__arc">
          <div className="fgo-story__arc-label">{t('trismegistos.fgo.cosmosDenial')}</div>
          <div className="fgo-story__chain">
            {lostbelts.map((item) => {
              const title = getLocalizedText(item, 'title', preferredLanguage)
              const sub = item.subtitle ? getLocalizedText(item, 'subtitle', preferredLanguage) : undefined
              const meta = [
                item.year ? formatYear(item.year) : null,
                item.location,
              ].filter(Boolean).join(' \u00B7 ')

              return (
                <button
                  key={item.slug}
                  className="fgo-story__card fgo-story__card--lostbelt"
                  onClick={() => openPreview(item.slug)}
                >
                  <div className="fgo-story__card-header">
                    {item.chapter && (
                      <span className="fgo-story__chapter">{item.chapter}</span>
                    )}
                    <span className="fgo-story__title">{title}</span>
                  </div>
                  {meta && <div className="fgo-story__meta">{meta}</div>}
                  {sub && <div className="fgo-story__sub">{sub}</div>}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}
