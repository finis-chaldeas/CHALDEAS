"""
Importance scoring pipeline for events and persons.

Uses gpt-5-mini (rubric prompt) to score 1-100.
- Events: individual scoring (~28K)
- Persons: batched 10 per call (~190K → ~19K calls)

Features:
- Async concurrent API calls with rate limiting
- JSONL checkpoint files for resume
- Progress tracking

Usage:
    python score_importance.py events          # Score events only
    python score_importance.py persons         # Score persons only
    python score_importance.py all             # Score both
    python score_importance.py events --limit 100  # Test with 100
"""
import sys
import os
import json
import time
import asyncio
import argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / '.env')

from openai import AsyncOpenAI
from sqlalchemy import create_engine, text

# ── Config ──
MODEL = "gpt-5-mini"
MAX_CONCURRENT = 500       # Concurrent API calls (rate limit: 10K RPM)
MAX_COMPLETION_TOKENS = 2000
CHECKPOINT_DIR = Path(__file__).parent.parent / "data" / "importance_scores"

engine = create_engine('postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas')
aclient = AsyncOpenAI()

# ── Prompts ──

EVENT_BATCH_PROMPT = """You are a world history expert. Score each event's historical importance (1-100) by evaluating:

1. GLOBAL REACH: Did it affect multiple civilizations/continents? (0-25 pts)
2. LASTING LEGACY: How long did the consequences last? (0-25 pts)
3. SCALE OF IMPACT: How many people were directly affected? (0-25 pts)
4. PARADIGM SHIFT: Did it fundamentally change politics, culture, or thought? (0-25 pts)

Score each event below:

{events_block}

Respond with ONLY a JSON array, one object per event in the same order:
[{{"id": <id>, "score": <1-100>, "reason": "<one sentence>"}}, ...]"""

PERSON_BATCH_PROMPT = """You are a world history expert. Score each person's historical importance (1-100) by evaluating:

1. GLOBAL INFLUENCE: Impact beyond their own region/era? (0-25 pts)
2. LASTING LEGACY: Are they remembered centuries later? (0-25 pts)
3. ACHIEVEMENTS: Scale and significance of their accomplishments? (0-25 pts)
4. PARADIGM SHIFT: Did they fundamentally change their field, culture, or society? (0-25 pts)

Score each person below:

{persons_block}

Respond with ONLY a JSON array, one object per person in the same order:
[{{"id": <id>, "score": <1-100>, "reason": "<one sentence>"}}, ...]"""


# ── Data loading ──

def load_events(limit: int = 0) -> list[dict]:
    """Load events from DB."""
    q = """
        SELECT e.id, e.title, e.date_start, e.date_end,
               LEFT(ed.description, 250) as description
        FROM events e
        LEFT JOIN event_details ed ON ed.event_id = e.id
        WHERE e.wikidata_id IS NOT NULL
        ORDER BY e.id
    """
    if limit > 0:
        q += f" LIMIT {limit}"

    with engine.connect() as conn:
        rows = conn.execute(text(q)).fetchall()

    events = []
    for r in rows:
        date_str = str(r[2])
        if r[3] and r[3] != r[2]:
            date_str += f" to {r[3]}"
        if r[2] and r[2] < 0:
            date_str = f"{abs(r[2])} BCE"
            if r[3] and r[3] != r[2]:
                end_str = f"{abs(r[3])} BCE" if r[3] < 0 else str(r[3])
                date_str += f" to {end_str}"

        events.append({
            "id": r[0],
            "title": r[1],
            "date": date_str,
            "description": r[4] or f"Historical event: {r[1]}",
        })
    return events


