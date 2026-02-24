import { useGlobeStore, type CameraMode } from '../../store/globeStore'
import { useSettingsStore, type GlobeStyleOption } from '../../store/settingsStore'

const MODES: { mode: CameraMode; label: string; hint: string }[] = [
  { mode: 'orbit', label: 'CHALDEAS', hint: 'Drag to rotate around globe' },
  { mode: 'map', label: 'SHEBA', hint: '2D map view' },
  { mode: 'fly', label: 'Fly', hint: 'WASD to move, Q/E to turn, R/F altitude' },
]

const GLOBE_STYLES: { key: GlobeStyleOption; label: string }[] = [
  { key: 'default', label: 'Blue Marble' },
  { key: 'holo', label: 'Holo' },
  { key: 'night', label: 'Night' },
]

export function CameraModeToggle() {
  const { cameraMode, setCameraMode, flyState } = useGlobeStore()
  const { globeStyle, setGlobeStyle } = useSettingsStore()

  return (
    <div className="camera-mode-wrapper">
      <div className="camera-mode-toggle">
        {MODES.map(({ mode, label, hint }) => (
          <button key={mode} onClick={() => setCameraMode(mode)} title={hint}
            className={`camera-mode-btn ${cameraMode === mode ? 'active' : ''}`}>
            {label}
          </button>
        ))}
      </div>
      {cameraMode === 'fly' && (
        <div className="camera-mode-fly-info">
          <span className="camera-mode-heading">{Math.round(flyState.heading)}&deg;</span>
          <span className="camera-mode-hint">WASD: Move | Q/E: Turn | R/F: Alt</span>
        </div>
      )}
      {cameraMode === 'orbit' && (
        <div className="globe-style-selector">
          {GLOBE_STYLES.map(({ key, label }) => (
            <button key={key} onClick={() => setGlobeStyle(key)}
              className={`globe-style-btn ${globeStyle === key ? 'active' : ''}`}>
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
