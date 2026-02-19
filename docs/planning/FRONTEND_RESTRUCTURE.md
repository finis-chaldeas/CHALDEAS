# Frontend 구조 개선안 v2

> **기반 문서**:
> - `docs/concepts/HISTORICAL_CHAIN_CONCEPT.md`
> - `docs/concepts/SYSTEM_OVERVIEW.md`
> - `docs/planning/future_plan/STORY_CURATION_SYSTEM.md`

---

## 핵심 철학 (원래 기획)

> "모든 역사는 **누가(Person)** **어디서(Location)** **언제(Time)** **무엇을(Event)** 했는가로 결정된다."

### 4가지 체인 유형

| 유형 | 설명 | 예시 |
|------|------|------|
| **Person Story** | 인물의 생애를 따라가는 사건 연쇄 | 알렉산더 대왕의 생애 |
| **Place Story** | 장소에서 일어난 사건들의 연대기 | 로마의 2000년 |
| **Era Story** | 시대의 인물, 장소, 사건 종합 | 르네상스 시대 |
| **Causal Chain** | 원인-결과로 연결된 사건 흐름 | 프랑스 혁명의 원인 |

---

## 원래 기획된 UX (SYSTEM_OVERVIEW.md에서)

### 메인 화면
```
┌────────────────────────────────────────────────────────────────────────┐
│                         🌍 CHALDEAS                                    │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                                                                  │  │
│  │                      [3D 지구본]                                 │  │
│  │                                                                  │  │
│  │           ● 아테네 (5 events)                                    │  │
│  │                    ● 로마 (12 events)                            │  │
│  │                              ● 피렌체 (8 events)                 │  │
│  │                                                                  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ──●────────────────────●────────────────────●──────────────────────   │
│   -500 BCE           0 CE                 1500 CE         [타임라인]   │
│                                                                        │
│  [검색창: "소크라테스에 대해 알려줘"]                                    │
└────────────────────────────────────────────────────────────────────────┘
```

### Person Story 뷰 (인물 탐색)
```
┌─────────────────────────────────────────────────────────────────┐
│ 📜 소크라테스의 이야기                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ #1 탄생과 성장 (-470)                                           │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 소크라테스는 기원전 470년경 아테네에서 태어났습니다.          │ │
│ │ 그의 아버지는 조각가, 어머니는 산파였습니다...                │ │
│ │                                                             │ │
│ │ 📍 아테네  📅 -470  📚 출처: 플라톤의 대화편                  │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                            │                                    │
│                            ▼                                    │
│ #2 철학적 활동 (-450 ~ -400)                                    │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 소크라테스는 아테네 광장(아고라)에서 시민들과 대화를 나누며   │ │
│ │ 진리를 탐구했습니다...                                       │ │
│ │                                                             │ │
│ │ 📍 아고라  📅 -450~-400  📚 출처: 크세노폰의 회상             │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                            │                                    │
│                            ▼                                    │
│ #3 재판과 죽음 (-399)                                           │
│ ...                                                             │
│                                                                 │
│ 🔗 관련 인물: 플라톤, 크세노폰, 아리스토텔레스                    │
│ 🗺️ 관련 장소: 아테네, 아고라, 델포이                             │
│ 📖 관련 시대: 고전 그리스 (-500 ~ -323)                          │
└─────────────────────────────────────────────────────────────────┘
```

### Era Story 뷰 (시대 탐색)
```
┌─────────────────────────────────────────────────────────────────┐
│ 🏛️ 르네상스 시대 (1400-1600)                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 📊 개요                                                         │
│ ├── 기간: 1400년 ~ 1600년 (200년)                               │
│ ├── 중심지: 이탈리아 (피렌체, 로마, 베네치아)                    │
│ └── 특징: 고전 문화의 부흥, 인문주의                            │
│                                                                 │
│ 👤 주요 인물 (32명)                                              │
│ ├── 레오나르도 다 빈치 (1452-1519)                               │
│ ├── 미켈란젤로 (1475-1564)                                       │
│ └── [더 보기...]                                                 │
│                                                                 │
│ 📅 주요 사건 (78개)                                              │
│ ├── 1453: 콘스탄티노플 함락                                      │
│ ├── 1492: 콜럼버스 신대륙 발견                                   │
│ └── [더 보기...]                                                 │
│                                                                 │
│ 🗺️ [지구본에 르네상스 중심지 하이라이트]                          │
└─────────────────────────────────────────────────────────────────┘
```

