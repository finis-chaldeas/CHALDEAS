"""
Event service - CRUD operations for events.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text
from typing import Optional

from app.models.event import Event
from app.models.location import Location


def get_events(
    db: Session,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    category_id: Optional[int] = None,
    importance_min: Optional[int] = None,
    include_orphans: bool = False,
    has_location: bool = True,  # 기본값: 위치 있는 것만
    lat_min: Optional[float] = None,
    lat_max: Optional[float] = None,
    lng_min: Optional[float] = None,
    lng_max: Optional[float] = None,
    sort_by: Optional[str] = None,  # 'importance' or 'date' (default)
    limit: int = 100,
    offset: int = 0,
    **kwargs,
) -> tuple[list[Event], int]:
    """Get events with optional filtering."""
    query = db.query(Event)

    # V2 모드: wikidata_id 있는 이벤트만 표시
    query = query.filter(Event.wikidata_id.isnot(None))

    # 위치 있는 이벤트만 (지구본 표시용)
    if has_location:
        query = query.filter(Event.primary_location_id.isnot(None))

    # Apply filters
    if year_start is not None:
        query = query.filter(Event.date_start >= year_start)
    if year_end is not None:
        query = query.filter(
            or_(
                Event.date_end <= year_end,
                and_(Event.date_end.is_(None), Event.date_start <= year_end)
            )
        )
    if category_id is not None:
        query = query.filter(Event.category_id == category_id)
    if importance_min is not None:
        query = query.filter(Event.importance >= importance_min)

    # Viewport bounds filter (lat/lng range)
    needs_location_join = (
        lat_min is not None or lat_max is not None
        or lng_min is not None or lng_max is not None
    )

    if needs_location_join:
        query = query.join(Location, Event.primary_location_id == Location.id)

        if lat_min is not None:
            query = query.filter(Location.latitude >= lat_min)
        if lat_max is not None:
            query = query.filter(Location.latitude <= lat_max)
        if lng_min is not None:
            query = query.filter(Location.longitude >= lng_min)
        if lng_max is not None:
            query = query.filter(Location.longitude <= lng_max)

    # Get total count
    total = query.count()

    # Apply sorting
    if sort_by == 'importance':
        events = query.order_by(Event.importance.desc(), Event.date_start).offset(offset).limit(limit).all()
    else:
        events = query.order_by(Event.date_start).offset(offset).limit(limit).all()

    return events, total


def get_event_by_id(db: Session, event_id: int) -> Optional[Event]:
    """Get single event by ID."""
    return db.query(Event).filter(Event.id == event_id).first()


def get_event_by_slug(db: Session, slug: str) -> Optional[Event]:
    """Get single event by slug (via event_details)."""
    from app.models.event_detail import EventDetail
    result = db.query(Event).join(EventDetail).filter(EventDetail.slug == slug).first()
    return result


def get_aggregate_events(
    db: Session,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    aggregate_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Event], int]:
    """Get aggregate (parent) events only."""
    query = db.query(Event).filter(Event.is_aggregate == True)

    if year_start is not None:
        query = query.filter(Event.date_start >= year_start)
    if year_end is not None:
        query = query.filter(
            or_(
                Event.date_end <= year_end,
                and_(Event.date_end.is_(None), Event.date_start <= year_end)
            )
        )
    if aggregate_type is not None:
        query = query.filter(Event.aggregate_type == aggregate_type)

    total = query.count()
    events = query.order_by(Event.date_start).offset(offset).limit(limit).all()

    return events, total


def get_event_children(
    db: Session,
    parent_id: int,
    include_nested: bool = False,
    limit: int = 100,
) -> list[Event]:
    """Get child events of a parent event."""
    if include_nested:
        # Recursive CTE to get all descendants
        result = db.execute(text("""
            WITH RECURSIVE children AS (
                SELECT id, title, date_start, parent_event_id, hierarchy_level, 1 as depth
                FROM events WHERE parent_event_id = :parent_id
                UNION ALL
                SELECT e.id, e.title, e.date_start, e.parent_event_id, e.hierarchy_level, c.depth + 1
                FROM events e
                JOIN children c ON e.parent_event_id = c.id
                WHERE c.depth < 5
            )
            SELECT id FROM children ORDER BY date_start LIMIT :limit
        """), {"parent_id": parent_id, "limit": limit})
        child_ids = [row[0] for row in result]
        if not child_ids:
            return []
        return db.query(Event).filter(Event.id.in_(child_ids)).order_by(Event.date_start).all()
    else:
        return db.query(Event).filter(
            Event.parent_event_id == parent_id
        ).order_by(Event.date_start).limit(limit).all()


def get_event_locations(
    db: Session,
    event_id: int,
) -> dict:
    """
    Get locations for an event.

    For individual events: returns own primary_location.
    For aggregate events: recursively collects all child event locations.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return None

    result = {
        "event_id": event.id,
        "title": event.title,
        "is_aggregate": event.is_aggregate,
        "own_location": None,
        "inherited_locations": [],
        "total_locations": 0,
    }

    # Own location
    if event.primary_location:
        loc = event.primary_location
        result["own_location"] = {
            "id": loc.id,
            "name": loc.name,
            "lat": float(loc.latitude) if loc.latitude else None,
            "lng": float(loc.longitude) if loc.longitude else None,
        }

    if event.is_aggregate:
        # Recursive CTE to collect all child event locations
        rows = db.execute(text("""
            WITH RECURSIVE child_events AS (
                SELECT id, primary_location_id FROM events WHERE id = :event_id
                UNION ALL
                SELECT e.id, e.primary_location_id
                FROM events e
                JOIN child_events ce ON e.parent_event_id = ce.id
            )
            SELECT DISTINCT l.id, l.name, l.latitude, l.longitude,
                   ce.id as from_event_id,
                   (SELECT title FROM events WHERE id = ce.id) as from_event_title
            FROM child_events ce
            JOIN locations l ON ce.primary_location_id = l.id
            WHERE ce.primary_location_id IS NOT NULL
              AND ce.id != :event_id
        """), {"event_id": event_id}).fetchall()

        result["inherited_locations"] = [
            {
                "id": row[0],
                "name": row[1],
                "lat": float(row[2]) if row[2] else None,
                "lng": float(row[3]) if row[3] else None,
                "from_event_id": row[4],
                "from_event": row[5],
            }
            for row in rows
        ]

    all_locs = result["inherited_locations"][:]
    if result["own_location"]:
        all_locs.append(result["own_location"])
    result["total_locations"] = len(all_locs)

    return result


