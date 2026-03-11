import { useTranslation } from 'react-i18next'
import { registerWidget, loc, type WidgetProps } from './registry'

interface ChangeItem {
  before?: string
  after?: string
  label?: string
  [key: string]: unknown
}

function TerritoryChange({ data, lang }: WidgetProps) {
  const changes = data.changes as ChangeItem[] | undefined
  const { t } = useTranslation()
  if (!changes?.length) return null

  const heading = loc(data, 'heading', lang) || t('trismegistos.widget.territoryChange')

  return (
    <div className="widget-card widget-terr">
      <div className="widget-terr-heading">{heading}</div>
      <div className="widget-terr-list">
        {changes.map((c, i) => {
          const rec = c as Record<string, unknown>
          const label = loc(rec, 'label', lang)
          const before = loc(rec, 'before', lang)
          const after = loc(rec, 'after', lang)
          if (!before && !after) return null

          return (
            <div key={i} className="widget-terr-item">
              {label && <div className="widget-terr-label">{label}</div>}
              <div className="widget-terr-flow">
                <span className="widget-terr-before">{before || '—'}</span>
                <span className="widget-terr-arrow">&rarr;</span>
                <span className="widget-terr-after">{after || '—'}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

registerWidget('territory_change', TerritoryChange)
export default TerritoryChange
