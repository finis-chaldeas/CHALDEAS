"""
DEPRECATED: connection_count columns removed from events (302) and persons (301).

This script is no longer functional. Connection counts are now computed
dynamically via JOINs on event_persons / event_connections.

Previously: Recompute connection_count for events and persons.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.session import SessionLocal


def recompute_event_connections(db):
    """Recompute events.connection_count from event_connections + event_persons."""
    print("Recomputing event connection counts...")

    db.execute(text("""
        UPDATE events e SET connection_count = sub.cnt
        FROM (
            SELECT e2.id,
                COALESCE(ec.ec_count, 0) + COALESCE(ep.ep_count, 0) as cnt
            FROM events e2
            LEFT JOIN (
                SELECT event_id, COUNT(*) as ec_count
                FROM (
                    SELECT event_a_id as event_id FROM event_connections
                    UNION ALL
                    SELECT event_b_id as event_id FROM event_connections
                ) t
                GROUP BY event_id
            ) ec ON ec.event_id = e2.id
            LEFT JOIN (
                SELECT event_id, COUNT(*) as ep_count
                FROM event_persons
                GROUP BY event_id
            ) ep ON ep.event_id = e2.id
        ) sub
        WHERE e.id = sub.id
    """))
    db.commit()

    result = db.execute(text("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE connection_count > 0) as with_connections,
            MAX(connection_count) as max_conn,
            AVG(connection_count)::int as avg_conn
        FROM events
        WHERE wikidata_id IS NOT NULL
    """)).fetchone()

    print(f"  Total events: {result[0]:,}")
    print(f"  With connections: {result[1]:,}")
    print(f"  Max connections: {result[2]:,}")
    print(f"  Avg connections: {result[3]}")


def recompute_person_connections(db):
    """Recompute persons.connection_count from event_persons + links."""
    print("Recomputing person connection counts...")

    # Check if links table exists
    has_links = db.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'links'
        )
    """)).scalar()

    if has_links:
        db.execute(text("""
            UPDATE persons p SET connection_count = sub.cnt
            FROM (
                SELECT p2.id,
                    COALESCE(ep.ep_count, 0) + COALESCE(lk.lk_count, 0) as cnt
                FROM persons p2
                LEFT JOIN (
                    SELECT person_id, COUNT(*) as ep_count
                    FROM event_persons
                    GROUP BY person_id
                ) ep ON ep.person_id = p2.id
                LEFT JOIN (
                    SELECT entity_id, COUNT(*) as lk_count
                    FROM (
                        SELECT from_id as entity_id FROM links WHERE from_type = 'person'
                        UNION ALL
                        SELECT to_id as entity_id FROM links WHERE to_type = 'person'
                    ) t
                    GROUP BY entity_id
                ) lk ON lk.entity_id = p2.id
            ) sub
            WHERE p.id = sub.id
        """))
    else:
        db.execute(text("""
            UPDATE persons p SET connection_count = COALESCE(sub.cnt, 0)
            FROM (
                SELECT person_id, COUNT(*) as cnt
                FROM event_persons
                GROUP BY person_id
            ) sub
            WHERE p.id = sub.person_id
        """))

    db.commit()

    result = db.execute(text("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE connection_count > 0) as with_connections,
            MAX(connection_count) as max_conn,
            AVG(connection_count) FILTER (WHERE connection_count > 0) as avg_conn
        FROM persons
        WHERE wikidata_id IS NOT NULL
    """)).fetchone()

    print(f"  Total persons: {result[0]:,}")
    print(f"  With connections: {result[1]:,}")
    print(f"  Max connections: {result[2]}")
    print(f"  Avg connections (non-zero): {result[3]:.1f}" if result[3] else "  Avg: N/A")


def main():
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    db = SessionLocal()
    try:
        recompute_event_connections(db)
        recompute_person_connections(db)
        print("\nDone!")
    finally:
        db.close()


if __name__ == "__main__":
    main()
