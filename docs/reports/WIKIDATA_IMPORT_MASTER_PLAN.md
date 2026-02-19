# Wikidata Import 마스터 플랜

> 최종 목적과 현재 상태, 개선 계획 종합

## 1. 최종 목적 (Goal)

### 1.1 CHALDEAS가 원하는 것

**"모든 역사적 이벤트를 완전한 형태로 저장하고, 3D 지구본에서 시각화"**

완전한 이벤트의 정의:
```
Event {
    name: "Battle of Hastings"          # 필수
    description: "1066년 영국을..."       # 필수 (맥락 설명)
    start_year: 1066                     # 필수 (시간축 배치)
    end_year: 1066                       # 선택
    primary_location: {                  # 필수 (지구본 마커)
        name: "Hastings"
        latitude: 50.8667
        longitude: 0.5833
    }
    participants: [                      # 권장 (인물 연결)
        { name: "William the Conqueror", role: "victor" },
        { name: "Harold II", role: "defeated" }
    ]
    part_of: "Norman Conquest"           # 권장 (계층 구조)
}
```

### 1.2 데이터 흐름 목표

```
┌─────────────────────────────────────────────────────────┐
│           Wikidata (113M+ 엔티티)                        │
│   - 이벤트: ~2M (추정)                                   │
│   - 인물: ~10M                                           │
│   - 장소: ~20M                                           │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼ 필터링
┌─────────────────────────────────────────────────────────┐
│              추출 대상 이벤트                             │
│   - 역사적 이벤트 (전쟁, 전투, 조약, 혁명 등)            │
│   - 완전성 80% 이상                                      │
│   - 예상: 50,000 ~ 200,000개                            │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼ 변환
┌─────────────────────────────────────────────────────────┐
│              CHALDEAS DB                                 │
│   events (id, name, description, year, location_id)     │
│   locations (id, name, lat, lng, type)                  │
│   persons (id, name, birth_year, death_year)            │
│   event_locations (event_id, location_id, role)         │
│   event_persons (event_id, person_id, role)             │
└─────────────────────────────────────────────────────────┘
```

## 2. 현재 상태 분석

### 2.1 기존 import_wikidata_events.py의 문제

| 구분 | 선언 | 실제 구현 | 상태 |
|------|------|----------|------|
| Phase 1: 이벤트 수집 | O | △ | 쿼리만 있음, 분류 없음 |
| Phase 2: 위치 확보 | O | X | **완전 미구현** |
| Phase 3: 인물 확보 | O | X | **완전 미구현** |
| Phase 4: DB 임포트 | O | △ | location 연결 안 함 |

**핵심 버그**: `insert_event()` 함수가 `location_qid`를 받지만 **사용하지 않음**

결과: 13,846개 이벤트 중 **98.2%가 위치 없음**

### 2.2 새 아키텍처 (data_access + processing)

**테스트 결과 (십자군 전쟁)**:
- 완전한 이벤트: 86.7%
- 위치 있음: 86.7%
- 평균 완전성: 90.5%

**구조**:
```
poc/scripts/wikidata/
├── data_access/              # 데이터 접근만
│   ├── sparql_client.py      # SPARQL 쿼리
│   ├── event_fetcher.py      # 이벤트 페칭
│   └── local_reader.py       # 로컬 덤프 리딩
│
├── processing/               # 처리/변환만
│   ├── parsers.py            # 원시 데이터 파싱
│   ├── transformers.py       # 도메인 모델 변환
│   └── validators.py         # 완전성 검증
│
└── importers/                # DB 임포트
    ├── base.py
    ├── location_importer.py
    └── event_importer.py
```

### 2.3 현재 병목

1. **Wikidata SPARQL API 속도**: ~0.6초/쿼리
2. **Rate Limit**: 분당 60-120회 제한
3. **좌표 없는 위치**: 일부 위치가 P625(좌표) 없음

## 3. 장기 개선 계획 (Long-term)

### Phase 1: 로컬 덤프 활용 (진행 중)

**목표**: API 병목 제거

```
Wikidata 덤프 (93GB bz2)
    │
    ▼ 스트리밍 추출
이벤트 JSONL (예상 500MB)
    │
    ▼ 2차 스캔
위치/인물 보강 (참조된 QID만)
    │
    ▼ 변환
도메인 모델
    │
    ▼ 임포트
DB
```

**상태**: 다운로드 진행 중 (현재 ~0.8%)

### Phase 2: 계층 구조 구축

**목표**: part_of 관계로 이벤트 트리 생성

```
십자군 전쟁 (Q12546)
├── 제1차 십자군 (Q79619)
│   ├── 니케아 공방전 (Q...)
│   ├── 안티오키아 공방전 (Q...)
│   └── 예루살렘 공방전 (Q...)
├── 제2차 십자군 (Q...)
│   └── ...
└── ...
```

### Phase 3: 좌표 보강

**목표**: 좌표 없는 위치 처리

전략:
1. 상위 위치(국가/지역)의 좌표 사용
2. GeoNames/Nominatim 폴백
3. 최후: country 중심점

### Phase 4: 품질 관리

**목표**: 지속적 품질 모니터링

```python
# 자동 검증 파이프라인
for event in new_events:
    result = validator.validate(event)
    if not result.is_complete:
        log_issue(event, result.issues)
        queue_for_enrichment(event)
```

## 4. 단기 개선 계획 (Short-term)

### 4.1 [완료] 데이터/처리 분리

- [x] `data_access/` 레이어 생성
- [x] `processing/` 레이어 생성
- [x] 테스트 통과 (90.5% 완전성)

### 4.2 [진행중] 로컬 덤프 다운로드

- [ ] Wikidata 덤프 다운로드 (93GB)
- [ ] 추출 스크립트 테스트
- [ ] 임포트 파이프라인 연결

### 4.3 [다음] Location NOT NULL 제약 해결

문제: `locations.latitude` NOT NULL
해결:
```sql
-- 옵션 A: 제약 완화
ALTER TABLE locations
ALTER COLUMN latitude DROP NOT NULL;

-- 옵션 B: 기본값
INSERT ... latitude = COALESCE(?, 0.0)
```

### 4.4 [다음] 배치 임포트 최적화

현재: 1건씩 INSERT
개선:
```python
# COPY 또는 bulk INSERT
psycopg2.extras.execute_values(
    cursor,
    "INSERT INTO events ...",
    events_data
)
```

## 5. 성공 지표 (KPI)

| 지표 | 현재 | 목표 |
|------|------|------|
| 이벤트 수 | 13,846 | 100,000+ |
| 위치 연결률 | 1.8% | 95%+ |
| 완전한 이벤트 | ~500 | 80,000+ |
| 임포트 속도 | 10/min | 1000+/min |

## 6. 파일 참조

- 기존 문제 분석: `docs/reports/WIKIDATA_IMPORT_GAP_ANALYSIS.md`
- 임포트 재설계: `docs/planning/WIKIDATA_IMPORT_REDESIGN.md`
- 세션 로그: `docs/logs/sessions/20260205_*.md`
