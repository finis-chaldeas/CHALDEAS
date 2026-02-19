"""
LLM-based event classifier using gpt-5.1-chat-latest.

Classifies events into their parent events with context information.
Falls back when Wikidata P361 is not available.
"""
import json
import asyncio
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import os

from openai import AsyncOpenAI


# Model configuration
MODEL = "gpt-5.1-chat-latest"
TEMPERATURE = 0.3  # Low for consistency
MAX_TOKENS = 500


class Confidence(Enum):
    HIGH = "high"      # 0.9 - auto apply
    MEDIUM = "medium"  # 0.7 - review recommended
    LOW = "low"        # 0.4 - needs manual review


@dataclass
class ClassificationResult:
    """Result of LLM classification."""
    event_id: int
    # Primary parent
    parent_event: Optional[str] = None
    parent_event_ko: Optional[str] = None
    parent_event_qid: Optional[str] = None
    # Classification
    hierarchy_level: int = 3
    context: str = "general"  # war, culture, religion, etc.
    confidence: Confidence = Confidence.LOW
    reasoning: str = ""
    # Additional parents (if any)
    additional_parents: list[dict] = field(default_factory=list)
    # Validation
    has_parent: bool = True  # False = confirmed no parent (top-level)
    warnings: list[str] = field(default_factory=list)

    @property
    def confidence_score(self) -> float:
        return {
            Confidence.HIGH: 0.9,
            Confidence.MEDIUM: 0.7,
            Confidence.LOW: 0.4
        }[self.confidence]


# System prompt
SYSTEM_PROMPT = """당신은 역사학 전문가입니다. 주어진 역사적 이벤트를 분석하여
어떤 상위 역사적 맥락에 속하는지 분류합니다.

## 분류 기준

### 계층 레벨 (hierarchy_level)
- 0: 시대 (Era) - 고대, 중세, 근대, 현대
- 1: 대사건 (Mega) - 로마 제국, 대항해시대
- 2: 집합 사건 (Aggregate) - 백년전쟁, 십자군 전쟁
- 3: 주요 사건 (Major) - 아쟁쿠르 전투
- 4: 세부 사건 (Minor) - 특정 조약, 소규모 교전

### 관계 맥락 (context)
- war: 전쟁/군사 맥락
- culture: 문화/예술 맥락
- religion: 종교 맥락
- politics: 정치 맥락
- science: 과학 맥락
- philosophy: 철학 맥락
- general: 일반/기본

### 중요: 시간 정합성
상위 이벤트의 기간은 하위 이벤트를 포함해야 합니다.
±50년 초과 벗어나면 해당 상위는 불가능합니다.

예:
- Battle of Hastings (1066) → Norman England (1066-1154) ✅
- Battle of Hastings (1066) → Roman Britain (43-410) ❌

### 다중 상위 지원
하나의 이벤트가 여러 맥락에서 다른 상위에 속할 수 있습니다.
예: 진주만 공격 → WW2 (war) + 태평양 전쟁 (war)
예: 잔 다르크 화형 → 백년전쟁 (war) + 중세 종교재판 (religion)

## 응답 형식 (JSON)

{
    "primary_parent": {
        "name": "상위 이벤트 영어 이름",
        "name_ko": "상위 이벤트 한국어 이름",
        "qid": "Wikidata QID (알면, 예: Q12544)",
        "context": "war|culture|religion|politics|science|philosophy|general"
    },
    "additional_parents": [
        {
            "name": "추가 상위 이벤트",
            "name_ko": "추가 상위 한국어",
            "qid": null,
            "context": "religion"
        }
    ],
    "hierarchy_level": 3,
    "has_parent": true,
    "confidence": "high|medium|low",
    "reasoning": "분류 이유 (1-2문장)"
}

상위가 없는 최상위 이벤트면:
{
    "primary_parent": null,
    "additional_parents": [],
    "hierarchy_level": 0,
    "has_parent": false,
    "confidence": "high",
    "reasoning": "최상위 시대/개념이므로 상위 이벤트 없음"
}
"""


