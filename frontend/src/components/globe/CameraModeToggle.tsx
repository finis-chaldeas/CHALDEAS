import { useSettingsStore, type GlobeStyleOption } from '../../store/settingsStore'

const GLOBE_STYLES: { key: GlobeStyleOption; label: string }[] = [
  { key: 'default', label: 'Blue Marble' },
  { key: 'holo', label: 'Holo' },
  { key: 'night', label: 'Night' },
]

export function CameraModeToggle() {
  const { globeStyle, setGlobeStyle } = useSettingsStore()

  return (
    <div className="camera-mode-wrapper">
      <div className="globe-style-selector">
        {GLOBE_STYLES.map(({ key, label }) => (
          <button key={key} onClick={() => setGlobeStyle(key)}
            className={`globe-style-btn ${globeStyle === key ? 'active' : ''}`}>
            {label}
          </button>
        ))}
      </div>
    </div>
  )
}
