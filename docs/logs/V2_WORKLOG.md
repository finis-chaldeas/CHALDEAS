# CHALDEAS V2 Work Log

This log tracks all work done for the CHALDEAS V2 implementation.

## Phase 1: Base Setup (Day 1-3)

### CP-1.1: V2 Schema Creation
**Started**: 2026-01-31 (Current session)
**Status**: COMPLETED

**Work Done**:
1. Created Alembic migration `100_create_v2_schema.py`
2. Created 11 new V2 tables:
   - `events_v2` - Enhanced events with vector attributes
   - `clusters` - Event groupings
   - `cluster_events` - M2M cluster-event association
   - `event_relations_v2` - Enhanced relations with Wikidata properties
   - `person_event_roles` - Role-based person-event connections
   - `historicity_sources` - Evidence for historical verification
   - `fgo_servants` - FGO servant data
   - `fgo_history_comparison` - Historical vs FGO comparison
   - `event_completeness` - Quality tracking
   - `fill_queue` - Work queue for data filling
   - `work_logs` - Checkpoint logging

3. Created SQLAlchemy models in `backend/app/models/v2/`:
   - `event_v2.py`
   - `cluster.py`
   - `relations.py`
   - `historicity.py`
   - `fgo.py`
   - `quality.py`
   - `work_log.py`

4. Created `system_completeness` view for tracking overall progress

**Verification**:
- `alembic upgrade head` - SUCCESS
- All 11 tables verified present in database

---

### CP-1.2: Automatic Logging System
**Started**: 2026-01-31
**Status**: COMPLETED

**Work Done**:
1. Created `poc/scripts/v2/work_logger.py` - WorkLogger context manager
2. Features:
   - Automatic start/end time tracking
   - Records processed/created/updated stats
   - LLM tier call tracking with cost estimation
   - Notes support
   - Work summary function

**Usage Example**:
```python
from work_logger import WorkLogger

with WorkLogger('CP-1.3', 'Migrate data to V2') as log:
    # Do work
    log.record_progress(processed=100, created=50)
    log.record_llm_call(tier=2)
    log.add_note("Migrated events with wikidata_id")
```

---

### CP-1.3: Data Migration to V2
**Started**: 2026-01-31
**Status**: COMPLETED

**Work Done**:
1. Created `poc/scripts/v2/migrate_to_v2.py` - Migration script
2. Migrated quality events (with wikidata_id): **4,055 events**
   - Note: 4,825 V0 events had wikidata_id, 770 were duplicates
   - Mapped certainty values: high->fact, medium->probable, low->legendary
3. Migrated event relationships: **9,062 relationships**
4. Migrated person-event roles: **318,370 roles**
5. Created event completeness records: **4,055 records**

**V2 System Status After Migration**:
- Events in V2: 4,055
- Events with Wikidata ID: 4,055 (100%)
- Events with description: 949 (23%)
- Event relations: 9,062
- Person-event roles: 318,370
- Average completeness score: 45.3
- Stub events (score < 30): 875

---

## Phase 2: LLM Tier System (Day 4-6)

### CP-2.1: Local LLM Benchmark
**Started**: 2026-01-31
**Status**: COMPLETED

**Work Done**:
1. Created `poc/scripts/benchmark/create_golden_dataset.py`
2. Created `poc/scripts/benchmark/local_llm_benchmark.py`
3. Created `poc/scripts/benchmark/run_all_benchmarks.py` - Multi-model benchmark
4. Generated golden dataset with **93 samples**:
   - Entity extraction: 34 samples
   - Nature classification: 26 samples
   - Date parsing: 33 samples
5. **Ran actual benchmark on 5 local models** (2026-02-01)

**Benchmark Results (RTX 3060 6GB VRAM)**:

| Model | Entity F1 | Nature Acc | Date Acc | Overall | Time |
|-------|-----------|------------|----------|---------|------|
| phi3:mini | 6.5% | 65.4% | 12.6% | 22.6% | 7분 |
| mistral:7b-instruct-q4_0 | 0.5% | **84.6%** | 47.5% | 33.3% | 7분 |
| llama3.1:8b-instruct-q4_0 | 1.8% | 80.8% | 40.2% | 29.0% | 9분 |
| qwen3:8b | 0.0% | 69.2% | 46.5% | 34.4% | 51분 |
| **gemma2:9b-instruct-q4_0** | 4.4% | 80.8% | **70.5%** | **43.0%** | 16분 |

**Best Models by Task**:
- **Entity Extraction**: phi3:mini (6.5%) - 전체적으로 실패 수준
- **Nature Classification**: mistral:7b (84.6%)
- **Date Parsing**: gemma2:9b (70.5%)
- **Overall Best**: gemma2:9b (43.0%)

