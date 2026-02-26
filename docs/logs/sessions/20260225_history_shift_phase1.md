# Session Log: 2026-02-25 History Shift Phase 1

## Session Info
- **Purpose**: Implement History Shift Phase 1 - backend migration + API + frontend ShiftPanel

## Summary
Implemented the complete History Shift feature (Phase 1), which provides page-based sequential views of connected historical events (like Age of Empires scenarios). The UI uses a top/bottom split view: globe on top, shift content panel on bottom.

## Files Created
| File | Description |
|------|-------------|
| `backend/alembic/versions/600_history_shifts.py` | Alembic migration adding shift columns to historical_chains + chain_segments |
| `backend/app/api/v1/shifts.py` | Shifts API (list, detail, pages, single page) |
| `backend/scripts/seed_aggregate_shifts.py` | Seed script to auto-generate shifts from aggregate events |
| `frontend/src/components/shift/ShiftPanel.tsx` | Main shift panel component with page navigation |
| `frontend/src/components/shift/ShiftPanel.css` | Shift panel styles |

## Files Modified
| File | Changes |
|------|---------|
| `backend/app/models/v1/chain.py` | Added shift columns (display_type, chapter_count, globe_importance, thumbnail_url, parent_shift_id) to HistoricalChain; added page columns (chapter_title, chapter_number, page_narrative, page_narrative_ko, sub_shift_id, media_url) to ChainSegment; added 'aggregate' to chain_type constraint |
| `backend/app/api/v1/router.py` | Registered shifts router at /shifts |
| `frontend/src/types/index.ts` | Added HistoryShift and ShiftPage interfaces |
| `frontend/src/api/client.ts` | Added shiftsApi (list, get, getPages, getPage) |
| `frontend/src/store/globeStore.ts` | Added activeShift/activePageIndex state + openShift/closeShift/goToPage/nextPage/prevPage actions |
| `frontend/src/App.tsx` | Added lazy-loaded ShiftPanel, shift-active class on globe-section, hide timeline when shift active |
| `frontend/src/styles/globals.css` | Added .globe-section.shift-active CSS for top/bottom split layout |

## Architecture Decisions
1. **No table rename**: Kept `historical_chains` table name, only added columns. "Shift" is a UI/API concept only.
2. **Split view**: Top 50% globe, bottom 50% shift panel (not fullscreen modal).
3. **Keyboard navigation**: Arrow keys for page navigation, Escape to close.
4. **Globe sync**: Page changes fly globe to event coordinates + update timeline year.
5. **Lazy loading**: ShiftPanel is code-split for performance.

## Verification
- [x] TypeScript `tsc --noEmit` passes
- [x] `npm run build` succeeds (ShiftPanel: 2.62 kB chunk)
- [ ] `alembic upgrade head` (needs DB running)
- [ ] Seed script execution (needs DB running)
- [ ] Visual testing in dev server

## Next Steps
- Run alembic migration on compact DB
- Run seed_aggregate_shifts.py to populate data
- Add "View Shift" entry point in NarrativeCard for aggregate events
- Phase 2: LLM-generated narratives, chapter system, richer media
