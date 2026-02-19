"""
Threads API - Event threads grouped by connecting person.

Uses event_connections (layer_type='person') to find events linked by a common person,
grouping them into narrative "threads" (story arcs).
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db

router = APIRouter()


@router.get("")
async def list_threads(
    year_start: Optional[int] = Query(None, description="Filter events from year"),
    year_end: Optional[int] = Query(None, description="Filter events until year"),
    lat_min: Optional[float] = Query(None, description="Viewport south bound"),
    lat_max: Optional[float] = Query(None, description="Viewport north bound"),
    lng_min: Optional[float] = Query(None, description="Viewport west bound"),
    lng_max: Optional[float] = Query(None, description="Viewport east bound"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    List event threads grouped by connecting person.

    A "thread" is a set of events linked by a common person through event_connections.
    Returns person info + event count + year range + sample event titles.
    """
    # Build WHERE clauses for event filtering
    where_clauses = ["ec.layer_type = 'person'"]
    params: dict = {"limit": limit}

    if year_start is not None:
        where_clauses.append("e.date_start >= :year_start")
        params["year_start"] = year_start
    if year_end is not None:
        where_clauses.append("e.date_start <= :year_end")
        params["year_end"] = year_end
    if lat_min is not None and lat_max is not None and lng_min is not None and lng_max is not None:
        where_clauses.append("""
            e.primary_location_id IN (
                SELECT id FROM locations
                WHERE latitude BETWEEN :lat_min AND :lat_max
                  AND longitude BETWEEN :lng_min AND :lng_max
            )
        """)
        params["lat_min"] = lat_min
        params["lat_max"] = lat_max
        params["lng_min"] = lng_min
        params["lng_max"] = lng_max

    where_sql = " AND ".join(where_clauses)

    # Main query: group event_connections by person, count distinct events
    query = text(f"""
        WITH thread_events AS (
            SELECT
                ec.layer_entity_id AS person_id,
                e.id AS event_id,
                e.title AS event_title,
                e.date_start
            FROM event_connections ec
            JOIN events e ON e.id = ec.event_a_id
            WHERE {where_sql}

            UNION

            SELECT
                ec.layer_entity_id AS person_id,
                e.id AS event_id,
                e.title AS event_title,
                e.date_start
            FROM event_connections ec
            JOIN events e ON e.id = ec.event_b_id
            WHERE {where_sql}
        ),
        thread_summary AS (
            SELECT
                person_id,
                COUNT(DISTINCT event_id) AS event_count,
                MIN(date_start) AS year_start,
                MAX(date_start) AS year_end,
                array_agg(DISTINCT event_title ORDER BY event_title) AS all_titles
            FROM thread_events
            GROUP BY person_id
            HAVING COUNT(DISTINCT event_id) >= 2
            ORDER BY COUNT(DISTINCT event_id) DESC
            LIMIT :limit
        )
        SELECT
            ts.person_id,
            p.name,
            p.name_ko,
            p.birth_year,
            p.death_year,
            p.role,
            ts.event_count,
            ts.year_start,
            ts.year_end,
            ts.all_titles AS sample_titles
        FROM thread_summary ts
        JOIN persons p ON p.id = ts.person_id
        ORDER BY ts.event_count DESC
    """)

    result = db.execute(query, params)
    threads = []
    for row in result:
        all_titles = row[9] or []
        threads.append({
            "person_id": row[0],
            "person_name": row[1],
            "person_name_ko": row[2],
            "birth_year": row[3],
            "death_year": row[4],
            "role": row[5],
            "event_count": row[6],
            "year_start": row[7],
            "year_end": row[8],
            "sample_titles": all_titles[:5],
        })

    return {"items": threads, "total": len(threads)}


@router.get("/{person_id}/events")
async def get_thread_events(
    person_id: int,
    year_start: Optional[int] = Query(None),
    year_end: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Get all events in a person's thread, ordered chronologically.
    """
    where_clauses = ["ec.layer_type = 'person'", "ec.layer_entity_id = :person_id"]
    params: dict = {"person_id": person_id}

    if year_start is not None:
        where_clauses.append("e.date_start >= :year_start")
        params["year_start"] = year_start
    if year_end is not None:
        where_clauses.append("e.date_start <= :year_end")
        params["year_end"] = year_end

    where_sql = " AND ".join(where_clauses)

    query = text(f"""
        SELECT DISTINCT e.id, e.title, e.title_ko, e.date_start, e.date_end,
               e.importance, l.latitude, l.longitude,
               l.name AS location_name
        FROM event_connections ec
        JOIN events e ON e.id = ec.event_a_id
        LEFT JOIN locations l ON l.id = e.primary_location_id
        WHERE {where_sql}

        UNION

        SELECT DISTINCT e.id, e.title, e.title_ko, e.date_start, e.date_end,
               e.importance, l.latitude, l.longitude,
               l.name AS location_name
        FROM event_connections ec
        JOIN events e ON e.id = ec.event_b_id
        LEFT JOIN locations l ON l.id = e.primary_location_id
        WHERE {where_sql}

        ORDER BY date_start, id
    """)

    result = db.execute(query, params)
    events = []
    for row in result:
        events.append({
            "id": row[0],
            "title": row[1],
            "title_ko": row[2],
            "date_start": row[3],
            "date_end": row[4],
            "importance": row[5],
            "latitude": row[6],
            "longitude": row[7],
            "location_name": row[8],
        })

    return {"person_id": person_id, "events": events, "total": len(events)}
