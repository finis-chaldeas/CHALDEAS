import { registerWidget, loc, type WidgetProps } from './registry'

function ModernEquivalent({ data, lang }: WidgetProps) {
  const ancient = loc(data, 'ancient', lang)
  const modern = loc(data, 'modern', lang)
  if (!ancient || !modern) return null

  const explanation = loc(data, 'explanation', lang)

  return (
    <div className="widget-card widget-meq">
      <div className="widget-meq-label">In Today's Terms</div>
      <div className="widget-meq-compare">
        <div className="widget-meq-ancient">{ancient}</div>
        <div className="widget-meq-arrow">&asymp;</div>
        <div className="widget-meq-modern">{modern}</div>
      </div>
      {explanation && <div className="widget-meq-explain">{explanation}</div>}
    </div>
  )
}

registerWidget('modern_equivalent', ModernEquivalent)
export default ModernEquivalent
