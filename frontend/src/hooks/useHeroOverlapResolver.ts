import { useEffect, useRef } from 'react'

interface Vec2 {
  x: number
  y: number
}

interface Rect {
  left: number
  right: number
  top: number
  bottom: number
}

interface CardInfo {
  el: HTMLElement
  id: string
  importance: number
  baseRect: Rect // screen rect with current transform subtracted out
}

function center(r: Rect): Vec2 {
  return { x: (r.left + r.right) / 2, y: (r.top + r.bottom) / 2 }
}

function shiftRect(r: Rect, ox: number, oy: number): Rect {
  return {
    left: r.left + ox,
    right: r.right + ox,
    top: r.top + oy,
    bottom: r.bottom + oy,
  }
}

function rectsOverlap(a: Rect, b: Rect): boolean {
  return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top
}

function showConnector(cardEl: HTMLElement, offsetX: number, offsetY: number) {
  const wrapper = cardEl.parentElement
  if (!wrapper) return

  let pin = wrapper.querySelector('.hero-pin') as HTMLElement
  if (!pin) {
    pin = document.createElement('div')
    pin.className = 'hero-pin'
    wrapper.insertBefore(pin, wrapper.firstChild)
  }
  pin.style.display = ''

  let stem = wrapper.querySelector('.hero-stem') as HTMLElement
  if (!stem) {
    stem = document.createElement('div')
    stem.className = 'hero-stem'
    wrapper.insertBefore(stem, wrapper.firstChild)
  }
  const length = Math.sqrt(offsetX ** 2 + offsetY ** 2)
  const angle = Math.atan2(offsetY, offsetX)
  stem.style.width = `${length}px`
  stem.style.transform = `rotate(${angle}rad)`
  stem.style.display = ''
}

function hideConnector(cardEl: HTMLElement) {
  const wrapper = cardEl.parentElement
  if (!wrapper) return
  const pin = wrapper.querySelector('.hero-pin') as HTMLElement
  const stem = wrapper.querySelector('.hero-stem') as HTMLElement
  if (pin) pin.style.display = 'none'
  if (stem) stem.style.display = 'none'
}

/**
 * RAF-based screen-coordinate overlap resolver for hero cards.
 *
 * Key insight: getBoundingClientRect() returns positions AFTER our transform.
 * We subtract the current applied offset to recover the "base" position,
 * then compute new displacements from that stable base. This prevents
 * the oscillation that occurs when reading already-displaced positions.
 */
