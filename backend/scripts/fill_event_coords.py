"""
Fill missing coordinates for imp 3+ events using LLM location extraction.

Strategy:
1. LLM extracts primary location (name + lat/lng) from event title + description
2. Match extracted location against existing locations table (within 0.5 degrees)
3. If no match, create new location entry
4. Link event to location

Uses GPT-5-mini (cheap: ~$0.03 total for 1,237 events)
"""

import sys
import os
import json
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load .env
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(env_path)

from openai import OpenAI
from app.db.session import engine
import psycopg2
from psycopg2.pool import ThreadedConnectionPool

# --- Config ---
LLM_MODEL = "gpt-5-mini"  # overridable with --model
DEFAULT_WORKERS = 15
CHECKPOINT_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'compact_export', 'coords_checkpoint.jsonl')

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

LOCATION_PROMPT = """Given this historical event, identify the PRIMARY geographic location where it took place.

Event: {title}
Description: {description}

Return a JSON object with:
- "location_name": the most specific place name (city, region, or country)
- "latitude": approximate latitude (decimal degrees)
- "longitude": approximate longitude (decimal degrees)
- "confidence": "high" if location is clearly identifiable, "medium" if approximate, "low" if very uncertain
- "reasoning": brief explanation (1 sentence)

For events spanning large areas (wars, empires, eras), pick the most representative single location (e.g., capital city, key battlefield, center of activity).
For global/abstract events with no clear location, use latitude 0, longitude 0 and confidence "none".

Return ONLY the JSON object, no markdown."""

# --- DB Setup ---
def get_db_url():
    url = str(engine.url)
    # Convert SQLAlchemy URL to psycopg2 format
    return url.replace('postgresql+psycopg2://', 'postgresql://').replace('postgresql://', 'postgresql://')

def get_events_needing_coords(conn, min_importance=3):
    """Get events without coordinates."""
    cur = conn.cursor()
    cur.execute("""
        SELECT e.id, e.title, ed.description, e.importance
        FROM events e
        LEFT JOIN event_details ed ON ed.event_id = e.id
        WHERE e.importance >= %s
          AND e.primary_location_id IS NULL
        ORDER BY e.importance DESC
    """, (min_importance,))
    rows = cur.fetchall()
    cur.close()
    return [{"id": r[0], "title": r[1], "description": r[2] or "", "importance": r[3]} for r in rows]

def extract_location_llm(event, model=None):
    """Use LLM to extract location from event."""
    use_model = model or LLM_MODEL
    desc = (event["description"] or "")[:800]

    # For gpt-5.1-chat, use simpler prompt (no response_format support needed)
    if "5.1" in use_model:
        prompt = (
            'What is the single most representative geographic location for this historical event/concept? '
            'Reply with ONLY a JSON: {"name":"City, Country","lat":12.34,"lng":56.78,"confidence":"high"} '
            'or {"name":"none","lat":0,"lng":0,"confidence":"none"} if no specific location.\n\n'
            f'Event: {event["title"]}\nBrief: {desc[:400]}'
        )
        extra_kwargs = {}
    else:
        prompt = LOCATION_PROMPT.format(title=event["title"], description=desc)
        extra_kwargs = {"response_format": {"type": "json_object"}}

    for attempt in range(2):
        try:
            resp = client.chat.completions.create(
                model=use_model,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=500,
                **extra_kwargs
            )
            content = resp.choices[0].message.content
            tokens_in = resp.usage.prompt_tokens
            tokens_out = resp.usage.completion_tokens
            if not content or not content.strip():
                if attempt == 0:
                    time.sleep(0.5)
                    continue
                print(f"  [LLM EMPTY] #{event['id']}: empty response")
                return None, tokens_in, tokens_out
            # Parse JSON from response (handle markdown code blocks and malformed numbers)
            import re as _re
            text_clean = content.strip()
            if text_clean.startswith("```"):
                text_clean = text_clean.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            # Fix malformed JSON: numbers like 39.774" → 39.774
            text_clean = _re.sub(r'(\d+\.\d+)"([,}])', r'\1\2', text_clean)
            result = json.loads(text_clean)
            return result, tokens_in, tokens_out
        except json.JSONDecodeError as e:
            print(f"  [JSON ERROR] #{event['id']}: {e} | raw={content[:100] if content else '(empty)'}")
            return None, 0, 0
        except Exception as e:
            if attempt == 0 and "max_tokens" in str(e).lower():
                time.sleep(0.5)
                continue
            print(f"  [LLM ERROR] #{event['id']}: {e}")
            return None, 0, 0
    return None, 0, 0

def find_nearby_location(cur, lat, lng, threshold=0.5):
    """Find existing location within threshold degrees."""
    cur.execute("""
        SELECT id, name, latitude, longitude
        FROM locations
        WHERE ABS(latitude - %s) < %s AND ABS(longitude - %s) < %s
          AND latitude IS NOT NULL
        ORDER BY ABS(latitude - %s) + ABS(longitude - %s)
        LIMIT 1
    """, (lat, threshold, lng, threshold, lat, lng))
    return cur.fetchone()

def create_location(cur, name, lat, lng):
    """Create a new location entry."""
    cur.execute("""
        INSERT INTO locations (name, latitude, longitude, location_type)
        VALUES (%s, %s, %s, 'event_location')
        RETURNING id
    """, (name[:200], lat, lng))
    return cur.fetchone()[0]

def link_event_to_location(cur, event_id, location_id):
    """Set event's primary_location_id."""
    cur.execute("""
        UPDATE events SET primary_location_id = %s WHERE id = %s
    """, (location_id, event_id))