### Causal Chain 뷰 (인과관계)
```
┌─────────────────────────────────────────────────────────────────┐
│ 🔗 로마 제국 멸망의 인과 사슬                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ [경제적 요인]                   [군사적 요인]                    │
│      │                              │                           │
│      ▼                              ▼                           │
│ ┌─────────┐                    ┌─────────┐                      │
│ │ 화폐가치 │                    │ 게르만족│                      │
│ │ 하락    │                    │ 침입    │                      │
│ └────┬────┘                    └────┬────┘                      │
│      │                              │                           │
│      └──────────┬───────────────────┘                           │
│                 ▼                                               │
│           ┌───────────┐                                         │
│           │ 서로마 제국│                                         │
│           │ 멸망 (476)│                                         │
│           └───────────┘                                         │
│                                                                 │
│ 📖 각 노드 클릭 시 상세 설명 및 출처 확인 가능                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 현재 상태 vs 원래 기획

### 현재 구현된 것

| 기능 | 현재 상태 | 원래 기획 | Gap |
|------|----------|----------|-----|
| 3D 지구본 | ✅ 있음 | 이벤트 마커 + 연결 아크 | 아크 미표시 |
| 타임라인 | ✅ 있음 | 시대별 밀도 표시 | 기본만 |
| 검색 | ✅ 있음 | 자연어 질문 → 체인 응답 | 단순 검색만 |
| Person Story | ❌ 없음 | 인물 생애 노드 체인 | **미구현** |
| Place Story | ❌ 없음 | 장소 연대기 | **미구현** |
| Era Story | ❌ 없음 | 시대 종합 뷰 | **미구현** |
| Causal Chain | ❌ 없음 | 인과관계 그래프 | **미구현** |
| 출처 표시 | ❌ 없음 | 각 노드에 1차 사료 인용 | **미구현** |
| 내러티브 | ❌ 없음 | AI 큐레이터 작성 스토리 | **미구현** |

### 현재 있지만 기획에 없는 것 (제거 대상)

| 컴포넌트 | 문제 |
|----------|------|
| ServantPanel | FGO 서번트 - 원래 기획 범위 외 |
| ShowcaseModal | 불명확한 쇼케이스 - 기획에 없음 |
| ExplorePanel | 검색과 중복, 기획에 없음 |
| 플로팅 버튼 4개 | UI 난잡, 기능이 사이드바로 통합되어야 함 |

### 현재 있고 유지할 것

| 컴포넌트 | 이유 |
|----------|------|
| ChatPanel | SHEBA 채팅 - 자연어 질문 인터페이스 |
| ChainPanel | Historical Chain 탐색 (개선 필요) |
| EventDetailPanel | 이벤트 상세 (소스 추가 필요) |

---

## 새 프론트엔드 구조

### 전체 레이아웃
```
┌──────────────────────────────────────────────────────────────────┐
│ Header                                                            │
│ [⊕ CHALDEAS] [━━━━━ 검색: "소크라테스" ━━━━━] [🌐 En] [⚙]        │
├────────────────┬─────────────────────────┬───────────────────────┤
│                │                         │                       │
│   Navigator    │        Globe            │    Story Panel        │
│   280px        │        flex             │    400px              │
│                │                         │                       │
│  ┌──────────┐  │   ┌───────────────┐     │  ┌─────────────────┐  │
│  │[탭: 이벤트]│  │   │               │     │  │ 📜 소크라테스    │  │
│  │[탭: 인물] │  │   │   3D Globe    │     │  │                 │  │
│  │[탭: 장소] │  │   │               │     │  │ #1 탄생 (-470)  │  │
│  │[탭: 시대] │  │   │  ● ─── ●      │     │  │ ├─ 내러티브     │  │
│  │[탭: 체인] │  │   │       \       │     │  │ └─ 📚 출처      │  │
│  │          │  │   │        ●      │     │  │       │         │  │
│  │ [목록]    │  │   └───────────────┘     │  │       ▼         │  │
│  │  - 항목1  │  │                         │  │ #2 철학 (-450)  │  │
│  │  - 항목2  │  │                         │  │ ...             │  │
│  │  - 항목3  │  │                         │  │                 │  │
│  └──────────┘  │                         │  │ 🔗 관련 인물     │  │
│                │                         │  │ 🗺️ 관련 장소     │  │
│                │                         │  └─────────────────┘  │
├────────────────┴─────────────────────────┴───────────────────────┤
│ Timeline                                                          │
│ -3000 ════════════════●════════════════════════════════════ 2025 │
│        [고대]    [중세]   [르네상스]   [근대]   [현대]             │
└──────────────────────────────────────────────────────────────────┘
                                                              [◎ Chat]
