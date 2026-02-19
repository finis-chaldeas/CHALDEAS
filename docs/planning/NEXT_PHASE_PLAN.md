# Next Phase Plan: UX 혁신 + 데이터 풍부화

> **작성**: 2026-02-15
> **전제**: Data Enrichment Phase (role, importance, biography) 완료 후 진행

---

## 0. 현재 완료 상태 (체크리스트)

Phase가 끝나면 하나씩 검증:

- [ ] `persons.role` 채워짐 (2,305 → ~7M)
- [ ] `persons.birthplace_id` 채워짐 (0 → ~2M)
- [ ] `events.importance` 1-5 분포 (전부 3 → 골고루)
- [ ] `events.primary_location_id` 보강
- [ ] QRank 테이블 존재 + 매칭됨
- [ ] `persons.biography` Wikipedia 첫 문단 (최소 수만 건)
- [ ] Feed API 동작: `GET /api/v1/feed?year_start=-500&year_end=-300`
- [ ] Feed 탭에서 카드 표시 (importance 순, events+persons 혼합)
- [ ] TypeScript 빌드 에러 없음

---

## 1. 지구본 뷰 개선

### 1A. 글로벌 뷰 — 주요 사건 라벨 표시

**현재**: 모든 이벤트가 동일한 막대기(marker)로 표시
**목표**: importance 4-5 사건은 **이름 라벨이 달린 큰 마커**로, 나머지는 현재처럼 작은 막대기로

```
┌─ 글로벌 뷰 (줌 아웃) ─────────────────────────┐
│                                                 │
│         ★ Battle of Marathon                    │
│         490 BCE                                 │
│    ·  ·                                         │
│         ★ Peloponnesian War                    │
│  ·      431 BCE                                 │
│              ·  ·                                │
│                   ★ Battle of Gaugamela         │
│                   331 BCE                       │
│  · = importance 1-3 (막대기만)                   │
│  ★ = importance 4-5 (이름+연도 라벨)            │
└─────────────────────────────────────────────────┘
```

**구현 포인트**:
- `react-globe.gl`의 `labelsData` 사용 (현재 `pointsData`만 사용 중)
- importance >= 4인 이벤트는 labelsData에 추가, 나머지는 pointsData
- 라벨 스타일: 반투명 배경 + 작은 폰트 + 카테고리 색상
- 줌 레벨에 따라 라벨 표시 임계값 변경 (줌인하면 importance 3도 표시)

**난이도**: 중 (react-globe.gl labelsData API 활용)

### 1B. 로컬 뷰 — 항공 뷰 모드

**현재**: 확대해도 지구본 형태 유지 (구면)
**목표**: 충분히 확대하면 **2D 평면 맵처럼** 전환 — 상하좌우 드래그, 회전 없음

```
┌─ 로컬 뷰 (프랑스 확대) ──────────────────────┐
│ ○ Paris                                       │
│   ├─ 1789 French Revolution ★★★★★            │
│   ├─ 1572 St. Bartholomew's Day ★★★★        │
│   └─ 1431 Trial of Joan of Arc ★★★          │
│                                               │
│ ○ Versailles                                  │
│   └─ 1919 Treaty of Versailles ★★★★★        │
│                                               │
│ ○ Normandy                                    │
│   └─ 1944 D-Day ★★★★★                       │
│                                               │
│ [드래그: 상하좌우 이동 / 스크롤: 줌]          │
└───────────────────────────────────────────────┘
```

**구현 포인트**:
- `react-globe.gl`의 카메라 설정 변경: 줌 레벨 > 임계값이면 `enableRotate=false`, `enablePan=true`
- 또는 줌 레벨 > 임계값이면 Leaflet/Mapbox 2D 맵으로 전환
- 로케이션 중심으로 클러스터링: 같은 도시의 이벤트는 그룹으로 표시

**난이도**: 상 (카메라 컨트롤 커스텀 or 맵 라이브러리 전환)

---

## 2. 로케이션 상시 표시 + 시대별 명칭

### 2A. 로케이션 = 고정 앵커

**현재**: 이벤트 위치만 마커로 표시 (이벤트가 없으면 안 보임)
**목표**: 주요 로케이션은 **항상 지구본에 고정** — 시대와 무관하게 존재

```
현재 시대에 이벤트가 있는 로케이션:  ● 밝은 마커
현재 시대에 이벤트가 없는 로케이션:  ○ 흐린 마커 (배경)
```