def load_persons(limit: int = 0) -> list[dict]:
    """Load persons from DB."""
    q = """
        SELECT p.id, p.name, p.birth_year, p.death_year,
               p.role, LEFT(p.description, 150) as description
        FROM persons p
        WHERE p.wikidata_id IS NOT NULL
        ORDER BY p.id
    """
    if limit > 0:
        q += f" LIMIT {limit}"

    with engine.connect() as conn:
        rows = conn.execute(text(q)).fetchall()

    persons = []
    for r in rows:
        dates = ""
        if r[2]:
            dates = f"{abs(r[2])} {'BCE' if r[2] < 0 else 'CE'}"
        if r[3]:
            dates += f" - {abs(r[3])} {'BCE' if r[3] < 0 else 'CE'}"

        persons.append({
            "id": r[0],
            "name": r[1],
            "dates": dates,
            "role": r[4] or "",
            "description": r[5] or "",
        })
    return persons


# ── Checkpoint ──

def load_checkpoint(filepath: Path) -> set[int]:
    """Load already-scored IDs from JSONL checkpoint."""
    scored_ids = set()
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if "id" in obj:
                        scored_ids.add(obj["id"])
                    elif "ids" in obj:
                        scored_ids.update(obj["ids"])
                except json.JSONDecodeError:
                    continue
    return scored_ids


def append_checkpoint(filepath: Path, data: dict):
    """Append a result to JSONL checkpoint."""
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False) + '\n')


# ── API calls ──

async def score_event_batch(batch: list[dict], semaphore: asyncio.Semaphore) -> list[dict]:
    """Score a batch of 5 events."""
    lines = []
    for i, e in enumerate(batch, 1):
        desc = e["description"][:150] if e["description"] else "No description"
        lines.append(f"{i}. [ID:{e['id']}] {e['title']} ({e['date']}). {desc}")

    events_block = "\n".join(lines)
    prompt = EVENT_BATCH_PROMPT.format(events_block=events_block)

    async with semaphore:
        try:
            response = await aclient.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=4000,
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            results = json.loads(content)

            output = []
            for i, e in enumerate(batch):
                if i < len(results):
                    r = results[i]
                    output.append({
                        "id": e["id"],
                        "title": e["title"],
                        "score": r.get("score", -1),
                        "reason": r.get("reason", ""),
                    })
                else:
                    output.append({
                        "id": e["id"],
                        "title": e["title"],
                        "score": -1,
                        "error": "missing from response",
                    })
            return output
        except Exception as e_err:
            return [
                {"id": e["id"], "title": e["title"], "score": -1, "error": str(e_err)}
                for e in batch
            ]


async def score_person_batch(batch: list[dict], semaphore: asyncio.Semaphore) -> list[dict]:
    """Score a batch of 10 persons."""
    lines = []
    for i, p in enumerate(batch, 1):
        desc = p["description"][:100] if p["description"] else "No description available"
        lines.append(f"{i}. [ID:{p['id']}] {p['name']} ({p['dates']}) - {p['role']}. {desc}")

    persons_block = "\n".join(lines)
    prompt = PERSON_BATCH_PROMPT.format(persons_block=persons_block)

    async with semaphore:
        try:
            response = await aclient.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=4000,  # Larger for batch response
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            results = json.loads(content)

            # Map results back to person IDs
            output = []
            for i, p in enumerate(batch):
                if i < len(results):
                    r = results[i]
                    output.append({
                        "id": p["id"],
                        "name": p["name"],
                        "score": r.get("score", -1),
                        "reason": r.get("reason", ""),
                    })
                else:
                    output.append({
                        "id": p["id"],
                        "name": p["name"],
                        "score": -1,
                        "error": "missing from response",
                    })
            return output
        except Exception as e:
            return [
                {"id": p["id"], "name": p["name"], "score": -1, "error": str(e)}
                for p in batch
            ]


# ── Main runners ──

