# 다중 상위 이벤트 (Multiple Parent Events)

**작성일**: 2026-01-28
**목적**: 하나의 이벤트가 여러 상위 이벤트에 속하는 경우 처리

---

## 1. 문제 정의

### 실제 사례

```
┌─────────────────────────────────────────────────────────────┐
│ Case 1: 전쟁 내 전쟁                                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  제2차 세계대전 (1939-1945)                                  │
│      └── 진주만 공격 (1941)                                  │
│                                                              │
│  태평양 전쟁 (1941-1945)                                     │
│      └── 진주만 공격 (1941)  ← 둘 다 상위!                   │
│                                                              │
│  결론: 태평양 전쟁은 WW2의 일부이자 독립적 맥락              │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Case 2: 다른 맥락의 동일 이벤트                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  잔 다르크 화형 (1431)                                       │
│      ├── 백년전쟁 (war context)                              │
│      └── 중세 종교재판 역사 (religion context)               │
│                                                              │
│  95개조 반박문 (1517)                                        │
│      ├── 종교개혁 (religion context)                         │
│      └── 르네상스 (culture context)                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Case 3: 계층적 중첩                                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  십자군 전쟁 (1095-1291)                                     │
│      └── 제1차 십자군 (1096-1099)                            │
│              └── 예루살렘 함락 (1099)                        │
│                                                              │
│  예루살렘 함락은:                                            │
│      - 직접 상위: 제1차 십자군                               │
│      - 간접 상위: 십자군 전쟁 전체                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 설계 옵션 비교

### Option A: 기존 event_relationships 테이블 활용

```sql
-- 기존 테이블
CREATE TABLE event_relationships (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(id),
    related_event_id INTEGER REFERENCES events(id),
    relationship_type VARCHAR(50)  -- 'part_of', 'causes', 'follows'
);
```

| 장점 | 단점 |
|------|------|
| 스키마 변경 없음 | 계층/인과 관계 혼재 |
| 이미 존재 | 'part_of'와 'causes' 구분 모호 |
| | is_primary 개념 없음 |
| | context 정보 없음 |

### Option B: 새 event_parents 테이블 ✅ 선택

```sql
CREATE TABLE event_parents (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(id) NOT NULL,
    parent_event_id INTEGER REFERENCES events(id) NOT NULL,
    is_primary BOOLEAN DEFAULT false,
    context VARCHAR(50),  -- 'war', 'culture', 'religion', 'politics'
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, parent_event_id)
);
```

| 장점 | 단점 |
|------|------|
| 계층 관계 전용 | 새 테이블 필요 |
| is_primary로 메인 상위 지정 | 마이그레이션 필요 |
| context로 맥락 구분 | |
| 확장 가능 (weight, confidence 등) | |

### Option C: parent_event_id 제거, M:N만 사용

| 장점 | 단점 |
|------|------|
| 단일 진실 소스 | 대규모 마이그레이션 |
| 깔끔한 구조 | 기존 코드 모두 수정 |
| | 단순 쿼리가 복잡해짐 |

---

## 3. 선택: Option B (새 event_parents 테이블)

### 이유

1. **계층 ≠ 인과**: "part_of"와 "causes/follows"는 완전히 다른 관계
2. **context 필드**: 같은 이벤트가 다른 맥락에서 다른 상위 가능
3. **is_primary**: 트리뷰, UI에서 어디에 표시할지 명확
4. **확장성**: weight, confidence, source 등 필드 추가 용이
5. **호환성**: 기존 parent_event_id 유지하며 점진적 전환

### 기존 parent_event_id와의 관계

```
events.parent_event_id (기존)
    └── 성능용 denormalized 필드로 유지
    └── is_primary=True인 parent와 동기화
    └── 간단한 쿼리에 사용 (트리뷰 등)

event_parents (신규)
    └── 정규화된 다중 상위 관계
    └── 복잡한 쿼리, 전체 맥락 조회에 사용
```

---

## 4. 스키마 설계

### 4.1 테이블 정의

```sql
CREATE TABLE event_parents (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    parent_event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,

    -- 메인 상위 여부 (트리뷰에서 이 부모 아래에 표시)
    is_primary BOOLEAN DEFAULT false,

    -- 관계 맥락 (같은 이벤트가 다른 맥락에서 다른 상위)
    context VARCHAR(50),  -- 'war', 'culture', 'religion', 'politics', 'science'

    -- 메타데이터
    created_at TIMESTAMP DEFAULT NOW(),
    source VARCHAR(50),  -- 'wikidata', 'llm', 'manual'
    confidence FLOAT DEFAULT 1.0,

    -- 제약조건
    UNIQUE(event_id, parent_event_id),
    CHECK(event_id != parent_event_id)  -- 자기 자신 참조 방지
);

