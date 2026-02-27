# Core Subsystems Audit: TRISMEGISTUS / LAPLACE / SHEBA / LOGOS / PAPERMOON

## 세션 정보
- **날짜**: 2026-02-26
- **목적**: backend/app/core/ 하위 6개 서브시스템의 현황 파악 및 정리 보고서

---

## 1. 전체 구조 요약

```
backend/app/core/
├── __init__.py                     # 문서화 주석만 있음
├── singularities.py                # FGO 시대 데이터 (미사용)
├── chain/          __init__.py     # 스텁 (빈 파일, 주석 처리된 import)
├── extraction/     __init__.py     # 스텁 (빈 파일)
├── sheba/
│   ├── observer.py                 # 쿼리 관찰기 (255줄)
│   └── history_agent.py            # 멀티스텝 에이전트 (515줄)
├── logos/
│   └── actor.py                    # LLM 응답 제안기 (193줄)
├── papermoon/
│   └── authority.py                # 제안 검증기 (111줄)
├── laplace/
│   └── explain.py                  # 출처 귀속/인과 추적 (196줄)
└── trismegistus/
    └── orchestrator.py             # 전체 파이프라인 조율 (106줄)
```

**총 코드량**: ~1,376줄 (핵심 로직만)

---

## 2. 서브시스템별 상세 분석

### 2.1 SHEBA (시바) — Layer 3: 관찰/검색

**역할**: "Near-Future Observation Lens" — 사용자 쿼리를 이해하고 DB에서 관련 정보를 찾아옴

#### observer.py (255줄) — LLM 없음, 순수 DB+정규식

| 기능 | 구현 | 설명 |
|------|------|------|
| `_extract_time()` | 정규식 | "490 BCE", "5th century" 등에서 연도 추출 |
| `_extract_location()` | DB lookup | 위치명을 locations 테이블에서 매칭 |
| `_find_related_events()` | SQL | 추출된 연도 ±50년 범위 이벤트 검색 |
| `_find_related_persons()` | SQL | 이름 기반 인물 검색 (노이즈 필터 포함) |
| `_generate_interpretation()` | 문자열 조합 | 사람이 읽을 수 있는 요약 생성 |

**특징**: API 키 없이 동작. "Mrs.", "Mr." 등 노이즈 필터링 내장.

#### history_agent.py (515줄) — LLM 사용 (gpt-4o-mini)

| 단계 | 메서드 | 설명 |
|------|--------|------|
| 1단계 | `analyze_query()` | 의도 분류 (8종) + 엔티티 추출 → JSON |
| 2단계 | `execute_search()` | RAG 검색 (벡터 유사도 + 필터) |
| 3단계 | `filter_relevant_results()` | LLM이 검색 결과를 다시 판단 (단순 유사도 X) |
| 4단계 | `generate_response()` | 구조화된 응답 생성 (6가지 포맷) |

**의도 유형 8가지**: comparison, timeline, causation, deep_dive, overview, map_query, person_info, connection

**응답 포맷 6가지**: narrative, comparison_table, timeline_list, flow_chart, map_markers, cards

**다국어**: en, ko, ja 지원

**평가**: 이 파일이 전체 core/ 중 가장 정교하고 실용적인 모듈. `/chat/agent` 엔드포인트의 핵심.

---

### 2.2 LOGOS (로고스) — Layer 5: 응답 제안

**역할**: "The Word" — SHEBA가 모은 관찰을 바탕으로 LLM 응답을 **제안**

#### actor.py (193줄)

| 기능 | 구현 | 설명 |
|------|------|------|
| `propose()` | 메인 | SHEBA Observation → Proposal 생성 |
| `_get_llm()` | 지연 로딩 | Anthropic(claude-3-haiku) 우선 → OpenAI(gpt-3.5-turbo) 폴백 |
| `_generate_llm_answer()` | LLM | 컨텍스트 기반 응답 생성 |
| `_generate_fallback_answer()` | DB만 | API 키 없을 때 DB 컨텍스트로 응답 |

