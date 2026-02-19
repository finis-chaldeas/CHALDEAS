# 개선 #002: 배치 임포트 최적화

> 상태: 계획 중

## 문제

현재 임포트 방식:
```python
for event in events:
    cursor.execute("INSERT INTO events ...", event)
    conn.commit()  # 매번 커밋!
```

- 1건당 1 INSERT + 1 COMMIT
- 네트워크 왕복 10만회 (10만 이벤트 기준)
- 예상 시간: 수 시간

## 목표

100,000개 이벤트 임포트: **10분 이내**

## 해결 방안

### 1. Batch INSERT

```python
from psycopg2.extras import execute_values

execute_values(
    cursor,
    """
    INSERT INTO events (name, description, year_start, wikidata_id)
    VALUES %s
    ON CONFLICT (wikidata_id) DO UPDATE SET
        name = EXCLUDED.name,
        description = EXCLUDED.description
    """,
    [(e.name, e.description, e.start_year, e.qid) for e in events],
    page_size=1000
)
conn.commit()
```

- 1000건당 1 INSERT
- 100배 속도 향상

### 2. COPY 프로토콜 (가장 빠름)

```python
import io

buffer = io.StringIO()
for event in events:
    buffer.write(f"{event.name}\t{event.description}\t{event.start_year}\t{event.qid}\n")

buffer.seek(0)
cursor.copy_from(buffer, 'events', columns=('name', 'description', 'year_start', 'wikidata_id'))
```

- PostgreSQL 네이티브 벌크 로드
- execute_values보다 2-3배 빠름

### 3. 임시 테이블 + UPSERT

```sql
-- 1. 임시 테이블에 빠르게 로드
CREATE TEMP TABLE events_staging (LIKE events INCLUDING DEFAULTS);
COPY events_staging FROM STDIN;

-- 2. 한 번에 UPSERT
INSERT INTO events
SELECT * FROM events_staging
ON CONFLICT (wikidata_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description;

DROP TABLE events_staging;
```

장점:
- 인덱스 영향 최소화
- 트랜잭션 단위 원자성

## 구현 계획

1. [ ] BatchImporter 클래스 생성
2. [ ] execute_values 기반 구현
3. [ ] 성능 테스트 (1000/10000/100000건)
4. [ ] COPY 프로토콜 옵션 추가

## 예상 성능

| 방식 | 100,000건 예상 시간 |
|------|---------------------|
| 현재 (1건씩) | 2-3시간 |
| execute_values | 2-3분 |
| COPY | 30초-1분 |
