# Frontend Redesign Plan A: Complete Rebuild

> "지구본이 캔버스다. UI는 지구본 위에 떠있는 레이어일 뿐이다."

## 철학

기존 컴포넌트 트리를 전면 재설계한다. 모든 데이터 모델을 처음부터 설계에 반영한다.
기존 코드는 `_deprecated/`로 이동하고, 새 컴포넌트를 처음부터 작성한다.

## 핵심 원칙

1. **Globe-First**: 모든 인터랙션의 시작과 끝은 지구본
2. **2-Tap Rule**: 아무 콘텐츠든 최대 2번 탭으로 도달
3. **Show, Don't Tell**: 텍스트 최소화, 시각적 표현 최대화
4. **Progressive Disclosure**: 기본은 단순, 탭/클릭으로 깊이 탐색

---

## 현재 문제

### 중복 경로 (같은 데이터, 여러 진입점)
```
"시대별 이벤트" → TimelineModal, HierarchyExplorer, TrismegistusHub(Era) = 3곳
"도메인별 인물" → DomainTimelineModal, TrismegistusHub(Domain), PersonTab = 3곳
"투어 에피소드" → FeaturedPersons, FeedTab, TrismegistusHub(Tours) = 3곳
"FGO 콘텐츠"   → ShowcaseModal, TrismegistusHub(FGO) = 2곳
```

### 풍부한 데이터 모델을 UI가 활용하지 못함

| 데이터 | DB/API 상태 | 프론트엔드 사용 |
|--------|-----------|---------------|
| 인물 관계 (teacher/student/rival/ally/family, strength 1-5) | `/persons/{id}/relations` API 완성 | PersonDetailView에서만 |
| 이벤트 인과관계 (causes/follows/enables, certainty) | `event_relationships` 테이블 존재 | **미사용** (API도 미노출) |
| 영토 역사 (territory_locations, valid_from/until) | DB 테이블 완성 | **미사용** (API 미노출) |
| 시간별 지명 변화 (location_names, name_type) | DB 테이블 완성 | LocationDetailView에서만 |
| 위키데이터 속성 (100+개 P-코드) | `/properties/{type}/{id}` API 완성 | 9개만 표시 (91% 미사용) |
| 스레드/서사 (threads by connecting person) | `/threads` API 완성 | **미사용** |
| 인물 플로우 (birth -> events -> death) | `/persons/{id}/flow` API 완성 | PersonDetailView에서만 |

### 인지 부하
- 풀스크린 모달 6개
- 사이드바 트리거 버튼 3개
- 랜딩 진입점 5개

---

## 화면 구조

```
+----------------------------------------------------------+
|  [검색]                              [설정]  <- 최소 헤더  |
+----------+-------------------------------+---------------+
|          |                               |               |
|  Context |      GLOBE                    |  Detail       |
|  Drawer  |      (풀스크린)               |  Slide        |
|          |                               |               |
|  열면    |  이벤트 마커                   |  열면         |
|  나옴    |  인물 아이콘                   |  나옴         |
|          |  영토 오버레이                 |               |
|          |  인과관계 화살표               |               |
|          |                               |               |
+----------+-------------------------------+---------------+
|  [<< ----------- TIMELINE ----------- >>]  <- 하단 바     |
|  [-3000 ==================*======= 2024]                 |
+----------------------------------------------------------+
```

### Context Drawer (왼쪽 슬라이드)
- **기본 상태**: 닫혀있음. 글로브만 보임
- **열리는 조건**: 검색 클릭, 시대 배너 클릭, 하단 타임라인 시대 라벨 클릭
- **내용**: 현재 시공간 컨텍스트에 맞는 피드 (기존 FeedInterest 로직 재활용)

### Detail Slide (오른쪽 슬라이드)
- **기본 상태**: 닫혀있음
- **열리는 조건**: 글로브에서 마커/인물/영토 클릭
- **내용**: EventDetail, PersonDetail, LocationDetail (기존 로직 재활용)

### 풀스크린 모달 -> 0개
- TimelineModal -> 하단 타임라인 바로 통합
- HierarchyExplorer -> EventDetail 내 인라인 드릴다운
- ShowcaseModal -> Navigator의 FGO 탭으로 통합
- StoryModal -> PersonDetail 내 "스토리" 탭으로 통합

---

## 새 컴포넌트 트리

