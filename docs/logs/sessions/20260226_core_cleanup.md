# Core Subsystem 정리 + HistoryAgent 강화

**날짜**: 2026-02-26
**목적**: 죽은 코드 정리 + LAPLACE/PAPERMOON의 유용한 로직을 HistoryAgent에 통합

## 변경 사항

### Phase 1: HistoryAgent 강화
**파일**: `backend/app/core/sheba/history_agent.py`

3개 메서드 추가:
- `enhance_sources()` — LAPLACE `_find_sources()` 로직. 소스 없으면 기본 참조 아카이브(Perseus, CText) 폴백.
- `adjust_confidence()` — PAPERMOON `verify()` 로직. 검색 결과 0건 → -0.3, 엔티티 언급 검증 → +0.1.
- `generate_followup_suggestions()` — LAPLACE `_generate_suggestions()` 로직. 엔티티 기반 맥락적 후속 질문.

`process()` 파이프라인: analyze → search → filter → generate → **enhance_sources → adjust_confidence → suggestions**

### Phase 2: chat.py 정리
**파일**: `backend/app/api/v1/chat.py`

삭제:
- `POST /chat` (Orchestrator 기반)
- `POST /chat/observe` (SHEBA observer만)
- `POST /chat/rag` (RAGService 직접)
- `Orchestrator` import, `get_db` import, `ChatRequest/ChatResponse` import
- `RAGFilters`, `RAGRequest`, `RAGResponseModel` 모델
- `get_rag_service()`, `get_history_agent()` 헬퍼

유지: `POST /chat/agent` + Agent 관련 Pydantic 모델

### Phase 3: 백엔드 코드 → `_deprecated/`
`git mv`로 이동 (히스토리 보존):
- `core/logos/` → `core/_deprecated/logos/`
- `core/trismegistus/` → `core/_deprecated/trismegistus/`
- `core/laplace/` → `core/_deprecated/laplace/`
- `core/papermoon/` → `core/_deprecated/papermoon/`
- `core/chain/` → `core/_deprecated/chain/`
- `core/extraction/` → `core/_deprecated/extraction/`
- `core/singularities.py` → `core/_deprecated/singularities.py`

`core/_deprecated/README.md` 생성 (왜 deprecated 됐는지 설명).

### Phase 4: 프론트엔드
변경 없음 — TrismegistusHub는 이미 `_deprecated/`에 있음.

### Phase 5: 문서화
- `core/__init__.py` 문서 업데이트
- 이 세션 로그 작성

## 검증
- `from app.core.sheba.history_agent import HistoryAgent` → OK
- `from app.api.v1.chat import router` → OK
- deprecated 모듈 참조가 `_deprecated/` 내부에만 존재함 확인

## 결과

| 항목 | Before | After |
|------|--------|-------|
| 백엔드 core/ 활성 파일 | 13+ | 4 (sheba/2 + __init__.py + _deprecated/) |
| chat 엔드포인트 | 4 | 1 (`/chat/agent`) |
| HistoryAgent 기능 | 검색+응답 | 검색+응답+출처귀속+신뢰도검증+후속질문 |
| 죽은 코드 | 활성 경로에 혼재 | `_deprecated/`로 격리 |

## 다음 작업
- 프론트 빌드 확인 (`npx tsc --noEmit`)
- 백엔드 서버 기동 테스트 (`uvicorn app.main:app`)
- `/chat/agent` 엔드포인트 BM25 폴백 동작 확인
