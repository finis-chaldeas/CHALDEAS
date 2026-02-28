# PORTAL 04 — 추천 엔진: "이런 것도 좋아하실 걸요"

> 아키텍처: `PORTAL_01_ARCHITECTURE.md` | 매거진 홈: `PORTAL_02_MAGAZINE_HOME.md`

---

## 왜 추천인가

"매번 같은 화면" = 재방문 동기 없음. 추천 시스템이 이걸 깨야 한다.

**목표**: 역사에 관심있는 사람이 "오, 이런 것도 있네?" 하면서 빠져드는 경험.
넷플릭스에서 "이 영화를 보셨으니 이것도 좋아하실 걸요"처럼.

---

## 추천이 등장하는 3곳

| 위치 | 섹션 | 추천 내용 |
|------|------|----------|
| 매거진 홈 상단 | TodayHero | 오늘의 역사 (날짜 매칭) |
| 매거진 홈 2번째 | RecommendationRow | 이번 주 추천 (혼합 큐레이션) |
| 컬렉션/상세 하단 | RelatedContent | "이런 것도 좋아하실 걸요" |

---

## 1. 오늘의 히어로 (TodayHero)

상세: `PORTAL_02_MAGAZINE_HOME.md` Section 1.

> **현실**: events 테이블에 `date_month`/`date_day` 없음. 전부 연도 단위.
> 따라서 "오늘의 역사" 월/일 매칭은 현재 불가.

**Phase 1**: 결정론적 일별 로테이션 (dayOfYear % poolSize)
**Phase 2**: `portal_calendar` 테이블 시딩 후 실제 날짜 매칭
**Phase 3**: events에 월/일 컬럼 추가 후 자동 매칭

---

## 2. 이번 주 추천 (RecommendationRow)

### 큐레이션 로직

#### Phase 1: 규칙 기반 (지금 구현)

```
슬롯 6개를 다음 규칙으로 채움:

1. featured 시프트 2개 (is_featured=true, 랜덤 2개)
2. featured portal_item 2개 (is_featured=true, 랜덤 2개)
3. featured 컬렉션 1개 (is_featured=true, 랜덤 1개)
4. 나머지 1개: 위에서 안 뽑힌 것 중 랜덤
```

**백엔드 구현**:

```python
# GET /api/v1/portal/featured 의 recommendations 필드

def get_recommendations(db: Session, limit: int = 6):
    results = []

    # 1. 고중요도 시프트 (globe_importance >= 4, 403개 풀)
    # ⚠ historical_chains에 is_featured 컬럼 없음.
    #    globe_importance로 대체 (5=174개, 4=229개).
    shifts = (
        db.query(HistoricalChain)
        .filter(HistoricalChain.globe_importance >= 4)
        .order_by(func.random())
        .limit(2)
        .all()
    )
    for s in shifts:
        results.append({
            "type": "shift",
            "id": s.id,
            "title": s.title,
            "title_ko": s.title_ko,
            "subtitle": f"시프트 · {s.segment_count} pages",
            "chain_type": s.chain_type,
        })

    # 2. featured portal items
    items = (
        db.query(PortalItem)
        .filter(PortalItem.is_featured == True)
        .order_by(func.random())
        .limit(2)
        .all()
    )
    for item in items:
        type_label = {
            'singularity': '특이점', 'lostbelt': '이문대',
            'servant_column': '서번트 컬럼',
            'history': '역사', 'literature': '문학', 'music': '음악',
        }.get(item.item_type, '아티클')
        results.append({
            "type": "portal_item",
            "slug": item.slug,
            "title": item.title,
            "title_ko": item.title_ko,
            "subtitle": type_label,
            "item_type": item.item_type,
        })

    # 3. featured collection
    coll = (
        db.query(Collection)
        .filter(Collection.is_featured == True)
        .order_by(func.random())
        .first()
    )
    if coll:
        entry_count = db.query(CollectionEntry).filter(
            CollectionEntry.collection_id == coll.id
        ).count()
        results.append({
            "type": "collection",
            "slug": coll.slug,
            "title": coll.title,
            "title_ko": coll.title_ko,
            "subtitle": f"컬렉션 · {entry_count} 항목",
            "icon": coll.icon,
        })

    # shuffle to mix types
    random.shuffle(results)
    return results[:limit]
```

#### Phase 2: 월별 테마 가중치 (중기)

