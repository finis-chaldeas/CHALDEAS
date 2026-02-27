"""
Globe API - Markers and connections for 3D globe visualization.

This endpoint provides:
- Location markers filtered by time and space
- Event markers with coordinates
- Person markers (birth/death locations)
- Connections between related entities
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Literal
from pydantic import BaseModel
from datetime import datetime

from app.db.session import get_db

router = APIRouter(prefix="/globe", tags=["globe"])


# ============== Response Models ==============

class GlobeMarker(BaseModel):
    id: int
    type: Literal["event", "person", "location"]
    lat: float
    lng: float
    year: Optional[int] = None
    year_end: Optional[int] = None
    category: Optional[str] = None
    title: str
    title_ko: Optional[str] = None
    title_ja: Optional[str] = None
    description: Optional[str] = None
    certainty: Optional[str] = None
    color: Optional[str] = None
    importance: Optional[int] = None


class GlobeConnection(BaseModel):
    source_id: int
    source_type: str
    target_id: int
    target_type: str
    source_lat: float
    source_lng: float
    target_lat: float
    target_lng: float
    connection_type: str
    year: Optional[int] = None


class MarkerStats(BaseModel):
    total_markers: int
    by_type: dict
    year_range: dict


# ============== Helper Functions ==============

def get_marker_color(entity_type: str, category: str = None, certainty: str = None) -> str:
    """Get marker color based on type and category."""
    if entity_type == "event":
        category_colors = {
            "battle": "#ef4444",      # red
            "war": "#dc2626",         # darker red
            "treaty": "#3b82f6",      # blue
            "discovery": "#22c55e",   # green
            "cultural": "#a855f7",    # purple
            "political": "#f59e0b",   # amber
            "religious": "#8b5cf6",   # violet
        }
        return category_colors.get(category, "#6b7280")  # gray default

    elif entity_type == "person":
        certainty_colors = {
            "fact": "#3b82f6",         # blue
            "probable": "#22c55e",     # green
            "legendary": "#f59e0b",    # amber
            "mythological": "#a855f7", # purple
        }
        return certainty_colors.get(certainty, "#6b7280")

    elif entity_type == "location":
        return "#14b8a6"  # teal

    return "#6b7280"  # gray


# ============== Endpoints ==============

@router.get("/markers", response_model=List[GlobeMarker])
async def get_globe_markers(
    types: str = Query("event,location", description="Comma-separated: event,person,location"),
    year_start: Optional[int] = Query(None, description="Filter from year (BCE as negative)"),
    year_end: Optional[int] = Query(None, description="Filter to year"),
    bounds: Optional[str] = Query(None, description="lat1,lng1,lat2,lng2 bounding box"),
    category: Optional[str] = Query(None, description="Filter by category"),
    certainty: Optional[str] = Query(None, description="Filter by certainty level"),
    limit: int = Query(1000, ge=1, le=5000, description="Max markers to return"),
    db: Session = Depends(get_db),
):
    """
    Get markers for the globe visualization.

    Supports filtering by:
    - Entity types (event, person, location)
    - Time range (year_start to year_end)
    - Spatial bounds (bounding box)
    - Category and certainty level
    """
    type_list = [t.strip() for t in types.split(",")]
    markers = []

    # Parse bounds if provided
    bounds_filter = ""
    bounds_params = {}
    if bounds:
        try:
            lat1, lng1, lat2, lng2 = map(float, bounds.split(","))
            bounds_filter = """
                AND latitude BETWEEN :lat_min AND :lat_max
                AND longitude BETWEEN :lng_min AND :lng_max
            """
            bounds_params = {
                "lat_min": min(lat1, lat2),
                "lat_max": max(lat1, lat2),
                "lng_min": min(lng1, lng2),
                "lng_max": max(lng1, lng2),
            }
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid bounds format. Use: lat1,lng1,lat2,lng2")

    # Get event markers (join with locations via primary_location_id)
    if "event" in type_list:
        conditions = ["l.latitude IS NOT NULL", "l.longitude IS NOT NULL", "e.wikidata_id IS NOT NULL"]
        params = {"limit": limit}
        params.update(bounds_params)

        if year_start is not None:
            conditions.append("e.date_start >= :year_start")
            params["year_start"] = year_start
        if year_end is not None:
            conditions.append("e.date_start <= :year_end")
            params["year_end"] = year_end
        if certainty:
            conditions.append("e.certainty = :certainty")
            params["certainty"] = certainty

        # Update bounds filter for joined query
        event_bounds_filter = bounds_filter.replace("latitude", "l.latitude").replace("longitude", "l.longitude")
        where_clause = " AND ".join(conditions) + event_bounds_filter

        result = db.execute(text(f"""
            SELECT e.id, e.title, e.title_ko, e.date_start, e.date_end,
                   l.latitude, l.longitude,
                   e.certainty, e.temporal_scale, ed.description, e.importance
            FROM events e
            JOIN locations l ON e.primary_location_id = l.id
            LEFT JOIN event_details ed ON ed.event_id = e.id
            WHERE {where_clause}
            ORDER BY e.date_start NULLS LAST
            LIMIT :limit
        """), params)

        for row in result:
            markers.append(GlobeMarker(
                id=row[0],
                type="event",
                title=row[1] or "Unknown Event",
                title_ko=row[2],
                lat=float(row[5]),
                lng=float(row[6]),
                year=row[3],
                year_end=row[4],
                certainty=row[7],
                category=row[8],  # temporal_scale as category for now
                description=row[9],
                color=get_marker_color("event", row[8], row[7]),
                importance=row[10],
            ))

    # Get location markers
    if "location" in type_list:
        conditions = ["latitude IS NOT NULL", "longitude IS NOT NULL", "wikidata_id IS NOT NULL"]
        params = {"limit": limit}
        params.update(bounds_params)

        if category:
            conditions.append("location_type = :loc_type")
            params["loc_type"] = category

        where_clause = " AND ".join(conditions) + bounds_filter

        result = db.execute(text(f"""
            SELECT id, name, name_ko, latitude, longitude, location_type
            FROM locations
            WHERE {where_clause}
            LIMIT :limit
        """), params)

        for row in result:
            markers.append(GlobeMarker(
                id=row[0],
                type="location",
                title=row[1] or "Unknown Location",
                title_ko=row[2],
                lat=float(row[3]),
                lng=float(row[4]),
                category=row[5],
                color=get_marker_color("location")
            ))

    # Get person markers (birth locations)
    if "person" in type_list:
        conditions = ["p.birth_year IS NOT NULL", "p.wikidata_id IS NOT NULL"]
        params = {"limit": limit}

        if year_start is not None:
            conditions.append("p.birth_year >= :year_start")
            params["year_start"] = year_start
        if year_end is not None:
            conditions.append("p.birth_year <= :year_end")
            params["year_end"] = year_end
        if certainty:
            conditions.append("p.certainty = :certainty")
            params["certainty"] = certainty

        where_clause = " AND ".join(conditions)

        # Join with locations to get coordinates
        # For now, use a simple approach - look for location matches
        result = db.execute(text(f"""
            SELECT p.id, p.name, p.name_ko, p.birth_year, p.death_year,
                   p.role, p.certainty, l.latitude, l.longitude
            FROM persons p
            LEFT JOIN locations l ON LOWER(l.name) LIKE '%' || LOWER(SPLIT_PART(p.name, ' of ', 2)) || '%'
            WHERE {where_clause}
            AND l.latitude IS NOT NULL
            ORDER BY p.birth_year ASC NULLS LAST
            LIMIT :limit
        """), params)

        for row in result:
            if row[7] and row[8]:  # has coordinates
                markers.append(GlobeMarker(
                    id=row[0],
                    type="person",
                    title=row[1] or "Unknown Person",
                    title_ko=row[2],
                    lat=float(row[7]),
                    lng=float(row[8]),
                    year=row[3],
                    year_end=row[4],
                    category=row[5],  # role
                    certainty=row[6],
                    color=get_marker_color("person", None, row[6])
                ))

    return markers[:limit]


class AnchorLocation(BaseModel):
    id: int
    name: str
    name_ko: Optional[str] = None
    name_ja: Optional[str] = None
    lat: float
    lng: float
    event_count: int
    tier: int  # 1=always visible, 2=regional zoom, 3=local zoom


@router.get("/anchor-locations", response_model=List[AnchorLocation])
async def get_anchor_locations(
    tier: int = Query(1, ge=1, le=3, description="Max tier to include (1=top cities, 2=regional, 3=all)"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get major locations that should always be visible on the globe.
    Tier system based on event count:
    - Tier 1: event_count > 50 (always visible, ~50-100 cities)
    - Tier 2: event_count > 10 (regional zoom, ~200 cities)
    - Tier 3: event_count > 2 (local zoom, all significant)
    """
    tier_thresholds = {1: 15, 2: 5, 3: 2}
    min_events = tier_thresholds.get(tier, 15)

    result = db.execute(text("""
        SELECT l.id, l.name, l.name_ko, l.name_ja, l.latitude, l.longitude,
               COUNT(e.id) as event_count
        FROM locations l
        JOIN events e ON e.primary_location_id = l.id
        WHERE l.latitude IS NOT NULL
          AND l.longitude IS NOT NULL
          AND l.location_type = 'point'
        GROUP BY l.id, l.name, l.name_ko, l.name_ja, l.latitude, l.longitude
        HAVING COUNT(e.id) >= :min_events
        ORDER BY COUNT(e.id) DESC
        LIMIT :limit
    """), {"min_events": min_events, "limit": limit})

    locations = []
    for row in result:
        ec = row[6]
        t = 1 if ec >= 15 else (2 if ec >= 5 else 3)
        locations.append(AnchorLocation(
            id=row[0],
            name=row[1] or "Unknown",
            name_ko=row[2],
            name_ja=row[3],
            lat=float(row[4]),
            lng=float(row[5]),
            event_count=ec,
            tier=t,
        ))

    return locations


