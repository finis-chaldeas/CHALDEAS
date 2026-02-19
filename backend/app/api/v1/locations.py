"""
Locations API endpoints.

Provides access to geographical location nodes from PostgreSQL database.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.db.session import get_db
from app.models.location import Location
from app.models.event import Event
from app.models.territory import TerritoryLocation
from app.services import location_service

router = APIRouter()


def location_to_dict(location, event_count=None) -> dict:
    """Convert Location model to dictionary for JSON response."""
    result = {
        "id": location.id,
        "name": location.name,
        "name_ko": location.name_ko,
        "name_ja": location.name_ja,
        "latitude": float(location.latitude) if location.latitude else None,
        "longitude": float(location.longitude) if location.longitude else None,
        "location_type": location.location_type,
        "wikidata_id": location.wikidata_id,
    }
    if event_count is not None:
        result["event_count"] = event_count
    return result


@router.get("")
def list_locations(
    db: Session = Depends(get_db),
    lat_min: Optional[float] = Query(None, description="Minimum latitude"),
    lat_max: Optional[float] = Query(None, description="Maximum latitude"),
    lng_min: Optional[float] = Query(None, description="Minimum longitude"),
    lng_max: Optional[float] = Query(None, description="Maximum longitude"),
    location_type: Optional[str] = Query(None, description="Filter by location_type"),
    sort_by: Optional[str] = Query(None, description="Sort by: 'events' for event count"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    List locations with optional bounding box filtering.
    Includes event_count (number of events at each location).
    """
    # Subquery for event counts
    event_count_sq = (
        db.query(
            Event.primary_location_id,
            func.count(Event.id).label('event_count')
        )
        .filter(Event.primary_location_id.isnot(None))
        .group_by(Event.primary_location_id)
        .subquery()
    )

    query = (
        db.query(Location, func.coalesce(event_count_sq.c.event_count, 0).label('event_count'))
        .outerjoin(event_count_sq, Location.id == event_count_sq.c.primary_location_id)
        .filter(Location.latitude.isnot(None))
    )

    # Filter by location_type
    if location_type:
        query = query.filter(Location.location_type == location_type)

    if lat_min is not None:
        query = query.filter(Location.latitude >= lat_min)
    if lat_max is not None:
        query = query.filter(Location.latitude <= lat_max)
    if lng_min is not None:
        query = query.filter(Location.longitude >= lng_min)
    if lng_max is not None:
        query = query.filter(Location.longitude <= lng_max)

    if sort_by == 'events':
        query = query.order_by(func.coalesce(event_count_sq.c.event_count, 0).desc())

    total = query.count()
    results = query.offset(offset).limit(limit).all()

    return {
        "items": [location_to_dict(loc, ec) for loc, ec in results],
        "total": total,
        "filtered": len(results),
    }


@router.get("/stats")
def get_location_stats(db: Session = Depends(get_db)):
    """Get statistics about location data."""
    total = db.query(func.count(Location.id)).scalar()
    with_coords = db.query(func.count(Location.id)).filter(
        Location.latitude.isnot(None)
    ).scalar()
    with_wikidata = db.query(func.count(Location.id)).filter(
        Location.wikidata_id.isnot(None)
    ).scalar()

    return {
        "total": total,
        "with_coordinates": with_coords,
        "with_wikidata": with_wikidata,
    }


@router.get("/{location_id}")
def get_location(
    location_id: int,
    db: Session = Depends(get_db),
):
    """Get detailed information about a specific location."""
    location = location_service.get_location_by_id(db, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    result = location_to_dict(location)
    result["country"] = location.country
    result["parent_location_id"] = location.parent_location_id

    # Add 1:1 details (description, wikipedia_url, etc.)
    if location.details:
        result["details"] = {
            "description": location.details.description,
            "description_ko": location.details.description_ko,
            "wikipedia_url": location.details.wikipedia_url,
        }

    # Add time-varying names
    result["names"] = [
        {
            "id": n.id,
            "name": n.name,
            "name_ko": n.name_ko,
            "name_ja": n.name_ja,
            "language": n.language,
            "valid_from": n.valid_from,
            "valid_until": n.valid_until,
            "is_primary": n.is_primary,
            "name_type": n.name_type,
        }
        for n in (location.names or [])
    ]

    # Add territory history (political affiliations over time)
    territory_locs = (
        db.query(TerritoryLocation)
        .filter(TerritoryLocation.location_id == location_id)
        .all()
    )
    result["territories"] = [
        {
            "name": tl.territory.name,
            "name_ko": tl.territory.name_ko,
            "territory_type": tl.territory.territory_type,
            "valid_from": tl.valid_from,
            "valid_until": tl.valid_until,
        }
        for tl in territory_locs
        if tl.territory
    ]

    # Add events at this location
    events = db.query(Event).filter(Event.primary_location_id == location_id).limit(50).all()
    result["events"] = [
        {
            "id": e.id,
            "title": e.title,
            "date_start": e.date_start,
            "date_end": e.date_end,
        }
        for e in events
    ]
    result["event_count"] = len(events)

    return result
