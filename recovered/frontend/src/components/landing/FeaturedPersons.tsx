/**
 * FeaturedPersons (Welcome Experience) - Minimal landing overlay for first-time visitors.
 *
 * Globe-first design: just 2 buttons over a transparent overlay.
 * - Explore: closes overlay, flies to Classical Greece
 * - Read Stories: closes overlay, opens sidebar drawer
 */
import './Landing.css'

interface Props {
  onExplore: () => void
  onReadStories: () => void
  onClose: () => void
}

export function FeaturedPersons({ onExplore, onReadStories, onClose }: Props) {
  return (
    <div className="landing-overlay" onClick={onClose}>
      <div className="welcome-container welcome-minimal" onClick={(e) => e.stopPropagation()}>
        <div className="welcome-header">
          <div className="welcome-logo">C H A L D E A S</div>
          <div className="welcome-tagline">Experience history like time travel</div>
        </div>

        <div className="welcome-paths">
          {/* Explore - fly to globe */}
          <button className="welcome-path-card welcome-path-explore" onClick={onExplore}>
            <div className="welcome-path-icon">{'\uD83C\uDF0D'}</div>
            <div className="welcome-path-title">Explore</div>
            <div className="welcome-path-desc">
              Spin the globe, move through time, and discover history.
            </div>
          </button>

          {/* Read Stories - open sidebar drawer */}
          <button className="welcome-path-card welcome-path-tour" onClick={onReadStories}>
            <div className="welcome-path-icon">{'\uD83D\uDCD6'}</div>
            <div className="welcome-path-title">Read Stories</div>
            <div className="welcome-path-desc">
              Follow curated episodes as the globe moves through key moments.
            </div>
          </button>
        </div>
      </div>
    </div>
  )
}
