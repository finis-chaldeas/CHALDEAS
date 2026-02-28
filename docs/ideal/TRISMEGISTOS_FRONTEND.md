# TRISMEGISTOS 프론트엔드 구현 기획서

## 한 줄 요약

4탭 모달 카탈로그 → **단일 스크롤 매거진 홈 + 컬렉션 포털** 전면 재작성.

---

## 현재 구조 (AS-IS)

```
TrismegistosModal.tsx
├── view: 'menu' | 'content' | 'servants'
├── 4탭 메뉴: Era | FGO | Reading | Explore
│   ├── Era     → EraTab (navigator 재사용)
│   ├── FGO     → TrismegistosMenu (2레벨 탭: FGO/PanHuman × 3서브탭)
│   ├── Reading → HistoryTab (navigator 재사용)
│   └── Explore → PersonTab (navigator 재사용)
└── 콘텐츠 상세 뷰 (TrismegistosContent 객체 렌더링)
```

**문제점**: 3단계 탭(모달탭→FGO/PanHuman→singularity/lostbelt/...), 정적 목록, 글로브 단절, Navigator와 중복.

---

## 목표 구조 (TO-BE)

```
TrismegistosPortal.tsx (전면 재작성)
├── view: 'home' | 'collection' | 'detail'
│
├── HOME (매거진 홈 — 단일 스크롤)
│   ├── TodayHero        — 오늘의 역사 히어로 배너
│   ├── RecommendationRow — 이번 주 추천 카드 4~6개
│   ├── FgoSection        — FGO 진입점 (특이점 + 이문대 + 서번트)
│   ├── ReadingSection    — 읽을거리 (역사/문학/음악/에세이)
│   └── CollectionGrid    — 컬렉션 둘러보기
│
├── COLLECTION (컬렉션 상세)
│   └── CollectionPage    — 시프트/아티클/인물/이벤트 통합 뷰
│
└── DETAIL (개별 콘텐츠)
    └── PortalItemDetail  — 아티클/쇼케이스 상세 (기존 콘텐츠 뷰 개선)
```

---

## 파일 구조

### 삭제
| 파일 | 이유 |
|------|------|
| `TrismegistosModal.tsx` | 전면 교체 → `TrismegistosPortal.tsx` |
| `TrismegistosMenu.tsx` | FGO/PanHuman 이중탭 해체 → 섹션 컴포넌트로 |
| `data/trismegistosData.ts` | 하드코딩 샘플 데이터. DB API로 전환 완료 |

### 신규
| 파일 | 역할 |
|------|------|
| `trismegistos/TrismegistosPortal.tsx` | 메인 컨테이너 (view 라우팅) |
| `trismegistos/MagazineHome.tsx` | 매거진 홈 (단일 스크롤, 5개 섹션) |
| `trismegistos/TodayHero.tsx` | 오늘의 역사 히어로 배너 |
| `trismegistos/RecommendationRow.tsx` | 추천 카드 로우 |
| `trismegistos/FgoSection.tsx` | FGO 진입점 (특이점/이문대/서번트) |
| `trismegistos/ReadingSection.tsx` | 읽을거리 필터 리스트 |
| `trismegistos/CollectionGrid.tsx` | 컬렉션 카드 그리드 |
| `trismegistos/CollectionPage.tsx` | 컬렉션 상세 (Layer 2) |
| `trismegistos/PortalItemDetail.tsx` | 아티클 상세 뷰 |
| `trismegistos/portal.css` | 스타일 전체 |
| `store/portalStore.ts` | 포털 전용 Zustand 스토어 |

### 수정
| 파일 | 변경 |
|------|------|
| `App.tsx` | `TrismegistosModal` → `TrismegistosPortal`로 교체, props 정리 |
| `api/client.ts` | `portalApi` 추가 (기존 `trismegistosApi` 유지 — 하위호환) |
| `types/index.ts` | Portal 관련 타입 추가 |

---

## 컴포넌트 상세

### 1. TrismegistosPortal.tsx — 메인 컨테이너

