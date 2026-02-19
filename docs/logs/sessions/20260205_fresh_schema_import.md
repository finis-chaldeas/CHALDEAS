# 세션 로그: 2026-02-05 Fresh Schema Import

## 세션 정보
- **시작 시간**: 2026-02-05 14:00
- **목적**: 기존 DB 폐기, 새 스키마로 Wikidata 임포트
- **이전 세션**: 20260205_wikidata_restructure.md

## 배경

이전 세션에서 결정된 새 아키텍처:
```
Location (점)     →  Territory (점 집합)
Person (개인)     →  Group (개인 집합)
Event            →  각 엔티티와 연결
```

기존 DB 문제:
- 14,195 이벤트 중 위치 연결률 2.9%
- 테이블 난잡함 (67개 테이블, 백업 포함)
- V0/V1/V2 혼재

## 작업 계획

### Phase 1: 스키마 준비 ✓
- [x] fresh_schema.sql 작성 (새 테이블 정의)

### Phase 2: 소규모 테스트
- [ ] DB 초기화 (테이블 생성)
- [ ] 위키데이터에서 100개 엔티티 추출
- [ ] 임포트 테스트
- [ ] 검증

### Phase 3: 전체 임포트 (테스트 성공 시)
- [ ] 전체 Location 추출/임포트
- [ ] 전체 Territory 추출/임포트
- [ ] 전체 Person 추출/임포트
- [ ] 전체 Group 추출/임포트
- [ ] 전체 Event 추출/임포트

## 진행 로그

### 14:00 - 스키마 파일 생성

`backend/fresh_schema.sql` 생성:
- 기존 테이블 전부 DROP (67개 → 0개)
- 새 테이블 15개 생성

### 14:10 - DB 초기화 실행 ✓

```bash
# 기존 67개 테이블 모두 삭제
# 새 스키마로 15개 테이블 생성
```

생성된 테이블:
- locations, location_names
- territories, territory_locations, territory_relations
- persons
- groups, group_members, group_relations
- events, event_locations, event_territories, event_persons, event_groups
- sources

### 14:15 - 추출 스크립트 작성 ✓

`poc/scripts/wikidata/fresh_extract.py`:
- 5가지 엔티티 타입 분류 (location, territory, person, group, event)
- Wikidata P31 기반 타입 판별
- bz2 스트리밍 방식

### 14:20 - 소규모 추출 테스트 ✓

```bash
python fresh_extract.py --output test_extract.jsonl --limit 100
```

결과 (46초, 8,852 엔티티 스캔):
- location: 20개
- territory: 20개
- person: 20개
- group: 20개
- event: 20개

### 14:25 - 임포트 스크립트 작성 ✓

`poc/scripts/wikidata/fresh_import.py`:
- QID 캐시 기반 참조 해결
- 의존성 순서대로 임포트 (location → territory → person → group → event)
- 관계 테이블 자동 생성 (event_locations, event_territories 등)

### 14:30 - 소규모 임포트 테스트 ✓

```bash
python fresh_import.py --input test_extract.jsonl
```

결과:
| 테이블 | 수량 |
|--------|------|
| locations | 20 |
| territories | 20 |
| persons | 20 |
| groups | 20 |
| events | 20 |
| event_locations | 1 |
| events with location | 1 |

**event_locations가 1개인 이유**: 이벤트가 참조하는 위치 QID가 추출된 20개 위치에 없음.
전체 추출 시 해결될 문제.

## 생성/수정 파일

| 파일 | 작업 |
|------|------|
| `backend/fresh_schema.sql` | 생성 |
| `poc/scripts/wikidata/fresh_extract.py` | 생성 |
| `poc/scripts/wikidata/fresh_import.py` | 생성 |
| `poc/scripts/wikidata/test_extract.jsonl` | 생성 (테스트 데이터) |

## 소규모 테스트 결론

**성공!** 파이프라인 동작 확인:
1. Wikidata 덤프에서 엔티티 추출 ✓
2. 새 스키마에 임포트 ✓
3. 관계 테이블 생성 ✓

## 14:45 - 스키마 재검토

**문제 발견**: 기존 스키마에 sources/mentions 누락
- UNIFIED_SPEC (2월 1일)의 출처 시스템 무시했음
- DATA_MODEL_REDESIGN (2월 5일)의 Territory/Group만 반영

**해결**: 두 문서 통합
- `docs/planning/FINAL_SCHEMA.md` 작성
- 13개 테이블 확정

