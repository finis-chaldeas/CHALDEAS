"""
WorkLog model - Checkpoint logging.
"""
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, CheckConstraint

from app.models.base import Base


class WorkLog(Base):
    __tablename__ = "work_logs"

    id = Column(Integer, primary_key=True, index=True)
    checkpoint = Column(String(20), nullable=False, index=True)
    task_name = Column(String(200), nullable=False)
    status = Column(
        String(20),
        CheckConstraint(
            "status IN ('started', 'in_progress', 'completed', 'failed')",
            name='ck_work_logs_status'
        ),
        nullable=False,
        default='started',
        index=True
    )
    started_at = Column(DateTime, server_default='now()')
    completed_at = Column(DateTime)
    duration_minutes = Column(Integer)
    notes = Column(Text)

    # Statistics
    records_processed = Column(Integer, default=0)
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)

    # Cost tracking
    llm_tier1_calls = Column(Integer, default=0)
    llm_tier2_calls = Column(Integer, default=0)
    llm_tier3_calls = Column(Integer, default=0)
    estimated_cost = Column(Numeric(10, 4), default=0)

    def __repr__(self):
        return f"<WorkLog(checkpoint='{self.checkpoint}', task='{self.task_name}', status='{self.status}')>"