```
역할: view 상태에 따라 Home / Collection / Detail 전환
진입: FloatingButtons 클릭 또는 Landing 버튼
```

**State (Zustand: portalStore)**
```typescript
interface PortalStore {
  // 뷰 라우팅
  view: 'home' | 'collection' | 'detail'

  // 컬렉션 뷰
  activeCollectionSlug: string | null

  // 디테일 뷰
  activeItemSlug: string | null

  // 네비게이션 히스토리 (뒤로가기 지원)
  history: Array<{ view: string; slug?: string }>

  // Actions
  goHome: () => void
  openCollection: (slug: string) => void
  openItem: (slug: string) => void
  goBack: () => void
}
```

**Props (from App.tsx)**
```typescript
interface Props {
  isOpen: boolean
  onClose: () => void
  onEventClick: (eventId: number) => void
  onPersonClick: (personId: number) => void
  onFlyToLocation: (lat: number, lng: number) => void
  onSetCurrentYear: (year: number) => void
  onOpenShift: (shiftId: number) => void
}
```

**렌더링 로직**
```
if view === 'home'       → <MagazineHome />
if view === 'collection' → <CollectionPage slug={activeCollectionSlug} />
if view === 'detail'     → <PortalItemDetail slug={activeItemSlug} />
```

**Escape 키**: detail → collection (있으면) → home → close modal.

---

### 2. MagazineHome.tsx — 매거진 홈

```
역할: 단일 스크롤 페이지. 5개 섹션을 세로로 배치.
탭 없음. 스크롤만.
```

**레이아웃**
```
┌─ TRISMEGISTOS ──────────────────────────────────────┐
│  [✕]                                                 │
│                                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │  ▶ TodayHero                                 │    │
│  │  오늘의 역사 — 히어로 배너                    │    │
│  │  [글로브에서 보기]  [시프트로 체험]             │    │
│  └──────────────────────────────────────────────┘    │
│                                                      │
│  ━━ 추천 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐                        │
│  │카드│ │카드│ │카드│ │카드│  RecommendationRow      │
│  └────┘ └────┘ └────┘ └────┘                        │
│                                                      │
│  ━━ FGO에서 시작하기 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  특이점: [F] [I] [II] ...                            │
│  이문대: [1] [2] ...           FgoSection            │
│  서번트: [길가] [레오] ...                            │
│                                                      │
│  ━━ 읽을거리 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  [전체|역사|문학|음악]          ReadingSection        │
│  ┌─ The Crusades ─────┐                              │
│  └────────────────────┘                              │
│                                                      │
│  ━━ 컬렉션 둘러보기 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  ┌──────┐ ┌──────┐ ┌──────┐   CollectionGrid        │
│  │FGO   │ │그리스│ │예술  │                          │
│  │메인  │ │로마  │ │문화  │                          │
│  └──────┘ └──────┘ └──────┘                          │
│                                                      │
│  ─── CHALDEAS ARCHIVE ───                            │
└──────────────────────────────────────────────────────┘
```

---

### 3. TodayHero.tsx — 오늘의 역사

```
역할: 최상단 히어로 배너. 오늘 날짜(월/일) 매칭 이벤트.
데이터: GET /api/v1/portal/featured → today 항목
폴백: featured portal_items 중 랜덤
```

**데이터 소스 우선순위**
1. 오늘 날짜 매칭 이벤트 (events 테이블 month/day + importance)
2. 이달의 테마 (수동 큐레이션, 미래)
3. featured portal_items 중 랜덤

**CTA 버튼**
- `[🌍 글로브에서 보기]` → `onClose()` + `onFlyToLocation()` + `onSetCurrentYear()`
- `[▶ 시프트로 체험]` → `onOpenShift(shiftId)` (관련 시프트가 있을 때만)

**백엔드 필요** (신규)
```
GET /api/v1/portal/today
→ { event: { id, title, title_ko, year, lat, lng, description_ko },
    shift_id?: number,
    theme?: string }
```

**구현 참고**: 날짜 매칭은 events 테이블의 date_start에서 월/일 추출.
BCE 이벤트는 정확한 날짜 없는 경우가 많으므로 importance 상위 이벤트 중 랜덤 폴백.

