# Wikidata Import 스크립트: 이상 vs 현실 Gap Analysis

## 분석 대상
- **파일**: `poc/scripts/wikidata/import_wikidata_events.py`
- **분석 일시**: 2026-02-05

---

## 1. 스크립트 선언 목표 (라인 1-11)

```python
"""
Wikidata 이벤트 전체 임포트 스크립트.

Phase 1: 이벤트 임포트 (전투, 전쟁, 조약, 왕조 등)
Phase 2: 연결된 인물 임포트 (P710 참여자)
Phase 3: 연결된 장소 임포트 (P276)
Phase 4: 이벤트 간 관계 구축 (P361, P155/P156)
"""
```

### 선언된 Phase 분석

| Phase | 설명 | Wikidata 속성 | 예상 동작 |
|-------|------|---------------|-----------|
| Phase 1 | 이벤트 임포트 | P31 (instance of) | events 테이블에 저장 |
| Phase 2 | 인물 임포트 | P710 (participant) | persons 테이블 생성 + event_persons 연결 |
| Phase 3 | 장소 임포트 | P276 (location) | locations 테이블 생성 + event_locations 연결 |
| Phase 4 | 관계 구축 | P361 (part of), P155/P156 (follows/followed by) | event_relationships 생성 |

---

## 2. 실제 구현 분석

### Phase 1: 이벤트 임포트 - ⚠️ 부분 구현

#### SPARQL 쿼리 (라인 237-258)
```python
query = f"""
SELECT DISTINCT
    ?item ?itemLabel ?itemDescription
    ?pointInTime ?startTime
    ?location ?locationLabel      # ← P276 가져옴
    ?partOf ?partOfLabel          # ← P361 가져옴
WHERE {{
    ?item wdt:P31 wd:{event_qid}.
    ...
    OPTIONAL {{ ?item wdt:P276 ?location. }}  # ← 위치 쿼리
    OPTIONAL {{ ?item wdt:P361 ?partOf. }}    # ← 관계 쿼리
    ...
}}
"""
```

**분석**:
- 이벤트 기본 정보 ✓
- P276 (location) 쿼리 ✓ (그러나 저장 안 함)
- P361 (part_of) 쿼리 ✓ (그러나 저장 안 함)
- P625 (coordinates) 쿼리 ✗

#### WikidataEvent 데이터 클래스 (라인 125-163)
```python
@dataclass
class WikidataEvent:
    qid: str
    label: str
    # ...
    location_qid: Optional[str] = None      # ← 필드 존재
    location_label: Optional[str] = None    # ← 필드 존재
    part_of_qid: Optional[str] = None       # ← 필드 존재
    part_of_label: Optional[str] = None     # ← 필드 존재
```

**분석**: 데이터 구조는 위치/관계 저장 준비됨

#### 객체 생성 (라인 281-300)
```python
event = WikidataEvent(
    # ...
    location_qid=r.get('location', {}).get('value', '').split('/')[-1] if r.get('location') else None,
    location_label=r.get('locationLabel', {}).get('value'),
    part_of_qid=r.get('partOf', {}).get('value', '').split('/')[-1] if r.get('partOf') else None,
    part_of_label=r.get('partOfLabel', {}).get('value'),
)
```

**분석**: location_qid, location_label, part_of_qid, part_of_label 모두 저장됨

#### insert_event() - **결정적 실패 지점** (라인 369-449)
```python
def insert_event(self, event: WikidataEvent) -> Optional[int]:
    # ...
    cur.execute("""
        INSERT INTO events (
            title, title_ko, slug, description,
            date_start, date_start_month, date_start_day,
            date_end, date_end_month, date_end_day,
            wikidata_id, wikipedia_url,
            source_reliability, certainty,
            created_at, updated_at
        ) VALUES (...)
    """, (
        event.label, event.label_ko, slug, event.description,
        year, month, day,
        end_year, end_month, end_day,
        event.qid, event.wikipedia_url
    ))
```

**결정적 문제**:
| 필드 | 객체에 존재 | INSERT에서 사용 | 결과 |
|------|-------------|-----------------|------|
| location_qid | ✓ | ✗ | **무시됨** |
| location_label | ✓ | ✗ | **무시됨** |
| part_of_qid | ✓ | ✗ | **무시됨** |
| part_of_label | ✓ | ✗ | **무시됨** |
| primary_location_id | - | ✗ | **설정 안 됨** |

---

### Phase 2: 인물 임포트 - ❌ 미구현

