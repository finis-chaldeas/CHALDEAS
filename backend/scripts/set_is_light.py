"""
Set is_light flags on persons and events tables.

Light entities = those shown in Feed, Navigator, Globe markers by default.
Heavy entities = only accessible via explicit search.

Criteria (from 07_DATASET_SELECTION_CRITERIA.md):
- Persons: QRank top ~100K OR in event_persons OR manually curated
- Events: all current events are light (only 28K)
- Locations: all with events are light

Prerequisites:
- qrank table must exist and be populated
- Run AFTER import_qrank.py

Usage:
    cd backend
    python scripts/set_is_light.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.session import SessionLocal

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def add_is_light_columns(db):
    """Add is_light boolean column to persons, events, locations if not exists."""
    print("Adding is_light columns...")

    for table in ['persons', 'events', 'locations']:
        # Check if column exists
        exists = db.execute(text(f"""
            SELECT EXISTS(
                SELECT 1 FROM information_schema.columns
                WHERE table_name = '{table}' AND column_name = 'is_light'
            )
        """)).scalar()

        if exists:
            print(f"  {table}.is_light already exists")
        else:
            db.execute(text(f"ALTER TABLE {table} ADD COLUMN is_light BOOLEAN DEFAULT FALSE"))
            db.commit()
            print(f"  {table}.is_light added")

    # Create indexes for fast filtering
    for table in ['persons', 'events', 'locations']:
        db.execute(text(f"""
            CREATE INDEX IF NOT EXISTS idx_{table}_is_light
            ON {table}(is_light) WHERE is_light = TRUE
        """))
    db.commit()
    print("  Indexes created")


def set_persons_light(db):
    """
    Mark persons as light based on:
    1. In event_persons (connected to events) — ~90K persons
    2. QRank top 100K (popular on Wikipedia)
    3. Has role AND (birth_year OR death_year) — minimum useful data
    """
    print("\nSetting persons.is_light...")

    # Reset all to false first
    db.execute(text("UPDATE persons SET is_light = FALSE"))
    db.commit()
    print("  Reset all to FALSE")

    # 1. Persons connected to events (most important — these are historically significant)
    result = db.execute(text("""
        UPDATE persons SET is_light = TRUE
        WHERE id IN (SELECT DISTINCT person_id FROM event_persons)
          AND is_light = FALSE
    """))
    db.commit()
    count1 = result.rowcount
    print(f"  Event-connected persons: {count1:,}")

    # 2. QRank top 100K persons (popular, even if not event-connected yet)
    result = db.execute(text("""
        UPDATE persons p SET is_light = TRUE
        FROM (
            SELECT p2.id
            FROM persons p2
            JOIN qrank q ON q.wikidata_id = p2.wikidata_id
            WHERE p2.is_light = FALSE
            ORDER BY q.score DESC
            LIMIT 100000
        ) top
        WHERE p.id = top.id
    """))
    db.commit()
    count2 = result.rowcount
    print(f"  QRank top 100K (additional): {count2:,}")

    # Verify total
    total = db.execute(text("SELECT COUNT(*) FROM persons WHERE is_light = TRUE")).scalar()
    print(f"  Total light persons: {total:,} / 12.9M")


def set_events_light(db):
    """All events are light (only 28K, all are meaningful)."""
    print("\nSetting events.is_light...")

    result = db.execute(text("UPDATE events SET is_light = TRUE"))
    db.commit()
    print(f"  All events marked light: {result.rowcount:,}")


def set_locations_light(db):
    """
    Mark locations as light if they have events or are birthplaces/deathplaces of light persons.
    """
    print("\nSetting locations.is_light...")

    # Reset
    db.execute(text("UPDATE locations SET is_light = FALSE"))
    db.commit()

    # 1. Locations with events
    result = db.execute(text("""
        UPDATE locations SET is_light = TRUE
        WHERE id IN (
            SELECT DISTINCT primary_location_id FROM events WHERE primary_location_id IS NOT NULL
            UNION
            SELECT DISTINCT location_id FROM event_locations
        )
    """))
    db.commit()
    count1 = result.rowcount
    print(f"  Event-connected locations: {count1:,}")

    # 2. Birth/death places of light persons
    result = db.execute(text("""
        UPDATE locations SET is_light = TRUE
        WHERE is_light = FALSE AND id IN (
            SELECT birthplace_id FROM persons WHERE is_light = TRUE AND birthplace_id IS NOT NULL
            UNION
            SELECT deathplace_id FROM persons WHERE is_light = TRUE AND deathplace_id IS NOT NULL
        )
    """))
    db.commit()
    count2 = result.rowcount
    print(f"  Light person birth/death places (additional): {count2:,}")

    total = db.execute(text("SELECT COUNT(*) FROM locations WHERE is_light = TRUE")).scalar()
    print(f"  Total light locations: {total:,} / 2.3M")


def verify(db):
    """Print summary of light entity counts."""
    print(f"\n{'='*60}")
    print("  Light Entity Summary")
    print(f"{'='*60}")

    for table in ['persons', 'events', 'locations']:
        total = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        light = db.execute(text(f"SELECT COUNT(*) FROM {table} WHERE is_light = TRUE")).scalar()
        pct = (light / total * 100) if total > 0 else 0
        print(f"  {table:12s}: {light:>10,} / {total:>12,}  ({pct:.1f}%)")

    # Light persons by QRank distribution
    print("\n  Light persons QRank distribution:")
    result = db.execute(text("""
        SELECT
            CASE
                WHEN q.score > 10000000 THEN 'S-tier (10M+)'
                WHEN q.score > 1000000 THEN 'A-tier (1M-10M)'
                WHEN q.score > 100000 THEN 'B-tier (100K-1M)'
                ELSE 'C-tier (<100K)'
            END as tier,
            COUNT(*)
        FROM persons p
        LEFT JOIN qrank q ON q.wikidata_id = p.wikidata_id
        WHERE p.is_light = TRUE
        GROUP BY 1
        ORDER BY 1
    """)).fetchall()
    for row in result:
        print(f"    {row[0]:25s}: {row[1]:>8,}")


def main():
    db = SessionLocal()
    try:
        add_is_light_columns(db)
        set_events_light(db)
        set_persons_light(db)
        set_locations_light(db)
        verify(db)
        print("\nDone!")
    finally:
        db.close()


if __name__ == "__main__":
    main()
