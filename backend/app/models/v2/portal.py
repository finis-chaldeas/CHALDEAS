"""
Trismegistus Portal models.

PortalItem: Curated articles/showcases (migrated from JSON files).
Collection: Themed exhibition rooms grouping diverse content.
CollectionEntry: Polymorphic M2M linking collections to various content types.
"""
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, ForeignKey,
    CheckConstraint, DateTime
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class PortalItem(Base):
    """
    A curated article or showcase piece.

    Migrated from static JSON files (singularities, lostbelts, servants,
    history, literature, music). Each item is an independent content unit
    that can belong to one or more collections.
    """
    __tablename__ = "portal_items"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(200), unique=True, nullable=False, index=True)

    # Classification
    item_type = Column(
        String(30),
        CheckConstraint(
            "item_type IN ('singularity', 'lostbelt', 'servant_column', "
            "'history', 'literature', 'music', 'essay')",
            name="ck_portal_item_type"
        ),
        nullable=False,
        index=True
    )

    # Multilingual content
    title = Column(String(300), nullable=False)
    title_ko = Column(String(300))
    title_ja = Column(String(300))
    subtitle = Column(String(300))
    subtitle_ko = Column(String(300))
    subtitle_ja = Column(String(300))
    description = Column(Text, nullable=False)
    description_ko = Column(Text)
    description_ja = Column(Text)

    # Metadata
    chapter = Column(String(50))       # "Singularity F", "Lostbelt No.1"
    era = Column(String(100))          # "Modern Era", "Age of Gods"
    year = Column(Integer)             # 2004, -2655
    location = Column(String(200))     # "Fuyuki, Japan"

    # FGO connection
    historical_basis = Column(Text)
    historical_basis_ko = Column(Text)
    historical_basis_ja = Column(Text)

    # Structured content (display-only -> JSONB)
    sections = Column(JSONB, default=[])
    # [{ title, title_ko, title_ja, content, content_ko, content_ja }]

    related_servants = Column(JSONB, default=[])
    # [{ name, class, rarity }]

    related_event_ids = Column(JSONB, default=[])  # [int]
    sources = Column(JSONB, default=[])             # [string]

    # Curation
    sort_order = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False, index=True)
    thumbnail_url = Column(String(500))

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<PortalItem(slug='{self.slug}', type='{self.item_type}')>"


class Collection(Base):
    """
    A themed exhibition room grouping diverse content.

    Collections can contain shifts, portal items, persons, events,
    and periods via CollectionEntry.
    """
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(200), unique=True, nullable=False, index=True)

    collection_type = Column(
        String(30),
        CheckConstraint(
            "collection_type IN ('fgo_storyline', 'era', 'theme', 'content')",
            name="ck_collection_type"
        ),
        nullable=False,
        index=True
    )

    # Multilingual
    title = Column(String(300), nullable=False)
    title_ko = Column(String(300))
    title_ja = Column(String(300))
    description = Column(Text)
    description_ko = Column(Text)
    description_ja = Column(Text)

    # Display
    icon = Column(String(50))              # Emoji or icon ID
    cover_image_url = Column(String(500))
    sort_order = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False, index=True)

    # Auto-matching tags
    tags = Column(JSONB, default=[])       # ['greece', 'rome', 'ancient']

    # Time range
    year_start = Column(Integer)
    year_end = Column(Integer)
    region = Column(String(100))

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    entries = relationship(
        "CollectionEntry",
        back_populates="collection",
        order_by="CollectionEntry.sort_order",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Collection(slug='{self.slug}', type='{self.collection_type}')>"


class CollectionEntry(Base):
    """
    Links a collection to a content item (polymorphic M2M).

    Exactly one of the FK columns must be set, enforced by a check constraint.
    Same pattern as ChainEntityRole.
    """
    __tablename__ = "collection_entries"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(
        Integer,
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Polymorphic type
    entry_type = Column(
        String(30),
        CheckConstraint(
            "entry_type IN ('shift', 'portal_item', 'person', 'event', 'period')",
            name="ck_entry_type"
        ),
        nullable=False
    )

    # Exactly one FK set per row
    shift_id = Column(Integer, ForeignKey("historical_chains.id"), index=True)
    portal_item_id = Column(Integer, ForeignKey("portal_items.id"), index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), index=True)
    event_id = Column(Integer, ForeignKey("events.id"), index=True)
    period_id = Column(Integer, ForeignKey("periods.id"), index=True)

    # Display within collection
    sort_order = Column(Integer, default=0)
    is_highlighted = Column(Boolean, default=False)
    note = Column(String(300))
    note_ko = Column(String(300))

    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    collection = relationship("Collection", back_populates="entries")
    shift = relationship("HistoricalChain")
    portal_item = relationship("PortalItem")
    person = relationship("Person")
    event = relationship("Event")
    period = relationship("Period")

    __table_args__ = (
        CheckConstraint(
            "((shift_id IS NOT NULL)::int + (portal_item_id IS NOT NULL)::int + "
            "(person_id IS NOT NULL)::int + (event_id IS NOT NULL)::int + "
            "(period_id IS NOT NULL)::int) = 1",
            name="exactly_one_entry_ref"
        ),
    )

    def __repr__(self):
        return f"<CollectionEntry(collection_id={self.collection_id}, type='{self.entry_type}')>"
