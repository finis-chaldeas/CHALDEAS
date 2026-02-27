import { registerWidget, loc, type WidgetProps } from './registry'

function PrimaryQuote({ data, lang }: WidgetProps) {
  const text = loc(data, 'text', lang)
  if (!text) return null

  const source = loc(data, 'source', lang)
  const speaker = loc(data, 'speaker', lang)
  const year = data.year as number | undefined

  return (
    <div className="widget-card widget-quote">
      <blockquote className="widget-quote-text">{text}</blockquote>
      <div className="widget-quote-attr">
        {speaker && <span className="widget-quote-speaker">{speaker}</span>}
        <span className="widget-quote-source">{source}</span>
        {year != null && (
          <span className="widget-quote-year">
            {year < 0 ? `${Math.abs(year)} BCE` : `${year} CE`}
          </span>
        )}
      </div>
    </div>
  )
}

registerWidget('primary_quote', PrimaryQuote)
export default PrimaryQuote
