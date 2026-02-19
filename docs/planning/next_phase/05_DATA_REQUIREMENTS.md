# 05. 데이터 요구사항 & 수집 전략

> 각 UX 기능별 필요 데이터, 소스, 수집 방법, 우선순위를 정리한다.

---

## 데이터 현황 요약

| 항목 | 현재 | 필요 | 소스 | 상태 |
|------|------|------|------|------|
| events | 28,331 | + Aggregate 300개 | Wikidata/수동 | |
| events.importance | 1-5 분포 (NTILE) | 1-5 분포 | QRank + composite | **완료** |
| events.is_light | 28,331 TRUE (100%) | - | - | **완료** |
| events.description | 1줄 wikidata | 2-3문장 | Wikipedia | |
| persons | 12,987,361 | 충분 | - | |
| persons.is_light | 190,710 TRUE (1.5%) | - | event_persons + QRank | **완료** |
| persons.role | 100,597건 (light 52.7%) | ~7M (전체) | entity_properties P106 | **light 완료** |
| persons.biography | 0건 | ~90K (이벤트 연결된) | Wikipedia sources | |
| persons.birthplace_id | 30,822건 (light 16.2%) | ~2M (전체) | entity_properties P19 | **light 완료** |
| persons.deathplace_id | 17,571건 (light 9.2%) | ~2M (전체) | entity_properties P20 | **light 완료** |
| persons.birth_year | 181,913건 (light 95.4%) | - | - | **완료** |
| locations | 2,387,834 | 충분 | - | |
| locations.is_light | 12,908 TRUE (0.5%) | - | events + person places | **완료** |
| location_names (시대별) | 0건 | ~500 주요 도시 | Wikidata P1448 | |
| location_polities (소속) | 0건 | ~500 주요 도시 | Wikidata P17 | |
| qrank | 28,691,759건 | - | qrank.toolforge.org | **완료** |
| servant_profiles | 0건 | ~300 | Atlas Academy | |
| highlights (큐레이션) | 0건 | ~50 | 수동 + LLM | |
| story_contents (내러티브) | 0건 | On-demand | LLM 생성 | |

---

## 기능별 데이터 의존성

### 01. 지구본 뷰 개선

| 기능 | 필요 데이터 | 우선순위 |
|------|------------|---------|
| 글로벌 뷰 주요 사건 라벨 | `events.importance` 분포 (QRank 기반) | **필수** |
| 줌 레벨별 마커 필터 | `events.importance` + `hierarchy_level` | **필수** |
| 이벤트 카테고리 색상 | `events.category` (이미 있음) | 있음 |
| 로케이션 앵커 상시 표시 | `locations` + event_count 계산 | 쉬움 |
| 시대별 히트맵 | 이벤트 밀도 계산 (쿼리) | 중 |
| 연결 라인 (인물 경로) | `event_persons` + location 조인 | 중 |
| 영토 폴리곤 | **event_regions** (PostGIS) — 미래 | 장기 |
| 진군 경로 애니메이션 | **event_movements** (PostGIS) — 미래 | 장기 |

### 02. 로케이션 시스템

| 기능 | 필요 데이터 | 우선순위 |
|------|------------|---------|
| 시대별 명칭 | `location_names` 테이블 (마이그레이션 008) | **필수** |
| 시대별 소속 | `location_polities` 테이블 (신규) | 중 |
| Tier 시스템 | `locations` + event_count 집계 | 쉬움 |
| 지역 그룹핑 | `locations.region`, `country` (이미 있음) | 있음 |

### 03. Feed + 진입점

| 기능 | 필요 데이터 | 우선순위 |
|------|------------|---------|
| Feed 카드 (events) | importance, description, location_name | **필수** |
| Feed 카드 (persons) | role, biography, event_count | **필수** |
| SHEBA 추천 에피소드 | `highlights` 테이블 (수동 큐레이션) | **높음** |
| LAPLACE 세계사 연표 | `events` + `hierarchy_level=0,1,2` | 중 |
| PAPERMOON 주요 인물 | persons + importance + role | 중 |
| TRISMEGISTUS 서번트 | `servant_profiles` + canonical_id | 중 |

### 04. 서번트 브릿지

| 기능 | 필요 데이터 | 우선순위 |
|------|------------|---------|
| 서번트 목록 | `servants.json` 확장 → servant_profiles | **높음** |
| 역사 인물 매칭 | canonical_id 매핑 | **높음** |
| 비교 카드 | servant_profiles.historical_fact + fate_interpretation | 중 |
| 원전 연결 | sources + text_mentions 매칭 | 중 |
| Singularity 매핑 | 수동 데이터 (8 Singularity × 역사 시대) | 쉬움 |
| 페르소나 내러티브 | story_contents (LLM 생성) | 장기 |

