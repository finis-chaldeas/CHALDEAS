"""
Compute composite importance scores for events and persons.

Uses QRank (page-view popularity), connection counts, and participant counts
to assign importance 1-5 via NTILE(5).

Usage:
    cd backend
    python scripts/compute_importance.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.session import SessionLocal


def compute_event_importance(db):
    """
    Events importance (1-5):
    raw_score = 0.50 * qrank_percentile + 0.30 * connection_count_percentile + 0.20 * participant_count_percentile
    importance = NTILE(5) over raw_score
    """
    print("Computing event importance...")

    # Check prerequisites
    qrank_count = db.execute(text(
        "SELECT COUNT(*) FROM events e JOIN qrank q ON q.wikidata_id = e.wikidata_id"
    )).scalar()
    print(f"  Events with QRank data: {qrank_count:,}")

    db.execute(text("""
        WITH event_scores AS (
            SELECT
                e.id,
                COALESCE(q.score, 0) as qrank_score,
                COALESCE(e.connection_count, 0) as conn_count,
                COALESCE(
                    (SELECT COUNT(*) FROM event_persons ep WHERE ep.event_id = e.id),
                    0
                ) as participant_count
            FROM events e
            LEFT JOIN qrank q ON q.wikidata_id = e.wikidata_id
            WHERE e.wikidata_id IS NOT NULL
        ),
        event_percentiles AS (
            SELECT
                id,
                PERCENT_RANK() OVER (ORDER BY qrank_score) as qrank_pct,
                PERCENT_RANK() OVER (ORDER BY conn_count) as conn_pct,
                PERCENT_RANK() OVER (ORDER BY participant_count) as part_pct
            FROM event_scores
        ),
        event_composite AS (
            SELECT
                id,
                0.50 * qrank_pct + 0.30 * conn_pct + 0.20 * part_pct as raw_score
            FROM event_percentiles
        ),
        event_importance AS (
            SELECT
                id,
                NTILE(5) OVER (ORDER BY raw_score) as new_importance
            FROM event_composite
        )
        UPDATE events SET importance = ei.new_importance
        FROM event_importance ei
        WHERE events.id = ei.id
    """))
    db.commit()

    # Verify distribution
    result = db.execute(text("""
        SELECT importance, COUNT(*) as cnt
        FROM events
        WHERE wikidata_id IS NOT NULL
        GROUP BY importance
        ORDER BY importance
    """)).fetchall()

    print("  Event importance distribution:")
    for row in result:
        print(f"    {row[0]}: {row[1]:,}")


def compute_person_importance(db):
    """
    Persons importance: stored in connection_count for now,
    but we also add a qrank-based boost.

    raw_score = 0.50 * qrank_percentile + 0.30 * connection_count_percentile + 0.20 * event_count_percentile
    We store the resulting 1-5 tier in a new importance-like metric.
    Since persons table doesn't have an importance column, we repurpose connection_count
    as a composite score or add a qrank-derived field.

    For now: update connection_count to be the composite percentile * 100 (0-100 range)
    so it can be used for sorting. Original connection_count already recalculated in recompute_connections.
    """
    print("Computing person importance (via connection_count)...")

    # Instead of adding a column, we can just use connection_count effectively
    # since recompute_connections.py sets it correctly.
    # Here we just verify QRank coverage for persons.
    qrank_count = db.execute(text(
        "SELECT COUNT(*) FROM persons p JOIN qrank q ON q.wikidata_id = p.wikidata_id"
    )).scalar()
    total = db.execute(text(
        "SELECT COUNT(*) FROM persons WHERE wikidata_id IS NOT NULL"
    )).scalar()
    print(f"  Persons with QRank data: {qrank_count:,} / {total:,}")

    # For the feed API, we'll use a live scoring query that combines
    # qrank + connection_count. No need to persist an importance column on persons.
    print("  (Person ranking will use live QRank + connection_count in Feed API)")


def main():
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    db = SessionLocal()
    try:
        compute_event_importance(db)
        compute_person_importance(db)
        print("\nDone!")
    finally:
        db.close()


if __name__ == "__main__":
    main()
