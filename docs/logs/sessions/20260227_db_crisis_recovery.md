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

## 추가 수정

### WorldBriefing 언어 버그
- `preferredLanguage === 'ko'` → `getEffectiveLanguage(preferredLanguage)` 사용
- `'auto'` 설정일 때 브라우저 언어 감지 작동하도록 수정
- 한/일/영 동적 필드 참조 (`headline_{lang}`, `narrative_{lang}`)

### 배포 이슈
- Git push 실패: 대용량 파일 3개 (qrank 590MB 등) → `git filter-branch`로 제거
- Cloud Run 시작 실패: `sentry-sdk` requirements.txt 누락 → 추가
- 최종 배포 성공 (7분 22초)

## 프로덕션 Cloud SQL 스키마 복구

배포 후 모든 API가 500 에러 — 프로덕션 DB가 alembic 003 수준 (로컬은 601).
자동 마이그레이션 불가 (CASCADE 충돌, 권한 문제) → 수동 스키마 동기화.

### 수동 생성한 테이블 (프로덕션)
| 테이블 | 행수 | 비고 |
|--------|------|------|
| event_details | 51,669 | events에서 마이그레이션 |
| person_details | 285,750 | persons에서 마이그레이션 |
| location_details | 34,299 | locations에서 마이그레이션 |
| location_names | 0 | 빈 테이블 |
| person_names | 0 | 빈 테이블 |
| territories | 0 | 빈 테이블 |
| territory_locations | 0 | 빈 테이블 |
| period_narratives | 0 | 로컬은 391행 |
| entity_narratives | 0 | 로컬은 7,412행 |
| location_relationships | 0 | |
| location_sources | 0 | |
| person_locations | 0 | |
| user_feedback | 0 | |

### 추가한 컬럼 (~30개)
events: title_ja, parent_event_id, hierarchy_level, parent_status, is_aggregate, aggregate_type, importance_score, wikidata_id
persons: name_ja, domain, description, description_model, description_at, importance
locations: name_ja, tier, wikidata_id, location_type, parent_location_id
historical_chains: is_published, view_count, avg_rating, display_type, chapter_count, globe_importance, thumbnail_url, parent_shift_id
chain_segments: widgets, chapter_title, chapter_number, page_narrative, page_narrative_ko, sub_shift_id, media_url
sources: source_type + 기타

### 데이터 보강
- events: NULL importance → 2 (43,081행), 주요 전투 → 5 (84행), 전쟁/혁명 → 4 (528행)
- 성능 인덱스 7개 추가

### 프로덕션 DB 접속 정보
- Cloud SQL: `chaldeas-db` @ `34.22.103.164`
- chaldeas: `chaldeas_gcp_2025`
- postgres: `chaldeas_postgres_2025`
- Alembic: stamped to `601_add_widgets_jsonb`

## 최종 상태

모든 주요 API 엔드포인트 200 OK:
- `/api/v1/events/{id}` ✅
- `/api/v1/persons/{id}` ✅
- `/api/v1/locations/{id}` ✅
- `/api/v1/globe/smart-markers` ✅
- `/api/v1/timeline/periods` ✅
- `/api/v1/shifts` ✅ (데이터 없음 — 체인 미배포)
- Frontend `www.chaldeas.site` ✅ 로딩

### 데이터 전체 교체 (compact DB → production)

프로덕션에 있던 raw archive 데이터(51K 중복 이벤트, 관계 0)를 로컬 compact DB 데이터로 전체 교체:

1. 프로덕션 테이블 전체 DROP
2. 로컬 스키마 pg_dump → 프로덕션 import (44 테이블 생성)
3. 로컬 데이터 pg_dump (387MB, --data-only) → 프로덕션 import
   - FK 제약 먼저 DROP → 데이터 import → FK 복원
   - Cloud SQL은 DISABLE TRIGGER ALL 불가 (superuser 필요)
   - SESSION AUTHORIZATION, \restrict 라인 제거 필요
4. sources 테이블: content_raw/content_html 빈 문자열로 경량 import (27MB vs 2.5GB)
5. FK 제약 복원, 시퀀스 리셋, alembic 601 stamp

### 최종 데이터 현황

| 테이블 | 프로덕션 (교체 후) | 비고 |
|--------|------------------|------|
| events | 28,331 | 중복 제거, 한글 제목 포함 |
| event_persons | 122,407 | 참여자 연결 |
| event_sources | 45,995 | 출처 연결 |
| persons | 190,710 | |
| person_details | 175,576 | 전기/약력 |
| sources | 186,583 | 경량 (본문 없음) |
| locations | 17,807 | |
| period_narratives | 391 | 42개 한국어 번역 |
| entity_narratives | 7,412 | |
| historical_chains | 895 | |
| chain_segments | 9,358 | |

### 남은 이슈
- 검색 비어있음 (embeddings/벡터 인덱스 미배포)
- sources 본문(content_raw) 비어있음 (텍스트 검색 불가)
- period_narratives 42/391만 한국어 번역됨

## 변경 파일

| 파일 | 변경 |
|------|------|
| `backend/app/api/v1_new/globe.py` | ed.description 복원 (3곳), global_score 복원, event_details JOIN 복원 |
| `frontend/src/components/globe/WorldBriefing.tsx` | getEffectiveLanguage 적용 |
| `backend/requirements.txt` | sentry-sdk 추가 |
| `.gitignore` | 대용량 파일, poc/data/book_contexts 제외 |
| `CLAUDE.md` | DB 안전 규칙 추가 |
| `MEMORY.md` | DB 스키마 정보 대폭 업데이트 |
