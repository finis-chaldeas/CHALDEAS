"""
Trismegistus Portal API — curated content, collections, featured items.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.v2.portal import PortalItem, Collection, CollectionEntry

router = APIRouter()


# === Pydantic Schemas ===

class PortalItemSummary(BaseModel):
    id: int
    slug: str
    item_type: str
    title: str
    title_ko: Optional[str] = None
    title_ja: Optional[str] = None
    subtitle: Optional[str] = None
    subtitle_ko: Optional[str] = None
    subtitle_ja: Optional[str] = None
    chapter: Optional[str] = None
    era: Optional[str] = None
    year: Optional[int] = None
    location: Optional[str] = None
    is_featured: bool = False
    thumbnail_url: Optional[str] = None
    sort_order: int = 0

    class Config:
        from_attributes = True


class PortalItemDetail(PortalItemSummary):
    description: str
    description_ko: Optional[str] = None
    description_ja: Optional[str] = None
    historical_basis: Optional[str] = None
    historical_basis_ko: Optional[str] = None
    historical_basis_ja: Optional[str] = None
    sections: list = []
    related_servants: list = []
    related_event_ids: list = []
    sources: list = []


class CollectionEntrySummary(BaseModel):
    id: int
    entry_type: str
    sort_order: int = 0
    is_highlighted: bool = False
    note: Optional[str] = None
    note_ko: Optional[str] = None
    # Resolved reference (one of these will be set)
    portal_item: Optional[PortalItemSummary] = None
    shift_id: Optional[int] = None
    person_id: Optional[int] = None
    event_id: Optional[int] = None
    period_id: Optional[int] = None

    class Config:
        from_attributes = True


class CollectionSummary(BaseModel):
    id: int
    slug: str
    collection_type: str
    title: str
    title_ko: Optional[str] = None
    title_ja: Optional[str] = None
    description: Optional[str] = None
    description_ko: Optional[str] = None
    description_ja: Optional[str] = None
    icon: Optional[str] = None
    cover_image_url: Optional[str] = None
    sort_order: int = 0
    is_featured: bool = False
    tags: list = []
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    region: Optional[str] = None
    entry_count: int = 0

    class Config:
        from_attributes = True


class CollectionDetail(CollectionSummary):
    entries: List[CollectionEntrySummary] = []


class FeaturedResponse(BaseModel):
    items: List[PortalItemSummary]
    collections: List[CollectionSummary]


# === Endpoints ===

@router.get("/items", response_model=List[PortalItemSummary])
def list_portal_items(
    item_type: Optional[str] = Query(None, description="Filter by type"),
    is_featured: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List portal items with optional filtering."""
    q = db.query(PortalItem)
    if item_type:
        q = q.filter(PortalItem.item_type == item_type)
    if is_featured is not None:
        q = q.filter(PortalItem.is_featured == is_featured)
    q = q.order_by(PortalItem.sort_order, PortalItem.id)
    total = q.count()
    items = q.offset(offset).limit(limit).all()
    return items


@router.get("/items/{slug}", response_model=PortalItemDetail)
def get_portal_item(slug: str, db: Session = Depends(get_db)):
    """Get a single portal item by slug."""
    item = db.query(PortalItem).filter(PortalItem.slug == slug).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Portal item '{slug}' not found")
    return item


@router.get("/collections", response_model=List[CollectionSummary])
def list_collections(
    collection_type: Optional[str] = Query(None),
    is_featured: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """List all collections."""
    q = db.query(Collection)
    if collection_type:
        q = q.filter(Collection.collection_type == collection_type)
    if is_featured is not None:
        q = q.filter(Collection.is_featured == is_featured)
    collections = q.order_by(Collection.sort_order, Collection.id).all()

    results = []
    for c in collections:
        entry_count = db.query(CollectionEntry).filter(
            CollectionEntry.collection_id == c.id
        ).count()
        summary = CollectionSummary.model_validate(c)
        summary.entry_count = entry_count
        results.append(summary)
    return results


@router.get("/collections/{slug}", response_model=CollectionDetail)
def get_collection(slug: str, db: Session = Depends(get_db)):
    """Get a collection with its entries."""
    collection = (
        db.query(Collection)
        .options(
            joinedload(Collection.entries).joinedload(CollectionEntry.portal_item)
        )
        .filter(Collection.slug == slug)
        .first()
    )
    if not collection:
        raise HTTPException(status_code=404, detail=f"Collection '{slug}' not found")

    entry_count = len(collection.entries)
    entries = []
    for e in sorted(collection.entries, key=lambda x: x.sort_order):
        entry_data = CollectionEntrySummary(
            id=e.id,
            entry_type=e.entry_type,
            sort_order=e.sort_order,
            is_highlighted=e.is_highlighted,
            note=e.note,
            note_ko=e.note_ko,
            portal_item=PortalItemSummary.model_validate(e.portal_item) if e.portal_item else None,
            shift_id=e.shift_id,
            person_id=e.person_id,
            event_id=e.event_id,
            period_id=e.period_id,
        )
        entries.append(entry_data)

    result = CollectionDetail.model_validate(collection)
    result.entry_count = entry_count
    result.entries = entries
    return result


@router.get("/featured", response_model=FeaturedResponse)
def get_featured(db: Session = Depends(get_db)):
    """Get featured portal items and collections for the magazine home."""
    items = (
        db.query(PortalItem)
        .filter(PortalItem.is_featured == True)
        .order_by(PortalItem.sort_order)
        .all()
    )
    collections = (
        db.query(Collection)
        .filter(Collection.is_featured == True)
        .order_by(Collection.sort_order)
        .all()
    )

    collection_summaries = []
    for c in collections:
        entry_count = db.query(CollectionEntry).filter(
            CollectionEntry.collection_id == c.id
        ).count()
        summary = CollectionSummary.model_validate(c)
        summary.entry_count = entry_count
        collection_summaries.append(summary)

    return FeaturedResponse(items=items, collections=collection_summaries)
