# docs/planning/ 마스터 인덱스

> **최종 수정**: 2026-02-14
> **전체 분석**: [PROJECT_ANALYSIS.md](./PROJECT_ANALYSIS.md) 참조

---

## 읽기 순서 (처음 접하는 사람)

| 순서 | 문서 | 내용 |
|------|------|------|
| 1 | [PROJECT_ANALYSIS.md](./PROJECT_ANALYSIS.md) | 프로젝트 종합 분석 (이 문서 먼저!) |
| 2 | [MASTER_PLAN.md](./MASTER_PLAN.md) | 현황 스냅샷 (DB 상태, 완료/진행 중) |
| 3 | [FINAL_SCHEMA.md](./FINAL_SCHEMA.md) | DB 구조 정의 (13개 테이블, 확정) |
| 4 | [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) | 구현 진행 (Phase 1~3 완료, 4~5 대기) |
| 5 | [event_hierarchy/INDEX.md](./event_hierarchy/INDEX.md) | 현재 대작업: 이벤트 계층화 |

---

## 폴더 구조

```
docs/planning/
├── PROJECT_ANALYSIS.md          ← 종합 분석 (이 문서의 상위)
├── INDEX.md                     ← 이 문서 (마스터 인덱스)
│
├── [핵심 문서 - 루트에 유지]
│   ├── MASTER_PLAN.md           ← 프로젝트 현황
│   ├── FINAL_SCHEMA.md          ← DB 구조 (확정)
│   └── IMPLEMENTATION_PLAN.md   ← 구현 진행
│
├── event_hierarchy/             ← 이벤트 계층화 (21개 문서)
├── data_model/                  ← 데이터 모델 (FINAL_SCHEMA 배경)
├── wikidata/                    ← Wikidata 관련
├── pipeline/                    ← 파이프라인 (책 추출 등)
├── classification/              ← 분류/가중치 체계
├── future_plan/                 ← V3+ 미래 계획
├── completed/                   ← 완료된 Phase 보고서
└── deprecated/                  ← 대체된 문서 (60+)
```

---

## A. 핵심 문서 (루트)

현재 유효한 최상위 문서. **이것만 읽으면 프로젝트를 이해할 수 있음.**

| 문서 | 상태 | 내용 |
|------|------|------|
| [PROJECT_ANALYSIS.md](./PROJECT_ANALYSIS.md) | 📊 분석 | 전체 프로젝트 종합 분석 |
| [MASTER_PLAN.md](./MASTER_PLAN.md) | 🔥 운영 | 현황 스냅샷: DB 상태, 아키텍처, API |
| [FINAL_SCHEMA.md](./FINAL_SCHEMA.md) | ✅ 확정 | 13개 테이블 정의 (모든 스키마의 최종본) |
| [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) | 🔥 진행 | Phase 1~3 완료, 4~5 대기 |

---

## B. event_hierarchy/ (이벤트 계층화)

**현재 진행 중인 핵심 작업.** 46,704개 이벤트를 5단계 계층으로 조직화.

상세: [event_hierarchy/INDEX.md](./event_hierarchy/INDEX.md)

| 문서 | 내용 |
|------|------|
| 00_OVERVIEW.md | 마스터 플랜, 358개 Aggregate 이벤트 |
| 01_SCHEMA.md | Alembic 마이그레이션, 모델 확장 |
| 02~06 | 카테고리별: 전쟁, 철학, 예술, 과학, 종교 |
| 07_EVENT_RELATIONS.md | 비계층 관계 (인과/영향) |
| 08_VECTOR_MODEL.md | 벡터 기반 숨은 연결 발견 |
| 09_RELATION_PIPELINE.md | Book Extractor 관계 후처리 |
| 10~12 | 장소 계층, 통합 모델, 시대 추출 |
| 13~16 | FGO 데이터, Multiverse 모델 |
| 17~21 | 계층 구축 전략 (Wikidata P361, LLM, 다중 부모) |
| CLASSIFICATION_METHODOLOGY_REPORT.md | 분류 방법론 보고서 |

루트에 남은 관련 문서:

| 문서 | 관계 |
|------|------|
| [HIERARCHY_METHODOLOGY_REPORT.md](./HIERARCHY_METHODOLOGY_REPORT.md) | event_hierarchy의 방법론 배경 |
| [HIERARCHY_SYSTEM_REPORT.md](./HIERARCHY_SYSTEM_REPORT.md) | 계층 시스템 전체 보고서 |

---

## C. data_model/ (데이터 모델)

**FINAL_SCHEMA.md의 배경 문서들.** FINAL_SCHEMA에 통합되었으므로 참고용.

