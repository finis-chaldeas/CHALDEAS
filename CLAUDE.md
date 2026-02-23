# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CHALDEAS is a world-centric historical knowledge system inspired by Fate/Grand Order's Chaldea. It provides an immersive 3D globe interface for exploring interconnected history, philosophy, science, mythology, and biographical information across time (BCE 3000 to present).

**Core Philosophy**: "모든 역사는 **누가(Person)** **어디서(Location)** **언제(Time)** **무엇을(Event)** 했는가로 결정된다."

**Core Principle**: "World State is explicit and immutable" - Intelligence proposes but never executes.

---

## 프론트엔드 작업 필독 (절대 위반 금지!)

**프론트엔드 코드를 수정하기 전에 반드시 `docs/ideal/` 폴더의 기획 문서를 전부 읽어야 한다.**

### 필독 파일 목록
| 파일 | 핵심 내용 |
|------|----------|
| `docs/ideal/INDEX.md` | 기획 문서 색인 |
| `docs/ideal/PURPOSE.md` | "역사를 시간여행처럼 체험" — 글로브가 시간여행의 창 |
| `docs/ideal/EXPERIENCE.md` | 첫 방문: 글로브만. 2-탭 규칙. 카드 전환 패턴 |
| `docs/ideal/ZOOM_AS_NARRATIVE.md` | 줌 = 서사 해상도 (COSMIC→LOCAL, 각 레벨이 다른 이야기) |
| `docs/ideal/TIME_AS_DIMENSION.md` | 시간 = 차원 (영토/이름/인물/사건 전부 변함) |
| `docs/ideal/RELATIONSHIPS.md` | 3가지 연결: 인물관계, 사건인과, 사건계층 |
| `docs/ideal/HOOKS.md` | 6가지 훅: 익숙한 장소, 알려진 이름, 동시대 서프라이즈 등 |
| `docs/ideal/TRAINING_WHEELS.md` | 가이드 투어, FGO 서번트, 오늘의 역사 |

### 핵심 디자인 원칙 (ideal 문서 요약)
1. **글로브 = 인터페이스**: "지구본을 돌려. 시간을 움직여. 뭔가 나오면 눌러." 사이드바/메뉴는 보조.
2. **서사가 UI를 대체**: 데이터가 충분히 풍부함 → 메타데이터 나열이 아니라 이야기 텍스트가 먼저.
3. **줌 = 서사 해상도**: COSMIC(문명) → CONTINENTAL(전쟁) → REGIONAL(전투) → LOCAL(하루하루). 각 레벨마다 다른 이야기.
4. **시간 = 차원**: 필터가 아님. 시간을 움직이면 영토가 숨쉬고, 이름이 바뀌고, 인물이 교체됨.
5. **2-탭 규칙**: 어떤 콘텐츠든 최대 2번 터치로 도달. 3번 이상 = 설계 실패.
6. **인과 흐름**: 마라톤→테르모필레→살라미스처럼 글로브가 사건을 따라감.

### 작업 전 체크리스트
- [ ] `docs/ideal/` 전체 읽었는가?
- [ ] 이 변경이 "글로브 = 인터페이스" 원칙을 따르는가?
- [ ] 사이드바에 쑤셔넣는 게 아니라 글로브 중심으로 설계했는가?
- [ ] 서사(narrative)가 메타데이터보다 먼저 보이는가?
- [ ] 2-탭 규칙을 위반하지 않는가?

---

## Version System

| 버전 | 설명 | 상태 | 경로 |
|-----|------|------|------|
| **V0** | 레거시 구조 (기존) | 운영 중 | `backend/app/models/`, `backend/app/api/v1/` |
| **V1** | Historical Chain 기반 신규 구조 | 개발 중 | `backend/app/models/v1/`, `backend/app/api/v1_new/` |

### V1 핵심 개념: Historical Chain (역사의 고리)

4가지 큐레이션 유형:
- **Person Story**: 인물의 생애와 주요 사건
- **Place Story**: 장소의 역사적 변천
- **Era Story**: 시대의 인물, 장소, 사건 종합
- **Causal Chain**: 인과관계로 연결된 사건 흐름

### V1 개발 원칙

