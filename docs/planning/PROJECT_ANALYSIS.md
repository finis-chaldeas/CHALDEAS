# CHALDEAS 프로젝트 종합 분석

> **작성일**: 2026-02-14
> **목적**: 프로젝트의 본질, 시도한 것, 결과, 현재 상태를 종합 정리

---

## 1. 프로젝트의 본질

### 한 문장 요약

> **"세계사의 모든 사건을 누가(Person), 어디서(Location), 언제(Time), 무엇을(Event) 했는가로 구조화하고, 모든 정보에 출처(Source)를 붙여 3D 지구본에서 탐색할 수 있게 만드는 시스템."**

### 핵심 원칙

1. **Wikidata QID = 유일 식별자**: 모든 엔티티는 QID로 식별. 이름은 alias일 뿐.
2. **출처 추적 (Source Attribution)**: 모든 정보에 "어디서 왔는지" 기록. mention 없으면 쓰레기.
3. **World State is Immutable**: 상태 변경은 Layer 6(PATCH/APPLY)만 통과.
4. **점진적 구축**: 확실한 것만 DB에, 불확실한 것은 "미확인" 큐.

### FGO에서 빌린 것 (이름만)

| 시스템명 | 역할 | 실제 의미 |
|---------|------|----------|
| CHALDEAS | World State | DB (PostgreSQL) |
| SHEBA | Query/Observe | 검색, 벡터 쿼리 |
| LOGOS | Propose | LLM 응답 생성 |
| PAPERMOON | Verify | 사실 확인 |
| LAPLACE | Explain | 출처 기반 설명 |
| TRISMEGISTUS | Orchestrate | 시스템 오케스트레이터 |

---

## 2. 프로젝트 연대기: 무엇을 했고, 왜 그렇게 됐나

### Phase A: 초기 구축 (2025년)

**무엇을 했나:**
- 3D Globe + Timeline UI 구현 (react-globe.gl)
- 기본 DB에 이름 기반으로 인물/장소/이벤트 삽입
- Gutenberg ZIM (8만권 책)에서 NER로 엔티티 추출 시작

**문제점:**
- 이름 기반 매칭 → 동명이인 문제 (예: "Alexander" = 알렉산드로스 대왕? 알렉산데르 6세?)
- QID 없이 삽입 → 중복 폭발 (같은 사람 여러 레코드)
- 110개 스크립트가 각각 다른 방식으로 매칭 → 쓰레기 데이터 양산

### Phase B: Wikidata 도입 (2026-01 초)

**깨달음:**
> "이름으로 매칭하면 안 된다. Wikidata가 이미 모든 엔티티를 식별했다. QID를 쓰자."

**무엇을 했나:**
- Wikidata 전체 덤프 다운로드 (E:\wikidata\latest-all.json, 1.6TB)
- QID 기반 중복 제거: 10,329개 합침
- 쓰레기 데이터 삭제: 894개
- 기존 DB에서 QID 있는 것만 살림: 91,596명/275,343명

**스크립트 진화 (search_correct_qids v1~v7):**
- v1: 단순 이름 검색 → 정확도 낮음
- v2: context 포함 검색 → 약간 개선
- v3~v5: 다양한 disambiguation 시도
- v6: embedding 유사도 추가
- v7: 최종 안정 버전 (6단계 매칭)
- 이 과정에서 "Entity Matcher 6단계 파이프라인" 탄생

### Phase C: 스키마 재설계 (2026-01~02)

**깨달음:**
> "기존 DB 구조로는 안 된다. 출처(Source)와 언급(Mention)이 1등 시민이어야 한다."

**무엇을 했나:**
1. 여러 플랜 문서 작성 (겹치는 내용 많음):
   - `DATA_MODEL_REDESIGN.md` → Location/Territory, Person/Group 분리 개념
   - `DATA_MODEL_SCHEMA.md` → 상세 SQL
   - `CLEAN_SCHEMA_PLAN.md` → 정리 계획
   - `CHALDEAS_UNIFIED_SPEC.md` → 통합 스펙
   - `CONCEPT_ENTITY_PROPOSAL.md` → 개념 엔티티 제안
   - 최종적으로 → **`FINAL_SCHEMA.md`** 로 통합 (2026-02-05 확정)

