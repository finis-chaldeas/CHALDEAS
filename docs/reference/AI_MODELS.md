# AI Model Usage Guide

## Model Selection

| 용도 | 모델 | 이유 |
|------|------|------|
| **모든 큐레이션** (캐릭터 분석, FGO↔역사 연결, 내러티브 생성 등) | `gpt-5.2-chat-latest` | 최고 품질, 디테일 |
| **기타 잡것** (요약, 번역, 분류, 태깅 등) | `gpt-5.1-chat-latest` | 가성비 최고 |
| 엔티티 추출 (로컬) | `llama3.1:8b-instruct-q4_0` | Ollama, 무료 |

### 사용하지 않는 모델

| 모델 | 이유 |
|------|------|
| `gpt-5-mini` | Reasoning 모델 — 출력 토큰의 ~73%가 reasoning에 낭비됨. 배치 작업에 비효율적 |
| `gpt-5.2-pro` | $21/$168 per 1M — 배치에는 과도한 비용 |

---

## 가격표 (2026-02 기준)

| 모델 | Input ($/1M) | Cached Input | Output ($/1M) |
|------|-------------|-------------|--------------|
| gpt-5.2-chat-latest | $1.75 | $0.175 | $14.00 |
| gpt-5.1-chat-latest | $1.25 | $0.125 | $10.00 |
| gpt-5-mini | $0.25 | $0.025 | $2.00 |
| gpt-5-nano | $0.05 | $0.005 | $0.40 |

---

## 실측 벤치마크 (Fuyuki 3 퀘스트 요약)

| 모델 | Input | Output | 비용 | 퀘스트당 |
|------|-------|--------|------|---------|
| gpt-5-mini | 10,486 | 3,582 (reasoning 2,624) | $0.0098 | $0.0033 |
| gpt-5.1-chat | 10,486 | 694 | $0.0200 | $0.0067 |
| gpt-5.2-chat | 10,486 | 706 | $0.0282 | $0.0094 |

### 품질 비교 (프롤로그 요약)

**gpt-5-mini**: 정확하지만 장황. reasoning 토큰 낭비.
> "A newly recruited Master awakens at Chaldea and is introduced to staff and residents including Mash, the mascot Fou, technician Leff, Dr. Romani, and Director Olga Marie during an orientation for the upcoming Rayshift..."

**gpt-5.1-chat**: 간결하고 정확.
> "The protagonist awakens in Chaldea and meets Mash, Fou, and several staff members including Leff and Dr. Roman, learning they are a newly recruited Master candidate just before a major Rayshift experiment..."

**gpt-5.2-chat**: 가장 구체적.
> "The protagonist awakens at Chaldea after an inexperienced Rayshift simulation... turning Chaldeas red, revealing deliberate sabotage..."

---

## API 호출 주의사항

### 공통
- `max_completion_tokens` 필수 설정 (미설정 시 기본값이 너무 낮을 수 있음)
- `response_format={"type": "json_object"}` → JSON 출력 강제
- `.env` 위치: `C:\Projects\Chaldeas\.env` (프로젝트 루트)

### chat 모델 (5.1, 5.2)
```python
response = client.chat.completions.create(
    model='gpt-5.1-chat-latest',
    messages=[...],
    max_completion_tokens=2000,
    response_format={"type": "json_object"}
    # temperature 미지원! 기본값(1)만 가능
)
```

### reasoning 모델 (5-mini) — 비권장
```python
response = client.chat.completions.create(
    model='gpt-5-mini',
    messages=[...],
    max_completion_tokens=2000,  # reasoning 토큰 포함!
    response_format={"type": "json_object"}
    # temperature 미지원
)
# usage.completion_tokens_details.reasoning_tokens 으로 reasoning 비율 확인
```

---

## 비용 추산 (FGO 파이프라인)

| 작업 | 건수 | 모델 | 예상 비용 |
|------|------|------|----------|
| 퀘스트 요약 (메인+이벤트) | ~2,180 | gpt-5.1-chat | ~$14.57 |
| 챕터 종합 요약 | ~152 | gpt-5.1-chat | ~$1.00 |
| 번역 (x2 언어) | ~4,660 | gpt-5.1-chat | ~$5.00 |
| 캐릭터 큐레이션 | TBD | gpt-5.2-chat | TBD |
| **합계 (큐레이션 제외)** | — | — | **~$20** |

---

## 배치 처리 패턴

```python
# 기본 템플릿 (enrich_event_narratives.py 기반)
from concurrent.futures import ThreadPoolExecutor
import threading

checkpoint_lock = threading.Lock()

def save_checkpoint(entry):
    with checkpoint_lock:
        with open(CHECKPOINT_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def process_one(item):
    response = client.chat.completions.create(...)
    save_checkpoint(result)
    return result

with ThreadPoolExecutor(max_workers=10) as pool:
    futures = [pool.submit(process_one, item) for item in items]
```

핵심:
- JSONL 체크포인트 (resume 가능)
- `ThreadPoolExecutor` 병렬 처리
- `threading.Lock()` 으로 체크포인트 쓰기 보호
- 프로그레스 출력: `[150/680] quest_name [OK] | $0.12`
