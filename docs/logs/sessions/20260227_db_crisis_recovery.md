# DB 위기 복구 — alembic_version 200 문제

**날짜**: 2026-02-27
**목적**: alembic_version이 200으로 리셋되어 API 전체 실패 → 원인 파악 및 복구

---

## 증상

- 프론트엔드 글로브 확대 시 콘솔 500 에러 (timeline, events, smart-markers)
- `period_narratives`, `event_details` 등 테이블이 "없다"는 에러

## 원인

`import_compact.py`가 실행되면서 `alembic_version`을 CSV 값(`200_connections`)으로 덮어씀.
**실제 테이블과 데이터는 모두 DB에 존재**했으나, alembic이 200이라 API 코드가 참조하는 테이블을 못 찾음.

### 핵심 포인트
- `import_compact.py`는 테이블을 DROP하지 않음 — 있는 테이블만 TRUNCATE+COPY
- `period_narratives`는 import 목록에 없어서 TRUNCATE도 안 됨 → 데이터 391행 무사
- `event_details` (28,331행), `person_details` (175,576행), `chain_segments` (9,358행) 모두 무사

## 복구 과정

1. `alembic upgrade head` 실행 → 601_add_widgets_jsonb로 복원
2. globe.py DB 호환 해킹 원복 (e.description → ed.description, connection_count → global_score)
3. 이전 세션에서 수정한 7개 파일 `git checkout --`으로 원복 (timeline.py, feed.py, featured.py, story.py, explore.py, stats.py, event.py)
4. 백엔드 재시작 (`PYTHONIOENCODING=utf-8`)

## 데이터 현황 (복구 후)

| 테이블 | 행수 | 비고 |
|--------|------|------|
| events | 28,331 | |
| event_details | 28,331 | description 26,590개 |
| persons | 190,710 | |
| person_details | 175,576 | |
| period_narratives | 391 | headline_ko 42개 번역됨 |
| entity_narratives | 7,412 | |
| historical_chains | 895 | |
| chain_segments | 9,358 | narrative 9,059개, narrative_ko 3,356개 |

## API 검증

- `/api/v1/globe/smart-markers` ✅ 4 heroes, 113 total events
- `/api/v1/timeline/periods` ✅ 2 items
- `/api/v1/events` ✅
- `/api/v1/shifts` ✅

## 교훈 — 다시는 이런 일 없도록

1. **`import_compact.py` 절대 무단 실행 금지** — alembic_version 덮어쓰기
2. **`export_compact.py`는 period_narratives, entity_narratives 미포함** — CSV 백업 불충분
3. **pg_dump 풀 백업 필수**: `data/compact_export/backup_20260227/chaldeas_full_20260227.dump`
4. DB 스키마 변경 후(migration 300+): `events.description` 삭제됨 → `event_details` 사용
5. `persons`는 `global_score` (not `connection_count`)

## 변경 파일

| 파일 | 변경 |
|------|------|
| `backend/app/api/v1_new/globe.py` | ed.description 복원 (3곳), global_score 복원, event_details JOIN 복원 |
| `CLAUDE.md` | DB 안전 규칙 추가 |
| `MEMORY.md` | DB 스키마 정보 대폭 업데이트 |
