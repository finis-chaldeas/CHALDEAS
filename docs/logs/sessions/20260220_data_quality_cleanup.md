# 세션 로그: 2026-02-20 19:50

## 세션 정보
- **목적**: 데이터 품질 정리 스크립트 구현 (Data Quality Cleanup)

## 한 작업

### 생성한 파일
- `poc/scripts/cleanup_data_quality.py` - 데이터 품질 정리 메인 스크립트

### 스크립트 기능 (5단계)
1. **Step 1: QID Name Resolution** - events(948), persons(27,278), locations(801)의 QID-only 이름을 Wikidata API로 해석. P31 확인으로 잘못 분류된 이벤트 탐지.
2. **Step 2: Fix Misclassified Events** - P31=Q5(human)인 events를 persons로 이전 또는 삭제
3. **Step 3: Fix Person Dates** - birth_year > death_year인 196명의 날짜를 Wikidata에서 재확인하여 수정
4. **Step 4: Fix Event-Person Mismatches** - 인물 생존기간과 이벤트 기간이 50년 이상 불일치하는 링크 제거
5. **Step 5: Report** - 현재 DB 상태 리포트

### 주요 발견/수정 사항
- Wikidata time format이 `+YYYY-MM-DDT00:00:00Z` (4자리 연도)임을 확인
- 196명의 birth > death 문제: Wikidata 자체도 동일한 오류 보유 (원본 소스가 같음)
  - 해결: birth/death를 swap하면 합리적 수명이 됨 (모든 196건 swap으로 해결)
- Event-person 시간 불일치: 34건 발견 (50년 threshold)
- Step 1의 ~29,000 QIDs는 API 배치 호출 필요 (50개씩, 0.2초 간격)

### 실행 방법
```bash
cd backend
python ../poc/scripts/cleanup_data_quality.py --dry-run          # 리포트만
python ../poc/scripts/cleanup_data_quality.py                     # 전체 실행
python ../poc/scripts/cleanup_data_quality.py --step 1            # 단계별 실행
python ../poc/scripts/cleanup_data_quality.py --step 1 --dry-run  # 단계별 리포트
```

### 캐시
- `poc/data/wikidata/entity_labels_cache.json` - Wikidata API 결과 캐시

## 결과
- 모든 단계 dry-run 테스트 통과
- Step 3: 196건 모두 swap으로 해결 가능 확인
- Step 4: 34건 불일치 탐지 확인
- Step 5: 정확한 카운트 확인 (events 948, persons 27,278, locations 801, bad_dates 196, mismatches 34)

## 반성
- 초기 time parser가 Wikidata의 4자리 연도 포맷을 잘못 처리 → 첫 dash까지 파싱으로 수정
- birth > death가 Wikidata에서도 동일하다는 사실을 API 테스트로 발견 → swap 전략으로 변경

## 다음 작업
- `python ../poc/scripts/cleanup_data_quality.py` 실제 실행 (--dry-run 없이)
- Step 1 실행 시 ~2분 소요 예상 (580 batches, 0.2초 간격)
- 실행 후 검증 쿼리로 잔여 이슈 확인
