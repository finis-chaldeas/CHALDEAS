# core/_deprecated/ — 비활성 서브시스템

이 폴더는 7-Layer World-Centric Architecture에서 설계되었으나
HistoryAgent(`/chat/agent`)로 통합되어 더 이상 활성 코드에서 사용하지 않는 모듈을 보관합니다.

## 왜 deprecated?

| 모듈 | 원래 역할 | deprecated 이유 |
|------|-----------|----------------|
| `logos/` | LLM 기반 응답 제안 | HistoryAgent가 직접 OpenAI 호출 |
| `trismegistus/` | SHEBA→LOGOS→PAPERMOON→LAPLACE 오케스트레이션 | HistoryAgent가 단일 파이프라인으로 대체 |
| `laplace/` | 출처 귀속, 인과관계 추적, 후속 질문 | 핵심 로직 → HistoryAgent.enhance_sources(), generate_followup_suggestions() |
| `papermoon/` | 제안 검증, 신뢰도 조정 | 핵심 로직 → HistoryAgent.adjust_confidence() |
| `chain/` | 체인 생성 스텁 | 비어있음 (코드 없음) |
| `extraction/` | NER 파이프라인 스텁 | 비어있음 (코드 없음) |
| `singularities.py` | FGO 시대 데이터 | JSON 파일(`showcases/`)이 대체 |

## 활성 코드

`core/sheba/` 만 프로덕션에서 사용됩니다:
- `history_agent.py` — 메인 AI (LAPLACE/PAPERMOON 로직 통합됨)
- `observer.py` — DB 기반 쿼리 관찰 (향후 활용 가능)

## 복원

필요시 이 폴더의 코드를 참고하여 활성 경로로 복원할 수 있습니다.
단, import 경로와 의존성(Observation, Proposal 등)을 업데이트해야 합니다.