---

### 4. RecommendationRow.tsx — 추천 카드

```
역할: 혼합 콘텐츠 카드 4~6개. 가로 스크롤.
데이터: featured portal_items + featured shifts 조합
```

**카드 타입별 렌더링**

| 타입 | 아이콘 | 소스 | 클릭 시 |
|------|--------|------|---------|
| portal_item (singularity) | ⚔ | `/portal/items?is_featured=true` | `openItem(slug)` |
| portal_item (article) | 📖 | `/portal/items?is_featured=true` | `openItem(slug)` |
| shift | ▶ | `/shifts?featured=true` | `onOpenShift(id)` → 모달 닫기 |
| collection | 🏛 | `/portal/collections?is_featured=true` | `openCollection(slug)` |

**카드 컴포넌트** (공용)
```typescript
interface RecommendationCard {
  type: 'portal_item' | 'shift' | 'collection'
  title: string
  title_ko?: string
  subtitle?: string      // "시프트 · 7 pages" 또는 "아티클 · 5분"
  thumbnail_url?: string
  slug_or_id: string | number
}
```

**레이아웃**: 가로 flex, overflow-x: auto, snap-type: x mandatory.
모바일에서 스와이프 가능.

---

### 5. FgoSection.tsx — FGO 진입점

```
역할: FGO 메인 스토리를 역사로 연결하는 진입점.
데이터: /api/v1/portal/items?item_type=singularity,lostbelt,servant_column
```

**레이아웃**
```
┌─────────────────────────────────────────────────┐
│  FGO를 아시나요? 게임 속 특이점은 실제 역사를    │
│  배경으로 합니다. 각 특이점의 진짜 역사를         │
│  지구본 위에서 체험해보세요.                      │
│                                                  │
│  ━━ 특이점 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  [F.Fuyuki] [I.Orleans] [II.Septem] → → →       │
│                                                  │
│  ━━ 이문대 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  [1.Anastasia] [2.Götterdämmerung] → → →        │
│                                                  │
│  ━━ 서번트 열전 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  [Gilgamesh] [Leonidas] [Joan of Arc] → → →     │
│                                                  │
│  [📚 FGO 메인 스토리 컬렉션 전체보기 →]          │
└─────────────────────────────────────────────────┘
```

**특이점/이문대 카드**: 챕터 번호 + 이름 + 연도/장소 + 대표 서번트 1~2명.
**서번트 카드**: 이름 + 클래스 + 레어도(★).
**하단 링크**: "FGO 메인 스토리" 컬렉션으로 이동 → `openCollection('fgo-main-story')`.

**탭 없음**. 카테고리 헤더로 구분. 기존 TrismegistosMenu의 FGO/PanHuman 이중탭 제거.

---

### 6. ReadingSection.tsx — 읽을거리

```
역할: 역사/문학/음악 아티클 + 에세이 통합 리스트.
데이터: /api/v1/portal/items?item_type=history,literature,music
```

**필터 칩**: `[전체]` `[역사]` `[문학]` `[음악]` (useState로 필터)
**정렬**: 추천순(sort_order) | 연도순(year)
**아이템 렌더링**: 제목 + 연도/장소 + 타입 라벨. 클릭 → `openItem(slug)`.

---

### 7. CollectionGrid.tsx — 컬렉션 둘러보기

```
역할: 모든 컬렉션을 카드 그리드로 표시.
데이터: GET /api/v1/portal/collections
```

**카드 디자인**
```
┌──────────┐
│ 🏛 아이콘│
│ 제목     │
│ 설명 1줄 │
│          │
│ N 시프트 │
│ M 아티클 │
└──────────┘
```

**CSS**: `display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr))`.
클릭 → `openCollection(slug)`.

---

### 8. CollectionPage.tsx — 컬렉션 상세 (Layer 2)

```
역할: 하나의 컬렉션 내 모든 콘텐츠를 타입별로 보여줌.
데이터: GET /api/v1/portal/collections/{slug}
```

