# PORTAL 03 — 컬렉션 페이지 + 아이템 상세

> 아키텍처: `PORTAL_01_ARCHITECTURE.md` | 매거진 홈: `PORTAL_02_MAGAZINE_HOME.md`

---

## 개요

Layer 2~3의 중첩 모달. "그리스·로마 컬렉션"을 열면 매거진 홈 위에 슬라이드.
그 안에서 아이템을 클릭하면 Layer 3으로 또 하나 열림.

```
Magazine Home (dimmed) → CollectionPage (active) → PortalItemDetail (active)
```

---

## CollectionPage.tsx — 컬렉션 상세

### 목적

하나의 주제 아래 시프트/아티클/인물/이벤트를 통합.
"그리스·로마에 관한 모든 것이 여기 있다."

### 와이어프레임

```
┌─ [← 홈] 그리스·로마 ────────────────────── [✕] ─┐
│                                                    │
│  🏛 그리스·로마 컬렉션                              │
│  "지중해를 지배한 두 문명의 이야기"                   │
│                                                    │
│  ┌──────────────────────────────────────────────┐  │
│  │  💡 편집자 추천                                │  │
│  │  "마라톤 전투 시프트부터 시작해보세요.          │  │
│  │   고대 그리스의 승리 이야기입니다."             │  │
│  │                                              │  │
│  │  ▶ 마라톤 전투  ←  클릭 시 시프트 바로 시작    │  │
│  └──────────────────────────────────────────────┘  │
│                                                    │
│  ━━ 시프트 (42) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                    │
│  ┌─ 그리스-페르시아 전쟁 ─────────────────────┐   │
│  │ ▶ -490 ~ -449 · 7 pages · aggregate       │   │
│  │ 마라톤에서 살라미스까지                     │   │
│  └────────────────────────────────────────────┘   │
│  ┌─ 알렉산드로스 대왕 ───────────────────────┐   │
│  │ ▶ -356 ~ -323 · 12 pages · person_story   │   │
│  └────────────────────────────────────────────┘   │
│  ┌─ 로마 공화정의 몰락 ─────────────────────┐    │
│  │ ▶ -133 ~ -27 · 9 pages · era_story       │    │
│  └────────────────────────────────────────────┘   │
│                                                    │
│  ━━ 아티클 (12) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                    │
│  ┌─ The Battle of Thermopylae ───────────────┐   │
│  │ 📖 -480 · Thermopylae · 역사              │   │
│  └────────────────────────────────────────────┘   │
│  ┌─ Spartan Society ────────────────────────┐    │
│  │ 📖 -700 · Greece · 역사                   │    │
│  └────────────────────────────────────────────┘   │
│                                                    │
│  ━━ 주요 인물 (150+) ━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                    │
│  ┌────────┐ ┌──────────┐ ┌────────┐ ┌──────┐     │
│  │Leonidas│ │Themistocl│ │Pericles│ │Alexan│     │
│  │-540    │ │es -524   │ │-495    │ │der   │     │
│  └────────┘ └──────────┘ └────────┘ └──────┘     │
│  ┌────────┐ ┌──────────┐ ┌────────┐               │
│  │Caesar  │ │Augustus  │ │Cicero  │               │
│  │-100    │ │-63       │ │-106    │               │
│  └────────┘ └──────────┘ └────────┘               │
│  + 143 더보기                                      │
│                                                    │
│  ━━ 주요 이벤트 (200+) ━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                    │
│  마라톤 전투(-490) · 살라미스(-480)                  │
│  테르모필레(-480) · 펠로폰네소스 전쟁(-431)          │
│  카이사르 암살(-44) · 악티움 해전(-31)               │
│  + 194 더보기                                      │
│                                                    │
│  ━━ 이런 것도 좋아하실 걸요 ━━━━━━━━━━━━━━━━━━━━  │
│                                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ 🗡 전쟁사│ │ 📜 철학사│ │ 🌏 실크  │           │
│  │ 컬렉션  │ │ 컬렉션  │ │ 로드     │           │
│  └──────────┘ └──────────┘ └──────────┘           │
│                                                    │
└────────────────────────────────────────────────────┘
```

