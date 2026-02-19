"""
새 스키마용 Wikidata 추출기

Usage:
    python fresh_extract.py --limit 100 --output test_extract.jsonl
    python fresh_extract.py --output full_extract.jsonl
"""

import bz2
import json
import sys
import argparse
import time
from typing import Dict, Set, Optional, Any, List
from dataclasses import dataclass, asdict, field

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DUMP_PATH = "C:/Projects/Chaldeas/data/wikidata/latest-all.json.bz2"

# ============================================
# TYPE DEFINITIONS (Wikidata P31 → CHALDEAS)
# ============================================

# Location types (점)
LOCATION_TYPES: Dict[str, str] = {
    'Q515': 'point',      # city
    'Q3957': 'point',     # town
    'Q532': 'point',      # village
    'Q5119': 'point',     # capital
    'Q486972': 'point',   # human settlement
    'Q839954': 'point',   # archaeological site
    'Q4895508': 'point',  # battlefield
    'Q41176': 'point',    # building
    'Q16560': 'point',    # palace
    'Q23413': 'point',    # castle
    'Q8502': 'natural',   # mountain
    'Q4022': 'natural',   # river
    'Q23397': 'natural',  # lake
    'Q23442': 'natural',  # island
    'Q165': 'sea',        # sea
    'Q9430': 'sea',       # ocean
}

# Territory types (영역)
TERRITORY_TYPES: Dict[str, str] = {
    'Q6256': 'country',       # country
    'Q3624078': 'country',    # sovereign state
    'Q3024240': 'country',    # historical country
    'Q48349': 'empire',       # empire
    'Q417175': 'country',     # kingdom
    'Q7270': 'country',       # republic
    'Q28575': 'country',      # duchy
    'Q208500': 'country',     # principality
    'Q5107': 'continent',     # continent
    'Q82794': 'region',       # geographic region
    'Q855697': 'region',      # subcontinent
}

# Group types (집단)
GROUP_TYPES: Dict[str, str] = {
    'Q176799': 'military',    # military unit
    'Q37726': 'military',     # army
    'Q189573': 'military',    # legion
    'Q1133779': 'religious',  # religious order
    'Q471195': 'religious',   # knightly order
    'Q41710': 'ethnic',       # ethnic group
    'Q133311': 'ethnic',      # tribe
    'Q7278': 'political',     # political party
    'Q43229': 'political',    # organization
}

# Event types (사건)
EVENT_TYPES: Dict[str, str] = {
    'Q178561': 'battle',
    'Q198': 'war',
    'Q180684': 'military_conflict',
    'Q188055': 'siege',
    'Q131569': 'treaty',
    'Q10931': 'revolution',
    'Q124734': 'rebellion',
    'Q45382': 'coup',
    'Q8465': 'civil_war',
    'Q13418847': 'historical_event',
    'Q173065': 'crusade',
    'Q192909': 'natural_disaster',
    'Q3199915': 'massacre',
    'Q2401485': 'expedition',
    'Q209480': 'coronation',
    'Q3882219': 'assassination',
}

# 제외할 타입
EXCLUDED_TYPES: Set[str] = {
    'Q16521',     # taxon
    'Q7889',      # video game
    'Q11424',     # film
    'Q5398426',   # TV series
    'Q7725634',   # literary work
}

# ============================================
# DATA CLASSES
# ============================================

@dataclass
class ExtractedLocation:
    qid: str
    name: str
    name_ko: Optional[str]
    latitude: float
    longitude: float
    location_type: str
    parent_qid: Optional[str] = None  # P131

@dataclass
class ExtractedTerritory:
    qid: str
    name: str
    name_ko: Optional[str]
    territory_type: str
    founded_year: Optional[int] = None  # P571
    dissolved_year: Optional[int] = None  # P576
    parent_qid: Optional[str] = None  # P131
    capital_qids: List[str] = field(default_factory=list)  # P36

