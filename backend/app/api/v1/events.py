"""
Events API endpoints.

Provides access to historical events data from PostgreSQL database.
Events are the core data type in CHALDEAS, representing
occurrences in time and space.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text as sa_text
from typing import Optional

from app.db.session import get_db
from app.services import event_service, category_service

router = APIRouter()


@router.get("/ping")
def ping():
    """Simple test endpoint without database."""
    return {"status": "ok", "message": "pong"}


def _batch_fetch_persons(db: Session, event_ids: list[int]) -> dict[int, dict]:
    """
    Batch-fetch person summaries for a list of event IDs.
    Returns {event_id: {"persons": [...first 3...], "person_count": N}}
    Uses a single efficient query with ROW_NUMBER window function.
    """
    if not event_ids:
        return {}

    rows = db.execute(sa_text("""
        WITH ranked AS (
            SELECT
                ep.event_id,
                p.id AS person_id,
                p.name AS person_name,
                ep.role,
                ROW_NUMBER() OVER (PARTITION BY ep.event_id ORDER BY p.id) AS rn
            FROM event_persons ep
            JOIN persons p ON p.id = ep.person_id
            WHERE ep.event_id = ANY(:ids)
        ),
        counts AS (
            SELECT event_id, COUNT(*) AS cnt
            FROM event_persons
            WHERE event_id = ANY(:ids)
            GROUP BY event_id
        )
        SELECT r.event_id, r.person_id, r.person_name, r.role, c.cnt
        FROM ranked r
        JOIN counts c ON c.event_id = r.event_id
        WHERE r.rn <= 3
        ORDER BY r.event_id, r.rn
    """), {"ids": event_ids}).fetchall()

    result: dict[int, dict] = {}
    for eid, pid, pname, role, cnt in rows:
        if eid not in result:
            result[eid] = {"persons": [], "person_count": cnt}
        result[eid]["persons"].append({
            "id": pid,
            "name": pname,
            "role": role or "participant",
        })
    return result


def _batch_fetch_source_counts(db: Session, event_ids: list[int]) -> dict[int, int]:
    """Batch-fetch source counts for a list of event IDs."""
    if not event_ids:
        return {}
    rows = db.execute(sa_text("""
        SELECT event_id, COUNT(*) FROM event_sources
        WHERE event_id = ANY(:ids)
        GROUP BY event_id
    """), {"ids": event_ids}).fetchall()
    return {eid: cnt for eid, cnt in rows}


def event_to_dict(event, persons_data: dict | None = None, source_count: int | None = None) -> dict:
    """Convert Event model to dictionary for JSON response.

    Args:
        event: Event ORM object
        persons_data: Pre-fetched {"persons": [...], "person_count": N} from batch query
        source_count: Pre-fetched source count from batch query
    """
    location = event.primary_location
    details = event.details

    result = {
        "id": event.id,
        "title": event.title,
        "title_ko": event.title_ko,
        "date_start": event.date_start,
        "date_end": event.date_end,
        "importance": event.importance or 3,
        "category": {
            "id": event.category.id,
            "slug": event.category.slug,
            "name": event.category.name,
        } if event.category else None,
        "location": {
            "id": location.id,
            "name": location.name,
            "latitude": float(location.latitude) if location.latitude else None,
            "longitude": float(location.longitude) if location.longitude else None,
        } if location else None,
        "latitude": float(location.latitude) if location and location.latitude else None,
        "longitude": float(location.longitude) if location and location.longitude else None,
        # Hierarchy fields
        "parent_event_id": event.parent_event_id,
        "is_aggregate": event.is_aggregate,
        "hierarchy_level": event.hierarchy_level,
        "aggregate_type": event.aggregate_type,
        "parent_status": event.parent_status,
    }

    # Include details when available (for detail views)
    if details:
        result["details"] = {
            "slug": details.slug,
            "description": details.description,
            "description_ko": details.description_ko,
            "description_source": details.description_source,
            "description_source_url": details.description_source_url,
            "wikipedia_url": details.wikipedia_url,
            "image_url": details.image_url,
            "date_start_month": details.date_start_month,
            "date_start_day": details.date_start_day,
            "date_end_month": details.date_end_month,
            "date_end_day": details.date_end_day,
        }
        # Also expose top-level for backward compat in list views
        result["description"] = details.description
        result["wikipedia_url"] = details.wikipedia_url
        result["image_url"] = details.image_url

    # Include pre-fetched persons summary (from batch query)
    if persons_data is not None:
        result["persons"] = persons_data["persons"]
        result["person_count"] = persons_data["person_count"]

    # Include pre-fetched source count
    if source_count is not None:
        result["source_count"] = source_count

    return result


@router.get("")
def list_events(
    db: Session = Depends(get_db),
    year_start: Optional[int] = Query(None, description="Start year (negative for BCE)"),
    year_end: Optional[int] = Query(None, description="End year (negative for BCE)"),
    category: Optional[str] = Query(None, description="Filter by category slug"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    importance_min: Optional[int] = Query(None, description="Minimum importance (1-5)"),
    include_orphans: bool = Query(False, description="Include entities with no connections"),
    has_location: bool = Query(True, description="Only events with coordinates"),
    region: Optional[str] = Query(None, description="Filter by region/country (e.g., 'Italy', 'Europe')"),
    lat_min: Optional[float] = Query(None, description="Viewport south bound"),
    lat_max: Optional[float] = Query(None, description="Viewport north bound"),
    lng_min: Optional[float] = Query(None, description="Viewport west bound"),
    lng_max: Optional[float] = Query(None, description="Viewport east bound"),
    sort_by: Optional[str] = Query(None, description="Sort by: 'importance' or 'date' (default: date)"),
    limit: int = Query(100, ge=1, le=3000),
    offset: int = Query(0, ge=0),
):
    """
    List events with optional filtering.

    Used by the globe view to display event markers.
    Supports temporal, categorical, and viewport filtering.
    """
    # If category slug provided, convert to category_id
    if category and not category_id:
        cat = category_service.get_category_by_slug(db, category)
        if cat:
            category_id = cat.id

    events, total = event_service.get_events(
        db,
        year_start=year_start,
        year_end=year_end,
        category_id=category_id,
        importance_min=importance_min,
        include_orphans=include_orphans,
        has_location=has_location,
        lat_min=lat_min,
        lat_max=lat_max,
        lng_min=lng_min,
        lng_max=lng_max,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )

    # Batch-fetch persons and source counts for all events (2 queries total)
    event_ids = [e.id for e in events]
    persons_map = _batch_fetch_persons(db, event_ids)
    sources_map = _batch_fetch_source_counts(db, event_ids)

    return {
        "items": [
            event_to_dict(
                e,
                persons_data=persons_map.get(e.id),
                source_count=sources_map.get(e.id),
            )
            for e in events
        ],
        "total": total,
        "filtered": len(events),
    }


@router.get("/map")
def get_events_for_map(
    db: Session = Depends(get_db),
    year: Optional[int] = Query(None, description="Center year for filtering"),
    year_range: int = Query(50, description="Range around center year"),
    limit: int = Query(500, ge=1, le=2000),
):
    """
    Get events formatted for map display.

    Returns simplified event data with just coordinates and essential info.
    """
    year_start = year - year_range if year else None
    year_end = year + year_range if year else None

    events, _ = event_service.get_events(
        db,
        year_start=year_start,
        year_end=year_end,
        limit=limit,
    )

    markers = []
    for e in events:
        loc = e.primary_location
        if loc and loc.latitude and loc.longitude:
            markers.append({
                "id": e.id,
                "title": e.title,
                "date": e.date_start,
                "lat": float(loc.latitude),
                "lng": float(loc.longitude),
                "category": e.category.slug if e.category else "general",
                "importance": e.importance or 3,
            })

    return {"markers": markers, "count": len(markers)}


@router.get("/stats")
def get_event_stats(db: Session = Depends(get_db)):
    """Get statistics about events data."""
    from sqlalchemy import func
    from app.models.event import Event

    total = db.query(func.count(Event.id)).scalar()
    with_location = db.query(func.count(Event.id)).filter(Event.primary_location_id.isnot(None)).scalar()

    return {
        "events": total,
        "events_with_coords": with_location,
    }


@router.get("/hierarchy")
def get_event_hierarchy(
    db: Session = Depends(get_db),
    root_id: Optional[int] = Query(None, description="Root event ID (None for top-level)"),
    max_depth: int = Query(3, ge=1, le=5, description="Maximum tree depth"),
):
    """
    Get hierarchical event tree.

    Returns events with their children nested.
    If root_id is None, returns all top-level aggregate events.
    """
    tree = event_service.get_hierarchy_tree(db, root_id=root_id, max_depth=max_depth)
    return {"tree": tree, "count": len(tree)}


@router.get("/aggregates")
def list_aggregate_events(
    db: Session = Depends(get_db),
    year_start: Optional[int] = Query(None, description="Start year"),
    year_end: Optional[int] = Query(None, description="End year"),
    aggregate_type: Optional[str] = Query(None, description="war, movement, dynasty, etc."),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    List aggregate (parent) events only.

    Aggregate events are container events like wars, movements, dynasties.
    Use this for high-level timeline views.
    """
    events, total = event_service.get_aggregate_events(
        db,
        year_start=year_start,
        year_end=year_end,
        aggregate_type=aggregate_type,
        limit=limit,
        offset=offset,
    )

    event_ids = [e.id for e in events]
    persons_map = _batch_fetch_persons(db, event_ids)
    sources_map = _batch_fetch_source_counts(db, event_ids)

    return {
        "items": [
            event_to_dict(
                e,
                persons_data=persons_map.get(e.id),
                source_count=sources_map.get(e.id),
            )
            for e in events
        ],
        "total": total,
        "filtered": len(events),
    }


