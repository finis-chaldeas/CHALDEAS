import { registerWidget, loc, type WidgetProps } from './registry'

function DramaticStat({ data, lang }: WidgetProps) {
  const number = loc(data, 'number', lang)
  if (!number) return null

  const label = loc(data, 'label', lang)
  const context = loc(data, 'context', lang)
  const prefix = loc(data, 'prefix', lang)
  const suffix = loc(data, 'suffix', lang)

  return (
    <div className="widget-card widget-stat">
      <div className="widget-stat-number">
        {prefix && <span className="widget-stat-affix">{prefix}</span>}
        {number}
        {suffix && <span className="widget-stat-affix">{suffix}</span>}
      </div>
      <div className="widget-stat-label">{label}</div>
      {context && <div className="widget-stat-context">{context}</div>}
    </div>
  )
}

registerWidget('dramatic_stat', DramaticStat)
export default DramaticStat
