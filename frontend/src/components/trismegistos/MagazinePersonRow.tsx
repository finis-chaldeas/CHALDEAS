import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'

interface PersonItem {
  id: number
  name: string
  name_ko?: string
  name_ja?: string
  birth_year?: number
  death_year?: number
  role?: string
}

interface Props {
  persons: PersonItem[]
  onPersonClick: (personId: number) => void
}

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

function formatLifespan(p: PersonItem): string {
  const parts: string[] = []
  if (p.birth_year != null) parts.push(formatYear(p.birth_year))
  if (p.death_year != null) parts.push(formatYear(p.death_year))
  return parts.join(' ~ ')
}

export function MagazinePersonRow({ persons, onPersonClick }: Props) {
  const { preferredLanguage } = useSettingsStore()

  return (
    <div className="mag-person-row">
      {persons.map((person) => {
        const name = getLocalizedText(person, 'name', preferredLanguage)
        return (
          <button
            key={person.id}
            className="mag-person-card"
            onClick={() => onPersonClick(person.id)}
          >
            <div className="mag-person-card__name">{name}</div>
            <div className="mag-person-card__lifespan">{formatLifespan(person)}</div>
            {person.role && (
              <div className="mag-person-card__role">{person.role}</div>
            )}
          </button>
        )
      })}
    </div>
  )
}