1. **V0 영향 없음**: 기존 서버/API 유지, 별도 경로에서 개발
2. **체크포인트 작업**: `docs/planning/V1_WORKPLAN.md` 참조
3. **작업 로그**: `docs/logs/V1_WORKLOG.md`에 진행상황 기록
4. **완성 후 전환**: V1이 V0 기능 100% 커버 시 전환

---

## AI Models

### 사용 모델

| 모델 | 용도 | 비용 |
|-----|------|------|
| `llama3.1:8b-instruct-q4_0` | 엔티티 추출 (기본, Ollama) | 무료 (로컬) |
| `gpt-5-mini` | 엔티티 추출 (폴백) | ~$0.25/1M tokens |
| `gpt-5.1-chat-latest` | 복잡한 체인 생성 | ~$1.25/1M tokens |
| `text-embedding-3-small` | 벡터 검색, 엔티티 매칭 | ~$0.02/1M tokens |

### 비용 예산

- **초기 구축**: ~$47 (일회성)
- **월간 운영**: ~$7/월
- 상세: `docs/planning/COST_ESTIMATION.md`

---

## Data Pipeline (Book Extractor)

### 핵심 도구: `tools/book_extractor/`

```
http://localhost:8200  # Book Extractor 대시보드
```

### 파이프라인 흐름

```
┌─────────────────────────────────────────────────────────────┐
│  1. ZIM 파일 (Gutenberg)                                    │
│     └─ data/kiwix/gutenberg_en_all.zim                      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Hierarchical Chunking                                   │
│     └─ BOOK/CHAPTER/SECTION 구조 자동 감지                  │
│     └─ 2500자 청크 + 200자 오버랩                           │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  3. LLM 엔티티 추출 (NER 아님!)                             │
│     └─ Ollama (llama3.1) 또는 OpenAI (gpt-5-mini)          │
│     └─ 프롬프트: "Extract named entities from this text..." │
│     └─ 출력: {persons: [], locations: [], events: []}       │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  4. EntityMatcher (DB 매칭)                                 │
│     └─ tools/book_extractor/entity_matcher.py               │
│     └─ 기존 DB 엔티티와 매칭                                │
│     └─ Wikidata QID로 중복 병합                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Post-Processing                                         │
│     └─ context 추출 (청크별 엔티티 위치)                    │
│     └─ text_mentions 생성 (출처 추적)                       │
│     └─ 관계 분석 (TODO: event_relationships 업데이트)       │
└─────────────────────────────────────────────────────────────┘
```

### Book Extractor 실행

```bash
cd tools/book_extractor
python server.py
# Open http://localhost:8200
```

### 관련 파일

| 파일 | 설명 |
|------|------|
| `tools/book_extractor/server.py` | FastAPI 서버 (메인) |
| `tools/book_extractor/entity_matcher.py` | DB 엔티티 매칭 |
| `tools/book_extractor/index.html` | 대시보드 UI |
| `poc/data/book_samples/extraction_results/` | 추출 결과 저장 |

---

## Common Commands

### Frontend (from `frontend/`)
```bash
npm run dev -- --port 3000    # Dev server (MUST use port 3000)
npm run build                  # Production build
npm run lint                   # ESLint checks
```

### Backend (from `backend/`)
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8100    # Dev server (MUST use port 8100)
```

### Database (Dual PostgreSQL Setup)

두 개의 PostgreSQL data directory를 전환하여 사용:

| DB | 경로 | 크기 | 용도 |
|----|------|------|------|
| **Compact** | `C:\PostgreSQL\data` | ~150 MB | 개발/서빙 (light 데이터만, SSD) |
| **Archive** | `E:\PostgreSQL\data` | 44 GB | 전체 데이터 (HDD, 느림) |

같은 포트(5432), 같은 DATABASE_URL → **코드 변경 없음**.

```powershell
# DB 전환 (PowerShell)
.\tools\switch-db.ps1 compact    # C: SSD compact DB (기본)
.\tools\switch-db.ps1 archive    # E: HDD 전체 DB
.\tools\switch-db.ps1 status     # 현재 상태 확인

# 수동 시작/중지
& "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" start -D "C:\PostgreSQL\data" -l "C:\PostgreSQL\data\pg.log"
& "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" status -D "C:\PostgreSQL\data"
& "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" stop -D "C:\PostgreSQL\data"

# psql 접속
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U chaldeas -d chaldeas -h localhost -p 5432

