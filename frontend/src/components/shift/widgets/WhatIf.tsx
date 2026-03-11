import { useTranslation } from 'react-i18next'
import { registerWidget, loc, type WidgetProps } from './registry'

function WhatIf({ data, lang }: WidgetProps) {
  const { t } = useTranslation()
  const hypothesis = loc(data, 'hypothesis', lang)
  if (!hypothesis) return null

  const consequence = loc(data, 'consequence', lang)

  return (
    <div className="widget-card widget-wif">
      <div className="widget-wif-label">{t('trismegistos.widget.whatIf')}</div>
      <div className="widget-wif-hypo">{hypothesis}</div>
      {consequence && <div className="widget-wif-cons">{consequence}</div>}
    </div>
  )
}

registerWidget('what_if', WhatIf)
export default WhatIf
