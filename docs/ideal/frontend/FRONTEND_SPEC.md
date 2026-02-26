# 프론트엔드 구현 기획서 v2

이 문서는 코드를 쓰기 전에 승인되어야 한다.
모든 화면, 모든 인터랙션, 모든 컴포넌트의 동작을 정의한다.

**v1 → v2 주요 변경**:
- 사이드바에 쑤셔넣지 않는다 → **글로브 위 플로팅 UI + 풀스크린**
- 이벤트 개별 마커 → **로케이션 노드에 이벤트 귀속**
- 맵 자동 전환 → **카메라 모드 버튼으로 수동 전환**
- WorldBriefing 고정 → **줌 레벨 연동 (글로벌=시대, 지역=지역설명)**
- ViewportFeed 단순 → **전체/이벤트/인물 탭 + 정렬**
- 히스토리 체인 없음 → **이전←현재→다음 순차 탐색**
- 소스 패널 → **소스 모달**
- 모바일 없음 → **모바일 동시 설계**
- FGO 서번트 미약 → **전용 경험 통합**

**기반 문서**:
- `docs/ideal/` 전체 (철학/경험/줌/시간/관계/훅/보조바퀴)
- `docs/ideal/frontend/BACKEND_INVENTORY.md` (데이터 구조)
- `docs/ideal/frontend/API_CAPABILITIES.md` (사용 가능한 API)
- `docs/ideal/frontend/DESIGN_RATIONALE.md` (설계 결정 배경)

---

## 1. 설계 철학

### 1.1 글로브 = 인터페이스

사이드바, 메뉴, 탭은 보조다. **글로브가 주인공**이다.
사이드바에 6개 탭을 쑤셔넣는 것은 전통적 웹앱 사고방식이고, CHALDEAS에는 맞지 않는다.

- 글로브 위에 **플로팅 버튼**으로 기능에 접근
- 상세 정보는 **풀스크린** 또는 **오버레이 패널**
- 사이드바 서랍은 최소화 (검색 + 설정 정도)

### 1.2 로케이션 노드 시스템

글로브에 이벤트를 하나하나 찍지 않는다.
**로케이션 노드**만 글로브에 표시하고, 이벤트는 노드에 귀속된다.

- COSMIC: 문명권 노드 ("Classical Greece", "Han Dynasty")
- CONTINENTAL: 주요 도시/지역 노드 ("Athens", "Rome", "Chang'an")
- REGIONAL: 전장/도시 노드 ("Thermopylae", "Marathon")
- LOCAL: 세부 위치

노드를 클릭하면 해당 시대+장소의 이벤트/인물 목록이 나온다.

### 1.3 이벤트 계층 그룹핑

줌 레벨에 따라 이벤트 계층을 올리거나 내린다.

예: Hundred Years' War의 하위 이벤트가 3-4개 지역에 흩어져 있으면:
- **CONTINENTAL**: "Hundred Years' War"를 대표 위치 또는 중심점에 하나의 노드로 표시
- **REGIONAL**: "Battle of Agincourt", "Siege of Orleans" 등 주요 하위 이벤트가 각 위치에 노드로 표시
- **LOCAL**: 개별 전투의 세부 하위 이벤트

DB 기반: `event_parents` 테이블의 부모-자식 관계, `temporal_scale` (longue_duree/conjuncture/evenementielle), `hierarchy_level`

API: `GET /events/aggregates` (상위 이벤트), `GET /events/{id}/children` (하위 이벤트), `GET /events/{id}/locations` (aggregate 위치 수집)

### 1.4 FGO 칼데아 명칭 체계

프론트엔드 기능에 FGO 칼데아 서브시스템 이름을 매핑한다.

| 기능 | FGO 명칭 | 원본 역할 | 프론트엔드 역할 |
|------|---------|----------|---------------|
| 글로브 | **CHALDEAS** | 지구 관측 모델 | 3D 글로브 뷰 |
| 맵 뷰 | **SHEBA** | 근미래 관측 렌즈 | 2D 맵 뷰 (근접 관측) |
| 히스토리 체인 탐색 | **Rayshift** | 시간여행 기술 | 순차 탐색 (이벤트 체인, 생애 흐름, 투어) |
| 콘텐츠 아카이브 | **TRISMEGISTUS** | 중앙 연산 컴퓨터 | 데이터 허브 (풀스크린 탐색) |
| AI 대화 | **LAPLACE** | 기록 전자해 | AI 채팅 (지식의 바다에서 답을 찾는다) |

### 1.5 모바일 동시 설계

데스크톱과 모바일을 동시에 설계한다. 같은 데이터, 다른 인터랙션.

---

