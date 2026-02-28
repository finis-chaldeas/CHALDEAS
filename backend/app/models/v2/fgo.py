"""
FGO models - Fate/Grand Order servant data and historical comparison.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base


class FGOServant(Base):
    __tablename__ = "fgo_servants"

    id = Column(Integer, primary_key=True, index=True)
    servant_id = Column(Integer, unique=True, nullable=False, index=True)  # FGO game ID
    name = Column(String(200), nullable=False)
    name_jp = Column(String(200))
    class_name = Column(String(50), nullable=False)  # Saber, Archer, etc.
    rarity = Column(Integer)  # 1-5 stars

    # Linked historical person
    person_id = Column(Integer, ForeignKey('persons.id'), index=True)

    # FGO-specific data
    noble_phantasm = Column(String(200))
    attribute = Column(String(50))  # Human, Earth, Sky, Star, Beast
    gender = Column(String(20))

    # Extended metadata
    name_ko = Column(String(200))
    dialogue_lines = Column(Integer, default=0)
    chapter_count = Column(Integer, default=0)
    is_original = Column(Boolean, default=False)  # FGO-original (not historical/mythological)
    atlas_id = Column(Integer)

    # Image
    portrait_url = Column(String(500))

    created_at = Column(DateTime, server_default='now()')
    updated_at = Column(DateTime, server_default='now()', onupdate='now()')

    # Relationships
    person = relationship("Person", foreign_keys=[person_id])
    comparisons = relationship("FGOHistoryComparison", back_populates="servant")

    def __repr__(self):
        return f"<FGOServant(id={self.servant_id}, name='{self.name}', class='{self.class_name}')>"


class FGOHistoryComparison(Base):
    __tablename__ = "fgo_history_comparison"

    id = Column(Integer, primary_key=True, index=True)
    servant_id = Column(Integer, ForeignKey('fgo_servants.id', ondelete='CASCADE'), nullable=False, index=True)

    # Comparison aspects
    aspect = Column(
        String(50),
        CheckConstraint(
            "aspect IN ('biography', 'appearance', 'abilities', 'personality', 'relationships', 'noble_phantasm')",
            name='ck_fgo_comparison_aspect'
        ),
        nullable=False
    )
    fgo_description = Column(Text)
    historical_description = Column(Text)

    # Accuracy assessment
    accuracy_score = Column(Integer)  # 1-5
    assessment = Column(
        String(30),
        CheckConstraint(
            "assessment IN ('accurate', 'artistic_license', 'fictional', 'composite', 'gender_swap')",
            name='ck_fgo_comparison_assessment'
        )
    )
    notes = Column(Text)

    created_at = Column(DateTime, server_default='now()')

    # Relationships
    servant = relationship("FGOServant", back_populates="comparisons")

    def __repr__(self):
        return f"<FGOHistoryComparison(servant_id={self.servant_id}, aspect='{self.aspect}')>"
