"""History models - User/system authored historical essays with entity tagging."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import Base


class History(Base):
    __tablename__ = "histories"

    id = Column(Integer, primary_key=True, index=True)

    # Meta
    title = Column(String(300), nullable=False)
    title_ko = Column(String(300))
    title_ja = Column(String(300))
    summary = Column(String(500))

    # Temporal scope
    era_start = Column(Integer)
    era_end = Column(Integer)

    # Body (Markdown with [name](entity:type:id) tags)
    body = Column(Text, nullable=False)
    body_ko = Column(Text)
    body_ja = Column(Text)

    # Classification
    category = Column(String(50), default="essay")
    tags = Column(ARRAY(Text))

    # Author
    author_type = Column(String(20), default="system")
    author_name = Column(String(100))

    # Status
    status = Column(String(20), default="published")
    importance = Column(Integer, default=3)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    entities = relationship("HistoryEntity", cascade="all, delete-orphan", back_populates="history")


class HistoryEntity(Base):
    __tablename__ = "history_entities"

    id = Column(Integer, primary_key=True, index=True)
    history_id = Column(Integer, ForeignKey("histories.id", ondelete="CASCADE"), nullable=False)

    # Linked entity
    entity_type = Column(String(20), nullable=False)  # person, event, location, shift
    entity_id = Column(Integer, nullable=False)
    entity_name = Column(String(255))  # Display name snapshot

    # Role: featured / mentioned / location
    role = Column(String(20), default="mentioned")

    # Unique constraint
    __table_args__ = (
        UniqueConstraint("history_id", "entity_type", "entity_id", name="uq_history_entities_unique"),
    )

    # Relationships
    history = relationship("History", back_populates="entities")
