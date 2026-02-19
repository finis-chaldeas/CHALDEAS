# 시간 기반 태그 시스템 설계

## 핵심 원칙

1. **시간은 절대적** - 모든 엔티티는 시간축 위에 존재
2. **태그는 자동 생성** - Wikidata든 LLM이든 같은 결과
3. **기존 시스템 확장** - 새 테이블 최소화, 기존 구조 활용

---

## 기존 시스템과의 관계

```
기존:
├── persons (birth_year, death_year 있음)
├── events (start_year, end_year 있음)
├── locations (created_year 등)
├── links (관계)
├── mentions (증거)
├── entity_attributes (속성)
└── entity_aliases (별칭)

추가:
├── tags (태그 정의)
├── entity_tags (엔티티-태그 매핑)
└── tag_rules (자동 태깅 규칙)
```

---

## 테이블 설계

### tags 테이블

```sql
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    name_ko VARCHAR(100),

    -- 계층 구조
    parent_id INTEGER REFERENCES tags(id),
    tag_type VARCHAR(50) NOT NULL,  -- era, classification, occupation, event, custom

    -- 시간 기반 태그의 경우
    time_start INTEGER,  -- 시작 연도 (BCE는 음수)
    time_end INTEGER,    -- 종료 연도

    -- 자동 생성 여부
    is_auto BOOLEAN DEFAULT FALSE,
    auto_source VARCHAR(50),  -- 'time_rule', 'wikidata_p31', 'llm_extracted'

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 초기 데이터: 시대 태그
INSERT INTO tags (name, name_ko, tag_type, time_start, time_end, is_auto, auto_source) VALUES
('ancient', '고대', 'era', -3000, 500, TRUE, 'time_rule'),
('classical_antiquity', '고전 고대', 'era', -800, 500, TRUE, 'time_rule'),
('medieval', '중세', 'era', 500, 1500, TRUE, 'time_rule'),
('renaissance', '르네상스', 'era', 1400, 1600, TRUE, 'time_rule'),
('early_modern', '근세', 'era', 1500, 1800, TRUE, 'time_rule'),
('modern', '근대', 'era', 1800, 1945, TRUE, 'time_rule'),
('contemporary', '현대', 'era', 1945, 2100, TRUE, 'time_rule');

-- 분류 태그 (Wikidata P31에서)
INSERT INTO tags (name, name_ko, tag_type, parent_id) VALUES
('monarch', '군주', 'classification', NULL),
('emperor', '황제', 'classification', (SELECT id FROM tags WHERE name='monarch')),
('king', '왕', 'classification', (SELECT id FROM tags WHERE name='monarch')),
('philosopher', '철학자', 'classification', NULL),
('military_leader', '군사 지도자', 'classification', NULL),
('general', '장군', 'classification', (SELECT id FROM tags WHERE name='military_leader'));
```

### entity_tags 테이블

```sql
CREATE TABLE entity_tags (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(20) NOT NULL,
    entity_id INTEGER NOT NULL,
    tag_id INTEGER REFERENCES tags(id),

    -- 출처 추적
    source VARCHAR(50) NOT NULL,  -- 'wikidata', 'llm', 'time_auto', 'manual'
    confidence FLOAT DEFAULT 1.0,

    -- 증거 (LLM 추출의 경우)
    evidence_text TEXT,
    source_id INTEGER,  -- sources 테이블 참조

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(entity_type, entity_id, tag_id)
);

CREATE INDEX idx_entity_tags_lookup ON entity_tags(entity_type, entity_id);
CREATE INDEX idx_entity_tags_tag ON entity_tags(tag_id);
```

### tag_rules 테이블 (자동 태깅 규칙)

```sql
CREATE TABLE tag_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    tag_id INTEGER REFERENCES tags(id),

    -- 규칙 조건 (JSON)
    rule_type VARCHAR(50),  -- 'time_range', 'attribute_match', 'link_exists'
    rule_condition JSONB,

    -- 예시:
    -- time_range: {"birth_year_gte": 1400, "birth_year_lte": 1600}
    -- attribute_match: {"attribute_type": "occupation", "value_contains": "general"}
    -- link_exists: {"link_category": "fought_in"}

    priority INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);

-- 예시 규칙들
INSERT INTO tag_rules (name, tag_id, rule_type, rule_condition) VALUES
('르네상스 시대 인물', (SELECT id FROM tags WHERE name='renaissance'),
 'time_range', '{"birth_year_gte": 1400, "birth_year_lte": 1600}'),

('장군 직업', (SELECT id FROM tags WHERE name='general'),
 'attribute_match', '{"attribute_type": "occupation", "value_contains": "general"}'),

('전쟁 참전자', (SELECT id FROM tags WHERE name='military_leader'),
 'link_exists', '{"link_category": "fought_in"}');
```

---

## 자동 태깅 파이프라인

### 1. 시간 기반 자동 태깅

