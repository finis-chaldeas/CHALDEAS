# Session Log: 2026-02-23 Frontend V4 Integration

## Session Info
- **Purpose**: Merge frontend-v4/ prototype components into frontend/ production app
- **Goal**: Single unified frontend with all V4 narrative-first features

## Work Done

### Phase 0: Foundation
- Updated `tailwind.config.js` with chaldea color palette (bg, panel, cyan, orange, magenta, gold, green, text-bright, etc.)
- Extended `api/client.ts`: added `eventsApi.getRelationships`, `eventsApi.getLocations`, `personsApi.getNarrative`, `personsApi.getRelations`, `personsApi.getProperties`, `reportsApi.submit`
- Added new types to `types/index.ts`: `EventRelationship`, `EventHierarchyNode`, `PersonNarrative`, `PersonRelation`, `PersonSource`, `ContentReport`, `SourceDetail`, `SourceMention`, `SourcePerson`
- Added `detailPanelMode: 'classic' | 'narrative'` to `settingsStore.ts` (default: 'narrative')

### Phase 1: WorldBriefing + PeriodDrawer
- Created `components/globe/WorldBriefing.tsx` - top overlay showing current period headline, narrative, events, persons, regional breakdowns
- Created `components/globe/PeriodDrawer.tsx` - expandable two-column detail drawer with events/figures
- Adapted from v4: `useAppStore` -> callback props, `currentYear` from `timelineStore`, positioned after sidebar (left: 320px)

### Phase 2: ViewportFeed
- Created `components/globe/ViewportFeed.tsx` - dynamic feed based on globe viewport position
- Uses `useGlobeStore.cameraPosition` instead of v4's viewport store
- Positioned after sidebar (left: 320px)

### Phase 3: NarrativeCard System (largest phase)
- Created `components/narrative/ReportButton.tsx` - content reporting UI
- Created `components/narrative/EventNarrativeCard.tsx` - event narrative with causes/consequences, hierarchy, relationships
- Created `components/narrative/PersonNarrativeCard.tsx` - person narrative with Story/Network/Sources tabs, quick facts, names, flow
- Created `components/narrative/NarrativePanel.tsx` - unified wrapper panel
- Created `components/narrative/index.ts` - barrel exports
- Feature flag: `settingsStore.detailPanelMode` controls classic vs narrative mode

### Phase 4: DeepRead Modal
- Created `components/navigator/DeepReadModal.tsx` - fullscreen era exploration with period presets, era filtering, narrative/events/persons/feed tabs

### Phase 5: SourceBrowser
- Created `components/sources/SourceBrowser.tsx` - source list with type badges and stats
- Created `components/sources/SourceDetailPanel.tsx` - source detail with persons/mentions tabs
- Created `components/sources/index.ts` - barrel exports

### Phase 6: Integration + Cleanup
- Added CSS animations to `globals.css`: `narrative-enter`, `briefing-enter`, `period-drawer-enter`
- Updated `App.tsx`:
  - Imported all new components
  - Added WorldBriefing and ViewportFeed to globe section
  - Added NarrativePanel (conditional on detailPanelMode)
  - Made EventDetailPanel and PersonDetailView conditional on classic mode
  - Added DeepReadModal and SourceBrowser
  - Added narrative-specific event/person click handlers
- Deleted frontend-v4/ contents (directory shell locked but empty)

### Bug Fixes
- **CRITICAL: React hooks violation in ViewportFeed.tsx** - Early return `if (viewMode !== 'globe') return null` was placed BEFORE `useMemo` and `useQuery` hooks, violating React Rules of Hooks. This caused the entire app to crash (blank page). Fixed by moving early return AFTER all hooks and using `enabled` flag on useQuery.
- **WorldBriefing useMemo anti-pattern** - `useMemo(() => { setFeedbackSent(null) }, [periodStart])` was using useMemo for a side effect. Changed to `useEffect`.
- **WorldBriefing pointer-events** - Added `pointer-events-none` to gradient overlay and `pointer-events-auto` to content div so globe interaction is not blocked.

## Files Changed

### New (12 files)
- `frontend/src/components/globe/WorldBriefing.tsx`
- `frontend/src/components/globe/PeriodDrawer.tsx`
- `frontend/src/components/globe/ViewportFeed.tsx`
- `frontend/src/components/narrative/NarrativePanel.tsx`
- `frontend/src/components/narrative/EventNarrativeCard.tsx`
- `frontend/src/components/narrative/PersonNarrativeCard.tsx`
- `frontend/src/components/narrative/ReportButton.tsx`
- `frontend/src/components/narrative/index.ts`
- `frontend/src/components/sources/SourceBrowser.tsx`
- `frontend/src/components/sources/SourceDetailPanel.tsx`
- `frontend/src/components/sources/index.ts`
- `frontend/src/components/navigator/DeepReadModal.tsx`

### Modified (5 files)
- `frontend/tailwind.config.js` - chaldea color palette
- `frontend/src/api/client.ts` - new API methods
- `frontend/src/types/index.ts` - new type interfaces
- `frontend/src/store/settingsStore.ts` - detailPanelMode
- `frontend/src/styles/globals.css` - animation keyframes
- `frontend/src/App.tsx` - all components integrated

### Deleted
- `frontend-v4/` - entire directory (contents removed, shell locked)

## Result
- `npx tsc --noEmit` passes cleanly
- `npm run build` succeeds
- Feature flag allows switching between classic and narrative panel modes
- All existing features (History, Showcase, Tour, Chat, Search, Navigator) preserved

### Post-Integration Fixes (context continuation)

**Problem**: V4 components were mechanically copied without understanding design philosophy. User feedback:
- Navigator sidebar에 Deep Read/Sources 버튼을 쑤셔넣음 → 사이드바 과적
- SourceBrowser가 wikisource/wikidata 쓰레기 데이터 표시 (126k entries)
- V4 핵심 철학(글로브 중심, 서사 우선, 인과 흐름)이 하나도 반영 안 됨

**Fixes applied**:
1. **CLAUDE.md 업데이트**: `docs/ideal/` 기획문서 필독 규칙 추가 — 프론트엔드 작업 전 반드시 읽어야 함
2. **Navigator.tsx**: `onOpenDeepRead`/`onOpenSources` props 및 trigger 버튼 제거
3. **navigator.css**: grid(2x2) → flex(원래 2버튼 레이아웃) 복원, 불필요한 `.trigger-deepread`/`.trigger-sources` CSS 삭제
4. **App.tsx**: Navigator에 전달하던 `onOpenDeepRead`/`onOpenSources` props 제거

## Reflection
- The hooks violation was a critical bug caused by adapting v4 code that used a different pattern (v4's ViewportFeed had no early returns). Should have checked hooks ordering during adaptation.
- The useMemo-for-side-effect anti-pattern was copied directly from v4. Should always convert such patterns during porting.
- **근본적 문제**: V4 코드를 기계적으로 복사했을 뿐, `docs/ideal/` 기획 문서를 읽지 않았다. 왜 이렇게 디자인했는지 이해 없이 구현하면 안 된다.
- CLAUDE.md에 필독 규칙을 추가해서 다시는 기획문서 없이 프론트엔드를 건드리지 않도록 함.

## Next Steps
- **기획문서 기반으로 V4 통합 재설계**: `docs/ideal/` 원칙에 맞춰 WorldBriefing/ViewportFeed/NarrativeCard가 글로브 중심으로 동작하도록
- SourceBrowser 데이터 품질 수정 (wikisource 쓰레기 필터링)
- Test with running backend to verify API calls
- Clean up empty frontend-v4/ directory after process restart
