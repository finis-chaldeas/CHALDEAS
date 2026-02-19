# Next Phase: 통합 미래 계획

> **최종 목표**: FGO만 아는 오타쿠가 들어와서 "역사 재밌네?" 하고 나가는 경험
> **작성**: 2026-02-15
> **최종 갱신**: 2026-02-17
> **통합**: event_hierarchy (FGO/위치/계층 관련) + future_plan (큐레이션/Globe V2) 흡수

---

## 이 폴더의 위치

```
docs/planning/
├── INDEX.md                    ← 전체 인덱스
├── MASTER_PLAN.md              ← 현황 스냅샷
├── FINAL_SCHEMA.md             ← DB 구조 확정
├── IMPLEMENTATION_PLAN.md      ← 구현 진행
├── NEXT_PHASE_PLAN.md          ← 데이터 파이프라인 (Sprint 0)
│
├── next_phase/                 ← ★ 이 폴더 (통합 미래 계획)
│   ├── INDEX.md                ← 이 문서
│   ├── 01_GLOBE_UX.md          ← 지구본 뷰 경험
│   ├── 02_LOCATION_SYSTEM.md   ← 로케이션 시스템
│   ├── 03_FEED_UX.md           ← Feed + 진입점 UX
│   ├── 04_FGO_BRIDGE.md        ← 서번트 ↔ 역사 브릿지
│   ├── 05_DATA_REQUIREMENTS.md ← 데이터 요구사항
│   ├── 06_DATASET_TIERS.md    ← 티어 시스템 + TRISMEGISTUS 확장
│   └── 07_DATASET_SELECTION_CRITERIA.md ← Full/Light 선정 기준 (학술 근거)
│
├── event_hierarchy/            ← 이벤트 계층화 (구조/데이터)
│   ├── 00~12                   ← 계층 구조, 카테고리, 관계 (유지)
│   ├── 13~16                   ← FGO/Multiverse → next_phase로 통합
│   └── 17~21                   ← 계층 구축 전략 (유지)
│
└── future_plan/                ← 미래 계획
    ├── GLOBE_VISUALIZATION_V2  → next_phase/01로 통합
    ├── CURATION_AND_FGO_*      → next_phase/03,04로 통합
    ├── CURATION_SYSTEM         → next_phase/03으로 통합
    ├── STORY_*                 → next_phase/04로 통합
    └── (나머지)                ← Wikidata 자동보강, 사용자 기여 등은 유지
```

---

## 문서 목록

| # | 파일 | 내용 | 흡수한 기존 문서 |
|---|------|------|-----------------|
| 1 | `01_GLOBE_UX.md` | 지구본 뷰 경험 — 4단계 줌, 항공뷰, 라벨 시스템 | `future_plan/GLOBE_VISUALIZATION_V2.md`, `event_hierarchy/00 (줌 필터)` |
| 2 | `02_LOCATION_SYSTEM.md` | 로케이션 상시 표시, 시대별 명칭/소속 변화 | `event_hierarchy/10_LOCATION_HIERARCHY.md` |
| 3 | `03_FEED_UX.md` | Feed 탭 + 4가지 진입점 (SHEBA/LAPLACE/PAPERMOON/TRISMEGISTUS) | `future_plan/CURATION_SYSTEM.md`, `future_plan/STORY_CURATION_SYSTEM.md` |
| 4 | `04_FGO_BRIDGE.md` | 서번트 ↔ 역사 브릿지, 멀티버스, 페르소나, 원전 연결 | `event_hierarchy/13~16 (FGO/Multiverse)`, `future_plan/CURATION_AND_FGO_MASTER_PLAN.md` |
| 5 | `05_DATA_REQUIREMENTS.md` | 모든 기능의 데이터 요구사항, 수집 전략, Sprint 계획 | `classification/ENTITY_IMPORTANCE_RANKING.md`, `future_plan/WIKIDATA_AUTO_ENRICHMENT.md` |
| 6 | `06_DATASET_TIERS.md` | 인물 티어 시스템, 최소 기동 데이터셋, TRISMEGISTUS 확장 | MIT Pantheon 연구, `event_hierarchy/13,16`, 미디어 확장 논의 |
| 7 | `07_DATASET_SELECTION_CRITERIA.md` | Full/Light 선정 기준, 학술 근거, 도메인 커버, 편향 교정 | Pantheon/CVDB/EventKG/Seshat 방법론, AP/IB 커리큘럼, Braudel |
| 8 | `08_PENDING_IMPROVEMENTS.md` | **미구현 작업 + 개선안 전체 정리** (2026-02-17 세션) | 위치 매칭, 데이터 갭, 시각 개선, 파이프라인 |
| 9 | `09_FRONTEND_RESTRUCTURE.md` | **프론트엔드 구조 개편** — 전문가/흥미 레벨 분리, UX 개선 | 2026-02-17 세션 |

---

## 핵심 원칙