2. **FINAL_SCHEMA (13개 테이블)**:
   - 엔티티 5개: locations, territories, persons, groups, events
   - 출처 2개: sources, mentions (**핵심!**)
   - 관계 6개: links, location_names, territory_locations, group_members, event_participants, event_locations

**왜 이 구조인가:**
- `mentions` 테이블이 핵심. 모든 엔티티는 최소 1개 mention이 있어야 함 = "출처 없으면 DB에 넣지 마라"
- `links` 테이블 = 범용 관계 (from_type/from_id → to_type/to_id + category)
- `territories` = Location의 시간 종속 확장 (로마 제국의 영토는 시기마다 다름)
- `groups` = Person의 집합 (기사단, 군대, 왕조)

### Phase D: 스키마 구현 & Unified 파이프라인 실행 (2026-02)

**무엇을 했나:**
- Alembic migration 001~200 순차 적용 → 22개 테이블 생성
- `poc/scripts/unified/` 파이프라인 실행:
  - `02_extract_wikidata.py` → Wikidata 덤프에서 persons 1300만, locations 240만 등 추출
  - `03_extract_wikipedia*.py` → Wikipedia 문서 250만개 추출
  - `04_import_*.py` → DB 임포트
  - `05_build_links.py` → Wikipedia 하이퍼링크에서 links 720만건 생성
  - entity_properties 1.1억건 (Wikidata 속성 전체)
- 결과: **대규모 데이터가 실제로 DB에 들어왔다**
- 단, mentions(40만)은 전체 엔티티 대비 극소량만 연결됨

### Phase E: 이벤트 계층화 설계 (2026-01-28~현재)

**깨달음:**
> "28,331개 이벤트가 평면적이다. 아쟁쿠르 전투 → 백년전쟁 → 중세 유럽 처럼 계층이 필요하다."

**무엇을 했나:**
- 21개 문서로 설계 완료 (`event_hierarchy/00~21`)
- 5단계 계층: Era(0) → Mega(1) → Aggregate(2) → Major(3) → Minor(4)
- 358개 대표 Aggregate 이벤트 목록 작성 (전쟁, 철학, 예술, 과학, 종교별)
- Wikidata P361(part_of) 속성 활용 전략
- LLM 분류기 설계 (gpt-5.1-chat-latest)
- DB 컬럼 추가: parent_event_id, is_aggregate, hierarchy_level, aggregate_type
- **하지만 실제 데이터 연결은 0건** (설계만 완료, 실행 미착수)

---

## 3. 데이터 파이프라인 구조

### 3.1 데이터 소스 (원천)

| 소스 | 형태 | 크기 | 용도 |
|------|------|------|------|
| Wikidata JSON 덤프 | E:\wikidata\latest-all.json | 1.6TB | 엔티티 메타데이터, QID, 속성 |
| Wikipedia ZIM | E:\chaldeas_data\kiwix\ | ~수십GB | 문서 본문, 하이퍼링크 관계 |
| Gutenberg ZIM | data/kiwix/gutenberg_en_all.zim | 206GB | 8만권 역사 관련 책 |
| FGO 서번트 | data/raw/atlas_academy/ | 소규모 | 게임 내 역사 인물 |

### 3.2 추출 파이프라인 (3개 독립 경로)

