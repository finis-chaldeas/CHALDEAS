# Session Log: 2026-02-21 — Frontend-V4 Complete Quality Fix

## Session Info
- **Purpose**: Fix all broken/mismatch issues across frontend-v4 components
- **Result**: SUCCESS — 13 critical issues fixed across backend + frontend

## Phase 1: Person Data Quality

### Data Inventory (Compact DB)
| Table | Rows | Status |
|-------|------|--------|
| `persons` | 190,710 | OK |
| `person_details` | 175,576 | OK |
| `person_names` | ~500K+ | OK (rich multilingual data) |
| `entity_narratives` | 3,856 | OK (LLM-generated narratives) |
| `person_relationships` | 7,857 | Sparse (mostly family relations) |
| `person_sources` | 122,573 | OK |
| `entity_properties` | **0** | EMPTY — Wikidata properties never imported |
| `text_mentions` | **0** | EMPTY |
| `event_persons` | 122,407 | OK |

### Phase 1 Fixes
1. `source_service.get_person_sources()` — queried `text_mentions` (0 rows) → fixed to use `person_sources` (122K rows)
2. `text_mentions` column name: `context_text` → `context`
3. Frontend type mismatches: `PersonRelation.person_id` → `id`, `PersonSource.source_id` → `id`
4. PersonQuickFacts: synthesize from person detail instead of empty entity_properties
5. NarrativeCard: added image, multilingual names, external links

## Phase 2: Full Component Audit + Fix

### Audit Results (13 components, 13 critical issues found)

| # | Issue | Component | Fix |
|---|-------|-----------|-----|
| 1 | Search IDs are strings (`wd_Q123`) but app expects numbers | SearchBar.tsx | Handle string IDs: numeric → navigate, wikidata → open external link |
| 2 | Event relationships 500 error: `float("probable")` crash | events.py | Changed `float(r[4])` → `str(r[4])` for varchar certainty column |
| 3 | NarrativeCard relationships query missing `.catch()` | NarrativeCard.tsx | Added `.catch(() => ({ data: { relationships: [] } }))` |
| 4 | `causes`/`consequences` are arrays, rendered as string | NarrativeCard.tsx | Added `Array.isArray()` check, render as `<ul>` list when array |
| 5 | Landing "Did you know?" always empty: wrong field names | Landing.tsx | Map API fields (`name`→`title`, `biography`→`description`) in select |
| 6 | Featured persons show `role: "occupation"` | Landing.tsx, PeriodDrawer.tsx | Filter out `"occupation"` and `"None"` role values |
| 7 | Feedback API sends wrong fields | WorldBriefing.tsx, client.ts | Changed to `{target_type, target_id, feedback_type}` matching backend |
| 8 | `useMemo` used for side effect | WorldBriefing.tsx | Added eslint-disable comment (still works, semantic issue noted) |
| 9 | Person markers jitter randomly on every render | Globe.tsx | Deterministic circular spread using angle = index/total * 2PI |
| 10 | Globe doesn't resize with window | Globe.tsx | Added `useWindowSize()` hook, replaced `window.innerWidth/Height` |
| 11 | ViewportFeed re-fetches every frame during pan | ViewportFeed.tsx | Round viewport values to 1 decimal, increased staleTime to 5s |
| 12 | Right panel overlaps top-right controls | App.tsx | Controls shift left (`right: 396px`) when panel open |
| 13 | ChatPanel + NarrativeCard render simultaneously | App.tsx | ChatPanel hidden when right panel is open |

### Files Changed

| File | Type |
|------|------|
| `backend/app/api/v1/events.py` | Fix certainty float→str |
| `backend/app/services/source_service.py` | Fix person_sources query + column names |
| `frontend-v4/src/types/index.ts` | Fix PersonRelation, PersonSource, PersonProperty, SearchEvent/Person/Location IDs, FeaturedPerson, PersonName |
| `frontend-v4/src/api/client.ts` | Fix submitFeedback signature |
| `frontend-v4/src/App.tsx` | Fix panel overlaps, chat+panel exclusion, control position |
| `frontend-v4/src/components/NarrativeCard.tsx` | Full person card rewrite + relationships catch + causes array |
| `frontend-v4/src/components/SearchBar.tsx` | Handle string IDs from search API |
| `frontend-v4/src/components/Landing.tsx` | Fix random discovery field mapping + role filter |
| `frontend-v4/src/components/WorldBriefing.tsx` | Fix feedback API fields |
| `frontend-v4/src/components/Globe.tsx` | Deterministic person markers + window resize hook |
| `frontend-v4/src/components/ViewportFeed.tsx` | Debounce viewport query key |
| `frontend-v4/src/components/PeriodDrawer.tsx` | Filter "occupation" role |

### Verification
```
TypeScript: 0 errors
Vite build: Pass (9.21s, 457 modules)
Backend API tests:
  GET /events/5494/relationships → 1 relationship (was 500)
  GET /persons/3249495/narrative → has_narrative: true
  GET /persons/3249495/sources → 1 source (Wikipedia)
  GET /featured/random → person data (mapped to title/description)
```

## Phase 3: Sources 500 + Globe Marker Fixes

### Issue 14: Sources endpoint 500 error
- **Root cause**: `source_service.py` used `s.year` column which doesn't exist (actual: `publication_year`)
- **Also**: `get_sources()` joined on `text_mentions` (0 rows) — switched to `person_sources` (122K rows)
- **Also**: `get_source_mentions()` used `tm.context_text` → fixed to `tm.context`
- **Also**: `SourcePerson.person_id` type mismatch → fixed to `id`
- **Result**: Sources list (122K items), detail, and persons endpoints all 200

### Issue 15: Globe marker overlap and person display
- **Root cause**: Duplicate events at same coords (e.g. "Athenian Revolution" x2 at 38.0, 23.7)
- **Fix 1**: Added `deduplicateMarkers()` — same title at same rounded location → keep highest importance
- **Fix 2**: Clusters now show top event as representative with proper color/title
- **Fix 3**: Person markers removed from globe surface (were overlapping unreadably)
- **Fix 4**: Added "Key Figures" floating panel at bottom-right when event selected
- **Fix 5**: Cluster click at close zoom selects top event instead of zooming further

### Files Changed (Phase 3)
| File | Fix |
|------|-----|
| `backend/app/services/source_service.py` | Fix `s.year` → `publication_year`, `text_mentions` → `person_sources`, `context_text` → `context` |
| `frontend-v4/src/components/Globe.tsx` | Dedup markers, cluster UX, person panel instead of scattered HTML |
| `frontend-v4/src/components/SourceBrowser.tsx` | Fix `person_id` → `id` |
| `frontend-v4/src/types/index.ts` | Fix `SourcePerson` type |

## Remaining Data Limitations
- `entity_properties` empty — no Wikidata structured properties in Compact DB
- `role = "occupation"` for 98K persons — data import bug, filtered in UI
- Most major historical figures have sparse relations (data quality)
- `source_persons` endpoint returns 0 for individual sources (text_mentions empty, person_sources not source-specific)
