import { registerWidget, loc, type WidgetProps } from './registry'

function NarratorAside({ data, lang }: WidgetProps) {
  const text = loc(data, 'text', lang)
  if (!text) return null

  return (
    <div className="widget-card widget-naside">
      <div className="widget-naside-text">{text}</div>
    </div>
  )
}

registerWidget('narrator_aside', NarratorAside)
export default NarratorAside
