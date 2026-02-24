# Session Log: 2026-02-24 Smart Markers Implementation

## Session Info
- **Purpose**: Implement 3-Layer Smart Marker System (Hero Cards + Cluster Bubbles + Location Nodes)
- **Branch**: frontend-v4-recovered

## Summary
Implemented zoom-level-aware event display system inspired by Google Maps landmark cards.

## Changes Made

### Phase 1: Backend API
- **`backend/app/api/v1_new/globe.py`**: Added `GET /globe/smart-markers` endpoint
  - `HeroMarker`, `ClusterBubble`, `SmartMarkersResponse` Pydantic models
  - Hero selection algorithm with importance-based filtering + overlap prevention (`_select_heroes`, `_haversine_approx`)
  - Grid-based cluster generation excluding hero events
  - Zoom-level configuration (cosmic/continental/regional/local) controlling min_importance, max_heroes, grid_size, min_distance

### Phase 2: Frontend Types + API
- **`frontend/src/types/index.ts`**: Added `HeroMarker`, `ClusterBubble`, `SmartMarkersResponse` interfaces
- **`frontend/src/api/client.ts`**: Added `smartMarkersApi.get()` method

### Phase 3: UI Styling
- **`frontend/src/styles/globals.css`**: Added CSS for:
  - `.hero-card` (floating card with category color accent, hover effects)
  - `.hero-card--{category}` (battle=red, treaty=blue, etc.)
  - `.cluster-bubble` (circular count bubble with zoom-click)
  - `.hero-card-deck` (mobile horizontal scroll)

### Phase 4: GlobeContainer Integration
- **`frontend/src/components/globe/GlobeContainer.tsx`**:
  - Added `smartMarkersApi` import and `smart-markers` query
  - Extended `htmlElements` memo to include hero + cluster markers with priority ordering
  - Extended `htmlElement` renderer with `hero` and `cluster` branches
  - Hero cards: show title, year, location, importance stars; click loads event detail
  - Cluster bubbles: show count, sized by log(count); click zooms into area

### Phase 5: Mobile HeroCardDeck
- **`frontend/src/components/mobile/HeroCardDeck.tsx`**: New component
  - Horizontal scrollable card deck showing hero markers
  - Tap: flies map to location + opens event detail
  - Uses own smart-markers query keyed to mobile zoom
- **`frontend/src/components/mobile/MobileLayout.tsx`**: Integrated HeroCardDeck below WorldBriefing

### Bug Fixes (Post-Implementation)

#### 1. 404 Error on `/globe/smart-markers`
- **Cause**: Old Python processes still running on port 8100, serving stale code
- **Fix**: Killed zombie processes, restarted uvicorn fresh
- **Verified**: All 4 zoom levels return data (cosmic: 3 heroes, continental: 8, regional: 14, local: 15)

#### 2. Globe Jitter/Vibration When Rotating
- **Cause**: `altitude` stored as `useState` → `handleZoom` called `setAltitude(pov.altitude)` every frame → re-render → `htmlElements` memo recalculated → DOM elements destroyed/recreated
- **Fix**: Changed `altitude` from `useState` to `useRef`, only update `currentZoomLevel` state when zoom level actually changes via functional update `setCurrentZoomLevel(prev => prev === newZoom ? prev : newZoom)`
- Added `placeholderData: (prev) => prev` to smart-markers query to prevent data flash
- Added `htmlTransitionDuration={800}` to Globe component

#### 3. Hero Card Click Behavior (3 iterations of user feedback)
- **v1**: Added zoom to altitude 0.6 on click → User: "too close, meaningless"
- **v2**: Made arcs semi-transparent → User: "arcs should be visible, OTHER things should fade"
- **v3**: Made everything always semi-transparent → User: "only fade when event IS SELECTED"
- **Final**:
  - Hero click: NO manual zoom, defers to existing `selectedEvent` useEffect (altitude: 2)
  - When `selectedEvent` exists: non-selected hero cards get `opacity: 0.3; pointer-events: none;`, clusters get `opacity: 0.2; pointer-events: none;`
  - Selected hero card: gold border highlight (`rgba(255, 215, 0, 0.8)` + glow shadow)
  - Arcs: always fully visible
  - Normal state (no selection): everything fully opaque

## Result
- TypeScript: `npx tsc --noEmit` passes
- Build: `npm run build` passes (15.72s)
- Backend: API verified with all 4 zoom levels
- Server running on port 8100

## Files Modified
1. `backend/app/api/v1_new/globe.py` (smart-markers endpoint)
2. `frontend/src/types/index.ts` (3 new interfaces)
3. `frontend/src/api/client.ts` (smartMarkersApi)
4. `frontend/src/components/globe/GlobeContainer.tsx` (query + rendering + jitter fix + selection fade)
5. `frontend/src/styles/globals.css` (hero card + cluster bubble CSS)
6. `frontend/src/components/mobile/HeroCardDeck.tsx` (new file)
7. `frontend/src/components/mobile/MobileLayout.tsx` (HeroCardDeck integration)

## Next Steps
- User to verify hero click behavior matches intent (fade + arcs visible)
- Tune zoom thresholds based on actual data density
- Add category icons to hero cards (currently text-only)
