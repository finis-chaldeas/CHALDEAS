# CHALDEAS 가중치 시스템 설계

## 개요

모든 데이터에 가중치를 부여하여:
1. 엔티티 중요도 계산
2. 링크(관계) 신뢰도/강도 계산
3. 검색/추천 랭킹

---

## 1. Wikidata 추가 활용 속성

### 현재 수집 중

| Property | 설명 | 용도 |
|----------|------|------|
| P625 | 좌표 | locations 위치 |
| P22/P25/P26/P40 | 가족관계 | persons 연결 |
| P710/P1344 | 이벤트 참가 | event↔person |
| P31/P279 | 분류 (instance/subclass) | 온톨로지 |

### 추가 수집 권장

#### 인물 (Persons)

| Property | 설명 | 활용 | 우선순위 |
|----------|------|------|----------|
| P569/P570 | 출생/사망일 | 타임라인 정확도 | 높음 |
| P19/P20 | 출생/사망지 | person↔location | 높음 |
| P27 | 국적 | 필터링, 분류 | 중간 |
| P106 | 직업 | 분류, 검색 | 높음 |
| P39 | 직위 (왕, 대통령 등) | 중요도 판단 | 높음 |
| P166 | 수상 내역 | 중요도 가산 | 낮음 |
| P800 | 대표작 | person↔work | 중간 |
| P607 | 참전한 전쟁 | person↔event | 중간 |
| P551 | 거주지 | person↔location | 낮음 |

#### 이벤트 (Events)

| Property | 설명 | 활용 | 우선순위 |
|----------|------|------|----------|
| P580/P582 | 시작/종료일 | 타임라인 | 높음 |
| P276 | 발생 장소 | event↔location | 높음 |
| P1542 | 원인 (has cause) | 인과관계 | 높음 |
| P1536 | 결과 (has effect) | 인과관계 | 높음 |
| P361 | 상위 이벤트 (part of) | 이벤트 계층 | 중간 |
| P527 | 하위 이벤트 (has part) | 이벤트 계층 | 중간 |

#### 장소 (Locations)

| Property | 설명 | 활용 | 우선순위 |
|----------|------|------|----------|
| P17 | 소속 국가 | 필터링 | 높음 |
| P131 | 행정구역 | 계층 구조 | 중간 |
| P36 | 수도 | location↔location | 낮음 |
| P1566 | GeoNames ID | 외부 연동 | 낮음 |

---

## 2. 링크(관계) 가중치 시스템

### 설계 원칙

```
link_weight = base_weight × source_reliability × evidence_strength
```

### 관계 유형별 기본 가중치 (base_weight)

#### 가족 관계 (Family) - 가장 확실

| category | base_weight | 설명 |
|----------|-------------|------|
| father | 1.0 | 직계 혈연 |
| mother | 1.0 | 직계 혈연 |
| child | 1.0 | 직계 혈연 |
| spouse | 0.95 | 법적 관계 |
| sibling | 0.9 | 형제자매 (추론 가능) |
| grandparent | 0.85 | 추론된 관계 |
| uncle/aunt | 0.8 | 추론된 관계 |

#### 이벤트 참여 (Participation)

| category | base_weight | 설명 |
|----------|-------------|------|
| participant | 0.9 | 직접 참여 |
| organizer | 0.95 | 주최자 |
| commander | 0.95 | 지휘관 |
| victim | 0.85 | 피해자 |
| witness | 0.7 | 목격자 |

#### 장소 관계 (Location)

| category | base_weight | 설명 |
|----------|-------------|------|
| birthplace | 0.95 | 출생지 |
| deathplace | 0.95 | 사망지 |
| residence | 0.7 | 거주지 |
| workplace | 0.75 | 근무지 |
| occurred_at | 0.9 | 이벤트 발생지 |

#### 추출된 관계 (Extracted)

| category | base_weight | 설명 |
|----------|-------------|------|
| mentioned_with | 0.3 | 같은 문서에 언급 |
| linked_in_text | 0.5 | 텍스트 내 링크 |
| same_sentence | 0.6 | 같은 문장에 언급 |
| wikidata_claim | 0.95 | Wikidata에서 가져옴 |

### 출처 신뢰도 (source_reliability)

| source_type | reliability | 설명 |
|-------------|-------------|------|
| wikidata | 1.0 | 검증된 구조화 데이터 |
| wikipedia | 0.9 | 커뮤니티 검증 |
| encyclopedia | 0.85 | 전문가 편집 |
| academic | 0.95 | 학술 자료 |
| gutenberg_classic | 0.7 | 고전 문학 |
| gutenberg_history | 0.8 | 역사서 |
| gutenberg_fiction | 0.4 | 소설 (사실 아닐 수 있음) |

