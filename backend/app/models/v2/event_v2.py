"""
EventV2 model - Enhanced events with vector attributes.
"""
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.models.base import Base


class EventV2(Base):
    __tablename__ = "events_v2"

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    title = Column(String(500), nullable=False)
    title_ko = Column(String(500))
    title_ja = Column(String(500))
    slug = Column(String(500), unique=True, nullable=False, index=True)
    description = Column(Text)
    description_ko = Column(Text)
    description_ja = Column(Text)

    # Temporal data (BCE support: negative numbers)
    date_start = Column(Integer, nullable=False, index=True)
    date_start_month = Column(Integer)
    date_start_day = Column(Integer)
    date_end = Column(Integer, index=True)
    date_end_month = Column(Integer)
    date_end_day = Column(Integer)
    date_precision = Column(String(20), default='year')

    # Braudel's temporal scale
    temporal_scale = Column(
        String(20),
        CheckConstraint(
            "temporal_scale IN ('evenementielle', 'conjuncture', 'longue_duree')",
            name='ck_events_v2_temporal_scale'
        ),
        default='evenementielle'
    )

    # Nature classification
    nature = Column(String(50), index=True)

    # Event vectors (origin/destination for movement events)
    origin_location_id = Column(Integer, ForeignKey('locations.id'))
    destination_location_id = Column(Integer, ForeignKey('locations.id'))
    vector_type = Column(String(50))

    # Hierarchy
    parent_event_id = Column(Integer, ForeignKey('events_v2.id'), index=True)
    hierarchy_level = Column(Integer, default=3, index=True)
    is_aggregate = Column(Boolean, default=False, index=True)
    aggregate_type = Column(String(50))

    # Classification
    certainty = Column(
        String(20),
        CheckConstraint(
            "certainty IN ('fact', 'probable', 'legendary', 'mythological')",
            name='ck_events_v2_certainty'
        ),
        default='fact'
    )
    importance = Column(
        Integer,
        CheckConstraint("importance >= 1 AND importance <= 5", name='ck_events_v2_importance'),
        default=3,
        index=True
    )

    # External references
    wikidata_id = Column(String(50), unique=True, index=True)
    wikipedia_url = Column(String(500))
    image_url = Column(String(500))

    # Embedding for vector search
    embedding = Column(Vector(1536))

    # Linked V0 event (for migration tracking)
    v0_event_id = Column(Integer, ForeignKey('events.id'), index=True)

    # Timestamps
    created_at = Column(DateTime, server_default='now()')
    updated_at = Column(DateTime, server_default='now()', onupdate='now()')

    # Relationships
    origin_location = relationship("Location", foreign_keys=[origin_location_id])
    destination_location = relationship("Location", foreign_keys=[destination_location_id])
    children = relationship("EventV2", backref="parent", remote_side=[id])
    v0_event = relationship("Event", foreign_keys=[v0_event_id])

    # Cluster relationship
    clusters = relationship("ClusterEvent", back_populates="event")

    # Person roles relationship
    person_roles = relationship("PersonEventRole", back_populates="event")

    # Relations
    outgoing_relations = relationship(
        "EventRelationV2",
        foreign_keys="EventRelationV2.from_event_id",
        back_populates="from_event"
    )
    incoming_relations = relationship(
        "EventRelationV2",
        foreign_keys="EventRelationV2.to_event_id",
        back_populates="to_event"
    )

    # Completeness
    completeness = relationship("EventCompleteness", back_populates="event", uselist=False)

    def __repr__(self):
        return f"<EventV2(id={self.id}, title='{self.title}', year={self.date_start})>"

    @property
    def date_display(self) -> str:
        """Human-readable date string."""
        year = abs(self.date_start)
        era = "BCE" if self.date_start < 0 else "CE"

        if self.date_precision == "century":
            century = (year // 100) + 1
            return f"{century}th century {era}"
        elif self.date_precision == "decade":
            decade = (year // 10) * 10
            return f"{decade}s {era}"
        elif self.date_precision == "exact" and self.date_start_month:
            if self.date_start_day:
                return f"{year}-{self.date_start_month:02d}-{self.date_start_day:02d} {era}"
            return f"{year}-{self.date_start_month:02d} {era}"

        return f"{year} {era}"

    @property
    def is_bce(self) -> bool:
        return self.date_start < 0

    @property
    def has_vector(self) -> bool:
        """Check if this is a movement/vector event."""
        return self.origin_location_id is not None and self.destination_location_id is not None
