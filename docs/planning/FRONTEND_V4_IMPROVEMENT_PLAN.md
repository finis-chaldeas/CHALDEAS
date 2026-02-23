# V4 Frontend Improvement Plan — Backend 100% 활용

## 현재 상태

| 지표 | 값 |
|------|-----|
| 백엔드 API 엔드포인트 | 80+ (16개 파일) |
| V4에서 사용 중 | 11개 (~25%) |
| 미사용 API | ~60개 (75%) |
| 컴포넌트 수 | 6개 (Globe, Timeline, NarrativeCard, WorldBriefing, Landing, DeepRead) |

## 미사용 백엔드 API 분석

### 완전 미사용 (0% 활용)

| API 그룹 | 엔드포인트 수 | 데이터 가치 |
|----------|-------------|------------|
| **Search** | 6개 (basic, full, advanced, date-location, logs, master) | 핵심 — 탐색의 기본 |
| **Chat/Agent** | 4개 (chat, observe, rag, agent) | 핵심 — AI 지능형 탐색 |
| **Story** | 2개 (person story, check) | 높음 — 인물 서사 시각화 |
| **Sources** | 5개 (list, detail, persons, mentions, wiki) | 높음 — 출처 추적 |
| **Persons Network** | 1개 (network graph data) | 높음 — 관계 시각화 |
| **Person Relations** | 1개 (strength-ranked relations) | 높음 — 인물 연결 |
| **Person Properties** | 1개 (Wikidata properties) | 중간 — 세부 정보 |
| **Person Wikipedia** | 1개 (Wikipedia 콘텐츠) | 중간 — 외부 지식 |
| **Person Sources** | 1개 (인물 관련 서적) | 중간 — 출처 추적 |
| **Featured** | 3개 (persons, random, servants) | 중간 — 발견 경험 |
| **Locations** | 3개 (list, detail, stats) | 중간 — 공간 탐색 |
| **Categories** | 1개 (taxonomy tree) | 중간 — 필터링 |
| **Servants** | 5개 (list, detail, stats, by-person, comparison) | 낮음(FGO 팬용) |
| **Showcases** | 9개 (singularities, lostbelts, history, etc.) | 낮음(FGO 팬용) |
| **Threads** | 2개 (person event chains) | 높음 — 인과 스레드 |
| **Reports** | 2개 (submit, stats) | 낮음 — 품질 관리 |
| **Properties** | 1개 (generic entity properties) | 중간 |

### 부분 사용 (일부만 활용)

| API 그룹 | 사용 중 | 미사용 |
|----------|---------|--------|
| **Events** | get, getMap, getRelationships | list, stats, hierarchy, aggregates, children, locations |
| **Persons** | get, getNarrative, getFlow | list, network, events, relations, sources, wikipedia, properties |
| **Timeline** | getPeriodDetail | periods list, period events, period persons, feedback |
| **Feed** | get | (파라미터 미활용: viewport 필터링) |

---

## 개선 계획

### Phase 1: 핵심 탐색 경험 (Critical Path)

> 글로브 + 서사 + 검색을 하나의 매끄러운 흐름으로 연결

#### 1-1. 글로벌 검색 바 (CommandBar)

**새 컴포넌트**: `SearchBar.tsx`
**사용 API**: `GET /search?q=...`, `GET /search/basic?q=...`
**위치**: 화면 상단 중앙, Ctrl+K로 토글

```
┌─────────────────────────────────────────┐
│  🔍 Search events, persons, places...   │
│─────────────────────────────────────────│
│  Events:                                │
│    ▸ Battle of Thermopylae (480 BCE)    │
│    ▸ Thermopylae Pass fortification     │
│  Persons:                               │
│    ▸ Leonidas I (540-480 BCE)           │
│    ▸ Xerxes I (519-465 BCE)            │
│  Locations:                             │
│    ▸ Thermopylae, Greece               │
└─────────────────────────────────────────┘
```

- 검색 결과 클릭 → 이벤트면 Globe flyTo + NarrativeCard, 인물이면 PersonCard
- 타입별 필터 탭 (All / Events / Persons / Locations)
- 디바운스 300ms, 최소 2글자

**사용할 API 함수 추가**:
```typescript
searchApi: {
  search: (q, limit?) => api.get('/search', { params: { q, limit } }),
  basic: (q, limit?) => api.get('/search/basic', { params: { q, limit } }),
  dateLocation: (params) => api.get('/search/date-location', { params }),
}
```

