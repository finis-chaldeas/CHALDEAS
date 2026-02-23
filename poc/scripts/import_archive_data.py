"""
Import Archive-extracted CSV data into Compact DB.

Reads CSVs from data/archive_extract/ and imports them into the running
Compact DB (C:\PostgreSQL\data, port 5432).

IMPORTANT: Make sure Compact DB is running:
    .\tools\switch-db.ps1 compact

Usage:
    python poc/scripts/import_archive_data.py
    python poc/scripts/import_archive_data.py --dry-run     # Preview only
    python poc/scripts/import_archive_data.py --tables sources_content_raw entity_narratives
"""

import argparse
import csv
import sys
import time
from pathlib import Path

import psycopg2

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_URL = "host=127.0.0.1 port=5432 dbname=chaldeas user=chaldeas password=chaldeas_dev"
CSV_DIR = Path("C:/Projects/Chaldeas/data/archive_extract")


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


def column_exists(cur, table_name, column_name):
    cur.execute("""
        SELECT EXISTS(
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s AND column_name = %s
        )
    """, (table_name, column_name))
    return cur.fetchone()[0]


def get_table_columns(cur, table_name):
    """Get list of column names for a table."""
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    return [row[0] for row in cur.fetchall()]


def import_sources_content_raw(cur, conn, csv_path, dry_run=False):
    """Import content_raw into existing sources table via UPDATE."""
    print(f"\n  --- Importing sources.content_raw ---")

    # Check if content_raw column exists, add if not
    if not column_exists(cur, 'sources', 'content_raw'):
        if dry_run:
            print(f"    Would add content_raw column to sources table")
        else:
            print(f"    Adding content_raw column to sources table...")
            cur.execute("ALTER TABLE sources ADD COLUMN content_raw TEXT")
            conn.commit()

    # Read CSV and update
    updated = 0
    skipped = 0
    not_found = 0

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        batch = []

        for row in reader:
            source_id = int(row['id'])
            content_raw = row.get('content_raw', '')

            if not content_raw or len(content_raw) < 100:
                skipped += 1
                continue

            batch.append((content_raw, source_id))

            if len(batch) >= 500:
                if not dry_run:
                    for content, sid in batch:
                        cur.execute("""
                            UPDATE sources SET content_raw = %s
                            WHERE id = %s
                        """, (content, sid))
                        if cur.rowcount > 0:
                            updated += 1
                        else:
                            not_found += 1
                    conn.commit()
                else:
                    updated += len(batch)
                batch = []

        # Remaining batch
        if batch:
            if not dry_run:
                for content, sid in batch:
                    cur.execute("""
                        UPDATE sources SET content_raw = %s
                        WHERE id = %s
                    """, (content, sid))
                    if cur.rowcount > 0:
                        updated += 1
                    else:
                        not_found += 1
                conn.commit()
            else:
                updated += len(batch)

    print(f"    Updated: {updated:,}")
    print(f"    Skipped (too short): {skipped:,}")
    if not_found > 0:
        print(f"    Not found in Compact DB: {not_found:,}")
    return updated


