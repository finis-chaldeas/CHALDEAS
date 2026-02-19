"""
Import QRank data (Wikidata entity popularity scores).

QRank (qrank.toolforge.org) provides page-view-based popularity scores
for all Wikidata entities across all Wikimedia projects. CC0 license.

Usage:
    cd backend
    python scripts/import_qrank.py
"""
import gzip
import io
import os
import sys
import csv
import urllib.request
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.session import SessionLocal

QRANK_URL = "https://qrank.wmcloud.org/download/qrank.csv.gz"
QRANK_CACHE = Path(__file__).parent / "qrank.csv.gz"
BATCH_SIZE = 50_000


def download_qrank():
    """Download QRank CSV (gzipped, ~100MB)."""
    if QRANK_CACHE.exists():
        size_mb = QRANK_CACHE.stat().st_size / (1024 * 1024)
        print(f"Using cached QRank file: {QRANK_CACHE} ({size_mb:.1f} MB)")
        return QRANK_CACHE

    print(f"Downloading QRank from {QRANK_URL}...")
    urllib.request.urlretrieve(QRANK_URL, QRANK_CACHE)
    size_mb = QRANK_CACHE.stat().st_size / (1024 * 1024)
    print(f"Downloaded: {size_mb:.1f} MB")
    return QRANK_CACHE


def create_qrank_table(db):
    """Create qrank table if not exists."""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS qrank (
            wikidata_id VARCHAR(20) PRIMARY KEY,
            score BIGINT NOT NULL
        )
    """))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_qrank_score ON qrank(score DESC)"))
    db.commit()
    print("qrank table ready.")


def import_qrank_data(db, filepath):
    """Parse and import QRank CSV into database."""
    # Truncate existing data for clean reimport
    db.execute(text("TRUNCATE TABLE qrank"))
    db.commit()

    total = 0
    batch = []

    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        reader = csv.reader(f)
        # Skip header line(s) - QRank CSV has: Entity,QRank
        for row in reader:
            if len(row) < 2:
                continue
            qid = row[0].strip()
            score_str = row[1].strip()

            # Skip header
            if qid == 'Entity' or not qid.startswith('Q'):
                continue

            try:
                score = int(score_str)
            except ValueError:
                continue

            batch.append({"wikidata_id": qid, "score": score})
            total += 1

            if len(batch) >= BATCH_SIZE:
                _insert_batch(db, batch)
                batch.clear()
                print(f"  Imported {total:,} rows...")

    if batch:
        _insert_batch(db, batch)

    db.commit()
    print(f"Total imported: {total:,} QRank scores.")
    return total


def _insert_batch(db, batch):
    """Insert a batch using COPY-like efficiency."""
    db.execute(
        text("""
            INSERT INTO qrank (wikidata_id, score)
            VALUES (:wikidata_id, :score)
            ON CONFLICT (wikidata_id) DO UPDATE SET score = EXCLUDED.score
        """),
        batch
    )
    db.commit()


def verify_import(db):
    """Verify import by checking join counts with events/persons."""
    result = db.execute(text("""
        SELECT
            (SELECT COUNT(*) FROM qrank) as total_qrank,
            (SELECT COUNT(*) FROM events e JOIN qrank q ON q.wikidata_id = e.wikidata_id) as matched_events,
            (SELECT COUNT(*) FROM persons p JOIN qrank q ON q.wikidata_id = p.wikidata_id) as matched_persons
    """)).fetchone()

    print(f"\nVerification:")
    print(f"  Total QRank entries: {result[0]:,}")
    print(f"  Matched events:     {result[1]:,}")
    print(f"  Matched persons:    {result[2]:,}")


def main():
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    filepath = download_qrank()
    db = SessionLocal()
    try:
        create_qrank_table(db)
        import_qrank_data(db, filepath)
        verify_import(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
