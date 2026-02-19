"""
Event model.

The core data type in CHALDEAS, representing historical occurrences
in time and space. Supports BCE dates using negative integers.

Slimmed to 21 core columns. Content fields (description, URLs, precise dates)
are stored in EventDetail (1:1).

V1 Extension:
- temporal_scale: Braudel's 3 levels (evenementielle, conjuncture, longue_duree)
- period_id: Link to Period for era classification
- certainty: How certain is this event? (fact, probable, legendary, mythological)
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship, backref

from app.models.base import Base, TimestampMixin


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)

    # Identification
    wikidata_id = Column(String(50), nullable=True, index=True)

    # Title (multilingual)
    title = Column(String(500), nullable=False)
    title_ko = Column(String(500))
    title_ja = Column(String(500))

    # Temporal data (BCE support: negative numbers)
    # -490 = 490 BCE, 476 = 476 CE
    date_start = Column(Integer, nullable=True, index=True)
    date_end = Column(Integer)
    date_precision = Column(String(20), default="year")  # exact, year, decade, century

    # V1: Braudel's Temporal Scale
    temporal_scale = Column(
        String(20),
        CheckConstraint(
            "temporal_scale IN ('evenementielle', 'conjuncture', 'longue_duree')"
        ),
        default="evenementielle",
        nullable=True
    )

    # Importance (1-5, higher = more significant)
    importance = Column(
        Integer,
        CheckConstraint("importance >= 1 AND importance <= 5"),
        default=3,
        index=True
    )

    # V1: Certainty Level
    certainty = Column(
        String(20),
        CheckConstraint(
            "certainty IN ('fact', 'probable', 'legendary', 'mythological')"
        ),
        default="fact",
        nullable=True
    )

    # Foreign keys
    category_id = Column(Integer, ForeignKey("categories.id"), index=True)
    primary_location_id = Column(Integer, ForeignKey("locations.id"))

    # V1: Link to Period
    period_id = Column(Integer, ForeignKey("periods.id"), nullable=True, index=True)

    # === Event Hierarchy ===
    parent_event_id = Column(Integer, ForeignKey("events.id"), nullable=True, index=True)
    is_aggregate = Column(Boolean, default=False, index=True)
    hierarchy_level = Column(Integer, default=3, index=True)
    aggregate_type = Column(String(50), nullable=True, index=True)
    parent_status = Column(String(20), default="unknown", index=True)

    # Relationships
    category = relationship("Category", back_populates="events")
    primary_location = relationship(
        "Location",
        back_populates="primary_events",
        foreign_keys=[primary_location_id]
    )
    locations = relationship(
        "Location",
        secondary="event_locations",
        back_populates="events"
    )
    persons = relationship(
        "Person",
        secondary="event_persons",
        back_populates="events"
    )
    sources = relationship(
        "Source",
        secondary="event_sources",
        back_populates="events"
    )

    # 1:1 Details
    details = relationship(
        "EventDetail",
        back_populates="event",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined"
    )

    # V1: Period relationship
    period = relationship("Period", back_populates="events", foreign_keys=[period_id])

    # Event Hierarchy relationship (self-referential)
    children = relationship(
        "Event",
        backref=backref("parent", remote_side="Event.id"),
        lazy="dynamic",
        foreign_keys=[parent_event_id]
    )

    def __repr__(self):
        return f"<Event(id={self.id}, title='{self.title}', year={self.date_start})>"

    @property
    def date_display(self) -> str:
        """Human-readable date string."""
        if self.date_start is None:
            return "Unknown"
        year = abs(self.date_start)
        era = "BCE" if self.date_start < 0 else "CE"

        if self.date_precision == "century":
            century = (year // 100) + 1
            return f"{century}th century {era}"
        elif self.date_precision == "decade":
            decade = (year // 10) * 10
            return f"{decade}s {era}"
        elif self.date_precision == "exact" and self.details:
            if self.details.date_start_month:
                if self.details.date_start_day:
                    return f"{year}-{self.details.date_start_month:02d}-{self.details.date_start_day:02d} {era}"
                return f"{year}-{self.details.date_start_month:02d} {era}"

        return f"{year} {era}"

    @property
    def is_bce(self) -> bool:
        """Check if event occurred in BCE."""
        return self.date_start is not None and self.date_start < 0
