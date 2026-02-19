"""
새 스키마용 Wikidata 임포트

Usage:
    python fresh_import.py --input test_extract.jsonl
"""

import json
import sys
import argparse
from typing import Dict, Optional, Any, List
from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DATABASE_URL = "postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas"

# ============================================
# DATABASE SETUP
# ============================================

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# ============================================
# QID CACHE (for resolving references)
# ============================================

class QIDCache:
    """Cache QID → DB ID mappings"""

    def __init__(self):
        self.locations: Dict[str, int] = {}
        self.territories: Dict[str, int] = {}
        self.persons: Dict[str, int] = {}
        self.groups: Dict[str, int] = {}
        self.events: Dict[str, int] = {}

    def load_from_db(self, session):
        """Load existing QID mappings from database"""
        # Locations
        result = session.execute(text("SELECT wikidata_id, id FROM locations WHERE wikidata_id IS NOT NULL"))
        for row in result:
            self.locations[row[0]] = row[1]

        # Territories
        result = session.execute(text("SELECT wikidata_id, id FROM territories WHERE wikidata_id IS NOT NULL"))
        for row in result:
            self.territories[row[0]] = row[1]

        # Persons
        result = session.execute(text("SELECT wikidata_id, id FROM persons WHERE wikidata_id IS NOT NULL"))
        for row in result:
            self.persons[row[0]] = row[1]

        # Groups
        result = session.execute(text("SELECT wikidata_id, id FROM groups WHERE wikidata_id IS NOT NULL"))
        for row in result:
            self.groups[row[0]] = row[1]

        # Events
        result = session.execute(text("SELECT wikidata_id, id FROM events WHERE wikidata_id IS NOT NULL"))
        for row in result:
            self.events[row[0]] = row[1]

        print(f"Loaded cache: L:{len(self.locations)} T:{len(self.territories)} "
              f"P:{len(self.persons)} G:{len(self.groups)} E:{len(self.events)}")

# ============================================
# IMPORTERS
# ============================================

def import_location(session, data: dict, cache: QIDCache) -> Optional[int]:
    """Import location"""
    qid = data['qid']

    # Skip if already exists
    if qid in cache.locations:
        return cache.locations[qid]

    # Resolve parent
    parent_id = None
    if data.get('parent_qid'):
        parent_id = cache.locations.get(data['parent_qid'])

    result = session.execute(text("""
        INSERT INTO locations (name, name_ko, latitude, longitude, location_type, parent_location_id, wikidata_id)
        VALUES (:name, :name_ko, :lat, :lng, :type, :parent_id, :qid)
        ON CONFLICT (wikidata_id) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
    """), {
        'name': data['name'],
        'name_ko': data.get('name_ko'),
        'lat': data['latitude'],
        'lng': data['longitude'],
        'type': data['location_type'],
        'parent_id': parent_id,
        'qid': qid
    })

    db_id = result.scalar()
    cache.locations[qid] = db_id
    return db_id

def import_territory(session, data: dict, cache: QIDCache) -> Optional[int]:
    """Import territory"""
    qid = data['qid']

    if qid in cache.territories:
        return cache.territories[qid]

    # Resolve parent territory
    parent_id = None
    if data.get('parent_qid'):
        parent_id = cache.territories.get(data['parent_qid'])

    result = session.execute(text("""
        INSERT INTO territories (name, name_ko, territory_type, founded_year, dissolved_year, parent_territory_id, wikidata_id)
        VALUES (:name, :name_ko, :type, :founded, :dissolved, :parent_id, :qid)
        ON CONFLICT (wikidata_id) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
    """), {
        'name': data['name'],
        'name_ko': data.get('name_ko'),
        'type': data['territory_type'],
        'founded': data.get('founded_year'),
        'dissolved': data.get('dissolved_year'),
        'parent_id': parent_id,
        'qid': qid
    })

    db_id = result.scalar()
    cache.territories[qid] = db_id

    # TODO: Add territory_locations for capitals
    # for capital_qid in data.get('capital_qids', []):
    #     ...

    return db_id

