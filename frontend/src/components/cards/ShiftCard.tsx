import { useEffect, useState } from 'react'
import { shiftsApi } from '../../api/client'
import { useSettingsStore, getEffectiveLanguage, getLocalizedText } from '../../store/settingsStore'
import { useGlobeStore } from '../../store/globeStore'
import { useCardPopup } from './useCardPopup'
import type { CardMode } from './useCardPopup'

interface ShiftData {
  id: number
  title: string
  title_ko?: string
  year_start: number
  year_end: number
  importance?: number
  page_count: number
  first_narrative?: string
  first_narrative_ko?: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  rawShift?: any
}

function formatYear(y: number): string {
  return y < 0 ? `${Math.abs(y)} BCE` : `${y} CE`
}

export default function ShiftCard({ entityId, mode, onViewDetail: _onViewDetail }: { entityId: number; mode: CardMode; onViewDetail?: () => void }) {
  const [data, setData] = useState<ShiftData | null>(null)
  const [loading, setLoading] = useState(true)
  const lang = getEffectiveLanguage(useSettingsStore((s) => s.preferredLanguage))
  const openShift = useGlobeStore((s) => s.openShift)
  const closeCard = useCardPopup((s) => s.closeCard)

  useEffect(() => {
    setLoading(true)
    shiftsApi.get(entityId).then((res) => {
      const s = res.data
      const pages = s.pages || []
      const firstPage = pages[0]
      setData({
        id: s.id,
        title: s.title,
        title_ko: s.title_ko,
        year_start: s.year_start,
        year_end: s.year_end,
        importance: s.globe_importance,
        page_count: pages.length,
        first_narrative: firstPage?.page_narrative,
        first_narrative_ko: firstPage?.page_narrative_ko,
        rawShift: s,
      })
    }).catch((err) => console.error('ShiftCard fetch failed:', err))
      .finally(() => setLoading(false))
  }, [entityId])

  if (loading) return <div className="card-loading">Loading...</div>
  if (!data) return <div className="card-error">Shift not found</div>

  const title = getLocalizedText(data, 'title', lang === 'en' ? 'en' : lang)
  const dateStr = `${formatYear(data.year_start)} — ${formatYear(data.year_end)}`

  const handlePlay = () => {
    if (data.rawShift) {
      closeCard()
      openShift(data.rawShift)
    }
  }

  if (mode === 'compact') {
    return (
      <>
        <div className="card-title">{title}</div>
        <div className="card-subtitle">{dateStr} &middot; {data.page_count} pages</div>
      </>
    )
  }

  const narrative = getLocalizedText(
    { description: data.first_narrative, description_ko: data.first_narrative_ko },
    'description',
    lang === 'en' ? 'en' : lang
  )

  return (
    <>
      <div className="card-title">{title}</div>
      <div className="card-date">{dateStr}</div>
      <div className="card-meta-row">
        {data.page_count} pages
        {data.importance != null && data.importance >= 1 && (
          <span className="card-stars">{' '}{'\u2605'.repeat(Math.min(data.importance, 5))}</span>
        )}
      </div>
      {narrative && <div className="card-snippet">{narrative.slice(0, 150)}</div>}
      <div className="card-actions">
        <button onClick={handlePlay}>{'\u25B6'} Play</button>
      </div>
    </>
  )
}