```
경로 1: 책 추출 (Book Extractor)
─────────────────────────────────
Gutenberg ZIM → 구조 감지(BOOK/CHAPTER/SECTION)
    → 2500자 청크 + 200자 오버랩
    → LLM 추출 (Ollama llama3.1 or gpt-5-mini)
    → Entity Matcher 6단계 매칭
    → DB (sources + mentions + entities)

경로 2: Wikidata 추출 (Unified Pipeline)
────────────────────────────────────────
Wikidata JSON 덤프 → 파싱 (1억+ 엔티티)
    → 타입 필터링 (Q5=인간, P31 기반)
    → 속성 추출 (P22=아버지, P607=참전, P276=장소...)
    → QID 매핑 (Wikidata QID ↔ Wikipedia 제목)
    → DB 임포트 (각 타입별)

경로 3: Wikipedia 추출
─────────────────────
Wikipedia ZIM → 문서 본문 추출
    → 하이퍼링크 파싱 (엔티티 간 관계)
    → QID 매핑으로 DB 연결
    → links 테이블에 관계 생성
```

### 3.3 Entity Matcher 6단계 (핵심 컴포넌트)

```
Stage 1: Exact Match      → 이름 완전 일치 (confidence: 1.0)
Stage 2: Alias Match      → entity_aliases 조회 (confidence: 0.95)
Stage 3: Wikidata QID     → Wikidata 검색 → 기존 QID 매칭 (confidence: 0.98)
Stage 4: Embedding        → OpenAI text-embedding-3-small 코사인 유사도
Stage 5: LLM Verify       → gpt-5.1-chat (0.85~0.95 사이 후보)
Stage 6: Partial Match    → Trigram 퍼지 검색 (confidence: 0.88)
         → NEW ENTITY     → 모두 실패 시 신규 엔티티 생성
```

### 3.4 LLM 티어 시스템

| 티어 | 모델 | 비용 | 용도 | 결과 |
|------|------|------|------|------|
| T1 (로컬) | llama3.1:8b-instruct-q4_0 | 무료 | 엔티티 추출 | 정확도 <7% (실패) |
| T1 (로컬) | mistral:7b | 무료 | 성질 분류 | 84.6% (사용 가능) |
| T1 (로컬) | gemma2:9b | 무료 | 날짜 파싱 | 70.5% (사용 가능) |
| T2 (API) | gpt-5-mini | $0.25/1M | 엔티티 추출 (폴백) | 사용 중 |
| T3 (API) | gpt-5.1-chat | $1.25/1M | 계층 분류, 복잡한 추론 | 사용 중 |

**교훈**: 로컬 모델로 엔티티 추출은 실패 (<7%). 분류/파싱은 가능. 추출은 API 필수.

---

## 4. 현재 DB 상태 (2026-02-14 실측)

**하나의 PostgreSQL DB, 하나의 스키마.** V0/V1/V2 같은 분리는 없다. Alembic migration `200_connections`까지 적용됨. 코드에 models/v1/, models/v2/ 폴더가 있지만, 실제 DB는 단일 스키마로 모든 테이블이 공존한다.

### 22개 테이블 전체 현황

**핵심 엔티티:**

| 테이블 | 행 수 | 비고 |
|--------|-------|------|
| **persons** | **12,987,361** | 전원 QID 보유 (100%). Wikidata Q5 전체 임포트 완료 |
| **locations** | **2,387,834** | 좌표 필수. Wikidata에서 추출 |
| **groups** | **590,284** | 군대, 종교단체, 민족, 정치조직 |
| **events** | **28,331** | parent_event_id 연결된 것: 0개. 계층화 미착수 |
| **territories** | **9,516** | 국가/제국/지역 |
| **categories** | **7** | |
| **periods** | **0** | 비어있음 |

**출처 & 언급:**

| 테이블 | 행 수 | 비고 |
|--------|-------|------|
| **sources** | **18,512,216** | Wikidata 16M + Wikipedia 2.5M |
| **mentions** | **400,516** | person 175K, territory 75K, group 69K, location 50K, event 31K |
| **text_mentions** | **0** | 비어있음 (레거시 테이블) |

**관계:**

