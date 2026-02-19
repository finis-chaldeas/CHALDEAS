# Session Log: 2026-02-14 Sidebar Redesign

## Session Info
- **Purpose**: Replace cluttered sidebar with Navigator tabs + viewport-aware filtering

## Changes Made

### Phase 1: Viewport tracking in globeStore
- `frontend/src/store/globeStore.ts`: Added `ViewportBounds`, `ZoomLevel` types; `viewportBounds`, `zoomLevel` state; `setViewportBounds()` action that derives zoomLevel from altitude
- `frontend/src/components/globe/GlobeContainer.tsx`: Updated `handleZoom` to compute viewport bounds from `pointOfView()` and push to store via `setViewportBounds`

### Phase 2: Sidebar replaced with Navigator
- `frontend/src/App.tsx`: Removed category filters, era toggle, advanced filters, chain stats section, VirtualEventList, ShowcaseMenu from sidebar. Replaced with `<Navigator>` component. Simplified footer to compact FGO/Servants buttons. Removed unused state (selectedCategory, showAllEras, advancedFilters, etc.)
- `frontend/src/components/navigator/Navigator.tsx`: Updated props to accept `currentYear`, `viewportBounds`, `zoomLevel`. Added viewport indicator badge.

### Phase 3: Importance-based display
- `frontend/src/components/navigator/EventTab.tsx`: Full rewrite - fetches events with viewport bounds + importance sort via API. Category filter as dropdown. Passes `importanceClass` to VirtualEventList.
- `frontend/src/components/sidebar/VirtualEventList.tsx`: Added `importanceClass` optional prop. Shows category name (not just slug).
- `frontend/src/components/navigator/PersonTab.tsx`: Viewport-aware queries (birthplace bounds), sorted by connections.
- `frontend/src/components/navigator/LocationTab.tsx`: Viewport-aware queries using existing API bounds params.

### Phase 4: Backend viewport query support
- `backend/app/api/v1/events.py`: Added `lat_min`, `lat_max`, `lng_min`, `lng_max`, `sort_by` params to list_events
- `backend/app/services/event_service.py`: Added viewport bounds filtering via Location join, `sort_by='importance'` support
- `backend/app/api/v1/persons.py`: Added `lat_min`, `lat_max`, `lng_min`, `lng_max`, `sort_by` params to list_persons
- `backend/app/services/person_service.py`: Added viewport bounds filtering via birthplace Location join, `sort_by='connections'` support

### Phase 5: Visual cleanup
- `frontend/src/components/navigator/navigator.css`: New CSS file with FGO-style tab bar, viewport indicator, filter row, importance classes, footer action buttons

## Result
- TypeScript: 0 errors (`npx tsc --noEmit` passes)
- Sidebar now shows 5 tabs: Events/Persons/Locations/Eras/Chains
- Events sorted by importance, with visual accents for importance levels
- Viewport-aware: zooming into a region filters sidebar content to visible area

## Next Steps
- Visual polish after testing with live data
- Consider adding `q` search param to events API for text search within EventTab
