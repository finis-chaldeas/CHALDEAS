"""
Person model.

Represents an immutable historical person node.
Core identity: who, when born/died, where born/died, what role.

Detail information (biography, URLs, precise dates) → PersonDetail
Aliases (alternative names) → PersonName
"""
from sqlalchemy import Column, Integer, String, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class Person(Base, TimestampMixin):
    __tablename__ = "persons"

    id = Column(Integer, primary_key=True, index=True)
    wikidata_id = Column(String(20), unique=True, index=True)

    # Representative name (current)
    name = Column(String(255), nullable=False)
    name_ko = Column(String(255))
    name_ja = Column(String(255))

    # Time axis bookends (flow start/end)
    birth_year = Column(Integer, index=True)
    death_year = Column(Integer)

    # Floruit (when birth/death unknown)
    floruit_start = Column(Integer)
    floruit_end = Column(Integer)

    # Space axis anchors
    birthplace_id = Column(Integer, ForeignKey("locations.id"))
    deathplace_id = Column(Integer, ForeignKey("locations.id"))

    # Classification
    role = Column(String(255))  # king, philosopher, general, prophet, artist, scientist, ...
    certainty = Column(
        String(20),
        CheckConstraint(
            "certainty IN ('fact', 'probable', 'legendary', 'mythological')"
        ),
        default="fact",
        nullable=True
    )

    # === Relationships ===

    birthplace = relationship(
        "Location",
        back_populates="birthplace_of",
        foreign_keys=[birthplace_id]
    )
    deathplace = relationship("Location", foreign_keys=[deathplace_id])

    events = relationship(
        "Event",
        secondary="event_persons",
        back_populates="persons"
    )

    # 1:1 detail info (biography, URLs, precise dates)
    details = relationship(
        "PersonDetail",
        back_populates="person",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # Time-varying names / aliases
    names = relationship(
        "PersonName",
        back_populates="person",
        cascade="all, delete-orphan",
        order_by="PersonName.valid_from"
    )

    def __repr__(self):
        return f"<Person(id={self.id}, name='{self.name}')>"

    @property
    def lifespan_display(self) -> str:
        """Human-readable lifespan string."""
        if not self.birth_year and not self.death_year:
            if self.floruit_start:
                return f"fl. {abs(self.floruit_start)} {'BCE' if self.floruit_start < 0 else 'CE'}"
            return "Unknown"

        def format_year(year: int) -> str:
            if year is None:
                return "?"
            era = "BCE" if year < 0 else "CE"
            return f"{abs(year)} {era}"

        birth = format_year(self.birth_year) if self.birth_year else "?"
        death = format_year(self.death_year) if self.death_year else "?"

        # Simplify if same era
        if self.birth_year and self.death_year:
            if (self.birth_year < 0) == (self.death_year < 0):
                era = "BCE" if self.birth_year < 0 else "CE"
                return f"{abs(self.birth_year)}-{abs(self.death_year)} {era}"

        return f"{birth} - {death}"

    def was_alive_in(self, year: int) -> bool:
        """Check if person was alive in a given year."""
        if self.birth_year is None:
            if self.floruit_start is not None:
                fl_end = self.floruit_end or (self.floruit_start + 40)
                return self.floruit_start <= year <= fl_end
            return False
        if self.death_year is None:
            return self.birth_year <= year <= self.birth_year + 80
        return self.birth_year <= year <= self.death_year