export function useHeroOverlapResolver(enabled: boolean) {
  // Current applied offset per card (used for lerp + base rect recovery)
  const offsetsRef = useRef<Map<string, Vec2>>(new Map())

  useEffect(() => {
    if (!enabled) return
    let rafId: number

    const resolve = () => {
      const container = document.querySelector('.globe-container')
      if (!container) {
        rafId = requestAnimationFrame(resolve)
        return
      }

      // 1. Collect all hero cards, recover base rects (subtract current offset)
      // Cap at 30 cards to prevent O(n²) blowup on mobile
      const MAX_RESOLVE_CARDS = 30
      const allElements = container.querySelectorAll('[data-hero-id]')
      const cards: CardInfo[] = Array.from(allElements)
        .map((el) => {
          const htmlEl = el as HTMLElement
          const id = el.getAttribute('data-hero-id') || ''
          const importance = parseInt(el.getAttribute('data-importance') || '0', 10)
          const screenRect = htmlEl.getBoundingClientRect()
          if (screenRect.width === 0) return null

          // Subtract current applied offset to get stable base position
          const cur = offsetsRef.current.get(id) || { x: 0, y: 0 }
          const baseRect: Rect = {
            left: screenRect.left - cur.x,
            right: screenRect.right - cur.x,
            top: screenRect.top - cur.y,
            bottom: screenRect.bottom - cur.y,
          }

          return { el: htmlEl, id, importance, baseRect }
        })
        .filter((c): c is CardInfo => c !== null)
        .sort((a, b) => b.importance - a.importance)
        .slice(0, MAX_RESOLVE_CARDS)

      if (cards.length === 0) {
        rafId = requestAnimationFrame(resolve)
        return
      }

      // 2. Force displacement from BASE rects (3 iterations)
      const targets = new Map<string, Vec2>()
      cards.forEach((c) => targets.set(c.id, { x: 0, y: 0 }))

      for (let iter = 0; iter < 3; iter++) {
        for (let i = 0; i < cards.length; i++) {
          for (let j = i + 1; j < cards.length; j++) {
            const a = cards[i]
            const b = cards[j]
            const ta = targets.get(a.id)!
            const tb = targets.get(b.id)!

            // Apply tentative offsets to base rects
            const aRect = shiftRect(a.baseRect, ta.x, ta.y)
            const bRect = shiftRect(b.baseRect, tb.x, tb.y)

            if (!rectsOverlap(aRect, bRect)) continue

            // Push the lower-importance card (b) away from higher (a)
            const ac = center(aRect)
            const bc = center(bRect)
            let dx = bc.x - ac.x
            let dy = bc.y - ac.y
            if (dx === 0 && dy === 0) {
              dx = 1
              dy = 1
            }
            const dist = Math.sqrt(dx * dx + dy * dy)

            const overlapX =
              Math.min(aRect.right, bRect.right) - Math.max(aRect.left, bRect.left)
            const overlapY =
              Math.min(aRect.bottom, bRect.bottom) - Math.max(aRect.top, bRect.top)
            const push = Math.max(overlapX, overlapY) + 8

            tb.x += (dx / dist) * push
            tb.y += (dy / dist) * push
          }
        }
      }

      // 3. Apply results with lerp (smooth convergence, no oscillation)
      for (const card of cards) {
        const target = targets.get(card.id)!
        const totalDist = Math.sqrt(target.x ** 2 + target.y ** 2)

        // Over 150px → occlude
        if (totalDist > 150) {
          card.el.classList.add('hero-card--occluded')
          hideConnector(card.el)
          // Keep tracking offset so base rect stays correct
          const cur = offsetsRef.current.get(card.id) || { x: 0, y: 0 }
          cur.x += (0 - cur.x) * 0.15 // lerp back to 0
          cur.y += (0 - cur.y) * 0.15
          offsetsRef.current.set(card.id, cur)
          card.el.style.transform = Math.abs(cur.x) > 0.5 || Math.abs(cur.y) > 0.5
            ? `translate(${cur.x}px, ${cur.y}px)`
            : ''
          continue
        }
        card.el.classList.remove('hero-card--occluded')

        // Lerp current → target at 15% per frame
        const cur = offsetsRef.current.get(card.id) || { x: 0, y: 0 }
        cur.x += (target.x - cur.x) * 0.15
        cur.y += (target.y - cur.y) * 0.15
        offsetsRef.current.set(card.id, cur)

        if (Math.abs(cur.x) > 1 || Math.abs(cur.y) > 1) {
          card.el.style.transform = `translate(${cur.x}px, ${cur.y}px)`
          showConnector(card.el, cur.x, cur.y)
        } else {
          // Snap to zero to avoid sub-pixel jitter
          cur.x = 0
          cur.y = 0
          card.el.style.transform = ''
          hideConnector(card.el)
        }
      }

      rafId = requestAnimationFrame(resolve)
    }

    rafId = requestAnimationFrame(resolve)
    return () => {
      cancelAnimationFrame(rafId)
      // Clean up all transforms
      const container = document.querySelector('.globe-container')
      if (container) {
        container.querySelectorAll('[data-hero-id]').forEach((el) => {
          ;(el as HTMLElement).style.transform = ''
          el.classList.remove('hero-card--occluded')
        })
      }
      offsetsRef.current.clear()
    }
  }, [enabled])
}