# Alembic 마이그레이션
cd backend
python -m alembic upgrade head
python -m alembic current  # 현재 버전 확인
```

**Compact DB 재구축** (archive에서 light 데이터 추출 후 임포트):
```powershell
.\tools\switch-db.ps1 archive           # E: DB 시작
cd backend
python scripts/export_compact.py         # CSV 추출 → data/compact_export/
.\tools\switch-db.ps1 compact           # C: DB 시작
python -m alembic upgrade head           # 스키마 생성
python scripts/import_compact.py         # CSV 임포트
```

### Book Extractor (from `tools/book_extractor/`)
```bash
python server.py                        # 대시보드 시작 (localhost:8200)
```

### Data Scripts (from `poc/scripts/`)
```bash
python import_entities_to_db.py         # 추출 결과 DB 임포트
python link_persons_persons_via_source.py  # 관계 생성
python update_person_relationship_strength.py  # 관계 강도 계산
```

## Fixed Ports (Hardcoded)
- Frontend: 3000 (dev)
- Backend API: 8100
- **PostgreSQL: 5432** (Compact: `C:\PostgreSQL\data`, Archive: `E:\PostgreSQL\data`)
- API Docs: http://localhost:8100/docs

> **주의**: DATABASE_URL은 항상 `localhost:5432` 사용. `.\tools\switch-db.ps1`로 compact/archive 전환.

## Data Paths
```
C:\PostgreSQL\data\     # Compact DB (SSD, ~150MB, light 데이터만)
E:\PostgreSQL\data\     # Archive DB (HDD, 44GB, 전체 데이터)
E:\wikidata\            # Wikidata 덤프 (1.6TB, 압축 해제됨)
  └─ latest-all.json    # 전체 Wikidata JSON 덤프
```

---

## Deployment (GCP Cloud Run)

### 중요: 리전 설정

| 서비스 | 리전 | 용도 | 도메인 |
|--------|------|------|--------|
| chaldeas-backend | asia-northeast3 | API 서버 | - |
| chaldeas-frontend | **us-central1** | 프론트엔드 | www.chaldeas.site |

> **주의**: Frontend는 반드시 **us-central1**에 배포해야 함. asia-northeast3는 커스텀 도메인 매핑을 지원하지 않음!

### 배포 명령어

```powershell
# 전체 배포 (Cloud Build)
gcloud builds submit --config=cloudbuild.yaml --project=chaldeas-archive

