"""
LocationDetail model.

Stores non-essential location information (description, URLs, etc.)
that doesn't belong in the core location node. Displayed in the "Details" tab.

1:1 relationship with Location.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.models.base import Base


class LocationDetail(Base):
    __tablename__ = "location_details"

    location_id = Column(
        Integer,
        ForeignKey("locations.id", ondelete="CASCADE"),
        primary_key=True
    )

    # Description (multilingual)
    description = Column(Text)
    description_ko = Column(Text)
    description_ja = Column(Text)
    description_source = Column(String(50))
    description_source_url = Column(String(500))

    # External links
    wikipedia_url = Column(String(500))

    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    location = relationship("Location", back_populates="details")

    def __repr__(self):
        return f"<LocationDetail(location_id={self.location_id})>"
