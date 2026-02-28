# PORTAL 02 — 매거진 홈: 5개 섹션 상세

> 아키텍처: `PORTAL_01_ARCHITECTURE.md` | 추천 엔진: `PORTAL_04_RECOMMENDATIONS.md`

---

## 전체 구조

매거진 홈 = Layer 1. 포털 열면 최초로 보이는 화면.
**탭 없음. 스크롤만.** 위에서 아래로 5개 섹션이 흐른다.

```
┌─ TRISMEGISTOS ──────────────────────────────── [✕] ─┐
│                                                      │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│  ┃  Section 1: TodayHero                         ┃  │
│  ┃  오늘의 역사 — 히어로 배너                     ┃  │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│                                                      │
│  ─── Section 2: RecommendationRow ───────────────── │
│  추천 카드 4~6개 (가로 스크롤)                       │
│                                                      │
│  ─── Section 3: FgoSection ─────────────────────── │
│  FGO에서 시작하기 (특이점 + 이문대 + 서번트)         │
│                                                      │
│  ─── Section 4: ReadingSection ─────────────────── │
│  읽을거리 (역사/문학/음악 필터)                      │
│                                                      │
│  ─── Section 5: CollectionGrid ─────────────────── │
│  컬렉션 둘러보기 (카드 그리드)                       │
│                                                      │
│  ─── Footer ────────────────────────────────────── │
│  CHALDEAS ARCHIVE                                    │
└──────────────────────────────────────────────────────┘
```

---

## MagazineHome.tsx

```typescript
interface MagazineHomeProps {
  // 글로브 액션 (TrismegistosPortal에서 전달)
  onFlyToLocation: (lat: number, lng: number) => void
  onSetCurrentYear: (year: number) => void
  onEventClick: (eventId: number) => void
  onPersonClick: (personId: number) => void
  onOpenShift: (shiftId: number) => void
}
```

**데이터 로딩**:

```typescript
// 한 번의 API 호출로 홈 전체 데이터
const { data: featured } = useQuery({
  queryKey: ['portal', 'featured', lang],
  queryFn: () => portalApi.getFeatured(),
  staleTime: 5 * 60 * 1000,  // 5분
})

// FGO 아이템은 별도 (타입별 필터)
const { data: fgoItems } = useQuery({
  queryKey: ['portal', 'items', 'fgo', lang],
  queryFn: () => portalApi.getItems({
    item_type: 'singularity,lostbelt,servant_column'
  }),
  staleTime: 10 * 60 * 1000,
})

// 읽을거리
const { data: readingItems } = useQuery({
  queryKey: ['portal', 'items', 'reading', lang],
  queryFn: () => portalApi.getItems({
    item_type: 'history,literature,music'
  }),
  staleTime: 10 * 60 * 1000,
})

// 컬렉션 목록
const { data: collections } = useQuery({
  queryKey: ['portal', 'collections', lang],
  queryFn: () => portalApi.getCollections(),
  staleTime: 10 * 60 * 1000,
})
```

---

## Section 1: TodayHero — 오늘의 역사

### 목적

"매번 같은 화면"을 깨는 핵심. 매일 다른 이벤트가 최상단에.

### 와이어프레임

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│  ▷ 오늘의 역사 — 2월 28일                            │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │                                                │  │
│  │  「228 사건」                                   │  │
│  │  1947 · 타이완                                 │  │
│  │                                                │  │
│  │  일본 식민지에서 해방된 지 불과 2년,             │  │
│  │  국민당 정부의 폭정에 맞선 타이완 민중의          │  │
│  │  항쟁이 시작되었다.                              │  │
│  │                                                │  │
│  │  [🌍 글로브에서 보기]    [▶ 시프트로 체험]       │  │
│  │                                                │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  내일 예고: 3월 1일 — 3·1 운동 (1919)                │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 데이터 소스

**우선순위**:
1. 오늘 날짜(월/일) 매칭 이벤트 — `GET /api/v1/portal/today`
2. is_featured=true인 portal_items 중 랜덤
3. 아무 이벤트 없으면: 정적 환영 메시지

### 백엔드 API (신규)

