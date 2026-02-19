"""
Cluster models - Event groupings.
"""
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey, DateTime, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base


class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(300), nullable=False)
    name_ko = Column(String(300))
    slug = Column(String(300), unique=True, nullable=False, index=True)
    description = Column(Text)
    description_ko = Column(Text)

    # Cluster type
    cluster_type = Column(
        String(30),
        CheckConstraint(
            "cluster_type IN ('spatiotemporal', 'causal', 'thematic', 'person_centric')",
            name='ck_clusters_type'
        ),
        nullable=False,
        index=True
    )

    # Temporal bounds
    date_start = Column(Integer, index=True)
    date_end = Column(Integer)

    # Spatial bounds (center point)
    center_lat = Column(Float)
    center_lng = Column(Float)
    radius_km = Column(Float)

    # Focal entity (optional)
    focal_person_id = Column(Integer, ForeignKey('persons.id'))
    focal_location_id = Column(Integer, ForeignKey('locations.id'))

    # Stats
    event_count = Column(Integer, default=0)
    importance = Column(Integer, default=3)

    # Auto-generation metadata
    is_auto_generated = Column(Boolean, default=False)
    generation_algorithm = Column(String(50))
    quality_score = Column(Float)

    created_at = Column(DateTime, server_default='now()')
    updated_at = Column(DateTime, server_default='now()', onupdate='now()')

    # Relationships
    focal_person = relationship("Person", foreign_keys=[focal_person_id])
    focal_location = relationship("Location", foreign_keys=[focal_location_id])
    events = relationship("ClusterEvent", back_populates="cluster")

    def __repr__(self):
        return f"<Cluster(id={self.id}, name='{self.name}', type='{self.cluster_type}')>"


class ClusterEvent(Base):
    __tablename__ = "cluster_events"

    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey('clusters.id', ondelete='CASCADE'), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey('events_v2.id', ondelete='CASCADE'), nullable=False, index=True)
    role_in_cluster = Column(String(30), default='member')  # core, member, peripheral
    sequence_number = Column(Integer)  # For ordered clusters
    added_at = Column(DateTime, server_default='now()')

    __table_args__ = (
        UniqueConstraint('cluster_id', 'event_id', name='uq_cluster_event'),
    )

    # Relationships
    cluster = relationship("Cluster", back_populates="events")
    event = relationship("EventV2", back_populates="clusters")

    def __repr__(self):
        return f"<ClusterEvent(cluster_id={self.cluster_id}, event_id={self.event_id})>"
