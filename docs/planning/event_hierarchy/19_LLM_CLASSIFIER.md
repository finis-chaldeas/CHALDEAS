# LLM 기반 이벤트 분류기

**작성일**: 2026-01-28
**목적**: Wikidata로 분류 불가능한 이벤트를 LLM으로 계층 구조에 배치

---

## 1. 개요

### 언제 LLM을 사용하는가?

```
┌─────────────────────────────────────────────────────────────┐
│                     분류 우선순위                            │
├─────────────────────────────────────────────────────────────┤
│  1순위: Wikidata P361 (신뢰도 0.9)                          │
│         ↓ 없으면                                            │
│  2순위: 기존 Category 기반 추론 (신뢰도 0.5)                 │
│         ↓ 불충분하면                                        │
│  3순위: LLM 분류 (신뢰도 0.3-0.8)  ← 이 문서                │
└─────────────────────────────────────────────────────────────┘
```

### 대상 이벤트

| 유형 | 예상 개수 | 설명 |
|------|----------|------|
| QID 없음 | ~27,000 | Wikidata 매칭 안 됨 |
| QID 있지만 P361 없음 | ~12,000 | 상위 관계 미정의 |
| **총 LLM 대상** | **~39,000** | 전체의 83% |

---

## 2. 모델 선택

### 2.1 비용-성능 비교

| 모델 | Input $/1M | Output $/1M | 정확도 | 선택 |
|------|-----------|-------------|--------|------|
| **gpt-5.1-chat-latest** | **$2.50** | **$10.00** | **95%+** | **메인** |
| gpt-5-nano | $0.10 | $0.40 | 80% | 대량 처리용 |
| gpt-5-mini | $0.30 | $1.20 | 85% | 대안 |
| claude-3-haiku | $0.25 | $1.25 | 80% | 대안 |

**선택 이유**: 역사 분류는 정확도가 중요. 한 번 잘못 분류하면 수정 비용이 더 큼.

### 2.2 비용 추정

```
이벤트당 토큰:
- Input: ~300 tokens (프롬프트 + 이벤트 정보)
- Output: ~100 tokens (JSON 응답)

39,000 이벤트 × 400 tokens = 15.6M tokens

gpt-5.1-chat-latest:
- Input: 15.6M × 0.75 × $2.50/1M = $29.25
- Output: 15.6M × 0.25 × $10.00/1M = $39.00
- 총: ~$68

최적화 적용시:
- Wikidata로 50% 처리 → ~$34
- 캐싱 + 점진적 처리 → ~$25-30
```

### 2.3 배치 API 사용 (50% 할인)

```python
# OpenAI Batch API 사용시 비용 절반 → ~$34 → ~$17
# 단, 24시간 내 처리 보장 없음

from openai import OpenAI
client = OpenAI()

# 배치 파일 생성
batch_input = [
    {
        "custom_id": f"event-{event.id}",
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": "gpt-5.1-chat-latest",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
    }
    for event in events
]

# 배치 제출
batch = client.batches.create(
    input_file_id=uploaded_file.id,
    endpoint="/v1/chat/completions",
    completion_window="24h"
)
```

---

## 3. 프롬프트 설계

### 3.1 시스템 프롬프트

