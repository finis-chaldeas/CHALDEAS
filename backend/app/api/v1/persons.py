"""
Persons API endpoints.

Provides CRUD operations for historical figures.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from sqlalchemy import text as sa_text

from app.db.session import get_db
from app.schemas.person import Person, PersonList, PersonDetail, PersonRelation, PersonRelationList, PersonFlow
from app.schemas.source import PersonSourceList, SourceWithMentions, MentionContext
from app.services import person_service, source_service

router = APIRouter()


@router.get("", response_model=PersonList)
async def list_persons(
    year_start: Optional[int] = Query(None, description="Active from year"),
    year_end: Optional[int] = Query(None, description="Active until year"),
    lat_min: Optional[float] = Query(None, description="Viewport south bound (birthplace)"),
    lat_max: Optional[float] = Query(None, description="Viewport north bound (birthplace)"),
    lng_min: Optional[float] = Query(None, description="Viewport west bound (birthplace)"),
    lng_max: Optional[float] = Query(None, description="Viewport east bound (birthplace)"),
    domain: Optional[str] = Query(None, description="Filter by domain: science, philosophy, military, etc."),
    sort_by: Optional[str] = Query(None, description="Sort by: 'birth' (default), 'importance'"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List historical figures with optional filtering."""
    persons, total = person_service.get_persons(
        db,
        year_start=year_start,
        year_end=year_end,
        limit=limit,
        offset=offset,
        lat_min=lat_min,
        lat_max=lat_max,
        lng_min=lng_min,
        lng_max=lng_max,
        sort_by=sort_by,
        domain=domain,
    )
    return PersonList(items=persons, total=total)


