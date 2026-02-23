# 프론트엔드가 쓸 수 있는 API 전체

Base URL: `/api/v1`

프론트엔드가 "이런 데이터를 보여주고 싶은데 API가 있나?"라고 물었을 때 답하는 문서.
각 API의 현재 프론트엔드 사용 여부를 표시한다.

**범례**:
- **사용 중**: 현재 프론트엔드에서 호출하는 API
- **미사용**: API는 존재하지만 프론트엔드에서 호출하지 않는 API
- **신규**: 최근 추가된 API

---

## Events API

| 엔드포인트 | 설명 | 상태 |
|-----------|------|------|
| `GET /events` | 이벤트 목록 (뷰포트, 시간, 카테고리 필터) | **사용 중** |
| `GET /events/{id}` | 이벤트 상세 (details, persons, sources 포함) | **사용 중** |
| `GET /events/{id}/children` | 하위 이벤트 (재귀 옵션) | **사용 중** |
| `GET /events/{id}/relationships` | 인과관계 (causes/enables/follows) | 미사용 |
| `GET /events/{id}/locations` | 로케이션 (aggregate는 하위 재귀 수집) | 미사용 |
| `GET /events/{id}/histories` | 이 사건이 언급된 History 에세이 | 미사용 |
| `GET /events/slug/{slug}` | 슬러그로 조회 | 미사용 |
| `GET /events/map` | 지도 마커용 (간소화) | 미사용 |
| `GET /events/stats` | 통계 (좌표 포함) | 미사용 |
| `GET /events/hierarchy` | 이벤트 트리 뷰 | 미사용 |
| `GET /events/aggregates` | 상위 이벤트만 | 미사용 |

**핵심 파라미터** (GET /events):
- `year_start`, `year_end`: 시간 범위
- `lat_min`, `lat_max`, `lng_min`, `lng_max`: 뷰포트 범위
- `category`: 카테고리 슬러그
- `importance_min`: 최소 중요도 (1-5)
- `limit`, `offset`: 페이지네이션

---

## Persons API

| 엔드포인트 | 설명 | 상태 |
|-----------|------|------|
| `GET /persons` | 인물 목록 (시간, 역할, 뷰포트 필터) | **사용 중** |
| `GET /persons/{id}` | 인물 상세 (details, names, birth/death locations) | **사용 중** |
| `GET /persons/{id}/narrative` | AI 생성 서사 | **사용 중** |
| `GET /persons/{id}/flow` | **생애 흐름** (시간순 이벤트 체인 + 지도 좌표) | 미사용 |
| `GET /persons/{id}/events` | 참여 이벤트 목록 | 미사용 |
| `GET /persons/{id}/relations` | **관계 네트워크** (type, strength 포함) | 미사용 |
| `GET /persons/{id}/sources` | 언급된 출처 (책/문서) | 미사용 |
| `GET /persons/{id}/properties` | Wikidata 속성 (P106, P27 등) | 미사용 |
| `GET /persons/{id}/histories` | 이 인물이 등장하는 History 에세이 | 미사용 |
| `GET /persons/{id}/wikipedia` | Wikipedia 문서 참조 | 미사용 |
| `GET /persons/network` | 인물 관계 그래프 데이터 | 미사용 |

**flow API 반환 데이터**:
```json
{
  "person_id": 1,
  "name": "Alexander the Great",
  "birthplace": { "name": "Pella", "lat": 40.76, "lng": 22.52 },
  "deathplace": { "name": "Babylon", "lat": 32.54, "lng": 44.42 },
  "flow": [
    { "event_id": 10, "title": "Battle of Granicus", "year": -334,
      "location": "Granicus", "lat": 40.34, "lng": 27.04, "role": "commander" }
  ]
}
```
→ 글로브 위에 인물의 생애 경로를 선으로 그릴 수 있다.

---

## Locations API

| 엔드포인트 | 설명 | 상태 |
|-----------|------|------|
| `GET /locations` | 장소 목록 (뷰포트, type 필터) | 미사용 |
| `GET /locations/{id}` | 장소 상세 (영토 이력, 시대별 이름, 사건) | **사용 중** |
| `GET /locations/{id}/events` | 이 장소의 사건 목록 | 미사용 |
| `GET /locations/stats` | 장소 통계/커버리지 | 미사용 |

---

## Timeline / Periods API

