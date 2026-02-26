"""
Parallel event narrative generation using the same logic as curate_with_llm.py step 1.

Reads the same source cache, uses the same prompts, writes to entity_narratives + event_details.
But runs API calls in parallel (20-50 workers) for ~20x speedup.

Usage:
    cd backend
    python scripts/enrich_event_narratives.py                    # Full run (imp 3+)
    python scripts/enrich_event_narratives.py --test 10          # Test with 10 events
    python scripts/enrich_event_narratives.py --workers 30       # 30 parallel workers
    python scripts/enrich_event_narratives.py --stats            # Show progress
    python scripts/enrich_event_narratives.py --dry-run          # Preview only

After generation, translate with:
    python scripts/translate_narratives.py --lang ko
"""
import argparse
import json
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2.pool import ThreadedConnectionPool

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Load .env
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if env_path.exists():
    for line in env_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            os.environ.setdefault(key.strip(), val.strip())

# --- Config ---
DB_URL = "postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas"
LLM_MODEL = "gpt-5.1-chat-latest"
SOURCE_CACHE_FILE = Path(__file__).resolve().parent.parent.parent / "poc" / "data" / "curation" / "source_cache.jsonl"
CHECKPOINT_DIR = Path(__file__).resolve().parent.parent.parent / "poc" / "data" / "curation"
CHECKPOINT_FILE = CHECKPOINT_DIR / "narratives_checkpoint.jsonl"  # Same as curate_with_llm.py
DEFAULT_WORKERS = 20

# --- Same prompts as curate_with_llm.py ---

SYSTEM_PROMPT = (
    "You are a historical encyclopedia editor writing for an interactive historical atlas. "
    "Write clear, engaging, and factually accurate content in English only. "
    "No Korean, Japanese, Chinese or other non-English languages in any field. "
    "Always respond with valid JSON only."
)


def format_year(year):
    if year is None:
        return "Unknown"
    if year < 0:
        return f"{abs(year)} BCE"
    return f"{year} CE"


def build_prompt_with_source(event):
    persons = event.get("persons", [])
    person_list = ", ".join(
        f"{p['name']} ({p.get('role', '?')})" for p in persons[:5]
    ) if persons else "None listed"

    source_text = event.get("source_text", "")
    if source_text and len(source_text) > 3000:
        source_text = source_text[:2500] + "\n\n[...truncated...]\n\n" + source_text[-500:]

    return f"""# Event: {event['title']} ({format_year(event.get('date_start'))} ~ {format_year(event.get('date_end'))})
# Location: {event.get('location_name') or 'Unknown'}
# Current description: {event.get('description') or 'None'}
# Related persons: {person_list}

## Source Material:
{source_text}

Based on the source material above, generate:
1. narrative: 150-250 word narrative explaining what happened, why it matters, and its historical context
2. significance: One sentence on global historical significance
3. causes: Array of 2-4 causes/preconditions (each 1 sentence)
4. consequences: Array of 2-4 consequences/effects (each 1 sentence)
5. description_enriched: 2-3 sentence enhanced description for the event card

IMPORTANT: Write in English only. No Korean, Japanese, or other languages.

Respond ONLY as valid JSON:
{{"narrative": "...", "significance": "...", "causes": ["..."], "consequences": ["..."], "description_enriched": "..."}}"""


def build_prompt_no_source(event):
    persons = event.get("persons", [])
    person_list = ", ".join(
        f"{p['name']} ({p.get('role', '?')})" for p in persons[:5]
    ) if persons else "None listed"

    return f"""# Event: {event['title']} ({format_year(event.get('date_start'))})
# Description: {event.get('description') or 'None'}
# Related persons: {person_list}

Using your historical knowledge, generate a brief narrative about this event.

Respond ONLY as valid JSON:
{{"narrative": "...", "significance": "...", "causes": ["..."], "consequences": ["..."]}}"""


# --- OpenAI ---

def get_openai_client():
    from openai import OpenAI
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found")
    return OpenAI(api_key=api_key)


def llm_call(client, event):
    """Call LLM for one event. Thread-safe (no shared state)."""
    eid = event["event_id"]
    has_source = bool(event.get("source_text"))

    if has_source:
        prompt = build_prompt_with_source(event)
        max_tokens = 2000
    else:
        prompt = build_prompt_no_source(event)
        max_tokens = 1500

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        result = json.loads(content)
        usage = response.usage
        return eid, result, usage
    except Exception as e:
        return eid, None, str(e)


