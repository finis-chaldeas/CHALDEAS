"""
Feed API - Unified importance-ranked feed of events + persons.

Returns interleaved events and persons sorted by importance for card-based display.
Designed for the Navigator's Feed tab.
"""
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from app.db.session import get_db

router = APIRouter()

# Cache whether qrank table exists
_qrank_exists: bool | None = None


def _has_qrank(db) -> bool:
    global _qrank_exists
    if _qrank_exists is None:
        _qrank_exists = db.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'qrank')"
        )).scalar()
    return _qrank_exists


def _format_year(year: Optional[int]) -> Optional[str]:
    """Format year for display."""
    if year is None:
        return None
    if year < 0:
        return f"{abs(year)} BCE"
    return f"{year} CE"


@router.get("")
def get_feed(
    db: Session = Depends(get_db),
    year_start: Optional[int] = Query(None, description="Start year (negative for BCE)"),
    year_end: Optional[int] = Query(None, description="End year"),
    lat_min: Optional[float] = Query(None, description="Viewport south bound"),
    lat_max: Optional[float] = Query(None, description="Viewport north bound"),
    lng_min: Optional[float] = Query(None, description="Viewport west bound"),
    lng_max: Optional[float] = Query(None, description="Viewport east bound"),
    limit: int = Query(30, ge=1, le=100, description="Total items to return"),
):
    """
    Unified feed: top events + top persons interleaved by importance.

    Returns card-ready items with context strings explaining why each item ranks highly.
    """
    event_limit = (limit + 1) // 2  # slightly more events than persons
    person_limit = limit // 2

    # --- Top Events ---
    events = _get_top_events(db, year_start, year_end, lat_min, lat_max, lng_min, lng_max, event_limit)

    # --- Top Persons ---
    persons = _get_top_persons(db, year_start, year_end, lat_min, lat_max, lng_min, lng_max, person_limit)

    # --- Interleave by importance ---
    items = _interleave(events, persons)

    # --- Totals (approximate, skip if no filters to avoid slow full scans) ---
    has_filters = any(v is not None for v in [year_start, year_end, lat_min, lat_max, lng_min, lng_max])
    if has_filters:
        events_total = _count_events(db, year_start, year_end, lat_min, lat_max, lng_min, lng_max)
        persons_total = _count_persons(db, year_start, year_end, lat_min, lat_max, lng_min, lng_max)
    else:
        events_total = len(events)
        persons_total = len(persons)

    return {
        "items": items,
        "events_total": events_total,
        "persons_total": persons_total,
    }


def _get_top_events(db, year_start, year_end, lat_min, lat_max, lng_min, lng_max, limit):
    """Get top events by importance for the given filters."""
    conditions = ["e.wikidata_id IS NOT NULL"]
    params = {"limit": limit}

    if year_start is not None:
        conditions.append("e.date_start >= :year_start")
        params["year_start"] = year_start
    if year_end is not None:
        conditions.append("(e.date_end <= :year_end OR (e.date_end IS NULL AND e.date_start <= :year_end))")
        params["year_end"] = year_end

    # Viewport filter via location join
    location_join = "LEFT JOIN locations l ON l.id = e.primary_location_id"
    if any(v is not None for v in [lat_min, lat_max, lng_min, lng_max]):
        location_join = "JOIN locations l ON l.id = e.primary_location_id"
        if lat_min is not None:
            conditions.append("l.latitude >= :lat_min")
            params["lat_min"] = lat_min
        if lat_max is not None:
            conditions.append("l.latitude <= :lat_max")
            params["lat_max"] = lat_max
        if lng_min is not None:
            conditions.append("l.longitude >= :lng_min")
            params["lng_min"] = lng_min
        if lng_max is not None:
            conditions.append("l.longitude <= :lng_max")
            params["lng_max"] = lng_max

    where = " AND ".join(conditions)

    has_qrank = _has_qrank(db)
    qrank_join = "LEFT JOIN qrank q ON q.wikidata_id = e.wikidata_id" if has_qrank else ""
    qrank_col = "COALESCE(q.score, 0)" if has_qrank else "0::bigint"

    rows = db.execute(text(f"""
        SELECT
            e.id, e.title, e.title_ko, e.date_start, e.date_end,
            e.importance, 0 as connection_count, ed.description,
            c.slug as category_slug, c.name as category_name,
            l.name as location_name, l.latitude, l.longitude,
            {qrank_col} as qrank_score,
            e.parent_event_id
        FROM events e
        LEFT JOIN event_details ed ON ed.event_id = e.id
        LEFT JOIN categories c ON c.id = e.category_id
        {location_join}
        {qrank_join}
        WHERE {where}
        ORDER BY e.importance DESC, {qrank_col} DESC
        LIMIT :limit
    """), params).fetchall()

    items = []
    for row in rows:
        # Get top 3 participants
        participants = db.execute(text("""
            SELECT p.name FROM event_persons ep
            JOIN persons p ON p.id = ep.person_id
            WHERE ep.event_id = :eid
            LIMIT 3
        """), {"eid": row[0]}).fetchall()
        participant_names = [p[0] for p in participants]

        # Participant total count
        p_total = db.execute(text(
            "SELECT COUNT(*) FROM event_persons WHERE event_id = :eid"
        ), {"eid": row[0]}).scalar()

        importance = row[5] or 3
        conn_count = row[6] or 0

        context = f"Importance {importance}/5"
        if conn_count > 5:
            context += f", {conn_count} connections"

        items.append({
            "type": "event",
            "id": row[0],
            "title": row[1],
            "title_ko": row[2],
            "date_start": row[3],
            "date_end": row[4],
            "date_display": _format_year(row[3]),
            "importance": importance,
            "connection_count": conn_count,
            "category": row[8],
            "category_name": row[9],
            "location_name": row[10],
            "latitude": float(row[11]) if row[11] else None,
            "longitude": float(row[12]) if row[12] else None,
            "description": (row[7][:200] + "...") if row[7] and len(row[7]) > 200 else row[7],
            "participants": participant_names,
            "participant_count": p_total,
            "context": context,
            "parent_event_id": row[14],
            "_sort_score": importance * 1000 + (row[13] or 0) / 1000000,  # for interleaving
        })

    return items


