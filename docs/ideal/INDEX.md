# CHALDEAS: Ideal (본질 문서)

이 폴더는 CHALDEAS 프로젝트의 **근본적 본질**을 다룬다.
코드가 아니라 철학을, 구현이 아니라 경험을, 기능이 아니라 목적을 말한다.

모든 기술적 결정, 모든 UI 설계, 모든 데이터 구조는
여기에 적힌 본질에서 출발해야 한다.

---

## 문서 목록

| 문서 | 내용 |
|------|------|
| [PURPOSE.md](./PURPOSE.md) | 왜 CHALDEAS가 존재하는가 |
| [EXPERIENCE.md](./EXPERIENCE.md) | 유저는 무엇을 보고, 느끼고, 하는가 |
| [ZOOM_AS_NARRATIVE.md](./ZOOM_AS_NARRATIVE.md) | 줌은 확대가 아니다. 서사의 해상도다. |
| [TIME_AS_DIMENSION.md](./TIME_AS_DIMENSION.md) | 시간은 필터가 아니다. 세계의 또 하나의 차원이다. |
| [RELATIONSHIPS.md](./RELATIONSHIPS.md) | 사람과 사람, 사건과 사건은 선으로 연결된다 |
| [DB_RATIONALE.md](./DB_RATIONALE.md) | 이 DB 구조가 존재하는 이유 |
| [HOOKS.md](./HOOKS.md) | 역사를 모르는 사람이 왜 이걸 열어보는가 |
| [TRAINING_WHEELS.md](./TRAINING_WHEELS.md) | 초보자의 보조바퀴: 가이드 투어, FGO 서번트, 오늘의 역사 |
| [**HISTORY_SHIFT.md**](./HISTORY_SHIFT.md) | **히스토리 시프트: 시나리오 탐색의 통합 시스템** |
| [DATA_FILLING_PLAN.md](./DATA_FILLING_PLAN.md) | 핵심 데이터 채우기 기획서: 4개 갭, 실행 방법, 비용 |

### TRISMEGISTOS 포털 — 정보 종합 포털 기획

| 문서 | 내용 |
|------|------|
| [TRISMEGISTOS.md](./TRISMEGISTOS.md) | 컨셉: 2-Layer 포털 (매거진 홈 + 컬렉션) |
| [TRISMEGISTOS_FRONTEND.md](./TRISMEGISTOS_FRONTEND.md) | 통합 프론트엔드 기획서 (구, 아래 4문서로 분할) |
| [**PORTAL_01_ARCHITECTURE.md**](./PORTAL_01_ARCHITECTURE.md) | **아키텍처: 중첩 모달 스택, portalStore, z-index, 키보드, 글로브 연결** |
| [**PORTAL_02_MAGAZINE_HOME.md**](./PORTAL_02_MAGAZINE_HOME.md) | **매거진 홈: TodayHero, RecommendationRow, FgoSection, ReadingSection, CollectionGrid** |
| [**PORTAL_03_COLLECTIONS.md**](./PORTAL_03_COLLECTIONS.md) | **컬렉션 페이지 + 아이템 상세: 중첩 모달 Layer 2~3, FGO 특수 레이아웃** |
| [**PORTAL_04_RECOMMENDATIONS.md**](./PORTAL_04_RECOMMENDATIONS.md) | **추천 엔진: 오늘의 역사, 이번 주 추천, "이런 것도 좋아하실 걸요", 맞춤 추천** |
| [**PORTAL_05_ARTICLES.md**](./PORTAL_05_ARTICLES.md) | **아티클 엔티티 링크: 6종 `[Name](entity:type:id)`, /resolve, /suggest-links API** |
| [**PORTAL_06_BIDIRECTIONAL.md**](./PORTAL_06_BIDIRECTIONAL.md) | **SHEBA ↔ Trismegistus 양방향 모드 전환: suspend/resume, 컨텍스트 전달, 상단 모드 바** |

### frontend/ — 프론트엔드 구현을 위한 백엔드 이해 문서

| 문서 | 내용 |
|------|------|
| [BACKEND_INVENTORY.md](./frontend/BACKEND_INVENTORY.md) | 백엔드에 뭐가 있는가 — 전체 테이블 목록과 프론트엔드 관련성 |
| [DESIGN_RATIONALE.md](./frontend/DESIGN_RATIONALE.md) | 왜 이렇게 만들었는가 — 7가지 핵심 설계 결정의 배경 |
| [HISTORY_SYSTEM.md](./frontend/HISTORY_SYSTEM.md) | 히스토리 시스템 — 다중 엔티티 에세이 플랫폼 |
| [API_CAPABILITIES.md](./frontend/API_CAPABILITIES.md) | 프론트엔드가 쓸 수 있는 API 전체 — ~70개 엔드포인트 + 사용 현황 |
| [FRONTEND_SPEC.md](./frontend/FRONTEND_SPEC.md) | 구현 수준 프론트엔드 기획서 — 모든 화면, 인터랙션, 컴포넌트 |

---

## 읽는 순서

1. **PURPOSE** — 먼저 이 프로젝트가 왜 존재하는지 이해한다
2. **EXPERIENCE** — 유저가 실제로 무엇을 경험하는지 그린다
3. **ZOOM_AS_NARRATIVE** — 가장 핵심적인 인터랙션을 깊이 이해한다
4. **TIME_AS_DIMENSION** — 두 번째로 핵심적인 인터랙션을 이해한다
5. **RELATIONSHIPS** — 데이터가 어떻게 연결되어 의미를 만드는지 이해한다
6. **DB_RATIONALE** — 위의 모든 경험을 가능하게 하는 데이터 구조를 이해한다
7. **HOOKS** — 역사를 모르는 사람을 어떻게 끌어들이는가
8. **TRAINING_WHEELS** — 초보자가 시작할 수 있는 구체적 시스템들
9. **HISTORY_SHIFT** — Rayshift, Histories, Historical Chain, Event Hierarchy를 통합한 시나리오 시스템

### 프론트엔드 구현 시
10. **frontend/BACKEND_INVENTORY** — 백엔드에 어떤 데이터가 있는지 파악
11. **frontend/DESIGN_RATIONALE** — 왜 이렇게 설계되었는지 이해
12. **frontend/HISTORY_SYSTEM** — History 에세이 시스템 이해 (→ HISTORY_SHIFT로 통합됨)
13. **frontend/API_CAPABILITIES** — 어떤 API를 쓸 수 있는지 확인
14. **frontend/FRONTEND_SPEC** — 구현 수준의 기획서 (Rayshift → HISTORY_SHIFT로 통합됨)
