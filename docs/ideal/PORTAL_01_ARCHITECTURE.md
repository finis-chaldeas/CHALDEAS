# PORTAL 01 — 아키텍처: 중첩 모달 + 스토어 + 라우팅

> 상위 문서: `TRISMEGISTOS.md` (컨셉), `TRISMEGISTOS_FRONTEND.md` (구 통합 기획서)

---

## 핵심 결정: 중첩 모달 (Stacked Modals)

### 왜 중첩 모달인가?

기존 설계: view 상태를 전환 (`home` → `collection` → `detail`). 한 번에 하나의 뷰만 보임.

**문제**: 컬렉션 목록에서 아이템 클릭 → 상세 뷰로 전환 → "뒤로" → 스크롤 위치 잃음. 맥락 단절.

**중첩 모달 장점**:
1. **맥락 유지** — 매거진 홈이 뒤에 흐릿하게 보임. "아직 포털 안에 있다" 느낌.
2. **깊이감** — 레이어가 쌓이면서 탐색 깊이를 시각적으로 표현.
3. **빠른 복귀** — 닫기 한 번이면 이전 레이어로. 애니메이션 자연스러움.
4. **FGO 터미널 느낌** — 게임 UI처럼 패널이 겹쳐 열리는 경험.

### 레이어 구조

```
Layer 0: 글로브 (항상 존재, 포털 열면 가려짐)
Layer 1: 매거진 홈 (z-index: 1000) — 풀스크린 오버레이
Layer 2: 컬렉션 페이지 (z-index: 1010) — 홈 위에 올라옴
Layer 3: 아이템 상세 (z-index: 1020) — 컬렉션 위에 올라옴
```

### 시각적 스택

```
┌─────────────────────────────────────────────┐
│  Layer 1: Magazine Home                      │
│  (full opacity, scrollable)                  │
│                                              │
│  사용자가 "그리스·로마" 컬렉션 클릭 ──┐      │
│                                        │      │
│  ┌─────────────────────────────────┐   │      │
│  │  Layer 2: 그리스·로마 컬렉션    │◀──┘      │
│  │  (slide up, home dims to 30%)   │          │
│  │                                 │          │
│  │  "알렉산드로스 대왕" 클릭 ──┐   │          │
│  │                              │   │          │
│  │  ┌──────────────────────┐   │   │          │
│  │  │  Layer 3: 상세 뷰    │◀──┘   │          │
│  │  │  (slide up, L2 dims) │       │          │
│  │  │                      │       │          │
│  │  │  [✕] 닫기 → L2로    │       │          │
│  │  └──────────────────────┘       │          │
│  │                                 │          │
│  │  [✕] 닫기 → L1(홈)으로         │          │
│  └─────────────────────────────────┘          │
│                                              │
│  [✕] 닫기 → 글로브로                         │
└─────────────────────────────────────────────┘
```

### 직접 열기 (Skip Layer)

추천 카드에서 직접 아이템 상세를 여는 경우:

```
Layer 1: Magazine Home → 카드 클릭 → Layer 2: 아이템 상세 (컬렉션 skip)
```

이 경우 Layer 2에 상세가 바로 올라옴. 컬렉션 레이어는 건너뜀.
뒤로가기 → 매거진 홈으로.

---

## 모달 스택 구현

### PortalStack 컴포넌트

```typescript
// 중첩 모달의 핵심: 스택 배열
interface PortalLayer {
  type: 'home' | 'collection' | 'detail'
  slug?: string        // collection slug or item slug
  scrollY?: number     // 복귀 시 스크롤 위치 복원용
}

// 스택 예시:
// [{ type: 'home' }]                                    → 홈만
// [{ type: 'home' }, { type: 'collection', slug: 'greece-rome' }]  → 홈 + 컬렉션
// [{ type: 'home' }, { type: 'collection', slug: 'greece-rome' }, { type: 'detail', slug: 'alexander' }]  → 3층
// [{ type: 'home' }, { type: 'detail', slug: 'singularity-f' }]  → 홈 + 직접 상세
```

### 렌더링 규칙

```typescript
function PortalStack({ layers }: { layers: PortalLayer[] }) {
  return (
    <>
      {layers.map((layer, index) => {
        const isTop = index === layers.length - 1
        const isBehind = !isTop

        return (
          <div
            key={`${layer.type}-${layer.slug || 'home'}`}
            className={classNames('portal-layer', {
              'portal-layer--dimmed': isBehind,
              'portal-layer--top': isTop,
            })}
            style={{ zIndex: 1000 + index * 10 }}
          >
            {layer.type === 'home' && <MagazineHome />}
            {layer.type === 'collection' && <CollectionPage slug={layer.slug!} />}
            {layer.type === 'detail' && <PortalItemDetail slug={layer.slug!} />}
          </div>
        )
      })}
    </>
  )
}
```

### CSS: 레이어 전환