```
App
+- MinimalHeader (검색 + 설정만)
+- GlobeCanvas (풀스크린, 모든 시각화)
|  +- EventMarkers (기존)
|  +- PersonIcons (NEW: 인물 위치에 아바타 표시)
|  +- TerritoryOverlay (NEW: 영토 경계선, 시간에 따라 변화)
|  +- CausalArrows (NEW: 이벤트 간 인과관계 화살표)
|  +- RelationshipLines (NEW: 인물 간 관계선)
+- ContextDrawer (왼쪽 슬라이드)
|  +- ContextBanner ("NOW OBSERVING: ...")
|  +- ContextFeed (시공간 기반 이벤트+인물 피드)
|  +- EpisodeList (SHEBA 에피소드)
|  +- FGOTab (서번트 매핑)
+- DetailSlide (오른쪽 슬라이드)
|  +- EventCard
|  |  +- 개요 (title, date, description, significance)
|  |  +- 인물들 (참여자 + 관계도)
|  |  +- 하위 이벤트 (인라인 드릴다운)
|  |  +- 인과관계 (causes -> this -> consequences)
|  |  +- 출처 (sources with quotes)
|  +- PersonCard
|  |  +- 프로필 (name, dates, role, domain, wikidata properties)
|  |  +- 생애 플로우 (birth -> events -> death, 지도 위에)
|  |  +- 관계도 (teacher/student/rival/ally 네트워크)
|  |  +- 영향력 (이 인물이 관여한 이벤트들)
|  |  +- 출처 (books with contexts)
|  +- LocationCard
|     +- 역사적 이름들 (시대별 지명 변화)
|     +- 영토 소속 (어느 제국/왕국에 속했는가, 시간순)
|     +- 이 장소의 이벤트들
+- TimelineBar (하단)
|  +- 연도 슬라이더
|  +- 시대 라벨 (클릭 -> ContextDrawer에 시대 개요)
|  +- 재생 컨트롤
|  +- 이벤트 밀도 히트맵 (연도별 이벤트 수)
+- TourOverlay (가이드 투어, 기존 유지)
+- WelcomeOverlay (첫 방문)
   +- "투어 시작" -> TourOverlay
   +- "탐험 시작" -> 오버레이 닫기
```

---

## 새로 활용하는 데이터

### 1. 인물 관계 네트워크 (PersonCard 내)
```
GET /persons/{id}/relations -> 관계 목록
UI: 미니 네트워크 그래프 (d3-force)
   - 노드 = 인물 (아바타)
   - 엣지 = 관계 (색상: 빨강=rival, 파랑=teacher, 초록=ally)
   - 엣지 두께 = strength (1-5)
   - 클릭 -> 해당 인물 PersonCard 열기
```

### 2. 이벤트 인과관계 (EventCard 내 + 글로브 위)
```
NEW API 필요: GET /events/{id}/relationships
UI: EventCard에 "왜 이 일이 일어났는가?" 섹션
   - <- causes (이전 이벤트들)
   - -> consequences (이후 이벤트들)
   - 글로브 위에 화살표로 시각화
   - 클릭 -> 해당 이벤트로 이동
```

### 3. 영토 오버레이 (글로브 위)
```
NEW API 필요: GET /territories?year={currentYear}
UI: 글로브 위 반투명 폴리곤
   - 시간 슬라이더 움직이면 영토가 변함
   - 제국/왕국 이름 라벨
   - 클릭 -> 해당 영토의 LocationCard
```

### 4. 시간별 지명 변화 (LocationCard 내)
```
NEW API 필요: GET /locations/{id}/names
UI: 타임라인 형태
   - "Constantinople (330~1453) -> Istanbul (1453~)"
   - "Byzantium (667 BCE~330 CE) -> Constantinople -> Istanbul"
```

### 5. 위키데이터 속성 확장 (PersonCard 내)
```
GET /properties/person/{id}
현재 9개 -> 25+ 주요 속성 표시
   - 교육기관 (P69), 직업 (P106), 수상 (P166)
   - 종교 (P140), 국적 (P27), 스승 (P1066), 학생 (P802)
```

### 6. 스레드 (ContextDrawer 내)
```
GET /threads -> 인물별 이벤트 스레드
UI: "알렉산더의 여정" -> 시간순 이벤트 카드
   - 클릭 -> 글로브가 해당 위치로 fly
```

---

## 작업량

| 항목 | 수량 |
|------|------|
| 새 컴포넌트 | ~15개 (3,000줄) |
| 수정 컴포넌트 | ~5개 (기존 로직 재활용) |
| 새 API | 3개 (territories, event_relationships, location_names) |
| deprecated 이동 | ~20개 파일 |

---

## 장점
- 데이터 모델 100% 활용
- 모달 0개 = 글로브 항상 보임
- 아이도 이해: "지구본 누르면 뭔가 나옴"
- 확장성 최고 (새 데이터 = 새 레이어)

## 단점
- 작업량 최대
- 기존 코드 대부분 재작성
- 3개 새 API 엔드포인트 필요
- 리스크: 기존에 작동하던 것도 깨질 수 있음

## 지표

| 항목 | 값 |
|------|-----|
| 모달 수 | 0 |
| 데이터 활용률 | 100% |
| 중복 제거율 | 100% |
| 아이 친화성 | ★★★★★ |
| 글로브 중심성 | ★★★★★ |
| 리스크 | 높음 |
