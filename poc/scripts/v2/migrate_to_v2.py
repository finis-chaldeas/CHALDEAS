"""
Migrate quality data from V0 to V2.

CP-1.3: Migrate existing quality data
- Events with wikidata_id (4,825)
- Events with good descriptions
- Event relationships
- Person-event connections
"""
import os
import sys
from datetime import datetime
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from work_logger import WorkLogger

load_dotenv()


def get_engine():
    db_url = os.getenv('DATABASE_URL', 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas')
    return create_engine(db_url)


def create_slug(title: str, event_id: int) -> str:
    """Create a URL-safe slug from title."""
    if not title:
        return f"event-v2-{event_id}"
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    slug = slug.strip('-')
    if not slug:
        slug = f"event-{event_id}"
    return f"{slug}-v2-{event_id}"


def migrate_quality_events(engine, log: WorkLogger):
    """Migrate events with wikidata_id to events_v2."""
    print("\n[1/4] Migrating quality events (with wikidata_id)...")

    with engine.connect() as conn:
        # First, clear any existing data (for re-runs)
        conn.execute(text("DELETE FROM events_v2"))
        conn.commit()

        # Get count
        result = conn.execute(text("SELECT COUNT(*) FROM events WHERE wikidata_id IS NOT NULL"))
        total = result.fetchone()[0]
        print(f"    Found {total} events with wikidata_id")

        # Migrate using INSERT ... SELECT (deduplicate by wikidata_id, keep first occurrence)
        migrated = conn.execute(text("""
            INSERT INTO events_v2 (
                title, title_ko, title_ja, slug,
                description, description_ko, description_ja,
                date_start, date_start_month, date_start_day,
                date_end, date_end_month, date_end_day, date_precision,
                temporal_scale, certainty, importance,
                wikidata_id, wikipedia_url, image_url,
                hierarchy_level, is_aggregate, aggregate_type,
                v0_event_id, created_at, updated_at
            )
            SELECT DISTINCT ON (wikidata_id)
                title, title_ko, title_ja,
                CONCAT(
                    LOWER(REGEXP_REPLACE(REGEXP_REPLACE(title, '[^a-zA-Z0-9\\s-]', '', 'g'), '[\\s_-]+', '-', 'g')),
                    '-v2-', id
                ) as slug,
                description, description_ko, description_ja,
                date_start, date_start_month, date_start_day,
                date_end, date_end_month, date_end_day,
                COALESCE(date_precision, 'year'),
                COALESCE(temporal_scale, 'evenementielle'),
                CASE certainty
                    WHEN 'high' THEN 'fact'
                    WHEN 'medium' THEN 'probable'
                    WHEN 'low' THEN 'legendary'
                    WHEN 'fact' THEN 'fact'
                    WHEN 'probable' THEN 'probable'
                    WHEN 'legendary' THEN 'legendary'
                    WHEN 'mythological' THEN 'mythological'
                    ELSE 'fact'
                END as certainty,
                COALESCE(importance, 3),
                wikidata_id, wikipedia_url, image_url,
                COALESCE(hierarchy_level, 3), COALESCE(is_aggregate, false), aggregate_type,
                id, NOW(), NOW()
            FROM events
            WHERE wikidata_id IS NOT NULL
            ORDER BY wikidata_id, id
        """))
        conn.commit()

        # Get actual count
        result = conn.execute(text("SELECT COUNT(*) FROM events_v2"))
        count = result.fetchone()[0]

        log.record_progress(processed=total, created=count)
        print(f"    [OK] Migrated {count} events to events_v2")


def migrate_event_relations(engine, log: WorkLogger):
    """Migrate event relationships to event_relations_v2."""
    print("\n[2/4] Migrating event relationships...")

    with engine.connect() as conn:
        # Clear existing
        conn.execute(text("DELETE FROM event_relations_v2"))
        conn.commit()

        # Count eligible relationships
        result = conn.execute(text("""
            SELECT COUNT(*) FROM event_relationships er
            WHERE EXISTS (SELECT 1 FROM events_v2 ev WHERE ev.v0_event_id = er.from_event_id)
              AND EXISTS (SELECT 1 FROM events_v2 ev WHERE ev.v0_event_id = er.to_event_id)
        """))
        eligible = result.fetchone()[0]
        print(f"    Found {eligible} eligible relationships")

        # Migrate using INSERT ... SELECT with type mapping
        conn.execute(text("""
            INSERT INTO event_relations_v2 (
                from_event_id, to_event_id, relation_type,
                strength, evidence_type, confidence
            )
            SELECT
                ev1.id as from_event_id,
                ev2.id as to_event_id,
                CASE er.relationship_type
                    WHEN 'causes' THEN 'causes'
                    WHEN 'caused_by' THEN 'causes'
                    WHEN 'follows' THEN 'follows'
                    WHEN 'precedes' THEN 'precedes'
                    WHEN 'part_of' THEN 'part_of'
                    WHEN 'contains' THEN 'part_of'
                    WHEN 'influences' THEN 'enables'
                    WHEN 'contemporary' THEN 'parallel_to'
                    ELSE 'parallel_to'
                END as relation_type,
                COALESCE(er.strength, 3),
                COALESCE(er.evidence_type, 'inferred'),
                COALESCE(er.confidence, 1.0)
            FROM event_relationships er
            JOIN events_v2 ev1 ON ev1.v0_event_id = er.from_event_id
            JOIN events_v2 ev2 ON ev2.v0_event_id = er.to_event_id
            ON CONFLICT (from_event_id, to_event_id, relation_type) DO NOTHING
        """))
        conn.commit()

        # Get count
        result = conn.execute(text("SELECT COUNT(*) FROM event_relations_v2"))
        count = result.fetchone()[0]

        log.record_progress(processed=eligible, created=count)
        print(f"    [OK] Migrated {count} relationships to event_relations_v2")


def migrate_person_event_roles(engine, log: WorkLogger):
    """Migrate person-event connections to person_event_roles."""
    print("\n[3/4] Migrating person-event connections...")

    with engine.connect() as conn:
        # Clear existing
        conn.execute(text("DELETE FROM person_event_roles"))
        conn.commit()

        # Count eligible
        result = conn.execute(text("""
            SELECT COUNT(*) FROM event_persons ep
            WHERE EXISTS (SELECT 1 FROM events_v2 ev WHERE ev.v0_event_id = ep.event_id)
        """))
        eligible = result.fetchone()[0]
        print(f"    Found {eligible} person-event links to migrate")

        # Migrate using INSERT ... SELECT
        conn.execute(text("""
            INSERT INTO person_event_roles (
                person_id, event_id, role, importance, is_primary, confidence
            )
            SELECT
                ep.person_id,
                ev.id as event_id,
                'participant' as role,
                3 as importance,
                false as is_primary,
                1.0 as confidence
            FROM event_persons ep
            JOIN events_v2 ev ON ev.v0_event_id = ep.event_id
        """))
        conn.commit()

        # Get count
        result = conn.execute(text("SELECT COUNT(*) FROM person_event_roles"))
        count = result.fetchone()[0]

        log.record_progress(processed=eligible, created=count)
        print(f"    [OK] Migrated {count} person-event roles")


def create_event_completeness(engine, log: WorkLogger):
    """Create completeness records for all V2 events."""
    print("\n[4/4] Creating event completeness records...")

    with engine.connect() as conn:
        # Clear existing
        conn.execute(text("DELETE FROM event_completeness"))
        conn.commit()

        # Create and calculate completeness in one query
        conn.execute(text("""
            INSERT INTO event_completeness (
                event_id,
                title_score,
                description_score,
                date_score,
                location_score,
                persons_score,
                relations_score,
                sources_score,
                overall_score,
                is_stub,
                needs_review,
                last_calculated_at
            )
            SELECT
                e.id as event_id,
                CASE WHEN e.title IS NOT NULL THEN 100 ELSE 0 END as title_score,
                CASE
                    WHEN e.description IS NOT NULL AND LENGTH(e.description) > 200 THEN 100
                    WHEN e.description IS NOT NULL AND LENGTH(e.description) > 50 THEN 50
                    WHEN e.description IS NOT NULL THEN 20
                    ELSE 0
                END as description_score,
                CASE
                    WHEN e.date_precision = 'exact' THEN 100
                    WHEN e.date_precision = 'year' THEN 80
                    WHEN e.date_precision = 'decade' THEN 50
                    ELSE 30
                END as date_score,
                0 as location_score,
                LEAST(100, COALESCE(per.person_count, 0) * 20) as persons_score,
                LEAST(100, COALESCE(rel.rel_count, 0) * 25) as relations_score,
                CASE WHEN e.wikidata_id IS NOT NULL THEN 50 ELSE 0 END as sources_score,
                -- Calculate overall
                (
                    (CASE WHEN e.title IS NOT NULL THEN 100 ELSE 0 END) * 0.05 +
                    (CASE
                        WHEN e.description IS NOT NULL AND LENGTH(e.description) > 200 THEN 100
                        WHEN e.description IS NOT NULL AND LENGTH(e.description) > 50 THEN 50
                        WHEN e.description IS NOT NULL THEN 20
                        ELSE 0
                    END) * 0.30 +
                    (CASE
                        WHEN e.date_precision = 'exact' THEN 100
                        WHEN e.date_precision = 'year' THEN 80
                        WHEN e.date_precision = 'decade' THEN 50
                        ELSE 30
                    END) * 0.15 +
                    0 * 0.15 +  -- location
                    LEAST(100, COALESCE(per.person_count, 0) * 20) * 0.15 +
                    LEAST(100, COALESCE(rel.rel_count, 0) * 25) * 0.10 +
                    (CASE WHEN e.wikidata_id IS NOT NULL THEN 50 ELSE 0 END) * 0.10
                )::integer as overall_score,
                -- is_stub if overall < 30
                (
                    (CASE WHEN e.title IS NOT NULL THEN 100 ELSE 0 END) * 0.05 +
                    (CASE
                        WHEN e.description IS NOT NULL AND LENGTH(e.description) > 200 THEN 100
                        WHEN e.description IS NOT NULL AND LENGTH(e.description) > 50 THEN 50
                        WHEN e.description IS NOT NULL THEN 20
                        ELSE 0
                    END) * 0.30 +
                    (CASE
                        WHEN e.date_precision = 'exact' THEN 100
                        WHEN e.date_precision = 'year' THEN 80
                        WHEN e.date_precision = 'decade' THEN 50
                        ELSE 30
                    END) * 0.15 +
                    LEAST(100, COALESCE(per.person_count, 0) * 20) * 0.15 +
                    LEAST(100, COALESCE(rel.rel_count, 0) * 25) * 0.10 +
                    (CASE WHEN e.wikidata_id IS NOT NULL THEN 50 ELSE 0 END) * 0.10
                ) < 30 as is_stub,
                false as needs_review,
                NOW()
            FROM events_v2 e
            LEFT JOIN (
                SELECT event_id, COUNT(*) as person_count
                FROM person_event_roles
                GROUP BY event_id
            ) per ON per.event_id = e.id
            LEFT JOIN (
                SELECT from_event_id as event_id, COUNT(*) as rel_count
                FROM event_relations_v2
                GROUP BY from_event_id
            ) rel ON rel.event_id = e.id
        """))
        conn.commit()

        # Get count and stats
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total,
                AVG(overall_score)::integer as avg_score,
                SUM(CASE WHEN is_stub THEN 1 ELSE 0 END) as stubs
            FROM event_completeness
        """))
        row = result.fetchone()

        log.record_progress(created=row[0])
        print(f"    [OK] Created {row[0]} completeness records")
        print(f"    Average score: {row[1]}, Stubs: {row[2]}")


def main():
    engine = get_engine()

    with WorkLogger('CP-1.3', 'Migrate V0 data to V2') as log:
        log.update_status('in_progress')

        # Step 1: Migrate quality events
        migrate_quality_events(engine, log)

        # Step 2: Migrate event relationships
        migrate_event_relations(engine, log)

        # Step 3: Migrate person-event roles
        migrate_person_event_roles(engine, log)

        # Step 4: Create completeness records
        create_event_completeness(engine, log)

        log.add_note("Migration completed successfully")

    # Print final status
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM system_completeness"))
        row = result.fetchone()
        print("\n" + "=" * 50)
        print("V2 System Status After Migration:")
        print("=" * 50)
        for i, col in enumerate(result.keys()):
            print(f"  {col}: {row[i]}")


if __name__ == '__main__':
    main()
