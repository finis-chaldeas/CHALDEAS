import { MeshBasicMaterial } from 'three'

/**
 * LRU cache for tile materials with proper GPU memory disposal.
 * Cache key format: "{z}/{x}/{y}/{style}"
 */
export class TileCache {
  private cache = new Map<string, MeshBasicMaterial>()
  private maxSize: number

  constructor(maxSize = 1024) {
    this.maxSize = maxSize
  }

  get(key: string): MeshBasicMaterial | undefined {
    const material = this.cache.get(key)
    if (!material) return undefined

    // Move to end (most recently used)
    this.cache.delete(key)
    this.cache.set(key, material)
    return material
  }

  set(key: string, material: MeshBasicMaterial): void {
    // If already exists, delete first (will be re-added at end)
    if (this.cache.has(key)) {
      this.cache.delete(key)
    }

    // Evict oldest if at capacity
    while (this.cache.size >= this.maxSize) {
      const oldestKey = this.cache.keys().next().value
      if (oldestKey !== undefined) {
        this.evict(oldestKey)
      }
    }

    this.cache.set(key, material)
  }

  has(key: string): boolean {
    return this.cache.has(key)
  }

  clear(): void {
    for (const [key] of this.cache) {
      this.evict(key)
    }
  }

  get size(): number {
    return this.cache.size
  }

  private evict(key: string): void {
    const material = this.cache.get(key)
    if (material) {
      try {
        if (material.map) {
          material.map.dispose()
          material.map = null
        }
        material.dispose()
      } catch {
        // GPU disposal can fail silently if context is lost — ignore
      }
      this.cache.delete(key)
    }
  }
}
