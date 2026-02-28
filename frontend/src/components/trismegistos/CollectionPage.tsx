import { useQuery } from '@tanstack/react-query'
import { usePortalStore } from '../../store/portalStore'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import { portalApi } from '../../api/client'
import type { CollectionDetail, CollectionEntrySummary } from '../../types'

interface Props {
  slug: string
  onEventClick: (eventId: number) => void
  onPersonClick: (personId: number) => void
  onOpenShift: (shiftId: number) => void
}

const ENTRY_TYPE_CONFIG: Record<string, { icon: string; label: string }> = {
  shift: { icon: '\u25B6', label: 'Shifts' },
  portal_item: { icon: '\uD83D\uDCD6', label: 'Articles' },
  person: { icon: '\uD83D\uDC64', label: 'Persons' },
  event: { icon: '\u26A1', label: 'Events' },
  period: { icon: '\uD83D\uDD52', label: 'Periods' },
}

export function CollectionPage({ slug, onEventClick, onPersonClick, onOpenShift }: Props) {
  const close = usePortalStore((s) => s.close)
  const pop = usePortalStore((s) => s.pop)
  const pushDetail = usePortalStore((s) => s.pushDetail)
  const { preferredLanguage } = useSettingsStore()

  const { data: collection, isLoading } = useQuery<CollectionDetail>({
    queryKey: ['portal-collection', slug],
    queryFn: async () => {
      const res = await portalApi.getCollection(slug)
      return res.data
    },
  })

  const handleEntryClick = (entry: CollectionEntrySummary) => {
    if (entry.entry_type === 'shift' && entry.shift_id) {
      close()
      onOpenShift(entry.shift_id)
    } else if (entry.entry_type === 'portal_item' && entry.portal_item) {
      pushDetail(entry.portal_item.slug)
    } else if (entry.entry_type === 'person' && entry.person_id) {
      close()
      onPersonClick(entry.person_id)
    } else if (entry.entry_type === 'event' && entry.event_id) {
      close()
      onEventClick(entry.event_id)
    }
  }

  const getEntryTitle = (entry: CollectionEntrySummary): string => {
    if (entry.portal_item) return getLocalizedText(entry.portal_item, 'title', preferredLanguage)
    if (entry.shift_summary) return getLocalizedText(entry.shift_summary, 'title', preferredLanguage)
    if (entry.person_summary) return getLocalizedText(entry.person_summary, 'name', preferredLanguage)
    if (entry.event_summary) return getLocalizedText(entry.event_summary, 'title', preferredLanguage)
    return `${entry.entry_type} #${entry.id}`
  }

  const getEntryMeta = (entry: CollectionEntrySummary): string | null => {
    if (entry.shift_summary) {
      const parts: string[] = []
      if (entry.shift_summary.chain_type) parts.push(entry.shift_summary.chain_type.replace('_', ' '))
      if (entry.shift_summary.segment_count) parts.push(`${entry.shift_summary.segment_count} pages`)
      return parts.join(' \u00B7 ')
    }
    if (entry.person_summary) {
      const { birth_year, death_year } = entry.person_summary
      if (birth_year) return `${formatYear(birth_year)}${death_year ? ` \u2013 ${formatYear(death_year)}` : ''}`
    }
    if (entry.event_summary?.date_start) {
      return formatYear(entry.event_summary.date_start)
    }
    if (entry.portal_item) {
      return [entry.portal_item.era, entry.portal_item.chapter].filter(Boolean).join(' \u00B7 ')
    }
    return null
  }

  // Group entries by type
  const groups = new Map<string, CollectionEntrySummary[]>()
  if (collection?.entries) {
    // First: highlighted entries
    const highlighted = collection.entries.filter((e) => e.is_highlighted)
    if (highlighted.length) groups.set('_highlighted', highlighted)

    // Then: by entry_type
    for (const entry of collection.entries) {
      if (entry.is_highlighted) continue
      const type = entry.entry_type
      if (!groups.has(type)) groups.set(type, [])
      groups.get(type)!.push(entry)
    }
  }

  const title = collection ? getLocalizedText(collection, 'title', preferredLanguage) : ''

  return (
    <div className="portal-modal">
      <div className="portal-header">
        <div className="portal-header__left">
          <button className="portal-header__back" onClick={pop}>{'\u2190'}</button>
          <span className="portal-header__title">{title || 'Collection'}</span>
        </div>
        <button className="portal-header__close" onClick={close}>{'\u2715'}</button>
      </div>

      <div className="portal-scroll">
        {isLoading && (
          <div>
            <div className="portal-skeleton" style={{ height: 20, width: '60%', marginBottom: 12 }} />
            <div className="portal-skeleton" style={{ height: 14, width: '80%', marginBottom: 8 }} />
            <div className="portal-skeleton" style={{ height: 14, width: '70%', marginBottom: 8 }} />
          </div>
        )}

        {collection?.description && (
          <p style={{ fontSize: 13, color: 'var(--chaldea-text)', marginBottom: 20, lineHeight: 1.6 }}>
            {getLocalizedText(collection, 'description', preferredLanguage)}
          </p>
        )}

        <div className="portal-collection-entries">
          {Array.from(groups.entries()).map(([groupKey, entries]) => {
            const config = groupKey === '_highlighted'
              ? { icon: '\u2B50', label: 'Highlighted' }
              : ENTRY_TYPE_CONFIG[groupKey] || { icon: '', label: groupKey }

            return (
              <div key={groupKey}>
                <div className="portal-entry-group__title">
                  <span>{config.icon}</span>
                  <span>{config.label}</span>
                </div>
                <div className="portal-entry-list">
                  {entries.map((entry) => (
                    <div
                      key={entry.id}
                      className={`portal-entry-item ${entry.is_highlighted ? 'portal-entry-item--highlighted' : ''}`}
                      onClick={() => handleEntryClick(entry)}
                    >
                      <span className="portal-entry-item__icon">
                        {ENTRY_TYPE_CONFIG[entry.entry_type]?.icon || '\u2022'}
                      </span>
                      <div className="portal-entry-item__body">
                        <div className="portal-entry-item__title">{getEntryTitle(entry)}</div>
                        {getEntryMeta(entry) && (
                          <div className="portal-entry-item__meta">{getEntryMeta(entry)}</div>
                        )}
                        {entry.note && (
                          <div className="portal-entry-item__note">
                            {getLocalizedText(entry, 'note', preferredLanguage)}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}
