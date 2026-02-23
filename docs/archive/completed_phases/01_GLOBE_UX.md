# 01. 지구본 뷰 UX

## 줌 레벨 정의

4단계 줌으로 경험이 전환된다. **지구본은 항상 지구본** — 2D 맵 전환 없음, 곡률이 줄어들 뿐.

```
Level 1: COSMIC (줌 아웃 최대)
  → 지구 전체가 보임
  → 시대의 "분위기"를 보여줌

Level 2: CONTINENTAL (대륙)
  → 유럽, 동아시아 등 대륙 단위
  → 주요 사건 라벨이 보이기 시작

Level 3: REGIONAL (지역/국가)
  → 프랑스, 그리스 등 국가 단위
  → 곡률이 약간 느껴짐 (항공뷰)
  → 로케이션 앵커가 보이기 시작

Level 4: LOCAL (도시)
  → 아테네, 파리 등 도시 단위
  → 거의 평면에 가까운 곡률
  → 모든 이벤트 + 로케이션 상세 표시
```

---

## Level 1: COSMIC — "이 시대의 세계"

### 유저 경험

```
유저가 타임라인을 BCE 500으로 이동 →

지구본이 천천히 회전하며 보여줌:
  ★ "Greco-Persian Wars" (그리스 위치에 빛나는 라벨)
  ★ "Spring and Autumn Period" (중국 위치에 라벨)
  ★ "Roman Republic Founded" (이탈리아에 라벨)
  · · · (나머지는 작은 점으로만)

유저: "아 이 시대에 그리스랑 중국이랑 로마가 동시에..."
```

### 마커 규칙

| importance | 표시 방식 | 라벨 |
|------------|----------|------|
| 5 | 큰 빛나는 마커 (금색 glow) | 제목 + 연도 항상 표시 |
| 4 | 중간 마커 (cyan glow) | 제목만 표시 (연도 생략) |
| 3 | 작은 점 | 라벨 없음 (hover 시 표시) |
| 1-2 | 미세 점 | 라벨 없음 |

### 자동 회전

- 타임라인 이동 시 지구본이 **주요 사건 밀집 지역**을 향해 자동 회전
- BCE 500 → 지중해 쪽으로 살짝 기울어짐
- 1940 → 유럽 쪽으로 살짝 기울어짐
- 수동 드래그하면 자동 회전 중지

### 배경 분위기

- 이벤트 밀도가 높은 지역: 은은한 히트맵 (지표면 glow)
- 시대별 컬러 톤 변화 (선택사항):
  - 고대: 따뜻한 골드/앰버
  - 중세: 어두운 퍼플/레드
  - 근현대: 차가운 블루/화이트

---

## Level 2: CONTINENTAL — "이 대륙에서 무슨 일이"

### 유저 경험

```
유저가 지중해 쪽으로 줌인 →

지구본이 유럽+북아프리카+서아시아를 보여줌:
  ★ Battle of Marathon (그리스, -490)
  ★ Founding of Rome (-753)
  ★ Persian Empire expansion (이란)
  ○ Athens (로케이션 앵커, 항상 표시)
  ○ Rome (로케이션 앵커)
  ○ Babylon (로케이션 앵커, 흐리게)
  · · · · (중요도 낮은 이벤트들)

Feed 탭이 자동으로 이 지역 이벤트/인물로 필터됨
```

### 마커 규칙 변화

| 요소 | 표시 |
|------|------|
| importance 5 | 큰 라벨 + 카테고리 아이콘 |
| importance 4 | 중간 라벨 |
| importance 3 | 작은 라벨 (제목만) |
| importance 1-2 | 점 (hover 시 표시) |
| 로케이션 (이벤트 있음) | ● 밝은 앵커 + 이름 |
| 로케이션 (이벤트 없음) | ○ 흐린 앵커 |

### 커넥션 라인

- 같은 인물이 참여한 이벤트 간 **얇은 선** 표시 (선택 사항)
- 예: 알렉산더 대왕의 이동 경로가 선으로 이어짐
- 기본 OFF, 특정 인물 선택 시 ON

---

## Level 3: REGIONAL (항공뷰) — "이 나라의 이야기"

### 유저 경험

```
유저가 프랑스 지역으로 줌인 →

지구본의 곡률이 살짝 느껴지는 항공뷰:
  지구본이 더 이상 회전하지 않음 (드래그 = 패닝)
  스크롤 = 줌인/줌아웃

  ● Paris  ─── "French Revolution (1789)" ★★★★★
              "Storming of the Bastille (1789)" ★★★★
              "Execution of Louis XVI (1793)" ★★★★

  ● Versailles ── "Treaty of Versailles (1919)" ★★★★★

  ● Orléans ── "Siege of Orléans (1429)" ★★★★
               서번트: 잔 다르크 👤

  ● Normandy ── "D-Day (1944)" ★★★★★

  로케이션 이름이 시대에 맞게 표시:
    "Lutetia" (BCE) → "Paris" (현재)
```

