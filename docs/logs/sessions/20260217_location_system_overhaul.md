# 세션 로그: 2026-02-17

## 세션 정보
- **목적**: Location 시스템 최종 플랜 구현 - 로케이션을 고정된 점(노드)으로 재정의

## 한 작업

### 1. Alembic 마이그레이션 생성
- `backend/alembic/versions/300_location_system_overhaul.py`
- locations 테이블에서 27개 불필요 컬럼 삭제
- parent_id → parent_location_id 리네임
- location_type NOT NULL DEFAULT 'point' 설정
- wikidata_id UNIQUE 제약조건 추가
- event_locations에 match_method, distance_km 추가
- event_coords_cache 테이블 생성 (이벤트 원래 좌표 보존)
- territories 테이블 생성 (placeholder)
- territory_locations 테이블 생성
- 기존 이벤트 좌표를 event_coords_cache에 자동 보존

### 2. Location 모델 재작성
- `backend/app/models/location.py` - 슬림화
- 남은 컬럼: id, wikidata_id, name, name_ko, name_ja, latitude, longitude, location_type, parent_location_id, created_at, updated_at
- 불필요한 관계(modern_parent, historical_parent, canonical) 제거
- get_name_at() 메서드 유지 (시대별 이름 조회)

### 3. 신규 모델 생성
- `backend/app/models/event_coords_cache.py` - 이벤트 원래 좌표 캐시
- `backend/app/models/territory.py` - Territory + TerritoryLocation
- `backend/app/models/associations.py` - event_locations에 match_method, distance_km 추가
- `backend/app/models/__init__.py` - 신규 모델 등록

### 4. 스키마/API/서비스 업데이트
- `backend/app/schemas/location.py` - LocationBase, Location, LocationDetail, LocationName 스키마
- `backend/app/api/v1/locations.py` - is_light 필터 제거, location_type 필터 추가, names 반환
- `backend/app/services/location_service.py` - is_light 제거
- `backend/app/services/search_service.py` - modern_name, connection_count 참조 제거
- `backend/app/services/event_service.py` - region, country, hierarchy_level 필터 제거
- `backend/app/services/hybrid_search.py` - location text_fields에서 modern_name, description 제거

### 5. v1_new API 업데이트
- `backend/app/api/v1_new/globe.py` - is_light→wikidata_id 필터, is_region→location_type 필터, type→location_type
- `backend/app/api/v1_new/explore.py` - type/modern_name/country 참조 → location_type
- `backend/app/api/v1_new/stats.py` - country 기반 통계 → location 기반 통계
- `backend/app/core/sheba/observer.py` - modern_name → location_names 조회

### 6. 프론트엔드 업데이트
- `frontend/src/types/index.ts` - Location 인터페이스 슬림화
- `frontend/src/components/detail/LocationDetailView.tsx` - type→location_type, 삭제된 필드 제거
- `frontend/src/components/detail/EventDetailPanel.tsx` - modern_name, country 표시 제거
- `frontend/src/components/navigator/LocationTab.tsx` - type→location_type, country 제거
- `frontend/src/components/story/PlaceStory.tsx` - 삭제된 필드 제거
- `frontend/src/components/wiki/WikiPanel.tsx` - modern_name 표시 제거
- `frontend/src/components/search/SearchBar.tsx` - modern_name 표시 제거

## 결과
- 성공: 모든 스키마 변경, 모델, API, 프론트엔드 업데이트 완료
- 마이그레이션 미실행 (DB 전환 필요)

## 변경 파일 목록
```
backend/alembic/versions/300_location_system_overhaul.py (신규)
backend/app/models/location.py (재작성)
backend/app/models/event_coords_cache.py (신규)
backend/app/models/territory.py (신규)
backend/app/models/associations.py (수정)
backend/app/models/__init__.py (수정)
backend/app/schemas/location.py (재작성)
backend/app/api/v1/locations.py (재작성)
backend/app/services/location_service.py (재작성)
backend/app/services/search_service.py (수정)
backend/app/services/event_service.py (수정)
backend/app/services/hybrid_search.py (수정)
backend/app/api/v1_new/globe.py (수정)
backend/app/api/v1_new/explore.py (수정)
backend/app/api/v1_new/stats.py (수정)
backend/app/core/sheba/observer.py (수정)
frontend/src/types/index.ts (수정)
frontend/src/components/detail/LocationDetailView.tsx (수정)
frontend/src/components/detail/EventDetailPanel.tsx (수정)
frontend/src/components/navigator/LocationTab.tsx (수정)
frontend/src/components/story/PlaceStory.tsx (수정)
frontend/src/components/wiki/WikiPanel.tsx (수정)
frontend/src/components/search/SearchBar.tsx (수정)
```

## 다음 작업
- `alembic upgrade head` 실행 (마이그레이션 적용)
- location_names 데이터 채우기 (Wikidata 시대별 이름)
- event_locations 매칭 로직 구현 (p276_direct, name_match, coord_nearest)
- 신규 노드 추가 + 재분배 로직 구현
- 위키피디아 역사적 장소 전수 추가
- Person 시스템도 동일 원칙으로 재설계 (플랜 작성 필요)
