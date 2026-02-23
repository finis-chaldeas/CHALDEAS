/**
 * DomainTimelineModal - Browse history by domain (science, philosophy, literature, etc.)
 *
 * Master Plan V3 - B4: Domain Timeline
 * Uses persons.domain data (178K classified persons) to show
 * the history of a specific field from ancient to modern.
 */
import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { personsApi } from '../../api/client'
import './DomainTimelineModal.css'

interface DomainTimelineModalProps {
  isOpen: boolean
  onClose: () => void
  onPersonClick: (personId: number) => void
  onOpenTimeline?: () => void
  initialDomain?: string
}

interface DomainPerson {
  id: number
  name: string
  name_ko?: string
  birth_year?: number
  death_year?: number
  role?: string
  domain?: string
  global_score?: number
  lifespan_display?: string
}

const DOMAINS = [
  { key: 'science', label: 'Science', label_ko: '\uacfc\ud559', icon: '\uD83D\uDD2C', color: '#4fc3f7' },
  { key: 'philosophy', label: 'Philosophy', label_ko: '\ucca0\ud559', icon: '\uD83E\uDDD0', color: '#ce93d8' },
  { key: 'literature', label: 'Literature', label_ko: '\ubb38\ud559', icon: '\uD83D\uDCDA', color: '#a5d6a7' },
  { key: 'military', label: 'Military', label_ko: '\uad70\uc0ac', icon: '\u2694\uFE0F', color: '#ef5350' },
  { key: 'statecraft', label: 'Statecraft', label_ko: '\uc815\uce58', icon: '\uD83D\uDC51', color: '#ffd54f' },
  { key: 'visual_arts', label: 'Visual Arts', label_ko: '\ubbf8\uc220', icon: '\uD83C\uDFA8', color: '#ff8a65' },
  { key: 'music', label: 'Music', label_ko: '\uc74c\uc545', icon: '\uD83C\uDFB5', color: '#f48fb1' },
  { key: 'religion', label: 'Religion', label_ko: '\uc885\uad50', icon: '\u2721', color: '#fff176' },
  { key: 'medicine', label: 'Medicine', label_ko: '\uc758\ud559', icon: '\u2695\uFE0F', color: '#80cbc4' },
  { key: 'technology', label: 'Technology', label_ko: '\uae30\uc220', icon: '\u2699\uFE0F', color: '#90a4ae' },
  { key: 'exploration', label: 'Exploration', label_ko: '\ud0d0\ud5d8', icon: '\uD83E\uDDED', color: '#4db6ac' },
  { key: 'scholarship', label: 'Scholarship', label_ko: '\ud559\ubb38', icon: '\uD83C\uDF93', color: '#9fa8da' },
] as const

type DomainKey = typeof DOMAINS[number]['key']

// Era definitions for grouping
const ERAS = [
  { key: 'ancient', label: 'Ancient', range: [-3000, -500] },
  { key: 'classical', label: 'Classical', range: [-500, 500] },
  { key: 'medieval', label: 'Medieval', range: [500, 1500] },
  { key: 'early_modern', label: 'Early Modern', range: [1500, 1800] },
  { key: 'modern', label: 'Modern', range: [1800, 1950] },
  { key: 'contemporary', label: 'Contemporary', range: [1950, 2100] },
]

