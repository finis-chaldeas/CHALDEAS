import { usePortalStore } from '../../store/portalStore'
import { useGlobeStore } from '../../store/globeStore'
import { useTimelineStore } from '../../store/timelineStore'
import { useSettingsStore } from '../../store/settingsStore'
import './ModeBar.css'

type Mode = 'sheba' | 'trismegistos' | 'shift'

interface ModeBarProps {
  onSearchClick: () => void
  onChatClick: () => void
  onMenuClick: () => void
  onShiftBrowse: () => void
  onTourClick?: () => void
}

export default function ModeBar({ onSearchClick, onChatClick, onMenuClick, onShiftBrowse, onTourClick }: ModeBarProps) {
  const isPortalOpen = usePortalStore((s) => s.isOpen)
  const isSuspended = usePortalStore((s) => s.isSuspended)
  const activeShift = useGlobeStore((s) => s.activeShift)
  const showMinorMarkers = useGlobeStore((s) => s.showMinorMarkers)
  const toggleMinorMarkers = useGlobeStore((s) => s.toggleMinorMarkers)
  const useCardMode = useSettingsStore((s) => s.useCardMode)
  const setUseCardMode = useSettingsStore((s) => s.setUseCardMode)

  // Determine current mode
  const currentMode: Mode = activeShift
    ? 'shift'
    : isPortalOpen
      ? 'trismegistos'
      : 'sheba'

  const handleTabClick = (mode: Mode) => {
    if (mode === currentMode) return

    switch (mode) {
      case 'sheba':
        if (isPortalOpen) {
          usePortalStore.getState().suspend()
        }
        if (activeShift) {
          useGlobeStore.getState().closeShift()
        }
        break

      case 'trismegistos':
        if (activeShift) {
          useGlobeStore.getState().closeShift()
        }
        {
          const { lat, lng } = useGlobeStore.getState().cameraPosition
          const year = useTimelineStore.getState().currentYear
          usePortalStore.getState().open({ lat, lng, year })
        }
        break

      case 'shift':
        if (isPortalOpen) {
          usePortalStore.getState().suspend()
        }
        if (activeShift) {
          // Already has an active shift — just switch to it
        } else {
          onShiftBrowse()
        }
        break
    }
  }

  const hasShift = !!activeShift

  return (
    <nav className="mode-bar">
      {/* Logo */}
      <div className="mode-bar__logo">CHALDEAS</div>

      {/* Mode Tabs */}
      <div className="mode-bar__tabs">
        <button
          className={`mode-bar__tab ${currentMode === 'sheba' ? 'mode-bar__tab--active' : ''}`}
          onClick={() => handleTabClick('sheba')}
        >
          <span className="mode-bar__tab-icon">{'\u25C9'}</span>
          <span className="mode-bar__tab-label">SHEBA</span>
        </button>

        <button
          className={`mode-bar__tab ${currentMode === 'trismegistos' ? 'mode-bar__tab--active' : ''} ${isSuspended && currentMode !== 'trismegistos' ? 'mode-bar__tab--suspended' : ''}`}
          onClick={() => handleTabClick('trismegistos')}
        >
          <span className="mode-bar__tab-icon">{'\u2726'}</span>
          <span className="mode-bar__tab-label">TRISMEGISTOS</span>
        </button>

        <button
          className={`mode-bar__tab ${currentMode === 'shift' ? 'mode-bar__tab--active' : ''} ${!hasShift && currentMode !== 'shift' ? 'mode-bar__tab--disabled' : ''}`}
          onClick={() => handleTabClick('shift')}
        >
          <span className="mode-bar__tab-icon">{'\u25B6'}</span>
          <span className="mode-bar__tab-label">SHIFT</span>
        </button>
      </div>

      {/* Action Icons */}
      <div className="mode-bar__actions">
        {onTourClick && (
          <button className="mode-bar__action" onClick={onTourClick} title="Guided Tours">
            {'\uD83C\uDFAC'}
          </button>
        )}
        <button
          className={`mode-bar__action ${useCardMode ? 'mode-bar__action--active' : ''}`}
          onClick={() => setUseCardMode(!useCardMode)}
          title="Card mode (Beta)"
        >
          {'\u2750'}
        </button>
        <button
          className={`mode-bar__action ${showMinorMarkers ? 'mode-bar__action--active' : ''}`}
          onClick={toggleMinorMarkers}
          title="Show minor events"
        >
          {'\u2295'}
        </button>
        <button className="mode-bar__action" onClick={onSearchClick} title="Search">
          {'\uD83D\uDD0D'}
        </button>
        <button className="mode-bar__action" onClick={onChatClick} title="LAPLACE">
          {'\u25C8'}
        </button>
        <button className="mode-bar__action" onClick={onMenuClick} title="Settings">
          {'\u2699'}
        </button>
      </div>
    </nav>
  )
}
