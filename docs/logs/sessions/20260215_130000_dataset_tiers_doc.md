# 세션 로그: 2026-02-15 13:00

## 세션 정보
- **플랜 체크포인트**: Sprint 0 (데이터 기반)
- **목적**: 데이터셋 티어 시스템 문서 작성 + TRISMEGISTUS 확장 아키텍처 설계

## 한 작업

### 1. 06_DATASET_TIERS.md 생성
- `docs/planning/next_phase/06_DATASET_TIERS.md` 신규 작성
- 학술 연구 기반 최소 기동 데이터셋 정의:
  - MIT Pantheon: 11,341명 (L≥25), ~85,000명 (L≥15)
  - Cross-Verified Database: 2,290,000명
  - Charles Murray: 4,002명
  - EventKG: 690,000 이벤트
  - Wikipedia Vital Articles: 계층별 문서 수
- 인물 티어 시스템 설계: S(500) / A(15K) / B(85K) / C(500K) / Archive(12M+)
- QRank 기반 SQL 분류 쿼리 작성
- TRISMEGISTUS FGO 너머 확장 아키텍처:
  - 3개 레이어: FGO Layer, Literary Layer, Media Layer
  - `trismegistus` 별도 스키마 설계
  - character_mappings, servant_profiles, source_references 테이블
  - API 엔드포인트 설계
  - 장기: 독립 서비스 분리 경로
- 기존 FGO 데이터 흡수 매핑표

### 2. INDEX.md 업데이트
- `docs/planning/next_phase/INDEX.md` — 06 문서 추가
- `docs/planning/INDEX.md` — Section G에 06 문서 추가

### 3. Feed API ORDER BY 0 버그 수정
- `backend/app/api/v1/feed.py` — qrank 없을 때 `"0"` → `"0::bigint"` 변경
- PostgreSQL에서 `ORDER BY 0`은 유효하지 않은 ordinal position으로 에러 발생
- `0::bigint`은 상수 표현식으로 해석되어 에러 없음

### 4. TypeScript 빌드 확인
- `npx tsc --noEmit` — 0 errors

## 결과
- 06_DATASET_TIERS.md 작성 완료
- Feed API 버그 수정 완료
- TypeScript 빌드 통과

## 현재 상태
- PostgreSQL role UPDATE (PID 47004) 여전히 진행중 — 외부 HDD I/O 제약으로 매우 느림
- psql 새 연결이 안 됨 (서버 I/O 포화)
- pg_ctl status는 running 확인

## 반성
- 외부 HDD에서 12.8M rows UPDATE는 시간이 매우 오래 걸림
- 향후 대규모 UPDATE는 배치로 나누거나 (LIMIT + OFFSET) 야간에 실행해야 함
- 동시에 여러 분석 쿼리 실행하면 I/O 경합이 심각해짐

## 다음 작업
1. role UPDATE 완료 대기
2. 나머지 enrichment SQL 실행 (birth_year, death_year, birthplace_id, deathplace_id)
3. QRank 다운로드 + 임포트 (`backend/scripts/import_qrank.py`)
4. importance 재계산 (`backend/scripts/compute_importance.py`)
5. tier 분류 SQL 실행
6. Wikipedia biography 추출
