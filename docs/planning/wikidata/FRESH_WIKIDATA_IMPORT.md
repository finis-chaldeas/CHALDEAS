# Wikidata 이벤트 완전 재임포트 계획

## 현재 상태 (폐기 대상)

| 항목 | 수량 | 문제 |
|------|------|------|
| Events | 14,131 | 98% 위치 없음, 설명 오염 |
| Locations | 1,679 | 이벤트와 연결 안 됨 |
| event_persons | 204,496 | 임포트와 무관 (별도 P607) |
| event_locations | ~50 | 거의 없음 |

**결론: 전체 재작업 필요**

---

## 새 임포트 원칙

### 1. 엔티티 순서
```
1. Locations 먼저 (독립)
2. Persons 먼저 (독립)
3. Events 마지막 (위치/인물 의존)
```

### 2. 완전성 보장
모든 이벤트는 반드시:
- ✅ 설명이 있어야 함
- ✅ 위치가 있어야 함 (없으면 국가라도)
- ✅ 날짜가 있어야 함
- ⚠️ 인물은 선택 (자연재해 등)

### 3. 검증 후 저장
```
가져오기 → 검증 → 연결 엔티티 생성 → 저장
```

---

## 새 임포트 흐름

### Step 1: 이벤트 후보 수집

Wikidata에서 "역사적 이벤트"로 분류된 항목 수집:

```sparql
SELECT ?event ?eventLabel WHERE {
    VALUES ?eventType {
        wd:Q178561   # battle
        wd:Q198      # war
        wd:Q131569   # treaty
        wd:Q13418847 # historical event
        wd:Q10931    # revolution
        wd:Q188055   # siege
        wd:Q3199915  # massacre
        # ... 더 많은 타입
    }
    ?event wdt:P31 ?eventType.

    # 날짜 필수
    { ?event wdt:P585 ?time. } UNION { ?event wdt:P580 ?time. }

    # 위치 필수 (location 또는 country)
    { ?event wdt:P276 ?loc. } UNION { ?event wdt:P17 ?country. }

    SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
```

### Step 2: 각 이벤트 상세 수집

```sparql
SELECT DISTINCT
    ?label ?labelKo ?description

    # 시간
    ?pointInTime ?startTime ?endTime

    # 위치 (다중)
    ?location ?locationLabel ?locationCoord
    ?country ?countryLabel ?countryCoord

    # 참여자 (다중)
    ?participant ?participantLabel ?role ?roleLabel

    # 관계
    ?partOf ?partOfLabel
    ?causes ?causesLabel
    ?causedBy ?causedByLabel

WHERE {
    wd:{QID} rdfs:label ?label. FILTER(LANG(?label) = "en")
    OPTIONAL { wd:{QID} rdfs:label ?labelKo. FILTER(LANG(?labelKo) = "ko") }
    OPTIONAL { wd:{QID} schema:description ?description. FILTER(LANG(?description) = "en") }

    # 시간
    OPTIONAL { wd:{QID} wdt:P585 ?pointInTime. }
    OPTIONAL { wd:{QID} wdt:P580 ?startTime. }
    OPTIONAL { wd:{QID} wdt:P582 ?endTime. }

    # 위치 (P276)
    OPTIONAL {
        wd:{QID} wdt:P276 ?location.
        OPTIONAL { ?location wdt:P625 ?locationCoord. }
    }

    # 국가 (P17) - fallback
    OPTIONAL {
        wd:{QID} wdt:P17 ?country.
        OPTIONAL { ?country wdt:P625 ?countryCoord. }
    }

    # 참여자 (P710)
    OPTIONAL {
        wd:{QID} p:P710 ?participantStmt.
        ?participantStmt ps:P710 ?participant.
        OPTIONAL { ?participantStmt pq:P3831 ?role. }
    }

    # 관계
    OPTIONAL { wd:{QID} wdt:P361 ?partOf. }
    OPTIONAL { wd:{QID} wdt:P1542 ?causes. }
    OPTIONAL { wd:{QID} wdt:P828 ?causedBy. }

    SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
```

