# Session Log: 2026-02-24 Globe Mini Modal & UX Improvements

## Session Info
- **Purpose**: Cluster/location click UX, hero localization, speed controls cleanup

## Changes Made

### 1. Backend: ClusterBubble top_events
- **File**: `backend/app/api/v1_new/globe.py`
- Added `ClusterEvent` model (id, title, title_ko/ja, year, importance, category)
- Added `top_events: List[ClusterEvent]` to `ClusterBubble` model
- After cluster query, uses window function SQL to fetch top 7 events per grid cell
- Maps events to clusters by grid key

### 2. Backend: HeroMarker localized location names
- **File**: `backend/app/api/v1_new/globe.py`
- Added `location_name_ko`, `location_name_ja`, `location_id` to HeroMarker
- SQL now selects `l.name_ko`, `l.name_ja`, `l.id` from locations table
- Frontend can now show "디모나" instead of "Dimona" in Korean mode

### 3. Backend: Hero zoom continuity fix
- **File**: `backend/app/api/v1_new/globe.py`
- `_select_heroes()` now uses two-pass monotonic inclusion:
  - Pass 1: Always select importance 5 "anchor" events with cosmic-level distance (15°)
  - Pass 2: Fill remaining with lower-importance at current zoom's min_distance
- Prevents events from flip-flopping between zoom levels

### 4. Frontend: Globe Mini Modal (replacing fixed panel)
- **File**: `frontend/src/components/globe/GlobeContainer.tsx`
- Removed fixed-position `cluster-event-panel` JSX
- Added `event-panel` kind to `htmlElementsData` — floats above city on globe
- Mini modal rendered as globe-anchored DOM element (not fixed position)
- Arrow points down to city location
- Event cards are clickable → opens event detail
- Close button dismisses modal
- Auto-dismiss on time slider change

### 5. Frontend: Location node click → mini modal (no LocationDetailView)
- Node click no longer calls `onLocationClick` (no right panel)
- Instead: pan to city + fetch events via `nodesApi.getEvents`
- Shows mini modal above city with event list
- If active_count > 0: uses time filter (±100yr)
- If active_count = 0: fetches ALL events at location (no time filter)
- Low importance events always accessible via location click

### 6. Frontend: Hero card location name clickable
- Location name in hero cards now localized (ko/ja)
- Clicking location name → pan to location + show events mini modal
- Visual: location name gets underline + cyan color on hover

### 7. Frontend: Cluster click → zoom in + mini modal
- Cluster click always zooms in by 40% (`currentAlt * 0.6`)
- Also shows mini modal with cluster's top events
- Guaranteed never to zoom out

### 8. Frontend: Speed controls cleanup
- **Files**: `UnifiedTimeline.tsx`, `TimelapseControls.tsx`
- Removed 2x and 50x speed options
- Kept only: 1x, 5x, 10x
- Added pause/stop button (⏹/⏸) next to speed buttons

### 9. Frontend: Types
- **File**: `frontend/src/types/index.ts`
- Added `ClusterEvent` interface
- Added `top_events` to `ClusterBubble`
- Added `location_name_ko/ja`, `location_id` to `HeroMarker`

### 10. CSS: Globe Mini Modal
- **File**: `frontend/src/styles/globals.css`
- `.globe-mini-modal` — glass-morphic floating panel above city
- Arrow pointing down to city
- Category color-coded event items
- Fade when event detail panel is open
- Entry animation (scale + translateY)

## Translation Progress
- Korean: 2,553/3,856 (66%) — still running

## Build Status
- TypeScript: PASS
- Vite build: PASS

## Backend Restart Needed
All backend changes require server restart to take effect.

## Next Steps
- Japanese translation after Korean completes
- Test mini modal positioning on various zoom levels
- Consider tile-based globe textures for higher resolution
