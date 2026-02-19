"""
새 스키마용 Wikidata 임포트 (sources/mentions 포함)

Usage:
    python import_with_sources.py --input test.jsonl
"""

import json
import sys
import argparse
from typing import Dict, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DATABASE_URL = "postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas"

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# ============================================
# QID CACHE
# ============================================

class QIDCache:
    def __init__(self):
        self.locations: Dict[str, int] = {}
        self.territories: Dict[str, int] = {}
        self.persons: Dict[str, int] = {}
        self.groups: Dict[str, int] = {}
        self.events: Dict[str, int] = {}
        self.sources: Dict[str, int] = {}  # qid → source_id

    def load_from_db(self, session):
        for table, cache in [
            ('locations', self.locations),
            ('territories', self.territories),
            ('persons', self.persons),
            ('groups', self.groups),
            ('events', self.events),
        ]:
            result = session.execute(text(f"SELECT wikidata_id, id FROM {table} WHERE wikidata_id IS NOT NULL"))
            for row in result:
                cache[row[0]] = row[1]

        # sources는 wikidata_id로 조회
        result = session.execute(text("SELECT wikidata_id, id FROM sources WHERE wikidata_id IS NOT NULL"))
        for row in result:
            self.sources[row[0]] = row[1]

        print(f"Loaded cache: L:{len(self.locations)} T:{len(self.territories)} "
              f"P:{len(self.persons)} G:{len(self.groups)} E:{len(self.events)} S:{len(self.sources)}")

# ============================================
# IMPORTERS
# ============================================

def import_location(session, data: dict, cache: QIDCache) -> Optional[int]:
    qid = data['qid']
    if qid in cache.locations:
        return cache.locations[qid]

    parent_id = None
    if data.get('parent_qid'):
        parent_id = cache.locations.get(data['parent_qid'])

    result = session.execute(text("""
        INSERT INTO locations (wikidata_id, name, name_ko, latitude, longitude, location_type, parent_location_id)
        VALUES (:qid, :name, :name_ko, :lat, :lng, :type, :parent_id)
        ON CONFLICT (wikidata_id) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
    """), {
        'qid': qid,
        'name': data['name'],
        'name_ko': data.get('name_ko'),
        'lat': data['latitude'],
        'lng': data['longitude'],
        'type': data['location_type'],
        'parent_id': parent_id
    })

    db_id = result.scalar()
    cache.locations[qid] = db_id
    return db_id

def import_territory(session, data: dict, cache: QIDCache) -> Optional[int]:
    qid = data['qid']
    if qid in cache.territories:
        return cache.territories[qid]

    result = session.execute(text("""
        INSERT INTO territories (wikidata_id, name, name_ko, territory_type, founded_year, dissolved_year)
        VALUES (:qid, :name, :name_ko, :type, :founded, :dissolved)
        ON CONFLICT (wikidata_id) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
    """), {
        'qid': qid,
        'name': data['name'],
        'name_ko': data.get('name_ko'),
        'type': data['territory_type'],
        'founded': data.get('founded_year'),
        'dissolved': data.get('dissolved_year')
    })

    db_id = result.scalar()
    cache.territories[qid] = db_id
    return db_id

def import_person(session, data: dict, cache: QIDCache) -> Optional[int]:
    qid = data['qid']
    if qid in cache.persons:
        return cache.persons[qid]

    birthplace_id = cache.locations.get(data.get('birthplace_qid')) if data.get('birthplace_qid') else None
    deathplace_id = cache.locations.get(data.get('deathplace_qid')) if data.get('deathplace_qid') else None

    result = session.execute(text("""
        INSERT INTO persons (wikidata_id, name, name_ko, birth_year, death_year, birthplace_id, deathplace_id, description)
        VALUES (:qid, :name, :name_ko, :birth, :death, :birthplace, :deathplace, :desc)
        ON CONFLICT (wikidata_id) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
    """), {
        'qid': qid,
        'name': data['name'],
        'name_ko': data.get('name_ko'),
        'birth': data.get('birth_year'),
        'death': data.get('death_year'),
        'birthplace': birthplace_id,
        'deathplace': deathplace_id,
        'desc': data.get('description')
    })

    db_id = result.scalar()
    cache.persons[qid] = db_id
    return db_id

