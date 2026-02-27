# 20260227 — Unified Hero Block + Region Modal

## Purpose
Replace separated hero card / fan-out / pin marker system with a unified hero block + region badge + region modal.

## Changes

### Backend (`backend/app/api/v1_new/globe.py`)
- `StackedEvent` → `NearbyEvent` (rename, same fields)
- Added `NearbyPerson` model (id, name, name_ko/ja, birth/death_year, role, importance)
- `HeroMarker.stacked` → `nearby_events` (max 7), added `nearby_persons` (max 5)
- Removed `PinMarker` model and `PIN_CONFIG`
- Removed `SmartMarkersResponse.pins` field
- Step 6: Replaced event+person pin queries with person-to-nearest-hero attribution logic

### Frontend Types (`frontend/src/types/index.ts`)
- `StackedEvent` → `NearbyEvent`
- Added `NearbyPerson` interface
- Updated `HeroMarker`: `stacked` → `nearby_events`, added `nearby_persons`
- Removed `PinMarker` interface
- Removed `pins` from `SmartMarkersResponse`

### Frontend Globe (`frontend/src/components/globe/GlobeContainer.tsx`)
- Import: replaced `StackedEvent, PinMarker` with `NearbyEvent, NearbyPerson`
- `clusterPanel` state: added optional `persons?: NearbyPerson[]`
- normalHtmlElements: removed pin mapping (2c block), hero uses `nearby_events/nearby_persons`
- Hero card rendering: removed `.hero-stack` wrapper, peek cards, fan cards
- Added region badge (stacked chip design) with category colors from nearby_events
- Badge click → opens region modal (mini modal with events + persons)
- Removed entire `kind === 'pin'` branch
- Event panel: added person section with `[data-person-id]` click handlers
- Section labels for events/persons in mini modal

### CSS (`frontend/src/styles/globals.css`)
- Added `position: relative` to `.hero-card`
- Removed: `.hero-stack*` (fan-out), `.pin-marker*` (pin markers) — ~180 lines
- Added: `.hero-region-badge`, `.hero-region-chip*` (stacked chip badge)
- Added: `.globe-mini-modal-section-label`, `.globe-mini-modal-person*` (person items)

## Verification
- `npx tsc --noEmit` passes
- No remaining references to `PinMarker`, `StackedEvent`, `PIN_CONFIG`

## Next Steps
- Visual testing: verify badge renders correctly on globe
- Test badge click → region modal → event/person click flows
- Test that nearby=0 heroes show clean cards without badge
