# Session Log: 2026-02-22 12:40

## Session Info
- **Plan Checkpoint**: Phase 1.7
- **Purpose**: Create reliable source fetching script for Phase 3 curation prep

## What Was Done

### Script Creation
- Created `poc/scripts/fetch_reliable_sources.py` - 5-step source acquisition script
  - `--step audit`: Reports source coverage gaps for top persons/events/locations
  - `--step wikipedia`: Fetches full Wikipedia articles via action=parse API
  - `--step wikisource`: Fetches primary source texts (speeches, letters, works)
  - `--step archive`: Fetches public domain texts from Internet Archive
  - `--step report`: Generates coverage report with Phase 3 readiness check
  - `--entity-type location`: Added location support (event_count as importance proxy)

### Execution Results

| Step | Target | Result |
|------|--------|--------|
| Wikipedia events | 50 | 1 new, 39 skipped (already had), 10 failed |
| Wikisource classical | 30 persons | 21 success |
| Wikisource ancient | 20 persons | 11 success |
| Wikisource medieval | 50 persons | 22 success |
| Wikisource early_modern | 50 persons | 35 success (70% - best rate) |
| Wikisource modern | 50 persons | 16 success |
| Wikisource all (top 500) | 500 persons | 80 new, 103 skipped, 317 failed |
| Internet Archive | 30 persons + 30 events | 20 persons, 4 events |
| **Wikipedia locations** | **200 locations** | **196 success, 4 failed** |

### V2 Scaled Execution (Wikisource search-based + Internet Archive)

| Step | Target | Result |
|------|--------|--------|
| Wikisource v2 events | 461 events | 389 success (84%), 72 failed |
| Wikisource v2 persons | 1000 persons | 727 success (73%), 115 skipped, 158 failed |
| Internet Archive events | 470 events | 47 success (10%), 423 failed |

### Final Source Counts (All Runs Combined)

| Source Type | Records | Total Chars |
|-------------|---------|-------------|
| Wikipedia | 158,602 | 2.3B |
| Wikisource | **4,889** | 192M |
| Internet Archive | **115** | 5.7M |

### Entity Coverage (Final)

| Entity | With Sources |
|--------|-------------|
| Persons with Wikisource | **842** (was 185) |
| Events with Wikisource | **424** (was 0) |
| Persons with Internet Archive | 20 |
| Events with Internet Archive | 51 |
| Locations with Wikipedia | 196 (was 0) |
| Events with Wikipedia | 20,992 |

## Key Patterns Used
- psycopg2 direct connection (matching existing scripts)
- JSONL checkpoint files in `poc/data/source_fetch/`
- Rate limiting: 1 req/sec (Wikimedia guideline)
- HTML-to-text: stdlib HTMLParser (no external deps)
- Dedup by URL before insert
- User-Agent: `ChaldeasBot/1.0`
- Location importance proxy: event_count from event_locations table

## DB Schema Notes
- Actual `sources` table uses `source_type` (not `type` or `archive_type`)
- `content_raw` is NOT NULL in DB (required field)
- `wikidata_id` has UNIQUE constraint on sources
- Existing wikipedia sources (158K) don't use wikidata_id
- New sources use `source_type` values: 'wikipedia', 'wikisource', 'internet_archive'
- `location_sources` table exists: (location_id, source_id, page_reference)

## User Feedback
- Wikipedia alone is NOT sufficient for curation - "원어가 없으면 아무런 의미가 없잖아"
- Wikisource primary texts are what matter for quality curation
- Don't use per-era quotas, focus on truly important figures globally

## Internet Archive Fix
- Original query `lending___status:is_lendable` found only copyrighted lending library
- Fixed: `-lending___status:is_lendable AND date:[1800-01-01 TO 1930-12-31] AND format:(DjVuTXT OR "Text PDF")`
- Added `sort[]: downloads desc` for better results

## Result
- SUCCESS: Script created, V2 search-based approach implemented, full-scale execution completed
- **4,889 Wikisource sources** for 842 persons + 424 events
- **115 Internet Archive sources** for 20 persons + 51 events
- 196 locations now have Wikipedia sources (was 0)
- Phase 3 readiness confirmed — sufficient primary source coverage for top entities

## Next Steps
1. Track 1: Backend API exposure (entity_narratives → API responses)
2. Track 2: Archive → Compact DB sync
3. Track 3: Frontend V4 narrative display
4. Trilingual support: Add narrative_ja columns to entity_narratives + period_narratives