---

## 데이터 수집 전략

### 1. entity_properties → persons 반영 (SQL) — **완료**

**스크립트**: `backend/scripts/enrich_light_persons.py`

Light persons (190,710명)만 대상으로 enrichment 완료:
```
persons.role       ← P106 occupation: 98,292행 (50분)
persons.birthplace_id ← P19: 30,822행 (44분)
persons.deathplace_id ← P20: 17,571행 (15분)
```
birth_year, death_year는 이미 Wikidata 임포트 시 반영됨 (181,913건, 95.4%)

**총 실행 시간**: 4시간 52분 (외부 USB HDD, entity_properties 112M행)

### 2. QRank 임포트 + importance 재계산 — **완료**

**스크립트**: `backend/scripts/import_qrank.py`, `backend/scripts/compute_importance.py`

```
qrank 테이블: 28,691,759행 임포트 (UNLOGGED + COPY 전략)
events.importance = NTILE(5) over composite_score
  composite = 0.50*qrank + 0.30*connection_count + 0.20*participant_count
결과: importance 1~5 각 ~5,666개 균등 분배
```

### 3. is_light 엔티티 분류 — **완료**

```
persons.is_light: 190,710 TRUE (event_persons 90K + QRank top 100K)
events.is_light: 28,331 TRUE (전체)
locations.is_light: 12,908 TRUE (event연결 2,921 + person 출생/사망지 9,987)
부분 인덱스: idx_persons/events/locations_is_light
```

### 4. Wikipedia biography 추출 (Python) — 미실행

**스크립트**: `backend/scripts/extract_biographies.py`

```
sources 테이블에 wikipedia 2.5M건 중
→ event_persons에 연결된 ~90K 인물의 Wikipedia에서
→ 첫 문단 추출 → persons.biography 업데이트
```

**비용**: 무료 (로컬 데이터)
**시간**: ~1시간
**주의**: sources.content가 실제 본문을 담고 있는지 확인 필요

### 4. Wikipedia event description 추출 (Python, 신규)

기존 `events.description` = Wikidata 1줄 → Wikipedia 첫 2-3문장으로 교체

```python
# 신규 스크립트: backend/scripts/extract_event_descriptions.py
# 로직: extract_biographies.py와 동일 패턴
# 대상: sources WHERE source_type='wikipedia' AND entity_type='event'
```

**비용**: 무료 (로컬 데이터)
**시간**: ~30분

### 5. location_names 데이터 (Wikidata P1448)

시대별 명칭 데이터 수집 방법:

**Option A: Wikidata SPARQL (주요 도시 500개)**
```sparql
SELECT ?city ?cityLabel ?name ?start ?end WHERE {
  ?city wdt:P31/wdt:P279* wd:Q515 .
  ?city p:P1448 ?stmt .
  ?stmt ps:P1448 ?name .
  OPTIONAL { ?stmt pq:P580 ?start }
  OPTIONAL { ?stmt pq:P582 ?end }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
LIMIT 5000
```

**Option B: Wikidata dump에서 추출**
```python
# E:\wikidata\latest-all.json 에서 P1448 추출
# 이미 덤프가 있으므로 API 제한 없음
```

**Option C: 수동 큐레이션 (50개 핵심 도시)**
```
Constantinople/Istanbul, Byzantium → Constantinople → Istanbul
Beijing/Peking, Dadu → Beijing
Mumbai/Bombay, Bombay → Mumbai
...
```

**권장**: Option C (50개 수동) → Option A (500개 SPARQL) → Option B (전체)

### 6. location_polities 데이터 (Wikidata P17)

```sparql
SELECT ?city ?cityLabel ?country ?countryLabel ?start ?end WHERE {
  ?city wdt:P31/wdt:P279* wd:Q515 .
  ?city p:P17 ?stmt .
  ?stmt ps:P17 ?country .
  OPTIONAL { ?stmt pq:P580 ?start }
  OPTIONAL { ?stmt pq:P582 ?end }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
```

**권장**: Phase 2에서 주요 도시 500개만

### 7. Highlights 큐레이션 (수동 + LLM)

30-50개 시대/에피소드 큐레이션:

```json
{
  "id": "hundred-years-war",
  "title": "Hundred Years' War",
  "title_ko": "백년전쟁",
  "period": [1337, 1453],
  "region": "France/England",
  "center_lat": 48.86, "center_lng": 2.35,
  "summary": "잉글랜드와 프랑스가 116년간 벌인 전쟁. 잔 다르크의 등장으로 프랑스가 승리.",
  "key_events": ["Battle of Crécy", "Siege of Orléans", "Battle of Castillon"],
  "servants": ["Jeanne d'Arc", "Gilles de Rais"],
  "difficulty": "beginner",
  "thumbnail": "hundred_years_war.jpg"
}
```