async def run_events(limit: int = 0):
    """Score all events."""
    checkpoint_path = CHECKPOINT_DIR / "events_scores.jsonl"
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading events from DB...")
    events = load_events(limit)
    print(f"Total events: {len(events)}")

    scored_ids = load_checkpoint(checkpoint_path)
    remaining = [e for e in events if e["id"] not in scored_ids]
    print(f"Already scored: {len(scored_ids)}, remaining: {len(remaining)}")

    if not remaining:
        print("All events already scored!")
        return

    # Create batches of 5 events
    event_batch_size = 5
    batches = [remaining[i:i + event_batch_size] for i in range(0, len(remaining), event_batch_size)]
    print(f"Batches to process: {len(batches)} ({event_batch_size} events each)")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    start_time = time.time()
    completed = 0
    errors = 0

    # Process in chunks of 50 batches for progress
    chunk_size = 50
    for chunk_start in range(0, len(batches), chunk_size):
        chunk = batches[chunk_start:chunk_start + chunk_size]
        tasks = [score_event_batch(batch, semaphore) for batch in chunk]
        batch_results = await asyncio.gather(*tasks)

        for batch_result in batch_results:
            for result in batch_result:
                append_checkpoint(checkpoint_path, result)
                if result.get("score", -1) > 0:
                    completed += 1
                else:
                    errors += 1

        total_batches_done = chunk_start + len(chunk)
        total_events_done = min(total_batches_done * event_batch_size, len(remaining))
        elapsed = time.time() - start_time
        rate = total_events_done / elapsed if elapsed > 0 else 0
        eta = (len(remaining) - total_events_done) / rate if rate > 0 else 0
        print(f"  [{total_events_done}/{len(remaining)}] "
              f"ok={completed} err={errors} "
              f"rate={rate:.1f}/s ETA={eta/60:.0f}min")

    elapsed = time.time() - start_time
    print(f"\nDone! {completed} scored, {errors} errors in {elapsed:.0f}s")
    print(f"Results: {checkpoint_path}")


async def run_persons(limit: int = 0):
    """Score all persons in batches of 10."""
    checkpoint_path = CHECKPOINT_DIR / "persons_scores.jsonl"
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading persons from DB...")
    persons = load_persons(limit)
    print(f"Total persons: {len(persons)}")

    scored_ids = load_checkpoint(checkpoint_path)
    remaining = [p for p in persons if p["id"] not in scored_ids]
    print(f"Already scored: {len(scored_ids)}, remaining: {len(remaining)}")

    if not remaining:
        print("All persons already scored!")
        return

    # Create batches of 10
    batch_size = 10
    batches = [remaining[i:i + batch_size] for i in range(0, len(remaining), batch_size)]
    print(f"Batches to process: {len(batches)} (10 persons each)")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    start_time = time.time()
    completed = 0
    errors = 0

    # Process in chunks of 50 batches for progress
    chunk_size = 50
    for chunk_start in range(0, len(batches), chunk_size):
        chunk = batches[chunk_start:chunk_start + chunk_size]
        tasks = [score_person_batch(batch, semaphore) for batch in chunk]
        batch_results = await asyncio.gather(*tasks)

        for batch_result in batch_results:
            for result in batch_result:
                append_checkpoint(checkpoint_path, result)
                if result.get("score", -1) > 0:
                    completed += 1
                else:
                    errors += 1

        total_batches_done = chunk_start + len(chunk)
        total_persons_done = min(total_batches_done * batch_size, len(remaining))
        elapsed = time.time() - start_time
        rate = total_persons_done / elapsed if elapsed > 0 else 0
        eta = (len(remaining) - total_persons_done) / rate if rate > 0 else 0
        print(f"  [{total_persons_done}/{len(remaining)}] "
              f"ok={completed} err={errors} "
              f"rate={rate:.1f}/s ETA={eta/60:.0f}min")

    elapsed = time.time() - start_time
    print(f"\nDone! {completed} scored, {errors} errors in {elapsed:.0f}s")
    print(f"Results: {checkpoint_path}")


async def main():
    parser = argparse.ArgumentParser(description="Score importance of events/persons")
    parser.add_argument("target", choices=["events", "persons", "all"],
                        help="What to score")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of items (0=all)")
    args = parser.parse_args()

    print(f"Model: {MODEL}")
    print(f"Concurrency: {MAX_CONCURRENT}")
    print(f"Checkpoint dir: {CHECKPOINT_DIR}")
    print()

    if args.target in ("events", "all"):
        await run_events(args.limit)
        print()

    if args.target in ("persons", "all"):
        await run_persons(args.limit)


if __name__ == "__main__":
    asyncio.run(main())
