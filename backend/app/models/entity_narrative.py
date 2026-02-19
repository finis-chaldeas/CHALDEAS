"""
EntityNarrative model.

Stores AI-generated narratives for individual events and persons.
Each narrative includes significance, causes, and consequences.

Used by the Timeline view for detailed entity descriptions within periods.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import ARRAY

from app.models.base import Base


class EntityNarrative(Base):
    __tablename__ = "entity_narratives"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(10), nullable=False, index=True)  # 'event' or 'person'
    entity_id = Column(Integer, nullable=False)
    period_start = Column(Integer)  # Which period this belongs to

    # Narrative content
    narrative = Column(Text)         # 100-150 word narrative
    narrative_ko = Column(Text)
    significance = Column(String(500))
    causes = Column(ARRAY(Text))
    consequences = Column(ARRAY(Text))

    # Generation metadata
    model_used = Column(String(50))
    source_url = Column(String(500))  # Wikipedia URL used
    generated_at = Column(DateTime, server_default=func.now())

    # Curation
    curated_status = Column(String(20), default="auto")  # auto/reviewed/flagged
    curated_by = Column(String(100))
    curated_at = Column(DateTime)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<EntityNarrative({self.entity_type}:{self.entity_id})>"
