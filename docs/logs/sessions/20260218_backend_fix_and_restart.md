# 세션 로그: 2026-02-18 Backend Fix & Restart

## 세션 정보
- **목적**: Category 모델 수정 후 백엔드 서버 시작 및 API 검증

## 한 작업

### 1. Category 모델 수정 (이전 세션에서)
- **문제**: `Category.persons` relationship이 `Person.category_id` FK를 참조하지만, Migration 301에서 `category_id`가 `persons` → `person_details`로 이동
- **영향**: SQLAlchemy `configure_mappers()` 실패 → 모든 API 500 에러
- **수정**: `backend/app/models/category.py`에서 `persons = relationship("Person", back_populates="category")` 제거

### 2. 백엔드 서버 시작
- `uvicorn app.main:app --reload --port 8100`
- 서버 정상 기동 확인

### 3. API 엔드포인트 검증
| 엔드포인트 | 상태 | 비고 |
|-----------|------|------|
| `/api/v1/events` | 정상 | details 포함 |
| `/api/v1/feed` | 정상 | person + event 통합 |
| `/api/v1/persons` | 정상 | 인물 목록 |
| `/api/v1/globe/markers` | 정상 | 지구본 마커 |

## 결과
- 모든 API 500 에러 해결
- 백엔드 서버 정상 작동 (port 8100)

## 다음 작업
- 프론트엔드에서 실제 데이터 표시 확인
- Person detail view: names, relationships, Wikipedia 링크 표시 확인
- Event detail panel: Wikipedia 링크 표시 확인
