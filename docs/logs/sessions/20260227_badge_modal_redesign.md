# 배지 모달 재설계 + 인물 클릭 버그 수정 + 스마트 마커 V2

**날짜**: 2026-02-27
**목적**: 히어로 카드 배지 모달의 위치 그룹핑, 이벤트 실종 방지, 클릭 시 핀 독립, z-index 수정

---

## 변경 파일

### 백엔드
- `backend/app/api/v1_new/globe.py`
  - candidate_limit: max_heroes*5 → max(max_heroes*10, 150)
  - _select_heroes Pass 2: imp≥4 orphan 멀면 히어로 승격 (기존: 무조건 귀속)
  - nearby_events cap: 7 → 50
  - `event_details` 테이블 참조 제거 → `e.description` 직접 사용 (compact DB에 event_details 없음)

### 프론트엔드
- `frontend/src/store/globeStore.ts` — PinnedEvent 상태 추가
- `frontend/src/components/globe/GlobeContainer.tsx`
  - pinnedEvent 렌더 (htmlElements)
  - 미니 모달 z-index: 10000
  - 모달 이벤트 클릭 → pin + fly + open
  - 위치 그룹핑 (좌표 기반 판단)
  - companion 필터 제거 (모달에서 전부 표시)
  - node 경로 location_name 포함
- `frontend/src/App.tsx`
  - personDetailId 복원 + PersonDetailView 렌더
- `frontend/src/types/index.ts` — ClusterEvent에 lat/lng
- `frontend/src/styles/globals.css`
  - 위치 그룹 헤더 CSS
  - pinned hero 금색 테두리 + 펄스

### 기획
- `docs/ideal/SMART_MARKERS_V2.md` — 스마트 마커 V2 전체 설계

## 검증
- `npx tsc --noEmit` 통과

## 미구현
- 줌 레벨 hysteresis (cosmic↔continental 경계 안정화)
- Sticky heroes (이전 프레임 히어로 유지)
- nearby_events 동적 로딩 (50개 초과 시)
