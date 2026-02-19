"""
Optimized batch LLM classifier for event hierarchy.

Two-phase approach:
1. Phase 1: Classify events and save results to JSON file
2. Phase 2: Apply results to DB (parents first, then children)

This prevents duplicate parent creation when child is processed before parent.
"""
import json
import asyncio
import sys
import os
from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv()

from openai import AsyncOpenAI

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

from sqlalchemy import text
from app.db.session import SessionLocal


# Configuration
MODEL = "gpt-5.1-chat-latest"
BATCH_SIZE = 15  # Events per API call
MAX_CONCURRENT = 3  # Parallel API calls
OUTPUT_DIR = Path(__file__).parent / "classification_results"


SYSTEM_PROMPT = """당신은 역사학 전문가입니다. 주어진 역사적 이벤트들을 분석하여 각각의 상위 역사적 맥락을 분류합니다.

## 분류 기준

### 계층 레벨 (hierarchy_level)
- 0: 시대 (Era) - 고대, 중세, 근대, 현대
- 1: 대사건 (Mega) - 로마 제국, 대항해시대, 산업혁명
- 2: 집합 사건 (Aggregate) - 백년전쟁, 십자군 전쟁, 나폴레옹 전쟁
- 3: 주요 사건 (Major) - 개별 전투, 조약, 혁명
- 4: 세부 사건 (Minor) - 소규모 교전, 부속 조약

### 관계 맥락 (context)
- war: 전쟁, 군사 작전, 전투
- dynasty: 왕조, 제국, 통치 시대
- revolution: 혁명, 봉기, 사회 변혁
- expedition: 탐험, 원정, 식민
- scientific_era: 과학 혁명, 기술 발전 시대
- philosophical_school: 철학, 사상, 계몽
- artistic_period: 예술 사조, 문화 운동
- religious: 종교 운동, 종교 전쟁
- general: 기타

### 중요 규칙
1. **시간 정합성**: 상위 이벤트는 하위 이벤트 시기를 포함해야 함 (±50년 허용)
2. **구체적 상위 선택**: 가능하면 구체적인 상위 선택 (예: "백년전쟁" > "중세")
3. **다중 맥락 가능**: 하나의 이벤트가 여러 맥락에 속할 수 있음
4. **최상위 이벤트**: 그 자체가 시대/집합인 경우 has_parent=false

### 잘 알려진 상위 이벤트 예시
- World War I, World War II (war)
- Hundred Years' War, Thirty Years' War (war)
- Age of Exploration, Age of Enlightenment (expedition/philosophical_school)
- Industrial Revolution, Scientific Revolution (scientific_era)
- French Revolution, American Revolution (revolution)
- Roman Empire, Byzantine Empire, Ottoman Empire (dynasty)
- Renaissance, Reformation (artistic_period/religious)
- Crusades, Napoleonic Wars (war)

## 응답 형식

각 이벤트에 대해 다음 JSON 배열로 응답:

```json
{
  "results": [
    {
      "id": 123,
      "has_parent": true,
      "parent": "Hundred Years' War",
      "parent_ko": "백년전쟁",
      "parent_qid": "Q12544",
      "context": "war",
      "confidence": "high",
      "level": 3,
      "reason": "1415년 아쟁쿠르 전투는 백년전쟁의 주요 전투"
    },
    {
      "id": 456,
      "has_parent": false,
      "context": "war",
      "confidence": "high",
      "level": 2,
      "reason": "제2차 세계대전은 그 자체가 최상위 집합 이벤트"
    }
  ]
}
```

필드 설명:
- id: 이벤트 ID (입력에서 제공)
- has_parent: 상위 이벤트 존재 여부
- parent: 상위 이벤트 영문명 (has_parent=true일 때)
- parent_ko: 상위 이벤트 한글명
- parent_qid: Wikidata QID (알면, 예: Q12544)
- context: 관계 맥락
- confidence: high/medium/low
- level: 해당 이벤트의 계층 레벨
- reason: 분류 근거 (간단히)"""


def format_year(year: int) -> str:
    if year < 0:
        return f"{abs(year)} BCE"
    return f"{year} CE"


def build_batch_prompt(events: list[dict]) -> str:
    """Build prompt for batch of events."""
    lines = ["다음 이벤트들을 분류해주세요:\n"]

    for e in events:
        date_str = format_year(e['date_start'])
        if e.get('date_end') and e['date_end'] != e['date_start']:
            date_str += f" ~ {format_year(e['date_end'])}"

        lines.append(f"[ID: {e['id']}]")
        lines.append(f"  제목: {e['title']}")
        lines.append(f"  날짜: {date_str}")
        if e.get('location'):
            lines.append(f"  장소: {e['location']}")
        if e.get('category'):
            lines.append(f"  카테고리: {e['category']}")
        if e.get('description'):
            desc = e['description'][:200] + '...' if len(e['description']) > 200 else e['description']
            lines.append(f"  설명: {desc}")
        lines.append("")

    return "\n".join(lines)


