import { useTranslation } from 'react-i18next'
import { registerWidget, loc, type WidgetProps } from './registry'

interface StatRow {
  label?: string
  value?: string
  [key: string]: unknown
}

function BattleStats({ data, lang }: WidgetProps) {
  const stats = data.stats as StatRow[] | undefined

  // Fallback: build stats from flat fields if no stats array
  const rows: { label: string; value: string }[] = []

  if (stats?.length) {
    for (const s of stats) {
      const label = loc(s as Record<string, unknown>, 'label', lang)
      const value = loc(s as Record<string, unknown>, 'value', lang)
      if (label && value) rows.push({ label, value })
    }
  } else {
    // Flat field fallback: casualties_left, casualties_right, duration, terrain
    const fields = ['casualties_left', 'casualties_right', 'duration', 'terrain']
    for (const f of fields) {
      const label = loc(data, `${f}_label`, lang)
      const value = loc(data, f, lang)
      if (label && value) rows.push({ label, value })
    }
  }

  const { t } = useTranslation()
  if (rows.length === 0) return null

  const heading = loc(data, 'heading', lang) || t('trismegistos.widget.battleStats')
  const significance = loc(data, 'significance', lang)

  return (
    <div className="widget-card widget-bstat">
      <div className="widget-bstat-heading">{heading}</div>
      <div className="widget-bstat-grid">
        {rows.map((r, i) => (
          <div key={i} className="widget-bstat-row">
            <span className="widget-bstat-label">{r.label}</span>
            <span className="widget-bstat-value">{r.value}</span>
          </div>
        ))}
      </div>
      {significance && (
        <div className="widget-bstat-sig">{significance}</div>
      )}
    </div>
  )
}

registerWidget('battle_stats', BattleStats)
export default BattleStats
