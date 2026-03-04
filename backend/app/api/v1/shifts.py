"""
History Shift API endpoints.

Provides access to curated historical shift narratives.
Shifts are page-based sequential views of connected events,
similar to Age of Empires scenarios.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sa_func
from typing import Optional

from app.db.session import get_db
from app.models.v1.chain import HistoricalChain, ChainSegment
from app.models.event import Event

router = APIRouter()


def _serialize_page(seg: ChainSegment) -> dict:
    """Serialize a ChainSegment as a shift page."""
    # Derive localized title from linked entity
    title_ko = None
    location_name = None
    location_name_ko = None
    if seg.event:
        title_ko = seg.event.title_ko
    if seg.location:
        location_name = seg.location.name
        location_name_ko = getattr(seg.location, 'name_ko', None)
    elif seg.event and seg.event.primary_location:
        location_name = seg.event.primary_location.name
        location_name_ko = getattr(seg.event.primary_location, 'name_ko', None)

    result = {
        "sequence_number": seg.sequence_number,
        "title": seg.title,
        "title_ko": title_ko,
        "chapter_number": seg.chapter_number,
        "chapter_title": seg.chapter_title,
        "page_narrative": seg.page_narrative,
        "page_narrative_ko": seg.page_narrative_ko,
        "narrative": seg.narrative,
        "narrative_ko": seg.narrative_ko,
        "year_start": seg.year_start,
        "year_end": seg.year_end,
        "importance": seg.importance or 3,
        "media_url": seg.media_url,
        "widgets": seg.widgets,
        "camera_altitude": seg.camera_altitude,
        "highlight_locations": seg.highlight_locations,
        "sub_shift_id": seg.sub_shift_id,
        "event_id": seg.event_id,
        "person_id": seg.person_id,
        "location_id": seg.location_id,
        "location_name": location_name,
        "location_name_ko": location_name_ko,
        "lat": None,
        "lng": None,
    }

    # Populate coordinates from linked location or event's primary_location
    if seg.location:
        result["lat"] = seg.location.latitude
        result["lng"] = seg.location.longitude
    elif seg.event and seg.event.primary_location:
        loc = seg.event.primary_location
        result["lat"] = loc.latitude
        result["lng"] = loc.longitude

    return result


def _serialize_shift(chain: HistoricalChain, include_pages: bool = False) -> dict:
    """Serialize a HistoricalChain as a shift."""
    result = {
        "id": chain.id,
        "chain_type": chain.chain_type,
        "title": chain.title,
        "title_ko": chain.title_ko,
        "summary": chain.summary,
        "summary_ko": chain.summary_ko,
        "year_start": chain.year_start,
        "year_end": chain.year_end,
        "globe_importance": chain.globe_importance or 3,
        "chapter_count": chain.chapter_count or 1,
        "page_count": chain.segment_count or 0,
        "display_type": chain.display_type or "modal",
        "thumbnail_url": chain.thumbnail_url,
        "status": chain.status,
        "parent_shift_id": chain.parent_shift_id,
    }

    if include_pages:
        result["pages"] = [_serialize_page(seg) for seg in chain.segments]

    return result


@router.get("")
def list_shifts(
    chain_type: Optional[str] = Query(None, description="Filter by chain type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    globe_importance_min: Optional[int] = Query(None, description="Minimum globe importance"),
    focal_event_id: Optional[int] = Query(None, description="Filter by focal event ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List available shifts."""
    query = db.query(HistoricalChain)

    if chain_type:
        query = query.filter(HistoricalChain.chain_type == chain_type)
    if status:
        query = query.filter(HistoricalChain.status == status)
    if globe_importance_min is not None:
        query = query.filter(HistoricalChain.globe_importance >= globe_importance_min)
    if focal_event_id is not None:
        query = query.filter(HistoricalChain.focal_event_id == focal_event_id)

    total = query.count()
    shifts = (
        query
        .order_by(HistoricalChain.globe_importance.desc(), HistoricalChain.year_start)
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "items": [_serialize_shift(s) for s in shifts],
        "total": total,
    }


@router.get("/{shift_id}")
def get_shift(
    shift_id: int,
    db: Session = Depends(get_db),
):
    """Get shift detail with all pages."""
    chain = (
        db.query(HistoricalChain)
        .options(
            joinedload(HistoricalChain.segments)
            .joinedload(ChainSegment.event)
            .joinedload(Event.primary_location),
            joinedload(HistoricalChain.segments)
            .joinedload(ChainSegment.location),
        )
        .filter(HistoricalChain.id == shift_id)
        .first()
    )

    if not chain:
        raise HTTPException(status_code=404, detail="Shift not found")

    # Update access count
    chain.access_count = (chain.access_count or 0) + 1
    chain.last_accessed_at = sa_func.now()
    db.commit()

    return _serialize_shift(chain, include_pages=True)


@router.get("/{shift_id}/pages")
def list_shift_pages(
    shift_id: int,
    db: Session = Depends(get_db),
):
    """Get all pages for a shift."""
    chain = db.query(HistoricalChain).filter(HistoricalChain.id == shift_id).first()
    if not chain:
        raise HTTPException(status_code=404, detail="Shift not found")

    segments = (
        db.query(ChainSegment)
        .options(
            joinedload(ChainSegment.event)
            .joinedload(Event.primary_location),
            joinedload(ChainSegment.location),
        )
        .filter(ChainSegment.chain_id == shift_id)
        .order_by(ChainSegment.sequence_number)
        .all()
    )

    return {
        "shift_id": shift_id,
        "pages": [_serialize_page(seg) for seg in segments],
        "total": len(segments),
    }


@router.get("/{shift_id}/pages/{seq}")
def get_shift_page(
    shift_id: int,
    seq: int,
    db: Session = Depends(get_db),
):
    """Get a single page with prev/next info."""
    segment = (
        db.query(ChainSegment)
        .options(
            joinedload(ChainSegment.event)
            .joinedload(Event.primary_location),
            joinedload(ChainSegment.location),
        )
        .filter(
            ChainSegment.chain_id == shift_id,
            ChainSegment.sequence_number == seq,
        )
        .first()
    )

    if not segment:
        raise HTTPException(status_code=404, detail="Page not found")

    # Get total page count for prev/next info
    total = (
        db.query(sa_func.count(ChainSegment.id))
        .filter(ChainSegment.chain_id == shift_id)
        .scalar()
    )

    page = _serialize_page(segment)
    page["has_prev"] = seq > 0
    page["has_next"] = seq < total - 1
    page["total_pages"] = total

    return page
