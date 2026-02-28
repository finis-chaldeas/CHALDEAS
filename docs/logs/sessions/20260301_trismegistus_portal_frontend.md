# 20260301 — Trismegistus Portal Frontend + Bidirectional System

## Purpose
1. Replace old `TrismegistosModal` with a layered portal system: Magazine Home → Collection → Detail
2. Add newspaper-style page tabs (Front Page / FGO / Reading / Collections)
3. Add mini preview panel (right slide-in on item click)
4. Implement SHEBA ↔ Trismegistus bidirectional mode switching (Phase A + B)

---

## Part 1: Portal Base (Magazine + Preview Panel)

### Backend (1 file)
- **`portal.py`**: comma-separated `item_type` filter, `joinedload` for collection entries, `RecommendationItem` + featured endpoint with shuffled mix

### Frontend Components (10 new files)
- **`portal.css`**: Full CSS — backdrop, layers, hero, recommendations, FGO cards, reading list, collections, detail, preview panel, responsive
- **`TrismegistosPortal.tsx`**: Container — layer stack, Escape priority (preview → layer → close), scroll restoration
- **`MagazineHome.tsx`**: 4-page tab system (Front/FGO/Reading/Collections), fetches via react-query
- **`TodayHero.tsx`**: Daily rotating featured item, Globe View / Read More CTAs
- **`RecommendationRow.tsx`**: Horizontal scroll cards
- **`FgoSection.tsx`**: Singularities / Lostbelts / Servant Columns
- **`ReadingSection.tsx`**: Filter chips + show more toggle
- **`CollectionGrid.tsx`**: CSS grid of collection cards
- **`CollectionPage.tsx`**: Collection entries grouped by type
- **`PortalItemDetail.tsx`**: Full article with sections accordion, servants, sources

### Frontend Infrastructure (3 files)
- **`portalStore.ts`**: Zustand store with layer stack (open/close/push/pop), page tabs, preview slug
- **`types/index.ts`**: Portal types (PortalLayer, PortalItemSummary, CollectionSummary, etc.)
- **`client.ts`**: `portalApi` with items/collections/featured/resolve/suggestLinks

---

## Part 2: Bidirectional System (Phase A + B)

### Phase A-1: Suspend/Resume
- **`portalStore.ts`**: Added `suspend()` / `resume()` / `isSuspended` + `suspendedLayers/Page/Preview` state
- **`TodayHero.tsx`**, **`PreviewPanel.tsx`**, **`PortalItemDetail.tsx`**: "Globe View" → `suspend()` (was `close()`)
- **`FloatingButtons.tsx`**: Cyan dot indicator when portal is suspended
- **`globals.css`**: `.floating-btn--suspended` styles
- **`App.tsx`**: `open()` with auto-resume when `isSuspended`

### Phase A-2: Globe Context
- **`portalStore.ts`**: `GlobeContext { lat, lng, year }`, passed via `open(context)`
- **`App.tsx`**: Passes `{ lat, lng, year }` from globeStore/timelineStore when opening portal
- **`MagazineHome.tsx`**: Context banner "Viewing: 480 BCE" + "Return to Globe →" on Front Page

### Phase B-1: Globe → Portal Links
- **`portal.py`**: 2 new endpoints:
  - `GET /portal/items/by-event/{event_id}` — JSONB `@>` containment on `related_event_ids`
  - `GET /portal/items/by-shift/{shift_id}` — CollectionEntry join for same-collection items
- **`client.ts`**: `portalApi.getItemsByEvent()`, `portalApi.getItemsByShift()`
- **`EventNarrativeCard.tsx`**: "✦ Trismegistus" section — queries portal items by event_id, click → open portal with item detail
- **`ShiftPanel.tsx`** + **`ShiftPanel.css`**: "✦ Portal" button in banner, queries portal items by shift_id, click → close shift + open portal

### Phase B-2: Portal → Globe Enrichment
- `onSetCurrentYear` → `onGlobeView({ year, eventId? })` across 6 files:
  - **`TrismegistosPortal.tsx`**, **`MagazineHome.tsx`**, **`TodayHero.tsx`**, **`PreviewPanel.tsx`**, **`PortalItemDetail.tsx`**, **`App.tsx`**
- **PreviewPanel** / **PortalItemDetail**: "Globe View" now passes `related_event_ids[0]` as eventId
- **App.tsx**: `onGlobeView` handler calls `handleNarrativeEventClick(eventId)` → auto-opens NarrativePanel on globe

---

## Changed Files Summary (this session)

| # | File | Change |
|---|------|--------|
| 1 | `backend/app/api/v1/portal.py` | Reverse-lookup endpoints (by-event, by-shift) |
| 2 | `frontend/src/App.tsx` | Globe context passing + onGlobeView handler |
| 3 | `frontend/src/api/client.ts` | portalApi reverse-lookup methods |
| 4 | `frontend/src/components/globe/FloatingButtons.tsx` | Suspended indicator |
| 5 | `frontend/src/components/narrative/EventNarrativeCard.tsx` | "✦ Trismegistus" related articles |
| 6 | `frontend/src/components/shift/ShiftPanel.css` | Portal link button styles |
| 7 | `frontend/src/components/shift/ShiftPanel.tsx` | "✦ Portal" button |
| 8 | `frontend/src/components/trismegistos/*.tsx` | All portal components (10 new) |
| 9 | `frontend/src/components/trismegistos/portal.css` | Full portal styles |
| 10 | `frontend/src/store/portalStore.ts` | New store with suspend/resume/preview |
| 11 | `frontend/src/styles/globals.css` | Suspended button styles |
| 12 | `frontend/src/types/index.ts` | Portal type definitions |
| 13 | `docs/ideal/PORTAL_06_BIDIRECTIONAL.md` | Bidirectional spec (Phase A/B/C) |
| 14 | `docs/ideal/INDEX.md` | Added PORTAL_06 link |

## Verification
- `npx tsc --noEmit` — pass
- `npm run build` — pass (TrismegistosPortal: 18.81 kB / 4.67 kB gzip)

## Next Steps
- **Phase C**: 통합 상단 모드 바 (SHEBA / TRISMEGISTOS / SHIFT 탭)
- i18n labels (section titles hardcoded English)
- Mobile responsiveness testing
- FGO servant column ↔ person 역참조
