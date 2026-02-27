# Globe Marker Enhancement

**Date**: 2026-02-26
**Branch**: frontend-v4-recovered

## Purpose
Enhance the globe marker system with 3 features:
1. **Stacked Hero Fan-out** — Same-location heroes show as stacked cards instead of being dropped
2. **City Pin** — Replace floating city labels with pin structure (head + stem + label)
3. **3-Tier Pin Marker** — Mid-importance events (diamond) and persons (circle) as pin markers

## Changes

### Backend (`backend/app/api/v1_new/globe.py`)
- Added `StackedEvent` model
- Added `stacked: List[StackedEvent]` to `HeroMarker`
- Simplified `_select_heroes()` from 2-pass (ANCHOR_DISTANCE) to single-pass algorithm
- Returns `(heroes, dropped_map)` tuple; dropped candidates attributed to nearest hero
- `hero_exclude` uses ALL dropped IDs (not just stacked top-5) to prevent cluster leaks
- Added `PinMarker` model (event diamond / person circle)
- Added `PIN_CONFIG` per zoom level
- Added `pins: List[PinMarker]` to `SmartMarkersResponse`
- Added event pin query (importance >= threshold, hero excluded)
- Added person pin query (birthplace coords, alive in range, global_score)
- Updated `ZOOM_CONFIG` for wider spacing: cosmic=15, continental=5, regional=2, local=0.8

### Frontend Types (`frontend/src/types/index.ts`)
- Added `StackedEvent` interface
- Added `stacked: StackedEvent[]` to `HeroMarker`
- Added `PinMarker` interface
- Added `pins: PinMarker[]` to `SmartMarkersResponse`

### Frontend Globe (`frontend/src/components/globe/GlobeContainer.tsx`)
- Hero rendering: stacked heroes show peek cards + gold `+N` badge
- **Click-toggle fan**: badge click toggles `.hero-stack--open` class (not hover)
- Fan card click → event detail (via `eventsApi.get(id)`)
- Added `pin` kind in normalHtmlElements from smartMarkers.pins
- Added `pin` branch in htmlElementFn with diamond/circle shape
- Pin click: event → EventDetail, person → PersonDetail
- Node rendering: replaced inline styles with structured city-pin HTML
- Added `onPersonClickRef` for stable callback reference

### CSS (`frontend/src/styles/globals.css`)
- `.hero-stack` — relative container with peek cards behind
- `.hero-stack-peek--1/--2` — translateY offset, decreasing opacity
- `.hero-stack-badge` — clickable gold `+N` badge (replaced `::after` pseudo-element)
- `.hero-stack-fan` — absolute above card, click-toggle via `.hero-stack--open`
- `.hero-stack--open .hero-stack-fan` — opacity 1, pointer-events auto, z-index 100
- `.hero-stack--open .hero-stack-badge` — cyan highlight when fan is open
- `.hero-stack-card` — mini card with fanCardIn animation
- `.pin-marker` — flex row, diamond (rotate 45deg cyan) / circle (gold round)
- `.pin-marker--legendary/--mythological` — purple/pink shapes
- `.city-pin` — flex column with head + stem + label
- `.city-pin--tier2` — smaller, label always visible
- `.city-pin--inactive` — dim colors
- `.city-pin-pulse` — @keyframes animation for active pins
- All marker types fade on `.globe-container.shifted`

## Iteration History

### Round 1: Initial implementation
- All 3 features implemented (backend + frontend + CSS)

### Round 2: City pin tier2 label + cluster leak fix
- City pin tier2: labels always visible (removed hover-only opacity)
- `hero_exclude` expanded to ALL dropped IDs

### Round 3: Single-pass hero selection
- Removed 2-pass ANCHOR_DISTANCE algorithm (too aggressive — only 1 anchor for all Greece)
- Simplified to single-pass with zoom-level min_distance
- Reduced ZOOM_CONFIG min_distances

### Round 4: Port fix + __pycache__ clearing
- Frontend `.env` points to 8101, started backend on 8101
- Cleared `__pycache__` to fix stale bytecode issue

### Round 5: Click-toggle fan + badge redesign + spacing
- Badge: `::after` pseudo → explicit `<span class="hero-stack-badge">+N</span>`
- Fan: hover-based → click-toggle with `.hero-stack--open` class
- Fan shows ALL stacked events (removed 3-card limit + overflow)
- Increased min_distances to reduce overlap (continental 5, cosmic 15)
- Decreased max_heroes (cosmic 10, continental 15)

## Verification
- `npx tsc --noEmit` → no new errors
- API test: 10 heroes (5 with stacks), 27 hero+stacked IDs, 0 leaks into clusters
- 15 pins returned (person circles: Cyrus, Thales, Euripides, etc.)
- Backend running on 8101 with `--reload`

## Next Steps
- Visual QA on globe at different zoom levels
- Mobile layout testing
- Test fan-out click interaction in browser
