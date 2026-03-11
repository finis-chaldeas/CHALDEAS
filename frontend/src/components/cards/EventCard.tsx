import { useEffect, useState } from 'react'
import { eventsApi } from '../../api/client'
import { useSettingsStore, getEffectiveLanguage, getLocalizedText } from '../../store/settingsStore'
import { useCardPopup } from './useCardPopup'
import type { CardMode } from './useCardPopup'

interface EventData {
  id: number
  title: string
  title_ko?: string
  title_ja?: string
  date_start: number
  date_end?: number
  importance: number
  description?: string
  description_ko?: string
  location_name?: string
  location_name_ko?: string
  location_name_ja?: string
  persons?: { id: number; name: string; name_ko?: string; name_ja?: string; role?: string }[]
}

function formatYear(y: number): string {
  return y < 0 ? `${Math.abs(y)} BCE` : `${y} CE`
}

function stars(n: number): string {
  return '\u2605'.repeat(Math.min(n, 5))
}

export default function EventCard({ entityId, mode, onViewDetail }: { entityId: number; mode: CardMode; onViewDetail?: () => void }) {
  const [data, setData] = useState<EventData | null>(null)
  const [loading, setLoading] = useState(true)
  const lang = getEffectiveLanguage(useSettingsStore((s) => s.preferredLanguage))
  const openCard = useCardPopup((s) => s.openCard)

  useEffect(() => {
    setLoading(true)
    eventsApi.get(entityId).then((res) => {
      const e = res.data
      setData({
        id: e.id,
        title: e.title,
        title_ko: e.title_ko,
        title_ja: e.title_ja,
        date_start: e.date_start,
        date_end: e.date_end,
        importance: e.importance,
        description: e.details?.description || e.description,
        description_ko: e.details?.description_ko || e.description_ko,
        location_name: e.location?.name || e.locations?.[0]?.name,
        location_name_ko: e.location?.name_ko || e.locations?.[0]?.name_ko,
        location_name_ja: e.location?.name_ja || e.locations?.[0]?.name_ja,
        persons: e.persons?.slice(0, 3).map((p: Record<string, unknown>) => ({
          id: p.id as number,
          name: p.name as string,
          name_ko: p.name_ko as string | undefined,
          name_ja: p.name_ja as string | undefined,
          role: p.role as string | undefined,
        })),
      })
    }).catch((err) => console.error('EventCard fetch failed:', err))
      .finally(() => setLoading(false))
  }, [entityId])

  if (loading) return <div className="card-loading">Loading...</div>
  if (!data) return <div className="card-error">Event not found</div>

  const title = getLocalizedText(data, 'title', lang === 'en' ? 'en' : lang)
  const locName = getLocalizedText(data, 'location_name', lang === 'en' ? 'en' : lang)
  const desc = getLocalizedText(
    { description: data.description, description_ko: data.description_ko },
    'description',
    lang === 'en' ? 'en' : lang
  )

  const dateStr = data.date_end && data.date_end !== data.date_start
    ? `${formatYear(data.date_start)} — ${formatYear(data.date_end)}`
    : formatYear(data.date_start)

  if (mode === 'compact') {
    return (
      <>
        <div className="card-title">{title}</div>
        <div className="card-subtitle">
          {dateStr} {data.importance >= 3 && <span className="card-stars">{stars(data.importance)}</span>}
        </div>
      </>
    )
  }

  return (
    <>
      <div className="card-title">{title}</div>
      {locName && <div className="card-location">{locName}</div>}
      <div className="card-date">{dateStr}</div>
      {data.importance >= 1 && <div className="card-importance">{stars(data.importance)}</div>}
      {desc && <div className="card-snippet">{desc.slice(0, 200)}</div>}
      {data.persons && data.persons.length > 0 && (
        <div className="card-related">
          <div className="card-related-label">Key figures</div>
          {data.persons.map((p) => (
            <span
              key={p.id}
              className="card-entity-link"
              onClick={(e) => { e.stopPropagation(); openCard('person', p.id, { mode: 'expanded' }) }}
            >
              {getLocalizedText(p, 'name', lang === 'en' ? 'en' : lang)}
            </span>
          ))}
        </div>
      )}
      {onViewDetail && (
        <div className="card-actions">
          <button onClick={onViewDetail}>View details</button>
        </div>
      )}
    </>
  )
}