**Key Findings**:
1. **Entity extraction needs API escalation** - All local models < 7%
2. **Nature classification works well locally** - mistral achieves 84.6%
3. **Date parsing is strong with gemma2** - 70.5% accuracy
4. **qwen3 thinking mode is too slow** - 51 min vs 7-16 min others
5. **gemma2:9b is the best overall local model**

**Recommended Configuration for TieredLLM**:
```python
TASK_DEFAULTS = {
    'entity_extraction': (LLMTier.MINI, 0.7),  # Must escalate to API
    'nature_classification': (LLMTier.LOCAL, 0.8),  # mistral locally
    'date_parsing': (LLMTier.LOCAL, 0.7),  # gemma2 locally
    'complex_analysis': (LLMTier.ADVANCED, 0.5),  # API required
}
```

**Result Files**:
- `poc/data/benchmark/BENCHMARK_REPORT_20260201_020315.md`
- `poc/data/benchmark/benchmark_*.json` (5 individual model results)

---

### CP-2.2: 3-Tier LLM Pipeline
**Started**: 2026-01-31
**Status**: COMPLETED

**Work Done**:
1. Created `poc/scripts/v2/tiered_llm.py`
2. Features:
   - Automatic tier escalation (T1 -> T2 -> T3)
   - Confidence-based escalation
   - Response caching
   - Task-specific configurations
   - Batch processing support

**Tier Configuration**:
| Tier | Model | Cost/1M tokens | Use Case |
|------|-------|----------------|----------|
| T1 (LOCAL) | llama3.1:8b | $0 | Simple extraction, parsing |
| T2 (MINI) | gpt-5-mini | $0.25 | Moderate complexity |
| T3 (ADVANCED) | gpt-5.1-chat | $1.25 | Complex reasoning |

---

### CP-2.3: Cost Tracking System
**Started**: 2026-01-31
**Status**: COMPLETED

**Work Done**:
1. Created `poc/scripts/v2/cost_tracker.py`
2. Features:
   - Real-time cost tracking per tier
   - Budget warnings at 80%/95%
   - Cost estimation before running tasks
   - Session and historical cost reports
   - Integration with work_logs table

**Usage**:
```python
from cost_tracker import CostTracker, CostEstimator

# Track costs
tracker = CostTracker(budget=Decimal('300.00'))
tracker.record_call(LLMTier.MINI, tokens=500)
tracker.print_report()

# Estimate before running
CostEstimator.print_estimate({
    'entity_extraction': {'tier': LLMTier.LOCAL, 'count': 1000}
})
```

---

## Cost Tracking

| Checkpoint | LLM Tier 1 | LLM Tier 2 | LLM Tier 3 | Est. Cost |
|------------|------------|------------|------------|-----------|
| CP-1.1 | 0 | 0 | 0 | $0.00 |
| CP-1.2 | 0 | 0 | 0 | $0.00 |
| CP-1.3 | 0 | 0 | 0 | $0.00 |
| CP-2.1 | 0 | 0 | 0 | $0.00 |
| CP-2.2 | 0 | 0 | 0 | $0.00 |
| CP-2.3 | 0 | 0 | 0 | $0.00 |
| **Total** | 0 | 0 | 0 | **$0.00** |

---

## Notes

- All V2 tables are **new tables**, not modifications of V0/V1
- V0/V1 remain fully operational
- Data can be migrated from V0 to V2 via `v0_event_id` foreign key
- **Phase 1-2 완료**: 비용 $0 (LLM 호출 없음)
- **Phase 3부터 비용 발생**: Wikidata 임포트, 계층 구축 등

---

## Phase 3: Data Construction (Day 7-12)

### CP-3.1: Wikidata Anchor Events Import
**Started**: 2026-02-01
**Status**: IN PROGRESS

**Work Done**:

#### 3.1.1 Event Type Classifier System
1. Created `poc/scripts/wikidata/event_type_mapping.json`
   - **70 mapped event types** across 12 categories:
     - `military`: battle, naval_battle, land_battle, war, civil_war, religious_war, military_conflict, military_operation, siege, skirmish, campaign, military_exercise, aerial_battle, massacre
     - `political`: treaty, peace_treaty, convention, rebellion, revolution, coup, coronation, assassination, election, abdication, funeral, demonstration, protest
     - `dynasty`: dynasty, empire, historical_country, caliphate, principality
     - `religious`: synod, crusade, religious_movement, religion, reformation, religious_text, witchcraft_trial
     - `cultural`: art_movement, cultural_movement, literary_movement, music_genre, art
     - `intellectual`: philosophical_movement, school_of_thought, ideology, academic_discipline, entity
     - `scientific`: discovery, invention, expedition, exploration
     - `economic`: economic_crisis, famine, plague
     - `natural`: epidemic, earthquake, flood, volcanic_eruption
     - `social`: migration, trial, social_movement
     - `mythological`: mythology, mythological_figure, legend
     - `period`: historical_period, era, age, century
   - `_exclude` section for non-historical types (sporting events, etc.)

