"""
LLM-based event classification - assigns pending events to parent events.
Uses person/location context, not title similarity.
"""
import sys
import os
import json
import time

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))

import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

from openai import OpenAI
from sqlalchemy import text
from app.db.session import SessionLocal


def get_event_context(db, event_id):
    """Get persons and locations for an event."""
    persons = db.execute(text('''
        SELECT p.name FROM persons p
        JOIN event_persons ep ON p.id = ep.person_id
        WHERE ep.event_id = :eid
        LIMIT 5
    '''), {'eid': event_id}).fetchall()

    locations = db.execute(text('''
        SELECT l.name FROM locations l
        JOIN event_locations el ON l.id = el.location_id
        WHERE el.event_id = :eid
        LIMIT 3
    '''), {'eid': event_id}).fetchall()

    return {
        'persons': [p[0] for p in persons],
        'locations': [l[0] for l in locations]
    }


def get_potential_parents(db):
    """Get confirmed events that could be parents."""
    result = db.execute(text('''
        SELECT id, title, date_start, date_end
        FROM events
        WHERE parent_status = 'confirmed'
          AND (is_aggregate = true OR wikidata_id IS NOT NULL)
        ORDER BY
            CASE WHEN is_aggregate THEN 0 ELSE 1 END,
            connection_count DESC NULLS LAST
        LIMIT 200
    ''')).fetchall()

    return [{'id': r[0], 'title': r[1], 'start': r[2], 'end': r[3]} for r in result]


def classify_batch(client, events_batch, parents):
    """Use LLM to classify events to parent events."""

    # Format events
    events_text = "\n".join([
        f"{i+1}. \"{e['title']}\" ({e['year'] or '?'})"
        f" - Persons: {', '.join(e['persons'][:3]) or 'none'}"
        f" - Locations: {', '.join(e['locations'][:2]) or 'none'}"
        for i, e in enumerate(events_batch)
    ])

    # Format potential parents (top 50 most relevant)
    parents_text = "\n".join([
        f"P{p['id']}: {p['title']} ({p['start'] or '?'}-{p['end'] or '?'})"
        for p in parents[:50]
    ])

    prompt = f'''Classify each historical event to its most appropriate parent event.
Consider the persons involved, locations, and time period.

EVENTS TO CLASSIFY:
{events_text}

POTENTIAL PARENT EVENTS:
{parents_text}

Return JSON: {{"results": [{{"index": 1, "parent_id": P123, "confidence": "high"/"medium"/"low"}}]}}
Only include if confident. Use null for parent_id if no good match.'''

    try:
        response = client.chat.completions.create(
            model='gpt-5-mini',
            messages=[{'role': 'user', 'content': prompt}],
            response_format={'type': 'json_object'},
            max_completion_tokens=3000
        )
        data = json.loads(response.choices[0].message.content)
        return data.get('results', [])
    except Exception as e:
        print(f"LLM Error: {e}")
        return []


def main():
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    db = SessionLocal()

    # Get potential parent events
    print("Loading parent events...")
    parents = get_potential_parents(db)
    print(f"Found {len(parents)} potential parents")

    # Get pending events with person connections
    print("\nLoading pending events with context...")
    events = db.execute(text('''
        SELECT e.id, e.title, e.date_start
        FROM events e
        WHERE e.parent_status = 'pending'
          AND e.wikidata_id IS NULL
          AND EXISTS (
              SELECT 1 FROM event_persons ep
              WHERE ep.event_id = e.id
          )
          AND NOT EXISTS (
              SELECT 1 FROM event_parents ep2
              WHERE ep2.event_id = e.id AND ep2.source = 'llm'
          )
        ORDER BY RANDOM()
        LIMIT 500
    ''')).fetchall()

    print(f"Processing {len(events)} events")

    # Add context to events
    events_with_context = []
    for e in events:
        ctx = get_event_context(db, e[0])
        events_with_context.append({
            'id': e[0],
            'title': e[1],
            'year': e[2],
            'persons': ctx['persons'],
            'locations': ctx['locations']
        })

    # Process in batches
    batch_size = 15
    total_classified = 0

    for i in range(0, len(events_with_context), batch_size):
        batch = events_with_context[i:i+batch_size]

        print(f"\nBatch {i//batch_size + 1}/{(len(events_with_context)+batch_size-1)//batch_size}")

        results = classify_batch(client, batch, parents)

        batch_count = 0
        for r in results:
            idx = r.get('index', 0) - 1
            parent_id = r.get('parent_id')
            confidence = r.get('confidence', 'low')

            if parent_id and confidence in ['high', 'medium'] and 0 <= idx < len(batch):
                # Extract numeric ID from P123 format
                if isinstance(parent_id, str) and parent_id.startswith('P'):
                    parent_id = int(parent_id[1:])

                event = batch[idx]

                # Verify parent exists
                parent_exists = db.execute(text(
                    'SELECT 1 FROM events WHERE id = :pid'
                ), {'pid': parent_id}).scalar()

                if parent_exists:
                    # Insert relationship
                    try:
                        db.execute(text('''
                            INSERT INTO event_parents (event_id, parent_event_id, is_primary, source, confidence)
                            VALUES (:eid, :pid, false, 'llm', :conf)
                            ON CONFLICT (event_id, parent_event_id) DO NOTHING
                        '''), {
                            'eid': event['id'],
                            'pid': parent_id,
                            'conf': 0.8 if confidence == 'high' else 0.6
                        })
                        batch_count += 1
                    except:
                        pass

        db.commit()
        total_classified += batch_count
        print(f"  Classified: {batch_count}")

        time.sleep(0.5)

    print(f"\n=== Total classified: {total_classified} ===")

    # Show stats
    llm_count = db.execute(text(
        "SELECT COUNT(*) FROM event_parents WHERE source = 'llm'"
    )).scalar()
    print(f"Total LLM relationships: {llm_count}")

    db.close()


if __name__ == '__main__':
    main()
