# Wikidata 완전 구조 설계

## 핵심 원칙

**모든 이벤트는 다음을 반드시 가져야 함:**
1. **설명 (Description)** - 무엇이 일어났는가
2. **위치 (Location)** - 어디서 일어났는가 (구체적 또는 범위)
3. **인물 (Participants)** - 누가 관여했는가
4. **시간 (Time)** - 언제 일어났는가

---

## 1. 이벤트 설명 (Description)

### Wikidata 속성
- `schema:description` - 짧은 설명 (1-2문장)
- Wikipedia 본문 - 상세 설명

### 문제점
- 현재 description이 잘못 매칭됨 (Treaty of Cusset → Vichy 설명)
- Wikidata description만으로는 부족

### 해결책
```python
def get_event_description(qid: str) -> str:
    # 1. Wikidata description 가져오기
    # 2. Wikipedia 본문 첫 단락 가져오기 (상세 설명)
    # 3. 둘 다 검증: 이벤트 제목과 일치하는지 확인
```

---

## 2. 이벤트 위치 (Location)

### 위치 유형

| 유형 | 예시 | 표현 방법 |
|------|------|-----------|
| **점 (Point)** | Battle of Hastings | lat, lng |
| **도시 (City)** | Siege of Paris | city_qid → lat, lng |
| **지역 (Region)** | Mongol Invasions | region_qid → bounding box |
| **국가 (Country)** | French Revolution | country_qid → polygon |
| **다중 (Multiple)** | World War I | multiple location_qids |

### Wikidata 속성
- `P276` (location) - 주요 위치
- `P625` (coordinates) - 좌표 (위치에 연결)
- `P17` (country) - 국가
- `P131` (located in administrative entity) - 상위 행정구역

### 위치 없는 이벤트 처리

```
전투/전쟁 → 반드시 P276 있어야 함
조약 → 서명 장소 (P276) 또는 적용 지역
왕조/시대 → 영토 범위 (P625 bounding box 또는 P17 국가들)
사상/운동 → 발원지 + 영향 지역
```

### DB 스키마 확장

```sql
-- locations 테이블 확장
ALTER TABLE locations ADD COLUMN IF NOT EXISTS
    location_type VARCHAR(20);  -- 'point', 'city', 'region', 'country'

ALTER TABLE locations ADD COLUMN IF NOT EXISTS
    bounds_ne_lat DECIMAL(10, 7);  -- bounding box (북동 위도)

ALTER TABLE locations ADD COLUMN IF NOT EXISTS
    bounds_ne_lng DECIMAL(10, 7);  -- bounding box (북동 경도)

ALTER TABLE locations ADD COLUMN IF NOT EXISTS
    bounds_sw_lat DECIMAL(10, 7);  -- bounding box (남서 위도)

ALTER TABLE locations ADD COLUMN IF NOT EXISTS
    bounds_sw_lng DECIMAL(10, 7);  -- bounding box (남서 경도)

-- event_locations 테이블 (다중 위치)
-- 이미 존재하지만 role 확장 필요
-- role: 'primary', 'start', 'end', 'affected_region', 'origin'
```

### 위치 계층 구조

```
특정 장소 (Battle Site)
    ↓
도시 (City)
    ↓
지역 (Region/Province)
    ↓
국가 (Country)
    ↓
대륙 (Continent)
```

**구체적 위치 없으면 상위 레벨로 올라감**

---

## 3. 이벤트 인물 (Participants)

### Wikidata 속성
- `P710` (participant) - 참여자
- `P1344` (participant in) - (인물 → 이벤트 역방향)
- `P710[P3831]` (role) - 참여 역할

### 참여자 역할

| 역할 | 설명 |
|------|------|
| participant | 일반 참여자 |
| commander | 지휘관 |
| winner | 승자 |
| loser | 패자 |
| signatory | 서명자 |
| victim | 피해자 |
| perpetrator | 가해자 |

### 인물 없는 이벤트?

**인물 없는 이벤트는 없음.**

- 자연재해 → 피해자, 대응자
- 기술 발전 → 발명가, 기여자
- 사회 운동 → 지도자, 참여자

P710이 없으면:
1. P710[주어 방향] 검색 (이벤트를 참여한 인물)
2. Wikipedia에서 인물 추출

---