@dataclass
class ExtractedPerson:
    qid: str
    name: str
    name_ko: Optional[str]
    birth_year: Optional[int] = None  # P569
    death_year: Optional[int] = None  # P570
    birthplace_qid: Optional[str] = None  # P19
    deathplace_qid: Optional[str] = None  # P20
    description: Optional[str] = None

@dataclass
class ExtractedGroup:
    qid: str
    name: str
    name_ko: Optional[str]
    group_type: str
    founded_year: Optional[int] = None  # P571
    dissolved_year: Optional[int] = None  # P576
    parent_qid: Optional[str] = None  # P749 parent organization
    territory_qid: Optional[str] = None  # P17 country

@dataclass
class ExtractedEvent:
    qid: str
    title: str
    title_ko: Optional[str]
    event_type: str
    date_start: Optional[int] = None
    date_end: Optional[int] = None
    description: Optional[str] = None
    location_qids: List[str] = field(default_factory=list)  # P276
    territory_qids: List[str] = field(default_factory=list)  # P17
    participant_qids: List[str] = field(default_factory=list)  # P710
    parent_qid: Optional[str] = None  # P361

# ============================================
# PARSING HELPERS
# ============================================

def get_label(entity: dict, lang: str = 'en') -> Optional[str]:
    """Get label in specified language"""
    labels = entity.get('labels', {})
    if lang in labels:
        return labels[lang].get('value')
    return None

def get_description(entity: dict, lang: str = 'en') -> Optional[str]:
    """Get description"""
    descs = entity.get('descriptions', {})
    if lang in descs:
        return descs[lang].get('value')
    return None

def get_claim_values(entity: dict, prop: str) -> List[dict]:
    """Get all claim values for a property"""
    claims = entity.get('claims', {}).get(prop, [])
    values = []
    for claim in claims:
        mainsnak = claim.get('mainsnak', {})
        if mainsnak.get('snaktype') == 'value':
            datavalue = mainsnak.get('datavalue', {})
            values.append({
                'value': datavalue.get('value'),
                'type': datavalue.get('type'),
                'qualifiers': claim.get('qualifiers', {})
            })
    return values

def get_qid_values(entity: dict, prop: str) -> List[str]:
    """Get QID values from wikibase-entityid type claims"""
    values = get_claim_values(entity, prop)
    qids = []
    for v in values:
        if v['type'] == 'wikibase-entityid':
            qid = v['value'].get('id')
            if qid:
                qids.append(qid)
    return qids

def get_first_qid(entity: dict, prop: str) -> Optional[str]:
    """Get first QID value"""
    qids = get_qid_values(entity, prop)
    return qids[0] if qids else None

def get_coordinate(entity: dict) -> Optional[tuple]:
    """Get coordinate from P625"""
    values = get_claim_values(entity, 'P625')
    for v in values:
        if v['type'] == 'globecoordinate':
            coord = v['value']
            return (coord.get('latitude'), coord.get('longitude'))
    return None

def parse_time_value(time_value: dict) -> Optional[int]:
    """Parse Wikidata time value to year (BCE as negative)"""
    if not time_value:
        return None
    time_str = time_value.get('time', '')
    # Format: +1066-10-14T00:00:00Z or -0490-01-01T00:00:00Z
    if not time_str:
        return None
    try:
        # Remove leading + or -
        sign = 1 if time_str[0] == '+' else -1
        year_str = time_str[1:].split('-')[0]
        year = int(year_str)
        return sign * year if year != 0 else None
    except:
        return None

def get_year(entity: dict, prop: str) -> Optional[int]:
    """Get year from time property"""
    values = get_claim_values(entity, prop)
    for v in values:
        if v['type'] == 'time':
            year = parse_time_value(v['value'])
            if year is not None:
                return year
    return None

def get_p31_types(entity: dict) -> Set[str]:
    """Get all P31 (instance of) QIDs"""
    return set(get_qid_values(entity, 'P31'))

