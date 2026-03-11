# 2026-03-11: Portal Reading/Collections Tab Redesign

## Purpose
Replace the empty Reading tab (0 portal_items) and sparse Collections tab with two rich new tabs:
- **History Magazine** — surfaces 895 shifts + period narratives + featured persons
- **Era Explorer** — era chip filter + expandable period cards + theme collections

## Changes

### New Files (9)
| File | Role |
|------|------|
| `HistoryMagazine.tsx` | Main magazine tab — 5-section vertical scroll |
| `MagazineShiftHero.tsx` | Hero card for featured shift |
| `MagazineShiftRow.tsx` | Type-grouped horizontal shift carousel + expand toggle |
| `MagazineSpotlight.tsx` | Period narrative editorial cards |
| `MagazinePersonRow.tsx` | Featured persons horizontal carousel |
| `MagazineTypeGrid.tsx` | Chain type quick-link grid |
| `EraExplorer.tsx` | Era chip bar + period timeline + collection footer |
| `PeriodCard.tsx` | Expandable period card (collapsed/expanded) |
| `PeriodDetail.tsx` | Expanded period: narrative + regions + events + persons + shifts |

### Modified Files (6)
| File | Change |
|------|--------|
| `MagazineHome.tsx` | Replaced Reading/Collections tabs with Magazine/EraExplorer, removed unused queries |
| `TrismegistosPortal.tsx` | Pass onEventClick + onPersonClick to MagazineHome |
| `portalStore.ts` | Added `eraContext`, `navigateToEra()`, expanded PageKey type |
| `portal.css` | Added `.mag-*` (magazine) + `.era-*` (era explorer) CSS classes |
| `en.json` / `ko.json` / `ja.json` | Added magazine + era i18n keys |

### Not Changed
- `ReadingSection.tsx` — kept (not imported anymore, can be deleted later)
- No backend changes — uses existing shiftsApi, timelineApi, featuredApi, portalApi

## Data Flow
- Magazine: `shiftsApi.list(200)` → client-side chain_type grouping
- Magazine spotlight: `timelineApi.listPeriods(min_score=80)` → 2 narrative periods
- Magazine persons: `featuredApi.getPersons(limit=10)`
- Era Explorer: `timelineApi.listPeriods(min_score=70, limit=300)` → client-side era filter
- Era detail: `timelineApi.getPeriodDetail()` + `shiftsApi.list(year range)` on-demand

## Verification
- `npx tsc --noEmit` — 0 errors
- `npm run build` — successful (10s)

## Next Steps
- Delete `ReadingSection.tsx` if confirmed unused
- Add scroll-to-section behavior for MagazineTypeGrid tiles → MagazineShiftRow anchors
- Consider lazy-loading magazine tab data only when tab is active
