# CHALDEAS 프롬프트 엔지니어링 가이드

## 개요

신규 책 처리 시 모델별 최적화된 프롬프트 전략.

| 모델 | 용도 | 비용 | 컨텍스트 |
|------|------|------|----------|
| `llama3.1:8b-instruct-q4_0` | 기본 엔티티 추출 | 무료 (로컬) | 8K |
| `gpt-5-mini` | 표준 추출 + 폴백 | ~$0.25/1M | 128K |
| `gpt-5.1-chat-latest` | 복잡한 추론/체인 | ~$1.25/1M | 128K |

---

## 1. 티어별 작업 분배

```
┌─────────────────────────────────────────────────────────────┐
│  Tier 1: 로컬 모델 (llama3.1)                               │
│  ─────────────────────────────────────────────────────────  │
│  • 기본 NER (인물, 장소, 이벤트 이름 추출)                   │
│  • 단순 분류 (person/location/event)                        │
│  • 청크 단위 처리                                           │
│  • 실패 시 → Tier 2로 에스컬레이션                          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Tier 2: gpt-5-mini                                         │
│  ─────────────────────────────────────────────────────────  │
│  • Tier 1 실패 케이스 처리                                  │
│  • 속성 추출 (직업, 시대, 관계)                             │
│  • 시간 태그 추론                                           │
│  • 엔티티 매칭 disambiguation                               │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Tier 3: gpt-5.1-chat-latest                                │
│  ─────────────────────────────────────────────────────────  │
│  • Historical Chain 생성                                    │
│  • 인과관계 추론                                            │
│  • 복잡한 관계 네트워크 분석                                │
│  • 요약 및 내러티브 생성                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Tier 1: 로컬 모델 (llama3.1:8b)

### 특성

- 작은 컨텍스트 (8K)
- JSON 출력 불안정 → 파싱 로직 필요
- 단순하고 직접적인 지시 필요
- Few-shot 예시 효과적

### 프롬프트 템플릿: 엔티티 추출

```python
LLAMA_ENTITY_EXTRACTION = """Extract named entities from this historical text.

Rules:
- Only extract EXPLICITLY mentioned names
- Do NOT infer or guess
- Return JSON only, no explanation

Categories:
- persons: People names (full names when possible)
- locations: Places, cities, countries, regions
- events: Battles, treaties, wars, revolutions

Example input:
"Napoleon Bonaparte led the French army at the Battle of Austerlitz in 1805."

Example output:
{"persons": ["Napoleon Bonaparte"], "locations": ["Austerlitz"], "events": ["Battle of Austerlitz"]}

---
Text to analyze:
{text}

Output (JSON only):"""
```

### 프롬프트 템플릿: 시대 분류

```python
LLAMA_ERA_CLASSIFICATION = """Classify the time period of this text.

Options:
- ANCIENT: Before 500 CE
- MEDIEVAL: 500-1500 CE
- EARLY_MODERN: 1500-1800 CE
- MODERN: 1800-1945 CE
- CONTEMPORARY: After 1945
- UNKNOWN: Cannot determine

Text:
{text}

Answer (one word only):"""
```

### 출력 파싱 전략

```python
def parse_llama_output(raw_output: str) -> dict:
    """
    로컬 모델의 불안정한 JSON 출력 처리
    """
    # 1. JSON 블록 추출 시도
    json_match = re.search(r'\{[\s\S]*\}', raw_output)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # 2. 라인별 파싱 폴백
    result = {"persons": [], "locations": [], "events": []}
    for line in raw_output.split('\n'):
        if 'person' in line.lower():
            # 이름 추출 로직
            pass

    # 3. 실패 시 Tier 2로 에스컬레이션
    if not any(result.values()):
        raise EscalateToTier2(raw_output)

    return result
