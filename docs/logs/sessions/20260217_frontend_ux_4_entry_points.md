# Session Log: 2026-02-17 Frontend UX 4 Entry Points + Globe Zoom

## Session Info
- **Purpose**: Implement 4 entry point tabs (SHEBA/PAPERMOON/LAPLACE/TRISMEGISTUS) + 4-level Globe zoom system

## Changes Made

### Phase 1: Static Data
- **Created** `frontend/src/data/shebaEpisodes.ts` - 18 curated historical episodes
- **Created** `frontend/src/data/laplaceTimeline.ts` - 6 eras x 8-12 entries (57 total)

### Phase 2: Globe Zoom System
- **Modified** `frontend/src/store/globeStore.ts`
  - ZoomLevel: `'global' | 'regional' | 'local'` -> `'cosmic' | 'continental' | 'regional' | 'local'`
  - Added `ZOOM_THRESHOLDS`, `getZoomLevel()` helper, `returnToCosmic` action
  - Initial altitude 2.5 -> 3.0 (starts in COSMIC)
- **Modified** `frontend/src/components/globe/GlobeContainer.tsx`
  - Zoom-based label filtering (cosmic=5, continental=4, regional=3, local=1)
  - Importance-based label colors (gold/cyan/gray)
  - Auto-rotate only at cosmic zoom
  - Added zoom level indicator UI (REGIONAL/LOCAL with "Back to Globe")
- **Modified** `frontend/src/components/globe/GlobeHeatmap.css` - zoom indicator styles
- **Modified 7 Navigator tabs** - `'global'` -> `'cosmic'` in all viewport checks:
  - FeedTab, PersonTab, EventTab, LocationTab, ThreadsTab, NetworkTab, Navigator

### Phase 3: TimelineTab (LAPLACE)
- **Created** `frontend/src/components/navigator/TimelineTab.tsx`
  - Collapsible 6-era timeline with search filter
  - Click entry -> flyToLocation + setCurrentYear
  - Servant tags on relevant entries

### Phase 4: ServantTab (TRISMEGISTUS)
- **Created** `frontend/src/components/navigator/ServantTab.tsx`
  - Class filter buttons (Saber/Archer/Lancer/etc + Extra)
  - Search filter, uses `useQuery` + `servantsApi`
  - Inline detail view via ServantTabDetail
- **Created** `frontend/src/components/navigator/ServantTabDetail.tsx`
  - Biography, lifespan, book mentions with expandable contexts
  - Action buttons: View in CHALDEAS, Explore Era, Wikidata

### Phase 5: FeedTab Enhancement
- **Modified** `frontend/src/components/navigator/FeedTab.tsx`
  - Added SHEBA curated episodes section at top
  - Shows 4 episodes by default, expandable
  - Click episode -> flyToLocation + setCurrentYear

### Phase 6: Navigator + App.tsx Integration
- **Rewrote** `frontend/src/components/navigator/Navigator.tsx`
  - Tabs: Feed (SHEBA) / People (PAPERMOON) / Timeline (LAPLACE) / Servants (TRISMEGISTUS)
  - New props: `onFlyToLocation`, `onSetCurrentYear`
- **Modified** `frontend/src/App.tsx`
  - Removed `ServantPanel` modal import and rendering
  - Removed `isServantPanelOpen` state
  - Removed footer "Servants" button
  - Pass `flyToLocation` and `setCurrentYear` to Navigator
- **Modified** `frontend/src/components/navigator/index.ts` - new exports
- **Modified** `frontend/src/components/navigator/navigator.css` - extensive new styles

### Phase 7: Backend Bug Fix
- **Fixed** `backend/app/schemas/location.py`
  - `type: str` -> `type: Optional[str] = None` in LocationBase schema
  - Root cause: Person detail API returned 500 for all persons because some deathplace/birthplace locations had NULL type field
  - This made ALL PersonDetailView displays broken (the user's reported "엉망" issue)

## Results
- `npx tsc --noEmit` passes with 0 errors
- All 4 tabs render correctly
- ServantPanel modal completely removed (replaced by inline Servants tab)
- Globe zoom system now has 4 levels with visual indicators
- Person detail API now returns 200 for all persons (was returning 500 for all)
- 6 servants have person_ids missing from Compact DB (Leonidas, Anastasia, Robin Hood, Lu Bu, Xiang Yu, Fionn) - data gap, not code bug

## File Summary
| File | Action |
|------|--------|
| `frontend/src/data/shebaEpisodes.ts` | NEW |
| `frontend/src/data/laplaceTimeline.ts` | NEW |
| `frontend/src/components/navigator/TimelineTab.tsx` | NEW |
| `frontend/src/components/navigator/ServantTab.tsx` | NEW |
| `frontend/src/components/navigator/ServantTabDetail.tsx` | NEW |
| `frontend/src/store/globeStore.ts` | MODIFIED |
| `frontend/src/components/globe/GlobeContainer.tsx` | MODIFIED |
| `frontend/src/components/globe/GlobeHeatmap.css` | MODIFIED |
| `frontend/src/components/navigator/Navigator.tsx` | REWRITTEN |
| `frontend/src/components/navigator/FeedTab.tsx` | MODIFIED |
| `frontend/src/components/navigator/PersonTab.tsx` | MODIFIED |
| `frontend/src/components/navigator/EventTab.tsx` | MODIFIED |
| `frontend/src/components/navigator/LocationTab.tsx` | MODIFIED |
| `frontend/src/components/navigator/ThreadsTab.tsx` | MODIFIED |
| `frontend/src/components/navigator/NetworkTab.tsx` | MODIFIED |
| `frontend/src/components/navigator/navigator.css` | MODIFIED |
| `frontend/src/components/navigator/index.ts` | MODIFIED |
| `frontend/src/App.tsx` | MODIFIED |
| `backend/app/schemas/location.py` | BUGFIX |