```python
SYSTEM_PROMPT = """당신은 역사학 전문가입니다. 주어진 역사적 이벤트를 분석하여
어떤 상위 역사적 맥락에 속하는지 분류합니다.

## 분류 기준

### 계층 레벨 (hierarchy_level)
- 0: 시대 (Era) - 고대, 중세, 근대, 현대
- 1: 대사건 (Mega) - 로마 제국, 대항해시대
- 2: 집합 사건 (Aggregate) - 백년전쟁, 르네상스
- 3: 주요 사건 (Major) - 아쟁쿠르 전투
- 4: 세부 사건 (Minor) - 특정 조약, 소규모 교전

### 집합 유형 (aggregate_type)
- war: 전쟁, 군사 분쟁
- revolution: 혁명, 정치적 격변
- movement: 사회/문화 운동
- dynasty: 왕조, 정권 시대
- expedition: 탐험, 원정
- crisis: 위기, 재난
- artistic_period: 예술 시대
- philosophical_school: 철학 사조
- scientific_era: 과학 시대
- religious: 종교 운동

## 응답 형식

반드시 JSON으로 응답하세요:
{
    "parent_event": "상위 이벤트 이름 (영어)",
    "parent_event_ko": "상위 이벤트 이름 (한국어)",
    "parent_event_qid": "Wikidata QID (알면)",
    "hierarchy_level": 3,
    "aggregate_type": "war",
    "confidence": "high|medium|low",
    "reasoning": "분류 이유 설명"
}

상위 이벤트가 없거나 불확실하면:
{
    "parent_event": null,
    "has_parent": false,  # true=미분류, false=상위 없음 확정
    "confidence": "low",
    "reasoning": "분류 불가 이유"
}

## 중요: 시간 정합성

상위 이벤트의 기간은 하위 이벤트를 **반드시 포함**해야 합니다.
- Battle of Hastings (1066) → Norman England (1066-1154) ✅
- Battle of Hastings (1066) → Roman Britain (43-410) ❌ 시간 범위 벗어남

지역별 시대 구분 참고:
- Britain: Roman Britain → Anglo-Saxon → Norman → Plantagenet...
- France: Gaul → Frankish → Capetian → Valois...
"""
```

### 3.2 이벤트 프롬프트

```python
def build_event_prompt(event: Event) -> str:
    return f"""다음 역사적 이벤트를 분류해주세요:

## 이벤트 정보
- 제목: {event.title}
- 한국어 제목: {event.title_ko or "없음"}
- 설명: {event.description[:500] if event.description else "없음"}
- 시작 연도: {format_year(event.date_start)}
- 종료 연도: {format_year(event.date_end) if event.date_end else "없음"}
- 장소: {event.primary_location.name if event.primary_location else "없음"}
- 카테고리: {event.category.name if event.category else "없음"}

이 이벤트가 속하는 상위 역사적 맥락은 무엇인가요?"""


def format_year(year: int) -> str:
    if year < 0:
        return f"BCE {abs(year)}"
    return f"CE {year}"
```

### 3.3 Few-Shot 예시

```python
FEW_SHOT_EXAMPLES = [
    # 예시 1: 명확한 전쟁 소속
    {
        "input": {
            "title": "Battle of Agincourt",
            "date_start": 1415,
            "location": "Agincourt, France",
            "category": "warfare"
        },
        "output": {
            "parent_event": "Hundred Years' War",
            "parent_event_ko": "백년전쟁",
            "parent_event_qid": "Q12544",
            "hierarchy_level": 3,
            "aggregate_type": "war",
            "confidence": "high",
            "reasoning": "1415년 영국-프랑스 간 전투로, 백년전쟁(1337-1453)의 핵심 전투"
        }
    },
    # 예시 2: 문화 운동
    {
        "input": {
            "title": "Completion of Sistine Chapel ceiling",
            "date_start": 1512,
            "location": "Vatican City",
            "category": "art"
        },
        "output": {
            "parent_event": "Italian Renaissance",
            "parent_event_ko": "이탈리아 르네상스",
            "parent_event_qid": "Q5598",
            "hierarchy_level": 3,
            "aggregate_type": "artistic_period",
            "confidence": "high",
            "reasoning": "미켈란젤로의 시스티나 성당 천장화는 르네상스 예술의 정점"
        }
    },
    # 예시 3: 불확실한 경우
    {
        "input": {
            "title": "Death of Socrates",
            "date_start": -399,
            "location": "Athens",
            "category": "philosophy"
        },
        "output": {
            "parent_event": "Classical Athens",
            "parent_event_ko": "고전기 아테네",
            "parent_event_qid": None,
            "hierarchy_level": 3,
            "aggregate_type": "philosophical_school",
            "confidence": "medium",
            "reasoning": "소크라테스의 죽음은 고전기 아테네 철학의 중요 사건이나, 명확한 상위 '이벤트'보다는 시대에 속함"
        }
    }
]
```

---

