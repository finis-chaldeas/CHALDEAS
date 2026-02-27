# 2026-02-27: Marker System v2 — Hero-centric Simplification

## Purpose
Simplify globe marker system from 3 types (Hero/Cluster/Node) to 2 types (Hero/Node), add companion lines for high-importance nearby events, and fix city node visual duplication.

## Changes

### Backend (`backend/app/api/v1_new/globe.py`)
- **Removed**: `ClusterBubble`, `ClusterEvent` Pydantic models
- **Removed**: `clusters` field from `SmartMarkersResponse`
- **Removed**: Step 4 (cluster grid query) and Step 5 (top events per cluster) from `get_smart_markers`
- **Removed**: `grid_size` from `ZOOM_CONFIG`
- **Removed**: `limit_clusters` parameter from endpoint
- **Updated ZOOM_CONFIG**:
  - continental: min_importance 4→3, max_heroes 15→20
  - regional: max_heroes 25→30
  - local: min_importance 2→3, max_heroes 30→40

### Frontend Types (`frontend/src/types/index.ts`)
- **Removed**: `ClusterBubble` interface
- **Removed**: `clusters` from `SmartMarkersResponse`
- **Kept**: `ClusterEvent` (still used by mini modal)

### Frontend GlobeContainer (`frontend/src/components/globe/GlobeContainer.tsx`)
- **Removed**: Cluster bubble mapping from `normalHtmlElements` (Section 3)
- **Removed**: `kind === 'cluster'` branch from `htmlElementFn`
- **Added**: City node suppression — nodes at hero locations are filtered out
- **Added**: Companion lines — nearby events with `importance >= hero.importance - 1 && >= 4` shown directly on hero card (max 2)
- **Added**: Companion click handler → opens event detail
- **Updated**: Badge count excludes companion events
- **Updated**: Badge hidden when eventCount=0 and personCount=0

### Frontend CSS (`frontend/src/styles/globals.css`)
- **Removed**: `.cluster-bubble`, `.cluster-bubble:hover`, `.shifted .cluster-bubble`
- **Added**: `.hero-card-companions`, `.hero-card-companion`, `.hero-card-companion:hover`

## Result
- `npx tsc --noEmit` passes
- Cluster bubbles completely removed
- imp=3 events visible as heroes at continental zoom
- Companion lines show high-importance nearby events without badge click
- No city pin duplication at hero locations

## Next Steps
- Visual testing with live data (Persian Wars scenario)
- Verify zoom transitions feel natural with increased hero counts