**레이아웃**
```
┌─ [← 홈] 그리스·로마 ────────────────────── [✕] ─┐
│                                                    │
│  🏛 그리스·로마 컬렉션                              │
│  "지중해를 지배한 두 문명의 이야기"                   │
│                                                    │
│  ━━ 시프트 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  ┌─ 그리스-페르시아 전쟁 ──────────────────┐       │
│  │ -490 ~ -449 · 7 pages                  │       │
│  └────────────────────────────────────────┘       │
│  ┌─ 알렉산드로스 대왕 ────────────────────┐       │
│  │ -356 ~ -323 · 12 pages                │       │
│  └────────────────────────────────────────┘       │
│                                                    │
│  ━━ 아티클 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  ┌─ Alexander the Great ──────────────────┐       │
│  └────────────────────────────────────────┘       │
│                                                    │
│  ━━ 주요 인물 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  [Leonidas] [Themistocles] [Alexander]            │
│                                                    │
│  ━━ 주요 이벤트 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  [마라톤(-490)] [살라미스(-480)]                    │
└────────────────────────────────────────────────────┘
```

**entry_type별 렌더링**

| entry_type | 렌더링 | 클릭 시 |
|------------|--------|---------|
| `shift` | 시프트 카드 (title, year_range, pages) | `onOpenShift(id)` → 모달 닫기 |
| `portal_item` | 아티클 카드 (title, year, type) | `openItem(slug)` |
| `person` | 인물 칩 (name, years) | `onPersonClick(id)` → 모달 닫기 |
| `event` | 이벤트 칩 (title, year) | `onEventClick(id)` → 모달 닫기 |
| `period` | 시대 카드 (title, range) | (미래 확장) |

**섹션 순서**: 시프트 → 아티클 → 인물 → 이벤트 (각 타입별로 그룹핑).

---

### 9. PortalItemDetail.tsx — 아이템 상세

```
역할: 기존 TrismegistosModal의 content 뷰 개선.
데이터: GET /api/v1/portal/items/{slug}
```

기존 콘텐츠 상세 뷰와 거의 동일하지만:
- 타입 색상 (singularity=orange, lostbelt=magenta, servant=gold, article=cyan)
- sections 렌더링 (접이식 아코디언)
- related_servants 그리드
- historical_basis 섹션
- **신규: [관련 시프트] 버튼** — 연결된 시프트가 있으면 표시
- **신규: [글로브에서 보기] 버튼** — year/location 기반 flyTo
- sources 리스트

**네비게이션**: `[← 뒤로]` → 이전 뷰 (home 또는 collection).

---

## API 클라이언트 변경

### api/client.ts에 추가

```typescript
export const portalApi = {
  // Portal Items
  getItems: (params?: { item_type?: string; is_featured?: boolean; limit?: number }) =>
    api.get('/portal/items', { params }),
  getItem: (slug: string) =>
    api.get(`/portal/items/${slug}`),

  // Collections
  getCollections: (params?: { collection_type?: string; is_featured?: boolean }) =>
    api.get('/portal/collections', { params }),
  getCollection: (slug: string) =>
    api.get(`/portal/collections/${slug}`),

  // Featured (magazine home)
  getFeatured: () =>
    api.get('/portal/featured'),

  // Today's History (신규 백엔드 필요)
  getToday: () =>
    api.get('/portal/today'),
}
```

기존 `trismegistosApi`는 삭제하지 않음 (showcases 레거시 URL은 DB에서 서빙 중).

---

## 타입 정의 추가

### types/index.ts에 추가