```
GET /api/v1/portal/today
Response:
{
  "event": {
    "id": 12345,
    "title": "February 28 Incident",
    "title_ko": "228 사건",
    "year": 1947,
    "month": 2,
    "day": 28,
    "lat": 25.0330,
    "lng": 121.5654,
    "description_ko": "일본 식민지에서 해방된 지 불과 2년...",
    "importance": 7
  },
  "shift_id": 456,           // 관련 시프트 (nullable)
  "tomorrow_preview": {       // 내일 예고 (nullable)
    "title_ko": "3·1 운동",
    "year": 1919
  }
}
```

**쿼리 로직 (백엔드)**:
```sql
SELECT e.id, e.title, e.title_ko, e.date_start as year,
       ed.description_ko, e.importance,
       l.latitude as lat, l.longitude as lng
FROM events e
LEFT JOIN event_details ed ON ed.event_id = e.id
LEFT JOIN event_locations el ON el.event_id = e.id
LEFT JOIN locations l ON l.id = el.location_id
WHERE EXTRACT(MONTH FROM make_date(2000,
    COALESCE(e.date_month, 1), COALESCE(e.date_day, 1)))
    = EXTRACT(MONTH FROM CURRENT_DATE)
  AND EXTRACT(DAY FROM make_date(2000,
    COALESCE(e.date_month, 1), COALESCE(e.date_day, 1)))
    = EXTRACT(DAY FROM CURRENT_DATE)
  AND e.importance >= 5
ORDER BY e.importance DESC
LIMIT 1
```

> 참고: events 테이블에 date_month, date_day 컬럼이 없을 수 있음.
> 그 경우 date_start (연도 정수)만으로는 월/일 매칭 불가 →
> event_details나 별도 매핑 테이블 필요. 아니면 수동 큐레이션 JSON fallback.

### CTA 버튼 동작

| 버튼 | 동작 |
|------|------|
| 🌍 글로브에서 보기 | `portalStore.close()` → `onFlyToLocation(lat, lng)` → `onSetCurrentYear(year)` |
| ▶ 시프트로 체험 | `portalStore.close()` → `onOpenShift(shift_id)`. shift_id 없으면 숨김 |

### 내일 예고

히어로 하단에 작은 텍스트:
```
내일 예고: 3월 1일 — 3·1 운동 (1919)
```
클릭 불가. 재방문 동기 부여용. API에서 tomorrow도 같이 보내줌.

### 폴백

- 오늘 매칭 이벤트 없음 → featured portal_items 중 랜덤 1개를 히어로로
- API 에러 → 정적 환영 메시지: "역사의 바다에 오신 것을 환영합니다"

---

## Section 2: RecommendationRow — 이번 주 추천

### 목적

다양한 타입의 콘텐츠를 섞어서 "이런 것도 있어요" 느낌.

### 와이어프레임

```
━━ 이번 주 추천 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

← ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ →
   │ ▶       │ │ 📖      │ │ 🏛      │ │ ⚔      │ │ ▶       │
   │ 그리스  │ │ 잔 다르│ │ 그리스  │ │ 길가메시│ │ 로마    │
   │ 페르시아│ │ 크의    │ │ ·로마   │ │ : 신화  │ │ 공화정  │
   │ 전쟁    │ │ 진실    │ │ 컬렉션  │ │ 에서    │ │ 의 몰락 │
   │         │ │         │ │         │ │ 역사로  │ │         │
   │ 시프트  │ │ 아티클  │ │ 컬렉션  │ │ 서번트  │ │ 시프트  │
   │ 7 pages │ │         │ │ 42 항목 │ │ 컬럼    │ │ 9 pages │
   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
```

### 카드 타입

| 타입 | 아이콘 | 하단 라벨 | 클릭 시 |
|------|--------|----------|---------|
| portal_item (singularity) | ⚔ | "특이점" | `pushDetail(slug)` |
| portal_item (lostbelt) | ✦ | "이문대" | `pushDetail(slug)` |
| portal_item (servant_column) | ⚔ | "서번트 컬럼" | `pushDetail(slug)` |
| portal_item (history/lit/music) | 📖 | "아티클" | `pushDetail(slug)` |
| shift | ▶ | "시프트 · N pages" | `portalStore.close()` → `onOpenShift(id)` |
| collection | 🏛 | "컬렉션 · N 항목" | `pushCollection(slug)` |

