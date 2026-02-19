# Session Log: 2026-02-19 Timeline Narratives System

## Session Info
- **Purpose**: Implement era-based narrative system with regional breakdown + curation/feedback
- **Plan**: Timeline narratives + curation system (period_narratives, entity_narratives, user_feedback)

## Changes Made

### Phase 1: Initial Implementation

#### Backend - Database (Alembic Migrations)
- `backend/alembic/versions/400_timeline_narratives.py` - NEW
  - Creates `period_narratives` table (AI-generated 50-year period overviews)
  - Creates `entity_narratives` table (AI-generated event/person narratives)
  - Creates `user_feedback` table (user curation reports)
- `backend/alembic/versions/401_add_region_to_narratives.py` - NEW
  - Adds `region` column for regional sub-narratives (europe, near_east, south_asia, east_asia, africa, americas)
  - Adds `event_count`, `person_count`, `top_events`, `top_persons` denormalized columns
- `backend/alembic/versions/402_add_quote_to_narratives.py` - NEW
  - Adds `quote` and `quote_source` columns for historical quotes per region

#### Backend - SQLAlchemy Models
- `backend/app/models/period_narrative.py` - NEW (with region, quote, denormalized fields)
- `backend/app/models/entity_narrative.py` - NEW
- `backend/app/models/user_feedback.py` - NEW
- `backend/app/models/__init__.py` - Modified (registered new models)

#### Backend - API Endpoints
- `backend/app/api/v1/timeline.py` - NEW (v2 with regional support)
  - `GET /api/v1/timeline/periods` - List periods with region_count, global headline
  - `GET /api/v1/timeline/periods/{period_start}` - Period detail with `regions[]` array + flat events/persons
  - `GET /api/v1/timeline/periods/{period_start}/events` - Period events
  - `GET /api/v1/timeline/periods/{period_start}/persons` - Period persons
  - `POST /api/v1/timeline/feedback` - Submit user feedback
  - Response models: PeriodSummary, RegionNarrative, PeriodDetail, FeedbackRequest
- `backend/app/api/v1/router.py` - Modified (registered timeline router)

### Phase 2: Regional Narrative Pipeline

#### Data Pipeline (permanent script)
- `backend/scripts/generate_narratives.py` - NEW (moved from poc/scripts)
  - Regional breakdown: classifies events/persons into 6 regions by lat/lng
  - Locationless events folded into top-scoring region (no overlapping "global" pseudo-region)
  - Per-region prompt generates 150-250 word narrative + headline + keywords + quote
  - Global overview synthesizes regional headlines into 100-150 word summary
  - JSONL checkpoint: `data/compact_export/era_narratives.jsonl`
  - `--apply` mode upserts into period_narratives with region, quote, top_entities
  - Cost: ~$0.003 per LLM call, ~$1-2 for full run (~585 calls)
- `poc/scripts/generate_era_narratives.py` - SUPERSEDED (v1, kept for reference)

### Phase 3: Frontend Regional UI

#### Frontend - Types & API
- `frontend/src/types/index.ts` - Modified
  - Added: PeriodSummary (with region_count), RegionNarrative, PeriodDetail (with regions[])
  - PeriodEvent, PeriodPerson unchanged
- `frontend/src/api/client.ts` - Modified (timelineApi namespace)

#### Frontend - Components
- `frontend/src/components/navigator/TimelineTab.tsx` - Rewritten
  - Fetches from /api/v1/timeline/periods
  - Groups by 6 eras, falls back to LAPLACE_ERAS
- `frontend/src/components/navigator/PeriodDetailPanel.tsx` - Rewritten (v2)
  - Global overview section (headline, narrative, defining moment)
  - **Regional cards** (expandable, sorted by activity):
    - Color-coded region tags (europe=cyan, near_east=orange, south_asia=green, etc.)
    - Headline, narrative, keywords
    - Historical quote with attribution (blockquote style)
    - Top events/persons chips
  - Flat event/person lists (backward compatible)
  - Feedback button
- `frontend/src/components/navigator/FeedbackModal.tsx` - NEW
- `frontend/src/components/navigator/navigator.css` - Modified (~400 lines total)
  - Added region card styles: .region-card, .region-card-header, .region-card-quote, etc.

### Docs Cleanup
- Moved to `docs/planning/completed/`: GPU_THERMAL_MANAGEMENT, 01_GLOBE_UX, 03_FEED_UX

## Results
- All 3 migrations applied successfully (400, 401, 402)
- Backend: 5 routes register, all imports work
- Frontend: `npx tsc --noEmit` passes with zero errors
- DB: 89 periods detected; test populated 7 entries (2 global + 5 regional for periods -600, -550)
- Pipeline test: 12 LLM calls for 2 periods, $0.04 cost, quality excellent
- Quotes working: Cyrus Cylinder (Near East), Chandogya Upanishad (South Asia)

## Architecture Notes
- Each period has 1 global overview (region=NULL) + N regional sub-narratives
- Regions classified by lat/lng bounding boxes (no overlap)
- Locationless events folded into highest-scoring region (avoids overlapping pseudo-regions)
- Pipeline is permanent (`backend/scripts/`), not one-off
- Frontend region cards are expandable accordion style
- Quote field optional (LLM only includes when a famous quote exists)

## Next Steps
- Run full pipeline: `cd backend && python scripts/generate_narratives.py` (~$1-2)
- Apply full results: `python scripts/generate_narratives.py --apply`
- Verify frontend with production data
- Consider: multilingual support (English main, then Korean/Japanese)
- Consider: Wikimedia Commons images for era illustrations
- Consider: namu.wiki style references for richer content
- Migrate remaining reusable poc/scripts/ to backend/scripts/
