import { useTranslation } from 'react-i18next'
import { registerWidget, loc, type WidgetProps } from './registry'

interface ContextItem {
  region?: string
  text?: string
  [key: string]: unknown
}

function EraContext({ data, lang }: WidgetProps) {
  const items = data.items as ContextItem[] | undefined
  const { t } = useTranslation()
  if (!items?.length) return null

  const heading = loc(data, 'heading', lang) || t('trismegistos.widget.meanwhile')

  return (
    <div className="widget-card widget-era">
      <div className="widget-era-heading">{heading}</div>
      <div className="widget-era-list">
        {items.map((item, i) => {
          const region = loc(item as Record<string, unknown>, 'region', lang)
          const text = loc(item as Record<string, unknown>, 'text', lang)
          if (!text) return null

          return (
            <div key={i} className="widget-era-item">
              {region && <span className="widget-era-region">{region}</span>}
              <span className="widget-era-text">{text}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

registerWidget('era_context', EraContext)
export default EraContext
