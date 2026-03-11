import { useTranslation } from 'react-i18next'
import { registerWidget, loc, locArray, type WidgetProps } from './registry'

interface AllianceGroup {
  name?: string
  members?: string[]
  color?: string
  [key: string]: unknown
}

function AllianceDiagram({ data, lang }: WidgetProps) {
  const groups = data.groups as AllianceGroup[] | undefined
  const { t } = useTranslation()
  if (!groups?.length) return null

  const heading = loc(data, 'heading', lang) || t('trismegistos.widget.alliances')

  const COLORS = [
    'var(--chaldea-cyan)',
    'var(--chaldea-magenta)',
    'var(--chaldea-gold)',
    'var(--chaldea-green, #22c55e)',
  ]

  return (
    <div className="widget-card widget-ally">
      <div className="widget-ally-heading">{heading}</div>
      <div className="widget-ally-groups">
        {groups.map((g, i) => {
          const rec = g as Record<string, unknown>
          const name = loc(rec, 'name', lang)
          const members = locArray(rec, 'members', lang)
          const color = (g.color as string) || COLORS[i % COLORS.length]
          if (!name && !members?.length) return null

          return (
            <div key={i} className="widget-ally-group" style={{ borderColor: color }}>
              {name && (
                <div className="widget-ally-name" style={{ color }}>
                  {name}
                </div>
              )}
              {members && (
                <div className="widget-ally-members">
                  {members.map((m, j) => (
                    <span key={j} className="widget-ally-member">{m}</span>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

registerWidget('alliance_diagram', AllianceDiagram)
export default AllianceDiagram
