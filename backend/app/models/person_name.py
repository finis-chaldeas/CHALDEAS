"""
PersonName model.

Manages person aliases across languages, time periods, and contexts.
Same person can have different names (Alexander III = Iskander = 알렉산드로스).

Mirrors LocationName structure for consistency.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.models.base import Base


class PersonName(Base):
    __tablename__ = "person_names"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(
        Integer,
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Name
    name = Column(String(255), nullable=False, index=True)
    name_ko = Column(String(255))
    name_ja = Column(String(255))

    # Valid period (optional)
    valid_from = Column(Integer)   # NULL = start unknown
    valid_until = Column(Integer)  # NULL = still current

    # Language
    language = Column(String(10), default='en')

    # Primary name for this period
    is_primary = Column(Boolean, default=False)

    # Name type
    name_type = Column(String(30), default='official')
    # Types: official, regnal, epithet, religious, alternate, romanized, native

    # Source
    source = Column(String(100))  # wikidata, manual, wikipedia
    wikidata_id = Column(String(50), index=True)

    created_at = Column(DateTime, server_default=func.now())

    # Relationship
    person = relationship("Person", back_populates="names")

    def __repr__(self):
        period = ""
        if self.valid_from or self.valid_until:
            fr = self.valid_from or "?"
            to = self.valid_until or "present"
            period = f" ({fr}~{to})"
        return f"<PersonName('{self.name}'{period})>"

    def is_valid_in(self, year: int) -> bool:
        """Check if this name is valid in a given year."""
        if self.valid_from is not None and year < self.valid_from:
            return False
        if self.valid_until is not None and year > self.valid_until:
            return False
        return True
