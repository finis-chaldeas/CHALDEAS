# 개념/사조/시대 엔티티 추가 기획서

> **작성일**: 2026-02-06
> **목적**: 인물/장소/사건 외에 추상적 개념(르네상스, 계몽주의 등) 통합

---

## 1. 문제 정의

### 1.1 현재 상태

현재 CHALDEAS는 5가지 엔티티 타입만 지원:

| 타입 | 예시 | P31 기준 |
|------|------|----------|
| person | 레오나르도 다빈치 | Q5 (human) |
| location | 피렌체 | 좌표 있는 엔티티 |
| territory | 이탈리아 | Q6256 (country) 등 |
| group | 메디치 가문 | Q37726 (dynasty) 등 |
| event | 이탈리아 전쟁 | Q178561 (battle) 등 |

### 1.2 누락된 개념들

역사 이해에 필수적인 추상 개념들이 누락됨:

| 개념 | Wikidata | 현재 상태 |
|------|----------|----------|
| 르네상스 | Q4692 | ❌ 누락 |
| 바로크 | Q37853 | ❌ 누락 |
| 계몽주의 | Q12539 | ❌ 누락 |
| 산업혁명 | Q2269 | ❌ 누락 |
| 종교개혁 | Q12546 | ❌ 누락 |
| 낭만주의 | Q37068 | ❌ 누락 |
| 고전주의 | Q164800 | ❌ 누락 |
| 인문주의 | Q1158924 | ❌ 누락 |

### 1.3 왜 중요한가

1. **맥락 제공**: "다빈치는 르네상스 시대 인물"
2. **시대 연결**: 르네상스 → 계몽주의 → 산업혁명
3. **관계 추적**: 르네상스에 속한 인물, 작품, 장소
4. **검색/탐색**: "르네상스 관련 모든 것 보기"

---

## 2. Wikidata 분류 분석

### 2.1 관련 P31 (instance of) 타입

```
Q2198855  - cultural movement (문화 운동)
Q968159   - art movement (예술 사조)
Q11514315 - historical period (역사적 시대)
Q3024417  - historical era (역사적 시대)
Q1371849  - intellectual movement (지적 운동)
Q5765044  - philosophical movement (철학 운동)
Q2738076  - school of thought (사상 학파)
Q15893266 - ideology (이데올로기)
Q7257     - philosophy (철학)
Q9174     - religion (종교)
Q1914636  - activity (활동)
Q1151067  - architectural style (건축 양식)
Q22669    - musical genre (음악 장르)
Q483394   - genre (장르)
```

### 2.2 예시 엔티티 분석

**르네상스 (Q4692)**:
```
P31: Q2198855 (cultural movement)
     Q11514315 (historical period)
P580: 14세기 (시작)
P582: 17세기 (종료)
P17: 이탈리아 (발생 국가)
P276: 피렌체 (발생 장소)
```

**계몽주의 (Q12539)**:
```
P31: Q2198855 (cultural movement)
     Q1371849 (intellectual movement)
P580: 17세기
P582: 18세기
```

---

## 3. 제안: Concept 엔티티 타입

### 3.1 개념 분류 체계

```
Concept (개념)
├── Movement (운동/사조)
│   ├── cultural_movement (문화 운동): 르네상스, 계몽주의
│   ├── art_movement (예술 사조): 바로크, 낭만주의, 인상주의
│   ├── intellectual_movement (지적 운동): 인문주의
│   └── philosophical_movement (철학 운동): 실존주의
│
├── Period (시대)
│   ├── historical_period: 중세, 근대
│   ├── era: 빅토리아 시대
│   └── age: 청동기 시대
│
├── Style (양식)
│   ├── architectural_style: 고딕, 로마네스크
│   ├── art_style: 큐비즘, 추상표현주의
│   └── musical_style: 클래식, 재즈
│
└── Ideology (이념/사상)
    ├── political_ideology: 자유주의, 사회주의
    ├── philosophy: 합리주의, 경험주의
    └── religion: 프로테스탄티즘, 가톨릭
```

