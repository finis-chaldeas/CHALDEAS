# 카드 시스템

**상태**: 설계 단계
**관련**: 글로브 마커, 히스토리 시프트, 엔티티 링크, FGO 포탈

---

## 핵심 원칙

### 1. 카드 = 글로브의 기본 단위

카드는 마커 라벨의 "중간 단계"가 아니라, **마커 라벨을 완전히 대체**한다.
현재 히어로 카드(제목+연도만 표시)를 카드 컴포넌트로 교체.

### 2. Compact / Expanded 2단계

글로브 위에 카드가 항상 펼쳐져 있으면 무거우므로 2단계 표시:

```
[Compact]  →  클릭/호버  →  [Expanded]  →  "자세히"  →  [DetailPanel]
 제목+연도                   본문 스니펫+인물              풀뷰
```

- **Compact**: 현재 히어로 마커 수준. 제목, 연도, 장소, 중요도.
- **Expanded**: 본문 스니펫, 관련 인물/이벤트, FGO 섹션, 액션 버튼.
- 글로브 마커는 Compact로 표시, 엔티티 링크 클릭은 바로 Expanded.

### 3. 본문 재사용 — 새 텍스트 만들지 않는다

카드 콘텐츠는 **기존 DB 텍스트를 잘라서 표시**. 전용 텍스트를 별도 생성하지 않음.

| 카드 타입 | 본문 소스 | 슬라이싱 |
|-----------|----------|---------|
| Event | `event_details.description` | 처음 200자 (이미 API에서 truncate 중) |
| Person | `person_details.biography` | 처음 150자 |
| Person | `entity_narratives.significance` | 1문장 그대로 |
| Location | `locations.description` | 처음 150자 (**생성 예정**) |
| Servant | `fgo_servants` 메타 + person biography | 조합 |
| Shift | `chain_segments.page_narrative` (1페이지) | 처음 150자 |

### 4. 통일된 컴포넌트

글로브 마커, 시프트 위젯, 엔티티 링크 — 전부 같은 카드 컴포넌트로 렌더링.

### 5. 언어 정책

- **영어 기본** — 모든 필드는 영어가 기준
- `_ko`, `_ja` 접미사 필드가 있으면 해당 언어로 표시
- 없으면 **영어 폴백** (빈 문자열 표시 X)
- 기존 `loc(data, key, lang)` 헬퍼 그대로 사용

### 6. 투트랙 전략 — Card (Beta) 토글

기존 시스템(DetailPanel)과 카드 시스템을 **동시 유지**.
ModeBar에 "Card (Beta)" 토글 → ON이면 카드, OFF면 기존.

- 혼재 UX 없음 (전체가 한꺼번에 전환)
- A/B 비교 가능 (토글 한 번이면 바로 비교)
- 카드가 안정화되면 토글 제거, 카드로 확정
- 상세: [phases/00_foundation.md](phases/00_foundation.md)

### 7. 디자인과 구성의 분리

- **구성(Structure)**: 각 카드 컴포넌트 (`.tsx`) — 데이터 바인딩, 레이아웃 순서, 조건부 렌더링
- **디자인(Style)**: 공통 CSS (`cards.css`) — 색, 크기, 그림자, 애니메이션, compact/expanded 전환

5종 카드가 같은 시각 언어를 공유하므로 CSS를 공통으로 관리.
디자인 변경 시 CSS만 수정, 구조 변경 시 컴포넌트만 수정.

```
cards.css 클래스 설계:
  .card                    — 공통 컨테이너
  .card--compact           — 접힌 상태
  .card--expanded          — 펼친 상태
  .card-header             — 제목 + 연도
  .card-body               — 본문 스니펫
  .card-meta               — 중요도, 역할 등 메타
  .card-fgo                — FGO 섹션 (있을 때만)
  .card-actions            — 액션 버튼 영역
  .card--person            — 타입별 미세 조정
  .card--event
  .card--location
  .card--servant
  .card--shift
```

---

## 카드 타입 정의

| 카드 | 정의 문서 |
|------|----------|
| Person Card | [cards/person.md](cards/person.md) |
| Event Card | [cards/event.md](cards/event.md) |
| Location Card | [cards/location.md](cards/location.md) |
| Servant Card | [cards/servant.md](cards/servant.md) |
| Shift Card | [cards/shift.md](cards/shift.md) |

## 구현 단계

| 단계 | 문서 |
|------|------|
| Phase 0: 기반 구조 | [phases/00_foundation.md](phases/00_foundation.md) |
| Phase 1: 글로브 마커 교체 | [phases/01_globe_replacement.md](phases/01_globe_replacement.md) |
| Phase 2: 엔티티 링크 연결 | [phases/02_entity_link.md](phases/02_entity_link.md) |
| Phase 3: API 변경 | [phases/03_api.md](phases/03_api.md) |

## 트리거 총정리

| 트리거 | 현재 | 카드 시스템 후 |
|--------|------|--------------|
| 글로브 히어로 마커 | raw HTML 라벨 (제목+연도) | **Event Card** (Compact) |
| 글로브 마커 클릭 | DetailPanel 직접 열기 | **Event Card** (Expanded) |
| 글로브 노드(도시) 클릭 | LocationDetailView | **Location Card** (Expanded) |
| `[Name](entity:person:id)` 클릭 | 텍스트만 | **Person Card** (Expanded) |
| `[Name](entity:event:id)` 클릭 | 텍스트만 | **Event Card** (Expanded) |
| 시프트 위젯 `person_card` | 커스텀 위젯 | **Person Card** (통일) |
| 서번트 이름 클릭 (포탈) | 없음 | **Servant Card** (Expanded) |
| 시프트 목록에서 클릭 | ShiftBrowser | **Shift Card** (Expanded) |

## 프론트엔드 컴포넌트 구조

```
frontend/src/components/cards/
  CardContainer.tsx       — 카드 공통 래퍼 (compact/expanded 전환, 닫기)
  PersonCard.tsx           — Person + FGO 서번트 통합 (구성만)
  EventCard.tsx            — Event 카드 (구성만)
  LocationCard.tsx         — Location 카드 (구성만)
  ServantCard.tsx          — FGO Servant 전용 (구성만)
  ShiftCard.tsx            — History Shift 프리뷰 (구성만)
  EntityLink.tsx           — entity:type:id 파싱 → 카드 트리거
  useCardPopup.ts          — 팝업 상태 관리 hook
  cards.css                — 공통 카드 스타일 (디자인 전담)
  index.ts
```
