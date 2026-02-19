# 세션 로그: 2026-02-18 Frontend Data Sync

## 세션 정보
- **목적**: 프론트엔드가 무시하던 DB 데이터를 표시하도록 컴포넌트 업데이트

## 한 작업

### PersonDetailView.tsx
- `PersonName` 인터페이스 추가 및 `PersonInfo.names` 필드 추가
- Relations API 호출: `min_strength=5` → `min_strength=0`, `limit=20` → `limit=30`
- **Also Known As 섹션**: 이름 목록 표시 (name_type 뱃지, 언어, 기간)
- **관계 유형 그룹핑**: Family → Spouse/Partner → Academic → Other 순서로 그룹
- **관계 유형 뱃지**: relationship_type을 색상 라벨로 표시 (빨강=가족, 핑크=배우자, 파랑=학문)
- **Wikipedia 링크**: biography 아래에 Wikipedia 외부 링크 버튼 추가
- strength가 0인 관계도 표시 (뱃지만, 바 없이)

### EventDetailPanel.tsx
- Description 하단에 Wikipedia 외부 링크 추가 (`event.details.wikipedia_url` 또는 `event.wikipedia_url`)

### EntityDetailView.css
- `.wikipedia-link`, `.wikipedia-icon` 스타일 추가
- `.description-meta` 플렉스 레이아웃 추가
- `.names-list`, `.name-item`, `.name-type-badge` (유형별 색상) 스타일 추가
- `.relation-group`, `.relation-group-label` (카테고리별 색상) 스타일 추가
- `.rel-type-badge` (family/spouse/academic/other) 스타일 추가
- `.entity-wiki-link` 스타일 추가 (LocationDetailView용)

## 결과
- `npx tsc --noEmit` 에러 없음
- 3개 파일 변경

## 다음 작업
- 브라우저에서 실제 데이터 표시 확인
- Person 예시: Alexander the Great (다국어 이름, 가족 관계 등)
