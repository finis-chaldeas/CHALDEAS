# 개선 #001: 이상적인 위치 구조

> 상태: 분석 완료, DB 변경 제안

## 현재 문제

### 데이터 현황
- 이벤트 14,131개 중 **2.5%만** primary_location 있음
- 위치 1,695개 존재 (모두 좌표 있음)
- **연결이 안 됨**

### 구조적 문제
1. 이벤트 생성 시 위치 연결 누락
2. 위치가 없으면 이벤트 생성해도 지구본에 안 보임
3. 광역 위치 (Holy Land, Mediterranean) 처리 불가
4. **시대별 명칭 변화 미지원** (서울/한양/한성/경성부)

## 이상적인 구조

### 원칙

1. **모든 이벤트는 위치가 있어야 함**
   - 구체적 위치 없으면 → 광역 위치 사용

2. **위치는 계층 구조**
   ```
   Europe (좌표: 중심점)
   └── Holy Land (좌표: 중심점)
       └── Jerusalem (정확한 좌표)
   ```

3. **좌표 상속**
   - 하위 위치 좌표 없으면 → 상위 위치 좌표 사용

4. **시대별 명칭 통합** (NEW!)
   ```
   Location ID: 1234
   좌표: (37.5665, 126.9780)

   Names:
   - "Seoul" (1945~현재, primary)
   - "Gyeongseong" (경성, 1910~1945)
   - "Hanseong" (한성, 1394~1910)
   - "Hanyang" (한양, 1394~1910, alternate)
   - "Wiryeseong" (위례성, BCE18~CE475)
   ```

### 제안 스키마 변경

```sql
-- 1. 위치 명칭 이력 테이블 (NEW!)
CREATE TABLE location_names (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id) NOT NULL,
    name VARCHAR(255) NOT NULL,
    name_ko VARCHAR(255),
    language VARCHAR(10) DEFAULT 'en',     -- en, ko, ja, zh, la (라틴어), ar
    valid_from INTEGER,                     -- 시작 연도 (BCE는 음수)
    valid_until INTEGER,                    -- 종료 연도 (NULL = 현재까지)
    is_primary BOOLEAN DEFAULT FALSE,       -- 해당 시기 대표 명칭
    source VARCHAR(100),                    -- wikidata, manual
    wikidata_id VARCHAR(50),                -- 해당 명칭의 Wikidata QID
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_location_names_location ON location_names(location_id);
CREATE INDEX idx_location_names_period ON location_names(valid_from, valid_until);

-- 2. 위치 계층 명확화
ALTER TABLE locations
ADD COLUMN is_region BOOLEAN DEFAULT FALSE,  -- 광역 여부
ADD COLUMN coords_source VARCHAR(20) DEFAULT 'exact';
-- coords_source: exact (정확), center (중심점), inherited (상위에서 상속)

-- 3. 위치 동일성 (같은 좌표 = 같은 장소)
-- canonical_location_id: 시대별 명칭이 다른 경우 하나로 통합
ALTER TABLE locations
ADD COLUMN canonical_id INTEGER REFERENCES locations(id);
-- NULL이면 자기 자신이 canonical
-- 값이 있으면 해당 ID가 대표 위치
```

### 예시: 서울

```sql
-- locations 테이블
INSERT INTO locations (id, name, latitude, longitude, type, is_region)
VALUES (1234, 'Seoul', 37.5665, 126.9780, 'city', FALSE);

-- location_names 테이블
INSERT INTO location_names (location_id, name, name_ko, valid_from, valid_until, is_primary, language) VALUES
(1234, 'Seoul', '서울', 1945, NULL, TRUE, 'en'),
(1234, 'Gyeongseong', '경성', 1910, 1945, TRUE, 'en'),
(1234, 'Keijō', '경성', 1910, 1945, FALSE, 'ja'),  -- 일본어명
(1234, 'Hanseong', '한성', 1394, 1910, TRUE, 'en'),
(1234, 'Hanyang', '한양', 1394, 1910, FALSE, 'en'),  -- 별칭
(1234, 'Wiryeseong', '위례성', -18, 475, TRUE, 'en');  -- BCE 18년
```

### 쿼리 예시

```sql
-- 1910년에 서울은 뭐라고 불렸나?
SELECT name, name_ko
FROM location_names
WHERE location_id = 1234
  AND is_primary = TRUE
  AND (valid_from IS NULL OR valid_from <= 1910)
  AND (valid_until IS NULL OR valid_until >= 1910);
-- 결과: Hanseong, 한성

-- 특정 이벤트 시점의 위치명
SELECT ln.name
FROM events e
JOIN locations l ON e.primary_location_id = l.id
JOIN location_names ln ON l.id = ln.location_id
WHERE e.id = 5678
  AND ln.is_primary = TRUE
  AND (ln.valid_from IS NULL OR ln.valid_from <= e.year_start)
  AND (ln.valid_until IS NULL OR ln.valid_until >= e.year_start);
```

### 임포트 로직

```python
class SmartLocationImporter:
    def get_or_create(self, qid: str) -> int:
        # 1. wikidata_id로 검색
        existing = self.find_by_wikidata_id(qid)
        if existing:
            return existing.id

        # 2. 좌표로 검색 (같은 좌표 = 같은 장소일 가능성)
        location_data = self.fetch_from_wikidata(qid)
        if location_data.get('latitude'):
            nearby = self.find_by_coords(
                location_data['latitude'],
                location_data['longitude'],
                threshold_km=0.5  # 500m 이내
            )
            if nearby:
                # 기존 위치에 명칭만 추가
                self.add_name_to_location(
                    nearby.id,
                    name=location_data['name'],
                    valid_from=location_data.get('valid_from'),
                    wikidata_id=qid
                )
                return nearby.id

        # 3. 새 위치 생성
        return self.create_location(location_data)
```

## 구현 계획

### Phase 1: 스키마 마이그레이션

1. `location_names` 테이블 생성
2. 기존 `locations.name` → `location_names`로 마이그레이션
3. `canonical_id`, `is_region`, `coords_source` 컬럼 추가

### Phase 2: 광역 위치 시드

```python
REGION_SEEDS = [
    {'qid': 'Q46', 'name': 'Europe', 'lat': 54.0, 'lng': 25.0, 'is_region': True},
    {'qid': 'Q37707', 'name': 'Holy Land', 'lat': 31.5, 'lng': 35.0, 'is_region': True},
    # ...
]
```

### Phase 3: 임포트 로직 개선

1. 좌표 기반 중복 검사
2. 시대별 명칭 자동 수집
3. 위치 연결 필수화

### Phase 4: 기존 데이터 정리

1. 중복 위치 통합 (같은 좌표)
2. 이벤트-위치 backfill

## 예상 결과

| 지표 | 현재 | 목표 |
|------|------|------|
| 위치 있는 이벤트 | 2.5% | **95%+** |
| 시대별 명칭 지원 | 없음 | **지원** |
| 중복 위치 | 다수 | **통합** |