```python
def auto_tag_by_time(entity_type, entity_id, birth_year, death_year=None):
    """
    시간 기반 자동 태깅
    - Wikidata든 LLM 추출이든 birth_year만 있으면 작동
    """
    # 활동 시기 계산 (birth + 30년 ~ death 또는 birth + 70년)
    active_start = birth_year + 30 if birth_year else None
    active_end = death_year or (birth_year + 70 if birth_year else None)

    # 시대 태그 조회
    cursor.execute("""
        SELECT id, name FROM tags
        WHERE tag_type = 'era'
          AND time_start <= %s AND time_end >= %s
    """, (active_start, active_start))

    for tag_id, tag_name in cursor.fetchall():
        save_entity_tag(entity_type, entity_id, tag_id,
                       source='time_auto', confidence=1.0)
```

### 2. 속성 기반 자동 태깅

```python
def auto_tag_by_attributes(entity_type, entity_id):
    """
    entity_attributes에서 태그 자동 생성
    - occupation: "general" → 태그 "장군"
    - position_held: "Emperor" → 태그 "황제"
    """
    cursor.execute("""
        SELECT attribute_type, attribute_value, attribute_qid
        FROM entity_attributes
        WHERE entity_type = %s AND entity_id = %s
    """, (entity_type, entity_id))

    for attr_type, attr_value, attr_qid in cursor.fetchall():
        # Wikidata QID로 태그 매핑
        if attr_qid:
            tag = get_tag_by_wikidata_qid(attr_qid)
            if tag:
                save_entity_tag(entity_type, entity_id, tag.id,
                               source='wikidata', confidence=1.0)

        # 텍스트 매칭으로 태그
        else:
            matching_rules = get_matching_rules('attribute_match', attr_type, attr_value)
            for rule in matching_rules:
                save_entity_tag(entity_type, entity_id, rule.tag_id,
                               source='rule_match', confidence=0.8)
```

### 3. LLM 추출 시 태깅

```python
LLM_TAG_EXTRACTION_PROMPT = """
다음 텍스트에서 인물의 분류/태그를 추출하세요.

텍스트: "{context}"
인물: "{person_name}"

가능한 태그 카테고리:
- 시대: 고대, 중세, 르네상스, 근세, 근대, 현대
- 역할: 군주, 장군, 철학자, 과학자, 예술가, 종교인, 정치인
- 국가/문화권: 그리스, 로마, 중국, 프랑스, 영국 등

JSON 형식으로 반환:
{
  "era": ["..."],
  "roles": ["..."],
  "culture": ["..."],
  "birth_year": null or number,
  "death_year": null or number
}

텍스트에 명시된 것만 포함하세요.
"""

def extract_tags_with_llm(context, person_name):
    """
    LLM으로 태그 추출 (Wikidata 없는 엔티티용)
    """
    response = llm.generate(
        LLM_TAG_EXTRACTION_PROMPT.format(context=context, person_name=person_name)
    )

    tags_data = json.loads(response)

    # 추출된 태그 저장
    for era in tags_data.get('era', []):
        tag = get_or_create_tag(era, 'era')
        save_entity_tag('person', entity_id, tag.id,
                       source='llm', confidence=0.7,
                       evidence_text=context)

    # birth_year가 추출되면 시간 기반 태깅도 실행
    if tags_data.get('birth_year'):
        auto_tag_by_time('person', entity_id,
                        tags_data['birth_year'],
                        tags_data.get('death_year'))
```

---

## 통합 파이프라인

### 새 책 추가 시 흐름

```
┌─────────────────────────────────────────────────────────────┐
│  1. 책 텍스트 입력                                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  2. LLM 엔티티 추출                                         │
│     - 이름, 유형 (person/event/location)                   │
│     - 날짜 (가능하면)                                       │
│     - 기본 속성 (직업, 역할 등)                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  3. 기존 엔티티 매칭                                        │
│     - entity_aliases로 검색                                 │
│     - 매칭되면 → 기존 엔티티에 정보 추가                   │
│     - 매칭 안 되면 → 새 엔티티 생성                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  4. 자동 태깅 실행                                          │
│                                                             │
│     ┌─────────────────────────────────────────────┐        │
│     │ 날짜 있음? → 시간 기반 자동 태깅            │        │
│     │   birth_year=1769 → "근대", "18세기"        │        │
│     └─────────────────────────────────────────────┘        │
│                              │                              │
│     ┌─────────────────────────────────────────────┐        │
│     │ 속성 있음? → 속성 기반 자동 태깅            │        │
│     │   occupation="general" → "장군", "군인"     │        │
│     └─────────────────────────────────────────────┘        │
│                              │                              │
│     ┌─────────────────────────────────────────────┐        │
│     │ 둘 다 없음? → LLM 태그 추출                 │        │
│     │   "The great emperor..." → "황제", "군주"   │        │
│     └─────────────────────────────────────────────┘        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  5. 시간 검증                                               │
│     - 추출된 관계가 시간적으로 가능한지 확인               │
│     - 불가능하면 경고 또는 제외                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  6. 저장                                                    │
│     - entities (persons/events/locations)                  │
│     - entity_attributes (source='extracted')               │
│     - entity_tags (source='time_auto'/'llm')              │
│     - links + mentions (증거 포함)                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 시간 검증 규칙

```python
def validate_temporal_consistency(link):
    """
    관계의 시간적 일관성 검증
    """
    from_entity = get_entity(link.from_type, link.from_id)
    to_entity = get_entity(link.to_type, link.to_id)

    # 규칙 1: 두 인물이 만나려면 생애가 겹쳐야 함
    if link.category in ['met', 'collaborated', 'student_of', 'teacher_of']:
        if not lifespans_overlap(from_entity, to_entity):
            return False, f"생애가 겹치지 않음: {from_entity.name}({from_entity.birth_year}-{from_entity.death_year}) vs {to_entity.name}"

    # 규칙 2: 이벤트 참여는 이벤트 기간 내 생존해야
    if link.category == 'participated_in' and link.to_type == 'event':
        event = to_entity
        person = from_entity
        if person.death_year and person.death_year < event.start_year:
            return False, f"{person.name}은 {event.name} 이전에 사망"
        if person.birth_year and person.birth_year > event.end_year:
            return False, f"{person.name}은 {event.name} 이후에 출생"

    # 규칙 3: 인과관계는 원인이 먼저
    if link.category == 'caused_by':
        if from_entity.start_year < to_entity.end_year:
            return False, "결과가 원인보다 먼저 발생"

    return True, None