### Props

```typescript
interface CollectionPageProps {
  slug: string
  // 글로브 액션 (TrismegistosPortal에서 전달)
  onEventClick: (eventId: number) => void
  onPersonClick: (personId: number) => void
  onOpenShift: (shiftId: number) => void
}
```

### 데이터

```typescript
const { data: collection } = useQuery({
  queryKey: ['portal', 'collection', slug, lang],
  queryFn: () => portalApi.getCollection(slug),
  staleTime: 5 * 60 * 1000,
})
```

API 응답 (CollectionDetail):
```typescript
{
  slug: "greece-rome",
  title: "Greece & Rome",
  title_ko: "그리스·로마",
  description_ko: "지중해를 지배한 두 문명의 이야기",
  icon: "🏛",
  entries: [
    {
      entry_type: "shift",
      shift_id: 123,
      sort_order: 1,
      is_highlighted: true,
      note_ko: "마라톤 전투 시프트부터 시작해보세요."
      // + shift 정보 (제목, 연도, 페이지수)
    },
    {
      entry_type: "portal_item",
      portal_item: { slug: "thermopylae", title: "The Battle of Thermopylae", ... },
      sort_order: 5,
    },
    {
      entry_type: "person",
      person_id: 501,
      // + person 기본 정보 (이름, 생몰년)
    },
    ...
  ]
}
```

### entry_type별 그룹핑 + 렌더링

```typescript
// 엔트리를 타입별로 그룹핑
const shifts = entries.filter(e => e.entry_type === 'shift')
const items = entries.filter(e => e.entry_type === 'portal_item')
const persons = entries.filter(e => e.entry_type === 'person')
const events = entries.filter(e => e.entry_type === 'event')
```

| entry_type | 렌더링 | 클릭 시 |
|------------|--------|---------|
| `shift` | 시프트 카드 (title, year_range, pages, chain_type) | `portalStore.close()` → `onOpenShift(id)` |
| `portal_item` | 아티클 카드 (title, year, item_type) | `portalStore.pushDetail(slug)` (Layer 3) |
| `person` | 인물 칩 (name, birth_year ~ death_year) | `portalStore.close()` → `onPersonClick(id)` |
| `event` | 이벤트 칩 (title, year) | `portalStore.close()` → `onEventClick(id)` |

### 편집자 추천 (is_highlighted)

`is_highlighted: true`인 엔트리가 있으면 최상단에 추천 박스:

```css
.portal-collection__highlight {
  background: rgba(0, 212, 255, 0.06);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: var(--overlay-radius);
  padding: 16px 20px;
  margin-bottom: 24px;
}

.portal-collection__highlight-label {
  font-size: 11px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--chaldea-cyan);
  margin-bottom: 8px;
}
```

### 인물/이벤트 "더보기"

인물·이벤트가 많을 때 (10개 이상) 초기 8개만 표시 + "더보기" 버튼:

```typescript
const [showAllPersons, setShowAllPersons] = useState(false)
const visiblePersons = showAllPersons ? persons : persons.slice(0, 8)
```

### 시프트 카드 디자인

```css
.portal-shift-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  border: 1px solid var(--chaldea-border);
  border-radius: var(--overlay-radius);
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.portal-shift-card:hover {
  border-color: var(--chaldea-cyan);
}

.portal-shift-card__icon {
  font-size: 20px;
  color: var(--chaldea-cyan);
  flex-shrink: 0;
}

.portal-shift-card__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--chaldea-text-bright);
}

.portal-shift-card__meta {
  font-size: 12px;
  color: var(--chaldea-text-dim);
  margin-top: 3px;
}

.portal-shift-card__type {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(0, 212, 255, 0.1);
  color: var(--chaldea-cyan);
}
```

### 인물 칩 디자인

