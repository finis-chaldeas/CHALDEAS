# 2026-03-05: Academic Paper Integration into Shift & Article Generation

## Purpose
Integrate OpenAlex academic paper abstracts into `create_shift.py --enhance` and `create_portal_article.py --generate` GPT prompts to improve narrative quality and factual grounding.

## Changes

### New File
- **`backend/scripts/paper_utils.py`** — Shared utility for loading/formatting academic papers
  - `load_paper_index()`: Loads JSON files → `{event_id: [paper, ...]}` dict (module-cached)
  - `get_papers_for_events()`: Batch lookup by event IDs
  - `format_papers_for_prompt()`: Formats papers as numbered entries for GPT prompts
  - `format_papers_as_sources()`: Formats papers as citation strings for sources field

### Modified Files
- **`backend/scripts/create_shift.py`**
  - Added `paper_utils` import
  - Extended `CONTENT_SYSTEM_PROMPT` with academic sources instructions
  - Extended `CONTENT_USER_TEMPLATE` with `{academic_papers}` field
  - `cmd_enhance()`: Loads paper index before loop, injects per-page paper context
  - Log output shows `papers=N` when papers are used

- **`backend/scripts/create_portal_article.py`**
  - Added `paper_utils` import + `_get_db_session()`
  - Extended `OUTLINE_USER_TEMPLATE` with `{academic_papers}` section
  - Extended `SECTION_USER_TEMPLATE` with `{academic_papers}` section
  - `cmd_generate()`: Searches topic-related events in DB, gathers papers, injects into both outline and section prompts
  - Auto-merges paper citations into `sources` field after outline generation

## Data
- Source: `data/compact_export/academic_papers/events_imp{3,4,5}_*.json`
- Coverage: 1,420 events with B+ grade papers (8,286 total papers)
- Latest imp3 file: `events_imp3_20260305_192616.json` (4,231 events, 9,218 papers)

## Validation
- `load_paper_index()`: 1,420 events loaded correctly
- Marathon topic search: Found 2 papers (Cambridge Ancient History, Shield Signal paper)
- Both scripts compile and import successfully

## Next Steps
- Run actual `--enhance` on a shift to verify GPT output quality with papers
- Run `--generate` on an article topic to verify sources integration
- Consider expanding to person-based paper lookup (not just event-based)
