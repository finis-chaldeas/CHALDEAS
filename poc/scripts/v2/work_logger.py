"""
WorkLogger - Automatic checkpoint logging utility.

Usage:
    with WorkLogger('CP-1.1', 'V2 스키마 생성') as log:
        # Do work
        log.record_progress(records_created=15)
        # Automatically logs duration and status on exit
"""
import os
import sys
from datetime import datetime
from decimal import Decimal
from contextlib import contextmanager
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()


class WorkLogger:
    """Context manager for logging checkpoint work."""

    # LLM cost estimates per call
    LLM_COSTS = {
        1: 0.0,       # Tier 1: Local LLM (free)
        2: 0.00025,   # Tier 2: gpt-5-mini ($0.25/1M tokens, ~1K tokens/call)
        3: 0.00125,   # Tier 3: gpt-5.1-chat ($1.25/1M tokens, ~1K tokens/call)
    }

    def __init__(self, checkpoint: str, task_name: str):
        self.checkpoint = checkpoint
        self.task_name = task_name
        self.log_id: Optional[int] = None
        self.started_at: Optional[datetime] = None

        # Stats
        self.records_processed = 0
        self.records_created = 0
        self.records_updated = 0
        self.errors_count = 0

        # LLM calls
        self.llm_tier1_calls = 0
        self.llm_tier2_calls = 0
        self.llm_tier3_calls = 0

        # Notes
        self.notes = []

        # DB connection
        db_url = os.getenv('DATABASE_URL', 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas')
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)

    def __enter__(self):
        """Start logging."""
        self.started_at = datetime.now()

        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO work_logs (checkpoint, task_name, status, started_at)
                    VALUES (:checkpoint, :task_name, 'started', :started_at)
                    RETURNING id
                """),
                {
                    'checkpoint': self.checkpoint,
                    'task_name': self.task_name,
                    'started_at': self.started_at
                }
            )
            self.log_id = result.fetchone()[0]
            conn.commit()

        print(f"[{self.checkpoint}] Started: {self.task_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Finish logging."""
        completed_at = datetime.now()
        duration = int((completed_at - self.started_at).total_seconds() / 60)

        status = 'completed' if exc_type is None else 'failed'
        if exc_val:
            self.notes.append(f"Error: {str(exc_val)}")
            self.errors_count += 1

        estimated_cost = self._calculate_cost()

        with self.engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE work_logs SET
                        status = :status,
                        completed_at = :completed_at,
                        duration_minutes = :duration,
                        notes = :notes,
                        records_processed = :records_processed,
                        records_created = :records_created,
                        records_updated = :records_updated,
                        errors_count = :errors_count,
                        llm_tier1_calls = :llm_tier1_calls,
                        llm_tier2_calls = :llm_tier2_calls,
                        llm_tier3_calls = :llm_tier3_calls,
                        estimated_cost = :estimated_cost
                    WHERE id = :log_id
                """),
                {
                    'status': status,
                    'completed_at': completed_at,
                    'duration': duration,
                    'notes': '\n'.join(self.notes) if self.notes else None,
                    'records_processed': self.records_processed,
                    'records_created': self.records_created,
                    'records_updated': self.records_updated,
                    'errors_count': self.errors_count,
                    'llm_tier1_calls': self.llm_tier1_calls,
                    'llm_tier2_calls': self.llm_tier2_calls,
                    'llm_tier3_calls': self.llm_tier3_calls,
                    'estimated_cost': estimated_cost,
                    'log_id': self.log_id
                }
            )
            conn.commit()

        status_symbol = '[OK]' if status == 'completed' else '[FAIL]'
        print(f"[{self.checkpoint}] {status_symbol} {status.upper()} in {duration}min")
        print(f"    Processed: {self.records_processed}, Created: {self.records_created}, Updated: {self.records_updated}")
        if estimated_cost > 0:
            print(f"    Estimated cost: ${estimated_cost:.4f}")

        return False  # Don't suppress exceptions

    def _calculate_cost(self) -> Decimal:
        """Calculate estimated cost from LLM calls."""
        return Decimal(str(
            self.llm_tier1_calls * self.LLM_COSTS[1] +
            self.llm_tier2_calls * self.LLM_COSTS[2] +
            self.llm_tier3_calls * self.LLM_COSTS[3]
        ))

    def record_progress(self, processed: int = 0, created: int = 0, updated: int = 0):
        """Record progress during work."""
        self.records_processed += processed
        self.records_created += created
        self.records_updated += updated

    def record_llm_call(self, tier: int):
        """Record an LLM call."""
        if tier == 1:
            self.llm_tier1_calls += 1
        elif tier == 2:
            self.llm_tier2_calls += 1
        elif tier == 3:
            self.llm_tier3_calls += 1

    def add_note(self, note: str):
        """Add a note to the log."""
        self.notes.append(note)

    def update_status(self, status: str):
        """Update status to 'in_progress' during long operations."""
        with self.engine.connect() as conn:
            conn.execute(
                text("UPDATE work_logs SET status = :status WHERE id = :log_id"),
                {'status': status, 'log_id': self.log_id}
            )
            conn.commit()


def get_work_summary() -> dict:
    """Get summary of all work logs."""
    db_url = os.getenv('DATABASE_URL', 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas')
    engine = create_engine(db_url)

    with engine.connect() as conn:
        # Get checkpoint summary
        result = conn.execute(text("""
            SELECT
                checkpoint,
                COUNT(*) as tasks,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(duration_minutes) as total_minutes,
                SUM(records_created) as total_created,
                SUM(estimated_cost) as total_cost
            FROM work_logs
            GROUP BY checkpoint
            ORDER BY checkpoint
        """))

        summary = {
            'checkpoints': [],
            'totals': {
                'tasks': 0,
                'completed': 0,
                'failed': 0,
                'minutes': 0,
                'created': 0,
                'cost': Decimal('0')
            }
        }

        for row in result:
            cp = {
                'checkpoint': row[0],
                'tasks': row[1],
                'completed': row[2],
                'failed': row[3],
                'minutes': row[4] or 0,
                'created': row[5] or 0,
                'cost': row[6] or Decimal('0')
            }
            summary['checkpoints'].append(cp)
            summary['totals']['tasks'] += cp['tasks']
            summary['totals']['completed'] += cp['completed']
            summary['totals']['failed'] += cp['failed']
            summary['totals']['minutes'] += cp['minutes']
            summary['totals']['created'] += cp['created']
            summary['totals']['cost'] += cp['cost']

        return summary


def print_work_summary():
    """Print formatted work summary."""
    summary = get_work_summary()

    print("\n" + "=" * 60)
    print("CHALDEAS V2 Work Summary")
    print("=" * 60)

    for cp in summary['checkpoints']:
        status = '[OK]' if cp['completed'] == cp['tasks'] else '[..]'
        print(f"{status} {cp['checkpoint']}: {cp['completed']}/{cp['tasks']} tasks, "
              f"{cp['minutes']}min, {cp['created']} records, ${cp['cost']:.4f}")

    print("-" * 60)
    t = summary['totals']
    print(f"Total: {t['completed']}/{t['tasks']} tasks, "
          f"{t['minutes']}min, {t['created']} records, ${t['cost']:.4f}")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    # Test the work logger
    print("Testing WorkLogger...")

    with WorkLogger('CP-TEST', 'Test logging system') as log:
        log.record_progress(processed=10, created=5)
        log.add_note("This is a test note")
        log.record_llm_call(tier=1)
        log.record_llm_call(tier=2)

    print("\nWork summary after test:")
    print_work_summary()