# Few-shot examples
FEW_SHOT_EXAMPLES = [
    # Example 1: Clear war event
    {
        "input": "이벤트: Battle of Agincourt\n날짜: 1415 CE\n장소: Agincourt, France\n카테고리: warfare\n설명: Major English victory in the Hundred Years' War",
        "output": {
            "primary_parent": {
                "name": "Hundred Years' War",
                "name_ko": "백년전쟁",
                "qid": "Q12544",
                "context": "war"
            },
            "additional_parents": [],
            "hierarchy_level": 3,
            "has_parent": True,
            "confidence": "high",
            "reasoning": "1415년 영국-프랑스 전투로 백년전쟁(1337-1453)의 주요 전투"
        }
    },
    # Example 2: Multiple parents
    {
        "input": "이벤트: Attack on Pearl Harbor\n날짜: 1941 CE\n장소: Pearl Harbor, Hawaii\n카테고리: warfare\n설명: Japanese surprise attack that brought the US into World War II",
        "output": {
            "primary_parent": {
                "name": "World War II",
                "name_ko": "제2차 세계대전",
                "qid": "Q362",
                "context": "war"
            },
            "additional_parents": [
                {
                    "name": "Pacific War",
                    "name_ko": "태평양 전쟁",
                    "qid": "Q8683",
                    "context": "war"
                }
            ],
            "hierarchy_level": 3,
            "has_parent": True,
            "confidence": "high",
            "reasoning": "WW2와 태평양전쟁 모두의 핵심 사건. WW2가 더 포괄적이므로 primary"
        }
    },
    # Example 3: Mixed context
    {
        "input": "이벤트: Execution of Joan of Arc\n날짜: 1431 CE\n장소: Rouen, France\n카테고리: religion\n설명: Joan of Arc was burned at the stake for heresy",
        "output": {
            "primary_parent": {
                "name": "Hundred Years' War",
                "name_ko": "백년전쟁",
                "qid": "Q12544",
                "context": "war"
            },
            "additional_parents": [
                {
                    "name": "Medieval Inquisition",
                    "name_ko": "중세 종교재판",
                    "qid": "Q156064",
                    "context": "religion"
                }
            ],
            "hierarchy_level": 3,
            "has_parent": True,
            "confidence": "high",
            "reasoning": "백년전쟁 맥락의 정치적 처형이자 종교재판 역사의 일부"
        }
    },
    # Example 4: Top-level event
    {
        "input": "이벤트: World War II\n날짜: 1939-1945 CE\n장소: Global\n카테고리: warfare\n설명: Global war involving most of the world's nations",
        "output": {
            "primary_parent": None,
            "additional_parents": [],
            "hierarchy_level": 1,
            "has_parent": False,
            "confidence": "high",
            "reasoning": "20세기 최대 전쟁으로 그 자체가 최상위 집합 이벤트"
        }
    }
]


def format_year(year: int) -> str:
    """Format year with BCE/CE."""
    if year < 0:
        return f"{abs(year)} BCE"
    return f"{year} CE"


def build_event_prompt(
    title: str,
    date_start: int,
    date_end: Optional[int],
    location: Optional[str],
    category: Optional[str],
    description: Optional[str]
) -> str:
    """Build prompt for event classification."""
    date_str = format_year(date_start)
    if date_end and date_end != date_start:
        date_str += f" - {format_year(date_end)}"

    prompt = f"""이벤트: {title}
날짜: {date_str}
장소: {location or '알 수 없음'}
카테고리: {category or '알 수 없음'}
설명: {(description[:500] + '...') if description and len(description) > 500 else description or '없음'}

이 이벤트의 상위 역사적 맥락을 분류해주세요."""

    return prompt


