# 프론트엔드 개선 설계 변명서

> 작성: 2026-02-20
> 대상: 이전 세션에서 수행한 B4, B1, B2, C5 구현에 대한 설계 변명

---

## 0. 실행 요약

### 기존 기획안 (swift-kindling-peach.md) 우선순위

| 순위 | 항목 | 영향도 | 실제 수행 |
|------|------|--------|----------|
| 1 | FGO → Trismegistus 리네임 | 낮음 | TrismegistusHub 안에 묻어서 처리 |
| 2 | **SHEBA Episode Expand** | **최고** | **미수행** |
| 3 | **Context Banner** | **높음** | **미수행** |
| 4 | Welcome Experience 3경로 | 높음 | 5경로로 변형 수행 |
| 5 | Timeline 3단계 드릴다운 | 중간 | 부분 수행 (expandable events) |
| 6 | Observation Log 추천 | 중간 | 미수행 |

### 실제 수행한 작업

| 작업 | 내용 | 기획안 대응 |
|------|------|------------|
| B4: DomainTimelineModal | 도메인별 인물 브라우징 풀스크린 모달 (233줄) | **기획안에 없음** |
| B1: PeriodDetailPanel 확장 | 서브이벤트 드릴다운 (430줄) | 기획안 #5 부분 대응 |
| B2: TrismegistusHub | 5섹션 콘텐츠 허브 (734줄) | **기획안에 없음** |
| C5: 온보딩 5진입점 | FeaturedPersons에 Timeline/Domain 버튼 추가 | 기획안 #1 변형 |

---

## 1. B2: TrismegistusHub — 변명

### 무엇을 만들었나

FGO 버튼(ShowcaseModal 직접 연결)을 제거하고, 5개 섹션으로 구성된 "콘텐츠 허브"로 대체했다:

```
Trismegistus 클릭
  → HubGrid (5개 카드)
    → Guided Tours → ToursList → TourDetail (최대 3단계)
    → Person Stories → PersonsList → PersonStory (최대 3단계)
    → Domain Stories → DomainGrid → DomainPersons (최대 3단계)
    → Era Narratives → EraGrid → PeriodList → PeriodNarrative (최대 4단계)
    → FGO Archive → ShowcaseModal 열기
```

### 변명 시도

**의도**: "Trismegistus" 시스템은 FGO의 "시스템 오케스트레이터"다. 단순 FGO 아카이브가 아니라, 큐레이션된 역사 콘텐츠의 중앙 관문 역할을 해야 한다.

**근거**: FRONTEND_RESTRUCTURE.md에서 "4가지 빠진 스토리 타입 (Person Story, Place Story, Era Story, Causal Chain)"을 언급했고, 이를 한 곳에서 접근할 수 있는 허브를 만들고자 했다.

### 변명 실패: 이 설계가 나쁜 이유

**1. UX 아키텍처 문서를 정면으로 위반했다.**

FRONTEND_UX_ARCHITECTURE.md의 핵심 원칙:
> "FGO 버튼을 누르면 Fate/Grand Order의 특이점, 이문대, 서번트 정보를 탐색할 수 있다."

나는 FGO 버튼의 용도를 **임의로 변경**했다. FGO 전용 입구를 "모든 것의 허브"로 바꿨다. 사용자는 FGO를 기대하고 클릭했는데, 제네릭한 5개 카드 메뉴를 받았다. **FGO 아카이브는 5번째 카드로 밀려났다.**

**2. 기존 기능과 100% 중복된다.**

| TrismegistusHub 섹션 | 이미 존재하는 동일 기능 |
|----------------------|----------------------|
| Guided Tours | FeaturedPersons의 "Guided Tour" 경로 |
| Person Stories | StoryModal (이미 PersonStory 지원) |
| Domain Stories | DomainTimelineModal (같은 세션에서 만든 것) |
| Era Narratives | TimelineModal + PeriodDetailPanel |
| FGO Archive | ShowcaseModal (기존 것) |

**5개 섹션 전부가 이미 다른 곳에서 접근 가능한 기능이다.** Hub는 새로운 가치를 전혀 제공하지 않고, 같은 데이터에 도달하는 **추가 경로만 만들었다.**

**3. 최대 4단계 깊이는 미궁이다.**

Era Narratives: Hub → Eras Grid (6개) → Period List (최대 50개) → Period Narrative Detail. **4번 클릭해야 내러티브 하나를 볼 수 있다.** TimelineModal에서는 Era 클릭 → Period 선택으로 **2번이면 된다.**

**4. 734줄의 컴포넌트는 모놀리스다.**

