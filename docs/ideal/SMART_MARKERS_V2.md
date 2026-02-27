# 스마트 마커 V2: 글로브 이벤트 표시 시스템 재설계

---

## 현재 문제점

### 1. 이벤트 실종
- **증상**: 줌 레벨이 바뀌면 importance 4-5 이벤트가 지도에서 사라짐
- **원인**: `_select_heroes`가 `max_heroes` 한도 초과 시 이벤트를 orphan으로 분류하고, 가까운 히어로에 귀속시키지만 — 히어로의 `nearby_events` 캡(기존 7, 현재 50)이 부족하거나, 아예 귀속할 히어로가 없으면 완전히 소실
- **예시**: 630 BCE에서 "페르시아-그리스 전쟁" (imp 5)이 cosmic 줌에서 지도에 없음

### 2. 배지 모달 위치 오류
- **증상**: 배지 클릭 시 모달에서 흡수된 이벤트의 위치가 "Unknown"이나 히어로 위치로 표시
- **원인**: nearby_events에 location_name이 없는 경우 폴백 처리 부실

### 3. 모달 Z-index
- **증상**: 배지 모달이 다른 히어로 카드 뒤에 가려짐
- **원인**: CSS2DRenderer에서 z-index 미설정

### 4. 클릭해도 반응 없음
- **증상**: 흡수된 이벤트를 클릭해도 지도에 찍히지 않음
- **원인**: 클릭 → NarrativePanel만 열리고, 지도에서는 해당 이벤트의 위치로 이동하거나 마커를 표시하지 않음

### 5. 스크롤 시 카드 불안정
- **증상**: 살짝 글로브를 돌려도 히어로 카드가 나타났다 사라짐
- **원인**: `_select_heroes`가 deterministic하지 않음 — 후보 순서가 미세하게 바뀌면 다른 히어로 세트가 선택됨

---

## 핵심 원칙 (V2 규칙)

### 규칙 1: Importance ≥ 4는 절대 실종 불가
> 어떤 줌이든, 어떤 뷰포트든, importance 4 이상의 이벤트는 **반드시** 지도에 존재해야 한다.
> 자기 자신의 히어로 카드이든, 다른 히어로의 배지 안이든 — 어딘가에는 있어야 한다.

- 히어로로 선택되지 못한 imp≥4 이벤트 → 가까운 히어로에 귀속
- 가까운 히어로도 없으면 → **강제 히어로 승격** (max_heroes 초과 허용)
- `nearby_events` 캡 무제한 (또는 충분히 큰 값)

### 규칙 2: 클릭 = 즉시 독립
> 흡수된 이벤트를 클릭하면, 해당 이벤트가 **지도에 독립 마커로 찍히고**, 글로브가 **그 위치로 이동**한다.

- 배지 모달에서 이벤트 클릭 → "pinned event"로 글로브에 찍힘
- 글로브가 해당 위치로 fly
- NarrativePanel이 열림
- pinned event는 금색 테두리 + 펄스 애니메이션으로 구분
- smart-markers가 새로 갱신되어 해당 이벤트가 일반 히어로로 나타나면 pin 자동 해제

### 규칙 3: 모달은 항상 최상위
> 배지 클릭으로 열린 모달은 **모든 히어로 카드 위에** 떠야 한다.

- `z-index: 10000` 으로 항상 최상위
- 히어로 카드와 겹치는 상황에서도 읽을 수 있어야 함

### 규칙 4: 위치 그룹핑은 정확해야
> 배지 모달의 이벤트는 **실제 위치**별로 그룹핑되어야 한다.
> location_name이 없으면 히어로 위치가 아니라, 좌표 기반으로 판단한다.

- 이벤트에 location_name이 있으면 → 그대로 사용
- 없으면 → 좌표로 히어로와의 거리 계산:
  - 0.5° 이내: 히어로 위치에 포함
  - 0.5° 이상: "Nearby" 그룹으로 분류
- 같은 위치 이벤트 먼저, 다른 위치 이벤트는 거리순

### 규칙 5: 히어로 선택은 안정적이어야
> 뷰포트가 소폭 변해도 기존 히어로가 사라지면 안 된다.

현재 문제: bounds를 보내지 않아서 이론적으로 안정적이어야 하지만, `debouncedYear`나 `currentZoomLevel`이 경계값에서 왔다갔다 하면 쿼리가 재실행됨.

- 줌 레벨 변경에 hysteresis 적용 (cosmic→continental 임계값과 continental→cosmic 임계값을 다르게)
- 히어로 선택 시 이전 프레임의 히어로를 우선 유지 (sticky heroes)

---

## 아키텍처

### 데이터 흐름