## 2. 데스크톱 레이아웃

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                   │
│  ┌──────────────────── WorldBriefing ──────────────────────┐     │
│  │ NOW OBSERVING: 480 BCE — 페르시아 전쟁의 절정기          │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                                                   │
│  ┌──────────┐                                                     │
│  │ Viewport │              G L O B E                              │
│  │ Feed     │            (풀스크린)                                │
│  │          │                                                     │
│  │ [전체]   │                                ┌──────────────┐     │
│  │ [이벤트] │                                │ Narrative    │     │
│  │ [인물]   │                                │ Panel        │     │
│  │          │                                │ (클릭 시)    │     │
│  └──────────┘                                └──────────────┘     │
│                                                                   │
│  ┌── 플로팅 버튼 ──────────────────────────────────────────┐     │
│  │  [🔍]  [TRISMEGISTUS]  [Rayshift]  [LAPLACE]  [☰]     │     │
│  └──────────────────────────────────────────────────────────┘     │
│                                                                   │
│  ═══════════════ UnifiedTimeline (하단) ════════════════════     │
│                                                                   │
│  카메라: [ CHALDEAS ] [ SHEBA ] [ Rayshift ]                     │
│  스킨:  [ 블루 마블 ] [ 홀로 ] [ 나이트 ]                         │
└─────────────────────────────────────────────────────────────────┘
```

### 항상 보이는 요소 (5개)

| 요소 | 위치 | 역할 |
|------|------|------|
| **Globe** | 중앙 풀스크린 | 인터페이스의 핵심 |
| **WorldBriefing** | 상단 오버레이 | 현재 관측 컨텍스트 (줌 레벨 연동) |
| **ViewportFeed** | 좌측 오버레이 | 현재 뷰포트의 이벤트/인물 (탭+정렬) |
| **UnifiedTimeline** | 하단 | 시간 조작 |
| **플로팅 버튼** | 하단 또는 우측 | 기능 진입점 |

### 플로팅 버튼 (글로브 위)

사이드바 탭 대신, 글로브 위에 플로팅 버튼을 배치한다.

| 버튼 | 아이콘 | 클릭 시 | 설명 |
|------|-------|--------|------|
| **검색** | 🔍 | 검색 오버레이 열림 | 통합 텍스트 검색 |
| **TRISMEGISTUS** | ✦ | 풀스크린 아카이브 | 시대탐색, FGO, 역사, 문학, 음악 |
| **Rayshift** | ⟳ | 히스토리 체인 모드 | 순차 탐색 (투어/체인/생애) |
| **LAPLACE** | ◎ | 채팅 패널 열림 | AI 대화 |
| **메뉴** | ☰ | 설정/기타 서랍 | 언어, 설정, 법적 고지 |

### 클릭 시 나타나는 요소

| 요소 | 트리거 | 형태 | 역할 |
|------|--------|------|------|
| **NarrativePanel** | 노드/카드 클릭 | 우측 패널 (380px) | 이벤트/인물/장소 상세 |
| **TRISMEGISTUS** | ✦ 버튼 | 풀스크린 | 데이터 아카이브 허브 |
| **Rayshift 모드** | ⟳ 버튼 또는 체인 클릭 | 하단 오버레이 | 이전←현재→다음 순차 탐색 |
| **LAPLACE Chat** | ◎ 버튼 | 우하단 플로팅 | AI 채팅 |
| **소스 모달** | 출처 클릭 | 중앙 모달 | 출처 상세 (기존 컨텍스트 유지) |
| **검색 오버레이** | 🔍 버튼 | 상단 드롭다운 | 통합 검색 + 자동완성 |
| **DeepReadModal** | WorldBriefing "더 읽기" | 풀스크린 | 시대 심층 읽기 |
| **HistoryViewer** | History 에세이 클릭 | 풀스크린 | 에세이 읽기 |
| **HistoryEditor** | 에세이 작성 | 풀스크린 모달 | 에세이 편집 |
| **메뉴 서랍** | ☰ 버튼 | 좌측 슬라이드 (좁음) | 설정, 언어, About |

---

## 3. 모바일 레이아웃

모바일에서는 3D 글로브가 현실적으로 어렵다. 완전히 다른 뷰를 제공한다.

### 3.1 기본 화면

```
┌─────────────────────┐
│ [☰] CHALDEAS  [🔍]  │  ← 상단 바
│                      │
│ ┌──────────────────┐ │
│ │                  │ │
│ │   2D 맵          │ │  ← Leaflet/Mapbox (화면 상반부)
│ │   (터치 드래그)   │ │
│ │                  │ │
│ └──────────────────┘ │
│                      │
│ ┌──────────────────┐ │
│ │ WorldBriefing    │ │  ← 현재 시대/지역 한 줄 요약
│ │ 480 BCE: 페르시아 │ │
│ └──────────────────┘ │
│                      │
│ ┌──────────────────┐ │
│ │ Feed Card 1      │ │  ← 스크롤 가능 피드
│ │ Feed Card 2      │ │
│ │ Feed Card 3      │ │
│ │ ...              │ │
│ └──────────────────┘ │
│                      │
│ ══ Timeline (스와이프) ══│  ← 좌우 스와이프로 시간 이동
│                      │
│ [✦] [⟳] [◎] [☰]    │  ← 하단 탭 바
└─────────────────────┘
```

### 3.2 모바일 원칙

| 데스크톱 | 모바일 |
|---------|--------|
| 3D 글로브 (풀스크린) | 2D 맵 (상반부) + 피드 (하반부) |
| 좌측 ViewportFeed | 맵 아래 스크롤 피드 |
| 우측 NarrativePanel (380px) | 풀스크린 바텀시트 (위로 스와이프) |
| 플로팅 버튼 | 하단 탭 바 |
| WorldBriefing 오버레이 | 맵과 피드 사이 한 줄 배너 |
| 타임라인 드래그 | 좌우 스와이프 |
| 풀스크린 모달 | 같은 풀스크린 |
| Rayshift 체인 탐색 | 좌우 스와이프 카드 |

### 3.3 모바일 인터랙션

| 동작 | 결과 |
|------|------|
| 맵 드래그 | 위치 이동 (피드 자동 업데이트) |
| 맵 핀치 줌 | 줌 레벨 변경 |
| 노드 탭 | 바텀시트로 상세 보기 |
| 타임라인 스와이프 | 시간 이동 |
| 피드 카드 탭 | 바텀시트로 상세 보기 |
| 바텀시트 위로 당기기 | 풀스크린 상세 |
| Rayshift 카드 좌우 스와이프 | 이전/다음 단계 |

### 3.4 모바일 브레이크포인트

```
Desktop: ≥ 1024px — 글로브 + 플로팅 패널
Tablet:  768-1023px — 글로브 (축소) + 오버레이 패널
Mobile:  < 768px — 2D 맵 + 피드 + 바텀시트
```

---

## 4. 카메라 모드

상단 또는 좌상단에 카메라 모드 버튼. 스킨 버튼은 별도.

### 4.1 카메라 모드 (뷰 전환)

```
[ CHALDEAS ] [ SHEBA ] [ Fly ]
```

| 모드 | 설명 | 조작 |
|------|------|------|
| **CHALDEAS** | 3D 글로브 궤도 뷰 (기본) | 드래그 회전, 스크롤 줌 |
| **SHEBA** | 2D 맵 뷰 (근접 관측) | Leaflet/Mapbox, 드래그 팬, 스크롤 줌 |
| **Fly** | 1인칭 비행 모드 | WASD 이동, QE 회전, RF 고도 |

- **자동 전환 제거**: altitude 0.15에서 자동으로 맵으로 바뀌던 것을 제거
- SHEBA 버튼을 눌러야만 2D 맵으로 전환
- CHALDEAS 버튼을 눌러야만 3D 글로브로 복귀
- 모든 모드에서 **같은 마커/노드 시스템** 유지

### 4.2 스킨 (글로브 텍스처)

```
[ 블루 마블 ] [ 홀로 ] [ 나이트 ]
```

| 스킨 | 설명 |
|------|------|
| **블루 마블** | 현실적 지구 텍스처 (기본) |
| **홀로** | FGO 칼데아스 홀로그램 스타일 (격자+폴리곤) |
| **나이트** | 야간 도시 불빛 |

스킨은 CHALDEAS 모드에서만 적용. SHEBA(맵)에서는 CartoDB 다크 타일.

---

## 5. WorldBriefing (상단 오버레이)

**핵심 변경**: 줌 레벨에 따라 내용이 바뀐다.

### 5.1 줌 레벨별 내용

Timeline 하단 바가 이미 시대 라벨과 연도를 보여주므로, WorldBriefing은 **서사적 요약**에 집중한다.
멀리서는 한 줄, 가까이서는 상세.

| 줌 레벨 | WorldBriefing 형태 | 내용 | 데이터 소스 |
|---------|-------------------|------|-----------|
| **COSMIC** | 한 줄 (미니멀) | "동서 문명이 병렬로 번성하던 시대" | `period_narratives.headline` |
| **CONTINENTAL** | 한 줄 (미니멀) | "페르시아 전쟁의 절정기 — 동서 충돌" | `period_narratives.headline` |
| **REGIONAL** | 상세 (펼침) | "그리스: 아테네 민주주의의 황금기. 페리클레스가..." | `GET /timeline/periods/{start}` → regional narrative |
| **LOCAL** | 상세 (펼침) | "테르모필레: 좁은 해안 협곡, 스파르타의 최후 방어선..." | `GET /locations/{id}` 또는 entity_narrative |

### 5.2 표시 구조

```
┌─ WorldBriefing ──────────────────────────────────────────────┐
│ NOW OBSERVING: 480 BCE                                        │
│ "페르시아 전쟁의 절정기. 레오니다스가 테르모필레에서..."       │
│                                              [더 읽기] [숨기기]│
└───────────────────────────────────────────────────────────────┘
```

- "더 읽기" → DeepReadModal (풀스크린, 시대 심층 분석)
- 시간 이동 시 자동 업데이트
- 줌/팬 시 자동 업데이트 (debounced)

---

## 6. ViewportFeed (좌측 오버레이)

**핵심 변경**: 탭 + 정렬 시스템. 글로브의 동반자.

### 6.1 구조

```
┌─ ViewportFeed ──────────────┐
│ [ 전체 | 이벤트 | 인물 ]     │  ← 뷰 탭
│ 정렬: 중요도▼ [시간] [거리]  │  ← 정렬 옵션
│ ─────────────────────────── │
│ ★★★★★ Battle of Thermopylae│  ← 가장 중요한 것이 위
│ 480 BCE · Military          │
│ ─────────────────────────── │
│ ★★★★★ Leonidas I           │
│ King of Sparta              │
│ ─────────────────────────── │
│ ★★★★☆ Battle of Salamis    │
│ 480 BCE · Military          │
│ ─────────────────────────── │
│ ★★★★☆ Xerxes I             │
│ King of Persia              │
│ ─────────────────────────── │
│ ...                         │
│ [접기 ◀]                    │
└─────────────────────────────┘
```

### 6.2 뷰 탭

| 탭 | 표시 내용 | API |
|----|---------|-----|
| **전체** | 이벤트 + 인물 혼합, importance 통합 정렬 | `GET /feed` |
| **이벤트** | 이벤트만. 카테고리 필터 가능 (전쟁/정치/과학...) | `GET /events` |
| **인물** | 인물만. 도메인 필터 가능 (군사/정치/학자...) | `GET /persons` |

### 6.3 정렬 옵션

| 정렬 | 설명 |
|------|------|
| **중요도** (기본) | importance 높은 순. 해당 시대+지역에서 가장 중요한 것이 위로 |
| **시간** | 연대순. 가장 오래된 것 또는 가장 최근 것 |
| **거리** | 현재 카메라 중심에서 가까운 순 |

### 6.4 줌 레벨 연동 시간 범위

| 줌 레벨 | 시간 범위 | 이유 |
|---------|----------|------|
| COSMIC | ±200년 | 문명 단위 |
| CONTINENTAL | ±100년 | 전쟁/운동 단위 |
| REGIONAL | ±25년 | 세대 단위 |
| LOCAL | ±10년 | 사건 단위 |

### 6.5 인터랙션

- 카드 클릭 → NarrativePanel 열림 + 글로브 마커 하이라이트
- 글로브 회전/줌/시간 이동 시 자동 업데이트 (debounced 300ms)
- 접기/펼치기 토글

---

## 7. 글로브 마커 시스템

### 7.1 로케이션 노드

글로브에는 **로케이션 노드**만 표시한다. 이벤트 텍스트 라벨은 표시하지 않는다.

| 줌 레벨 | 노드 표시 | 노드 크기 | 정보 표시 |
|---------|----------|----------|----------|
| **COSMIC** | Tier 1 도시만 (Rome, Athens, Chang'an, Memphis...) | 이벤트 밀도 비례 | 문명권 이름 |
| **CONTINENTAL** | Tier 1-2 도시/지역 | 이벤트 수 비례 | 도시 이름 + 이벤트 수 배지 |
| **REGIONAL** | Tier 1-3 + 전장/성소 | importance 비례 | 장소 이름 |
| **LOCAL** | 모든 위치 | 균일 | 장소 이름 + 세부 이벤트 |

### 7.2 노드 클릭 시

노드를 클릭하면 해당 시대+장소의 이벤트/인물 목록이 팝업으로 표시된다.

```
┌─ Athens (480 BCE) ────────────┐
│ Events (3):                    │
│  · Battle of Salamis ★★★★★    │
│  · Evacuation of Athens ★★★   │
│  · Themistocles' Strategy ★★★ │
│                                │
│ Persons (2):                   │
│  · Themistocles ★★★★          │
│  · Aristides ★★★              │
└────────────────────────────────┘
```

목록의 항목 클릭 → NarrativePanel 열림.

### 7.3 이벤트 계층 그룹핑

부모-자식 이벤트 관계를 줌 레벨에 따라 활용:

```
COSMIC:
  "Classical Greece" (longue_duree) → Athens 노드에 표시

