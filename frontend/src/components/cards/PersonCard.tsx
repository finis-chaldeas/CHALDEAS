import { useEffect, useState } from 'react'
import { personsApi, servantsApi } from '../../api/client'
import { useSettingsStore, getEffectiveLanguage, getLocalizedText } from '../../store/settingsStore'
import { useCardPopup } from './useCardPopup'
import type { CardMode } from './useCardPopup'

interface PersonData {
  id: number
  name: string
  name_ko?: string
  name_ja?: string
  birth_year?: number
  death_year?: number
  role?: string
  biography?: string
  biography_ko?: string
}

interface ServantData {
  name: string
  class_name: string
  rarity: number
}

function formatYear(y: number): string {
  return y < 0 ? `${Math.abs(y)} BCE` : `${y} CE`
}

function formatLifespan(birth?: number, death?: number): string | null {
  if (birth != null && death != null) return `${formatYear(birth)} — ${formatYear(death)}`
  if (birth != null) return `b. ${formatYear(birth)}`
  if (death != null) return `d. ${formatYear(death)}`
  return null
}

export default function PersonCard({ entityId, mode, onViewDetail }: { entityId: number; mode: CardMode; onViewDetail?: () => void }) {
  const [data, setData] = useState<PersonData | null>(null)
  const [servant, setServant] = useState<ServantData | null>(null)
  const [loading, setLoading] = useState(true)
  const lang = getEffectiveLanguage(useSettingsStore((s) => s.preferredLanguage))
  const openCard = useCardPopup((s) => s.openCard)

  useEffect(() => {
    setLoading(true)
    const fetchPerson = personsApi.get(entityId).then((res) => {
      const p = res.data
      setData({
        id: p.id,
        name: p.name,
        name_ko: p.name_ko,
        name_ja: p.name_ja,
        birth_year: p.birth_year,
        death_year: p.death_year,
        role: p.role,
        biography: p.details?.biography,
        biography_ko: p.details?.biography_ko,
      })
    })
    const fetchServant = servantsApi.getByPerson(entityId).then((res) => {
      const list = res.data
      if (Array.isArray(list) && list.length > 0) {
        const s = list[0]
        setServant({
          name: s.fgo_name,
          class_name: s.fgo_class || '',
          rarity: s.rarity || 0,
        })
      }
    }).catch(() => { /* no servant match — fine */ })

    Promise.all([fetchPerson, fetchServant])
      .catch((err) => console.error('PersonCard fetch failed:', err))
      .finally(() => setLoading(false))
  }, [entityId])

  if (loading) return <div className="card-loading">Loading...</div>
  if (!data) return <div className="card-error">Person not found</div>

  const name = getLocalizedText(data, 'name', lang === 'en' ? 'en' : lang)
  const lifespan = formatLifespan(data.birth_year, data.death_year)

  if (mode === 'compact') {
    return (
      <>
        <div className="card-title">{name}</div>
        <div className="card-subtitle">
          {lifespan} {data.role && <span className="card-role">{data.role}</span>}
        </div>
      </>
    )
  }

  const bio = getLocalizedText(
    { description: data.biography, description_ko: data.biography_ko },
    'description',
    lang === 'en' ? 'en' : lang
  )

  return (
    <>
      <div className="card-title">{name}</div>
      {data.role && <div className="card-role">{data.role}</div>}
      {lifespan && <div className="card-date">{lifespan}</div>}
      {bio && <div className="card-snippet">{bio.slice(0, 150)}</div>}
      {servant && (
        <div
          className="card-fgo"
          onClick={(e) => { e.stopPropagation(); openCard('servant', entityId, { mode: 'expanded' }) }}
        >
          <span className="card-fgo-stars">{'\u2605'.repeat(servant.rarity)}</span>
          <span className="card-fgo-class">{servant.class_name}</span>
          <span className="card-fgo-name">{servant.name}</span>
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