def import_person(session, data: dict, cache: QIDCache) -> Optional[int]:
    """Import person"""
    qid = data['qid']

    if qid in cache.persons:
        return cache.persons[qid]

    # Resolve birthplace/deathplace
    birthplace_id = None
    deathplace_id = None
    if data.get('birthplace_qid'):
        birthplace_id = cache.locations.get(data['birthplace_qid'])
    if data.get('deathplace_qid'):
        deathplace_id = cache.locations.get(data['deathplace_qid'])

    result = session.execute(text("""
        INSERT INTO persons (name, name_ko, birth_year, death_year, birthplace_id, deathplace_id, biography, wikidata_id)
        VALUES (:name, :name_ko, :birth, :death, :birthplace, :deathplace, :bio, :qid)
        ON CONFLICT (wikidata_id) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
    """), {
        'name': data['name'],
        'name_ko': data.get('name_ko'),
        'birth': data.get('birth_year'),
        'death': data.get('death_year'),
        'birthplace': birthplace_id,
        'deathplace': deathplace_id,
        'bio': data.get('description'),
        'qid': qid
    })

    db_id = result.scalar()
    cache.persons[qid] = db_id
    return db_id

def import_group(session, data: dict, cache: QIDCache) -> Optional[int]:
    """Import group"""
    qid = data['qid']

    if qid in cache.groups:
        return cache.groups[qid]

    # Resolve parent group and territory
    parent_id = None
    territory_id = None
    if data.get('parent_qid'):
        parent_id = cache.groups.get(data['parent_qid'])
    if data.get('territory_qid'):
        territory_id = cache.territories.get(data['territory_qid'])

    result = session.execute(text("""
        INSERT INTO groups (name, name_ko, group_type, founded_year, dissolved_year, parent_group_id, territory_id, wikidata_id)
        VALUES (:name, :name_ko, :type, :founded, :dissolved, :parent_id, :territory_id, :qid)
        ON CONFLICT (wikidata_id) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
    """), {
        'name': data['name'],
        'name_ko': data.get('name_ko'),
        'type': data['group_type'],
        'founded': data.get('founded_year'),
        'dissolved': data.get('dissolved_year'),
        'parent_id': parent_id,
        'territory_id': territory_id,
        'qid': qid
    })

    db_id = result.scalar()
    cache.groups[qid] = db_id
    return db_id