### 증거 강도 (evidence_strength)

```python
def calculate_evidence_strength(mentions_count, sources_count):
    """
    여러 번, 여러 곳에서 언급될수록 강함
    """
    # 언급 횟수 (로그 스케일, 최대 1.0)
    m = min(math.log(mentions_count + 1) / 5, 1.0)

    # 출처 다양성 (더 중요, 최대 1.0)
    s = min(math.log(sources_count + 1) / 3, 1.0)

    # 가중 평균
    return m * 0.4 + s * 0.6
```

### 최종 가중치 계산

```python
def calculate_link_weight(link):
    """
    링크의 최종 가중치 계산
    """
    # 1. 기본 가중치
    base = CATEGORY_WEIGHTS.get(link.category, 0.5)

    # 2. 출처 신뢰도 (해당 링크의 mentions에서)
    reliability = get_source_reliability(link)

    # 3. 증거 강도
    evidence = calculate_evidence_strength(
        link.mentions_count,
        link.sources_count
    )

    # 최종 가중치 (0.0 ~ 1.0)
    weight = base * reliability * evidence

    return min(weight, 1.0)
```

---

## 3. 테이블 구조

### links 테이블 확장

```sql
ALTER TABLE links ADD COLUMN base_weight FLOAT DEFAULT 0.5;
ALTER TABLE links ADD COLUMN source_reliability FLOAT DEFAULT 0.5;
ALTER TABLE links ADD COLUMN evidence_strength FLOAT DEFAULT 0.0;
ALTER TABLE links ADD COLUMN final_weight FLOAT DEFAULT 0.0;
ALTER TABLE links ADD COLUMN weight_version VARCHAR(10) DEFAULT 'v1';
```

### 관계 유형 정의 테이블

```sql
CREATE TABLE link_category_weights (
    category VARCHAR(50) PRIMARY KEY,
    base_weight FLOAT NOT NULL,
    category_group VARCHAR(50),  -- family, participation, location, extracted
    description TEXT,
    version VARCHAR(10) DEFAULT 'v1'
);

-- 초기 데이터
INSERT INTO link_category_weights VALUES
('father', 1.0, 'family', '아버지', 'v1'),
('mother', 1.0, 'family', '어머니', 'v1'),
('child', 1.0, 'family', '자녀', 'v1'),
('spouse', 0.95, 'family', '배우자', 'v1'),
('participant', 0.9, 'participation', '참가자', 'v1'),
('birthplace', 0.95, 'location', '출생지', 'v1'),
('mentioned_with', 0.3, 'extracted', '함께 언급됨', 'v1'),
('wikidata_claim', 0.95, 'extracted', 'Wikidata 출처', 'v1');
```

### 출처 신뢰도 테이블

```sql
CREATE TABLE source_type_reliability (
    source_type VARCHAR(50) PRIMARY KEY,
    reliability FLOAT NOT NULL,
    description TEXT
);

INSERT INTO source_type_reliability VALUES
('wikidata', 1.0, 'Wikidata 구조화 데이터'),
('wikipedia', 0.9, 'Wikipedia 문서'),
('gutenberg_history', 0.8, 'Gutenberg 역사서'),
('gutenberg_fiction', 0.4, 'Gutenberg 소설');
```

---

## 4. 가중치 활용

### 검색 랭킹

```sql
-- 관련 인물 검색 (가중치 기반)
SELECT p.name, SUM(l.final_weight) as relevance
FROM persons p
JOIN links l ON l.to_type = 'person' AND l.to_id = p.id
WHERE l.from_type = 'event' AND l.from_id = :event_id
GROUP BY p.id
ORDER BY relevance DESC
LIMIT 20;
```

### 그래프 시각화

```javascript
// 엣지 두께 = 가중치
edge.width = link.final_weight * 5;

// 노드 크기 = 중요도
node.size = entity.importance_score * 10;
```

### 추천 시스템

```python
def recommend_related_entities(entity, limit=10):
    """가중치 높은 연결된 엔티티 추천"""
    links = get_links_for_entity(entity)
    links.sort(key=lambda l: l.final_weight, reverse=True)
    return links[:limit]
```

---

## 5. 버전 관리

