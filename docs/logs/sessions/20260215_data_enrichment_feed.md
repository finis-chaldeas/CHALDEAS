# Session Log: 2026-02-15 Data Enrichment + Feed

## Session Info
- **Plan Checkpoint**: Data Enrichment + Context Feed
- **Purpose**: Enrich persons/events from entity_properties, add QRank-based importance, build unified Feed API and FeedTab

## Work Done

### Phase 1-2: SQL Enrichment (Running)
- Executed `backend/scripts/enrich_persons.sql` (birth_year, death_year, birthplace_id, deathplace_id, role from entity_properties P569/P570/P19/P20/P106)
- Executed `backend/scripts/enrich_events.sql` (primary_location_id from event_locations)
- **Status**: Running - large table joins across millions of rows

### Phase 3: QRank + Importance Scripts (Created)
- `backend/scripts/import_qrank.py` - Downloads QRank CSV from Wikimedia, creates qrank table, imports scores
- `backend/scripts/compute_importance.py` - Computes event importance 1-5 via composite score (QRank 50% + connections 30% + participants 20%)
- `backend/scripts/recompute_connections.py` - Recalculates connection_count from actual junction tables

### Phase 4: Biography Extraction (Created)
- `backend/scripts/extract_biographies.py` - Extracts first paragraphs from Wikipedia sources for event-connected persons

### Phase 5: Feed API (Created)
- `backend/app/api/v1/feed.py` - GET /api/v1/feed with year/viewport filtering
  - Returns interleaved events + persons sorted by importance
  - Gracefully handles missing qrank table
  - Includes context strings, participants, role info
- Registered in `backend/app/api/v1/router.py`
- Added `feedApi` to `frontend/src/api/client.ts`

### Phase 6-7: Frontend (Created/Modified)
- `frontend/src/components/navigator/FeedTab.tsx` - New unified feed component
  - Event cards: importance stars, category badge, date, location, description, participants
  - Person cards: importance stars, role badge, lifespan, biography snippet, event count, Story button
- `frontend/src/components/navigator/Navigator.tsx` - Updated tabs: Feed | Places | Eras | Chains (removed Threads/Network)
- `frontend/src/components/navigator/navigator.css` - Added feed-card styles
- `frontend/src/types/index.ts` - Added FeedItem, FeedResponse types
- `frontend/src/components/navigator/index.ts` - Updated exports

### Phase 8: Cleanup
- Removed ThreadsTab and NetworkTab from Navigator imports/exports
- TypeScript build: 0 errors (`npx tsc --noEmit`)
- Old tab files (ThreadsTab.tsx, NetworkTab.tsx, EventTab.tsx, PersonTab.tsx) left in place but unused

## Files Changed
- **New**: `backend/scripts/import_qrank.py`, `compute_importance.py`, `recompute_connections.py`, `extract_biographies.py`
- **New**: `backend/app/api/v1/feed.py`
- **New**: `frontend/src/components/navigator/FeedTab.tsx`
- **Modified**: `backend/app/api/v1/router.py`, `frontend/src/api/client.ts`, `frontend/src/types/index.ts`
- **Modified**: `frontend/src/components/navigator/Navigator.tsx`, `navigator.css`, `index.ts`

## Result
- All code created and TypeScript verified
- SQL enrichment scripts running (will take time for millions of rows)
- Data pipeline scripts ready to run sequentially after enrichment

## Next Steps
1. Wait for SQL enrichment to complete, verify with `SELECT COUNT(*) FROM persons WHERE role IS NOT NULL`
2. Run: `python scripts/import_qrank.py` (downloads ~100MB, imports scores)
3. Run: `python scripts/recompute_connections.py`
4. Run: `python scripts/compute_importance.py`
5. Run: `python scripts/extract_biographies.py`
6. Start backend + frontend, verify Feed tab works
7. Delete unused tab files (EventTab.tsx, PersonTab.tsx, ThreadsTab.tsx, NetworkTab.tsx) after confirming