```
[백엔드 smart-markers API]
  ↓ candidates: imp≥min_importance, ±100yr
  ↓ _select_heroes(): 겹침 방지 + 스태킹
  ↓ Pass 2: imp≥4 orphan → 귀속 or 승격
  ↓ nearby_events: max 50, importance desc
  ↓ nearby_persons: max 5, score desc
  ↓
[프론트엔드 smart-markers query]
  ↓ queryKey: [debouncedYear, currentZoomLevel]
  ↓ placeholderData: 이전 데이터 유지 (flicker 방지)
  ↓
[normalHtmlElements useMemo]
  ↓ 1. SHEBA highlights
  ↓ 2. Hero cards (from smartMarkers)
  ↓ 2b. Arc target events
  ↓ 2c. Pinned event (from globeStore)
  ↓ 3. Location nodes (city labels)
  ↓ 4. Event-panel (mini modal from badge click)
  ↓
[htmlElementFn callback]
  ↓ hero → hero card HTML (with badge, companions)
  ↓ event-panel → mini modal HTML (location-grouped, z-index: 10000)
  ↓
[사용자 인터랙션]
  ↓ 카드 본문 클릭 → NarrativePanel
  ↓ 배지 클릭 → mini modal (location-grouped)
  ↓ 모달 내 이벤트 클릭 → pin + fly + NarrativePanel
  ↓ 인물 클릭 → PersonDetailView
  ↓ 위치명 클릭 → 해당 위치 이벤트 목록
```

### 백엔드 변경 요약

| 항목 | 기존 | V2 |
|------|------|-----|
| candidate_limit | max_heroes × 5 | max(max_heroes × 10, 150) |
| _select_heroes Pass 2 | imp≥4 orphan → nearest hero 귀속 | 가까우면 귀속, 멀면 **히어로 승격** |
| nearby_events cap | 7 → 25 → 50 | **50** (충분히 큰 값) |
| nearby_event_count | len(raw_nearby) | 변경 없음 (실제 총 수) |

### 프론트엔드 변경 요약

| 항목 | 기존 | V2 |
|------|------|-----|
| 배지 모달 z-index | 없음 | `el.style.zIndex = '10000'` |
| 배지 모달 companion 필터 | companion 제외 | **제외 안 함** (전부 표시) |
| 배지 모달 위치 그룹핑 | flat list | **location_name별 그룹** + 거리순 정렬 |
| 모달 이벤트 클릭 | NarrativePanel만 | **pin + fly + NarrativePanel** |
| globeStore | — | `pinnedEvent` 상태 추가 |
| htmlElements | — | pinned event → 금색 히어로 카드 |
| PersonDetailView | 렌더 안 됨 | **App.tsx에서 렌더** (인물 클릭 버그 수정) |

---

## 파일별 변경 내역

### `backend/app/api/v1_new/globe.py`
- `candidate_limit`: `max(max_heroes * 10, 150)`
- `_select_heroes()` Pass 2: imp≥4 orphan이 `max_attr_dist` 밖이면 히어로로 승격
- `nearby_events` 캡: `raw_nearby[:50]`

### `frontend/src/store/globeStore.ts`
- `PinnedEvent` 인터페이스 추가
- `pinnedEvent`, `setPinnedEvent`, `clearPinnedEvent` 추가

### `frontend/src/components/globe/GlobeContainer.tsx`
- `pinnedEvent` 선택자 추가
- `normalHtmlElements`에 pinned event를 히어로로 추가 (2c)
- `pinnedEvent`를 useMemo deps에 추가
- smart-markers 갱신 시 pin 자동 해제 useEffect
- mini modal: `el.style.zIndex = '10000'`
- mini modal 이벤트 클릭: `setPinnedEvent` + `flyToLocation` + `onEventClick`
- location grouping: 좌표 기반 판단 (heroLocName 폴백 제거)
- node 클릭 경로: location_name 포함
- pinned hero: `hero-card--pinned` CSS 클래스, compact 모드 무시

### `frontend/src/App.tsx`
- `personDetailId` 상태 변수 복원 (기존: `[, setPersonDetailId]`)
- `PersonDetailView` lazy import + 조건부 렌더

### `frontend/src/types/index.ts`
- `ClusterEvent`에 `lat?`, `lng?` 추가

### `frontend/src/styles/globals.css`
- `.globe-mini-modal-loc-group` (위치 그룹 헤더)
- `.globe-mini-modal-loc-group--remote` (원격 위치 헤더)
- `.hero-card--pinned` (금색 테두리 + 펄스)

---

## 미구현 / 추후 과제

### 줌 레벨 Hysteresis
현재 `getZoomLevel(altitude)`는 단순 임계값 비교. cosmic↔continental 경계에서 카드가 왔다갔다.
- 방향별 임계값 분리: zoom-in 임계와 zoom-out 임계를 다르게 → 경계에서 안정

### Sticky Heroes
줌이 바뀌어도 이전 프레임의 히어로를 일정 시간 유지.
- 이전 hero ID 세트를 캐시
- 새 hero 후보에 이전 hero가 포함되면 우선 선택
- 3초 후 자연 전환

### nearby_events 동적 로딩
현재 nearby_events는 smart-markers 응답에 50개까지 포함. 50개 초과 시 배지 모달에서 "더 보기" → 별도 API 호출.

### 배지 모달에서 서브 시프트 열기
배지 모달의 aggregate 이벤트 → 바로 히스토리 시프트로 열기 (있으면).
