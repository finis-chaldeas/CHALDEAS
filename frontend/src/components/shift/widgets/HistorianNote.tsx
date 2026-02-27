import { registerWidget, loc, type WidgetProps } from './registry'

function HistorianNote({ data, lang }: WidgetProps) {
  const note = loc(data, 'note', lang)
  if (!note) return null

  const historian = loc(data, 'historian', lang)
  const work = loc(data, 'work', lang)
  const tone = (data.tone as string) || 'neutral' // neutral | caution | praise

  const toneClass = `widget-hnote--${tone}`

  return (
    <div className={`widget-card widget-hnote ${toneClass}`}>
      <div className="widget-hnote-icon">
        {tone === 'caution' ? '\u26A0' : tone === 'praise' ? '\u2605' : '\uD83D\uDCDD'}
      </div>
      <div className="widget-hnote-body">
        <div className="widget-hnote-text">{note}</div>
        {(historian || work) && (
          <div className="widget-hnote-attr">
            {historian && <span className="widget-hnote-who">{historian}</span>}
            {work && <span className="widget-hnote-work">{work}</span>}
          </div>
        )}
      </div>
    </div>
  )
}

registerWidget('historian_note', HistorianNote)
export default HistorianNote