#### 1-2. 인물 관계 네트워크 (PersonNetwork)

**새 컴포넌트**: `PersonNetwork.tsx`
**사용 API**: `GET /persons/{id}/relations`, `GET /persons/network`
**위치**: NarrativeCard 내 탭 또는 별도 패널

선택된 인물 중심의 관계도:
```
                    [Aristotle]
                   ↗    |    ↘
          [Plato] ←─── [Alexander] ───→ [Darius III]
             ↓                              ↓
         [Socrates]                    [Achaemenid Empire]
```

- 강도(strength)에 따른 선 두께
- 관계 유형별 색상 (teacher/student, ally, enemy, family)
- 노드 클릭 → 인물 전환
- Canvas 기반 (react-force-graph 또는 d3-force)

**사용할 API 함수 추가**:
```typescript
personsApi: {
  getRelations: (id, params?) => api.get(`/persons/${id}/relations`, { params }),
  getNetwork: (params?) => api.get('/persons/network', { params }),
}
```

#### 1-3. 인물 상세 강화 (PersonCard Enhancement)

**기존 수정**: `NarrativeCard.tsx` PersonNarrativeCard 부분
**사용 API**:
- `GET /persons/{id}/relations` — 관련 인물
- `GET /persons/{id}/sources` — 출처 서적
- `GET /persons/{id}/properties` — Wikidata 속성
- `GET /persons/{id}/wikipedia` — Wikipedia 본문
- `GET /story/person/{id}` — 인생 서사 노드맵

현재 인물 카드에 추가할 섹션:

```
┌─ Person: Alexander the Great ──────────┐
│                                         │
│  Narrative (기존)                        │
│  Significance (기존)                     │
│  Life Events (기존 flow)                 │
│                                         │
│  ─── 새로 추가 ───                       │
│                                         │
│  📊 Quick Facts (properties)             │
│  ├ Occupation: King, Military Commander  │
│  ├ Country: Macedonia                    │
│  ├ Education: Aristotle (mentor)         │
│  └ Awards: Pharaoh of Egypt             │
│                                         │
│  🔗 Related Persons (relations)          │
│  ├ Aristotle (teacher, strength: 0.9)    │
│  ├ Darius III (enemy, strength: 0.85)    │
│  └ Ptolemy I (subordinate, 0.7)          │
│    └ [View Full Network →]               │
│                                         │
│  📚 Mentioned In (sources)               │
│  ├ The Histories - Herodotus            │
│  ├ Anabasis of Alexander - Arrian       │
│  └ 12 more sources...                    │
│                                         │
│  📖 Wikipedia Summary (wikipedia)        │
│  └ [Read Full Article →]                 │
│                                         │
└─────────────────────────────────────────┘
```

#### 1-4. 이벤트 계층 구조 (EventHierarchy)

**새 컴포넌트**: `EventHierarchy.tsx` (NarrativeCard 내 섹션)
**사용 API**: `GET /events/hierarchy?root_id=...`, `GET /events/{id}/children`

예: "Peloponnesian War" 선택 시:
```
▼ Peloponnesian War (431-404 BCE)
  ├─ Archidamian War (431-421 BCE)
  │   ├─ Siege of Plataea (429 BCE)
  │   ├─ Battle of Sphacteria (425 BCE)
  │   └─ Peace of Nicias (421 BCE)
  └─ Sicilian Expedition (415-413 BCE)
      ├─ Siege of Syracuse (414 BCE)
      └─ Destruction of Athenian Fleet (413 BCE)
```

- 트리 노드 클릭 → 해당 이벤트로 이동
- 접기/펼치기
- 현재 선택된 이벤트 하이라이트

#### 1-5. Landing 페이지 개편

**기존 수정**: `Landing.tsx`
**사용 API**:
- `GET /featured/persons?era=...` — 시대별 추천 인물
- `GET /featured/random` — 랜덤 인물
- `GET /events/stats` — 전체 통계