**핵심 원칙**: "Intelligence proposes but never executes" — 제안만 하고 직접 실행하지 않음

**사용 모델**: `claude-3-haiku-20240307` 또는 `gpt-3.5-turbo` (오래된 모델명)

**신뢰도**: LLM 응답 = 0.8, 폴백 = 0.6

---

### 2.3 PAPERMOON (페이퍼문) — Layer 6: 검증

**역할**: "The Authority" — LOGOS의 제안을 실행 전에 검증

#### authority.py (111줄) — LLM 없음, 규칙 기반

| 검증 항목 | 로직 | 영향 |
|-----------|------|------|
| 컨텍스트 사용 여부 | DB 컨텍스트 미사용 시 | 신뢰도 -0.2 |
| 이벤트 언급 | 응답에 관련 이벤트명 포함 시 | 신뢰도 +0.1 |
| 인물 언급 | 응답에 관련 인물명 포함 시 | 신뢰도 +0.1 |
| 승인 기준 | 신뢰도 ≥ 0.4 AND 교정 < 3개 | 통과/거부 |

**미구현**: `log_decision()` — 검증 결과를 `proposal_logs` 테이블에 기록하는 기능

**평가**: 가장 약한 서브시스템. 단순 문자열 매칭 수준이며, 실제 팩트체킹을 하지 않음.

---

### 2.4 LAPLACE (라플라스) — Layer 7: 설명/출처

**역할**: "Historical Record Electronic Sea" — 출처 귀속 + 인과 추적 + 후속 질문 제안

#### explain.py (196줄) — LLM 없음, DB 순회

| 기능 | 구현 | 설명 |
|------|------|------|
| `_find_sources()` | SQL | 관련 이벤트/인물에서 출처 추출 |
| `_trace_causality()` | 시간순 정렬 | 이벤트를 날짜순으로 나열하여 인과 체인 구성 |
| `_generate_suggestions()` | 패턴 매칭 | 후속 질문 자동 생성 ("What happened before X?") |

**기본 출처** (DB에 출처 없을 때): Perseus Digital Library, Chinese Text Project

**미구현**: `explain_value()` — 특정 DB 필드의 "왜?" 설명 기능

---

### 2.5 TRISMEGISTUS (트리스메기스토스) — 오케스트레이터

**역할**: 전체 파이프라인 조율 (지휘자)

#### orchestrator.py (106줄)

```
process_query(query, db):
  1. observation = SHEBA.observe(query)        # 관찰
  2. proposal   = LOGOS.propose(query, obs)     # 제안
  3. verify     = PAPERMOON.verify(prop, obs)   # 검증
  4. if not approved → 저신뢰 응답 반환
  5. explain    = LAPLACE.explain(prop, obs)    # 설명
  6. return ChatResponse                        # 최종 응답
```

**별도 엔드포인트**: `observe_only()` — SHEBA만 실행 (LLM 호출 없음)

---

### 2.6 보조 모듈

#### singularities.py — FGO 시대 데이터 (미사용)

7개 특이점(Singularity) + 7개 이문대(Lostbelt) + 15개 특별 에피소드의 역사 시대 매핑.
예: Orleans(1431, 100년전쟁), Babylonia(-2655, 메소포타미아).

**문제**: 이 데이터를 참조하는 코드가 없음. `/showcases` API는 별도 JSON 파일 사용.

#### chain/, extraction/ — 빈 스텁

주석 처리된 import만 존재. `ChainGenerator`, `ChainPromoter`, `HybridNERPipeline` 등이 계획되었으나 미구현.

---

## 3. API 엔드포인트 매핑

`backend/app/api/v1/chat.py` (358줄)에서 4개 엔드포인트 제공:

| 엔드포인트 | 사용 서브시스템 | 상태 |
|-----------|---------------|------|
| `POST /chat` | TRISMEGISTUS (전체 파이프라인) | 동작하지만 거의 안 씀 |
| `POST /chat/observe` | SHEBA.observer만 | LLM 무료 |
| `POST /chat/rag` | RAGService (SHEBA+LOGOS+LAPLACE 통합) | 동작 |
| `POST /chat/agent` | SHEBA.HistoryAgent | **프로덕션 메인** |

**핵심**: `/chat/agent`가 사실상 유일한 프로덕션 엔드포인트. 나머지는 실험용.

---

## 4. 지원 서비스 (core/ 바깥)

| 서비스 | 파일 | 역할 |
|--------|------|------|
| `RAGService` | `services/rag_service.py` (277줄) | 벡터검색 + LLM 응답 (gpt-4o-mini) |
| `EmbeddingService` | `services/embeddings/embedding_service.py` (151줄) | text-embedding-3-small 벡터 생성 |
| `VectorStore` | `services/embeddings/vector_store.py` (314줄) | pgvector 저장/검색 |
| `HybridSearchService` | `services/hybrid_search.py` (385줄) | BM25 + 벡터 하이브리드 검색 |

`RAGService`의 시스템 프롬프트는 한국어 구어체 스타일로 작성됨 ("~했거든요", "ㅋㅋ" 등).

---

## 5. 설계 vs 현실 비교

### 7-Layer 아키텍처 이행 현황

| Layer | 설계 | 현실 | 이행도 |
|-------|------|------|--------|
| 1. SCHEMA (CHALDEAS) | 세계 구조 정의 | `backend/app/core/chaldeas/` 디렉토리 자체가 없음. SQLAlchemy 모델이 대신함 | 0% |
| 2. SNAPSHOT | 불변 상태 스냅샷 | 미구현. DB를 직접 쿼리함 | 0% |
| 3. PROJECTION (SHEBA) | 읽기 전용 뷰 생성 | **observer.py + history_agent.py** | 90% |
| 4. ACTION | 액션 가용성 계산 | 명시적 구현 없음 | 0% |
| 5. EFFECT RUNTIME (LOGOS) | 순수 함수, 부작용 없음 | **actor.py** — 제안만 생성 | 60% |
| 6. PATCH/APPLY (PAPERMOON) | 상태 변경의 유일한 경로 | **authority.py** — 검증만 하고 실제 상태 변경 안 함 | 50% |
| 7. EXPLAIN (LAPLACE) | 해석, 인과 추적, 출처 | **explain.py** — 기본적 출처 추적 | 60% |

### 실제 작동 모델

설계 문서의 "7-Layer" 대신, 현실은 **4단계 RAG 파이프라인**:

```
[사용자 질문]
    │
    ▼
┌──────────────────────┐
│ SHEBA: 쿼리 이해     │  ← 의도 분류 + 엔티티 추출 + 벡터 검색
│  (observer.py +      │     gpt-4o-mini로 분석
│   history_agent.py)  │
└──────────────────────┘
    │
    ▼
┌──────────────────────┐
│ LOGOS: 응답 생성      │  ← claude-3-haiku 또는 gpt-3.5-turbo
│  (actor.py)          │     컨텍스트 기반 제안
└──────────────────────┘
    │
    ▼
┌──────────────────────┐
│ PAPERMOON: 검증       │  ← 규칙 기반 (LLM 없음)
│  (authority.py)      │     신뢰도 조정만
└──────────────────────┘
    │
    ▼
┌──────────────────────┐
│ LAPLACE: 출처 첨부    │  ← DB 순회 (LLM 없음)
│  (explain.py)        │     인과 체인 + 후속 질문
└──────────────────────┘
    │
    ▼
[최종 응답 + 출처 + 후속 질문]
```