**데이터**: locations 테이블에서 `event_count > N` (또는 connection_count)인 주요 도시 선별
- 전체 로케이션을 다 보여주면 너무 많음 → **tier 시스템**
  - Tier 1 (항상 표시): event_count > 50 (~수백 개 도시)
  - Tier 2 (regional 줌): event_count > 10
  - Tier 3 (local 줌): 전부

**난이도**: 하 (globeStore에 locations 레이어 추가)

### 2B. 시대별 명칭 변화

**이미 설계됨**: `location_names` 테이블 (마이그레이션 008)

```
location_id=42 (좌표: 41.01, 28.98)
├─ Byzantium     (BCE 667 ~ 330 CE)   type=official
├─ Constantinople (330 ~ 1453)         type=official
├─ Konstantiniyye (1453 ~ 1930)        type=official
└─ Istanbul       (1930 ~ 현재)        type=official
```

**표시 방식**:
- 현재 시대(currentYear)에 따라 `location_names`에서 해당 시기의 `is_primary=true` 이름 조회
- 없으면 기본 `locations.name` 사용
- 글로브 마커 라벨에 시대별 이름 표시

**데이터 채우기**:
- Wikidata P1448 (official name) + 시기 한정자(P580/P582)에서 추출
- 또는 Wikipedia "Name" / "Etymology" 섹션에서 LLM 추출
- 주요 도시 200-500개만 먼저 수동/반자동 큐레이션

**API 수정**:
```
GET /api/v1/locations?year=-500
→ 각 location에 temporal_name 필드 추가
```

**난이도**: 중 (데이터 수집이 주 작업, 코드는 간단)

### 2C. 시대별 소속(정치체) 변화

**개념**: 로케이션이 어느 정치체에 속했는지 시대별로 변화
```
Paris:
├─ 가울 (갈리아) (BCE ~ 52 BCE)
├─ 로마 제국 (52 BCE ~ 486)
├─ 프랑크 왕국 (486 ~ 843)
├─ 프랑스 왕국 (843 ~ 1792)
├─ 프랑스 제1공화국 (1792 ~ 1804)
└─ ... → 현재 프랑스
```

**구현 방향**:
- `location_polities` 테이블 (location_id, polity_name, valid_from, valid_until)
- Wikidata P17 (country) + 시기 한정자에서 대부분 추출 가능
- 지구본에서 확대 시 **영토 경계** 표시는 복잡 → v2에서 고려
- 우선은 텍스트로만: "Paris · 프랑스 왕국 (843-1792)"

**난이도**: 중상 (Wikidata P17 시계열 추출은 가능하나 데이터 정리 필요)

---

## 3. FGO 오타쿠 친화 레이어

### 3A. Highlight 카드 (시대별 큐레이션)

**목표**: 시대+지역별 "한 줄 요약 + 주요 사건 + 관련 서번트" 큐레이션

```json
{
  "id": "classical-greece",
  "title": "Classical Greece",
  "title_ko": "고전기 그리스",
  "period": [-500, -300],
  "region": "Greece",
  "summary": "그리스-페르시아 전쟁에서 알렉산더 대왕의 정복까지, 서양 문명의 기초가 만들어진 시대",
  "key_events": [123, 456, 789],
  "servants": ["Leonidas I", "Iskandar", "Medea"],
  "difficulty": "beginner"
}
```

**표시 위치**: Feed 탭 상단에 "추천 시대" 카드로 표시 (현재 시간대 기반)

**데이터 생성**:
- 초기 30-50개 수동 작성 (또는 LLM 초안 + 검수)
- 서번트 매핑은 기존 `servants` 데이터 활용
- 테이블: `highlights` (id, title, period_start, period_end, region, summary, difficulty)

**난이도**: 하 (데이터만 만들면 됨, 코드 간단)

### 3B. Wikipedia 설명 강화

**현재**: events.description = Wikidata 한 줄 요약 (빈약)
**목표**: Wikipedia 첫 2-3문장으로 교체

**방법**:
1. `extract_biographies.py` (Phase 4, 이미 작성)로 persons.biography 채우기
2. 동일 로직으로 events.description도 Wikipedia에서 채우기 → `extract_event_descriptions.py` 신규

**난이도**: 하 (기존 패턴 재활용)

### 3C. Simple English 옵션

**목표**: 영어가 어려운 사용자를 위해 Simple English Wikipedia 설명 제공

**방법**:
- Simple English Wikipedia API: `https://simple.wikipedia.org/w/api.php`
- Wikidata QID → Simple English Wikipedia 문서 자동 연결
- persons/events에 `description_simple` 컬럼 추가