| 문서 | 내용 | 통합 상태 |
|------|------|----------|
| [DATA_MODEL_REDESIGN.md](./data_model/DATA_MODEL_REDESIGN.md) | Location/Territory, Person/Group 분리 개념 | → FINAL_SCHEMA |
| [DATA_MODEL_SCHEMA.md](./data_model/DATA_MODEL_SCHEMA.md) | 상세 SQL 정의 | → FINAL_SCHEMA |
| [CLEAN_SCHEMA_PLAN.md](./data_model/CLEAN_SCHEMA_PLAN.md) | DB 정리 계획 | → FINAL_SCHEMA |
| [CHALDEAS_UNIFIED_SPEC.md](./data_model/CHALDEAS_UNIFIED_SPEC.md) | 통합 스펙 (UI + 데이터) | → FINAL_SCHEMA (데이터 부분) |
| [CONCEPT_ENTITY_PROPOSAL.md](./data_model/CONCEPT_ENTITY_PROPOSAL.md) | 개념 엔티티 (추상 개념 모델링) | 미반영 (장기 과제) |
| [DATA_INTEGRATION.md](./data_model/DATA_INTEGRATION.md) | 데이터 통합 전략 | → IMPLEMENTATION_PLAN |

---

## D. wikidata/ (Wikidata 관련)

**Wikidata 연동 전략과 속성 구조.** IMPLEMENTATION_PLAN에 실행 계획 반영.

| 문서 | 내용 | 상태 |
|------|------|------|
| [WIKIDATA_COMPLETE_STRUCTURE.md](./wikidata/WIKIDATA_COMPLETE_STRUCTURE.md) | Wikidata 전체 속성 구조 | 📋 참고용 (속성 목록) |
| [WIKIDATA_IMPORT_REDESIGN.md](./wikidata/WIKIDATA_IMPORT_REDESIGN.md) | 임포트 재설계 | → IMPLEMENTATION_PLAN |
| [WIKIDATA_MAPPING.md](./wikidata/WIKIDATA_MAPPING.md) | QID ↔ DB 매핑 전략 | → IMPLEMENTATION_PLAN |
| [FRESH_WIKIDATA_IMPORT.md](./wikidata/FRESH_WIKIDATA_IMPORT.md) | 신규 임포트 계획 | → IMPLEMENTATION_PLAN |
| [UNIFIED_EXTRACTION_SYSTEM.md](./wikidata/UNIFIED_EXTRACTION_SYSTEM.md) | Wikidata + Wikipedia 통합 추출 | 📋 미구현 (대규모) |

---

## E. pipeline/ (파이프라인)

**책 추출 및 소스 관리 파이프라인.** 운영 중.

| 문서 | 내용 | 상태 |
|------|------|------|
| [PIPELINE_GUIDE.md](./pipeline/PIPELINE_GUIDE.md) | 책 추가 파이프라인 가이드 | ✅ 운영 |
| [SOURCE_BOOK_MANAGEMENT.md](./pipeline/SOURCE_BOOK_MANAGEMENT.md) | 소스/책 관리 규칙 | ✅ 운영 |
| [BOOK_CONTEXT_TRACKING_PLAN.md](./pipeline/BOOK_CONTEXT_TRACKING_PLAN.md) | 166권 Context 역추적 | 📋 계획 |
| [BOOK_INTEGRATION_STATUS.md](./pipeline/BOOK_INTEGRATION_STATUS.md) | 책 통합 현황 | ✅ 운영 |
| [GUTENBERG_MERGE_PLAN.md](./pipeline/GUTENBERG_MERGE_PLAN.md) | Gutenberg 병합 계획 | 📋 계획 |
| [PROMPT_ENGINEERING.md](./pipeline/PROMPT_ENGINEERING.md) | LLM 프롬프트 설계 가이드 | 📋 참고 |

---

## F. classification/ (분류 & 가중치)

**엔티티/이벤트 분류 및 가중치 체계.** 아직 통합 문서 없음.

| 문서 | 내용 | 상태 |
|------|------|------|
| [CHALDEAS_CLASSIFICATION_SYSTEM.md](./classification/CHALDEAS_CLASSIFICATION_SYSTEM.md) | 전체 분류 체계 | 📋 설계 |
| [ENTITY_IMPORTANCE_RANKING.md](./classification/ENTITY_IMPORTANCE_RANKING.md) | 엔티티 중요도 랭킹 기준 | 📋 설계 |
| [WEIGHTING_SYSTEM.md](./classification/WEIGHTING_SYSTEM.md) | 관계 강도 가중치 | 📋 설계 |
| [TEMPORAL_TAG_SYSTEM.md](./classification/TEMPORAL_TAG_SYSTEM.md) | 시간 태그 (Braudel 스케일) | 📋 설계 |
| [EVENT_EXPANSION_PLAN.md](./classification/EVENT_EXPANSION_PLAN.md) | 이벤트 확장 전략 | 📋 설계 |

---

## G. next_phase/ (통합 미래 계획) ★ NEW

**UX 혁신 + FGO 브릿지 + 데이터 풍부화의 통합 계획.**
event_hierarchy의 FGO/위치 관련 문서와 future_plan의 큐레이션/시각화를 흡수.

상세: [next_phase/INDEX.md](./next_phase/INDEX.md)

