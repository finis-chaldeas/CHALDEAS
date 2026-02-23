# Session Log: 2026-02-20 - Frontend Hybrid Rebuild (Plan Na)

## Session Info
- **Purpose**: Implement "Plan Na (Hybrid Rebuild)" - reduce UI duplication, expose unused data, simplify navigation
- **Plan Reference**: Frontend redesign 3-plan document, Plan Na selected

## Summary
Implemented the Hybrid Rebuild plan which keeps existing infrastructure (stores, globe, timeline, API client) while simplifying navigation and removing duplicate entry points.

## Changes Made

### 1. Deprecated Files Moved to `_deprecated/`
- `showcase/TrismegistusHub.tsx` -> `_deprecated/TrismegistusHub.tsx`
- `showcase/TrismegistusHub.css` -> `_deprecated/TrismegistusHub.css`
- `navigator/DomainTimelineModal.tsx` -> `_deprecated/DomainTimelineModal.tsx`
- `navigator/DomainTimelineModal.css` -> `_deprecated/DomainTimelineModal.css`

### 2. App.tsx (~-80 lines)
- Removed imports for `TrismegistusHub` and `DomainTimelineModal`
- Removed state: `isDomainTimelineOpen`, `isTrismegistusOpen`
- Removed TrismegistusHub JSX block (30+ lines)
- Removed DomainTimelineModal JSX block (12+ lines)
- Changed Navigator's `onOpenShowcase` to open ShowcaseModal directly (was TrismegistusHub)
- Removed `onOpenDomainTimeline` prop from Navigator and FeaturedPersons
- Removed "Explore Eras" button from globe overlay (duplicate of TimelineModal)

### 3. FeaturedPersons.tsx (~-130 lines)
- Reduced from 5 entry points to 2: Guided Tour + Free Explore
- Removed: Timeline card, By Subject card, Recommended Figures row
- Removed: persons grid view, ERA_TABS, useQuery for featured persons
- Removed unused props: `onOpenDomainTimeline`, `onOpenServantPanel`, `onOpenShowcase`
- WelcomeView type: `'welcome' | 'guided-tours'` (removed `'persons'`)

### 4. Navigator.tsx (~-15 lines)
- Removed "Domains" trigger button
- Removed `onOpenDomainTimeline` prop from interface and destructuring
- Now has 2 buttons: Timeline + Trismegistus (opens ShowcaseModal directly)

### 5. PersonTab.tsx (~+25 lines)
- Added domain filter dropdown (replaces DomainTimelineModal functionality)
- 11 domain options: All Fields, Science, Philosophy, Literature, Military, Statecraft, Visual Arts, Music, Religion, Mathematics, Exploration
- Domain param sent to `/persons` API (backend already supports `domain` query param)

### 6. EventDetailPanel.tsx (~+50 lines)
- Added "Person's Thread" section in overview tab
- Fetches events from `/threads/{personId}/events` API for the main participant
- Shows up to 8 other events involving that person, excluding current event
- Uses existing `related-event-item` styling for consistency

### 7. navigator.css (~-10 lines)
- Removed `.trigger-domain:hover` and `.trigger-domain:hover .trigger-icon` styles

### 8. globals.css (~+15 lines)
- Added `.thread-events-list` and `.thread-more-hint` styles

### Already Implemented (No Changes Needed)
- **PersonDetailView**: Already has full relations display (grouped by family/spouse/academic/other with strength bars)
- **LocationDetailView**: Already has territories (Political History) and historical names sections
- **Context Banner**: Already has period headline + "View in Timeline" link in both FeedInterest and FeedTab

## Verification
- `npx tsc --noEmit` passes with 0 errors
- No dead imports to deprecated files (verified via grep)
- No references to removed state variables

## Results
- **Duplicate entry points reduced**: 5 landing paths -> 2, 3 navigator buttons -> 2
- **Deprecated**: 4 files moved (TrismegistusHub + DomainTimelineModal with CSS)
- **New data exposed**: Domain filter in PersonTab, Thread events in EventDetailPanel
- **Modified files**: App.tsx, FeaturedPersons.tsx, Navigator.tsx, PersonTab.tsx, EventDetailPanel.tsx, navigator.css, globals.css

## Next Steps
- Browser smoke test to verify all navigation paths work
- Consider Plan Ga's globe visualization features (territory overlay, relationship lines) as future incremental additions
