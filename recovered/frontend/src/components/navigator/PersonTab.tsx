/**
 * PersonTab - Viewport-aware historical figures list
 *
 * - Global: featured/high-connection persons for current era
 * - Regional/Local: persons with birthplace in visible viewport
 * - Shows connection count, lifespan, role
 */
import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { useDebounce } from '../../hooks/useDebounce'
import { api } from '../../api/client'
import type { ViewportBounds, ZoomLevel } from '../../store/globeStore'

interface PersonTabProps {
  currentYear: number
  viewportBounds: ViewportBounds | null
  zoomLevel: ZoomLevel
  onPersonClick: (personId: number) => void
}

interface Person {
  id: number
  name: string
  name_ko?: string
  birth_year?: number
  death_year?: number
  lifespan_display?: string
  connection_count?: number
  category?: { slug: string; name: string } | null
  birthplace?: { name: string } | null
}

const TIME_RANGE = 200

type SortOption = 'connections' | 'birth'

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'connections', label: 'Connections' },
  { value: 'birth', label: 'Birth Year' },
]

const DOMAIN_OPTIONS = [
  { value: '', label: 'All Fields' },
  { value: 'science', label: 'Science' },
  { value: 'philosophy', label: 'Philosophy' },
  { value: 'literature', label: 'Literature' },
  { value: 'military', label: 'Military' },
  { value: 'statecraft', label: 'Statecraft' },
  { value: 'visual_arts', label: 'Visual Arts' },
  { value: 'music', label: 'Music' },
  { value: 'religion', label: 'Religion' },
  { value: 'mathematics', label: 'Mathematics' },
  { value: 'exploration', label: 'Exploration' },
]

function formatLifespan(person: Person): string {
  if (person.lifespan_display) return person.lifespan_display
  if (person.birth_year != null && person.death_year != null) {
    const birth = person.birth_year < 0 ? `${Math.abs(person.birth_year)} BCE` : `${person.birth_year}`
    const death = person.death_year < 0 ? `${Math.abs(person.death_year)} BCE` : `${person.death_year}`
    return `${birth} \u2013 ${death}`
  }
  if (person.birth_year != null) {
    const birth = person.birth_year < 0 ? `${Math.abs(person.birth_year)} BCE` : `${person.birth_year}`
    return `b. ${birth}`
  }
  return ''
}

function getConnectionBadge(count: number): { label: string; cls: string } {
  if (count >= 20) return { label: `${count}`, cls: 'conn-high' }
  if (count >= 10) return { label: `${count}`, cls: 'conn-med' }
  if (count > 0) return { label: `${count}`, cls: 'conn-low' }
  return { label: '', cls: '' }
}

export function PersonTab({ currentYear, viewportBounds, zoomLevel, onPersonClick }: PersonTabProps) {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<SortOption>('connections')
  const [domainFilter, setDomainFilter] = useState('')
  const debouncedYear = useDebounce(currentYear, 150)
  const debouncedBounds = useDebounce(viewportBounds, 300)

  const queryParams = useMemo(() => {
    const params: Record<string, unknown> = {
      limit: 100,
      sort_by: sortBy,
    }

    if (domainFilter) {
      params.domain = domainFilter
    }

    if (searchQuery) {
      params.q = searchQuery
    } else {
      params.year_start = debouncedYear - TIME_RANGE
      params.year_end = debouncedYear + TIME_RANGE

      if (zoomLevel !== 'cosmic' && debouncedBounds) {
        params.lat_min = debouncedBounds.south
        params.lat_max = debouncedBounds.north
        params.lng_min = debouncedBounds.west
        params.lng_max = debouncedBounds.east
      }
    }

    return params
  }, [searchQuery, debouncedYear, zoomLevel, debouncedBounds, sortBy, domainFilter])

  const { data, isLoading } = useQuery({
    queryKey: ['navigator-persons', queryParams],
    queryFn: () => api.get('/persons', { params: queryParams }),
    select: (res) => res.data,
  })

  const persons: Person[] = data?.items || []

  return (
    <div className="navigator-tab-content">
      {/* Controls */}
      <div className="nav-controls">
        <div className="nav-controls-row">
          <input
            type="text"
            placeholder={t('navigator.searchPersons', 'Search persons...')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="nav-search-input"
          />
          <select
            className="nav-select nav-select-sm"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortOption)}
          >
            {SORT_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div className="nav-controls-row">
          <select
            className="nav-select"
            value={domainFilter}
            onChange={(e) => setDomainFilter(e.target.value)}
          >
            {DOMAIN_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div className="nav-result-count">
          {persons.length} {t('navigator.persons', 'persons')}
          {zoomLevel !== 'cosmic' && <span className="nav-viewport-tag">viewport</span>}
        </div>
      </div>

      {/* List */}
      <div className="nav-list">
        {isLoading ? (
          <div className="navigator-loading">{t('common.loading', 'Loading...')}</div>
        ) : persons.length === 0 ? (
          <div className="navigator-empty">{t('navigator.noPersons', 'No persons found')}</div>
        ) : (
          persons.map((person) => {
            const conns = person.connection_count || 0
            const badge = getConnectionBadge(conns)
            const lifespan = formatLifespan(person)
            const catName = person.category?.name
            const birthplace = person.birthplace?.name

            return (
              <button
                key={person.id}
                className="nav-person-card"
                onClick={() => onPersonClick(person.id)}
              >
                <div className="nav-person-avatar">
                  {person.name.charAt(0).toUpperCase()}
                </div>
                <div className="nav-person-body">
                  <div className="nav-person-name">{person.name}</div>
                  <div className="nav-person-meta">
                    {lifespan && <span className="nav-person-lifespan">{lifespan}</span>}
                    {catName && <span className="nav-person-role">{catName}</span>}
                    {birthplace && <span className="nav-person-place">{birthplace}</span>}
                  </div>
                </div>
                {badge.label && (
                  <div className={`nav-conn-badge ${badge.cls}`} title={`${conns} connections`}>
                    {badge.label}
                  </div>
                )}
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}