`portal_calendar` 테이블이 없어도 작동하는 하드코딩 방식.
collections/items의 `tags` 또는 `region` 필드로 매칭.

```python
# 월별 가중 태그 (하드코딩, 추후 DB로 이동 가능)
MONTHLY_THEMES: dict[int, list[tuple[str, int]]] = {
    1:  [("new_year", 3), ("japan", 2), ("calendar", 2)],
    2:  [("revolution", 3), ("independence", 2)],
    3:  [("rome", 3), ("ides", 2), ("korea", 2)],       # 카이사르 3/15, 3·1운동
    4:  [("exploration", 3), ("science", 2)],
    5:  [("war", 3), ("europe", 2)],                     # 5월 전승기념일
    6:  [("normandy", 3), ("war", 2), ("d-day", 3)],
    7:  [("revolution", 4), ("america", 3), ("france", 3)], # 7/4, 7/14
    8:  [("war", 3), ("japan", 3), ("atomic", 3)],       # 8/15 종전
    9:  [("empire", 2), ("byzantine", 2)],
    10: [("revolution", 4), ("russia", 3)],              # 10월 혁명
    11: [("armistice", 3), ("war", 2)],                  # 11/11 정전
    12: [("religion", 2), ("medieval", 2), ("calendar", 2)],
}

def apply_monthly_weight(item_tags: list[str], month: int) -> int:
    """월별 테마와 아이템 태그의 매칭 가중치 계산."""
    themes = MONTHLY_THEMES.get(month, [])
    weight = 0
    for theme_tag, theme_weight in themes:
        if theme_tag in item_tags:
            weight += theme_weight
    return weight
```

Phase 1 로직에 가중치 추가:
```python
def get_recommendations_v2(db, month: int, limit: int = 6):
    candidates = get_all_featured_candidates(db)  # shifts + items + collections

    for c in candidates:
        c["score"] = c.get("base_score", 1)
        c["score"] += apply_monthly_weight(c.get("tags", []), month)

    candidates.sort(key=lambda x: x["score"], reverse=True)
    # 상위 후보에서 랜덤 샘플 (항상 1등만 보여주면 지루)
    top_pool = candidates[:20]
    random.shuffle(top_pool)
    return top_pool[:limit]
```

#### Phase 3: 열람 이력 기반 (장기)

**localStorage 구조**:
```typescript
// localStorage key: 'chaldeas_viewing_history'
interface StoredViewingHistory {
  version: 1
  entries: Array<{
    type: 'shift' | 'portal_item' | 'collection' | 'event' | 'person'
    id: string | number
    tags: string[]             // 해당 콘텐츠의 태그
    ts: number                 // Unix timestamp (ms)
  }>
  // 최대 100개, FIFO
}
```

**태그 빈도 → 추천 가중치**:
```typescript
function getPersonalizedRecommendations(
  candidates: RecommendationCandidate[],
  history: StoredViewingHistory
): RecommendationCandidate[] {
  // 1. 최근 50개 항목에서 태그 빈도 계산
  const tagCounts: Record<string, number> = {}
  const recent = history.entries.slice(-50)
  for (const entry of recent) {
    for (const tag of entry.tags) {
      tagCounts[tag] = (tagCounts[tag] || 0) + 1
    }
  }

  // 2. 이미 본 것 제외
  const seenIds = new Set(history.entries.map(e => `${e.type}:${e.id}`))

  // 3. 후보별 맞춤 스코어
  return candidates
    .filter(c => !seenIds.has(`${c.type}:${c.id}`))
    .map(c => {
      let score = c.baseScore || 1
      for (const tag of c.tags || []) {
        score += (tagCounts[tag] || 0) * 2  // 관심 태그 가중치
      }
      return { ...c, personalizedScore: score }
    })
    .sort((a, b) => b.personalizedScore - a.personalizedScore)
}
```

**"연관 영역" 추천** (같은 태그만 반복하지 않기 위해):
```typescript
// 그리스를 5번 봤으면 → 페르시아(적의 시각), 로마(후속 문명) 추천
const ADJACENT_TAGS: Record<string, string[]> = {
  'greece': ['persia', 'rome', 'mediterranean', 'philosophy'],
  'rome': ['greece', 'carthage', 'gaul', 'byzantine'],
  'japan': ['korea', 'china', 'pacific'],
  'war': ['diplomacy', 'revolution', 'empire'],
  'fgo': ['fate', 'servant', 'singularity'],
}

function getAdjacentRecommendations(topTags: string[]): string[] {
  const adjacent = new Set<string>()
  for (const tag of topTags.slice(0, 5)) {
    for (const adj of ADJACENT_TAGS[tag] || []) {
      adjacent.add(adj)
    }
  }
  return [...adjacent]
}
```

