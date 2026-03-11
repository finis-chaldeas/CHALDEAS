# 20260308 — FGO Content Pipeline Implementation

## Purpose
Implement the complete FGO content pipeline: servant linking, servant column generation, singularity/LB article generation, shift creation, and cross-linking.

## Changes

### New Files
| File | Description |
|------|-------------|
| `backend/scripts/fgo_data_utils.py` | FGO data loading utilities (bond text, story summaries, chapter metadata, DB helpers) |
| `backend/scripts/create_fgo_content.py` | Batch runner for all phases (1-4) |
| `backend/scripts/fill_fgo_persons.py` | GPT-powered comprehensive person enrichment (--generate + --apply) |
| `backend/scripts/output/fgo_enrichment.json` | 318 enrichment entries (258 create, 60 skip) |

### Modified Files
| File | Changes |
|------|---------|
| `backend/scripts/link_fgo_persons.py` | Added `--apply-db` mode to push confirmed_links.json → fgo_servants.person_id; fixed DB config (added password, changed user to 'chaldeas') |
| `backend/scripts/create_portal_article.py` | Added `--servant-id`, `--singularity`, `--lostbelt`, `--import-after`, `--force` modes; added servant column + chapter prompts; integrated fgo_data_utils |

### Database Changes
- `fgo_servants`: person_id linked: 82 → 131 (Phase 0) → **389 (86.6%)** (fill_fgo_persons)
- `persons`: 140 new entries created (mythological 106, legendary 55, historical 24, fictional 16)
- `person_details`: 187 new entries with EN/KO biographies, era, wikipedia_url
- `persons.birthplace_id`: 293 servants' persons linked to nearest location
- `collections`: Created 4 new (fgo-singularities, fgo-lostbelts, fgo-servant-columns, fgo-history-bridge)
- `collection_entries`: Linked 27 existing portal items to new collections

## Architecture

### Pipeline Phases
```
Phase 0a: link_fgo_persons.py --apply-db            → 131 linked (done, $0)
Phase 0b: fill_fgo_persons.py --generate + --apply  → 389 linked (done, ~$1.80)
          - 140 persons created, 47 found in DB
          - 187 person_details with EN/KO bios
          - 293 birthplace locations linked
Phase 1:  create_portal_article.py --servant-id      → 30 servant columns (~$10.50)
Phase 2:  create_portal_article.py --singularity/LB  → 15 chapters (~$6.30)
Phase 3:  create_shift.py --generate (via batch)     → 15 shifts (~$5.50)
Phase 4:  create_fgo_content.py --phase 4            → collections + cross-linking (done, $0)
```

### Data Flow
```
E:\chaldeas_data\fgo_db\servants\by_id\*.json  →  Bond text context
E:\chaldeas_data\processed\fgo\summaries\       →  Story summary context
E:\chaldeas_data\processed\fgo\person_links\    →  Servant-person mappings
DB persons/events/event_persons                 →  Historical context
academic_papers JSON                            →  Paper citations
                    ↓ (GPT-5.2)
        backend/scripts/output/*.yaml           →  Generated articles
                    ↓ (--import)
        portal_items / collection_entries        →  DB
```

### Test Results
- **Caesar servant column**: 5 sections, 3,346 words, $0.115, 2.5 min
- **Babylonia singularity**: 6 sections, 4,341 words, $0.176, 3.4 min
- Content quality: Rich, engaging, cross-references FGO bond text with real history

## Running the Pipeline

```bash
cd backend

# Full pipeline (estimated ~$22, ~90 min)
python scripts/create_fgo_content.py --phase all --import-after

# Test with limits first
python scripts/create_fgo_content.py --phase 1 --limit 3 --import-after
python scripts/create_fgo_content.py --phase 2 --limit 2 --import-after
python scripts/create_fgo_content.py --phase 3 --limit 2

# Check status
python scripts/create_fgo_content.py --status

# Individual servant/chapter
python scripts/create_portal_article.py --servant-id 12 --import-after    # Gilgamesh
python scripts/create_portal_article.py --singularity VII --import-after   # Babylonia
python scripts/create_portal_article.py --lostbelt 1 --import-after        # Anastasia
```

## fill_fgo_persons.py — Enrichment Pipeline

GPT-5.2-chat powered comprehensive person data creation for ALL non-Type-Moon FGO servants.

### Category Breakdown (318 total)
| Category | Count | Description |
|----------|-------|-------------|
| mythological | 111 | Greek, Indian, Celtic, Norse, Japanese, Mesopotamian, Aztec deities/heroes |
| legendary | 64 | Arthurian knights, semi-historical figures (Robin Hood, Musashi) |
| historical | 60 | Real documented persons (Attila, Musashi, Lakshmi Bai) |
| fgo_original | 59 | Type-Moon originals (Mash, BB, Emiya) — skipped |
| fictional | 24 | Literature characters (Sherlock Holmes, Frankenstein, Nemo) |

### Cost
- 30 GPT batches × ~$0.06/batch = **~$1.80 total**
- 10 servants per batch, ~15 sec/batch

### Usage
```bash
cd backend
python scripts/fill_fgo_persons.py --status                # 현황
python scripts/fill_fgo_persons.py --generate              # GPT enrichment 생성
python scripts/fill_fgo_persons.py --generate --resume     # 이어서 생성
python scripts/fill_fgo_persons.py --generate --limit 3    # 테스트 (3배치)
python scripts/fill_fgo_persons.py --apply                 # DB 적용
python scripts/fill_fgo_persons.py --apply --dry-run       # 미리보기
```

## Next Steps
- Run Phase 1 full batch (30 servants, ~$10.50)
- Run Phase 2 full batch (15 chapters, ~$6.30)
- Run Phase 3 full batch (15 shifts, ~$5.50)
- Entity linking on generated articles: `python scripts/link_article_entities.py --mode db`
- Korean translation of new articles