| 테이블 | 행 수 | 비고 |
|--------|-------|------|
| **entity_properties** | **112,791,499** | Wikidata 속성. person 98M, location 12M, group 3M |
| **links** | **7,201,807** | person→person 5.3M, person→location 1.9M (Wikipedia 하이퍼링크) |
| **group_members** | **985,487** | 집단 구성원 |
| **event_participants** | **122,760** | 이벤트 참여자 (person/group/territory) |
| **event_persons** | **122,430** | 이벤트-인물 (레거시) |
| **event_sources** | **22,977** | 이벤트 출처 |
| **event_connections** | **20,681** | 이벤트 간 연결 |
| **event_locations** | **4,612** | 이벤트 발생 장소 |
| **location_names** | **0** | 비어있음 (시대별 장소 이름) |
| **territory_locations** | **0** | 비어있음 (영역↔장소) |
| **connection_sources** | **0** | 비어있음 |

### 데이터 품질 현황

| 항목 | 값 | 판단 |
|------|-----|------|
| persons QID 커버리지 | 100% (12,987,361/12,987,361) | ✅ 완벽 |
| events parent 연결 | 0/28,331 (0%) | ❌ 계층화 필요 |
| events location 연결 | 4,474/28,331 (16%) | ⚠️ 대부분 위치 없음 |
| mentions 커버리지 | 400K/16M+ 엔티티 (극히 일부) | ⚠️ 대부분 mention 없음 |
| entity_properties | 1.1억 (person당 평균 ~7.5개) | ✅ 풍부 |
| links (Wikipedia) | 7.2M | ✅ person→person 관계 풍부 |

### 주요 Wikidata 속성 (entity_properties 상위 15개)

| 속성 | 이름 | 건수 |
|------|------|------|
| P106 | occupation (직업) | 6,915,031 |
| P31 | instance of (타입) | 6,870,681 |
| P21 | sex/gender (성별) | 5,717,955 |
| P735 | given name (이름) | 4,621,422 |
| P569 | date of birth (생년) | 4,259,996 |
| P27 | citizenship (국적) | 3,399,485 |
| P734 | family name (성) | 3,278,408 |
| P19 | place of birth (출생지) | 2,155,669 |
| P570 | date of death (몰년) | 2,062,967 |
| P1412 | languages spoken | 1,936,729 |
| P69 | educated at (학력) | 1,936,352 |

### 이벤트 타입 분포

| event_type | 건수 |
|------------|------|
| historical_event | 22,951 |
| occurrence | 1,603 |
| massacre | 1,020 |
| historical_period | 610 |
| treaty | 523 |
| flood | 430 |
| battle | 411 |
| epidemic | 180 |
| rebellion | 133 |

### 코드 vs DB의 관계

코드에 `backend/app/models/v1/`, `backend/app/models/v2/` 폴더가 있지만, 이것은 **모델 파일의 정리용 구분**이지 DB 분리가 아니다. 모든 migration은 같은 DB에 순차 적용되었고, 결과는 위 22개 테이블이다.

- `models/*.py` (event.py, person.py, location.py 등): 현재 운영 중인 핵심 모델
- `models/v1/*.py` (chain.py, period.py, polity.py 등): 추가된 테이블 (periods, historical_chains 등)
- `models/v2/*.py` (event_v2.py, cluster.py 등): **DB에 존재하지 않음**. 아직 migration 미실행. 설계만 완료된 상태

---

## 5. 스크립트 현황

### 전체 규모

| 위치 | 스크립트 수 | 상태 |
|------|-----------|------|
| poc/scripts/ (루트) | 49 | 활성 |
| poc/scripts/deprecated/ | 41 | 대체됨 |
| poc/scripts/temp/ | 39 | 일회성 |
| poc/scripts/hierarchy/ | 21 | 활성 (이벤트 계층) |
| poc/scripts/wikidata/ | 25 | 활성 (Wikidata 추출) |
| poc/scripts/unified/ | 28 | 활성 (통합 파이프라인) |
| poc/scripts/v2/ | 12 | 활성 (V2 아키텍처) |
| tools/book_extractor/ | 4 핵심 | 활성 (웹 대시보드) |
| **합계** | **~219** | |

