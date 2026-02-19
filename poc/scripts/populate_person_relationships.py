"""
Populate person_relationships from Wikidata API.

Fetches family/intellectual relationship properties:
- P22 (father), P25 (mother), P26 (spouse), P40 (child)
- P3373 (sibling), P1066 (student of), P184 (doctoral advisor)
- P737 (influenced by)

Only inserts relationships where BOTH persons exist in our DB.

Usage:
    cd backend
    python ../poc/scripts/populate_person_relationships.py
"""
import sys
import time
import requests
import psycopg2

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_URL = 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas'
WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
BATCH_SIZE = 50
REQUEST_DELAY = 0.25

# Wikidata property -> relationship_type mapping
RELATIONSHIP_PROPS = {
    'P22':   {'type': 'father',           'strength': 5, 'bidir': 0},
    'P25':   {'type': 'mother',           'strength': 5, 'bidir': 0},
    'P26':   {'type': 'spouse',           'strength': 5, 'bidir': 1},
    'P40':   {'type': 'child',            'strength': 5, 'bidir': 0},
    'P3373': {'type': 'sibling',          'strength': 4, 'bidir': 1},
    'P1066': {'type': 'student_of',       'strength': 4, 'bidir': 0},
    'P184':  {'type': 'doctoral_advisor', 'strength': 4, 'bidir': 0},
    'P185':  {'type': 'doctoral_student', 'strength': 4, 'bidir': 0},
    'P737':  {'type': 'influenced_by',    'strength': 3, 'bidir': 0},
    'P451':  {'type': 'partner',          'strength': 4, 'bidir': 1},
    'P1038': {'type': 'relative',         'strength': 2, 'bidir': 1},
}


def fetch_batch(qids):
    props = '|'.join(RELATIONSHIP_PROPS.keys())
    params = {
        'action': 'wbgetentities',
        'ids': '|'.join(qids),
        'props': 'claims',
        'format': 'json',
    }
    headers = {'User-Agent': 'Chaldeas/1.0 (historical data project)'}
    for attempt in range(3):
        try:
            resp = requests.get(WIKIDATA_API, params=params, headers=headers, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                time.sleep(2 ** (attempt + 1))
        except Exception:
            time.sleep(2)
    return None


def extract_entity_relations(entity):
    """Extract person QID targets from relationship properties."""
    claims = entity.get('claims', {})
    relations = []
    for prop, config in RELATIONSHIP_PROPS.items():
        for claim in claims.get(prop, []):
            mainsnak = claim.get('mainsnak', {})
            dv = mainsnak.get('datavalue', {})
            if dv.get('type') != 'wikibase-entityid':
                continue
            target_qid = 'Q' + str(dv['value'].get('numeric-id', ''))
            if target_qid == 'Q':
                continue
            relations.append({
                'target_qid': target_qid,
                'type': config['type'],
                'strength': config['strength'],
                'bidir': config['bidir'],
            })
    return relations


def run():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Build QID -> person_id lookup
    cur.execute("SELECT id, wikidata_id FROM persons WHERE wikidata_id IS NOT NULL")
    rows = cur.fetchall()
    qid_to_pid = {qid: pid for pid, qid in rows}
    all_qids = list(qid_to_pid.keys())
    print(f"=== PERSON RELATIONSHIPS: {len(all_qids)} persons ===\n", flush=True)

    total_batches = (len(all_qids) + BATCH_SIZE - 1) // BATCH_SIZE
    inserted = 0
    skipped_no_target = 0
    duplicates = 0
    start_time = time.time()

    for batch_idx in range(total_batches):
        batch = all_qids[batch_idx * BATCH_SIZE:(batch_idx + 1) * BATCH_SIZE]
        data = fetch_batch(batch)
        if not data:
            continue

        entities = data.get('entities', {})
        for qid in batch:
            entity = entities.get(qid)
            if not entity or 'missing' in entity:
                continue

            pid = qid_to_pid[qid]
            relations = extract_entity_relations(entity)

            for rel in relations:
                target_pid = qid_to_pid.get(rel['target_qid'])
                if not target_pid:
                    skipped_no_target += 1
                    continue
                if target_pid == pid:
                    continue  # skip self-reference

                try:
                    cur.execute("""
                        INSERT INTO person_relationships
                        (person_id, related_person_id, relationship_type, strength, is_bidirectional, confidence)
                        VALUES (%s, %s, %s, %s, %s, 1.0)
                    """, (pid, target_pid, rel['type'], rel['strength'], rel['bidir']))
                    inserted += 1
                except psycopg2.errors.UniqueViolation:
                    conn.rollback()
                    duplicates += 1
                    continue
                except Exception:
                    conn.rollback()
                    continue

        if (batch_idx + 1) % 50 == 0 or batch_idx == total_batches - 1:
            conn.commit()
            elapsed = time.time() - start_time
            pct = (batch_idx + 1) / total_batches * 100
            eta = (elapsed / (batch_idx + 1)) * (total_batches - batch_idx - 1) if batch_idx > 0 else 0
            print(f"  [{pct:.0f}%] inserted: {inserted} | skipped(no target): {skipped_no_target} | dupes: {duplicates} | {elapsed:.0f}s | ETA {eta:.0f}s", flush=True)

        time.sleep(REQUEST_DELAY)

    conn.commit()
    elapsed = time.time() - start_time
    print(f"\n=== Done in {elapsed:.0f}s ({elapsed/60:.1f}min) ===", flush=True)
    print(f"  Inserted: {inserted}", flush=True)
    print(f"  Skipped (target not in DB): {skipped_no_target}", flush=True)
    print(f"  Duplicates: {duplicates}", flush=True)

    # Stats
    cur.execute("SELECT COUNT(*) FROM person_relationships")
    print(f"\nTotal person_relationships: {cur.fetchone()[0]}", flush=True)

    cur.execute("SELECT relationship_type, COUNT(*) FROM person_relationships GROUP BY relationship_type ORDER BY COUNT(*) DESC")
    print("\nBy type:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")

    cur.close()
    conn.close()


if __name__ == '__main__':
    run()
