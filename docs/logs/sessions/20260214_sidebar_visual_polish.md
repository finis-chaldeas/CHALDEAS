# Session Log: 2026-02-14 Sidebar Visual Polish

## Session Info
- **Purpose**: Fix globe brightness, redesign navigator tab cards with sort options and richer display

## Changes Made

### Fix 1: Globe brightness boost
- `frontend/src/styles/globals.css`: Default globe canvas now has `brightness(1.35) saturate(1.15) contrast(1.05)` filter. Added ambient glow `::before` pseudo-element behind globe. Holo style gets `brightness(1.15) saturate(1.3)`. Night style boosted to `brightness(1.4) saturate(1.3) contrast(1.1)`.
- `frontend/src/components/globe/GlobeContainer.tsx`: Increased atmosphere altitude from 0.15 to 0.22 (default) and 0.2 to 0.25 (holo).

### Fix 2: Backend - expose connection_count
- `backend/app/schemas/event.py`: Added `connection_count: int = 0` to EventBase
- `backend/app/schemas/person.py`: Added `connection_count: int = 0` to PersonBase
- `backend/app/api/v1/events.py`: Added `connection_count` to event_to_dict output
- `backend/app/services/event_service.py`: Added `sort_by='connections'` option
- `frontend/src/types/index.ts`: Added `connection_count?: number` to Event and Person types

### Fix 3: EventTab redesign
- `frontend/src/components/navigator/EventTab.tsx`: Complete rewrite
  - Sort dropdown: Importance / Connections / Date
  - Category filter dropdown
  - Custom card design with colored importance bar (left edge)
  - Shows importance dots (filled/empty circles), connection count badge, location name
  - Importance-5 events get gold title, importance bar color-coded
  - No longer uses VirtualEventList - renders its own cards for tighter control
  - Removed bookmark props (simplified)

### Fix 4: PersonTab redesign
- `frontend/src/components/navigator/PersonTab.tsx`: Complete rewrite
  - Sort dropdown: Connections / Birth Year
  - Search input + sort side-by-side
  - Avatar circle with first letter of name
  - Shows lifespan, category/role, birthplace
  - Connection count badge (high/med/low tiers with distinct colors)

### Fix 5: LocationTab redesign
- `frontend/src/components/navigator/LocationTab.tsx`: Complete rewrite
  - Search input
  - Type-based emoji icons (city, region, landmark, battle_site)
  - Shows type label, country, lat/lng coordinates

### Fix 6: Navigator + App cleanup
- `frontend/src/components/navigator/Navigator.tsx`: Removed bookmarkedIds and onBookmarkToggle props (EventTab no longer needs them)
- `frontend/src/App.tsx`: Removed bookmarkedIds/toggleBookmark/useBookmarkStore from Navigator pass-through

### Fix 7: navigator.css rewrite
- `frontend/src/components/navigator/navigator.css`: Complete rewrite with new card styles for all three entity types, shared controls row, viewport tag, scrollbar styling. Kept existing tab bar, viewport indicator, chain overview, era item, footer action styles.

## Result
- TypeScript: 0 errors (`npx tsc --noEmit` passes)
- Globe: brighter with visible atmosphere glow
- Events: sorted by importance/connections/date with colored importance bars and connection badges
- Persons: avatar + lifespan + connection count badge
- Locations: emoji type icons + country + coordinates

## Next Steps
- Test with live data to verify visual improvements
- Consider re-adding bookmarks in a different UX pattern if needed
