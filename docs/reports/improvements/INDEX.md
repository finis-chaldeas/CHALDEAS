# Wikidata Import 개선 목록

## 현재 상태

**Wikidata 덤프 다운로드**: ~4.6% (4.3GB/93GB) 진행 중

## 완료된 작업

### 데이터/처리 분리 아키텍처 ✓

```
poc/scripts/wikidata/
├── data_access/              # 데이터 접근만
├── processing/               # 처리/변환만
└── importers/                # DB 임포트
```

테스트 결과: 90.5% 완전성 달성

### DB 스키마 설계 ✓

1. `location_names` 테이블 (시대별 명칭)
2. `locations` 컬럼 추가: `is_region`, `coords_source`, `canonical_id`
3. 마이그레이션 생성: `008_location_names_table.py`

## 우선순위별 정리

### 긴급 (이번 주)

| # | 제목 | 상태 | 파일 |
|---|------|------|------|
| 001 | 위치 구조 개선 | **구현 중** | [001_IDEAL_LOCATION_STRUCTURE.md](001_IDEAL_LOCATION_STRUCTURE.md) |
| 002 | 배치 임포트 최적화 | 계획 중 | [002_BATCH_IMPORT.md](002_BATCH_IMPORT.md) |

### 중요 (다음 주)

| # | 제목 | 상태 | 파일 |
|---|------|------|------|
| 003 | 이벤트 계층 구조 | 설계 중 | [003_HIERARCHY_STRUCTURE.md](003_HIERARCHY_STRUCTURE.md) |

### 일반 (이번 달)

| # | 제목 | 상태 |
|---|------|------|
| 004 | 좌표 보강 파이프라인 | 미시작 |
| 005 | 품질 대시보드 | 미시작 |
| 006 | 증분 업데이트 | 미시작 |

## 진행 현황

```
[██████████] 데이터/처리 분리 (완료)
[████░░░░░░] 로컬 덤프 (다운로드 ~5%)
[████████░░] 위치 구조 개선 (마이그레이션+모델 완료, 테스트 대기)
[░░░░░░░░░░] 배치 임포트
[░░░░░░░░░░] 계층 구조
```

## 새로 생성된 파일

### 마이그레이션
- `backend/alembic/versions/008_location_names_table.py`

### 모델
- `backend/app/models/location_name.py`
- `backend/app/models/location.py` (수정)
- `backend/app/models/__init__.py` (수정)

### 임포터
- `poc/scripts/wikidata/importers/smart_location_importer.py`

### 보고서
- `docs/reports/WIKIDATA_IMPORT_MASTER_PLAN.md`
- `docs/logs/sessions/20260205_wikidata_restructure.md`

## 마스터 문서

전체 계획: [WIKIDATA_IMPORT_MASTER_PLAN.md](../WIKIDATA_IMPORT_MASTER_PLAN.md)
