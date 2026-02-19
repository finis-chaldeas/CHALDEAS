"""
Import P17 extraction results into territory_locations table.

Phase B-2: Takes the P17 extraction JSON and creates territory_locations entries.
Also creates new territories for P17 values not in our territories table.

Usage:
    cd backend
    python ../poc/scripts/import_territory_locations.py
"""
import sys
import json
import psycopg2
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_URL = 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas'
INPUT_PATH = Path(r'C:\Projects\Chaldeas\poc\data\wikidata\p17_extractions.json')


def load_territory_map():
    """Load territory wikidata_id -> id mapping."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT wikidata_id, id FROM territories WHERE wikidata_id IS NOT NULL")
    mapping = {row[0]: row[1] for row in cur.fetchall()}
    cur.close()
    conn.close()
    return mapping


def import_results():
    """Import P17 extraction results into territory_locations."""
    if not INPUT_PATH.exists():
        print(f"ERROR: Input file not found: {INPUT_PATH}")
        print("Run extract_p17_from_dump.py first.")
        sys.exit(1)

    print("Loading extraction results...")
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        results = json.load(f)
    print(f"  {len(results)} locations with P17 data")

    print("Loading territory map...")
    territory_map = load_territory_map()
    print(f"  {len(territory_map)} known territories")

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    inserted = 0
    skipped = 0
    unknown_territories = {}
    created_territories = 0

    for qid, data in results.items():
        location_id = data['location_id']
        location_name = data['location_name']

        for p17 in data['p17']:
            country_qid = p17['country_qid']
            start_year = p17.get('start_year')
            end_year = p17.get('end_year')
            rank = p17.get('rank', 'normal')

            # Skip deprecated claims
            if rank == 'deprecated':
                continue

            # Resolve territory
            territory_id = territory_map.get(country_qid)

            if territory_id is None:
                # Track unknown territory for later creation
                if country_qid not in unknown_territories:
                    unknown_territories[country_qid] = {
                        'count': 0,
                        'locations': []
                    }
                unknown_territories[country_qid]['count'] += 1
                if len(unknown_territories[country_qid]['locations']) < 3:
                    unknown_territories[country_qid]['locations'].append(location_name)
                skipped += 1
                continue

            # Insert territory_location (ON CONFLICT skip)
            try:
                cur.execute("""
                    INSERT INTO territory_locations (territory_id, location_id, valid_from, valid_until, relation_type)
                    VALUES (%s, %s, %s, %s, 'contains')
                    ON CONFLICT ON CONSTRAINT territory_locations_territory_id_location_id_valid_from_key DO NOTHING
                """, (territory_id, location_id, start_year, end_year))
                if cur.rowcount > 0:
                    inserted += 1
            except Exception as e:
                print(f"  ERROR inserting {location_name} -> territory {territory_id}: {e}")
                conn.rollback()
                continue

    conn.commit()

    print(f"\n=== Import complete ===")
    print(f"Inserted: {inserted} territory_location entries")
    print(f"Skipped (unknown territory): {skipped}")

    # Report unknown territories
    if unknown_territories:
        sorted_unknown = sorted(unknown_territories.items(), key=lambda x: -x[1]['count'])[:30]
        print(f"\nTop unknown territories ({len(unknown_territories)} total):")
        for qid, info in sorted_unknown:
            locs = ', '.join(info['locations'][:3])
            print(f"  {qid}: {info['count']} locations (e.g. {locs})")

    # Final count
    cur.execute("SELECT COUNT(*) FROM territory_locations")
    print(f"\nTotal territory_locations in DB: {cur.fetchone()[0]}")

    cur.close()
    conn.close()


if __name__ == '__main__':
    import_results()
