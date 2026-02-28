# PORTAL 06 — SHEBA / Trismegistus 양방향 모드 전환

> 상위: `TRISMEGISTOS.md` | 아키텍처: `PORTAL_01_ARCHITECTURE.md`

---

## 한 문장

**"글로브와 포털은 같은 역사의 두 가지 렌즈다. 하나에서 다른 하나로, 맥락을 잃지 않고 넘어간다."**

---

## 현재 상태 (As-Is)

```
SHEBA (Globe)                    Trismegistus (Portal)
┌─────────────────────┐          ┌─────────────────────┐
│                     │          │                     │
│   3D Globe          │   ✦ →   │   Magazine Home     │
│   Timeline          │          │   Collection        │
│   ShiftPanel        │  ← CTA  │   Detail            │
│   NarrativePanel    │          │   PreviewPanel      │
│                     │          │                     │
└─────────────────────┘          └─────────────────────┘
```

### 문제점

| # | 문제 | 상세 |
|---|------|------|
| 1 | **일방통행** | 포털→글로브는 CTA로 가능하지만, 글로브→포털 아이템 연결이 ✦ 버튼밖에 없음 |
| 2 | **맥락 단절** | 포털에서 "Globe View" → 포털 완전 닫힘. 돌아오면 처음부터 |
| 3 | **풀스크린 덮어쓰기** | 포털이 글로브를 100% 가림. 양쪽을 동시에 볼 수 없음 |
| 4 | **글로브 맥락 무시** | 포털을 열면 글로브의 현재 위치/시간과 무관한 콘텐츠가 나옴 |
| 5 | **진입점 부족** | NarrativePanel, ShiftPanel에서 관련 포털 아이템으로 가는 경로 없음 |

---

## 비전 (To-Be): 3단계 진화

### Phase A — 컨텍스트 보존 (맥락을 잃지 않기)

현재 구조 유지하되, **왔다 갔다 할 때 맥락이 보존**되도록.

#### A-1. 포털 상태 보존 (Portal → Globe → Portal)

```
현재: 포털에서 "Globe View" 클릭 → close() → 글로브 이동
      ✦ 다시 클릭 → open() → 매거진 홈 (처음부터)

개선: 포털에서 "Globe View" 클릭 → suspend() → 글로브 이동
      ✦ 다시 클릭 → resume() → 마지막 보던 페이지/레이어 복귀
```

**구현**:
```typescript
// portalStore 추가
interface PortalStore {
  // 기존
  isOpen: boolean
  layers: PortalLayer[]

  // 신규: 일시정지
  isSuspended: boolean
  suspendedLayers: PortalLayer[]   // 닫기 전 레이어 백업
  suspendedPage: PageKey           // 닫기 전 활성 페이지 탭

  suspend: () => void   // 글로브로 나갈 때 (상태 보존)
  resume: () => void    // 다시 돌아올 때 (상태 복원)
  close: () => void     // 완전 닫기 (상태 폐기)
}
```

**UX 변화**:
- "Globe View" CTA → `suspend()` + flyTo (기존: `close()` + flyTo)
- ✦ 버튼 클릭 → `isSuspended ? resume() : open()`
- ✦ 버튼 길게 누르기 or 우클릭 → 메뉴: "이전 위치로 돌아가기" / "새로 열기"
- ✦ 버튼에 suspend 상태 표시 (도트 인디케이터)

#### A-2. 글로브 컨텍스트 전달 (Globe → Portal)

포털을 열 때 현재 글로브 위치/시간을 포털에 전달.

```typescript
// open 시 글로브 컨텍스트 전달
open: (context?: GlobeContext) => void

interface GlobeContext {
  lat: number
  lng: number
  year: number
  activeShiftId?: number
  activeEventId?: number
}
```

**활용**:
- Front Page 히어로: 글로브 위치/시간 근처의 콘텐츠 우선 표시
- Recommendations: "지금 보고 계신 시대와 관련된..." 카드 추가
- Reading 섹션: 현재 시대/지역 관련 아티클 상단 배치

```
예) 글로브가 -480년 그리스 → 포털 열기
    → 히어로: "그리스-페르시아 전쟁"
    → 추천: 테르모필레, 살라미스, 레오니다스
    → Reading: 스파르타 사회, 페르시아 제국 상단
```

---

### Phase B — 양방향 링크 (글로브 ↔ 포털 상호 참조)

#### B-1. 글로브 → 포털 진입점 추가