function formatYear(year: number | undefined | null): string {
  if (year == null) return '?'
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

export function DomainTimelineModal({
  isOpen,
  onClose,
  onPersonClick,
  onOpenTimeline,
  initialDomain,
}: DomainTimelineModalProps) {
  const [selectedDomain, setSelectedDomain] = useState<DomainKey | null>(
    (initialDomain as DomainKey) || null
  )

  // Fetch top persons for selected domain
  const { data: persons, isLoading } = useQuery({
    queryKey: ['domain-timeline', selectedDomain],
    queryFn: () => personsApi.list({
      domain: selectedDomain,
      sort_by: 'importance',
      limit: 200,
    }),
    enabled: !!selectedDomain,
    select: (res) => (res.data?.items || []) as DomainPerson[],
    staleTime: 5 * 60 * 1000,
  })

  // Group persons by era
  const groupedByEra = useMemo(() => {
    if (!persons) return []

    return ERAS.map(era => {
      const eraPersons = persons.filter(p => {
        const year = p.birth_year ?? p.death_year
        if (year == null) return false
        return year >= era.range[0] && year < era.range[1]
      })
      return {
        ...era,
        persons: eraPersons,
      }
    }).filter(era => era.persons.length > 0)
  }, [persons])

  const domainInfo = DOMAINS.find(d => d.key === selectedDomain)

  if (!isOpen) return null

  return (
    <div className="domain-timeline-overlay" onClick={onClose}>
      <div className="domain-timeline-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="domain-timeline-header">
          <div className="domain-timeline-title-row">
            {selectedDomain && (
              <button
                className="domain-timeline-back"
                onClick={() => setSelectedDomain(null)}
              >
                {'\u2190'}
              </button>
            )}
            <h2 className="domain-timeline-title">
              {selectedDomain
                ? `${domainInfo?.icon || ''} History of ${domainInfo?.label || selectedDomain}`
                : 'Domain Timeline'
              }
            </h2>
            <button className="domain-timeline-close" onClick={onClose}>
              {'\u2715'}
            </button>
          </div>
          {!selectedDomain && (
            <p className="domain-timeline-subtitle">
              Choose a field to explore its history from ancient times to the modern era.
            </p>
          )}
        </div>

        {/* Domain Selection Grid */}
        {!selectedDomain && (
          <div className="domain-grid">
            {DOMAINS.map(domain => (
              <button
                key={domain.key}
                className="domain-grid-card"
                onClick={() => setSelectedDomain(domain.key)}
                style={{ '--domain-color': domain.color } as React.CSSProperties}
              >
                <span className="domain-grid-icon">{domain.icon}</span>
                <span className="domain-grid-label">{domain.label}</span>
                <span className="domain-grid-label-ko">{domain.label_ko}</span>
              </button>
            ))}
          </div>
        )}

        {/* Domain Timeline Content */}
        {selectedDomain && (
          <div className="domain-timeline-content">
            {isLoading && (
              <div className="domain-timeline-loading">Loading...</div>
            )}

            {!isLoading && groupedByEra.length === 0 && (
              <div className="domain-timeline-empty">No data available for this domain.</div>
            )}

            {groupedByEra.map(era => (
              <div key={era.key} className="domain-era-group">
                <div className="domain-era-header">
                  <span className="domain-era-label">{era.label.toUpperCase()}</span>
                  <span className="domain-era-range">
                    {formatYear(era.range[0])} ~ {formatYear(era.range[1])}
                  </span>
                </div>

                <div className="domain-era-timeline">
                  {era.persons.map((person, i) => (
                    <div key={person.id} className="domain-person-entry">
                      <div className="domain-person-dot" style={{
                        background: domainInfo?.color || '#4fc3f7'
                      }} />
                      {i < era.persons.length - 1 && (
                        <div className="domain-person-line" />
                      )}
                      <div className="domain-person-content">
                        <button
                          className="domain-person-btn"
                          onClick={() => onPersonClick(person.id)}
                        >
                          <span className="domain-person-year">
                            {formatYear(person.birth_year)}
                          </span>
                          <span className="domain-person-name">
                            {person.name}
                          </span>
                          {person.name_ko && (
                            <span className="domain-person-name-ko">
                              {person.name_ko}
                            </span>
                          )}
                        </button>
                        {person.role && (
                          <div className="domain-person-role">{person.role}</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}

            {/* Link to full timeline */}
            {onOpenTimeline && (
              <div className="domain-timeline-footer">
                <button
                  className="domain-timeline-link"
                  onClick={() => { onClose(); onOpenTimeline(); }}
                >
                  View in full Timeline {'\u2192'}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
