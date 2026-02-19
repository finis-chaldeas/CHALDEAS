"""
Apply person domain classifications to database.

Adds domain column and calculates global_score = importance_score × domain_weight.

Usage:
    python apply_person_domains.py
    python apply_person_domains.py --dry-run
    python apply_person_domains.py --verify    # Show top persons per domain
"""
import sys
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

# Domain weights (must match classify_person_domains.py)
DOMAIN_WEIGHTS = {
    "statecraft":    1.00,
    "military":      0.95,
    "religion":      1.00,
    "philosophy":    0.90,
    "science":       0.90,
    "medicine":      0.80,
    "technology":    0.85,
    "literature":    0.80,
    "visual_arts":   0.75,
    "music":         0.70,
    "exploration":   0.85,
    "economy":       0.65,
    "law":           0.70,
    "reform":        0.80,
    "scholarship":   0.60,
    "entertainment": 0.35,
}


def load_domains(filepath: Path) -> dict[int, str]:
    """Load domain classifications from JSONL, keeping latest per ID."""
    domains = {}
    if not filepath.exists():
        return domains
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if obj.get("domain") and "id" in obj and not obj.get("error"):
                    domains[obj["id"]] = obj["domain"]
            except json.JSONDecodeError:
                continue
    return domains


def ensure_columns():
    """Add domain and global_score columns if they don't exist."""
    with engine.connect() as conn:
        # Check domain column
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'persons' AND column_name = 'domain'
        """)).fetchone()

        if not result:
            print("Adding domain column to persons...")
            conn.execute(text("ALTER TABLE persons ADD COLUMN domain VARCHAR(20)"))
            conn.execute(text("CREATE INDEX idx_persons_domain ON persons (domain)"))
            conn.commit()
            print("  domain column and index added.")
        else:
            print("  domain column already exists.")

        # Check global_score column
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'persons' AND column_name = 'global_score'
        """)).fetchone()

        if not result:
            print("Adding global_score column to persons...")
            conn.execute(text("ALTER TABLE persons ADD COLUMN global_score INTEGER"))
            conn.execute(text("CREATE INDEX idx_persons_global_score ON persons (global_score)"))
            conn.commit()
            print("  global_score column and index added.")
        else:
            print("  global_score column already exists.")


def apply_domains(dry_run: bool = False):
    """Apply domain classifications and calculate global_score."""
    filepath = CHECKPOINT_DIR / "persons_domains.jsonl"
    domains = load_domains(filepath)
    print(f"Loaded {len(domains)} domain classifications")

    if not domains:
        print("No domains to apply!")
        return

    # Distribution
    dist = Counter(domains.values())
    print(f"\nDomain distribution:")
    for d, c in dist.most_common():
        weight = DOMAIN_WEIGHTS.get(d, 0)
        print(f"  {d:<16} {c:>7}  (w={weight})")

    if dry_run:
        print("\n[DRY RUN] Would update persons table")
        return

    ensure_columns()

    with engine.connect() as conn:
        batch_size = 1000
        items = list(domains.items())
        updated = 0

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            for pid, domain in batch:
                weight = DOMAIN_WEIGHTS.get(domain, 0.5)
                # global_score = importance_score × weight (fetched via subquery)
                conn.execute(text("""
                    UPDATE persons
                    SET domain = :domain,
                        global_score = ROUND(COALESCE(importance_score, 0) * :weight)
                    WHERE id = :id
                """), {"domain": domain, "weight": weight, "id": pid})
            conn.commit()
            updated += len(batch)
            if updated % 10000 == 0 or updated == len(items):
                print(f"  Updated {updated}/{len(items)} persons")

    print(f"\nDone! Applied {len(domains)} domain classifications")


def verify():
    """Show top persons per domain with global_score comparison."""
    print("\n" + "=" * 90)
    print("TOP 5 PERSONS PER DOMAIN (importance_score vs global_score)")
    print("=" * 90)

    with engine.connect() as conn:
        domains = conn.execute(text("""
            SELECT DISTINCT domain FROM persons
            WHERE domain IS NOT NULL AND domain != ''
            ORDER BY domain
        """)).fetchall()

        for (domain,) in domains:
            weight = DOMAIN_WEIGHTS.get(domain, 0)
            print(f"\n--- {domain} (weight={weight}) ---")
            rows = conn.execute(text("""
                SELECT name, birth_year, importance_score, global_score
                FROM persons
                WHERE domain = :domain AND importance_score IS NOT NULL
                ORDER BY importance_score DESC
                LIMIT 5
            """), {"domain": domain}).fetchall()

            for r in rows:
                year = f"{abs(r[1])} {'BCE' if r[1] < 0 else 'CE'}" if r[1] else "?"
                print(f"  {r[0]:<35} {year:<12} score={r[2]:>3} → global={r[3]:>3}")

        # Show global top 20 (old vs new ranking)
        print(f"\n{'='*90}")
        print("GLOBAL TOP 20: importance_score vs global_score ranking")
        print(f"{'='*90}")

        print("\n  By importance_score (기존):")
        rows = conn.execute(text("""
            SELECT name, domain, importance_score, global_score
            FROM persons
            WHERE importance_score IS NOT NULL
            ORDER BY importance_score DESC, id
            LIMIT 20
        """)).fetchall()
        for i, r in enumerate(rows, 1):
            print(f"  {i:>2}. {r[0]:<30} {r[1]:<14} imp={r[2]:>3}  glo={r[3]:>3}")

        print("\n  By global_score (개선):")
        rows = conn.execute(text("""
            SELECT name, domain, importance_score, global_score
            FROM persons
            WHERE global_score IS NOT NULL
            ORDER BY global_score DESC, importance_score DESC, id
            LIMIT 20
        """)).fetchall()
        for i, r in enumerate(rows, 1):
            print(f"  {i:>2}. {r[0]:<30} {r[1]:<14} imp={r[2]:>3}  glo={r[3]:>3}")


def main():
    parser = argparse.ArgumentParser(description="Apply person domain classifications to DB")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify", action="store_true", help="Show top persons per domain")
    args = parser.parse_args()

    if args.verify:
        verify()
        return

    apply_domains(args.dry_run)

    # Auto-verify after apply
    if not args.dry_run:
        verify()


if __name__ == "__main__":
    main()