### 카드 컴포넌트

```typescript
interface RecommendationCardProps {
  type: 'portal_item' | 'shift' | 'collection'
  icon: string
  title: string
  title_ko?: string
  subtitle: string       // 타입 라벨 + 메타
  slug_or_id: string | number
  onClick: () => void
}
```

### CSS

```css
.portal-rec-row {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  padding: 0 24px 16px;
  -webkit-overflow-scrolling: touch;
}

.portal-rec-row::-webkit-scrollbar { height: 4px; }
.portal-rec-row::-webkit-scrollbar-thumb {
  background: var(--chaldea-border);
  border-radius: 2px;
}

.portal-rec-card {
  flex: 0 0 160px;
  scroll-snap-align: start;
  background: var(--overlay-bg);
  border: 1px solid var(--chaldea-border);
  border-radius: var(--overlay-radius);
  padding: 16px 14px;
  cursor: pointer;
  transition: border-color 0.2s, transform 0.2s;
}

.portal-rec-card:hover {
  border-color: var(--overlay-border-hover);
  transform: translateY(-2px);
}
```

### 데이터

`GET /api/v1/portal/featured` 응답의 `recommendations` 배열.
상세: `PORTAL_04_RECOMMENDATIONS.md`

---

## Section 3: FgoSection — FGO에서 시작하기

### 목적

FGO를 아는 사람에겐 친숙한 진입점. 모르는 사람에겐 "게임 속 역사?" 호기심 유발.

### 와이어프레임

```
━━ FGO에서 시작하기 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  FGO를 아시나요? 게임 속 특이점은 실제 역사를
  배경으로 합니다. 각 특이점의 진짜 역사를
  지구본 위에서 체험해보세요.

  ── 특이점 ──────────────────────────────────────

  ┌────────────┐ ┌────────────┐ ┌────────────┐ →
  │ F. Fuyuki  │ │ I. Orleans │ │VII.Babylonia│
  │ 2004 일본  │ │ 1431 프랑스│ │-2655 메소포 │
  │            │ │            │ │  타미아     │
  │ Mash       │ │Joan of Arc │ │ Gilgamesh  │
  └────────────┘ └────────────┘ └────────────┘

  ── 이문대 ──────────────────────────────────────

  ┌────────────┐ ┌────────────┐ →
  │1.Anastasia │ │5. Olympus  │
  │ 1570 러시아│ │-12000 그리스│
  └────────────┘ └────────────┘

  ── 서번트 열전 ─────────────────────────────────

  ┌────────────┐ ┌────────────┐ →
  │ Gilgamesh  │ │ Leonidas   │
  │ Archer ★5  │ │ Lancer ★2  │
  │ 신화→역사  │ │ 스파르타의 │
  │            │ │ 전사왕     │
  └────────────┘ └────────────┘

  [📚 FGO 메인 스토리 컬렉션 전체보기 →]
```

### 데이터

```typescript
// FGO 아이템 필터링
const singularities = fgoItems?.filter(i => i.item_type === 'singularity')
  .sort((a, b) => a.sort_order - b.sort_order)
const lostbelts = fgoItems?.filter(i => i.item_type === 'lostbelt')
  .sort((a, b) => a.sort_order - b.sort_order)
const servantColumns = fgoItems?.filter(i => i.item_type === 'servant_column')
  .sort((a, b) => a.sort_order - b.sort_order)
```

### FGO 카드 컴포넌트

```typescript
interface FgoCardProps {
  item: PortalItem
  onClick: () => void     // pushDetail(slug)
}

// 특이점/이문대 카드:
// - 챕터 번호 (chapter 필드: "Singularity F", "Lostbelt No.1")
// - 타이틀 (title / title_ko)
// - 연도 + 장소 (year, location)
// - 대표 서번트 1~2 (related_servants 배열의 앞 2개)

// 서번트 카드:
// - 이름 (title)
// - 클래스 + 레어도 (related_servants[0]의 class, rarity)
// - 한 줄 소개 (subtitle / subtitle_ko)
```

### 색상 체계