# ============================================
# ENTITY CLASSIFICATION
# ============================================

def classify_entity(entity: dict) -> Optional[str]:
    """Classify entity into CHALDEAS type"""
    p31_types = get_p31_types(entity)

    # Check exclusions first
    if p31_types & EXCLUDED_TYPES:
        return None

    # Person (Q5)
    if 'Q5' in p31_types:
        return 'person'

    # Location (needs coordinate)
    for qid in p31_types:
        if qid in LOCATION_TYPES:
            coord = get_coordinate(entity)
            if coord and coord[0] is not None:
                return 'location'

    # Territory
    for qid in p31_types:
        if qid in TERRITORY_TYPES:
            return 'territory'

    # Group
    for qid in p31_types:
        if qid in GROUP_TYPES:
            return 'group'

    # Event
    for qid in p31_types:
        if qid in EVENT_TYPES:
            return 'event'

    return None

# ============================================
# ENTITY EXTRACTORS
# ============================================

def extract_location(entity: dict) -> Optional[ExtractedLocation]:
    """Extract location from entity"""
    coord = get_coordinate(entity)
    if not coord or coord[0] is None:
        return None

    p31_types = get_p31_types(entity)
    loc_type = 'point'
    for qid in p31_types:
        if qid in LOCATION_TYPES:
            loc_type = LOCATION_TYPES[qid]
            break

    return ExtractedLocation(
        qid=entity['id'],
        name=get_label(entity, 'en') or entity['id'],
        name_ko=get_label(entity, 'ko'),
        latitude=coord[0],
        longitude=coord[1],
        location_type=loc_type,
        parent_qid=get_first_qid(entity, 'P131')
    )

def extract_territory(entity: dict) -> Optional[ExtractedTerritory]:
    """Extract territory from entity"""
    p31_types = get_p31_types(entity)
    terr_type = 'country'
    for qid in p31_types:
        if qid in TERRITORY_TYPES:
            terr_type = TERRITORY_TYPES[qid]
            break

    return ExtractedTerritory(
        qid=entity['id'],
        name=get_label(entity, 'en') or entity['id'],
        name_ko=get_label(entity, 'ko'),
        territory_type=terr_type,
        founded_year=get_year(entity, 'P571'),
        dissolved_year=get_year(entity, 'P576'),
        parent_qid=get_first_qid(entity, 'P131'),
        capital_qids=get_qid_values(entity, 'P36')
    )

def extract_person(entity: dict) -> Optional[ExtractedPerson]:
    """Extract person from entity"""
    return ExtractedPerson(
        qid=entity['id'],
        name=get_label(entity, 'en') or entity['id'],
        name_ko=get_label(entity, 'ko'),
        birth_year=get_year(entity, 'P569'),
        death_year=get_year(entity, 'P570'),
        birthplace_qid=get_first_qid(entity, 'P19'),
        deathplace_qid=get_first_qid(entity, 'P20'),
        description=get_description(entity, 'en')
    )

def extract_group(entity: dict) -> Optional[ExtractedGroup]:
    """Extract group from entity"""
    p31_types = get_p31_types(entity)
    grp_type = 'political'
    for qid in p31_types:
        if qid in GROUP_TYPES:
            grp_type = GROUP_TYPES[qid]
            break

    return ExtractedGroup(
        qid=entity['id'],
        name=get_label(entity, 'en') or entity['id'],
        name_ko=get_label(entity, 'ko'),
        group_type=grp_type,
        founded_year=get_year(entity, 'P571'),
        dissolved_year=get_year(entity, 'P576'),
        parent_qid=get_first_qid(entity, 'P749'),
        territory_qid=get_first_qid(entity, 'P17')
    )