그런데 **프로덕션에서는** 이 4단계 파이프라인(`/chat`)보다 `HistoryAgent`(`/chat/agent`)를 직접 사용함. HistoryAgent는 SHEBA 안에서 검색+응답+검증을 한번에 처리하므로, 사실상 LOGOS/PAPERMOON/LAPLACE를 우회.

---

## 6. 사용 중인 LLM 모델 현황

| 위치 | 모델명 | 용도 | 비고 |
|------|--------|------|------|
| history_agent.py | `gpt-4o-mini` | 의도분석, 필터링, 응답 | 메인 |
| rag_service.py | `gpt-4o-mini` | 번역 | 보조 |
| rag_service.py | `gpt-5-nano` | RAG 채팅 | **오타 가능성** |
| actor.py | `claude-3-haiku-20240307` | LOGOS 제안 (Anthropic) | 구형 모델 |
| actor.py | `gpt-3.5-turbo` | LOGOS 제안 (OpenAI) | 구형 모델 |
| embedding_service.py | `text-embedding-3-small` | 벡터 임베딩 | 정상 |

**문제점**: LOGOS의 모델(`claude-3-haiku`, `gpt-3.5-turbo`)이 구형이고, `gpt-5-nano`는 오타일 수 있음.

---

## 7. 미구현 / 불완전 목록

| 항목 | 파일:줄 | 상태 |
|------|---------|------|
| CHALDEAS 서브시스템 (세계 상태) | `core/chaldeas/` | 디렉토리 자체 없음 |
| SNAPSHOT 레이어 | — | 미구현 |
| ACTION 레이어 | — | 미구현 |
| `log_decision()` | `authority.py:109` | 미구현 (감사 로그) |
| `explain_value()` | `explain.py:189` | 미구현 ("왜?" 설명) |
| `chain/` 모듈 | `core/chain/` | 스텁만 |
| `extraction/` 모듈 | `core/extraction/` | 스텁만 |
| `singularities.py` | `core/singularities.py` | 데이터는 있으나 미연동 |
| 테스트 | — | 0건 |

---

## 8. 진단 요약

### 잘 된 것
1. **SHEBA.HistoryAgent**는 정교하고 실용적. 8종 의도분류, 6종 응답포맷, 다국어 지원, LLM 기반 재필터링까지.
2. **아키텍처 설계** 자체는 깔끔 — 각 서브시스템이 하나의 책임만 가짐.
3. **우아한 폴백** — API 키 없으면 BM25 키워드 검색으로 자동 전환.

### 안 된 것
1. **설계와 구현의 괴리**: 7-Layer 중 Layer 1, 2, 4가 완전히 빠져있음. "World State is explicit and immutable" 원칙이 코드에 반영되지 않음.
2. **PAPERMOON이 유명무실**: 규칙 기반 문자열 매칭으로 팩트체킹을 하지 못함. 신뢰도 ±0.1~0.2 조정이 전부.
3. **오케스트레이터 우회**: 프로덕션에서 `/chat/agent`가 TRISMEGISTUS를 거치지 않고 HistoryAgent를 직접 호출. LOGOS→PAPERMOON→LAPLACE 파이프라인이 사실상 사용되지 않음.
4. **모델 버전 낙후**: LOGOS가 `claude-3-haiku`/`gpt-3.5-turbo`를 사용 — 2024년 초 모델.
5. **글로브 연동 부재**: 이 서브시스템들이 프론트엔드 글로브와 직접 연결되는 부분이 없음. "글로브 = 인터페이스" 원칙과 단절.

### 핵심 모순

> 프로젝트의 핵심 원칙 "Intelligence proposes but never executes"를 구현하기 위해 4단계 파이프라인을 설계했으나, 실제로는 HistoryAgent가 모든 것을 한번에 처리하면서 이 원칙이 무의미해짐.

---

## 9. 향후 판단 필요 사항

이 보고서는 **현황 파악**만을 목적으로 함. 다음 판단은 별도 논의 필요:

