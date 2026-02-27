import { registerWidget, loc, type WidgetProps } from './registry'

function PersonCard({ data, lang }: WidgetProps) {
  const name = loc(data, 'name', lang)
  if (!name) return null

  const role = loc(data, 'role', lang)
  const summary = loc(data, 'summary', lang)
  const birthYear = data.birth_year as number | undefined
  const deathYear = data.death_year as number | undefined

  const fmtYear = (y: number) => (y < 0 ? `${Math.abs(y)} BCE` : `${y} CE`)

  const lifespan =
    birthYear != null && deathYear != null
      ? `${fmtYear(birthYear)} – ${fmtYear(deathYear)}`
      : birthYear != null
        ? `b. ${fmtYear(birthYear)}`
        : deathYear != null
          ? `d. ${fmtYear(deathYear)}`
          : null

  return (
    <div className="widget-card widget-person">
      <div className="widget-person-header">
        <div className="widget-person-name">{name}</div>
        {role && <div className="widget-person-role">{role}</div>}
      </div>
      {lifespan && <div className="widget-person-life">{lifespan}</div>}
      {summary && <div className="widget-person-summary">{summary}</div>}
    </div>
  )
}

registerWidget('person_card', PersonCard)
export default PersonCard