| item_type | 좌측 보더 색상 | CSS 변수 |
|-----------|--------------|----------|
| singularity | orange | `--chaldea-orange` |
| lostbelt | magenta | `--chaldea-magenta` |
| servant_column | gold | `--chaldea-gold` |

```css
.portal-fgo-card--singularity { border-left: 3px solid var(--chaldea-orange); }
.portal-fgo-card--lostbelt { border-left: 3px solid var(--chaldea-magenta); }
.portal-fgo-card--servant { border-left: 3px solid var(--chaldea-gold); }
```

### 하단 링크

```typescript
<button
  className="portal-fgo__collection-link"
  onClick={() => usePortalStore.getState().pushCollection('fgo-main-story')}
>
  📚 FGO 메인 스토리 컬렉션 전체보기 →
</button>
```

---

## Section 4: ReadingSection — 읽을거리

### 목적

역사/문학/음악 아티클을 한 곳에. 필터 칩으로 빠르게 탐색.

### 와이어프레임

```
━━ 읽을거리 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  [전체]  [역사]  [문학]  [음악]       정렬: 추천순 ▼

  ┌─────────────────────────────────────────────────┐
  │  📖 The Crusades                                 │
  │  1095 · Europe / Middle East · 역사              │
  │  서유럽 기독교 세계가 성지 탈환을 위해...         │
  └─────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────┐
  │  📖 Arthurian Legend                             │
  │  500 · Britain · 문학                            │
  │  아서 왕 전설의 역사적 기원과 문학적 변용...      │
  └─────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────┐
  │  🎵 Mozart                                       │
  │  1756 · Austria · 음악                           │
  │  35년의 짧은 생애, 600곡 이상의 걸작...           │
  └─────────────────────────────────────────────────┘

  더 보기 (N개) →
```

### 필터 상태

```typescript
const [readingFilter, setReadingFilter] = useState<string>('all')
// 'all' | 'history' | 'literature' | 'music'

const filteredItems = readingItems?.filter(item =>
  readingFilter === 'all' || item.item_type === readingFilter
)
```

### 칩 CSS

```css
.portal-reading__filters {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.portal-filter-chip {
  padding: 6px 14px;
  border: 1px solid var(--chaldea-border);
  border-radius: 16px;
  background: transparent;
  color: var(--chaldea-text);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.portal-filter-chip--active {
  background: var(--chaldea-cyan);
  color: #000;
  border-color: var(--chaldea-cyan);
}
```

### 아이템 카드

```css
.portal-reading-item {
  padding: 14px 18px;
  border: 1px solid var(--chaldea-border);
  border-radius: var(--overlay-radius);
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.portal-reading-item:hover {
  border-color: var(--chaldea-cyan);
}

.portal-reading-item__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--chaldea-text-bright);
}

.portal-reading-item__meta {
  font-size: 12px;
  color: var(--chaldea-text-dim);
  margin-top: 4px;
}

.portal-reading-item__excerpt {
  font-size: 13px;
  color: var(--chaldea-text);
  margin-top: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
```

### "더 보기" 제한

초기: 최대 5개만 표시. 클릭하면 전체 리스트 (또는 ReadingSection 전체를 스크롤).

---

## Section 5: CollectionGrid — 컬렉션 둘러보기

### 목적

주제별 "전시실" 입구. 카드 클릭 → Layer 2 (CollectionPage) 중첩 모달.

### 와이어프레임

```
━━ 컬렉션 둘러보기 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ ⚔ FGO   │ │ 🏛 그리스│ │ 🎭 예술  │
  │ 메인     │ │ ·로마    │ │ ·문화    │
  │ 스토리   │ │          │ │          │
  │          │ │ 42 시프트│ │  7 아티클│
  │ 8 특이점 │ │ 12 아티클│ │ 30+ 인물 │
  │ 7 이문대 │ │ 150+ 인물│ │          │
  └──────────┘ └──────────┘ └──────────┘

  ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ 🗡 전쟁사│ │ ⛩ 동아시│ │ 📜 철학사│
  │          │ │ 아       │ │          │
  │ 67 시프트│ │ 38 시프트│ │ 23 시프트│
  │  8 아티클│ │  6 아티클│ │  5 아티클│
  └──────────┘ └──────────┘ └──────────┘
```

