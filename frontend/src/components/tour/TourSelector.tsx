/**
 * TourSelector - Grid of available tour episodes.
 * Shown as a modal overlay when user clicks "Guided Tour" from landing or ModeBar.
 */
import { SHEBA_EPISODES, type ShebaEpisode } from '../../data/shebaEpisodes'
import '../landing/Landing.css'

interface Props {
  onSelectEpisode: (episode: ShebaEpisode) => void
  onClose: () => void
}

function formatDateRange(start: number, end: number): string {
  const fmt = (y: number) => y < 0 ? `${Math.abs(y)} BCE` : `${y} CE`
  if (start === end) return fmt(start)
  return `${fmt(start)} – ${fmt(end)}`
}

export function TourSelector({ onSelectEpisode, onClose }: Props) {
  const episodes = SHEBA_EPISODES.filter(ep => ep.tourSteps && ep.tourSteps.length > 0)

  return (
    <div className="landing-overlay" onClick={onClose}>
      <div className="landing-container" onClick={(e) => e.stopPropagation()}>
        <div className="landing-header">
          <div>
            <div className="landing-logo">Guided Tours</div>
            <div className="landing-subtitle">Watch history unfold on the globe</div>
          </div>
          <button className="landing-close" onClick={onClose}>Close</button>
        </div>

        <div className="tour-selection-grid">
          {episodes.map((ep, i) => (
            <button
              key={ep.id}
              className="tour-selection-card"
              style={{ animationDelay: `${i * 0.03}s` }}
              onClick={() => onSelectEpisode(ep)}
            >
              <div className="tour-card-region">{ep.region}</div>
              <div className="tour-card-title">{ep.title}</div>
              {ep.title_ko && <div className="tour-card-title-ko">{ep.title_ko}</div>}
              <div className="tour-card-desc">{ep.description}</div>
              <div className="tour-card-meta">
                <span className="tour-card-date">
                  {formatDateRange(ep.dateRange.start, ep.dateRange.end)}
                </span>
                <span className="tour-card-steps">
                  {ep.tourSteps?.length || 0} steps
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
