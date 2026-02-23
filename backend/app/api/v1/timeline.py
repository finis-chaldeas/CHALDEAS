"""
Timeline API - Period-based historical narrative exploration.

Provides endpoints for browsing 50-year historical periods with AI-generated
regional narratives, top events/persons, and user feedback/curation.
"""
import json
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from pydantic import BaseModel

from app.db.session import get_db

router = APIRouter()


def _format_year(year: Optional[int]) -> Optional[str]:
    """Format year for display."""
    if year is None:
        return None
    if year < 0:
        return f"{abs(year)} BCE"
    return f"{year} CE"


def _format_lifespan(birth: Optional[int], death: Optional[int]) -> str:
    """Format person lifespan for display."""
    if birth is None and death is None:
        return "Unknown"

    def fmt(y):
        if y is None:
            return "?"
        return f"{abs(y)} BCE" if y < 0 else f"{y} CE"

    if birth and death and (birth < 0) == (death < 0):
        era = "BCE" if birth < 0 else "CE"
        return f"{abs(birth)}-{abs(death)} {era}"

    return f"{fmt(birth)} - {fmt(death)}"


REGION_NAMES = {
    "europe": "Europe & Mediterranean",
    "near_east": "Near East & Central Asia",
    "south_asia": "South Asia",
    "east_asia": "East Asia & Pacific",
    "africa": "Africa",
    "americas": "Americas",
}


# --- Response Models ---

class PeriodSummary(BaseModel):
    period_start: int
    period_end: int
    era_id: Optional[str] = None
    headline: Optional[str] = None
    headline_ko: Optional[str] = None
    event_count: int = 0
    person_count: int = 0
    region_count: int = 0
    has_narrative: bool = False
    date_display: Optional[str] = None


class RegionNarrative(BaseModel):
    region: str
    region_name: str
    headline: Optional[str] = None
    narrative: Optional[str] = None
    keywords: Optional[list[str]] = None
    quote: Optional[str] = None
    quote_source: Optional[str] = None
    event_count: int = 0
    person_count: int = 0
    top_events: Optional[list[dict]] = None
    top_persons: Optional[list[dict]] = None
    narrative_id: Optional[int] = None


class PeriodDetail(BaseModel):
    period_start: int
    period_end: int
    era_id: Optional[str] = None
    # Global overview
    headline: Optional[str] = None
    headline_ko: Optional[str] = None
    narrative: Optional[str] = None
    narrative_ko: Optional[str] = None
    defining_moment: Optional[str] = None
    curated_status: Optional[str] = None
    narrative_id: Optional[int] = None
    # Regional breakdowns
    regions: list[RegionNarrative] = []
    # Flat event/person lists (for backward compatibility + full lists)
    events: list[dict] = []
    persons: list[dict] = []


class FeedbackRequest(BaseModel):
    target_type: str       # 'period_narrative', 'entity_narrative', 'domain', 'score'
    target_id: int
    feedback_type: str     # 'incorrect', 'misleading', 'missing', 'wrong_domain', 'wrong_score'
    description: Optional[str] = None
    suggested_fix: Optional[str] = None


# --- Endpoints ---

