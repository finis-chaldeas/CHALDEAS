# Phase 1: 글로브 마커 → 카드 교체

## 목표

GlobeContainer의 raw HTML 히어로 카드를 React Event Card 컴포넌트로 교체.
**카드가 마커 라벨을 완전히 대체한다.**

## 현재 상태

`GlobeContainer.tsx:937-1047`에서 히어로 마커를 raw DOM으로 생성:
- `el.innerHTML = ...` 로 제목, 연도, 장소, 별점 표시
- `el.onclick` 으로 클릭 핸들링
- description 데이터는 API에서 오지만 **현재 표시 안 함**

## 작업

### 1. Event Card 구현

`cards/EventCard.tsx` — [카드 정의](../cards/event.md) 참고

본문 소스: `event_details.description[:200]` (이미 smart-markers API가 반환 중)

### 2. 글로브 마커 교체 방식

**React Portal 방식 추천:**
- GlobeContainer의 htmlElementFn은 그대로 유지 (DOM 기반)
- 마커 클릭 시 `openCard('event', eventId, clickPosition)` 호출
- CardContainer가 React Portal로 글로브 위에 렌더링

**이유:** htmlElementFn 1300줄을 React로 전면 재작성하는 건 리스크 큼.
마커 *라벨* 자체는 가벼운 DOM으로 두고, *카드 팝업*을 React로 처리.

→ 또는: htmlElementFn 자체를 React 컴포넌트로 점진 교체. 이건 논의 필요.

### 3. 노드(도시) 클릭 → Location Card

현재 `GlobeContainer.tsx:1179`에서 LocationDetailView 열기
→ Location Card 팝업으로 교체

### 4. 인물 마커 → Person Card

글로브에 인물 마커가 있으면 Person Card 팝업

## 선행 조건

- Phase 0 완료 (CardContainer, useCardPopup)

## 예상 영향

- `GlobeContainer.tsx` 클릭 핸들러 수정
- 기존 DetailPanel 열기 로직을 카드 열기로 변경
- DetailPanel은 카드의 "자세히" 버튼에서 접근
