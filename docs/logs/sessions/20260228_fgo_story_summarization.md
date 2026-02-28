# 20260228 FGO Story Summarization Pipeline

## 목적
FGO 메인 스토리(36) + 이벤트(118) 전체에 대한 AI 기반 챕터 단위 요약 생성.

## 진행 과정

### Phase 1: 설계 & 비용 추정
- 3개 모델 비교 테스트 (gpt-5-mini, gpt-5.1-chat, gpt-5.2-chat) on Fuyuki 3 quests
- gpt-5-mini: $0.0098 → reasoning 토큰이 73% 차지, 비효율
- gpt-5.1-chat: $0.0200 → 가성비 최고
- gpt-5.2-chat: $0.0282 → 품질 최고 but 요약에는 overkill
- **결정**: 요약/번역 = gpt-5.1-chat, 큐레이션 = gpt-5.2-chat

### Phase 2: 요약 전략
- **챕터 단위 요약** (퀘스트별 X)
- 짧은 챕터 (<40K est tokens) → One-shot
- 긴 챕터 → AI가 퀘스트 이름+대사수+스피커 분석 → 서사 파트 분할 → 파트별 요약 → 종합 synthesis
- 스팟 기반 분할 거부 (비선형 방문 패턴 1→2→1)
- 자연스러운 서사 전환점 자동 탐지 (스피커 변화, 챕터명 패턴 등)

### Phase 3: 스크립트 개발
- `backend/scripts/summarize_fgo_stories.py` 생성
- 체크포인트 기반 재시작 (JSONL)
- `log()` 함수로 백그라운드 실행 시 stdout 버퍼링 해결
- `MAX_DIALOGUE_CHARS = 120,000` 전체 대사 truncation
- `MAX_DIALOGUE_CHARS_PART = 80,000` 파트별 truncation (후에 추가)

### Phase 4: 실행
1. 메인 스토리 35/36 완료 (~$5, ~30분)
   - lb7 Part 1 context overflow → truncation 추가로 해결
   - america 60K threshold 문제 → 40K로 하향
2. 이벤트 118개 완료 (~$13.23, ~91분)
   - event_9113: AI split 역순 범위 (30→14) → 빈 대사 → 에러
   - event_9119: 파트 하나가 context overflow → 에러
   - 두 건 모두 스크립트 수정 후 재처리 성공 ($0.46)

## 변경 파일
- `backend/scripts/summarize_fgo_stories.py` — 새 스크립트 (메인)
- `docs/reference/AI_MODELS.md` — 모델 사용 가이드

## 버그 수정 (이벤트 처리 후)
1. AI split 역순 범위 검증 (start > end → swap)
2. 파트별 대사 길이 제한 추가 (MAX_DIALOGUE_CHARS_PART = 80K)
3. synthesis에서 error 필드 fallback 처리

## 출력
```
E:\chaldeas_data\processed\fgo\summaries\
  by_chapter/
    fuyuki.json, orleans.json, ..., lb7.json     — 메인 35개
    event_8313.json, ..., event_9195.json         — 이벤트 118개
    lb7/part_1.json, part_2.json, ...             — 긴 스토리 파트별 상세
  checkpoint.jsonl                                — 처리 추적 (153 chapters, 154 parts)
```

## 비용
| 단계 | 비용 |
|------|------|
| 메인 스토리 | ~$5.00 |
| 이벤트 | ~$13.23 |
| 에러 재처리 | ~$0.46 |
| **합계** | **~$18.69** |

## 다음 작업
- [ ] 캐릭터별 대사 추출 (extract_fgo_dialogues.py, 로컬 처리, $0)
- [ ] 캐릭터별 대사 큐레이션 (gpt-5.2-chat 사용, 별도 비용)
- [ ] 요약 번역 EN→KO/JA (gpt-5.1-chat)
- [ ] DB 스키마 + API 엔드포인트 (Phase 3)
