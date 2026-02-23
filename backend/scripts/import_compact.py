"""
Import compact CSV data into a fresh PostgreSQL database.

Assumes:
    - Schema already created via `alembic upgrade head`
    - CSV files in C:\\Projects\\Chaldeas\\data\\compact_export\\
    - PostgreSQL running on port 5432 (compact DB on C:)

Usage:
    cd backend
    python scripts/import_compact.py

Import order respects FK dependencies:
    1. alembic_version, categories, periods
    2. locations, location_names
    3. persons
    4. events
    5. polities
    6. sources (minimal subset)
    7. Junction tables (event_persons, event_locations, etc.)
    8. qrank
"""
import sys
import time
from pathlib import Path

import psycopg2

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_URL = "host=127.0.0.1 port=5432 dbname=chaldeas user=chaldeas password=chaldeas_dev"
CSV_DIR = Path("C:/Projects/Chaldeas/data/compact_export")

# Import order (FK-safe): parents before children
IMPORT_ORDER = [
    # 0. Migration tracking (no deps)
    "alembic_version",
    # 1. Independent tables
    "categories",
    "periods",
    "masters",
    "import_batches",
    # 2. Locations (self-referential FKs handled by disabling triggers)
    "locations",
    "location_names",
    # 3. Persons (depends on categories, locations)
    "persons",
    # 4. Events (depends on categories, locations, periods)
    "events",
    # 5. Polities (depends on locations)
    "polities",
    # 6. Sources (minimal subset for FK integrity)
    "sources",
    # 7. Junction / association tables
    "event_persons",
    "event_locations",
    "event_sources",
    "person_sources",
    "person_detail",
    "event_connections",
    "event_relationships",
    "historical_chains",
    "chain_segments",
    "chain_entity_roles",
    "person_relationships",
    "person_locations",
    "location_relationships",
    "entity_aliases",
    # 8. Narrative / mention tables
    "entity_narratives",
    "text_mentions",
    "entity_properties",
    # 9. Histories
    "histories",
    "history_entities",
    # 10. QRank (independent, but import last)
    "qrank",
]

# Tables with serial/identity PKs that need sequence resets
TABLES_WITH_SERIAL_ID = [
    "categories", "locations", "location_names", "persons", "events",
    "polities", "sources", "event_connections", "event_relationships",
    "historical_chains", "chain_segments", "chain_entity_roles",
    "masters", "import_batches", "entity_aliases", "periods",
    "entity_narratives", "text_mentions", "entity_properties",
    "histories", "history_entities",
]


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


def import_table(cur, table_name, csv_path):
    """Import CSV into table using COPY FROM STDIN."""
    copy_sql = f"COPY {table_name} FROM STDIN WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')"

    start = time.time()
    with open(csv_path, 'r', encoding='utf-8') as f:
        cur.copy_expert(copy_sql, f)

    # Count imported rows
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    row_count = cur.fetchone()[0]
    elapsed = time.time() - start
    size_mb = csv_path.stat().st_size / (1024 * 1024)
    print(f"  {table_name:30s}  {row_count:>10,} rows  {size_mb:>8.1f} MB  ({elapsed:.1f}s)")
    return row_count


def reset_sequence(cur, table_name):
    """Reset the serial sequence to MAX(id) + 1 for a table."""
    # Find the sequence name
    cur.execute("""
        SELECT pg_get_serial_sequence(%s, 'id')
    """, (table_name,))
    result = cur.fetchone()
    if result and result[0]:
        seq_name = result[0]
        cur.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table_name}")
        max_id = cur.fetchone()[0]
        if max_id > 0:
            cur.execute(f"SELECT setval('{seq_name}', {max_id})")


def main():
    if not CSV_DIR.exists():
        print(f"ERROR: CSV directory not found: {CSV_DIR}")
        print("Run export_compact.py first!")
        sys.exit(1)

    available_csvs = {f.stem: f for f in CSV_DIR.glob("*.csv")}
    print("=" * 70)
    print("  CHALDEAS Compact DB Import")
    print("=" * 70)
    print(f"\n  CSV source: {CSV_DIR}")
    print(f"  Available CSVs: {len(available_csvs)}")
    print(f"  Tables to import: {', '.join(available_csvs.keys())}")

    conn = get_conn()
    conn.set_client_encoding('UTF8')
    conn.autocommit = False
    cur = conn.cursor()

    # Disable triggers on ALL tables to bypass FK checks during bulk load
    print("\n  Disabling triggers for bulk import...")
    cur.execute("""
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    """)
    all_tables = [row[0] for row in cur.fetchall()]
    for t in all_tables:
        cur.execute(f"ALTER TABLE {t} DISABLE TRIGGER ALL")
    conn.commit()

    # Truncate tables that will be imported (reverse order to respect FKs conceptually)
    print("  Truncating target tables...")
    for table_name in reversed(IMPORT_ORDER):
        if table_name in available_csvs and table_exists(cur, table_name):
            cur.execute(f"TRUNCATE TABLE {table_name} CASCADE")
    conn.commit()

    # Import tables in order
    print(f"\n  {'Table':30s}  {'Rows':>10s}  {'Size':>8s}  Time")
    print(f"  {'-'*30}  {'-'*10}  {'-'*8}  {'-'*6}")

    total_rows = 0
    imported_count = 0
    skipped = []

    for table_name in IMPORT_ORDER:
        csv_path = available_csvs.get(table_name)
        if csv_path is None:
            continue  # CSV not exported, skip silently

        if not table_exists(cur, table_name):
            skipped.append(f"{table_name} (table not in DB)")
            continue

        # Skip empty CSVs (header only)
        if csv_path.stat().st_size < 10:
            skipped.append(f"{table_name} (empty CSV)")
            continue

        try:
            rows = import_table(cur, table_name, csv_path)
            total_rows += rows
            imported_count += 1
            conn.commit()
        except Exception as e:
            conn.rollback()
            # Re-disable triggers after rollback
            for t in all_tables:
                cur.execute(f"ALTER TABLE {t} DISABLE TRIGGER ALL")
            conn.commit()
            print(f"  {table_name:30s}  FAILED: {e}")
            skipped.append(f"{table_name} (error: {e})")

    # Reset sequences
    print("\n  Resetting sequences...")
    for table_name in TABLES_WITH_SERIAL_ID:
        if table_exists(cur, table_name):
            try:
                reset_sequence(cur, table_name)
            except Exception:
                pass  # Some tables might not have sequences
    conn.commit()

    # Re-enable triggers
    print("  Re-enabling triggers...")
    for t in all_tables:
        try:
            cur.execute(f"ALTER TABLE {t} ENABLE TRIGGER ALL")
        except Exception:
            pass
    conn.commit()

    # Run ANALYZE for query planner stats
    print("  Running ANALYZE...")
    conn.autocommit = True
    cur.execute("ANALYZE")

    # Verify
    print(f"\n{'='*70}")
    print("  Import Summary")
    print(f"{'='*70}")
    print(f"  Tables imported: {imported_count}")
    print(f"  Total rows:      {total_rows:,}")

    if skipped:
        print(f"\n  Skipped ({len(skipped)}):")
        for s in skipped:
            print(f"    - {s}")

    # Quick verification counts
    print(f"\n  Verification:")
    for table in ['persons', 'events', 'locations', 'categories', 'qrank']:
        if table_exists(cur, table):
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"    {table:20s}: {count:>10,}")

    print(f"\n{'='*70}")
    print("  Import complete! DB is ready.")
    print(f"{'='*70}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
