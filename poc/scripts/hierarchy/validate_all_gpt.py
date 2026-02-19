"""
Validate ALL remaining events with GPT-4o-mini.
Runs continuously until all events are processed.
"""
import subprocess
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

BATCH_SIZE = 5000  # Events per batch

def get_remaining_count():
    """Get count of remaining unknown events."""
    from app.db.session import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    result = db.execute(text("""
        SELECT COUNT(*) FROM events
        WHERE wikidata_id IS NULL
          AND wikipedia_url IS NULL
          AND parent_status NOT IN ('garbage', 'pending')
          AND NOT EXISTS (SELECT 1 FROM event_sources WHERE event_id = events.id)
    """))
    count = result.scalar()
    db.close()
    return count

def main():
    print("="*60, flush=True)
    print("GPT-4o-mini Continuous Validation", flush=True)
    print("="*60, flush=True)

    batch_num = 1

    while True:
        remaining = get_remaining_count()
        print(f"\n{'='*50}", flush=True)
        print(f"Batch {batch_num}: {remaining} events remaining", flush=True)
        print(f"{'='*50}\n", flush=True)

        if remaining == 0:
            print("All events processed!", flush=True)
            break

        # Run GPT validation script
        limit = min(BATCH_SIZE, remaining)
        cmd = [
            sys.executable,
            "validate_events_gpt.py",
            "--limit", str(limit),
            "--apply",
            "--quarantine"
        ]

        print(f"Running: {' '.join(cmd)}", flush=True)
        result = subprocess.run(cmd, cwd=os.path.dirname(__file__))

        if result.returncode != 0:
            print(f"Batch {batch_num} failed with code {result.returncode}", flush=True)
            break

        batch_num += 1
        time.sleep(2)  # Brief pause between batches

    print("\n" + "="*60, flush=True)
    print("GPT Validation Complete!", flush=True)
    print("="*60, flush=True)

if __name__ == "__main__":
    main()
