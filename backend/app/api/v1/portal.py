"""
Trismegistus Portal API — curated content, collections, featured items.

Includes entity link resolution and suggestion APIs for the
[Name](entity:type:id) inline tagging system.
"""
import json
import random
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, text

from app.db.session import get_db
from app.models.v2.portal import PortalItem, Collection, CollectionEntry
from app.models.v1.chain import HistoricalChain
from app.models.person import Person
from app.models.event import Event
from app.models.location import Location

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


class ShiftSummary(BaseModel):
    id: int
    title: str
    title_ko: Optional[str] = None
    chain_type: Optional[str] = None
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    segment_count: Optional[int] = None

    class Config:
        from_attributes = True


class PersonSummary(BaseModel):
    id: int
    name: str
    name_ko: Optional[str] = None
    birth_year: Optional[int] = None
    death_year: Optional[int] = None

    class Config:
        from_attributes = True


class EventSummary(BaseModel):
    id: int
    title: str
    title_ko: Optional[str] = None
    date_start: Optional[int] = None

    class Config:
        from_attributes = True


class CollectionEntrySummary(BaseModel):
    id: int
    entry_type: str
    sort_order: int = 0
    is_highlighted: bool = False
    note: Optional[str] = None
    note_ko: Optional[str] = None
    # Resolved references
    portal_item: Optional[PortalItemSummary] = None
    shift_summary: Optional[ShiftSummary] = None
    person_summary: Optional[PersonSummary] = None
    event_summary: Optional[EventSummary] = None
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


class RecommendationItem(BaseModel):
    type: str  # 'shift' | 'portal_item' | 'collection'
    id: Optional[int] = None
    slug: Optional[str] = None
    title: str
    title_ko: Optional[str] = None
    subtitle: Optional[str] = None
    item_type: Optional[str] = None
    chain_type: Optional[str] = None
    icon: Optional[str] = None
    segment_count: Optional[int] = None


class FeaturedResponse(BaseModel):
    items: List[PortalItemSummary]
    collections: List[CollectionSummary]
    recommendations: List[RecommendationItem] = []


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
        types = [t.strip() for t in item_type.split(',')]
        if len(types) > 1:
            q = q.filter(PortalItem.item_type.in_(types))
        else:
            q = q.filter(PortalItem.item_type == types[0])
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

    # Enrich related_servants with portal item slugs for linking
    if item.related_servants:
        servant_names = [s.get("name", "") for s in item.related_servants]
        servant_items = (
            db.query(PortalItem.slug, PortalItem.title)
            .filter(
                PortalItem.item_type == "servant_column",
                or_(*[PortalItem.title.ilike(f"%{name}%") for name in servant_names if name])
            )
            .all()
        )
        # Build name→slug lookup (match by checking if servant name appears in title)
        name_to_slug = {}
        for s_slug, s_title in servant_items:
            s_title_lower = s_title.lower()
            for name in servant_names:
                if name and name.lower() in s_title_lower:
                    name_to_slug[name.lower()] = s_slug

        enriched = []
        for s in item.related_servants:
            entry = dict(s)
            entry["slug"] = name_to_slug.get(s.get("name", "").lower())
            enriched.append(entry)

        # Return enriched copy without mutating the ORM object
        result = PortalItemDetail.model_validate(item)
        result.related_servants = enriched
        return result

    return item


@router.get("/items/by-event/{event_id}", response_model=List[PortalItemSummary])
def get_items_by_event(
    event_id: int = Path(..., description="Event ID to look up"),
    db: Session = Depends(get_db),
):
    """Find portal items whose related_event_ids contains this event."""
    items = (
        db.query(PortalItem)
        .filter(
            text("related_event_ids @> cast(:val as jsonb)")
        )
        .params(val=json.dumps([event_id]))
        .order_by(PortalItem.sort_order, PortalItem.id)
        .all()
    )
    return items


