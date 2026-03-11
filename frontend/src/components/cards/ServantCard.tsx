import { useEffect, useState } from 'react'
import { servantsApi, personsApi } from '../../api/client'
import { useSettingsStore, getEffectiveLanguage, getLocalizedText } from '../../store/settingsStore'
import { useCardPopup } from './useCardPopup'
import type { CardMode } from './useCardPopup'

interface ServantFullData {
  fgo_name: string
  fgo_class: string
  rarity: number
  origin?: string
  person_id?: number
  person_name?: string
  person_name_ko?: string
}

export default function ServantCard({ entityId, mode, onViewDetail }: { entityId: number; mode: CardMode; onViewDetail?: () => void }) {
  const [data, setData] = useState<ServantFullData | null>(null)
  const [loading, setLoading] = useState(true)
  const lang = getEffectiveLanguage(useSettingsStore((s) => s.preferredLanguage))
  const openCard = useCardPopup((s) => s.openCard)

  useEffect(() => {
    setLoading(true)
    // entityId here is the person_id — fetch servant by person
    servantsApi.getByPerson(entityId).then(async (res) => {
      const list = res.data
      if (!Array.isArray(list) || list.length === 0) { setLoading(false); return }
      const s = list[0]
      let personName: string | undefined
      let personNameKo: string | undefined
      if (s.person_id) {
        try {
          const pRes = await personsApi.get(s.person_id)
          personName = pRes.data?.name
          personNameKo = pRes.data?.name_ko
        } catch { /* ignore */ }
      }
      setData({
        fgo_name: s.fgo_name,
        fgo_class: s.fgo_class || '',
        rarity: s.rarity || 0,
        origin: s.origin,
        person_id: s.person_id,
        person_name: personName || s.person_name,
        person_name_ko: personNameKo,
      })
    }).catch((err) => console.error('ServantCard fetch failed:', err))
      .finally(() => setLoading(false))
  }, [entityId])

  if (loading) return <div className="card-loading">Loading...</div>
  if (!data) return <div className="card-error">Servant not found</div>

  const starStr = '\u2605'.repeat(data.rarity)

  if (mode === 'compact') {
    return (
      <>
        <div className="card-title">{data.fgo_name}</div>
        <div className="card-subtitle">{starStr} {data.fgo_class}</div>
      </>
    )
  }

  return (
    <>
      <div className="card-fgo-header">
        <span className="card-fgo-stars">{starStr}</span>
        <span className="card-fgo-class">{data.fgo_class}</span>
      </div>
      <div className="card-title">{data.fgo_name}</div>
      {data.origin && <div className="card-subtitle">{data.origin}</div>}
      {data.person_id && data.person_name && (
        <div className="card-related">
          <div className="card-related-label">Historical</div>
          <span
            className="card-entity-link"
            onClick={(e) => { e.stopPropagation(); openCard('person', data.person_id!, { mode: 'expanded' }) }}
          >
            {getLocalizedText(
              { name: data.person_name, name_ko: data.person_name_ko },
              'name',
              lang === 'en' ? 'en' : lang
            )}
          </span>
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