## 4. 구현

### 4.1 파일 구조

```
poc/scripts/hierarchy/
├── llm_classifier.py           # LLM 분류기 메인
├── prompts.py                  # 프롬프트 정의
├── batch_processor.py          # 배치 처리
└── confidence_filter.py        # 신뢰도 기반 필터링
```

### 4.2 분류기 구현

```python
# poc/scripts/hierarchy/llm_classifier.py

import json
import asyncio
from openai import AsyncOpenAI
from dataclasses import dataclass
from typing import Optional
from enum import Enum

from app.models.event import Event
from prompts import SYSTEM_PROMPT, build_event_prompt, FEW_SHOT_EXAMPLES


class Confidence(Enum):
    HIGH = "high"      # 0.8
    MEDIUM = "medium"  # 0.6
    LOW = "low"        # 0.3


@dataclass
class ClassificationResult:
    event_id: int
    parent_event: Optional[str]
    parent_event_ko: Optional[str]
    parent_event_qid: Optional[str]
    hierarchy_level: int
    aggregate_type: Optional[str]
    confidence: Confidence
    reasoning: str

    @property
    def confidence_score(self) -> float:
        return {
            Confidence.HIGH: 0.8,
            Confidence.MEDIUM: 0.6,
            Confidence.LOW: 0.3
        }[self.confidence]


class LLMEventClassifier:
    def __init__(self, model: str = "gpt-5.1-chat-latest"):
        self.client = AsyncOpenAI()
        self.model = model
        self.semaphore = asyncio.Semaphore(10)  # 동시 요청 제한

    async def classify(self, event: Event) -> ClassificationResult:
        """단일 이벤트 분류"""
        async with self.semaphore:
            messages = self._build_messages(event)

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.3,  # 일관성 위해 낮게
                max_tokens=300
            )

            return self._parse_response(event.id, response)

    async def classify_batch(self, events: list[Event],
                            progress_callback=None) -> list[ClassificationResult]:
        """배치 분류"""
        results = []
        for i, event in enumerate(events):
            result = await self.classify(event)
            results.append(result)

            if progress_callback and (i + 1) % 100 == 0:
                progress_callback(i + 1, len(events))

        return results

    def _build_messages(self, event: Event) -> list[dict]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Few-shot 예시 추가
        for example in FEW_SHOT_EXAMPLES:
            messages.append({
                "role": "user",
                "content": json.dumps(example["input"], ensure_ascii=False)
            })
            messages.append({
                "role": "assistant",
                "content": json.dumps(example["output"], ensure_ascii=False)
            })

        # 실제 이벤트
        messages.append({
            "role": "user",
            "content": build_event_prompt(event)
        })

        return messages

    def _parse_response(self, event_id: int, response) -> ClassificationResult:
        try:
            content = response.choices[0].message.content
            data = json.loads(content)

            return ClassificationResult(
                event_id=event_id,
                parent_event=data.get("parent_event"),
                parent_event_ko=data.get("parent_event_ko"),
                parent_event_qid=data.get("parent_event_qid"),
                hierarchy_level=data.get("hierarchy_level", 3),
                aggregate_type=data.get("aggregate_type"),
                confidence=Confidence(data.get("confidence", "low")),
                reasoning=data.get("reasoning", "")
            )
        except Exception as e:
            return ClassificationResult(
                event_id=event_id,
                parent_event=None,
                parent_event_ko=None,
                parent_event_qid=None,
                hierarchy_level=3,
                aggregate_type=None,
                confidence=Confidence.LOW,
                reasoning=f"Parse error: {str(e)}"
            )
```

### 4.3 신뢰도 기반 처리