**수정 사항**:
- wikidata_id: NOT NULL → NULL 허용 (책 추출 등 대비)
- mention 필수: 출처 없는 데이터 = 쓰레기

## 15:00 - 구현 계획서 작성

`docs/planning/IMPLEMENTATION_PLAN.md`:
- Phase 1: 스키마 구현 (CP-1.1 ~ CP-1.4)
- Phase 2: 추출 스크립트 수정
- Phase 3: 소규모 테스트
- Phase 4: 전체 임포트
- Phase 5: 검증

## 15:10 - Phase 1 완료

13개 테이블 생성:
- `backend/schema/01_base_tables.sql` (locations, territories, sources)
- `backend/schema/02_entity_tables.sql` (persons, groups, events)
- `backend/schema/03_mentions.sql` (mentions)
- `backend/schema/04_relation_tables.sql` (6개 관계 테이블)

## 15:30 - Phase 2 완료

스크립트 작성:
- `poc/scripts/wikidata/extract_with_sources.py` - 엔티티 + source + mention 추출
- `poc/scripts/wikidata/import_with_sources.py` - 임포트

버그 수정:
- sources.wikidata_id에 UNIQUE 제약 추가

## 15:45 - Phase 3 CP-3.1 완료

100개 테스트 결과:
| 항목 | 수량 |
|------|------|
| locations | 20 |
| territories | 20 |
| persons | 20 |
| groups | 20 |
| events | 20 |
| sources | 100 |
| mentions | 100 |

**Mention Coverage: 100%** (모든 엔티티에 출처 연결됨!)

## 15:00 - bz2 압축 해제 시작

**목적**: bz2 스트리밍 속도 제한(~315 entities/s) 해결을 위해 압축 해제

**설정**:
- 입력: `C:/Projects/Chaldeas/data/wikidata/latest-all.json.bz2` (132GB)
- 출력: `D:/project/wikidata/latest-all.json` (~700GB-1TB 예상)
- 스크립트: `poc/scripts/wikidata/decompress_dump.py`

**진행**:
- 시작: 15:00
- 속도: ~30MB/s (108GB/hour)
- 예상 완료: 6-9시간 후

## 16:00 - 기존 추출 폐기, 통합 시스템 설계

**결정**: 기존 추출 방식 폐기
- Wikidata 일부 속성만 추출 → **전체 속성 추출**
- Wikipedia 본문 없음 → **전체 본문 + 하이퍼링크 추출**

**설계 문서**: `docs/planning/UNIFIED_EXTRACTION_SYSTEM.md`

핵심 변경:
1. `entity_properties` 테이블 추가 (모든 Wikidata 속성)
2. Wikipedia 본문 → `sources.content_raw`
3. Wikipedia 하이퍼링크 → `mentions` (링크 위치, 문맥 포함)

## 16:15 - 통합 파이프라인 테스트 완료

### CP-1: 스키마 확장 ✅
- `entity_properties` 테이블 생성
- `sources` 테이블에 `content_html`, `word_count` 추가
- `mentions` 테이블에 `link_text` 추가

### CP-2~6: 파이프라인 테스트 ✅

**테스트 결과:**
| 항목 | 수량 |
|------|------|
| Persons 추출 | 10 |
| 전체 속성 | 3,004 (평균 300개/person) |
| Wikipedia 문서 | 9 |
| 총 단어 수 | ~160,000 |
| 하이퍼링크 | 10,321 |
| Cross-reference 매칭 | 2 (데이터셋 작아서) |
| Mention 커버리지 | **100%** |

**검증 완료:**
```
George Washington - Wikipedia → George W. Bush (link: "George W. Bush")
George W. Bush - Wikipedia → George Washington (link: "George Washington")
```

### 생성/수정 파일
| 파일 | 설명 |
|------|------|
| `docs/planning/UNIFIED_EXTRACTION_SYSTEM.md` | 통합 설계 문서 |
| `backend/schema/05_unified_extensions.sql` | 스키마 확장 |
| `poc/scripts/unified/quick_test.py` | 빠른 테스트 |
| `poc/scripts/unified/pipeline_test.py` | 전체 파이프라인 테스트 |

## 현재 상태

- 압축 해제: 71GB / ~700GB (진행 중, ~6시간 남음)
- 파이프라인: **검증 완료** ✅

## 다음 작업

1. 압축 해제 완료 대기
2. 전체 스케일 추출 스크립트 작성
3. Phase 4: 전체 임포트

---
