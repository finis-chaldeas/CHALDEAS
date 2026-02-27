import { useEffect, useCallback, useRef } from 'react'
import { useGlobeStore } from '../store/globeStore'
import type { GlobeMethods } from 'react-globe.gl'

interface UseFlyModeOptions {
  globeRef: React.RefObject<GlobeMethods | undefined>
  enabled: boolean
}

// Convert degrees to radians
const toRad = (deg: number) => (deg * Math.PI) / 180

// WASD keys only (no arrow keys — those are used by ShiftPanel nav)
const WASD_KEYS = new Set(['w', 'a', 's', 'd', 'q', 'e',
                            'W', 'A', 'S', 'D', 'Q', 'E'])

/**
 * WASD navigation for the globe (integrated into orbit mode)
 * WASD: Move forward/backward/left/right
 * Q/E: Turn left/right (yaw)
 * Shift: Speed boost
 */
export function useFlyMode({ globeRef, enabled }: UseFlyModeOptions) {
  const { cameraPosition, setCameraPosition, flyState, updateFlyState } = useGlobeStore()
  const keysPressed = useRef<Set<string>>(new Set())
  const animationFrame = useRef<number | null>(null)

  const BASE_SPEED = 0.5
  const TURN_SPEED = 2

  const updatePosition = useCallback(() => {
    if (!enabled || !globeRef.current) return

    const keys = keysPressed.current
    if (keys.size === 0) {
      animationFrame.current = requestAnimationFrame(updatePosition)
      return
    }

    const speedMultiplier = keys.has('Shift') ? 2.5 : 1.0
    const moveSpeed = BASE_SPEED * speedMultiplier * flyState.speed

    let { lat, lng, altitude } = cameraPosition
    let { heading } = flyState

    // Turn left/right (Q/E)
    if (keys.has('q') || keys.has('Q')) {
      heading = (heading - TURN_SPEED * speedMultiplier + 360) % 360
      updateFlyState({ heading })
    }
    if (keys.has('e') || keys.has('E')) {
      heading = (heading + TURN_SPEED * speedMultiplier) % 360
      updateFlyState({ heading })
    }

    // Forward/backward (W/S)
    const moveForward = keys.has('w') || keys.has('W')
    const moveBackward = keys.has('s') || keys.has('S')

    if (moveForward || moveBackward) {
      const direction = moveForward ? 1 : -1
      const headingRad = toRad(heading)
      lat += direction * moveSpeed * Math.cos(headingRad)
      lng += direction * moveSpeed * Math.sin(headingRad) / Math.cos(toRad(lat))
      lat = Math.max(-85, Math.min(85, lat))
      lng = ((lng + 180) % 360 + 360) % 360 - 180
    }

    // Strafe left/right (A/D)
    const strafeLeft = keys.has('a') || keys.has('A')
    const strafeRight = keys.has('d') || keys.has('D')

    if (strafeLeft || strafeRight) {
      const direction = strafeRight ? 1 : -1
      const strafeHeading = toRad(heading + 90)
      lat += direction * moveSpeed * 0.7 * Math.cos(strafeHeading)
      lng += direction * moveSpeed * 0.7 * Math.sin(strafeHeading) / Math.cos(toRad(lat))
      lat = Math.max(-85, Math.min(85, lat))
      lng = ((lng + 180) % 360 + 360) % 360 - 180
    }

    setCameraPosition({ lat, lng, altitude })
    globeRef.current.pointOfView({ lat, lng, altitude }, 50)

    animationFrame.current = requestAnimationFrame(updatePosition)
  }, [enabled, cameraPosition, flyState, setCameraPosition, updateFlyState, globeRef])

  useEffect(() => {
    if (!enabled) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (!WASD_KEYS.has(e.key) && e.key !== 'Shift') return

      keysPressed.current.add(e.key)
      e.preventDefault()
    }

    const handleKeyUp = (e: KeyboardEvent) => {
      keysPressed.current.delete(e.key)
    }

    const handleBlur = () => {
      keysPressed.current.clear()
    }

    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)
    window.addEventListener('blur', handleBlur)

    animationFrame.current = requestAnimationFrame(updatePosition)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
      window.removeEventListener('blur', handleBlur)
      if (animationFrame.current) cancelAnimationFrame(animationFrame.current)
    }
  }, [enabled, updatePosition])

  return {
    heading: flyState.heading,
    speed: flyState.speed,
    setSpeed: (speed: number) => updateFlyState({ speed }),
  }
}