| 위치 | 트리거 | 동작 |
|------|--------|------|
| NarrativePanel (이벤트 카드) | "관련 아티클" 링크 | openPreview(slug) or pushDetail(slug) |
| NarrativePanel (인물 카드) | "서번트 컬럼" 링크 | 해당 servant_column 포털 아이템 열기 |
| ShiftPanel 페이지 | "더 읽기" 버튼 | 관련 portal_item 프리뷰 |
| 타임라인 시대 클릭 | "시대 아티클" 아이콘 | 해당 시대 portal_item 열기 |

**데이터 연결** (이미 존재하는 FK 활용):
```
portal_items.related_event_ids  → events  → NarrativePanel에서 역참조
portal_items.related_servants   → fgo_servants → persons → NarrativePanel에서 역참조
collection_entries.shift_id     → historical_chains → ShiftPanel에서 역참조
collection_entries.event_id     → events → NarrativePanel에서 역참조
```

**백엔드 필요**:
```
GET /api/v1/portal/items/by-event/{event_id}
  → 이 이벤트와 연결된 portal_items 목록

GET /api/v1/portal/items/by-person/{person_id}
  → 이 인물과 연결된 portal_items (servant_column 등)

GET /api/v1/portal/items/by-shift/{shift_id}
  → 이 시프트와 연결된 portal_items
```

#### B-2. 포털 → 글로브 풍부화

현재: "Globe View" = 단순 flyTo + setYear
개선: 포털 아이템에 따라 글로브에 추가 정보 표시

```
포털에서 "Globe View (1431 CE)" 클릭
→ 글로브로 전환
→ 해당 위치/시간으로 이동
→ 관련 이벤트 마커 하이라이트
→ NarrativePanel 자동 열림 (관련 이벤트 카드)
→ 관련 시프트가 있으면 "이 시프트 시작하기" 배너 표시
```

---

### Phase C — 통합 내비게이션 (FGO 터미널 스타일)

#### 컨셉: 상단 모드 바

FGO의 터미널처럼, 앱 상단에 항상 보이는 모드 바.

```
┌──────────────────────────────────────────────────────────┐
│  CHALDEAS   [SHEBA]  [TRISMEGISTOS]  [SHIFT ▶]     🔍  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  (현재 모드의 콘텐츠)                                     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

| 탭 | 모드 | 내용 |
|----|------|------|
| **SHEBA** | Globe | 3D 글로브 + 타임라인 + NarrativePanel |
| **TRISMEGISTOS** | Portal | 매거진 홈 (신문 페이지 탭 포함) |
| **SHIFT** | Active Shift | 현재 진행 중인 시프트 (없으면 비활성) |

#### 모드 전환 애니메이션

```css
/* SHEBA → TRISMEGISTOS */
@keyframes modeSwitch {
  0%   { opacity: 1; }
  50%  { opacity: 0; }
  100% { opacity: 1; }
}
/* 또는 슬라이드: 글로브가 왼쪽으로 밀리고 포털이 오른쪽에서 등장 */
```

#### 전환 시 컨텍스트 전달

```
SHEBA → TRISMEGISTOS:
  현재 위치/시간 → 포털 추천에 반영
  현재 보고 있는 이벤트/인물 → 관련 포털 아이템 하이라이트

TRISMEGISTOS → SHEBA:
  마지막 본 아이템의 위치/시간 → 글로브 이동
  또는 아무 변화 없이 전환 (유저 선택)

SHIFT 탭:
  시프트 진행 중일 때만 활성화
  클릭 → 시프트 재개 (중간에 포털 갔다 와도 유지)
