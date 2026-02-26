"""
Seed aggregate shifts from existing aggregate events.

Reads events WHERE is_aggregate = true, fetches their children via
event_parents table, and creates historical_chains + chain_segments records.

Usage:
    cd backend
    python scripts/seed_aggregate_shifts.py [--dry-run]
"""
import sys
import os
import argparse

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)
Session = sessionmaker(bind=engine)


def slugify(title: str) -> str:
    """Simple slug generation from title."""
    import re
    slug = title.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug[:500]


def seed_shifts(dry_run: bool = False):
    db = Session()
    try:
        # Detect if event_parents table exists
        has_event_parents = False
        try:
            db.execute(text("SELECT 1 FROM event_parents LIMIT 1"))
            has_event_parents = True
            print("Using event_parents table for child lookup")
        except Exception:
            db.rollback()
            print("event_parents table not found, using parent_event_id column")

        # 1. Find aggregate events
        agg_events = db.execute(text("""
            SELECT e.id, e.title, e.title_ko, e.date_start, e.date_end, e.importance
            FROM events e
            WHERE e.is_aggregate = true
            ORDER BY e.date_start
        """)).fetchall()

        print(f"Found {len(agg_events)} aggregate events")

        # Check existing shifts to avoid duplicates
        existing = db.execute(text("""
            SELECT focal_event_id FROM historical_chains
            WHERE chain_type = 'aggregate'
        """)).fetchall()
        existing_event_ids = {r[0] for r in existing}

        created = 0
        skipped = 0

        for agg in agg_events:
            agg_id, title, title_ko, date_start, date_end, importance = agg

            if agg_id in existing_event_ids:
                skipped += 1
                continue

            # Skip events without date_start (NOT NULL constraint on historical_chains)
            if date_start is None:
                skipped += 1
                continue

            # 2. Get children ordered by date_start
            if has_event_parents:
                children = db.execute(text("""
                    SELECT e.id, e.title, e.title_ko, e.date_start, e.date_end,
                           e.importance, e.primary_location_id,
                           l.latitude, l.longitude,
                           ed.description, ed.description_ko
                    FROM event_parents ep
                    JOIN events e ON e.id = ep.event_id
                    LEFT JOIN locations l ON l.id = e.primary_location_id
                    LEFT JOIN event_details ed ON ed.event_id = e.id
                    WHERE ep.parent_event_id = :parent_id
                    ORDER BY e.date_start NULLS LAST, e.importance DESC
                """), {"parent_id": agg_id}).fetchall()
            else:
                children = db.execute(text("""
                    SELECT e.id, e.title, e.title_ko, e.date_start, e.date_end,
                           e.importance, e.primary_location_id,
                           l.latitude, l.longitude,
                           ed.description, ed.description_ko
                    FROM events e
                    LEFT JOIN locations l ON l.id = e.primary_location_id
                    LEFT JOIN event_details ed ON ed.event_id = e.id
                    WHERE e.parent_event_id = :parent_id
                    ORDER BY e.date_start NULLS LAST, e.importance DESC
                """), {"parent_id": agg_id}).fetchall()

            if len(children) < 2:
                skipped += 1
                continue

            # Get parent event description for summary
            parent_desc = db.execute(text("""
                SELECT ed.description, ed.description_ko
                FROM event_details ed
                WHERE ed.event_id = :event_id
            """), {"event_id": agg_id}).fetchone()

            slug = f"shift-{slugify(title)}"

            # Ensure slug uniqueness
            slug_exists = db.execute(
                text("SELECT 1 FROM historical_chains WHERE slug = :slug"),
                {"slug": slug}
            ).fetchone()
            if slug_exists:
                slug = f"{slug}-{agg_id}"

            if dry_run:
                print(f"  [DRY] Would create: {title} ({len(children)} pages)")
                created += 1
                continue

            # 3. Create HistoricalChain record
            result = db.execute(text("""
                INSERT INTO historical_chains
                (chain_type, slug, title, title_ko, summary, summary_ko,
                 focal_event_id, year_start, year_end,
                 segment_count, status, is_auto_generated,
                 display_type, chapter_count, globe_importance)
                VALUES
                ('aggregate', :slug, :title, :title_ko, :summary, :summary_ko,
                 :focal_event_id, :year_start, :year_end,
                 :segment_count, 'system', true,
                 'split', 1, :globe_importance)
                RETURNING id
            """), {
                "slug": slug,
                "title": title,
                "title_ko": title_ko,
                "summary": parent_desc[0] if parent_desc else None,
                "summary_ko": parent_desc[1] if parent_desc else None,
                "focal_event_id": agg_id,
                "year_start": date_start,
                "year_end": date_end,
                "segment_count": len(children),
                "globe_importance": min(importance or 3, 5),
            })
            chain_id = result.fetchone()[0]

            # 4. Create ChainSegment records for each child
            for seq, child in enumerate(children):
                (child_id, child_title, child_title_ko,
                 child_date_start, child_date_end,
                 child_importance, child_loc_id,
                 child_lat, child_lng,
                 child_desc, child_desc_ko) = child

                db.execute(text("""
                    INSERT INTO chain_segments
                    (chain_id, sequence_number, title, narrative, narrative_ko,
                     event_id, location_id, year_start, year_end,
                     importance, chapter_number, page_narrative, page_narrative_ko)
                    VALUES
                    (:chain_id, :seq, :title, :narrative, :narrative_ko,
                     :event_id, :location_id, :year_start, :year_end,
                     :importance, 1, :page_narrative, :page_narrative_ko)
                """), {
                    "chain_id": chain_id,
                    "seq": seq,
                    "title": child_title,
                    "narrative": child_title,
                    "narrative_ko": child_title_ko,
                    "event_id": child_id,
                    "location_id": child_loc_id,
                    "year_start": child_date_start,
                    "year_end": child_date_end,
                    "importance": child_importance or 3,
                    "page_narrative": child_desc,
                    "page_narrative_ko": child_desc_ko,
                })

            created += 1
            if created % 10 == 0:
                print(f"  Created {created} shifts...")

        db.commit()
        print(f"\nDone! Created: {created}, Skipped: {skipped} (already exist or <2 children)")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed aggregate shifts from events")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually create records")
    args = parser.parse_args()
    seed_shifts(dry_run=args.dry_run)
