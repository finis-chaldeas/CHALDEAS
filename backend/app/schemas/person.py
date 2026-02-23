"""Person schemas."""
from pydantic import BaseModel
from typing import Optional

from app.schemas.location import Location
from app.schemas.source import Source


class PersonBase(BaseModel):
    name: str
    name_ko: Optional[str] = None
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    lifespan_display: str
    role: Optional[str] = None
    domain: Optional[str] = None
    global_score: Optional[int] = None


class Person(PersonBase):
    """Person for list view."""
    id: int
    wikidata_id: Optional[str] = None
    birthplace: Optional[Location] = None

    class Config:
        from_attributes = True


class PersonDetailInfo(BaseModel):
    """Detail info from person_details table."""
    slug: Optional[str] = None
    biography: Optional[str] = None
    biography_ko: Optional[str] = None
    biography_ja: Optional[str] = None
    biography_source: Optional[str] = None
    biography_source_url: Optional[str] = None
    image_url: Optional[str] = None
    wikipedia_url: Optional[str] = None
    birth_date_precision: Optional[str] = "year"
    death_date_precision: Optional[str] = "year"
    era: Optional[str] = None

    class Config:
        from_attributes = True


class PersonName(BaseModel):
    """Person alias/name entry."""
    id: int
    name: str
    name_ko: Optional[str] = None
    name_ja: Optional[str] = None
    language: str = "en"
    name_type: str = "official"
    is_primary: bool = False
    valid_from: Optional[int] = None
    valid_until: Optional[int] = None

    class Config:
        from_attributes = True


class PersonDetail(Person):
    """Full person details for wiki panel."""
    name_ja: Optional[str] = None
    certainty: Optional[str] = None
    floruit_start: Optional[int] = None
    floruit_end: Optional[int] = None
    deathplace: Optional[Location] = None
    details: Optional[PersonDetailInfo] = None
    names: list[PersonName] = []
    sources: list[Source] = []

    class Config:
        from_attributes = True


class PersonList(BaseModel):
    items: list[Person]
    total: int


class PersonRelation(BaseModel):
    """Related person with relationship strength."""
    id: int
    name: str
    name_ko: Optional[str] = None
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    strength: int = 0
    time_distance: Optional[int] = None
    relationship_type: Optional[str] = None
    is_bidirectional: int = 0

    @property
    def is_contemporary(self) -> bool:
        """True if persons lived in the same era."""
        return self.time_distance is None or self.time_distance <= 0


class PersonRelationList(BaseModel):
    person_id: int
    relations: list[PersonRelation]
    total: int


# Flow schemas
class FlowEvent(BaseModel):
    event_id: int
    title: str
    title_ko: Optional[str] = None
    year: Optional[int] = None
    year_end: Optional[int] = None
    location: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    role: Optional[str] = None


class FlowLocation(BaseModel):
    id: int
    name: str
    lat: Optional[float] = None
    lng: Optional[float] = None


class PersonFlow(BaseModel):
    person_id: int
    name: str
    name_ko: Optional[str] = None
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    birthplace: Optional[FlowLocation] = None
    deathplace: Optional[FlowLocation] = None
    flow: list[FlowEvent] = []
    total_events: int = 0
