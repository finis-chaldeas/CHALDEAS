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

## Section 1: TodayHero — 오늘의 히어로

### 목적

"매번 같은 화면"을 깨는 핵심. 열 때마다 다른 콘텐츠가 최상단에.

### 와이어프레임

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│  ▷ 오늘의 역사                                       │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │                                                │  │
│  │  「그리스-페르시아 전쟁」                        │  │
│  │  -499 ~ -449 · 그리스, 페르시아                 │  │
│  │                                                │  │
│  │  마라톤에서 시작된 작은 반란이                    │  │
│  │  서양 문명의 운명을 결정짓는                      │  │
│  │  대전쟁으로 번져나갔다.                          │  │
│  │                                                │  │
│  │  [🌍 글로브에서 보기]    [▶ 시프트로 체험]       │  │
│  │                                                │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 데이터 소스: 3단계 접근

> **현실**: events 테이블의 `date_start`는 **연도 정수**만 저장.
> `date_precision`도 전부 'year'. 월/일 매칭 데이터가 없음.

#### Phase 1 (현재): 결정론적 일별 로테이션

월/일 데이터 없으므로, **오늘 날짜의 해시로 콘텐츠를 결정**.

```typescript
// 프론트엔드에서 계산 (API 호출 불필요)
function getTodayHeroIndex(itemCount: number): number {
  const today = new Date()
  const dayOfYear = Math.floor(
    (today.getTime() - new Date(today.getFullYear(), 0, 0).getTime()) / 86400000
  )
  return dayOfYear % itemCount
}
```

**로테이션 풀**:
1. `is_featured=true`인 portal_items (현재 15개)
2. `globe_importance >= 7`인 shifts (상위 ~50개)
3. 두 풀을 합쳐서 인덱스로 선택

```typescript
const heroPool = [
  ...featuredItems.map(i => ({ kind: 'item' as const, data: i })),
  ...topShifts.map(s => ({ kind: 'shift' as const, data: s })),
]
const todayHero = heroPool[getTodayHeroIndex(heroPool.length)]
```

#### Phase 2 (미래): `portal_calendar` 테이블

월/일별 큐레이션 데이터. AI 배치 또는 수동 시딩.

```sql
CREATE TABLE portal_calendar (
  id SERIAL PRIMARY KEY,
  month INTEGER NOT NULL,          -- 1~12
  day INTEGER NOT NULL,            -- 1~31
  title VARCHAR(300) NOT NULL,     -- "228 사건"
  title_ko VARCHAR(300),
  description TEXT,
  description_ko TEXT,
  -- 참조 (하나만 NOT NULL)
  event_id INTEGER REFERENCES events(id),
  person_id INTEGER REFERENCES persons(id),
  shift_id INTEGER REFERENCES historical_chains(id),
  portal_item_id INTEGER REFERENCES portal_items(id),
  -- 표시
  lat FLOAT,
  lng FLOAT,
  year INTEGER,                    -- 대표 연도
  importance INTEGER DEFAULT 5,
  UNIQUE(month, day, COALESCE(event_id,0), COALESCE(person_id,0))
);
-- 약 200~365개 시딩 (1일 1~3개)
```

API:
```
GET /api/v1/portal/today?month=2&day=28
Response:
{
  "date": { "month": 2, "day": 28 },
  "entries": [
    {
      "title": "February 28 Incident",
      "title_ko": "228 사건",
      "year": 1947,
      "lat": 25.033, "lng": 121.565,
      "event_id": 12345,
      "shift_id": 456,
      "description_ko": "일본 식민지에서 해방된 지..."
    }
  ],
  "tomorrow_preview": {
    "title_ko": "3·1 운동",
    "year": 1919
  }
}
```

#### Phase 3 (미래): 자동 매칭

events 테이블에 `date_month`, `date_day` 컬럼을 추가하고,
Wikidata에서 정확한 날짜를 가진 이벤트(선언, 전투, 조약 등)를 역추출.

### CTA 버튼 동작

| 버튼 | 동작 |
|------|------|
| 🌍 글로브에서 보기 | `portalStore.close()` → `onFlyToLocation(lat, lng)` → `onSetCurrentYear(year)` |
| ▶ 시프트로 체험 | `portalStore.close()` → `onOpenShift(shift_id)`. shift_id 없으면 숨김 |

**좌표 해결** (Phase 1):
- portal_item → `related_event_ids[0]` → events → event_locations → locations.lat/lng
- shift → `chain_segments[0]` → segment.lat/lng
- 좌표 없으면 "글로브에서 보기" 버튼 숨김

### 폴백

- 로테이션 풀 비어있음 → 정적 환영 메시지: "역사의 바다에 오신 것을 환영합니다"
- API 에러 → 동일 폴백

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
| `PORTAL_01_ARCHITECTURE.md` | 중첩 모달 스택, portalStore, 글로브 연결 |
| `PORTAL_03_COLLECTIONS.md` | CollectionPage, PortalItemDetail, 엔트리 joinedload |
| `PORTAL_04_RECOMMENDATIONS.md` | 추천 로직 상세, "이런 것도" 시스템 |
| `PORTAL_05_ARTICLES.md` | 엔티티 링크 6종, /resolve, /suggest-links |

---

## 현재 데이터 현황 (2026-02-28 기준)

| 테이블 | 행 수 | 비고 |
|--------|-------|------|
| portal_items | 34 | singularity(8), lostbelt(7), servant_column(12), history(3), literature(2), music(2) |
| collections | 3 | fgo-main-story, greece-rome, arts-culture |
| collection_entries | 10 | 전부 portal_item 타입 (shift/person/event 미사용) |
| fgo_servants | 449 | 82개 person 링크, 367개 미링크 |
| historical_chains | 895 | 시프트 (9,358 페이지) |
| events | 28,331 | date_precision 전부 'year', date_month/date_day 없음 |