def lifespans_overlap(person1, person2):
    """두 인물의 생애가 겹치는지 확인"""
    # 생몰년 정보가 없으면 True 반환 (알 수 없음)
    if not person1.birth_year or not person2.birth_year:
        return True

    p1_end = person1.death_year or (person1.birth_year + 100)
    p2_end = person2.death_year or (person2.birth_year + 100)

    return not (p1_end < person2.birth_year or p2_end < person1.birth_year)
```

---

## 쿼리 예시

### 시간 + 태그 복합 쿼리

```sql
-- "18세기 유럽 철학자"
SELECT DISTINCT p.id, p.name, p.birth_year
FROM persons p
JOIN entity_tags et1 ON et1.entity_type = 'person' AND et1.entity_id = p.id
JOIN tags t1 ON et1.tag_id = t1.id AND t1.name = 'philosopher'
JOIN entity_tags et2 ON et2.entity_type = 'person' AND et2.entity_id = p.id
JOIN tags t2 ON et2.tag_id = t2.id AND t2.name IN ('european', 'french', 'german', 'british')
WHERE p.birth_year BETWEEN 1700 AND 1800;

-- "나폴레옹과 동시대 군사 지도자"
WITH napoleon AS (
    SELECT birth_year, death_year FROM persons WHERE name = 'Napoleon'
)
SELECT p.name, p.birth_year, p.death_year
FROM persons p
JOIN entity_tags et ON et.entity_type = 'person' AND et.entity_id = p.id
JOIN tags t ON et.tag_id = t.id AND t.name = 'military_leader'
CROSS JOIN napoleon n
WHERE p.birth_year <= n.death_year
  AND (p.death_year IS NULL OR p.death_year >= n.birth_year)
  AND p.name != 'Napoleon';
```

### 계층적 태그 쿼리

```sql
-- "모든 군주" (황제, 왕 등 포함)
WITH RECURSIVE tag_tree AS (
    SELECT id, name FROM tags WHERE name = 'monarch'
    UNION ALL
    SELECT t.id, t.name FROM tags t
    JOIN tag_tree tt ON t.parent_id = tt.id
)
SELECT p.name, t.name as role
FROM persons p
JOIN entity_tags et ON et.entity_type = 'person' AND et.entity_id = p.id
JOIN tag_tree t ON et.tag_id = t.id;
```

---

## 기존 시스템과의 일관성

| 기존 | 신규 | 관계 |
|------|------|------|
| entity_attributes.occupation | tags (occupation type) | attribute → 자동 태그 생성 |
| links.category | tags (role type) | fought_in → "전쟁 참전자" 태그 |
| persons.birth_year | tags (era type) | 시간 → 자동 시대 태그 |
| Wikidata P31 | tags (classification) | instance_of → 분류 태그 |

**모든 것이 tags + entity_tags로 통합되지만, 원본 데이터는 그대로 유지**

---

## 구현 순서

| 순서 | 작업 | 의존성 |
|------|------|--------|
| 1 | tags, entity_tags 테이블 생성 | 없음 |
| 2 | 시대 태그 초기 데이터 | 1 |
| 3 | 시간 기반 자동 태깅 함수 | 2 |
| 4 | Wikidata P31 → 태그 매핑 | 1 |
| 5 | entity_attributes → 태그 변환 | 1, 4 |
| 6 | LLM 태그 추출 프롬프트 | 1 |
| 7 | 시간 검증 함수 | 3 |
| 8 | 통합 파이프라인 | 전체 |
