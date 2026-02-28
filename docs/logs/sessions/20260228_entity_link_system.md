# 2026-02-28: Entity Link System 확장 + 포털 기획 갭 채우기

## 목적

1. 기존 `[Name](entity:person|event|location:id)` 엔티티 링크 시스템을 6종으로 확장하고,
   통합 검색 API와 링크 추천 API를 구축.
2. PORTAL_01~05 기획 문서의 빠진 갭 전부 채우기.

## 변경 파일

### Backend
- `backend/app/api/v1/portal.py` — `/resolve` (통합 검색), `/suggest-links` (텍스트 분석 → 링크 추천) 엔드포인트
- `backend/app/api/v1/histories.py` — ENTITY_TAG_PATTERN을 6종으로 확장 (person/event/location/shift/item/collection)
- `backend/app/models/history.py` — entity_type 컬럼 길이 String(10) → String(20) 확장

### Frontend
- `frontend/src/api/client.ts` — `portalApi` 추가 (resolve, suggestLinks, items, collections, featured)
- `frontend/src/components/history/HistoryEditor.tsx` — 자동완성을 `searchApi.search()` → `portalApi.resolve()`로 교체, 6종 아이콘
- `frontend/src/components/history/HistoryViewer.tsx` — 파싱 패턴 6종 확장, onShiftClick/onItemClick/onCollectionClick props 추가
- `frontend/src/components/history/history.css` — shift/item/collection 색상 + autocomplete-meta 스타일

### Docs (기획 갭 채우기)
- `docs/ideal/PORTAL_01_ARCHITECTURE.md` — 포털↔글로브 연결 플로우, sections JSONB vs 위젯 시스템 관계 섹션 추가
- `docs/ideal/PORTAL_02_MAGAZINE_HOME.md` — TodayHero 전면 재설계 (date_month/day 없음 → dayOfYear 로테이션 3단계)
- `docs/ideal/PORTAL_03_COLLECTIONS.md` — joinedload 구현, 좌표 해결 훅, 데이터 현황 추가
- `docs/ideal/PORTAL_04_RECOMMENDATIONS.md` — Phase 2 MONTHLY_THEMES, Phase 3 localStorage + ADJACENT_TAGS 상세화
- `docs/ideal/PORTAL_05_ARTICLES.md` — 기존 [[wiki-link]] 문서를 [Name](entity:type:id) 확장으로 전면 개정
- `docs/ideal/INDEX.md` — PORTAL_05 참조 추가

## 결과

- `/portal/resolve?q=Alexander` → person/event/shift 결과 통합 반환 (verified)
- `/portal/suggest-links` → 텍스트 분석, "Alexander the Great", "Battle of Gaugamela" 등 자동 감지 (verified)
- 한국어 검색 ("잔 다르크") → person + portal item 결과 (verified)
- TypeScript 빌드 통과 (`npx tsc --noEmit` 클린)

## 설계 결정

1. **[[wiki-link]] 도입 대신 기존 포맷 확장**: 사용자 결정. 이미 동작하는 `[Name](entity:type:id)` 유지.
2. **item/collection은 history_entities에 미저장**: entity_id가 Integer 컬럼이라 slug 저장 불가. 본문 렌더링은 정상 작동.
3. **suggest-links는 importance 기반**: persons(≥5), events(≥5), shifts(≥3) 로딩하여 이름 매칭.

## 기획 갭 채우기 — DB 실사 기반 수정

- events 테이블에 date_month/date_day 컬럼 없음 (28,331건 전부 date_precision='year')
- portal_items에 lat/lng 없음 → related_event_ids → events → event_locations → locations 체인으로 좌표 해결
- historical_chains에 is_featured 없음 → globe_importance ≥ 4를 피처드 풀로 사용 (403건)
- fgo_servants: 449건 중 82건만 person 매핑 완료
- collections: 3개, collection_entries: 10개 (전부 portal_item 타입, shift/person/event 엔트리 미시딩)

## 다음 작업

- App.tsx에서 HistoryViewer에 onShiftClick 연결 (shifts API fetch → openShift)
- ArticleEditor 구현 (portal_items 편집용, 섹션 단위)
- suggest-links UI (에디터에서 "추천 링크" 버튼)
- collection_entries에 shift/person/event 타입 시딩 (현재 portal_item만 10건)
- portalStore.ts 구현 (중첩 모달 스택)
- 프론트엔드 포털 컴포넌트 구현 시작
