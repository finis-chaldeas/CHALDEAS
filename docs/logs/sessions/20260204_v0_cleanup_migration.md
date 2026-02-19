# 세션 로그: 2026-02-04 V0 정리 및 마이그레이션

## 세션 정보
- **목적**: V0 기반 모든 작업물 백업 이동, V2 기반 클린 스타트
- **백업 위치**: `D:\chaldeas_back`

---

## 문제 발견

### 1. Gutenberg 작업을 V0에 잘못 추가
- batch_id: `gutenberg_books_20260204_104122`
- 255,267개 text_mentions를 V0 테이블에 추가
- **V2 플랜 무시하고 기존 DB에 작업함**

### 2. 기존 V0 데이터 오염 확인
- 728,506개 text_mentions (batch_id NULL) - 오염됨
- "Uruzgan wedding bombing" 소스에 페르시아 건국 이벤트 연결 등 비정상 데이터
- event_persons에 독일 학자들이 페르시아 건국 인물로 연결

---

## 백업으로 이동할 것 (D:\chaldeas_back)

### 데이터베이스
- [ ] `chaldeas_v0_full_20260204.sql` - 전체 DB 덤프

### poc/data/ (오래된 추출 데이터)
- [ ] `integrated_ner_full/` - NER 추출 결과
- [ ] `wikipedia_extract/` - 위키피디아 추출
- [ ] `wikipedia_enriched/` - 위키피디아 보강 데이터
- [ ] `wikipedia_full/` - 위키피디아 전체
- [ ] `wikipedia_persons/` - 위키피디아 인물
- [ ] `normalized/` - 정규화 데이터
- [ ] `book_samples/` - 책 샘플
- [ ] `book_contexts/` - 책 컨텍스트

### poc/scripts/ (V0 대상 스크립트)
- [ ] `deprecated_garbage_20260201/` - 이미 deprecated 표시된 것들
- [ ] `cleanup/` 일부 - V0 대상 정리 스크립트
- [ ] V0 테이블 대상 스크립트들

### 기타
- [ ] 루트의 임시 파일들 (*.json, *.sql.gz 등)

---

## 유지할 것 (원래 위치)

### V2 관련
- `backend/app/models/v2/` - V2 모델
- `backend/alembic/versions/100_create_v2_schema.py` - V2 스키마
- `poc/scripts/v2/` - V2 스크립트 (work_logger, tiered_llm, cost_tracker 등)
- `poc/scripts/wikidata/` - Wikidata 임포트 (V2용)
- `poc/scripts/benchmark/` - LLM 벤치마크

### 프론트엔드/백엔드 코어
- `frontend/` - 프론트엔드 코드
- `backend/app/` - 백엔드 코드 (V2 모델 포함)
- `backend/alembic/` - 마이그레이션

### 문서/로그
- `docs/logs/` - 작업 로그 (기록 보존)
- `docs/planning/` - 계획 문서
- `CLAUDE.md` - 프로젝트 가이드

### 데이터 소스
- `data/kiwix/` - ZIM 파일 (원본 소스)
- `tools/book_extractor/` - 추출 도구

---

## 작업 순서

1. [x] 백업 디렉토리 생성 (D:\chaldeas_back)
2. [x] DB 전체 덤프 - 진행 중 (13GB+)
3. [x] poc/data/ 이동 완료
4. [x] poc/scripts/ deprecated 이동 완료
5. [x] 루트 임시 파일 이동 완료
6. [x] /backups 폴더 이동 완료
7. [ ] V0 text_mentions 삭제 (DB에서)
8. [ ] V2 text_mentions 테이블 생성
9. [ ] Gutenberg 재작업 (V2 엔티티만 대상)

---

## 이동된 파일들

### D:\chaldeas_back\poc_data\
- integrated_ner_full/, integrated_ner_pilot/ - NER 추출 결과
- wikipedia_extract/, wikipedia_enriched/, wikipedia_full/, wikipedia_persons/
- book_samples/, book_contexts/, normalized/
- archivist_results/, reconcile_results/, enrichment_results/
- model_comparison/, pilot/, batch/, stories/, test_v3/, logs/
- 각종 .json, .log, .jsonl 임시 파일들

### D:\chaldeas_back\poc_scripts\
- deprecated_garbage_20260201/ - 이전 deprecated 스크립트
- verify/ - V0 검증 스크립트
- integrated_ner/ - NER 추출 스크립트