### 핵심 스크립트 (현재 쓰이는 것)

```
tools/book_extractor/
  server.py                    ← 책 추출 대시보드 (localhost:8200)
  entity_matcher.py            ← 6단계 엔티티 매칭

poc/scripts/unified/
  01_build_qid_mapping.py      ← QID ↔ Wikipedia 매핑
  02_extract_wikidata.py       ← Wikidata 엔티티 추출
  03_extract_wikipedia*.py     ← Wikipedia 본문 + 링크 추출
  04_import_*.py               ← DB 임포트
  05_build_links.py            ← 관계 생성

poc/scripts/hierarchy/
  llm_classifier.py            ← 이벤트 계층 분류 (gpt-5.1)
  match_orphan_events.py       ← 고아 이벤트 부모 찾기
  fetch_p361.py                ← Wikidata P361(part_of) 추출

poc/scripts/wikidata/
  extract_events_from_dump.py  ← 이벤트 추출
  import_events_fast.py        ← 빠른 임포트
  data_access/                 ← SPARQL, 덤프 리더
  importers/                   ← 타입별 임포터
```

### 왜 스크립트가 이렇게 많은가

**근본 원인**: 시행착오 반복.
- 이름 매칭 → 실패 → Wikidata 도입 → 실패 → 6단계 파이프라인 → 성공
- 로컬 LLM → 실패 → API → 비용 문제 → 티어 시스템 → 안정
- DB 구조 변경마다 새 임포터 필요

**교훈**: deprecated/와 temp/에 있는 ~80개 스크립트는 이 과정의 흔적. 지우면 안 되지만 참고할 필요도 없음.

---

## 6. 플랜 문서 분석

### 현재 문서 분포

| 위치 | 문서 수 | 설명 |
|------|---------|------|
| docs/planning/ 루트 | 30 | 혼재 (핵심 + 잡다) |
| event_hierarchy/ | 25 | 잘 정리됨 (INDEX 있음) |
| future_plan/ | 15 | V3+ 로드맵 |
| completed/ | 23 | 완료된 Phase 보고서 |
| deprecated/ | ~60 | 대체된 문서 |

### 문서 간 관계와 중복

```
문서 흐름 (시간순):

DATA_MODEL_REDESIGN.md ──┐
DATA_MODEL_SCHEMA.md ────┤
CLEAN_SCHEMA_PLAN.md ────┼──► FINAL_SCHEMA.md (통합 결과)
CHALDEAS_UNIFIED_SPEC.md─┤
CONCEPT_ENTITY_PROPOSAL.md┘

WIKIDATA_IMPORT_REDESIGN.md──┐
WIKIDATA_COMPLETE_STRUCTURE.md┼──► IMPLEMENTATION_PLAN.md (실행 계획)
FRESH_WIKIDATA_IMPORT.md─────┤
WIKIDATA_MAPPING.md──────────┘

HIERARCHY_METHODOLOGY_REPORT.md──┐
HIERARCHY_SYSTEM_REPORT.md───────┼──► event_hierarchy/00_OVERVIEW.md (통합)
EVENT_EXPANSION_PLAN.md──────────┘

CHALDEAS_CLASSIFICATION_SYSTEM.md──┐
ENTITY_IMPORTANCE_RANKING.md───────┼──► 아직 통합 안 됨
WEIGHTING_SYSTEM.md────────────────┤
TEMPORAL_TAG_SYSTEM.md─────────────┘
```

### 핵심 문서 (이것만 읽으면 됨)

| 순서 | 문서 | 왜 중요한가 |
|------|------|-----------|
| 1 | `MASTER_PLAN.md` | 프로젝트 현황 스냅샷 |
| 2 | `FINAL_SCHEMA.md` | DB 구조 정의 (13개 테이블) |
| 3 | `IMPLEMENTATION_PLAN.md` | 뭘 했고 뭘 안 했는지 |
| 4 | `event_hierarchy/INDEX.md` | 현재 진행 중인 대작업 |
| 5 | `PIPELINE_GUIDE.md` | 책 추가 파이프라인 |