-- 인덱스
CREATE INDEX ix_event_parents_event_id ON event_parents(event_id);
CREATE INDEX ix_event_parents_parent_event_id ON event_parents(parent_event_id);
CREATE INDEX ix_event_parents_is_primary ON event_parents(is_primary);
CREATE INDEX ix_event_parents_context ON event_parents(context);
```

### 4.2 Context 값

| Context | 설명 | 예시 |
|---------|------|------|
| `war` | 전쟁/군사 맥락 | 진주만 → WW2 |
| `culture` | 문화/예술 맥락 | 시스티나 성당 → 르네상스 |
| `religion` | 종교 맥락 | 95개조 → 종교개혁 |
| `politics` | 정치 맥락 | 바스티유 습격 → 프랑스 혁명 |
| `science` | 과학 맥락 | 증기기관 발명 → 산업혁명 |
| `philosophy` | 철학 맥락 | 소크라테스 죽음 → 고전 아테네 |
| `general` | 일반/기본 | 명확한 맥락 없음 |

---

## 5. 데이터 동기화

### 5.1 parent_event_id와 event_parents 동기화

```python
def sync_primary_parent(event_id: int, db: Session):
    """event_parents의 is_primary=True와 events.parent_event_id 동기화"""

    # event_parents에서 primary 찾기
    primary = db.query(EventParent).filter(
        EventParent.event_id == event_id,
        EventParent.is_primary == True
    ).first()

    event = db.query(Event).get(event_id)

    if primary:
        event.parent_event_id = primary.parent_event_id
    else:
        # primary 없으면 첫 번째를 primary로
        first = db.query(EventParent).filter(
            EventParent.event_id == event_id
        ).first()

        if first:
            first.is_primary = True
            event.parent_event_id = first.parent_event_id
        else:
            event.parent_event_id = None

    db.commit()
```

### 5.2 기존 데이터 마이그레이션

```python
def migrate_existing_parents(db: Session):
    """기존 parent_event_id를 event_parents로 마이그레이션"""

    events = db.query(Event).filter(
        Event.parent_event_id.isnot(None)
    ).all()

    for event in events:
        # 이미 있는지 확인
        existing = db.query(EventParent).filter(
            EventParent.event_id == event.id,
            EventParent.parent_event_id == event.parent_event_id
        ).first()

        if not existing:
            parent = EventParent(
                event_id=event.id,
                parent_event_id=event.parent_event_id,
                is_primary=True,
                context='general',
                source='migration'
            )
            db.add(parent)

    db.commit()
```

---

## 6. API 설계

### 6.1 조회

```python
# 이벤트의 모든 상위 조회
GET /api/v1/events/{id}/parents
Response:
{
    "primary": {
        "id": 123,
        "title": "World War II",
        "context": "war"
    },
    "additional": [
        {"id": 456, "title": "Pacific War", "context": "war"},
        {"id": 789, "title": "Cold War Origins", "context": "politics"}
    ]
}

# 상위 이벤트의 모든 자식 조회
GET /api/v1/events/{id}/children
GET /api/v1/events/{id}/children?context=war  # 특정 맥락만
```

### 6.2 수정

```python
# 상위 추가
POST /api/v1/events/{id}/parents
{
    "parent_event_id": 123,
    "is_primary": false,
    "context": "religion"
}

# 상위 제거
DELETE /api/v1/events/{id}/parents/{parent_id}

# Primary 변경
PATCH /api/v1/events/{id}/parents/{parent_id}
{
    "is_primary": true
}
```

---

## 7. 쿼리 예시

### 7.1 모든 상위 조회

```sql
SELECT
    e.title as event_title,
    p.title as parent_title,
    ep.is_primary,
    ep.context
FROM events e
JOIN event_parents ep ON e.id = ep.event_id
JOIN events p ON ep.parent_event_id = p.id
WHERE e.id = 123;
```

### 7.2 특정 맥락의 하위 조회

```sql
-- WW2 아래의 모든 'war' 맥락 이벤트
SELECT e.*
FROM events e
JOIN event_parents ep ON e.id = ep.event_id
WHERE ep.parent_event_id = (SELECT id FROM events WHERE title = 'World War II')
AND ep.context = 'war'
ORDER BY e.date_start;
```

### 7.3 Primary 기반 트리 구조

```sql
-- 계층적 트리 (is_primary만)
WITH RECURSIVE event_tree AS (
    -- 루트 (parent 없음)
    SELECT id, title, 0 as depth
    FROM events
    WHERE id NOT IN (SELECT event_id FROM event_parents WHERE is_primary = true)

    UNION ALL

    -- 자식들
    SELECT e.id, e.title, et.depth + 1
    FROM events e
    JOIN event_parents ep ON e.id = ep.event_id AND ep.is_primary = true
    JOIN event_tree et ON ep.parent_event_id = et.id
)
SELECT * FROM event_tree ORDER BY depth, title;
```

---

## 8. 마이그레이션 계획

### Phase 1: 스키마 추가
```
[ ] event_parents 테이블 생성 (Alembic)
[ ] EventParent 모델 생성
[ ] 기존 parent_event_id 데이터 마이그레이션
```

### Phase 2: 코드 업데이트
```
[ ] 분류 파이프라인에서 event_parents 사용
[ ] API 엔드포인트 추가
[ ] 검증 로직 업데이트 (다중 부모 지원)
```

### Phase 3: 점진적 전환
```
[ ] 새 분류는 event_parents에 저장
[ ] 기존 parent_event_id는 is_primary와 동기화
[ ] 향후 parent_event_id deprecate 검토
```

---

## 9. 결론

**선택**: 새 `event_parents` 테이블 생성

**핵심 필드**:
- `is_primary`: 메인 상위 (트리뷰용)
- `context`: 관계 맥락 (war, culture, religion 등)

**호환성**:
- 기존 `parent_event_id` 유지 (성능용)
- 점진적 전환 가능

**확장성**:
- 다중 상위 지원
- 맥락별 분류 가능
- 향후 weight, confidence 추가 가능
