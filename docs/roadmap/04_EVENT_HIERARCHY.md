# 04. 이벤트 계층구조 확장

## 문제

CHALDEAS의 핵심 비전은 **"줌 = 서사 해상도"** — 줌아웃하면 문명, 줌인하면 전투의 하루가 보여야 한다. 이를 위해 이벤트 간 부모-자식 관계가 필수.

현재 `parent_event_id`가 35.3%만 채워져 있어, 줌 기반 필터링이 불완전하다.

## 현재 상태

### 스키마 (이미 존재하는 컬럼들)

| 컬럼 | 타입 | 현재 커버리지 | 비고 |
|------|------|-------------|------|
| `parent_event_id` | INTEGER FK | 35.3% (10,013개) | **핵심 갭** |
| `hierarchy_level` | INTEGER | 100% | 1=문명, 2=전쟁, 3=전투 |
| `temporal_scale` | VARCHAR | 100% | evenementielle/conjuncture/longue_duree |
| `is_aggregate` | BOOLEAN | 100% | 1,478개 true |
| `aggregate_type` | VARCHAR | 있음 | |
| `wikidata_id` | VARCHAR | 100% (28,331개) | 전부 Q-ID 보유 |

### hierarchy_level 분포

| 레벨 | 설명 | 수 | 비율 |
|------|------|-----|------|
| 1 | 문명/시대 (longue_duree) | 611 | 2.2% |
| 2 | 전쟁/운동 (conjuncture) | 3,924 | 13.9% |
| 3 | 전투/사건 (evenementielle) | 23,796 | 84.0% |

### parent_event_id 현황

- **있음**: 10,013 (35.3%)
- **없음**: 18,318 (64.7%)
- **목표**: 70-85% (DATA_FILLING_PLAN.md 기준)

### 대표 계층 구조 (이미 동작하는 것)

```
American Civil War (Q8676) ─── 510 하위 이벤트
World War II (Q362)        ─── 340 하위 이벤트
World War I (Q361)         ─── 180 하위 이벤트
Eighty Years' War          ─── 146 하위 이벤트
Seven Years' War           ─── 129 하위 이벤트
Reconquista                ─── 100 하위 이벤트
```

### 타이틀 패턴 분포

| 패턴 | 수 | 비율 |
|------|-----|------|
| "Battle of %" | 11,542 | 40.8% |
| "Siege of %" | 3,135 | 11.1% |
| "%War" / "%Wars" | 1,186 | 4.2% |

→ "Battle of X", "Siege of X"는 거의 확실히 level 3이며, 해당 전쟁의 자식이어야 함.

## 실행 계획

### 방법 1: Wikidata P361 (part of) — 1차 소스

모든 이벤트에 `wikidata_id`가 있으므로, Wikidata 덤프에서 P361 속성을 추출하면 부모 관계를 얻을 수 있다.

```
Q42848 (Battle of Thermopylae) --P361--> Q57237 (Greco-Persian Wars)
Q48611 (Battle of Midway)      --P361--> Q362   (World War II)
```

**스크립트 흐름**:

```python
# scripts/fill_event_hierarchy.py

# 1. Wikidata 덤프에서 P361 추출 (기존 poc/scripts/wikidata/ 참조)
#    - 모든 Q-ID에 대해 P361 값 조회
#    - P361 값이 DB의 wikidata_id에 매칭되면 parent_event_id 설정

# 2. DB 이벤트의 wikidata_id 목록 로드
event_qids = {row.wikidata_id: row.id for row in events}

# 3. Wikidata에서 P361 매핑 추출
for qid, p361_target in wikidata_p361_pairs:
    if qid in event_qids and p361_target in event_qids:
        child_id = event_qids[qid]
        parent_id = event_qids[p361_target]
        # UPDATE events SET parent_event_id = parent_id WHERE id = child_id

# 4. is_aggregate 플래그 업데이트
# UPDATE events SET is_aggregate = true
# WHERE id IN (SELECT DISTINCT parent_event_id FROM events WHERE parent_event_id IS NOT NULL)
```

**예상 커버리지**: +20-30% (기존 35% → 55-65%)

### 방법 2: 타이틀 패턴 매칭 — 2차 보완

Wikidata P361이 없는 경우, 타이틀 패턴으로 추론:

```python
# "Battle of X" → 같은 시기 + 같은 지역의 "X War" 또는 "%X%" aggregate 이벤트 탐색
# "Siege of X"  → 동일
# 시간 범위 겹침 + 지리적 근접성으로 부모 후보 스코어링
```

**예상 추가 커버리지**: +10-15%

### 방법 3: GPT 기반 분류 — 3차 보완 (선택)

나머지 미분류 이벤트에 대해 GPT로 "이 이벤트의 부모는 무엇인가?" 판단.
비용이 들므로 imp4+ 이벤트에만 적용.

## Wikidata 덤프 접근

기존 스크립트 경로: `poc/scripts/wikidata/`
- `extract_events_core.py` — 이벤트 데이터 추출
- `extract_events_from_dump.py` — 덤프에서 추출
- `match_event_locations.py` — P276 (장소) 매칭

동일한 패턴으로 P361 추출 스크립트 작성 가능. Wikidata 덤프는 로컬에 이미 있을 가능성 높음 (기존 스크립트가 사용했으므로).

## 비용

| 방법 | 비용 |
|------|------|
| Wikidata P361 | $0 (로컬 덤프) |
| 타이틀 패턴 매칭 | $0 (로컬 로직) |
| GPT 보완 (선택) | ~$10-30 (imp4+ 대상) |

## 수정 파일

| 파일 | 변경 |
|------|------|
| `backend/scripts/fill_event_hierarchy.py` | **신규** — P361 기반 parent 설정 |
| `backend/scripts/fill_event_hierarchy_pattern.py` | **신규** (선택) — 타이틀 패턴 보완 |

DB 스키마 변경 없음 (컬럼 이미 존재).

## 검증

```sql
-- 적용 전후 비교
SELECT
  COUNT(*) AS total,
  COUNT(parent_event_id) AS with_parent,
  ROUND(100.0 * COUNT(parent_event_id) / COUNT(*), 1) AS pct
FROM events;

-- 계층 깊이 확인
WITH RECURSIVE tree AS (
  SELECT id, parent_event_id, 1 AS depth FROM events WHERE parent_event_id IS NULL
  UNION ALL
  SELECT e.id, e.parent_event_id, t.depth + 1
  FROM events e JOIN tree t ON e.parent_event_id = t.id
)
SELECT depth, COUNT(*) FROM tree GROUP BY depth ORDER BY depth;
```

## 프론트엔드 영향

계층 데이터가 채워지면:
- 글로브 줌 레벨에 따라 표시 이벤트 필터링 가능 (level 1 → 줌아웃, level 3 → 줌인)
- 이벤트 클릭 → 하위 이벤트 드릴다운
- 시프트 자동 생성 시 더 정확한 하위 이벤트 수집
