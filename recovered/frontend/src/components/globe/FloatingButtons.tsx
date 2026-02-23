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
    <div className="fixed right-3 bottom-24 z-50 flex flex-col gap-1.5 items-end">
      {BUTTONS.map(({ id, icon, label }) => (
        <div key={id} className="flex items-center gap-2 flex-row-reverse">
          <button
            onClick={handlers[id]}
            onMouseEnter={() => setHoveredId(id)}
            onMouseLeave={() => setHoveredId(null)}
            className="w-9 h-9 rounded-lg bg-chaldea-panel/80 backdrop-blur-xl
                       border border-chaldea-border/30 text-chaldea-cyan/70
                       flex items-center justify-center text-sm
                       hover:border-chaldea-cyan/30 hover:text-chaldea-cyan
                       hover:-translate-y-px transition-all shadow-lg shadow-black/20"
          >
            {icon}
          </button>
          {hoveredId === id && (
            <span className="bg-chaldea-panel/90 backdrop-blur-xl border border-chaldea-border/30
                             rounded-md px-2.5 py-1 text-[10px] font-semibold tracking-wide
                             text-chaldea-cyan/80 whitespace-nowrap animate-fade-in shadow-lg shadow-black/20">
              {label}
            </span>
          )}
        </div>
      ))}
    </div>
  )
}
