# API Reference

## 구현 상태: Migration 302 반영 완료 (2026-02-17)

Base URL: `/api/v1`

## Events API

### GET /events
이벤트 목록 조회 (지구본 마커용)

**Query Parameters:**
| 파라미터 | 타입 | 설명 |
|----------|------|------|
| year_start | int | 시작 연도 (음수 = BCE) |
| year_end | int | 종료 연도 |
| category | string | 카테고리 슬러그 필터 |
| importance_min | int | 최소 중요도 (1-5) |
| sort_by | string | 정렬 (importance/date) |
| lat_min/lat_max | float | 위도 범위 (뷰포트 필터) |
| lng_min/lng_max | float | 경도 범위 (뷰포트 필터) |
| limit | int | 결과 수 (기본 100) |
| offset | int | 오프셋 |

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "title": "Battle of Marathon",
      "title_ko": "마라톤 전투",
      "wikidata_id": "Q152770",
      "date_start": -490,
      "date_display": "490 BCE",
      "importance": 5,
      "certainty": "fact",
      "temporal_scale": "evenementielle",
      "category": { "id": 1, "name": "Military", "color": "#EF4444" },
      "location": { "id": 10, "name": "Marathon", "latitude": 38.15, "longitude": 23.96 },
      "parent_event_id": null,
      "is_aggregate": false,
      "hierarchy_level": 3,
      "aggregate_type": null,
      "parent_status": null,
      "description": "The Battle of Marathon...",
      "wikipedia_url": "https://en.wikipedia.org/wiki/Battle_of_Marathon",
      "image_url": null,
      "details": {
        "slug": "battle-of-marathon",
        "description": "The Battle of Marathon...",
        "description_source": "wikipedia_en",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Battle_of_Marathon"
      }
    }
  ],
  "total": 100
}
```

> **Note**: `description`, `wikipedia_url`, `image_url`는 하위 호환을 위해 최상위에도 포함. 새 코드는 `details` 객체 사용 권장.

### GET /events/{id}
이벤트 상세 조회 (details, persons, sources 포함)

### GET /events/slug/{slug}
슬러그로 이벤트 조회

### GET /events/{id}/locations
이벤트의 로케이션 조회 (aggregate 이벤트는 하위 이벤트 로케이션을 재귀적으로 수집)

**Response (개별 이벤트):**
```json
{
  "event_id": 101,
  "title": "Battle of Crécy",
  "is_aggregate": false,
  "own_location": { "id": 1, "name": "Crécy", "latitude": 50.25, "longitude": 1.88 },
  "inherited_locations": [],
  "total_locations": 1
}
```

**Response (aggregate 이벤트):**
```json
{
  "event_id": 100,
  "title": "Hundred Years' War",
  "is_aggregate": true,
  "own_location": null,
  "inherited_locations": [
    { "id": 1, "name": "Crécy", "latitude": 50.25, "longitude": 1.88, "from_event_id": 101, "from_event": "Battle of Crécy" },
    { "id": 2, "name": "Poitiers", "latitude": 46.58, "longitude": 0.34, "from_event_id": 102, "from_event": "Battle of Poitiers" },
    { "id": 3, "name": "Agincourt", "latitude": 50.46, "longitude": 2.14, "from_event_id": 103, "from_event": "Battle of Agincourt" }
  ],
  "total_locations": 3
}
```

---

## Persons API

### GET /persons
인물 목록 조회

**Query Parameters:**
| 파라미터 | 타입 | 설명 |
|----------|------|------|
| year_start | int | 활동 시작 연도 필터 |
| year_end | int | 활동 종료 연도 필터 |
| role | string | 역할 필터 (king, philosopher 등) |
| search | string | 이름 검색 |
| limit | int | 결과 수 (기본 50) |
| offset | int | 오프셋 |

### GET /persons/{id}
인물 상세 조회 (details, names 포함)

**Response:**
```json
{
  "id": 1,
  "name": "Alexander the Great",
  "name_ko": "알렉산드로스 대왕",
  "name_ja": "アレクサンドロス大王",
  "wikidata_id": "Q8409",
  "birth_year": -356,
  "death_year": -323,
  "floruit_start": null,
  "floruit_end": null,
  "role": "king",
  "certainty": "fact",
  "birthplace": { "id": 10, "name": "Pella" },
  "deathplace": { "id": 20, "name": "Babylon" },
  "details": {
    "biography": "Alexander III of Macedon...",
    "biography_ko": "마케도니아의 알렉산드로스 3세...",
    "biography_source": "wikipedia_en",
    "biography_source_url": "https://en.wikipedia.org/wiki/Alexander_the_Great",
    "image_url": "https://...",
    "wikipedia_url": "https://en.wikipedia.org/wiki/Alexander_the_Great",
    "era": "Classical Antiquity"
  },
  "names": [
    { "id": 1, "name": "Alexandros III", "language": "la", "name_type": "official", "is_primary": true },
    { "id": 2, "name": "Iskander", "language": "ar", "name_type": "alternate", "is_primary": false }
  ]
}
```

### GET /persons/{id}/flow
인물의 흐름 (시간순 이벤트 체인)

> 인물에 엮인 모든 이벤트를 시간순으로 정렬하여 반환. 탄생→이벤트들→사망을 잇는 역사의 실(thread).

**Response:**
```json
{
  "person_id": 1,
  "name": "Alexander the Great",
  "name_ko": "알렉산드로스 대왕",
  "birth_year": -356,
  "death_year": -323,
  "birthplace": { "id": 10, "name": "Pella", "lat": 40.76, "lng": 22.52 },
  "deathplace": { "id": 20, "name": "Babylon", "lat": 32.54, "lng": 44.42 },
  "flow": [
    { "event_id": 10, "title": "Battle of Granicus", "year": -334, "location": "Granicus", "lat": 40.34, "lng": 27.04, "role": "commander" },
    { "event_id": 11, "title": "Battle of Issus", "year": -333, "location": "Issus", "lat": 36.84, "lng": 36.17, "role": "commander" }
  ],
  "total_events": 2
}
```

### GET /persons/{id}/events
인물 관련 이벤트 조회

### GET /persons/{id}/relations
인물 관계 (관련 인물, 강도 포함)

### GET /persons/{id}/properties
Wikidata 속성 조회

### GET /persons/{id}/sources
인물 언급 출처 (책/문서)

---

## Locations API

### GET /locations
장소 목록 조회

### GET /locations/{id}
장소 상세 조회

### GET /locations/{id}/events
장소에서 발생한 이벤트 조회

---

## Search API

### GET /search
통합 검색

**Query Parameters:**
| 파라미터 | 타입 | 설명 |
|----------|------|------|
| q | string | 검색어 (필수) |
| type | string | event/person/location/all |
| limit | int | 결과 수 |

**Response:**
```json
{
  "query": "socrates",
  "results": {
    "events": [...],
    "persons": [...],
    "locations": [...]
  }
}
```

### GET /search/date-location
시간+장소 관측 (SHEBA)

**Query Parameters:**
| 파라미터 | 타입 | 설명 |
|----------|------|------|
| year | int | 연도 (필수) |
| latitude | float | 위도 |
| longitude | float | 경도 |
| radius_km | float | 반경 (기본 100km) |

**Response:**
```json
{
  "year": -490,
  "year_display": "490 BCE",
  "events": [...],
  "persons_active": [...]
}
```

---

## Chat API (SHEBA)

### POST /chat
자연어 질의

**Request:**
```json
{
  "query": "What happened at Marathon in 490 BCE?",
  "context": {
    "year": -490,
    "location": "Marathon"
  },
  "language": "en"
}
```

**Response:**
```json
{
  "answer": "The Battle of Marathon was...",
  "sources": [
    {
      "source": { "name": "Herodotus, Histories", "url": "..." },
      "relevance": 0.95
    }
  ],
  "confidence": 0.85,
  "related_events": [...],
  "suggested_queries": [
    "Who was Miltiades?",
    "What caused the Persian Wars?"
  ]
}
```

---

## Categories API

### GET /categories
카테고리 트리 조회

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "History",
      "name_ko": "역사",
      "color": "#3B82F6",
      "children": [
        { "id": 2, "name": "Military", "color": "#EF4444" }
      ]
    }
  ]
}
```