### 읽을 필요 없는 문서

- `deprecated/` 전체 (60+ 문서) - 대체됨
- `DATA_MODEL_REDESIGN.md`, `DATA_MODEL_SCHEMA.md`, `CLEAN_SCHEMA_PLAN.md` - FINAL_SCHEMA에 통합됨
- `WIKIDATA_IMPORT_REDESIGN.md`, `FRESH_WIKIDATA_IMPORT.md` - IMPLEMENTATION_PLAN에 반영됨
- `GPU_THERMAL_MANAGEMENT.md` - 하드웨어 참고자료
- `JOAN_OF_ARC_SHOWCASE.md` - 예시

---

## 7. 무엇이 성공했고, 무엇이 실패했나

### 성공

| 항목 | 결과 |
|------|------|
| 3D Globe + Timeline UI | ✅ 운영 중 (www.chaldeas.site) |
| Book Extractor 대시보드 | ✅ 운영 중 (localhost:8200) |
| Entity Matcher 6단계 | ✅ 안정적 (entity_matcher.py) |
| **Wikidata 전체 임포트** | ✅ persons 1300만, locations 240만 (QID 100%) |
| **Wikipedia 임포트** | ✅ sources 250만, links 720만 |
| **entity_properties** | ✅ Wikidata 속성 1.1억건 (직업, 성별, 생년 등) |
| **출처 시스템** | ✅ sources 1850만 + mentions 40만 |
| QID 기반 중복 방지 | ✅ persons 전원 wikidata_id UNIQUE |
| 이벤트 계층 설계 | ✅ 21개 문서, 358개 Aggregate 목록 |
| 티어별 LLM 비용 관리 | ✅ 로컬(무료) + API(유료) 분리 |

### 미완성 (데이터는 있으나 채워지지 않은 것)

| 항목 | 상태 | 설명 |
|------|------|------|
| 이벤트 계층 (parent_event_id) | 0/28,331 (0%) | 설계 완료, 데이터 미연결 |
| 이벤트 위치 (primary_location_id) | 4,474/28,331 (16%) | 대부분 위치 없음 |
| mentions 커버리지 | 40만/1600만+ 엔티티 | 극히 일부만 mention 연결 |
| location_names (시대별 이름) | 0건 | 테이블 비어있음 |
| territory_locations (영역↔장소) | 0건 | 테이블 비어있음 |
| periods (시대 구분) | 0건 | 테이블 비어있음 |
| 책 Context 역추적 (166권) | 미완 | 계획만 수립 |
| 프론트엔드 재구성 | 미완 | 백엔드 우선 |

### 버려진 접근법

| 접근 | 왜 버림 | 대체안 |
|------|---------|--------|
| NER (Named Entity Recognition) | 정확도 부족 | LLM 기반 추출 |
| 이름 기반 매칭 | 동명이인, 중복 | QID + 6단계 매칭 |
| 로컬 모델만으로 추출 | 7% 미만 정확도 | 티어 시스템 (로컬→API) |
| 배치 LLM 분류 (이벤트 레벨) | "관계가 레벨보다 먼저" | Wikidata P361 + LLM 분류기 |

---

## 8. 현재 당면 과제와 우선순위

### 데이터 현실 인식

Unified 파이프라인이 실행되어 **대규모 데이터가 이미 들어와 있다.** 과거 플랜에서 "Phase 4 전체 임포트"라고 적힌 것은 **대부분 완료된 상태**.

하지만 "데이터가 있다"와 "데이터가 연결되어 있다"는 다르다:
- persons 1300만명이 있지만, mention은 40만건 (3%)
- events 28,331건이 있지만, parent 연결은 0건
- sources 1850만건이 있지만, 대부분 원문만 있고 엔티티와 연결 안 됨

