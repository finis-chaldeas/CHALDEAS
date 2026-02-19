"""
Location model.

Represents fixed geographical nodes (points) where historical events occurred.
Each location is an immutable point with (latitude, longitude) coordinates.

Locations are nodes - once created, their coordinates don't change.
Time-varying attributes (names, territorial affiliation) are in separate tables.
"""
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class Location(Base, TimestampMixin):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)

    # External reference
    wikidata_id = Column(String(50), nullable=True, unique=True)

    # Representative name (current, for search/display)
    name = Column(String(255), nullable=False)
    name_ko = Column(String(255))
    name_ja = Column(String(255))

    # Coordinates (immutable, required)
    latitude = Column(Numeric(10, 8), nullable=False)
    longitude = Column(Numeric(11, 8), nullable=False)

    # Classification: point (cities, buildings, battlefields), natural (mountains, rivers), sea
    location_type = Column(String(30), nullable=False, default='point', server_default='point', index=True)

    # Modern country (for filtering/grouping)
    country = Column(String(100))

    # Physical hierarchy (immutable: 경복궁 → 서울)
    parent_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True, index=True)

    # === Relationships ===

    # M2M with events via event_locations
    events = relationship(
        "Event",
        secondary="event_locations",
        back_populates="locations"
    )

    # Events where this is the primary location
    primary_events = relationship(
        "Event",
        back_populates="primary_location",
        foreign_keys="Event.primary_location_id"
    )

    # Persons born here
    birthplace_of = relationship(
        "Person",
        back_populates="birthplace",
        foreign_keys="Person.birthplace_id"
    )

    # Physical hierarchy (parent/children)
    parent = relationship(
        "Location",
        remote_side=[id],
        foreign_keys=[parent_location_id],
        backref="children"
    )

    # Time-varying names
    names = relationship(
        "LocationName",
        back_populates="location",
        cascade="all, delete-orphan",
        order_by="LocationName.valid_from"
    )

    # 1:1 detail info (description, URLs)
    details = relationship(
        "LocationDetail",
        back_populates="location",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Location(id={self.id}, name='{self.name}')>"

    @property
    def coords(self) -> tuple[float, float]:
        """Return (latitude, longitude) tuple."""
        return (float(self.latitude), float(self.longitude))

    def get_name_at(self, year: int, language: str = 'en') -> str:
        """Get the name of this location at a specific year.

        Args:
            year: Year to query (BCE as negative)
            language: Language code (en, ko, ja)

        Returns:
            The period-appropriate name, or current name as fallback.
        """
        if not self.names:
            return self.name

        # Find primary name for the period
        for loc_name in self.names:
            if loc_name.is_primary and loc_name.is_valid_in(year):
                if language == 'ko' and loc_name.name_ko:
                    return loc_name.name_ko
                if language == 'ja' and loc_name.name_ja:
                    return loc_name.name_ja
                return loc_name.name

        # Fallback: any valid name for the period
        for loc_name in self.names:
            if loc_name.is_valid_in(year):
                if language == 'ko' and loc_name.name_ko:
                    return loc_name.name_ko
                if language == 'ja' and loc_name.name_ja:
                    return loc_name.name_ja
                return loc_name.name

        return self.name
