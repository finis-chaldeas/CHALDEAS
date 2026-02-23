# Session Log: 2026-02-23 18:41

## Session Info
- **Purpose**: Frontend redesign - Globe-centric narrative experience

## What Was Done

### 1. Sidebar Drawer Conversion (globals.css + App.tsx)
- Changed `.app-container` from `grid-template-columns: 320px 1fr` to `grid-template-columns: 1fr`
- Made `.sidebar` a fixed position overlay drawer (`position: fixed; transform: translateX(-100%)`)
- Added `.sidebar.sidebar-open` state with `transform: translateX(0)`
- Made menu toggle button (`.mobile-menu-btn`) visible on all screen sizes (was mobile-only)
- Made overlay (`.mobile-overlay`) visible on all screen sizes
- Removed tablet breakpoint that set sidebar to 280px grid column
- Simplified mobile breakpoint (removed duplicate drawer rules now that they're default)

### 2. WorldBriefing Position Fix
- Changed `left: '320px'` to `left: '60px'` (past the hamburger menu button)
- Changed "Show Briefing" button from `left: '340px'` to `left: '68px'`

### 3. ViewportFeed Removal
- Removed `<ViewportFeed>` rendering from App.tsx
- Commented out import (file preserved for potential future use)
- WorldBriefing provides sufficient viewport context

### 4. NarrativePanel as Default (Classic Mode Removed)
- Removed `detailPanelMode` from settingsStore (type, state, setter)
- Removed all `detailPanelMode === 'narrative'` conditionals in App.tsx
- NarrativePanel always renders (no conditional wrapper)
- Removed classic EventDetailPanel rendering block
- Removed classic-only PersonDetailView rendering block
- Cleaned up handler functions (removed classic/narrative branching)

### 5. Landing Simplification
- Rewrote FeaturedPersons.tsx: card wall -> 2-button minimal overlay
- Two buttons: "Explore" (fly to 480 BCE Athens) and "Read Stories" (open sidebar drawer)
- Made landing overlay more transparent (0.75 opacity, 6px blur) so globe visible behind
- Updated App.tsx props: `onExplore`, `onReadStories`, `onClose`

### 6. Causal Flow Verification
- Confirmed: `setSelectedEvent()` in globeStore already calls `flyToLocation()` automatically
- Flow: Connected Event click -> API fetch -> handleEventClick -> setSelectedEvent (flyTo) + setCurrentYear
- No changes needed

### 7. SourceBrowser Filtering
- Added `type: 'book'` to sourcesApi.list() call
- Backend already supports type filter parameter

## Files Changed
- `frontend/src/styles/globals.css` - Sidebar drawer layout
- `frontend/src/App.tsx` - Drawer toggle, ViewportFeed removal, classic mode removal, landing props
- `frontend/src/components/landing/FeaturedPersons.tsx` - Minimal 2-button overlay
- `frontend/src/components/landing/Landing.css` - Transparent overlay style
- `frontend/src/components/globe/WorldBriefing.tsx` - Position fix (left: 60px)
- `frontend/src/store/settingsStore.ts` - Removed detailPanelMode
- `frontend/src/components/narrative/NarrativePanel.tsx` - Comment update
- `frontend/src/components/sources/SourceBrowser.tsx` - Book type filter

## Verification
- `npx tsc --noEmit` - PASS
- `npm run build` - PASS (13.65s)

## Result
- Globe is now 100% fullscreen by default
- Sidebar is a collapsible drawer (hamburger menu on all screen sizes)
- Narrative panel is the sole detail view
- Landing is a minimal 2-button overlay over the rotating globe
- WorldBriefing positioned naturally on globe (not offset by sidebar)
