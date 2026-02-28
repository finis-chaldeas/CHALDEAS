# CLAUDE.md

## Project Overview

CHALDEAS — 3D 글로브 위에서 역사를 시간여행처럼 체험하는 시스템. FGO의 칼데아에서 영감.

**Core**: "모든 역사는 **누가(Person)** **어디서(Location)** **언제(Time)** **무엇을(Event)** 했는가로 결정된다."

**Tech Stack**: React 18 + TypeScript + Vite + react-globe.gl + Zustand | Python 3.12 + FastAPI + SQLAlchemy 2.0 + PostgreSQL 18 (pgvector)

---

## 디자인 원칙 (프론트엔드 작업 전 필독)

**`docs/ideal/` 폴더의 기획 문서를 반드시 먼저 읽을 것.** 특히 `HISTORY_SHIFT.md`.

1. **글로브 = 인터페이스** — "지구본을 돌려. 시간을 움직여. 뭔가 나오면 눌러." 사이드바/메뉴는 보조.
2. **서사 > 메타데이터** — 이야기 텍스트가 먼저. 데이터 나열 X.
3. **줌 = 서사 해상도** — COSMIC(문명) → CONTINENTAL(전쟁) → REGIONAL(전투) → LOCAL(하루하루).
4. **시간 = 차원** — 필터가 아님. 시간을 움직이면 영토/이름/인물/사건이 전부 변함.
5. **2-탭 규칙** — 어떤 콘텐츠든 최대 2번 터치로 도달. 3번 이상 = 설계 실패.
6. **인과 흐름** — 마라톤→테르모필레→살라미스처럼 글로브가 사건을 따라감.

---

## 핵심 기능: History Shift

에이지 오브 엠파이어의 시나리오를 지구본 위에서. 상세: `docs/ideal/HISTORY_SHIFT.md`

**현재 상태**: Phase 1 완료 (895 aggregate 시프트, 9358 페이지), Phase 2 위젯 시스템 구현 중.

| 유형 | chain_type | 예시 |
|------|-----------|------|
| 인물 이야기 | `person_story` | 알렉산더의 일생 |
| 장소 이야기 | `place_story` | 이스탄불 3000년 |
| 시대 이야기 | `era_story` | 르네상스 |
| 인과 사슬 | `causal_chain` | 마라톤→살라미스 |
| 대사건 | `aggregate` | 그리스-페르시아 전쟁 |

### Widget System

위젯 추가 = **파일 1개 + import 1줄**. 미등록 위젯 타입은 무시.

```
1. frontend/src/components/shift/widgets/YourWidget.tsx 생성
2. registerWidget('your_widget', YourWidget) 호출
3. widgets/index.ts에 import './YourWidget' 추가
```

데이터 흐름: `PostgreSQL JSONB → SQLAlchemy → FastAPI → WidgetSlot → WidgetRenderer → Component`

| 항목 | 규칙 | 예시 |
|------|------|------|
| 컴포넌트 파일 | PascalCase | `PrimaryQuote.tsx` |
| type 문자열 | snake_case | `primary_quote` |
| CSS 클래스 | `widget-{약어}-*` | `widget-quote-text` |

---

## 프로젝트 구조

```
frontend/src/
  components/shift/           — ShiftPanel, ShiftBrowser, widgets/
  components/globe/           — GlobeContainer (핵심)
  components/narrative/       — NarrativePanel
  store/                      — globeStore, timelineStore, settingsStore, ...
  hooks/                      — useFlyMode, useGlobeTiles
  types/index.ts              — 모든 타입 정의

backend/app/
  api/v1/                     — 운영 API (events, persons, locations, shifts, ...)
  api/v1_new/                 — 실험 API (chains, explore, globe)
  models/                     — V0 ORM (event, person, location, ...)
  models/v1/                  — V1 ORM (chain.py=시프트, period, polity)
  core/                       — 7-layer subsystems (sheba, logos, papermoon, laplace, trismegistus)
  services/                   — 비즈니스 로직
  scripts/                    — 데이터 스크립트 (seed, enrich, translate, export/import)

docs/ideal/                   — 기획 문서 (PURPOSE, EXPERIENCE, HISTORY_SHIFT, ...)
docs/reference/               — API.md, DATABASE.md
docs/guides/                  — SETUP.md, DEPLOYMENT.md
docs/logs/sessions/           — 세션 로그
```

---

## Commands