# DB 동기화 (로컬 → 클라우드)
.\scripts\sync-db.ps1 up
```

### Production URLs

- **Frontend**: https://www.chaldeas.site
- **Backend API**: https://chaldeas-backend-951004107180.asia-northeast3.run.app
- **GCP Project**: `chaldeas-archive`

상세 가이드: `docs/guides/DEPLOYMENT.md`

---

## Architecture: 7-Layer World-Centric Model

```
Layer 7: EXPLAIN (LAPLACE)     - Interpretation, causation tracking, source attribution
Layer 6: PATCH / APPLY         - Sole path for state modification
Layer 5: EFFECT RUNTIME        - Pure functions without side effects
Layer 4: ACTION                - Compute action availability
Layer 3: PROJECTION (SHEBA)    - Read-only view generation, query observation
Layer 2: SNAPSHOT              - Immutable state snapshot
Layer 1: SCHEMA                - World structure definition (CHALDEAS)
```

### Named Subsystems (FGO-Inspired)

| System | Role | Location |
|--------|------|----------|
| **CHALDEAS** | World state, immutable snapshots | `backend/app/core/chaldeas/` |
| **SHEBA** | Query observation, intent detection, vector search | `backend/app/core/sheba/` |
| **LOGOS** | LLM-based response proposer (GPT-5-nano) | `backend/app/core/logos/` |
| **PAPERMOON** | Proposal verification, fact-checking | `backend/app/core/papermoon/` |
| **LAPLACE** | Explanation, source attribution | `backend/app/core/laplace/` |
| **TRISMEGISTUS** | System orchestrator | `backend/app/core/trismegistus/` |

### Data Flow
```
User Query → CHALDEAS (state) → SHEBA (observe) → LOGOS (propose) → PAPERMOON (verify) → LAPLACE (explain) → Response
```

---

## Tech Stack

### Frontend
- React 18 + TypeScript 5.3 + Vite 5.0
- react-globe.gl (Three.js-based 3D globe)
- Zustand (state management)
- Tailwind CSS 3.4

### Backend
- Python 3.12 + FastAPI 0.109
- SQLAlchemy 2.0 + Alembic (migrations)
- pgvector (PostgreSQL vector search)
- OpenAI (LLM integration)

### Database
- PostgreSQL 18 with pgvector extension (E:\PostgreSQL\data)
- BCE dates stored as negative integers (-490 = 490 BCE)

---

## Key API Endpoints

### V0 (현재 운영)
```
GET  /api/v1/events                    # List events (details nested)
GET  /api/v1/events/{id}               # Event detail (with details, persons, sources)
GET  /api/v1/events/{id}/locations     # Event locations (aggregate: recursive child locations)
GET  /api/v1/persons                   # List historical figures
GET  /api/v1/persons/{id}              # Person detail (with details, names)
GET  /api/v1/persons/{id}/flow         # Person flow (chronological event chain)
GET  /api/v1/persons/{id}/relations    # Related persons with strength
GET  /api/v1/persons/{id}/properties   # Wikidata properties
GET  /api/v1/persons/{id}/sources      # Books mentioning person
GET  /api/v1/locations                 # List places
GET  /api/v1/search?q=...&type=all     # Unified search
GET  /api/v1/feed                      # Unified feed (events + persons, JOINs event_details)
GET  /api/v1/featured                  # Featured content
POST /api/v1/chat/agent                # Agent-based intelligent query
```

### V1 (개발 중)
```
POST /api/v1/curation/chain            # 역사의 고리 생성/조회
GET  /api/v1/curation/chain/{id}       # 체인 상세 조회
GET  /api/v1/periods                   # 시대 목록
```

---

## Frontend State Stores (Zustand)

- `globeStore`: Selected event, viewport, markers
- `timelineStore`: Current year, playback state, animation speed

## Environment Variables

Required in `.env`:
```
POSTGRES_USER=chaldeas
POSTGRES_PASSWORD=chaldeas_dev
POSTGRES_DB=chaldeas
OPENAI_API_KEY=sk-...
VITE_API_URL=http://localhost:8100

# Book Extractor (tools/book_extractor/)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b-instruct-q4_0

# Sentry (비활성화 상태 - true로 변경 시 활성화)
SENTRY_ENABLED=false
VITE_SENTRY_ENABLED=false
```

---

## Important Patterns

1. **Immutability**: All world state changes must go through Layer 6 (PATCH/APPLY)
2. **Source Attribution**: Every fact must trace back to a source
3. **BCE Handling**: Use negative years for BCE dates in all calculations
4. **Agent Responses**: Return structured data with confidence scores and follow-up suggestions
5. **Multilingual**: Support `name_ko` fields for Korean translations
6. **Braudel's Temporal Scale**: evenementielle (단기) / conjuncture (중기) / longue_duree (장기)

---

## Documentation

### 구현 완료 (Implemented)
- `docs/reference/ARCHITECTURE.md` - Full 7-layer design
- `docs/reference/API.md` - Complete API reference (Person flow, relations, sources 포함)
- `docs/reference/DATABASE.md` - Schema and relationships (Person system overhaul 반영)
- `docs/guides/SETUP.md` - Development environment setup
- `docs/DEPLOYMENT.md` - GCP Cloud Run deployment

### V1 계획 (Planning)
- `docs/planning/METHODOLOGY.md` - 역사학 방법론 (CIDOC-CRM, Annales 학파 등)
- `docs/planning/HISTORICAL_CHAIN_CONCEPT.md` - 역사의 고리 컨셉 설계
- `docs/planning/REDESIGN_PLAN.md` - V1 재설계 상세 계획
- `docs/planning/COST_ESTIMATION.md` - AI 비용 산정
- `docs/planning/MODELS.md` - 사용 AI 모델 목록
- `docs/planning/FINAL_SCHEMA.md` - 최종 스키마 (persons 슬림화 반영)

### 작업 로그
- `docs/logs/sessions/` - 세션별 작업 로그 (타임스탬프 파일)

---

## Development Workflow

### 필수 로깅 규칙 (절대 위반 금지!)

**모든 작업에 대해 `docs/logs/sessions/`에 타임스탬프 파일 생성:**

1. **작업 시작 시 파일 생성**: `YYYYMMDD_HHMMSS_작업명.md`
2. **작업 중 계속 업데이트**: 뭐 했는지, 어떤 파일 변경했는지
3. **작업 후 결과 기록**: 성공/실패, 목적 달성 여부
4. **반성점과 다음 작업**: 뭘 잘못했고, 다음에 뭘 해야 하는지

```markdown
# 세션 로그: YYYY-MM-DD HH:MM