1. **지구본이 메인**: 모든 경험은 지구본에서 시작하고 지구본으로 돌아온다
2. **줌 = 디테일**: 멀리서 보면 큰 그림, 가까이 가면 세부 이야기
3. **클릭 한 번의 가치**: 아무거나 눌러도 "읽을 만한" 내용이 나와야 한다
4. **서번트가 입구**: FGO 팬의 자연스러운 진입점은 아는 캐릭터
5. **계층 = 이해**: 이벤트 계층(Era → Mega → Aggregate → Major → Minor)이 복잡한 역사를 소화 가능하게 만든다

---

## 유저 페르소나 & 경험 레벨

### 흥미 레벨 (Interest Level) — "재밌네?" 경험

> 처음 온 유저가 **5분 안에** "역사 재밌네?" 하고 느끼게 만드는 것

| 페르소나 | 설명 | 원하는 것 | 진입점 |
|----------|------|-----------|--------|
| **A. FGO 오타쿠** (주 타겟) | 서번트 이름은 안다, 역사는 모른다 | "이 캐릭터 실제로 뭐 했어?" | TRISMEGISTUS, SHEBA |
| **B. 일반 방문자** | 지구본이 멋있어서 클릭함 | 흥미로운 이야기, 비주얼 | SHEBA, 지구본 자유 탐색 |

**핵심 원칙**:
- 긴 글 NO → 카드, 비주얼, 한 줄 요약
- 선택지 적게 → 추천 에피소드 3개면 충분
- 클릭 한 번 = 읽을 만한 콘텐츠
- 서번트/에피소드가 "낚시바늘" 역할

### 전문가 레벨 (Expert Level) — "더 깊이!" 경험

> 흥미 레벨에서 흥미를 느낀 유저가 **스스로 깊이 파고드는** 것

| 페르소나 | 설명 | 원하는 것 | 진입점 |
|----------|------|-----------|--------|
| **C. 역사 관심자** | 특정 시대/지역에 관심 | 지구본 시공간 탐색, 상세 정보 | LAPLACE, 지구본 직접 탐색 |
| **D. 연구자/학생** | 인과관계, 네트워크 분석 | 출처, 학술적 분류, 데이터 | Chains, 검색, 계층 트리 |

**핵심 원칙**:
- 데이터 밀도 높게 → 목록, 필터, 정렬, 소스
- 지구본 = 분석 도구 (줌/패닝/시간축)
- 클릭 → 상세 뷰 → 관련 엔티티 네트워크
- 모든 정보에 출처 표시

### 두 레벨의 관계

```
흥미 레벨 (기본)                    전문가 레벨 (전환)
┌────────────────────┐            ┌────────────────────┐
│ 추천 에피소드       │  "더 알고  │ 상세 이벤트 목록    │
│ 서번트 카드         │  싶다!"   │ 인물 네트워크       │
│ 한 줄 역사 요약     │ ───────→ │ 출처 + 원문         │
│ 지구본 자유 탐색    │           │ 타임라인 분석       │
└────────────────────┘            └────────────────────┘

진입 = 무조건 흥미 레벨
전환 = 유저가 직접 선택 ("상세 보기", "Expert Mode")
```

→ **상세: `09_FRONTEND_RESTRUCTURE.md`**

---

## 진입점 시스템 (FGO 칼데아스 시설 네이밍)

| 시스템 | 역할 | 대상 | 문서 |
|--------|------|------|------|
| **SHEBA** | 추천 에피소드 관측 | 처음 오는 모든 유저 | 03_FEED_UX.md |
| **LAPLACE** | 세계사 연표 안내 | 역사 관심자 | 03_FEED_UX.md |
| **PAPERMOON** | 주요 인물 갤러리 | 인물 중심 탐색 | 03_FEED_UX.md |
| **TRISMEGISTUS** | 영령 ↔ 역사 통합 안내 | FGO 팬 | 04_FGO_BRIDGE.md |

---

## 통합 구현 로드맵

### Sprint 0: 데이터 기반
- [x] Feed API 구현 (backend)
- [x] FeedTab 프론트엔드
- [ ] entity_properties → persons 반영
- [ ] QRank + importance 재계산
- [ ] Wikipedia biography 추출

### Sprint 0.5: UX 4 Entry Points (2026-02-17 완료)
- [x] Navigator 4탭 재구성 (SHEBA/PAPERMOON/LAPLACE/TRISMEGISTUS)
- [x] 4단계 Globe 줌 시스템 (cosmic/continental/regional/local)
- [x] SHEBA 에피소드 18개 정적 데이터
- [x] LAPLACE 타임라인 6에라 57개
- [x] ServantTab (모달 → 인라인)
- [x] flyToLocation globe 카메라 이동
- [x] Location.type Optional 버그 수정

### Sprint 0.7: 위치 매칭 + 노드 시스템 (2026-02-17 진행 중)
- [x] **노드 기반 위치 시스템 확정** (locations = 고정 노드, 이벤트 → 최근접 노드)
- [x] **Backend: Globe Node API** (`GET /globe/nodes`, `GET /globe/nodes/{id}/events`)
- [x] **Frontend: 노드 마커 시스템** (이벤트 수 배지, 줌별 필터링, active/inactive)
- [~] **Wikidata 덤프 스캔 진행 중** — 89% 완료 (24,132/28,331 발견, 좌표 10,623개)
  - `poc/scripts/wikidata/match_event_locations.py --scan`
  - 체크포인트: `data/compact_export/event_sitelinks.jsonl`
