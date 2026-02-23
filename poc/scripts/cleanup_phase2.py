"""
Phase 2: Data Cleanup for Compact DB.

Steps:
  Step 1: Deactivate orphan persons (no events, no relationships, no narratives)
  Step 2: Fix role='occupation' bug
  Step 3: Deduplicate events (same title + coords + year)
  Step 4: Mark language contamination (Korean in English fields)

Default mode is --dry-run. Run without it to apply changes.

Usage:
    python poc/scripts/cleanup_phase2.py --dry-run          # Preview all steps
    python poc/scripts/cleanup_phase2.py --step 1 --dry-run # Preview step 1 only
    python poc/scripts/cleanup_phase2.py --step 1           # Execute step 1
    python poc/scripts/cleanup_phase2.py                    # Execute all steps
"""

import argparse
import sys
from datetime import datetime

import psycopg2

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_URL = "host=127.0.0.1 port=5432 dbname=chaldeas user=chaldeas password=chaldeas_dev"


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


def detect_importance_column(cur, table="persons"):
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = %s AND column_name IN ('importance_score', 'importance')
        ORDER BY column_name DESC
    """, (table,))
    cols = [row[0] for row in cur.fetchall()]
    if 'importance_score' in cols:
        return 'importance_score'
    if 'importance' in cols:
        return 'importance'
    return None


# ═══════════════════════════════════════════
# Step 1: Orphan Person Deactivation
# ═══════════════════════════════════════════

def step1_orphan_persons(cur, conn, dry_run=True):
    """Mark orphan persons (no events, no relationships, no narratives) with importance_score = -1."""
    print("\n" + "=" * 60)
    print("STEP 1: Orphan Person Deactivation")
    print("=" * 60)

    imp_col = detect_importance_column(cur, "persons")
    if not imp_col:
        print("  [ERROR] No importance column found on persons table")
        return 0

    # Count current state
    cur.execute(f"SELECT COUNT(*) FROM persons")
    total_persons = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM persons WHERE {imp_col} = -1")
    already_deactivated = cur.fetchone()[0]

    # Build the orphan query
    has_entity_narratives = table_exists(cur, 'entity_narratives')
    has_person_sources = table_exists(cur, 'person_sources')

    narrative_clause = ""
    if has_entity_narratives:
        narrative_clause = f"AND p.id NOT IN (SELECT entity_id FROM entity_narratives WHERE entity_type = 'person')"

    source_clause = ""
    if has_person_sources:
        source_clause = f"AND p.id NOT IN (SELECT person_id FROM person_sources)"

    orphan_query = f"""
        SELECT p.id, p.name, p.{imp_col}
        FROM persons p
        WHERE p.id NOT IN (SELECT person_id FROM event_persons)
          AND ({imp_col} IS NULL OR {imp_col} = 0 OR {imp_col} <= 1)
          AND p.id NOT IN (SELECT person_id FROM person_relationships)
          AND p.id NOT IN (SELECT related_person_id FROM person_relationships)
          {narrative_clause}
          {source_clause}
          AND {imp_col} != -1
    """

    cur.execute(orphan_query)
    orphans = cur.fetchall()

    print(f"\n  Total persons:      {total_persons:,}")
    print(f"  Already deactivated: {already_deactivated:,}")
    print(f"  New orphans found:   {len(orphans):,}")

    if not orphans:
        print("  No orphans to deactivate.")
        return 0

    # Sample
    print(f"\n  Sample orphans (first 10):")
    for pid, name, score in orphans[:10]:
        print(f"    [{pid}] {name} (score: {score})")

    if dry_run:
        remaining = total_persons - already_deactivated - len(orphans)
        print(f"\n  [DRY RUN] Would deactivate {len(orphans):,} persons")
        print(f"  [DRY RUN] Active persons after: ~{remaining:,}")
        return len(orphans)

    # Execute
    orphan_ids = [o[0] for o in orphans]
    batch_size = 5000
    deactivated = 0

    for i in range(0, len(orphan_ids), batch_size):
        batch = orphan_ids[i:i + batch_size]
        cur.execute(f"""
            UPDATE persons SET {imp_col} = -1
            WHERE id = ANY(%s)
        """, (batch,))
        deactivated += cur.rowcount
        conn.commit()
        print(f"    Batch {i//batch_size + 1}: deactivated {cur.rowcount:,}")

    cur.execute(f"SELECT COUNT(*) FROM persons WHERE {imp_col} != -1")
    active_count = cur.fetchone()[0]

    print(f"\n  Deactivated: {deactivated:,}")
    print(f"  Active persons remaining: {active_count:,}")
    return deactivated


# ═══════════════════════════════════════════
# Step 2: Fix role='occupation' Bug
# ═══════════════════════════════════════════

def step2_fix_roles(cur, conn, dry_run=True):
    """Fix role='occupation' and role='None' data bugs."""
    print("\n" + "=" * 60)
    print("STEP 2: Fix role='occupation' Bug")
    print("=" * 60)

    # Count problematic roles
    cur.execute("SELECT role, COUNT(*) FROM persons GROUP BY role ORDER BY COUNT(*) DESC LIMIT 20")
    role_dist = cur.fetchall()

    print(f"\n  Current role distribution (top 20):")
    for role, cnt in role_dist:
        marker = " <-- BUG" if role in ('occupation', 'None') else ""
        print(f"    {role or 'NULL':30s}: {cnt:>8,}{marker}")

    cur.execute("SELECT COUNT(*) FROM persons WHERE role = 'occupation'")
    occupation_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM persons WHERE role = 'None'")
    none_count = cur.fetchone()[0]

    print(f"\n  role='occupation': {occupation_count:,}")
    print(f"  role='None':       {none_count:,}")

    if dry_run:
        print(f"\n  [DRY RUN] Would set {occupation_count + none_count:,} roles to NULL")
        return occupation_count + none_count

    # Fix: set to NULL
    cur.execute("UPDATE persons SET role = NULL WHERE role = 'occupation'")
    fixed_occ = cur.rowcount
    cur.execute("UPDATE persons SET role = NULL WHERE role = 'None'")
    fixed_none = cur.rowcount
    conn.commit()

    print(f"\n  Fixed 'occupation' → NULL: {fixed_occ:,}")
    print(f"  Fixed 'None' → NULL:       {fixed_none:,}")
    return fixed_occ + fixed_none


# ═══════════════════════════════════════════
# Step 3: Duplicate Event Cleanup
# ═══════════════════════════════════════════

def step3_dedup_events(cur, conn, dry_run=True):
    """Find and deactivate duplicate events (same title + location + year)."""
    print("\n" + "=" * 60)
    print("STEP 3: Duplicate Event Cleanup")
    print("=" * 60)

    imp_col = detect_importance_column(cur, "events")
    if not imp_col:
        print("  [ERROR] No importance column found on events table")
        return 0

    # Find duplicates: same title + same primary_location_id + same date_start
    cur.execute(f"""
        SELECT title, primary_location_id, date_start, COUNT(*) AS cnt,
               array_agg(id ORDER BY {imp_col} DESC NULLS LAST) AS ids,
               array_agg({imp_col} ORDER BY {imp_col} DESC NULLS LAST) AS scores
        FROM events
        WHERE {imp_col} != -1 OR {imp_col} IS NULL
        GROUP BY title, primary_location_id, date_start
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC
        LIMIT 100
    """)
    duplicates = cur.fetchall()

    total_dupes = 0
    deactivate_ids = []

    print(f"\n  Duplicate groups found: {len(duplicates):,}")

    if duplicates:
        print(f"\n  Sample duplicates (first 10):")
        for title, loc_id, date_start, cnt, ids, scores in duplicates[:10]:
            print(f"    '{title}' (loc:{loc_id}, year:{date_start}) x{cnt}")
            print(f"      IDs: {ids[:5]}, Scores: {scores[:5]}")
            # Keep highest importance, deactivate rest
            keep_id = ids[0]
            for eid in ids[1:]:
                deactivate_ids.append(eid)
                total_dupes += 1

        # Process remaining groups
        for title, loc_id, date_start, cnt, ids, scores in duplicates[10:]:
            for eid in ids[1:]:
                deactivate_ids.append(eid)
                total_dupes += 1

    print(f"\n  Events to deactivate: {total_dupes:,}")

    if dry_run or not deactivate_ids:
        if deactivate_ids:
            print(f"  [DRY RUN] Would deactivate {total_dupes:,} duplicate events")
        else:
            print(f"  No duplicates to clean.")
        return total_dupes

    # Execute
    batch_size = 5000
    deactivated = 0
    for i in range(0, len(deactivate_ids), batch_size):
        batch = deactivate_ids[i:i + batch_size]
        cur.execute(f"""
            UPDATE events SET {imp_col} = -1
            WHERE id = ANY(%s)
        """, (batch,))
        deactivated += cur.rowcount
        conn.commit()

    print(f"  Deactivated: {deactivated:,}")
    return deactivated


# ═══════════════════════════════════════════
# Step 4: Language Contamination Marking
# ═══════════════════════════════════════════

def step4_language_contamination(cur, conn, dry_run=True):
    """Mark entities with Korean characters in English name/description fields."""
    print("\n" + "=" * 60)
    print("STEP 4: Language Contamination Check")
    print("=" * 60)

    imp_col = detect_importance_column(cur, "persons")
    if not imp_col:
        print("  [ERROR] No importance column found on persons table")
        return 0

    # Find persons with Korean in name field
    cur.execute(f"""
        SELECT id, name, {imp_col}
        FROM persons
        WHERE name ~ '[가-힣]'
          AND {imp_col} != -1
    """)
    korean_names = cur.fetchall()

    # Find persons with Korean in description
    cur.execute(f"""
        SELECT id, name, description
        FROM persons
        WHERE description ~ '[가-힣]'
          AND {imp_col} != -1
    """)
    korean_descs = cur.fetchall()

    # Find events with Korean in title
    event_imp_col = detect_importance_column(cur, "events")
    cur.execute(f"""
        SELECT id, title
        FROM events
        WHERE title ~ '[가-힣]'
          AND ({event_imp_col} != -1 OR {event_imp_col} IS NULL)
    """)
    korean_event_titles = cur.fetchall()

    print(f"\n  Persons with Korean in name:        {len(korean_names):,}")
    print(f"  Persons with Korean in description:  {len(korean_descs):,}")
    print(f"  Events with Korean in title:         {len(korean_event_titles):,}")

    if korean_names:
        print(f"\n  Sample persons with Korean names (first 10):")
        for pid, name, score in korean_names[:10]:
            print(f"    [{pid}] {name} (score: {score})")

    if korean_event_titles:
        print(f"\n  Sample events with Korean titles (first 10):")
        for eid, title in korean_event_titles[:10]:
            print(f"    [{eid}] {title}")

    total_contaminated = len(korean_names) + len(korean_descs) + len(korean_event_titles)

    if dry_run:
        print(f"\n  [DRY RUN] Would mark {len(korean_names):,} persons for re-curation")
        print(f"  [DRY RUN] These will be picked up by Phase 3 curation (importance >= 1)")
        return total_contaminated

    # Mark persons with Korean names: ensure importance >= 1 so they get curated
    if korean_names:
        korean_person_ids = [p[0] for p in korean_names]
        cur.execute(f"""
            UPDATE persons
            SET {imp_col} = GREATEST(COALESCE({imp_col}, 0), 1)
            WHERE id = ANY(%s)
              AND (COALESCE({imp_col}, 0) < 1)
        """, (korean_person_ids,))
        boosted = cur.rowcount
        conn.commit()
        print(f"\n  Persons boosted to importance >= 1: {boosted:,}")

    print(f"  Contaminated entries will be re-curated in Phase 3 (English-only output)")
    return total_contaminated


# ═══════════════════════════════════════════
# Summary Report
# ═══════════════════════════════════════════

def print_summary(cur):
    """Print current DB state summary."""
    print("\n" + "=" * 60)
    print("  DATA QUALITY SUMMARY")
    print("=" * 60)

    imp_col = detect_importance_column(cur, "persons")
    event_imp_col = detect_importance_column(cur, "events")

    if imp_col:
        cur.execute(f"SELECT COUNT(*) FROM persons WHERE {imp_col} != -1")
        active_persons = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM persons WHERE {imp_col} = -1")
        inactive_persons = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM persons")
        total_persons = cur.fetchone()[0]
        print(f"\n  Persons:  {total_persons:,} total, {active_persons:,} active, {inactive_persons:,} deactivated")

    if event_imp_col:
        cur.execute(f"SELECT COUNT(*) FROM events WHERE {event_imp_col} != -1 OR {event_imp_col} IS NULL")
        active_events = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM events WHERE {event_imp_col} = -1")
        inactive_events = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM events")
        total_events = cur.fetchone()[0]
        print(f"  Events:   {total_events:,} total, {active_events:,} active, {inactive_events:,} deactivated")

    # Role distribution (top 10)
    cur.execute("SELECT role, COUNT(*) FROM persons WHERE role IS NOT NULL GROUP BY role ORDER BY COUNT(*) DESC LIMIT 10")
    roles = cur.fetchall()
    print(f"\n  Top 10 person roles:")
    for role, cnt in roles:
        print(f"    {role:30s}: {cnt:>8,}")

    cur.execute("SELECT COUNT(*) FROM persons WHERE role IS NULL")
    null_roles = cur.fetchone()[0]
    print(f"    {'NULL':30s}: {null_roles:>8,}")

    # Narrative coverage
    if table_exists(cur, 'entity_narratives'):
        cur.execute("SELECT entity_type, COUNT(*) FROM entity_narratives GROUP BY entity_type")
        narr_stats = cur.fetchall()
        print(f"\n  Entity narratives:")
        for etype, cnt in narr_stats:
            print(f"    {etype}: {cnt:,}")

    # Source coverage
    cur.execute("SELECT COUNT(*) FROM sources")
    total_sources = cur.fetchone()[0]
    print(f"\n  Sources: {total_sources:,}")
    try:
        cur.execute("SELECT COUNT(*) FROM sources WHERE content_raw IS NOT NULL")
        with_content = cur.fetchone()[0]
        print(f"  Sources with content_raw: {with_content:,}")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Phase 2: Data Cleanup for Compact DB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Steps:
  1. Deactivate orphan persons (no events, no relationships, no narratives)
  2. Fix role='occupation' bug
  3. Deduplicate events (same title + coords + year)
  4. Mark language contamination (Korean in English fields)

Examples:
  python cleanup_phase2.py --dry-run          # Preview all steps
  python cleanup_phase2.py --step 1 --dry-run # Preview step 1
  python cleanup_phase2.py --step 1           # Execute step 1
  python cleanup_phase2.py                    # Execute all steps
        """
    )
    parser.add_argument("--step", type=int, choices=[1, 2, 3, 4],
                        help="Run specific step only")
    parser.add_argument("--dry-run", action="store_true", default=False,
                        help="Preview changes without applying (default: execute)")
    args = parser.parse_args()

    conn = get_conn()
    conn.set_client_encoding('UTF8')
    cur = conn.cursor()

    start_time = datetime.now()

    print(f"╔{'═' * 58}╗")
    print(f"║  Phase 2: Data Cleanup Pipeline                          ║")
    print(f"║  Mode: {'DRY RUN (preview only)' if args.dry_run else 'EXECUTE (applying changes)':46s} ║")
    print(f"║  Started: {start_time.strftime('%Y-%m-%d %H:%M:%S'):<46} ║")
    print(f"╚{'═' * 58}╝")

    results = {}

    if args.step is None or args.step == 1:
        results['step1'] = step1_orphan_persons(cur, conn, dry_run=args.dry_run)

    if args.step is None or args.step == 2:
        results['step2'] = step2_fix_roles(cur, conn, dry_run=args.dry_run)

    if args.step is None or args.step == 3:
        results['step3'] = step3_dedup_events(cur, conn, dry_run=args.dry_run)

    if args.step is None or args.step == 4:
        results['step4'] = step4_language_contamination(cur, conn, dry_run=args.dry_run)

    # Print summary
    print_summary(cur)

    elapsed = datetime.now() - start_time
    print(f"\n{'=' * 60}")
    print(f"  Completed in {elapsed.total_seconds():.1f}s")
    if args.dry_run:
        print(f"  (DRY RUN - no changes applied. Re-run without --dry-run to execute)")
    print(f"{'=' * 60}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