```

### 컴포넌트 구조

```
src/
├── App.tsx                      # 라우팅만 (50줄 이하)
├── layouts/
│   └── MainLayout.tsx           # 3열 레이아웃
│
├── components/
│   ├── header/
│   │   ├── Header.tsx           # 상단 바
│   │   ├── SearchBar.tsx        # 통합 검색
│   │   ├── LanguageSelector.tsx
│   │   └── SettingsMenu.tsx     # 기존 플로팅 ⚙ 대체
│   │
│   ├── navigator/               # 왼쪽 패널 (NEW)
│   │   ├── Navigator.tsx        # 탭 컨테이너
│   │   ├── EventTab.tsx         # 이벤트 목록
│   │   ├── PersonTab.tsx        # 인물 목록 (NEW)
│   │   ├── LocationTab.tsx      # 장소 목록 (NEW)
│   │   ├── EraTab.tsx           # 시대 목록 (NEW)
│   │   └── ChainTab.tsx         # 체인 목록 (기존 ChainPanel 통합)
│   │
│   ├── globe/
│   │   ├── GlobeContainer.tsx   # 기존 유지
│   │   └── ConnectionArcs.tsx   # 연결 아크 표시 (NEW)
│   │
│   ├── story/                   # 오른쪽 패널 (REDESIGN)
│   │   ├── StoryPanel.tsx       # 스토리 컨테이너
│   │   ├── PersonStory.tsx      # 인물 스토리 뷰 (NEW)
│   │   ├── PlaceStory.tsx       # 장소 스토리 뷰 (NEW)
│   │   ├── EraStory.tsx         # 시대 스토리 뷰 (NEW)
│   │   ├── CausalChain.tsx      # 인과 체인 뷰 (NEW)
│   │   ├── StoryNode.tsx        # 스토리 노드 (공통)
│   │   └── SourceViewer.tsx     # 출처 뷰어 (NEW)
│   │
│   ├── timeline/
│   │   └── Timeline.tsx         # 기존 유지, 개선
│   │
│   ├── chat/
│   │   └── ChatPanel.tsx        # 기존 유지 (우하단 플로팅)
│   │
│   └── common/
│       ├── TabBar.tsx
│       ├── Card.tsx
│       └── Badge.tsx
│
├── store/
│   ├── navigationStore.ts       # 현재 선택된 엔티티/뷰
│   ├── storyStore.ts            # 스토리 상태 (NEW)
│   ├── globeStore.ts            # 기존 유지
│   └── timelineStore.ts         # 기존 유지
│
└── types/
    ├── story.ts                 # Story, StoryNode, Source (NEW)
    └── chain.ts                 # Chain types
```

---

## 작업 단계

### Phase 1: 정리 (1일) ✅ 완료

**제거:**
- [x] 플로팅 버튼 4개 (explore, servant, hierarchy, settings)
- [x] components/explore/ 폴더
- [x] components/servants/ 폴더
- [x] components/showcase/ 폴더
- [x] 관련 상태 및 import

**유지:**
- [x] ChatPanel (우하단 플로팅)
- [x] ChainPanel (Navigator로 통합 예정)

### Phase 2: 레이아웃 재구성 (2일) ✅ 완료

- [x] MainLayout.tsx 생성 (3열 구조)
- [x] Header 컴포넌트 분리 (검색 + 설정)
- [x] Navigator 탭 구조 구현
- [x] StoryPanel 컨테이너 생성

### Phase 3: Navigator 구현 (2일) ✅ 완료

- [x] EventTab (기존 VirtualEventList 활용)
- [x] PersonTab (인물 목록 + 검색)
- [x] LocationTab (장소 목록 + 검색)
- [x] EraTab (시대 계층 트리)
- [x] ChainTab (기존 ChainPanel 통합)

### Phase 4: Story 뷰 구현 (3일) ✅ 완료

- [x] StoryPanel 기본 구조
- [x] PersonStory 뷰 (인물 생애 노드 체인)
- [x] PlaceStory 뷰 (장소 연대기)
- [x] EraStory 뷰 (시대 종합)
- [x] StoryNode 컴포넌트 (노드 + 내러티브 + 출처)
- [x] SourceViewer (Wikipedia/원문 표시)

### Phase 5: 글로브 연동 (1일)

- [ ] ConnectionArcs 컴포넌트
- [ ] 스토리 노드 클릭 시 글로브 이동
- [ ] 글로브 마커 클릭 시 스토리 표시

### Phase 6: 백엔드 API 연동 (1일)

- [ ] GET /api/v1/events/{id} → sources 표시
- [ ] GET /api/v1/sources/wiki/{id} → Wikipedia 본문
- [ ] GET /api/v1/globe/arcs/{id} → 연결 아크
- [ ] GET /api/v1/story/person/{id} → 인물 스토리 (추후)

---

## 삭제 대상 파일

```
# 컴포넌트
frontend/src/components/explore/ExplorePanel.tsx
frontend/src/components/servants/ServantDetail.tsx
frontend/src/components/servants/ServantList.tsx
frontend/src/components/servants/ServantPanel.tsx
frontend/src/components/showcase/ShowcaseMenu.tsx
frontend/src/components/showcase/ShowcaseModal.tsx