def get_hierarchy_tree(
    db: Session,
    root_id: Optional[int] = None,
    max_depth: int = 3,
) -> list[dict]:
    """Get hierarchical event tree."""
    if root_id:
        root = db.query(Event).filter(Event.id == root_id).first()
        if not root:
            return []
        return [_build_tree_node(db, root, max_depth, 0)]
    else:
        roots = db.query(Event).filter(
            Event.is_aggregate == True,
            Event.parent_event_id.is_(None)
        ).order_by(Event.date_start).all()

        return [_build_tree_node(db, r, max_depth, 0) for r in roots]


def _build_tree_node(db: Session, event: Event, max_depth: int, current_depth: int) -> dict:
    """Build a single tree node with children."""
    node = {
        "id": event.id,
        "title": event.title,
        "title_ko": event.title_ko,
        "date_start": event.date_start,
        "date_end": event.date_end,
        "hierarchy_level": event.hierarchy_level,
        "is_aggregate": event.is_aggregate,
        "aggregate_type": event.aggregate_type,
        "importance": event.importance,
        "children": [],
        "child_count": 0,
    }

    if current_depth < max_depth:
        children = db.query(Event).filter(
            Event.parent_event_id == event.id
        ).order_by(Event.date_start).limit(50).all()

        node["child_count"] = len(children)
        node["children"] = [
            _build_tree_node(db, c, max_depth, current_depth + 1)
            for c in children
        ]
    else:
        node["child_count"] = db.query(Event).filter(
            Event.parent_event_id == event.id
        ).count()

    return node