def _get_top_persons(db, year_start, year_end, lat_min, lat_max, lng_min, lng_max, limit):
    """Get top persons by QRank + connection_count for the given filters."""
    conditions = [
        "p.wikidata_id IS NOT NULL",
    ]
    params = {"limit": limit}

    # Time filter: person was alive during the period
    # Persons with NULL birth/death AND no floruit are excluded (not matched to any era)
    if year_start is not None or year_end is not None:
        time_parts = []
        # Case 1: has birth/death years
        alive_conds = []
        if year_start is not None:
            alive_conds.append("((p.death_year IS NULL AND p.birth_year + 80 >= :year_start) OR p.death_year >= :year_start)")
            params["year_start"] = year_start
        if year_end is not None:
            alive_conds.append("p.birth_year <= :year_end")
            params["year_end"] = year_end
        alive_conds.append("p.birth_year IS NOT NULL")
        time_parts.append(f"({' AND '.join(alive_conds)})")
        # Case 2: no birth/death but has floruit
        floruit_conds = ["p.birth_year IS NULL", "p.floruit_start IS NOT NULL"]
        if year_start is not None:
            floruit_conds.append("COALESCE(p.floruit_end, p.floruit_start + 40) >= :year_start")
        if year_end is not None:
            floruit_conds.append("p.floruit_start <= :year_end")
        time_parts.append(f"({' AND '.join(floruit_conds)})")
        conditions.append(f"({' OR '.join(time_parts)})")

    # Viewport filter via birthplace location
    location_join = "LEFT JOIN locations l ON l.id = p.birthplace_id"
    has_viewport = any(v is not None for v in [lat_min, lat_max, lng_min, lng_max])
    if has_viewport:
        viewport_conditions = []
        if lat_min is not None:
            viewport_conditions.append("el.latitude >= :lat_min")
            params["lat_min"] = lat_min
        if lat_max is not None:
            viewport_conditions.append("el.latitude <= :lat_max")
            params["lat_max"] = lat_max
        if lng_min is not None:
            viewport_conditions.append("el.longitude >= :lng_min")
            params["lng_min"] = lng_min
        if lng_max is not None:
            viewport_conditions.append("el.longitude <= :lng_max")
            params["lng_max"] = lng_max

        viewport_where = " AND ".join(viewport_conditions)
        conditions.append(f"""p.id IN (
            SELECT DISTINCT ep.person_id FROM event_persons ep
            JOIN events ev ON ev.id = ep.event_id
            JOIN locations el ON el.id = ev.primary_location_id
            WHERE {viewport_where}
        )""")

    where = " AND ".join(conditions)

    has_qrank = _has_qrank(db)
    qrank_join = "LEFT JOIN qrank q ON q.wikidata_id = p.wikidata_id" if has_qrank else ""
    qrank_col = "COALESCE(q.score, 0)" if has_qrank else "0::bigint"

    rows = db.execute(text(f"""
        SELECT
            p.id, p.name, p.name_ko, p.birth_year, p.death_year,
            p.role, pd.biography, 0 as connection_count,
            l.name as birthplace_name,
            {qrank_col} as qrank_score
        FROM persons p
        LEFT JOIN person_details pd ON pd.person_id = p.id
        {location_join}
        {qrank_join}
        WHERE {where}
        ORDER BY {qrank_col} DESC
        LIMIT :limit
    """), params).fetchall()

    # Batch-fetch event counts for result persons
    person_ids = [row[0] for row in rows]
    event_counts = {}
    if person_ids:
        ec_rows = db.execute(text("""
            SELECT person_id, COUNT(*) FROM event_persons
            WHERE person_id = ANY(:ids)
            GROUP BY person_id
        """), {"ids": person_ids}).fetchall()
        event_counts = {r[0]: r[1] for r in ec_rows}

    items = []
    for row in rows:
        event_count = event_counts.get(row[0], 0)
        conn_count = row[7] or 0

        context_parts = []
        if event_count > 0:
            context_parts.append(f"{event_count} events")
        if conn_count > 3:
            context_parts.append(f"{conn_count} connections")
        context = ", ".join(context_parts) if context_parts else "Notable figure"

        # Compute importance-like score for interleaving (1-5 scale)
        qrank_score = row[9] or 0  # index 9 = qrank_score (after removing event_count from query)
        if qrank_score > 1000000:
            importance = 5
        elif qrank_score > 100000:
            importance = 4
        elif qrank_score > 10000:
            importance = 3
        elif qrank_score > 1000:
            importance = 2
        else:
            importance = 1

        bio_snippet = None
        if row[6]:
            bio = row[6]
            bio_snippet = (bio[:150] + "...") if len(bio) > 150 else bio

        items.append({
            "type": "person",
            "id": row[0],
            "title": row[1],  # name as title for unified interface
            "name": row[1],
            "name_ko": row[2],
            "birth_year": row[3],
            "death_year": row[4],
            "date_start": row[3],  # for unified sorting
            "date_display": _format_lifespan(row[3], row[4]),
            "importance": importance,
            "role": row[5],
            "biography": bio_snippet,
            "event_count": event_count,
            "connection_count": conn_count,
            "birthplace_name": row[8],
            "context": context,
            "_sort_score": importance * 1000 + qrank_score / 1000000,
        })

    return items


