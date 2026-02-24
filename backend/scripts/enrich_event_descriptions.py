"""
Enrich events with descriptions and translations (KO/JA).

Reads source texts (Wikipedia, Wikisource, etc.) linked to each event,
feeds them to GPT-5-mini to generate:
  1. English description (if missing or too short)
  2. Korean title + description
  3. Japanese title + description

Also maps missing coordinates via wikidata_id.

Usage:
    cd backend
    python scripts/enrich_event_descriptions.py                    # Full run (imp 4+)
    python scripts/enrich_event_descriptions.py --min-importance 3  # Include imp 3
    python scripts/enrich_event_descriptions.py --translate-only    # Only KO/JA for existing descriptions
    python scripts/enrich_event_descriptions.py --coords-only      # Only fix missing coordinates
    python scripts/enrich_event_descriptions.py --test 5            # Test with 5 events
    python scripts/enrich_event_descriptions.py --resume            # Resume from checkpoint
    python scripts/enrich_event_descriptions.py --stats             # Show progress stats
    python scripts/enrich_event_descriptions.py --dry-run           # Preview without writing

Output: data/compact_export/event_enrichment.jsonl (checkpoint)
"""
import argparse
import json
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.session import SessionLocal

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# --- Config ---
CHECKPOINT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "compact_export"
CHECKPOINT_FILE = CHECKPOINT_DIR / "event_enrichment.jsonl"
LLM_MODEL = "gpt-5-mini"  # Fast + cheap for descriptions
MAX_SOURCE_CHARS = 6000  # Max source text to feed per event
BATCH_SIZE = 500  # Concurrent API calls per wave
RATE_LIMIT_DELAY = 1.0  # Seconds between waves


def get_openai_client():
    from openai import OpenAI
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding='utf-8').splitlines():
                if line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in env or .env file")
    return OpenAI(api_key=api_key)


def format_year(year):
    if year is None:
        return "unknown date"
    if year < 0:
        return f"{abs(year)} BCE"
    return f"{year} CE"


# --- Data Loading ---

def get_events_needing_work(db, min_importance=4, translate_only=False):
    """Get events that need description generation or translation."""
    if translate_only:
        # Events with English description but missing KO or JA
        rows = db.execute(text("""
            SELECT e.id, e.title, e.title_ko, e.title_ja,
                   e.date_start, e.date_end, e.importance,
                   ed.description, ed.description_ko, ed.description_ja,
                   l.name as location_name, l.name_ko as location_name_ko,
                   e.wikidata_id
            FROM events e
            LEFT JOIN event_details ed ON ed.event_id = e.id
            LEFT JOIN locations l ON e.primary_location_id = l.id
            WHERE e.importance >= :min_imp
              AND ed.description IS NOT NULL
              AND LENGTH(ed.description) > 50
              AND (ed.description_ko IS NULL OR e.title_ja IS NULL OR e.title_ja = '')
            ORDER BY e.importance DESC, e.id
        """), {"min_imp": min_importance}).fetchall()
    else:
        # Events needing description OR translation
        rows = db.execute(text("""
            SELECT e.id, e.title, e.title_ko, e.title_ja,
                   e.date_start, e.date_end, e.importance,
                   ed.description, ed.description_ko, ed.description_ja,
                   l.name as location_name, l.name_ko as location_name_ko,
                   e.wikidata_id
            FROM events e
            LEFT JOIN event_details ed ON ed.event_id = e.id
            LEFT JOIN locations l ON e.primary_location_id = l.id
            WHERE e.importance >= :min_imp
              AND (
                ed.description IS NULL
                OR LENGTH(ed.description) <= 50
                OR ed.description_ko IS NULL
                OR e.title_ko IS NULL OR e.title_ko = ''
                OR e.title_ja IS NULL OR e.title_ja = ''
              )
            ORDER BY e.importance DESC, e.id
        """), {"min_imp": min_importance}).fetchall()

    events = []
    for r in rows:
        events.append({
            "id": r[0], "title": r[1], "title_ko": r[2], "title_ja": r[3],
            "date_start": r[4], "date_end": r[5], "importance": r[6],
            "description": r[7], "description_ko": r[8], "description_ja": r[9],
            "location_name": r[10], "location_name_ko": r[11],
            "wikidata_id": r[12],
        })
    return events