1. **유지할 것인가**: 현재 HistoryAgent 중심 구조를 공식화할 것인가
2. **되살릴 것인가**: 4단계 파이프라인(LOGOS→PAPERMOON→LAPLACE)을 제대로 구현할 것인가
3. **정리할 것인가**: 미사용 코드(singularities.py, chain/, extraction/)를 삭제할 것인가
4. **모델 업데이트**: LOGOS의 구형 모델을 현재 모델로 교체할 것인가

---

## 10. 프론트엔드 현황

### 10.1 활성 파일 (현재 마운트됨)

#### ChatPanel.tsx (332줄) — App.tsx에 마운트

```
App.tsx → FloatingButtons(채팅 아이콘) → ChatPanel 열림
```

- 제목: "SHEBA AI Chat Interface"
- `POST /api/v1/chat/agent` 호출 (React Query `useMutation`)
- API 키를 localStorage(`chaldeas_openai_api_key`)에 저장/관리
- 응답의 `navigation` 필드로 글로브 자동 이동 (좌표+연도)
- `useTimelineStore`로 타임라인 연도 변경
- `useGlobeStore`로 하이라이트 위치 설정
- API 키 없으면 BM25 폴백 검색

#### AgentResponseRenderer.tsx (225줄) — ChatPanel이 사용

6가지 구조화된 응답 렌더링:

| 포맷 | 렌더링 |
|------|--------|
| comparison_table | 좌우 비교 테이블 |
| timeline_list | 시간순 이벤트 플로우 (도트+라인) |
| flow_chart (causal) | 원인 → 결과 체인 |
| map_markers | 좌표가 있는 위치 핀 목록 |
| cards | 태그가 달린 정보 카드 |
| narrative | 일반 서술 텍스트 |

+ 신뢰도 바 (0~100%) + 출처 목록 (관련도 점수 포함)

#### chat.css (773줄) — 전체 스타일링

- `.chat-panel`: 우하단 고정 모달 (420px, max-height 600px)
- 다크 테마 + 시안 액센트 (`#00c8ff`)
- 로딩 애니메이션 (바운싱 닷)
- API 키 입력 패널 UI

#### shebaEpisodes.ts (426줄) — TourOverlay, FeedTab 등에서 사용

16개 큐레이트된 역사 에피소드 데이터:
- 테르모필레 전투 (4단계 투어)
- 알렉산더 동방 원정 (5단계)
- 메소포타미아의 여명 (4단계)
- 카이사르와 로마 멸망 (4단계)
- 잔 다르크 (4단계)
- 나머지 11개는 투어 없이 카드만

각 에피소드: 제목, 설명, 날짜 범위, 지역, 좌표, 관련 FGO 서번트, 중요도 점수

#### API 클라이언트 (client.ts 106~113줄)

```typescript
chatApi.query(query, context)            // POST /chat           (오케스트레이터)
chatApi.observe(query)                   // POST /chat/observe   (SHEBA만)
chatApi.agent(query, apiKey, language)   // POST /chat/agent     (프로덕션 메인)
```

#### 타입 정의 (types/index.ts 308~423줄)

`ResponseFormat`, `QueryIntent`, `AgentAnalysis`, `AgentStructuredData`, `AgentResponseData`, `AgentResponse` 등 완전한 타입 정의.

---

### 10.2 Deprecated 파일 (미사용)

#### TrismegistusHub.tsx (734줄) — `_deprecated/`에 이동됨

원래 5섹션 큐레이션 허브:
1. Guided Tours (SHEBA 에피소드)
2. Person Stories (인물 플로우 타임라인)
3. Domain Stories (과학, 철학, 군사 등)
4. Era Narratives (시대별 서사)
5. FGO Archive (특이점, 이문대, 서번트)

**폐기 이유**: ShowcaseModal (4탭: Era, FGO, Reading, Explore)로 기능 이전.
TrismegistusHub.css도 함께 미사용.

