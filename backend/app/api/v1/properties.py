"""
Entity Properties API - Expose Wikidata properties for persons, events, locations.

entity_properties 테이블에서 속성 조회.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from pydantic import BaseModel

from app.db.session import get_db

router = APIRouter()


class EntityProperty(BaseModel):
    id: int
    property: str
    property_name: Optional[str] = None
    value_string: Optional[str] = None
    value_qid: Optional[str] = None
    value_year: Optional[int] = None


class EntityPropertiesResponse(BaseModel):
    entity_type: str
    entity_id: int
    properties: List[EntityProperty]
    total: int


@router.get("/{entity_type}/{entity_id}", response_model=EntityPropertiesResponse)
async def get_entity_properties(
    entity_type: str,
    entity_id: int,
    properties: Optional[str] = Query(None, description="Comma-separated property IDs to filter (e.g. P106,P27,P140)"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Get Wikidata properties for an entity.

    Supports filtering by specific property IDs.
    """
    if entity_type not in ("person", "event", "location"):
        raise HTTPException(status_code=400, detail="entity_type must be person, event, or location")

    params = {"entity_type": entity_type, "entity_id": entity_id, "limit": limit}

    prop_filter = ""
    if properties:
        prop_list = [p.strip() for p in properties.split(",") if p.strip()]
        if prop_list:
            prop_filter = "AND ep.property = ANY(:props)"
            params["props"] = prop_list

    result = db.execute(text(f"""
        SELECT ep.id, ep.property, ep.property_name, ep.value_string, ep.value_qid, ep.value_year
        FROM entity_properties ep
        WHERE ep.entity_type = :entity_type AND ep.entity_id = :entity_id
        {prop_filter}
        ORDER BY ep.property, ep.id
        LIMIT :limit
    """), params)

    props = [
        EntityProperty(
            id=row[0],
            property=row[1],
            property_name=row[2],
            value_string=row[3],
            value_qid=row[4],
            value_year=row[5],
        )
        for row in result
    ]

    return EntityPropertiesResponse(
        entity_type=entity_type,
        entity_id=entity_id,
        properties=props,
        total=len(props),
    )
