"""
Territory and TerritoryLocation models.

Territories represent political/administrative entities that control locations over time.
TerritoryLocation tracks which locations belong to which territories and when.

Example: Seoul was part of Baekje → Goguryeo → Silla → Goryeo → Joseon → ...
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.models.base import Base


class Territory(Base):
    __tablename__ = "territories"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    name_ko = Column(String(255))
    wikidata_id = Column(String(20), unique=True)

    # Classification: empire, kingdom, republic, caliphate, etc.
    territory_type = Column(String(50), nullable=False)

    # When this territory existed (BCE as negative)
    founded_year = Column(Integer)
    dissolved_year = Column(Integer)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship to location memberships
    locations = relationship("TerritoryLocation", back_populates="territory", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Territory(id={self.id}, name='{self.name}')>"


class TerritoryLocation(Base):
    __tablename__ = "territory_locations"

    id = Column(Integer, primary_key=True)
    territory_id = Column(
        Integer,
        ForeignKey("territories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    location_id = Column(
        Integer,
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # When this location was part of this territory
    valid_from = Column(Integer)   # BCE as negative, NULL = unknown start
    valid_until = Column(Integer)  # NULL = still part of territory

    # Relation type: contains (default), capital
    relation_type = Column(String(50), default='contains', server_default='contains')

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('territory_id', 'location_id', 'valid_from', name='uq_territory_location_period'),
    )

    # Relationships
    territory = relationship("Territory", back_populates="locations")
    location = relationship("Location")

    def __repr__(self):
        return f"<TerritoryLocation(territory={self.territory_id}, location={self.location_id})>"