def import_group(session, data: dict, cache: QIDCache) -> Optional[int]:
    qid = data['qid']
    if qid in cache.groups:
        return cache.groups[qid]

    territory_id = cache.territories.get(data.get('territory_qid')) if data.get('territory_qid') else None

    result = session.execute(text("""
        INSERT INTO groups (wikidata_id, name, name_ko, group_type, founded_year, dissolved_year, territory_id)
        VALUES (:qid, :name, :name_ko, :type, :founded, :dissolved, :territory_id)
        ON CONFLICT (wikidata_id) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
    """), {
        'qid': qid,
        'name': data['name'],
        'name_ko': data.get('name_ko'),
        'type': data['group_type'],
        'founded': data.get('founded_year'),
        'dissolved': data.get('dissolved_year'),
        'territory_id': territory_id
    })

    db_id = result.scalar()
    cache.groups[qid] = db_id
    return db_id

def import_event(session, data: dict, cache: QIDCache) -> Optional[int]:
    qid = data['qid']
    if qid in cache.events:
        return cache.events[qid]

    primary_location_id = None
    for loc_qid in data.get('location_qids', []):
        if loc_qid in cache.locations:
            primary_location_id = cache.locations[loc_qid]
            break

    parent_event_id = cache.events.get(data.get('parent_qid')) if data.get('parent_qid') else None

    result = session.execute(text("""
        INSERT INTO events (wikidata_id, title, title_ko, date_start, date_end, event_type, primary_location_id, parent_event_id, description)
        VALUES (:qid, :title, :title_ko, :date_start, :date_end, :type, :location_id, :parent_id, :desc)
        ON CONFLICT (wikidata_id) DO UPDATE SET title = EXCLUDED.title
        RETURNING id
    """), {
        'qid': qid,
        'title': data['title'],
        'title_ko': data.get('title_ko'),
        'date_start': data['date_start'],
        'date_end': data.get('date_end'),
        'type': data['event_type'],
        'location_id': primary_location_id,
        'parent_id': parent_event_id,
        'desc': data.get('description')
    })

    db_id = result.scalar()
    cache.events[qid] = db_id

    # event_locations
    for loc_qid in data.get('location_qids', []):
        loc_id = cache.locations.get(loc_qid)
        if loc_id:
            session.execute(text("""
                INSERT INTO event_locations (event_id, location_id, role)
                VALUES (:event_id, :loc_id, 'location')
                ON CONFLICT DO NOTHING
            """), {'event_id': db_id, 'loc_id': loc_id})

    # event_participants (person/group/territory)
    for part_qid in data.get('participant_qids', []):
        if part_qid in cache.persons:
            session.execute(text("""
                INSERT INTO event_participants (event_id, participant_type, participant_id, role)
                VALUES (:eid, 'person', :pid, 'participant')
                ON CONFLICT DO NOTHING
            """), {'eid': db_id, 'pid': cache.persons[part_qid]})
        elif part_qid in cache.groups:
            session.execute(text("""
                INSERT INTO event_participants (event_id, participant_type, participant_id, role)
                VALUES (:eid, 'group', :gid, 'participant')
                ON CONFLICT DO NOTHING
            """), {'eid': db_id, 'gid': cache.groups[part_qid]})
        elif part_qid in cache.territories:
            session.execute(text("""
                INSERT INTO event_participants (event_id, participant_type, participant_id, role)
                VALUES (:eid, 'territory', :tid, 'participant')
                ON CONFLICT DO NOTHING
            """), {'eid': db_id, 'tid': cache.territories[part_qid]})

    for terr_qid in data.get('territory_qids', []):
        terr_id = cache.territories.get(terr_qid)
        if terr_id:
            session.execute(text("""
                INSERT INTO event_participants (event_id, participant_type, participant_id, role)
                VALUES (:eid, 'territory', :tid, 'location')
                ON CONFLICT DO NOTHING
            """), {'eid': db_id, 'tid': terr_id})

    return db_id

