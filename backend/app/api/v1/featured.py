"""
Featured Persons API - Curated person recommendations for the landing page.

event_connections 기반으로 실제 Story가 있는 인물을 importance 점수로 랭킹.
"""
import json
from pathlib import Path
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from pydantic import BaseModel

from app.db.session import get_db

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent

router = APIRouter()

# Era boundaries
ERA_RANGES = {
    "ancient": (-3000, 476),
    "medieval": (476, 1453),
    "early_modern": (1453, 1789),
    "modern": (1789, 2100),
}


class FeaturedPerson(BaseModel):
    id: int
    name: str
    name_ko: Optional[str] = None
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    role: Optional[str] = None
    biography: Optional[str] = None
    image_url: Optional[str] = None
    importance: int = 0


class FeaturedPersonsResponse(BaseModel):
    items: List[FeaturedPerson]
    total: int
    era: Optional[str] = None


@router.get("/persons", response_model=FeaturedPersonsResponse)
async def get_featured_persons(
    era: Optional[str] = Query(None, description="Era filter: ancient, medieval, early_modern, modern"),
    limit: int = Query(12, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Get featured persons with the richest data.

    Uses event_connections to find persons who have Story data,
    ranked by connection count and data richness.
    """
    era_filter = ""
    params: dict = {"limit": limit, "offset": offset}

    if era and era in ERA_RANGES:
        year_start, year_end = ERA_RANGES[era]
        era_filter = "AND p.birth_year >= :year_start AND p.birth_year < :year_end"
        params["year_start"] = year_start
        params["year_end"] = year_end

    # Use event_connections to find persons with actual story data
    result = db.execute(text(f"""
        SELECT
            p.id, p.name, p.name_ko, p.birth_year, p.death_year,
            p.role, LEFT(pd.biography, 200) as biography, pd.image_url,
            ec.conn_count as importance
        FROM persons p
        LEFT JOIN person_details pd ON pd.person_id = p.id
        JOIN (
            SELECT layer_entity_id as person_id, COUNT(*) as conn_count
            FROM event_connections
            WHERE layer_type = 'person'
            GROUP BY layer_entity_id
        ) ec ON ec.person_id = p.id
        WHERE p.birth_year IS NOT NULL
          {era_filter}
        ORDER BY ec.conn_count DESC, p.birth_year
        LIMIT :limit OFFSET :offset
    """), params)

    items = [
        FeaturedPerson(
            id=row[0],
            name=row[1],
            name_ko=row[2],
            birth_year=row[3],
            death_year=row[4],
            role=row[5],
            biography=row[6],
            image_url=row[7],
            importance=row[8] or 0,
        )
        for row in result
    ]

    # Get total count
    count_result = db.execute(text(f"""
        SELECT COUNT(*)
        FROM persons p
        JOIN (
            SELECT DISTINCT layer_entity_id as person_id
            FROM event_connections
            WHERE layer_type = 'person'
        ) ec ON ec.person_id = p.id
        WHERE p.birth_year IS NOT NULL
          {era_filter}
    """), params)
    total = count_result.scalar() or 0

    return FeaturedPersonsResponse(items=items, total=total, era=era)


@router.get("/random", response_model=FeaturedPerson)
async def get_random_person(
    db: Session = Depends(get_db),
):
    """Get a random person who has event_connections (story data)."""
    result = db.execute(text("""
        SELECT p.id, p.name, p.name_ko, p.birth_year, p.death_year,
               p.role, LEFT(pd.biography, 200) as biography, pd.image_url
        FROM persons p
        LEFT JOIN person_details pd ON pd.person_id = p.id
        WHERE p.id IN (
            SELECT DISTINCT layer_entity_id
            FROM event_connections
            WHERE layer_type = 'person'
        )
        AND p.birth_year IS NOT NULL
        ORDER BY RANDOM()
        LIMIT 1
    """))

    row = result.fetchone()
    if not row:
        return FeaturedPerson(id=0, name="No persons available")

    return FeaturedPerson(
        id=row[0],
        name=row[1],
        name_ko=row[2],
        birth_year=row[3],
        death_year=row[4],
        role=row[5],
        biography=row[6],
        image_url=row[7],
    )


class FeaturedServant(BaseModel):
    fgo_name: str
    fgo_class: Optional[str] = None
    rarity: Optional[int] = None
    origin: Optional[str] = None
    person_id: Optional[int] = None
    person_name: Optional[str] = None


@router.get("/servants", response_model=list[FeaturedServant])
async def get_featured_servants(limit: int = Query(6, ge=1, le=20)):
    """Featured FGO servants for the landing page."""
    mapping_path = PROJECT_ROOT / "data/raw/atlas_academy/servant_db_mapping.json"
    fgo_path = PROJECT_ROOT / "data/raw/atlas_academy/fgo_historical_figures.json"

    if not mapping_path.exists() or not fgo_path.exists():
        return []

    with open(mapping_path, encoding='utf-8') as f:
        mapping = json.load(f)
    with open(fgo_path, encoding='utf-8') as f:
        fgo_data = json.load(f)

    fgo_lookup = {s['fgo_name']: s for s in fgo_data}

    # Pick mapped servants with highest rarity
    results = []
    for m in mapping.get('mapped', []):
        fgo_info = fgo_lookup.get(m['fgo_name'], {})
        results.append(FeaturedServant(
            fgo_name=m['fgo_name'],
            fgo_class=fgo_info.get('fgo_class'),
            rarity=fgo_info.get('rarity'),
            origin=fgo_info.get('origin'),
            person_id=m.get('person_id'),
            person_name=m.get('person_name'),
        ))

    # Sort by rarity desc, take top N
    results.sort(key=lambda x: -(x.rarity or 0))
    return results[:limit]