```css
.portal-person-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--chaldea-border);
  border-radius: 16px;
  background: transparent;
  color: var(--chaldea-text);
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.portal-person-chip:hover {
  border-color: var(--chaldea-gold);
  background: rgba(255, 215, 0, 0.08);
}

.portal-person-chip__years {
  font-size: 11px;
  color: var(--chaldea-text-dim);
}
```

### "이런 것도 좋아하실 걸요" 하단

컬렉션 하단에 관련 컬렉션 추천. 상세: `PORTAL_04_RECOMMENDATIONS.md`.

```typescript
// 같은 태그를 공유하는 다른 컬렉션 3개
const relatedCollections = allCollections.filter(c =>
  c.slug !== currentSlug &&
  c.tags.some(tag => currentCollection.tags.includes(tag))
).slice(0, 3)
```

---

## PortalItemDetail.tsx — 아이템 상세

### 목적

기존 TrismegistosModal의 content 뷰를 독립 중첩 모달로.
특이점/이문대/서번트/아티클 공통 상세 뷰.

### 와이어프레임

```
┌─ [← 뒤로] Singularity I: Orleans ─────── [✕] ─┐
│                                                  │
│  ⚔ SINGULARITY                                   │
│                                                  │
│  I. Orleans                                      │
│  La Ville en Flammes                             │
│  The Wicked Dragon Hundred Years' War            │
│                                                  │
│  1431 · France                                   │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │ 백년전쟁 말기, 잔 다르크가 처형당한        │  │
│  │ 실제 역사의 이면에서 특이점이 발생한다.     │  │
│  │ 프랑스 전역이 불꽃에 휩싸이고...            │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  ━━ 역사적 배경 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                  │
│  잔 다르크(1412-1431)는 프랑스의 국민 영웅으로,  │
│  백년전쟁 중 오를레앙 공방전에서 프랑스군을       │
│  승리로 이끌었다...                               │
│                                                  │
│  ━━ 관련 서번트 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐  │
│  │ Joan of Arc│ │Gilles de   │ │ Marie       │  │
│  │ Ruler ★5   │ │Rais        │ │ Antoinette  │  │
│  │            │ │ Caster ★3  │ │ Rider ★4    │  │
│  └────────────┘ └────────────┘ └────────────┘  │
│                                                  │
│  ━━ 섹션: The Real History ━━━━━━━━━━━━━━━━━━  │
│                                                  │
│  ▼ The Hundred Years' War                        │
│    [접이식 아코디언 — 클릭하면 펼침]              │
│                                                  │
│  ▼ Joan of Arc's Trial                           │
│    [접이식 아코디언]                              │
│                                                  │
│  ━━ 관련 시프트 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                  │
│  ┌─ 잔 다르크의 생애 ─────────────────────┐     │
│  │ ▶ 1412 ~ 1431 · 8 pages               │     │
│  └────────────────────────────────────────┘     │
│  ┌─ 백년전쟁 ────────────────────────────┐      │
│  │ ▶ 1337 ~ 1453 · 15 pages             │      │
│  └────────────────────────────────────────┘     │
│                                                  │
│  ─── 액션 ──────────────────────────────────── │
│                                                  │
│  [🌍 글로브에서 보기]    [▶ 시프트로 체험]       │
│                                                  │
│  ━━ 출처 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  • Wikipedia: Joan of Arc                        │
│  • Pernoud, R. "Joan of Arc: Her Story" (2000)  │
│                                                  │
│  ━━ 이런 것도 좋아하실 걸요 ━━━━━━━━━━━━━━━━━  │
│                                                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ II.Septem│ │ 서번트: │ │ 📖 중세 │           │
│  │ 로마제국│ │ 레오니다│ │ 유럽의  │           │
│  │ 특이점  │ │ 스      │ │ 전쟁    │           │
│  └─────────┘ └─────────┘ └─────────┘           │
│                                                  │
└──────────────────────────────────────────────────┘
```

### 데이터

```typescript
const { data: item } = useQuery({
  queryKey: ['portal', 'item', slug, lang],
  queryFn: () => portalApi.getItem(slug),
  staleTime: 5 * 60 * 1000,
})
```