**난이도**: 중 (API 호출 + 매칭, 커버리지 낮을 수 있음)

### 3D. 서번트 → 역사 브릿지

**현재**: 서번트 패널에서 역사적 인물 연결은 되지만, 탐색 흐름이 자연스럽지 않음
**목표**: 서번트 카드에서 "이 시대 탐색" 버튼 → 해당 시대+지역으로 글로브 이동 + Feed 표시

```
길가메쉬 카드 → [이 시대 탐색]
→ 글로브가 메소포타미아로 이동, 연도 BCE 2700으로 설정
→ Feed에 수메르 관련 이벤트/인물 표시
```

**난이도**: 하 (globeStore.setYear + setViewport 호출)

---

## 4. 구현 우선순위

| # | 항목 | 난이도 | 임팩트 | 의존성 |
|---|------|--------|--------|--------|
| 1 | **Feed 카드에 Wikipedia 설명 표시** (3B) | 하 | 상 | enrichment 완료 |
| 2 | **글로벌 뷰 주요 사건 라벨** (1A) | 중 | 상 | importance 분포 |
| 3 | **로케이션 상시 표시** (2A) | 하 | 중 | - |
| 4 | **Highlight 큐레이션 30개** (3A) | 하 | 상 | 수동 작업 |
| 5 | **서번트 → 시대 탐색 버튼** (3D) | 하 | 중 | - |
| 6 | **시대별 로케이션 명칭** (2B) | 중 | 중 | location_names 데이터 |
| 7 | **로컬 뷰 항공 모드** (1B) | 상 | 상 | 카메라 제어 리서치 |
| 8 | **시대별 소속 변화** (2C) | 중상 | 중 | Wikidata P17 추출 |
| 9 | **Simple English 옵션** (3C) | 중 | 하 | API 커버리지 확인 |

### 추천 실행 순서

**Sprint 1 (즉시)**: #1, #3, #5 — 코드만으로 즉시 개선
**Sprint 2 (1주)**: #2, #4 — 라벨 표시 + 큐레이션 작성
**Sprint 3 (2주)**: #6, #7 — 로케이션 명칭 + 뷰 전환
**Backlog**: #8, #9

---

## 5. 기술 참고

### react-globe.gl 라벨 표시 (1A)

```tsx
// labelsData: importance >= 4인 이벤트
<Globe
  labelsData={majorEvents}
  labelLat={d => d.latitude}
  labelLng={d => d.longitude}
  labelText={d => d.title}
  labelSize={d => d.importance >= 5 ? 1.5 : 1.0}
  labelColor={() => 'rgba(255, 215, 0, 0.9)'}
  labelResolution={2}
  // 기존 pointsData는 유지
  pointsData={minorEvents}
/>
```

### 로케이션 상시 표시 (2A)

```tsx
// 별도 레이어로 로케이션 표시
<Globe
  // 이벤트 마커 (현재)
  pointsData={eventMarkers}
  // 로케이션 앵커 (신규)
  htmlElementsData={locationAnchors}
  htmlElement={d => {
    const el = document.createElement('div')
    el.className = d.hasEvents ? 'loc-active' : 'loc-dormant'
    el.textContent = d.temporalName
    return el
  }}
/>
```

### 시대별 명칭 쿼리 (2B)

```sql
SELECT l.id, l.latitude, l.longitude,
  COALESCE(
    (SELECT ln.name FROM location_names ln
     WHERE ln.location_id = l.id AND ln.is_primary = true
       AND (ln.valid_from IS NULL OR ln.valid_from <= :year)
       AND (ln.valid_until IS NULL OR ln.valid_until >= :year)
     LIMIT 1),
    l.name
  ) as temporal_name
FROM locations l
WHERE l.latitude IS NOT NULL
```

---

## 6. 데이터 소스 정리

| 데이터 | 소스 | 방법 | 비용 |
|--------|------|------|------|
| 이벤트 설명 | English Wikipedia | 첫 2-3문장 추출 | 무료 (로컬) |
| 인물 전기 | English Wikipedia | 첫 문단 추출 | 무료 (로컬) |
| 시대별 명칭 | Wikidata P1448 | SPARQL/dump 추출 | 무료 |
| 시대별 소속 | Wikidata P17 | SPARQL/dump 추출 | 무료 |
| 하이라이트 큐레이션 | 수동 + LLM 보조 | gpt-5-mini 요약 | ~$2 |
| Simple English | simple.wikipedia.org | API 호출 | 무료 |
| QRank 인기도 | qrank.toolforge.org | CSV 다운로드 | 무료 |