@dataclass
class BatchResult:
    event_id: int
    event_title: str  # Store title for matching
    has_parent: bool
    parent_event: Optional[str] = None
    parent_event_ko: Optional[str] = None
    parent_qid: Optional[str] = None
    context: str = "general"
    confidence: str = "medium"
    hierarchy_level: int = 3
    reasoning: str = ""
    error: Optional[str] = None


class BatchClassifier:
    def __init__(self, api_key: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    async def classify_batch(self, events: list[dict]) -> list[BatchResult]:
        """Classify a batch of events in one API call."""
        async with self.semaphore:
            prompt = build_batch_prompt(events)

            try:
                response = await self.client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )

                # Track tokens
                if response.usage:
                    self.total_input_tokens += response.usage.prompt_tokens
                    self.total_output_tokens += response.usage.completion_tokens

                return self._parse_response(events, response)

            except Exception as e:
                # Return error results for all events in batch
                return [
                    BatchResult(
                        event_id=ev['id'],
                        event_title=ev['title'],
                        has_parent=False,
                        error=str(e)[:100]
                    )
                    for ev in events
                ]

    def _parse_response(self, events: list[dict], response) -> list[BatchResult]:
        """Parse API response into BatchResult objects."""
        results = []
        event_map = {e['id']: e for e in events}

        try:
            data = json.loads(response.choices[0].message.content)
            items = data.get('results', [])

            # Map results by ID
            result_map = {}
            for item in items:
                eid = item.get('id')
                if eid:
                    result_map[eid] = item

            # Create BatchResult for each input event
            for e in events:
                item = result_map.get(e['id'])
                if item:
                    results.append(BatchResult(
                        event_id=e['id'],
                        event_title=e['title'],
                        has_parent=item.get('has_parent', True),
                        parent_event=item.get('parent'),
                        parent_event_ko=item.get('parent_ko'),
                        parent_qid=item.get('parent_qid'),
                        context=item.get('context', 'general'),
                        confidence=item.get('confidence', 'medium'),
                        hierarchy_level=item.get('level', 3),
                        reasoning=item.get('reason', '')
                    ))
                else:
                    results.append(BatchResult(
                        event_id=e['id'],
                        event_title=e['title'],
                        has_parent=False,
                        error="Not in response"
                    ))

        except json.JSONDecodeError as je:
            for e in events:
                results.append(BatchResult(
                    event_id=e['id'],
                    event_title=e['title'],
                    has_parent=False,
                    error=f"JSON parse error: {str(je)[:50]}"
                ))

        return results

    def get_cost_estimate(self) -> dict:
        """Get estimated cost based on token usage."""
        # GPT-4o pricing estimate
        input_cost = self.total_input_tokens / 1000 * 0.0025
        output_cost = self.total_output_tokens / 1000 * 0.01
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "estimated_cost": input_cost + output_cost
        }


# ============================================================
# PHASE 1: Classification (LLM calls, save to JSON)
# ============================================================