```
┌─────────────────────────────────────────────┐
│                  CHALDEAS                    │
│        World-Centric Knowledge System        │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │  🔍 Search history...                │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  📊 3,856 Events · 2,100 Persons · 45 Eras  │
│                                              │
│  Featured Figures                             │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│  │Caesar│ │Muham-│ │Confu-│ │Cleop-│       │
│  │      │ │ mad  │ │cius  │ │atra  │       │
│  │44 BCE│ │570CE │ │551BCE│ │69 BCE│       │
│  └──────┘ └──────┘ └──────┘ └──────┘       │
│                                              │
│  [🌍 Explore Globe]    [📖 Read Stories]     │
│                                              │
│  Random Discovery: "Did you know..."         │
│  → Hypatia of Alexandria (360-415 CE)        │
│                                              │
└─────────────────────────────────────────────┘
```

---

### Phase 2: 공간-시간 탐색 강화

#### 2-1. Globe 필터링 시스템

**기존 수정**: `Globe.tsx`
**사용 API**:
- `GET /events?category=...&importance_min=...` — 카테고리/중요도 필터
- `GET /categories` — 카테고리 트리
- `GET /search/date-location` — 지점 주변 검색
- `GET /events/{id}/locations` — 이벤트 관련 장소 전체 (aggregate)
- `GET /locations?lat_min=...&lng_max=...` — 뷰포트 내 장소

Globe 좌측에 필터 패널:
```
┌─ Filters ─────────┐
│ Category:          │
│ ☑ Battle/War       │
│ ☑ Politics         │
│ ☐ Religion         │
│ ☐ Philosophy       │
│ ☑ Science          │
│                    │
│ Importance: ≥3 ━━━ │
│                    │
│ Show:              │
│ ◉ Events           │
│ ○ Persons          │
│ ○ Both             │
│                    │
│ [Reset Filters]    │
└────────────────────┘
```

#### 2-2. 뷰포트 연동 Feed

**기존 수정**: Globe.tsx + 새 컴포넌트 `ViewportFeed.tsx`
**사용 API**: `GET /feed?lat_min=...&lat_max=...&lng_min=...&lng_max=...&year_start=...&year_end=...`

지구본 회전/줌 시 현재 보이는 영역의 이벤트+인물 피드가 사이드에 자동 업데이트:
```
┌─ In View ────────────────────┐
│ 480 BCE · Eastern Med        │
│                              │
│ ⚔ Battle of Thermopylae     │
│   480 BCE · Importance 5     │
│                              │
│ 👤 Leonidas I                │
│   540-480 BCE · Spartan King │
│                              │
│ ⚔ Battle of Salamis          │
│   480 BCE · Importance 5     │
│                              │
│ 👤 Xerxes I                  │
│   519-465 BCE · Persian King │
│                              │
│ 12 events · 8 persons in view│
└──────────────────────────────┘
```

#### 2-3. 타임라인 기간 상세 (Period Drawer)

**새 컴포넌트**: `PeriodDrawer.tsx`
**사용 API**:
- `GET /timeline/periods` — 기간 목록
- `GET /timeline/periods/{start}/events` — 기간 내 이벤트
- `GET /timeline/periods/{start}/persons` — 기간 내 인물

현재 WorldBriefing은 period_narratives만 표시.
PeriodDrawer는 해당 기간의 **실제 이벤트/인물 목록**을 보여줌:

```
┌─ 480-530 BCE ───────────────────────────┐
│ The Classical Age of Greece              │
│ "Democracy, philosophy, and Persian..."  │
│                                          │
│ Top Events                               │
│ 1. Battle of Marathon (490 BCE) ⭐⭐⭐⭐⭐ │
│ 2. Battle of Thermopylae (480 BCE) ⭐⭐⭐⭐│
│ 3. Battle of Salamis (480 BCE) ⭐⭐⭐⭐   │
│ 4. Founding of Delian League (478 BCE)  │
│                                          │
│ Key Figures                              │
│ 1. Socrates (470-399 BCE)               │
│ 2. Pericles (495-429 BCE)               │
│ 3. Herodotus (484-425 BCE)              │
│                                          │
│ Regional Breakdown                       │
│ ├ Europe: Greek city-states flourish     │
│ ├ Near East: Achaemenid expansion halted │
│ └ East Asia: Confucius & Warring States  │
└──────────────────────────────────────────┘
```

#### 2-4. 인물 스레드 (PersonThreads)

**새 컴포넌트**: `PersonThread.tsx`
**사용 API**: `GET /threads?year_start=...&year_end=...`, `GET /threads/{person_id}/events`

