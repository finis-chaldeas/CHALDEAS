"""
Apply importance scores from JSONL checkpoint to database.

Adds importance_score (1-100) column if not exists, then updates.
Also recalculates importance (1-5) from the 100-point score.

Usage:
    python apply_importance_scores.py events
    python apply_importance_scores.py persons
    python apply_importance_scores.py all
    python apply_importance_scores.py all --dry-run
"""
import sys
import os
import json
import argparse
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / '.env')

from sqlalchemy import create_engine, text

CHECKPOINT_DIR = Path(__file__).parent.parent / "data" / "importance_scores"
engine = create_engine('postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas')


def score_to_importance_5(score: int) -> int:
    """Map 1-100 score to 1-5 importance bucket.

    Uses percentile-like mapping:
    1-15  → 1 (trivial)
    16-35 → 2 (minor)
    36-60 → 3 (notable)
    61-80 → 4 (major)
    81-100 → 5 (world-defining)
    """
    if score <= 15:
        return 1
    elif score <= 35:
        return 2
    elif score <= 60:
        return 3
    elif score <= 80:
        return 4
    else:
        return 5


def load_scores(filepath: Path) -> dict[int, dict]:
    """Load scores from JSONL, keeping latest per ID."""
    scores = {}
    if not filepath.exists():
        return scores

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if obj.get("score", -1) > 0 and "id" in obj:
                    scores[obj["id"]] = obj
            except json.JSONDecodeError:
                continue
    return scores


def ensure_columns(table: str):
    """Add importance_score column if it doesn't exist."""
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = :table AND column_name = 'importance_score'
        """), {"table": table}).fetchone()

        if not result:
            print(f"Adding importance_score column to {table}...")
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN importance_score INTEGER"))
            conn.execute(text(f"CREATE INDEX idx_{table}_importance_score ON {table} (importance_score)"))
            conn.commit()
            print(f"  Column and index added.")
        else:
            print(f"  importance_score column already exists on {table}")

        # For persons, also ensure importance column exists
        if table == "persons":
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'persons' AND column_name = 'importance'
            """)).fetchone()
            if not result:
                print("Adding importance column to persons...")
                conn.execute(text("ALTER TABLE persons ADD COLUMN importance INTEGER DEFAULT 3"))
                conn.execute(text("CREATE INDEX idx_persons_importance ON persons (importance)"))
                conn.commit()
                print("  Column added.")


def apply_events(dry_run: bool = False):
    """Apply event scores to DB."""
    filepath = CHECKPOINT_DIR / "events_scores.jsonl"
    scores = load_scores(filepath)
    print(f"Loaded {len(scores)} event scores")

    if not scores:
        print("No scores to apply!")
        return

    # Distribution
    dist = Counter(score_to_importance_5(s["score"]) for s in scores.values())
    print(f"Distribution (1-5): {dict(sorted(dist.items()))}")

    score_values = [s["score"] for s in scores.values()]
    print(f"Score range: {min(score_values)}-{max(score_values)}, "
          f"avg={sum(score_values)/len(score_values):.1f}")

    if dry_run:
        print("[DRY RUN] Would update events table")
        return

    ensure_columns("events")

    # Drop old CHECK constraint on importance if it restricts to 1-5
    with engine.connect() as conn:
        # Update in batches
        batch_size = 500
        items = list(scores.items())
        updated = 0

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            for eid, data in batch:
                score = data["score"]
                imp5 = score_to_importance_5(score)
                conn.execute(text("""
                    UPDATE events
                    SET importance_score = :score, importance = :imp5
                    WHERE id = :id
                """), {"score": score, "imp5": imp5, "id": eid})
            conn.commit()
            updated += len(batch)
            print(f"  Updated {updated}/{len(items)} events")

    print(f"Done! Applied {len(scores)} event scores")


def apply_persons(dry_run: bool = False):
    """Apply person scores to DB."""
    filepath = CHECKPOINT_DIR / "persons_scores.jsonl"
    scores = load_scores(filepath)
    print(f"Loaded {len(scores)} person scores")

    if not scores:
        print("No scores to apply!")
        return

    dist = Counter(score_to_importance_5(s["score"]) for s in scores.values())
    print(f"Distribution (1-5): {dict(sorted(dist.items()))}")

    score_values = [s["score"] for s in scores.values()]
    print(f"Score range: {min(score_values)}-{max(score_values)}, "
          f"avg={sum(score_values)/len(score_values):.1f}")

    if dry_run:
        print("[DRY RUN] Would update persons table")
        return

    ensure_columns("persons")

    with engine.connect() as conn:
        batch_size = 500
        items = list(scores.items())
        updated = 0

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            for pid, data in batch:
                score = data["score"]
                imp5 = score_to_importance_5(score)
                conn.execute(text("""
                    UPDATE persons
                    SET importance_score = :score, importance = :imp5
                    WHERE id = :id
                """), {"score": score, "imp5": imp5, "id": pid})
            conn.commit()
            updated += len(batch)
            print(f"  Updated {updated}/{len(items)} persons")

    print(f"Done! Applied {len(scores)} person scores")


def main():
    parser = argparse.ArgumentParser(description="Apply importance scores to DB")
    parser.add_argument("target", choices=["events", "persons", "all"])
    parser.add_argument("--dry-run", action="store_true", help="Show stats without updating DB")
    args = parser.parse_args()

    if args.target in ("events", "all"):
        print("=== EVENTS ===")
        apply_events(args.dry_run)
        print()

    if args.target in ("persons", "all"):
        print("=== PERSONS ===")
        apply_persons(args.dry_run)


if __name__ == "__main__":
    main()