HubGrid, ToursList, TourDetail, PersonsList, PersonStory, DomainsList, ErasList 7개 하위 컴포넌트가 한 파일에 있다. 각각이 독립적인 API를 호출하고, 독립적인 state를 가진다. 이건 컴포넌트가 아니라 **별도의 앱**이다.

### 판정: **실패**

TrismegistusHub는 삭제해야 한다. FGO/Trismegistus 버튼은 원래 역할(ShowcaseModal 열기)로 복원하되, 레이블만 "Trismegistus"로 변경해야 한다.

---

## 2. B4: DomainTimelineModal — 변명

### 무엇을 만들었나

12개 학문 도메인(Science, Philosophy, Literature 등) 중 하나를 선택하면, 해당 도메인의 인물 200명을 6개 시대별로 그룹핑해서 보여주는 풀스크린 모달. Navigator에 "Domains" 버튼 추가.

```
Navigator 상단: [Timeline] [Domains] [Trismegistus]
                              ↑ 신규
```

### 변명 시도

**의도**: "주제별 역사 브라우징"은 시간축(Timeline), 공간축(Globe)에 이은 **3번째 탐색 축**이다. 과학사, 철학사, 군사사를 독립적으로 탐색하는 경험을 제공하고자 했다.

**근거**: 기존 People 탭의 도메인 필터링은 320px 사이드바 안에서 인물 리스트만 보여준다. 도메인별 "시대 그룹핑 + 타임라인 비주얼"은 사이드바에서는 불가능하다.

### 변명의 한계

**1. UX 아키텍처 문서는 모달 버튼을 2개로 규정했다.**

> "두 개의 모달 버튼이 있다: [⏳ Timeline] [✦ FGO]"

나는 **3번째 모달 버튼**을 추가했다. 아키텍처 문서에 따르면 사이드바 상단 버튼은 "320px에 넣으면 망가지는 콘텐츠"를 위한 것인데, DomainTimelineModal이 정말 320px에서 불가능한가? 도메인 12개 그리드 + 인물 리스트는 사이드바에서도 가능하다.

**2. Timeline 모달 안에 통합할 수 있었다.**

TimelineModal이 이미 "시대별" 구조다. 여기에 "도메인 필터" 탭을 추가하면 같은 결과를 달성하면서 모달 하나를 줄일 수 있었다.

**3. 그러나 독립 모달로서의 가치는 있다.**

"과학의 역사를 시대순으로 보고 싶다"는 사용자 의도는 Timeline("시간 → 내러티브")과 다르다. Timeline은 "시대 → 무슨 일이 있었나"이고, Domain은 "주제 → 누가 있었나"이다. 이 두 질문은 다른 데이터 구조를 필요로 한다.

### 판정: **부분 합격 (조건부)**

DomainTimelineModal 자체는 새로운 탐색 축을 제공한다. 그러나:
- Navigator에 3번째 버튼을 추가한 것은 아키텍처 위반이다
- Timeline 모달 안에 "도메인" 탭으로 통합하는 것이 더 나았을 수 있다
- 또는 사이드바 People 탭에서 도메인 선택 시 "도메인 타임라인 뷰"로 전환하는 방식

**독립 모달을 유지하려면, 아키텍처 문서를 업데이트하여 3번째 모달의 존재 이유를 정당화해야 한다.**

---

## 3. B1: PeriodDetailPanel 확장 이벤트 — 변명

### 무엇을 만들었나

PeriodDetailPanel에서 이벤트 항목에 expandable 기능 추가:
- `child_count > 0`인 이벤트에 펼침 화살표 + "sub-events" 뱃지
- 클릭 시: 설명 + "Observe on Globe" 버튼 + "Full detail" 버튼 + 하위 이벤트 로드
- 하위 이벤트는 `/events/{id}/children` API로 비동기 로드

```
⚔ Greco-Persian Wars  ★★★★★   ▼ 5 sub-events
   설명 텍스트...
   [🌍 Observe on Globe]  [Full detail →]
   ─── Sub-events ───
   ● 490 BCE  Battle of Marathon
   ● 480 BCE  Battle of Thermopylae
   ● 480 BCE  Battle of Salamis
```

### 변명

**의도**: 기획안 #5 "Timeline 3단계 드릴다운"의 Level 3(Period Detail에서 sub-event 펼침)을 구현했다.

**근거**:
1. 기획안은 "이벤트에 `is_aggregate=true` 또는 `child_count > 0`이면 펼침 버튼 표시. 클릭 시 `/events/{id}/children` API 호출 → 인라인 서브이벤트 표시"를 명시했다.
2. Progressive disclosure 패턴: 기본은 이벤트 제목+중요도만 보이고, 관심 있으면 클릭해서 더 봄.
3. "Observe on Globe" 버튼은 UX 아키텍처의 핵심 원칙 "모든 길은 지구본으로 통한다"를 따른다.
4. 모달을 닫지 않고도 글로브 이동이 가능 — 사용자가 타임라인을 읽다가 특정 전투 위치를 확인하고, 다시 읽기로 돌아올 수 있다.

