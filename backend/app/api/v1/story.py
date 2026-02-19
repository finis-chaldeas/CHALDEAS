"""
Story API - Person/Place/Arc Story for immersive historical exploration.

인물/장소/아크의 스토리를 지도 위 노드로 시각화하기 위한 API.
다중 소스 기반: event_connections → event_persons → entity_properties (fallback chain)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from pydantic import BaseModel

from app.db.session import get_db

router = APIRouter()


# ============== Pydantic Models ==============

class StoryLocation(BaseModel):
    """위치 정보 (지도 표시용)"""
    name: str
    name_ko: Optional[str] = None
    lat: float
    lng: float


class StoryNode(BaseModel):
    """스토리 노드 (지도 위 한 지점)"""
    order: int
    event_id: Optional[int] = None  # None for synthetic nodes (birth/death)
    title: str
    title_ko: Optional[str] = None
    year: Optional[int] = None
    year_end: Optional[int] = None
    location: Optional[StoryLocation] = None
    node_type: str = "normal"  # birth, major, battle, political, death, normal
    description: Optional[str] = None
    narrative: Optional[str] = None  # For synthetic nodes


class StoryPerson(BaseModel):
    """인물 정보"""
    id: int
    name: str
    name_ko: Optional[str] = None
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    role: Optional[str] = None


class MapView(BaseModel):
    """지도 뷰 설정"""
    center_lat: float
    center_lng: float
    zoom: int = 6


class PersonStoryResponse(BaseModel):
    """Person Story 응답"""
    person: StoryPerson
    nodes: List[StoryNode]
    total_nodes: int
    map_view: MapView


# ============== Helper Functions ==============

def determine_node_type(event_title: str, year: int, birth_year: int, death_year: int) -> str:
    """이벤트 제목과 연도로 노드 타입 결정"""
    title_lower = event_title.lower() if event_title else ""

    # Birth/Death check by year
    if birth_year and year == birth_year:
        return "birth"
    if death_year and year == death_year:
        return "death"

    # Keyword-based detection
    if any(word in title_lower for word in ["birth", "born", "출생", "탄생"]):
        return "birth"
    if any(word in title_lower for word in ["death", "died", "execution", "화형", "사망", "처형", "순교"]):
        return "death"
    if any(word in title_lower for word in ["battle", "siege", "war", "전투", "포위", "공방"]):
        return "battle"
    if any(word in title_lower for word in ["coronation", "treaty", "대관", "조약", "즉위"]):
        return "political"
    if any(word in title_lower for word in ["victory", "liberation", "해방", "승리"]):
        return "major"

    return "normal"


def calculate_map_view(nodes: List[dict]) -> MapView:
    """노드들의 좌표로 적절한 지도 뷰 계산"""
    if not nodes:
        return MapView(center_lat=48.0, center_lng=2.0, zoom=5)

    lats = [n["lat"] for n in nodes if n.get("lat")]
    lngs = [n["lng"] for n in nodes if n.get("lng")]

    if not lats or not lngs:
        return MapView(center_lat=48.0, center_lng=2.0, zoom=5)

    center_lat = sum(lats) / len(lats)
    center_lng = sum(lngs) / len(lngs)

    # Calculate zoom based on spread
    lat_spread = max(lats) - min(lats)
    lng_spread = max(lngs) - min(lngs)
    spread = max(lat_spread, lng_spread)

    if spread < 2:
        zoom = 8
    elif spread < 5:
        zoom = 7
    elif spread < 10:
        zoom = 6
    elif spread < 20:
        zoom = 5
    else:
        zoom = 4

    return MapView(center_lat=center_lat, center_lng=center_lng, zoom=zoom)


def _fetch_from_event_connections(db: Session, person_id: int, min_strength: float) -> list:
    """Source 1: event_connections 테이블에서 이벤트 조회"""
    result = db.execute(text("""
        WITH person_events AS (
            SELECT DISTINCT
                e.id as event_id,
                e.title,
                e.title_ko,
                ed.description,
                e.date_start as year,
                e.date_end as year_end,
                l.name as loc_name,
                l.name_ko as loc_name_ko,
                l.latitude as lat,
                l.longitude as lng
            FROM event_connections ec
            JOIN events e ON ec.event_a_id = e.id
            LEFT JOIN event_details ed ON ed.event_id = e.id
            LEFT JOIN locations l ON e.primary_location_id = l.id
            WHERE ec.layer_type = 'person'
              AND ec.layer_entity_id = :person_id
              AND ec.strength_score >= :min_strength

            UNION

            SELECT DISTINCT
                e.id as event_id,
                e.title,
                e.title_ko,
                ed.description,
                e.date_start as year,
                e.date_end as year_end,
                l.name as loc_name,
                l.name_ko as loc_name_ko,
                l.latitude as lat,
                l.longitude as lng
            FROM event_connections ec
            JOIN events e ON ec.event_b_id = e.id
            LEFT JOIN event_details ed ON ed.event_id = e.id
            LEFT JOIN locations l ON e.primary_location_id = l.id
            WHERE ec.layer_type = 'person'
              AND ec.layer_entity_id = :person_id
              AND ec.strength_score >= :min_strength
        )
        SELECT DISTINCT event_id, title, title_ko, description, year, year_end,
                        loc_name, loc_name_ko, lat, lng
        FROM person_events
        WHERE year IS NOT NULL
        ORDER BY year
    """), {"person_id": person_id, "min_strength": min_strength})

    return [dict(row._mapping) for row in result]


def _fetch_from_event_persons(db: Session, person_id: int) -> list:
    """Source 2 (fallback): event_persons 테이블에서 직접 이벤트 참여 조회"""
    result = db.execute(text("""
        SELECT DISTINCT
            e.id as event_id,
            e.title,
            e.title_ko,
            ed.description,
            e.date_start as year,
            e.date_end as year_end,
            l.name as loc_name,
            l.name_ko as loc_name_ko,
            l.latitude as lat,
            l.longitude as lng
        FROM event_persons ep
        JOIN events e ON ep.event_id = e.id
        LEFT JOIN event_details ed ON ed.event_id = e.id
        LEFT JOIN locations l ON e.primary_location_id = l.id
        WHERE ep.person_id = :person_id AND e.date_start IS NOT NULL
        ORDER BY e.date_start
        LIMIT 50
    """), {"person_id": person_id})

    return [dict(row._mapping) for row in result]


def _build_birth_node(db: Session, person: StoryPerson) -> Optional[StoryNode]:
    """합성 출생 노드 생성 (entity_properties P19 또는 person.birthplace_id)"""
    if not person.birth_year:
        return None

    location = None

    # Try entity_properties P19 first
    loc_result = db.execute(text("""
        SELECT l.name, l.name_ko, l.latitude, l.longitude
        FROM entity_properties ep
        JOIN locations l ON l.wikidata_id = ep.value_qid
        WHERE ep.entity_type = 'person' AND ep.entity_id = :pid AND ep.property = 'P19'
        LIMIT 1
    """), {"pid": person.id}).fetchone()

    if loc_result and loc_result[2] and loc_result[3]:
        location = StoryLocation(
            name=loc_result[0] or "Unknown",
            name_ko=loc_result[1],
            lat=float(loc_result[2]),
            lng=float(loc_result[3])
        )
    else:
        # Fallback: person.birthplace_id
        bp_result = db.execute(text("""
            SELECT l.name, l.name_ko, l.latitude, l.longitude
            FROM persons p
            JOIN locations l ON p.birthplace_id = l.id
            WHERE p.id = :pid
        """), {"pid": person.id}).fetchone()

        if bp_result and bp_result[2] and bp_result[3]:
            location = StoryLocation(
                name=bp_result[0] or "Unknown",
                name_ko=bp_result[1],
                lat=float(bp_result[2]),
                lng=float(bp_result[3])
            )

    loc_name = location.name if location else ""
    narrative = f"Born in {person.birth_year}"
    if person.birth_year < 0:
        narrative = f"Born in {abs(person.birth_year)} BCE"
    if loc_name:
        narrative += f" in {loc_name}"

    return StoryNode(
        order=0,
        event_id=None,
        title=f"Birth of {person.name}",
        year=person.birth_year,
        location=location,
        node_type="birth",
        narrative=narrative
    )


def _build_death_node(db: Session, person: StoryPerson) -> Optional[StoryNode]:
    """합성 사망 노드 생성 (entity_properties P20 또는 person.deathplace_id)"""
    if not person.death_year:
        return None

    location = None

    # Try entity_properties P20 first
    loc_result = db.execute(text("""
        SELECT l.name, l.name_ko, l.latitude, l.longitude
        FROM entity_properties ep
        JOIN locations l ON l.wikidata_id = ep.value_qid
        WHERE ep.entity_type = 'person' AND ep.entity_id = :pid AND ep.property = 'P20'
        LIMIT 1
    """), {"pid": person.id}).fetchone()

    if loc_result and loc_result[2] and loc_result[3]:
        location = StoryLocation(
            name=loc_result[0] or "Unknown",
            name_ko=loc_result[1],
            lat=float(loc_result[2]),
            lng=float(loc_result[3])
        )
    else:
        # Fallback: person.deathplace_id
        dp_result = db.execute(text("""
            SELECT l.name, l.name_ko, l.latitude, l.longitude
            FROM persons p
            JOIN locations l ON p.deathplace_id = l.id
            WHERE p.id = :pid
        """), {"pid": person.id}).fetchone()

        if dp_result and dp_result[2] and dp_result[3]:
            location = StoryLocation(
                name=dp_result[0] or "Unknown",
                name_ko=dp_result[1],
                lat=float(dp_result[2]),
                lng=float(dp_result[3])
            )

    loc_name = location.name if location else ""
    narrative = f"Died in {person.death_year}"
    if person.death_year < 0:
        narrative = f"Died in {abs(person.death_year)} BCE"
    if loc_name:
        narrative += f" in {loc_name}"

    return StoryNode(
        order=0,
        event_id=None,
        title=f"Death of {person.name}",
        year=person.death_year,
        location=location,
        node_type="death",
        narrative=narrative
    )


def _merge_nodes(existing: list, new_rows: list, seen_event_ids: set) -> list:
    """event_id 기준으로 중복 없이 병합"""
    for row in new_rows:
        eid = row["event_id"]
        if eid not in seen_event_ids:
            seen_event_ids.add(eid)
            existing.append(row)
    return existing


# ============== API Endpoints ==============

@router.get("/person/{person_id}", response_model=PersonStoryResponse)
async def get_person_story(
    person_id: int,
    min_strength: float = Query(0, description="Minimum connection strength"),
    db: Session = Depends(get_db),
):
    """
    Get Person Story - 인물의 생애를 지도 노드로 반환.

    다중 소스 기반:
    1. event_connections (기존)
    2. event_persons (fallback - 부족할 때)
    3. 합성 birth/death 노드 (entity_properties + person fields)
    """
    # 1. Get person info
    person_result = db.execute(text("""
        SELECT id, name, name_ko, birth_year, death_year, role
        FROM persons
        WHERE id = :person_id
    """), {"person_id": person_id})

    person_row = person_result.fetchone()
    if not person_row:
        raise HTTPException(status_code=404, detail="Person not found")

    person = StoryPerson(
        id=person_row[0],
        name=person_row[1],
        name_ko=person_row[2],
        birth_year=person_row[3],
        death_year=person_row[4],
        role=person_row[5]
    )

    # 2. Source 1: event_connections
    ec_rows = _fetch_from_event_connections(db, person_id, min_strength)
    seen_event_ids = {r["event_id"] for r in ec_rows}
    all_rows = list(ec_rows)

    # 3. Source 2 fallback: event_persons (if event_connections insufficient)
    if len(all_rows) < 3:
        ep_rows = _fetch_from_event_persons(db, person_id)
        all_rows = _merge_nodes(all_rows, ep_rows, seen_event_ids)

    # 4. Build event-based nodes
    nodes = []
    node_locs = []

    for row in all_rows:
        location = None
        if row["lat"] and row["lng"]:
            location = StoryLocation(
                name=row["loc_name"] or "Unknown",
                name_ko=row["loc_name_ko"],
                lat=float(row["lat"]),
                lng=float(row["lng"])
            )
            node_locs.append({"lat": float(row["lat"]), "lng": float(row["lng"])})

        node_type = determine_node_type(
            row["title"],
            row["year"],
            person.birth_year,
            person.death_year
        )

        nodes.append(StoryNode(
            order=0,
            event_id=row["event_id"],
            title=row["title"],
            title_ko=row["title_ko"],
            year=row["year"],
            year_end=row["year_end"],
            location=location,
            node_type=node_type,
            description=row["description"][:200] if row["description"] else None
        ))

    # 5. Synthetic birth/death nodes
    birth_node = _build_birth_node(db, person)
    death_node = _build_death_node(db, person)

    # Inject if no existing birth/death node at the same year
    existing_years = {n.year for n in nodes if n.year}
    has_birth_node = any(n.node_type == "birth" for n in nodes)
    has_death_node = any(n.node_type == "death" for n in nodes)

    if birth_node and not has_birth_node:
        nodes.append(birth_node)
        if birth_node.location:
            node_locs.append({"lat": birth_node.location.lat, "lng": birth_node.location.lng})

    if death_node and not has_death_node:
        nodes.append(death_node)
        if death_node.location:
            node_locs.append({"lat": death_node.location.lat, "lng": death_node.location.lng})

    # 6. Sort by year and assign order
    nodes.sort(key=lambda n: (n.year or 0, 0 if n.node_type == "birth" else 1))
    for i, n in enumerate(nodes):
        n.order = i

    # 7. Calculate map view
    map_view = calculate_map_view(node_locs)

    return PersonStoryResponse(
        person=person,
        nodes=nodes,
        total_nodes=len(nodes),
        map_view=map_view
    )


@router.get("/person/{person_id}/check")
async def check_person_story_available(
    person_id: int,
    db: Session = Depends(get_db),
):
    """
    Check if Person Story is available.

    다중 소스 확인: event_connections + event_persons + person birth/death 정보.
    """
    # Check person exists
    person = db.execute(text("""
        SELECT id, name, birth_year, death_year FROM persons WHERE id = :person_id
    """), {"person_id": person_id}).fetchone()

    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    # Count from event_connections
    ec_count = db.execute(text("""
        SELECT COUNT(DISTINCT CASE
            WHEN event_a_id IS NOT NULL THEN event_a_id
            ELSE event_b_id
        END)
        FROM event_connections
        WHERE layer_type = 'person' AND layer_entity_id = :person_id
    """), {"person_id": person_id}).scalar() or 0

    # Count from event_persons
    ep_count = db.execute(text("""
        SELECT COUNT(DISTINCT event_id)
        FROM event_persons
        WHERE person_id = :person_id
    """), {"person_id": person_id}).scalar() or 0

    # Synthetic nodes available?
    has_birth = person[2] is not None  # birth_year
    has_death = person[3] is not None  # death_year
    synthetic_count = (1 if has_birth else 0) + (1 if has_death else 0)

    total = ec_count + ep_count + synthetic_count

    return {
        "person_id": person_id,
        "person_name": person[1],
        "has_story": total > 0,
        "event_count": total,
        "sources": {
            "event_connections": ec_count,
            "event_persons": ep_count,
            "synthetic": synthetic_count
        }
    }