# App.tsx에서 제거할 코드
- explore-toggle-btn
- servant-toggle-btn
- hierarchy-toggle-btn
- settings-toggle-btn (Header로 이동)
- 관련 useState, import, JSX
```

---

## 우선순위

| 순위 | 작업 | 이유 | 소요 |
|-----|------|------|------|
| 1 | Phase 1: 정리 | 불필요 코드 제거 | 1일 |
| 2 | Phase 2: 레이아웃 | 구조 잡기 | 2일 |
| 3 | Phase 4: Story 뷰 | 핵심 기능 (원래 기획) | 3일 |
| 4 | Phase 3: Navigator | 탐색 개선 | 2일 |
| 5 | Phase 5-6: 연동 | 완성도 | 2일 |

**총 예상: 10일**

---

## 참고 문서

- `docs/concepts/HISTORICAL_CHAIN_CONCEPT.md` - 4가지 체인 유형 정의
- `docs/concepts/SYSTEM_OVERVIEW.md` - 완성 UX 와이어프레임
- `docs/planning/future_plan/STORY_CURATION_SYSTEM.md` - 내러티브 생성 시스템
- `docs/concepts/METHODOLOGY.md` - Braudel 시간 구조

---

## 구현 결과 (2026-02-13)

### Phase 1-4 완료

#### 삭제된 파일
```
frontend/src/components/explore/          # 폴더 전체 삭제
frontend/src/components/servants/         # 폴더 전체 삭제
frontend/src/components/showcase/         # 폴더 전체 삭제
frontend/src/components/hierarchy/        # 폴더 전체 삭제
frontend/src/data/showcaseData.ts         # 미사용 데이터 삭제
```

#### 생성된 파일

**레이아웃:**
```
frontend/src/layouts/MainLayout.tsx       # 3열 레이아웃 (Navigator | Globe | StoryPanel)
```

**Header:**
```
frontend/src/components/header/Header.tsx # 상단 바 (로고, 검색, 언어, 설정)
frontend/src/components/header/index.ts   # export
```

**Navigator (5개 탭):**
```
frontend/src/components/navigator/Navigator.tsx    # 탭 컨테이너
frontend/src/components/navigator/EventTab.tsx     # 이벤트 목록
frontend/src/components/navigator/PersonTab.tsx    # 인물 검색/목록
frontend/src/components/navigator/LocationTab.tsx  # 장소 검색/목록
frontend/src/components/navigator/EraTab.tsx       # 시대 목록
frontend/src/components/navigator/ChainTab.tsx     # 체인 통계
frontend/src/components/navigator/index.ts         # export
```

**Story (4가지 뷰):**
```
frontend/src/components/story/StoryPanel.tsx   # 스토리 뷰 컨테이너
frontend/src/components/story/StoryNode.tsx    # 스토리 노드 (내러티브 + 출처)
frontend/src/components/story/PersonStory.tsx  # 인물 생애 체인 뷰
frontend/src/components/story/PlaceStory.tsx   # 장소 연대기 뷰
frontend/src/components/story/EraStory.tsx     # 시대 종합 뷰
frontend/src/components/story/SourceViewer.tsx # Wikipedia 본문 뷰어
frontend/src/components/story/index.ts         # export (업데이트)
```

#### 수정된 파일
```
frontend/src/App.tsx                      # 버튼 4개 제거, import 정리
frontend/src/styles/globals.css           # 새 레이아웃 CSS 추가
```

### 남은 작업 (Phase 5-6)

| Phase | 작업 | 상태 |
|-------|------|------|
| 5 | ConnectionArcs 컴포넌트 | 미완료 |
| 5 | 글로브-스토리 클릭 연동 | 미완료 |
| 6 | Globe arcs API (`/api/v1/globe/arcs`) | 미완료 |
| 6 | Story API (`/api/v1/story/person`) | 미완료 |

### 기존 API (이미 구현됨)
```
GET /api/v1/events/{id}        # sources 포함
GET /api/v1/sources/wiki/{id}  # Wikipedia 본문 (ZIM)
```

### TypeScript 검증
- `npx tsc --noEmit` 통과 (에러 없음)

### 다음 단계
1. **App.tsx에 새 레이아웃 적용** - 현재 컴포넌트는 생성되었지만 App.tsx에 통합되지 않음
2. **Phase 5-6 완료** - 글로브 연동 및 백엔드 API
3. **테스트** - 실제 동작 확인
