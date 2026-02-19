# CHALDEAS 데이터 통합 아키텍처

## 개요

CHALDEAS는 여러 데이터 소스에서 수집한 정보를 통합하여 시맨틱 네트워크를 구축합니다.

---

## 데이터 소스

| 소스 | 데이터 유형 | 수집 방식 | 수량 |
|------|------------|----------|------|
| **Wikidata** | 엔티티 기본정보, QID | SPARQL/API | 522K 엔티티 |
| **Wikidata** | 별칭 (labels + aliases) | API (wbgetentities) | 1.58M aliases |
| **Wikidata** | 속성 (좌표, 관계, 분류) | API (claims) | 22K+ 관계 |
| **Wikipedia** | 문서 링크, 본문 | ZIM 파일 파싱 | 15M+ mentions |
| **Gutenberg** | 책 본문, 엔티티 언급 | ZIM + LLM 추출 | (예정) |

---

## 테이블 구조

### 핵심 엔티티 테이블

```
┌─────────────────────────────────────────────────────────────┐
│  persons / events / locations                               │
├─────────────────────────────────────────────────────────────┤
│  id              SERIAL PRIMARY KEY                         │
│  name            VARCHAR(500)                               │
│  wikidata_id     VARCHAR(20)  ← 통합 키                     │
│  birth_date      INTEGER (BCE는 음수)                       │
│  death_date      INTEGER                                    │
│  latitude        FLOAT (locations만)                        │
│  longitude       FLOAT (locations만)                        │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
```

### 보조 테이블

```
┌─────────────────────────────────────────────────────────────┐
│  entity_aliases (별칭)                                      │
├─────────────────────────────────────────────────────────────┤
│  entity_type     ENUM('person', 'event', 'location')        │
│  entity_id       INTEGER → FK                               │
│  alias           VARCHAR(500)                               │
│  alias_type      ENUM('translation', 'wikidata', ...)       │
│  language        VARCHAR(10) ('en', 'ko', 'la', ...)        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  links (관계)                                               │
├─────────────────────────────────────────────────────────────┤
│  from_type       ENUM('person', 'event', 'location')        │
│  from_id         INTEGER                                    │
│  to_type         ENUM('person', 'event', 'location')        │
│  to_id           INTEGER                                    │
│  category        VARCHAR(50) ('father', 'participant', ...) │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  mentions (증거)                                            │
├─────────────────────────────────────────────────────────────┤
│  source_id       INTEGER → sources.id                       │
│  link_id         INTEGER → links.id                         │
│  context         TEXT (문장 컨텍스트)                        │
│  position        INTEGER (문서 내 위치)                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  sources (출처)                                             │
├─────────────────────────────────────────────────────────────┤
│  source_type     ENUM('wikipedia', 'gutenberg', ...)        │
│  source_ref      VARCHAR(500) (문서 제목, 책 ID)            │
│  entity_type     ENUM('person', 'event', 'location')        │
│  entity_id       INTEGER                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 데이터 통합 흐름

### 1단계: Wikidata 엔티티 수집 (완료)

```
Wikidata SPARQL → persons/events/locations 테이블
                  (wikidata_id = Q번호)
```

### 2단계: Wikidata 별칭 수집 (완료)

```
Wikidata API (wbgetentities)
    ↓
┌─────────────────────────────────────────┐
│ labels (각 언어별 대표 이름)            │
│   → alias_type = 'translation'          │
│   예: Mozart(en), 모차르트(ko)          │
├─────────────────────────────────────────┤
│ aliases (각 언어별 별칭들)              │
│   → alias_type = 'wikidata'             │
│   예: Wolfgang Amadeus Mozart           │
└─────────────────────────────────────────┘
    ↓
entity_aliases 테이블 (1.58M rows)
```

### 3단계: Wikidata 속성 수집 (진행 중)

```
Wikidata API (claims)
    ↓
┌─────────────────────────────────────────┐
│ P625 (좌표)                             │
│   → locations.latitude/longitude        │
├─────────────────────────────────────────┤
│ P22/P25/P26/P40 (가족관계)              │
│   → links (category: father/mother/...) │
├─────────────────────────────────────────┤
│ P710/P1344 (이벤트 참가)                │
│   → links (category: participant)       │
├─────────────────────────────────────────┤
│ P31/P279 (분류)                         │
│   → 온톨로지 구축용 (추후 활용)         │
└─────────────────────────────────────────┘
```

### 4단계: Wikipedia 문서 추출 (진행 중)

```
Wikipedia ZIM 파일
    ↓
문서 본문에서 링크 추출
    ↓
