# Hero Card Clustering Redesign

**Date**: 2026-02-27
**Purpose**: Prevent hero card overlap with 3-tier cascading approach

## Changes

### Backend (`backend/app/api/v1_new/globe.py`)
- **_select_heroes 2-pass**: Added orphan collection + Pass 2 force-attribution for imp>=4 events that were silently dropped
- **ZOOM_CONFIG**: Adjusted thresholds (cosmic: imp 4/10 heroes/20deg, continental: 4/15/8, regional: 3/25/3, local: 2/40/1.0)
- **NearbyEvent lat/lng**: Added coordinates to model and serialization for connector arcs

### Frontend Types (`frontend/src/types/index.ts`)
- Added `lat?: number`, `lng?: number` to NearbyEvent interface

### New Hook (`frontend/src/hooks/useHeroOverlapResolver.ts`)
- RAF-based screen-coordinate overlap resolver
- 3-iteration force displacement (lower importance cards pushed away)
- Lerp smoothing (15% per frame) for smooth transitions
- >150px displacement → occlude (hide) card
- Pin (pulsing dot) + stem (line) connector when card displaced

### GlobeContainer (`frontend/src/components/globe/GlobeContainer.tsx`)
- Added `data-importance` attribute to hero-card elements
- Imported and wired `useHeroOverlapResolver(!activeShift)`
- Connector arcs: hero → distant nearby events (layer_type='connector', subtle gray, no animation)
- Arc targets: distance check (2deg) before adding — prevents overlapping hero cards
- City nodes: geographic proximity filter (1.5deg) in addition to location_id check
- LAYER_COLORS: added 'connector' entry

### CSS (`frontend/src/styles/globals.css`)
- `.hero-pin`: 6px pulsing cyan dot at anchor position
- `.hero-stem`: 1px semi-transparent line from pin to displaced card
- `.hero-card--occluded`: opacity 0 + pointer-events none for merged cards

## Verification
- `npx tsc --noEmit` — pass
- `npm run build` — pass

## Architecture
```
Backend: importance filter + geographic clustering (rough)
    ↓
Frontend render: CSS2DRenderer 3D→2D projection
    ↓
useHeroOverlapResolver (every frame):
  1. getBoundingClientRect() for all hero cards
  2. Force displacement (3 iterations, high imp = anchored)
  3. Lerp smoothed transform + pin/stem
  4. >150px → occlude
```

## Next Steps
- Tune displacement threshold (currently 150px) based on actual UX testing
- Consider merge badge count for occluded cards
- Test with dense marker scenarios (e.g., Mediterranean ancient history)
