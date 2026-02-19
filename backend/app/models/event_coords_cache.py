"""
EventCoordsCache model.

Stores the original coordinates for events (as extracted from Wikidata).
Used for reassigning events when new location nodes are added.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, func

from app.models.base import Base


class EventCoordsCache(Base):
    __tablename__ = "event_coords_cache"

    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        primary_key=True
    )

    # Original coordinates from Wikidata
    latitude = Column(Numeric(10, 7))
    longitude = Column(Numeric(10, 7))

    # How the coordinates were obtained
    coord_source = Column(String(30))
    # Values: p625 (Wikidata P625 direct), p276_resolved (P276 location's coords),
    #         name_geocoded (geocoded from name), inherited (from assigned location)

    # Wikidata QID that provided the coordinates
    source_qid = Column(String(20))

    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<EventCoordsCache(event_id={self.event_id}, lat={self.latitude}, lng={self.longitude})>"