---

## 3. "이런 것도 좋아하실 걸요" (RelatedContent)

컬렉션 페이지 하단과 아이템 상세 하단에 표시.

### 컬렉션 하단의 추천

**로직**: 현재 컬렉션의 `tags`와 겹치는 다른 컬렉션.

```typescript
function getRelatedCollections(
  currentSlug: string,
  currentTags: string[],
  allCollections: CollectionSummary[]
): CollectionSummary[] {
  return allCollections
    .filter(c => c.slug !== currentSlug)
    .map(c => ({
      ...c,
      relevance: c.tags.filter(t => currentTags.includes(t)).length,
    }))
    .filter(c => c.relevance > 0)
    .sort((a, b) => b.relevance - a.relevance)
    .slice(0, 3)
}
```

**예시**:

| 현재 컬렉션 | tags | 추천 컬렉션 | 이유 |
|------------|------|------------|------|
| 그리스·로마 | greece, rome, ancient, mediterranean | 전쟁사 | ancient, war 겹침 |
| 그리스·로마 | greece, rome, ancient, mediterranean | 철학사 | greece, ancient 겹침 |
| FGO 메인스토리 | fgo, singularity, lostbelt | 그리스·로마 | babylonia, olympus 연결 |

### 아이템 상세 하단의 추천

**로직**: 같은 `item_type`의 다른 아이템 + 같은 시대의 다른 아이템.

```typescript
function getRelatedItems(
  currentSlug: string,
  currentItem: PortalItem,
  allItems: PortalItem[]
): PortalItem[] {
  const results: Array<PortalItem & { score: number }> = []

  for (const item of allItems) {
    if (item.slug === currentSlug) continue

    let score = 0

    // 같은 타입이면 +2
    if (item.item_type === currentItem.item_type) score += 2

    // 같은 시대 (±200년)이면 +3
    if (item.year && currentItem.year) {
      const diff = Math.abs(item.year - currentItem.year)
      if (diff <= 200) score += 3
      else if (diff <= 500) score += 1
    }

    // 같은 location 포함이면 +2
    if (item.location && currentItem.location) {
      const overlap = item.location.toLowerCase().includes(
        currentItem.location.toLowerCase().split(',')[0]
      )
      if (overlap) score += 2
    }

    if (score > 0) results.push({ ...item, score })
  }

  return results
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)
}
```

**예시**:

| 현재 아이템 | 추천 1 | 추천 2 | 추천 3 |
|------------|--------|--------|--------|
| Singularity I: Orleans (1431, France) | Singularity II: Septem (same type +2) | 잔 다르크 서번트 컬럼 (같은 시대 +3) | 백년전쟁 아티클 (같은 시대+지역 +5) |
| Gilgamesh 서번트 컬럼 (-2655, Mesopotamia) | Babylonia 특이점 (같은 시대+지역 +5) | Leonidas 서번트 컬럼 (같은 타입 +2) | 알렉산더 서번트 컬럼 (같은 타입 +2) |

---

## 4. 크로스 콘텐츠 디스커버리

### 시프트 → 포털 연결

시프트를 다 보고 나면 ShiftPanel 마지막 페이지 하단에:

```
━━ 더 알아보기 ━━━━━━━━━━━━━━━━━━━━━━━━━━━

이 시프트와 관련된 콘텐츠:

[📖 그리스-페르시아 전쟁 아티클]  → 포털 열기
[🏛 그리스·로마 컬렉션]         → 포털 열기
[👤 레오니다스 상세]             → NarrativePanel
```

**구현**: ShiftPanel 마지막 페이지에 관련 콘텐츠 섹션 추가.
시프트의 tags/키워드로 portal_items 검색.

### NarrativePanel → 포털 연결

EventNarrativeCard 하단에:

```
이 사건이 포함된 컬렉션:
[🏛 그리스·로마]  [🗡 전쟁사]
```

**구현**: 이벤트 ID로 collection_entries 검색 → 소속 컬렉션 표시.

