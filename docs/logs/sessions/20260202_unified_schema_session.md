# 세션 로그: 2026-02-02 통합 스키마 구축

## 세션 목표
- 모든 연결에 증거(evidence) 필수인 통합 스키마 구축
- Wikipedia/Gutenberg에서 엔티티 추출 파이프라인 구현

---

## 추출 진행 상태 (실시간)

### 완료된 추출
| 타입 | sources | links | mentions | 소요시간 |
|------|---------|-------|----------|----------|
| events | 13,989 | 2,929,981 | 3,193,864 | ~5시간 |
| locations | 1,682 | 380,596 | 454,149 | ~45분 |

### 완료된 Wikidata 작업 (2026-02-02 14:04)
| 작업 | 처리량 | 결과 | 소요시간 |
|------|--------|------|----------|
| **Wikidata Aliases** | 256,756 엔티티 | **1,581,555 aliases** | 2시간 43분 |

**상세:**
- persons: 241,799 → 1,451,128 aliases
- events: 13,355 → 116,745 aliases
- locations: 1,602 → 13,682 aliases

### 진행 중인 작업
| 작업 | Task ID | 진행률 | 예상 완료 |
|------|---------|--------|-----------|
| Persons Wikipedia 추출 | ba9bf79 | ~24% (64K/270K) | ~24시간 |
| **Wikidata Properties** | bd1c3b5 | 진행 중 | ~1시간 |

### 현재 DB 상태 (2026-02-02 14:04)
| 테이블 | 수량 |
|--------|------|
| sources | 50,641+ |
| links | 5,998,441+ (가족관계 추가 중) |
| mentions | 8,660,251+ |
| tentative_entities | 984,936+ |
| **entity_aliases** | **1,581,555** ✅ |

---

## 완료된 작업

### 1. 통합 스키마 설계 및 생성

| 테이블 | 용도 | 초기 데이터 |
|--------|------|-------------|
| `sources` | 출처 (Wikipedia 문서, Gutenberg 책) | 테스트 100개 |
| `links` | 엔티티 간 연결 (event→person 등) | 테스트 25,216개 |
| `mentions` | 연결의 증거 텍스트 | 테스트 35,299개 |
| `tags` | 그룹 태그 (French Revolution 등) | 162개 |
| `entity_tags` | 엔티티-태그 매핑 | 16,263개 |
| `tentative_entities` | 임시 엔티티 (LLM 분류 대기) | 테스트 403개 |
| `entity_aliases` | 별칭 (Mozart → Wolfgang Amadeus Mozart) | 9,917개 |

### 2. 추출 파이프라인 구현

**파일:**
- `poc/scripts/unified/extract_wikipedia.py` - Wikipedia 추출 메인 스크립트
- `poc/scripts/unified/extract_gutenberg_llm.py` - Gutenberg LLM 추출
- `poc/scripts/unified/fetch_wiki_sitelinks.py` - Wikidata sitelinks 수집
- `poc/scripts/unified/run_full_extraction.py` - 배치 실행 스크립트

**흐름:**
```
Wikipedia ZIM 문서 → 링크 파싱 → sitelinks로 DB 매칭
→ 매칭 성공: links + mentions 생성
→ 매칭 실패: tentative_entities에 저장 (LLM이 나중에 분류)
```

### 3. 데이터 품질

- **Evidence coverage: 100%** - 모든 연결에 증거 있음
- **sitelinks 매핑: 291,204개** - Wikipedia 제목 → DB 엔티티

### 4. 추가된 DB 컬럼

| 테이블 | 컬럼 | 용도 |
|--------|------|------|
| persons/events/locations | `auto_created_at` | 자동 생성 시간 |
| persons/events/locations | `auto_created_source` | 자동 생성 출처 |
| persons/events/locations | `classification_method` | 분류 방법 |
| persons/events/locations | `needs_review` | LLM 검토 필요 여부 |

---

## 해결된 문제

### 1. 전체 추출 실패 → ✅ 해결됨
- **원인**: 트랜잭션 처리 오류 (source 커밋 전 mentions 삽입 시도)
- **해결**: `extract_wikipedia.py`에서 source 삽입 직후 `self.conn.commit()` 추가
- **결과**: events/locations 완료, persons 진행 중

