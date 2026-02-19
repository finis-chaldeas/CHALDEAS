"""
Extract P17 (country) claims with temporal qualifiers from Wikidata dump.

Phase B of the territories pipeline:
1. Load all location wikidata_ids from DB
2. Stream through the 1.6TB Wikidata JSON dump
3. For matching entities, extract P17 claims with P580/P582 qualifiers
4. Save results as JSON for later import

The dump is line-delimited JSON (each line = one entity).
Expected runtime: 2-4 hours for 1.6TB on HDD.

Usage:
    cd backend
    python ../poc/scripts/extract_p17_from_dump.py
"""
import sys
import os
import json
import time
import psycopg2
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_URL = 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas'
DUMP_PATH = Path(r'E:\wikidata\latest-all.json')
OUTPUT_PATH = Path(r'C:\Projects\Chaldeas\poc\data\wikidata\p17_extractions.json')


def load_location_qids():
    """Load all location wikidata_ids from DB."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT wikidata_id, id, name FROM locations WHERE wikidata_id IS NOT NULL")
    qid_map = {}
    for qid, loc_id, name in cur.fetchall():
        qid_map[qid] = {'id': loc_id, 'name': name}
    cur.close()
    conn.close()
    return qid_map


def load_territory_qids():
    """Load all territory wikidata_ids for resolving P17 values."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT wikidata_id, id, name FROM territories WHERE wikidata_id IS NOT NULL")
    qid_map = {}
    for qid, tid, name in cur.fetchall():
        qid_map[qid] = {'id': tid, 'name': name}
    cur.close()
    conn.close()
    return qid_map


def parse_year_from_time(time_value):
    """Parse year from Wikidata time value like '+1453-00-00T00:00:00Z' or '-0753-00-00T00:00:00Z'."""
    if not time_value:
        return None
    try:
        # Remove leading + if present
        t = time_value.lstrip('+')
        # Extract year part (before first -)
        if t.startswith('-'):
            # BCE date
            parts = t[1:].split('-')
            return -int(parts[0])
        else:
            parts = t.split('-')
            return int(parts[0])
    except (ValueError, IndexError):
        return None


def extract_p17_from_entity(entity_data):
    """Extract P17 (country) claims with temporal qualifiers from a single entity."""
    claims = entity_data.get('claims', {})
    p17_claims = claims.get('P17', [])

    results = []
    for claim in p17_claims:
        mainsnak = claim.get('mainsnak', {})
        datavalue = mainsnak.get('datavalue', {})

        if datavalue.get('type') != 'wikibase-entityid':
            continue

        country_qid = 'Q' + str(datavalue.get('value', {}).get('numeric-id', ''))

        # Extract temporal qualifiers
        qualifiers = claim.get('qualifiers', {})
        start_time = None
        end_time = None

        # P580 = start time
        for q in qualifiers.get('P580', []):
            dv = q.get('datavalue', {})
            if dv.get('type') == 'time':
                start_time = parse_year_from_time(dv.get('value', {}).get('time'))

        # P582 = end time
        for q in qualifiers.get('P582', []):
            dv = q.get('datavalue', {})
            if dv.get('type') == 'time':
                end_time = parse_year_from_time(dv.get('value', {}).get('time'))

        # Rank (preferred/normal/deprecated)
        rank = claim.get('rank', 'normal')

        results.append({
            'country_qid': country_qid,
            'start_year': start_time,
            'end_year': end_time,
            'rank': rank,
        })

    return results


def stream_dump(dump_path, location_qids, territory_qids):
    """Stream through the Wikidata dump and extract P17 for our locations."""
    results = {}
    total_lines = 0
    matched = 0
    with_p17 = 0
    with_temporal = 0

    start_time = time.time()
    file_size = os.path.getsize(dump_path)

    print(f"Streaming {dump_path}")
    print(f"File size: {file_size / (1024**3):.1f} GB")
    print(f"Looking for {len(location_qids)} location QIDs")
    print(f"Known territory QIDs: {len(territory_qids)}")
    print()

    # Also collect P17 values that aren't in our territories (to potentially add later)
    unknown_territories = {}

    with open(dump_path, 'r', encoding='utf-8') as f:
        while True:
            line = f.readline()
            if not line:
                break
            total_lines += 1

            # Progress reporting every 1M lines
            if total_lines % 1_000_000 == 0:
                elapsed = time.time() - start_time
                pos = f.tell()
                pct = (pos / file_size) * 100 if file_size > 0 else 0
                rate = total_lines / elapsed if elapsed > 0 else 0
                print(f"  [{pct:.1f}%] {total_lines/1e6:.0f}M lines | "
                      f"{matched} matched | {with_p17} with P17 | {with_temporal} with temporal | "
                      f"{elapsed:.0f}s | {rate:.0f} lines/s",
                      flush=True)

            # Skip array delimiters
            line = line.strip().rstrip(',')
            if not line or line in ('[', ']'):
                continue

            try:
                entity = json.loads(line)
            except json.JSONDecodeError:
                continue

            qid = entity.get('id', '')
            if qid not in location_qids:
                continue

            matched += 1
            loc_info = location_qids[qid]

            # Extract P17
            p17_data = extract_p17_from_entity(entity)
            if p17_data:
                with_p17 += 1
                has_temporal = any(d['start_year'] or d['end_year'] for d in p17_data)
                if has_temporal:
                    with_temporal += 1

                # Track unknown territories
                for d in p17_data:
                    cqid = d['country_qid']
                    if cqid not in territory_qids and cqid not in unknown_territories:
                        # Try to get label from the entity's P17 claim
                        unknown_territories[cqid] = unknown_territories.get(cqid, 0) + 1

                results[qid] = {
                    'location_id': loc_info['id'],
                    'location_name': loc_info['name'],
                    'p17': p17_data,
                }

            # Early exit if we've found all locations
            if matched >= len(location_qids):
                print(f"\n  Found all {len(location_qids)} locations! Stopping early.")
                break

    elapsed = time.time() - start_time
    print(f"\n=== Extraction complete ===")
    print(f"Total lines scanned: {total_lines:,}")
    print(f"Locations matched: {matched}")
    print(f"With P17 claims: {with_p17}")
    print(f"With temporal qualifiers: {with_temporal}")
    print(f"Time: {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # Report top unknown territories
    if unknown_territories:
        sorted_unknown = sorted(unknown_territories.items(), key=lambda x: -x[1])[:30]
        print(f"\nTop unknown territory QIDs (not in our territories table):")
        for qid, count in sorted_unknown:
            print(f"  {qid}: {count} locations")

    return results


def save_results(results, output_path):
    """Save extraction results to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(results)} results to {output_path}")


if __name__ == '__main__':
    print("=== Wikidata P17 Extraction ===\n")

    # Check dump exists
    if not DUMP_PATH.exists():
        print(f"ERROR: Wikidata dump not found at {DUMP_PATH}")
        print("Make sure E: drive is accessible.")
        sys.exit(1)

    # Load QID sets
    print("Loading location QIDs from DB...")
    location_qids = load_location_qids()
    print(f"  {len(location_qids)} locations loaded")

    print("Loading territory QIDs from DB...")
    territory_qids = load_territory_qids()
    print(f"  {len(territory_qids)} territories loaded")

    # Stream dump
    results = stream_dump(DUMP_PATH, location_qids, territory_qids)

    # Save
    save_results(results, OUTPUT_PATH)

    print("\nDone! Next step: run import_territory_locations.py to load into DB.")
