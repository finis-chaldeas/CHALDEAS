"""
Cost Tracking System for CHALDEAS V2.

Tracks API usage and costs across all LLM tiers.
Provides alerts when approaching budget limits.
"""
import os
import sys
import json
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Optional
from enum import Enum

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()


class LLMTier(Enum):
    LOCAL = 1
    MINI = 2
    ADVANCED = 3


class CostTracker:
    """Track LLM API costs and enforce budget limits."""

    # Cost per 1K tokens
    COSTS_PER_1K = {
        LLMTier.LOCAL: Decimal('0.0'),
        LLMTier.MINI: Decimal('0.00025'),     # $0.25 per 1M tokens
        LLMTier.ADVANCED: Decimal('0.00125')  # $1.25 per 1M tokens
    }

    # Budget settings
    DEFAULT_BUDGET = Decimal('300.00')
    WARNING_THRESHOLD = Decimal('0.80')  # Warn at 80% of budget
    CRITICAL_THRESHOLD = Decimal('0.95')  # Critical at 95%

    def __init__(self, budget: Decimal = None):
        self.budget = budget or self.DEFAULT_BUDGET
        self.db_url = os.getenv('DATABASE_URL', 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas')
        self.engine = create_engine(self.db_url)

        # In-memory tracking for current session
        self.session_stats = {
            'calls': {tier: 0 for tier in LLMTier},
            'tokens': {tier: 0 for tier in LLMTier},
            'cost': {tier: Decimal('0') for tier in LLMTier}
        }

    def record_call(self, tier: LLMTier, tokens: int, cost: float = None):
        """Record an LLM API call."""
        if cost is None:
            cost = (Decimal(str(tokens)) / 1000) * self.COSTS_PER_1K[tier]
        else:
            cost = Decimal(str(cost))

        self.session_stats['calls'][tier] += 1
        self.session_stats['tokens'][tier] += tokens
        self.session_stats['cost'][tier] += cost

        # Check budget
        total = self.get_total_cost()
        if total >= self.budget * self.CRITICAL_THRESHOLD:
            print(f"\n[CRITICAL] Budget {self.CRITICAL_THRESHOLD*100:.0f}% used! ${total:.2f}/${self.budget:.2f}")
        elif total >= self.budget * self.WARNING_THRESHOLD:
            print(f"\n[WARNING] Budget {self.WARNING_THRESHOLD*100:.0f}% used! ${total:.2f}/${self.budget:.2f}")

    def get_session_cost(self) -> Decimal:
        """Get total cost for current session."""
        return sum(self.session_stats['cost'].values())

    def get_total_cost(self) -> Decimal:
        """Get total cost including database records."""
        db_cost = self._get_db_total_cost()
        session_cost = self.get_session_cost()
        return db_cost + session_cost

    def _get_db_total_cost(self) -> Decimal:
        """Get total cost from database."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COALESCE(SUM(estimated_cost), 0) FROM work_logs
                """))
                return Decimal(str(result.fetchone()[0]))
        except Exception as e:
            print(f"Warning: Could not read DB costs: {e}")
            return Decimal('0')

    def get_daily_cost(self, target_date: date = None) -> Decimal:
        """Get cost for a specific day."""
        target_date = target_date or date.today()

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COALESCE(SUM(estimated_cost), 0)
                    FROM work_logs
                    WHERE DATE(started_at) = :target_date
                """), {'target_date': target_date})
                return Decimal(str(result.fetchone()[0]))
        except:
            return Decimal('0')

    def get_remaining_budget(self) -> Decimal:
        """Get remaining budget."""
        return self.budget - self.get_total_cost()

    def can_afford(self, tier: LLMTier, estimated_tokens: int) -> bool:
        """Check if we can afford a call with estimated tokens."""
        estimated_cost = (Decimal(str(estimated_tokens)) / 1000) * self.COSTS_PER_1K[tier]
        return self.get_remaining_budget() >= estimated_cost

    def estimate_cost(self, tier: LLMTier, tokens: int) -> Decimal:
        """Estimate cost for a given number of tokens."""
        return (Decimal(str(tokens)) / 1000) * self.COSTS_PER_1K[tier]

    def get_cost_report(self) -> Dict:
        """Generate a cost report."""
        total_cost = self.get_total_cost()
        remaining = self.get_remaining_budget()

        return {
            'budget': float(self.budget),
            'total_spent': float(total_cost),
            'remaining': float(remaining),
            'percent_used': float((total_cost / self.budget) * 100),
            'session': {
                'calls': {tier.name: count for tier, count in self.session_stats['calls'].items()},
                'tokens': {tier.name: count for tier, count in self.session_stats['tokens'].items()},
                'cost': {tier.name: float(cost) for tier, cost in self.session_stats['cost'].items()},
                'total': float(self.get_session_cost())
            },
            'by_tier': {
                tier.name: {
                    'rate_per_1m': float(self.COSTS_PER_1K[tier] * 1000),
                    'session_tokens': self.session_stats['tokens'][tier],
                    'session_cost': float(self.session_stats['cost'][tier])
                }
                for tier in LLMTier
            },
            'status': self._get_budget_status(total_cost)
        }

    def _get_budget_status(self, total_cost: Decimal) -> str:
        """Get budget status string."""
        ratio = total_cost / self.budget
        if ratio >= self.CRITICAL_THRESHOLD:
            return 'CRITICAL'
        elif ratio >= self.WARNING_THRESHOLD:
            return 'WARNING'
        elif ratio >= Decimal('0.5'):
            return 'MODERATE'
        else:
            return 'OK'

    def print_report(self):
        """Print formatted cost report."""
        report = self.get_cost_report()

        print("\n" + "=" * 60)
        print("CHALDEAS V2 Cost Report")
        print("=" * 60)

        print(f"\nBudget Status: {report['status']}")
        print(f"  Budget:     ${report['budget']:.2f}")
        print(f"  Spent:      ${report['total_spent']:.4f} ({report['percent_used']:.1f}%)")
        print(f"  Remaining:  ${report['remaining']:.2f}")

        print("\nCurrent Session:")
        for tier_name, data in report['by_tier'].items():
            if data['session_tokens'] > 0:
                print(f"  {tier_name}:")
                print(f"    Tokens: {data['session_tokens']:,}")
                print(f"    Cost:   ${data['session_cost']:.4f}")

        print(f"\n  Session Total: ${report['session']['total']:.4f}")
        print("=" * 60)

    def save_session_to_db(self, checkpoint: str, task_name: str):
        """Save session costs to database via work_logs."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO work_logs (
                        checkpoint, task_name, status,
                        llm_tier1_calls, llm_tier2_calls, llm_tier3_calls,
                        estimated_cost
                    ) VALUES (
                        :checkpoint, :task_name, 'completed',
                        :t1_calls, :t2_calls, :t3_calls,
                        :cost
                    )
                """), {
                    'checkpoint': checkpoint,
                    'task_name': task_name,
                    't1_calls': self.session_stats['calls'][LLMTier.LOCAL],
                    't2_calls': self.session_stats['calls'][LLMTier.MINI],
                    't3_calls': self.session_stats['calls'][LLMTier.ADVANCED],
                    'cost': float(self.get_session_cost())
                })
                conn.commit()
        except Exception as e:
            print(f"Warning: Could not save to DB: {e}")


class CostEstimator:
    """Estimate costs before running tasks."""

    # Average tokens per task type
    AVG_TOKENS = {
        'entity_extraction': 300,
        'nature_classification': 150,
        'date_parsing': 100,
        'description_generation': 500,
        'relationship_inference': 400,
        'complex_analysis': 800
    }

    @classmethod
    def estimate_task_cost(cls, task_type: str, tier: LLMTier, count: int = 1) -> Decimal:
        """Estimate cost for running a task type."""
        avg_tokens = cls.AVG_TOKENS.get(task_type, 300)
        total_tokens = avg_tokens * count
        return (Decimal(str(total_tokens)) / 1000) * CostTracker.COSTS_PER_1K[tier]

    @classmethod
    def estimate_batch_cost(cls, tasks: Dict[str, Dict]) -> Dict:
        """
        Estimate cost for a batch of tasks.

        Args:
            tasks: Dict of {task_type: {'tier': LLMTier, 'count': int}}

        Returns:
            Cost breakdown by task and total
        """
        breakdown = {}
        total = Decimal('0')

        for task_type, config in tasks.items():
            tier = config.get('tier', LLMTier.LOCAL)
            count = config.get('count', 1)
            cost = cls.estimate_task_cost(task_type, tier, count)
            breakdown[task_type] = {
                'count': count,
                'tier': tier.name,
                'estimated_cost': float(cost)
            }
            total += cost

        return {
            'breakdown': breakdown,
            'total_estimated': float(total)
        }

    @classmethod
    def print_estimate(cls, tasks: Dict[str, Dict]):
        """Print formatted cost estimate."""
        estimate = cls.estimate_batch_cost(tasks)

        print("\nCost Estimate:")
        print("-" * 40)
        for task_type, data in estimate['breakdown'].items():
            print(f"  {task_type}:")
            print(f"    Count: {data['count']}, Tier: {data['tier']}")
            print(f"    Est. Cost: ${data['estimated_cost']:.4f}")
        print("-" * 40)
        print(f"  TOTAL ESTIMATE: ${estimate['total_estimated']:.4f}")


def main():
    """Test cost tracking."""
    print("Testing Cost Tracker...")

    tracker = CostTracker(budget=Decimal('300.00'))

    # Simulate some calls
    print("\nSimulating API calls...")
    tracker.record_call(LLMTier.LOCAL, 500)
    tracker.record_call(LLMTier.LOCAL, 300)
    tracker.record_call(LLMTier.MINI, 400)
    tracker.record_call(LLMTier.ADVANCED, 800)

    # Print report
    tracker.print_report()

    # Test estimator
    print("\n\nTesting Cost Estimator...")
    CostEstimator.print_estimate({
        'entity_extraction': {'tier': LLMTier.LOCAL, 'count': 1000},
        'description_generation': {'tier': LLMTier.MINI, 'count': 500},
        'relationship_inference': {'tier': LLMTier.ADVANCED, 'count': 100}
    })


if __name__ == '__main__':
    main()
