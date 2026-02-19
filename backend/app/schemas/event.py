"""Event schemas."""
from pydantic import BaseModel
from typing import Optional

from app.schemas.category import Category
from app.schemas.location import Location
from app.schemas.source import Source


class EventDetailInfo(BaseModel):
    """Event detail data (from event_details table)."""
    slug: Optional[str] = None
    wikipedia_url: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    description_ko: Optional[str] = None
    description_ja: Optional[str] = None
    description_source: Optional[str] = None
    description_source_url: Optional[str] = None
    date_start_month: Optional[int] = None
    date_start_day: Optional[int] = None
    date_end_month: Optional[int] = None
    date_end_day: Optional[int] = None

    class Config:
        from_attributes = True


class EventBase(BaseModel):
    title: str
    title_ko: Optional[str] = None
    date_start: int  # Negative for BCE
    date_end: Optional[int] = None
    date_display: str
    importance: int = 3
    # Hierarchy fields
    parent_event_id: Optional[int] = None
    is_aggregate: bool = False
    hierarchy_level: int = 3  # 0=Era, 1=Mega, 2=Aggregate, 3=Major, 4=Minor
    aggregate_type: Optional[str] = None  # war, movement, dynasty, etc.
    parent_status: Optional[str] = None


class Event(EventBase):
    """Event for list/globe view."""
    id: int
    category: Optional[Category] = None
    location: Optional[Location] = None  # Primary location

    class Config:
        from_attributes = True


class PersonBrief(BaseModel):
    """Brief person info for event detail."""
    id: int
    name: str
    name_ko: Optional[str] = None
    role: Optional[str] = None

    class Config:
        from_attributes = True


class EventDetail(Event):
    """Full event details for wiki panel."""
    date_precision: str = "year"
    locations: list[Location] = []
    persons: list[PersonBrief] = []
    sources: list[Source] = []
    # Details from event_details table
    details: Optional[EventDetailInfo] = None


class EventList(BaseModel):
    items: list[Event]
    total: int
