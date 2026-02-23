import { useGlobeStore, type CameraMode } from '../../store/globeStore'

const MODES: { mode: CameraMode; label: string; hint: string }[] = [
  { mode: 'orbit', label: 'CHALDEAS', hint: 'Drag to rotate around globe' },
  { mode: 'map', label: 'SHEBA', hint: '2D map view' },
  { mode: 'fly', label: 'Fly', hint: 'WASD to move, Q/E to turn, R/F altitude' },
]

export function CameraModeToggle({ className = '' }: { className?: string }) {
  const { cameraMode, setCameraMode, flyState } = useGlobeStore()

  return (
    <div className={className}>
      <div className="flex bg-chaldea-panel/80 backdrop-blur-xl border border-chaldea-border/30 rounded-lg overflow-hidden">
        {MODES.map(({ mode, label, hint }) => (
          <button key={mode} onClick={() => setCameraMode(mode)} title={hint}
            className={`px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide
                        border-r border-white/5 last:border-r-0 transition-colors
                        ${cameraMode === mode
                          ? 'bg-chaldea-cyan/15 text-chaldea-cyan'
                          : 'text-chaldea-text/50 hover:text-chaldea-cyan/70 hover:bg-white/5'}`}>
            {label}
          </button>
        ))}
      </div>
      {cameraMode === 'fly' && (
        <div className="mt-1 bg-chaldea-panel/80 backdrop-blur-xl border border-chaldea-border/30
                        rounded-lg px-2.5 py-1.5 text-[10px] text-chaldea-text/60">
          <span className="text-chaldea-gold font-mono font-semibold">{Math.round(flyState.heading)}&deg;</span>
          <span className="ml-2 text-[9px] text-chaldea-text/30">WASD: Move | Q/E: Turn | R/F: Alt</span>
        </div>
      )}
    </div>
  )
}
