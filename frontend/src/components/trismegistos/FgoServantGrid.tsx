import { usePortalStore } from '../../store/portalStore'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import type { PortalItemSummary } from '../../types'

interface Props {
  items: PortalItemSummary[]
}

// Hardcoded culture group mapping for 30 FGO servants
const CULTURE_GROUPS: { label: string; slugs: string[] }[] = [
  {
    label: 'Greek / Trojan War',
    slugs: ['achilles', 'heracles', 'medea', 'leonidas', 'iskandar'],
  },
  {
    label: 'Celtic / Arthurian',
    slugs: ['cu-chulainn', 'altria', 'mordred'],
  },
  {
    label: 'Ancient Near East',
    slugs: ['gilgamesh', 'ozymandias', 'cleopatra'],
  },
  {
    label: 'Indian Epic',
    slugs: ['karna', 'arjuna'],
  },
  {
    label: 'East Asian',
    slugs: ['zhuge-liang', 'qin-shi-huang', 'nobunaga', 'ushiwakamaru', 'musashi'],
  },
  {
    label: 'Roman',
    slugs: ['nero', 'caesar', 'spartacus'],
  },
  {
    label: 'European',
    slugs: [
      'jeanne', 'drake', 'da-vinci', 'napoleon', 'tesla',
      'marie-antoinette', 'ivan', 'vlad', 'nightingale',
    ],
  },
]

export function FgoServantGrid({ items }: Props) {
  const openPreview = usePortalStore((s) => s.openPreview)
  const { preferredLanguage } = useSettingsStore()

  // Build slug lookup from items
  const bySlug = new Map(items.map((i) => [i.slug, i]))

  // Group items — items not matched by any group go into "Other"
  const matchedSlugs = new Set(CULTURE_GROUPS.flatMap((g) => g.slugs))
  const ungrouped = items.filter((i) => !matchedSlugs.has(i.slug))

  return (
    <div className="fgo-servants">
      {CULTURE_GROUPS.map((group) => {
        const groupItems = group.slugs
          .map((slug) => bySlug.get(slug))
          .filter((i): i is PortalItemSummary => !!i)
        if (!groupItems.length) return null

        return (
          <div key={group.label} className="fgo-servants__group">
            <div className="fgo-servants__group-label">
              {group.label} ({groupItems.length})
            </div>
            <div className="fgo-servants__grid">
              {groupItems.map((item) => {
                const title = getLocalizedText(item, 'title', preferredLanguage)
                return (
                  <button
                    key={item.slug}
                    className="fgo-servants__card"
                    onClick={() => openPreview(item.slug)}
                  >
                    <div className="fgo-servants__card-name">{title}</div>
                    {item.era && (
                      <div className="fgo-servants__card-class">{item.era}</div>
                    )}
                    {item.year && (
                      <div className="fgo-servants__card-year">{formatYear(item.year)}</div>
                    )}
                  </button>
                )
              })}
            </div>
          </div>
        )
      })}

      {/* Ungrouped servants */}
      {ungrouped.length > 0 && (
        <div className="fgo-servants__group">
          <div className="fgo-servants__group-label">Other ({ungrouped.length})</div>
          <div className="fgo-servants__grid">
            {ungrouped.map((item) => {
              const title = getLocalizedText(item, 'title', preferredLanguage)
              return (
                <button
                  key={item.slug}
                  className="fgo-servants__card"
                  onClick={() => openPreview(item.slug)}
                >
                  <div className="fgo-servants__card-name">{title}</div>
                  {item.year && (
                    <div className="fgo-servants__card-year">{formatYear(item.year)}</div>
                  )}
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