#### fetch_participants() 메서드 존재 (라인 309-340)
```python
def fetch_participants(self, event_qid: str) -> List[Dict]:
    """이벤트의 참여자들을 가져옴."""
    query = f"""
    SELECT ?person ?personLabel ?personLabel_ko ?role ?roleLabel WHERE {{
        wd:{event_qid} wdt:P710 ?person.
        # ...
    }}
    """
```

**분석**: 메서드는 구현되어 있음

#### 호출 코드 - **존재하지 않음**
`import_region()` 또는 다른 어떤 메서드에서도 `fetch_participants()`를 호출하지 않음.

**결과**:
- persons 테이블에 레코드 생성 ✗
- event_persons 연결 생성 ✗

---

### Phase 3: 장소 임포트 - ❌ 완전 미구현

**예상 구현**:
```python
def create_location(self, location_qid: str, location_label: str) -> int:
    """위치 레코드 생성"""
    # 1. locations 테이블에서 wikidata_id로 조회
    # 2. 없으면 Wikidata에서 P625(좌표) 가져와서 새로 생성
    # 3. location_id 반환

def link_event_location(self, event_id: int, location_id: int):
    """이벤트-위치 연결"""
    # 1. events.primary_location_id 설정
    # 2. event_locations 레코드 생성
```

**실제 구현**: 없음

---

### Phase 4: 관계 구축 - ❌ 완전 미구현

**예상 구현**:
```python
def create_event_relationship(self, event_id: int, related_qid: str, relationship_type: str):
    """이벤트 간 관계 생성"""
    # 1. related_qid로 이벤트 조회
    # 2. event_relationships 레코드 생성
```

**실제 구현**: 없음

---

## 3. 데이터 흐름 비교

### 이상적 흐름 (선언된 Phase 기준)

```
┌─────────────────────────────────────────────────────────────┐
│  1. Wikidata SPARQL 쿼리                                    │
│     ├─ 이벤트 기본 정보                                     │
│     ├─ P276 (location) → location QID, label, 좌표         │
│     ├─ P710 (participants) → person QIDs                   │
│     └─ P361 (part_of) → parent event QID                   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  2. DB 저장 (Phase 1)                                       │
│     └─ events 테이블: 기본 정보 저장                        │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  3. 위치 처리 (Phase 3)                                     │
│     ├─ locations 테이블: 위치 레코드 생성 (wikidata_id)     │
│     ├─ events.primary_location_id 연결                      │
│     └─ event_locations 브릿지 생성                          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  4. 인물 처리 (Phase 2)                                     │
│     ├─ persons 테이블: 인물 레코드 생성 (wikidata_id)       │
│     └─ event_persons 연결 생성                              │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  5. 관계 처리 (Phase 4)                                     │
│     └─ event_relationships: part_of, follows 등 연결        │
└─────────────────────────────────────────────────────────────┘
```

### 실제 흐름