┌─────────────────────────────────────────┐
│ 링크 타겟 → sitelinks/aliases로 매칭   │
│   매칭 성공 → links + mentions 생성     │
│   매칭 실패 → tentative_entities 저장   │
└─────────────────────────────────────────┘
```

---

## 엔티티 매칭 전략

### 매칭 우선순위

1. **Wikidata sitelinks** (가장 정확)
   - Wikipedia 문서 제목 → 엔티티 직접 매핑
   - 291,204개 매핑

2. **entity_aliases** (폭넓은 커버리지)
   - 모든 언어의 별칭으로 검색
   - 1,581,555개 별칭

3. **Fuzzy matching** (폴백)
   - 정확한 매칭 실패 시 유사도 검색
   - 임계값: 0.85

### 매칭 실패 처리

```
매칭 실패한 엔티티 → tentative_entities 테이블
    ↓
나중에 LLM으로 분류 (person/event/location)
    ↓
실제 테이블에 생성 + wikidata_id 추가
```

---

## 시맨틱 네트워크 구조

### 노드 (Nodes)

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│ persons  │  │  events  │  │locations │
│ (522K)   │  │  (56K)   │  │  (40K)   │
└──────────┘  └──────────┘  └──────────┘
```

### 엣지 (Edges) - links 테이블

| category | from_type | to_type | 설명 |
|----------|-----------|---------|------|
| father | person | person | 아버지 |
| mother | person | person | 어머니 |
| spouse | person | person | 배우자 |
| child | person | person | 자녀 |
| participant | event | person | 이벤트 참가자 |
| participated_in | person | event | 참여한 이벤트 |
| occurred_at | event | location | 발생 장소 |
| mentioned | * | * | 문서 내 언급 |

### 증거 (Evidence) - mentions 테이블

모든 links는 최소 하나의 mention을 가짐:
- 출처 문서 (sources)
- 컨텍스트 텍스트
- 문서 내 위치

---

## 쿼리 예시

### 가족관계 탐색

```sql
-- 나폴레옹의 가족 찾기
SELECT p2.name, l.category
FROM persons p1
JOIN links l ON l.from_type = 'person' AND l.from_id = p1.id
JOIN persons p2 ON l.to_type = 'person' AND l.to_id = p2.id
WHERE p1.name = 'Napoleon Bonaparte'
  AND l.category IN ('father', 'mother', 'spouse', 'child');
```

### 별칭으로 엔티티 찾기

```sql
-- "아서왕"으로 King Arthur 찾기
SELECT p.id, p.name, ea.alias, ea.language
FROM persons p
JOIN entity_aliases ea ON ea.entity_type = 'person' AND ea.entity_id = p.id
WHERE ea.alias ILIKE '%arthur%' OR ea.alias ILIKE '%아서%';
```

### 이벤트 참가자 조회

```sql
-- 워털루 전투 참가자
SELECT p.name
FROM events e
JOIN links l ON l.from_type = 'event' AND l.from_id = e.id
JOIN persons p ON l.to_type = 'person' AND l.to_id = p.id
WHERE e.name = 'Battle of Waterloo'
  AND l.category = 'participant';
```

---

## 향후 확장

### 1. 온톨로지 계층

Wikidata P31/P279를 활용한 분류 체계:
```
나폴레옹 → instance_of → 황제 → subclass_of → 군주 → subclass_of → 인물
```

### 2. 추론 규칙

```
IF father(A, B) AND father(B, C) THEN grandfather(A, C)
IF participated_in(Person, Event) AND occurred_at(Event, Place)
   THEN was_at(Person, Place)
```

### 3. 시간적 추론

이벤트 순서에 기반한 인과관계 추론

### 4. 그래프 DB 고려

복잡한 경로 쿼리가 많아지면 Neo4j 도입 검토

---

## 스크립트 참조

| 스크립트 | 용도 |
|----------|------|
| `poc/scripts/unified/fetch_wikidata_aliases.py` | Wikidata 별칭 수집 |
| `poc/scripts/unified/fetch_wikidata_properties.py` | Wikidata 속성 수집 |
| `poc/scripts/unified/extract_wikipedia.py` | Wikipedia 문서 추출 |
| `poc/scripts/unified/run_wikidata_full.py` | Wikidata 통합 실행 |

---

## 현재 데이터 현황 (2026-02-02)

| 항목 | 수량 |
|------|------|
| persons | 425,552 |
| events | 56,567 |
| locations | 40,613 |
| entity_aliases | 1,581,555 |
| links | 6M+ |
| mentions | 8.6M+ |
| sources | 50K+ |