### D:\chaldeas_back\root_temp\
- agent_test.json, openapi_check.json
- chaldeas_dump.sql, chaldeas_full_20260119.dump, chaldeas_prod.sql.gz
- uncertain_events_batch1.json, uncertain_events_batch2.json

### D:\chaldeas_back\backups\
- analysis/, change_logs/
- backup_full_*.sql (6.6GB+)
- events_*.json, locations_*.json

---

## 유지된 파일들

### poc/data/ (V2 관련)
- benchmark/ - LLM 벤치마크 결과
- benchmark_results/ - 벤치마크 원본
- wikidata/ - Wikidata 임포트 데이터
- seeds/ - 시드 데이터

### poc/scripts/ (V2 관련)
- v2/ - V2 스크립트 (work_logger, tiered_llm 등)
- wikidata/ - Wikidata 임포트 스크립트
- benchmark/ - 벤치마크 스크립트
- hierarchy/ - 계층 구조 스크립트
- cleanup/ - 정리 스크립트 (일부)
- unified/ - 통합 추출 스크립트

---

## DB 정리 결과

### 삭제됨
- text_mentions: 1,017,001개 전체 삭제
- event_persons (bad roles): 1,111,620개 삭제
  - content_mention: 703,622
  - mentioned: 393,983
  - wikipedia_link: 14,015

### 유지됨
- event_persons: 204,507개
  - participant: 201,589 (Wikidata P607)
  - significant_event: 2,906
  - subject: 12

### V2 테이블 (그대로)
- events_v2: 4,055
- person_event_roles: 318,370
- work_logs: 10
- clusters: 45

---

## 진행 상태
- [x] DB 덤프 완료 (17GB)
- [x] V0 데이터 삭제 완료
- [x] EntityMatcher 수정 (wikidata_only 모드 추가)
- [x] match_books_local.py V2 모드로 수정
- [x] Gutenberg V2 매칭 1차 (192/252권, 166,615 mentions)
- [ ] Gutenberg V2 매칭 2차 (재시작, 나머지 60권 처리 중)
- [x] API V2 모드 적용 완료

## API V2 필터 적용
- `event_service.py`: wikidata_id IS NOT NULL 필터 추가
- `person_service.py`: wikidata_id IS NOT NULL 필터 추가
- `location_service.py`: wikidata_id IS NOT NULL 필터 추가
- `search_service.py`: 검색에도 wikidata 필터 추가

## 결과
| 항목 | V0 (이전) | V2 (현재) |
|------|-----------|-----------|
| Events | 43,210 | 3,458 |
| Persons | ~420,000 | 50,454 |
| text_mentions | 0 → V2 | 166,963+ |

## 확인 명령어
```sql
-- 진행 상황 확인
SELECT batch_id, COUNT(*) FROM text_mentions GROUP BY batch_id;

-- 전체 mentions
SELECT COUNT(*) FROM text_mentions;
```

---

## 최종 결과 (2026-02-04 완료)

### Gutenberg V2 매칭 완료
- **총 text_mentions**: 194,062개
  - 1차 배치 (gutenberg_v2_20260204_183002): 166,615개
  - 2차 배치 (gutenberg_v2_20260204_205747): 27,447개
- **Gutenberg 소스**: 253권 처리 완료

### 엔티티별 현황
| 엔티티 타입 | 고유 엔티티 | 멘션 수 |
|------------|-----------|---------|
| Person | 15,578 | 124,086 |
| Location | 575 | 35,430 |
| Event | 2,307 | 34,546 |

### API V2 필터 적용됨
- 모든 서비스에서 `wikidata_id IS NOT NULL` 필터 적용
- 프론트엔드에서 V0 데이터 완전히 숨김

---

## V0 완전 삭제 (2026-02-05)

### 삭제된 V0 데이터
- Events: 42,436개
- Persons: 183,747개
- Locations: 39,004개
- 관련 테이블: person_locations, event_locations, person_relationships, location_relationships 등

### 최종 데이터베이스 상태
| 테이블 | 수량 | 비고 |
|--------|------|------|
| Events | 14,131 | 100% Wikidata |
| Persons | 241,805 | 100% Wikidata |
| Locations | 1,609 | 100% Wikidata |
| text_mentions | 292,874 | Gutenberg 253권 |
| event_persons | 204,496 | Wikidata P607 |

### V0 잔여
- Events: 0
- Persons: 0
- Locations: 0

**모든 데이터가 V2 (Wikidata 기반)으로 정리됨**

---

*작성: 2026-02-04*
*최종 업데이트: 2026-02-05*
