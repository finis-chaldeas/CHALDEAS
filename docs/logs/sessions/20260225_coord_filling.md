# Session Log: 2026-02-25 - Coordinate Filling for imp 3+ Events

## Session Info
- **Purpose**: Fill missing coordinates for 1,237 imp 3+ events to achieve globe display readiness
- **Previous Session**: Narrative generation + translation for imp 3+ events ($39.55)

## Work Done

### 1. Analysis
- Found 1,237 imp 3+ events without `primary_location_id`
- All had `wikidata_id` but Wikidata P625 coordinates unavailable (these events were already filtered by previous enrichment passes)
- All had descriptions from narrative generation
- Existing `enrich_event_descriptions.py --coords-only` (Wikidata API approach) wouldn't work for these

### 2. Created `backend/scripts/fill_event_coords.py`
- LLM-based coordinate extraction from event title + description
- Multi-model support: GPT-5-mini (cheap) and GPT-5.1-chat (better accuracy)
- ThreadPoolExecutor parallel processing (10-15 workers)
- Checkpoint/resume support
- Matches extracted locations against 17,723 existing locations (within 0.3 degree threshold)
- Creates new locations when no nearby match exists

### 3. Execution (4 passes)

| Pass | Model | Linked | New Locs | Cost | Time |
|------|-------|--------|----------|------|------|
| 1st | gpt-5-mini | 759 | 17 | $0.48 | 8 min |
| 2nd (retry) | gpt-5-mini | 96 | 9 | $0.07 | 6 min |
| 3rd (gpt-5.1) | gpt-5.1-chat | 271 | 56 | $0.05 | 1 min |
| 4th (final) | gpt-5.1-chat | 7 | 2 | $0.001 | 0.1 min |
| **Total** | | **1,133** | **84** | **$0.60** | **15 min** |

### 4. Issues Fixed
- GPT-5-mini `response_format=json_object` caused empty responses for ~30% of events
- GPT-5.1-chat response key mismatch (`lat`/`lng` vs `latitude`/`longitude`)
- GPT-5.1-chat malformed JSON numbers (e.g., `39.774"` instead of `39.774`)

## Results
- **Before**: 4,654/5,891 (79.0%) coordinate coverage
- **After**: 5,795/5,891 (98.4%) coordinate coverage
- **Remaining 96**: Genuinely abstract concepts with no geographic location (geological epochs, legal concepts, social phenomena)

## Files Changed
- `backend/scripts/fill_event_coords.py` (NEW)
- `data/compact_export/coords_checkpoint.jsonl` (checkpoint data)
- DB: 1,133 events updated with `primary_location_id`, 84 new locations created

## Cost
- **Total session cost**: $0.60 (coordinate filling only)
- **Cumulative project cost this sprint**: ~$40.15 (narratives $39.55 + coords $0.60)

## Next Steps
- Deploy to production (user requested)
- Hide incomplete features for public launch
