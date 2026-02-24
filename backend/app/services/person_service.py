"""Person service - CRUD operations for persons."""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, not_, or_
from typing import Optional

from app.models.person import Person
from app.models.location import Location

# Noise patterns to exclude (honorifics without real names)
NOISE_PATTERNS = [
    "Mrs.%", "Mrs %", "Miss %", "Mr. %", "Mr %",
    "Sig.%", "Sig %", "Junr%", "Senr%",
    "Madame %", "Mme.%", "Mlle.%",
]


def get_persons(
    db: Session,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    include_noise: bool = False,
    lat_min: Optional[float] = None,
    lat_max: Optional[float] = None,
    lng_min: Optional[float] = None,
    lng_max: Optional[float] = None,
    sort_by: Optional[str] = None,
    domain: Optional[str] = None,
) -> tuple[list[Person], int]:
    """Get persons with optional filtering."""
    query = db.query(Person)

    # Only persons with wikidata_id
    query = query.filter(Person.wikidata_id.isnot(None))

    # Exclude noise data by default
    if not include_noise:
        noise_filters = [Person.name.ilike(p) for p in NOISE_PATTERNS]
        query = query.filter(not_(or_(*noise_filters)))

    # Domain filter
    if domain is not None:
        query = query.filter(Person.domain == domain)

    if year_start is not None:
        query = query.filter(Person.death_year >= year_start)
    if year_end is not None:
        query = query.filter(Person.birth_year <= year_end)

    # Viewport bounds filter (birthplace coordinates)
    if lat_min is not None or lat_max is not None or lng_min is not None or lng_max is not None:
        query = query.join(Location, Person.birthplace_id == Location.id)
        if lat_min is not None:
            query = query.filter(Location.latitude >= lat_min)
        if lat_max is not None:
            query = query.filter(Location.latitude <= lat_max)
        if lng_min is not None:
            query = query.filter(Location.longitude >= lng_min)
        if lng_max is not None:
            query = query.filter(Location.longitude <= lng_max)

    total = query.count()

    # Sorting
    if sort_by == 'importance':
        query = query.order_by(Person.global_score.desc().nullslast(), Person.birth_year)
    else:
        query = query.order_by(Person.birth_year)

    persons = query.offset(offset).limit(limit).all()

    return persons, total


def get_person_by_id(db: Session, person_id: int) -> Optional[Person]:
    return db.query(Person).options(
        joinedload(Person.details),
        joinedload(Person.names),
        joinedload(Person.birthplace),
        joinedload(Person.deathplace),
    ).filter(Person.id == person_id).first()


def get_person_events(db: Session, person_id: int) -> list:
    person = get_person_by_id(db, person_id)
    return person.events if person else []


def get_related_persons(
    db: Session,
    person_id: int,
    limit: int = 20,
    min_strength: float = 0,
) -> list[dict]:
    """Get related persons from person_relationships table."""
    from sqlalchemy import text

    query = text("""
        SELECT
            p.id,
            p.name,
            p.name_ko,
            p.name_ja,
            p.birth_year,
            p.death_year,
            pr.strength,
            pr.time_distance,
            pr.relationship_type,
            pr.is_bidirectional
        FROM person_relationships pr
        JOIN persons p ON p.id = pr.related_person_id
        WHERE pr.person_id = :person_id
          AND pr.strength >= :min_strength

        UNION

        SELECT
            p.id,
            p.name,
            p.name_ko,
            p.name_ja,
            p.birth_year,
            p.death_year,
            pr.strength,
            pr.time_distance,
            pr.relationship_type,
            pr.is_bidirectional
        FROM person_relationships pr
        JOIN persons p ON p.id = pr.person_id
        WHERE pr.related_person_id = :person_id
          AND pr.strength >= :min_strength

        ORDER BY strength DESC
        LIMIT :limit
    """)

    result = db.execute(query, {
        "person_id": person_id,
        "min_strength": min_strength,
        "limit": limit
    })

    relations = []
    for row in result:
        relations.append({
            "id": row[0],
            "name": row[1],
            "name_ko": row[2],
            "name_ja": row[3],
            "birth_year": row[4],
            "death_year": row[5],
            "strength": row[6],
            "time_distance": row[7],
            "relationship_type": row[8],
            "is_bidirectional": row[9],
        })

    return relations


def get_person_flow(db: Session, person_id: int) -> dict:
    """Get a person's event flow in chronological order."""
    from sqlalchemy import text

    person = get_person_by_id(db, person_id)
    if not person:
        return None

    # Get events linked to this person, sorted chronologically
    result = db.execute(text("""
        SELECT e.id, e.title, e.title_ko, e.title_ja, e.date_start, e.date_end,
               l.name as location_name, l.latitude, l.longitude,
               ep.role
        FROM event_persons ep
        JOIN events e ON ep.event_id = e.id
        LEFT JOIN locations l ON e.primary_location_id = l.id
        WHERE ep.person_id = :person_id
        ORDER BY e.date_start ASC NULLS LAST
    """), {"person_id": person_id})

    flow = []
    for row in result:
        flow.append({
            "event_id": row[0],
            "title": row[1],
            "title_ko": row[2],
            "title_ja": row[3],
            "year": row[4],
            "year_end": row[5],
            "location": row[6],
            "lat": float(row[7]) if row[7] else None,
            "lng": float(row[8]) if row[8] else None,
            "role": row[9],
        })

    # Build birthplace/deathplace info
    birthplace = None
    if person.birthplace:
        birthplace = {
            "id": person.birthplace.id,
            "name": person.birthplace.name,
            "lat": float(person.birthplace.latitude) if person.birthplace.latitude else None,
            "lng": float(person.birthplace.longitude) if person.birthplace.longitude else None,
        }

    deathplace = None
    if person.deathplace:
        deathplace = {
            "id": person.deathplace.id,
            "name": person.deathplace.name,
            "lat": float(person.deathplace.latitude) if person.deathplace.latitude else None,
            "lng": float(person.deathplace.longitude) if person.deathplace.longitude else None,
        }

    return {
        "person_id": person.id,
        "name": person.name,
        "name_ko": person.name_ko,
        "name_ja": person.name_ja,
        "birth_year": person.birth_year,
        "death_year": person.death_year,
        "birthplace": birthplace,
        "deathplace": deathplace,
        "flow": flow,
        "total_events": len(flow),
    }
