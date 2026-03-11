import { useTranslation } from 'react-i18next'
import { registerWidget, loc, type WidgetProps } from './registry'

function WeDontKnow({ data, lang }: WidgetProps) {
  const { t } = useTranslation()
  const question = loc(data, 'question', lang)
  if (!question) return null

  const detail = loc(data, 'detail', lang)
  const theories = loc(data, 'theories', lang)

  return (
    <div className="widget-card widget-wdk">
      <div className="widget-wdk-header">
        <span className="widget-wdk-icon">?</span>
        <span className="widget-wdk-label">{t('trismegistos.widget.weDontKnow')}</span>
      </div>
      <div className="widget-wdk-question">{question}</div>
      {detail && <div className="widget-wdk-detail">{detail}</div>}
      {theories && <div className="widget-wdk-theories">{theories}</div>}
    </div>
  )
}

registerWidget('we_dont_know', WeDontKnow)
export default WeDontKnow
