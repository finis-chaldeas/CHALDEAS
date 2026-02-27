import { registerWidget, loc, locArray, type WidgetProps } from './registry'

function FactionVs({ data, lang }: WidgetProps) {
  const leftName = loc(data, 'left_name', lang)
  const rightName = loc(data, 'right_name', lang)
  if (!leftName || !rightName) return null

  const leftCmd = loc(data, 'left_commander', lang)
  const leftStr = loc(data, 'left_strength', lang)
  const leftDetails = locArray(data, 'left_details', lang)
  const rightCmd = loc(data, 'right_commander', lang)
  const rightStr = loc(data, 'right_strength', lang)
  const rightDetails = locArray(data, 'right_details', lang)
  const outcome = loc(data, 'outcome', lang)

  return (
    <div className="widget-card widget-fvs">
      <div className="widget-fvs-grid">
        {/* Left faction */}
        <div className="widget-fvs-side widget-fvs-left">
          <div className="widget-fvs-name">{leftName}</div>
          {leftCmd && <div className="widget-fvs-cmd">{leftCmd}</div>}
          {leftStr && <div className="widget-fvs-str">{leftStr}</div>}
          {leftDetails?.map((det, i) => (
            <div key={i} className="widget-fvs-detail">{det}</div>
          ))}
        </div>

        {/* VS divider */}
        <div className="widget-fvs-vs">VS</div>

        {/* Right faction */}
        <div className="widget-fvs-side widget-fvs-right">
          <div className="widget-fvs-name">{rightName}</div>
          {rightCmd && <div className="widget-fvs-cmd">{rightCmd}</div>}
          {rightStr && <div className="widget-fvs-str">{rightStr}</div>}
          {rightDetails?.map((det, i) => (
            <div key={i} className="widget-fvs-detail">{det}</div>
          ))}
        </div>
      </div>

      {outcome && <div className="widget-fvs-outcome">{outcome}</div>}
    </div>
  )
}

registerWidget('faction_vs', FactionVs)
export default FactionVs