- [ ] Phase 2: `--match` 실행 → 최근접 노드 매칭 (numpy haversine)
- [ ] Phase 3: 매칭 결과 DB 반영 (primary_location_id UPDATE)

### Sprint 1: 데이터 품질 + UX 개편
- [ ] **프론트엔드 구조 개편** — 전문가/흥미 레벨 분리 (09_FRONTEND_RESTRUCTURE.md)
- [ ] **Compact DB 서번트 person 6명 이관** (B2)
- [ ] **persons.biography Wikipedia 추출** (B2)
- [ ] **로케이션 상시 표시** (Tier 시스템, 노드 API 활용)
- [ ] Feed에 Wikipedia description

### Sprint 2: 라벨 + 큐레이션
- [ ] 글로벌 뷰 주요 사건 라벨 개선
- [ ] SHEBA 추천 에피소드 30개로 확장
- [ ] servants.json 100개 확장
- [ ] location_names 50개 수동 큐레이션

### Sprint 3: 로케이션 + 뷰 전환
- [ ] 시대별 명칭 API + 글로브 표시
- [ ] 줌 레벨별 조작 전환 (회전 → 패닝)
- [ ] Aggregate 이벤트 50개 생성 + 계층 연결
- [ ] LLM 지오코딩 (나머지 이벤트)

### Sprint 4: 서번트 브릿지
- [ ] servant_profiles 테이블 + Atlas Academy 임포트
- [ ] 비교 카드 (게임 vs 역사)
- [ ] Singularity/Lostbelt → 역사 시대 매핑

### Backlog (장기)
- [ ] 영토 폴리곤 시각화 (PostGIS)
- [ ] 진군 경로 애니메이션
- [ ] 페르소나 내러티브 시스템 (LLM on-demand)
- [ ] FGO 스토리 스크립트 검색
- [ ] Simple English Wikipedia
- [ ] 사용자 기여 시스템

---

## event_hierarchy/ 와의 관계

`event_hierarchy/` 폴더는 이벤트 **구조화**(스키마, 카테고리, 관계, 파이프라인)를 담당하고,
`next_phase/` 폴더는 **UX 경험**(어떻게 보여줄 것인가)을 담당한다.

### event_hierarchy에서 유지되는 것 (데이터/구조)
- `00_OVERVIEW.md` — Aggregate 이벤트 목록, hierarchy_level 정의
- `01_SCHEMA.md` — DB 마이그레이션
- `02~06` — 카테고리별 이벤트 목록 (전쟁, 철학, 예술, 과학, 종교)
- `07~09` — 이벤트 관계, 벡터 모델, 파이프라인
- `10_LOCATION_HIERARCHY.md` — 장소 계층 (데이터 구조)
- `11_UNIFIED_MODEL.md` — HistoricalUnit 통합 모델
- `12_PERIOD_EXTRACTION.md` — 시대 추출
- `17~21` — 계층 구축 전략 (Wikidata P361, LLM, 다중 부모)

### next_phase로 통합된 것 (UX/경험)
- `13_FGO_DATA_LAYER.md` → `04_FGO_BRIDGE.md` (서번트 DB 구조, 소스 책 매핑)
- `14_FGO_ENHANCEMENT.md` → `04_FGO_BRIDGE.md` (서번트 분류 체계, UX 시나리오)
- `15_FGO_MINI.md` → `04_FGO_BRIDGE.md` (미니 프로젝트 → 에피소드 큐레이션)
- `16_MULTIVERSE_MODEL.md` → `04_FGO_BRIDGE.md` (universe/canonical_id)

### future_plan에서 통합된 것
- `GLOBE_VISUALIZATION_V2.md` → `01_GLOBE_UX.md` (영토/경로 시각화 컨셉)
- `CURATION_AND_FGO_MASTER_PLAN.md` → `03_FEED_UX.md` + `04_FGO_BRIDGE.md`
- `CURATION_SYSTEM.md` → `03_FEED_UX.md` (AI 큐레이터)
- `STORY_CURATION_SYSTEM.md` → `04_FGO_BRIDGE.md` (페르소나, 내러티브)
- `STORY_IMPLEMENTATION.md` → `04_FGO_BRIDGE.md` (스토리 구현)

### future_plan에서 유지되는 것 (아직 통합 불필요)
- `WIKIDATA_AUTO_ENRICHMENT.md` — 장기 자동화
- `WIKIDATA_FACTGRID_EXPANSION.md` — FactGrid 연동
- `USER_DATA_CONTRIBUTION.md` — 사용자 기여
- `USER_DATA_PIPELINE_DESIGN.md` — 사용자 파이프라인
- `OPEN_CURATION_VISION.md` — 오픈 큐레이션 비전
- `DATA_INGESTION_PIPELINE.md` — V3 데이터 진입
- `SYSTEM_GAPS_AND_SOLUTIONS.md` — 시스템 갭 분석
