"""
Validate ALL remaining unknown events with LLM.
Runs continuously until all events are processed.
"""
import subprocess
import sys
import time

BATCH_SIZE = 5000

def get_remaining_count():
    """Get count of remaining unknown events."""
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))
    from app.db.session import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    result = db.execute(text("""
        SELECT COUNT(*) FROM events
        WHERE wikidata_id IS NULL
          AND wikipedia_url IS NULL
          AND parent_status = 'unknown'
          AND NOT EXISTS (SELECT 1 FROM event_sources WHERE event_id = events.id)
    """))
    count = result.scalar()
    db.close()
    return count

def main():
    batch_num = 1

    while True:
        remaining = get_remaining_count()
        print(f"\n{'='*50}", flush=True)
        print(f"Batch {batch_num}: {remaining} events remaining", flush=True)
        print(f"{'='*50}\n", flush=True)

        if remaining == 0:
            print("All events processed!", flush=True)
            break

        # Run validation script
        cmd = [
            sys.executable,
            "validate_events_llm.py",
            "--limit", str(min(BATCH_SIZE, remaining)),
            "--apply",
            "--quarantine",
            "--output", f"uncertain_events_batch{batch_num}.json"
        ]

        print(f"Running: {' '.join(cmd)}", flush=True)
        result = subprocess.run(cmd, cwd=r"C:\Projects\Chaldeas\poc\scripts\hierarchy")

        if result.returncode != 0:
            print(f"Batch {batch_num} failed with code {result.returncode}", flush=True)
            break

        batch_num += 1
        time.sleep(2)  # Brief pause between batches

if __name__ == "__main__":
    main()