```

#### ✦ 버튼 → 모드 바로 대체

Phase C에서는 ✦ 플로팅 버튼이 사라지고, 상단 모드 바가 그 역할을 대체.

```
Before: ✦ 클릭 → 풀스크린 포털 오버레이
After:  TRISMEGISTOS 탭 클릭 → 모드 전환 (오버레이 아님)
```

---

## 레이아웃 옵션 비교

### Option 1: 풀스크린 전환 (현재 + Phase A/B)

```
[SHEBA 모드]           [TRISMEGISTOS 모드]
┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │
│   Globe 100%    │ ↔  │   Portal 100%   │
│                 │    │                 │
└─────────────────┘    └─────────────────┘
```

- 장점: 단순, 각 모드에 집중
- 단점: 양쪽 동시 불가

### Option 2: 사이드 패널 포털 (Phase C 대안)

```
┌──────────────────────────────────────────┐
│  SHEBA + TRISMEGISTOS (동시)              │
│                                          │
│  ┌────────────────┐ ┌─────────────────┐  │
│  │                │ │                 │  │
│  │   Globe 60%    │ │   Portal 40%    │  │
│  │                │ │   (사이드)       │  │
│  │                │ │                 │  │
│  └────────────────┘ └─────────────────┘  │
└──────────────────────────────────────────┘
```

- 장점: 글로브를 보면서 포털 탐색 가능
- 단점: 좁은 화면에서 사용 불가, 복잡도 증가

### Option 3: PIP (Picture-in-Picture) (Phase C 대안)

```
┌──────────────────────────────────────────┐
│                                          │
│   Portal (주 화면)                        │
│                                          │
│                    ┌──────────┐          │
│                    │ Globe    │          │
│                    │ (미니)   │          │
│                    └──────────┘          │
│                                          │
└──────────────────────────────────────────┘
```

- 장점: 포털 읽으면서 글로브 위치 확인 가능
- 단점: 미니 글로브의 상호작용 제한

**추천**: Phase A/B는 Option 1 (풀스크린). Phase C에서 Option 2 (데스크탑) + Option 1 (모바일).

---

## 데이터 흐름 전체도

```
┌─ App Level State ──────────────────────────────────────┐
│                                                         │
│  globeStore         portalStore        timelineStore     │
│  ├ cameraPosition   ├ isOpen           ├ currentYear     │
│  ├ activeShift      ├ isSuspended      ├ ...             │
│  ├ flyTarget        ├ layers[]         │                 │
│  └ ...              ├ activePage       │                 │
│                     ├ previewSlug      │                 │
│                     └ globeContext?     │                 │
│                                                         │
│          ┌──────────────────────┐                        │
│          │    Mode Controller   │  ← Phase C 신규        │
│          │  activeMode: 'sheba' │                        │
│          │    | 'trismegistos'  │                        │
│          │    | 'shift'         │                        │
│          └──────────────────────┘                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
               │                    │
    ┌──────────┴──────────┐  ┌──────┴──────────┐
    │ SHEBA (Globe)       │  │ TRISMEGISTOS    │
    │                     │  │ (Portal)        │
    │ GlobeContainer      │  │ MagazineHome    │
    │ NarrativePanel      │  │ CollectionPage  │
    │ ShiftPanel          │  │ ItemDetail      │
    │ Timeline            │  │ PreviewPanel    │
    │                     │  │                 │
    │ "이 아티클 읽기" →  │  │ ← "Globe View"  │
    │ "서번트 컬럼" →     │  │ ← "Start Shift" │
    └─────────────────────┘  └─────────────────┘
```

---

## 구현 우선순위

| Phase | 내용 | 난이도 | 가치 |
|-------|------|--------|------|
| **A-1** | 포털 상태 보존 (suspend/resume) | 낮음 | 높음 |
| **A-2** | 글로브 컨텍스트 → 포털 추천 | 중간 | 높음 |
| **B-1** | NarrativePanel → 포털 아이템 링크 | 중간 | 중간 |
| **B-2** | 포털 → 글로브 풍부화 (하이라이트, 자동 패널) | 중간 | 중간 |
| **C** | 상단 모드 바 + 사이드 패널 | 높음 | 높음 |

**추천 시작점**: A-1 (suspend/resume) — 코드 변경 최소, 체감 효과 최대.

---

## 미해결 질문

1. **모바일에서 모드 바**: 상단 바가 화면을 먹으면? → 햄버거 메뉴 or 하단 탭?
2. **시프트 중 포털**: 시프트 재생 중에 포털을 열면? → 시프트 일시정지? 같이 보이기?
3. **포털 추천의 글로브 컨텍스트 의존도**: 너무 많이 의존하면 "항상 같은 추천" 문제 → 혼합 비율?
4. **사이드 패널 포털**: NarrativePanel(우측)과 공간 충돌 → NarrativePanel이 포털 안으로 통합?

---

## 관련 문서

| 문서 | 내용 |
|------|------|
| `PORTAL_01_ARCHITECTURE.md` | 현재 모달 스택 + 글로브 연결 패턴 |
| `PORTAL_02_MAGAZINE_HOME.md` | 매거진 홈 5개 섹션 |
| `EXPERIENCE.md` | 탐험의 두 가지 길 (Explorer vs Reader) |
| `TRISMEGISTOS.md` | 포털 전체 컨셉 |