#### laplaceTimeline.ts (486줄) — 아마 미사용

6개 시대의 계층적 타임라인 데이터 (고대~현대).
TrismegistusHub에서만 참조 → 허브 폐기로 함께 사장.

---

### 10.3 프론트엔드 연동 현황

```
┌─────────────────────────────────────────────────────────┐
│  App.tsx                                                │
│                                                         │
│  FloatingButtons ─── [채팅 아이콘 클릭] ──→ ChatPanel   │
│                                              │          │
│                                    POST /chat/agent     │
│                                              │          │
│                                              ▼          │
│                                  AgentResponseRenderer  │
│                                     │          │        │
│                            navigation 데이터   │        │
│                                     │          │        │
│                         ┌───────────┘          │        │
│                         ▼                      ▼        │
│                   useGlobeStore         useTimelineStore │
│                    (좌표 이동)            (연도 변경)    │
│                         │                      │        │
│                         ▼                      ▼        │
│                    Globe.tsx ←──────────── Timeline      │
└─────────────────────────────────────────────────────────┘
```

**핵심**: ChatPanel → `/chat/agent` → HistoryAgent → 응답 → 글로브/타임라인 네비게이션.
TRISMEGISTUS 오케스트레이터(`/chat`)를 호출하는 프론트엔드 코드는 `chatApi.query()`로 존재하지만 **어디서도 사용하지 않음**.

---

### 10.4 "트리스메기스토스" 이름의 현재 위치

| 위치 | 용도 | 상태 |
|------|------|------|
| `backend/core/trismegistus/orchestrator.py` | `/chat` 엔드포인트 | 동작하지만 프론트에서 안 부름 |
| `frontend/_deprecated/TrismegistusHub.tsx` | 큐레이션 허브 UI | 폐기됨, ShowcaseModal로 대체 |
| `App.tsx:386 주석` | `{/* TRISMEGISTUS - FGO content */}` | ShowcaseModal의 주석 라벨로만 존재 |

→ "트리스메기스토스"라는 이름은 백엔드에서는 안 쓰이는 오케스트레이터, 프론트에서는 deprecated 컴포넌트. **사실상 사장된 브랜드**.

---

## 11. 전체 생사 판정표

### 백엔드

| 모듈 | 코드 존재 | 엔드포인트 | 프론트 호출 | 최종 판정 |
|------|----------|-----------|------------|----------|
| SHEBA observer | 255줄 | `/chat`, `/chat/observe` | chatApi.observe (미사용) | 살아있으나 직접 안 불림 |
| SHEBA HistoryAgent | 515줄 | `/chat/agent` | ChatPanel | **유일한 생존자** |
| LOGOS actor | 193줄 | `/chat` (via orchestrator) | chatApi.query (미사용) | 사실상 사망 |
| PAPERMOON authority | 111줄 | `/chat` (via orchestrator) | chatApi.query (미사용) | 사실상 사망 |
| LAPLACE explain | 196줄 | `/chat` (via orchestrator) | chatApi.query (미사용) | 사실상 사망 |
| TRISMEGISTUS orchestrator | 106줄 | `/chat` | chatApi.query (미사용) | 사실상 사망 |
| singularities.py | 완성 | — | — | 미연동, 방치 |
| chain/ | 스텁 | — | — | 미구현 |
| extraction/ | 스텁 | — | — | 미구현 |
| RAGService | 277줄 | `/chat/rag` | — | HistoryAgent가 내부적으로 사용 |
| HybridSearchService | 385줄 | `/chat/agent` (폴백) | ChatPanel (키 없을 때) | BM25 폴백으로 활성 |

### 프론트엔드

