# 세션 로그: 2026-02-05 Wikidata Import 구조 개선

## 세션 정보
- **목적**: Wikidata 임포트 구조 완전 재설계
- **이전 문제**: 이벤트의 98.2%가 위치 연결 없음

## 완료한 작업

### 1. 문제 분석 ✓

**기존 import_wikidata_events.py 버그**:
- `location_qid`를 가져오지만 **사용 안 함**
- `primary_location_id` 항상 NULL로 설정
- 결과: 14,131개 이벤트 중 2.5%만 위치 연결

### 2. 데이터/처리 분리 아키텍처 ✓

```
poc/scripts/wikidata/
├── data_access/              # 데이터 접근만
│   ├── sparql_client.py      # SPARQL 쿼리 (rate limit, retry)
│   ├── event_fetcher.py      # 이벤트 페칭
│   └── local_reader.py       # 로컬 덤프 리딩
│
├── processing/               # 처리/변환만
│   ├── parsers.py            # 원시 데이터 파싱
│   ├── transformers.py       # 도메인 모델 변환
│   └── validators.py         # 완전성 검증
│
└── importers/                # DB 임포트
    └── smart_location_importer.py
```

**테스트 결과 (십자군 전쟁 via SPARQL)**:
- 완전한 이벤트: 86.7%
- 위치 있음: 86.7%
- 평균 완전성: 90.5%

### 3. DB 스키마 개선 ✓

#### 새 테이블: location_names
시대별 위치 명칭 관리 (London/Londinium, Seoul/한양/한성)

```sql
CREATE TABLE location_names (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    name VARCHAR(255) NOT NULL,
    name_ko VARCHAR(255),
    valid_from INTEGER,    -- BCE는 음수
    valid_until INTEGER,
    is_primary BOOLEAN,
    wikidata_id VARCHAR(50),
    ...
);
```

#### locations 테이블 확장
- `is_region`: 광역 위치 여부
- `coords_source`: exact/center/inherited
- `canonical_id`: 동일 장소 통합

### 4. SmartLocationImporter ✓

**기능**:
- 좌표 기반 중복 검사 (500m 이내 = 같은 장소)
- 시대별 명칭 자동 추가
- 광역 위치 시드 데이터 (Europe, Holy Land, etc.)
- 좌표 상속 (상위 위치에서)

**테스트 결과**:
| 위치 | QID | is_region | coords |
|------|-----|-----------|--------|
| Holy Land | Q37707 | True | (31.5, 35.0) |
| Europe | Q46 | True | (54.0, 25.0) |
| London | Q84 | False | (51.5, -0.13) |
| Jerusalem | Q1218 | False | (31.8, 35.2) |

### 5. 이벤트 추출 스크립트 ✓

`extract_events_from_dump.py`:
- 로컬 Wikidata 덤프에서 이벤트 추출
- 테스트 결과: 100개 이벤트 중 93% 위치, 95% 날짜

### 6. 이벤트 임포트 스크립트 ✓

`import_extracted_events.py`:
- 추출된 JSONL → DB 임포트
- SmartLocationImporter와 연동하여 위치 자동 생성/연결
- 테스트: Q173220 (2007 Formula One espionage controversy) 임포트 성공

### 7. 마이그레이션 적용 ✓

- `008_location_names` 마이그레이션 성공
- 기존 1,695개 위치 명칭 → location_names로 마이그레이션됨

### 8. 임포트 파이프라인 검증 ✓

**부분 덤프에서 추출 및 임포트 테스트**:
- partial_events.jsonl: 418개 이벤트 추출
- 63개 신규 이벤트 DB 임포트 성공
- **위치 연결률: 96.8%** (61/63)

**데이터 품질**:
- 위치 있음: 82.8%
- 날짜 있음: 94.3%

**임포트된 이벤트 예시**:
- Q1288821: Battle of Abu Klea → Khartoum
- Q1281559: Battle of Isonzo → Soča
- Q1231054: Battle of Gaza → Gaza City

### 9. SPARQL 병목 발견 및 해결 ✓

**문제**: SmartLocationImporter가 새 위치마다 Wikidata SPARQL 쿼리
- 649개 이벤트 임포트에 수 분 소요
- 20만개 이벤트면 수십 시간 걸림

**해결책**: 로컬 덤프에서 위치 데이터도 추출 (구현 완료)

**새 스크립트**:
- `extract_locations_from_dump.py`: 위치 엔티티 추출
- `import_extracted_locations.py`: 위치 임포트 (SPARQL 없음)
- `import_events_fast.py`: 빠른 이벤트 임포트 (DB 조회만)