### 2. Wikipedia 타이틀 매칭 실패 → ✅ 해결됨
- **원인**: DB 엔티티 이름으로 Wikipedia 문서 검색 시 불일치
- **해결**: sitelinks 파일 사용 (Wikipedia 타이틀 → DB 엔티티 매핑)
- **결과**: 291,204개 매핑으로 높은 매칭률 달성

---

## 남은 문제점

### 1. Wikipedia ZIM에서 QID 추출 불가 ⚠️
- Wikipedia 덤프에 Wikidata QID가 포함되지 않음
- 해결: 나중에 Wikidata API로 QID 보충 필요

### 2. tentative_entities 분류 필요 ⚠️
- 현재 ~100만개 미분류 엔티티 축적 중
- LLM 분류 스크립트 구현 필요

---

## 다음 작업 (TODO)

### 단기 (우선)
1. [x] `extract_wikipedia.py` 트랜잭션 오류 수정 ✅
2. [x] events 56,567개 전체 추출 ✅ (13,989 완료)
3. [x] locations 추출 ✅ (1,682 완료)
4. [ ] persons 추출 (진행 중... 24%)
5. [x] **Wikidata aliases 가져오기** ✅ 완료 (1,581,555 aliases)
   - 스크립트: `poc/scripts/unified/fetch_wikidata_aliases.py`
   - persons: 1,451,128 / events: 116,745 / locations: 13,682
6. [ ] **Wikidata properties 가져오기** (진행 중...)
   - 스크립트: `poc/scripts/unified/fetch_wikidata_properties.py`
   - 좌표, 가족관계, 이벤트 참가자, 분류 정보

### 중기
6. [ ] LLM 분류 백그라운드 스크립트 구현
   - `tentative_entities`에서 pending 항목 가져옴
   - LLM으로 person/event/location 분류
   - 실제 테이블에 생성 + status 업데이트

7. [ ] Wikidata API로 QID 보충
   - `tentative_entities` 및 신규 생성 엔티티에 QID 추가

### 장기
7. [ ] Gutenberg 책 추출 (`docs/planning/GUTENBERG_MERGE_PLAN.md` 참조)
8. [ ] Backend API 새 테이블 연동
9. [ ] 구 테이블 삭제 (event_persons, event_relationships 등)
10. [ ] Frontend 연동

---

## 기존 엔티티 (Wikidata에서 가져온 것)
- persons: 425,552
- events: 56,567
- locations: 40,613

---

## 명령어 참조

```bash
# 단일 이벤트 추출 테스트
python poc/scripts/unified/extract_wikipedia.py --event "Battle of Waterloo" --save

# 이벤트 목록 추출
python poc/scripts/unified/extract_wikipedia.py --event-list poc/data/events_100.txt --save --limit 200

# 전체 추출 (수정 후)
python poc/scripts/unified/run_full_extraction.py --type events
python poc/scripts/unified/run_full_extraction.py --type persons
python poc/scripts/unified/run_full_extraction.py --type locations
```

---

## 파일 구조

```
poc/scripts/unified/
├── extract_wikipedia.py        # Wikipedia 추출 메인
├── extract_gutenberg_llm.py    # Gutenberg LLM 추출
├── fetch_wiki_sitelinks.py     # Wikidata sitelinks 수집
├── fetch_wikidata_aliases.py   # Wikidata aliases 수집 ✅
├── fetch_wikidata_properties.py # Wikidata properties 수집 (진행중)
├── run_wikidata_full.py        # Wikidata 통합 실행 스크립트
└── run_full_extraction.py      # 배치 실행

poc/data/
├── events_100.txt            # 테스트용 이벤트 100개
└── wikipedia_extract/
    └── wiki_sitelinks.json   # sitelinks 매핑 (291,204개)
```

## Wikidata Properties 수집 항목

| Property | 설명 | 적용 대상 |
|----------|------|----------|
| P625 | 좌표 (coordinate location) | locations |
| P22/P25/P26/P40 | 가족관계 (부/모/배우자/자녀) | persons |
| P710 | 이벤트 참가자 (participant) | events → persons |
| P1344 | 참여한 이벤트 (participant in) | persons → events |
| P31 | 분류 (instance of) | all |
| P279 | 상위분류 (subclass of) | all |