**생성 방법**:
1. LLM으로 초안 30개 생성 (~$2)
2. 수동 검수 + 서번트 매핑 확인
3. key_events를 실제 event_id로 매핑

**우선순위 에피소드 목록**:
1. 잔 다르크와 백년전쟁
2. 아서 왕 전설과 브리튼의 몰락
3. 알렉산더 대왕의 동방원정
4. 메소포타미아 — 문명의 새벽
5. 페르시아 전쟁과 그리스의 영광
6. 로마 공화정의 종말
7. 십자군 전쟁
8. 몽골 제국의 세계 정복
9. 르네상스와 예술의 부활
10. 프랑스 혁명
11. 트로이 전쟁
12. 바이킹 시대
13. 나폴레옹 전쟁
14. 대항해시대
15. 인도 서사시 (마하바라타)

### 8. Servant Profiles 확장 (Atlas Academy + 수동)

```python
# 1. Atlas Academy API에서 기본 정보 수집
# GET https://api.atlasacademy.io/nice/NA/servant/{id}
# → name, class, rarity, noble_phantasm

# 2. 역사 인물 매칭 (persons 테이블)
# servant.name → persons WHERE wikidata_id = ...

# 3. historical_fact, fate_interpretation은 수동 작성 또는 LLM 생성
```

**기존 데이터**: `backend/app/data/showcases/servants.json` (2개)
**목표**: 100개+ (Phase 1), 300개+ (Phase 2)

### 9. Aggregate Events 생성 (이벤트 계층화)

**이미 상세 목록 존재**: `event_hierarchy/00_OVERVIEW.md` (02~06 카테고리별)

```
Phase 1: 핵심 Aggregate 50개 생성 (is_aggregate=true, hierarchy_level=2)
Phase 2: 기존 이벤트를 Aggregate에 연결 (parent_event_id 설정)
Phase 3: 키워드 + 시간/공간 매칭으로 자동 연결 스크립트
```

**스크립트 기존**: `event_hierarchy/00_OVERVIEW.md`의 Section 7.4에 자동화 예시

---

## 실행 순서 (Sprint 계획)

### Sprint 0: 데이터 기반 — **완료** (2026-02-16)
- [x] Feed API 구현
- [x] FeedTab 프론트엔드
- [x] entity_properties → persons 반영 (light 190K만)
- [x] QRank 임포트 (28.7M행)
- [x] importance 재계산 (1~5 NTILE)
- [x] is_light 엔티티 분류 + 인덱스
- [ ] Wikipedia biography 추출 (sources.content 확인 필요)

### Sprint 1: 즉시 개선 (코드만)
- [ ] 로케이션 상시 표시 (Tier 시스템)
- [ ] 서번트 → 시대 탐색 버튼
- [ ] Feed에 Wikipedia description 표시

### Sprint 2: 라벨 + 큐레이션 (1주)
- [ ] 글로벌 뷰 주요 사건 라벨 (labelsData)
- [ ] Highlight 큐레이션 30개 작성
- [ ] servants.json 확장 (100개)

### Sprint 3: 로케이션 + 뷰 전환 (2주)
- [ ] location_names 데이터 수집 (50개 수동)
- [ ] 시대별 명칭 API + 글로브 표시
- [ ] 줌 레벨별 조작 전환 (회전 → 패닝)

### Sprint 4: 서번트 브릿지 (2주)
- [ ] servant_profiles 테이블 + 임포트
- [ ] 비교 카드 UI
- [ ] Singularity 매핑

### Backlog
- [ ] location_polities (시대별 소속)
- [ ] 영토 폴리곤 시각화 (PostGIS)
- [ ] 진군 경로 애니메이션
- [ ] Simple English Wikipedia 옵션
- [ ] 페르소나 내러티브 시스템
- [ ] FGO 스토리 스크립트 검색

---

## 비용 요약

| 항목 | 소스 | 비용 |
|------|------|------|
| QRank | qrank.toolforge.org | 무료 |
| Wikipedia description | 로컬 sources 테이블 | 무료 |
| Wikipedia biography | 로컬 sources 테이블 | 무료 |
| Location names | Wikidata SPARQL / dump | 무료 |
| Location polities | Wikidata SPARQL / dump | 무료 |
| Highlights 큐레이션 | LLM (gpt-5-mini) 초안 | ~$2 |
| Servant profiles | Atlas Academy API | 무료 |
| 내러티브 생성 | On-demand LLM (gpt-5-nano) | ~$5-10/월 |
| **합계 (초기)** | | **~$5** |
| **합계 (월간)** | | **~$5-10** |

