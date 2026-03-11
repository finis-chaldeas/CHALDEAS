# Minor Markers Toggle — importance 2 기본 숨김

**날짜**: 2026-03-01

## 목적
importance ≤2 이벤트를 기본적으로 숨기고, 토글 버튼 또는 local 줌에서만 표시.

## 변경 파일

### Backend
- `backend/app/api/v1_new/globe.py`
  - `ZOOM_CONFIG` local min_importance: 2 → 3 (importance 2 기본 숨김)
  - `ZOOM_CONFIG_FULL` 추가 (기존 값 유지, local min_importance=2)
  - `get_smart_markers`에 `show_minor: bool` 쿼리 파라미터 추가

### Frontend
- `frontend/src/store/globeStore.ts` — `showMinorMarkers` 상태 + `toggleMinorMarkers` 액션
- `frontend/src/api/client.ts` — `show_minor` 파라미터 추가
- `frontend/src/components/globe/GlobeContainer.tsx` — `show_minor` 전달 (토글 OR local 줌)
- `frontend/src/components/navigation/ModeBar.tsx` — ⊕ 토글 버튼 (Search 앞)
- `frontend/src/components/navigation/ModeBar.css` — `.mode-bar__action--active` 스타일

## 데이터 흐름
```
ModeBar [⊕] → globeStore.showMinorMarkers
  ↓
GlobeContainer: showMinor = toggle || zoom === 'local'
  ↓
API: /smart-markers?show_minor=true
  ↓
Backend: ZOOM_CONFIG_FULL (local min_importance=2)
```

## 결과
- tsc --noEmit ✅
- npm run build ✅