| 엔드포인트 | 설명 | 상태 |
|-----------|------|------|
| `GET /timeline/periods` | 50년 단위 시대 목록 (global + regional 서사) | **사용 중** |
| `GET /timeline/periods/{start}` | 시대 상세 (지역별 narratives) | **사용 중** |
| `GET /timeline/periods/{start}/events` | 해당 시대 이벤트 | 미사용 |
| `GET /timeline/periods/{start}/persons` | 해당 시대 인물 | 미사용 |
| `POST /timeline/feedback` | 사용자 피드백 | **사용 중** |

**periods 반환 데이터**:
```json
{
  "period_start": -500,
  "period_end": -451,
  "headline": "The Birth of Western Civilization",
  "narrative": "In the 5th century BCE...",
  "keywords": ["democracy", "philosophy"],
  "defining_moment": "The Battle of Salamis",
  "regional": {
    "europe": { "headline": "...", "narrative": "..." },
    "east_asia": { "headline": "...", "narrative": "..." }
  }
}
```

---

## Feed API

| 엔드포인트 | 설명 | 상태 |
|-----------|------|------|
| `GET /feed` | 통합 피드 (이벤트+인물, importance순, 뷰포트 인식) | **사용 중** |

**핵심 파라미터**:
- `year_start`, `year_end`: 시간 범위
- `lat_min/max`, `lng_min/max`: 뷰포트
- `limit`: 결과 수

**반환**: events와 persons를 interleave하여 importance순으로 정렬.

---

## Search API

| 엔드포인트 | 설명 | 상태 |
|-----------|------|------|
| `GET /search` | 통합 텍스트 검색 (events/persons/locations) | **사용 중** |
| `GET /search/basic` | BM25 키워드 검색 (AI 없음) | 미사용 |
| `POST /search/advanced` | BM25 + 벡터 + AI (OpenAI 키 필요) | 미사용 |
| `GET /search/date-location` | 시간+장소 관측 (SHEBA) | 미사용 |
| `GET /search/logs/public` | 공개 검색 기록 | 미사용 |

---

## Chat / Agent API

| 엔드포인트 | 설명 | 상태 |
|-----------|------|------|
| `POST /chat/agent` | 지능형 에이전트 응답 (소스 포함) | **사용 중** |
| `POST /chat` | 기본 채팅 | 미사용 |
| `POST /chat/observe` | 관측 (LLM 없음) | 미사용 |
| `POST /chat/rag` | RAG 검색 + 소스 | 미사용 |

---

## Sources API

| 엔드포인트 | 설명 | 상태 |
|-----------|------|------|
| `GET /sources` | 출처 목록 (페이지네이션) | **사용 중** |
| `GET /sources/{id}` | 출처 상세 (메타데이터) | **사용 중** |
| `GET /sources/{id}/persons` | 출처에 언급된 인물 | **사용 중** |
| `GET /sources/{id}/mentions` | 출처의 모든 언급 | **사용 중** |
| `GET /sources/{id}/wiki` | Wikipedia 전문 | 미사용 |

---

## Histories API

| 엔드포인트 | 설명 | 상태 |
|-----------|------|------|
| `GET /histories` | History 목록 (카테고리, 시대, 태그, 상태 필터) | **사용 중** |
| `GET /histories/{id}` | History 상세 (entities 포함) | **사용 중** |
| `POST /histories` | History 생성 (entity 태그 자동 파싱) | **사용 중** |
| `PUT /histories/{id}` | History 수정 (entity 재동기화) | **사용 중** |
| `DELETE /histories/{id}` | History 삭제 | **사용 중** |

---

## Featured / Showcase API

| 엔드포인트 | 설명 | 상태 |
|-----------|------|------|
| `GET /showcases/fgo/singularities` | FGO 특이점 목록 | **사용 중** |
| `GET /showcases/fgo/lostbelts` | FGO 이문대 목록 | **사용 중** |
| `GET /showcases/fgo/servants` | FGO 서번트 기사 | **사용 중** |
| `GET /showcases/history` | 역사 기사 | **사용 중** |
| `GET /showcases/literature` | 문학 기사 | **사용 중** |
| `GET /showcases/music` | 음악 기사 | **사용 중** |
| `GET /showcases/{id}` | 쇼케이스 상세 | 미사용 |
| `GET /showcases` | 전체 쇼케이스 | 미사용 |
| `GET /showcases/stats/summary` | 쇼케이스 통계 | 미사용 |
| `GET /featured/persons` | 추천 인물 (시대별) | 미사용 |
| `GET /featured/random` | 랜덤 추천 인물 | 미사용 |
| `GET /featured/servants` | 추천 FGO 서번트 | 미사용 |

---

## FGO Servants API

