# 세션 로그: 2026-02-05 Wikidata Import 스크립트 분석

## 세션 정보
- **목적**: Wikidata 이벤트 임포트 스크립트의 결함 완전 분석
- **배경**: 98.2% 이벤트에 위치 데이터 없음, 데이터 품질 문제 원인 규명
- **상세 분석 문서**: `docs/reports/WIKIDATA_IMPORT_GAP_ANALYSIS.md`

## 핵심 발견

### 결정적 버그 위치: `insert_event()` 라인 369-449

```python
# 객체에는 location_qid가 있음
event = WikidataEvent(
    location_qid=r.get('location', {}).get('value', '').split('/')[-1],  # ← 저장됨
    ...
)

# 하지만 INSERT에서 사용 안 함
cur.execute("""
    INSERT INTO events (
        title, title_ko, slug, description,
        date_start, ...,
        wikidata_id, wikipedia_url,  # ← location_qid 없음!
        ...
    ) VALUES (...)
""")
```

### 미구현 Phase들

| Phase | 설명 | 메서드 존재 | 호출 여부 | DB 저장 |
|-------|------|-------------|-----------|---------|
| Phase 1 | 이벤트 | ✓ insert_event | ✓ | ⚠️ 부분 |
| Phase 2 | 인물 | ✓ fetch_participants | ✗ 호출 안 함 | ✗ |
| Phase 3 | 장소 | ✗ 없음 | - | ✗ |
| Phase 4 | 관계 | ✗ 없음 | - | ✗ |

---

## 스크립트 개요

**파일**: `poc/scripts/wikidata/import_wikidata_events.py`

### 선언된 목표 (주석 기준)
```
Phase 1: 이벤트 임포트 (전투, 전쟁, 조약, 왕조 등)
Phase 2: 연결된 인물 임포트 (P710 참여자)
Phase 3: 연결된 장소 임포트 (P276)
Phase 4: 이벤트 간 관계 구축 (P361, P155/P156)
```

### 실제 구현 상태
| Phase | 설명 | 구현 상태 |
|-------|------|-----------|
| Phase 1 | 이벤트 임포트 | ⚠️ 부분 구현 |
| Phase 2 | 인물 임포트 | ❌ 미구현 |
| Phase 3 | 장소 임포트 | ❌ 미구현 |
| Phase 4 | 관계 구축 | ❌ 미구현 |

---

## 상세 분석

### 1. 데이터 흐름 분석

```
┌─────────────────────────────────────────────────────────────┐
│  1. SPARQL 쿼리 (fetch_events_by_type, 라인 222-307)        │
│     - ?item, ?itemLabel, ?itemDescription                   │
│     - ?pointInTime, ?startTime                              │
│     - ?location, ?locationLabel ← P276 데이터 가져옴!       │
│     - ?partOf, ?partOfLabel                                 │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  2. WikidataEvent 객체 생성 (라인 281-300)                  │
│     - qid, label, description ✓                             │
│     - location_qid ← 저장됨! (라인 293)                     │
│     - location_label ← 저장됨! (라인 294)                   │
│     - country_qid, country_label ← None (미사용)            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  3. insert_event() (라인 369-449)                           │
│     INSERT INTO events (...) VALUES (...)                   │
│                                                             │
│     ❌ location_qid 무시됨!                                 │
│     ❌ location_label 무시됨!                               │
│     ❌ locations 테이블에 레코드 생성 안 함!                │
│     ❌ primary_location_id 설정 안 함!                      │
│     ❌ event_locations 연결 안 함!                          │
└─────────────────────────────────────────────────────────────┘
```

### 2. 문제 코드 분석

#### 2.1 WikidataEvent 데이터 클래스 (라인 125-163)
```python
@dataclass
class WikidataEvent:
    # ... 기타 필드 ...

    # 장소 - 데이터는 정의되어 있음
    location_qid: Optional[str] = None      # ← 존재
    location_label: Optional[str] = None    # ← 존재
    country_qid: Optional[str] = None       # ← 존재
    country_label: Optional[str] = None     # ← 존재
```
**분석**: 데이터 모델은 위치 정보를 저장할 준비가 되어 있음.

#### 2.2 SPARQL 쿼리 (라인 237-258)
```python
query = f"""
SELECT DISTINCT
    ?item ?itemLabel ?itemDescription
    ?pointInTime ?startTime
    ?location ?locationLabel      # ← P276 위치 데이터 가져옴
    ?partOf ?partOfLabel
WHERE {{
    ?item wdt:P31 wd:{event_qid}.
    ...
    OPTIONAL {{ ?item wdt:P276 ?location. }}  # ← 위치 쿼리
    ...
}}
"""
```
**분석**: Wikidata에서 P276(위치) 데이터를 가져옴. 여기까지는 정상.

#### 2.3 WikidataEvent 객체 생성 (라인 281-300)
```python
event = WikidataEvent(
    qid=qid,
    label=r.get('itemLabel', {}).get('value', ''),
    ...
    # 위치 데이터 저장
    location_qid=r.get('location', {}).get('value', '').split('/')[-1] if r.get('location') else None,
    location_label=r.get('locationLabel', {}).get('value'),
    ...
)
```
**분석**: 객체에 location_qid와 location_label이 저장됨. 여기까지는 정상.