---

## Feed API

### GET /feed
통합 피드 (이벤트 + 인물). event_details/person_details JOIN으로 description 포함.

**Query Parameters:**
| 파라미터 | 타입 | 설명 |
|----------|------|------|
| year_start | int | 시작 연도 |
| year_end | int | 종료 연도 |
| limit | int | 결과 수 |

**Response:**
```json
{
  "items": [
    {
      "type": "event",
      "id": 1,
      "title": "Battle of Marathon",
      "date_start": -490,
      "importance": 5,
      "category": "battle",
      "location_name": "Marathon",
      "description": "The Battle of Marathon..."
    },
    {
      "type": "person",
      "id": 2,
      "title": "Socrates",
      "birth_year": -470,
      "death_year": -399,
      "role": "philosopher",
      "biography": "5th-century BCE Greek philosopher"
    }
  ],
  "events_total": 100,
  "persons_total": 50
}
```

---

## 구현 파일

- `backend/app/api/v1/events.py` (event_details JOIN, /locations 엔드포인트)
- `backend/app/api/v1/persons.py` (flow, relations, properties, sources 엔드포인트 포함)
- `backend/app/api/v1/locations.py`
- `backend/app/api/v1/search.py` (event_details JOIN for description search)
- `backend/app/api/v1/chat.py`
- `backend/app/api/v1/categories.py`
- `backend/app/api/v1/feed.py` (통합 피드 — event_details/person_details JOIN)
- `backend/app/api/v1/featured.py` (추천 인물/이벤트 — person_details JOIN)
- `backend/app/api/v1/story.py` (스토리 — event_details JOIN)
- `backend/app/api/v1/servants.py` (FGO 서번트 매핑)
- `backend/app/api/v1_new/globe.py` (지구본 — event_details JOIN)
- `backend/app/api/v1_new/stats.py` (통계 — event_details description_source)
- `backend/app/api/v1_new/explore.py` (탐색 — event_details slug JOIN)
