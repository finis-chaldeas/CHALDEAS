# 세션 로그: 2026-02-13 23:30

## 세션 정보
- **목적**: 로케이션 없는 이벤트 3개 분석 - 왜 위키데이터 추출 과정에서 로케이션이 없게 되었는지

## 작업 진행

### 1. 로케이션 없는 이벤트 3개 선택 (랜덤)

| ID | Title | Wikidata ID | Date |
|----|-------|-------------|------|
| 5301 | Battle of Flarchheim | Q322345 | 1080 |
| 5425 | Battle of Ragaz | Q681720 | 1446 |
| 5266 | Montreal Protocol | Q219438 | 1987 |

### 2. Wikidata API 조회 결과

**Q322345 (Battle of Flarchheim):**
- P276 (location): Q288161 (Flarchheim)
- P17 (country): NOT FOUND
- P625 (coordinates): NOT FOUND

**Q681720 (Battle of Ragaz):**
- P276 (location): Q95759 (Ragaz)
- P17 (country): NOT FOUND
- P625 (coordinates): NOT FOUND

**Q219438 (Montreal Protocol):**
- P276 (location): NOT FOUND
- P17 (country): NOT FOUND
- P625 (coordinates): NOT FOUND

### 3. DB 확인

- Q288161 (Flarchheim): **DB에 없음**
- Q95759 (Ragaz): **DB에 없음**

### 4. 추출 스크립트 분석

`poc/scripts/wikidata/backfill_event_locations.py` 확인:

이 스크립트의 동작:
1. events 테이블에서 wikidata_id 있고 primary_location_id 없는 이벤트 조회
2. Wikidata SPARQL로 P276 (location) 조회
3. 해당 location QID로 locations 테이블에 레코드 생성
4. events.primary_location_id 연결

## 결론: 로케이션 없는 3가지 원인

| 이벤트 | 원인 | 상세 |
|--------|------|------|
| Battle of Flarchheim | **백필 스크립트 미실행** | Wikidata에 P276=Q288161 있음. 하지만 Q288161이 DB에 없음. `backfill_event_locations.py`가 이 이벤트를 처리 안 했거나 실패함 |
| Battle of Ragaz | **백필 스크립트 미실행** | Wikidata에 P276=Q95759 있음. 동일 문제. |
| Montreal Protocol | **Wikidata에 위치 없음** | 국제 조약이라 특정 위치 없음. P276 자체가 없음 |

## 핵심 문제

1. **`backfill_event_locations.py` 실행 안 됨 또는 부분 실행**: 23,857개 이벤트에 위치가 없음 (84%)
2. **좌표 없는 location**: P276은 있지만 P625(좌표)가 없는 경우도 있음

## 변경 파일
- (이 로그 파일만)

## 다음 작업
- `backfill_event_locations.py --all` 실행하여 위치 백필 필요
