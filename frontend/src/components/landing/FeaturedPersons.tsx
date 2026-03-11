/**
 * FeaturedPersons (Welcome Experience) - Landing overlay for first-time visitors.
 *
 * Globe-first design: 3 path cards + quick controls guide.
 * - Explore: closes overlay, flies to Classical Greece
 * - Guided Tour: closes overlay, opens tour episode selection
 * - Read Stories: closes overlay, opens TRISMEGISTOS portal
 */
import './Landing.css'

interface Props {
  onExplore: () => void
  onGuidedTour: () => void
  onReadStories: () => void
  onClose: () => void
}

export function FeaturedPersons({ onExplore, onGuidedTour, onReadStories, onClose }: Props) {
  return (
    <div className="landing-overlay" onClick={onClose}>
      <div className="welcome-container welcome-minimal" onClick={(e) => e.stopPropagation()}>
        <div className="welcome-header">
          <div className="welcome-logo">C H A L D E A S</div>
          <div className="welcome-tagline">Experience history like time travel</div>
        </div>

        <div className="welcome-paths welcome-paths--three">
          {/* Explore - fly to globe */}
          <button className="welcome-path-card welcome-path-explore" onClick={onExplore}>
            <div className="welcome-path-icon">{'\uD83C\uDF0D'}</div>
            <div className="welcome-path-title">Explore</div>
            <div className="welcome-path-desc">
              Spin the globe, move through time, and discover history.
            </div>
          </button>

          {/* Guided Tour - open episode selection */}
          <button className="welcome-path-card welcome-path-timeline" onClick={onGuidedTour}>
            <div className="welcome-path-icon">{'\uD83C\uDFAC'}</div>
            <div className="welcome-path-title">Guided Tour</div>
            <div className="welcome-path-desc">
              Watch history unfold as the globe flies through key moments.
            </div>
          </button>

          {/* Read Stories - open portal */}
          <button className="welcome-path-card welcome-path-tour" onClick={onReadStories}>
            <div className="welcome-path-icon">{'\uD83D\uDCD6'}</div>
            <div className="welcome-path-title">Read Stories</div>
            <div className="welcome-path-desc">
              Browse curated articles and deep dives into world history.
            </div>
          </button>
        </div>

        <div className="welcome-controls-hint">
          <span className="welcome-hint-item">{'\uD83D\uDDB1\uFE0F'} Drag to rotate</span>
          <span className="welcome-hint-sep">{'\u00B7'}</span>
          <span className="welcome-hint-item">{'\u23F1\uFE0F'} Timeline to time-travel</span>
          <span className="welcome-hint-sep">{'\u00B7'}</span>
          <span className="welcome-hint-item">{'\uD83D\uDD0D'} Zoom to explore</span>
        </div>
      </div>
    </div>
  )
}
