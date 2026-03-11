import { useEffect, useState } from 'react'
import { locationsApi } from '../../api/client'
import { useSettingsStore, getEffectiveLanguage, getLocalizedText } from '../../store/settingsStore'
import { useCardPopup } from './useCardPopup'
import type { CardMode } from './useCardPopup'

interface LocationData {
  id: number
  name: string
  name_ko?: string
  name_ja?: string
  country?: string
  latitude: number
  longitude: number
  description?: string
  description_ko?: string
  events?: { id: number; title: string; title_ko?: string; title_ja?: string; date_start?: number; importance?: number }[]
}

export default function LocationCard({ entityId, mode, onViewDetail }: { entityId: number; mode: CardMode; onViewDetail?: () => void }) {
  const [data, setData] = useState<LocationData | null>(null)
  const [loading, setLoading] = useState(true)
  const lang = getEffectiveLanguage(useSettingsStore((s) => s.preferredLanguage))
  const openCard = useCardPopup((s) => s.openCard)

  useEffect(() => {
    setLoading(true)
    locationsApi.get(entityId).then((res) => {
      const loc = res.data
      // Events are returned inline by the location endpoint
      const events = (loc.events || []).slice(0, 3).map((e: Record<string, unknown>) => ({
        id: e.id as number,
        title: e.title as string,
        title_ko: e.title_ko as string | undefined,
        title_ja: e.title_ja as string | undefined,
        date_start: e.date_start as number | undefined,
      }))
      setData({
        id: loc.id,
        name: loc.name,
        name_ko: loc.name_ko,
        name_ja: loc.name_ja,
        country: loc.country,
        latitude: loc.latitude,
        longitude: loc.longitude,
        description: loc.details?.description,
        description_ko: loc.details?.description_ko,
        events,
      })
    }).catch((err) => console.error('LocationCard fetch failed:', err))
      .finally(() => setLoading(false))
  }, [entityId])

  if (loading) return <div className="card-loading">Loading...</div>
  if (!data) return <div className="card-error">Location not found</div>

  const name = getLocalizedText(data, 'name', lang === 'en' ? 'en' : lang)

  if (mode === 'compact') {
    return (
      <>
        <div className="card-title">{name}</div>
        {data.country && <div className="card-subtitle">{data.country}</div>}
      </>
    )
  }

  const desc = getLocalizedText(
    { description: data.description, description_ko: data.description_ko },
    'description',
    lang === 'en' ? 'en' : lang
  )

  return (
    <>
      <div className="card-title">{name}</div>
      {data.country && <div className="card-location">{data.country}</div>}
      <div className="card-coords">
        {data.latitude.toFixed(2)}&deg;{data.latitude >= 0 ? 'N' : 'S'},{' '}
        {data.longitude.toFixed(2)}&deg;{data.longitude >= 0 ? 'E' : 'W'}
      </div>
      {desc && <div className="card-snippet">{desc.slice(0, 150)}</div>}
      {data.events && data.events.length > 0 && (
        <div className="card-related">
          <div className="card-related-label">Major events</div>
          {data.events.map((e) => (
            <span
              key={e.id}
              className="card-entity-link"
              onClick={(ev) => { ev.stopPropagation(); openCard('event', e.id, { mode: 'expanded' }) }}
            >
              {getLocalizedText(e, 'title', lang === 'en' ? 'en' : lang)}
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
