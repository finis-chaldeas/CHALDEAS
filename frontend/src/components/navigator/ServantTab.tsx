/**
 * ServantTab - TRISMEGISTUS servant browser (inline, not modal)
 *
 * Displays FGO servants with class filters, search, and inline detail view.
 * Replaces the old ServantPanel modal.
 */
import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { servantsApi } from '../../api/client'
import { ServantTabDetail } from './ServantTabDetail'

interface Servant {
  fgo_name: string
  fgo_class?: string
  rarity?: number
  origin?: string
  person_id?: number
  person_name?: string
  wikidata_id?: string
  mention_count: number
  is_fgo_original: boolean
}

interface ServantTabProps {
  onPersonClick?: (personId: number) => void
  onFlyToLocation?: (lat: number, lng: number) => void
  onSetCurrentYear?: (year: number) => void
}

const CLASS_ICONS: Record<string, string> = {
  Saber: '\u2694\uFE0F',
  Archer: '\uD83C\uDFF9',
  Lancer: '\uD83D\uDD31',
  Rider: '\uD83C\uDFC7',
  Caster: '\uD83D\uDD2E',
  Assassin: '\uD83D\uDDE1\uFE0F',
  Berserker: '\uD83D\uDCA2',
  Ruler: '\u2696\uFE0F',
  Avenger: '\uD83D\uDD25',
  Shielder: '\uD83D\uDEE1\uFE0F',
  Foreigner: '\uD83C\uDF0C',
  'Alter Ego': '\uD83C\uDFAD',
  'Moon Cancer': '\uD83C\uDF19',
  Pretender: '\uD83C\uDFAD',
  Beast: '\uD83D\uDC32',
}

const CLASS_ORDER = ['Saber', 'Archer', 'Lancer', 'Rider', 'Caster', 'Assassin', 'Berserker', 'Extra']

function getClassIcon(cls?: string): string {
  if (!cls) return '\u2726'
  return CLASS_ICONS[cls] || '\u2726'
}

function rarityStars(rarity?: number): string {
  if (!rarity) return ''
  return '\u2605'.repeat(rarity)
}

export function ServantTab({ onPersonClick, onFlyToLocation, onSetCurrentYear }: ServantTabProps) {
  const [search, setSearch] = useState('')
  const [classFilter, setClassFilter] = useState<string | null>(null)
  const [selectedServantName, setSelectedServantName] = useState<string | null>(null)

  // Fetch all servants
  const { data: servants = [], isLoading } = useQuery<Servant[]>({
    queryKey: ['servants-list'],
    queryFn: async () => {
      const res = await servantsApi.list({ limit: 200, has_books: true })
      return res.data
    },
    staleTime: 5 * 60 * 1000,
  })

  // Client-side filtering
  const filteredServants = useMemo(() => {
    let result = servants
    if (classFilter) {
      if (classFilter === 'Extra') {
        const mainClasses = new Set(['Saber', 'Archer', 'Lancer', 'Rider', 'Caster', 'Assassin', 'Berserker'])
        result = result.filter(s => !s.fgo_class || !mainClasses.has(s.fgo_class))
      } else {
        result = result.filter(s => s.fgo_class === classFilter)
      }
    }
    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(s =>
        s.fgo_name.toLowerCase().includes(q) ||
        (s.person_name && s.person_name.toLowerCase().includes(q)) ||
        (s.origin && s.origin.toLowerCase().includes(q))
      )
    }
    return result
  }, [servants, classFilter, search])

  // If detail view selected
  if (selectedServantName) {
    return (
      <div className="navigator-tab-content">
        <ServantTabDetail
          fgoName={selectedServantName}
          onBack={() => setSelectedServantName(null)}
          onPersonClick={onPersonClick}
          onFlyToLocation={onFlyToLocation}
          onSetCurrentYear={onSetCurrentYear}
        />
      </div>
    )
  }

  return (
    <div className="navigator-tab-content">
      {/* Header with class filters */}
      <div className="servant-tab-header">
        <div className="servant-tab-tagline">Observe the true history of Heroic Spirits</div>
        <div className="servant-class-filters">
          {CLASS_ORDER.map(cls => (
            <button
              key={cls}
              className={`servant-class-btn ${classFilter === cls ? 'active' : ''}`}
              onClick={() => setClassFilter(classFilter === cls ? null : cls)}
            >
              {cls}
            </button>
          ))}
        </div>
        <input
          type="text"
          className="nav-search-input servant-tab-search"
          placeholder="Search servants..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Controls */}
      <div className="nav-controls">
        <div className="nav-result-count">
          {filteredServants.length} servants
          {classFilter && <span className="nav-viewport-tag">{classFilter}</span>}
        </div>
      </div>

      {/* Servant list */}
      <div className="nav-list">
        {isLoading ? (
          <div className="navigator-loading">Loading servants...</div>
        ) : filteredServants.length === 0 ? (
          <div className="navigator-empty">No servants found</div>
        ) : (
          filteredServants.map(servant => (
            <button
              key={servant.fgo_name}
              className="servant-tab-card"
              onClick={() => setSelectedServantName(servant.fgo_name)}
            >
              <span className="servant-tab-class-icon">
                {getClassIcon(servant.fgo_class)}
              </span>
              <div className="servant-tab-body">
                <div className="servant-tab-name">
                  {servant.fgo_name}
                  {servant.rarity && (
                    <span className="servant-tab-rarity">{rarityStars(servant.rarity)}</span>
                  )}
                  {servant.is_fgo_original && (
                    <span className="servant-fgo-badge">FGO</span>
                  )}
                </div>
                {(servant.person_name || servant.origin) && (
                  <div className="servant-tab-origin">
                    {servant.person_name || servant.origin}
                  </div>
                )}
              </div>
              {servant.mention_count > 0 && (
                <div className="servant-tab-actions" style={{ opacity: 1 }}>
                  <span className="feed-card-events-badge">{servant.mention_count.toLocaleString()}</span>
                </div>
              )}
            </button>
          ))
        )}
      </div>
    </div>
  )
}
