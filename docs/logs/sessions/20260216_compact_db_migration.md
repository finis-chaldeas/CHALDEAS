# 세션 로그: 2026-02-16 Compact DB Migration

## 세션 정보
- **목적**: E: HDD의 44GB DB를 C: SSD에 ~150MB compact DB로 마이그레이션하기 위한 스크립트 생성

## 한 작업

### 생성한 파일
1. `backend/scripts/export_compact.py` - E: DB에서 light 데이터 CSV 추출
   - persons (is_light=TRUE ~190K), locations (is_light=TRUE ~12.9K) 필터링
   - events, categories 등 작은 테이블은 전체 추출
   - qrank은 light 엔티티의 wikidata_id 기준 필터링
   - event_sources + 참조되는 sources 최소 서브셋 포함
   - 출력: `C:\Projects\Chaldeas\data\compact_export\`

2. `backend/scripts/import_compact.py` - C: compact DB에 CSV 임포트
   - FK 의존성 순서대로 임포트 (categories → locations → persons → events → junction tables)
   - DISABLE TRIGGER ALL로 FK 체크 우회 (bulk load 성능)
   - 시퀀스 리셋 (setval로 MAX(id) 동기화)
   - ANALYZE 실행

3. `tools/switch-db.ps1` - compact ↔ archive DB 전환
   - `.\tools\switch-db.ps1 compact` (C: SSD)
   - `.\tools\switch-db.ps1 archive` (E: HDD)
   - `.\tools\switch-db.ps1 status` (현재 상태)
   - 같은 포트(5432), 같은 DATABASE_URL → 코드 변경 없음

### 수정한 파일
4. `CLAUDE.md` - Database 섹션 업데이트
   - Dual DB 설정 (Compact vs Archive) 문서화
   - switch-db.ps1 사용법 추가
   - Fixed Ports, Data Paths 섹션 업데이트

## 결과
- 4개 파일 생성/수정 완료
- 실제 실행은 미수행 (E: DB 접근 필요)

## 다음 작업 (사용자 실행)
1. E: DB 시작 → `python scripts/export_compact.py` 실행
2. E: DB 중지 → C: initdb → C: DB 시작
3. `alembic upgrade head` → `python scripts/import_compact.py`
4. 검증 (COUNT, Feed API, Frontend)
