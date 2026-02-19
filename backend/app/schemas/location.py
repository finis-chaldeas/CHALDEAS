"""Location schemas."""
from pydantic import BaseModel
from typing import Optional


class LocationBase(BaseModel):
    name: str
    name_ko: Optional[str] = None
    name_ja: Optional[str] = None
    latitude: float
    longitude: float
    location_type: str = 'point'
    parent_location_id: Optional[int] = None


class Location(LocationBase):
    id: int
    wikidata_id: Optional[str] = None

    class Config:
        from_attributes = True


class LocationName(BaseModel):
    id: int
    name: str
    name_ko: Optional[str] = None
    name_ja: Optional[str] = None
    valid_from: Optional[int] = None
    valid_until: Optional[int] = None
    is_primary: bool = False
    name_type: str = 'official'

    class Config:
        from_attributes = True


class LocationDetail(Location):
    names: list[LocationName] = []


class LocationList(BaseModel):
    items: list[Location]
    total: int