인물의 생애를 따라가는 이벤트 체인:
```
Alexander the Great — Life Thread
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  356 BCE  Born in Pella, Macedonia
     │
  343 BCE  Tutored by Aristotle
     │
  336 BCE  Becomes King of Macedonia
     │
  334 BCE  Battle of Granicus ──→ [Globe: fly to Turkey]
     │
  333 BCE  Battle of Issus ──→ [Globe: fly to Issus]
     │
  331 BCE  Battle of Gaugamela ──→ [Globe: fly to Iraq]
     │
  326 BCE  Battle of Hydaspes ──→ [Globe: fly to India]
     │
  323 BCE  Death in Babylon ──→ [Globe: fly to Baghdad]
```

- 각 노드 클릭 → Globe가 해당 장소로 flyTo
- 타임라인도 해당 연도로 이동
- 여러 인물의 스레드를 동시에 표시 가능

---

### Phase 3: AI 지능형 탐색

#### 3-1. AI 대화 인터페이스 (ChatPanel)

**새 컴포넌트**: `ChatPanel.tsx`
**사용 API**:
- `POST /chat/agent` — 지능형 에이전트 (메인)
- `POST /chat/rag` — RAG 파이프라인 (폴백)
- `POST /chat/observe` — 의도 감지 (프리뷰)

