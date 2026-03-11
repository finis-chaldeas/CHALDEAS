# 2026-03-11 — FGO Portal Display Redesign

## Purpose
Upgrade Trismegistos portal to properly display 46 FGO content items (30 servant columns, 9 singularities, 7 lostbelts) and 15 FGO-linked history shifts. Previous UI was skeleton-era horizontal scroll + FAQ-style accordion.

## Changes

### Phase 1: Article Detail — Full Scroll Magazine Layout
- **`PortalItemDetail.tsx`**: Rewrote from accordion to continuous-scroll article
  - Removed `openSections` state + toggle accordion logic
  - Added Table of Contents (TOC) with scroll-to-section navigation
  - All sections render fully expanded for magazine reading experience
  - Added Related Shifts section (queries shifts within ±200 years)
  - Dual CTA buttons: Globe View (secondary) + Start Shift (primary)
  - Accepts `onOpenShift` prop for shift launching

### Phase 2: FGO Tab Redesign
- **`FgoSection.tsx`**: Rewritten with chip bar navigation (Story/Servants/Shifts)
- **NEW `FgoStoryChain.tsx`**: Vertical timeline chain for singularities + lostbelts
  - Left color border: orange = singularity, magenta = lostbelt
  - Two arcs: "Grand Order" and "Cosmos Denial"
- **NEW `FgoServantGrid.tsx`**: Culture group grid for 30 servants
  - 7 hardcoded groups: Greek, Celtic, Near East, Indian, East Asian, Roman, European
  - "Other" catch-all for unmatched slugs
- **NEW `FgoShiftList.tsx`**: FGO-linked shifts from 'fgo-history-bridge' collection

### Phase 3: Backend Year Range Filter
- **`backend/app/api/v1/shifts.py`**: Added `year_start` and `year_end` query params to list endpoint for overlap-based shift filtering

### Phase 4: CSS
- **`portal.css`**: ~300 lines of new styles
  - `.portal-article*` — full-scroll article layout, TOC, section typography
  - `.fgo-chip-bar` / `.fgo-chip` — sub-navigation chips
  - `.fgo-story*` — vertical timeline chain
  - `.fgo-servants*` — culture group grid
  - `.fgo-shifts*` — shift list cards
  - Responsive rules for mobile

### Prop Threading
- **`TrismegistosPortal.tsx`**: Pass `onOpenShift` to `PortalItemDetail`
- **`MagazineHome.tsx`**: Pass `onOpenShift` to `FgoSection`

## Verification
- `npx tsc --noEmit` — clean
- `npm run build` — success (11.48s)

## Files Changed
| File | Action |
|------|--------|
| `frontend/src/components/trismegistos/PortalItemDetail.tsx` | Rewritten |
| `frontend/src/components/trismegistos/FgoSection.tsx` | Rewritten |
| `frontend/src/components/trismegistos/FgoStoryChain.tsx` | NEW |
| `frontend/src/components/trismegistos/FgoServantGrid.tsx` | NEW |
| `frontend/src/components/trismegistos/FgoShiftList.tsx` | NEW |
| `frontend/src/components/trismegistos/portal.css` | Extended |
| `frontend/src/components/trismegistos/TrismegistosPortal.tsx` | Minor edit |
| `frontend/src/components/trismegistos/MagazineHome.tsx` | Minor edit |
| `backend/app/api/v1/shifts.py` | Added year_start/year_end params |

## Next Steps
- Phase 4: Front Page enhancement (TodayHero rotation with FGO content, recommendation mix)
- Visual polish: test with actual data in dev server
- Add `fgo-history-bridge` collection entries if not already present
