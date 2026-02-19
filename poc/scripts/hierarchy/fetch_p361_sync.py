"""
Fetch Wikidata P361 (part of) relationships - Synchronous version.
"""
import sys
import os
import time
import requests

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

from sqlalchemy import text
from app.db.session import SessionLocal

WIKIDATA_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "CHALDEAS/1.0 (https://chaldeas.site)"

def query_sparql(query: str) -> list:
    """Execute SPARQL query."""
    try:
        response = requests.get(
            WIKIDATA_SPARQL_ENDPOINT,
            params={"query": query, "format": "json"},
            headers={"User-Agent": USER_AGENT},
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        return data.get("results", {}).get("bindings", [])
    except Exception as e:
        print(f"SPARQL error: {e}", flush=True)
        return []

def extract_qid(uri):
    """http://www.wikidata.org/entity/Q12345 -> Q12345"""
    if not uri:
        return None
    if uri.startswith("http://www.wikidata.org/entity/"):
        return uri.split("/")[-1]
    if uri.startswith("Q"):
        return uri
    return None

def get_value(row, key):
    """Extract value from SPARQL result row."""
    if key in row and "value" in row[key]:
        return row[key]["value"]
    return None

def fetch_batch(qids):
    """Fetch P361 for a batch of QIDs - simplified query."""
    values = " ".join(f"wd:{qid}" for qid in qids)
    # Simplified query - just get P361 relationships (no labels)
    query = f"""
    SELECT ?event ?parent WHERE {{
      VALUES ?event {{ {values} }}
      ?event wdt:P361 ?parent .
    }}
    """

    rows = query_sparql(query)

    results = {}
    for r in rows:
        qid = extract_qid(get_value(r, "event"))
        parent_qid = extract_qid(get_value(r, "parent"))
        if qid and qid not in results:
            results[qid] = {
                "parent_qid": parent_qid,
                "parent_label": None  # We'll skip labels for speed
            }

    # Fill in missing QIDs (no P361 in Wikidata)
    for qid in qids:
        if qid not in results:
            results[qid] = {"parent_qid": None, "parent_label": None}

    return results


def main():
    db = SessionLocal()

    try:
        print("=== Phase 1: Wikidata P361 Fetch (Sync) ===\n", flush=True)

        # 1. Get events with wikidata_id that haven't been processed
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

        print(f"Events to process: {len(events)}", flush=True)

        if not events:
            print("Nothing to process!")
            return

        # 2. Fetch P361 in batches
        batch_size = 50
        qid_to_event = {e['wikidata_id']: e for e in events}
        all_results = {}

        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            qids = [e['wikidata_id'] for e in batch]

            print(f"  Fetching batch {i//batch_size + 1}/{(len(events) + batch_size - 1)//batch_size}...", flush=True)

            batch_results = fetch_batch(qids)
            all_results.update(batch_results)

            # Rate limit (Wikidata recommends 1-2 req/s)
            time.sleep(0.5)

        # 3. Count results
        has_parent = [qid for qid, r in all_results.items() if r["parent_qid"]]
        no_parent = [qid for qid, r in all_results.items() if not r["parent_qid"]]

        print(f"\nResults:", flush=True)
        print(f"  Has P361 parent: {len(has_parent)}", flush=True)
        print(f"  No P361 parent: {len(no_parent)}", flush=True)

        # 4. Match parent QIDs to DB events
        parent_qids = list(set(all_results[qid]["parent_qid"] for qid in has_parent))
        print(f"\nUnique parent QIDs: {len(parent_qids)}", flush=True)

        # Find which parents exist in DB
        if parent_qids:
            result = db.execute(text("""
                SELECT id, wikidata_id, title
                FROM events
                WHERE wikidata_id = ANY(:qids)
            """), {"qids": parent_qids})
            db_parents = {row[1]: {"id": row[0], "title": row[2]} for row in result}
        else:
            db_parents = {}

        print(f"Parents found in DB: {len(db_parents)}", flush=True)

        # 5. Connect events to parents
        connected = 0
        not_in_db = []

        for qid in has_parent:
            event = qid_to_event.get(qid)
            if not event:
                continue

            parent_qid = all_results[qid]["parent_qid"]
            parent = db_parents.get(parent_qid)

            if parent:
                # Insert into event_parents
                db.execute(text("""
                    INSERT INTO event_parents (event_id, parent_event_id, is_primary, source, confidence)
                    VALUES (:eid, :pid, true, 'wikidata', 0.95)
                    ON CONFLICT (event_id, parent_event_id) DO UPDATE SET
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
                    title = event['title'][:40] if event['title'] else 'N/A'
                    ptitle = parent['title'][:30] if parent['title'] else 'N/A'
                    print(f"  [{event['id']}] {title} -> {ptitle}", flush=True)
            else:
                not_in_db.append({
                    "event_id": event['id'],
                    "event_title": event['title'],
                    "parent_qid": parent_qid,
                    "parent_label": all_results[qid]["parent_label"]
                })

        if connected > 20:
            print(f"  ... and {connected - 20} more", flush=True)

        db.commit()

        # 6. Summary
        print(f"\n=== Summary ===", flush=True)
        print(f"Connected: {connected}", flush=True)
        print(f"Parent not in DB: {len(not_in_db)}", flush=True)
        print(f"No P361 in Wikidata: {len(no_parent)}", flush=True)

        # Show missing parents
        if not_in_db:
            print(f"\n=== Parents not in DB (top 20) ===", flush=True)
            by_parent = {}
            for item in not_in_db:
                key = (item['parent_qid'], item['parent_label'] or 'Unknown')
                if key not in by_parent:
                    by_parent[key] = []
                by_parent[key].append(item['event_title'])

            sorted_parents = sorted(by_parent.items(), key=lambda x: -len(x[1]))[:20]
            for (qid, label), children in sorted_parents:
                print(f"  {qid} ({label[:30] if label else 'Unknown'}): {len(children)} children", flush=True)

    finally:
        db.close()


if __name__ == "__main__":
    main()
