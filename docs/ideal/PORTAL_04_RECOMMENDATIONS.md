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

## 1. 오늘의 역사 (TodayHero)

상세: `PORTAL_02_MAGAZINE_HOME.md` Section 1.

**요약**: 오늘 날짜 매칭 이벤트 → 시프트 연결 → 글로브 연결.

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

    # 1. featured shifts
    shifts = (
        db.query(HistoricalChain)
        .filter(HistoricalChain.is_featured == True)
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
            "subtitle": f"시프트 · {s.page_count} pages",
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

#### Phase 2: 시간 기반 (중기)

```
시즌/월 기반 가중치:

3월: 로마 관련 가중치 +3 (카이사르 암살 3/15)
7월: 미국/프랑스 혁명 가중치 +3 (독립선언 7/4, 바스티유 7/14)
10월: 러시아 혁명 가중치 +3 (10월 혁명)

→ 시프트/아이템의 tags에 'rome', 'revolution' 등이 있으면
  해당 월에 추천 확률 증가.
```

#### Phase 3: 열람 이력 기반 (장기)

```
유저가 그리스 관련 시프트를 3개 봤다면:
→ "그리스 더 보기" 카드 추가
→ 로마 컬렉션 추천 ("그리스를 좋아하셨으니 로마도?")
→ 페르시아 제국 시프트 추천 ("적의 시각에서")

저장: observationStore에 viewHistory 추가
→ localStorage에 최근 20개 열람 기록
→ 태그 빈도 계산 → 추천 가중치
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
is_featured = true 설정 기준:

시프트:
- page_count >= 5 (충분한 분량)
- chain_type = 'aggregate' 또는 'person_story' (가장 완성도 높음)
- 한국어 번역 있음 (narrative_ko)

포털 아이템:
- sections >= 2 (충분한 내용)
- description_ko 있음
- 관련 서번트 또는 관련 이벤트 있음

컬렉션:
- entry_count >= 5 (빈 컬렉션은 추천 X)
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

```json
{
  "today": {
    "event": {
      "id": 12345,
      "title": "February 28 Incident",
      "title_ko": "228 사건",
      "year": 1947,
      "lat": 25.033,
      "lng": 121.565,
      "description_ko": "...",
      "importance": 7
    },
    "shift_id": 456,
    "tomorrow_preview": {
      "title_ko": "3·1 운동",
      "year": 1919
    }
  },
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
  - featured 플래그 설정 (seed_portal.py 수정)
  - GET /api/v1/portal/featured 엔드포인트 구현
  - RecommendationRow 규칙 기반 (랜덤 featured)
  - RelatedContent 태그 매칭 (컬렉션 하단)

Phase 2 (중기):
  - GET /api/v1/portal/today 구현 (날짜 매칭 이벤트)
  - TodayHero 컴포넌트
  - 시즌/월 기반 가중치

Phase 3 (장기):
  - observationStore에 viewingHistory 추가
  - 태그 빈도 기반 맞춤 추천
  - 추천 문구 생성
  - 크로스 콘텐츠 디스커버리 (ShiftPanel → 포털)
```

---

## 관련 문서

| 문서 | 내용 |
|------|------|
| `PORTAL_01_ARCHITECTURE.md` | 전체 아키텍처 |
| `PORTAL_02_MAGAZINE_HOME.md` | TodayHero, RecommendationRow 배치 |
| `PORTAL_03_COLLECTIONS.md` | 컬렉션 하단 추천 위치 |
| `TRISMEGISTOS.md` | 큐레이션 시스템 원본 기획 |