@router.get("/periods")
def list_periods(
    db: Session = Depends(get_db),
    era_id: Optional[str] = Query(None, description="Filter by era: ancient, classical, medieval, early-modern, modern, contemporary"),
    min_score: int = Query(70, ge=0, le=100, description="Minimum importance_score for events/persons in period"),
    limit: int = Query(200, ge=1, le=500, description="Max periods to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """
    List all historical periods with summary info.

    Returns 50-year windows that contain events/persons with importance_score >= min_score.
    Includes narrative headline (from global overview) and count of active regions.
    """
    era_filter = ""
    params: dict = {"min_score": min_score, "limit": limit, "offset": offset}

    if era_id:
        era_filter = "AND pn.era_id = :era_id"
        params["era_id"] = era_id

    rows = db.execute(text(f"""
        WITH period_events AS (
            SELECT
                FLOOR(date_start::float / 50) * 50 AS ps,
                COUNT(*) AS cnt,
                MAX(importance_score) AS max_score
            FROM events
            WHERE date_start IS NOT NULL AND importance_score >= :min_score
            GROUP BY FLOOR(date_start::float / 50) * 50
        ),
        period_persons AS (
            SELECT
                FLOOR(COALESCE(birth_year, floruit_start)::float / 50) * 50 AS ps,
                COUNT(*) AS cnt,
                MAX(COALESCE(global_score, importance_score)) AS max_score
            FROM persons
            WHERE COALESCE(birth_year, floruit_start) IS NOT NULL
              AND COALESCE(global_score, importance_score) >= :min_score
            GROUP BY FLOOR(COALESCE(birth_year, floruit_start)::float / 50) * 50
        ),
        all_periods AS (
            SELECT COALESCE(e.ps, p.ps) AS ps,
                   COALESCE(e.cnt, 0) AS event_count,
                   COALESCE(p.cnt, 0) AS person_count
            FROM period_events e
            FULL OUTER JOIN period_persons p ON e.ps = p.ps
        )
        SELECT
            ap.ps AS period_start,
            ap.ps + 49 AS period_end,
            ap.event_count,
            ap.person_count,
            pn.id AS narrative_id,
            pn.era_id,
            pn.headline,
            pn.headline_ko,
            (SELECT COUNT(*) FROM period_narratives pn2
             WHERE pn2.period_start = ap.ps::integer AND pn2.region IS NOT NULL) AS region_count
        FROM all_periods ap
        LEFT JOIN period_narratives pn
            ON pn.period_start = ap.ps::integer AND pn.period_end = (ap.ps + 49)::integer
            AND pn.region IS NULL
        WHERE 1=1 {era_filter}
        ORDER BY ap.ps
        LIMIT :limit OFFSET :offset
    """), params).fetchall()

    items = []
    for row in rows:
        ps = int(row[0])
        pe = int(row[1])
        items.append(PeriodSummary(
            period_start=ps,
            period_end=pe,
            era_id=row[5],
            headline=row[6],
            headline_ko=row[7],
            event_count=row[2],
            person_count=row[3],
            region_count=row[8] or 0,
            has_narrative=row[4] is not None,
            date_display=f"{_format_year(ps)} ~ {_format_year(pe)}",
        ).model_dump())

    # Total count
    total_result = db.execute(text(f"""
        WITH period_events AS (
            SELECT FLOOR(date_start::float / 50) * 50 AS ps
            FROM events
            WHERE date_start IS NOT NULL AND importance_score >= :min_score
            GROUP BY FLOOR(date_start::float / 50) * 50
        ),
        period_persons AS (
            SELECT FLOOR(COALESCE(birth_year, floruit_start)::float / 50) * 50 AS ps
            FROM persons
            WHERE COALESCE(birth_year, floruit_start) IS NOT NULL
              AND COALESCE(global_score, importance_score) >= :min_score
            GROUP BY FLOOR(COALESCE(birth_year, floruit_start)::float / 50) * 50
        ),
        all_periods AS (
            SELECT COALESCE(e.ps, p.ps) AS ps
            FROM period_events e
            FULL OUTER JOIN period_persons p ON e.ps = p.ps
        )
        SELECT COUNT(*) FROM all_periods ap
        LEFT JOIN period_narratives pn
            ON pn.period_start = ap.ps::integer AND pn.period_end = (ap.ps + 49)::integer
            AND pn.region IS NULL
        WHERE 1=1 {era_filter}
    """), params).scalar()

    return {
        "items": items,
        "total": total_result or 0,
    }


@router.get("/periods/{period_start}")
def get_period_detail(
    period_start: int,
    db: Session = Depends(get_db),
    event_limit: int = Query(10, ge=1, le=50, description="Max events to return"),
    person_limit: int = Query(10, ge=1, le=50, description="Max persons to return"),
):
    """
    Get detailed period info: global overview + regional narratives + events + persons.

    Regional narratives are returned as an array sorted by event_count (most active first).
    Events and persons are returned as flat lists for backward compatibility.
    """
    period_end = period_start + 49

    # Fetch global overview (region IS NULL)
    pn = db.execute(text("""
        SELECT id, era_id, headline, headline_ko, narrative, narrative_ko,
               defining_moment, curated_status
        FROM period_narratives
        WHERE period_start = :ps AND period_end = :pe AND region IS NULL
    """), {"ps": period_start, "pe": period_end}).fetchone()

    # Fetch regional narratives
    region_rows = db.execute(text("""
        SELECT id, region, headline, narrative, keywords,
               quote, quote_source, event_count, person_count,
               top_events, top_persons
        FROM period_narratives
        WHERE period_start = :ps AND period_end = :pe AND region IS NOT NULL
        ORDER BY COALESCE(event_count, 0) + COALESCE(person_count, 0) DESC
    """), {"ps": period_start, "pe": period_end}).fetchall()

    regions = []
    for r in region_rows:
        region_id = r[1]
        top_ev = None
        top_pe = None
        try:
            if r[9]:
                top_ev = json.loads(r[9])
            if r[10]:
                top_pe = json.loads(r[10])
        except (json.JSONDecodeError, TypeError):
            pass

        regions.append(RegionNarrative(
            region=region_id,
            region_name=REGION_NAMES.get(region_id, region_id),
            headline=r[2],
            narrative=r[3],
            keywords=r[4],
            quote=r[5],
            quote_source=r[6],
            event_count=r[7] or 0,
            person_count=r[8] or 0,
            top_events=top_ev,
            top_persons=top_pe,
            narrative_id=r[0],
        ).model_dump())

    # Fetch top events (flat list) with hierarchy info
    event_rows = db.execute(text("""
        SELECT e.id, e.title, e.title_ko, e.date_start, e.date_end,
               e.importance_score, ed.description, ed.wikipedia_url,
               l.name AS location_name, l.latitude, l.longitude,
               en.narrative AS entity_narrative, en.significance,
               e.is_aggregate, e.parent_event_id,
               (SELECT COUNT(*) FROM events c WHERE c.parent_event_id = e.id) AS child_count
        FROM events e
        LEFT JOIN event_details ed ON ed.event_id = e.id
        LEFT JOIN locations l ON l.id = e.primary_location_id
        LEFT JOIN entity_narratives en ON en.entity_type = 'event' AND en.entity_id = e.id
        WHERE e.date_start >= :start AND e.date_start <= :end
          AND e.importance_score IS NOT NULL
        ORDER BY e.importance_score DESC
        LIMIT :limit
    """), {"start": period_start, "end": period_end, "limit": event_limit}).fetchall()

    events = [{
        "id": r[0], "title": r[1], "title_ko": r[2],
        "date_start": r[3], "date_end": r[4],
        "date_display": _format_year(r[3]),
        "importance_score": r[5],
        "description": (r[6][:200] + "...") if r[6] and len(r[6]) > 200 else r[6],
        "wikipedia_url": r[7],
        "location_name": r[8],
        "latitude": float(r[9]) if r[9] else None,
        "longitude": float(r[10]) if r[10] else None,
        "narrative": r[11],
        "significance": r[12],
        "is_aggregate": r[13],
        "child_count": r[14] or 0,
    } for r in event_rows]

    # Fetch top persons (flat list)
    person_rows = db.execute(text("""
        SELECT p.id, p.name, p.name_ko, p.birth_year, p.death_year,
               p.role, p.domain,
               COALESCE(p.global_score, p.importance_score) AS score,
               pd.wikipedia_url, pd.image_url,
               en.narrative AS entity_narrative, en.significance
        FROM persons p
        LEFT JOIN person_details pd ON pd.person_id = p.id
        LEFT JOIN entity_narratives en ON en.entity_type = 'person' AND en.entity_id = p.id
        WHERE COALESCE(p.birth_year, p.floruit_start) >= :start
          AND COALESCE(p.birth_year, p.floruit_start) <= :end
          AND COALESCE(p.global_score, p.importance_score) IS NOT NULL
        ORDER BY COALESCE(p.global_score, p.importance_score) DESC
        LIMIT :limit
    """), {"start": period_start, "end": period_end, "limit": person_limit}).fetchall()

    persons = [{
        "id": r[0], "name": r[1], "name_ko": r[2],
        "birth_year": r[3], "death_year": r[4],
        "date_display": _format_lifespan(r[3], r[4]),
        "role": r[5], "domain": r[6], "score": r[7],
        "wikipedia_url": r[8], "image_url": r[9],
        "narrative": r[10], "significance": r[11],
    } for r in person_rows]

    return PeriodDetail(
        period_start=period_start,
        period_end=period_end,
        era_id=pn[1] if pn else None,
        headline=pn[2] if pn else None,
        headline_ko=pn[3] if pn else None,
        narrative=pn[4] if pn else None,
        narrative_ko=pn[5] if pn else None,
        defining_moment=pn[6] if pn else None,
        curated_status=pn[7] if pn else None,
        narrative_id=pn[0] if pn else None,
        regions=regions,
        events=events,
        persons=persons,
    ).model_dump()


@router.get("/periods/{period_start}/events")
def get_period_events(
    period_start: int,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Max events to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    min_score: int = Query(0, ge=0, le=100, description="Minimum importance_score"),
):
    """Get events within a period, sorted by importance_score."""
    period_end = period_start + 49

    rows = db.execute(text("""
        SELECT e.id, e.title, e.title_ko, e.date_start, e.date_end,
               e.importance_score, ed.description,
               l.name AS location_name, l.latitude, l.longitude
        FROM events e
        LEFT JOIN event_details ed ON ed.event_id = e.id
        LEFT JOIN locations l ON l.id = e.primary_location_id
        WHERE e.date_start >= :start AND e.date_start <= :end
          AND e.importance_score >= :min_score
        ORDER BY e.importance_score DESC
        LIMIT :limit OFFSET :offset
    """), {"start": period_start, "end": period_end, "min_score": min_score,
           "limit": limit, "offset": offset}).fetchall()

    total = db.execute(text("""
        SELECT COUNT(*) FROM events
        WHERE date_start >= :start AND date_start <= :end
          AND importance_score >= :min_score
    """), {"start": period_start, "end": period_end, "min_score": min_score}).scalar()

    items = [{
        "id": r[0], "title": r[1], "title_ko": r[2],
        "date_start": r[3], "date_end": r[4],
        "date_display": _format_year(r[3]),
        "importance_score": r[5],
        "description": (r[6][:200] + "...") if r[6] and len(r[6]) > 200 else r[6],
        "location_name": r[7],
        "latitude": float(r[8]) if r[8] else None,
        "longitude": float(r[9]) if r[9] else None,
    } for r in rows]

    return {"items": items, "total": total or 0}


@router.get("/periods/{period_start}/persons")
def get_period_persons(
    period_start: int,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Max persons to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    min_score: int = Query(0, ge=0, le=100, description="Minimum score"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
):
    """Get persons within a period, sorted by global_score."""
    period_end = period_start + 49

    domain_filter = ""
    params: dict = {
        "start": period_start, "end": period_end, "min_score": min_score,
        "limit": limit, "offset": offset,
    }
    if domain:
        domain_filter = "AND p.domain = :domain"
        params["domain"] = domain

    rows = db.execute(text(f"""
        SELECT p.id, p.name, p.name_ko, p.birth_year, p.death_year,
               p.role, p.domain,
               COALESCE(p.global_score, p.importance_score) AS score,
               pd.wikipedia_url, pd.image_url
        FROM persons p
        LEFT JOIN person_details pd ON pd.person_id = p.id
        WHERE COALESCE(p.birth_year, p.floruit_start) >= :start
          AND COALESCE(p.birth_year, p.floruit_start) <= :end
          AND COALESCE(p.global_score, p.importance_score) >= :min_score
          {domain_filter}
        ORDER BY COALESCE(p.global_score, p.importance_score) DESC
        LIMIT :limit OFFSET :offset
    """), params).fetchall()

    total = db.execute(text(f"""
        SELECT COUNT(*) FROM persons p
        WHERE COALESCE(p.birth_year, p.floruit_start) >= :start
          AND COALESCE(p.birth_year, p.floruit_start) <= :end
          AND COALESCE(p.global_score, p.importance_score) >= :min_score
          {domain_filter}
    """), params).scalar()

    items = [{
        "id": r[0], "name": r[1], "name_ko": r[2],
        "birth_year": r[3], "death_year": r[4],
        "date_display": _format_lifespan(r[3], r[4]),
        "role": r[5], "domain": r[6], "score": r[7],
        "wikipedia_url": r[8], "image_url": r[9],
    } for r in rows]

    return {"items": items, "total": total or 0}


@router.post("/feedback")
def submit_feedback(
    feedback: FeedbackRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Submit user feedback/report about content.

    Accepts reports about incorrect narratives, wrong classifications, etc.
    """
    client_ip = request.client.host if request.client else None

    db.execute(text("""
        INSERT INTO user_feedback
            (target_type, target_id, feedback_type, description, suggested_fix, reporter_ip)
        VALUES (:target_type, :target_id, :feedback_type, :description, :suggested_fix, :reporter_ip)
    """), {
        "target_type": feedback.target_type,
        "target_id": feedback.target_id,
        "feedback_type": feedback.feedback_type,
        "description": feedback.description,
        "suggested_fix": feedback.suggested_fix,
        "reporter_ip": client_ip,
    })
    db.commit()

    return {"status": "ok", "message": "Feedback submitted successfully"}
