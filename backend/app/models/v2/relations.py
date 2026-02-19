"""
Relation models - Event relations and person-event roles.
"""
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey, DateTime, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base


class EventRelationV2(Base):
    __tablename__ = "event_relations_v2"

    id = Column(Integer, primary_key=True, index=True)
    from_event_id = Column(Integer, ForeignKey('events_v2.id', ondelete='CASCADE'), nullable=False, index=True)
    to_event_id = Column(Integer, ForeignKey('events_v2.id', ondelete='CASCADE'), nullable=False, index=True)

    # Relation type
    relation_type = Column(
        String(30),
        CheckConstraint(
            "relation_type IN ('causes', 'follows', 'part_of', 'parallel_to', 'precedes', 'enables', 'opposes')",
            name='ck_event_relations_v2_type'
        ),
        nullable=False,
        index=True
    )

    # Wikidata property (e.g., P361 = part of, P155 = follows)
    wikidata_property = Column(String(20))

    # Strength and confidence
    strength = Column(Integer, default=3)
    confidence = Column(Float, default=1.0)

    # Evidence
    evidence_type = Column(String(30))  # wikidata, scholarly, inferred
    evidence_source = Column(Text)

    created_at = Column(DateTime, server_default='now()')

    __table_args__ = (
        UniqueConstraint('from_event_id', 'to_event_id', 'relation_type', name='uq_event_relation_v2'),
    )

    # Relationships
    from_event = relationship("EventV2", foreign_keys=[from_event_id], back_populates="outgoing_relations")
    to_event = relationship("EventV2", foreign_keys=[to_event_id], back_populates="incoming_relations")

    def __repr__(self):
        return f"<EventRelationV2(from={self.from_event_id}, to={self.to_event_id}, type='{self.relation_type}')>"


class PersonEventRole(Base):
    __tablename__ = "person_event_roles"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey('persons.id', ondelete='CASCADE'), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey('events_v2.id', ondelete='CASCADE'), nullable=False, index=True)

    # Role in the event
    role = Column(
        String(30),
        CheckConstraint(
            "role IN ('leader', 'participant', 'victim', 'witness', 'initiator', 'opponent', 'beneficiary', 'advisor', 'commander')",
            name='ck_person_event_roles_role'
        ),
        nullable=False,
        index=True
    )

    # Importance of this person to the event (1-5)
    importance = Column(Integer, default=3)

    # Was this person a primary actor?
    is_primary = Column(Boolean, default=False)

    # Evidence
    evidence_source = Column(String(100))
    confidence = Column(Float, default=1.0)

    created_at = Column(DateTime, server_default='now()')

    # Relationships
    person = relationship("Person", foreign_keys=[person_id])
    event = relationship("EventV2", back_populates="person_roles")

    def __repr__(self):
        return f"<PersonEventRole(person_id={self.person_id}, event_id={self.event_id}, role='{self.role}')>"
