import { useState, useRef, useEffect, useCallback } from 'react'
import { MeshBasicMaterial, TextureLoader, SRGBColorSpace, Color } from 'three'
import { TileCache } from '../utils/tileCache'
import {
  getVisibleTiles, tileUrl, altitudeToTileZoom,
  type TileStyle, type TileInfo,
} from '../utils/tilemath'

// Material tint per style — multiplied with texture to match base globe tone
// default: darken + slight blue to match Blue Marble aesthetic
// holo/night: already dark tiles, no adjustment needed
const TILE_TINT: Record<string, Color> = {
  default: new Color(0.52, 0.54, 0.58),  // slightly warm blue-grey, closer to Blue Marble
  holo: new Color(1, 1, 1),
  night: new Color(1, 1, 1),
}

export interface TileData {
  lat: number
  lng: number
  widthDeg: number
  heightDeg: number
  material: MeshBasicMaterial
  key: string
}

const MAX_CONCURRENT_LOADS = 8
const DEBOUNCE_MS = 30
const RETRY_DELAY_MS = 2000
const FALLBACK_COLOR = 0x1a1e2e
// How often (ms) the RAF altitude monitor checks for zoom changes
const ALTITUDE_POLL_MS = 60

function createFallbackMaterial(): MeshBasicMaterial {
  return new MeshBasicMaterial({ color: FALLBACK_COLOR })
}

/**
 * Orchestrator hook for loading slippy map tiles on the 3D globe.
 *
 * Key behavior: when zoom level changes, keeps previous tiles visible
 * until new zoom level's tiles are fully loaded — prevents the
 * "tiles laying down one by one" flicker.
 */