### Dev Servers
```bash
cd frontend && npm run dev -- --port 3000     # Frontend (포트 3000 고정)
cd backend && uvicorn app.main:app --reload --port 8100  # Backend (포트 8100 고정)
```

### Database
```powershell
.\tools\switch-db.ps1 compact    # C:\PostgreSQL\data (SSD, 개발용 — 실제 44GB 풀 데이터)
.\tools\switch-db.ps1 archive    # E:\PostgreSQL\data (HDD, 백업용)
.\tools\switch-db.ps1 status     # 현재 상태

cd backend
python -m alembic current        # 현재 버전 확인
python -m alembic upgrade head   # 마이그레이션 적용
```

**⚠️ DB 안전 규칙:**
- **절대 `import_compact.py` 무단 실행 금지** — alembic_version을 200으로 덮어써서 API가 깨짐
- 현재 alembic HEAD: `602_trismegistus_portal` (이 버전이어야 정상 작동)
- `export_compact.py`는 `period_narratives` 등 핵심 테이블을 내보내지 않음 — CSV 백업으로 불충분
- **pg_dump 백업**: `data/compact_export/backup_20260227/chaldeas_full_20260227.dump` (988MB)
- 백업 생성: `pg_dump -h 127.0.0.1 -U chaldeas -Fc chaldeas > backup.dump`
- 복원: `pg_restore -h 127.0.0.1 -U chaldeas -d chaldeas --clean backup.dump`

포트 고정: Frontend=3000, Backend=8100, PostgreSQL=5432, API Docs=http://localhost:8100/docs

### 검증
```bash
cd frontend && npx tsc --noEmit   # TypeScript 검사
cd frontend && npm run build      # 프로덕션 빌드
```

### 배포 (GCP Cloud Run)
```powershell
gcloud builds submit --config=cloudbuild.yaml --project=chaldeas-archive
```
- Frontend: https://www.chaldeas.site (**us-central1** — 커스텀 도메인 때문)
- Backend: asia-northeast3
- 상세: `docs/guides/DEPLOYMENT.md`

---

## 코드 규칙

### 필수 패턴
- **BCE 날짜**: 음수 정수 (-490 = 490 BCE)
- **3언어 (한/일/영)**: 영어 기본 + `_ko`, `_ja` 접미사. 없으면 영어 폴백. 위젯 데이터도 동일 (`text` / `text_ko` / `text_ja`)
- **Windows UTF-8**: Python 파일 I/O에 `encoding='utf-8'` 필수
- **경로**: `pathlib.Path` 사용 권장
- **htmlAltitude**: react-globe.gl에서 반드시 0 (양수 = 패럴랙스 드리프트)
- **htmlElements deps**: 자주 변하는 state를 useMemo deps에 넣지 말 것 → ref + DOM 조작

### AI 모델
| 모델 | 용도 |
|------|------|
| `llama3.1:8b-instruct-q4_0` | 엔티티 추출 (Ollama, 무료) |
| `gpt-5-mini` | 번역, 내러티브 생성 (reasoning 모델 — `max_completion_tokens` 필수, `temperature` 미지원) |
| `gpt-5.1-chat-latest` | 복잡한 체인 생성 |

---

## 작업 워크플로우

### 세션 로그 (필수)
모든 작업에 대해 `docs/logs/sessions/YYYYMMDD_작업명.md` 생성. 내용: 목적, 변경 파일, 결과, 다음 작업.

### 커밋 메시지
```
feat: History Shift 위젯 시스템
fix: 글로브 마커 좌표 오류 수정
docs: 기획 문서 업데이트
```

### 프론트엔드 변경 전 체크리스트
- [ ] `docs/ideal/` 읽었는가?
- [ ] 글로브 중심 설계인가? (사이드바에 쑤셔넣기 X)
- [ ] 서사가 메타데이터보다 먼저 보이는가?
- [ ] 2-탭 규칙 위반 없는가?

### 참고 문서
| 문서 | 내용 |
|------|------|
| `docs/ideal/INDEX.md` | 기획 문서 색인 (읽는 순서 포함) |
| `docs/ideal/HISTORY_SHIFT.md` | 히스토리 시프트 전체 기획 (V1 + V2 보강) |
| `docs/reference/API.md` | API 레퍼런스 |
| `docs/reference/DATABASE.md` | DB 스키마 |
| `docs/guides/SETUP.md` | 개발 환경 설정 |