### 타입별 색상

```typescript
const TYPE_COLORS: Record<string, string> = {
  singularity: 'var(--chaldea-orange)',
  lostbelt: 'var(--chaldea-magenta)',
  servant_column: 'var(--chaldea-gold)',
  history: 'var(--chaldea-cyan)',
  literature: 'var(--chaldea-cyan)',
  music: 'var(--chaldea-cyan)',
}

const TYPE_LABELS: Record<string, string> = {
  singularity: 'SINGULARITY',
  lostbelt: 'LOSTBELT',
  servant_column: 'SERVANT',
  history: 'HISTORY',
  literature: 'LITERATURE',
  music: 'MUSIC',
}
```

### 섹션 아코디언

`sections` JSONB의 각 항목을 접이식으로:

```typescript
const [openSections, setOpenSections] = useState<Set<number>>(new Set([0]))
// 첫 번째 섹션만 기본 열림

function toggleSection(index: number) {
  setOpenSections(prev => {
    const next = new Set(prev)
    if (next.has(index)) next.delete(index)
    else next.add(index)
    return next
  })
}
```

```css
.portal-detail__section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 0;
  cursor: pointer;
  color: var(--chaldea-text-bright);
  font-size: 15px;
  font-weight: 600;
}

.portal-detail__section-header::before {
  content: '▶';
  font-size: 10px;
  transition: transform 0.2s;
}

.portal-detail__section-header--open::before {
  transform: rotate(90deg);
}

.portal-detail__section-body {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease;
}

.portal-detail__section-body--open {
  max-height: 2000px;  /* 충분히 큰 값 */
}
```

### 관련 서번트 그리드

```css
.portal-detail__servants {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 10px;
}

.portal-servant-card {
  padding: 12px;
  border: 1px solid var(--chaldea-border);
  border-radius: var(--overlay-radius-sm);
  text-align: center;
}

.portal-servant-card__name {
  font-weight: 600;
  color: var(--chaldea-text-bright);
}

.portal-servant-card__class {
  font-size: 12px;
  color: var(--chaldea-text-dim);
}

.portal-servant-card__rarity {
  color: var(--chaldea-gold);
  font-size: 11px;
}
```

### 관련 시프트 (신규)

portal_item에 year/location이 있으면 연관 시프트 검색:

```typescript
// 같은 시대 + 지역의 시프트 찾기
const { data: relatedShifts } = useQuery({
  queryKey: ['shifts', 'related', item?.year, item?.location],
  queryFn: () => shiftsApi.list({
    year_start_lte: item!.year! + 100,
    year_end_gte: item!.year! - 100,
    limit: 5,
  }),
  enabled: !!item?.year,
  staleTime: 10 * 60 * 1000,
})
```

### CTA 버튼

```typescript
// 글로브에서 보기 — year과 location 기반
function handleViewOnGlobe() {
  if (!item?.year) return
  usePortalStore.getState().close()
  // location에서 lat/lng를 추출해야 함
  // → portal_items에 lat/lng 컬럼 추가 필요 (또는 locations 테이블 조회)
  props.onSetCurrentYear(item.year)
  // TODO: lat/lng를 events에서 찾거나 location 문자열로 geocode
}

// 시프트로 체험 — 관련 시프트의 첫 번째
function handleStartShift() {
  if (!relatedShifts?.[0]) return
  usePortalStore.getState().close()
  props.onOpenShift(relatedShifts[0].id)
}
```

### 뒤로가기

```typescript
<button
  className="portal-detail__back"
  onClick={() => usePortalStore.getState().pop()}
>
  ← {previousLayer === 'collection' ? '컬렉션으로' : '홈으로'}
</button>
```

---

## FGO 스토리라인 컬렉션 (특수 처리)

FGO 컬렉션(`fgo-main-story`)은 다른 컬렉션보다 풍부한 UI:

### 차별점

