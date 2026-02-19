"""
EventParent model.

Many-to-many relationship for event hierarchy with multiple parents.
Supports different contexts (war, culture, religion, etc.) for the same event
belonging to different parent events.
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class EventParent(Base):
    """
    Event-to-Parent relationship with context.

    Examples:
        - Pearl Harbor Attack -> WW2 (context='war', is_primary=True)
        - Pearl Harbor Attack -> Pacific War (context='war', is_primary=False)
        - Joan of Arc's Execution -> Hundred Years' War (context='war', is_primary=True)
        - Joan of Arc's Execution -> Medieval Inquisition (context='religion', is_primary=False)
    """
    __tablename__ = "event_parents"

    id = Column(Integer, primary_key=True, index=True)

    # The child event
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # The parent event
    parent_event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Is this the primary parent? (used for tree view display)
    is_primary = Column(Boolean, default=False, index=True)

    # Relationship context
    # war, culture, religion, politics, science, philosophy, general
    context = Column(String(50), nullable=True, index=True)

    # Classification metadata
    source = Column(String(50), nullable=True)  # wikidata, llm, manual, migration
    confidence = Column(Float, default=1.0)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint('event_id', 'parent_event_id', name='uq_event_parents_event_parent'),
        CheckConstraint('event_id != parent_event_id', name='ck_event_parents_no_self_ref'),
    )

    # Relationships
    event = relationship(
        "Event",
        foreign_keys=[event_id],
        backref="parent_relations"
    )
    parent_event = relationship(
        "Event",
        foreign_keys=[parent_event_id],
        backref="child_relations"
    )

    def __repr__(self):
        return f"<EventParent(event={self.event_id}, parent={self.parent_event_id}, primary={self.is_primary}, context={self.context})>"


# Context type constants
class ParentContext:
    WAR = "war"
    CULTURE = "culture"
    RELIGION = "religion"
    POLITICS = "politics"
    SCIENCE = "science"
    PHILOSOPHY = "philosophy"
    GENERAL = "general"

    ALL = [WAR, CULTURE, RELIGION, POLITICS, SCIENCE, PHILOSOPHY, GENERAL]
