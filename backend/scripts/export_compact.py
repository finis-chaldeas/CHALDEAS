"""
Export compact (light-only) data from the current DB as CSV files.

Exports only is_light=TRUE rows from large tables (persons, locations)
and all rows from small tables (events, categories, etc).

Output: C:\\Projects\\Chaldeas\\data\\compact_export\\

Usage:
    cd backend
    python scripts/export_compact.py

Prerequisites:
    - PostgreSQL running on port 5432 (E: archive DB)
    - is_light flags set (run set_is_light.py first)
"""
import os
import sys
import time
from pathlib import Path

import psycopg2

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Connection string
DB_URL = "host=127.0.0.1 port=5432 dbname=chaldeas user=chaldeas password=chaldeas_dev"

# Output directory
OUTPUT_DIR = Path("C:/Projects/Chaldeas/data/compact_export")


def get_conn():
    return psycopg2.connect(DB_URL)


def table_exists(cur, table_name):
    cur.execute("""
        SELECT EXISTS(
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
        )
    """, (table_name,))
    return cur.fetchone()[0]


def export_table(cur, table_name, query, output_path):
    """Export a query result to CSV using COPY TO STDOUT."""
    copy_sql = f"COPY ({query}) TO STDOUT WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')"
    start = time.time()

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        cur.copy_expert(copy_sql, f)

    # Count rows (header - 1)
    with open(output_path, 'r', encoding='utf-8') as f:
        row_count = sum(1 for _ in f) - 1

    elapsed = time.time() - start
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  {table_name:30s}  {row_count:>10,} rows  {size_mb:>8.1f} MB  ({elapsed:.1f}s)")
    return row_count


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = get_conn()
    conn.set_client_encoding('UTF8')
    cur = conn.cursor()

    print("=" * 70)
    print("  CHALDEAS Compact DB Export")
    print("=" * 70)

    # Check is_light flags exist
    cur.execute("SELECT COUNT(*) FROM persons WHERE is_light = TRUE")
    light_persons = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM locations WHERE is_light = TRUE")
    light_locations = cur.fetchone()[0]
    print(f"\n  Light persons:  {light_persons:,}")
    print(f"  Light locations: {light_locations:,}")

    if light_persons == 0:
        print("\n  ERROR: No light persons found. Run set_is_light.py first!")
        sys.exit(1)

    total_rows = 0
    print(f"\n  Output: {OUTPUT_DIR}\n")
    print(f"  {'Table':30s}  {'Rows':>10s}  {'Size':>8s}  Time")
    print(f"  {'-'*30}  {'-'*10}  {'-'*8}  {'-'*6}")

    # ==========================================
    # 1. Full export (small tables, all rows)
    # ==========================================

    full_tables = [
        ("alembic_version", "SELECT * FROM alembic_version"),
        ("categories",      "SELECT * FROM categories"),
        ("events",          "SELECT * FROM events"),
    ]

    # Conditionally add tables that may or may not exist
    optional_full_tables = [
        "event_connections",
        "event_locations",
        "event_relationships",
        "periods",
        "polities",
        "historical_chains",
        "chain_segments",
        "chain_entity_roles",
        "masters",
        "entity_aliases",
        "import_batches",
        "entity_narratives",
        "text_mentions",
        "entity_properties",
        "person_sources",
        "person_detail",
        "histories",
        "history_entities",
    ]

    for table in optional_full_tables:
        if table_exists(cur, table):
            full_tables.append((table, f"SELECT * FROM {table}"))

    for table_name, query in full_tables:
        out_path = OUTPUT_DIR / f"{table_name}.csv"
        rows = export_table(cur, table_name, query, out_path)
        total_rows += rows

    # ==========================================
    # 2. Light-filtered exports (big tables)
    # ==========================================

    # Persons (is_light only)
    out_path = OUTPUT_DIR / "persons.csv"
    rows = export_table(cur, "persons (light)",
        "SELECT * FROM persons WHERE is_light = TRUE", out_path)
    total_rows += rows

    # Locations (is_light only)
    out_path = OUTPUT_DIR / "locations.csv"
    rows = export_table(cur, "locations (light)",
        "SELECT * FROM locations WHERE is_light = TRUE", out_path)
    total_rows += rows

    # Event-persons (only light persons)
    if table_exists(cur, 'event_persons'):
        out_path = OUTPUT_DIR / "event_persons.csv"
        rows = export_table(cur, "event_persons (light)",
            """SELECT ep.* FROM event_persons ep
               JOIN persons p ON p.id = ep.person_id
               WHERE p.is_light = TRUE""", out_path)
        total_rows += rows

    # Location names (only light locations)
    if table_exists(cur, 'location_names'):
        out_path = OUTPUT_DIR / "location_names.csv"
        rows = export_table(cur, "location_names (light)",
            """SELECT ln.* FROM location_names ln
               JOIN locations l ON l.id = ln.location_id
               WHERE l.is_light = TRUE""", out_path)
        total_rows += rows

    # Person relationships (both persons must be light)
    if table_exists(cur, 'person_relationships'):
        out_path = OUTPUT_DIR / "person_relationships.csv"
        rows = export_table(cur, "person_relationships (light)",
            """SELECT pr.* FROM person_relationships pr
               JOIN persons p1 ON p1.id = pr.person_id
               JOIN persons p2 ON p2.id = pr.related_person_id
               WHERE p1.is_light = TRUE AND p2.is_light = TRUE""", out_path)
        total_rows += rows

    # Person locations (person must be light, location must be light)
    if table_exists(cur, 'person_locations'):
        out_path = OUTPUT_DIR / "person_locations.csv"
        rows = export_table(cur, "person_locations (light)",
            """SELECT pl.* FROM person_locations pl
               JOIN persons p ON p.id = pl.person_id
               JOIN locations l ON l.id = pl.location_id
               WHERE p.is_light = TRUE AND l.is_light = TRUE""", out_path)
        total_rows += rows

    # Location relationships (both locations must be light)
    if table_exists(cur, 'location_relationships'):
        out_path = OUTPUT_DIR / "location_relationships.csv"
        rows = export_table(cur, "location_relationships (light)",
            """SELECT lr.* FROM location_relationships lr
               JOIN locations l1 ON l1.id = lr.location_id
               JOIN locations l2 ON l2.id = lr.related_location_id
               WHERE l1.is_light = TRUE AND l2.is_light = TRUE""", out_path)
        total_rows += rows

    # QRank (only for light entities)
    if table_exists(cur, 'qrank'):
        out_path = OUTPUT_DIR / "qrank.csv"
        rows = export_table(cur, "qrank (light)",
            """SELECT q.* FROM qrank q
               WHERE q.wikidata_id IN (
                   SELECT wikidata_id FROM persons
                   WHERE is_light = TRUE AND wikidata_id IS NOT NULL
                   UNION
                   SELECT wikidata_id FROM events
                   WHERE wikidata_id IS NOT NULL
                   UNION
                   SELECT wikidata_id FROM locations
                   WHERE is_light = TRUE AND wikidata_id IS NOT NULL
               )""", out_path)
        total_rows += rows

    # ==========================================
    # 3. Source-dependent tables (minimal subset)
    # ==========================================

    # Event sources (all, small table)
    if table_exists(cur, 'event_sources'):
        out_path = OUTPUT_DIR / "event_sources.csv"
        rows = export_table(cur, "event_sources",
            "SELECT * FROM event_sources", out_path)
        total_rows += rows

    # Export sources referenced by event_sources or person_sources
    has_person_sources = table_exists(cur, 'person_sources')
    if table_exists(cur, 'event_sources') or has_person_sources:
        person_sources_clause = "UNION SELECT DISTINCT source_id FROM person_sources" if has_person_sources else ""
        out_path = OUTPUT_DIR / "sources.csv"
        rows = export_table(cur, "sources (connected)",
            f"""SELECT s.* FROM sources s
               WHERE s.id IN (
                   SELECT DISTINCT source_id FROM event_sources
                   {person_sources_clause}
               )""", out_path)
        total_rows += rows

    # ==========================================
    # Summary
    # ==========================================

    total_size = sum(f.stat().st_size for f in OUTPUT_DIR.glob("*.csv")) / (1024 * 1024)
    csv_count = len(list(OUTPUT_DIR.glob("*.csv")))

    print(f"\n{'='*70}")
    print(f"  Export complete!")
    print(f"  Files: {csv_count}")
    print(f"  Total rows: {total_rows:,}")
    print(f"  Total size: {total_size:.1f} MB")
    print(f"  Output: {OUTPUT_DIR}")
    print(f"{'='*70}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