## 4. 완전한 데이터 수집 쿼리

```sparql
SELECT DISTINCT
    ?event ?eventLabel ?eventDescription
    ?pointInTime ?startTime ?endTime

    # 위치 (다중)
    ?location ?locationLabel ?locationCoord
    ?country ?countryLabel

    # 참여자 (다중)
    ?participant ?participantLabel ?participantRole

    # 관계
    ?partOf ?partOfLabel
    ?instanceOf

WHERE {
    BIND(wd:Q83224 AS ?event)  # Battle of Hastings

    # 기본 정보
    ?event rdfs:label ?eventLabel. FILTER(LANG(?eventLabel) = "en")
    OPTIONAL { ?event schema:description ?eventDescription. FILTER(LANG(?eventDescription) = "en") }

    # 시간
    OPTIONAL { ?event wdt:P585 ?pointInTime. }
    OPTIONAL { ?event wdt:P580 ?startTime. }
    OPTIONAL { ?event wdt:P582 ?endTime. }

    # 위치 (다중)
    OPTIONAL {
        ?event wdt:P276 ?location.
        OPTIONAL { ?location wdt:P625 ?locationCoord. }
    }
    OPTIONAL { ?event wdt:P17 ?country. }

    # 참여자 (다중)
    OPTIONAL {
        ?event wdt:P710 ?participant.
        OPTIONAL {
            ?event p:P710 ?stmt.
            ?stmt ps:P710 ?participant.
            ?stmt pq:P3831 ?role.
        }
    }

    # 관계
    OPTIONAL { ?event wdt:P361 ?partOf. }
    OPTIONAL { ?event wdt:P31 ?instanceOf. }

    SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
```

---

## 5. 임포트 흐름 (완전 구조)

```
┌─────────────────────────────────────────────────────────────┐
│  1. 이벤트 기본 정보 수집                                   │
│     - QID, Label, Description                               │
│     - 시간 (P585/P580/P582)                                 │
│     - 타입 검증 (P31)                                       │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  2. 위치 수집 및 등록                                       │
│     - P276 (location) 수집                                  │
│     - 없으면 P17 (country) 사용                             │
│     - 각 위치를 locations 테이블에 등록                     │
│     - 좌표 (P625) 또는 bounding box 가져오기                │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  3. 인물 수집 및 등록                                       │
│     - P710 (participant) 수집                               │
│     - 역할 (P3831) 포함                                     │
│     - 각 인물을 persons 테이블에 등록                       │
│     - 인물 없으면 Wikipedia에서 추출                        │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  4. 이벤트 저장 및 연결                                     │
│     - events 테이블 저장                                    │
│     - event_locations 연결 (다중)                           │
│     - event_persons 연결 (역할 포함)                        │
│     - event_relationships (P361 part_of)                    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  5. 검증                                                    │
│     - 위치 연결 확인 (최소 1개)                             │
│     - 인물 연결 확인 (최소 1개)                             │
│     - 설명 존재 확인                                        │
│     - 실패 시 로그 기록                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. 위치 범위 처리 예시

### 예시 1: Battle of Hastings (점)
```
P276: Battle (Q737593)
  → lat: 50.9166, lng: 0.4833
  → location_type: 'point'
```

### 예시 2: Mongol Invasions (광역)
```
P276: 없음
P17: multiple countries
  → Mongolia, China, Persia, Russia, etc.
  → location_type: 'region'
  → bounds: {ne: (60, 140), sw: (20, 40)}
```

### 예시 3: French Revolution (국가)
```
P276: Paris (주요)
P17: France
  → primary: Paris (48.8566, 2.3522)
  → affected_region: France bounding box
```

---

## 7. 구현 우선순위

### Phase 1: 위치 완전성
1. [ ] P276 → P17 fallback 구현
2. [ ] 위치 없는 이벤트 0개 목표
3. [ ] bounding box 지원 (latitude NULL 허용)

### Phase 2: 인물 완전성
1. [ ] P710 참여자 수집
2. [ ] 역할 (P3831) 포함
3. [ ] 인물 없는 이벤트 로그

### Phase 3: 설명 완전성
1. [ ] Wikipedia 본문 첫 단락 가져오기
2. [ ] 설명-제목 일치 검증
3. [ ] 잘못된 설명 수정

---

*작성: 2026-02-05*
