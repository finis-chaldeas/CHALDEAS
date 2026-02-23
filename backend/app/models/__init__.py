"""
SQLAlchemy models for CHALDEAS.

These models represent the world state (Layer 1: Schema in World-Centric Architecture).

V0: Legacy models (현재 운영)
V1: Historical Chain 기반 신규 모델 (개발 중)
"""
from app.models.base import Base
from app.models.category import Category
from app.models.location import Location
from app.models.location_name import LocationName
from app.models.location_detail import LocationDetail
from app.models.event import Event
from app.models.event_detail import EventDetail
from app.models.person import Person
from app.models.person_detail import PersonDetail
from app.models.person_name import PersonName
from app.models.source import Source
from app.models.master import Master, SearchLog
from app.models.event_parent import EventParent, ParentContext
from app.models.event_coords_cache import EventCoordsCache
from app.models.territory import Territory, TerritoryLocation
from app.models.associations import (
    event_locations,
    event_persons,
    event_sources,
    person_sources,
    person_relationships,
    event_relationships,
    # V1: New associations
    polity_relationships,
    person_polities,
)

# Timeline / Curation Models
from app.models.period_narrative import PeriodNarrative
from app.models.entity_narrative import EntityNarrative
from app.models.user_feedback import UserFeedback
from app.models.history import History, HistoryEntity

# V1 Models
from app.models.v1 import (
    Period,
    Polity,
    HistoricalChain,
    ChainSegment,
    ChainEntityRole,
    TextMention,
    EntityAlias,
    ImportBatch,
    PendingEntity,
)

__all__ = [
    # Base
    "Base",
    # V0 Models
    "Category",
    "Location",
    "LocationName",
    "LocationDetail",
    "Event",
    "EventDetail",
    "Person",
    "PersonDetail",
    "PersonName",
    "Source",
    "Master",
    "SearchLog",
    "EventParent",
    "ParentContext",
    # Location system
    "EventCoordsCache",
    "Territory",
    "TerritoryLocation",
    # V0 Associations
    "event_locations",
    "event_persons",
    "event_sources",
    "person_sources",
    "person_relationships",
    "event_relationships",
    # Timeline / Curation
    "PeriodNarrative",
    "EntityNarrative",
    "UserFeedback",
    "History",
    "HistoryEntity",
    # V1 Associations
    "polity_relationships",
    "person_polities",
    # V1 Models
    "Period",
    "Polity",
    "HistoricalChain",
    "ChainSegment",
    "ChainEntityRole",
    "TextMention",
    "EntityAlias",
    "ImportBatch",
    "PendingEntity",
]