class LLMEventClassifier:
    """LLM-based event classifier."""

    def __init__(self, api_key: Optional[str] = None, model: str = MODEL):
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.semaphore = asyncio.Semaphore(5)  # Limit concurrent requests

    async def classify(
        self,
        event_id: int,
        title: str,
        date_start: int,
        date_end: Optional[int] = None,
        location: Optional[str] = None,
        category: Optional[str] = None,
        description: Optional[str] = None
    ) -> ClassificationResult:
        """Classify a single event."""
        async with self.semaphore:
            messages = self._build_messages(
                title, date_start, date_end, location, category, description
            )

            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS
                )

                return self._parse_response(event_id, response)

            except Exception as e:
                return ClassificationResult(
                    event_id=event_id,
                    confidence=Confidence.LOW,
                    reasoning=f"API error: {str(e)}",
                    warnings=[f"API error: {str(e)}"]
                )

    async def classify_batch(
        self,
        events: list[dict],
        progress_callback=None
    ) -> list[ClassificationResult]:
        """Classify multiple events."""
        results = []

        for i, event in enumerate(events):
            result = await self.classify(
                event_id=event["id"],
                title=event["title"],
                date_start=event["date_start"],
                date_end=event.get("date_end"),
                location=event.get("location"),
                category=event.get("category"),
                description=event.get("description")
            )
            results.append(result)

            if progress_callback and (i + 1) % 10 == 0:
                progress_callback(i + 1, len(events))

        return results

    def _build_messages(self, title, date_start, date_end, location, category, description) -> list[dict]:
        """Build messages for API call."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add few-shot examples
        for example in FEW_SHOT_EXAMPLES:
            messages.append({"role": "user", "content": example["input"]})
            messages.append({
                "role": "assistant",
                "content": json.dumps(example["output"], ensure_ascii=False)
            })

        # Add actual event
        prompt = build_event_prompt(title, date_start, date_end, location, category, description)
        messages.append({"role": "user", "content": prompt})

        return messages

    def _parse_response(self, event_id: int, response) -> ClassificationResult:
        """Parse API response into ClassificationResult."""
        try:
            content = response.choices[0].message.content
            data = json.loads(content)

            primary = data.get("primary_parent")
            additional = data.get("additional_parents", [])

            result = ClassificationResult(
                event_id=event_id,
                hierarchy_level=data.get("hierarchy_level", 3),
                has_parent=data.get("has_parent", True),
                confidence=Confidence(data.get("confidence", "low")),
                reasoning=data.get("reasoning", "")
            )

            if primary:
                result.parent_event = primary.get("name")
                result.parent_event_ko = primary.get("name_ko")
                result.parent_event_qid = primary.get("qid")
                result.context = primary.get("context", "general")

            if additional:
                result.additional_parents = additional

            return result

        except Exception as e:
            return ClassificationResult(
                event_id=event_id,
                confidence=Confidence.LOW,
                reasoning=f"Parse error: {str(e)}",
                warnings=[f"Parse error: {str(e)}"]
            )


# Test
async def test_classifier():
    classifier = LLMEventClassifier()

    print("Testing LLM classifier...")
    print("=" * 50)

    # Test 1: Clear war event
    result = await classifier.classify(
        event_id=1,
        title="Battle of Agincourt",
        date_start=1415,
        location="Agincourt, France",
        category="warfare",
        description="Major English victory in the Hundred Years' War"
    )
    print(f"\n1. Battle of Agincourt:")
    print(f"   Parent: {result.parent_event} ({result.parent_event_ko})")
    print(f"   Context: {result.context}")
    print(f"   Confidence: {result.confidence.value}")
    print(f"   Reasoning: {result.reasoning}")

    # Test 2: Multiple parents case
    result = await classifier.classify(
        event_id=2,
        title="Attack on Pearl Harbor",
        date_start=1941,
        location="Pearl Harbor, Hawaii",
        category="warfare",
        description="Japanese surprise attack"
    )
    print(f"\n2. Pearl Harbor:")
    print(f"   Primary: {result.parent_event}")
    print(f"   Additional: {[p['name'] for p in result.additional_parents]}")
    print(f"   Confidence: {result.confidence.value}")


if __name__ == "__main__":
    asyncio.run(test_classifier())