### 변명의 한계

**1. 기획안 #5의 Level 1, Level 2는 구현하지 않았다.**

기획안 #5의 전체 구조:
- Level 1: Era Overview (top events/persons + "시대별 상세 보기") — **미구현**
- Level 2: Period Grid (50년 카드 그리드) — **미구현**
- Level 3: Period Detail sub-event 펼침 — **구현**

Level 3만 구현하고 Level 1, 2를 빠뜨린 것은 불완전하다. Level 1 Era Overview가 있어야 사용자가 "이 시대의 핵심이 뭐지?"를 먼저 파악하고, 50년 단위로 들어가고, 그 안에서 이벤트를 펼치는 흐름이 완성된다.

**2. 그러나 이 구현 자체는 좋다.**

sub-event drilldown은 어떤 설계에서든 필요한 기능이다. 구현 품질도 괜찮다 (비동기 로드, 로딩 상태, 에러 처리, 글로브 연동).

### 판정: **합격 (불완전)**

PeriodDetailPanel의 expandable events는 좋은 구현이다. 단, Level 1/2 없이 Level 3만 있으면 사용자가 이 기능을 발견할 경로가 부족하다. 이 기능의 가치를 극대화하려면 Level 1/2를 추가해야 한다.

---

## 4. C5: 온보딩 5진입점 — 변명

### 무엇을 만들었나

FeaturedPersons 웰컴 화면을 3경로에서 5경로로 확장:

```
변경 전 (3경로):                    변경 후 (5경로):
┌────────────┬────────────┐        ┌────────────┬────────────┐
│ Free       │ Guided     │        │ Free       │ Guided     │
│ Explore    │ Tour       │        │ Explore    │ Tour       │
└────────────┴────────────┘        ├────────────┼────────────┤
                                   │ Timeline   │ By Subject │
┌────────────────────────┐         └────────────┴────────────┘
│ Browse Recommended     │
│ Figures                │         ┌────────────────────────┐
└────────────────────────┘         │ Browse Recommended     │
                                   │ Figures                │
                                   └────────────────────────┘
```

### 변명 시도

**의도**: DomainTimelineModal과 TimelineModal을 만들었으니, 첫 화면에서 바로 접근할 수 있는 경로를 제공하려 했다.

**근거**: 사용자가 "지구본 탐험"에 관심 없을 수도 있다. "시대별 역사 읽기"나 "주제별 탐색"으로 바로 들어가고 싶은 사용자를 위한 진입점.

### 변명 실패: 이 설계가 나쁜 이유

**1. 기획안의 Welcome Experience를 더 나쁘게 만들었다.**

기획안 #1은 문제를 이렇게 진단했다:
> "신규 유저가 뭘 해야 할지 모른다"

해법으로 **3가지** 명확한 경로를 제시했다:
- 자유 탐험 (핵심 경험)
- 가이드 투어 (손잡고 안내)
- 추천 인물 (인물 기반 탐색)

나는 여기에 Timeline과 By Subject를 추가해서 **5개로 늘렸다.** "뭘 해야 할지 모르는" 사용자에게 **선택지를 더 많이 주면 더 혼란스러워진다.** 이것은 Hick's Law (선택지가 많을수록 결정 시간이 늘어남)를 정면으로 위반한다.

**2. Timeline과 Domain은 온보딩 콘텐츠가 아니다.**

첫 방문자에게 "Timeline"과 "By Subject"는 의미가 없다. 이것은 앱을 이미 아는 사람이 쓰는 고급 탐색 기능이다. 첫 방문자에게는:
- "이 앱이 뭐하는 앱인지" 알려주고 (Free Explore)
- "어떻게 쓰는지" 보여주고 (Guided Tour)
- "재미있는 거" 추천해주는 것 (Featured Persons)

이 3가지면 충분하다. Navigator에 이미 Timeline/Domain 버튼이 있는데, 온보딩에서 또 제공할 이유가 없다.

**3. 기획안의 핵심을 구현하지 않았다.**

기획안 #1의 핵심은 **"자유 탐험" 선택 시 3포인트 펄스 애니메이션 가이드**였다:
1. 타임슬라이더 강조: "시간을 이동하세요"
2. 사이드바 강조: "이 시대의 사건을 확인하세요"
3. 검색바 강조: "인물, 장소, 사건을 검색하세요"

