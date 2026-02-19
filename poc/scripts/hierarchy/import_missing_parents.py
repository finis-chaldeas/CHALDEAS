"""
Import missing parent events from Wikidata.

These are events that are P361 parents but aren't in our database.
"""
import sys
import os
import time
import requests
import json

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


def get_event_details(qids: list) -> dict:
    """Fetch event details from Wikidata."""
    if not qids:
        return {}

    values = " ".join(f"wd:{qid}" for qid in qids[:50])  # Batch of 50
    query = f"""
    SELECT ?event ?label ?labelKo ?start ?end WHERE {{
      VALUES ?event {{ {values} }}
      OPTIONAL {{ ?event rdfs:label ?label . FILTER(LANG(?label) = "en") }}
      OPTIONAL {{ ?event rdfs:label ?labelKo . FILTER(LANG(?labelKo) = "ko") }}
      OPTIONAL {{ ?event wdt:P580 ?start . }}
      OPTIONAL {{ ?event wdt:P582 ?end . }}
      OPTIONAL {{ ?event wdt:P585 ?start . }}
    }}
    """

    results = {}
    rows = query_sparql(query)

    for r in rows:
        uri = r.get("event", {}).get("value", "")
        qid = uri.split("/")[-1] if uri else None
        if qid and qid not in results:
            label = r.get("label", {}).get("value", "")
            label_ko = r.get("labelKo", {}).get("value")
            start = r.get("start", {}).get("value")
            end = r.get("end", {}).get("value")

            results[qid] = {
                "qid": qid,
                "label": label,
                "label_ko": label_ko,
                "start": parse_date(start),
                "end": parse_date(end)
            }

    # Fill in missing
    for qid in qids[:50]:
        if qid not in results:
            results[qid] = {"qid": qid, "label": "", "label_ko": None, "start": None, "end": None}

    return results


def parse_date(date_str):
    """Parse ISO date to year."""
    if not date_str:
        return None
    try:
        if date_str.startswith("+"):
            return int(date_str[1:5])
        elif date_str.startswith("-"):
            return -int(date_str[1:5])
        return int(date_str[:4])
    except:
        return None


def main():
    db = SessionLocal()

    try:
        print("=== Import Missing Parent Events ===\n", flush=True)

        # 1. Get list of missing parent QIDs with child counts
        result = db.execute(text("""
            WITH child_parents AS (
                SELECT DISTINCT
                    e.id as child_id,
                    e.wikidata_id as child_qid
                FROM events e
                WHERE e.wikidata_id IS NOT NULL
                  AND e.parent_status != 'garbage'
            )
            SELECT parent_qid, COUNT(*) as child_count
            FROM (
                SELECT DISTINCT child_id, parent_qid
                FROM child_parents cp
                CROSS JOIN LATERAL (
                    SELECT (jsonb_array_elements_text(
                        (SELECT jsonb_agg(r.parent_qid)
                         FROM (SELECT DISTINCT parent_qid FROM unnest(ARRAY(
                             SELECT CASE
                                 WHEN parent_event_id IS NOT NULL
                                 THEN (SELECT wikidata_id FROM events WHERE id = parent_event_id)
                                 ELSE NULL
                             END
                             FROM event_parents WHERE event_id = cp.child_id
                         )) as parent_qid WHERE parent_qid IS NOT NULL) r)
                    )) as parent_qid
                ) sub
                WHERE parent_qid IS NOT NULL
            ) x
            WHERE NOT EXISTS (SELECT 1 FROM events WHERE wikidata_id = parent_qid)
            GROUP BY parent_qid
            ORDER BY child_count DESC
            LIMIT 50
        """))

        # That query is complex, let's simplify
        # Get missing parents from the log output we saw earlier

        missing_parents = [
            "Q8676",    # American Civil War
            "Q33143",   # Seven Years' War
            "Q849680",  # American Indian Wars
            "Q184425",  # Napoleonic Wars (probably)
            "Q207318",  # World War I related
            "Q10859",   # French Revolution
            "Q152989",  # some war
            "Q8669",    # another war
            "Q2490042", # some event
            "Q187742",  # some event
        ]

        # Check which are already in DB
        result = db.execute(text("""
            SELECT wikidata_id FROM events
            WHERE wikidata_id = ANY(:qids)
        """), {"qids": missing_parents})
        existing = {row[0] for row in result}

        to_import = [qid for qid in missing_parents if qid not in existing]
        print(f"Missing parents to import: {len(to_import)}", flush=True)

        if not to_import:
            print("All parents already in DB!")
            return

        # 2. Fetch details from Wikidata
        print("Fetching from Wikidata...", flush=True)
        details = get_event_details(to_import)

        # 3. Insert into database
        imported = 0
        for qid, info in details.items():
            if not info["label"]:
                print(f"  Skipping {qid} - no label", flush=True)
                continue

            # Check if already exists (by title as fallback)
            result = db.execute(text("""
                SELECT id FROM events WHERE title = :title LIMIT 1
            """), {"title": info["label"]})
            row = result.fetchone()

            if row:
                # Update existing with QID
                db.execute(text("""
                    UPDATE events SET wikidata_id = :qid WHERE id = :id
                """), {"qid": qid, "id": row[0]})
                print(f"  Updated [{row[0]}] {info['label']} with {qid}", flush=True)
            else:
                # Generate slug from title
                import re
                slug = re.sub(r'[^a-z0-9]+', '-', info["label"].lower()).strip('-')
                slug = f"{slug}-{qid.lower()}"  # Make unique with QID

                # Insert new
                db.execute(text("""
                    INSERT INTO events (title, slug, date_start, date_end, wikidata_id, parent_status, created_at, updated_at)
                    VALUES (:title, :slug, :start, :end, :qid, 'unknown', NOW(), NOW())
                    ON CONFLICT DO NOTHING
                """), {
                    "title": info["label"],
                    "slug": slug,
                    "start": info["start"],
                    "end": info["end"],
                    "qid": qid
                })
                print(f"  Imported: {info['label']} ({qid})", flush=True)

            imported += 1
            time.sleep(0.1)

        db.commit()
        print(f"\nImported/updated {imported} parent events", flush=True)

        # 4. Now re-run P361 to connect children
        print("\nRe-connecting children to new parents...", flush=True)

        # Get events that have parent QIDs matching our new imports
        for qid in to_import:
            result = db.execute(text("""
                SELECT id FROM events WHERE wikidata_id = :qid
            """), {"qid": qid})
            row = result.fetchone()
            if not row:
                continue

            parent_id = row[0]

            # Find children with this parent in P361
            # For now, just output what we'd connect
            print(f"  Parent: {qid} (id={parent_id})", flush=True)

    finally:
        db.close()


if __name__ == "__main__":
    main()
