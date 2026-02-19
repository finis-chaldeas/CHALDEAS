# Data Enrichment Phase 완료 보고서

**작성일**: 2026-02-16
**실행 시간**: 01:30 ~ 08:16 (약 7시간, 대부분 DB UPDATE 대기)
**환경**: PostgreSQL 18, 데이터 E:\PostgreSQL\data (USB HDD)

---

## 1. 개요

CHALDEAS 프로젝트의 핵심 데이터를 "전화번호부 수준"에서 "의미 있는 랭킹 데이터"로 전환하는 작업.

**핵심 변환**:
- importance 전부 3 → 1~5 실제 분포
- role 2,305건 → 100,597건
- birthplace 0건 → 30,822건
- 12.9M 인물 중 "의미 있는" 190K만 빠르게 서빙

---

## 2. 전/후 비교

### Events (28,331건)

| 항목 | Before | After |
|------|--------|-------|
| importance | **전부 3** (구분 불가) | **1~5 균등 분배** (각 ~5,666개) |
| is_light | 컬럼 없음 | 28,331 TRUE (100%) |

**importance 분포 (After)**:
```
importance 1: ~5,666  (마이너 사건)
importance 2: ~5,666
importance 3: ~5,667
importance 4: ~5,666
importance 5: ~5,666  (마라톤 전투, 테르모필레 등)
```

**가중치**: QRank 50% + connection_count 30% + participant_count 20%

### Persons (12,987,361건)

| 항목 | Before | After |
|------|--------|-------|
| is_light | 컬럼 없음 | **190,710 TRUE** (1.5%) |
| role (전체) | 2,305건 (0.02%) | - |
| role (light) | - | **100,597건** (52.7% of light) |
| birthplace_id (전체) | 0건 | - |
| birthplace_id (light) | - | **30,822건** (16.2% of light) |
| deathplace_id (light) | - | **17,571건** (9.2% of light) |
| birth_year (light) | - | **181,913건** (95.4% of light) |
| death_year (light) | - | **105,317건** (55.2% of light) |
| biography | 0건 | 0건 (미실행) |

**Light persons 선정 기준**:
- event_persons 연결 인물: 90,710명
- QRank 인기도 top 100K: 100,000명 (추가)
- **합계: 190,710명** (전체의 1.5%)

### Locations (2,387,834건)

| 항목 | Before | After |
|------|--------|-------|
| is_light | 컬럼 없음 | **12,908 TRUE** (0.5%) |

**Light locations 구성**:
- Event 연결 장소: 2,921개
- Light person 출생/사망 장소: 9,987개 (추가)

### QRank (신규 테이블)

| 항목 | Before | After |
|------|--------|-------|
| qrank 테이블 | 없음 | **28,691,759행** |
| Event 매칭률 | - | 26,021 / 28,331 (91.8%) |
| Person 매칭률 | - | 4,596,679 / 12,987,361 (35.4%) |

**QRank 분포**:
```
25th percentile:     10
50th percentile:     79
75th percentile:    608
90th percentile:  3,786
95th percentile: 11,576
99th percentile: 92,609
```

---

## 3. 인덱스 추가

| 인덱스 | 테이블 | 유형 |
|--------|--------|------|
| idx_persons_is_light | persons | Partial (WHERE is_light = TRUE) |
| idx_events_is_light | events | Partial (WHERE is_light = TRUE) |
| idx_locations_is_light | locations | Partial (WHERE is_light = TRUE) |
| idx_qrank_wikidata_id | qrank | Primary Key |
| idx_qrank_score | qrank | DESC |

---

## 4. API 변경사항

### is_light 필터 적용

| API | 파일 | 변경 |
|-----|------|------|
| Feed API | `backend/app/api/v1/feed.py` | events/persons 모두 `is_light = TRUE` |
| Events 서비스 | `backend/app/services/event_service.py` | `light_only=True` 파라미터 |
| Persons 서비스 | `backend/app/services/person_service.py` | `light_only=True` 파라미터 |
| Locations 서비스 | `backend/app/services/location_service.py` | `light_only=True` + graceful fallback |
| Locations API | `backend/app/api/v1/locations.py` | `is_light = TRUE` (캐시된 존재 확인) |
| Globe API | `backend/app/api/v1_new/globe.py` | event/location/person 마커 필터 |
| Search API | `backend/app/services/search_service.py` | **변경 없음** (전체 검색 유지) |