| 엔드포인트 | 설명 | 상태 |
|-----------|------|------|
| `GET /servants` | 서번트 목록 (필터 지원) | **사용 중** |
| `GET /servants/{name}` | 서번트 상세 + 책 언급 | 미사용 |
| `GET /servants/by-person/{id}` | 인물에 매핑된 서번트 | 미사용 |
| `GET /servants/stats` | 서번트↔역사 매핑 통계 | 미사용 |
| `GET /servants/{name}/comparison` | FGO vs 역사 비교 | 미사용 |

---

## Globe API (V1 확장)

| 엔드포인트 | 설명 | 상태 |
|-----------|------|------|
| `GET /globe/markers` | 글로브 마커 (type, time, bbox 필터) | 미사용 |
| `GET /globe/anchor-locations` | 주요 도시 (tier별) | 미사용 |
| `GET /globe/markers/stats` | 마커 가용성 | 미사용 |
| `GET /globe/markers/density` | 시간별 이벤트 밀도 | 미사용 |
| `GET /globe/connections/{type}/{id}` | 엔티티 연결선 | 미사용 |
| `GET /globe/arcs/{event_id}` | 이벤트 인과관계 아크 | 미사용 |
| `GET /globe/clusters` | 지리적 마커 클러스터 | 미사용 |
| `GET /globe/nodes` | 줌 레벨별 위치 노드 | 미사용 |
| `GET /globe/nodes/{location_id}/events` | 위치의 이벤트 | 미사용 |

---

## Explore API (V1 확장)

| 엔드포인트 | 설명 | 상태 |
|-----------|------|------|
| `GET /explore/stats` | 엔티티 수/그룹핑 | 미사용 |
| `GET /explore/persons` | 인물 탐색 (검색, 필터, 페이지네이션) | 미사용 |
| `GET /explore/locations` | 장소 탐색 | 미사용 |
| `GET /explore/events` | 이벤트 탐색 | 미사용 |
| `GET /explore/polities` | 정치체 탐색 | 미사용 |
| `GET /explore/periods` | 시대 탐색 | 미사용 |
| `GET /explore/top-mentioned` | 가장 많이 언급된 엔티티 | 미사용 |

---

## 기타 API

| 엔드포인트 | 설명 | 상태 |
|-----------|------|------|
| `GET /categories` | 카테고리 트리 | 미사용 |
| `GET /properties/{type}/{id}` | Wikidata 속성 | 미사용 |
| `POST /reports` | 콘텐츠 품질 신고 | **사용 중** |
| `GET /reports/stats` | 신고 통계 (관리자) | 미사용 |
| `GET /threads` | 인물별 이벤트 그룹 | 미사용 |
| `GET /threads/{id}/events` | 스레드 내 이벤트 | 미사용 |
| `GET /story/person/{id}` | 인물 스토리 (노드+경로) | 미사용 |
| `GET /story/person/{id}/check` | 스토리 데이터 가용성 | 미사용 |

---

## 사용률 요약

| 구분 | 수 |
|------|-----|
| **사용 중** | ~35개 |
| **미사용** | ~35개 |
| **전체** | ~70개 |

---

## 미사용이지만 프론트엔드에서 반드시 노출해야 할 API

원칙 5 (백엔드 기능 전부 노출)에 따라, 다음 API는 프론트엔드 UI가 필요하다:

### 최우선 (핵심 경험)
1. **`/persons/{id}/flow`** — 인물 생애 경로를 글로브 위에 선으로 표시
2. **`/persons/{id}/relations`** — 인물 관계 네트워크 시각화
3. **`/events/{id}/relationships`** — 인과관계 화살표 (이벤트 카드 + 글로브)
4. **`/events/{id}/locations`** — aggregate 이벤트의 하위 위치들

### 우선 (풍부한 경험)
5. **`/persons/{id}/sources`** — "이 인물에 대해 더 읽기" 출처 목록
6. **`/persons/{id}/properties`** — Wikidata 속성 (종교, 국적, 직업 등)
7. **`/persons/{id}/histories`** / **`/events/{id}/histories`** — 관련 History 에세이
8. **`/timeline/periods/{start}/events`** — 시대별 이벤트 탐색
9. **`/timeline/periods/{start}/persons`** — 시대별 인물 탐색

### 차후 (탐색 심화)
10. **`/globe/*`** — V1 Globe API (줌 레벨별 마커, 클러스터, 밀도)
11. **`/explore/*`** — V1 Explore API (전체 데이터 탐색)
12. **`/search/date-location`** — 시간+장소 관측
13. **`/categories`** — 카테고리별 필터/색상
14. **`/locations/{id}/events`** — 장소별 사건 타임라인