def _format_lifespan(birth: Optional[int], death: Optional[int]) -> str:
    """Format person lifespan for display."""
    if birth is None and death is None:
        return "Unknown"

    def fmt(y):
        if y is None:
            return "?"
        return f"{abs(y)} BCE" if y < 0 else f"{y} CE"

    b = fmt(birth)
    d = fmt(death)

    # Simplify if same era
    if birth and death and (birth < 0) == (death < 0):
        era = "BCE" if birth < 0 else "CE"
        return f"{abs(birth)}-{abs(death)} {era}"

    return f"{b} - {d}"


def _interleave(events, persons):
    """Interleave events and persons by sort score."""
    combined = events + persons
    combined.sort(key=lambda x: x.get("_sort_score", 0), reverse=True)

    # Remove internal sort key
    for item in combined:
        item.pop("_sort_score", None)

    return combined


def _count_events(db, year_start, year_end, lat_min, lat_max, lng_min, lng_max):
    """Approximate total event count for the filters."""
    conditions = ["e.wikidata_id IS NOT NULL"]
    params = {}

    if year_start is not None:
        conditions.append("e.date_start >= :year_start")
        params["year_start"] = year_start
    if year_end is not None:
        conditions.append("(e.date_end <= :year_end OR (e.date_end IS NULL AND e.date_start <= :year_end))")
        params["year_end"] = year_end

    join_clause = ""
    if any(v is not None for v in [lat_min, lat_max, lng_min, lng_max]):
        join_clause = "JOIN locations l ON l.id = e.primary_location_id"
        if lat_min is not None:
            conditions.append("l.latitude >= :lat_min")
            params["lat_min"] = lat_min
        if lat_max is not None:
            conditions.append("l.latitude <= :lat_max")
            params["lat_max"] = lat_max
        if lng_min is not None:
            conditions.append("l.longitude >= :lng_min")
            params["lng_min"] = lng_min
        if lng_max is not None:
            conditions.append("l.longitude <= :lng_max")
            params["lng_max"] = lng_max

    where = " AND ".join(conditions)
    return db.execute(text(f"SELECT COUNT(*) FROM events e {join_clause} WHERE {where}"), params).scalar()


def _count_persons(db, year_start, year_end, lat_min, lat_max, lng_min, lng_max):
    """Approximate total person count for the filters."""
    conditions = ["p.wikidata_id IS NOT NULL"]
    params = {}

    if year_start is not None or year_end is not None:
        time_parts = []
        alive_conds = []
        if year_start is not None:
            alive_conds.append("((p.death_year IS NULL AND p.birth_year + 80 >= :year_start) OR p.death_year >= :year_start)")
            params["year_start"] = year_start
        if year_end is not None:
            alive_conds.append("p.birth_year <= :year_end")
            params["year_end"] = year_end
        alive_conds.append("p.birth_year IS NOT NULL")
        time_parts.append(f"({' AND '.join(alive_conds)})")
        floruit_conds = ["p.birth_year IS NULL", "p.floruit_start IS NOT NULL"]
        if year_start is not None:
            floruit_conds.append("COALESCE(p.floruit_end, p.floruit_start + 40) >= :year_start")
        if year_end is not None:
            floruit_conds.append("p.floruit_start <= :year_end")
        time_parts.append(f"({' AND '.join(floruit_conds)})")
        conditions.append(f"({' OR '.join(time_parts)})")

    where = " AND ".join(conditions)
    return db.execute(text(f"SELECT COUNT(*) FROM persons p WHERE {where}"), params).scalar()