### 높은 우선순위

1. **이벤트 계층 구축**
   - 28,331개 이벤트에 parent_event_id 연결
   - 358개 Aggregate 이벤트 생성 및 연결
   - Wikidata P361(part_of) 먼저, LLM 분류 보충

2. **이벤트 위치 보강**
   - 28,331개 중 84%가 위치 없음 → 3D Globe에서 표시 불가
   - entity_properties에서 P276(location) 추출하여 연결

3. **mentions 확대**
   - 현재 40만건 → 엔티티 수 대비 극소량
   - Wikipedia source에서 mention 자동 생성 필요

### 중간 우선순위

4. **비어있는 테이블 채우기**: location_names, territory_locations, periods
5. **책 Context 역추적** (166권)
6. **프론트엔드 재구성**

### 낮은 우선순위

7. 큐레이션 시스템
8. 사용자 투고 파이프라인

---

## 9. DB 스키마 정리

### 현실: 하나의 DB, 하나의 스키마

코드에 `models/`, `models/v1/`, `models/v2/` 폴더가 있지만 이는 **코드 정리용 구분**이다. 실제 PostgreSQL DB는 22개 테이블이 하나의 public 스키마에 공존한다.

```
실제 DB (PostgreSQL, alembic 200_connections):
────────────────────────────────────────────
핵심 엔티티:    persons, locations, events, groups, territories, categories, periods
출처:          sources, mentions, text_mentions(레거시, 비어있음)
속성:          entity_properties (1.1억건, Wikidata 속성)
관계:          links, event_connections, event_persons, event_locations,
              event_sources, event_participants, group_members,
              location_names, territory_locations, connection_sources
```

### 코드 파일 ↔ DB 테이블 매핑

| 코드 위치 | DB 테이블 | 상태 |
|----------|----------|------|
| `models/event.py` | events | ✅ 데이터 있음 (28K) |
| `models/person.py` | persons | ✅ 데이터 있음 (13M) |
| `models/location.py` | locations | ✅ 데이터 있음 (2.4M) |
| `models/source.py` | sources | ✅ 데이터 있음 (18.5M) |
| `models/associations.py` | event_*, person_*, location_* | ✅ 데이터 있음 |
| `models/event_parent.py` | (events.parent_event_id 컬럼) | ⚠️ 컬럼 있으나 0건 연결 |
| `models/location_name.py` | location_names | ⚠️ 테이블 있으나 비어있음 |
| `models/v1/chain.py` | historical_chains 등 | ❌ DB에 테이블 없음 |
| `models/v1/polity.py` | polities | ❌ DB에 테이블 없음 |
| `models/v2/*.py` | events_v2, clusters 등 | ❌ DB에 테이블 없음 |

**핵심**: models/v1/과 models/v2/의 대부분은 아직 migration이 실행되지 않아 **DB에 존재하지 않는다.** 코드에만 있는 "계획" 상태.

---

## 10. 플랜 문서 논리적 분류

### A. 핵심 (현재 유효, 필수 참고)

| 문서 | 내용 |
|------|------|
| `MASTER_PLAN.md` | 프로젝트 현황 스냅샷 |
| `FINAL_SCHEMA.md` | DB 구조 정의 (확정) |
| `IMPLEMENTATION_PLAN.md` | 구현 진행 상황 |

### B. 이벤트 계층 (현재 대작업)

| 문서 | 내용 |
|------|------|
| `event_hierarchy/INDEX.md` | 마스터 인덱스 |
| `event_hierarchy/00~21` | 설계 21개 문서 |
| `HIERARCHY_METHODOLOGY_REPORT.md` | 방법론 보고서 |
| `HIERARCHY_SYSTEM_REPORT.md` | 시스템 보고서 |

### C. 데이터 모델 (FINAL_SCHEMA에 통합됨 - 참고용)