export function useGlobeTiles(
  lat: number,
  lng: number,
  altitude: number,
  globeStyle: string,
  enabled: boolean,
): { tilesData: TileData[]; isLoading: boolean } {
  const [tilesData, setTilesData] = useState<TileData[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const cacheRef = useRef(new TileCache(512))
  const loaderRef = useRef(new TextureLoader())
  const activeLoadsRef = useRef(0)
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const prevStyleRef = useRef(globeStyle)
  const mountedRef = useRef(true)
  const loadQueueRef = useRef<TileInfo[]>([])
  const retrySetRef = useRef(new Set<string>())
  // Track previous zoom to detect zoom changes
  const prevZoomRef = useRef(0)
  // Pending tiles: accumulate new zoom tiles here, swap in when all loaded
  const pendingBatchRef = useRef<{ z: number; total: number; loaded: Set<string> } | null>(null)

  // Track latest camera values (updated both from props AND from RAF monitor)
  const latRef = useRef(lat)
  const lngRef = useRef(lng)
  const altitudeRef = useRef(altitude)
  latRef.current = lat
  lngRef.current = lng
  altitudeRef.current = altitude

  // Incrementing counter to force re-evaluation when RAF detects zoom change
  const [rafTick, setRafTick] = useState(0)

  // Clear cache when style changes
  useEffect(() => {
    if (prevStyleRef.current !== globeStyle) {
      cacheRef.current.clear()
      retrySetRef.current.clear()
      pendingBatchRef.current = null
      prevStyleRef.current = globeStyle
    }
  }, [globeStyle])

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      cacheRef.current.clear()
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [])

  // RAF-based altitude monitor: detects zoom level changes during animations
  // (when cameraPosition state is frozen but globe.pointOfView is animating)
  // Uses a polling approach since three-globe doesn't expose per-frame callbacks
  // for the internal TWEEN animation.
  useEffect(() => {
    if (!enabled) return
    let rafId: number
    let lastCheck = 0
    const lastZoomRef = { current: altitudeToTileZoom(altitude) }

    const poll = (time: number) => {
      if (!mountedRef.current) return
      rafId = requestAnimationFrame(poll)

      // Throttle checks to ALTITUDE_POLL_MS intervals
      if (time - lastCheck < ALTITUDE_POLL_MS) return
      lastCheck = time

      const currentAlt = altitudeRef.current
      const currentZoom = altitudeToTileZoom(currentAlt)
      if (currentZoom !== lastZoomRef.current) {
        lastZoomRef.current = currentZoom
        // Bump tick to force main effect to re-evaluate
        setRafTick(prev => prev + 1)
      }
    }

    rafId = requestAnimationFrame(poll)
    return () => cancelAnimationFrame(rafId)
  }, [enabled, altitude])

  /** Build TileData[] from cache for current viewport at a specific zoom */
  const buildTilesForZoom = useCallback((camLat: number, camLng: number, camAlt: number, style: TileStyle): TileData[] => {
    const cache = cacheRef.current
    const visibleTiles = getVisibleTiles(camLat, camLng, camAlt)
    const data: TileData[] = []
    for (const tile of visibleTiles) {
      const key = `${tile.z}/${tile.x}/${tile.y}/${style}`
      const material = cache.get(key)
      if (material) {
        data.push({
          lat: tile.lat, lng: tile.lng,
          widthDeg: tile.widthDeg, heightDeg: tile.heightDeg,
          material, key,
        })
      }
    }
    return data
  }, [])

  /** Flush pending batch: swap tiles to new zoom level's data */
  const flushPendingBatch = useCallback(() => {
    if (!mountedRef.current) return
    const style = prevStyleRef.current as TileStyle
    const data = buildTilesForZoom(latRef.current, lngRef.current, altitudeRef.current, style)
    setTilesData(data)
    pendingBatchRef.current = null
  }, [buildTilesForZoom])

  const processQueue = useCallback(() => {
    if (!mountedRef.current) return

    const queue = loadQueueRef.current
    const cache = cacheRef.current
    const style = prevStyleRef.current as TileStyle
    const batch = pendingBatchRef.current

    while (queue.length > 0 && activeLoadsRef.current < MAX_CONCURRENT_LOADS) {
      const tile = queue.shift()
      if (!tile) break

      const key = `${tile.z}/${tile.x}/${tile.y}/${style}`
      if (cache.has(key)) {
        // Already loaded — mark in batch
        if (batch && tile.z === batch.z) {
          batch.loaded.add(key)
          if (batch.loaded.size >= batch.total) {
            flushPendingBatch()
          }
        }
        continue
      }

      activeLoadsRef.current++
      const url = tileUrl(tile.x, tile.y, tile.z, style)

      loaderRef.current.load(
        url,
        (texture) => {
          if (!mountedRef.current) {
            texture.dispose()
            activeLoadsRef.current--
            return
          }
          texture.colorSpace = SRGBColorSpace
          const tint = TILE_TINT[prevStyleRef.current] || TILE_TINT.default
          const material = new MeshBasicMaterial({ map: texture, color: tint })
          cache.set(key, material)
          activeLoadsRef.current--

          const currentBatch = pendingBatchRef.current
          if (currentBatch && tile.z === currentBatch.z) {
            currentBatch.loaded.add(key)
            if (currentBatch.loaded.size >= currentBatch.total) {
              // All tiles for new zoom loaded — swap in atomically
              flushPendingBatch()
            }
          } else {
            // Same-zoom panning: update incrementally
            const data = buildTilesForZoom(latRef.current, lngRef.current, altitudeRef.current, style)
            setTilesData(data)
          }
          processQueue()
        },
        undefined,
        () => {
          activeLoadsRef.current--
          if (!mountedRef.current) return

          if (!retrySetRef.current.has(key)) {
            const fallback = createFallbackMaterial()
            cache.set(key, fallback)
            retrySetRef.current.add(key)
            setTimeout(() => {
              if (mountedRef.current) retrySetRef.current.delete(key)
            }, RETRY_DELAY_MS)
          }

          // Count failed tile as "loaded" for batch purposes
          const currentBatch = pendingBatchRef.current
          if (currentBatch && tile.z === currentBatch.z) {
            currentBatch.loaded.add(key)
            if (currentBatch.loaded.size >= currentBatch.total) {
              flushPendingBatch()
            }
          } else {
            const data = buildTilesForZoom(latRef.current, lngRef.current, altitudeRef.current, style)
            setTilesData(data)
          }
          processQueue()
        },
      )
    }

    if (queue.length === 0 && activeLoadsRef.current === 0) {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [buildTilesForZoom, flushPendingBatch])

  // Main effect: debounce camera changes and compute visible tiles
  // Uses altitudeRef.current for real-time altitude (tracks animations via RAF monitor)
  // rafTick forces re-evaluation when RAF detects zoom level change during animation
  useEffect(() => {
    if (!enabled) {
      if (tilesData.length > 0) setTilesData([])
      prevZoomRef.current = 0
      pendingBatchRef.current = null
      return
    }

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    debounceTimerRef.current = setTimeout(() => {
      if (!mountedRef.current) return

      // Read real-time values from refs (tracks animations)
      const camLat = latRef.current
      const camLng = lngRef.current
      const camAlt = altitudeRef.current

      const cache = cacheRef.current
      const style = globeStyle as TileStyle
      const newZoom = altitudeToTileZoom(camAlt)

      if (newZoom === 0) {
        setTilesData([])
        prevZoomRef.current = 0
        pendingBatchRef.current = null
        return
      }

      const visibleTiles = getVisibleTiles(camLat, camLng, camAlt)
      if (visibleTiles.length === 0) {
        setTilesData([])
        return
      }

      // Sort by distance to camera center (closest first)
      visibleTiles.sort((a, b) => {
        const distA = Math.abs(a.lat - camLat) + Math.abs(a.lng - camLng)
        const distB = Math.abs(b.lat - camLat) + Math.abs(b.lng - camLng)
        return distA - distB
      })

      const zoomChanged = newZoom !== prevZoomRef.current
      prevZoomRef.current = newZoom

      // Find uncached tiles that need loading
      const toLoad: TileInfo[] = []
      for (const tile of visibleTiles) {
        const key = `${tile.z}/${tile.x}/${tile.y}/${style}`
        if (!cache.has(key)) {
          toLoad.push(tile)
        }
      }

      if (toLoad.length === 0) {
        // All cached — show immediately
        const data = buildTilesForZoom(camLat, camLng, camAlt, style)
        setTilesData(data)
        pendingBatchRef.current = null
        return
      }

      if (zoomChanged) {
        // Zoom changed: keep old tiles visible, batch-load new zoom
        // DON'T clear tilesData — old tiles stay on screen
        pendingBatchRef.current = {
          z: newZoom,
          total: visibleTiles.length,
          loaded: new Set(
            visibleTiles
              .filter(t => cache.has(`${t.z}/${t.x}/${t.y}/${style}`))
              .map(t => `${t.z}/${t.x}/${t.y}/${style}`)
          ),
        }
      } else {
        // Same zoom, panning: show cached immediately, load missing incrementally
        const data = buildTilesForZoom(camLat, camLng, camAlt, style)
        setTilesData(data)
        pendingBatchRef.current = null
      }

      // Queue uncached tiles for loading
      setIsLoading(true)
      loadQueueRef.current = toLoad
      processQueue()
    }, DEBOUNCE_MS)

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lat, lng, altitude, globeStyle, enabled, rafTick])

  return { tilesData, isLoading }
}