### 데이터

```typescript
// GET /api/v1/portal/collections 응답
interface CollectionSummary {
  slug: string
  title: string
  title_ko?: string
  icon?: string              // 이모지
  entry_count: number        // 총 엔트리 수
  collection_type: string
  is_featured: boolean
}
```

> **참고**: 현재 entry_count만 API가 보내줌. 타입별 카운트(시프트 N개, 아티클 M개)가
> 필요하면 백엔드에 `entry_counts: { shift: 42, portal_item: 12, person: 150 }` 추가 필요.

### 카드 CSS

```css
.portal-collection-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  padding: 0 24px;
}

.portal-collection-card {
  background: var(--overlay-bg);
  border: 1px solid var(--chaldea-border);
  border-radius: var(--overlay-radius);
  padding: 20px 16px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, transform 0.2s;
}

.portal-collection-card:hover {
  border-color: var(--overlay-border-hover);
  transform: translateY(-2px);
}

.portal-collection-card__icon {
  font-size: 28px;
  margin-bottom: 8px;
}

.portal-collection-card__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--chaldea-text-bright);
  margin-bottom: 4px;
}

.portal-collection-card__stats {
  font-size: 12px;
  color: var(--chaldea-text-dim);
  line-height: 1.5;
}
```

### 클릭 동작

```typescript
onClick={() => usePortalStore.getState().pushCollection(collection.slug)}
// → Layer 2 중첩 모달로 CollectionPage 등장
```

---

## 모달 내부 레이아웃

### 스크롤 컨테이너

```css
/* 매거진 홈의 모달 컨테이너 */
.portal-home {
  max-width: 900px;
  width: 95vw;
  max-height: 90vh;
  background: linear-gradient(135deg, rgba(10, 16, 24, 0.98), rgba(5, 8, 16, 0.98));
  border: 2px solid var(--chaldea-border);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  /* 스캔라인 이펙트 유지 */
  position: relative;
}

.portal-home::before {
  content: '';
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 212, 255, 0.015) 2px,
    rgba(0, 212, 255, 0.015) 4px
  );
  pointer-events: none;
  z-index: 10;
}

/* 스크롤 영역 */
.portal-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 0 0 32px;
}

/* 헤더 (고정) */
.portal-home__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--chaldea-border);
  flex-shrink: 0;
}

.portal-home__title {
  font-size: 14px;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--chaldea-text-dim);
}
```

### 섹션 공용 스타일

```css
.portal-section {
  padding: 24px 24px 16px;
}

.portal-section__title {
  font-size: 13px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--chaldea-text-dim);
  margin-bottom: 16px;
  /* 구분선 */
  display: flex;
  align-items: center;
  gap: 12px;
}

.portal-section__title::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--chaldea-border);
}
```

---

## 반응형

| 너비 | 변경 |
|------|------|
| > 900px | 기본 레이아웃 (max-width: 900px) |
| 640~900px | 모달 width: 95vw. 컬렉션 그리드 2열 |
| < 640px | 모달 width: 100vw, height: 100vh (풀스크린). FGO 카드 가로 스크롤 |

```css
@media (max-width: 640px) {
  .portal-home {
    max-width: 100vw;
    max-height: 100vh;
    border-radius: 0;
    border: none;
  }

  .portal-collection-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .portal-fgo__grid {
    flex-wrap: nowrap;
    overflow-x: auto;
  }
}
```

---

## 스켈레톤 로딩

API 로딩 중 표시할 스켈레톤:

```css
.portal-skeleton {
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0.05) 25%,
    rgba(255, 255, 255, 0.1) 50%,
    rgba(255, 255, 255, 0.05) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--overlay-radius-sm);
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
```

---

## 관련 문서

| 문서 | 내용 |
|------|------|
| `PORTAL_01_ARCHITECTURE.md` | 중첩 모달 스택, portalStore |
| `PORTAL_03_COLLECTIONS.md` | CollectionPage, PortalItemDetail |
| `PORTAL_04_RECOMMENDATIONS.md` | 추천 로직 상세, "이런 것도" 시스템 |
