"""
UserFeedback model.

Stores user reports about incorrect, misleading, or missing content.
Supports feedback on narratives, domain classifications, and importance scores.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, func

from app.models.base import Base


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, index=True)

    # Target
    target_type = Column(String(20), nullable=False, index=True)  # 'period_narrative', 'entity_narrative', 'domain', 'score'
    target_id = Column(Integer, nullable=False)

    # Feedback content
    feedback_type = Column(String(20), nullable=False)  # 'incorrect', 'misleading', 'missing', 'wrong_domain', 'wrong_score'
    description = Column(Text)
    suggested_fix = Column(Text)

    # Reporter metadata (anonymous)
    reporter_ip = Column(String(50))

    # Review workflow
    status = Column(String(20), default="pending", index=True)  # pending/reviewed/accepted/rejected
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime)
    review_note = Column(Text)

    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<UserFeedback({self.target_type}:{self.target_id} - {self.feedback_type})>"
