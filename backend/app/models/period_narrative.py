"""
PeriodNarrative model.

Stores AI-generated narratives for 50-year historical periods.
Each period gets an overview headline, narrative, keywords, and defining moment.

Used by the Timeline view for era-based historical exploration.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import ARRAY

from app.models.base import Base


class PeriodNarrative(Base):
    __tablename__ = "period_narratives"

    id = Column(Integer, primary_key=True, index=True)
    period_start = Column(Integer, nullable=False, index=True)  # e.g., -500
    period_end = Column(Integer, nullable=False)                # e.g., -451

    # Era classification
    era_id = Column(String(20))  # 'ancient', 'classical', 'medieval', etc.

    # Region (NULL = global overview, else regional sub-narrative)
    region = Column(String(30))  # 'europe', 'east_asia', 'south_asia', 'near_east', 'africa', 'americas'

    # Period overview
    headline = Column(String(200))
    headline_ko = Column(String(200))
    narrative = Column(Text)         # 200-300 word overview
    narrative_ko = Column(Text)
    keywords = Column(ARRAY(Text))   # Major themes
    defining_moment = Column(String(500))

    # Quote
    quote = Column(String(500))       # Representative historical quote
    quote_source = Column(String(200))  # Attribution

    # Quick display data (denormalized)
    event_count = Column(Integer, default=0)
    person_count = Column(Integer, default=0)
    top_events = Column(Text)    # JSON array for quick display
    top_persons = Column(Text)   # JSON array for quick display

    # Generation metadata
    model_used = Column(String(50))
    generated_at = Column(DateTime, server_default=func.now())
    quality_score = Column(Integer)

    # Curation
    curated_status = Column(String(20), default="auto")  # auto/reviewed/flagged
    curated_by = Column(String(100))
    curated_at = Column(DateTime)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        # Each period is unique
        {"schema": None},
    )

    def __repr__(self):
        return f"<PeriodNarrative({self.period_start}~{self.period_end})>"