### 3.2 데이터베이스 스키마

```sql
-- concepts 테이블
CREATE TABLE concepts (
    id SERIAL PRIMARY KEY,

    -- 식별
    wikidata_id VARCHAR(20) UNIQUE,

    -- 이름
    name VARCHAR(255) NOT NULL,
    name_ko VARCHAR(255),

    -- 분류
    concept_type VARCHAR(50) NOT NULL,
        -- movement, period, style, ideology
    concept_subtype VARCHAR(50),
        -- cultural_movement, art_movement, historical_period, etc.

    -- 시간 범위
    date_start INTEGER,      -- BCE 음수
    date_end INTEGER,

    -- 설명
    description TEXT,
    description_ko TEXT,

    -- 메타
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_concepts_wikidata ON concepts(wikidata_id);
CREATE INDEX idx_concepts_type ON concepts(concept_type);
CREATE INDEX idx_concepts_dates ON concepts(date_start, date_end);
```

### 3.3 관계 확장

기존 `links` 테이블로 관계 표현:

```sql
-- Person ↔ Concept 관계
-- 다빈치 → 르네상스 (소속)
INSERT INTO links (from_type, from_id, to_type, to_id, category)
VALUES ('person', 123, 'concept', 1, 'belongs_to:movement');

-- Concept → Location 관계
-- 르네상스 → 피렌체 (발생지)
INSERT INTO links (from_type, from_id, to_type, to_id, category)
VALUES ('concept', 1, 'location', 456, 'origin:birthplace');

-- Concept → Concept 관계
-- 르네상스 → 계몽주의 (영향)
INSERT INTO links (from_type, from_id, to_type, to_id, category)
VALUES ('concept', 1, 'concept', 2, 'influence:led_to');
```

### 3.4 Wikidata 속성 매핑

| Wikidata 속성 | 의미 | 용도 |
|--------------|------|------|
| P31 | instance of | concept_type 분류 |
| P580 | start time | date_start |
| P582 | end time | date_end |
| P17 | country | 발생 국가 연결 |
| P276 | location | 발생 장소 연결 |
| P155 | follows | 선행 개념 연결 |
| P156 | followed by | 후행 개념 연결 |
| P737 | influenced by | 영향 받음 |
| P1536 | contemporary | 동시대 개념 |
| P527 | has part | 하위 개념 |
| P361 | part of | 상위 개념 |

---

## 4. 구현 계획

### 4.1 Phase 1: 스키마 확장

**CP-C1.1: concepts 테이블 생성**
```bash
backend/schema/06_concepts.sql
```

**CP-C1.2: config.py 업데이트**
```python
CONCEPT_TYPES = {
    'Q2198855': 'cultural_movement',
    'Q968159': 'art_movement',
    'Q11514315': 'historical_period',
    'Q3024417': 'era',
    'Q1371849': 'intellectual_movement',
    'Q5765044': 'philosophical_movement',
    'Q2738076': 'school_of_thought',
    'Q1151067': 'architectural_style',
}
```

### 4.2 Phase 2: 추출 스크립트 수정

**CP-C2.1: 02_extract_wikidata.py 수정**
- `classify_entity()` 함수에 concept 타입 추가
- `extract_concept()` 함수 추가

```python
def classify_entity(p31_types: Set[str]) -> Optional[str]:
    # ... 기존 코드 ...

    # Concept 체크 (맨 마지막에)
    for qid in p31_types:
        if qid in CONCEPT_TYPES:
            return 'concept'

    return None

def extract_concept(entity: dict) -> Dict:
    # date_start, date_end
    # related locations, persons
    # etc.
```

### 4.3 Phase 3: 임포트 스크립트 수정

**CP-C3.1: 04_import_all.py 수정**
- concepts 테이블 임포트 추가