### 조작 방식 전환

**줌 임계값을 넘으면 조작이 바뀜:**

| 동작 | 글로벌/대륙 뷰 | 지역/로컬 뷰 |
|------|----------------|-------------|
| 드래그 | 지구본 회전 | 상하좌우 패닝 |
| 스크롤 | 줌인/줌아웃 | 줌인/줌아웃 |
| 더블클릭 | 해당 위치로 줌인 | 해당 이벤트 선택 |
| 우클릭 드래그 | 틸트 (선택) | 없음 |

**전환 인디케이터**:
```
┌────────────────────────────┐
│ 🌍 REGIONAL VIEW           │
│ Drag to pan · Scroll to zoom │
│ [← Back to Globe]          │
└────────────────────────────┘
```

### 로케이션 클러스터링

같은 도시에 이벤트가 많으면 클러스터로 표시:

```
● Paris (47 events)
  ├─ ★★★★★ French Revolution (1789)
  ├─ ★★★★★ Paris Commune (1871)
  ├─ ★★★★  Treaty of Paris (1783)
  └─ +44 more...     [펼치기]
```

클러스터를 클릭하면 펼쳐지거나 더 줌인됨.

---

## Level 4: LOCAL — "이 도시의 세부"

### 유저 경험

```
유저가 Paris로 더 줌인 →

거의 평면에 가까운 뷰 (곡률 미세):
  지도 위에 이벤트들이 위치별로 펼쳐짐

  ┌─ Paris 상세 ──────────────────────┐
  │                                    │
  │  📍 Bastille                       │
  │     "Storming of the Bastille"     │
  │     July 14, 1789                  │
  │     ★★★★★                         │
  │     "파리 시민들이 바스티유 감옥을  │
  │      습격하며 혁명이 시작..."       │
  │                                    │
  │  📍 Place de la Concorde           │
  │     "Execution of Louis XVI"       │
  │     January 21, 1793              │
  │                                    │
  │  📍 Notre-Dame                     │
  │     "Coronation of Napoleon"       │
  │     December 2, 1804              │
  └────────────────────────────────────┘

  각 이벤트를 클릭하면 상세 패널 열림
```

### 이 레벨에서 보이는 것

- 모든 이벤트 (importance 무관)
- 이벤트별 위치가 구분됨 (같은 도시 내 다른 장소)
- 간략한 설명 (Wikipedia 첫 문장)
- 관련 인물 아바타
- 관련 서번트 표시 (있으면)

---

## 줌 전환 애니메이션

줌 레벨 간 전환 시 부드러운 애니메이션:

```
COSMIC → CONTINENTAL:
  카메라가 부드럽게 접근 (1.5초)
  라벨이 페이드인

CONTINENTAL → REGIONAL:
  카메라가 더 접근 (1초)
  회전 → 패닝 모드 전환
  "REGIONAL VIEW" 인디케이터 표시

REGIONAL → LOCAL:
  이미 패닝 모드, 자연스럽게 줌인
  클러스터가 펼쳐짐

어느 단계에서든 줌아웃 → 역순으로 전환
```

---

## 기술 구현 메모

### react-globe.gl 설정

```tsx
<Globe
  // 줌 레벨에 따른 동적 설정
  enableRotate={zoomLevel < REGIONAL_THRESHOLD}

  // 라벨 데이터 (importance >= 라벨 임계값)
  labelsData={visibleLabels}
  labelLat={d => d.lat}
  labelLng={d => d.lng}
  labelText={d => d.title}
  labelSize={d => labelSizeByImportance(d.importance, zoomLevel)}
  labelDotRadius={d => d.importance >= 5 ? 0.4 : 0.2}
  labelColor={d => importanceColor(d.importance)}
  labelAltitude={0.01}

  // 로케이션 앵커 (별도 레이어)
  htmlElementsData={locationAnchors}
  htmlAltitude={0.005}
/>
```

### 줌 레벨 감지

```tsx
// globeStore에 추가
const ZOOM_THRESHOLDS = {
  COSMIC: 0,        // altitude > 2.5
  CONTINENTAL: 2.5,  // altitude 1.0 ~ 2.5
  REGIONAL: 1.0,     // altitude 0.3 ~ 1.0
  LOCAL: 0.3,        // altitude < 0.3
}
```

### 패닝 모드 전환

```tsx
// react-globe.gl은 three.js OrbitControls 사용
// REGIONAL 이상 줌인 시:
const controls = globeRef.current.controls()
controls.enableRotate = false  // 회전 비활성화
controls.enablePan = true      // 패닝 활성화
controls.screenSpacePanning = true
```