### Feed API 최적화

- 기존: correlated subquery로 event_count 계산 (모든 행 스캔)
- 변경: batch SELECT로 결과 행만 조회
- 필터 없을 때 COUNT 쿼리 스킵

---

## 5. 실행 시간 상세

| 단계 | 작업 | 시간 |
|------|------|------|
| QRank 다운로드 | 100.6 MB gz | ~5분 |
| QRank 임포트 | UNLOGGED + COPY 28.7M행 | ~10분 |
| Event importance | NTILE(5) 계산 | ~5분 |
| Light persons 마킹 | event_persons + QRank top 100K | 154분 |
| birthplace_id | entity_properties P19 JOIN | 44분 |
| deathplace_id | entity_properties P20 JOIN | 15분 |
| role | entity_properties P106 DISTINCT ON | 50분 |
| Locations is_light | events + person places | 15분 |
| 인덱스 생성 | 3개 partial index | 4분 |
| **총계** | | **~5시간** |

**병목**: USB HDD의 entity_properties (112M행) full scan. SSD 환경에서는 10~20배 빠를 것으로 예상.

---

## 6. Feed API 테스트 결과

**요청**: `GET /api/v1/feed?year_start=-500&year_end=-300&lat_min=30&lat_max=45&lng_min=20&lng_max=35&limit=5`

**응답** (71초, USB HDD):
```
1. Alexander the Great  (person, importance 5, 356-323 BCE)
2. Battle of Thermopylae (event, importance 5, 480 BCE, 10 connections)
3. Leonidas I           (person, importance 5, ?-480 BCE)
4. Battle of Marathon    (event, importance 5, 490 BCE, 10 connections)
5. Battle of Chaeronea  (event, importance 5, 338 BCE, 6 connections)
```

events_total: 40, persons_total: (계산됨)

---

## 7. 알려진 이슈

### 데이터 품질
- **role 값 "occupation"**: entity_properties P106의 value_string이 실제 직업명이 아닌 프로퍼티명("occupation")으로 들어간 경우 있음
- **Alexander 무(無) birthplace**: birthplace_id가 NULL — entity_properties에 P19 데이터가 없거나 locations 테이블에 매칭 안 됨
- **biography 0건**: Wikipedia 본문 추출 미실행 (sources.content 확인 필요)

### 성능
- Feed API 71초 (viewport 필터 있을 때) — USB HDD 한계
- 필터 없는 Feed 요청은 120초+ 타임아웃 가능

---

## 8. 미완료 항목

| 항목 | 상태 | 비고 |
|------|------|------|
| Wikipedia biography 추출 | 미실행 | sources.content 본문 존재 여부 확인 필요 |
| Wikipedia event description | 미실행 | 1줄 → 2-3문장 보강 |
| role 데이터 정제 | 미실행 | "occupation" 같은 잘못된 값 수정 |
| Heavy entity enrichment | 의도적 미실행 | 12.9M 전체 대상은 USB HDD에서 비현실적 |

---

## 9. 변경 파일 목록

### 신규 생성
- `backend/scripts/enrich_light_persons.py` — 통합 enrichment 스크립트
- `backend/scripts/import_qrank.py` — QRank 임포트
- `backend/scripts/compute_importance.py` — importance 계산
- `backend/scripts/set_is_light.py` — is_light 설정 (enrich_light_persons에 통합)

### 수정
- `backend/app/models/person.py` — is_light Boolean 추가
- `backend/app/models/event.py` — is_light Boolean 추가
- `backend/app/models/location.py` — is_light Boolean 추가
- `backend/app/services/person_service.py` — light_only 파라미터
- `backend/app/services/event_service.py` — light_only 파라미터
- `backend/app/services/location_service.py` — light_only + 캐시된 존재 확인
- `backend/app/api/v1/feed.py` — is_light 필터 + 최적화
- `backend/app/api/v1/locations.py` — is_light 필터
- `backend/app/api/v1_new/globe.py` — 마커 is_light 필터

### 임시 (삭제 가능)
- `backend/scripts/qrank_clean.csv` — QRank CSV (100MB+)