```typescript
// Portal
export interface PortalItem {
  id: number
  slug: string
  item_type: string
  title: string
  title_ko?: string
  title_ja?: string
  subtitle?: string
  subtitle_ko?: string
  subtitle_ja?: string
  description: string
  description_ko?: string
  description_ja?: string
  chapter?: string
  era?: string
  year?: number
  location?: string
  historical_basis?: string
  historical_basis_ko?: string
  historical_basis_ja?: string
  sections: Array<{
    title: string; title_ko?: string; title_ja?: string
    content: string; content_ko?: string; content_ja?: string
  }>
  related_servants: Array<{ name: string; class: string; rarity: number }>
  related_event_ids: number[]
  sources: string[]
  is_featured: boolean
  sort_order: number
  thumbnail_url?: string
}

export interface PortalCollection {
  id: number
  slug: string
  collection_type: string
  title: string
  title_ko?: string
  title_ja?: string
  description?: string
  description_ko?: string
  description_ja?: string
  icon?: string
  cover_image_url?: string
  is_featured: boolean
  tags: string[]
  year_start?: number
  year_end?: number
  region?: string
  entry_count: number
  entries?: PortalCollectionEntry[]
}

export interface PortalCollectionEntry {
  id: number
  entry_type: 'shift' | 'portal_item' | 'person' | 'event' | 'period'
  sort_order: number
  is_highlighted: boolean
  note?: string
  note_ko?: string
  // 다형적 참조 (하나만 채워짐)
  portal_item?: PortalItem
  shift_id?: number
  person_id?: number
  event_id?: number
  period_id?: number
}
```

---

## 스타일 가이드

### CSS 변수 (기존 chaldea 테마 활용)

| 변수 | 용도 |
|------|------|
| `--chaldea-bg` | 배경 |
| `--chaldea-border` | 테두리 |
| `--chaldea-text` / `text-bright` / `text-dim` | 텍스트 |
| `--chaldea-cyan` | 인터랙티브 요소, 아티클 |
| `--chaldea-orange` | 특이점 |
| `--chaldea-magenta` | 이문대 |
| `--chaldea-gold` | 서번트 |

### CSS 클래스 네이밍 (신규)

```
.portal-*                    — 포털 전체
.portal-home                 — 매거진 홈 스크롤 컨테이너
.portal-hero                 — 히어로 배너
.portal-hero__title          — 히어로 제목
.portal-hero__cta            — CTA 버튼 row
.portal-section              — 섹션 공용 (제목 + 내용)
.portal-section__title       — 섹션 제목 (━━ 구분선 포함)
.portal-card                 — 카드 공용
.portal-card--shift          — 시프트 카드
.portal-card--item           — 아이템 카드
.portal-card--collection     — 컬렉션 카드
.portal-card__type           — 타입 라벨
.portal-card__title          — 카드 제목
.portal-card__meta           — 연도/장소 메타
.portal-rec-row              — 추천 카드 가로 스크롤
.portal-fgo                  — FGO 섹션
.portal-fgo__intro           — 도입 문구
.portal-fgo__grid            — 특이점/이문대 그리드
.portal-reading              — 읽을거리 섹션
.portal-reading__filters     — 필터 칩 row
.portal-collection-grid      — 컬렉션 그리드
.portal-collection-page      — 컬렉션 상세
.portal-collection-page__header — 컬렉션 헤더
.portal-detail               — 아이템 상세
.portal-detail__sections     — 섹션 아코디언
```

### 모달 형태

| 뷰 | 형태 | 글로브 |
|----|------|--------|
| 매거진 홈 | 풀스크린 모달 (max-width: 900px, 90vh) | 가려짐 |
| 컬렉션 상세 | 동일 모달 (내부 전환) | 가려짐 |
| 아이템 상세 | 동일 모달 (내부 전환) | 가려짐 |
| 시프트 진입 | **모달 닫기** → ShiftPanel (글로브 위) | **보임** |
| 글로브에서 보기 | **모달 닫기** → flyTo + NarrativePanel | **보임** |

**핵심**: 콘텐츠를 "보는" 건 모달 안. "체험하는" 건 글로브 위.

---

## 모달 ↔ 글로브 전환 패턴

```
사용자가 모달 안에서 [글로브에서 보기] 클릭
  1. onClose() → 모달 닫기
  2. onFlyToLocation(lat, lng) → 글로브 이동
  3. onSetCurrentYear(year) → 시간 설정
  4. (optional) onEventClick(eventId) → NarrativePanel 열기

사용자가 모달 안에서 [시프트로 체험] 클릭
  1. onClose() → 모달 닫기
  2. onOpenShift(shiftId) → ShiftPanel 열기
```