#### 2.4 insert_event() - **문제의 핵심** (라인 369-449)
```python
def insert_event(self, event: WikidataEvent) -> Optional[int]:
    # ... 시간 파싱 ...

    # 새로 삽입
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

**결정적 문제점**:
1. `event.location_qid` **완전히 무시됨**
2. `event.location_label` **완전히 무시됨**
3. `primary_location_id` 컬럼 **설정 안 함**
4. locations 테이블에 **레코드 생성 안 함**
5. event_locations 브릿지 테이블 **연결 안 함**

### 3. 누락된 로직

#### 있어야 할 코드 (존재하지 않음):
```python
def insert_event(self, event: WikidataEvent) -> Optional[int]:
    # ... 기존 코드 ...

    # ======== 누락된 코드 시작 ========
    location_id = None
    if event.location_qid:
        # 1. 위치 레코드 조회 또는 생성
        cur.execute("SELECT id FROM locations WHERE wikidata_id = %s", (event.location_qid,))
        existing_loc = cur.fetchone()

        if existing_loc:
            location_id = existing_loc[0]
        else:
            # 위치가 없으면 새로 생성
            cur.execute("""
                INSERT INTO locations (name, wikidata_id, created_at, updated_at)
                VALUES (%s, %s, NOW(), NOW())
                RETURNING id
            """, (event.location_label, event.location_qid))
            location_id = cur.fetchone()[0]

    # 2. 이벤트 삽입 시 primary_location_id 설정
    cur.execute("""
        INSERT INTO events (..., primary_location_id, ...)
        VALUES (..., %s, ...)
    """, (..., location_id, ...))

    # 3. event_locations 연결
    if location_id:
        cur.execute("""
            INSERT INTO event_locations (event_id, location_id, relationship_type)
            VALUES (%s, %s, 'primary')
        """, (event_id, location_id))
    # ======== 누락된 코드 끝 ========
```

### 4. 추가 누락 사항

#### 4.1 좌표 데이터 (P625)
- SPARQL 쿼리에서 P625(coordinates) 가져오지 않음
- locations 테이블의 latitude, longitude 설정 불가

#### 4.2 인물 연결 (P710)
- `fetch_participants()` 메서드는 존재함 (라인 309-340)
- **하지만 `import_region()`에서 호출하지 않음!**
- event_persons 연결 코드 없음

#### 4.3 이벤트 관계 (P361 part_of)
- SPARQL에서 part_of_qid, part_of_label 가져옴
- **하지만 event_relationships 테이블에 연결하지 않음!**

---

## 결론

### 문제 요약
| 항목 | 상태 | 영향 |
|------|------|------|
| 이벤트 기본 정보 | ✅ 정상 | 제목, 설명, 날짜 저장됨 |
| 위치 데이터 가져오기 | ✅ 정상 | SPARQL로 P276 가져옴 |
| 위치 데이터 저장 | ❌ **누락** | locations 테이블 비어있음 |
| 이벤트-위치 연결 | ❌ **누락** | primary_location_id = NULL |
| 좌표 데이터 | ❌ **누락** | 지도에 표시 불가 |
| 인물 연결 | ❌ **미구현** | event_persons 비어있음 |
| 이벤트 계층 | ❌ **미구현** | parent/child 관계 없음 |

### 근본 원인
**스크립트가 Phase 1만 부분 구현하고 Phase 2, 3, 4를 전혀 구현하지 않음.**

데이터를 가져오는 것까지는 성공했지만, DB에 저장하는 단계에서 위치 관련 필드를 완전히 무시함.

### 결과
- 14,131개 이벤트 중 98.2%가 위치 없음
- 지구본에서 대부분의 이벤트를 표시할 수 없음
- 이벤트-인물 관계 없음 (별도 Wikidata P607 임포트로 일부 해결)
- 이벤트 계층 구조 없음

---

## 해결 방안

### 1. 백필 스크립트 작성 (즉시)
기존 이벤트의 위치 데이터를 Wikidata에서 다시 가져와서:
- locations 테이블에 레코드 생성
- events.primary_location_id 연결
- event_locations 연결 생성

### 2. 임포트 스크립트 수정 (장기)
`insert_event()` 메서드에 위치 처리 로직 추가

---

## 작업 내용

### 1. 백필 스크립트 작성
- **파일**: `poc/scripts/wikidata/backfill_event_locations.py`
- **기능**: 기존 이벤트에 Wikidata P276(location) 데이터 보완
- **상태**: 테스트 완료, 100개 이벤트 처리 시 93개 위치 연결 성공

### 2. 테스트 결과
```
=== 결과 ===
총 이벤트: 100
처리됨: 100
위치 발견: 95
위치 연결: 93
```

### 3. 남은 문제
- latitude가 NULL인 위치 처리 필요 (Wikidata에 좌표 없는 경우)
- 전체 ~13,800개 이벤트 백필 필요

## 다음 작업
1. [ ] latitude NULL 허용하도록 스키마 수정 (또는 Nominatim geocoding)
2. [x] 전체 이벤트 백필 실행 중 (500개 배치)
3. [x] 임포트 스크립트 근본 수정 완료

---

## 새 임포터 구조 구현 완료

### 파일 구조
```
poc/scripts/wikidata/
├── importers/
│   ├── __init__.py
│   ├── base.py              # BaseImporter 추상 클래스
│   ├── location_importer.py # 위치 임포트 (좌표 포함)
│   └── event_importer.py    # 이벤트 임포트 (위치 연결!)
├── test_new_importer.py     # 테스트 스크립트
└── backfill_with_new_importer.py  # 백필 스크립트
```

### 핵심 개선점
1. **LocationImporter**: 위치를 먼저 생성/조회
2. **EventImporter.insert()**: `primary_location_id` 설정!
3. **event_locations 브릿지**: 자동 생성
4. **타입 검증**: 비이벤트 (도시, 국가 등) 필터링

### 테스트 결과
```
Battle of Hastings (Q83224):
  - Date: 1066
  - Location: Battle (Q737593)
  - ✓ 위치 연결 성공!

50개 백필 테스트:
  - 45개 위치 발견
  - 42개 연결 성공 (84%)
```

---

*분석 일시: 2026-02-05*
*최종 업데이트: 2026-02-05 08:20*