```
┌─ Ask CHALDEAS ──────────────────────────┐
│                                          │
│ 🤖 Ask me anything about world history   │
│                                          │
│ You: "Why did Rome fall?"                │
│                                          │
│ CHALDEAS:                                │
│ The fall of the Western Roman Empire     │
│ was a gradual process spanning...        │
│                                          │
│ 📌 Related Events:                       │
│ • Sack of Rome (410 CE) [→ Globe]        │
│ • Fall of Western Rome (476 CE) [→ Globe]│
│                                          │
│ 📚 Sources:                              │
│ • The Decline and Fall - Gibbon          │
│ • The History of Rome - Livy            │
│                                          │
│ Confidence: 0.87                         │
│                                          │
│ ┌──────────────────────────────────────┐ │
│ │ Type your question...                │ │
│ └──────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

- 응답 내 이벤트/인물 클릭 → Globe flyTo + NarrativeCard
- 검색 결과 시각화 (Globe에 하이라이트)
- 한국어/영어 지원 (language 파라미터)

#### 3-2. 검색 로그 & 히스토리

**새 컴포넌트**: `SearchHistory.tsx`
**사용 API**:
- `GET /search/logs/public` — 공개 검색 로그
- `GET /search/master/{number}/history` — 마스터 검색 기록

최근 검색 기록 + 다른 사용자들의 인기 검색어:
```
┌─ Recent Searches ────────────┐
│ 🕐 Battle of Thermopylae     │
│ 🕐 Alexander the Great       │
│ 🕐 Fall of Rome              │
│                              │
│ 🔥 Popular on CHALDEAS       │
│ • "Silk Road trade routes"   │
│ • "Renaissance artists"     │
│ • "Mongol Empire expansion" │
└──────────────────────────────┘
```

---

### Phase 4: 출처 & 서적 탐색

#### 4-1. 출처 브라우저 (SourceBrowser)

**새 컴포넌트**: `SourceBrowser.tsx`
**사용 API**:
- `GET /sources` — 출처 목록
- `GET /sources/{id}` — 출처 상세
- `GET /sources/{id}/persons` — 출처에 등장하는 인물
- `GET /sources/{id}/mentions` — 텍스트 멘션
- `GET /sources/wiki/{id}` — Wikipedia 원문

```
┌─ Sources ────────────────────────────────┐
│                                          │
│ 📚 The Histories — Herodotus             │
│    Type: gutenberg                       │
│    Mentions: 145 entities                │
│                                          │
│ Persons Mentioned:                       │
│ ├ Xerxes I (23 mentions)                 │
│ ├ Leonidas I (18 mentions)               │
│ ├ Darius I (15 mentions)                 │
│ └ 42 more...                             │
│                                          │
│ Sample Mentions:                         │
│ "...Xerxes, having thus spoken,          │
│  passed over the Hellespont..."          │
│  — Book VII, Chapter 56                  │
│                                          │
│ [📖 Read Full Text]                      │
└──────────────────────────────────────────┘
```

#### 4-2. 인물-서적 연결 (NarrativeCard 내)

**기존 수정**: `NarrativeCard.tsx`
**사용 API**: `GET /persons/{id}/sources?include_contexts=true`

인물 카드에서 "이 인물이 언급된 서적"과 구체적 인용문 표시.

---

### Phase 5: 장소 & 지리 탐색

#### 5-1. 장소 상세 패널 (LocationDetail)

**새 컴포넌트**: `LocationDetail.tsx`
**사용 API**:
- `GET /locations/{id}` — 장소 상세 (names, territories, events)

```
┌─ Athens, Greece ─────────────────────────┐
│ 📍 37.97°N, 23.72°E                      │
│                                          │
│ Historical Names:                        │
│ ├ Ἀθῆναι (Ancient Greek)                 │
│ ├ 아테네 (Korean)                         │
│ └ アテネ (Japanese)                       │
│                                          │
│ Political History:                       │
│ ├ City-state (-508 to -338 BCE)          │
│ ├ Macedonian rule (-338 to -146 BCE)     │
│ ├ Roman province (-146 BCE to 395 CE)    │
│ └ ...                                    │
│                                          │
│ Events at this location:                 │
│ ├ Birth of Democracy (-508 BCE)          │
│ ├ Golden Age of Pericles (-461 BCE)      │
│ ├ Trial of Socrates (-399 BCE)           │
│ └ 24 more events...                      │
└──────────────────────────────────────────┘
```

- Globe 마커 옆에 장소 이름 표시
- 장소 클릭 → 해당 장소의 이벤트 목록

#### 5-2. 지도 위 장소 검색 (DateLocationSearch)

**Globe.tsx 수정**
**사용 API**: `GET /search/date-location?year=...&latitude=...&longitude=...&radius_km=...`

Globe에서 특정 지점 롱프레스/우클릭 → "이 시기 이 장소에서 무슨 일이?":
```
╔═══════════════════════════════════╗
║ 📍 Near Athens, 480 BCE           ║
║ Within 100km:                     ║
║ ├ Battle of Salamis (480 BCE)     ║
║ ├ Evacuation of Athens (480 BCE)  ║
║ └ Battle of Plataea (479 BCE)     ║
╚═══════════════════════════════════╝
```

---

### Phase 6: 보조 기능

#### 6-1. 이벤트 통계 대시보드

**새 컴포넌트**: `StatsOverlay.tsx`
**사용 API**: `GET /events/stats`, `GET /events/aggregates`, `GET /locations/stats`

```
┌─ CHALDEAS Statistics ────────┐
│ 📊 Events: 3,856             │
│ 📍 With coordinates: 2,891   │
│ 👤 Persons: 2,100            │
│ 🗺 Locations: 1,456          │
│ 📚 Sources: 89               │
└──────────────────────────────┘
```

#### 6-2. 카테고리 필터 (CategoryFilter)

**새 컴포넌트**: `CategoryFilter.tsx`
**사용 API**: `GET /categories`

트리형 카테고리 선택기:
```
▼ History
  ├ ☑ Battle/War
  ├ ☑ Political
  └ ☐ Social
▼ Philosophy
  ├ ☐ Ethics
  └ ☐ Metaphysics
▼ Science
  └ ☑ Discovery
