"""
Extract Wikipedia biography first-paragraphs for persons.

Looks at the sources table for Wikipedia entries matching persons
via entity_type='person', extracts the first meaningful paragraph
from the content, and updates persons.biography.

Only processes persons connected to events (via event_persons, ~90K).

Usage:
    cd backend
    python scripts/extract_biographies.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.session import SessionLocal

BATCH_SIZE = 1000


def check_sources_content(db):
    """Check if sources.content actually has text content."""
    result = db.execute(text("""
        SELECT
            COUNT(*) as total_wiki,
            COUNT(*) FILTER (WHERE content IS NOT NULL AND content != '') as with_content,
            AVG(LENGTH(content)) FILTER (WHERE content IS NOT NULL AND content != '') as avg_len
        FROM sources
        WHERE source_type = 'wikipedia' AND entity_type = 'person'
        LIMIT 1
    """)).fetchone()

    print(f"Wikipedia person sources: {result[0]:,}")
    print(f"  With content: {result[1]:,}")
    if result[2]:
        print(f"  Avg content length: {result[2]:.0f} chars")
    return result[1] > 0


def extract_first_paragraph(content: str) -> str:
    """Extract the first meaningful paragraph from Wikipedia content."""
    if not content:
        return ""

    # Remove HTML tags
    text_clean = re.sub(r'<[^>]+>', '', content)

    # Split into paragraphs
    paragraphs = text_clean.split('\n')

    for p in paragraphs:
        p = p.strip()
        # Skip short lines, headers, empty lines
        if len(p) < 50:
            continue
        # Skip lines that look like metadata
        if p.startswith('{') or p.startswith('|') or p.startswith('!'):
            continue
        # Skip disambiguation lines
        if 'may refer to' in p.lower() or 'disambiguation' in p.lower():
            continue

        # Found a meaningful paragraph - truncate if too long
        if len(p) > 500:
            # Cut at sentence boundary
            sentences = re.split(r'(?<=[.!?])\s+', p)
            result = ""
            for s in sentences:
                if len(result) + len(s) > 500:
                    break
                result += s + " "
            return result.strip()

        return p

    return ""


def extract_biographies(db):
    """Extract and update biographies for event-connected persons."""
    # Get count of eligible persons
    eligible = db.execute(text("""
        SELECT COUNT(DISTINCT ep.person_id)
        FROM event_persons ep
        JOIN persons p ON p.id = ep.person_id
        WHERE p.biography IS NULL
          AND p.wikidata_id IS NOT NULL
    """)).scalar()
    print(f"\nEligible persons (in events, no biography): {eligible:,}")

    if eligible == 0:
        print("No persons need biography extraction.")
        return

    # Process in batches
    updated = 0
    offset = 0

    while True:
        rows = db.execute(text("""
            SELECT DISTINCT p.id as person_id, s.content
            FROM event_persons ep
            JOIN persons p ON p.id = ep.person_id
            JOIN sources s ON s.entity_type = 'person' AND s.entity_id = p.id
                AND s.source_type = 'wikipedia'
                AND s.content IS NOT NULL AND s.content != ''
            WHERE p.biography IS NULL
              AND p.wikidata_id IS NOT NULL
            ORDER BY p.id
            LIMIT :limit OFFSET :offset
        """), {"limit": BATCH_SIZE, "offset": offset}).fetchall()

        if not rows:
            break

        updates = []
        for row in rows:
            bio = extract_first_paragraph(row[1])
            if bio and len(bio) >= 30:
                updates.append({"pid": row[0], "bio": bio})

        if updates:
            for u in updates:
                db.execute(text(
                    "UPDATE persons SET biography = :bio, biography_source = 'wikipedia_en' WHERE id = :pid"
                ), u)
            db.commit()
            updated += len(updates)

        offset += BATCH_SIZE
        print(f"  Processed {offset:,} rows, updated {updated:,} biographies...")

    print(f"\nTotal biographies extracted: {updated:,}")


def main():
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    db = SessionLocal()
    try:
        has_content = check_sources_content(db)
        if has_content:
            extract_biographies(db)
        else:
            print("\nSources table has no content for Wikipedia person entries.")
            print("Skipping biography extraction.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
