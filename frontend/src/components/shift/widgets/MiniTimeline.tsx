import { registerWidget, loc, type WidgetProps } from './registry'

interface TimelineEvent {
  year?: number
  label?: string
  [key: string]: unknown
}

function MiniTimeline({ data, lang }: WidgetProps) {
  const events = data.events as TimelineEvent[] | undefined
  if (!events?.length) return null

  const heading = loc(data, 'heading', lang)

  return (
    <div className="widget-card widget-tl">
      {heading && <div className="widget-tl-heading">{heading}</div>}
      <div className="widget-tl-track">
        {events.map((evt, i) => {
          const label = loc(evt as Record<string, unknown>, 'label', lang)
          const year = evt.year as number | undefined
          const highlight = !!evt.highlight

          return (
            <div
              key={i}
              className={`widget-tl-item${highlight ? ' widget-tl-item--hl' : ''}`}
            >
              <div className="widget-tl-dot" />
              <div className="widget-tl-content">
                {year != null && (
                  <span className="widget-tl-year">
                    {year < 0 ? `${Math.abs(year)} BCE` : `${year} CE`}
                  </span>
                )}
                <span className="widget-tl-label">{label}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

registerWidget('mini_timeline', MiniTimeline)
export default MiniTimeline