def import_person_sources(cur, conn, csv_path, dry_run=False):
    """Import person_sources junction table."""
    print(f"\n  --- Importing person_sources ---")

    if not table_exists(cur, 'person_sources'):
        if dry_run:
            print(f"    Would create person_sources table")
            return 0
        print(f"    Creating person_sources table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS person_sources (
                person_id INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
                source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
                page_reference VARCHAR(100),
                chunk_references JSONB DEFAULT '[]',
                PRIMARY KEY (person_id, source_id)
            )
        """)
        conn.commit()

    # Get valid person and source IDs from Compact DB
    cur.execute("SELECT id FROM persons")
    valid_person_ids = {row[0] for row in cur.fetchall()}
    cur.execute("SELECT id FROM sources")
    valid_source_ids = {row[0] for row in cur.fetchall()}

    imported = 0
    skipped = 0

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        batch = []

        for row in reader:
            person_id = int(row['person_id'])
            source_id = int(row['source_id'])

            # Only import if both person and source exist in Compact
            if person_id not in valid_person_ids or source_id not in valid_source_ids:
                skipped += 1
                continue

            page_ref = row.get('page_reference', None)
            chunk_refs = row.get('chunk_references', '[]')

            batch.append((person_id, source_id, page_ref, chunk_refs))

            if len(batch) >= 1000:
                if not dry_run:
                    for pid, sid, pref, cref in batch:
                        try:
                            cur.execute("""
                                INSERT INTO person_sources (person_id, source_id, page_reference, chunk_references)
                                VALUES (%s, %s, %s, %s)
                                ON CONFLICT (person_id, source_id) DO NOTHING
                            """, (pid, sid, pref, cref))
                        except Exception:
                            conn.rollback()
                            continue
                    conn.commit()
                imported += len(batch)
                batch = []

        if batch:
            if not dry_run:
                for pid, sid, pref, cref in batch:
                    try:
                        cur.execute("""
                            INSERT INTO person_sources (person_id, source_id, page_reference, chunk_references)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (person_id, source_id) DO NOTHING
                        """, (pid, sid, pref, cref))
                    except Exception:
                        conn.rollback()
                        continue
                conn.commit()
            imported += len(batch)

    print(f"    Imported: {imported:,}")
    print(f"    Skipped (FK missing): {skipped:,}")
    return imported


def import_table_with_copy(cur, conn, table_name, csv_path, dry_run=False, truncate=False):
    """Generic table import using COPY FROM STDIN."""
    print(f"\n  --- Importing {table_name} ---")

    if not table_exists(cur, table_name):
        print(f"    [SKIP] Table {table_name} does not exist in Compact DB")
        return 0

    # Count rows in CSV
    with open(csv_path, 'r', encoding='utf-8') as f:
        csv_row_count = sum(1 for _ in f) - 1

    if dry_run:
        print(f"    Would import {csv_row_count:,} rows into {table_name}")
        return csv_row_count

    # Get CSV columns and DB columns, import only matching ones
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        csv_columns = next(reader)

    db_columns = get_table_columns(cur, table_name)

    # Only import columns that exist in both CSV and DB
    matching_columns = [c for c in csv_columns if c in db_columns]

    if not matching_columns:
        print(f"    [SKIP] No matching columns between CSV and DB table")
        return 0

    missing_in_db = set(csv_columns) - set(db_columns)
    if missing_in_db:
        print(f"    [NOTE] CSV columns not in DB: {missing_in_db}")

    if truncate:
        cur.execute(f"TRUNCATE TABLE {table_name} CASCADE")
        conn.commit()

    # If columns match exactly, use COPY for speed
    if set(csv_columns) == set(matching_columns) and list(csv_columns) == list(matching_columns):
        copy_sql = f"COPY {table_name} ({', '.join(matching_columns)}) FROM STDIN WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')"
        start = time.time()
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                cur.copy_expert(copy_sql, f)
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"    [ERROR] COPY failed: {e}")
            print(f"    Falling back to row-by-row insert...")
            return import_table_row_by_row(cur, conn, table_name, csv_path, matching_columns)
    else:
        return import_table_row_by_row(cur, conn, table_name, csv_path, matching_columns)

    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    row_count = cur.fetchone()[0]
    elapsed = time.time() - start
    print(f"    Imported {row_count:,} rows ({elapsed:.1f}s)")
    return row_count


def import_table_row_by_row(cur, conn, table_name, csv_path, columns):
    """Fallback: row-by-row insert for column mismatch cases."""
    imported = 0
    errors = 0

    col_indices = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        for col in columns:
            if col in header:
                col_indices[col] = header.index(col)

    placeholders = ', '.join(['%s'] * len(columns))
    col_list = ', '.join(columns)
    insert_sql = f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        batch = []

        for row in reader:
            values = []
            for col in columns:
                idx = col_indices.get(col)
                if idx is not None and idx < len(row):
                    val = row[idx]
                    values.append(val if val != '' else None)
                else:
                    values.append(None)
            batch.append(tuple(values))

            if len(batch) >= 500:
                for vals in batch:
                    try:
                        cur.execute(insert_sql, vals)
                        imported += 1
                    except Exception:
                        conn.rollback()
                        errors += 1
                conn.commit()
                batch = []

        if batch:
            for vals in batch:
                try:
                    cur.execute(insert_sql, vals)
                    imported += 1
                except Exception:
                    conn.rollback()
                    errors += 1
            conn.commit()

    print(f"    Row-by-row: {imported:,} imported, {errors:,} errors")
    return imported


def main():
    parser = argparse.ArgumentParser(description="Import Archive data CSVs into Compact DB")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no changes")
    parser.add_argument("--tables", nargs="+", help="Import specific tables only")
    args = parser.parse_args()

    if not CSV_DIR.exists():
        print(f"ERROR: CSV directory not found: {CSV_DIR}")
        print("Run extract_from_archive.py first!")
        sys.exit(1)

    available_csvs = {f.stem: f for f in CSV_DIR.glob("*.csv")}
    print("=" * 70)
    print("  Archive Data Import to Compact DB")
    print("=" * 70)
    print(f"\n  CSV source: {CSV_DIR}")
    print(f"  Available CSVs: {', '.join(available_csvs.keys())}")
    if args.dry_run:
        print(f"  MODE: DRY RUN (no changes)")

    conn = get_conn()
    conn.set_client_encoding('UTF8')
    cur = conn.cursor()

    # Quick DB check
    cur.execute("SELECT COUNT(*) FROM persons")
    print(f"\n  Compact DB persons: {cur.fetchone()[0]:,}")
    cur.execute("SELECT COUNT(*) FROM events")
    print(f"  Compact DB events: {cur.fetchone()[0]:,}")
    cur.execute("SELECT COUNT(*) FROM sources")
    print(f"  Compact DB sources: {cur.fetchone()[0]:,}")

    total_imported = 0
    tables_to_import = args.tables if args.tables else None

    # 1. Sources content_raw (UPDATE, not INSERT)
    if "sources_content_raw" in available_csvs:
        if not tables_to_import or "sources_content_raw" in tables_to_import:
            rows = import_sources_content_raw(
                cur, conn,
                available_csvs["sources_content_raw"],
                dry_run=args.dry_run
            )
            total_imported += rows

    # 2. Person sources (junction table)
    if "person_sources" in available_csvs:
        if not tables_to_import or "person_sources" in tables_to_import:
            rows = import_person_sources(
                cur, conn,
                available_csvs["person_sources"],
                dry_run=args.dry_run
            )
            total_imported += rows

    # 3. Entity narratives (UPSERT)
    if "entity_narratives" in available_csvs:
        if not tables_to_import or "entity_narratives" in tables_to_import:
            rows = import_table_with_copy(
                cur, conn, "entity_narratives",
                available_csvs["entity_narratives"],
                dry_run=args.dry_run,
                truncate=True  # Replace existing
            )
            total_imported += rows

    # 4. Text mentions
    if "text_mentions" in available_csvs:
        if not tables_to_import or "text_mentions" in tables_to_import:
            rows = import_table_with_copy(
                cur, conn, "text_mentions",
                available_csvs["text_mentions"],
                dry_run=args.dry_run,
                truncate=True
            )
            total_imported += rows

    # 5. Entity properties
    if "entity_properties" in available_csvs:
        if not tables_to_import or "entity_properties" in tables_to_import:
            rows = import_table_with_copy(
                cur, conn, "entity_properties",
                available_csvs["entity_properties"],
                dry_run=args.dry_run,
                truncate=True
            )
            total_imported += rows

    # 6. Person detail (biography)
    if "person_detail" in available_csvs:
        if not tables_to_import or "person_detail" in tables_to_import:
            rows = import_table_with_copy(
                cur, conn, "person_detail",
                available_csvs["person_detail"],
                dry_run=args.dry_run,
                truncate=False  # Don't truncate, merge
            )
            total_imported += rows

    # Reset sequences for tables with serial IDs
    if not args.dry_run:
        for table_name in ['entity_narratives', 'text_mentions', 'entity_properties']:
            if table_exists(cur, table_name):
                try:
                    cur.execute(f"SELECT pg_get_serial_sequence('{table_name}', 'id')")
                    result = cur.fetchone()
                    if result and result[0]:
                        cur.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table_name}")
                        max_id = cur.fetchone()[0]
                        if max_id > 0:
                            cur.execute(f"SELECT setval('{result[0]}', {max_id})")
                except Exception:
                    pass
        conn.commit()

        # ANALYZE
        conn.autocommit = True
        cur.execute("ANALYZE")

    # Verification
    print(f"\n{'='*70}")
    print(f"  Import Summary")
    print(f"{'='*70}")
    print(f"  Total rows imported: {total_imported:,}")

    if not args.dry_run:
        print(f"\n  Verification:")
        if column_exists(cur, 'sources', 'content_raw'):
            cur.execute("SELECT COUNT(*) FROM sources WHERE content_raw IS NOT NULL")
            print(f"    Sources with content_raw: {cur.fetchone()[0]:,}")
        if table_exists(cur, 'person_sources'):
            cur.execute("SELECT COUNT(*) FROM person_sources")
            print(f"    Person-source links: {cur.fetchone()[0]:,}")
        if table_exists(cur, 'entity_narratives'):
            cur.execute("SELECT COUNT(*) FROM entity_narratives")
            print(f"    Entity narratives: {cur.fetchone()[0]:,}")
        if table_exists(cur, 'text_mentions'):
            cur.execute("SELECT COUNT(*) FROM text_mentions")
            print(f"    Text mentions: {cur.fetchone()[0]:,}")

    print(f"\n{'='*70}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