```

#### 6-3. 품질 신고 (ReportButton)

**새 컴포넌트**: `ReportButton.tsx`
**사용 API**: `POST /reports`

NarrativeCard/PersonCard 하단에 "Report Issue" 버튼:
- 신고 유형: incorrect, suspicious, low_quality
- 자유 텍스트 사유

#### 6-4. 타임라인 피드백

**기존 수정**: WorldBriefing 또는 PeriodDrawer
**사용 API**: `POST /timeline/feedback`

Period narrative에 👍/👎 버튼.

---

## 구현 우선순위 (Impact × Effort)

### 🔴 즉시 (1-2시간, 기존 컴포넌트 수정만)

| # | 작업 | 파일 | API |
|---|------|------|-----|
| 1 | WorldBriefing에 top events/persons 표시 | WorldBriefing.tsx | getPeriodDetail (이미 fetch됨, 표시만 추가) |
| 2 | Landing에 featured persons 카루셀 | Landing.tsx | GET /featured/persons |
| 3 | Landing에 검색 바 추가 | Landing.tsx | GET /search |
| 4 | Landing에 통계 표시 | Landing.tsx | GET /events/stats |
| 5 | PersonCard에 relations 섹션 | NarrativeCard.tsx | GET /persons/{id}/relations |
| 6 | PersonCard에 properties 섹션 | NarrativeCard.tsx | GET /persons/{id}/properties |
| 7 | PersonCard에 sources 섹션 | NarrativeCard.tsx | GET /persons/{id}/sources |

### 🟡 빠른 승리 (3-4시간, 새 컴포넌트 1개)

| # | 작업 | 파일 | API |
|---|------|------|-----|
| 8 | 글로벌 검색 바 (Ctrl+K) | SearchBar.tsx (NEW) | GET /search |
| 9 | Globe 카테고리 필터 | Globe.tsx + CategoryFilter (NEW) | GET /categories, GET /events?category= |
| 10 | 뷰포트 연동 Feed | ViewportFeed.tsx (NEW) | GET /feed?lat_min=...&year_start=... |
| 11 | Period Drawer (기간 이벤트/인물) | PeriodDrawer.tsx (NEW) | GET /timeline/periods/{start}/events,persons |

### 🟢 중간 (4-8시간)

| # | 작업 | 파일 | API |
|---|------|------|-----|
| 12 | 인물 관계 네트워크 시각화 | PersonNetwork.tsx (NEW) | GET /persons/{id}/relations, /persons/network |
| 13 | 인물 스레드 (생애 체인) | PersonThread.tsx (NEW) | GET /threads, GET /story/person/{id} |
| 14 | 이벤트 계층 트리 | EventHierarchy.tsx (NEW) | GET /events/hierarchy, /events/{id}/children |
| 15 | 출처 브라우저 | SourceBrowser.tsx (NEW) | GET /sources, /sources/{id}, etc. |
| 16 | 장소 상세 패널 | LocationDetail.tsx (NEW) | GET /locations/{id} |
| 17 | Globe 우클릭 → 주변 검색 | Globe.tsx 수정 | GET /search/date-location |

### 🔵 대형 (8시간+)

| # | 작업 | 파일 | API |
|---|------|------|-----|
| 18 | AI 대화 패널 | ChatPanel.tsx (NEW) | POST /chat/agent, /chat/rag |
| 19 | DeepRead 전면 개편 (연속 스크롤) | DeepRead.tsx 재작성 | periods + events + persons APIs |

---

## 최종 레이아웃 비전

```
┌──────────────────────────────────────────────────────────────────┐
│ [🔍 Search...]                                    [⚙] [?] [AI] │
├──────────┬───────────────────────────────────────┬───────────────┤
│          │                                       │               │
│ Filters  │         3D Globe                      │  Narrative    │
│ ├Category│         (markers, arcs, rings)         │  Card         │
│ ├Import. │                                       │  ├ Story      │
│ ├Show    │                                       │  ├ Facts      │
│          │                                       │  ├ Relations  │
│ ──────── │                                       │  ├ Sources    │
│ Viewport │                                       │  ├ Hierarchy  │
│ Feed     │                                       │  └ Thread     │
│ ├Event1  │                                       │               │
│ ├Person1 │         [+] [-] [🏠]                  │  ── or ──     │
│ ├Event2  │                                       │               │
│ └Person2 │                                       │  Person       │
│          │    ┌─World Briefing──────────────┐    │  Network      │
│          │    │ 480 BCE: Classical Greece    │    │  Graph        │
│          │    │ Top: Marathon, Thermopylae   │    │               │
│          │    └─────────────────────────────┘    │               │
├──────────┴───────────────────────────────────────┴───────────────┤
│ ◀◀  ▶  ▶▶  ━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━  480 BCE  1x 2x 5x  │
│   Ancient │ Classical │ Medieval │ Early Mod │ Modern            │
└──────────────────────────────────────────────────────────────────┘
```

## API client.ts에 추가해야 할 함수

```typescript
// 추가할 API 함수들
export const searchApi = {
  search: (q: string, limit?: number) =>
    api.get('/search', { params: { q, limit } }),
  basic: (q: string, limit?: number) =>
    api.get('/search/basic', { params: { q, limit } }),
  dateLocation: (params: { year: number; latitude: number; longitude: number; radius_km?: number }) =>
    api.get('/search/date-location', { params }),
}