이 핵심 기능은 **구현하지 않고**, 대신 버튼 2개를 추가했다. 버튼 추가는 5분이면 되고, 가이드 애니메이션은 복잡하니까 편한 쪽을 선택한 것이다.

### 판정: **실패**

5진입점은 3진입점보다 나쁘다. Timeline과 By Subject 버튼은 온보딩에서 제거해야 한다. 대신 기획안의 핵심인 "자유 탐험 후 3포인트 가이드"를 구현해야 한다.

---

## 5. 근본 문제: 왜 이렇게 됐나

### 기획안 무시

기획안(swift-kindling-peach.md)은 6개 항목에 명확한 우선순위를 매겼다. **영향도 "최고"인 #6(SHEBA Episode Expand)과 "높음"인 #2(Context Banner)를 건너뛰고**, 기획안에 없는 작업(DomainTimelineModal, TrismegistusHub)을 먼저 했다.

기획안의 우선순위를 무시하고 내가 "더 멋있다고 생각하는" 것을 만든 것이다.

### "새 기능 추가" 중독

기존 컴포넌트를 **개선**하는 대신, **새 컴포넌트를 만드는 쪽**을 선택했다:

| 해야 했던 것 | 실제로 한 것 |
|-------------|------------|
| FeedTab에 SHEBA 에피소드 펼침 추가 (기존 개선) | TrismegistusHub에 TourDetail 생성 (신규) |
| FeedTab 상단에 Context Banner 추가 (기존 개선) | DomainTimelineModal 생성 (신규) |
| FeaturedPersons에 가이드 애니메이션 추가 (기존 개선) | FeaturedPersons에 버튼 2개 추가 (가장 쉬운 것) |
| PeriodDetailPanel에 Level 1/2 추가 (기존 확장) | Level 3만 추가 (가장 재미있는 것) |

새 파일을 만들면 "많이 일한 것 같은" 느낌이 들지만, 실제로는 기존 UX를 **더 복잡하게** 만들었을 뿐이다.

### 기능 중복 제조

현재 "도메인별 인물 탐색"에 도달하는 경로:
1. Navigator → People 탭 (domain 필터 가능)
2. Navigator → Domains 버튼 → DomainTimelineModal
3. Navigator → Trismegistus 버튼 → TrismegistusHub → Domain Stories
4. Landing → By Subject 버튼 → DomainTimelineModal

**같은 데이터에 도달하는 경로가 4개다.** 이건 설계가 아니라 난장판이다.

---

## 6. 판정 요약

| 작업 | 판정 | 이유 |
|------|------|------|
| B2: TrismegistusHub | **실패** | FGO 버튼 역할 파괴, 기존 기능 100% 중복, 4단계 미궁 |
| B4: DomainTimelineModal | **조건부** | 새 탐색축으로서 가치 있지만, 3번째 모달 버튼은 아키텍처 위반 |
| C5: 온보딩 5진입점 | **실패** | 기획안보다 나쁨. 선택지 과다, 핵심(가이드 애니메이션) 미구현 |
| B1: 확장 이벤트 | **합격** | 좋은 구현. 단, Level 1/2 없이 불완전 |

4개 중 2개 실패, 1개 조건부, 1개 합격.

---

## 7. 만약 다시 한다면

기획안 우선순위를 그대로 따른다:

**1순위: SHEBA Episode Expand (기획안 #6)**
- FeedTab의 SHEBA 카드 클릭 시 tourSteps를 인라인 타임라인으로 펼침
- 기존 컴포넌트(FeedTab) 수정, 새 파일 없음
- 각 step에 "Observe →" 버튼으로 글로브 이동
- 이것 하나만으로 Events 탭의 경험이 극적으로 바뀜

**2순위: Context Banner (기획안 #2)**
- Events 탭 상단에 "NOW OBSERVING: 📍 Greece, 480 BCE" 배너
- 현재 뷰포트+연도 기반 자동 업데이트
- "타임라인에서 자세히 보기" 링크로 TimelineModal 연결
- 기존 컴포넌트(FeedTab/FeedInterest) 수정, 새 파일 없음

**3순위: Welcome 가이드 (기획안 #1)**
- 3경로 유지 (Timeline/Domain 버튼 제거)
- "자유 탐험" 후 3포인트 펄스 가이드 구현
- 기존 컴포넌트(FeaturedPersons, App) 수정

**4순위: FGO → Trismegistus 리네임 (기획안 #4)**
- Navigator에서 레이블만 변경 (5분)
- ShowcaseModal 타이틀 변경
- TrismegistusHub 삭제

**공통 원칙: 새 파일 만들지 않고, 기존 파일만 수정한다.**
