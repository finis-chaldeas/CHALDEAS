# 개선 #003: 이벤트 계층 구조

> 상태: 설계 중

## 문제

현재 이벤트는 **플랫**:
```
- Battle of Hastings
- Norman Conquest
- Battle of Stamford Bridge
- Hundred Years' War
- Battle of Crécy
```

원하는 구조 (**계층적**):
```
Norman Conquest
├── Battle of Stamford Bridge
└── Battle of Hastings

Hundred Years' War
├── Battle of Crécy
├── Battle of Poitiers
└── ...
```

## Wikidata 관계

| Property | 의미 | 예시 |
|----------|------|------|
| P361 | part of | Battle of Hastings → Norman Conquest |
| P527 | has part | Norman Conquest → Battle of Hastings |
| P1542 | has effect | Norman Conquest → Norman England |
| P828 | has cause | Norman Conquest → Death of Edward |

## 데이터 구조 옵션

### 옵션 A: Self-referential FK

```sql
ALTER TABLE events
ADD COLUMN parent_id INTEGER REFERENCES events(id);
```

장점: 단순
단점: 재귀 쿼리 필요

### 옵션 B: Closure Table (권장)

```sql
CREATE TABLE event_hierarchy (
    ancestor_id INTEGER REFERENCES events(id),
    descendant_id INTEGER REFERENCES events(id),
    depth INTEGER,
    PRIMARY KEY (ancestor_id, descendant_id)
);
```

장점:
- 모든 조상/자손 O(1) 조회
- 깊이별 쿼리 가능

단점:
- 관계 수정 시 테이블 재구성

### 옵션 C: Materialized Path

```sql
ALTER TABLE events
ADD COLUMN path VARCHAR;  -- e.g., "Q12546/Q79619/Q..."
```

장점: 간단한 prefix 쿼리
단점: path 변경 시 전파 필요

## 구현 계획

1. [ ] 옵션 B (Closure Table) 채택
2. [ ] Alembic 마이그레이션
3. [ ] 임포트 시 P361 파싱 → 계층 구축
4. [ ] API: GET /events/{id}/children, /events/{id}/ancestors

## 쿼리 예시

```sql
-- Q12546 (십자군 전쟁)의 모든 하위 이벤트
SELECT e.*
FROM events e
JOIN event_hierarchy h ON e.id = h.descendant_id
WHERE h.ancestor_id = (SELECT id FROM events WHERE wikidata_id = 'Q12546')
ORDER BY h.depth, e.year_start;
```

## 예상 결과

십자군 전쟁:
```
Q12546: Crusades (depth 0)
├── Q79619: First Crusade (depth 1)
│   ├── Q12428: Battle of Dorylaeum (depth 2)
│   ├── Q...: Siege of Antioch (depth 2)
│   └── ...
├── Q82627: Second Crusade (depth 1)
│   └── ...
└── ...
```
