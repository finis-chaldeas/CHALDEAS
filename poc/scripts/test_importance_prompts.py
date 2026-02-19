"""
Test importance scoring prompts with gpt-5-mini.
Compares 3 prompt strategies on a curated set of events.
"""
import sys
import os
import json
import asyncio

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# Add backend to path for DB access
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from openai import OpenAI
from sqlalchemy import create_engine, text

engine = create_engine('postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas')
client = OpenAI()  # Uses OPENAI_API_KEY from env

MODEL = "gpt-5-mini"

# Test events: mix of world-defining, major, regional, minor
TEST_EVENT_TITLES = [
    # World-defining (expected: 85-100)
    'World War II',
    'French Revolution',
    'Fall of Constantinople',
    # Major (expected: 60-85)
    'Battle of Hastings',
    'American Revolution',
    'Battle of Thermopylae',  # 480 BCE one
    # Regional/notable (expected: 30-60)
    'Siege of Hull',
    'Battle of Klyastitsy',
    'Battle of Waxhaws',
    # Minor (expected: 1-30)
    'Battle of Kurowem (1831)',
    'Battle of Flint Creek',
    'Battle of Haram',
]

# ── Prompt A: Simple direct ──
PROMPT_A = """You are a world history expert. Rate the historical importance of this event on a scale of 1-100.

Scoring guide:
- 90-100: Civilization-defining (changed the course of human history)
- 70-89: Major turning point (reshaped a region or era)
- 50-69: Significant event (notable impact, remembered in history)
- 30-49: Regional/limited event (affected a specific area or group)
- 10-29: Minor event (limited scope, short-term impact)
- 1-9: Trivial (barely notable)

Event: {title}
Date: {date}
Description: {description}

Respond with ONLY a JSON object: {{"score": <number>, "reason": "<one sentence>"}}"""

# ── Prompt B: Multi-criteria rubric ──
PROMPT_B = """You are a world history expert. Score this event's historical importance (1-100) by evaluating:

1. GLOBAL REACH: Did it affect multiple civilizations/continents? (0-25 pts)
2. LASTING LEGACY: How long did the consequences last? (0-25 pts)
3. SCALE OF IMPACT: How many people were directly affected? (0-25 pts)
4. PARADIGM SHIFT: Did it fundamentally change politics, culture, or thought? (0-25 pts)

Event: {title}
Date: {date}
Description: {description}

Respond with ONLY a JSON object: {{"score": <number>, "g": <0-25>, "l": <0-25>, "s": <0-25>, "p": <0-25>, "reason": "<one sentence>"}}"""

# ── Prompt C: Anchor-based comparison ──
PROMPT_C = """You are a world history expert scoring events on a 1-100 importance scale.

Reference points:
- World War II = 97 (global conflict, reshaped world order)
- French Revolution = 88 (ended monarchy, inspired democracies worldwide)
- Fall of the Roman Empire = 92 (ended an era, reshaped Europe)
- Battle of Hastings = 72 (changed England's trajectory)
- Siege of Vienna 1683 = 55 (regional turning point)
- A minor border skirmish = 8

Now score this event relative to these anchors:

Event: {title}
Date: {date}
Description: {description}

Respond with ONLY a JSON object: {{"score": <number>, "reason": "<one sentence>"}}"""


def get_test_events():
    """Fetch test events from DB."""
    events = []
    with engine.connect() as conn:
        for title in TEST_EVENT_TITLES:
            row = conn.execute(text("""
                SELECT e.id, e.title, e.date_start, e.date_end,
                       LEFT(ed.description, 300) as description,
                       (SELECT COUNT(*) FROM event_persons WHERE event_id = e.id) as person_count
                FROM events e
                LEFT JOIN event_details ed ON ed.event_id = e.id
                WHERE e.title = :title AND e.wikidata_id IS NOT NULL
                ORDER BY
                    (SELECT COUNT(*) FROM event_persons WHERE event_id = e.id) DESC,
                    e.date_start
                LIMIT 1
            """), {"title": title}).fetchone()

            if row:
                date_str = str(row[2])
                if row[3] and row[3] != row[2]:
                    date_str += f" to {row[3]}"
                if row[2] < 0:
                    date_str = f"{abs(row[2])} BCE" + (f" to {abs(row[3])} BCE" if row[3] and row[3] != row[2] else "")

                events.append({
                    "id": row[0],
                    "title": row[1],
                    "date": date_str,
                    "description": row[4] or f"Historical event: {row[1]}",
                    "person_count": row[5],
                })
            else:
                print(f"  [WARN] Not found: {title}")
    return events


def score_event(event: dict, prompt_template: str) -> dict:
    """Score a single event with a given prompt."""
    prompt = prompt_template.format(
        title=event["title"],
        date=event["date"],
        description=event["description"][:300],
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=3000,  # reasoning model needs room for thinking
        )
        content = response.choices[0].message.content.strip()
        # Parse JSON from response
        # Handle markdown code blocks
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(content)
        return result
    except Exception as e:
        return {"score": -1, "reason": f"ERROR: {e}", "raw": content if 'content' in dir() else ""}


def main():
    print("=" * 80)
    print("IMPORTANCE SCORING PROMPT TEST")
    print(f"Model: {MODEL}")
    print("=" * 80)

    # Fetch events
    print("\nFetching test events...")
    events = get_test_events()
    print(f"Found {len(events)} events\n")

    prompts = {
        "A_simple": PROMPT_A,
        "B_rubric": PROMPT_B,
        "C_anchor": PROMPT_C,
    }

    all_results = {}

    for prompt_name, prompt_template in prompts.items():
        print(f"\n{'─' * 60}")
        print(f"  PROMPT {prompt_name}")
        print(f"{'─' * 60}")

        results = []
        for event in events:
            result = score_event(event, prompt_template)
            score = result.get("score", -1)
            reason = result.get("reason", "?")
            results.append({"event": event["title"], "score": score, "reason": reason, "full": result})

            # Display
            bar = "█" * (score // 5) if score > 0 else "ERROR"
            print(f"  {score:3d} {bar:<20s} {event['title']}")

        all_results[prompt_name] = results

    # ── Comparison table ──
    print(f"\n\n{'=' * 80}")
    print("COMPARISON TABLE")
    print(f"{'=' * 80}")
    print(f"{'Event':<35s} {'A_simple':>8s} {'B_rubric':>8s} {'C_anchor':>8s} {'Avg':>6s}")
    print(f"{'─' * 35} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 6}")

    for i, event in enumerate(events):
        scores = []
        row = f"{event['title'][:34]:<35s}"
        for prompt_name in prompts:
            s = all_results[prompt_name][i]["score"]
            scores.append(s)
            row += f" {s:>7d}"
        avg = sum(scores) / len(scores) if all(s > 0 for s in scores) else -1
        row += f" {avg:>6.1f}"
        print(row)

    # ── Spread analysis ──
    print(f"\n{'─' * 60}")
    print("SPREAD ANALYSIS (good prompt = wide spread between major & minor)")
    for prompt_name in prompts:
        scores = [r["score"] for r in all_results[prompt_name] if r["score"] > 0]
        if scores:
            print(f"  {prompt_name}: min={min(scores)}, max={max(scores)}, spread={max(scores)-min(scores)}, stdev={( sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores) )**0.5:.1f}")

    # ── Save results ──
    output_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'benchmark', 'importance_prompt_test.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