| 문서 | 내용 |
|------|------|
| 01_GLOBE_UX.md | 지구본 4단계 줌, 항공뷰, 라벨 시스템 |
| 02_LOCATION_SYSTEM.md | 로케이션 상시 표시, 시대별 명칭/소속 |
| 03_FEED_UX.md | Feed + 4가지 진입점 (SHEBA/LAPLACE/PAPERMOON/TRISMEGISTUS) |
| 04_FGO_BRIDGE.md | 서번트 ↔ 역사 브릿지, 멀티버스, 페르소나 |
| 05_DATA_REQUIREMENTS.md | 전체 데이터 요구사항, Sprint 계획, 비용 |
| 06_DATASET_TIERS.md | 인물 티어 (S/A/B/C/Archive), TRISMEGISTUS 미디어 확장 |
| 07_DATASET_SELECTION_CRITERIA.md | Full/Light 선정 기준, 학술 근거, 대학 교양 커버리지 |

---

## H. future_plan/ (미래 계획 — 일부 next_phase로 통합됨)

**next_phase로 통합되지 않은 나머지 장기 계획들.**

상세: [future_plan/INDEX.md](./future_plan/INDEX.md)

| 문서 | 내용 | 상태 |
|------|------|------|
| GLOBE_VISUALIZATION_V2.md | 글로브 V2 | → next_phase/01 통합 |
| CURATION_AND_FGO_MASTER_PLAN.md | 큐레이션 + FGO | → next_phase/03,04 통합 |
| CURATION_SYSTEM.md | AI 큐레이터 | → next_phase/03 통합 |
| STORY_CURATION_SYSTEM.md | 스토리 큐레이션 | → next_phase/04 통합 |
| STORY_IMPLEMENTATION.md | 스토리 구현 | → next_phase/04 통합 |
| WIKIDATA_AUTO_ENRICHMENT.md | 자동 보강 | 유지 (장기) |
| DATA_INGESTION_PIPELINE.md | 데이터 수집 | 유지 (장기) |
| USER_DATA_*.md | 사용자 기여 | 유지 (장기) |
| OPEN_CURATION_VISION.md | 오픈 큐레이션 | 유지 (장기) |
| SYSTEM_GAPS_AND_SOLUTIONS.md | 갭 분석 | 유지 (장기) |
| WIKIDATA_FACTGRID_EXPANSION.md | FactGrid | 유지 (장기) |

---

## I. completed/ (완료)

**완료된 Phase 보고서.** 역사적 참고용.

| 문서 | 내용 |
|------|------|
| V1_PROGRESS_REPORT.md | V1 진행 보고 |
| V1_GLOBE_INTEGRATION_PLAN.md | Globe 통합 |
| V1_PIPELINE_FAILURE_REPORT.md | 파이프라인 실패 분석 |
| PHASE_2_3_REPORT.md | Phase 2~3 보고 |
| PHASE_3_4_REPORT.md | Phase 3~4 보고 |
| PHASE7_HISTORICAL_CHAIN.md | Historical Chain 구현 |
| PHASE8_UI_IMPROVEMENT.md | UI 개선 |
| DATA_QUALITY_REPORT.md | 데이터 품질 보고 |
| DATA_RECONCILIATION_PLAN.md | 데이터 정합 |
| PRE_CURATION_CHECKLIST.md | 큐레이션 전 체크 |
| ARCHIVIST_CHECKPOINT_REDESIGN.md | Archivist 재설계 |
| INTEGRATED_NER_PIPELINE.md | 통합 NER |
| NER_PIPELINE_DESIGN.md | NER 설계 |
| TIMELINE_UI_REDESIGN.md | Timeline UI |
| GLOBE_MARKER_IMPROVEMENTS.md | Globe 마커 |
| 2026-01-18_*.md | 1/18 포스트모템 + 복구 |

---

## J. deprecated/ (대체됨)

**60+ 문서. 읽을 필요 없음.** 새 문서에 의해 대체된 과거 계획/분석.

주요 카테고리:
- V1_WORKPLAN.md → IMPLEMENTATION_PLAN으로 대체
- DATA_QUALITY_IMPROVEMENT_PLAN.md → FINAL_SCHEMA로 대체
- WIKIDATA_PIPELINE.md → unified/ 파이프라인으로 대체
- CLEAN_START_PLAN.md → IMPLEMENTATION_PLAN으로 대체
- FRONTEND_IMPROVEMENTS.md → FRONTEND_RESTRUCTURE.md로 대체
- 기타: 일회성 보고서, 작업 기록, 과거 전략

---

## K. 기타 (루트 잔류)

| 문서 | 내용 | 비고 |
|------|------|------|
| [FRONTEND_RESTRUCTURE.md](./FRONTEND_RESTRUCTURE.md) | 프론트엔드 재구성 계획 | 미구현 |
| [JOAN_OF_ARC_SHOWCASE.md](./JOAN_OF_ARC_SHOWCASE.md) | 잔다르크 쇼케이스 예시 | 참고 |
| [GPU_THERMAL_MANAGEMENT.md](./GPU_THERMAL_MANAGEMENT.md) | GPU 온도 관리 | 하드웨어 참고 |