```

### 최적화 팁

1. **청크 크기**: 1500-2000자 (컨텍스트 여유 확보)
2. **온도**: 0.1 (일관성 우선)
3. **반복 방지**: `repeat_penalty: 1.1`
4. **JSON 모드**: Ollama의 `format: "json"` 옵션 활용

---

## 3. Tier 2: gpt-5-mini

### 특성

- 안정적인 JSON 출력
- 구조화된 출력 (Structured Outputs) 지원
- 중간 수준의 추론 능력
- 비용 효율적

### 프롬프트 템플릿: 속성 추출

```python
GPT_MINI_ATTRIBUTE_EXTRACTION = """You are a historical data extraction assistant.

Extract attributes for the entities mentioned in this text.
Only include information that is EXPLICITLY stated.

Text:
{text}

Entities to analyze:
{entities}

For each entity, extract:
- occupation: Job or role (e.g., "king", "philosopher", "general")
- birth_year: Year of birth (negative for BCE, e.g., -470 for 470 BCE)
- death_year: Year of death
- nationality: Country or region of origin
- era_tags: Time period tags (e.g., ["ancient", "greek", "classical"])
- relationships: Connections to other entities

Return as JSON:
{
  "entities": [
    {
      "name": "...",
      "type": "person|location|event",
      "occupation": ["..."],
      "birth_year": null,
      "death_year": null,
      "nationality": "...",
      "era_tags": ["..."],
      "relationships": [
        {"type": "father|mother|teacher|participant", "target": "..."}
      ]
    }
  ]
}"""
```

### 프롬프트 템플릿: 엔티티 Disambiguation

```python
GPT_MINI_DISAMBIGUATION = """Match the entity mention to the correct database entry.

Context: "{context}"
Entity mention: "{mention}"

Candidates from database:
{candidates}

Rules:
1. Consider the context carefully
2. If no candidate matches well, return "NEW_ENTITY"
3. If ambiguous, return "UNCERTAIN" with confidence < 0.7

Return JSON:
{
  "match": "candidate_id or NEW_ENTITY or UNCERTAIN",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}"""
```

### 프롬프트 템플릿: 시간 태그 추론

```python
GPT_MINI_TEMPORAL_TAGS = """Assign temporal tags to this entity based on the text.

Entity: {entity_name}
Text context: {context}

Available era tags:
- ancient_near_east, ancient_egypt, ancient_greece, ancient_rome
- medieval_europe, medieval_asia, medieval_islamic
- renaissance, reformation, enlightenment
- industrial_revolution, world_wars, cold_war
- contemporary

Rules:
1. Only assign tags supported by the text
2. Include century tags (e.g., "19th_century")
3. Include decade tags for modern era (e.g., "1920s")

Return JSON:
{
  "era_tags": ["..."],
  "century": "...",
  "decade": "..." or null,
  "confidence": 0.0-1.0
}"""
```

### Structured Output 스키마

```python
from pydantic import BaseModel
from typing import Optional

class EntityAttributes(BaseModel):
    name: str
    type: str  # person, location, event
    occupation: list[str] = []
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    era_tags: list[str] = []
    confidence: float = 0.0

class ExtractionResult(BaseModel):
    entities: list[EntityAttributes]
    source_reliability: float = 0.7  # extracted에서 온 데이터