def get_source_texts(db, event_id):
    """Get source texts linked to an event, prioritizing quality."""
    rows = db.execute(text("""
        SELECT s.source_type, s.title, s.author, s.content_raw, s.word_count
        FROM event_sources es
        JOIN sources s ON s.id = es.source_id
        WHERE es.event_id = :eid
          AND s.content_raw IS NOT NULL
          AND LENGTH(s.content_raw) > 100
        ORDER BY
          CASE s.source_type
            WHEN 'wikisource' THEN 1
            WHEN 'internet_archive' THEN 2
            WHEN 'wikipedia' THEN 3
            ELSE 4
          END,
          s.word_count DESC
        LIMIT 5
    """), {"eid": event_id}).fetchall()

    texts = []
    total_chars = 0
    for r in rows:
        source_type, title, author, content, word_count = r
        remaining = MAX_SOURCE_CHARS - total_chars
        if remaining <= 200:
            break
        snippet = content[:remaining] if content else ""
        header = f"[{source_type}] {title}"
        if author:
            header += f" by {author}"
        texts.append(f"{header}\n{snippet}")
        total_chars += len(snippet)

    return "\n\n---\n\n".join(texts) if texts else None


def get_events_needing_coords(db, min_importance=3):
    """Events with wikidata_id but no location."""
    rows = db.execute(text("""
        SELECT e.id, e.title, e.wikidata_id
        FROM events e
        WHERE e.importance >= :min_imp
          AND e.primary_location_id IS NULL
          AND e.wikidata_id IS NOT NULL
          AND e.wikidata_id != ''
        ORDER BY e.importance DESC
    """), {"min_imp": min_importance}).fetchall()
    return [{"id": r[0], "title": r[1], "wikidata_id": r[2]} for r in rows]


# --- LLM Calls ---

DESCRIPTION_PROMPT = """You are a historical encyclopedia writer. Based on the source texts below, write a concise but informative description of this historical event.

Event: {title}
Date: {date}
Location: {location}

Source texts:
{sources}

Requirements:
1. Write a factual description in English (2-4 sentences, ~80-150 words)
2. Translate the event title to Korean (한국어) and Japanese (日本語)
3. Translate the description to Korean and Japanese
4. Use proper historical terminology in each language

Respond in JSON format:
{{
  "description_en": "...",
  "title_ko": "...",
  "title_ja": "...",
  "description_ko": "...",
  "description_ja": "..."
}}"""

TRANSLATE_PROMPT = """Translate this historical event information to Korean (한국어) and Japanese (日本語).

Event title (English): {title}
Description (English): {description}
Date: {date}
Location: {location}

Requirements:
- Use proper historical terminology and names in each language
- Korean: Use standard Korean historical naming conventions
- Japanese: Use standard Japanese historical naming conventions (kanji where appropriate)

Respond in JSON format:
{{
  "title_ko": "...",
  "title_ja": "...",
  "description_ko": "...",
  "description_ja": "..."
}}"""

NO_SOURCE_PROMPT = """You are a historical encyclopedia writer. Write a concise factual description of this historical event based on your knowledge.

Event: {title}
Date: {date}
Location: {location}
Wikidata ID: {wikidata_id}

Requirements:
1. Write a factual description in English (2-4 sentences, ~80-150 words)
2. Only include well-established historical facts
3. Translate the event title to Korean (한국어) and Japanese (日本語)
4. Translate the description to Korean and Japanese

Respond in JSON format:
{{
  "description_en": "...",
  "title_ko": "...",
  "title_ja": "...",
  "description_ko": "...",
  "description_ja": "..."
}}"""


