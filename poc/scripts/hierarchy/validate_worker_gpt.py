"""
GPT-5-mini validation worker - runs in parallel with other workers.
Each worker handles events where (event_id % num_workers) == worker_id
"""
import sys
import os
import json
import time
import argparse

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))

from openai import OpenAI
from sqlalchemy import text
from app.db.session import SessionLocal

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

BATCH_SIZE = 10


def validate_batch_gpt(events: list) -> list:
    """Validate a batch of events with GPT-5-mini."""
    events_text = "\n".join([
        f"{i+1}. [ID:{e['id']}] \"{e['title']}\" (persons:{e['persons']}, locations:{e['locations']})"
        for i, e in enumerate(events)
    ])

    prompt = f'''Validate these historical events as REAL or GARBAGE (generic/incomplete data).

{events_text}

Return JSON: {{"results": [{{"id": <id>, "is_real": true/false, "confidence": "high"/"medium"/"low"}}]}}'''

    try:
        response = client.chat.completions.create(
            model='gpt-5-mini',
            messages=[{'role': 'user', 'content': prompt}],
            response_format={'type': 'json_object'},
            max_completion_tokens=5000
        )
        data = json.loads(response.choices[0].message.content)
        return data.get('results', [])
    except Exception as e:
        print(f"GPT Error: {e}", flush=True)
        return []


def run_worker(worker_id: int, num_workers: int, limit: int = 5000):
    """Run a single worker processing its share of events."""
    db = SessionLocal()

    try:
        print(f"=== Worker {worker_id}/{num_workers} (GPT-5-mini) ===\n", flush=True)

        # Get events for this worker using modulo
        events = db.execute(text('''
            SELECT e.id, e.title,
                   (SELECT COUNT(*) FROM event_persons ep WHERE ep.event_id = e.id) as person_count,
                   (SELECT COUNT(*) FROM event_locations el WHERE el.event_id = e.id) as location_count
            FROM events e
            WHERE e.wikidata_id IS NULL
              AND e.wikipedia_url IS NULL
              AND NOT EXISTS (SELECT 1 FROM event_sources es WHERE es.event_id = e.id)
              AND e.parent_status NOT IN ('garbage', 'pending')
              AND (e.id % :num_workers) = :worker_id
            ORDER BY person_count DESC
            LIMIT :limit
        '''), {'worker_id': worker_id, 'num_workers': num_workers, 'limit': limit}).fetchall()

        print(f"Events to process: {len(events)}\n", flush=True)

        if not events:
            print("Nothing to process!")
            return

        garbage_ids = []
        real_ids = []
        total_real = 0
        total_garbage = 0

        for i in range(0, len(events), BATCH_SIZE):
            batch = events[i:i + BATCH_SIZE]
            batch_data = [
                {'id': e[0], 'title': e[1], 'persons': e[2], 'locations': e[3]}
                for e in batch
            ]

            print(f"[W{worker_id}] [{i+1}-{i+len(batch)}/{len(events)}]", end=" ", flush=True)

            start = time.time()
            results = validate_batch_gpt(batch_data)
            elapsed = time.time() - start

            batch_real = 0
            batch_garbage = 0

            for j, event in enumerate(batch_data):
                result = None
                for r in results:
                    if r.get('id') == event['id']:
                        result = r
                        break
                if not result and j < len(results):
                    result = results[j]

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
                    batch_real += 1

            total_real += batch_real
            total_garbage += batch_garbage
            print(f"R:{batch_real} G:{batch_garbage} ({elapsed:.1f}s)", flush=True)

            time.sleep(0.3)  # Rate limit

        # Apply changes
        if garbage_ids:
            for eid in garbage_ids:
                db.execute(text('UPDATE events SET parent_status = :status WHERE id = :id'),
                          {'status': 'garbage', 'id': eid})

        if real_ids:
            for eid in real_ids:
                db.execute(text('UPDATE events SET parent_status = :status WHERE id = :id AND parent_status = :old'),
                          {'status': 'pending', 'id': eid, 'old': 'unknown'})

        db.commit()

        print(f"\n=== Worker {worker_id} Complete ===", flush=True)
        print(f"REAL: {total_real}, GARBAGE: {total_garbage}", flush=True)
        print(f"Marked garbage: {len(garbage_ids)}, pending: {len(real_ids)}", flush=True)

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", type=int, required=True, help="Worker ID (0-based)")
    parser.add_argument("--total", type=int, required=True, help="Total number of workers")
    parser.add_argument("--limit", type=int, default=5000, help="Max events per worker")
    args = parser.parse_args()

    run_worker(args.worker, args.total, args.limit)
