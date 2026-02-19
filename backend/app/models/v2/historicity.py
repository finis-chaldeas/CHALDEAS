"""
Historicity model - Evidence for historical verification.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, CheckConstraint

from app.models.base import Base


class HistoricitySource(Base):
    __tablename__ = "historicity_sources"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(
        String(20),
        CheckConstraint(
            "entity_type IN ('event', 'person')",
            name='ck_historicity_sources_entity_type'
        ),
        nullable=False,
        index=True
    )
    entity_id = Column(Integer, nullable=False, index=True)

    # Source type
    source_type = Column(
        String(30),
        CheckConstraint(
            "source_type IN ('primary', 'secondary', 'archaeological', 'literary', 'oral', 'epigraphic')",
            name='ck_historicity_sources_source_type'
        ),
        nullable=False
    )

    # Source details
    source_name = Column(String(300), nullable=False)
    source_url = Column(String(500))
    author = Column(String(200))
    publication_year = Column(Integer)

    # Reliability assessment
    reliability_score = Column(Integer, default=3)  # 1-5
    assessment_notes = Column(Text)

    created_at = Column(DateTime, server_default='now()')

    def __repr__(self):
        return f"<HistoricitySource(entity={self.entity_type}:{self.entity_id}, source='{self.source_name}')>"
