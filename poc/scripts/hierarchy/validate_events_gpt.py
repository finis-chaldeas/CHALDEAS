"""
Validate events with GPT-5-mini (batch processing).
Much faster than Ollama - processes 10 events per request.
"""
import sys
import os
import json
import time
import argparse
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))

from openai import OpenAI
from sqlalchemy import text
from app.db.session import SessionLocal

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

BATCH_SIZE = 10  # Events per GPT request

BATCH_PROMPT = '''You are validating historical event data. For each event below, determine if it's a REAL historical event or GARBAGE data (generic words, incomplete data, extraction errors).

Events to validate:
{events_list}

Respond with a JSON array. For each event (in order):
{{"id": <event_id>, "is_real": true/false, "confidence": "high"/"medium"/"low"}}

Only output the JSON array, nothing else.'''


def validate_batch_gpt(events: list) -> list:
    """Validate a batch of events with GPT-5-mini."""
    events_text = "\n".join([
        f"{i+1}. [ID:{e['id']}] \"{e['title']}\" (persons:{e['persons']}, locations:{e['locations']})"
        for i, e in enumerate(events)
    ])

    prompt = BATCH_PROMPT.format(events_list=events_text)

    try:
        response = client.chat.completions.create(
            model='gpt-5-mini',
            messages=[{'role': 'user', 'content': prompt}],
            response_format={'type': 'json_object'},
            max_completion_tokens=5000
        )

        content = response.choices[0].message.content
        # Parse response - might be {"results": [...]} or just [...]
        data = json.loads(content)
        if isinstance(data, dict):
            results = data.get('results', data.get('events', []))
        else:
            results = data

        return results
    except Exception as e:
        print(f"GPT Error: {e}", flush=True)
        return []


def validate_events(limit: int = 1000, dry_run: bool = True, quarantine: bool = False):
    """Main validation function."""
    db = SessionLocal()

    try:
        print("=== GPT-5-mini Event Validator (Batch Mode) ===", flush=True)
        print(f"Batch size: {BATCH_SIZE} events per request\n", flush=True)

        # Get events to validate
        events = db.execute(text('''
            SELECT e.id, e.title, e.date_start,
                   (SELECT COUNT(*) FROM event_persons ep WHERE ep.event_id = e.id) as person_count,
                   (SELECT COUNT(*) FROM event_locations el WHERE el.event_id = e.id) as location_count
            FROM events e
            WHERE e.wikidata_id IS NULL
              AND e.wikipedia_url IS NULL
              AND NOT EXISTS (SELECT 1 FROM event_sources es WHERE es.event_id = e.id)
              AND e.parent_status NOT IN ('garbage', 'pending')
            ORDER BY person_count DESC
            LIMIT :limit
        '''), {'limit': limit}).fetchall()

        print(f"Events to validate: {len(events)}\n", flush=True)

        if not events:
            print("Nothing to validate!")
            return

        # Process in batches
        total_real = 0
        total_garbage = 0
        garbage_ids = []
        real_ids = []

        for i in range(0, len(events), BATCH_SIZE):
            batch = events[i:i + BATCH_SIZE]
            batch_data = [
                {'id': e[0], 'title': e[1], 'year': e[2], 'persons': e[3], 'locations': e[4]}
                for e in batch
            ]

            print(f"[{i+1}-{i+len(batch)}/{len(events)}] Processing batch...", end=" ", flush=True)

            start = time.time()
            results = validate_batch_gpt(batch_data)
            elapsed = time.time() - start

            # Match results to events
            batch_real = 0
            batch_garbage = 0

            for j, event in enumerate(batch_data):
                # Find matching result
                result = None
                for r in results:
                    if r.get('id') == event['id']:
                        result = r
                        break

                if not result and j < len(results):
                    result = results[j]  # Fallback to positional

                if result:
                    is_real = result.get('is_real', True)
                    conf = result.get('confidence', 'medium')

                    if is_real:
                        batch_real += 1
                        if conf == 'high':
                            real_ids.append(event['id'])
                    else:
                        batch_garbage += 1
                        if conf == 'high':
                            garbage_ids.append(event['id'])
                else:
                    batch_real += 1  # Default to real if parsing fails

            total_real += batch_real
            total_garbage += batch_garbage

            print(f"REAL:{batch_real} GARBAGE:{batch_garbage} ({elapsed:.1f}s)", flush=True)

            # Rate limit: ~3 requests per second is safe
            time.sleep(0.3)

        print(f"\n=== Summary ===", flush=True)
        print(f"Total REAL: {total_real}", flush=True)
        print(f"Total GARBAGE: {total_garbage}", flush=True)
        print(f"High confidence garbage: {len(garbage_ids)}", flush=True)
        print(f"High confidence real: {len(real_ids)}", flush=True)

        # Apply changes
        if not dry_run:
            if garbage_ids and quarantine:
                print(f"\n=== Quarantining {len(garbage_ids)} garbage events ===", flush=True)
                for eid in garbage_ids:
                    db.execute(text('''
                        UPDATE events SET parent_status = 'garbage'
                        WHERE id = :id
                    '''), {'id': eid})
                print(f"Marked {len(garbage_ids)} events as garbage", flush=True)

            if real_ids:
                print(f"\n=== Marking {len(real_ids)} real events as pending ===", flush=True)
                for eid in real_ids:
                    db.execute(text('''
                        UPDATE events SET parent_status = 'pending'
                        WHERE id = :id AND parent_status = 'unknown'
                    '''), {'id': eid})
                print(f"Marked {len(real_ids)} events as pending", flush=True)

            db.commit()
        else:
            print(f"\n[DRY RUN] No changes made.", flush=True)

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate events with GPT-5-mini")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--apply", action="store_true", help="Apply changes")
    parser.add_argument("--quarantine", action="store_true", help="Quarantine garbage events")

    args = parser.parse_args()
    validate_events(
        limit=args.limit,
        dry_run=not args.apply,
        quarantine=args.quarantine
    )
