/**
 * ServantComparison - FGO vs History comparison view
 * Shows side-by-side comparison of how Fate portrays a servant vs actual history.
 */
import { useEffect, useState } from 'react'
import { servantsApi } from '../../api/client'
import './ServantPanel.css'

interface ComparisonAspect {
  aspect: string
  fgo_description: string
  historical_description: string
  accuracy_score: number
  assessment: string
}

interface ComparisonData {
  fgo_name: string
  fgo_class?: string
  rarity?: number
  person_name?: string
  person_id?: number
  aspects: ComparisonAspect[]
  overall_accuracy: number
}

interface Props {
  fgoName: string
  onClose: () => void
  onPersonClick?: (personId: number) => void
}

const ASSESSMENT_STYLES: Record<string, { label: string; color: string }> = {
  accurate: { label: 'Accurate', color: '#22c55e' },
  artistic_license: { label: 'Artistic License', color: '#eab308' },
  fictional: { label: 'Fictional', color: '#ef4444' },
  composite: { label: 'Composite', color: '#3b82f6' },
  gender_swap: { label: 'Gender Swap', color: '#a855f7' },
}

export function ServantComparison({ fgoName, onClose, onPersonClick }: Props) {
  const [data, setData] = useState<ComparisonData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    servantsApi.get(`${encodeURIComponent(fgoName)}/comparison`)
      .then(res => setData(res.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [fgoName])

  if (loading) {
    return (
      <div className="servant-comparison-overlay" onClick={onClose}>
        <div className="servant-comparison" onClick={e => e.stopPropagation()}>
          <div className="loading">Loading comparison...</div>
        </div>
      </div>
    )
  }

  if (!data || data.aspects.length === 0) {
    return (
      <div className="servant-comparison-overlay" onClick={onClose}>
        <div className="servant-comparison" onClick={e => e.stopPropagation()}>
          <button className="close-btn" onClick={onClose}>x</button>
          <h2>{fgoName}</h2>
          <div className="no-books">No comparison data available yet.</div>
        </div>
      </div>
    )
  }

  const rarityStars = data.rarity ? '\u2605'.repeat(data.rarity) : ''

  return (
    <div className="servant-comparison-overlay" onClick={onClose}>
      <div className="servant-comparison" onClick={e => e.stopPropagation()}>
        <button className="close-btn" onClick={onClose}>x</button>

        <div className="comparison-header">
          <h2>{data.fgo_name}</h2>
          <div className="comparison-meta">
            {data.fgo_class && <span className="class-badge">{data.fgo_class}</span>}
            {rarityStars && <span className="rarity" style={{ color: '#ffc107' }}>{rarityStars}</span>}
          </div>
          {data.person_name && (
            <div className="comparison-person">
              Historical: <strong>{data.person_name}</strong>
              {data.person_id && onPersonClick && (
                <button
                  className="view-person-btn"
                  onClick={() => { onPersonClick(data.person_id!); onClose() }}
                >
                  View in CHALDEAS
                </button>
              )}
            </div>
          )}
          <div className="overall-accuracy">
            Overall Accuracy: <strong>{data.overall_accuracy}/5</strong>
          </div>
        </div>

        <div className="comparison-aspects">
          {data.aspects.map((aspect) => {
            const style = ASSESSMENT_STYLES[aspect.assessment] || ASSESSMENT_STYLES.artistic_license
            return (
              <div key={aspect.aspect} className="comparison-aspect">
                <div className="aspect-header">
                  <span className="aspect-name">{aspect.aspect}</span>
                  <span className="assessment-badge" style={{ background: style.color + '22', color: style.color, border: `1px solid ${style.color}44` }}>
                    {style.label}
                  </span>
                  <span className="accuracy-score">
                    {Array.from({ length: 5 }, (_, i) => (
                      <span key={i} style={{ color: i < aspect.accuracy_score ? '#ffc107' : '#333' }}>{'\u2605'}</span>
                    ))}
                  </span>
                </div>
                <div className="aspect-columns">
                  <div className="aspect-column fgo">
                    <div className="column-label">In Fate/Grand Order</div>
                    <p>{aspect.fgo_description}</p>
                  </div>
                  <div className="aspect-column history">
                    <div className="column-label">In History</div>
                    <p>{aspect.historical_description}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default ServantComparison