```python
# poc/scripts/hierarchy/confidence_filter.py

from dataclasses import dataclass
from typing import List
from llm_classifier import ClassificationResult, Confidence


@dataclass
class FilteredResults:
    auto_apply: List[ClassificationResult]    # 자동 적용 (high)
    review_queue: List[ClassificationResult]  # 검토 필요 (medium)
    rejected: List[ClassificationResult]      # 미분류 유지 (low)


def filter_by_confidence(results: List[ClassificationResult],
                         auto_threshold: float = 0.8,
                         review_threshold: float = 0.5) -> FilteredResults:
    """신뢰도 기준 분류 결과 필터링"""

    auto_apply = []
    review_queue = []
    rejected = []

    for r in results:
        score = r.confidence_score

        if score >= auto_threshold and r.parent_event:
            auto_apply.append(r)
        elif score >= review_threshold and r.parent_event:
            review_queue.append(r)
        else:
            rejected.append(r)

    return FilteredResults(
        auto_apply=auto_apply,
        review_queue=review_queue,
        rejected=rejected
    )


def save_review_queue(results: List[ClassificationResult], filepath: str):
    """검토 큐를 CSV로 저장"""
    import csv

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'event_id', 'parent_event', 'parent_event_ko',
            'confidence', 'reasoning', 'approve'
        ])

        for r in results:
            writer.writerow([
                r.event_id,
                r.parent_event,
                r.parent_event_ko,
                r.confidence.value,
                r.reasoning,
                ''  # 수동 검토용 빈 칸
            ])
```

### 4.4 DB 업데이트

```python
# poc/scripts/hierarchy/apply_classifications.py

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.event import Event
from llm_classifier import ClassificationResult


# 알려진 Aggregate 이벤트 매핑
KNOWN_AGGREGATES = {
    "Hundred Years' War": {"qid": "Q12544", "ko": "백년전쟁"},
    "Crusades": {"qid": "Q12544", "ko": "십자군 전쟁"},
    "World War I": {"qid": "Q361", "ko": "제1차 세계대전"},
    "World War II": {"qid": "Q362", "ko": "제2차 세계대전"},
    "French Revolution": {"qid": "Q6534", "ko": "프랑스 혁명"},
    "Renaissance": {"qid": "Q4692", "ko": "르네상스"},
    # ... 주요 50개 정도 미리 정의
}


async def apply_classifications(results: list[ClassificationResult],
                                db: Session = None):
    """분류 결과를 DB에 적용"""
    if db is None:
        db = SessionLocal()

    try:
        for result in results:
            if not result.parent_event:
                continue

            event = db.query(Event).get(result.event_id)
            if not event:
                continue

            # 1. 부모 이벤트 찾기/생성
            parent_id = await get_or_create_aggregate(
                db,
                result.parent_event,
                result.parent_event_ko,
                result.parent_event_qid
            )

            # 2. 이벤트 업데이트
            if parent_id:
                event.parent_event_id = parent_id
                event.hierarchy_level = result.hierarchy_level
                event.aggregate_type = result.aggregate_type

        db.commit()

    finally:
        if db:
            db.close()


async def get_or_create_aggregate(db: Session, name: str,
                                  name_ko: str, qid: str) -> Optional[int]:
    """Aggregate 이벤트 조회 또는 생성"""

    # 1. 알려진 매핑 확인
    known = KNOWN_AGGREGATES.get(name)
    if known:
        qid = known.get("qid", qid)
        name_ko = known.get("ko", name_ko)

    # 2. QID로 찾기
    if qid:
        parent = db.query(Event).filter(Event.wikidata_id == qid).first()
        if parent:
            return parent.id

    # 3. 이름으로 찾기
    parent = db.query(Event).filter(Event.title == name).first()
    if parent:
        return parent.id

    # 4. 새로 생성
    parent = Event(
        title=name,
        title_ko=name_ko,
        slug=f"aggregate-{name.lower().replace(' ', '-')}",
        wikidata_id=qid,
        date_start=0,  # 나중에 자식들 기준으로 계산
        is_aggregate=True,
        hierarchy_level=2,
        importance=4
    )
    db.add(parent)
    db.flush()

    return parent.id
```

---

## 5. 실행 가이드

### 5.1 단계별 실행