| 모듈 | 줄수 | 마운트 | 최종 판정 |
|------|------|--------|----------|
| ChatPanel.tsx | 332 | App.tsx | **활성** |
| AgentResponseRenderer.tsx | 225 | ChatPanel | **활성** |
| chat.css | 773 | ChatPanel | **활성** |
| shebaEpisodes.ts | 426 | TourOverlay, FeedTab | **활성** |
| TrismegistusHub.tsx | 734 | — | **폐기** |
| TrismegistusHub.css | ? | — | **폐기** |
| laplaceTimeline.ts | 486 | — | **아마 폐기** |

---

## 12. 최종 진단 (백엔드+프론트엔드 통합)

### 한줄 요약

> **1,376줄의 백엔드 아키텍처 중 515줄(HistoryAgent)만 살아있고, 나머지 861줄은 호출되지 않는 죽은 코드.**

### 현재 실제 동작하는 전체 흐름

```
[사용자] → ChatPanel → POST /chat/agent → HistoryAgent(SHEBA)
                                              ├─ analyze_query (gpt-4o-mini)
                                              ├─ execute_search (RAGService → pgvector)
                                              ├─ filter_relevant (gpt-4o-mini)
                                              └─ generate_response (gpt-4o-mini)
                                                    │
                                                    ▼
         AgentResponseRenderer ← 구조화된 응답 (6종 포맷)
              │            │
              ▼            ▼
         Globe 이동    Timeline 변경
```

### 설계했으나 쓰이지 않는 경로

```
chatApi.query() → POST /chat → Orchestrator
                                  ├─ SHEBA.observe()      ← observer.py
                                  ├─ LOGOS.propose()       ← actor.py
                                  ├─ PAPERMOON.verify()    ← authority.py
                                  └─ LAPLACE.explain()     ← explain.py
                                        │
                                        ▼
                                   (아무도 안 부름)
```

### 판단 필요 사항 (업데이트)

1. **죽은 코드 정리**: LOGOS/PAPERMOON/LAPLACE/TRISMEGISTUS 861줄 — 삭제? 유지?
2. **프론트 deprecated 정리**: TrismegistusHub(734줄) + laplaceTimeline(486줄) — 삭제?
3. **HistoryAgent 공식화**: 현재 구조를 "이게 우리 아키텍처다"로 인정?
4. **아키텍처 문서 수정**: CLAUDE.md의 7-Layer 설명이 현실과 불일치
5. **이름 정리**: "SHEBA", "LAPLACE" 등의 브랜드를 ChatPanel UI에 반영할 것인가

---

*작성: 2026-02-26 | 조사 범위: backend/app/core/ 전체 + frontend/src/ 전체 + 관련 API/서비스*

---

## 13. 정리 결과 (2026-02-26 실행)

위 감사 보고서를 바탕으로 정리 작업을 실행함. 상세: `20260226_core_cleanup.md`

### 실행된 조치

| 판단 사항 | 결정 | 결과 |
|-----------|------|------|
| 죽은 코드 정리 | `_deprecated/`로 이동 (보존) | logos, trismegistus, laplace, papermoon, chain, extraction, singularities.py |
| HistoryAgent 공식화 | LAPLACE/PAPERMOON 로직 통합 | enhance_sources(), adjust_confidence(), generate_followup_suggestions() 추가 |
| chat.py 정리 | 미사용 엔드포인트 삭제 | `/chat`, `/chat/observe`, `/chat/rag` 제거 → `/chat/agent`만 유지 |
| 프론트 deprecated | 변경 없음 | TrismegistusHub는 이미 `_deprecated/`에 있음 |

### 정리 후 구조

```
backend/app/core/
├── __init__.py                    # 문서 업데이트됨
├── sheba/
│   ├── history_agent.py           # 강화됨 (7단계 파이프라인)
│   └── observer.py                # 유지
└── _deprecated/                   # 비활성 코드 보존
    ├── README.md
    ├── logos/
    ├── trismegistus/
    ├── laplace/
    ├── papermoon/
    ├── chain/
    ├── extraction/
    └── singularities.py
```
