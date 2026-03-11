# 2026-03-05: Launch Prep — ErrorBoundary + Event Hierarchy + Onboarding

## 완료

### 1. ErrorBoundary (01번 태스크)
- `frontend/src/components/common/ErrorBoundary.tsx` — 전역 에러 바운더리 + PanelErrorFallback
- `frontend/src/components/common/ErrorBoundary.css` — CHALDEAS 테마 에러 화면
- `App.tsx`에 최상위 ErrorBoundary 래핑
- tsc + 빌드 통과

### 2. Event Hierarchy Script (04번 태스크)
- `backend/scripts/fill_event_hierarchy.py` — Wikidata P361 추출 + DB 적용
- `--extract-only`, `--apply-only`, `--dry-run`, `--force` 지원
- 500K 엔티티 테스트 통과 (551 매핑 발견)
- **전체 덤프 스캔 실행 중** (16M 시점에서 2,091 새 매핑 발견, 계속 증가)
- 완료 후: `python scripts/fill_event_hierarchy.py --apply-only`

### 3. Onboarding + Tour 진입점 (06번 태스크)
- **FeaturedPersons 랜딩**: 2-card → 3-card (Explore / Guided Tour / Read Stories)
- **조작 안내**: 드래그, 타임라인, 줌 힌트 추가
- **TourSelector 컴포넌트**: 에피소드 선택 그리드 (18개 에피소드)
- **ModeBar**: 투어 아이콘 추가 (상시 접근)
- tsc + 빌드 통과

## 비용 산출 완료 (돈 드는 작업)

| 작업 | 페이지/아이템 | 비용 |
|------|-------------|------|
| enhance imp5 | 3,587p | $57.93 |
| enhance imp4+ | 6,148p | $99.29 |
| enhance 전체 | 9,339p | $150.83 |
| 포탈 50개 | 50 articles | $17.60 |
| 포탈 75개 | 75 articles | $26.40 |
| 포탈 100개 | 100 articles | $35.20 |
| **imp4+ enhance + 75 포탈** | | **$125.69** |

## 실행 중

- Wikidata P361 추출: 백그라운드 (b1f912c), ~7-8시간 예상

## 변경 파일

| 파일 | 유형 |
|------|------|
| `frontend/src/components/common/ErrorBoundary.tsx` | 신규 |
| `frontend/src/components/common/ErrorBoundary.css` | 신규 |
| `frontend/src/components/common/index.ts` | 수정 |
| `frontend/src/components/tour/TourSelector.tsx` | 신규 |
| `frontend/src/components/tour/index.ts` | 수정 |
| `frontend/src/components/landing/FeaturedPersons.tsx` | 수정 |
| `frontend/src/components/landing/Landing.css` | 수정 |
| `frontend/src/components/navigation/ModeBar.tsx` | 수정 |
| `frontend/src/App.tsx` | 수정 |
| `backend/scripts/fill_event_hierarchy.py` | 신규 |
| `docs/roadmap/` (7개 문서) | 신규 |