def extract_event(entity: dict) -> Optional[ExtractedEvent]:
    """Extract event from entity"""
    p31_types = get_p31_types(entity)
    evt_type = 'historical_event'
    for qid in p31_types:
        if qid in EVENT_TYPES:
            evt_type = EVENT_TYPES[qid]
            break

    # Date: P585 (point in time) or P580/P582 (start/end)
    date_start = get_year(entity, 'P585')
    date_end = None
    if date_start is None:
        date_start = get_year(entity, 'P580')
        date_end = get_year(entity, 'P582')

    if date_start is None:
        return None  # Event without date is useless

    return ExtractedEvent(
        qid=entity['id'],
        title=get_label(entity, 'en') or entity['id'],
        title_ko=get_label(entity, 'ko'),
        event_type=evt_type,
        date_start=date_start,
        date_end=date_end,
        description=get_description(entity, 'en'),
        location_qids=get_qid_values(entity, 'P276'),
        territory_qids=get_qid_values(entity, 'P17'),
        participant_qids=get_qid_values(entity, 'P710'),
        parent_qid=get_first_qid(entity, 'P361')
    )

# ============================================
# MAIN EXTRACTION
# ============================================

def extract_from_dump(output_path: str, limit: Optional[int] = None):
    """Extract entities from Wikidata dump"""

    counts = {
        'location': 0,
        'territory': 0,
        'person': 0,
        'group': 0,
        'event': 0
    }
    limits = {k: limit // 5 if limit else None for k in counts}

    processed = 0
    start_time = time.time()

    print(f"Opening dump: {DUMP_PATH}")
    print(f"Limit per type: {limits['location'] if limit else 'unlimited'}")
    print()

    with bz2.open(DUMP_PATH, 'rt', encoding='utf-8') as dump_file:
        with open(output_path, 'w', encoding='utf-8') as out_file:

            for line in dump_file:
                # Skip array brackets
                line = line.strip()
                if line in ['[', ']', '']:
                    continue
                if line.endswith(','):
                    line = line[:-1]

                try:
                    entity = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if entity.get('type') != 'item':
                    continue

                processed += 1

                # Progress
                if processed % 100000 == 0:
                    elapsed = time.time() - start_time
                    rate = processed / elapsed
                    print(f"Processed: {processed:,} ({rate:.0f}/s) | "
                          f"L:{counts['location']} T:{counts['territory']} "
                          f"P:{counts['person']} G:{counts['group']} E:{counts['event']}")

                # Check if we've reached all limits
                if limit:
                    all_done = all(
                        counts[k] >= limits[k]
                        for k in counts if limits[k]
                    )
                    if all_done:
                        print(f"\nAll limits reached at entity #{processed:,}")
                        break

                # Classify
                entity_type = classify_entity(entity)
                if not entity_type:
                    continue

                # Check limit for this type
                if limit and counts[entity_type] >= limits[entity_type]:
                    continue

                # Extract
                extracted = None
                if entity_type == 'location':
                    extracted = extract_location(entity)
                elif entity_type == 'territory':
                    extracted = extract_territory(entity)
                elif entity_type == 'person':
                    extracted = extract_person(entity)
                elif entity_type == 'group':
                    extracted = extract_group(entity)
                elif entity_type == 'event':
                    extracted = extract_event(entity)

                if extracted:
                    counts[entity_type] += 1
                    record = {
                        'type': entity_type,
                        'data': asdict(extracted)
                    }
                    out_file.write(json.dumps(record, ensure_ascii=False) + '\n')

    elapsed = time.time() - start_time
    print()
    print(f"=== Extraction Complete ===")
    print(f"Total processed: {processed:,}")
    print(f"Time: {elapsed:.1f}s")
    print(f"Extracted:")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    print(f"Output: {output_path}")

# ============================================
# CLI
# ============================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract entities from Wikidata dump')
    parser.add_argument('--output', '-o', required=True, help='Output JSONL file')
    parser.add_argument('--limit', '-l', type=int, help='Limit per entity type')

    args = parser.parse_args()

    extract_from_dump(args.output, args.limit)