def import_source(session, data: dict, cache: QIDCache) -> Optional[int]:
    qid = data['qid']
    if qid in cache.sources:
        return cache.sources[qid]

    result = session.execute(text("""
        INSERT INTO sources (source_type, title, content_raw, url, wikidata_id)
        VALUES ('wikidata', :title, :content, :url, :qid)
        ON CONFLICT (wikidata_id) DO UPDATE SET title = EXCLUDED.title
        RETURNING id
    """), {
        'title': data['title'],
        'content': data['content_raw'],
        'url': data['url'],
        'qid': qid
    })

    db_id = result.scalar()
    cache.sources[qid] = db_id
    return db_id

def import_mention(session, data: dict, cache: QIDCache) -> Optional[int]:
    source_qid = data['source_qid']
    target_type = data['target_type']
    target_qid = data['target_qid']

    # source_id 조회
    source_id = cache.sources.get(source_qid)
    if not source_id:
        return None

    # target_id 조회
    target_id = None
    if target_type == 'location':
        target_id = cache.locations.get(target_qid)
    elif target_type == 'territory':
        target_id = cache.territories.get(target_qid)
    elif target_type == 'person':
        target_id = cache.persons.get(target_qid)
    elif target_type == 'group':
        target_id = cache.groups.get(target_qid)
    elif target_type == 'event':
        target_id = cache.events.get(target_qid)

    if not target_id:
        return None

    result = session.execute(text("""
        INSERT INTO mentions (source_id, target_type, target_id, evidence_raw)
        VALUES (:source_id, :target_type, :target_id, :evidence)
        RETURNING id
    """), {
        'source_id': source_id,
        'target_type': target_type,
        'target_id': target_id,
        'evidence': data['evidence_raw']
    })

    return result.scalar()

# ============================================
# MAIN IMPORT
# ============================================

def import_from_file(input_path: str):
    session = Session()
    cache = QIDCache()
    cache.load_from_db(session)

    # Collect all records by type
    records = {
        'location': [], 'territory': [], 'person': [], 'group': [], 'event': [],
        'source': [], 'mention': []
    }

    print(f"\nReading {input_path}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            record = json.loads(line)
            record_type = record['type']
            if record_type in records:
                records[record_type].append(record['data'])

    for t, lst in records.items():
        print(f"  {t}: {len(lst)}")

    counts = {k: 0 for k in records.keys()}

    # Import in order
    print("\nImporting locations...")
    for data in records['location']:
        if import_location(session, data, cache):
            counts['location'] += 1
    session.commit()

    print("Importing territories...")
    for data in records['territory']:
        if import_territory(session, data, cache):
            counts['territory'] += 1
    session.commit()

    print("Importing persons...")
    for data in records['person']:
        if import_person(session, data, cache):
            counts['person'] += 1
    session.commit()

    print("Importing groups...")
    for data in records['group']:
        if import_group(session, data, cache):
            counts['group'] += 1
    session.commit()

    print("Importing events...")
    for data in records['event']:
        if import_event(session, data, cache):
            counts['event'] += 1
    session.commit()

    print("Importing sources...")
    for data in records['source']:
        if import_source(session, data, cache):
            counts['source'] += 1
    session.commit()

    print("Importing mentions...")
    for data in records['mention']:
        if import_mention(session, data, cache):
            counts['mention'] += 1
    session.commit()

    session.close()

    print("\n=== Import Complete ===")
    for t, c in counts.items():
        print(f"  {t}: {c}")

    # Verification
    print("\n=== Verification ===")
    with engine.connect() as conn:
        for table in ['locations', 'territories', 'persons', 'groups', 'events', 'sources', 'mentions']:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"  {table}: {count}")

        # Check mention coverage
        print("\n=== Mention Coverage ===")
        for entity_type, table in [('person', 'persons'), ('location', 'locations'),
                                   ('territory', 'territories'), ('group', 'groups'), ('event', 'events')]:
            result = conn.execute(text(f"""
                SELECT COUNT(*) FROM {table} t
                WHERE EXISTS (SELECT 1 FROM mentions m WHERE m.target_type = :type AND m.target_id = t.id)
            """), {'type': entity_type})
            with_mention = result.scalar()

            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            total = result.scalar()

            pct = (with_mention / total * 100) if total > 0 else 0
            print(f"  {table}: {with_mention}/{total} ({pct:.0f}%)")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import entities with sources to database')
    parser.add_argument('--input', '-i', required=True, help='Input JSONL file')

    args = parser.parse_args()
    import_from_file(args.input)
