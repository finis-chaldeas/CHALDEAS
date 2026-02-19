"""
Batched Person Enrichment from entity_properties.

Unlike enrich_persons.sql (single transaction), this runs each UPDATE
as a separate transaction and batches the heavy role UPDATE.

Usage:
    cd backend
    python scripts/enrich_persons_batched.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.session import SessionLocal

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def run_update(db, name: str, sql: str):
    """Run a single UPDATE in its own transaction with timing."""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    start = time.time()
    result = db.execute(text(sql))
    db.commit()
    elapsed = time.time() - start
    rows = result.rowcount
    print(f"  Updated: {rows:,} rows in {elapsed:.1f}s")
    return rows


def run_role_batched(db, batch_size: int = 500_000):
    """Run role UPDATE in batches to avoid long locks."""
    print(f"\n{'='*60}")
    print(f"  role (P106) — batched, {batch_size:,} rows per batch")
    print(f"{'='*60}")

    total_updated = 0
    batch_num = 0
    start_total = time.time()

    while True:
        batch_num += 1
        start = time.time()

        result = db.execute(text(f"""
            UPDATE persons p SET role = sub.occ
            FROM (
                SELECT DISTINCT ON (ep.entity_id) ep.entity_id,
                    COALESCE(ep.value_string, ep.property_name) as occ
                FROM entity_properties ep
                JOIN persons p2 ON p2.id = ep.entity_id
                WHERE ep.entity_type = 'person' AND ep.property = 'P106'
                  AND (ep.value_string IS NOT NULL OR ep.property_name IS NOT NULL)
                  AND (p2.role IS NULL OR p2.role = '')
                ORDER BY ep.entity_id, ep.id
                LIMIT {batch_size}
            ) sub
            WHERE sub.entity_id = p.id AND (p.role IS NULL OR p.role = '')
        """))
        db.commit()

        rows = result.rowcount
        elapsed = time.time() - start
        total_updated += rows
        print(f"  Batch {batch_num}: {rows:,} rows in {elapsed:.1f}s (total: {total_updated:,})")

        if rows == 0 or rows < batch_size:
            break

    elapsed_total = time.time() - start_total
    print(f"  Role total: {total_updated:,} rows in {elapsed_total:.1f}s")
    return total_updated


def verify(db):
    """Print current enrichment status."""
    print(f"\n{'='*60}")
    print(f"  Verification")
    print(f"{'='*60}")

    checks = [
        ("birth_year", "SELECT COUNT(*) FROM persons WHERE birth_year IS NOT NULL"),
        ("death_year", "SELECT COUNT(*) FROM persons WHERE death_year IS NOT NULL"),
        ("birthplace_id", "SELECT COUNT(*) FROM persons WHERE birthplace_id IS NOT NULL"),
        ("deathplace_id", "SELECT COUNT(*) FROM persons WHERE deathplace_id IS NOT NULL"),
        ("role", "SELECT COUNT(*) FROM persons WHERE role IS NOT NULL AND role != ''"),
    ]

    for name, sql in checks:
        count = db.execute(text(sql)).scalar()
        print(f"  {name:20s}: {count:>12,}")


def main():
    db = SessionLocal()
    try:
        # 1. birth_year
        run_update(db, "birth_year (P569)", """
            UPDATE persons p SET birth_year = ep.value_year
            FROM entity_properties ep
            WHERE ep.entity_type = 'person' AND ep.entity_id = p.id
              AND ep.property = 'P569' AND ep.value_year IS NOT NULL
              AND p.birth_year IS NULL
        """)

        # 2. death_year
        run_update(db, "death_year (P570)", """
            UPDATE persons p SET death_year = ep.value_year
            FROM entity_properties ep
            WHERE ep.entity_type = 'person' AND ep.entity_id = p.id
              AND ep.property = 'P570' AND ep.value_year IS NOT NULL
              AND p.death_year IS NULL
        """)

        # 3. birthplace_id
        run_update(db, "birthplace_id (P19)", """
            UPDATE persons p SET birthplace_id = l.id
            FROM entity_properties ep
            JOIN locations l ON l.wikidata_id = ep.value_qid
            WHERE ep.entity_type = 'person' AND ep.entity_id = p.id
              AND ep.property = 'P19' AND ep.value_qid IS NOT NULL
              AND p.birthplace_id IS NULL
        """)

        # 4. deathplace_id
        run_update(db, "deathplace_id (P20)", """
            UPDATE persons p SET deathplace_id = l.id
            FROM entity_properties ep
            JOIN locations l ON l.wikidata_id = ep.value_qid
            WHERE ep.entity_type = 'person' AND ep.entity_id = p.id
              AND ep.property = 'P20' AND ep.value_qid IS NOT NULL
              AND p.deathplace_id IS NULL
        """)

        # 5. role (batched)
        run_role_batched(db, batch_size=500_000)

        # Verification
        verify(db)

        print("\nDone!")

    finally:
        db.close()


if __name__ == "__main__":
    main()