```css
/* 베이스 레이어 */
.portal-layer {
  position: fixed;
  inset: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: opacity 0.3s ease, filter 0.3s ease;
}

/* 뒤에 깔린 레이어 */
.portal-layer--dimmed {
  opacity: 0.3;
  filter: blur(4px);
  pointer-events: none;   /* 클릭 차단 */
}

/* 최상위 레이어 */
.portal-layer--top {
  opacity: 1;
  filter: none;
  pointer-events: auto;
}

/* 새 레이어 등장 애니메이션 */
.portal-layer--entering {
  animation: portalSlideUp 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes portalSlideUp {
  from {
    opacity: 0;
    transform: translateY(40px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* 레이어 퇴장 */
.portal-layer--exiting {
  animation: portalSlideDown 0.25s ease-in forwards;
}

@keyframes portalSlideDown {
  to {
    opacity: 0;
    transform: translateY(30px) scale(0.98);
  }
}
```

---

## portalStore (Zustand)

```typescript
import { create } from 'zustand'

interface PortalLayer {
  type: 'home' | 'collection' | 'detail'
  slug?: string
  scrollY?: number
}

interface PortalStore {
  // 포털 열림/닫힘
  isOpen: boolean

  // 레이어 스택
  layers: PortalLayer[]

  // Actions
  open: () => void
  close: () => void

  // 네비게이션
  pushCollection: (slug: string) => void
  pushDetail: (slug: string) => void
  pop: () => void           // 최상위 레이어 제거 (뒤로가기)
  popToHome: () => void     // 홈까지 전부 pop

  // 유틸
  currentLayer: () => PortalLayer | null
  canGoBack: () => boolean
}

export const usePortalStore = create<PortalStore>((set, get) => ({
  isOpen: false,
  layers: [],

  open: () => set({
    isOpen: true,
    layers: [{ type: 'home' }],
  }),

  close: () => set({
    isOpen: false,
    layers: [],
  }),

  pushCollection: (slug) => {
    const { layers } = get()
    // 현재 레이어의 스크롤 위치 저장
    const currentScrollY = document.querySelector('.portal-layer--top .portal-scroll')?.scrollTop ?? 0
    const updated = layers.map((l, i) =>
      i === layers.length - 1 ? { ...l, scrollY: currentScrollY } : l
    )
    set({ layers: [...updated, { type: 'collection', slug }] })
  },

  pushDetail: (slug) => {
    const { layers } = get()
    const currentScrollY = document.querySelector('.portal-layer--top .portal-scroll')?.scrollTop ?? 0
    const updated = layers.map((l, i) =>
      i === layers.length - 1 ? { ...l, scrollY: currentScrollY } : l
    )
    set({ layers: [...updated, { type: 'detail', slug }] })
  },

  pop: () => {
    const { layers } = get()
    if (layers.length <= 1) {
      // 홈에서 pop = 닫기
      set({ isOpen: false, layers: [] })
    } else {
      set({ layers: layers.slice(0, -1) })
    }
  },

  popToHome: () => set({
    layers: [{ type: 'home' }],
  }),

  currentLayer: () => {
    const { layers } = get()
    return layers.length > 0 ? layers[layers.length - 1] : null
  },

  canGoBack: () => get().layers.length > 1,
}))
```

---

## 키보드 내비게이션

```typescript
// TrismegistosPortal.tsx 내부
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault()
      const { layers, pop, close } = usePortalStore.getState()

      if (layers.length > 1) {
        pop()        // 상위 레이어 닫기
      } else {
        close()      // 포털 전체 닫기
      }
    }
  }
  window.addEventListener('keydown', handleKeyDown)
  return () => window.removeEventListener('keydown', handleKeyDown)
}, [])
```

**Escape 흐름**:
```
Layer 3 (상세) → Esc → Layer 2 (컬렉션) → Esc → Layer 1 (홈) → Esc → 글로브
```

---

## Z-Index 전체 맵 (기존 + 포털)

```
9999 ── StoryModal (최우선)
5000 ── TimelineModal
2000 ── SearchOverlay
1020 ── Portal Layer 3 (아이템 상세)
1010 ── Portal Layer 2 (컬렉션)
1000 ── Portal Layer 1 (매거진 홈) / ShiftBrowser / TourOverlay
 997 ── ServantPanel
 700 ── Navigator/SearchAutocomplete
 200 ── SourceBrowser
  70 ── ShiftPanel (top banner)
  60 ── ShiftPanel (bottom nav)
  50 ── FloatingButtons
  40 ── NarrativePanel (right sidebar)
  30 ── EraFeed
  20 ── PeriodDrawer
```

---

## 글로브 연결 패턴

포털 안에서 글로브로 나가는 모든 액션:

```typescript
interface PortalGlobeActions {
  // App.tsx에서 props로 전달
  onFlyToLocation: (lat: number, lng: number) => void
  onSetCurrentYear: (year: number) => void
  onEventClick: (eventId: number) => void
  onPersonClick: (personId: number) => void
  onOpenShift: (shiftId: number) => void
}

// 사용 패턴: "글로브에서 보기" 클릭 시
function handleViewOnGlobe(lat: number, lng: number, year: number) {
  portalStore.close()             // 포털 전체 닫기
  props.onFlyToLocation(lat, lng)
  props.onSetCurrentYear(year)
}

// 사용 패턴: "시프트로 체험" 클릭 시
function handleStartShift(shiftId: number) {
  portalStore.close()             // 포털 전체 닫기
  props.onOpenShift(shiftId)      // ShiftPanel이 글로브 위에 열림
}
```

