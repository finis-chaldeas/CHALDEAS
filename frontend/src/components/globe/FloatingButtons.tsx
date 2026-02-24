import { useState } from 'react'

interface FloatingButtonsProps {
  onSearchClick: () => void
  onShowcaseClick: () => void
  onRayshiftClick: () => void
  onChatClick: () => void
  onMenuClick: () => void
}

const BUTTONS = [
  { id: 'search', icon: '\uD83D\uDD0D', label: 'Search' },
  { id: 'showcase', icon: '\u2726', label: 'TRISMEGISTUS' },
  { id: 'rayshift', icon: '\u21E8', label: 'Rayshift' },
  { id: 'chat', icon: '\u25C8', label: 'LAPLACE' },
  { id: 'menu', icon: '\u2699', label: 'Settings' },
] as const

export default function FloatingButtons({
  onSearchClick, onShowcaseClick, onRayshiftClick, onChatClick, onMenuClick,
}: FloatingButtonsProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  const handlers: Record<string, () => void> = {
    search: onSearchClick, showcase: onShowcaseClick,
    rayshift: onRayshiftClick, chat: onChatClick, menu: onMenuClick,
  }

  return (
    <div className="floating-buttons">
      {BUTTONS.map(({ id, icon, label }) => (
        <div key={id} className="floating-btn-row">
          <button
            onClick={handlers[id]}
            onMouseEnter={() => setHoveredId(id)}
            onMouseLeave={() => setHoveredId(null)}
            className="floating-btn"
          >
            {icon}
          </button>
          {hoveredId === id && (
            <span className="floating-btn-label">
              {label}
            </span>
          )}
        </div>
      ))}
    </div>
  )
}