### 글로브 마커 → 포털 연결

(미래) 글로브에서 마커 클릭 → NarrativePanel에 "포털에서 더 보기" 링크.

---

## 5. 맞춤 추천 시스템 (Phase 3)

### 열람 이력 추적

```typescript
// observationStore.ts에 추가

interface ViewingHistory {
  type: 'shift' | 'portal_item' | 'collection' | 'event' | 'person'
  id: string | number
  tags: string[]
  timestamp: number
}

interface ObservationStore {
  // 기존 필드...

  // 추천용 이력
  viewingHistory: ViewingHistory[]
  addView: (view: ViewingHistory) => void

  // 태그 빈도
  getTopTags: (limit?: number) => Array<{ tag: string; count: number }>

  // 추천
  getPersonalizedWeight: (tags: string[]) => number
}
```

### 태그 빈도 계산

```typescript
getTopTags: (limit = 10) => {
  const tagCounts: Record<string, number> = {}
  const history = get().viewingHistory

  // 최근 50개만 (너무 오래된 건 가중치 감소)
  const recent = history.slice(-50)

  for (const view of recent) {
    for (const tag of view.tags) {
      tagCounts[tag] = (tagCounts[tag] || 0) + 1
    }
  }

  return Object.entries(tagCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, limit)
    .map(([tag, count]) => ({ tag, count }))
},
```

### 추천 가중치

```typescript
getPersonalizedWeight: (itemTags: string[]) => {
  const topTags = get().getTopTags(20)
  const tagMap = new Map(topTags.map(t => [t.tag, t.count]))

  let weight = 0
  for (const tag of itemTags) {
    weight += tagMap.get(tag) || 0
  }
  return weight
},
```

### 추천 문구 생성

| 유저 프로필 | 문구 |
|------------|------|
| greece 5회, rome 3회 | "고대 지중해에 관심이 많으시네요. 페르시아 제국도 한번 보세요." |
| war 4회, battle 3회 | "전쟁사를 좋아하시는군요. 나폴레옹 전쟁 시프트 어때요?" |
| fgo 6회 | "FGO 팬이시군요! 아직 안 본 특이점이 있어요." |

**Phase 3에서 구현** — 지금은 규칙 기반으로 충분.

---

## 6. featured 마킹 전략

### 어떤 콘텐츠를 featured로?

```
포털 아이템 (portal_items.is_featured):
- sections >= 2 (충분한 내용)
- description_ko 있음
- 관련 서번트 또는 관련 이벤트 있음
- 현재: 15/34개 featured

시프트 (featured 컬럼 없음 → globe_importance로 대체):
- globe_importance = 5 → 최상위 추천 풀 (174개)
- globe_importance = 4 → 확장 풀 (229개, 합계 403개)
- segment_count >= 5 (충분한 분량)
- chain_type = 'aggregate' 또는 'person_story'

컬렉션 (collections.is_featured):
- entry_count >= 5 (빈 컬렉션은 추천 X)
- 현재: 3개 모두 entries < 5 → Phase 2에서 엔트리 시딩 후 featured 설정
```

### 시딩 스크립트에서 featured 설정

```python
# seed_portal.py에 추가
FEATURED_ITEMS = [
    'singularity-f',     # Fuyuki (입문용)
    'singularity-vii',   # Babylonia (가장 인기)
    'lostbelt-5',        # Olympus (그리스 연결)
    'servant-gilgamesh', # 가장 유명한 서번트
    'history-crusades',  # 대중적 주제
]

for slug in FEATURED_ITEMS:
    db.query(PortalItem).filter(PortalItem.slug == slug).update(
        {PortalItem.is_featured: True}
    )
```

---

## 7. API 응답 설계

### GET /api/v1/portal/featured (통합)

> Phase 1에서는 `today`가 없음 (프론트엔드에서 로테이션으로 처리).
> Phase 2에서 `portal_calendar` 시딩 후 `today` 필드 추가.

