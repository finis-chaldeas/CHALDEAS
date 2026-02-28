# 20260301 — Phase C: Unified Mode Bar (FGO Terminal Style)

## Purpose

FloatingButtons (개별 아이콘 5개) → 상단 통합 모드 바로 교체.
현재 모드(SHEBA/TRISMEGISTOS/SHIFT)를 명시하고, 원클릭 전환 가능하게 개선.

## Changes

### New Files
- `frontend/src/components/navigation/ModeBar.tsx` — 통합 상단 내비게이션 바
  - 좌측: CHALDEAS 로고 (gold accent)
  - 중앙: 모드 탭 3개 (SHEBA / TRISMEGISTOS / SHIFT)
  - 우측: Search / LAPLACE / Settings 아이콘
  - 모드 전환 로직: suspend/resume portal, close shift, context passing
- `frontend/src/components/navigation/ModeBar.css` — 40px 고정 바, glass morphism, cyan accent

### Modified Files
- `frontend/src/App.tsx` — FloatingButtons → ModeBar 교체
- `frontend/src/styles/globals.css` — globe-section에 margin-top: 40px 추가, floating-btn 스타일 제거, 모바일 EraFeed/timeline 위치 조정
- `frontend/src/components/trismegistos/portal.css` — portal-backdrop top: 40px (모드바 아래)
- `frontend/src/components/shift/ShiftPanel.css` — shift-singularity top: 56→96px (모드바 40px 반영)

### Deleted Files
- `frontend/src/components/globe/FloatingButtons.tsx` — 모든 기능이 ModeBar로 이동

## Mode Tab Behavior

| Tab | Active When | Click Action |
|-----|------------|-------------|
| SHEBA | Globe visible (default) | suspend portal / close shift |
| TRISMEGISTOS | portalStore.isOpen | open portal (auto-resume if suspended) |
| SHIFT | activeShift exists | resume shift / open ShiftBrowser if none |

- Suspended portal → TRISMEGISTOS 탭에 cyan dot indicator
- No active shift → SHIFT 탭 dimmed, click opens ShiftBrowser

## Build Result
- `tsc --noEmit` — PASS
- `npm run build` — PASS (882 modules, 11.1s)

## Next Steps
- E2E 검증: 모든 모드 전환 플로우 테스트
- 필요시 ModeBar 애니메이션/트랜지션 추가
