# Phase 2: 엔티티 링크 → 카드 연결

## 목표

`[Name](entity:type:id)` 형식의 엔티티 링크 클릭 시 카드 팝업 표시.

## 현재 상태

`HistoryViewer.tsx`에서 6가지 엔티티 타입 파싱:
```typescript
const ENTITY_TAG_RE = /(\[[^\]]+\]\(entity:[^)]+\))/
// person, event, location, shift, item, collection
```

현재는 클릭 시 `onPersonClick`, `onEventClick` 등으로 DetailPanel 직접 열기.
→ 카드 팝업으로 교체.

## 작업

### 1. EntityLink 컴포넌트 분리

현재 HistoryViewer 내부의 인라인 파싱 로직을 독립 컴포넌트로 추출:

```typescript
// cards/EntityLink.tsx
function EntityLink({ type, id, displayName, onOpenCard }) {
  return (
    <span className="entity-link" onClick={() => onOpenCard(type, id)}>
      {displayName}
    </span>
  )
}
```

### 2. HistoryViewer 수정

- 기존 `RenderBody` 내 엔티티 태그 렌더링 → `EntityLink` 컴포넌트 사용
- `onPersonClick` 등 → `openCard(type, id)` 로 통일

### 3. 시프트 위젯 PersonCard 통합

현재 `shift/widgets/PersonCard.tsx` (37줄, 독립 구현)
→ `cards/PersonCard`를 import해서 위임, 또는 위젯 자체를 카드로 교체

## 선행 조건

- Phase 0 완료
- Person Card, Event Card, Location Card 구현 (Phase 1에서 Event 완료)

## 예상 영향

- `HistoryViewer.tsx` 수정 (엔티티 링크 렌더링 부분)
- `shift/widgets/PersonCard.tsx` 수정 또는 교체
- 새 파일: `cards/EntityLink.tsx`, `cards/PersonCard.tsx`, `cards/LocationCard.tsx`
