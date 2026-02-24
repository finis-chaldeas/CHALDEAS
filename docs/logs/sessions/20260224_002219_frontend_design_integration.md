# 세션 로그: 2026-02-24 00:22

## 세션 정보
- **목적**: 프론트엔드 디자인 통합 + 코드 개선 (Phase 1-5)

## 한 작업

### Phase 1: globals.css 디자인 시스템 통합
- **globals.css**: 사이드바 CSS 제거 (`.sidebar`, `.sidebar-open`, `.sidebar-header`, `.sidebar-footer`)
- **globals.css**: 네비게이터 CSS 제거 (`.navigator-panel`, `.navigator-tab`, `.navigator-item` 등)
- **globals.css**: 레거시 모바일 사이드바 CSS 제거 (`.mobile-menu-btn`, `.mobile-overlay` 등)
- **globals.css**: 반응형 네비게이터 collapse 규칙 제거
- **globals.css**: V4 플로팅 UI 컴포넌트 CSS 추가:
  - `.narrative-panel`, `.narrative-panel-close`, `.narrative-panel-body`
  - `.floating-buttons`, `.floating-btn`, `.floating-btn-label`
  - `.world-briefing`, `.world-briefing-bar`, `.world-briefing-expanded`
  - `.viewport-feed`, `.viewport-feed-pill`, `.viewport-feed-tab`, `.viewport-feed-sort-btn`
  - `.camera-mode-toggle`, `.camera-mode-btn`, `.globe-style-selector`, `.globe-style-btn`
  - `.source-modal-backdrop`, `.source-modal`, `.source-modal-close`
  - `.rayshift-bar`, `.rayshift-nav-btn`, `.rayshift-dots`

### Phase 2: 컴포넌트 스타일링 통일
- **NarrativePanel.tsx**: 인라인 스타일 전부 제거 → `.narrative-panel` CSS 클래스
- **FloatingButtons.tsx**: Tailwind → CSS 클래스 (`.floating-btn`, `.floating-btn-label`)
- **WorldBriefing.tsx**: Tailwind → CSS 클래스 (`.world-briefing-*`)
- **ViewportFeed.tsx**: Tailwind → CSS 클래스 (`.viewport-feed-*`)
- **CameraModeToggle.tsx**: Tailwind → CSS 클래스 (`.camera-mode-*`)
- **SourceBrowser.tsx**: 인라인 스타일 + Tailwind → CSS 클래스 (`.source-modal-*`)
- **Rayshift.tsx**: 인라인 `<style>` 태그 제거 (CSS는 globals.css에 있음)

### Phase 3: App.tsx 레이아웃 정리
- `GLOBE_STYLE_KEYS` 상수 제거 (CameraModeToggle이 직접 관리)
- `globeStyle` / `setGlobeStyle` 간소화 (settingsStore에서 직접 읽기)
- `rayshiftEntityId` 상태 복원 (unused setter 패턴 제거)
- `Rayshift` 컴포넌트 import 및 렌더링 추가
- `NarrativePanel`에 `onRayshift` 핸들러 전달

### Phase 4: 기능 갭 수정
- **ViewportFeed**: 3가지 정렬 추가 (importance/time/distance) + haversine 거리 계산
- **CameraModeToggle**: 글로브 스킨 선택기 추가 (Blue Marble/Holo/Night, orbit 모드에서만)
- **EventNarrativeCard**: `onRayshift` prop 추가, "Follow Causal Chain" → "Rayshift: Follow Causal Chain" 버튼 연결
- **PersonNarrativeCard**: `onRayshift` prop 추가, "Follow Life Journey" → "Rayshift: Follow Life Journey" 버튼 연결
- **NarrativePanel**: `onRayshift` prop 추가, causal/life 모드 분기

### Phase 5: 검증
- `npx tsc --noEmit`: ✅ 에러 0
- `npm run build`: ✅ 빌드 성공 (11.65s)

## 변경된 파일 목록
1. `frontend/src/styles/globals.css` - CSS 시스템 통합
2. `frontend/src/components/narrative/NarrativePanel.tsx` - 인라인→CSS + onRayshift
3. `frontend/src/components/globe/FloatingButtons.tsx` - Tailwind→CSS
4. `frontend/src/components/globe/WorldBriefing.tsx` - Tailwind→CSS
5. `frontend/src/components/globe/ViewportFeed.tsx` - Tailwind→CSS + 3정렬
6. `frontend/src/components/globe/CameraModeToggle.tsx` - Tailwind→CSS + 스킨선택기
7. `frontend/src/components/sources/SourceBrowser.tsx` - 인라인→CSS
8. `frontend/src/components/rayshift/Rayshift.tsx` - 인라인 style태그 제거
9. `frontend/src/App.tsx` - 미사용 변수 정리 + Rayshift 연결
10. `frontend/src/components/narrative/EventNarrativeCard.tsx` - onRayshift 연결
11. `frontend/src/components/narrative/PersonNarrativeCard.tsx` - onRayshift 연결

## 결과
- ✅ TypeScript 에러 0
- ✅ 빌드 성공
- ✅ 모든 인라인 스타일 제거
- ✅ 일관된 CSS 변수 기반 디자인 시스템
- ✅ ViewportFeed 3정렬 (importance/time/distance)
- ✅ Rayshift 버튼 연결 (causal chain + life journey)
- ✅ 글로브 스킨 선택기 (CameraModeToggle에 통합)

## 반성
- globals.css가 여전히 3400+ 줄로 크지만, 레거시 CSS를 유지해야 하는 컴포넌트가 아직 있음
- ESLint 설정 파일이 없는 것은 기존 이슈 (이번 작업과 무관)

## 다음 작업
- 시각 확인 (dev 서버에서 실제 UI 확인)
- 글로브가 뷰포트 80%+ 차지하는지 확인
- 모든 오버레이가 동일한 색상/보더/그라데이션인지 확인
