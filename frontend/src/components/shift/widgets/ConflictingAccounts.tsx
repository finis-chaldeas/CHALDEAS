import { useTranslation } from 'react-i18next'
import { registerWidget, loc, type WidgetProps } from './registry'

interface Account {
  source?: string
  claim?: string
  [key: string]: unknown
}

function ConflictingAccounts({ data, lang }: WidgetProps) {
  const accounts = data.accounts as Account[] | undefined
  const { t } = useTranslation()
  if (!accounts?.length || accounts.length < 2) return null

  const heading = loc(data, 'heading', lang) || loc(data, 'topic', lang) || t('trismegistos.widget.conflictingAccounts')
  const verdict = loc(data, 'verdict', lang)

  return (
    <div className="widget-card widget-conf">
      <div className="widget-conf-heading">{heading}</div>
      <div className="widget-conf-list">
        {accounts.map((a, i) => {
          const rec = a as Record<string, unknown>
          const source = loc(rec, 'source', lang)
          const claim = loc(rec, 'claim', lang)
          if (!claim) return null

          return (
            <div key={i} className="widget-conf-item">
              {source && <div className="widget-conf-source">{source}</div>}
              <div className="widget-conf-claim">{claim}</div>
            </div>
          )
        })}
      </div>
      {verdict && (
        <div className="widget-conf-verdict">{verdict}</div>
      )}
    </div>
  )
}

registerWidget('conflicting_accounts', ConflictingAccounts)
export default ConflictingAccounts