@router.get("/{event_id}")
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a specific event.

    Includes related persons, locations, and sources.
    This data is displayed in the wiki panel (LAPLACE output).
    """
    event = event_service.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    result = event_to_dict(event)

    # Add related data
    result["persons"] = [
        {
            "id": p.id,
            "name": p.name,
            "slug": p.slug if hasattr(p, 'slug') and p.slug else f"person-{p.id}",
            "role": "participant",
            "birth_year": p.birth_year,
            "death_year": p.death_year,
        }
        for p in event.persons
    ]
    result["locations"] = [
        {
            "id": l.id,
            "name": l.name,
            "latitude": float(l.latitude) if l.latitude else None,
            "longitude": float(l.longitude) if l.longitude else None,
            "role": "location",
        }
        for l in event.locations
    ]

    # Add hierarchy info
    if event.parent_event_id:
        parent = event_service.get_event_by_id(db, event.parent_event_id)
        if parent:
            result["parent"] = {
                "id": parent.id,
                "title": parent.title,
                "title_ko": parent.title_ko,
            }

    # Add children summary
    children = event_service.get_event_children(db, event.id, include_nested=False, limit=10)
    result["children"] = [
        {"id": c.id, "title": c.title, "date_start": c.date_start}
        for c in children
    ]
    result["child_count"] = len(children)

    # Add sources
    from sqlalchemy import text
    sources_query = db.execute(text('''
        SELECT s.id, s.source_type, s.title, s.url, s.content_raw, es.page_reference
        FROM event_sources es
        JOIN sources s ON s.id = es.source_id
        WHERE es.event_id = :event_id
    '''), {"event_id": event_id}).fetchall()

    result["sources"] = [
        {
            "id": row[0],
            "type": row[1],
            "title": row[2],
            "url": row[3],
            "content": row[4][:500] if row[4] else None,
            "page_reference": row[5],
        }
        for row in sources_query
    ]

    return result


@router.get("/{event_id}/children")
def get_event_children(
    event_id: int,
    db: Session = Depends(get_db),
    include_nested: bool = Query(False, description="Include all descendants"),
    limit: int = Query(100, ge=1, le=500),
):
    """
    Get child events of a specific event.

    Set include_nested=true to get all descendants recursively.
    """
    event = event_service.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    children = event_service.get_event_children(
        db, event_id, include_nested=include_nested, limit=limit
    )

    return {
        "parent": {"id": event.id, "title": event.title},
        "items": [event_to_dict(c) for c in children],
        "count": len(children),
    }


@router.get("/{event_id}/locations")
def get_event_locations(
    event_id: int,
    db: Session = Depends(get_db),
):
    """
    Get locations for an event.

    For individual events: returns own primary_location.
    For aggregate events: recursively collects all child event locations.
    """
    result = event_service.get_event_locations(db, event_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return result