@router.get("/items/by-shift/{shift_id}", response_model=List[PortalItemSummary])
def get_items_by_shift(
    shift_id: int = Path(..., description="Shift (chain) ID to look up"),
    db: Session = Depends(get_db),
):
    """Find portal items that share a collection with this shift."""
    # Collections containing this shift
    shift_coll_ids = (
        db.query(CollectionEntry.collection_id)
        .filter(CollectionEntry.shift_id == shift_id)
    )
    # Portal items from those collections
    item_ids = (
        db.query(CollectionEntry.portal_item_id)
        .filter(
            CollectionEntry.collection_id.in_(shift_coll_ids),
            CollectionEntry.portal_item_id.isnot(None),
        )
    )
    items = (
        db.query(PortalItem)
        .filter(PortalItem.id.in_(item_ids))
        .order_by(PortalItem.sort_order, PortalItem.id)
        .all()
    )
    return items


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
            joinedload(Collection.entries).joinedload(CollectionEntry.portal_item),
            joinedload(Collection.entries).joinedload(CollectionEntry.shift),
            joinedload(Collection.entries).joinedload(CollectionEntry.person),
            joinedload(Collection.entries).joinedload(CollectionEntry.event),
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
            shift_summary=ShiftSummary.model_validate(e.shift) if e.shift else None,
            person_summary=PersonSummary.model_validate(e.person) if e.person else None,
            event_summary=EventSummary.model_validate(e.event) if e.event else None,
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

    # Build recommendations: featured items + top shifts + a collection
    recs: List[RecommendationItem] = []

    # Featured items (up to 2)
    for item in items[:2]:
        recs.append(RecommendationItem(
            type='portal_item',
            slug=item.slug,
            title=item.title,
            title_ko=item.title_ko,
            subtitle=item.subtitle,
            item_type=item.item_type,
        ))

    # High globe_importance shifts (up to 2)
    top_shifts = (
        db.query(HistoricalChain)
        .filter(HistoricalChain.globe_importance >= 4)
        .order_by(HistoricalChain.globe_importance.desc())
        .limit(10)
        .all()
    )
    sampled_shifts = random.sample(top_shifts, min(2, len(top_shifts))) if top_shifts else []
    for s in sampled_shifts:
        recs.append(RecommendationItem(
            type='shift',
            id=s.id,
            title=s.title,
            title_ko=getattr(s, 'title_ko', None),
            chain_type=s.chain_type,
            segment_count=s.segment_count,
        ))

    # One collection
    if collection_summaries:
        c = collection_summaries[0]
        recs.append(RecommendationItem(
            type='collection',
            slug=c.slug,
            title=c.title,
            title_ko=c.title_ko,
            icon=c.icon,
        ))

    random.shuffle(recs)

    return FeaturedResponse(items=items, collections=collection_summaries, recommendations=recs)


# === Entity Link Resolution ===

class ResolveResult(BaseModel):
    type: str          # person, event, location, shift, item, collection
    id: object         # int or str (slug for item/collection)
    name: str
    name_ko: Optional[str] = None
    meta: Optional[str] = None  # e.g. "1412-1431", "시프트 · 7 pages"