def call_llm(client, prompt, event_id):
    """Call LLM and parse JSON response."""
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_completion_tokens=4096,
        )
        content = response.choices[0].message.content
        if not content:
            print(f"  [DEBUG] Event {event_id}: Empty content. Finish reason: {response.choices[0].finish_reason}")
            print(f"  [DEBUG] Usage: {response.usage}")
            return None
        result = json.loads(content)
        result["_event_id"] = event_id
        result["_tokens"] = {
            "input": response.usage.prompt_tokens,
            "output": response.usage.completion_tokens,
        }
        return result
    except Exception as e:
        print(f"  [ERROR] Event {event_id}: {e}")
        return None


# --- Checkpoint ---

def load_checkpoint():
    """Load completed event IDs from checkpoint file."""
    done = set()
    if CHECKPOINT_FILE.exists():
        for line in CHECKPOINT_FILE.read_text(encoding='utf-8').splitlines():
            if line.strip():
                try:
                    data = json.loads(line)
                    done.add(data.get("_event_id") or data.get("id"))
                except json.JSONDecodeError:
                    pass
    return done


def save_checkpoint(result):
    """Append result to checkpoint file."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")


def apply_to_db(db, result, event, dry_run=False):
    """Apply enrichment result to database."""
    event_id = event["id"]

    desc_en = result.get("description_en")
    desc_ko = result.get("description_ko")
    desc_ja = result.get("description_ja")
    title_ko = result.get("title_ko")
    title_ja = result.get("title_ja")

    if dry_run:
        print(f"  [DRY] Event {event_id}: {event['title']}")
        if desc_en:
            print(f"    EN: {desc_en[:80]}...")
        if title_ko:
            print(f"    KO: {title_ko}")
        if title_ja:
            print(f"    JA: {title_ja}")
        return

    # Update event titles
    updates = []
    params = {"eid": event_id}
    if title_ko and (not event.get("title_ko")):
        updates.append("title_ko = :title_ko")
        params["title_ko"] = title_ko
    if title_ja and (not event.get("title_ja")):
        updates.append("title_ja = :title_ja")
        params["title_ja"] = title_ja

    if updates:
        db.execute(text(f"UPDATE events SET {', '.join(updates)} WHERE id = :eid"), params)

    # Update event_details (description)
    existing_desc = event.get("description")
    has_good_desc = existing_desc and len(existing_desc) > 50

    if has_good_desc:
        # Only add translations
        detail_updates = []
        detail_params = {"eid": event_id}
        if desc_ko and not event.get("description_ko"):
            detail_updates.append("description_ko = :desc_ko")
            detail_params["desc_ko"] = desc_ko
        if desc_ja and not event.get("description_ja"):
            detail_updates.append("description_ja = :desc_ja")
            detail_params["desc_ja"] = desc_ja
        if detail_updates:
            db.execute(text(
                f"UPDATE event_details SET {', '.join(detail_updates)} WHERE event_id = :eid"
            ), detail_params)
    elif desc_en:
        # Check if event_details row exists
        exists = db.execute(text(
            "SELECT 1 FROM event_details WHERE event_id = :eid"
        ), {"eid": event_id}).fetchone()

        if exists:
            db.execute(text("""
                UPDATE event_details
                SET description = :desc_en, description_ko = :desc_ko, description_ja = :desc_ja
                WHERE event_id = :eid
            """), {"eid": event_id, "desc_en": desc_en, "desc_ko": desc_ko, "desc_ja": desc_ja})
        else:
            db.execute(text("""
                INSERT INTO event_details (event_id, description, description_ko, description_ja)
                VALUES (:eid, :desc_en, :desc_ko, :desc_ja)
            """), {"eid": event_id, "desc_en": desc_en, "desc_ko": desc_ko, "desc_ja": desc_ja})

    db.commit()


# --- Main ---

def build_prompt(event, db, translate_only=False):
    """Build the LLM prompt for an event (called from main thread for DB access)."""
    has_good_desc = event.get("description") and len(event["description"]) > 50

    if has_good_desc:
        return TRANSLATE_PROMPT.format(
            title=event["title"],
            description=event["description"][:500],
            date=format_year(event["date_start"]),
            location=event.get("location_name") or "unknown",
        )
    else:
        source_text = get_source_texts(db, event["id"])
        if source_text:
            return DESCRIPTION_PROMPT.format(
                title=event["title"],
                date=format_year(event["date_start"]),
                location=event.get("location_name") or "unknown",
                sources=source_text,
            )
        else:
            return NO_SOURCE_PROMPT.format(
                title=event["title"],
                date=format_year(event["date_start"]),
                location=event.get("location_name") or "unknown",
                wikidata_id=event.get("wikidata_id") or "N/A",
            )


def run_enrichment(args):
    client = get_openai_client()
    db = SessionLocal()

    if args.stats:
        done = load_checkpoint()
        print(f"Checkpoint: {len(done)} events completed")
        print(f"File: {CHECKPOINT_FILE}")
        return

    print(f"=== Event Description Enrichment ===")
    print(f"Model: {LLM_MODEL}")
    print(f"Min importance: {args.min_importance}")
    print(f"Concurrency: {BATCH_SIZE}")
    print()

    # Load events
    events = get_events_needing_work(db, args.min_importance, args.translate_only)
    print(f"Found {len(events)} events needing work")

    if args.test:
        events = events[:args.test]
        print(f"Test mode: processing {len(events)} events")

    # Load checkpoint
    done = load_checkpoint()
    events = [e for e in events if e["id"] not in done]
    print(f"After checkpoint filter: {len(events)} remaining")
    print()

    if not events:
        print("Nothing to do!")
        return

    total_input_tokens = 0
    total_output_tokens = 0
    processed = 0
    errors = 0
    start_time = time.time()
    checkpoint_lock = threading.Lock()

    for wave_start in range(0, len(events), BATCH_SIZE):
        wave = events[wave_start:wave_start + BATCH_SIZE]
        wave_num = wave_start // BATCH_SIZE + 1
        total_waves = (len(events) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"\n=== Wave {wave_num}/{total_waves} ({len(wave)} events) ===")

        # Step 1: Build all prompts (main thread, needs DB)
        print(f"  Preparing prompts...")
        prompt_pairs = []  # [(event, prompt), ...]
        for event in wave:
            prompt = build_prompt(event, db, args.translate_only)
            prompt_pairs.append((event, prompt))

        # Step 2: Fire all LLM calls in parallel
        print(f"  Firing {len(prompt_pairs)} parallel API calls...")
        wave_results = []

        def process_one(event_prompt_pair):
            ev, pr = event_prompt_pair
            return (ev, call_llm(client, pr, ev["id"]))

        with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
            futures = {
                executor.submit(process_one, pp): pp[0]["id"]
                for pp in prompt_pairs
            }
            for future in as_completed(futures):
                event, result = future.result()
                wave_results.append((event, result))

        # Step 3: Apply results to DB (main thread)
        wave_ok = 0
        wave_err = 0
        for event, result in wave_results:
            if result:
                tokens = result.get("_tokens", {})
                total_input_tokens += tokens.get("input", 0)
                total_output_tokens += tokens.get("output", 0)

                save_checkpoint(result)
                apply_to_db(db, result, event, dry_run=args.dry_run)

                processed += 1
                wave_ok += 1
                title_ko = result.get("title_ko", "")
                print(f"  [{processed}/{len(events)}] #{event['id']} {event['title'][:40]} -> {title_ko}")
            else:
                errors += 1
                wave_err += 1

        # Wave summary
        elapsed = time.time() - start_time
        rate = processed / elapsed if elapsed > 0 else 0
        eta = (len(events) - processed) / rate if rate > 0 else 0
        cost = (total_input_tokens * 0.4 + total_output_tokens * 1.6) / 1_000_000
        print(f"  Wave done: {wave_ok} ok, {wave_err} err | Total: {processed}/{len(events)} ({processed/len(events)*100:.1f}%)")
        print(f"  Rate: {rate:.1f}/s | ETA: {eta/60:.1f}min | Cost: ${cost:.2f}")

        # Brief pause between waves
        if wave_start + BATCH_SIZE < len(events):
            time.sleep(RATE_LIMIT_DELAY)

    # Final report
    elapsed = time.time() - start_time
    cost = (total_input_tokens * 0.4 + total_output_tokens * 1.6) / 1_000_000
    print(f"\n=== Done ===")
    print(f"Processed: {processed} | Errors: {errors}")
    print(f"Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"Tokens: {total_input_tokens:,} in + {total_output_tokens:,} out")
    print(f"Est. cost: ${cost:.3f}")

    db.close()


def run_coords(args):
    """Fix missing coordinates using wikidata_id."""
    import requests

    db = SessionLocal()
    events = get_events_needing_coords(db, args.min_importance)
    print(f"Found {len(events)} events needing coordinates")

    if args.test:
        events = events[:args.test]

    fixed = 0
    for event in events:
        qid = event["wikidata_id"]
        if not qid or not qid.startswith("Q"):
            continue

        try:
            url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
            resp = requests.get(url, timeout=10)
            data = resp.json()
            entity = data.get("entities", {}).get(qid, {})
            claims = entity.get("claims", {})

            # P625 = coordinate location
            coords = claims.get("P625", [])
            if coords:
                val = coords[0].get("mainclaim", {}).get("datavalue", {}).get("value", {})
                if not val:
                    val = coords[0].get("mainsnak", {}).get("datavalue", {}).get("value", {})
                lat = val.get("latitude")
                lng = val.get("longitude")

                if lat and lng:
                    # Find or create location
                    loc = db.execute(text(
                        "SELECT id FROM locations WHERE ABS(latitude - :lat) < 0.01 AND ABS(longitude - :lng) < 0.01 LIMIT 1"
                    ), {"lat": lat, "lng": lng}).fetchone()

                    if loc:
                        db.execute(text(
                            "UPDATE events SET primary_location_id = :lid WHERE id = :eid"
                        ), {"lid": loc[0], "eid": event["id"]})
                    else:
                        # Create new location
                        result = db.execute(text("""
                            INSERT INTO locations (name, latitude, longitude, location_type, wikidata_id)
                            VALUES (:name, :lat, :lng, 'event_location', :qid)
                            RETURNING id
                        """), {"name": event["title"][:100], "lat": lat, "lng": lng, "qid": qid})
                        new_loc_id = result.fetchone()[0]
                        db.execute(text(
                            "UPDATE events SET primary_location_id = :lid WHERE id = :eid"
                        ), {"lid": new_loc_id, "eid": event["id"]})

                    db.commit()
                    fixed += 1
                    print(f"  [{fixed}] #{event['id']} {event['title'][:50]} -> ({lat:.2f}, {lng:.2f})")

            time.sleep(0.5)  # Wikidata rate limit
        except Exception as e:
            print(f"  [ERROR] {event['id']}: {e}")

    print(f"\nFixed coordinates: {fixed}/{len(events)}")
    db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich event descriptions + translations")
    parser.add_argument("--min-importance", type=int, default=4, help="Minimum importance (default: 4)")
    parser.add_argument("--translate-only", action="store_true", help="Only translate existing descriptions")
    parser.add_argument("--coords-only", action="store_true", help="Only fix missing coordinates")
    parser.add_argument("--test", type=int, help="Process only N events (test mode)")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--stats", action="store_true", help="Show checkpoint stats")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    args = parser.parse_args()

    if args.coords_only:
        run_coords(args)
    else:
        run_enrichment(args)