def import_event(session, data: dict, cache: QIDCache) -> Optional[int]:
    """Import event"""
    qid = data['qid']

    if qid in cache.events:
        return cache.events[qid]

    # Resolve primary location
    primary_location_id = None
    if data.get('location_qids'):
        for loc_qid in data['location_qids']:
            if loc_qid in cache.locations:
                primary_location_id = cache.locations[loc_qid]
                break

    # Resolve parent event
    parent_event_id = None
    if data.get('parent_qid'):
        parent_event_id = cache.events.get(data['parent_qid'])

    result = session.execute(text("""
        INSERT INTO events (title, title_ko, wikidata_id, date_start, date_end, description, primary_location_id, event_type, parent_event_id)
        VALUES (:title, :title_ko, :qid, :date_start, :date_end, :description, :location_id, :type, :parent_id)
        ON CONFLICT (wikidata_id) DO UPDATE SET title = EXCLUDED.title
        RETURNING id
    """), {
        'title': data['title'],
        'title_ko': data.get('title_ko'),
        'qid': qid,
        'date_start': data['date_start'],
        'date_end': data.get('date_end'),
        'description': data.get('description'),
        'location_id': primary_location_id,
        'type': data['event_type'],
        'parent_id': parent_event_id
    })

    db_id = result.scalar()
    cache.events[qid] = db_id

    # Add event_locations
    for loc_qid in data.get('location_qids', []):
        loc_id = cache.locations.get(loc_qid)
        if loc_id:
            session.execute(text("""
                INSERT INTO event_locations (event_id, location_id, role)
                VALUES (:event_id, :loc_id, 'location')
                ON CONFLICT DO NOTHING
            """), {'event_id': db_id, 'loc_id': loc_id})

    # Add event_territories
    for terr_qid in data.get('territory_qids', []):
        terr_id = cache.territories.get(terr_qid)
        if terr_id:
            session.execute(text("""
                INSERT INTO event_territories (event_id, territory_id, role)
                VALUES (:event_id, :terr_id, 'participant')
                ON CONFLICT DO NOTHING
            """), {'event_id': db_id, 'terr_id': terr_id})

    # Add event_persons (P710 participants that are persons)
    for part_qid in data.get('participant_qids', []):
        person_id = cache.persons.get(part_qid)
        if person_id:
            session.execute(text("""
                INSERT INTO event_persons (event_id, person_id, role)
                VALUES (:event_id, :person_id, 'participant')
                ON CONFLICT DO NOTHING
            """), {'event_id': db_id, 'person_id': person_id})

    # Add event_groups (P710 participants that are groups)
    for part_qid in data.get('participant_qids', []):
        group_id = cache.groups.get(part_qid)
        if group_id:
            session.execute(text("""
                INSERT INTO event_groups (event_id, group_id, role)
                VALUES (:event_id, :group_id, 'participant')
                ON CONFLICT DO NOTHING
            """), {'event_id': db_id, 'group_id': group_id})

    return db_id

# ============================================
# MAIN IMPORT
# ============================================

def import_from_file(input_path: str):
    """Import entities from JSONL file"""

    session = Session()
    cache = QIDCache()

    # Load existing data
    cache.load_from_db(session)

    # First pass: collect all entities by type
    entities = {
        'location': [],
        'territory': [],
        'person': [],
        'group': [],
        'event': []
    }

    print(f"\nReading {input_path}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            record = json.loads(line)
            entity_type = record['type']
            entities[entity_type].append(record['data'])

    for t, lst in entities.items():
        print(f"  {t}: {len(lst)}")

    # Import in dependency order
    counts = {'location': 0, 'territory': 0, 'person': 0, 'group': 0, 'event': 0}

    print("\nImporting locations...")
    for data in entities['location']:
        if import_location(session, data, cache):
            counts['location'] += 1
    session.commit()

    print("Importing territories...")
    for data in entities['territory']:
        if import_territory(session, data, cache):
            counts['territory'] += 1
    session.commit()

    print("Importing persons...")
    for data in entities['person']:
        if import_person(session, data, cache):
            counts['person'] += 1
    session.commit()

    print("Importing groups...")
    for data in entities['group']:
        if import_group(session, data, cache):
            counts['group'] += 1
    session.commit()

    print("Importing events...")
    for data in entities['event']:
        if import_event(session, data, cache):
            counts['event'] += 1
    session.commit()

    session.close()

    print("\n=== Import Complete ===")
    for t, c in counts.items():
        print(f"  {t}: {c}")

    # Verify
    print("\n=== Verification ===")
    with engine.connect() as conn:
        for table in ['locations', 'territories', 'persons', 'groups', 'events']:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"  {table}: {count}")

        # Check event_locations
        result = conn.execute(text("SELECT COUNT(*) FROM event_locations"))
        print(f"  event_locations: {result.scalar()}")

        # Check events with locations
        result = conn.execute(text("""
            SELECT COUNT(*) FROM events WHERE primary_location_id IS NOT NULL
        """))
        print(f"  events with location: {result.scalar()}")

# ============================================
# CLI
# ============================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import entities to database')
    parser.add_argument('--input', '-i', required=True, help='Input JSONL file')

    args = parser.parse_args()

    import_from_file(args.input)
