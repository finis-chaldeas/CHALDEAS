/**
 * Tile coordinate math for Web Mercator (slippy map) tiles.
 * Pure functions, no side effects.
 */

export type TileStyle = 'default' | 'holo' | 'night'

export interface TileCoord {
  x: number
  y: number
  z: number
}

export interface TileInfo extends TileCoord {
  lat: number
  lng: number
  widthDeg: number
  heightDeg: number
}

const MERCATOR_MAX_LAT = 85.0511287798

/** Convert latitude/longitude to tile x,y at zoom level z */
export function latLngToTileXY(lat: number, lng: number, z: number): { x: number; y: number } {
  const clampedLat = Math.max(-MERCATOR_MAX_LAT, Math.min(MERCATOR_MAX_LAT, lat))
  const n = 1 << z
  const x = Math.floor(((lng + 180) / 360) * n)
  const latRad = (clampedLat * Math.PI) / 180
  const y = Math.floor(((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n)
  return {
    x: ((x % n) + n) % n, // wrap around anti-meridian
    y: Math.max(0, Math.min(n - 1, y)),
  }
}

/** Convert tile x,y,z to the north-west corner lat/lng */
export function tileXYToLatLng(x: number, y: number, z: number): { lat: number; lng: number } {
  const n = 1 << z
  const lng = (x / n) * 360 - 180
  const latRad = Math.atan(Math.sinh(Math.PI * (1 - (2 * y) / n)))
  const lat = (latRad * 180) / Math.PI
  return { lat, lng }
}

/** Get the center lat/lng of a tile */
export function tileCenter(x: number, y: number, z: number): { lat: number; lng: number } {
  const nw = tileXYToLatLng(x, y, z)
  const se = tileXYToLatLng(x + 1, y + 1, z)
  return {
    lat: (nw.lat + se.lat) / 2,
    lng: (nw.lng + se.lng) / 2,
  }
}

/** Get tile dimensions in degrees (height varies by latitude due to Mercator) */
export function tileDimensions(x: number, y: number, z: number): { widthDeg: number; heightDeg: number } {
  const nw = tileXYToLatLng(x, y, z)
  const se = tileXYToLatLng(x + 1, y + 1, z)
  return {
    widthDeg: se.lng - nw.lng,
    heightDeg: nw.lat - se.lat, // NW lat > SE lat
  }
}

/** Map globe altitude to appropriate tile zoom level. Returns 0 if tiles shouldn't be shown. */
export function altitudeToTileZoom(altitude: number): number {
  if (altitude > 1.0) return 0
  if (altitude > 0.6) return 3
  if (altitude > 0.35) return 4
  if (altitude > 0.2) return 5
  if (altitude > 0.1) return 6
  if (altitude > 0.05) return 7
  if (altitude > 0.025) return 8
  if (altitude > 0.012) return 9
  if (altitude > 0.006) return 10
  return 11 // ~2.5km/pixel at max zoom
}

/** Get all visible tiles for a camera position */
export function getVisibleTiles(lat: number, lng: number, altitude: number): TileInfo[] {
  const z = altitudeToTileZoom(altitude)
  if (z === 0) return []

  // Estimate viewport span in degrees
  const latSpan = altitude * 35
  const lngSpan = altitude * 45

  const north = Math.min(MERCATOR_MAX_LAT, lat + latSpan)
  const south = Math.max(-MERCATOR_MAX_LAT, lat - latSpan)
  const west = lng - lngSpan
  const east = lng + lngSpan

  const nwTile = latLngToTileXY(north, west, z)
  const seTile = latLngToTileXY(south, east, z)

  const n = 1 << z
  // Add 1-tile margin for smooth panning
  const minY = Math.max(0, nwTile.y - 1)
  const maxY = Math.min(n - 1, seTile.y + 1)
  const minX = nwTile.x - 1
  const maxX = seTile.x + 1

  const tiles: TileInfo[] = []

  for (let ty = minY; ty <= maxY; ty++) {
    for (let tx = minX; tx <= maxX; tx++) {
      const wrappedX = ((tx % n) + n) % n
      const center = tileCenter(wrappedX, ty, z)
      const dims = tileDimensions(wrappedX, ty, z)
      tiles.push({
        x: wrappedX,
        y: ty,
        z,
        lat: center.lat,
        lng: center.lng,
        widthDeg: dims.widthDeg,
        heightDeg: dims.heightDeg,
      })
    }
  }

  return tiles
}

const SUBDOMAINS = ['a', 'b', 'c', 'd']

/** Generate tile image URL for a given style */
export function tileUrl(x: number, y: number, z: number, style: TileStyle): string {
  const s = SUBDOMAINS[(x + y) % 4]

  switch (style) {
    case 'default':
      return `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${z}/${y}/${x}`
    case 'holo':
      return `https://${s}.basemaps.cartocdn.com/dark_all/${z}/${x}/${y}@2x.png`
    case 'night':
      return `https://${s}.basemaps.cartocdn.com/dark_nolabels/${z}/${x}/${y}@2x.png`
    default:
      return `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${z}/${y}/${x}`
  }
}