async def phase1_classify(limit: int = 100, offset: int = 0) -> Path:
    """
    Phase 1: Run LLM classification and save results to JSON file.
    Returns the path to the output file.
    """
    db = SessionLocal()
    classifier = BatchClassifier()

    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"classification_{timestamp}.json"

    try:
        # Get events to classify
        result = db.execute(text("""
            SELECT e.id, e.title, e.date_start, e.date_end,
                   l.name as location, c.name as category, e.description
            FROM events e
            LEFT JOIN locations l ON l.id = e.primary_location_id
            LEFT JOIN categories c ON c.id = e.category_id
            WHERE e.parent_status = 'unknown'
            ORDER BY e.importance DESC
            LIMIT :limit OFFSET :offset
        """), {"limit": limit, "offset": offset})

        events = [dict(row._mapping) for row in result]

        print(f"[Phase 1] Classifying {len(events)} events")
        print(f"Output: {output_file}")
        print("=" * 60)

        all_results = []
        total_batches = (len(events) + BATCH_SIZE - 1) // BATCH_SIZE

        for i in range(0, len(events), BATCH_SIZE):
            batch = events[i:i+BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1

            print(f"\nBatch {batch_num}/{total_batches} ({len(batch)} events)...")

            results = await classifier.classify_batch(batch)
            all_results.extend(results)

            # Print batch results
            for r in results:
                if r.error:
                    print(f"  [{r.event_id}] ERROR: {r.error}")
                elif r.has_parent:
                    print(f"  [{r.event_id}] -> {r.parent_event} ({r.context}, {r.confidence})")
                else:
                    print(f"  [{r.event_id}] -> (top-level, L{r.hierarchy_level})")

            # Save incrementally every 500 events
            if len(all_results) % 500 == 0:
                _save_results_json(output_file, all_results)
                print(f"  [Checkpoint saved: {len(all_results)} results]")

        # Final save
        _save_results_json(output_file, all_results)

        # Summary
        print("\n" + "=" * 60)
        print("PHASE 1 COMPLETE")
        print("=" * 60)

        success = [r for r in all_results if not r.error]
        with_parent = [r for r in success if r.has_parent]
        top_level = [r for r in success if not r.has_parent]
        errors = [r for r in all_results if r.error]

        print(f"Total classified: {len(all_results)}")
        print(f"  With parent: {len(with_parent)}")
        print(f"  Top-level: {len(top_level)}")
        print(f"  Errors: {len(errors)}")

        cost = classifier.get_cost_estimate()
        print(f"\nToken usage:")
        print(f"  Input:  {cost['input_tokens']:,}")
        print(f"  Output: {cost['output_tokens']:,}")
        print(f"  Est. cost: ${cost['estimated_cost']:.4f}")

        print(f"\nResults saved to: {output_file}")
        print(f"\nRun Phase 2 to apply results:")
        print(f"  python {__file__} --phase2 {output_file}")

        return output_file

    finally:
        db.close()


def _save_results_json(filepath: Path, results: list[BatchResult]):
    """Save results to JSON file."""
    data = [asdict(r) for r in results]
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================
# Parent Name Normalization (prevent duplicates)
# ============================================================

# Known aliases for common parent events
PARENT_ALIASES = {
    # World Wars
    "WWII": "World War II",
    "WW2": "World War II",
    "Second World War": "World War II",
    "WWI": "World War I",
    "WW1": "World War I",
    "First World War": "World War I",
    "Great War": "World War I",
    # Napoleonic
    "Napoleonic Era": "Napoleonic Wars",
    # Crusades
    "The Crusades": "Crusades",
    # Revolutions
    "American War of Independence": "American Revolution",
    "American Revolutionary War": "American Revolution",
    # Hundred Years War
    "Hundred Years War": "Hundred Years' War",
    "100 Years War": "Hundred Years' War",
    # Others
    "Industrial Age": "Industrial Revolution",
    "Age of Discovery": "Age of Exploration",
}


def normalize_parent_name(name: str) -> str:
    """Normalize parent event name to prevent duplicates."""
    if not name:
        return name
    # Check aliases
    if name in PARENT_ALIASES:
        return PARENT_ALIASES[name]
    # Basic normalization
    normalized = name.strip()
    return normalized


# ============================================================
# PHASE 2: Apply to DB (parents first, then children)
# ============================================================

def phase2_apply(json_file: Path):
    """
    Phase 2: Apply classification results to database.
    Processes in correct order: top-level events first, then children.
    """
    print(f"[Phase 2] Applying results from: {json_file}")
    print("=" * 60)

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = [BatchResult(**d) for d in data]

    # Separate into categories
    errors = [r for r in results if r.error]
    top_level = [r for r in results if not r.error and not r.has_parent]
    with_parent = [r for r in results if not r.error and r.has_parent]

    print(f"Total results: {len(results)}")
    print(f"  Top-level: {len(top_level)}")
    print(f"  With parent: {len(with_parent)}")
    print(f"  Errors (skip): {len(errors)}")

    db = SessionLocal()

    try:
        # Step 1: Process top-level events first
        print(f"\n[Step 1] Processing {len(top_level)} top-level events...")
        for r in top_level:
            db.execute(text("""
                UPDATE events
                SET parent_status = 'none',
                    hierarchy_level = :level,
                    is_aggregate = CASE WHEN :level <= 2 THEN true ELSE false END
                WHERE id = :id
            """), {"id": r.event_id, "level": r.hierarchy_level})
        db.commit()
        print(f"  Done: {len(top_level)} events marked as top-level")

        # Step 2: Build parent name -> ID mapping from existing events
        print(f"\n[Step 2] Building parent mapping...")

        # Get unique parent names mentioned (normalized)
        parent_names = set()
        parent_qids = set()
        for r in with_parent:
            if r.parent_event:
                normalized = normalize_parent_name(r.parent_event)
                parent_names.add(normalized)
            if r.parent_qid:
                parent_qids.add(r.parent_qid)

        # Find existing events that match parent names
        parent_map = {}  # name/qid -> event_id

        # Match by QID first (most reliable)
        if parent_qids:
            result = db.execute(text("""
                SELECT id, title, wikidata_id FROM events
                WHERE wikidata_id = ANY(:qids)
            """), {"qids": list(parent_qids)})
            for row in result:
                parent_map[row[2]] = row[0]  # qid -> id
                parent_map[row[1]] = row[0]  # title -> id (also map by title)

        # Match by title
        if parent_names:
            # Also check if any classified event IS a parent
            event_title_to_id = {}
            for r in results:
                if not r.error:
                    event_title_to_id[r.event_title] = r.event_id

            # Check both DB and classified results
            result = db.execute(text("""
                SELECT id, title FROM events
                WHERE title = ANY(:titles)
            """), {"titles": list(parent_names)})
            for row in result:
                if row[1] not in parent_map:
                    parent_map[row[1]] = row[0]

            # Also check in our classified results (event might be its own parent candidate)
            for name in parent_names:
                if name in event_title_to_id and name not in parent_map:
                    parent_map[name] = event_title_to_id[name]

        print(f"  Found {len(parent_map)} matching parents in DB/results")

        # Step 3: 부모 이벤트는 이미 DB에 있어야 함 (Wikidata에서 import 했으므로)
        # 새로 생성하지 않음 - 못 찾으면 검색 문제이거나 LLM 환각
        print(f"\n[Step 3] Verifying parent events exist in DB...")

        missing_count = 0
        for r in with_parent:
            normalized_name = normalize_parent_name(r.parent_event) if r.parent_event else None
            key = r.parent_qid or normalized_name
            if key and key not in parent_map:
                missing_count += 1

        print(f"  Parents in DB: {len(parent_map)}")
        print(f"  Parents not found: {missing_count} (will be skipped)")

        # Step 4: Link children to parents
        print(f"\n[Step 4] Linking {len(with_parent)} children to parents...")
        linked_count = 0
        not_found = 0

        for r in with_parent:
            normalized_name = normalize_parent_name(r.parent_event) if r.parent_event else None
            key = r.parent_qid or normalized_name
            parent_id = parent_map.get(key)

            if not parent_id and normalized_name:
                parent_id = parent_map.get(normalized_name)

            if parent_id:
                # Update event
                db.execute(text("""
                    UPDATE events
                    SET parent_event_id = :parent_id,
                        parent_status = :status,
                        hierarchy_level = :level
                    WHERE id = :id
                """), {
                    "parent_id": parent_id,
                    "status": "pending" if r.confidence != "high" else "confirmed",
                    "level": r.hierarchy_level,
                    "id": r.event_id
                })

                # Add to event_parents
                db.execute(text("""
                    INSERT INTO event_parents (event_id, parent_event_id, is_primary, context, source, confidence)
                    VALUES (:eid, :pid, true, :ctx, 'llm', :conf)
                    ON CONFLICT (event_id, parent_event_id) DO UPDATE SET
                        context = :ctx, confidence = :conf
                """), {
                    "eid": r.event_id,
                    "pid": parent_id,
                    "ctx": r.context,
                    "conf": {"high": 0.9, "medium": 0.7, "low": 0.5}.get(r.confidence, 0.7)
                })
                linked_count += 1
            else:
                not_found += 1
                print(f"  Warning: Parent not found for [{r.event_id}] -> {r.parent_event}")

        db.commit()

        # Step 5: Update importance based on hierarchy level (scale 1-5)
        print(f"\n[Step 5] Updating importance scores...")
        db.execute(text("""
            UPDATE events
            SET importance = CASE
                WHEN hierarchy_level <= 1 THEN 5
                WHEN hierarchy_level = 2 THEN GREATEST(importance, 4)
                WHEN hierarchy_level = 3 THEN GREATEST(importance, 3)
                ELSE importance
            END
            WHERE hierarchy_level IS NOT NULL
            AND is_aggregate = true
        """))
        db.commit()
        print("  Done")

        print(f"\n" + "=" * 60)
        print("PHASE 2 COMPLETE")
        print("=" * 60)
        print(f"  Linked: {linked_count}")
        print(f"  Parent not found: {not_found}")

    finally:
        db.close()


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Batch LLM event classifier (2-phase)")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--phase2", type=str, help="Path to JSON file for phase 2")

    args = parser.parse_args()

    if args.phase2:
        # Phase 2: Apply results from JSON
        phase2_apply(Path(args.phase2))
    else:
        # Phase 1: Classify and save to JSON
        asyncio.run(phase1_classify(limit=args.limit, offset=args.offset))