### 4.4 Phase 4: 링크 생성

**CP-C4.1: 05_build_links.py 수정**
- concept 관련 링크 타입 추가
- P737 (influenced by), P155/P156 (follows/followed by) 처리

---

## 5. 예상 데이터

### 5.1 추출 예상

| 타입 | Wikidata 추정 | 비고 |
|------|--------------|------|
| cultural_movement | ~5,000 | 르네상스, 계몽주의 등 |
| art_movement | ~3,000 | 바로크, 인상주의 등 |
| historical_period | ~2,000 | 중세, 근대 등 |
| architectural_style | ~1,000 | 고딕, 로마네스크 등 |
| philosophical_movement | ~500 | 실존주의, 합리주의 등 |
| **총합** | **~12,000** | |

### 5.2 관계 예상

```
Person → Concept: ~50만 (인물-사조 연결)
Concept → Location: ~2만 (사조-발생지)
Concept → Concept: ~3만 (사조 간 영향)
Event → Concept: ~5만 (사건-사조 연결)
```

---

## 6. 쿼리 예시

### 6.1 르네상스 관련 모든 것

```sql
-- 르네상스에 속한 인물
SELECT p.name, p.birth_year, p.death_year
FROM persons p
JOIN links l ON l.from_type = 'person' AND l.from_id = p.id
JOIN concepts c ON l.to_type = 'concept' AND l.to_id = c.id
WHERE c.name = 'Renaissance';

-- 르네상스 시대 작품 (sources에서)
SELECT s.title, s.content_raw
FROM sources s
JOIN mentions m ON m.source_id = s.id
JOIN concepts c ON m.target_type = 'concept' AND m.target_id = c.id
WHERE c.name = 'Renaissance';
```

### 6.2 시대 흐름

```sql
-- 르네상스 → 이후 운동들
SELECT c2.name, l.category
FROM concepts c1
JOIN links l ON l.from_type = 'concept' AND l.from_id = c1.id
JOIN concepts c2 ON l.to_type = 'concept' AND l.to_id = c2.id
WHERE c1.name = 'Renaissance'
  AND l.category LIKE 'influence%';
```

### 6.3 특정 시대의 인물들

```sql
-- 1400-1600년 사이 활동한 르네상스 인물
SELECT p.name, p.birth_year, p.occupation
FROM persons p
JOIN links l ON l.from_type = 'person' AND l.from_id = p.id
JOIN concepts c ON l.to_type = 'concept' AND l.to_id = c.id
WHERE c.concept_type = 'movement'
  AND c.date_start <= 1500 AND c.date_end >= 1500
  AND p.birth_year BETWEEN 1400 AND 1550;
```

---

## 7. UI/UX 고려사항

### 7.1 Globe 시각화

```
시대 레이어:
- 1300-1600: 르네상스 (이탈리아 중심 하이라이트)
- 1600-1750: 바로크 (유럽 전역)
- 1750-1850: 계몽주의/고전주의

타임라인에서 시대 선택 시:
→ 해당 시대 인물/장소/사건 필터링
→ 관련 지역 강조
```

### 7.2 탐색 시나리오

```
사용자: "르네상스"
→ 르네상스 개요 표시
→ 주요 인물 목록 (다빈치, 미켈란젤로...)
→ 관련 장소 (피렌체, 로마...)
→ 주요 사건
→ 영향 받은/준 다른 운동
→ 타임라인상 위치
```

---

## 8. 일정

| Phase | 작업 | 예상 시간 |
|-------|------|----------|
| C1 | 스키마 확장 | 30분 |
| C2 | 추출 스크립트 수정 | 1시간 |
| C3 | 임포트 스크립트 수정 | 30분 |
| C4 | 링크 생성 스크립트 수정 | 1시간 |
| 테스트 | 소규모 테스트 | 1시간 |
| **총합** | | **4시간** |

---

## 9. 의존성

