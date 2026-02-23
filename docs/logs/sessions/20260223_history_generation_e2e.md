# Session Log: 2026-02-23 12:00

## Session Info
- **Purpose**: History auto-generation + E2E test
- **Plan**: HISTORY_SYSTEM_PLAN.md (Step 1-4)

## Completed Work

### 1. Seed Test Data (`poc/scripts/seed_test_histories.py`)
- Created script that looks up real entity IDs from compact DB
- Inserts 3 hardcoded sample histories with `[Name](entity:type:id)` tagging:
  - "The Fall of the Roman Republic: Caesar's Final Act" (essay, 7 entities)
  - "Napoleon and the Reshaping of Europe" (biography, 4 entities)
  - "Genghis Khan and the Mongol Conquest" (era_overview, 3 entities)
- Uses `author_name='seed_test'` for easy cleanup (`--clean` flag)
- Automatically parses body for mentioned entities + inserts featured/location/mentioned roles

### 2. API Verification
All endpoints tested successfully:
- `GET /api/v1/histories` - Returns all 8 histories (3 seed + 5 auto)
- `GET /api/v1/histories/{id}` - Full detail with entity list
- `GET /api/v1/persons/{id}/histories` - Reverse-lookup working
- `GET /api/v1/events/{id}/histories` - Reverse-lookup working

### 3. GPT-5.1 Auto-Generation (`poc/scripts/generate_histories.py`)
- Two generation strategies:
  - **Cluster mode**: Parent events with >= 3 children → essay/era_overview
  - **Person mode**: High-importance persons with >= 3 events → biography
- Features: JSONL checkpoint, `--dry-run`, `--skip-existing`, `--limit N`
- Fixed: events table doesn't have `description` column directly (use `event_details` JOIN)
- Fixed: `DISTINCT` + `ORDER BY` PostgreSQL constraint (use subquery instead)
- Generated successfully:
  - 3 cluster histories (American Civil War, WWII, WWI) ~56s, ~$0.03
  - 2 person biographies (Julius Caesar, Muhammad) ~28s, ~$0.02
  - Entity tagging in body works correctly (25 entities in WWII essay)

### 4. Files Changed
| File | Action |
|------|--------|
| `poc/scripts/seed_test_histories.py` | NEW |
| `poc/scripts/generate_histories.py` | NEW |
| `poc/data/curation/histories_checkpoint.jsonl` | NEW (auto-created) |

### 5. DB State
- 8 histories total in compact DB
- history_entities correctly populated with featured/mentioned/location roles

## Issues Encountered
1. Backend server needed manual restart to pick up new histories router (not auto-reloaded)
2. `events.description` doesn't exist - it's in `event_details.description` (compact DB schema)
3. `SELECT DISTINCT ... ORDER BY` PostgreSQL constraint required subquery pattern

## Results
- All 4 plan steps completed successfully
- Total LLM cost: ~$0.05 for 5 histories
- Both scripts follow existing `curate_with_llm.py` patterns

## Next Steps
- Run `generate_histories.py` with larger limits for production data
- Frontend verification (Navigator → History tab → viewer → tag clicks)
- Consider adding `--mode both` for combined generation