이 패턴은 기존 TrismegistosModal과 동일. Props로 전달받은 콜백 사용.

---

## 데이터 흐름

```
┌─ portalStore (Zustand) ─────────────────────────┐
│  view: 'home' | 'collection' | 'detail'          │
│  activeCollectionSlug: string | null              │
│  activeItemSlug: string | null                    │
│  history: [{ view, slug }]                        │
└──────────────────────┬──────────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
   MagazineHome   CollectionPage   PortalItemDetail
       │               │               │
  React Query     React Query     React Query
       │               │               │
       ▼               ▼               ▼
  portalApi.      portalApi.      portalApi.
  getFeatured()   getCollection() getItem()
       │               │               │
       ▼               ▼               ▼
  /api/v1/portal/ /api/v1/portal/ /api/v1/portal/
  featured        collections/    items/{slug}
                  {slug}
```

**React Query 캐싱**: staleTime 5분. 매거진 홈 데이터는 한 번 로드하면 세션 내 유지.

---

## i18n 전략

모든 텍스트 필드는 `_ko`, `_ja` 접미사. 유틸 함수:

```typescript
// 기존 패턴 재사용
function getLocalizedText(item: any, field: string, lang: string): string {
  if (lang !== 'en') {
    const localized = item[`${field}_${lang}`]
    if (localized) return localized
  }
  return item[field] || ''
}
```

UI 라벨은 기존 `useTranslation()` (i18next) 사용.

**추가할 i18n 키** (ko.json / ja.json):
```json
{
  "portal.today": "오늘의 역사",
  "portal.recommendations": "이번 주 추천",
  "portal.fgo_section": "FGO에서 시작하기",
  "portal.fgo_intro": "FGO를 아시나요? 게임 속 특이점은 실제 역사를 배경으로 합니다.",
  "portal.reading": "읽을거리",
  "portal.collections": "컬렉션 둘러보기",
  "portal.view_on_globe": "글로브에서 보기",
  "portal.start_shift": "시프트로 체험",
  "portal.back": "홈으로",
  "portal.all": "전체",
  "portal.history": "역사",
  "portal.literature": "문학",
  "portal.music": "음악"
}
```

---

## 구현 순서

```
Step 1: 기반 (1일)
  - portalStore.ts 생성
  - types/index.ts에 Portal 타입 추가
  - api/client.ts에 portalApi 추가
  - portal.css 기본 레이아웃

Step 2: 매거진 홈 쉘 (1일)
  - TrismegistosPortal.tsx (view 라우팅)
  - MagazineHome.tsx (5섹션 스켈레톤)
  - App.tsx 연결 교체

Step 3: 섹션 컴포넌트 (2일)
  - FgoSection.tsx (API 연동)
  - ReadingSection.tsx (필터 + 리스트)
  - CollectionGrid.tsx (컬렉션 카드)
  - RecommendationRow.tsx (featured 데이터)

Step 4: Layer 2 (1일)
  - CollectionPage.tsx (entry_type별 렌더링)
  - PortalItemDetail.tsx (기존 콘텐츠 뷰 이식)

Step 5: 오늘의 역사 (1일)
  - 백엔드 /api/v1/portal/today 엔드포인트
  - TodayHero.tsx

Step 6: 폴리시 (1일)
  - 애니메이션 (fadeIn, slideUp)
  - 반응형 (640px 브레이크포인트)
  - Escape 키 네비게이션
  - 기존 TrismegistosModal/Menu 삭제
```

---

## 삭제 체크리스트 (최종)

구현 완료 후 삭제:

- [ ] `trismegistos/TrismegistosModal.tsx` → `TrismegistosPortal.tsx`로 교체됨
- [ ] `trismegistos/TrismegistosMenu.tsx` → FgoSection + ReadingSection으로 분해됨
- [ ] `data/trismegistosData.ts` → DB API 전환 완료
- [ ] `api/client.ts`의 `trismegistosApi` → `portalApi`로 교체됨 (showcases URL은 유지)
- [ ] App.tsx의 `TrismegistosContent` 타입 → `PortalItem` 타입으로 교체
