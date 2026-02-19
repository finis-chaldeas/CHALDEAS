# 02. 로케이션 시스템

## 핵심 개념

**로케이션은 지구 위의 고정된 점**이다. 사건은 오고 가지만, 장소는 변하지 않는다.
단, 그 장소의 **이름과 소속은 시대에 따라 바뀐다**.

```
좌표 (41.01°N, 28.98°E):
  BCE 667 ~ CE 330:    Byzantium (그리스 식민도시)
  CE 330 ~ 1453:       Constantinople (로마/비잔틴 제국)
  1453 ~ 1930:         Konstantiniyye (오스만 제국)
  1930 ~ 현재:          Istanbul (튀르키예 공화국)
```

---

## 로케이션 표시 규칙

### 항상 보이는 로케이션 (Tier 시스템)

| Tier | 조건 | 줌 레벨 | 표시 |
|------|------|---------|------|
| **Tier 1** | event_count > 50 or 세계 주요 도시 | COSMIC부터 항상 | ● 이름 라벨 |
| **Tier 2** | event_count > 10 | CONTINENTAL부터 | ● 이름 라벨 |
| **Tier 3** | event_count > 0 | REGIONAL부터 | ○ 작은 점 |
| **Tier 4** | 이벤트 없음 | LOCAL에서만 | · 미세 점 |

### 활성/비활성 상태

```
현재 시대(타임라인)에 이벤트가 있는 로케이션:
  ● 밝은 마커 + 이름 (활성)
  로케이션 주변에 이벤트 수 배지

현재 시대에 이벤트가 없는 로케이션:
  ○ 흐린 마커 + 이름 (비활성/dormant)
  "이 시대에는 기록된 사건 없음"
```

### 유저 경험: 로케이션 클릭

```
유저가 지구본에서 "Constantinople" 클릭 →

┌─ Constantinople ─────────────────────┐
│ 📍 41.01°N, 28.98°E                 │
│                                      │
│ 시대별 이름:                         │
│  Byzantium → Constantinople →        │
│  Konstantiniyye → Istanbul           │
│                                      │
│ 현재 시대 (CE 330-1453):             │
│  로마 제국 → 비잔틴 제국             │
│                                      │
│ 이 시대 주요 사건 (12):              │
│  ★★★★★ Fall of Constantinople (1453)│
│  ★★★★  Fourth Crusade (1204)        │
│  ★★★★  Nika Riots (532)             │
│                                      │
│ [History] [이 지역 탐색] [Place Story]│
└──────────────────────────────────────┘
```

---

## 시대별 명칭 변화

### 데이터 구조 (이미 존재: location_names 테이블)

```sql
-- 시대에 맞는 이름 조회
SELECT COALESCE(
  (SELECT name FROM location_names
   WHERE location_id = :loc_id
     AND is_primary = true
     AND (valid_from IS NULL OR valid_from <= :year)
     AND (valid_until IS NULL OR valid_until >= :year)
   ORDER BY valid_from DESC NULLS LAST
   LIMIT 1),
  l.name
) as temporal_name
FROM locations l WHERE l.id = :loc_id
```

### API 설계

```
GET /api/v1/locations/globe?year=-500&zoom=continental
→ {
    "locations": [
      {
        "id": 42,
        "latitude": 41.01,
        "longitude": 28.98,
        "name": "Istanbul",           // 현재 공식 이름
        "temporal_name": "Byzantium", // BCE 500 시점 이름
        "tier": 1,
        "event_count": 3,             // 이 시대 이벤트 수
        "total_event_count": 87,      // 전체 이벤트 수
        "polity": "Greek colony",     // 이 시대 소속
        "active": true                // 이 시대 이벤트 있음
      },
      ...
    ]
  }
```

---

## 시대별 소속(정치체) 변화

### 유저 경험

```
타임라인: BCE 100 (로마 공화국 말기)

지구본에서 지중해 주변 로케이션들:
  ● Rome (로마 공화국)         — 이탈리아
  ● Alexandria (로마 공화국)   — 이집트
  ● Athens (로마 공화국)       — 그리스
  ● Jerusalem (로마 공화국)    — 레반트
  ● Carthage (로마 공화국)     — 북아프리카

타임라인을 CE 500으로 이동하면:
  ● Roma (서로마 제국 → 멸망)
  ● Alexandria (비잔틴 제국)
  ● Athens (비잔틴 제국)
  ● Jerusalem (비잔틴 제국)
  ● Carthage (반달족)

→ 같은 좌표지만 소속이 시대에 따라 바뀜
→ 로케이션 카드에 "(소속: 비잔틴 제국)" 표시
```

