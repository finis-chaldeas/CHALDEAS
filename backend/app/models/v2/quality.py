"""
Quality tracking models - Completeness and fill queue.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base


class EventCompleteness(Base):
    __tablename__ = "event_completeness"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('events_v2.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)

    # Field completeness (0-100)
    title_score = Column(Integer, default=0)
    description_score = Column(Integer, default=0)
    date_score = Column(Integer, default=0)
    location_score = Column(Integer, default=0)
    persons_score = Column(Integer, default=0)
    relations_score = Column(Integer, default=0)
    sources_score = Column(Integer, default=0)

    # Overall completeness
    overall_score = Column(Integer, default=0, index=True)

    # Flags
    needs_review = Column(Boolean, default=False, index=True)
    is_stub = Column(Boolean, default=True)

    last_calculated_at = Column(DateTime, server_default='now()')

    # Relationships
    event = relationship("EventV2", back_populates="completeness")

    def __repr__(self):
        return f"<EventCompleteness(event_id={self.event_id}, score={self.overall_score})>"

    def calculate_overall(self):
        """Calculate overall score from individual scores."""
        weights = {
            'title': 0.05,
            'description': 0.30,
            'date': 0.15,
            'location': 0.15,
            'persons': 0.15,
            'relations': 0.10,
            'sources': 0.10,
        }
        self.overall_score = int(
            self.title_score * weights['title'] +
            self.description_score * weights['description'] +
            self.date_score * weights['date'] +
            self.location_score * weights['location'] +
            self.persons_score * weights['persons'] +
            self.relations_score * weights['relations'] +
            self.sources_score * weights['sources']
        )
        self.is_stub = self.overall_score < 30


class FillQueue(Base):
    __tablename__ = "fill_queue"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(
        String(20),
        CheckConstraint(
            "entity_type IN ('event', 'person', 'cluster')",
            name='ck_fill_queue_entity_type'
        ),
        nullable=False,
        index=True
    )
    entity_id = Column(Integer, nullable=False, index=True)

    # Task type
    task_type = Column(String(50), nullable=False, index=True)

    # Priority (higher = more urgent)
    priority = Column(Integer, default=0, index=True)

    # Status
    status = Column(
        String(20),
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'skipped')",
            name='ck_fill_queue_status'
        ),
        default='pending',
        index=True
    )

    # LLM tier to use
    llm_tier = Column(Integer, default=1)

    # Processing info
    attempts = Column(Integer, default=0)
    last_attempt_at = Column(DateTime)
    error_message = Column(Text)

    created_at = Column(DateTime, server_default='now()')

    def __repr__(self):
        return f"<FillQueue(entity={self.entity_type}:{self.entity_id}, task='{self.task_type}', status='{self.status}')>"