```bash
# 1. 테스트 (100개, dry-run)
python poc/scripts/hierarchy/run_llm_classification.py \
    --limit 100 \
    --dry-run \
    --output test_results.json

# 2. 소규모 실행 (1,000개)
python poc/scripts/hierarchy/run_llm_classification.py \
    --limit 1000 \
    --output results_1k.json

# 3. 신뢰도 필터링
python poc/scripts/hierarchy/filter_results.py \
    --input results_1k.json \
    --auto-apply auto_apply.json \
    --review-queue review_queue.csv

# 4. 자동 적용
python poc/scripts/hierarchy/apply_classifications.py \
    --input auto_apply.json

# 5. 전체 실행 (배치 API)
python poc/scripts/hierarchy/run_llm_batch.py \
    --output batch_results.json
```

### 5.2 모니터링

```python
# 진행 상황 출력
def progress_callback(current, total):
    pct = current / total * 100
    print(f"진행: {current}/{total} ({pct:.1f}%)")

results = await classifier.classify_batch(events, progress_callback)
```

---

## 6. 품질 관리

### 6.1 샘플 검증

```python
# 100개 랜덤 샘플 수동 검증
import random

def sample_for_validation(results: list, n: int = 100):
    sample = random.sample(results, min(n, len(results)))

    print("=== 검증 샘플 ===")
    for r in sample:
        print(f"\n이벤트 ID: {r.event_id}")
        print(f"분류: {r.parent_event} ({r.parent_event_ko})")
        print(f"신뢰도: {r.confidence.value}")
        print(f"이유: {r.reasoning}")
        print("-" * 50)

        # 수동 검증 입력
        correct = input("정확함? (y/n/s): ")  # s = skip
        # ... 결과 저장
```

### 6.2 정확도 추적

```python
# 검증 결과 분석
def analyze_validation(validations: list[dict]) -> dict:
    total = len([v for v in validations if v["answer"] != "s"])
    correct = len([v for v in validations if v["answer"] == "y"])

    by_confidence = {}
    for conf in ["high", "medium", "low"]:
        subset = [v for v in validations
                  if v["confidence"] == conf and v["answer"] != "s"]
        if subset:
            by_confidence[conf] = {
                "total": len(subset),
                "correct": len([v for v in subset if v["answer"] == "y"]),
                "accuracy": len([v for v in subset if v["answer"] == "y"]) / len(subset)
            }

    return {
        "overall_accuracy": correct / total if total > 0 else 0,
        "by_confidence": by_confidence
    }
```

### 6.3 프롬프트 개선 루프

```
1. 100개 분류 실행
2. 수동 검증 (정확도 측정)
3. 오분류 패턴 분석
4. 프롬프트 수정 (예시 추가, 지침 명확화)
5. 반복
```

---

## 7. 예상 결과

### 7.1 분류 분포 (gpt-5.1-chat-latest 사용시)

| 신뢰도 | 예상 비율 | 개수 | 처리 |
|--------|----------|------|------|
| High | 45% | ~17,500 | 자동 적용 |
| Medium | 35% | ~13,600 | 검토 큐 |
| Low | 20% | ~7,800 | 미분류 |

*gpt-5.1의 높은 정확도로 High 비율 증가 예상*

### 7.2 정확도 목표

| 신뢰도 | 목표 정확도 |
|--------|------------|
| High | >95% |
| Medium | >80% |
| Low | - (미적용) |

---

## 8. 비용 최적화

### 8.1 캐싱

```python
# 동일 유형 이벤트 캐싱
CLASSIFICATION_CACHE = {}

async def classify_with_cache(event: Event) -> ClassificationResult:
    # 카테고리 + 연도대 조합으로 캐시 키
    cache_key = f"{event.category_id}:{event.date_start // 100}"

    if cache_key in CLASSIFICATION_CACHE:
        cached = CLASSIFICATION_CACHE[cache_key]
        if cached.confidence == Confidence.HIGH:
            return ClassificationResult(
                event_id=event.id,
                **cached.__dict__
            )

    result = await classifier.classify(event)

    if result.confidence == Confidence.HIGH:
        CLASSIFICATION_CACHE[cache_key] = result

    return result
```

### 8.2 점진적 처리