CONTINENTAL:
  "Greco-Persian Wars" (conjuncture) → 그리스 지역 대표 노드에 표시
  "Peloponnesian War" (conjuncture) → 그리스 지역 대표 노드에 표시

REGIONAL:
  "Battle of Thermopylae" (evenementielle) → Thermopylae 노드
  "Battle of Salamis" (evenementielle) → Salamis 노드
  "Battle of Marathon" (evenementielle) → Marathon 노드

LOCAL:
  "Day 1: Initial Defense" → Thermopylae 노드 내 하위
  "Day 2: Betrayal" → Thermopylae 노드 내 하위
```

**부모 이벤트의 위치 결정**:
- `GET /events/{id}/locations` (aggregate 모드) → 하위 이벤트 위치들 수집
- 대표 위치 선택: 가장 중요한 하위 이벤트의 위치, 또는 위치들의 중심점
- DB에 이벤트 자체 좌표가 있으면 그것을 우선 사용

### 7.4 인과관계 표시

REGIONAL 줌에서 같은 뷰포트 내 이벤트 간 인과관계 화살표를 표시:

```
Marathon (490 BCE) ──→ Thermopylae (480 BCE) ──→ Salamis (480 BCE)
```

API: `GET /events/{id}/relationships` → causes/enables/follows

---

## 8. NarrativePanel (우측 패널)

마커/카드 클릭 시 우측에서 슬라이드. 서사가 메타데이터보다 먼저.

### 8.1 이벤트 모드

```
┌─ NarrativePanel ────────────────┐
│ [✕]                              │
│                                  │
│ Battle of Thermopylae            │
│ 480 BCE · Thermopylae            │
│ ★★★★★ · fact                    │
│                                  │
│ ─── 이야기 ───                   │
│ 레오니다스 1세가 300명의          │
│ 스파르타 병사와 함께...           │
│                                  │
│ ─── 원인과 결과 ───              │  ← /events/{id}/relationships
│ ← Marathon (490 BCE)             │
│ → Salamis (480 BCE)              │
│ [🔗 Rayshift: 인과 체인 따라가기] │
│                                  │
│ ─── 참여 인물 ───                │  ← /events/{id} → persons
│ 👤 Leonidas I (commander)        │
│ 👤 Xerxes I (invader)            │
│                                  │
│ ─── Story (하위 사건 타임라인) ── │  ← /events/{id}/children
│ ●─ Day 1: Initial Defense        │     항상 펼쳐진 타임라인 형태
│ ●─ Day 2: Betrayal               │     (토글 아님, 즉시 보임)
│ ●─ Day 3: Last Stand             │     하위 이벤트 = 이 이벤트의 히스토리
│                                  │
│ ─── 관련 읽을거리 ───            │  ← /histories (entity_type/id 필터)
│ 📜 "The Persian Wars"            │     (있으면 표시, 없으면 생략)
│                                  │
│ ─── 출처 ───                    │  ← sources (클릭 시 모달)
│ 📖 Herodotus, Histories         │
└──────────────────────────────────┘
```

### 8.2 인물 모드

```
┌─ NarrativePanel ────────────────┐
│ [✕]                              │
│                                  │
│ Leonidas I                       │
│ King of Sparta                   │
│ 540 BCE — 480 BCE                │
│                                  │
│ ─── 전기 ───                    │  ← /persons/{id}/narrative
│ 스파르타의 아기아드 왕조...       │
│                                  │
│ ─── 생애 흐름 ───                │  ← /persons/{id}/flow
│ 540 Sparta (출생)                │
│  ↓                               │
│ 490 Sparta (왕위 계승)           │
│  ↓                               │
│ 480 Thermopylae (최후)           │
│ [🔗 Rayshift: 생애 따라가기]     │
│ [🌍 글로브에서 경로 보기]        │
│                                  │
│ ─── 관계 ───                    │  ← /persons/{id}/relations
│ 👤 Gorgo (아내, ★★★★★)          │
│ 👤 Xerxes I (적, ★★★★)          │
│                                  │
│ ─── FGO ───                     │  ← /servants/by-person/{id}
│ ⚔ Leonidas I (Lancer, ★★)       │
│ [서번트 상세 보기]               │
│                                  │
│ ─── 관련 읽을거리 ───            │  ← /persons/{id}/histories
│ 📜 "Spartan Kings"               │
│                                  │
│ ─── 출처 ───                    │  ← /persons/{id}/sources (모달)
│ 📖 Herodotus, Histories         │
│                                  │
│ ─── 속성 ───                    │  ← /persons/{id}/properties
│ 국적: Sparta                     │
│ 직업: King, General              │
└──────────────────────────────────┘
```

### 8.3 인터랙션

| 요소 | 클릭 시 |
|------|---------|
| 원인/결과 이벤트 | 글로브 비행 + 시간 이동 + NarrativePanel 전환 |
| "Rayshift: 인과 체인" | Rayshift 모드 진입 (§9) |
| 참여 인물 | NarrativePanel 인물 모드로 전환 |
| 하위 사건 | NarrativePanel 해당 이벤트로 전환 |
| 생애 흐름 항목 | 글로브 비행 + 시간 이동 |
| "Rayshift: 생애 따라가기" | Rayshift 모드 진입 (§9) |
| "글로브에서 경로 보기" | 글로브에 생애 경로 아크 표시 |
| 관계 인물 | NarrativePanel 해당 인물로 전환 |
| FGO 서번트 | 서번트 상세 뷰 (§11) |
| History 에세이 | HistoryViewer (풀스크린) |
| 출처 | **소스 모달** (§10) |

---

## 9. Rayshift — 순차 탐색 모드

> **통합 안내**: Rayshift는 **히스토리 시프트**의 네비게이션 엔진으로 통합되었습니다.
> 하단 오버레이 UI → 전체화면 모달로 변경. 데이터 모델은 HistoricalChain → HistoryShift로 리네이밍.
> 최신 기획은 → [HISTORY_SHIFT.md](../HISTORY_SHIFT.md) 참조.
> 아래 내용은 이전 기획으로, 참고용으로 유지됩니다.

**핵심 신규 기능**: 히스토리 체인, 생애 흐름, 가이드 투어를 하나의 인터페이스로.

### 9.1 컨셉

FGO의 레이시프트처럼, **시간과 공간을 따라 이동하면서 이야기를 순서대로 체험**한다.

> **중요: Rayshift = 기존 History 시스템의 진화**
>
> 기존의 History(에세이) 시스템은 텍스트 기반이었다. Rayshift는 이것을
> **글로브 위에서 체험하는 인터랙티브 형태**로 진화시킨 것이다.
>
> - History 에세이의 entity 태그 → Rayshift의 스텝 좌표
> - History의 era_start/end → Rayshift의 시간 이동
> - History의 featured entities → Rayshift의 정거장
> - 이벤트의 hierarchy children → 해당 이벤트의 Story (자동 Rayshift 후보)
>
> History 에세이는 "읽기"용으로 여전히 존재하지만,
> 핵심 탐색 경험은 Rayshift가 담당한다.

진입 방법:
1. NarrativePanel의 "Rayshift: 인과 체인 따라가기" 클릭
2. NarrativePanel의 "Rayshift: 생애 따라가기" 클릭
3. 플로팅 버튼 ⟳ 클릭 → 투어 선택
4. TRISMEGISTUS에서 투어/체인 선택

### 9.2 UI (데스크톱)

Rayshift 모드가 활성화되면 하단에 오버레이:

```
┌─ Rayshift ───────────────────────────────────────────────────┐
│                                                                │
│  [◀ 이전]                                         [다음 ▶]    │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ Step 4/7: Battle of Thermopylae                        │   │
│  │ 480 BCE · Thermopylae                                  │   │
│  │                                                        │   │
│  │ 레오니다스 1세가 300명의 스파르타 병사와 함께            │   │
│  │ 크세르크세스의 대군을 3일간 저지했다.                    │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                │
│  ○───○───○───●───○───○───○                                    │
│  1   2   3   4   5   6   7                                    │
│                                           [✕ 나가기]          │
└────────────────────────────────────────────────────────────────┘
```

### 9.3 UI (모바일)

풀스크린 카드. 좌우 스와이프로 이전/다음.

```
┌─────────────────────┐
│ Rayshift  Step 4/7   │
│ [✕]                  │
│                      │
│ ┌──────────────────┐ │
│ │                  │ │
│ │   2D 맵          │ │  ← 현재 위치 표시
│ │   (자동 이동)     │ │
│ │                  │ │
│ └──────────────────┘ │
│                      │
│ Battle of            │
│ Thermopylae          │
│ 480 BCE              │
│                      │
│ 레오니다스 1세가...   │
│                      │
│ ○─○─○─●─○─○─○       │
│                      │
│ ◀ 스와이프 ▶         │
└─────────────────────┘
```

### 9.4 동작 시퀀스

"다음" 클릭 시:
1. 다음 단계 데이터 fetch
2. 글로브(또는 맵)가 해당 위치로 **비행** (flyToLocation)
3. 타임라인이 해당 연도로 **이동** (setCurrentYear)
4. Rayshift 카드가 새 내용으로 **전환**
5. 글로브 마커가 **하이라이트**

### 9.5 Rayshift의 3가지 모드

| 모드 | 데이터 소스 | 진입 | 예시 |
|------|-----------|------|------|
| **인과 체인** | `GET /events/{id}/relationships` 재귀 | 이벤트의 "인과 체인 따라가기" | Marathon → Thermopylae → Salamis → Plataea |
| **생애 흐름** | `GET /persons/{id}/flow` | 인물의 "생애 따라가기" | Pella → Granicus → Issus → Gaugamela → Babylon |
| **가이드 투어** | shebaEpisodes 또는 History 에세이 | ⟳ 버튼 → 투어 목록 | "그리스-페르시아 전쟁 7단계" |

### 9.6 투어 목록 (⟳ 버튼 클릭 시)

```
┌─ Rayshift: 투어 선택 ────────────────┐
│                                        │
│ ── 시대별 투어 ──                      │
│ 📍 그리스-페르시아 전쟁 (7단계)        │
│ 📍 알렉산더의 정복 (12단계)            │
│ 📍 로마의 흥망 (15단계)                │
│                                        │
│ ── FGO 특이점 투어 ──                  │
│ 🎮 제1특이점: 오를레앙 (잔 다르크)     │
│ 🎮 제7특이점: 바빌로니아 (길가메시)    │
│                                        │
│ ── 인물별 투어 ──                      │
│ 👤 알렉산더의 여정 (12단계)            │
│ 👤 카이사르의 갈리아 전쟁 (8단계)      │
│                                        │
│ ── 장소별 투어 ──                      │
│ 🏛 이스탄불의 3000년 (10단계)          │
│ 🏛 로마: 영원의 도시 (12단계)          │
└────────────────────────────────────────┘
```

---

## 10. 소스 모달

출처를 클릭하면 **모달**로 열린다. 현재 보고 있는 NarrativePanel 등의 컨텍스트를 유지.

> **핵심 원칙: 소스 = 원문 열람**
>
> 소스 클릭 시 외부 링크(새 탭)로 보내지 않는다.
> 모달 안에서 원문을 직접 보여준다.
> - Wikipedia 소스 → Wikipedia 본문을 모달 안에서 렌더링 (iframe 또는 API fetch)
> - Book 소스 → 관련 구절(text_mentions)을 인용 형태로 표시
> - 외부 링크는 "원본 페이지 열기" 보조 버튼으로만 제공
>
> NarrativeCard의 Sources 섹션도 `<a href>` 외부 링크가 아닌,
> `onSourceClick(sourceId)` → SourceBrowser 모달 열기로 동작해야 한다.

```
┌─────────────────── 소스 모달 ──────────────────┐
│ [✕]                                              │
│                                                  │
│ 📖 Herodotus, Histories                         │
│                                                  │
│ 저자: Herodotus                                  │
│ 시대: ~430 BCE                                   │
│ 분류: 역사서                                     │
│                                                  │
│ ── 이 출처에서 언급된 인물 ──                    │
│ Leonidas I · Xerxes I · Themistocles · Darius I  │
│                                                  │
│ ── 관련 구절 ──                                  │
│ "At Thermopylae, Leonidas held the pass..."      │
│ "The Greek fleet at Salamis..."                   │
│                                                  │
│ ── Wikipedia ──                                  │
│ [📄 전문 보기]                                   │
└──────────────────────────────────────────────────┘
```

API: `GET /sources/{id}`, `GET /sources/{id}/persons`, `GET /sources/{id}/mentions`, `GET /sources/{id}/wiki`

---

## 11. FGO 서번트 경험

### 11.1 진입 경로

FGO 서번트에 접근하는 경로:

1. **NarrativePanel**: 인물 상세에 "FGO" 섹션 → 매핑된 서번트 표시
2. **TRISMEGISTUS**: FGO 아카이브 (특이점, 이문대, 서번트 목록)
3. **Rayshift**: FGO 특이점 투어
4. **검색**: 서번트 이름으로 검색

### 11.2 서번트 상세 뷰

NarrativePanel 내에서 또는 별도 패널로:

```
┌─ 서번트 상세 ──────────────────┐
│ [✕]                             │
│                                 │
│ ⚔ Leonidas I                   │
│ Lancer · ★★                    │
│                                 │
│ ─── FGO 설정 ───               │
│ "300의 용사를 이끈 스파르타의 왕"│
│ 클래스: Lancer                  │
│ 레어도: ★★                     │
│                                 │
│ ─── 역사적 인물 ───             │
│ 👤 Leonidas I (540-480 BCE)    │
│ [🌍 역사적 인물로 이동]         │
│                                 │
│ ─── FGO vs 역사 비교 ───       │  ← /servants/{name}/comparison
│ FGO: 보구 "테르모필레 에나리시오"│
│ 역사: 실제 테르모필레 전투      │
│                                 │
│ ─── 관련 서번트 ───             │
│ 🎮 Xerxes I (없음, 적)         │
│ 🎮 Gorgo (없음, 아내)          │
│ 🎮 Iskandar (Rider, ★★★★★)    │
│                                 │
│ ─── 등장 작품 ───               │
│ 특이점: 제7특이점 바빌로니아    │
│ 이벤트: 네로제                  │
└─────────────────────────────────┘
```

### 11.3 TRISMEGISTUS 내 FGO 섹션

```
┌─ TRISMEGISTUS: FGO Archive ──────────────────────┐
│                                                     │
│ [ 특이점 ] [ 이문대 ] [ 서번트 ] [ 비교 ]           │
│                                                     │
│ ── 특이점 (Part 1) ──                               │
│ 🔴 제1특이점: 백년전쟁의 성녀 — 오를레앙 1431       │
│ 🔴 제2특이점: 광기의 미개찬리 — 로마 0060           │
│ 🔴 제3특이점: 봉쇄종국사해 — 오케아노스 1573        │
│ ...                                                 │
│ 🔴 제7특이점: 절대마수전선 — 바빌로니아 BC2655      │
│                                                     │
│ 각 특이점 클릭 → 상세 뷰 + [Rayshift 투어 시작]     │
│                                                     │
│ ── 서번트 ──                                        │
│ 클래스: [Saber] [Archer] [Lancer] [Rider] ...       │
│ 검색: [____________________]                        │
│                                                     │
│ ⚔ Gilgamesh (Archer ★★★★★) — 우루크의 영웅왕       │
│ 🏹 Arjuna (Archer ★★★★★) — 인드라의 아들           │
│ 🔱 Leonidas I (Lancer ★★) — 테르모필레의 수호자     │
│ ...                                                 │
└─────────────────────────────────────────────────────┘
```

API: `GET /showcases/fgo/singularities`, `/showcases/fgo/lostbelts`, `/showcases/fgo/servants`, `GET /servants`, `GET /servants/{name}`

---

## 12. TRISMEGISTUS — 풀스크린 데이터 허브

플로팅 버튼 ✦ 클릭 시 열리는 풀스크린 아카이브.

사이드바 탭에 쑤셔넣던 것들을 여기서 풀스크린으로 제공한다.

### 12.1 구조

```
┌─ TRISMEGISTUS ──────────────────────────────────────────────┐
│ [✕]                                                          │
│                                                              │
│ [ 시대 탐색 ] [ FGO ] [ 읽을거리 ] [ 탐색 ]                 │
│                                                              │
│ ────────────────────────────────────────────────────────────  │
│ (선택한 탭의 콘텐츠가 풀스크린으로 표시)                      │
└──────────────────────────────────────────────────────────────┘
```

### 12.2 탭별 내용

| 탭 | 내용 | API |
|----|------|-----|
| **시대 탐색** | 50년 단위 시대 목록 → 클릭 → 시대 상세 (이벤트/인물/지역별 서사) | `/timeline/periods`, `/timeline/periods/{start}/events`, `/timeline/periods/{start}/persons` |
| **FGO** | 특이점/이문대/서번트 브라우저 (§11.3) | `/showcases/fgo/*`, `/servants` |
| **읽을거리** | History 에세이 목록 + 역사/문학/음악 기사 + 작성 | `/histories`, `/showcases/history`, `/showcases/literature`, `/showcases/music` |
| **탐색** | 인물/장소/이벤트 고급 탐색 (필터, 정렬, 페이지네이션) | `/explore/*` |

### 12.3 시대 탐색 → 글로브 연동

시대 상세에서 이벤트/인물 클릭 시:
1. TRISMEGISTUS 닫힘
2. 글로브가 해당 위치로 비행
3. 타임라인이 해당 연도로 이동
4. NarrativePanel이 열림

---

## 13. 줌 레벨별 경험 (종합)

### COSMIC (지구 전체)

| 항목 | 내용 |
|------|------|
| **노드** | Tier 1 도시만 (문명 중심지), 이벤트 밀도 원 |
| **이벤트 계층** | longue_duree만 (문명, 대제국) |
| **인물** | 숨김 |
| **WorldBriefing** | 한 줄 서사 요약 (headline) |
| **ViewportFeed** | 문명 단위 요약, ±200년 |
| **영토** | 대제국 단위 |

### CONTINENTAL (대륙/지역권)

| 항목 | 내용 |
|------|------|
| **노드** | Tier 1-2 도시/지역, 이벤트 수 배지 |
| **이벤트 계층** | conjuncture + longue_duree (전쟁, 운동) |
| **인물** | importance ≥ 80만 |
| **WorldBriefing** | 한 줄 서사 요약 (headline) |
| **ViewportFeed** | 전쟁/운동 단위, ±100년 |
| **영토** | 제국/왕국 단위 |

### REGIONAL (국가/지역)

| 항목 | 내용 |
|------|------|
| **노드** | Tier 1-3 + 전장/성소, 인과관계 화살표 |
| **이벤트 계층** | 모든 scale (개별 전투 포함) |
| **인물** | importance ≥ 40 |
| **WorldBriefing** | 지역 요약 (regional narrative) |
| **ViewportFeed** | 개별 이벤트/인물, ±25년 |
| **영토** | 도시국가/소왕국 |

### LOCAL (도시/전장)

| 항목 | 내용 |
|------|------|
| **노드** | 모든 위치, 하위 이벤트 표시 |
| **이벤트 계층** | 최하위 (하루 단위) |
| **인물** | 전원 표시 |
| **WorldBriefing** | 장소/이벤트 설명 (entity_narrative) |
| **ViewportFeed** | 하위 이벤트 + 전 참여 인물, ±10년 |
| **영토** | 상세 지형 |

---

## 14. 시간 이동 경험

타임라인을 드래그하면 6가지가 변한다:

| # | 변화 | 데이터 소스 |
|---|------|-----------|
| 1 | 노드의 이벤트 배지가 바뀜 | events.date_start/end |
| 2 | 인물 아이콘이 나타나고 사라짐 | persons.birth_year/death_year |
| 3 | 장소 이름이 바뀜 | location_names.valid_from/until |
| 4 | 영토 오버레이가 바뀜 | territory_locations.valid_from/until |
| 5 | WorldBriefing이 바뀜 | period_narratives |
| 6 | ViewportFeed이 바뀜 | feed API |

### 성능 고려
- 드래그 중 API debounce (300ms)
- location_names 프론트엔드 캐시
- 영토 50년 단위 업데이트
- 마커는 뷰포트 내에서만

### 재생 모드
- 시간 자동 흐름 (기본 10년/초)
- 속도: 1년/초, 10년/초, 50년/초, 100년/초
- **글로브 회전 속도와 독립** (원칙 4)

---

## 15. 인과 흐름 (Causal Flow)

NarrativePanel에서 "원인/결과" 클릭 시의 단일 점프는 그대로 유지:

1. 다음 이벤트 fetch (`GET /events/{id}`)
2. 글로브 비행 (flyToLocation)
3. 타임라인 이동 (setCurrentYear)
4. NarrativePanel 전환

"Rayshift: 인과 체인 따라가기"를 클릭하면 Rayshift 모드(§9)로 진입하여 전체 체인을 순차 탐색.

---

## 16. 인물 생애 흐름 (Person Flow)

NarrativePanel 인물 모드의 "글로브에서 경로 보기":
1. `GET /persons/{id}/flow` 호출
2. flow 좌표를 글로브 아크로 표시
3. 출생지 → 이벤트1 → ... → 사망지
4. 아크 색상 = 시간순 그라데이션

"Rayshift: 생애 따라가기"를 클릭하면 Rayshift 모드(§9)로 진입하여 생애 단계를 순차 탐색.

---

## 17. 랜딩 / 홈 화면

### 첫 방문 (데스크톱)
```
[글로브가 천천히 돌고 있다]
[메뉴도 없다. 버튼도 없다.]

        C H A L D E A S
        [시작하기]
```

"시작하기" → 글로브가 지중해로 비행, 480 BCE. UI 요소들이 나타남.

### 첫 방문 (모바일)
```
[2D 세계 지도 배경]

   C H A L D E A S
   [시작하기]
```

"시작하기" → 맵이 지중해로 이동, 480 BCE. 피드 카드가 나타남.

### 재방문
- 글로브/맵 + WorldBriefing + ViewportFeed가 바로 보인다
- 마지막 위치/시간 기억 (localStorage)
- "뭘 해야 할지 모르겠어?"에 대한 답:
  1. WorldBriefing "더 읽기"
  2. ViewportFeed 카드 아무거나 클릭
  3. ⟳ Rayshift → 가이드 투어
  4. ✦ TRISMEGISTUS → 아카이브 탐색

---

## 18. 2-탭 규칙 검증

| 보고 싶은 것 | 1탭 | 2탭 | 통과 |
|-------------|-----|-----|------|
| 특정 사건 상세 | 글로브 노드 클릭 → 팝업 | 팝업 내 이벤트 클릭 | ✅ |
| 특정 인물 상세 | ViewportFeed 인물 카드 | (NarrativePanel 열림) | ✅ |
| 인물 생애 흐름 | NarrativePanel 인물 | "생애 흐름" 섹션 스크롤 | ✅ |
| 인과관계 체인 | NarrativePanel 이벤트 | "Rayshift: 인과 체인" 클릭 | ✅ |
| 시대 개요 | WorldBriefing "더 읽기" | (DeepReadModal 열림) | ✅ |
| 가이드 투어 | ⟳ Rayshift 버튼 | 투어 선택 | ✅ |
| FGO 서번트 | ✦ TRISMEGISTUS | FGO 탭 → 서번트 선택 | ✅ |
| FGO 특이점 투어 | ✦ TRISMEGISTUS → FGO | 특이점 → Rayshift 시작 | ✅ (3탭이지만 TRISMEGISTUS 내부) |
| History 에세이 | ✦ TRISMEGISTUS | 읽을거리 탭 → 에세이 클릭 | ✅ |
| 출처 확인 | NarrativePanel 출처 섹션 | 출처 클릭 (모달) | ✅ |
| 검색 | 🔍 버튼 | 결과 클릭 | ✅ |
| 서번트→역사 연결 | NarrativePanel 인물 FGO 섹션 | "역사적 인물로 이동" | ✅ |

---

## 19. 컴포넌트-API 매핑

| 컴포넌트 | 사용 API |
|---------|---------|
| **GlobeContainer** | `/events` (뷰포트+줌 필터), `/events/aggregates`, `/globe/anchor-locations` |
| **MapContainer** | 동일 (2D 렌더링) |
| **WorldBriefing** | `/timeline/periods/{start}` (global + regional), `/locations/{id}` |
| **ViewportFeed** | `/feed` (전체), `/events` (이벤트탭), `/persons` (인물탭) |
| **UnifiedTimeline** | (부모에서 전달) |
| **NarrativePanel (event)** | `/events/{id}`, `/events/{id}/relationships`, `/events/{id}/children`, `/events/{id}/histories` |
| **NarrativePanel (person)** | `/persons/{id}`, `/persons/{id}/narrative`, `/persons/{id}/flow`, `/persons/{id}/relations`, `/persons/{id}/sources`, `/persons/{id}/properties`, `/persons/{id}/histories`, `/servants/by-person/{id}` |
| **Rayshift** | `/persons/{id}/flow`, `/events/{id}/relationships` (재귀), shebaEpisodes, `/histories` |
| **TRISMEGISTUS 시대** | `/timeline/periods`, `/timeline/periods/{start}/events`, `/timeline/periods/{start}/persons` |
| **TRISMEGISTUS FGO** | `/showcases/fgo/*`, `/servants`, `/servants/{name}`, `/servants/{name}/comparison` |
| **TRISMEGISTUS 읽을거리** | `/histories`, `/showcases/history`, `/showcases/literature`, `/showcases/music` |
| **TRISMEGISTUS 탐색** | `/explore/*` |
| **소스 모달** | `/sources/{id}`, `/sources/{id}/persons`, `/sources/{id}/mentions`, `/sources/{id}/wiki` |
| **검색** | `/search` |
| **LAPLACE Chat** | `POST /chat/agent` |
| **HistoryEditor** | `/histories` CRUD |

---

## 20. 검증 체크리스트

### 설계 철학
- [ ] 글로브 = 인터페이스인가? (사이드바에 쑤셔넣지 않았는가?)
- [ ] 서사가 메타데이터보다 먼저 보이는가?
- [ ] 2-탭 규칙을 위반하는 경로가 없는가?
- [ ] 모드 전환(Interest/Expert)이 없는가?
- [ ] 백엔드 API가 전부 어딘가에서 접근 가능한가?
- [ ] 사이드바 대신 플로팅 버튼 + 풀스크린을 쓰고 있는가?

### 로케이션 노드
- [ ] 이벤트 텍스트 라벨이 글로브 위에 직접 표시되지 않는가?
- [ ] 노드 클릭 시 해당 시대+장소의 이벤트 팝업이 나오는가?
- [ ] 줌 레벨에 따라 이벤트 계층이 바뀌는가?
- [ ] 부모 이벤트가 하위 이벤트 위치를 자동 수집하는가?

### 카메라 모드
- [ ] CHALDEAS(글로브)/SHEBA(맵)/Fly 버튼이 있는가?
- [ ] 자동 맵 전환이 제거되었는가?
- [ ] 스킨(블루마블/홀로/나이트)이 별도 버튼인가?

### WorldBriefing
- [ ] COSMIC: 한 줄 서사 요약 (headline)?
- [ ] CONTINENTAL: 한 줄 서사 요약 (headline)?
- [ ] REGIONAL: 지역 요약 (regional narrative)?
- [ ] LOCAL: 장소/이벤트 설명 (entity narrative)?

### ViewportFeed
- [ ] 전체/이벤트/인물 탭이 있는가?
- [ ] 중요도/시간/거리 정렬이 있는가?
- [ ] 줌 레벨에 따라 시간 범위가 동적인가?

### Rayshift
- [ ] 이전←현재→다음 순차 탐색이 작동하는가?
- [ ] 글로브 비행 + 시간 이동이 함께 일어나는가?
- [ ] 인과 체인, 생애 흐름, 가이드 투어 3가지 모드가 있는가?
- [ ] 모바일에서 좌우 스와이프가 작동하는가?

### 소스
- [ ] 출처 클릭 시 모달로 열리는가? (패널이 아니라)
- [ ] 모달이 열려도 기존 NarrativePanel이 유지되는가?

### FGO
- [ ] NarrativePanel에 FGO 섹션이 있는가?
- [ ] TRISMEGISTUS에 FGO 아카이브가 있는가?
- [ ] 서번트→역사적 인물 연결이 작동하는가?
- [ ] FGO 특이점 투어가 Rayshift로 시작되는가?

### 모바일
- [ ] < 768px에서 2D 맵 + 피드 레이아웃인가?
- [ ] 상세 보기가 바텀시트인가?
- [ ] Rayshift가 좌우 스와이프 카드인가?
- [ ] 하단 탭 바가 있는가?

### 시간 이동
- [ ] 타임라인 드래그 시 6가지 변화가 일어나는가?
- [ ] 재생 속도와 글로브 회전이 독립적인가?

### 인과 흐름
- [ ] 이벤트 카드에 원인/결과가 표시되는가?
- [ ] REGIONAL 줌에서 인과관계 화살표가 보이는가?

### 인물
- [ ] 생애 흐름(flow)이 표시되는가?
- [ ] 관계 네트워크가 표시되는가?
- [ ] "글로브에서 경로 보기"가 작동하는가?
