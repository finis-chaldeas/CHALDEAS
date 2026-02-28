import { useState } from 'react'
import { usePortalStore } from '../../store/portalStore'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import type { PortalItemSummary } from '../../types'

interface Props {
  items: PortalItemSummary[]
}

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'history', label: 'History' },
  { key: 'literature', label: 'Literature' },
  { key: 'music', label: 'Music' },
] as const

const INITIAL_COUNT = 5

export function ReadingSection({ items }: Props) {
  const [filter, setFilter] = useState('all')
  const [showAll, setShowAll] = useState(false)
  const openPreview = usePortalStore((s) => s.openPreview)
  const { preferredLanguage } = useSettingsStore()

  const filtered = filter === 'all' ? items : items.filter((item) => item.item_type === filter)
  const displayed = showAll ? filtered : filtered.slice(0, INITIAL_COUNT)

  return (
    <>
      <div className="portal-filter-chips">
        {FILTERS.map(({ key, label }) => (
          <button
            key={key}
            className={`portal-chip ${filter === key ? 'portal-chip--active' : ''}`}
            onClick={() => { setFilter(key); setShowAll(false) }}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="portal-reading-list">
        {displayed.map((item) => {
          const title = getLocalizedText(item, 'title', preferredLanguage)
          const meta = [item.era, item.year ? formatYear(item.year) : null]
            .filter(Boolean)
            .join(' \u00B7 ')

          return (
            <div
              key={item.slug}
              className="portal-reading-item"
              onClick={() => openPreview(item.slug)}
            >
              <span className={`portal-reading-item__badge portal-hero-badge--${item.item_type}`}>
                {item.item_type}
              </span>
              <div className="portal-reading-item__body">
                <div className="portal-reading-item__title">{title}</div>
                {meta && <div className="portal-reading-item__meta">{meta}</div>}
              </div>
            </div>
          )
        })}
      </div>

      {filtered.length > INITIAL_COUNT && (
        <button className="portal-show-more" onClick={() => setShowAll(!showAll)}>
          {showAll ? 'Show less' : `Show all (${filtered.length})`}
        </button>
      )}
    </>
  )
}

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}