```python
# 중요도 높은 것부터 처리
events_by_importance = db.query(Event).filter(
    Event.parent_event_id.is_(None)
).order_by(Event.importance.desc()).all()

# Phase 1: importance >= 4 (최우선)
# Phase 2: importance == 3 (일반)
# Phase 3: importance <= 2 (필요시)
```

---

## 9. 시간 정합성 검증

LLM 분류 결과는 반드시 시간 정합성 검증 필요:

```python
# 허용 오차: ±50년
TEMPORAL_TOLERANCE = 50

def validate_temporal(event: Event, parent: Event) -> dict:
    """
    시간 정합성 검증
    - hard: ±50년 초과 → 완전 거부
    - soft: 범위 내지만 정확히 포함 아님 → 경고
    """
    event_start = event.date_start
    event_end = event.date_end or event_start
    parent_start = parent.date_start
    parent_end = parent.date_end

    # Hard limit: ±50년 초과면 완전 아웃
    if event_start < parent_start - TEMPORAL_TOLERANCE:
        return {"valid": False, "reason": f"시작일이 {abs(event_start - parent_start)}년 초과 벗어남"}

    if parent_end and event_end > parent_end + TEMPORAL_TOLERANCE:
        return {"valid": False, "reason": f"종료일이 {abs(event_end - parent_end)}년 초과 벗어남"}

    # Soft check: 정확히 범위 내인지
    warnings = []
    if event_start < parent_start:
        warnings.append(f"시작일 {parent_start - event_start}년 앞섬 (경계 이벤트)")
    if parent_end and event_end > parent_end:
        warnings.append(f"종료일 {event_end - parent_end}년 뒤짐 (경계 이벤트)")

    return {"valid": True, "warnings": warnings}


async def apply_with_validation(result: ClassificationResult, db: Session):
    """검증 후 적용"""
    event = db.query(Event).get(result.event_id)
    parent = find_parent_event(db, result.parent_event, result.parent_event_qid)

    if not parent:
        event.parent_status = "unknown"
        return

    temporal_check = validate_temporal(event, parent)

    if not temporal_check["valid"]:
        # ±50년 초과 → 완전 거부
        result.confidence = Confidence.LOW
        result.reasoning += f" [REJECTED: {temporal_check['reason']}]"
        save_to_review_queue(result)
        return

    if temporal_check.get("warnings"):
        # 경계 이벤트 → 적용하되 경고 기록
        result.reasoning += f" [WARNING: {', '.join(temporal_check['warnings'])}]"

    # 적용
    event.parent_event_id = parent.id
    event.parent_status = "confirmed"


# Location은 추천용 (hard constraint 아님)
def get_location_suggestion(event: Event, parent: Event) -> Optional[str]:
    """공간 정합성 체크 - 추천/참고용"""
    if not event.primary_location:
        return None  # 체크 불가

    if not parent.locations:
        return None  # 세계대전 같은 경우

    if is_location_within(event.primary_location, parent.locations):
        return None  # OK

    return f"장소 불일치: {event.primary_location.name} ∉ {[l.name for l in parent.locations]}"
```

---

## 10. 리스크 & 완화

| 리스크 | 확률 | 완화 |
|--------|------|------|
| 할루시네이션 (없는 상위 이벤트 생성) | 중 | KNOWN_AGGREGATES로 검증 |
| **시간 정합성 위반** | **중** | **자동 검증 후 검토 큐** |
| 일관성 없는 분류 | 중 | temperature=0.3, few-shot |
| 비용 초과 | 저 | 배치 API, 점진적 처리 |
| Rate limit | 저 | semaphore, 지수 백오프 |

---

## 부록: 프롬프트 버전 관리

```
prompts/
├── v1_basic.py          # 초기 버전
├── v2_few_shot.py       # Few-shot 추가
├── v3_structured.py     # 구조화된 출력
└── current.py           # 현재 사용 (symlink)
```

각 버전별 정확도 기록:
| 버전 | High 정확도 | Medium 정확도 | 날짜 |
|------|------------|--------------|------|
| v1 | 75% | 55% | 2026-01-28 |
| v2 | 85% | 65% | TBD |
| v3 | 90% | 75% | TBD |