@router.get("/network")
async def get_person_network(
    year_start: Optional[int] = Query(None, description="Active from year"),
    year_end: Optional[int] = Query(None, description="Active until year"),
    lat_min: Optional[float] = Query(None, description="Viewport south bound"),
    lat_max: Optional[float] = Query(None, description="Viewport north bound"),
    lng_min: Optional[float] = Query(None, description="Viewport west bound"),
    lng_max: Optional[float] = Query(None, description="Viewport east bound"),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Get persons in viewport with their inter-relationships from the links table.

    Returns persons[] + relations[] (from_id, to_id, category).
    """
    persons_list, total = person_service.get_persons(
        db,
        year_start=year_start,
        year_end=year_end,
        limit=limit,
        offset=0,
        lat_min=lat_min,
        lat_max=lat_max,
        lng_min=lng_min,
        lng_max=lng_max,
        sort_by='connections',
    )

    if not persons_list:
        return {"persons": [], "relations": [], "total": 0}

    person_ids = [p.id for p in persons_list]
    persons_out = []
    for p in persons_list:
        persons_out.append({
            "id": p.id,
            "name": p.name,
            "name_ko": getattr(p, 'name_ko', None),
            "birth_year": p.birth_year,
            "death_year": p.death_year,
            "role": getattr(p, 'role', None),
        })

    # Get links between these persons
    result = db.execute(sa_text("""
        SELECT from_id, to_id, category
        FROM links
        WHERE from_type = 'person' AND to_type = 'person'
          AND from_id = ANY(:person_ids)
          AND to_id = ANY(:person_ids)
        ORDER BY category, from_id
    """), {"person_ids": person_ids})

    relations = []
    for row in result:
        relations.append({
            "from_id": row[0],
            "to_id": row[1],
            "category": row[2],
        })

    return {
        "persons": persons_out,
        "relations": relations,
        "total": total,
    }


@router.get("/{person_id}", response_model=PersonDetail)
async def get_person(
    person_id: int,
    db: Session = Depends(get_db),
):
    """Get detailed information about a historical figure."""
    person = person_service.get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


@router.get("/{person_id}/narrative")
async def get_person_narrative(
    person_id: int,
    db: Session = Depends(get_db),
):
    """Get LLM-generated narrative for a person from entity_narratives."""
    person = person_service.get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    row = db.execute(sa_text('''
        SELECT narrative, significance, causes, consequences, model_used, source_url
        FROM entity_narratives
        WHERE entity_type = 'person' AND entity_id = :pid
        LIMIT 1
    '''), {"pid": person_id}).fetchone()

    if not row:
        return {"person_id": person_id, "has_narrative": False}

    return {
        "person_id": person_id,
        "has_narrative": True,
        "narrative": row[0],
        "significance": row[1],
        "causes": row[2],
        "consequences": row[3],
        "model_used": row[4],
        "source_url": row[5],
    }


@router.get("/{person_id}/flow", response_model=PersonFlow)
async def get_person_flow(
    person_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a person's event flow in chronological order.

    Returns birth → events → death as a timeline of locations.
    All persons have a flow, even with 0 events (birth→death only).
    """
    flow_data = person_service.get_person_flow(db, person_id)
    if not flow_data:
        raise HTTPException(status_code=404, detail="Person not found")
    return flow_data


@router.get("/{person_id}/events")
async def get_person_events(
    person_id: int,
    db: Session = Depends(get_db),
):
    """Get events associated with a person."""
    events = person_service.get_person_events(db, person_id)
    return {"person_id": person_id, "events": events}


@router.get("/{person_id}/relations", response_model=PersonRelationList)
async def get_person_relations(
    person_id: int,
    limit: int = Query(20, ge=1, le=100, description="Max relations to return"),
    min_strength: float = Query(0, ge=0, description="Minimum strength threshold"),
    db: Session = Depends(get_db),
):
    """Get related persons with relationship strength."""
    relations = person_service.get_related_persons(
        db,
        person_id=person_id,
        limit=limit,
        min_strength=min_strength,
    )
    return PersonRelationList(
        person_id=person_id,
        relations=[PersonRelation(**r) for r in relations],
        total=len(relations),
    )


@router.get("/{person_id}/sources", response_model=PersonSourceList)
async def get_person_sources(
    person_id: int,
    limit: int = Query(20, ge=1, le=100, description="Max sources to return"),
    include_contexts: bool = Query(True, description="Include mention contexts"),
    max_contexts: int = Query(3, ge=1, le=10, description="Max contexts per source"),
    db: Session = Depends(get_db),
):
    """Get sources (books, documents) that mention this person."""
    person = person_service.get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    sources, total = source_service.get_person_sources(
        db,
        person_id=person_id,
        limit=limit,
        include_contexts=include_contexts,
        max_contexts=max_contexts,
    )

    return PersonSourceList(
        person_id=person_id,
        sources=[
            SourceWithMentions(
                id=s["id"],
                name=s["name"],
                title=s.get("title"),
                type=s["type"],
                author=s.get("author"),
                mention_count=s["mention_count"],
                person_count=s.get("person_count", 0),
                mentions=[MentionContext(**m) for m in s.get("mentions", [])]
            )
            for s in sources
        ],
        total=total
    )


@router.get("/{person_id}/wikipedia")
async def get_person_wikipedia(
    person_id: int,
    db: Session = Depends(get_db),
):
    """Get Wikipedia content for a person via person_sources table."""
    from sqlalchemy import text

    result = db.execute(text("""
        SELECT s.id, s.title, s.url,
               LEFT(s.content_raw, 3000) as content_excerpt,
               LENGTH(s.content_raw) as full_length
        FROM person_sources ps
        JOIN sources s ON s.id = ps.source_id
        WHERE ps.person_id = :person_id
          AND s.source_type = 'wikipedia'
        LIMIT 1
    """), {"person_id": person_id})

    row = result.fetchone()
    if not row:
        return {"person_id": person_id, "has_wikipedia": False}

    return {
        "person_id": person_id,
        "has_wikipedia": True,
        "source_id": row[0],
        "title": row[1],
        "url": row[2],
        "content_excerpt": row[3],
        "full_length": row[4],
    }


@router.get("/{person_id}/properties")
async def get_person_properties(
    person_id: int,
    db: Session = Depends(get_db),
):
    """Get key Wikidata properties for a person."""
    from sqlalchemy import text

    person = person_service.get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    KEY_PROPERTIES = ['P106', 'P27', 'P140', 'P69', 'P166', 'P39', 'P101', 'P108', 'P463']

    result = db.execute(text("""
        SELECT property, property_name, value_string, value_qid
        FROM entity_properties
        WHERE entity_type = 'person' AND entity_id = :person_id
          AND property = ANY(:props)
        ORDER BY property, id
    """), {"person_id": person_id, "props": KEY_PROPERTIES})

    grouped: dict = {}
    for row in result:
        prop = row[0]
        if prop not in grouped:
            grouped[prop] = {
                "property": prop,
                "label": row[1] or prop,
                "values": []
            }
        value = row[2] or row[3] or ""
        if value and value not in grouped[prop]["values"]:
            grouped[prop]["values"].append(value)

    return {
        "person_id": person_id,
        "properties": list(grouped.values()),
    }


@router.get("/{person_id}/histories")
async def get_person_histories(
    person_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get histories that reference this person."""
    rows = db.execute(sa_text("""
        SELECT h.id, h.title, h.title_ko, h.summary,
               h.era_start, h.era_end, h.category, h.author_type, h.importance,
               he.role, h.created_at
        FROM history_entities he
        JOIN histories h ON h.id = he.history_id
        WHERE he.entity_type = 'person' AND he.entity_id = :pid
          AND h.status != 'archived'
        ORDER BY h.importance DESC, h.created_at DESC
        LIMIT :lim
    """), {"pid": person_id, "lim": limit})

    items = []
    for row in rows:
        items.append({
            "id": row[0],
            "title": row[1],
            "title_ko": row[2],
            "summary": row[3],
            "era_start": row[4],
            "era_end": row[5],
            "category": row[6],
            "author_type": row[7],
            "importance": row[8],
            "role_in_history": row[9],
            "created_at": row[10].isoformat() if row[10] else None,
        })

    return {"person_id": person_id, "histories": items, "total": len(items)}