@router.get("/markers/stats", response_model=MarkerStats)
async def get_marker_stats(
    year_start: Optional[int] = Query(None),
    year_end: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Get statistics about available markers."""
    # Event count with coordinates (join with locations)
    event_params = {}
    event_conditions = ["l.latitude IS NOT NULL", "e.primary_location_id IS NOT NULL"]
    if year_start:
        event_conditions.append("e.date_start >= :year_start")
        event_params["year_start"] = year_start
    if year_end:
        event_conditions.append("e.date_start <= :year_end")
        event_params["year_end"] = year_end

    event_where = " AND ".join(event_conditions)
    event_count = db.execute(
        text(f"""
            SELECT COUNT(*)
            FROM events e
            JOIN locations l ON e.primary_location_id = l.id
            WHERE {event_where}
        """),
        event_params
    ).scalar()

    # Location count with coordinates
    location_count = db.execute(
        text("SELECT COUNT(*) FROM locations WHERE latitude IS NOT NULL")
    ).scalar()

    # Year range
    year_range_result = db.execute(text("""
        SELECT MIN(date_start), MAX(date_start)
        FROM events WHERE date_start IS NOT NULL
    """)).fetchone()

    return MarkerStats(
        total_markers=event_count + location_count,
        by_type={
            "events": event_count,
            "locations": location_count,
        },
        year_range={
            "min": year_range_result[0] if year_range_result else None,
            "max": year_range_result[1] if year_range_result else None,
        }
    )


@router.get("/markers/density")
async def get_marker_density(
    bucket_size: int = Query(100, description="Year bucket size for aggregation"),
    types: str = Query("event", description="Entity types to include"),
    db: Session = Depends(get_db),
):
    """
    Get event density over time for timeline heatmap.
    Returns counts per time bucket.
    """
    type_list = [t.strip() for t in types.split(",")]

    if "event" in type_list:
        result = db.execute(text("""
            SELECT
                FLOOR(e.date_start / :bucket_size) * :bucket_size as year_bucket,
                COUNT(*) as count
            FROM events e
            JOIN locations l ON e.primary_location_id = l.id
            WHERE e.date_start IS NOT NULL AND l.latitude IS NOT NULL
            GROUP BY year_bucket
            ORDER BY year_bucket
        """), {"bucket_size": bucket_size})

        buckets = [{"year": int(row[0]), "count": row[1]} for row in result]

        return {
            "bucket_size": bucket_size,
            "buckets": buckets,
            "total_events": sum(b["count"] for b in buckets)
        }

    return {"bucket_size": bucket_size, "buckets": [], "total_events": 0}


@router.get("/connections/{entity_type}/{entity_id}")
async def get_entity_connections(
    entity_type: str,
    entity_id: int,
    connection_types: Optional[str] = Query(None, description="Filter connection types"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Get connections from a specific entity to other entities.
    Useful for visualizing relationships on the globe.
    """
    if entity_type not in ["event", "person", "location"]:
        raise HTTPException(status_code=400, detail="Invalid entity_type")

    connections = []

    if entity_type == "event":
        # Get event's location (join with locations)
        event = db.execute(text("""
            SELECT e.id, e.title, l.latitude, l.longitude, e.date_start
            FROM events e
            JOIN locations l ON e.primary_location_id = l.id
            WHERE e.id = :id
        """), {"id": entity_id}).fetchone()

        if not event or not event[2]:
            return {"entity_id": entity_id, "entity_type": entity_type, "connections": []}

        # Find other events at the same location or same time period
        result = db.execute(text("""
            SELECT e.id, e.title, l.latitude, l.longitude, e.date_start
            FROM events e
            JOIN locations l ON e.primary_location_id = l.id
            WHERE e.id != :id
            AND l.latitude IS NOT NULL
            AND (
                -- Same location (within ~100km)
                (ABS(l.latitude - :lat) < 1 AND ABS(l.longitude - :lng) < 1)
                OR
                -- Same time period (within 50 years)
                (e.date_start IS NOT NULL AND ABS(e.date_start - :year) < 50)
            )
            LIMIT :limit
        """), {
            "id": entity_id,
            "lat": event[2],
            "lng": event[3],
            "year": event[4] or 0,
            "limit": limit
        })

        for row in result:
            connections.append(GlobeConnection(
                source_id=entity_id,
                source_type="event",
                target_id=row[0],
                target_type="event",
                source_lat=float(event[2]),
                source_lng=float(event[3]),
                target_lat=float(row[2]),
                target_lng=float(row[3]),
                connection_type="temporal" if abs((row[4] or 0) - (event[4] or 0)) < 50 else "spatial",
                year=row[4]
            ))

    elif entity_type == "location":
        # Get events at this location
        location = db.execute(text("""
            SELECT id, name, latitude, longitude
            FROM locations WHERE id = :id
        """), {"id": entity_id}).fetchone()

        if not location or not location[2]:
            return {"entity_id": entity_id, "entity_type": entity_type, "connections": []}

        # Find events near this location (join with locations)
        result = db.execute(text("""
            SELECT e.id, e.title, l.latitude, l.longitude, e.date_start
            FROM events e
            JOIN locations l ON e.primary_location_id = l.id
            WHERE l.latitude IS NOT NULL
            AND ABS(l.latitude - :lat) < 0.5 AND ABS(l.longitude - :lng) < 0.5
            ORDER BY e.date_start NULLS LAST
            LIMIT :limit
        """), {
            "lat": location[2],
            "lng": location[3],
            "limit": limit
        })

        for row in result:
            connections.append(GlobeConnection(
                source_id=entity_id,
                source_type="location",
                target_id=row[0],
                target_type="event",
                source_lat=float(location[2]),
                source_lng=float(location[3]),
                target_lat=float(row[2]),
                target_lng=float(row[3]),
                connection_type="location_event",
                year=row[4]
            ))

    return {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "connections": connections
    }


class GlobeArc(BaseModel):
    """Arc data for Historical Chain visualization on globe."""
    connection_id: int
    source_event_id: int
    target_event_id: int
    source_title: str
    target_title: str
    source_title_ko: Optional[str] = None
    target_title_ko: Optional[str] = None
    source_title_ja: Optional[str] = None
    target_title_ja: Optional[str] = None
    source_lat: float
    source_lng: float
    target_lat: float
    target_lng: float
    source_year: Optional[int] = None
    target_year: Optional[int] = None
    layer_type: str  # person, location, causal, thematic
    connection_type: Optional[str] = None  # causes, leads_to, follows, etc.
    direction: str  # forward, backward, bidirectional
    strength: float


@router.get("/arcs/{event_id}", response_model=List[GlobeArc])
async def get_event_arcs(
    event_id: int,
    layer_type: Optional[str] = Query(None, description="Filter by layer: person, location, causal"),
    min_strength: float = Query(3.0, description="Minimum connection strength"),
    limit: int = Query(30, ge=1, le=100, description="Max arcs to return"),
    db: Session = Depends(get_db),
):
    """
    Get arc data for Historical Chain visualization on globe.
    Returns connections with coordinates for drawing arcs between events.
    """
    arcs = []

    # Build conditions
    conditions = ["(ec.event_a_id = :event_id OR ec.event_b_id = :event_id)"]
    params = {"event_id": event_id, "min_strength": min_strength, "limit": limit}

    conditions.append("ec.strength_score >= :min_strength")

    if layer_type:
        conditions.append("ec.layer_type = :layer_type")
        params["layer_type"] = layer_type

    where_clause = " AND ".join(conditions)

    # Query connections with coordinates
    result = db.execute(text(f"""
        SELECT
            ec.id,
            ec.event_a_id,
            ec.event_b_id,
            ea.title as title_a,
            eb.title as title_b,
            la.latitude as lat_a,
            la.longitude as lng_a,
            lb.latitude as lat_b,
            lb.longitude as lng_b,
            ea.date_start as year_a,
            eb.date_start as year_b,
            ec.layer_type,
            ec.connection_type,
            ec.direction,
            ec.strength_score,
            ea.title_ko as title_a_ko,
            eb.title_ko as title_b_ko,
            ea.title_ja as title_a_ja,
            eb.title_ja as title_b_ja
        FROM event_connections ec
        JOIN events ea ON ec.event_a_id = ea.id
        JOIN events eb ON ec.event_b_id = eb.id
        LEFT JOIN locations la ON ea.primary_location_id = la.id
        LEFT JOIN locations lb ON eb.primary_location_id = lb.id
        WHERE {where_clause}
          AND la.latitude IS NOT NULL
          AND lb.latitude IS NOT NULL
        ORDER BY ec.strength_score DESC
        LIMIT :limit
    """), params)

    for row in result:
        # Determine source/target based on which event was selected
        if row[1] == event_id:
            # event_a is source
            arcs.append(GlobeArc(
                connection_id=row[0],
                source_event_id=row[1],
                target_event_id=row[2],
                source_title=row[3],
                target_title=row[4],
                source_title_ko=row[15],
                target_title_ko=row[16],
                source_title_ja=row[17],
                target_title_ja=row[18],
                source_lat=float(row[5]),
                source_lng=float(row[6]),
                target_lat=float(row[7]),
                target_lng=float(row[8]),
                source_year=row[9],
                target_year=row[10],
                layer_type=row[11],
                connection_type=row[12],
                direction=row[13],
                strength=float(row[14])
            ))
        else:
            # event_b is source (flip the arc)
            arcs.append(GlobeArc(
                connection_id=row[0],
                source_event_id=row[2],
                target_event_id=row[1],
                source_title=row[4],
                target_title=row[3],
                source_title_ko=row[16],
                target_title_ko=row[15],
                source_title_ja=row[18],
                target_title_ja=row[17],
                source_lat=float(row[7]),
                source_lng=float(row[8]),
                target_lat=float(row[5]),
                target_lng=float(row[6]),
                source_year=row[10],
                target_year=row[9],
                layer_type=row[11],
                connection_type=row[12],
                direction=row[13],
                strength=float(row[14])
            ))

    return arcs


@router.get("/clusters")
async def get_marker_clusters(
    year_start: Optional[int] = Query(None),
    year_end: Optional[int] = Query(None),
    grid_size: float = Query(5.0, description="Grid cell size in degrees"),
    db: Session = Depends(get_db),
):
    """
    Get clustered markers for zoomed-out view.
    Groups markers by geographic grid cells.
    """
    params = {"grid_size": grid_size}
    conditions = ["l.latitude IS NOT NULL"]

    if year_start:
        conditions.append("e.date_start >= :year_start")
        params["year_start"] = year_start
    if year_end:
        conditions.append("e.date_start <= :year_end")
        params["year_end"] = year_end

    where_clause = " AND ".join(conditions)

    result = db.execute(text(f"""
        SELECT
            FLOOR(l.latitude / :grid_size) * :grid_size + :grid_size / 2 as center_lat,
            FLOOR(l.longitude / :grid_size) * :grid_size + :grid_size / 2 as center_lng,
            COUNT(*) as count,
            MIN(e.date_start) as min_year,
            MAX(e.date_start) as max_year
        FROM events e
        JOIN locations l ON e.primary_location_id = l.id
        WHERE {where_clause}
        GROUP BY FLOOR(l.latitude / :grid_size), FLOOR(l.longitude / :grid_size)
        HAVING COUNT(*) > 0
        ORDER BY count DESC
    """), params)

    clusters = [
        {
            "lat": float(row[0]),
            "lng": float(row[1]),
            "count": row[2],
            "year_range": [row[3], row[4]]
        }
        for row in result
    ]

    return {
        "grid_size": grid_size,
        "clusters": clusters,
        "total_clusters": len(clusters)
    }


# ============== Smart Markers System ==============

class NearbyEvent(BaseModel):
    """Event near a hero (too close to display separately)."""
    id: int
    title: str
    title_ko: Optional[str] = None
    title_ja: Optional[str] = None
    year: Optional[int] = None
    category: Optional[str] = None
    importance: int
    location_name: Optional[str] = None
    location_name_ko: Optional[str] = None
    location_name_ja: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class NearbyPerson(BaseModel):
    """Person attributed to a nearby hero marker."""
    id: int
    name: str
    name_ko: Optional[str] = None
    name_ja: Optional[str] = None
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    role: Optional[str] = None
    importance: int  # global_score mapped to 1-5 scale


class HeroMarker(BaseModel):
    """Hero marker: important event displayed as a card on the globe."""
    id: int
    type: Literal["event"] = "event"
    lat: float
    lng: float
    title: str
    title_ko: Optional[str] = None
    title_ja: Optional[str] = None
    description: Optional[str] = None
    year: Optional[int] = None
    year_end: Optional[int] = None
    category: Optional[str] = None
    importance: int
    child_count: int = 0
    location_name: Optional[str] = None
    location_name_ko: Optional[str] = None
    location_name_ja: Optional[str] = None
    location_id: Optional[int] = None
    nearby_events: List[NearbyEvent] = []
    nearby_event_count: int = 0    # actual total (may exceed len(nearby_events))
    nearby_persons: List[NearbyPerson] = []
    nearby_person_count: int = 0   # actual total


class SmartMarkersResponse(BaseModel):
    """Response with hero cards for zoom-aware display."""
    heroes: List[HeroMarker]
    zoom: str
    total_events: int


def _haversine_approx(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Approximate angular distance in degrees (fast, no trig)."""
    dlat = abs(lat1 - lat2)
    dlng = abs(lng1 - lng2)
    return (dlat * dlat + dlng * dlng) ** 0.5


def _select_heroes(candidates: list, max_count: int, min_distance_deg: float, zoom: str = "cosmic") -> tuple:
    """Select heroes with overlap prevention and stacking (2-pass).

    Pass 1: iterate candidates (sorted by importance DESC),
    accept if far enough from all existing heroes, otherwise attribute
    (stack) to the nearest hero. Orphans (too far, over limit) collected.

    Pass 2: imp>=4 orphans force-attributed to nearest hero so they
    don't silently disappear.

    Returns: (heroes_list, dropped_map) where dropped_map maps
             winner hero id -> list of dropped candidate dicts.
    """
    heroes: list = []
    hero_ids: set = set()
    dropped_map: dict = {}  # hero_id -> [dropped_candidate, ...]
    orphans: list = []  # candidates that couldn't be attributed
    # Max distance for attribution: beyond this, candidate goes to orphans
    max_attr_dist = min_distance_deg * 3

    for c in candidates:
        if c["id"] in hero_ids:
            continue
        # Find nearest hero
        nearest_hero = None
        nearest_dist = float("inf")
        for h in heroes:
            d = _haversine_approx(c["lat"], c["lng"], h["lat"], h["lng"])
            if d < nearest_dist:
                nearest_dist = d
                nearest_hero = h

        if nearest_dist < min_distance_deg and nearest_hero:
            # Too close to existing hero: attribute as nearby
            dropped_map.setdefault(nearest_hero["id"], []).append(c)
        elif len(heroes) >= max_count:
            # Over limit: attribute to nearest hero ONLY if within max range
            if nearest_hero and nearest_dist < max_attr_dist:
                dropped_map.setdefault(nearest_hero["id"], []).append(c)
            else:
                orphans.append(c)
        else:
            heroes.append(c)
            hero_ids.add(c["id"])

    # Pass 2: imp>=4 orphans → attribute if close to hero, else promote to hero
    for o in orphans:
        if o.get("importance", 0) < 4:
            continue
        # Check against all heroes (including newly promoted)
        nearest = None
        nearest_dist = float("inf")
        for h in heroes:
            d = _haversine_approx(o["lat"], o["lng"], h["lat"], h["lng"])
            if d < nearest_dist:
                nearest_dist = d
                nearest = h
        if nearest and nearest_dist < min_distance_deg:
            # Close enough → stack onto nearest hero
            dropped_map.setdefault(nearest["id"], []).append(o)
        elif nearest and nearest_dist < max_attr_dist:
            # Within attribution range → stack (shows in badge)
            dropped_map.setdefault(nearest["id"], []).append(o)
        else:
            # Too far from any hero → promote to independent hero
            heroes.append(o)
            hero_ids.add(o["id"])

    return heroes, dropped_map


# Zoom-level configuration
# min_distance calibrated to prevent visual overlap of hero cards:
#   continental: card ~130px compact, ~23px/° → need ~6° separation, set 10° for margin
#   regional:    card ~180px full, ~45px/° → need ~4° separation
#   local:       card ~180px full, ~150px/° → need ~1.2° separation
ZOOM_CONFIG = {
    "cosmic":      {"min_importance": 4, "max_heroes": 10,  "min_distance": 20},
    "continental": {"min_importance": 4, "max_heroes": 15,  "min_distance": 8},
    "regional":    {"min_importance": 3, "max_heroes": 25,  "min_distance": 3},
    "local":       {"min_importance": 2, "max_heroes": 40,  "min_distance": 1.0},
}


@router.get("/smart-markers", response_model=SmartMarkersResponse)
async def get_smart_markers(
    year_start: int = Query(..., description="Start year (BCE as negative)"),
    year_end: int = Query(..., description="End year"),
    zoom: str = Query("cosmic", description="Zoom level: cosmic/continental/regional/local"),
    bounds: Optional[str] = Query(None, description="lat1,lng1,lat2,lng2 viewport bounds"),
    limit_heroes: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Smart Markers: zoom-level-aware event display.

    Returns hero cards (important events) with nearby event stacking.
    Hero selection uses importance-based filtering with overlap prevention.
    """
    config = ZOOM_CONFIG.get(zoom, ZOOM_CONFIG["cosmic"])
    min_importance = config["min_importance"]
    min_distance = config["min_distance"]
    max_heroes = min(config["max_heroes"], limit_heroes)

    # Parse bounds
    bounds_filter = ""
    bounds_params: dict = {}
    if bounds:
        try:
            lat1, lng1, lat2, lng2 = map(float, bounds.split(","))
            bounds_filter = """
                AND l.latitude BETWEEN :lat_min AND :lat_max
                AND l.longitude BETWEEN :lng_min AND :lng_max
            """
            bounds_params = {
                "lat_min": min(lat1, lat2),
                "lat_max": max(lat1, lat2),
                "lng_min": min(lng1, lng2),
                "lng_max": max(lng1, lng2),
            }
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid bounds format")

    # Step 1: Get hero candidates (high importance events)
    candidate_limit = max(max_heroes * 10, 150)  # Fetch enough to never lose imp>=4 events
    params_heroes: dict = {
        "year_start": year_start,
        "year_end": year_end,
        "min_importance": min_importance,
        "candidate_limit": candidate_limit,
    }
    params_heroes.update(bounds_params)

    hero_result = db.execute(text(f"""
        SELECT e.id, e.title, e.title_ko, e.title_ja,
               ed.description, e.date_start, e.date_end,
               l.latitude, l.longitude, l.name as location_name,
               e.importance,
               (SELECT COUNT(*) FROM events ec WHERE ec.parent_event_id = e.id) as child_count,
               c.name as category,
               l.name_ko as location_name_ko,
               l.name_ja as location_name_ja,
               l.id as location_id
        FROM events e
        JOIN locations l ON e.primary_location_id = l.id
        LEFT JOIN event_details ed ON ed.event_id = e.id
        LEFT JOIN categories c ON e.category_id = c.id
        WHERE e.date_start >= :year_start AND e.date_start <= :year_end
          AND l.latitude IS NOT NULL
          AND l.longitude IS NOT NULL
          AND e.importance >= :min_importance
          {bounds_filter}
        ORDER BY e.importance DESC, child_count DESC, e.date_start ASC NULLS LAST
        LIMIT :candidate_limit
    """), params_heroes)

    candidates = []
    for row in hero_result:
        candidates.append({
            "id": row[0],
            "title": row[1] or "Unknown Event",
            "title_ko": row[2],
            "title_ja": row[3],
            "description": (row[4] or "")[:200] if row[4] else None,
            "year": row[5],
            "year_end": row[6],
            "lat": float(row[7]),
            "lng": float(row[8]),
            "location_name": row[9],
            "importance": row[10] or 3,
            "child_count": row[11] or 0,
            "category": row[12],
            "location_name_ko": row[13],
            "location_name_ja": row[14],
            "location_id": row[15],
        })

    # Step 2: Select heroes with overlap prevention
    selected, dropped_map = _select_heroes(candidates, max_heroes, min_distance, zoom)
    hero_ids = [h["id"] for h in selected]

    heroes = []
    for h in selected:
        # Build nearby_events from dropped candidates (max 50, importance desc)
        raw_nearby = dropped_map.get(h["id"], [])
        raw_nearby.sort(key=lambda x: x.get("importance", 0), reverse=True)
        nearby_events = [
            NearbyEvent(
                id=s["id"],
                title=s["title"],
                title_ko=s.get("title_ko"),
                title_ja=s.get("title_ja"),
                year=s.get("year"),
                category=s.get("category"),
                importance=s.get("importance", 0),
                location_name=s.get("location_name"),
                location_name_ko=s.get("location_name_ko"),
                location_name_ja=s.get("location_name_ja"),
                lat=s.get("lat"),
                lng=s.get("lng"),
            )
            for s in raw_nearby[:50]
        ]
        heroes.append(HeroMarker(
            id=h["id"],
            lat=h["lat"],
            lng=h["lng"],
            title=h["title"],
            title_ko=h["title_ko"],
            title_ja=h["title_ja"],
            description=h["description"],
            year=h["year"],
            year_end=h["year_end"],
            category=h["category"],
            importance=h["importance"],
            child_count=h["child_count"],
            location_name=h["location_name"],
            location_name_ko=h.get("location_name_ko"),
            location_name_ja=h.get("location_name_ja"),
            location_id=h.get("location_id"),
            nearby_events=nearby_events,
            nearby_event_count=len(raw_nearby),
        ))

    # Step 3: Get total event count for this time range
    params_total: dict = {"year_start": year_start, "year_end": year_end}
    params_total.update(bounds_params)
    total_events = db.execute(text(f"""
        SELECT COUNT(*)
        FROM events e
        JOIN locations l ON e.primary_location_id = l.id
        WHERE e.date_start >= :year_start AND e.date_start <= :year_end
          AND l.latitude IS NOT NULL
          {bounds_filter}
    """), params_total).scalar() or 0

    # Step 4: Attribute persons to nearest heroes
    if heroes and zoom != "cosmic":
        person_min_score = {"continental": 70, "regional": 50, "local": 30}.get(zoom, 70)
        params_persons: dict = {
            "year_start": year_start,
            "year_end": year_end,
            "person_min_score": person_min_score,
            "person_limit": max_heroes * 5,
        }
        params_persons.update(bounds_params)

        person_bounds = bounds_filter.replace("l.", "bl.") if bounds_filter else ""

        person_result = db.execute(text(f"""
            SELECT p.id, p.name, p.name_ko, p.name_ja,
                   p.birth_year, p.death_year,
                   bl.latitude, bl.longitude,
                   COALESCE(p.global_score, 0), p.role
            FROM persons p
            JOIN locations bl ON p.birthplace_id = bl.id
            WHERE bl.latitude IS NOT NULL AND bl.longitude IS NOT NULL
              AND COALESCE(p.global_score, 0) >= :person_min_score
              AND p.birth_year <= :year_end
              AND COALESCE(p.death_year, p.birth_year + 80) >= :year_start
              {person_bounds}
            ORDER BY p.global_score DESC NULLS LAST
            LIMIT :person_limit
        """), params_persons)

        # Build person_map: hero_id -> [NearbyPerson, ...]
        person_map: dict = {}
        hero_dicts = [{"id": h.id, "lat": h.lat, "lng": h.lng} for h in heroes]
        for row in person_result:
            p_lat, p_lng = float(row[6]), float(row[7])
            # Find nearest hero
            nearest_hero = None
            nearest_dist = float("inf")
            for hd in hero_dicts:
                d = _haversine_approx(p_lat, p_lng, hd["lat"], hd["lng"])
                if d < nearest_dist:
                    nearest_dist = d
                    nearest_hero = hd
            # Only attribute if within reasonable distance (min_distance * 3)
            if nearest_hero and nearest_dist < min_distance * 3:
                hid = nearest_hero["id"]
                if hid not in person_map:
                    person_map[hid] = []
                person_map[hid].append(NearbyPerson(
                    id=row[0],
                    name=row[1] or "Unknown",
                    name_ko=row[2],
                    name_ja=row[3],
                    birth_year=row[4],
                    death_year=row[5],
                    role=row[9],
                    importance=min(5, max(1, (row[8] or 0) // 20)),
                ))

        # Attach nearby_persons to heroes (max 5 in list, but track real count)
        for hero in heroes:
            persons = person_map.get(hero.id, [])
            persons.sort(key=lambda p: p.importance, reverse=True)
            hero.nearby_persons = persons[:5]
            hero.nearby_person_count = len(persons)

    return SmartMarkersResponse(
        heroes=heroes,
        zoom=zoom,
        total_events=total_events,
    )


# ============== Node System ==============

class LocationNode(BaseModel):
    """로케이션 노드: 이벤트가 할당된 고정 지리 노드."""
    id: int
    name: str
    name_ko: Optional[str] = None
    name_ja: Optional[str] = None
    lat: float
    lng: float
    event_count: int          # 전체 이벤트 수
    active_event_count: int   # 현재 연도 범위 내 이벤트 수
    tier: int                 # 1=cosmic, 2=continental, 3=regional, 4=local
    top_event: Optional[str] = None     # 가장 중요한 이벤트 제목
    top_importance: Optional[int] = None


class NodeEventsResponse(BaseModel):
    """노드의 이벤트 리스트."""
    location_id: int
    location_name: str
    lat: float
    lng: float
    total: int
    events: list


@router.get("/nodes", response_model=List[LocationNode])
async def get_location_nodes(
    year_start: Optional[int] = Query(None, description="시작 연도 (BCE=-값)"),
    year_end: Optional[int] = Query(None, description="종료 연도"),
    zoom: str = Query("cosmic", description="줌 레벨: cosmic/continental/regional/local"),
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    """
    로케이션 노드 목록 반환.

    노드 = locations 테이블의 레코드. 각 노드에 매칭된 이벤트 수를 집계.
    줌 레벨에 따라 최소 이벤트 수 기준으로 필터링.

    Tier 기준:
    - Tier 1 (cosmic):       event_count >= 20
    - Tier 2 (continental):  event_count >= 5
    - Tier 3 (regional):     event_count >= 1
    - Tier 4 (local):        모든 노드 (이벤트 0개 포함)
    """
    # 줌별 최소 이벤트 수
    zoom_thresholds = {
        "cosmic": 20,
        "continental": 5,
        "regional": 1,
        "local": 0,
    }
    min_events = zoom_thresholds.get(zoom, 5)

    # 연도 필터 조건
    year_conditions = ""
    params: dict = {"min_events": min_events, "limit": limit}

    active_count_expr = "0"
    if year_start is not None and year_end is not None:
        year_conditions = """
            AND e_active.date_start >= :year_start
            AND e_active.date_start <= :year_end
        """
        active_count_expr = f"""
            (SELECT COUNT(e_active.id)
             FROM events e_active
             WHERE e_active.primary_location_id = l.id
             {year_conditions})
        """
        params["year_start"] = year_start
        params["year_end"] = year_end
    elif year_start is not None:
        year_conditions = "AND e_active.date_start >= :year_start"
        active_count_expr = f"""
            (SELECT COUNT(e_active.id)
             FROM events e_active
             WHERE e_active.primary_location_id = l.id
             {year_conditions})
        """
        params["year_start"] = year_start
    elif year_end is not None:
        year_conditions = "AND e_active.date_start <= :year_end"
        active_count_expr = f"""
            (SELECT COUNT(e_active.id)
             FROM events e_active
             WHERE e_active.primary_location_id = l.id
             {year_conditions})
        """
        params["year_end"] = year_end

    # min_events가 0이면 LEFT JOIN으로 이벤트 없는 노드도 포함
    if min_events == 0:
        result = db.execute(text(f"""
            SELECT l.id, l.name, l.name_ko, l.name_ja, l.latitude, l.longitude,
                   COUNT(e.id) as event_count,
                   {active_count_expr} as active_count,
                   (SELECT e2.title FROM events e2
                    WHERE e2.primary_location_id = l.id
                    ORDER BY e2.importance DESC NULLS LAST, e2.id
                    LIMIT 1) as top_event,
                   (SELECT e2.importance FROM events e2
                    WHERE e2.primary_location_id = l.id
                    ORDER BY e2.importance DESC NULLS LAST, e2.id
                    LIMIT 1) as top_importance
            FROM locations l
            LEFT JOIN events e ON e.primary_location_id = l.id
            WHERE l.latitude IS NOT NULL
              AND l.longitude IS NOT NULL
            GROUP BY l.id, l.name, l.name_ko, l.name_ja, l.latitude, l.longitude
            ORDER BY COUNT(e.id) DESC
            LIMIT :limit
        """), params)
    else:
        result = db.execute(text(f"""
            SELECT l.id, l.name, l.name_ko, l.name_ja, l.latitude, l.longitude,
                   COUNT(e.id) as event_count,
                   {active_count_expr} as active_count,
                   (SELECT e2.title FROM events e2
                    WHERE e2.primary_location_id = l.id
                    ORDER BY e2.importance DESC NULLS LAST, e2.id
                    LIMIT 1) as top_event,
                   (SELECT e2.importance FROM events e2
                    WHERE e2.primary_location_id = l.id
                    ORDER BY e2.importance DESC NULLS LAST, e2.id
                    LIMIT 1) as top_importance
            FROM locations l
            JOIN events e ON e.primary_location_id = l.id
            WHERE l.latitude IS NOT NULL
              AND l.longitude IS NOT NULL
            GROUP BY l.id, l.name, l.name_ko, l.name_ja, l.latitude, l.longitude
            HAVING COUNT(e.id) >= :min_events
            ORDER BY COUNT(e.id) DESC
            LIMIT :limit
        """), params)

    nodes = []
    for row in result:
        ec = row[6]
        tier = 1 if ec >= 20 else (2 if ec >= 5 else (3 if ec >= 1 else 4))
        nodes.append(LocationNode(
            id=row[0],
            name=row[1] or "Unknown",
            name_ko=row[2],
            name_ja=row[3],
            lat=float(row[4]),
            lng=float(row[5]),
            event_count=ec,
            active_event_count=row[7] or 0,
            tier=tier,
            top_event=row[8],
            top_importance=row[9],
        ))

    return nodes


@router.get("/nodes/{location_id}/events")
async def get_node_events(
    location_id: int,
    year_start: Optional[int] = Query(None),
    year_end: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    특정 노드의 이벤트 리스트 반환.
    노드 클릭 시 해당 로케이션의 이벤트들을 보여줌.
    """
    # 로케이션 정보
    loc = db.execute(text("""
        SELECT id, name, name_ko, latitude, longitude FROM locations WHERE id = :id
    """), {"id": location_id}).fetchone()

    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    # 이벤트 쿼리
    conditions = ["e.primary_location_id = :location_id"]
    params: dict = {"location_id": location_id, "limit": limit, "offset": offset}

    if year_start is not None:
        conditions.append("e.date_start >= :year_start")
        params["year_start"] = year_start
    if year_end is not None:
        conditions.append("e.date_start <= :year_end")
        params["year_end"] = year_end

    where = " AND ".join(conditions)

    # 전체 수
    total = db.execute(text(f"""
        SELECT COUNT(*) FROM events e WHERE {where}
    """), params).scalar()

    # 이벤트 리스트
    events = db.execute(text(f"""
        SELECT e.id, e.title, e.title_ko, e.title_ja, e.date_start, e.date_end,
               e.importance, ed.description, e.category_id,
               c.name as category_name
        FROM events e
        LEFT JOIN event_details ed ON ed.event_id = e.id
        LEFT JOIN categories c ON e.category_id = c.id
        WHERE {where}
        ORDER BY e.importance DESC NULLS LAST, e.date_start ASC NULLS LAST
        LIMIT :limit OFFSET :offset
    """), params)

    event_list = [
        {
            "id": row[0],
            "title": row[1],
            "title_ko": row[2],
            "title_ja": row[3],
            "date_start": row[4],
            "date_end": row[5],
            "importance": row[6],
            "description": row[7],
            "category": row[9],
        }
        for row in events
    ]

    return {
        "location_id": loc[0],
        "location_name": loc[1],
        "location_name_ko": loc[2],
        "lat": float(loc[3]),
        "lng": float(loc[4]),
        "total": total,
        "events": event_list,
    }
