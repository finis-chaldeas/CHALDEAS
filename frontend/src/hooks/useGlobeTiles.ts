import { useState, useRef, useEffect, useCallback } from 'react'
import { MeshBasicMaterial, TextureLoader, SRGBColorSpace, Color } from 'three'
import { TileCache } from '../utils/tileCache'
import {
  getVisibleTiles, getAllTilesAtZoom, tileUrl, altitudeToTileZoom,
  type TileStyle, type TileInfo,
} from '../utils/tilemath'

// Material tint per style — multiplied with texture to match base globe tone
// default: darken + slight blue to match Blue Marble aesthetic
// holo/night: already dark tiles, no adjustment needed
const TILE_TINT: Record<string, Color> = {
  default: new Color(0.44, 0.48, 1.00),  // blue tint to match Blue Marble base texture
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
  altitude: number
}

const MAX_CONCURRENT_LOADS = 16
const PRELOAD_CONCURRENT = 8
const DEBOUNCE_MS = 10
const RETRY_DELAY_MS = 2000
const FALLBACK_COLOR = 0x1a1e2e
const ALTITUDE_POLL_MS = 30
const PRELOAD_ZOOM = 4
const BASE_TILE_ALT = 0.00001   // z=4 permanent base layer (on globe surface)
const OVERLAY_TILE_ALT = 0.001   // higher zoom overlay well above base to prevent z-fighting

// Memoized z=4 tile list (256 tiles, computed once)
let _z4TilesCache: TileInfo[] | null = null
function getZ4Tiles(): TileInfo[] {
  if (!_z4TilesCache) _z4TilesCache = getAllTilesAtZoom(PRELOAD_ZOOM)
  return _z4TilesCache
}

function createFallbackMaterial(): MeshBasicMaterial {
  return new MeshBasicMaterial({ color: FALLBACK_COLOR })
}

/**
 * Preload all tiles at PRELOAD_ZOOM (z=4, 256 tiles, ~9MB).
 * Fires once per style, loads in background with limited concurrency.
 */
const preloadedStyles = new Set<string>()
function preloadZ4(cache: TileCache, loader: TextureLoader, style: TileStyle): void {
  if (preloadedStyles.has(style)) return
  preloadedStyles.add(style)

  const allTiles = getAllTilesAtZoom(PRELOAD_ZOOM)
  const tint = TILE_TINT[style] || TILE_TINT.default
  let idx = 0
  let active = 0

  function next() {
    while (idx < allTiles.length && active < PRELOAD_CONCURRENT) {
      const tile = allTiles[idx++]
      const key = `${tile.z}/${tile.x}/${tile.y}/${style}`
      if (cache.has(key)) continue

      active++
      const url = tileUrl(tile.x, tile.y, tile.z, style)
      loader.load(
        url,
        (texture) => {
          texture.colorSpace = SRGBColorSpace
          const material = new MeshBasicMaterial({ map: texture, color: tint })
          cache.set(key, material)
          active--
          next()
        },
        undefined,
        () => { active--; next() },
      )
    }
  }
  next()
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

  const cacheRef = useRef(new TileCache(2048))
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

  // Preload z=4 tiles on first enable (and when style changes)
  useEffect(() => {
    if (enabled) {
      preloadZ4(cacheRef.current, loaderRef.current, globeStyle as TileStyle)
    }
  }, [enabled, globeStyle])

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
    const lastZoomRef = { current: altitudeToTileZoom(altitudeRef.current) }

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
  // altitude is tracked via altitudeRef — no need in deps
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled])

  /** Build TileData[] — z=4 permanent base + higher-res overlay */
  const buildTilesForZoom = useCallback((camLat: number, camLng: number, camAlt: number, style: TileStyle): TileData[] => {
    const cache = cacheRef.current
    const z = altitudeToTileZoom(camAlt)
    const data: TileData[] = []

    // z=4 permanent base layer — ALL 256 preloaded tiles, always visible at ANY altitude
    for (const tile of getZ4Tiles()) {
      const key = `4/${tile.x}/${tile.y}/${style}`
      const material = cache.get(key)
      if (material) {
        data.push({
          lat: tile.lat, lng: tile.lng,
          widthDeg: tile.widthDeg, heightDeg: tile.heightDeg,
          material, key: `base-${key}`,
          altitude: BASE_TILE_ALT,
        })
      }
    }

    // Higher-res overlay (z > 4 only)
    if (z > 4) {
      const visibleTiles = getVisibleTiles(camLat, camLng, camAlt)
      for (const tile of visibleTiles) {
        const key = `${tile.z}/${tile.x}/${tile.y}/${style}`
        const material = cache.get(key)
        if (material) {
          data.push({
            lat: tile.lat, lng: tile.lng,
            widthDeg: tile.widthDeg, heightDeg: tile.heightDeg,
            material, key,
            altitude: OVERLAY_TILE_ALT,
          })
        }
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
        // Cosmic view — still show z=4 base layer
        const data = buildTilesForZoom(camLat, camLng, camAlt, style)
        setTilesData(data)
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
        // Cancel any in-flight queue from previous zoom change
        loadQueueRef.current = []
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
