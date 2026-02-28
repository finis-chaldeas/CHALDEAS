import { usePortalStore } from '../../store/portalStore'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import type { PortalItemSummary } from '../../types'

interface GlobeViewOptions {
  year: number
  eventId?: number
}

interface Props {
  items: PortalItemSummary[]
  onGlobeView: (opts: GlobeViewOptions) => void
}

export function TodayHero({ items, onGlobeView }: Props) {
  const suspend = usePortalStore((s) => s.suspend)
  const pushDetail = usePortalStore((s) => s.pushDetail)
  const { preferredLanguage } = useSettingsStore()

  if (!items.length) return null

  // Deterministic daily rotation
  const now = new Date()
  const dayOfYear = Math.floor((now.getTime() - new Date(now.getFullYear(), 0, 0).getTime()) / 86400000)
  const todayItem = items[dayOfYear % items.length]

  const title = getLocalizedText(todayItem, 'title', preferredLanguage)
  const subtitle = todayItem.subtitle
    ? getLocalizedText(todayItem, 'subtitle', preferredLanguage)
    : undefined

  const meta = [todayItem.era, todayItem.year ? formatYear(todayItem.year) : null, todayItem.location]
    .filter(Boolean)
    .join(' \u00B7 ')

  return (
    <div className="portal-hero-card">
      <span className={`portal-hero-badge portal-hero-badge--${todayItem.item_type}`}>
        {todayItem.item_type.replace('_', ' ')}
      </span>
      <div className="portal-hero-title">{title}</div>
      {meta && <div className="portal-hero-meta">{meta}</div>}
      {subtitle && <div className="portal-hero-excerpt">{subtitle}</div>}
      <div className="portal-hero-actions">
        {todayItem.year && (
          <button
            className="portal-btn portal-btn--primary"
            onClick={() => {
              suspend()
              if (todayItem.year) onGlobeView({ year: todayItem.year })
            }}
          >
            Globe View
          </button>
        )}
        <button
          className="portal-btn portal-btn--secondary"
          onClick={() => pushDetail(todayItem.slug)}
        >
          Read More
        </button>
      </div>
    </div>
  )
}

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}