# API 호출 시
response = client.chat.completions.create(
    model="gpt-5-mini",
    messages=[...],
    response_format={"type": "json_schema", "json_schema": EntityAttributes.model_json_schema()}
)
```

---

## 4. Tier 3: gpt-5.1-chat-latest

### 특성

- 최고 수준의 추론 능력
- 긴 컨텍스트 처리
- 복잡한 관계 추론
- 내러티브 생성

### 프롬프트 템플릿: Historical Chain 생성

```python
GPT_ADVANCED_CHAIN_GENERATION = """You are a historian creating a narrative chain.

Task: Create a {chain_type} for {subject}.

Chain types:
- person_story: Life events of a person in chronological order
- place_story: Historical events at a location over time
- era_story: Key events, figures, and places of an era
- causal_chain: Events connected by cause-and-effect

Available entities from our database:
{available_entities}

Rules:
1. Only use entities from the provided list
2. Each node must have a clear temporal position
3. Connections must be historically accurate
4. Include source_confidence for each claim

Return JSON:
{
  "chain_type": "...",
  "subject": "...",
  "nodes": [
    {
      "entity_id": "...",
      "entity_type": "person|event|location",
      "year": -470,
      "description": "...",
      "source_confidence": 0.0-1.0
    }
  ],
  "edges": [
    {
      "from_node": 0,
      "to_node": 1,
      "relationship": "caused|led_to|participated_in|born_at|died_at",
      "description": "..."
    }
  ],
  "narrative_summary": "2-3 sentence overview"
}"""
```

### 프롬프트 템플릿: 인과관계 추론

```python
GPT_ADVANCED_CAUSALITY = """Analyze the causal relationships between these historical events.

Events:
{events_with_context}

For each pair of events, determine:
1. Is there a causal relationship?
2. What type? (direct_cause, contributing_factor, consequence, correlation)
3. Confidence level

Rules:
- Only assert causality with historical evidence
- Distinguish correlation from causation
- Consider temporal order (cause must precede effect)

Return JSON:
{
  "causal_links": [
    {
      "cause_event_id": "...",
      "effect_event_id": "...",
      "relationship_type": "direct_cause|contributing_factor|consequence|correlation",
      "confidence": 0.0-1.0,
      "evidence": "brief explanation"
    }
  ],
  "uncertain_links": [
    {
      "event_pair": ["...", "..."],
      "reason": "why uncertain"
    }
  ]
}"""
```

### 프롬프트 템플릿: 복잡한 관계 네트워크

```python
GPT_ADVANCED_NETWORK = """Analyze the relationship network in this historical text.

Text:
{full_text}

Known entities:
{entities}

Extract ALL relationships:
- Family: father, mother, child, spouse, sibling
- Professional: teacher, student, employer, colleague
- Political: ally, rival, successor, predecessor
- Event: participant, organizer, victim, witness

Return comprehensive network:
{
  "relationships": [
    {
      "source": "entity_name",
      "target": "entity_name",
      "type": "...",
      "subtype": "..." or null,
      "temporal_context": "when this relationship existed",
      "evidence_quote": "exact quote from text",
      "confidence": 0.0-1.0
    }
  ],
  "inferred_relationships": [
    {
      "source": "...",
      "target": "...",
      "type": "...",
      "inference_reason": "why inferred (e.g., 'siblings share parents')"
    }
  ]
}"""
```

---

## 5. 에러 처리 및 폴백 전략

### 에스컬레이션 로직

```python
class ExtractionPipeline:
    def __init__(self):
        self.tier1 = OllamaClient()
        self.tier2 = OpenAIClient(model="gpt-5-mini")
        self.tier3 = OpenAIClient(model="gpt-5.1-chat-latest")

    def extract_entities(self, text: str, chunk_id: str) -> dict:
        # Tier 1 시도
        try:
            result = self.tier1.extract(text, LLAMA_ENTITY_EXTRACTION)
            parsed = parse_llama_output(result)
            if self._is_valid(parsed):
                return {"result": parsed, "tier": 1, "cost": 0}
        except (ParseError, EscalateToTier2) as e:
            log.info(f"Tier 1 failed for {chunk_id}: {e}")

        # Tier 2 폴백
        try:
            result = self.tier2.extract(text, GPT_MINI_ENTITY_EXTRACTION)
            return {"result": result, "tier": 2, "cost": self._calculate_cost(text, "mini")}
        except Exception as e:
            log.warning(f"Tier 2 failed for {chunk_id}: {e}")

        # Tier 3 최후 수단 (비용 주의)
        if self._is_high_value_text(text):
            result = self.tier3.extract(text, GPT_ADVANCED_EXTRACTION)
            return {"result": result, "tier": 3, "cost": self._calculate_cost(text, "advanced")}

        return {"result": None, "tier": None, "error": "All tiers failed"}

    def _is_valid(self, result: dict) -> bool:
        """결과 품질 검증"""
        # 최소 1개 엔티티 필요
        total = sum(len(v) for v in result.values() if isinstance(v, list))
        return total > 0

    def _is_high_value_text(self, text: str) -> bool:
        """Tier 3 사용 가치 판단"""
        # 역사적으로 중요한 키워드 포함 시
        important_keywords = ['war', 'revolution', 'treaty', 'emperor', 'king']
        return any(kw in text.lower() for kw in important_keywords)
```

### 품질 검증

```python
def validate_extraction(result: dict, text: str) -> dict:
    """추출 결과 품질 검증"""
    issues = []

    # 1. 텍스트에 없는 엔티티 체크
    for entity in result.get("persons", []):
        if entity.lower() not in text.lower():
            issues.append(f"Hallucinated entity: {entity}")

    # 2. 시간 일관성 체크
    if result.get("birth_year") and result.get("death_year"):
        if result["birth_year"] > result["death_year"]:
            issues.append("Invalid: birth after death")

    # 3. 관계 검증
    for rel in result.get("relationships", []):
        if rel["target"] not in text:
            issues.append(f"Relationship target not in text: {rel['target']}")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "confidence_adjustment": 1.0 - (len(issues) * 0.1)
    }