## 세션 정보
- **플랜 체크포인트**: CP-X.X
- **목적**: 왜 이 작업을 하는가

## 한 작업
- 변경한 파일들
- 생성한 데이터
- 실행한 명령어

## 결과
- 성공/실패 여부
- 목적 달성 여부

## 반성
- 뭘 잘못했는지
- 어떻게 개선할지

## 다음 작업
- 이어서 할 것
```

### 플랜 준수 규칙 (절대 위반 금지!)

1. **플랜 문서 먼저 확인**: 작업 전 반드시 플랜 파일 읽기
2. **플랜에 없는 작업 금지**: 플랜에 명시된 작업만 수행
3. **플랜 순서 준수**: CP-1.1 → CP-1.2 → CP-1.3 순서대로
4. **V0 테이블 건드리지 않기**: V2 테이블에만 작업
5. **지정된 모델만 사용**: llama3.1(T1), gpt-5-mini(T2), gpt-5.1-chat(T3)
6. **로컬 데이터 우선**: API 호출 전 로컬 파일 먼저 확인

### 작업 체크리스트 규칙 (필수!)

**Claude Code는 반드시 작업 시작 전 체크리스트를 작성해야 함:**

1. **TodoWrite 도구 사용**: 모든 비단순 작업에서 TodoWrite로 체크리스트 생성
2. **작업 시작 전 계획**: 무엇을 할지 먼저 목록화
3. **진행 상태 업데이트**: 작업 중 `in_progress` → 완료 시 `completed`
4. **작은 단위로 분할**: 큰 작업은 작은 체크포인트로 나누기

```
예시:
[ ] Globe API 생성
[ ] 라우터 등록
[ ] API 테스트
[ ] 프론트엔드 연동
```

### V2 작업 시

1. **플랜 확인**: `~/.claude/plans/` 또는 지정된 플랜 파일에서 다음 CP 확인
2. **로그 작성**: `docs/logs/V2_WORKLOG.md`에 작업 시작 기록
3. **작업 수행**: 플랜에 명시된 파일 경로, 테이블, 모델만 사용
4. **결과 기록**: 작업 결과와 검증 내용 로그에 기록
5. **커밋**: CP 단위로 커밋 (예: `feat(v2): CP-1.2 로깅 시스템 구축`)

### 커밋 메시지 형식

```
feat(v1): CP-X.X 작업 내용
fix(v0): 버그 수정 내용
docs: 문서 업데이트
```

---

## Platform Notes (Windows)

### UTF-8 인코딩 필수

Windows 환경에서 파일 읽기/쓰기 시 반드시 UTF-8 인코딩 명시:

```python
# Python 파일 처리
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# .env 파일은 BOM 마커 주의 (UTF-8-BOM → UTF-8로 저장)
# stdout 설정 (Windows 콘솔)
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
```

### 경로 처리

```python
from pathlib import Path
# 항상 Path 객체 사용 권장
file_path = Path("C:/Projects/Chaldeas/data/file.json")
```

---

## Code Quality Workflow

### TypeScript 에러 수정 순서

TypeScript 에러 수정 시 우선순위:
1. **Type 에러** (타입 불일치, 누락)
2. **Unused 변수/import**
3. **Style 이슈**

수정 후 반드시 검증:
```bash
cd frontend && npx tsc --noEmit
```

### 리팩토링 워크플로우

다중 파일 리팩토링 시:
1. 영향 받는 파일 목록 먼저 작성
2. 파일 그룹별로 순차 수정
3. 각 그룹 완료 후 커밋
4. 전체 완료 후 통합 테스트

```bash
# 리팩토링 검증 스크립트
cd backend && python -m pytest tests/ -v
cd frontend && npm run lint && npx tsc --noEmit
```

### 커밋 체크포인트 전략

대규모 작업 시 12세션마다 1커밋이 아닌, 논리적 단위마다 커밋:
- 파일 그룹 수정 완료 시
- 기능 단위 완료 시
- 테스트 통과 확인 시