### Step 3: 위치 등록

1. location_qid들 수집
2. 각 위치를 locations 테이블에 등록:
   - name, name_ko
   - latitude, longitude (P625)
   - type (city, region, country 등)
   - wikidata_id

### Step 4: 인물 등록

1. participant_qid들 수집
2. 각 인물을 persons 테이블에 등록:
   - name, name_ko
   - birth/death dates
   - wikidata_id

### Step 5: 이벤트 저장

1. events 테이블에 저장:
   - title, description
   - date_start, date_end
   - primary_location_id (첫 번째 위치)
   - wikidata_id

2. event_locations 연결 (다중):
   - event_id, location_id, role ('primary', 'affected', etc.)

3. event_persons 연결:
   - event_id, person_id, role

4. event_relationships 연결:
   - source_id, target_id, type ('part_of', 'caused', etc.)

---

## 기존 데이터 처리

### 옵션 1: 전체 삭제 후 재임포트
```sql
-- 관계 테이블 먼저
TRUNCATE event_locations CASCADE;
TRUNCATE event_persons CASCADE;
TRUNCATE event_relationships CASCADE;

-- 메인 테이블
DELETE FROM events WHERE wikidata_id IS NOT NULL;
DELETE FROM locations WHERE wikidata_id IS NOT NULL;
DELETE FROM persons WHERE wikidata_id IS NOT NULL;
```

### 옵션 2: 마킹 후 재임포트
```sql
-- 기존 데이터에 태그
UPDATE events SET needs_reimport = true WHERE wikidata_id IS NOT NULL;

-- 새 임포트 후 기존 삭제
DELETE FROM events WHERE needs_reimport = true AND id NOT IN (새 임포트 IDs);
```

---

## 예상 결과

### 완전한 이벤트 예시

**Battle of Hastings (Q83224)**

```json
{
    "title": "Battle of Hastings",
    "title_ko": "헤이스팅스 전투",
    "description": "The Battle of Hastings was fought on 14 October 1066 between the Norman-French army of William, the Duke of Normandy, and an English army under the Anglo-Saxon King Harold II...",
    "date_start": 1066,
    "date_start_month": 10,
    "date_start_day": 14,
    "wikidata_id": "Q83224",

    "locations": [
        {
            "id": 123,
            "name": "Battle",
            "latitude": 50.9166,
            "longitude": 0.4833,
            "role": "primary"
        }
    ],

    "participants": [
        {
            "id": 456,
            "name": "William the Conqueror",
            "role": "commander",
            "side": "winner"
        },
        {
            "id": 789,
            "name": "Harold II",
            "role": "commander",
            "side": "loser"
        }
    ],

    "relationships": [
        {
            "type": "part_of",
            "target": "Norman conquest of England"
        }
    ]
}
```

---

## 품질 기준

### 필수 (이벤트 저장 불가)
- [ ] 제목 (English label)
- [ ] 날짜 (P585 또는 P580)
- [ ] 위치 (P276 또는 P17)

### 권장 (경고만)
- [ ] 설명 (schema:description)
- [ ] 인물 (P710)
- [ ] 관계 (P361 등)

### 검증 스크립트
```python
def validate_event(entity: dict) -> tuple[bool, list[str]]:
    errors = []

    if not entity.get('label'):
        errors.append('Missing title')

    if not entity.get('start_year'):
        errors.append('Missing date')

    if not entity.get('location_qid') and not entity.get('country_qid'):
        errors.append('Missing location')

    return len(errors) == 0, errors
```

---

## 실행 계획

1. **기존 데이터 백업** (이미 D:\chaldeas_back에 있음)
2. **기존 Wikidata 데이터 삭제**
3. **새 임포터로 재임포트**
4. **검증**:
   - 위치 연결률 > 95%
   - 인물 연결률 > 50%
   - 설명 존재율 > 90%

---

*작성: 2026-02-05*
