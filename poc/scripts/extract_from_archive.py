"""
Extract data from Archive DB (E:\PostgreSQL\data) to CSV files.

This script connects to the Archive DB (must be running on port 5432)
and extracts content_raw, entity_narratives, text_mentions, and
entity_properties for entities that exist in Compact DB.

IMPORTANT: Before running this script:
    .\tools\switch-db.ps1 archive   # Start Archive DB on port 5432

After running:
    .\tools\switch-db.ps1 compact   # Switch back to Compact DB
    python poc/scripts/import_archive_data.py  # Import CSVs

Output: data/archive_extract/*.csv

Usage:
    python poc/scripts/extract_from_archive.py
    python poc/scripts/extract_from_archive.py --dry-run   # Preview counts only
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
OUTPUT_DIR = Path("C:/Projects/Chaldeas/data/archive_extract")

# Compact DB entity IDs (loaded from compact_export CSVs)
COMPACT_EXPORT_DIR = Path("C:/Projects/Chaldeas/data/compact_export")


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


def load_compact_ids(table_name):
    """Load entity IDs from compact_export CSVs (to know what's in Compact DB)."""
    csv_path = COMPACT_EXPORT_DIR / f"{table_name}.csv"
    if not csv_path.exists():
        print(f"  [WARN] {csv_path} not found. Will extract all from Archive.")
        return None

    ids = set()
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'id' in row:
                try:
                    ids.add(int(row['id']))
                except (ValueError, TypeError):
                    pass
    return ids


def export_with_copy(cur, query, output_path, description):
    """Export query result to CSV using COPY TO STDOUT."""
    copy_sql = f"COPY ({query}) TO STDOUT WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')"
    start = time.time()

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        cur.copy_expert(copy_sql, f)

    # Count rows
    with open(output_path, 'r', encoding='utf-8') as f:
        row_count = sum(1 for _ in f) - 1  # subtract header

    elapsed = time.time() - start
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  {description:40s}  {row_count:>10,} rows  {size_mb:>8.1f} MB  ({elapsed:.1f}s)")
    return row_count


def main():
    parser = argparse.ArgumentParser(description="Extract data from Archive DB to CSV")
    parser.add_argument("--dry-run", action="store_true", help="Preview counts only, don't extract")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = get_conn()
    conn.set_client_encoding('UTF8')
    cur = conn.cursor()

    print("=" * 70)
    print("  Archive DB Data Extraction")
    print("=" * 70)

    # Verify we're connected to Archive (check for content_raw)
    has_content_raw = column_exists(cur, 'sources', 'content_raw')
    if not has_content_raw:
        print("\n  [ERROR] sources.content_raw column not found!")
        print("  Make sure Archive DB is running: .\\tools\\switch-db.ps1 archive")
        cur.close()
        conn.close()
        sys.exit(1)

    # Quick stats
    cur.execute("SELECT COUNT(*) FROM sources WHERE content_raw IS NOT NULL AND LENGTH(content_raw) > 100")
    total_content_raw = cur.fetchone()[0]
    print(f"\n  Archive sources with content_raw: {total_content_raw:,}")

    cur.execute("SELECT COUNT(*) FROM persons")
    total_persons = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM events")
    total_events = cur.fetchone()[0]
    print(f"  Archive persons: {total_persons:,}")
    print(f"  Archive events: {total_events:,}")

    # Check optional tables
    has_entity_narratives = table_exists(cur, 'entity_narratives')
    has_text_mentions = table_exists(cur, 'text_mentions')
    has_entity_properties = table_exists(cur, 'entity_properties')
    has_person_sources = table_exists(cur, 'person_sources')
    has_person_detail = table_exists(cur, 'person_detail')

    print(f"\n  Tables available:")
    print(f"    entity_narratives: {'YES' if has_entity_narratives else 'NO'}")
    print(f"    text_mentions:     {'YES' if has_text_mentions else 'NO'}")
    print(f"    entity_properties: {'YES' if has_entity_properties else 'NO'}")
    print(f"    person_sources:    {'YES' if has_person_sources else 'NO'}")
    print(f"    person_detail:     {'YES' if has_person_detail else 'NO'}")

    if args.dry_run:
        print("\n  === DRY RUN: Extraction Counts ===")

        # 1. Sources with content_raw (connected to events or persons)
        cur.execute("""
            SELECT COUNT(DISTINCT s.id) FROM sources s
            WHERE s.content_raw IS NOT NULL AND LENGTH(s.content_raw) > 100
              AND (
                  s.id IN (SELECT source_id FROM event_sources)
                  OR s.id IN (SELECT source_id FROM person_sources)
              )
        """)
        print(f"    Sources (content_raw, connected): {cur.fetchone()[0]:,}")

        if has_entity_narratives:
            cur.execute("SELECT COUNT(*) FROM entity_narratives")
            print(f"    Entity narratives: {cur.fetchone()[0]:,}")

        if has_text_mentions:
            cur.execute("SELECT COUNT(*) FROM text_mentions")
            print(f"    Text mentions (total): {cur.fetchone()[0]:,}")

        if has_entity_properties:
            cur.execute("SELECT COUNT(*) FROM entity_properties")
            print(f"    Entity properties (total): {cur.fetchone()[0]:,}")

        if has_person_sources:
            cur.execute("SELECT COUNT(*) FROM person_sources")
            print(f"    Person-source links: {cur.fetchone()[0]:,}")

        if has_person_detail:
            cur.execute("SELECT COUNT(*) FROM person_detail WHERE biography IS NOT NULL AND LENGTH(biography) > 50")
            print(f"    Person details (with bio): {cur.fetchone()[0]:,}")

        print("\n  Run without --dry-run to extract.")
        cur.close()
        conn.close()
        return

    # ============================================
    # EXTRACTION
    # ============================================

    total_rows = 0
    print(f"\n  {'Description':40s}  {'Rows':>10s}  {'Size':>8s}  Time")
    print(f"  {'-'*40}  {'-'*10}  {'-'*8}  {'-'*6}")

    # 1. Sources content_raw (only connected sources)
    rows = export_with_copy(cur, """
        SELECT s.id, s.content_raw
        FROM sources s
        WHERE s.content_raw IS NOT NULL AND LENGTH(s.content_raw) > 100
          AND (
              s.id IN (SELECT source_id FROM event_sources)
              OR s.id IN (SELECT source_id FROM person_sources)
          )
    """, OUTPUT_DIR / "sources_content_raw.csv", "sources.content_raw (connected)")
    total_rows += rows

    # 2. Person sources (junction table)
    if has_person_sources:
        rows = export_with_copy(cur, """
            SELECT * FROM person_sources
        """, OUTPUT_DIR / "person_sources.csv", "person_sources (all)")
        total_rows += rows

    # 3. Entity narratives (all - already curated by GPT-5.1)
    if has_entity_narratives:
        rows = export_with_copy(cur, """
            SELECT * FROM entity_narratives
        """, OUTPUT_DIR / "entity_narratives.csv", "entity_narratives (all)")
        total_rows += rows

    # 4. Text mentions (all)
    if has_text_mentions:
        rows = export_with_copy(cur, """
            SELECT * FROM text_mentions
        """, OUTPUT_DIR / "text_mentions.csv", "text_mentions (all)")
        total_rows += rows

    # 5. Entity properties (if exists)
    if has_entity_properties:
        rows = export_with_copy(cur, """
            SELECT * FROM entity_properties
        """, OUTPUT_DIR / "entity_properties.csv", "entity_properties (all)")
        total_rows += rows

    # 6. Person detail (biography data)
    if has_person_detail:
        rows = export_with_copy(cur, """
            SELECT * FROM person_detail
            WHERE biography IS NOT NULL AND LENGTH(biography) > 10
        """, OUTPUT_DIR / "person_detail.csv", "person_detail (with biography)")
        total_rows += rows

    # 7. Full sources table (for metadata + content_raw)
    # Export all source records that are connected, with all columns
    rows = export_with_copy(cur, """
        SELECT * FROM sources
        WHERE id IN (SELECT source_id FROM event_sources)
           OR id IN (SELECT source_id FROM person_sources)
    """, OUTPUT_DIR / "sources_full.csv", "sources (full records, connected)")
    total_rows += rows

    # Summary
    total_size = sum(f.stat().st_size for f in OUTPUT_DIR.glob("*.csv")) / (1024 * 1024)
    csv_count = len(list(OUTPUT_DIR.glob("*.csv")))

    print(f"\n{'='*70}")
    print(f"  Extraction complete!")
    print(f"  Files: {csv_count}")
    print(f"  Total rows: {total_rows:,}")
    print(f"  Total size: {total_size:.1f} MB")
    print(f"  Output: {OUTPUT_DIR}")
    print(f"\n  Next steps:")
    print(f"    1. .\\tools\\switch-db.ps1 compact")
    print(f"    2. python poc/scripts/import_archive_data.py")
    print(f"{'='*70}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
