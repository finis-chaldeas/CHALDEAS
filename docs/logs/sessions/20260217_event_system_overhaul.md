# Session Log: 2026-02-17 - Event System Overhaul

## Session Info
- **Plan Checkpoint**: Event System Overhaul (Migration 302)
- **Purpose**: Slim events table from ~41 columns to 21, create event_details (1:1), add aggregate location inheritance

## Changes Made

### New Files
- `backend/app/models/event_detail.py` - EventDetail model (1:1 with Event)
- `backend/alembic/versions/302_event_system_overhaul.py` - Migration: create event_details, migrate data, drop columns

### Modified Files

**Backend - Models**
- `backend/app/models/event.py` - Slimmed to 21 columns, added `details` relationship
- `backend/app/models/__init__.py` - Registered EventDetail

**Backend - Schemas**
- `backend/app/schemas/event.py` - Removed connection_count/display fields from EventBase, added EventDetailInfo schema

**Backend - Services**
- `backend/app/services/event_service.py` - Removed is_light/connection_count filters, removed get_events_by_zoom, added get_event_locations() with recursive CTE for aggregate location inheritance
- `backend/app/services/search_service.py` - Event.description.ilike -> JOIN event_details
- `backend/app/services/hybrid_search.py` - No changes needed (uses in-memory BM25, not DB columns)

**Backend - APIs**
- `backend/app/api/v1/events.py` - Removed slug/description/connection_count/is_light/display fields from event_to_dict, added details nesting, backward-compat top-level description/wikipedia_url/image_url, added /events/{id}/locations endpoint
- `backend/app/api/v1/feed.py` - SQL: e.description -> ed.description via LEFT JOIN event_details
- `backend/app/api/v1/story.py` - SQL: e.description -> ed.description via LEFT JOIN event_details (2 queries)
- `backend/app/api/v1_new/globe.py` - SQL: e.description -> ed.description via LEFT JOIN event_details (2 queries)
- `backend/app/api/v1_new/stats.py` - enriched_by -> event_details description_source for enrichment stats
- `backend/app/api/v1_new/explore.py` - SQL: events.slug -> JOIN event_details, added table alias `e.` prefix

**Backend - Core**
- `backend/app/core/logos/actor.py` - event.description -> event.details.description

**Backend - Scripts**
- `backend/scripts/recompute_connections.py` - Marked as DEPRECATED (connection_count removed)

**Frontend**
- `frontend/src/types/index.ts` - Added EventDetailInfo interface, updated Event interface with hierarchy fields + details
- `frontend/src/components/detail/EventDetailPanel.tsx` - description_source -> event.details.description_source
- `frontend/src/components/navigator/EventTab.tsx` - Removed 'connections' sort option, removed connection_count display

## Verification
- Event model: 21 columns confirmed (id, wikidata_id, title, title_ko, title_ja, date_start, date_end, date_precision, temporal_scale, importance, certainty, category_id, primary_location_id, period_id, parent_event_id, is_aggregate, hierarchy_level, aggregate_type, parent_status, created_at, updated_at)
- EventDetail model: 18 columns confirmed
- TypeScript: `npx tsc --noEmit` passes with zero errors
- Python imports: All models load correctly

## Columns Moved to event_details
slug, description, description_ko, description_ja, description_source, description_source_url, image_url, wikipedia_url, date_start_month, date_start_day, date_end_month, date_end_day, source_reliability, default_collapsed, min_zoom_level

## Columns Deleted (computed/pipeline)
connection_count, is_light, enriched_by, enriched_at, enrichment_version

## Database Migration (302_event_system @ head)
- Migration 300 → 301 → 302 실행 완료
- Migration 300/302를 idempotent하게 수정 (compact DB 혼합 상태 대응)
- person_details에 persons.description → biography 수동 이전 (156,417건)
- 최종 상태: events 21컬럼, persons 18컬럼(레거시 3), locations 11컬럼

## Documentation (전면 재작성)
- `docs/reference/DATABASE.md` - 실측 DB 기준 전면 재작성: ER diagram, 모든 테이블 컬럼 수 실측 반영, Compact DB 데이터 현황 테이블, 레거시 컬럼 명시, 마이그레이션 체인
- `docs/reference/API.md` - Events API 응답 형식 (details nesting + hierarchy), /events/{id}/locations 신규 엔드포인트, Feed API 추가, 구현 파일 목록 업데이트 (event_details JOIN 명시)
- `CLAUDE.md` - Key API Endpoints 갱신 (events detail/locations, feed JOINs)

## Territory System Pipeline (Phase A, B, C)

### Phase A: Seed Territories (완료)
- `poc/scripts/seed_territories.py` 실행
- 80개 큐레이션 territories + SPARQL 84개 = **164개 territories** 시드
- 고대(이집트, 아시리아, 아케메네스) ~ 현대(미국, 한국, 이스라엘) 망라

### Phase B: P17 Temporal Qualifiers (완료)
- 1.6TB 덤프 스캔 → 11시간 예상으로 **Wikidata API 방식으로 전환**
- `poc/scripts/extract_p17_via_api.py` — wbgetentities API (50 QIDs/batch × 355 batches)
- **19분**에 17,584/17,723 locations P17 데이터 수집 완료 (99.2%)
- 1,859개에 temporal qualifiers (시대별 국가 변화)
- `poc/scripts/import_territory_locations.py`로 import → 27,560개 territory_location 추가

### Phase C: Event-based + Modern Country Mapping (완료)
- `poc/scripts/map_territories_from_events.py` 실행
- Phase C-1: 이벤트 기반 매핑 → **796개** territory_location 추가
- Phase C-2: 현대국가 매핑 → **7,607개** territory_location 추가

### Locations 관련 기타
- `locations.country` 컬럼 추가 (reverse geocoding으로 17,723개 매핑 완료)
- locations 12컬럼 (country 포함)
- Missing modern countries 50개 추가 (Azerbaijan, Spain, Poland, Ukraine 등)

### 최종 Territory Status
| 지표 | 값 |
|------|-----|
| Territories | 214 |
| Territory_locations | 35,963 |
| Unique locations mapped | 14,738 / 17,723 (83.2%) |
| Avg territories per location | 2.4 |
| With temporal dates | 12,487 (34.7%) |
| Top multi-territory | Tartu (11), Izmail (10), Bely (10) |

## Next Steps
- Populate event_details for events that don't have one yet
- Populate location_details from archive DB (descriptions)
- Clean up Pheasant Island anomaly (483 territories — data issue)