```
┌─────────────────────────────────────────────────────────────┐
│  1. Wikidata SPARQL 쿼리                                    │
│     ├─ 이벤트 기본 정보 ✓                                   │
│     ├─ P276 (location) ✓ 가져옴                             │
│     ├─ P710 (participants) ✗ 안 가져옴                      │
│     └─ P361 (part_of) ✓ 가져옴                              │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  2. WikidataEvent 객체 저장                                 │
│     ├─ 기본 정보 ✓                                          │
│     ├─ location_qid/label ✓ 저장됨                          │
│     └─ part_of_qid/label ✓ 저장됨                           │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  3. insert_event() DB 저장                                  │
│     ├─ 기본 정보만 INSERT ✓                                 │
│     ├─ location_qid ❌ 무시됨 (INSERT 문에 없음)            │
│     ├─ part_of_qid ❌ 무시됨 (INSERT 문에 없음)             │
│     ├─ locations 테이블 ❌ 생성 안 함                       │
│     └─ event_relationships ❌ 생성 안 함                    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  결과: 고아 이벤트                                          │
│     - 위치 연결 없음                                        │
│     - 인물 연결 없음                                        │
│     - 이벤트 계층 없음                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 누락된 코드 상세

### 4.1 insert_event()에서 누락된 로직

```python
def insert_event(self, event: WikidataEvent) -> Optional[int]:
    # 현재: 이벤트만 저장

    # ======== 누락된 코드 ========

    # 1. 위치 처리 (Phase 3)
    location_id = None
    if event.location_qid:
        # 1.1 기존 위치 조회
        cur.execute("SELECT id FROM locations WHERE wikidata_id = %s", (event.location_qid,))
        existing = cur.fetchone()

        if existing:
            location_id = existing[0]
        else:
            # 1.2 Wikidata에서 위치 상세 정보 가져오기 (좌표 포함)
            location_details = self.fetch_location_details(event.location_qid)

            # 1.3 locations 테이블에 새 레코드 생성
            cur.execute("""
                INSERT INTO locations (
                    name, latitude, longitude, type, wikidata_id, ...
                ) VALUES (...)
                RETURNING id
            """, ...)
            location_id = cur.fetchone()[0]

    # 2. 이벤트 저장 (primary_location_id 포함)
    cur.execute("""
        INSERT INTO events (
            ..., primary_location_id, ...
        ) VALUES (
            ..., %s, ...
        )
        RETURNING id
    """, (..., location_id, ...))
    event_id = cur.fetchone()[0]

    # 3. event_locations 브릿지 생성
    if location_id:
        cur.execute("""
            INSERT INTO event_locations (event_id, location_id, relationship_type)
            VALUES (%s, %s, 'occurred_at')
        """, (event_id, location_id))

    # 4. 이벤트 관계 처리 (Phase 4)
    if event.part_of_qid:
        cur.execute("SELECT id FROM events WHERE wikidata_id = %s", (event.part_of_qid,))
        parent = cur.fetchone()
        if parent:
            cur.execute("""
                INSERT INTO event_relationships (source_id, target_id, relationship_type)
                VALUES (%s, %s, 'part_of')
            """, (event_id, parent[0]))

    return event_id
```

### 4.2 fetch_location_details() - 누락된 메서드

```python
def fetch_location_details(self, location_qid: str) -> dict:
    """위치의 좌표, 유형 등 상세 정보를 Wikidata에서 가져옴."""
    query = f"""
    SELECT ?label ?coord ?typeLabel WHERE {{
        BIND(wd:{location_qid} AS ?loc)
        OPTIONAL {{ ?loc rdfs:label ?label. FILTER(LANG(?label) = "en") }}
        OPTIONAL {{ ?loc wdt:P625 ?coord. }}  # coordinates
        OPTIONAL {{ ?loc wdt:P31 ?type. }}    # instance of
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """
    # ... 좌표 파싱 등
```

### 4.3 import_region()에서 누락된 호출

```python
def import_region(self, region: str, ...):
    # 현재: 이벤트만 처리

    # ======== 누락된 코드 ========

    # Phase 2: 인물 처리
    for event in all_events:
        participants = self.fetch_participants(event.qid)  # 메서드는 있으나 호출 안 함
        for p in participants:
            person_id = self.get_or_create_person(p)  # 누락
            self.link_event_person(event_id, person_id, p['role'])  # 누락
```

---

## 5. 결과 영향

### 데이터베이스 상태

| 항목 | 예상 값 | 실제 값 | 손실률 |
|------|---------|---------|--------|
| events with location | ~90% | ~1.8% | **98.2%** |
| locations (wikidata) | ~10,000+ | 1,609 | - |
| event_persons (from import) | ~50,000+ | 0 | **100%** |
| event_relationships (part_of) | ~5,000+ | 0 | **100%** |

### 기능적 영향

1. **지구본 표시 불가**: 98.2% 이벤트가 좌표 없음
2. **관련 인물 표시 불가**: 이벤트-인물 연결 없음
3. **이벤트 계층 구조 없음**: 전쟁-전투 관계 없음
4. **검색 품질 저하**: 위치 기반 필터링 불가

---

## 6. 결론

### 핵심 문제
**코드가 데이터를 가져오기만 하고 저장/연결하지 않음.**

1. SPARQL로 location_qid 가져옴 → ✓
2. WikidataEvent 객체에 저장 → ✓
3. INSERT 문에서 사용 → ✗ **여기서 끊김**

### 원인 추정
- Phase 1만 구현하고 Phase 2, 3, 4는 미완성 상태로 방치
- 또는 Phase 간 연동 로직을 작성하지 않음
- 테스트 시 데이터 정합성 검증 부재

### 해결 방안

**즉시 조치**:
- 백필 스크립트로 기존 이벤트의 위치 데이터 보완

**장기 조치**:
- import 스크립트 전면 수정
- Phase 2, 3, 4 완전 구현
- 데이터 정합성 테스트 추가

---

*분석 완료: 2026-02-05*
