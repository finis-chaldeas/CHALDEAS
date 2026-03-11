import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { PortalItemSummary } from '../../types'
import { FgoStoryChain } from './FgoStoryChain'
import { FgoServantGrid } from './FgoServantGrid'
import { FgoShiftList } from './FgoShiftList'

type FgoView = 'story' | 'servants' | 'shifts'

interface Props {
  items: PortalItemSummary[]
  onOpenShift: (shiftId: number) => void
}

export function FgoSection({ items, onOpenShift }: Props) {
  const { t } = useTranslation()
  const [activeView, setActiveView] = useState<FgoView>('story')

  const chips: { key: FgoView; label: string }[] = [
    { key: 'story', label: t('trismegistos.fgo.story') },
    { key: 'servants', label: t('trismegistos.fgo.servants') },
    { key: 'shifts', label: t('trismegistos.fgo.shifts') },
  ]

  const storyItems = items.filter(
    (i) => i.item_type === 'singularity' || i.item_type === 'lostbelt'
  )
  const servantItems = items.filter((i) => i.item_type === 'servant_column')

  return (
    <div className="portal-section">
      <div className="portal-section__title">{t('trismegistos.tabs.fgo')}</div>

      {/* Chip bar */}
      <div className="fgo-chip-bar">
        {chips.map(({ key, label }) => (
          <button
            key={key}
            className={`fgo-chip ${activeView === key ? 'fgo-chip--active' : ''}`}
            onClick={() => setActiveView(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Sub-views */}
      {activeView === 'story' && <FgoStoryChain items={storyItems} />}
      {activeView === 'servants' && <FgoServantGrid items={servantItems} />}
      {activeView === 'shifts' && <FgoShiftList onOpenShift={onOpenShift} />}
    </div>
  )
}
