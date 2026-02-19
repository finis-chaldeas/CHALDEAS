# Session Log: 2026-02-17 Person System Overhaul

## Session Info
- **Plan Checkpoint**: Person System Final Plan
- **Purpose**: Implement Person node slimming + details/names separation + flow API

## Tasks Completed

### 1. New Models Created
- `backend/app/models/person_detail.py` - PersonDetail (1:1 with Person)
- `backend/app/models/person_name.py` - PersonName (aliases, mirrors LocationName)
- `backend/app/models/location_detail.py` - LocationDetail (1:1 with Location)

### 2. Alembic Migration
- `backend/alembic/versions/301_person_system_overhaul.py`
  - Creates `person_details`, `location_details`, `person_names` tables
  - Migrates data from persons to person_details (biography, slug, image_url, etc.)
  - Migrates name_original to person_names (name_type='native')
  - Drops 28+ columns from persons table
  - Full downgrade support

### 3. Person Model Slimmed (44 columns -> 15)
- `backend/app/models/person.py` rewritten
- Kept: id, wikidata_id, name, name_ko, name_ja, birth_year, death_year, floruit_start, floruit_end, birthplace_id, deathplace_id, role, certainty, created_at, updated_at
- Added relationships: details (PersonDetail), names (PersonName[])

### 4. Schema Updated
- `backend/app/schemas/person.py` - PersonBase, Person, PersonDetail, PersonDetailInfo, PersonName, PersonFlow, FlowEvent, FlowLocation

### 5. Backend Services Updated
- `backend/app/services/person_service.py` - Removed is_light/connection_count filters, added get_person_flow(), eager loading details+names
- `backend/app/services/search_service.py` - Removed biography search, connection_count filters
- `backend/app/services/hybrid_search.py` - Removed biography from BM25 text fields

### 6. API Endpoints Updated
- `backend/app/api/v1/persons.py` - Added `/persons/{id}/flow` endpoint, removed category_id/include_orphans params
- `backend/app/api/v1/feed.py` - JOIN person_details for biography, removed is_light/connection_count
- `backend/app/api/v1/featured.py` - JOIN person_details for biography/image_url
- `backend/app/api/v1/servants.py` - Access biography via person.details
- `backend/app/api/v1_new/globe.py` - Removed is_light/mention_count references
- `backend/app/api/v1_new/stats.py` - Replaced enriched_by/mention_count with person_details/event_persons queries
- `backend/app/core/logos/actor.py` - Access biography via person.details

### 7. Frontend Updated
- `frontend/src/types/index.ts` - New Person interface (slim), PersonDetailInfo, PersonNameEntry, PersonFlow, FlowEvent
- `frontend/src/components/detail/PersonDetailView.tsx` - Biography from person.details
- `frontend/src/components/story/PersonStory.tsx` - Removed dead biography/image_url references

### 8. Models Registered
- `backend/app/models/__init__.py` - Added PersonDetail, PersonName, LocationDetail
- `backend/app/models/location.py` - Added details relationship

## Verification
- TypeScript: `npx tsc --noEmit` - PASS (0 errors)
- Python imports: All models, schemas, services, API modules import cleanly
- Alembic migration: Full upgrade + downgrade SQL

## Files Changed (Summary)
### New Files (4)
- backend/app/models/person_detail.py
- backend/app/models/person_name.py
- backend/app/models/location_detail.py
- backend/alembic/versions/301_person_system_overhaul.py

### Modified Files (16)
- backend/app/models/person.py (rewritten)
- backend/app/models/location.py (added details relationship)
- backend/app/models/__init__.py
- backend/app/schemas/person.py (rewritten)
- backend/app/services/person_service.py (rewritten)
- backend/app/services/search_service.py
- backend/app/services/hybrid_search.py
- backend/app/api/v1/persons.py (rewritten, +flow endpoint)
- backend/app/api/v1/feed.py
- backend/app/api/v1/featured.py
- backend/app/api/v1/servants.py
- backend/app/api/v1_new/globe.py
- backend/app/api/v1_new/stats.py
- backend/app/core/logos/actor.py
- frontend/src/types/index.ts
- frontend/src/components/detail/PersonDetailView.tsx (rewritten)
- frontend/src/components/story/PersonStory.tsx

### 9. Documentation Updated
All docs updated to reflect new Person/Location system:

- `docs/reference/DATABASE.md` — persons 테이블 15컬럼, person_details/person_names/location_details 추가, ER 다이어그램 갱신, V1 확장 섹션 갱신
- `docs/reference/API.md` — `/persons/{id}/flow` 엔드포인트 추가, person detail 응답 구조 갱신, relations/properties/sources 엔드포인트 추가
- `CLAUDE.md` — Key API Endpoints에 flow/relations/properties/sources/feed/featured 추가, 문서 참조 경로 갱신
- `docs/planning/FINAL_SCHEMA.md` — persons 테이블 슬림화 반영, person_details/person_names/location_details 테이블 추가

## Next Steps
- Run `python -m alembic upgrade head` on compact DB to apply migration
- Test `/persons/{id}/flow` API with real data
- Populate person_names with Wikidata aliases (Step 8 from plan)
