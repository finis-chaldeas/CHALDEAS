# 개선 #001: Location NOT NULL 제약 문제

> 상태: 분석 완료, 구현 대기

## 문제

현재 `locations` 테이블 스키마:
```sql
CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    latitude FLOAT NOT NULL,    -- 문제!
    longitude FLOAT NOT NULL,   -- 문제!
    type VARCHAR NOT NULL       -- 문제!
);
```

Wikidata에서 가져온 위치 중 일부는 좌표가 없음.
- 예: "Holy Land" (Q37707) - 지역 개념, 좌표 없음
- 예: 멸망한 도시들 - 정확한 위치 불명

## 영향

- LocationImporter가 좌표 없는 위치를 **건너뜀**
- 이벤트가 해당 위치 참조 시 **연결 실패**
- 결과: 위치 연결률 저하

## 해결 방안

### 옵션 A: NOT NULL 제약 완화 (권장)

```sql
ALTER TABLE locations
ALTER COLUMN latitude DROP NOT NULL,
ALTER COLUMN longitude DROP NOT NULL;
```

장점:
- 모든 위치 저장 가능
- 좌표 없어도 텍스트 검색/연결 가능
- 나중에 좌표 추가 가능

단점:
- 지구본 표시 시 NULL 체크 필요
- 프론트엔드 수정 필요

### 옵션 B: 기본 좌표 사용

```python
latitude = location.latitude or 0.0
longitude = location.longitude or 0.0
```

장점:
- 스키마 변경 불필요

단점:
- (0, 0)에 마커 몰림 (아프리카 기니만)
- 의미 없는 데이터

### 옵션 C: 상위 위치 좌표 상속

```python
if not location.latitude:
    parent = get_parent_location(location)
    if parent and parent.latitude:
        location.latitude = parent.latitude
        location.longitude = parent.longitude
```

장점:
- 의미 있는 대략적 위치

단점:
- 추가 쿼리 필요
- 상위 위치도 없을 수 있음

## 결정

**옵션 A + C 조합**:
1. NOT NULL 제약 완화 (모든 위치 저장)
2. 좌표 없는 경우 상위 위치 좌표 시도
3. 프론트엔드에서 좌표 없는 위치 필터링

## 구현 계획

1. [ ] Alembic 마이그레이션 생성
2. [ ] LocationImporter 수정 (좌표 없어도 저장)
3. [ ] 좌표 상속 로직 추가
4. [ ] 프론트엔드 마커 표시 로직 수정

## 관련 파일

- `backend/alembic/versions/XXX_allow_null_coordinates.py`
- `poc/scripts/wikidata/importers/location_importer.py`
- `frontend/src/components/Globe.tsx`
