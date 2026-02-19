"""
Enrich only light-candidate persons from entity_properties.

Instead of scanning ALL 12.9M persons (extremely slow on USB HDD),
this script:
1. First marks light persons (event_persons + QRank top 100K)
2. Only enriches those ~100-150K persons

This is 100x faster than enrich_persons_batched.py.

Usage:
    cd backend
    python scripts/enrich_light_persons.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.session import SessionLocal

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def step1_mark_light_persons(db):
    """Mark persons as is_light based on event_persons + QRank."""
    print("\n" + "=" * 60)
    print("  Step 1: Mark light persons")
    print("=" * 60)

    # Reset
    start = time.time()
    db.execute(text("UPDATE persons SET is_light = FALSE WHERE is_light = TRUE"))
    db.commit()
    print(f"  Reset in {time.time() - start:.1f}s")

    # 1a. Event-connected persons
    start = time.time()
    result = db.execute(text("""
        UPDATE persons SET is_light = TRUE
        WHERE id IN (SELECT DISTINCT person_id FROM event_persons)
    """))
    db.commit()
    count1 = result.rowcount
    print(f"  Event-connected: {count1:,} in {time.time() - start:.1f}s")

    # 1b. QRank top 100K (not already light)
    start = time.time()
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
    print(f"  QRank top 100K (additional): {count2:,} in {time.time() - start:.1f}s")

    total = db.execute(text("SELECT COUNT(*) FROM persons WHERE is_light = TRUE")).scalar()
    print(f"  Total light persons: {total:,}")
    return total


def step2_enrich_light(db):
    """Enrich only light persons with data from entity_properties."""
    print("\n" + "=" * 60)
    print("  Step 2: Enrich light persons only")
    print("=" * 60)

    # 2a. birthplace_id (only for light persons)
    start = time.time()
    result = db.execute(text("""
        UPDATE persons p SET birthplace_id = l.id
        FROM entity_properties ep
        JOIN locations l ON l.wikidata_id = ep.value_qid
        WHERE ep.entity_type = 'person' AND ep.entity_id = p.id
          AND ep.property = 'P19' AND ep.value_qid IS NOT NULL
          AND p.birthplace_id IS NULL
          AND p.is_light = TRUE
    """))
    db.commit()
    print(f"  birthplace_id: {result.rowcount:,} rows in {time.time() - start:.1f}s")

    # 2b. deathplace_id (only for light persons)
    start = time.time()
    result = db.execute(text("""
        UPDATE persons p SET deathplace_id = l.id
        FROM entity_properties ep
        JOIN locations l ON l.wikidata_id = ep.value_qid
        WHERE ep.entity_type = 'person' AND ep.entity_id = p.id
          AND ep.property = 'P20' AND ep.value_qid IS NOT NULL
          AND p.deathplace_id IS NULL
          AND p.is_light = TRUE
    """))
    db.commit()
    print(f"  deathplace_id: {result.rowcount:,} rows in {time.time() - start:.1f}s")

    # 2c. role (only for light persons, no batching needed for ~100K)
    start = time.time()
    result = db.execute(text("""
        UPDATE persons p SET role = sub.occ
        FROM (
            SELECT DISTINCT ON (ep.entity_id) ep.entity_id,
                COALESCE(ep.value_string, ep.property_name) as occ
            FROM entity_properties ep
            JOIN persons p2 ON p2.id = ep.entity_id
            WHERE ep.entity_type = 'person' AND ep.property = 'P106'
              AND (ep.value_string IS NOT NULL OR ep.property_name IS NOT NULL)
              AND (p2.role IS NULL OR p2.role = '')
              AND p2.is_light = TRUE
            ORDER BY ep.entity_id, ep.id
        ) sub
        WHERE sub.entity_id = p.id AND (p.role IS NULL OR p.role = '')
    """))
    db.commit()
    print(f"  role: {result.rowcount:,} rows in {time.time() - start:.1f}s")


def step3_set_locations_light(db):
    """Mark locations as light if connected to events or light persons."""
    print("\n" + "=" * 60)
    print("  Step 3: Set locations light")
    print("=" * 60)

    start = time.time()
    db.execute(text("UPDATE locations SET is_light = FALSE WHERE is_light = TRUE"))
    db.commit()

    # Event-connected locations
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
    print(f"  Event-connected: {count1:,}")

    # Birth/death places of light persons
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
    print(f"  Light person places (additional): {count2:,}")

    total = db.execute(text("SELECT COUNT(*) FROM locations WHERE is_light = TRUE")).scalar()
    print(f"  Total light locations: {total:,} in {time.time() - start:.1f}s")


def step4_verify(db):
    """Print summary."""
    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)

    for table in ['persons', 'events', 'locations']:
        total = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        light = db.execute(text(f"SELECT COUNT(*) FROM {table} WHERE is_light = TRUE")).scalar()
        pct = (light / total * 100) if total > 0 else 0
        print(f"  {table:12s}: {light:>10,} / {total:>12,}  ({pct:.1f}%)")

    # Enrichment check for light persons
    print("\n  Light person enrichment:")
    checks = [
        ("birth_year", "SELECT COUNT(*) FROM persons WHERE birth_year IS NOT NULL AND is_light = TRUE"),
        ("death_year", "SELECT COUNT(*) FROM persons WHERE death_year IS NOT NULL AND is_light = TRUE"),
        ("birthplace_id", "SELECT COUNT(*) FROM persons WHERE birthplace_id IS NOT NULL AND is_light = TRUE"),
        ("role", "SELECT COUNT(*) FROM persons WHERE role IS NOT NULL AND role <> '' AND is_light = TRUE"),
    ]
    light_total = db.execute(text("SELECT COUNT(*) FROM persons WHERE is_light = TRUE")).scalar()
    for name, sql in checks:
        count = db.execute(text(sql)).scalar()
        pct = (count / light_total * 100) if light_total > 0 else 0
        print(f"    {name:20s}: {count:>8,} / {light_total:,} ({pct:.1f}%)")

    # Create indexes
    print("\n  Creating indexes...")
    for table in ['persons', 'events', 'locations']:
        db.execute(text(f"""
            CREATE INDEX IF NOT EXISTS idx_{table}_is_light
            ON {table}(is_light) WHERE is_light = TRUE
        """))
    db.commit()
    print("  Indexes created")


def main():
    db = SessionLocal()
    try:
        step1_mark_light_persons(db)
        step2_enrich_light(db)
        step3_set_locations_light(db)
        step4_verify(db)
        print("\nDone!")
    finally:
        db.close()


if __name__ == "__main__":
    main()
