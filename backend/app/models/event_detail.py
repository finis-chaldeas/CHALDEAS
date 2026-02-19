"""
EventDetail model.

Stores non-essential event information (description, URLs, precise dates,
display hints, etc.) that doesn't belong in the core event node.

1:1 relationship with Event.
"""
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.models.base import Base


class EventDetail(Base):
    __tablename__ = "event_details"

    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        primary_key=True
    )

    # URL / slug
    slug = Column(String(500))
    wikipedia_url = Column(String(500))
    image_url = Column(String(500))

    # Content (multilingual)
    description = Column(Text)
    description_ko = Column(Text)
    description_ja = Column(Text)
    description_source = Column(String(50))
    description_source_url = Column(String(500))

    # Precise dates (more detail than date_start/date_end years)
    date_start_month = Column(Integer)
    date_start_day = Column(Integer)
    date_end_month = Column(Integer)
    date_end_day = Column(Integer)

    # Display hints
    source_reliability = Column(Integer, default=3)
    default_collapsed = Column(Boolean, default=False)
    min_zoom_level = Column(Float, default=1.0)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    event = relationship("Event", back_populates="details")

    def __repr__(self):
        return f"<EventDetail(event_id={self.event_id})>"