### 데이터 구조

```sql
CREATE TABLE location_polities (
  id SERIAL PRIMARY KEY,
  location_id INTEGER REFERENCES locations(id),
  polity_name VARCHAR(255) NOT NULL,
  polity_name_ko VARCHAR(255),
  polity_wikidata_id VARCHAR(50),  -- Q12544 등
  valid_from INTEGER,               -- 시작 연도
  valid_until INTEGER,              -- 종료 연도
  source VARCHAR(100)               -- wikidata, manual
);
```

### 데이터 수집

- **Wikidata P17** (country) + 시기 한정자 (P580 start, P582 end)
- 주요 도시 500개에 대해 SPARQL로 추출 가능
- 예시 SPARQL:
```sparql
SELECT ?city ?cityLabel ?country ?countryLabel ?start ?end WHERE {
  ?city wdt:P31/wdt:P279* wd:Q515 .  # 도시
  ?city p:P17 ?stmt .
  ?stmt ps:P17 ?country .
  OPTIONAL { ?stmt pq:P580 ?start }
  OPTIONAL { ?stmt pq:P582 ?end }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
```

---

## 노드 기반 매칭 규칙 (2026-02-17 확정)

### 핵심 원칙

1. **로케이션 = 노드**: 우리 DB의 ~12,908개 로케이션이 고정 노드
2. **이벤트 → 가장 가까운 노드에 매칭**: 이벤트의 Wikidata 좌표(P625/P276)를 기준으로 haversine 최근접 노드에 `primary_location_id` 연결
3. **기존 매칭 보존**: 이미 `primary_location_id`가 있는 이벤트는 건드리지 않음
4. **노드별 역사적 이름변천 관리**: `location_names` 테이블에 시대별 명칭 기록

### 새 노드 추가 시 재분배

새 로케이션(노드)을 추가할 때:
1. 새 노드의 좌표와 기존 이벤트의 **원래 좌표**(coords 파일에 저장됨)를 비교
2. 새 노드가 기존 노드보다 더 가까운 이벤트들을 찾음
3. 해당 이벤트들의 `primary_location_id`를 새 노드로 재할당

```
예시: 새 노드 "Thermopylae" 추가
  기존: "Battle of Thermopylae" → "Athens" (150km)
  변경: "Battle of Thermopylae" → "Thermopylae" (2km)  ← 더 가까우므로 재할당
```

### 좌표 추출 파이프라인

```
이벤트 좌표 추출 (1회):
  Wikidata 로컬 덤프 (1.8TB) 스트리밍 스캔
  → P625 직접 좌표 / P276 위치의 좌표 / P17 국가 좌표
  → poc/data/wikidata/event_coords.json에 저장

최근접 노드 매칭 (즉시):
  event_coords.json + locations 테이블
  → numpy 벡터화 haversine
  → primary_location_id UPDATE
```

### 관련 도구

```
poc/scripts/wikidata/match_event_locations.py
  --scan           Phase 1: 덤프 스캔 → 좌표 추출 (체크포인트 지원)
  --scan --resume  중단 후 재시작
  --match          Phase 2: 좌표 → 최근접 노드 매칭
  --match --dry-run 매칭 dry-run
  --stats          현황 확인
  --reassign 123   새 노드 추가 시 재분배
```

---

## 로케이션 묶기 (지역 그룹)

### 개념

확대하면 개별 도시가 보이지만, 줌아웃하면 **지역 단위**로 묶어서 표시:

```
COSMIC 뷰:
  ● "Mediterranean" (이벤트 247개)
  ● "East Asia" (이벤트 89개)

CONTINENTAL 뷰:
  ● "Greece" (이벤트 45개)
  ● "Italy" (이벤트 67개)
  ● "Egypt" (이벤트 23개)

REGIONAL 뷰:
  ● Athens (12개)
  ● Sparta (5개)
  ● Thebes (3개)
```

### 구현

- `locations.hierarchy_level` 활용: continent > country > region > city
- 줌 레벨에 따라 적절한 hierarchy_level만 표시
- 이미 locations 테이블에 `region`, `country` 컬럼 존재