```json
{
  "recommendations": [
    {
      "type": "shift",
      "id": 123,
      "title": "Greek-Persian Wars",
      "title_ko": "그리스-페르시아 전쟁",
      "subtitle": "시프트 · 7 pages",
      "chain_type": "aggregate"
    },
    {
      "type": "portal_item",
      "slug": "servant-gilgamesh",
      "title": "Gilgamesh",
      "title_ko": "길가메시",
      "subtitle": "서번트 컬럼",
      "item_type": "servant_column"
    },
    {
      "type": "collection",
      "slug": "greece-rome",
      "title": "Greece & Rome",
      "title_ko": "그리스·로마",
      "subtitle": "컬렉션 · 42 항목",
      "icon": "🏛"
    }
  ],
  "featured_items": [
    { "slug": "singularity-f", "title": "...", ... },
    { "slug": "singularity-vii", "title": "...", ... }
  ]
}
```

---

## 8. 와이어프레임: "이런 것도 좋아하실 걸요" 섹션

```
━━ 이런 것도 좋아하실 걸요 ━━━━━━━━━━━━━━━━━━━━━

  ┌─────────┐ ┌─────────┐ ┌─────────┐
  │ ▶ 로마  │ │ 🏛 전쟁 │ │ 📖 스파 │
  │ 공화정  │ │ 사      │ │ 르타의  │
  │ 의 몰락 │ │ 컬렉션  │ │ 사회    │
  │         │ │         │ │         │
  │ 시프트  │ │ 67 시프트│ │ 아티클  │
  │ 9 pages │ │ 8 아티클 │ │         │
  └─────────┘ └─────────┘ └─────────┘

  이전에 본 것: 그리스-페르시아 전쟁 시프트,
  그리스·로마 컬렉션 → "고대 지중해"에 관심 있으시네요!
```

### CSS

```css
.portal-related {
  padding: 24px;
  border-top: 1px solid var(--chaldea-border);
  margin-top: 24px;
}

.portal-related__title {
  font-size: 13px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--chaldea-text-dim);
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.portal-related__title::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--chaldea-border);
}

.portal-related__cards {
  display: flex;
  gap: 12px;
}

.portal-related__reason {
  font-size: 12px;
  color: var(--chaldea-text-dim);
  font-style: italic;
  margin-top: 12px;
}
```

---

## 구현 순서

```
Phase 1 (지금):
  - featured 플래그 설정 (portal_items.is_featured = true, 15개)
  - shifts: globe_importance >= 4 을 featured 대체로 사용 (403개 풀)
  - GET /api/v1/portal/featured 엔드포인트 확장 (recommendations 필드)
  - TodayHero: dayOfYear % poolSize 로테이션 (프론트엔드 계산)
  - RecommendationRow: featured pool에서 랜덤 6개
  - RelatedContent: 태그 매칭 (컬렉션/아이템 하단)

Phase 2 (중기):
  - portal_calendar 테이블 생성 + 시딩 (AI 배치 또는 수동)
  - GET /api/v1/portal/today?month=N&day=N 구현
  - TodayHero: 실제 날짜 매칭 (portal_calendar에서)
  - 월별 테마 가중치 (MONTHLY_THEMES 딕셔너리)
  - 컬렉션/시프트에 tags 시딩 (region, era, theme 등)

Phase 3 (장기):
  - localStorage에 viewingHistory 저장 (최대 100개)
  - 태그 빈도 기반 맞춤 추천
  - 연관 영역 추천 (ADJACENT_TAGS)
  - 추천 문구 생성
  - 크로스 콘텐츠 디스커버리 (ShiftPanel → 포털)
```

---

## 현재 데이터 현황 (2026-02-28)

| 풀 | 수량 | 비고 |
|----|------|------|
| portal_items is_featured=true | 15개 | singularity(8), lostbelt(7) 위주 |
| shifts globe_importance=5 | 174개 | 대부분 aggregate 타입 |
| shifts globe_importance=4 | 229개 | 합계 403개 |
| collections | 3개 | 엔트리 부족 (최대 5개) |
| portal_calendar | 0개 | Phase 2에서 시딩 예정 |
| events date_month/day | 없음 | date_start는 연도 정수만 |

---

## 관련 문서

| 문서 | 내용 |
|------|------|
| `PORTAL_01_ARCHITECTURE.md` | 전체 아키텍처, 글로브 연결 |
| `PORTAL_02_MAGAZINE_HOME.md` | TodayHero, RecommendationRow 배치 |
| `PORTAL_03_COLLECTIONS.md` | 컬렉션 하단 추천 위치 |
| `PORTAL_05_ARTICLES.md` | 엔티티 링크 시스템 |
| `TRISMEGISTOS.md` | 큐레이션 시스템 원본 기획 |
