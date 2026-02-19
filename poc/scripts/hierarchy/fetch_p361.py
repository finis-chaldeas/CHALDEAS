"""
Fetch Wikidata P361 (part of) relationships and connect to DB.

Phase 1 of hierarchy building - most reliable source.
"""
import asyncio
import sys
import os

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

from sqlalchemy import text
from app.db.session import SessionLocal
from wikidata_client import WikidataClient


async def fetch_and_connect():
    db = SessionLocal()

    try:
        # 1. Get events with wikidata_id that haven't been processed
        print("=== Phase 1: Wikidata P361 Fetch ===\n")

        result = db.execute(text("""
            SELECT e.id, e.wikidata_id, e.title
            FROM events e
            WHERE e.wikidata_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM event_parents ep
                  WHERE ep.event_id = e.id AND ep.source = 'wikidata'
              )
            ORDER BY e.id
        """))
        events = [dict(row._mapping) for row in result]

        print(f"Events to process: {len(events)}")

        if not events:
            print("Nothing to process!")
            return

        # 2. Fetch P361 from Wikidata
        qids = [e['wikidata_id'] for e in events]
        qid_to_event = {e['wikidata_id']: e for e in events}

        async with WikidataClient(rate_limit=1.5) as client:
            print(f"\nFetching from Wikidata (batch size 50)...")
            wd_results = await client.get_events_bulk(qids, batch_size=50)

        # 3. Count results
        has_parent = [r for r in wd_results if r.parent_qid]
        no_parent = [r for r in wd_results if not r.parent_qid]

        print(f"\nResults:")
        print(f"  Has P361 parent: {len(has_parent)}")
        print(f"  No P361 parent: {len(no_parent)}")

        # 4. Match parent QIDs to DB events
        parent_qids = list(set(r.parent_qid for r in has_parent))
        print(f"\nUnique parent QIDs: {len(parent_qids)}")

        # Find which parents exist in DB
        if parent_qids:
            result = db.execute(text("""
                SELECT id, wikidata_id, title, date_start, date_end
                FROM events
                WHERE wikidata_id = ANY(:qids)
            """), {"qids": parent_qids})
            db_parents = {row[1]: {"id": row[0], "title": row[2], "date_start": row[3], "date_end": row[4]}
                         for row in result}
        else:
            db_parents = {}

        print(f"Parents found in DB: {len(db_parents)}")

        # 5. Connect events to parents
        connected = 0
        not_in_db = []

        for wd in has_parent:
            event = qid_to_event.get(wd.qid)
            if not event:
                continue

            parent = db_parents.get(wd.parent_qid)
            if parent:
                # Insert into event_parents
                db.execute(text("""
                    INSERT INTO event_parents (event_id, parent_id, is_primary, source, confidence)
                    VALUES (:eid, :pid, true, 'wikidata', 0.95)
                    ON CONFLICT (event_id, parent_id) DO UPDATE SET
                        source = 'wikidata', confidence = 0.95
                """), {"eid": event['id'], "pid": parent['id']})

                # Update parent_status
                db.execute(text("""
                    UPDATE events
                    SET parent_status = 'confirmed', parent_event_id = :pid
                    WHERE id = :eid
                """), {"eid": event['id'], "pid": parent['id']})

                connected += 1
                if connected <= 20:
                    print(f"  [{event['id']}] {event['title'][:40]} -> {parent['title'][:30]}")
            else:
                not_in_db.append({
                    "event_id": event['id'],
                    "event_title": event['title'],
                    "parent_qid": wd.parent_qid,
                    "parent_label": wd.parent_label
                })

        if connected > 20:
            print(f"  ... and {connected - 20} more")

        db.commit()

        # 6. Mark events without P361 as checked (so we don't re-process)
        # We'll add them to event_parents with parent_id = NULL to mark as processed
        # Actually, let's just leave them - they need LLM classification later

        # 7. Summary
        print(f"\n=== Summary ===")
        print(f"Connected: {connected}")
        print(f"Parent not in DB: {len(not_in_db)}")
        print(f"No P361 in Wikidata: {len(no_parent)}")

        # Show missing parents (might want to import these)
        if not_in_db:
            print(f"\n=== Parents not in DB (top 20) ===")
            # Group by parent
            by_parent = {}
            for item in not_in_db:
                key = (item['parent_qid'], item['parent_label'])
                if key not in by_parent:
                    by_parent[key] = []
                by_parent[key].append(item['event_title'])

            sorted_parents = sorted(by_parent.items(), key=lambda x: -len(x[1]))[:20]
            for (qid, label), children in sorted_parents:
                print(f"  {qid} ({label}): {len(children)} children")
                for child in children[:3]:
                    print(f"    - {child[:50]}")
                if len(children) > 3:
                    print(f"    ... +{len(children)-3} more")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(fetch_and_connect())