# --- Main ---
def process_event(event, db_pool, stats, lock, checkpoint_set, model=None):
    """Process a single event: extract location via LLM, match/create in DB."""
    eid = event["id"]

    if eid in checkpoint_set:
        with lock:
            stats["skipped"] += 1
        return

    result, tokens_in, tokens_out = extract_location_llm(event, model=model)

    if not result:
        with lock:
            stats["errors"] += 1
        return

    with lock:
        stats["total_input"] += tokens_in
        stats["total_output"] += tokens_out

    confidence = result.get("confidence", "none")
    lat = result.get("latitude") or result.get("lat")
    lng = result.get("longitude") or result.get("lng")
    loc_name = result.get("location_name") or result.get("name") or ""

    # Skip if no location or confidence is none
    if confidence == "none" or lat is None or lng is None:
        with lock:
            stats["no_location"] += 1
            # Save to checkpoint as "no_location"
            with open(CHECKPOINT_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"event_id": eid, "status": "no_location", "result": result}, ensure_ascii=False) + '\n')
        return

    # Validate coordinates
    try:
        lat = float(lat)
        lng = float(lng)
    except (ValueError, TypeError):
        with lock:
            stats["errors"] += 1
        return

    if lat == 0 and lng == 0:
        with lock:
            stats["no_location"] += 1
            with open(CHECKPOINT_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"event_id": eid, "status": "no_location", "result": result}, ensure_ascii=False) + '\n')
        return

    # Clamp coordinates
    lat = max(-90, min(90, lat))
    lng = max(-180, min(180, lng))

    # DB operations
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()

        # Try to find nearby existing location
        existing = find_nearby_location(cur, lat, lng, threshold=0.3)

        if existing:
            loc_id = existing[0]
            loc_source = "existing"
        else:
            loc_id = create_location(cur, loc_name, lat, lng)
            loc_source = "new"

        link_event_to_location(cur, eid, loc_id)
        conn.commit()
        cur.close()

        with lock:
            stats["linked"] += 1
            if loc_source == "new":
                stats["new_locs"] += 1
            # Save checkpoint
            with open(CHECKPOINT_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "event_id": eid, "status": "linked",
                    "location_id": loc_id, "source": loc_source,
                    "lat": lat, "lng": lng, "name": loc_name,
                    "confidence": confidence
                }, ensure_ascii=False) + '\n')
    except Exception as e:
        conn.rollback()
        with lock:
            stats["errors"] += 1
            print(f"  [DB ERROR] #{eid}: {e}")
    finally:
        db_pool.putconn(conn)


def main():
    parser = argparse.ArgumentParser(description="Fill missing event coordinates using LLM")
    parser.add_argument("--min-importance", type=int, default=3)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--test", type=int, help="Process only N events")
    parser.add_argument("--dry-run", action="store_true", help="LLM only, no DB writes")
    parser.add_argument("--resume", action="store_true", help="Skip already-processed events")
    parser.add_argument("--model", type=str, default=LLM_MODEL, help="LLM model to use")
    args = parser.parse_args()

    use_model = args.model
    print(f"[MODEL] {use_model}")

    # Load checkpoint
    checkpoint_set = set()
    if args.resume and os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    checkpoint_set.add(rec["event_id"])
                except:
                    pass
        print(f"[RESUME] Loaded {len(checkpoint_set)} checkpoints")

    # DB pool
    db_url = get_db_url()
    db_pool = ThreadedConnectionPool(2, args.workers + 2, db_url)

    # Get events
    conn = db_pool.getconn()
    events = get_events_needing_coords(conn, args.min_importance)
    db_pool.putconn(conn)
    print(f"[INFO] {len(events)} events need coordinates (imp >= {args.min_importance})")

    if args.test:
        events = events[:args.test]
        print(f"[TEST] Processing only {len(events)} events")

    # Estimate cost
    avg_tokens = 300  # ~250 input + 50 output per event
    est_cost = len(events) * avg_tokens * 0.4 / 1_000_000  # GPT-5-mini input pricing
    print(f"[COST] Estimated: ~${est_cost:.2f}")
    print(f"[WORKERS] {args.workers} parallel threads")

    stats = {
        "linked": 0, "new_locs": 0, "no_location": 0,
        "errors": 0, "skipped": 0,
        "total_input": 0, "total_output": 0
    }
    lock = Lock()
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_event, ev, db_pool, stats, lock, checkpoint_set, use_model): ev
            for ev in events
        }

        done_count = 0
        for future in as_completed(futures):
            done_count += 1
            if done_count % 50 == 0 or done_count == len(events):
                elapsed = time.time() - start_time
                rate = done_count / elapsed if elapsed > 0 else 0
                remaining = (len(events) - done_count) / rate if rate > 0 else 0
                cost = (stats["total_input"] * 0.4 + stats["total_output"] * 1.6) / 1_000_000
                print(f"  [{done_count}/{len(events)}] linked={stats['linked']} new={stats['new_locs']} "
                      f"no_loc={stats['no_location']} err={stats['errors']} | "
                      f"{rate:.1f}/s | ETA {remaining/60:.1f}min | ${cost:.3f}")

    elapsed = time.time() - start_time
    cost = (stats["total_input"] * 0.4 + stats["total_output"] * 1.6) / 1_000_000
    print(f"\n{'='*50}")
    print(f"[DONE] {stats['linked']} linked, {stats['new_locs']} new locations created")
    print(f"[SKIP] {stats['no_location']} no location, {stats['errors']} errors, {stats['skipped']} resumed")
    print(f"[TIME] {elapsed:.1f}s ({elapsed/60:.1f}min)")
    print(f"[TOKENS] {stats['total_input']:,} in + {stats['total_output']:,} out")
    print(f"[COST] ${cost:.3f}")

    db_pool.closeall()


if __name__ == "__main__":
    main()