- 현재 Wikidata 다운로드 완료 필요
- 기존 파이프라인 (Step 1-5) 동작 확인됨 ✅

---

## 10. 결론

Concept 엔티티 추가로:

1. **완전성**: 역사 이해에 필요한 모든 요소 포함
2. **맥락**: 인물/사건을 시대/사조와 연결
3. **탐색**: "르네상스 시대 모든 것" 검색 가능
4. **교육**: 역사 흐름 이해 도움

**권장**: 현재 파이프라인 전체 실행 후 Phase C1-C4 진행

---

## 11. 검토 의견 및 개선사항 (2026-02-06 추가)

### 11.1 분류 경계 명확화 필요

**문제**: 일부 항목은 Concept보다 Event에 가까움

| 항목 | 제안 분류 | 재검토 |
|------|----------|--------|
| 산업혁명 (Q2269) | concept | ⚠️ Event 성격 강함 (1760-1840 특정 기간) |
| 종교개혁 (Q12546) | concept | ⚠️ Event 성격 강함 (1517 시작점 명확) |
| 르네상스 (Q4692) | concept | ✅ Movement/Period로 적합 |
| 바로크 (Q37853) | concept | ✅ Art movement로 적합 |

**해결안**:
```python
# Event vs Concept 구분 기준
def classify_period_or_event(entity):
    # 명확한 시작/종료 이벤트가 있으면 → Event
    # 점진적 문화 변화면 → Concept
    has_point_in_time = 'P585' in entity['claims']  # point in time
    has_significant_event = 'P793' in entity['claims']  # significant event

    if has_point_in_time or has_significant_event:
        return 'event'  # 산업혁명, 종교개혁
    return 'concept'  # 르네상스, 바로크
```

### 11.2 핵심 누락 속성: P135 (movement)

**중요**: Wikidata에서 인물→사조 연결은 주로 P135 사용

```
다빈치 (Q762):
  P135: 르네상스 (Q4692)
  P135: 이탈리아 르네상스 (Q1473494)
```

**config.py에 추가 필요**:
```python
RELATIONSHIP_PROPERTIES.update({
    'movement': ('person', 'concept', 'belongs_to'),  # P135
    'genre': ('person', 'concept', 'style'),          # P136
    'field_of_work': ('person', 'concept', 'field'),  # P101
})
```

### 11.3 기존 entity_properties 활용

현재 `entity_properties` 테이블에 이미 모든 Wikidata 속성 저장됨.
Concept 관계는 새 추출 없이 기존 데이터에서 구축 가능:

```sql
-- 이미 저장된 P135 (movement) 데이터 활용
SELECT ep.entity_id, ep.value_qid as concept_qid
FROM entity_properties ep
WHERE ep.property = 'P135'
  AND ep.entity_type = 'person';
```

### 11.4 Source Attribution 추가

제안서에 누락된 출처 추적:

```sql
-- concepts도 sources 테이블 연결 필요
ALTER TABLE concepts ADD COLUMN source_wikidata_id INTEGER REFERENCES sources(id);
ALTER TABLE concepts ADD COLUMN source_wikipedia_id INTEGER REFERENCES sources(id);
```

### 11.5 Religion 처리 주의

종교는 복잡한 계층 구조:
```
Q9174 (religion)
├── Q5043 (Christianity)
│   ├── Q1841 (Catholicism)
│   └── Q23540 (Protestantism)
└── Q432 (Islam)
```

**권장**: 종교는 별도 `religions` 테이블 또는 `concept_subtype = 'religion'`으로만 처리

### 11.6 수정된 구현 우선순위

| 순서 | 작업 | 이유 |
|------|------|------|
| 1 | P135/P136 링크 먼저 구축 | 기존 entity_properties로 즉시 가능 |
| 2 | concepts 테이블 생성 | 스키마 확장 |
| 3 | Event vs Concept 경계 확정 | 분류 명확화 |
| 4 | Source attribution 연결 | 일관성 유지 |

---