```python
WEIGHT_VERSIONS = {
    'v1': {
        'description': '초기 버전',
        'category_weights': {...},
        'source_reliability': {...},
    },
    'v2': {
        'description': 'sources 비중 증가',
        'category_weights': {...},
        'source_reliability': {...},
    },
}

def recalculate_all_weights(version='v1'):
    """전체 링크 가중치 재계산"""
    config = WEIGHT_VERSIONS[version]
    # ... 재계산 로직
```

---

## 6. 새 엔티티 처리 (Wikidata 없는 경우)

### 문제

- **Wikidata 엔티티**: 직업, 직위, 출생지 등 구조화된 데이터 있음
- **책에서 온 엔티티**: Wikidata 없음 → 속성 없음

### 해결: 동일 스키마, 다중 소스

```sql
-- entity_attributes.source 필드로 구분
source = 'wikidata'   -- Wikidata API에서 가져옴
source = 'extracted'  -- LLM이 텍스트에서 추출
source = 'inferred'   -- 규칙 기반 추론
source = 'manual'     -- 수동 입력
```

### 추출 파이프라인

```
책 텍스트
    ↓
청크 단위로 분할
    ↓
LLM 엔티티 추출 (현재 구현됨)
    ↓
┌─────────────────────────────────────┐
│ LLM 속성 추출 (추가 구현 필요)      │
│                                     │
│ "General Smith commanded..."        │
│     ↓                               │
│ occupation: "general"               │
│ role: "commander"                   │
└─────────────────────────────────────┘
    ↓
entity_attributes 저장 (source='extracted')
```

### LLM 속성 추출 프롬프트

```python
ATTRIBUTE_EXTRACTION_PROMPT = """
Extract attributes for the person mentioned in this text.

Text: "{context}"
Person: "{person_name}"

Extract if mentioned:
- occupation: their job or role (e.g., "king", "philosopher", "general")
- position: official title (e.g., "President of France")
- birthplace: where they were born
- nationality: their country/nation
- relationships: family or other connections

Return JSON:
{
  "occupation": ["..."],
  "position": ["..."],
  "birthplace": "...",
  "relationships": [{"type": "...", "target": "..."}]
}

Only include what is explicitly mentioned. Return empty if not found.
"""
```

### 통합 뷰

```sql
-- 모든 소스의 속성 통합 조회
SELECT
    ea.attribute_type,
    ea.attribute_value,
    ea.source,
    CASE ea.source
        WHEN 'wikidata' THEN 1.0
        WHEN 'extracted' THEN 0.7
        WHEN 'inferred' THEN 0.5
    END as confidence
FROM entity_attributes ea
WHERE ea.entity_type = 'person' AND ea.entity_id = :id
ORDER BY confidence DESC;
```

### 신뢰도 비교

| source | confidence | 설명 |
|--------|------------|------|
| wikidata | 1.0 | 검증된 구조화 데이터 |
| extracted | 0.7 | LLM 추출 (오류 가능) |
| inferred | 0.5 | 규칙 추론 |
| manual | 0.9 | 수동 입력 |

### 구현 시점

| 단계 | 작업 | 시점 |
|------|------|------|
| 1 | Wikidata 속성 수집 | 현재 (초기 시드) |
| 2 | LLM 속성 추출 | Gutenberg 처리 시 |
| 3 | 추론 규칙 | 데이터 충분해지면 |

---

## 7. 구현 순서

| 단계 | 작업 | 우선순위 |
|------|------|----------|
| 1 | link_category_weights 테이블 생성 | 높음 |
| 2 | source_type_reliability 테이블 생성 | 높음 |
| 3 | links 테이블 컬럼 추가 | 높음 |
| 4 | 기존 links 가중치 계산 | 높음 |
| 5 | Wikidata 추가 속성 수집 (P106, P39 등) | 중간 |
| 6 | 가중치 재계산 배치 스크립트 | 중간 |

---

## 7. Wikidata 추가 수집 스크립트

```python
# fetch_wikidata_properties.py 확장

ADDITIONAL_PROPS = {
    # 인물
    'P569': 'birth_date',
    'P570': 'death_date',
    'P19': 'birthplace',
    'P20': 'deathplace',
    'P27': 'citizenship',
    'P106': 'occupation',
    'P39': 'position_held',
    'P607': 'conflict',

    # 이벤트
    'P580': 'start_date',
    'P582': 'end_date',
    'P276': 'location',
    'P1542': 'has_cause',
    'P1536': 'has_effect',

    # 장소
    'P17': 'country',
    'P131': 'admin_region',
}
```