2. Created `poc/scripts/wikidata/event_type_classifier.py`
   - **EventTypeClassifier** class with:
     - QID → (category, nature) lookup
     - Unknown type logging to `unknown_event_types.json`
     - Automatic mapping addition support
     - Statistics output
   - Singleton pattern via `get_classifier()`
   - Unknown types logged incrementally for review

3. Integrated classifier into `import_wikidata_events.py`
   - Events now have `category` and `nature` fields
   - Excluded types are skipped automatically
   - Unknown type count tracked in stats

#### 3.1.2 UK History Import Test
**Test Result**: SUCCESS

```
Region: United Kingdom
Events: 283 unique events
Timeline: 55 BCE (Caesar) ~ 2021 CE (Glasgow Climate Pact)
Unknown types: 0 (all classified)

Categories found:
- military/battle: 100+ events
- military/siege: 100+ events
- military/war: 28 events
- military/massacre: 20 events
- politica/treaty: 40+ events
- politica/rebellio: 28 events
- period/historic: 9 events
- dynasty/dynasty: 2 events
```

**Key Events Verified**:
- 55 BCE: Caesar's invasions of Britain
- 1066: Battle of Hastings
- 1215: Magna Carta (if treaty included)
- 1314: Battle of Bannockburn
- 1381: Peasants' Revolt
- 1485: Battle of Bosworth Field
- 1642: English Civil War
- 1746: Jacobite rising / Culloden
- 1982: Falklands War

**Files Created**:
- `poc/scripts/wikidata/event_type_mapping.json`
- `poc/scripts/wikidata/event_type_classifier.py`
- `poc/scripts/wikidata/import_wikidata_events.py` (updated)
- `poc/data/wikidata/events_uk_*.json` (test outputs)

#### 3.1.3 Global Import Execution
**Date**: 2026-02-01
**Status**: COMPLETED

**Import Statistics**:
```
Events Fetched:    23,429
Events Inserted:    9,306
Events Updated:     1,710
Events Skipped:     9,742 (no date)
Unknown Types:          0
```

**Database After Import**:
```
Total Events:           56,567
Events with QID:        14,131 (25%)
New Imports (confirmed): 9,306 (80% with description)

Era Distribution:
  Ancient (< 500 BCE):     264
  Classical (500BCE-500):   979
  Medieval (500-1500):    2,282
  Early Modern (1500-1800): 3,123
  Modern (1800-2000):     6,390
  Contemporary (2000+):   1,093
```

**Verification**:
- API: Working ✓
- Search: Working ✓
- Data Quality: 80% with descriptions ✓

**Next Steps**:
1. Import connected persons (P710 participants)
2. Build event hierarchy (P361 part of)
3. Import locations (P276)
4. Create clusters

---

## Next Steps (Phase 3 continued)

| Checkpoint | 작업 | 예상 비용 | Status |
|------------|------|----------|--------|
| CP-3.1 | Wikidata 앵커 이벤트 임포트 | **$0** | IN PROGRESS |
| CP-3.2 | P361 계층 구조 구축 | $0-2 | - |
| CP-3.3 | 인물-이벤트 연결 강화 | $0-5 | - |
| CP-3.4 | 클러스터 자동 생성 | $5-10 | - |
| CP-3.5 | FGO 서번트 연동 | $0-2 | - |

**Note**: Wikidata import uses pre-mapped classification (no LLM needed!)
- P31 (instance of) → category/nature via mapping file
- Unknown types logged for manual review
- Expected cost: **$0** for basic import

---

## Files Created

### Phase 1
- `backend/alembic/versions/100_create_v2_schema.py`
- `backend/app/models/v2/*.py` (7 files)
- `poc/scripts/v2/work_logger.py`
- `poc/scripts/v2/migrate_to_v2.py`

### Phase 2
- `poc/scripts/benchmark/create_golden_dataset.py`
- `poc/scripts/benchmark/local_llm_benchmark.py`
- `poc/scripts/benchmark/run_all_benchmarks.py`
- `poc/scripts/v2/tiered_llm.py`
- `poc/scripts/v2/cost_tracker.py`
- `poc/data/benchmark/golden_dataset.json`
- `poc/data/benchmark/BENCHMARK_REPORT_20260201_020315.md`
- `poc/data/benchmark/BENCHMARK_REPORT_20260201_020315.json`
- `poc/data/benchmark/benchmark_*.json` (5 model results)

### Phase 3
- `poc/scripts/wikidata/event_type_mapping.json` - 70 types across 12 categories
- `poc/scripts/wikidata/event_type_classifier.py` - QID classifier with unknown logging
- `poc/scripts/wikidata/import_wikidata_events.py` - Main import script
- `poc/data/wikidata/events_uk_*.json` - UK test results
- `docs/reports/LOCAL_LLM_BENCHMARK_ANALYSIS.md` - Detailed benchmark report

---

*Last updated: 2026-02-01 03:15*
