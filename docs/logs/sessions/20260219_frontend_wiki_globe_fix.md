# 세션 로그: 2026-02-19 Frontend Wikipedia Content + Globe Fix

## 세션 정보
- **목적**: 프론트엔드에서 Wikipedia 원문 표시 + 지구본 회색 노드 숨기기

## 한 작업

### 1. 지구본 회색 노드 숨기기
- **문제**: `active_event_count === 0`인 노드가 cosmic/continental 줌에서도 회색으로 표시되어 지구본 가독성 저하
- **원인**: `visibleNodes` 필터가 `event_count`(전체)만 확인, `active_event_count`(시대 내) 미확인
- **수정**: `GlobeContainer.tsx` - cosmic/continental 줌에서 `active_event_count > 0` 필수 조건 추가
  - cosmic: `active_event_count > 0 && event_count >= 20`
  - continental: `active_event_count > 0 && event_count >= 5`
  - regional: active이면 `event_count >= 1`, inactive면 `event_count >= 20` (주요 도시만)
  - local: 전부 표시

### 2. Wikipedia 원문 API 엔드포인트 추가
- **새 엔드포인트**: `GET /api/v1/persons/{id}/wikipedia`
- **데이터 소스**: `person_sources` → `sources` 테이블 (source_type='wikipedia')
- **반환**: `content_excerpt` (첫 3000자), `url`, `full_length`, `source_id`
- **커버리지**: 122,573명의 인물에 Wikipedia 소스 연결됨

### 3. PersonDetailView Wikipedia 섹션 추가
- Biography 아래, Also Known As 위에 Wikipedia 섹션 표시
- 기본 600자 표시 → "Read more" 버튼으로 3000자까지 확장
- Full article on Wikipedia 외부 링크

### 4. CSS 스타일 추가
- `.wiki-content`, `.wiki-excerpt`, `.wiki-expand-btn` 스타일

## 변경 파일
| 파일 | 변경 내용 |
|------|----------|
| `frontend/src/components/globe/GlobeContainer.tsx` | visibleNodes 필터 수정 |
| `backend/app/api/v1/persons.py` | Wikipedia 엔드포인트 추가 |
| `frontend/src/components/detail/PersonDetailView.tsx` | Wikipedia 섹션 + wikiData 쿼리 추가 |
| `frontend/src/components/detail/EntityDetailView.css` | wiki-content 스타일 추가 |

## 갯수 불일치 원인 설명 (사용자 질문)
- 지구본 노드: 노드 API의 `active_event_count` 또는 `event_count` 표시
- 로케이션 디테일: `primary_location_id` 기반 이벤트만 표시
- 두 쿼리의 데이터 소스가 다름 (노드 API는 `event_locations` M2M 포함)

## 결과
- TypeScript 검증 통과 (`npx tsc --noEmit`)
- Wikipedia API 테스트 통과 (히포크라테스 34,261자 원문 확인)
- 백엔드 서버 재시작 완료

## 다음 작업
- 프론트엔드에서 실제 Wikipedia 섹션 표시 확인
- 이벤트/로케이션 Wikipedia 콘텐츠도 비슷하게 추가 고려