@router.get("/resolve", response_model=dict)
def resolve_entity_links(
    q: str = Query(..., min_length=1, description="Search query for entity resolution"),
    type_filter: Optional[str] = Query(None, description="Filter: person, event, location, shift, item, collection"),
    limit: int = Query(10, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """
    Unified entity search for [Name](entity:type:id) autocomplete.

    Used by editors when user types '[' to insert an entity tag.
    Searches across persons, events, locations, shifts, portal items, and collections.
    """
    results: list[dict] = []
    per_type = max(2, limit // 5)

    if not type_filter or type_filter == "person":
        persons = (
            db.query(Person)
            .filter(or_(
                Person.name.ilike(f"%{q}%"),
                Person.name_ko.ilike(f"%{q}%"),
            ))
            .order_by(Person.importance_score.desc().nullslast())
            .limit(per_type)
            .all()
        )
        for p in persons:
            years = ""
            if p.birth_year:
                years = f"{p.birth_year}"
                if p.death_year:
                    years += f" ~ {p.death_year}"
            results.append({
                "type": "person",
                "id": p.id,
                "name": p.name,
                "name_ko": getattr(p, "name_ko", None),
                "meta": years or None,
            })

    if not type_filter or type_filter == "event":
        events = (
            db.query(Event)
            .filter(or_(
                Event.title.ilike(f"%{q}%"),
                Event.title_ko.ilike(f"%{q}%"),
            ))
            .order_by(Event.importance.desc().nullslast())
            .limit(per_type)
            .all()
        )
        for e in events:
            results.append({
                "type": "event",
                "id": e.id,
                "name": e.title,
                "name_ko": getattr(e, "title_ko", None),
                "meta": str(e.date_start) if e.date_start else None,
            })

    if not type_filter or type_filter == "location":
        locations = (
            db.query(Location)
            .filter(or_(
                Location.name.ilike(f"%{q}%"),
                Location.name_ko.ilike(f"%{q}%"),
            ))
            .limit(per_type)
            .all()
        )
        for loc in locations:
            results.append({
                "type": "location",
                "id": loc.id,
                "name": loc.name,
                "name_ko": getattr(loc, "name_ko", None),
            })

    if not type_filter or type_filter == "shift":
        shifts = (
            db.query(HistoricalChain)
            .filter(or_(
                HistoricalChain.title.ilike(f"%{q}%"),
                HistoricalChain.title_ko.ilike(f"%{q}%"),
            ))
            .order_by(HistoricalChain.globe_importance.desc().nullslast())
            .limit(per_type)
            .all()
        )
        for s in shifts:
            page_count = s.segment_count or 0
            results.append({
                "type": "shift",
                "id": s.id,
                "name": s.title,
                "name_ko": getattr(s, "title_ko", None),
                "meta": f"시프트 · {page_count} pages",
            })

    if not type_filter or type_filter == "item":
        items = (
            db.query(PortalItem)
            .filter(or_(
                PortalItem.title.ilike(f"%{q}%"),
                PortalItem.title_ko.ilike(f"%{q}%"),
                PortalItem.slug.ilike(f"%{q}%"),
            ))
            .limit(per_type)
            .all()
        )
        for item in items:
            results.append({
                "type": "item",
                "id": item.slug,
                "name": item.title,
                "name_ko": getattr(item, "title_ko", None),
                "meta": item.item_type,
            })

    if not type_filter or type_filter == "collection":
        colls = (
            db.query(Collection)
            .filter(or_(
                Collection.title.ilike(f"%{q}%"),
                Collection.title_ko.ilike(f"%{q}%"),
                Collection.slug.ilike(f"%{q}%"),
            ))
            .limit(per_type)
            .all()
        )
        for c in colls:
            results.append({
                "type": "collection",
                "id": c.slug,
                "name": c.title,
                "name_ko": getattr(c, "title_ko", None),
                "meta": "컬렉션",
            })

    return {"query": q, "results": results[:limit]}


# === Entity Link Suggestion ===

# Match existing [Name](entity:type:id) tags to skip already-linked text
_EXISTING_TAG_RE = re.compile(r'\[([^\]]+)\]\(entity:[^)]+\)')


@router.post("/suggest-links")
def suggest_entity_links(
    body: dict,
    db: Session = Depends(get_db),
):
    """
    Analyze text and suggest entity links that could be added.

    Request body: { "text": "잔 다르크가 오를레앙에서 전투를 이끌었다.", "limit": 10 }

    Returns potential [Name](entity:type:id) matches found in the text.
    Already-tagged entities are excluded from suggestions.
    """
    text = body.get("text", "")
    limit = body.get("limit", 10)
    if not text or len(text) < 3:
        return {"suggestions": []}

    # 1. Find already-tagged names to exclude
    already_tagged = set()
    for m in _EXISTING_TAG_RE.finditer(text):
        already_tagged.add(m.group(1).lower())

    # 2. Strip existing tags to get plain text for matching
    plain_text = _EXISTING_TAG_RE.sub(lambda m: m.group(1), text)

    suggestions: list[dict] = []
    seen_ids: set[tuple] = set()

    # 3. Search persons whose names appear in the text
    #    Use importance_score to prioritize well-known figures
    persons = (
        db.query(Person)
        .filter(Person.importance_score >= 5)
        .order_by(Person.importance_score.desc())
        .limit(500)
        .all()
    )
    for p in persons:
        if ("person", p.id) in seen_ids:
            continue
        # Check if person's name appears in plain text
        name_hit = None
        if p.name and p.name.lower() not in already_tagged and p.name.lower() in plain_text.lower():
            name_hit = p.name
        elif p.name_ko and p.name_ko not in already_tagged and p.name_ko in plain_text:
            name_hit = p.name_ko

        if name_hit:
            seen_ids.add(("person", p.id))
            suggestions.append({
                "type": "person",
                "id": p.id,
                "name": p.name,
                "name_ko": p.name_ko,
                "matched_text": name_hit,
                "tag": f"[{name_hit}](entity:person:{p.id})",
                "importance": p.importance_score or 0,
            })

    # 4. Search events whose titles appear in the text
    events = (
        db.query(Event)
        .filter(Event.importance >= 5)
        .order_by(Event.importance.desc())
        .limit(500)
        .all()
    )
    for e in events:
        if ("event", e.id) in seen_ids:
            continue
        name_hit = None
        if e.title and len(e.title) >= 4 and e.title.lower() not in already_tagged and e.title.lower() in plain_text.lower():
            name_hit = e.title
        elif e.title_ko and len(e.title_ko) >= 3 and e.title_ko not in already_tagged and e.title_ko in plain_text:
            name_hit = e.title_ko

        if name_hit:
            seen_ids.add(("event", e.id))
            suggestions.append({
                "type": "event",
                "id": e.id,
                "name": e.title,
                "name_ko": getattr(e, "title_ko", None),
                "matched_text": name_hit,
                "tag": f"[{name_hit}](entity:event:{e.id})",
                "importance": e.importance or 0,
            })

    # 5. Search shifts whose titles appear in the text
    shifts = (
        db.query(HistoricalChain)
        .filter(HistoricalChain.globe_importance >= 3)
        .order_by(HistoricalChain.globe_importance.desc())
        .limit(200)
        .all()
    )
    for s in shifts:
        if ("shift", s.id) in seen_ids:
            continue
        name_hit = None
        if s.title and len(s.title) >= 4 and s.title.lower() not in already_tagged and s.title.lower() in plain_text.lower():
            name_hit = s.title
        elif s.title_ko and len(s.title_ko) >= 3 and s.title_ko not in already_tagged and s.title_ko in plain_text:
            name_hit = s.title_ko

        if name_hit:
            seen_ids.add(("shift", s.id))
            suggestions.append({
                "type": "shift",
                "id": s.id,
                "name": s.title,
                "name_ko": getattr(s, "title_ko", None),
                "matched_text": name_hit,
                "tag": f"[{name_hit}](entity:shift:{s.id})",
                "importance": s.globe_importance or 0,
            })

    # 6. Sort by importance and limit
    suggestions.sort(key=lambda x: x.get("importance", 0), reverse=True)
    return {"suggestions": suggestions[:limit]}
