"""History schemas - Request/response models for history API."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class HistoryEntityBase(BaseModel):
    entity_type: str
    entity_id: int
    entity_name: Optional[str] = None


class HistoryEntityResponse(HistoryEntityBase):
    id: int
    role: str = "mentioned"

    class Config:
        from_attributes = True


class HistoryCreate(BaseModel):
    title: str
    title_ko: Optional[str] = None
    title_ja: Optional[str] = None
    summary: Optional[str] = None
    era_start: Optional[int] = None
    era_end: Optional[int] = None
    body: str
    body_ko: Optional[str] = None
    body_ja: Optional[str] = None
    category: str = "essay"
    tags: list[str] = []
    author_type: str = "user"
    author_name: Optional[str] = None
    importance: int = 3
    featured_entities: list[HistoryEntityBase] = []
    locations: list[HistoryEntityBase] = []


class HistoryUpdate(BaseModel):
    title: Optional[str] = None
    title_ko: Optional[str] = None
    title_ja: Optional[str] = None
    summary: Optional[str] = None
    era_start: Optional[int] = None
    era_end: Optional[int] = None
    body: Optional[str] = None
    body_ko: Optional[str] = None
    body_ja: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    author_name: Optional[str] = None
    importance: Optional[int] = None
    status: Optional[str] = None
    featured_entities: Optional[list[HistoryEntityBase]] = None
    locations: Optional[list[HistoryEntityBase]] = None


class HistoryResponse(BaseModel):
    id: int
    title: str
    title_ko: Optional[str] = None
    title_ja: Optional[str] = None
    summary: Optional[str] = None
    era_start: Optional[int] = None
    era_end: Optional[int] = None
    body: str
    body_ko: Optional[str] = None
    body_ja: Optional[str] = None
    category: str
    tags: list[str] = []
    author_type: str
    author_name: Optional[str] = None
    importance: int
    status: str
    entities: list[HistoryEntityResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HistoryListItem(BaseModel):
    id: int
    title: str
    title_ko: Optional[str] = None
    summary: Optional[str] = None
    era_start: Optional[int] = None
    era_end: Optional[int] = None
    category: str
    author_type: str
    author_name: Optional[str] = None
    importance: int
    status: str
    entity_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class HistoryList(BaseModel):
    items: list[HistoryListItem]
    total: int
