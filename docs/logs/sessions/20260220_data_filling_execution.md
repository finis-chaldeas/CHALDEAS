# 세션 로그: 2026-02-20 Data Filling Execution

## 세션 정보
- **목적**: DATA_FILLING_PLAN.md의 4가지 Gap을 실행하고 검증
- **이전 세션**: 20260220_design_defense.md (docs/ideal/ 작성 + 데이터 갭 분석)

## 실행한 작업

### Gap 1: 이벤트 계층 구조 (fill_event_hierarchy.py)
- **스크립트**: `poc/scripts/fill_event_hierarchy.py`
- **데이터 소스**: Wikidata P361 (part of), P31 (instance of)
- **결과**:
  - 28,331 이벤트 전체 분류 완료
  - hierarchy_level: L1=611, L2=3,924, L3=23,796
  - parent_event_id: 10,013개 연결 (35%)
  - is_aggregate: 1,478개 (큰 전쟁/혁명 등)
  - temporal_scale: evenementielle/conjuncture/longue_duree
- **품질 확인**: 부모-자식 관계 정확 (예: Battle of Aljubarrota → Portuguese Interregnum)
- **캐시**: `poc/data/wikidata/event_hierarchy_cache.json`

### Gap 2: 지명 시간범위 (fill_location_name_dates.py)
- **스크립트**: `poc/scripts/fill_location_name_dates.py`
- **데이터 소스**: Wikidata P1448/P1705 with P580/P582 qualifiers
- **결과**:
  - 17,723개 위치 검색 → 904개에서 시간 데이터 발견
  - 127개 이름 날짜 업데이트, 1개 신규 삽입
  - 전체 248,762개 이름 중 2,471개(1%)에 시간범위 존재
- **품질 확인**: 정확 (예: Abaza: Абакано-Заводская 1868-1921 → Абаза 1921+)
- **캐시**: `poc/data/wikidata/location_names_cache.json`

### Gap 3: 시대 내러티브 (fill_period_narratives.py)
- **스크립트**: `poc/scripts/fill_period_narratives.py`
- **LLM**: Ollama llama3.1:8b-instruct-q4_0 (로컬)
- **결과**:
  - 391개 내러티브 (기존 10 + 신규 381)
  - 6개 지역 + Global: europe(65), near_east(81), east_asia(56), south_asia(45), americas(24), africa(23), global(97)
  - 기간: BCE 3000 ~ CE 2049
  - 315개 스킵 (해당 시대/지역에 데이터 없음)
  - 1개 실패 (1600-1649 CE South Asia - LLM JSON 파싱 오류)
- **품질 확인**: 좋음 (예: 500-451 BCE Europe → "Persia's Fury Unleashes a Golden Age for Greece")
- **소요 시간**: ~40분 (Ollama 로컬, 내러티브당 ~15-20초)

### Gap 4: 이벤트 위치 (fill_event_locations.py)
- **스크립트**: `poc/scripts/fill_event_locations.py`
- **데이터 소스**: Wikidata P276 (location), P17 (country), P625 (coordinates)
- **결과**:
  - 7,060개 위치 없는 이벤트 검색
  - 2,884개에서 위치 데이터 발견
  - 2,202개 업데이트 (P276: 10개, P17: 2,192개)
  - 682개 DB 매칭 실패 (Wikidata에는 있으나 우리 DB에 해당 location 없음)
  - 이벤트 위치 보유율: 75% → 82.9% (23,473/28,331)
- **캐시**: `poc/data/wikidata/event_locations_cache.json`

## 최종 결과 요약

| 항목 | 이전 | 이후 | 개선 |
|------|------|------|------|
| 이벤트 계층 분류 | 0% | 100% (28,331) | +100% |
| 부모 이벤트 연결 | 0% | 35% (10,013) | +35% |
| 지명 시간범위 | 2,344 | 2,471 | +127 |
| 시대 내러티브 | 10 | 391 | +381 |
| 이벤트 위치 보유 | 75% | 82.9% | +7.9% |

## 생성된 파일
- `poc/scripts/fill_event_hierarchy.py` (이전 세션)
- `poc/scripts/fill_location_name_dates.py`
- `poc/scripts/fill_period_narratives.py`
- `poc/scripts/fill_event_locations.py`
- `poc/data/wikidata/event_hierarchy_cache.json`
- `poc/data/wikidata/location_names_cache.json`
- `poc/data/wikidata/event_locations_cache.json`

## 반성
- Gap 3 LLM 생성은 시간이 오래 걸림 (~40분). 병렬화 가능하나 Ollama 로컬이라 효과 제한적
- Gap 2 결과가 예상보다 적음 (1%). Wikidata에 시간 qualifier가 있는 지명이 적기 때문
- Gap 4에서 682개가 매칭 실패 — 우리 DB에 해당 국가/위치가 없는 경우

## 다음 작업
- 프론트엔드 재설계 (플랜 나: Hybrid Rebuild) 진행
- 1개 실패한 내러티브 (1600-1649 CE South Asia) 수동 재시도 가능