---

## 테이블 생성 요약

### 이미 존재하는 테이블
- `location_names` (마이그레이션 008)
- `event_parents` (마이그레이션 007)
- `qrank` (스크립트로 생성)

### 신규 필요 테이블

```sql
-- 1. location_polities (시대별 소속)
CREATE TABLE location_polities (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    polity_name VARCHAR(255) NOT NULL,
    polity_name_ko VARCHAR(255),
    polity_wikidata_id VARCHAR(50),
    valid_from INTEGER,
    valid_until INTEGER,
    source VARCHAR(100)
);

-- 2. highlights (큐레이션 에피소드)
CREATE TABLE highlights (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    title_ko VARCHAR(255),
    period_start INTEGER,
    period_end INTEGER,
    region VARCHAR(255),
    center_lat FLOAT,
    center_lng FLOAT,
    summary TEXT,
    summary_ko TEXT,
    difficulty VARCHAR(20) DEFAULT 'beginner',
    display_order INTEGER DEFAULT 0
);

-- 3. highlight_items (에피소드 ↔ 이벤트/서번트 연결)
CREATE TABLE highlight_items (
    id SERIAL PRIMARY KEY,
    highlight_id INTEGER REFERENCES highlights(id),
    item_type VARCHAR(20) NOT NULL,  -- 'event', 'person', 'servant'
    item_id INTEGER NOT NULL,
    display_order INTEGER DEFAULT 0
);

-- 4. universes (세계관)
CREATE TABLE universes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(30) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    name_ko VARCHAR(100),
    is_canonical BOOLEAN DEFAULT FALSE,
    color VARCHAR(7)
);

-- 5. servant_profiles (FGO 전용)
CREATE TABLE servant_profiles (
    id SERIAL PRIMARY KEY,
    person_id INTEGER REFERENCES persons(id),
    servant_class VARCHAR(50),
    rarity INTEGER,
    noble_phantasm_name VARCHAR(200),
    origin_type VARCHAR(50),
    atlas_id INTEGER,
    historical_fact TEXT,
    fate_interpretation TEXT,
    portrait_url TEXT,
    UNIQUE(person_id)
);

-- 6. story_contents (내러티브 캐시)
CREATE TABLE story_contents (
    id SERIAL PRIMARY KEY,
    story_type VARCHAR(20) NOT NULL,
    subject_id INTEGER NOT NULL,
    event_id INTEGER REFERENCES events(id),
    node_order INTEGER,
    narrative_en TEXT,
    narrative_ko TEXT,
    persona VARCHAR(20) DEFAULT 'official',
    generated_by VARCHAR(50),
    generated_at TIMESTAMP DEFAULT NOW(),
    is_verified BOOLEAN DEFAULT FALSE,
    UNIQUE(story_type, subject_id, event_id, persona)
);

-- 7. story_sources (출처 연결)
CREATE TABLE story_sources (
    id SERIAL PRIMARY KEY,
    story_content_id INTEGER REFERENCES story_contents(id) ON DELETE CASCADE,
    source_type VARCHAR(20),
    source_id INTEGER REFERENCES sources(id),
    title VARCHAR(500),
    excerpt TEXT,
    excerpt_translation TEXT,
    display_order INTEGER DEFAULT 0
);
```

---

## 기존 문서 통합 참조

이 문서는 다음 기존 문서들의 데이터 요구사항을 통합한 것:

| 기존 문서 | 통합된 내용 |
|----------|------------|
| `NEXT_PHASE_PLAN.md` | Phase 1-8 데이터 파이프라인 |
| `event_hierarchy/00_OVERVIEW.md` | Aggregate 이벤트 목록, hierarchy_level |
| `event_hierarchy/13_FGO_DATA_LAYER.md` | 서번트 DB 구조, 소스 책 매핑 |
| `event_hierarchy/14_FGO_ENHANCEMENT.md` | 서번트 분류 체계, 데이터 수집 |
| `event_hierarchy/16_MULTIVERSE_MODEL.md` | universe/canonical_id 구조 |
| `future_plan/CURATION_AND_FGO_MASTER_PLAN.md` | story_contents/sources, 페르소나, 비용 |
| `future_plan/GLOBE_VISUALIZATION_V2.md` | event_regions/movements (장기) |
| `future_plan/WIKIDATA_AUTO_ENRICHMENT.md` | Wikidata 속성 추출 전략 |
| `classification/ENTITY_IMPORTANCE_RANKING.md` | importance 계산 방법 |
