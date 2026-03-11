"""
Fill event parent_event_id from Wikidata P361 (part of).

Reads the full Wikidata JSON dump, extracts P361 for events already in our DB,
and updates parent_event_id where both child and parent exist in our events table.

Usage:
    cd backend
    python scripts/fill_event_hierarchy.py                    # full run
    python scripts/fill_event_hierarchy.py --dry-run          # preview only
    python scripts/fill_event_hierarchy.py --limit 5000000    # test with first 5M entities
    python scripts/fill_event_hierarchy.py --extract-only     # save to JSONL, don't touch DB
    python scripts/fill_event_hierarchy.py --apply-only       # apply from saved JSONL

Timing estimate: ~90 minutes for full 1.7TB dump scan (SSD → HDD).
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# === .env loading ===
ENV_PATH = Path(__file__).resolve().parent.parent.parent / '.env'
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            os.environ.setdefault(key.strip(), val.strip().strip('"'))

DUMP_PATH = "E:/wikidata/latest-all.json"
OUTPUT_PATH = Path(__file__).parent / "output" / "event_p361_mapping.jsonl"


def _get_db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.config import get_settings
    settings = get_settings()
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    return Session()


def load_event_qids() -> dict[str, int]:
    """Load {wikidata_id: event_id} mapping from DB."""
    from sqlalchemy import text as sql_text
    db = _get_db_session()
    rows = db.execute(sql_text(
        "SELECT id, wikidata_id FROM events WHERE wikidata_id IS NOT NULL"
    )).fetchall()
    db.close()
    return {row[1]: row[0] for row in rows}


def get_claim_values(entity: dict, property_id: str) -> list[str]:
    """Extract values for a property from entity claims."""
    values = []
    claims = entity.get('claims', {}).get(property_id, [])
    for claim in claims:
        mainsnak = claim.get('mainsnak', {})
        datavalue = mainsnak.get('datavalue', {})
        dtype = datavalue.get('type')
        if dtype == 'wikibase-entityid':
            qid = datavalue.get('value', {}).get('id')
            if qid:
                values.append(qid)
    return values


def stream_wikidata(dump_path: str, limit: int = 0):
    """Stream Wikidata JSON dump line by line."""
    with open(dump_path, 'r', encoding='utf-8') as f:
        count = 0
        for line in f:
            line = line.strip()
            if not line or line in ['[', ']']:
                continue
            if line.endswith(','):
                line = line[:-1]
            try:
                entity = json.loads(line)
                yield entity
                count += 1
                if limit > 0 and count >= limit:
                    break
            except json.JSONDecodeError:
                continue


def cmd_extract(args, event_qids: dict[str, int]) -> list[dict]:
    """Scan dump, extract P361 for our events. Returns list of {child_qid, parent_qid}."""
    dump_path = args.dump
    print(f"=== P361 Extraction ===")
    print(f"  Dump: {dump_path}")
    print(f"  Events in DB: {len(event_qids):,}", flush=True)
    print(f"  Limit: {args.limit if args.limit > 0 else 'full'}")

    if not os.path.exists(dump_path):
        print(f"  ERROR: Dump file not found: {dump_path}")
        sys.exit(1)

    start = time.time()
    scanned = 0
    matched = 0
    p361_found = 0
    p361_both_in_db = 0
    mappings: list[dict] = []

    for entity in stream_wikidata(dump_path, args.limit):
        scanned += 1

        if scanned % 2_000_000 == 0:
            elapsed = time.time() - start
            rate = scanned / elapsed
            print(f"  Scanned: {scanned:,} | Matched: {matched:,} | "
                  f"P361 found: {p361_found} | Both in DB: {p361_both_in_db} | "
                  f"Rate: {rate:,.0f}/s | {elapsed/60:.1f}m", flush=True)

        qid = entity.get('id', '')
        if qid not in event_qids:
            continue

        matched += 1

        # Extract P361 (part of)
        p361_targets = get_claim_values(entity, 'P361')
        if not p361_targets:
            continue

        p361_found += 1

        for target_qid in p361_targets:
            if target_qid in event_qids:
                p361_both_in_db += 1
                mappings.append({
                    "child_qid": qid,
                    "parent_qid": target_qid,
                    "child_id": event_qids[qid],
                    "parent_id": event_qids[target_qid],
                })
                break  # take first valid parent

    elapsed = time.time() - start
    print(f"\n  Done in {elapsed/60:.1f}m")
    print(f"  Scanned: {scanned:,}")
    print(f"  Matched (in DB): {matched:,}")
    print(f"  P361 found: {p361_found}")
    print(f"  Both child+parent in DB: {p361_both_in_db}")

    # Save to JSONL
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        for m in mappings:
            f.write(json.dumps(m, ensure_ascii=False) + '\n')
    print(f"  Saved: {OUTPUT_PATH} ({len(mappings)} mappings)")

    return mappings


def cmd_apply(args, mappings: list[dict]):
    """Apply P361 mappings to DB."""
    from sqlalchemy import text as sql_text

    if not mappings:
        print("  No mappings to apply.")
        return

    # Filter: only where parent_event_id is currently NULL
    db = _get_db_session()
    try:
        existing = db.execute(sql_text(
            "SELECT id, parent_event_id FROM events "
            "WHERE id = ANY(:ids) AND parent_event_id IS NOT NULL"
        ), {"ids": [m["child_id"] for m in mappings]}).fetchall()
        already_set = {row[0] for row in existing}

        to_update = [m for m in mappings if m["child_id"] not in already_set]
        skip_count = len(mappings) - len(to_update)

        if args.force:
            to_update = mappings
            skip_count = 0

        print(f"\n=== Apply P361 to DB ===")
        print(f"  Total mappings: {len(mappings)}")
        print(f"  Already has parent: {skip_count} (skip)")
        print(f"  To update: {len(to_update)}")

        if args.dry_run:
            print(f"\n  DRY RUN: Would update {len(to_update)} events")
            for m in to_update[:20]:
                print(f"    {m['child_qid']} → parent {m['parent_qid']}  "
                      f"(event {m['child_id']} → {m['parent_id']})")
            if len(to_update) > 20:
                print(f"    ... and {len(to_update) - 20} more")
            return

        updated = 0
        for m in to_update:
            db.execute(sql_text(
                "UPDATE events SET parent_event_id = :parent_id "
                "WHERE id = :child_id"
            ), {"parent_id": m["parent_id"], "child_id": m["child_id"]})
            updated += 1

        # Also update is_aggregate for all parents
        parent_ids = list({m["parent_id"] for m in to_update})
        if parent_ids:
            db.execute(sql_text(
                "UPDATE events SET is_aggregate = true "
                "WHERE id = ANY(:ids) AND (is_aggregate IS NULL OR is_aggregate = false)"
            ), {"ids": parent_ids})

        db.commit()
        print(f"  Updated: {updated} events")
        print(f"  Marked aggregate: {len(parent_ids)} parents")

        # Report new coverage
        stats = db.execute(sql_text("""
            SELECT
                COUNT(*) AS total,
                COUNT(parent_event_id) AS with_parent,
                ROUND(100.0 * COUNT(parent_event_id) / COUNT(*), 1) AS pct
            FROM events
        """)).fetchone()
        print(f"\n  Coverage: {stats[1]:,}/{stats[0]:,} ({stats[2]}%)")

    except Exception as e:
        db.rollback()
        print(f"  ERROR: {e}")
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description='Fill event hierarchy from Wikidata P361',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--dump', default=DUMP_PATH, help='Wikidata dump path')
    parser.add_argument('--limit', type=int, default=0, help='Max entities to scan (0=all)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without DB writes')
    parser.add_argument('--force', action='store_true', help='Overwrite existing parent_event_id')
    parser.add_argument('--extract-only', action='store_true', help='Only extract, save to JSONL')
    parser.add_argument('--apply-only', action='store_true', help='Only apply from saved JSONL')
    args = parser.parse_args()

    if args.apply_only:
        # Load from saved JSONL
        if not OUTPUT_PATH.exists():
            print(f"ERROR: No saved mappings at {OUTPUT_PATH}")
            sys.exit(1)
        mappings = []
        with open(OUTPUT_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                mappings.append(json.loads(line.strip()))
        print(f"  Loaded {len(mappings)} mappings from {OUTPUT_PATH}")
        cmd_apply(args, mappings)
        return

    # Load event QIDs from DB
    print("Loading event QIDs from DB...")
    event_qids = load_event_qids()
    print(f"  {len(event_qids):,} events with wikidata_id")

    # Extract
    mappings = cmd_extract(args, event_qids)

    # Apply (unless extract-only)
    if not args.extract_only:
        cmd_apply(args, mappings)


if __name__ == "__main__":
    main()