```

---

## 6. 비용 최적화

### 예상 비용 (책 1권 기준)

| 단계 | 모델 | 청크 수 | 토큰/청크 | 총 비용 |
|------|------|---------|-----------|---------|
| 기본 추출 | llama3.1 | 200 | 2000 | $0 |
| 폴백 (10%) | gpt-5-mini | 20 | 2500 | ~$0.01 |
| 복잡 작업 | gpt-5.1 | 5 | 4000 | ~$0.03 |
| **합계** | | | | **~$0.04/책** |

### 비용 모니터링

```python
class CostTracker:
    def __init__(self):
        self.daily_budget = 5.0  # $5/일
        self.spent_today = 0.0

    def can_use_tier(self, tier: int, estimated_tokens: int) -> bool:
        cost_per_1k = {1: 0, 2: 0.00025, 3: 0.00125}
        estimated_cost = (estimated_tokens / 1000) * cost_per_1k[tier]
        return (self.spent_today + estimated_cost) < self.daily_budget

    def log_usage(self, tier: int, tokens: int):
        # 사용량 기록 및 알림
        pass
```

---

## 7. 프롬프트 버전 관리

```python
PROMPT_VERSIONS = {
    "entity_extraction": {
        "v1": {
            "llama": LLAMA_ENTITY_EXTRACTION_V1,
            "mini": GPT_MINI_ENTITY_EXTRACTION_V1,
            "description": "초기 버전"
        },
        "v2": {
            "llama": LLAMA_ENTITY_EXTRACTION_V2,
            "mini": GPT_MINI_ENTITY_EXTRACTION_V2,
            "description": "Few-shot 예시 추가"
        }
    },
    "attribute_extraction": {
        "v1": {...}
    }
}

# 버전 전환
CURRENT_VERSIONS = {
    "entity_extraction": "v2",
    "attribute_extraction": "v1"
}

def get_prompt(task: str, model: str) -> str:
    version = CURRENT_VERSIONS[task]
    return PROMPT_VERSIONS[task][version][model]
```

---

## 8. 테스트 및 평가

### 벤치마크 데이터셋

```
poc/data/benchmark/
├── entity_extraction/
│   ├── test_cases.json      # 입력 텍스트
│   └── expected_output.json # 정답
├── attribute_extraction/
└── chain_generation/
```

### 평가 메트릭

```python
def evaluate_extraction(predicted: dict, expected: dict) -> dict:
    """추출 정확도 평가"""
    metrics = {}

    for entity_type in ["persons", "locations", "events"]:
        pred_set = set(predicted.get(entity_type, []))
        exp_set = set(expected.get(entity_type, []))

        precision = len(pred_set & exp_set) / len(pred_set) if pred_set else 0
        recall = len(pred_set & exp_set) / len(exp_set) if exp_set else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

        metrics[entity_type] = {
            "precision": precision,
            "recall": recall,
            "f1": f1
        }

    return metrics
```

### 모델별 성능 기준

| 작업 | llama3.1 목표 | gpt-5-mini 목표 | gpt-5.1 목표 |
|------|--------------|-----------------|--------------|
| 엔티티 추출 F1 | > 0.7 | > 0.85 | > 0.95 |
| 속성 추출 정확도 | N/A | > 0.8 | > 0.9 |
| 관계 추출 F1 | N/A | > 0.75 | > 0.9 |

---

## 9. 구현 우선순위

| 단계 | 작업 | 우선순위 |
|------|------|----------|
| 1 | Tier 1 llama 프롬프트 최적화 | 높음 |
| 2 | 에스컬레이션 로직 구현 | 높음 |
| 3 | Tier 2 속성 추출 프롬프트 | 높음 |
| 4 | 벤치마크 데이터셋 구축 | 중간 |
| 5 | Tier 3 체인 생성 프롬프트 | 중간 |
| 6 | 비용 모니터링 대시보드 | 낮음 |
