# Phase 0: 기반 구조

## 목표

카드 컴포넌트들의 공통 기반 — 컨테이너, 상태 관리, CSS.
**디자인과 구성을 분리**하여 유지보수성 확보.

## 작업

### 0. Card (Beta) 토글 — settingsStore

기존 시스템과 카드 시스템을 **동시에 유지**, 사용자가 선택.

```typescript
// settingsStore에 추가
useCardMode: boolean     // default: false
toggleCardMode: () => void
```

- **ModeBar**에 "Card (Beta)" 토글 버튼 추가
- ON: 모든 클릭이 카드 팝업으로 라우팅
- OFF: 기존 DetailPanel 동작 유지
- localStorage에 저장하여 세션 간 유지

모든 엔티티 클릭 핸들러에서:
```typescript
if (useCardMode) {
  openCard(type, id, { position })
} else {
  existingHandler(id)  // 기존 그대로
}
```

→ 카드 시스템이 안정화되면 토글 제거하고 카드로 확정.

### 1. `useCardPopup` hook (또는 Zustand store)

```typescript
interface CardPopupState {
  isOpen: boolean
  type: 'person' | 'event' | 'location' | 'servant' | 'shift' | null
  entityId: number | null
  mode: 'compact' | 'expanded'
  position: { x: number; y: number } | null
  openCard: (type, id, opts?: { mode?, position? }) => void
  expandCard: () => void    // compact → expanded 전환
  closeCard: () => void
}
```

- 한 번에 1개 카드만 열림 (스택 X)
- ESC / 배경 클릭으로 닫기
- 글로브 마커 → compact로 열림, 엔티티 링크 → expanded로 열림

### 2. `CardContainer.tsx` — 구성 담당

모든 카드의 공통 래퍼. **레이아웃과 동작만 담당, 스타일은 CSS에 위임.**

```typescript
interface CardContainerProps {
  type: 'person' | 'event' | 'location' | 'servant' | 'shift'
  mode: 'compact' | 'expanded'
  position?: { x: number; y: number }
  onClose: () => void
  onExpand?: () => void
  children: React.ReactNode
}
```

- compact/expanded 전환 로직
- 위치 계산 (글로브 위 or 클릭 위치)
- 닫기/뒤로가기 버튼
- 언어 선택은 `loc()` 헬퍼 사용 (영어 폴백)

### 3. `cards.css` — 디자인 전담

**구성과 완전히 분리.** 컴포넌트는 CSS 클래스만 할당, 시각 결정은 CSS에서.

```css
/* 공통 */
.card { }                    /* 기본 컨테이너 */
.card--compact { }           /* 접힌 상태: 제목+연도만 */
.card--expanded { }          /* 펼친 상태: 본문+액션 */
.card-header { }             /* 제목 영역 */
.card-body { }               /* 본문 스니펫 */
.card-meta { }               /* 중요도, 역할, 좌표 등 */
.card-fgo { }                /* FGO 섹션 */
.card-actions { }            /* 액션 버튼 */

/* 타입별 미세 조정 */
.card--person { }
.card--event { }
.card--location { }
.card--servant { }
.card--shift { }

/* 전환 애니메이션 */
.card-enter { }
.card-exit { }
.card--compact-to-expanded { }
```

- 다크 테마 기반 (글로브 배경)
- 반응형 (모바일: 하단 시트 고려)
- compact → expanded 전환 애니메이션

### 4. 디렉터리 생성

```
frontend/src/components/cards/
  CardContainer.tsx          ← 구성
  useCardPopup.ts            ← 상태
  cards.css                  ← 디자인
  index.ts
```

## 원칙: 무엇이 어디에

| 관심사 | 위치 | 예시 |
|--------|------|------|
| 어떤 데이터를 보여줄까 | 각 카드 `.tsx` | biography 표시 여부 |
| 어떤 순서로 배치할까 | 각 카드 `.tsx` | header → body → actions |
| 어떻게 생겼을까 | `cards.css` | 색, 크기, 그림자, 라운드 |
| 어떻게 움직일까 | `cards.css` | compact→expanded 전환 |
| 언제 열고 닫을까 | `useCardPopup.ts` | 상태 관리 |

## 선행 조건

없음 — 독립적으로 시작 가능.

## 예상 영향

- 신규 파일만 생성, 기존 코드 변경 없음