export const chatApi = {
  agent: (query: string, language?: string) =>
    api.post('/chat/agent', { query, language }),
  rag: (query: string, context_limit?: number) =>
    api.post('/chat/rag', { query, context_limit }),
}

export const storyApi = {
  getPersonStory: (id: number, min_strength?: number) =>
    api.get(`/story/person/${id}`, { params: { min_strength } }),
  checkPersonStory: (id: number) =>
    api.get(`/story/person/${id}/check`),
}

export const featuredApi = {
  getPersons: (era?: string, limit?: number) =>
    api.get('/featured/persons', { params: { era, limit } }),
  getRandom: () => api.get('/featured/random'),
}

export const sourcesApi = {
  list: (params?: { type?: string; limit?: number }) =>
    api.get('/sources', { params }),
  get: (id: number) => api.get(`/sources/${id}`),
  getPersons: (id: number) => api.get(`/sources/${id}/persons`),
  getMentions: (id: number, entity_type?: string) =>
    api.get(`/sources/${id}/mentions`, { params: { entity_type } }),
}

export const categoriesApi = {
  getTree: () => api.get('/categories'),
}

export const threadsApi = {
  list: (params?: { year_start?: number; year_end?: number }) =>
    api.get('/threads', { params }),
  getPersonEvents: (personId: number) =>
    api.get(`/threads/${personId}/events`),
}

export const reportsApi = {
  submit: (data: { entity_type: string; entity_id: number; report_type: string; reason: string }) =>
    api.post('/reports', data),
}

// personsApi에 추가
personsApi.getRelations = (id, params?) => api.get(`/persons/${id}/relations`, { params })
personsApi.getNetwork = (params?) => api.get('/persons/network', { params })
personsApi.getSources = (id, params?) => api.get(`/persons/${id}/sources`, { params })
personsApi.getWikipedia = (id) => api.get(`/persons/${id}/wikipedia`)
personsApi.getProperties = (id) => api.get(`/persons/${id}/properties`)

// eventsApi에 추가
eventsApi.list = (params?) => api.get('/events', { params })
eventsApi.getStats = () => api.get('/events/stats')
eventsApi.getHierarchy = (root_id) => api.get('/events/hierarchy', { params: { root_id } })
eventsApi.getChildren = (id) => api.get(`/events/${id}/children`)
eventsApi.getLocations = (id) => api.get(`/events/${id}/locations`)

// locationsApi에 추가
locationsApi.get = (id) => api.get(`/locations/${id}`)
locationsApi.getStats = () => api.get('/locations/stats')
```

## 새 타입 정의 (types/index.ts에 추가)

```typescript
// Search
interface SearchResult {
  query: string
  events: Event[]
  locations: Location[]
  persons: Person[]
  total: number
}

// Chat/Agent
interface AgentResponse {
  analysis: string
  search_results: unknown[]
  response: string
  confidence: number
  related_events: Event[]
  sources: SourceReference[]
}

// Story
interface PersonStory {
  nodes: StoryNode[]
  map_view: { center_lat: number; center_lng: number; zoom: number }
}
interface StoryNode {
  id: number
  type: 'birth' | 'death' | 'battle' | 'political' | 'major' | 'normal'
  title: string
  year: number
  latitude?: number
  longitude?: number
}

// Person Relations
interface PersonRelation {
  person_id: number
  name: string
  role?: string
  birth_year?: number
  death_year?: number
  strength: number
  relationship_type: string
  shared_events: number
}

// Location Detail
interface LocationDetail extends Location {
  names: Array<{ name: string; language: string; valid_from?: number; valid_to?: number }>
  territories: Array<{ territory_name: string; start_year: number; end_year: number }>
  events: Event[]
}

// Featured
interface FeaturedPerson {
  id: number
  name: string
  birth_year?: number
  death_year?: number
  role?: string
  story?: string
  event_count: number
}

// Source Detail
interface SourceDetail {
  id: number
  title: string
  type: string
  author?: string
  mention_count: number
  persons: Array<{ id: number; name: string; mention_count: number }>
}

// Thread
interface PersonThread {
  person_id: number
  person_name: string
  events: Array<{ id: number; title: string; year: number; latitude?: number; longitude?: number }>
  event_count: number
}
```