1. **순서가 중요** — 특이점 F → I → II → ... → VII → 이문대 1 → ...
2. **진행 경로 표시** — 카드 사이에 `→` 연결선
3. **카테고리 구분** — "특이점" / "이문대" / "서번트 열전" 서브 헤더
4. **도입 문구** — FGO 설명 + 역사 연결 설명

### 감지 + 분기

```typescript
// CollectionPage.tsx 내부
const isFgoCollection = collection?.collection_type === 'fgo_storyline'

if (isFgoCollection) {
  return <FgoCollectionLayout collection={collection} ... />
} else {
  return <DefaultCollectionLayout collection={collection} ... />
}
```

### FGO 컬렉션 레이아웃

```typescript
// entry의 portal_item.item_type으로 그룹핑
const singularities = entries
  .filter(e => e.portal_item?.item_type === 'singularity')
  .sort((a, b) => a.sort_order - b.sort_order)

const lostbelts = entries
  .filter(e => e.portal_item?.item_type === 'lostbelt')
  .sort((a, b) => a.sort_order - b.sort_order)

const servantColumns = entries
  .filter(e => e.portal_item?.item_type === 'servant_column')
```

---

## 모달 크기 + 위치

### Layer 2 (CollectionPage, PortalItemDetail)

```css
.portal-layer:nth-child(2) .portal-modal {
  max-width: 850px;     /* 홈보다 약간 좁게 → 깊이감 */
  max-height: 88vh;
}

.portal-layer:nth-child(3) .portal-modal {
  max-width: 800px;     /* 더 좁게 */
  max-height: 85vh;
}
```

각 레이어가 점점 작아지면서 "안으로 들어가는" 느낌.

### 닫기 버튼

```css
.portal-modal__close {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 32px;
  height: 32px;
  border: 1px solid var(--chaldea-border);
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  color: var(--chaldea-text);
  font-size: 16px;
  cursor: pointer;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.2s;
}

.portal-modal__close:hover {
  border-color: var(--chaldea-orange);
}
```

---

## 백엔드 API 변경 필요

### 1. CollectionDetail에 entry 상세 정보 포함

현재 `GET /api/v1/portal/collections/{slug}` 응답의 entries에
shift/person/event의 기본 정보가 부족할 수 있음.

**필요한 정보**:
- `shift` entry → shift의 title, title_ko, year_start, year_end, page_count, chain_type
- `person` entry → person의 name, name_ko, birth_year, death_year
- `event` entry → event의 title, title_ko, date_start

**방법 1**: API에서 joinedload로 가져오기 (현재 portal_item만 joinedload)
**방법 2**: 별도 API 호출 (비효율적)

→ 방법 1 권장. `portal.py` API에서:
```python
# 현재: joinedload(CollectionEntry.portal_item)만 있음
# 추가: joinedload(CollectionEntry.shift), .person, .event

entries = (
    db.query(CollectionEntry)
    .filter(CollectionEntry.collection_id == collection.id)
    .options(
        joinedload(CollectionEntry.portal_item),
        joinedload(CollectionEntry.shift),
        joinedload(CollectionEntry.person),
        joinedload(CollectionEntry.event),
    )
    .order_by(CollectionEntry.sort_order)
    .all()
)
```

### 2. entry_counts by type

컬렉션 목록(`GET /api/v1/portal/collections`)에서 타입별 카운트:

```python
# 응답에 추가
"entry_counts": {
    "shift": 42,
    "portal_item": 12,
    "person": 150,
    "event": 200
}
```

### 3. 관련 시프트 검색

`GET /api/v1/shifts` 에 연도 범위 필터 추가:
```
GET /api/v1/shifts?year_start_lte=-400&year_end_gte=-500&limit=5
```

---

## 관련 문서

| 문서 | 내용 |
|------|------|
| `PORTAL_01_ARCHITECTURE.md` | 중첩 모달 스택, z-index |
| `PORTAL_02_MAGAZINE_HOME.md` | 매거진 홈에서 컬렉션 진입 |
| `PORTAL_04_RECOMMENDATIONS.md` | "이런 것도 좋아하실 걸요" 로직 |