# --- Checkpoint ---

def load_checkpoint():
    done = set()
    if CHECKPOINT_FILE.exists():
        for line in CHECKPOINT_FILE.read_text(encoding='utf-8').splitlines():
            if line.strip():
                try:
                    entry = json.loads(line)
                    key = entry.get("_key", "")
                    if key:
                        done.add(key)
                    # Also extract event_id for dedup
                    eid = entry.get("event_id")
                    if eid:
                        done.add(f"eid:{eid}")
                except json.JSONDecodeError:
                    pass
    return done


checkpoint_lock = threading.Lock()

def save_checkpoint(entry):
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    with checkpoint_lock:
        with open(CHECKPOINT_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# --- DB Write ---

def save_to_db(db_pool, eid, result, source_url):
    """Write narrative to entity_narratives + event_details. Thread-safe via pool."""
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()

        # Insert into entity_narratives
        cur.execute("""
            INSERT INTO entity_narratives
                (entity_type, entity_id, narrative, significance, causes, consequences,
                 model_used, source_url, curated_status, generated_at, created_at, updated_at)
            VALUES ('event', %s, %s, %s, %s, %s, %s, %s, 'auto', NOW(), NOW(), NOW())
            ON CONFLICT DO NOTHING
        """, (
            eid,
            result.get("narrative"),
            result.get("significance"),
            result.get("causes"),
            result.get("consequences"),
            LLM_MODEL,
            source_url,
        ))

        # Update event_details.description if enriched
        enriched = result.get("description_enriched")
        if enriched:
            cur.execute("""
                UPDATE event_details
                SET description = CASE WHEN description IS NULL OR LENGTH(description) < %s
                                       THEN %s ELSE description END,
                    updated_at = NOW()
                WHERE event_id = %s
            """, (len(enriched), enriched, eid))

        conn.commit()
        cur.close()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        db_pool.putconn(conn)


# --- Stats ---

class Stats:
    def __init__(self):
        self.lock = threading.Lock()
        self.success = 0
        self.errors = 0
        self.total_input = 0
        self.total_output = 0


def show_stats():
    done = load_checkpoint()
    event_ids = {k.split(":")[1] for k in done if k.startswith("eid:")}
    print(f"=== Checkpoint Stats ===")
    print(f"Entries: {len(done)}")
    print(f"Unique events: {len(event_ids)}")
    print(f"File: {CHECKPOINT_FILE}")

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    for label, min_s, max_s in [("imp 5 (90+)", 90, 999), ("imp 4 (70-89)", 70, 89), ("imp 3 (50-69)", 50, 69)]:
        cur.execute("""
            SELECT COUNT(*) FROM events WHERE importance_score >= %s AND importance_score <= %s
        """, (min_s, max_s))
        total = cur.fetchone()[0]
        cur.execute("""
            SELECT COUNT(*) FROM entity_narratives en
            JOIN events e ON e.id = en.entity_id AND en.entity_type = 'event'
            WHERE e.importance_score >= %s AND e.importance_score <= %s
              AND en.narrative IS NOT NULL
        """, (min_s, max_s))
        has = cur.fetchone()[0]
        cur.execute("""
            SELECT COUNT(*) FROM entity_narratives en
            JOIN events e ON e.id = en.entity_id AND en.entity_type = 'event'
            WHERE e.importance_score >= %s AND e.importance_score <= %s
              AND en.narrative_ko IS NOT NULL
        """, (min_s, max_s))
        has_ko = cur.fetchone()[0]
        pct = f"{has/total*100:.0f}%" if total else "0%"
        print(f"  {label}: {has}/{total} ({pct}) narratives, {has_ko} KO")
    cur.close()
    conn.close()


# --- Main ---

def run(args):
    # Load source cache
    if not SOURCE_CACHE_FILE.exists():
        print(f"[ERROR] Source cache not found: {SOURCE_CACHE_FILE}")
        print("Run: cd backend && python ../poc/scripts/curate_with_llm.py --step 0")
        return

    all_events = []
    for line in SOURCE_CACHE_FILE.read_text(encoding='utf-8').splitlines():
        if line.strip():
            all_events.append(json.loads(line))

    print(f"Source cache: {len(all_events)} events")

    # Filter: importance_score >= 50 (imp 3+)
    events = [e for e in all_events if (e.get("importance_score") or 0) >= 50]
    print(f"Filtered (score >= 50): {len(events)}")

    # Skip existing in DB
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT entity_id FROM entity_narratives WHERE entity_type = 'event'")
    existing_ids = {row[0] for row in cur.fetchall()}
    cur.close()
    conn.close()

    events = [e for e in events if e["event_id"] not in existing_ids]
    print(f"After skipping DB existing: {len(events)} (skipped {len(existing_ids)})")

    # Skip checkpoint
    done = load_checkpoint()
    events = [e for e in events if f"eid:{e['event_id']}" not in done]
    print(f"After checkpoint filter: {len(events)}")

    if args.test:
        events = events[:args.test]
        print(f"[TEST] Limited to {len(events)}")

    if not events:
        print("Nothing to do!")
        return

    has_source = sum(1 for e in events if e.get("source_text"))
    print(f"With source text: {has_source}/{len(events)}")
    print(f"Workers: {args.workers}")
    print(f"Model: {LLM_MODEL}")
    print()

    if args.dry_run:
        est_cost = len(events) * 0.007  # ~$0.007 per event avg
        print(f"[DRY RUN] Would process {len(events)} events")
        print(f"Estimated cost: ~${est_cost:.2f}")
        return

    # Setup
    client = get_openai_client()
    db_pool = ThreadedConnectionPool(2, args.workers + 2, DB_URL)
    stats = Stats()
    start_time = time.time()
    total = len(events)

    def process_one(event):
        eid, result, usage = llm_call(client, event)

        if result and result.get("narrative"):
            # Save to DB
            save_to_db(db_pool, eid, result, event.get("source_url"))

            # Save checkpoint
            save_checkpoint({
                "_key": f"narrative:parallel:{eid}",
                "event_id": eid,
                "title": event.get("title", "?"),
                "narrative_len": len(result.get("narrative", "")),
                "has_enriched_desc": bool(result.get("description_enriched")),
                "timestamp": datetime.now().isoformat(),
            })

            return eid, event.get("title", "?"), usage, True
        else:
            return eid, event.get("title", "?"), usage, False

    # Process in parallel
    print(f"Starting {total} events with {args.workers} workers...")
    print()

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_one, e): e for e in events}

        for future in as_completed(futures):
            try:
                eid, title, usage, ok = future.result()

                with stats.lock:
                    if ok:
                        stats.success += 1
                        if hasattr(usage, 'prompt_tokens'):
                            stats.total_input += usage.prompt_tokens
                            stats.total_output += usage.completion_tokens
                    else:
                        stats.errors += 1
                    done_count = stats.success + stats.errors

                # Print progress every 10 or first few
                if done_count <= 5 or done_count % 10 == 0 or done_count == total:
                    elapsed = time.time() - start_time
                    rate = done_count / elapsed if elapsed > 0 else 0
                    eta = (total - done_count) / rate if rate > 0 else 0
                    cost = (stats.total_input * 2.0 + stats.total_output * 8.0) / 1_000_000
                    status = "OK" if ok else "FAIL"
                    print(f"  [{done_count}/{total}] #{eid} {title[:35]} [{status}] "
                          f"| {rate:.1f}/s | ETA {eta/60:.1f}min | ${cost:.2f}")

            except Exception as e:
                with stats.lock:
                    stats.errors += 1
                err_msg = str(e)[:80]
                print(f"  [ERROR] {err_msg}")

    # Final report
    elapsed = time.time() - start_time
    cost = (stats.total_input * 2.0 + stats.total_output * 8.0) / 1_000_000
    print(f"\n{'=' * 60}")
    print(f"DONE!")
    print(f"  Success: {stats.success} | Errors: {stats.errors}")
    print(f"  Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"  Tokens: {stats.total_input:,} in + {stats.total_output:,} out")
    print(f"  Cost: ${cost:.2f}")
    print(f"\nNext: python scripts/translate_narratives.py --lang ko")

    db_pool.closeall()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parallel event narrative generation")
    parser.add_argument("--test", type=int, help="Process only N events")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help=f"Parallel workers (default: {DEFAULT_WORKERS})")
    parser.add_argument("--stats", action="store_true", help="Show progress stats")
    parser.add_argument("--dry-run", action="store_true", help="Preview without API calls")
    args = parser.parse_args()

    if args.stats:
        show_stats()
    else:
        run(args)