**새 워크플로우**:
```bash
# 1. 위치 추출 (덤프 완료 후)
python extract_locations_from_dump.py --output locations.jsonl

# 2. 위치 임포트
python import_extracted_locations.py --input locations.jsonl

# 3. 이벤트 추출
python extract_events_from_dump.py --output events.jsonl

# 4. 이벤트 빠른 임포트
python import_events_fast.py --input events.jsonl
```

## 진행 중

### Wikidata 덤프 다운로드
- 현재: ~43GB / 93GB (~46%)
- 백그라운드에서 계속 진행 중
- 연결 끊김 시 자동 재시작 설정

## 생성된 파일

### 마이그레이션
- `backend/alembic/versions/008_location_names_table.py`

### 모델
- `backend/app/models/location_name.py` (NEW)
- `backend/app/models/location.py` (수정 - 새 컬럼 + relationship)
- `backend/app/models/__init__.py` (LocationName 등록)

### 데이터 접근 레이어
- `poc/scripts/wikidata/data_access/__init__.py`
- `poc/scripts/wikidata/data_access/sparql_client.py`
- `poc/scripts/wikidata/data_access/event_fetcher.py`
- `poc/scripts/wikidata/data_access/local_reader.py`

### 처리 레이어
- `poc/scripts/wikidata/processing/__init__.py`
- `poc/scripts/wikidata/processing/parsers.py`
- `poc/scripts/wikidata/processing/transformers.py`
- `poc/scripts/wikidata/processing/validators.py`

### 임포터/추출기
- `poc/scripts/wikidata/importers/smart_location_importer.py`
- `poc/scripts/wikidata/extract_events_from_dump.py`
- `poc/scripts/wikidata/import_extracted_events.py`
- `poc/scripts/wikidata/extract_locations_from_dump.py` (NEW)
- `poc/scripts/wikidata/import_extracted_locations.py` (NEW)
- `poc/scripts/wikidata/import_events_fast.py` (NEW)

### 테스트
- `poc/scripts/wikidata/test_new_architecture.py`
- `poc/scripts/wikidata/test_events.jsonl` (100개 테스트 이벤트)

### 보고서
- `docs/reports/WIKIDATA_IMPORT_MASTER_PLAN.md`
- `docs/reports/WIKIDATA_IMPORT_GAP_ANALYSIS.md`
- `docs/reports/improvements/INDEX.md`
- `docs/reports/improvements/001_IDEAL_LOCATION_STRUCTURE.md`
- `docs/reports/improvements/002_BATCH_IMPORT.md`
- `docs/reports/improvements/003_HIERARCHY_STRUCTURE.md`

## 다음 작업 (다운로드 완료 후)

```bash
cd poc/scripts/wikidata

# 1. 위치 추출 (먼저!)
python extract_locations_from_dump.py --output all_locations.jsonl

# 2. 위치 임포트 (SPARQL 없이 빠름)
python import_extracted_locations.py --input all_locations.jsonl

# 3. 이벤트 추출
python extract_events_from_dump.py --output all_events.jsonl

# 4. 이벤트 빠른 임포트 (DB 조회만)
python import_events_fast.py --input all_events.jsonl
```

**예상 결과**:
- 위치: ~500,000개 (도시, 지역, 자연지형 등)
- 이벤트: ~200,000개 (93%+ 위치 연결)
- 임포트 속도: 분당 수천 개 (SPARQL 없이)

## 핵심 결정사항

1. **시대별 명칭**: `location_names` 테이블로 관리
2. **동일 좌표 = 동일 장소**: `canonical_id`로 통합
3. **광역 위치**: `is_region` 플래그 + 시드 데이터
4. **좌표 상속**: `coords_source`로 출처 추적
5. **데이터/처리 분리**: 각 레이어 독립적으로 테스트 가능

## 성과 지표

| 지표 | 이전 | 현재 (실제 임포트) |
|------|------|-------------------|
| 이벤트 위치 연결률 | 2.5% | **96.8%** |
| 이벤트 날짜 있음 | ? | **94.3%** |
| 시대별 명칭 지원 | 없음 | **지원** |
| 신규 위치 자동 생성 | 수동 | **자동** |

## 현재 DB 상태

| 항목 | 수량 |
|------|------|
| 총 이벤트 | 14,195 |
| 위치 연결된 이벤트 | 408 (2.9%) |
| 총 위치 | 1,776 |

> 참고: 기존 이벤트의 위치 백필은 별도 작업 필요