**규칙**: 글로브 관련 액션은 항상 포털을 **전체 닫기**. 부분 닫기(pop) 아님.
이유: 글로브가 보여야 하는 액션이므로 모든 레이어를 없애야 함.

---

## App.tsx 변경

### Before (현재)
```typescript
// App.tsx
const [showTrismegistos, setShowTrismegistos] = useState(false)
const [trismegistosContent, setTrismegistosContent] = useState<TrismegistosContent | null>(null)

<TrismegistosModal
  isOpen={showTrismegistos}
  content={trismegistosContent}
  onClose={() => { setShowTrismegistos(false); setTrismegistosContent(null) }}
  ...
/>
```

### After (신규)
```typescript
// App.tsx
// showTrismegistos, trismegistosContent useState 삭제
// portalStore.isOpen 사용

import { usePortalStore } from './store/portalStore'

const isPortalOpen = usePortalStore((s) => s.isOpen)
const portalLayers = usePortalStore((s) => s.layers)

// FloatingButtons에서:
<FloatingButtons
  onTrismegistosClick={() => usePortalStore.getState().open()}
/>

// 렌더링:
{isPortalOpen && (
  <TrismegistosPortal
    layers={portalLayers}
    onEventClick={handleEventClick}
    onPersonClick={handlePersonClick}
    onFlyToLocation={flyToLocation}
    onSetCurrentYear={setCurrentYear}
    onOpenShift={handleOpenShift}
  />
)}
```

---

## 파일 구조

```
frontend/src/
├── components/
│   └── trismegistos/           ← 기존 폴더 재사용
│       ├── TrismegistosPortal.tsx   ← 신규: 메인 컨테이너 + PortalStack
│       ├── MagazineHome.tsx         ← 신규: 매거진 홈
│       ├── TodayHero.tsx            ← 신규: 오늘의 역사
│       ├── RecommendationRow.tsx    ← 신규: 추천 카드 로우
│       ├── FgoSection.tsx           ← 신규: FGO 진입점
│       ├── ReadingSection.tsx       ← 신규: 읽을거리
│       ├── CollectionGrid.tsx       ← 신규: 컬렉션 카드 그리드
│       ├── CollectionPage.tsx       ← 신규: 컬렉션 상세 (Layer 2)
│       ├── PortalItemDetail.tsx     ← 신규: 아이템 상세 (Layer 2/3)
│       ├── portal.css               ← 신규: 포털 전체 스타일
│       │
│       ├── TrismegistosModal.tsx    ← 삭제 예정 (구현 완료 후)
│       ├── TrismegistosMenu.tsx     ← 삭제 예정
│       └── trismegistos.css         ← portal.css로 흡수 후 삭제
│
├── store/
│   └── portalStore.ts               ← 신규
│
├── api/
│   └── client.ts                    ← portalApi 추가
│
└── types/
    └── index.ts                     ← Portal 타입 추가
```

---

## 구현 우선순위

이 문서의 범위에서 먼저 구현할 것:

1. `portalStore.ts` — 스택 기반 스토어
2. `TrismegistosPortal.tsx` — PortalStack 렌더러
3. `portal.css` — 레이어 전환 애니메이션
4. `App.tsx` 수정 — useState → portalStore 교체

나머지 섹션 컴포넌트는 `PORTAL_02`, `PORTAL_03` 문서 참조.

---

## 데이터 흐름 전체도

```
┌─ portalStore (Zustand) ──────────────────────────────────┐
│  isOpen: boolean                                          │
│  layers: PortalLayer[]                                    │
│                                                           │
│  open() → [{ type: 'home' }]                              │
│  pushCollection('greece') → [..., { type: 'collection' }] │
│  pushDetail('alexander') → [..., { type: 'detail' }]      │
│  pop() → layers.slice(0, -1)                              │
│  close() → { isOpen: false, layers: [] }                  │
└──────────────────────┬────────────────────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
  MagazineHome    CollectionPage   PortalItemDetail
       │               │               │
  React Query      React Query     React Query
       │               │               │
       ▼               ▼               ▼
  portalApi.       portalApi.      portalApi.
  getFeatured()    getCollection() getItem()
       │               │               │
       ▼               ▼               ▼
  /api/v1/portal/  /api/v1/portal/ /api/v1/portal/
  featured         collections/   items/{slug}
                   {slug}
```

---

## 관련 문서

| 문서 | 내용 |
|------|------|
| `PORTAL_02_MAGAZINE_HOME.md` | 매거진 홈 5개 섹션 상세 |
| `PORTAL_03_COLLECTIONS.md` | 컬렉션 + 아이템 상세 |
| `PORTAL_04_RECOMMENDATIONS.md` | 추천 엔진 + "이런 것도 좋아하실 걸요" |
| `TRISMEGISTOS.md` | 상위 컨셉 문서 |
