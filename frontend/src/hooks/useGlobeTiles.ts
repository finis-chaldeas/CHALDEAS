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
  default: new Color(0.45, 0.48, 0.55),  // dark blue-grey, matches Blue Marble
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

const MAX_CONCURRENT_LOADS = 6
const DEBOUNCE_MS = 80
const RETRY_DELAY_MS = 2000
const FALLBACK_COLOR = 0x1a1e2e

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

  // Track latest camera values
  const latRef = useRef(lat)
  const lngRef = useRef(lng)
  const altitudeRef = useRef(altitude)
  latRef.current = lat
  lngRef.current = lng
  altitudeRef.current = altitude

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

      const cache = cacheRef.current
      const style = globeStyle as TileStyle
      const newZoom = altitudeToTileZoom(altitude)

      if (newZoom === 0) {
        setTilesData([])
        prevZoomRef.current = 0
        pendingBatchRef.current = null
        return
      }

      const visibleTiles = getVisibleTiles(lat, lng, altitude)
      if (visibleTiles.length === 0) {
        setTilesData([])
        return
      }

      // Sort by distance to camera center (closest first)
      visibleTiles.sort((a, b) => {
        const distA = Math.abs(a.lat - lat) + Math.abs(a.lng - lng)
        const distB = Math.abs(b.lat - lat) + Math.abs(b.lng - lng)
        return distA - distB
      })

      const zoomChanged = newZoom !== prevZoomRef.current
      prevZoomRef.current = newZoom

      // Count cached vs uncached
      const toLoad: TileInfo[] = []
      let cachedCount = 0
      for (const tile of visibleTiles) {
        const key = `${tile.z}/${tile.x}/${tile.y}/${style}`
        if (cache.has(key)) {
          cachedCount++
        } else {
          toLoad.push(tile)
        }
      }

      if (toLoad.length === 0) {
        // All cached — show immediately
        const data = buildTilesForZoom(lat, lng, altitude, style)
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
        const data = buildTilesForZoom(lat, lng, altitude, style)
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
  }, [lat, lng, altitude, globeStyle, enabled])

  return { tilesData, isLoading }
}