| 문서 | 내용 | 상태 |
|------|------|------|
| `DATA_MODEL_REDESIGN.md` | Location/Territory, Person/Group 분리 | → FINAL_SCHEMA |
| `DATA_MODEL_SCHEMA.md` | 상세 SQL | → FINAL_SCHEMA |
| `CLEAN_SCHEMA_PLAN.md` | 정리 계획 | → FINAL_SCHEMA |
| `CHALDEAS_UNIFIED_SPEC.md` | 통합 스펙 | → FINAL_SCHEMA |
| `CONCEPT_ENTITY_PROPOSAL.md` | 개념 엔티티 | → FINAL_SCHEMA |

### D. Wikidata (IMPLEMENTATION_PLAN에 반영됨 - 참고용)

| 문서 | 내용 | 상태 |
|------|------|------|
| `WIKIDATA_COMPLETE_STRUCTURE.md` | Wikidata 속성 전체 구조 | 참고용 (속성 목록) |
| `WIKIDATA_IMPORT_REDESIGN.md` | 임포트 재설계 | → IMPLEMENTATION_PLAN |
| `WIKIDATA_MAPPING.md` | QID 매핑 전략 | → IMPLEMENTATION_PLAN |
| `FRESH_WIKIDATA_IMPORT.md` | 새 임포트 계획 | → IMPLEMENTATION_PLAN |
| `UNIFIED_EXTRACTION_SYSTEM.md` | Wikidata+Wikipedia 통합 | 계획 (미구현) |

### E. 파이프라인 (운영 중)

| 문서 | 내용 |
|------|------|
| `PIPELINE_GUIDE.md` | 책 추가 파이프라인 |
| `SOURCE_BOOK_MANAGEMENT.md` | 소스/책 관리 |
| `BOOK_CONTEXT_TRACKING_PLAN.md` | Context 역추적 계획 |
| `BOOK_INTEGRATION_STATUS.md` | 통합 현황 |
| `GUTENBERG_MERGE_PLAN.md` | Gutenberg 병합 |

### F. 분류 & 가중치 (아직 통합 안 됨)

| 문서 | 내용 |
|------|------|
| `CHALDEAS_CLASSIFICATION_SYSTEM.md` | 전체 분류 체계 |
| `ENTITY_IMPORTANCE_RANKING.md` | 엔티티 중요도 |
| `WEIGHTING_SYSTEM.md` | 가중치 시스템 |
| `TEMPORAL_TAG_SYSTEM.md` | 시간 태그 |
| `EVENT_EXPANSION_PLAN.md` | 이벤트 확장 |

### G. 기타

| 문서 | 내용 |
|------|------|
| `FRONTEND_RESTRUCTURE.md` | 프론트엔드 재구성 계획 |
| `PROMPT_ENGINEERING.md` | LLM 프롬프트 가이드 |
| `DATA_INTEGRATION.md` | 데이터 통합 |
| `JOAN_OF_ARC_SHOWCASE.md` | 쇼케이스 예시 |
| `GPU_THERMAL_MANAGEMENT.md` | 하드웨어 참고 |

---

## 11. 핵심 교훈

1. **QID를 처음부터 썼어야 했다.** 이름 매칭으로 쌓은 데이터는 전부 쓰레기.
2. **출처(Source/Mention)가 핵심이다.** "정보가 있다"보다 "어디서 왔는가"가 중요.
3. **로컬 LLM은 추출에 부적합하다.** 분류/파싱은 가능하지만, 엔티티 추출은 API 필수.
4. **스크립트는 일회성이 되기 쉽다.** 표준화된 파이프라인(unified/)이 답.
5. **플랜 문서는 통합해야 한다.** 겹치는 문서 10개보다 통합된 1개가 낫다.
6. **관계가 레벨보다 먼저.** 이벤트 계층은 "소속(P361)"부터 설정 후 레벨을 매기는 게 맞다.

---

## 12. 문서 구조 가이드

이 문서 이후 docs/planning/의 구조는 `INDEX.md`를 참조.
