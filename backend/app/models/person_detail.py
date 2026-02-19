"""
PersonDetail model.

Stores non-essential person information (biography, URLs, precise dates, etc.)
that doesn't belong in the core person node. Displayed in the "Details" tab.

1:1 relationship with Person.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.models.base import Base


class PersonDetail(Base):
    __tablename__ = "person_details"

    person_id = Column(
        Integer,
        ForeignKey("persons.id", ondelete="CASCADE"),
        primary_key=True
    )

    # URL / slug
    slug = Column(String(255))
    wikipedia_url = Column(String(500))
    image_url = Column(String(500))

    # Precise dates (more detail than birth_year/death_year)
    birth_month = Column(Integer)
    birth_day = Column(Integer)
    death_month = Column(Integer)
    death_day = Column(Integer)
    birth_date_precision = Column(String(20), default="year")
    death_date_precision = Column(String(20), default="year")

    # Biography (multilingual)
    biography = Column(Text)
    biography_ko = Column(Text)
    biography_ja = Column(Text)
    biography_source = Column(String(50))
    biography_source_url = Column(String(500))

    # Additional classification
    category_id = Column(Integer, ForeignKey("categories.id"))
    era = Column(String(100))

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    person = relationship("Person", back_populates="details")
    category = relationship("Category")

    def __repr__(self):
        return f"<PersonDetail(person_id={self.person_id})>"
