"""
Wikidata 추출기 (sources/mentions 포함)

Usage:
    python extract_with_sources.py --limit 100 --output test.jsonl
    python extract_with_sources.py --output full.jsonl
"""

import bz2
import json
import sys
import argparse
import time
from typing import Dict, Set, Optional, List
from dataclasses import dataclass, asdict, field

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DUMP_PATH = "C:/Projects/Chaldeas/data/wikidata/latest-all.json.bz2"

# ============================================
# TYPE DEFINITIONS
# ============================================

LOCATION_TYPES: Dict[str, str] = {
    'Q515': 'point', 'Q3957': 'point', 'Q532': 'point',
    'Q5119': 'point', 'Q486972': 'point', 'Q839954': 'point',
    'Q4895508': 'point', 'Q41176': 'point', 'Q16560': 'point',
    'Q23413': 'point', 'Q8502': 'natural', 'Q4022': 'natural',
    'Q23397': 'natural', 'Q23442': 'natural', 'Q165': 'sea', 'Q9430': 'sea',
}

TERRITORY_TYPES: Dict[str, str] = {
    'Q6256': 'country', 'Q3624078': 'country', 'Q3024240': 'country',
    'Q48349': 'empire', 'Q417175': 'country', 'Q7270': 'country',
    'Q28575': 'country', 'Q208500': 'country', 'Q5107': 'continent',
    'Q82794': 'region', 'Q855697': 'region',
}

GROUP_TYPES: Dict[str, str] = {
    'Q176799': 'military', 'Q37726': 'military', 'Q189573': 'military',
    'Q1133779': 'religious', 'Q471195': 'religious',
    'Q41710': 'ethnic', 'Q133311': 'ethnic',
    'Q7278': 'political', 'Q43229': 'political',
}

EVENT_TYPES: Dict[str, str] = {
    'Q178561': 'battle', 'Q198': 'war', 'Q180684': 'military_conflict',
    'Q188055': 'siege', 'Q131569': 'treaty', 'Q10931': 'revolution',
    'Q124734': 'rebellion', 'Q45382': 'coup', 'Q8465': 'civil_war',
    'Q13418847': 'historical_event', 'Q173065': 'crusade',
    'Q192909': 'natural_disaster', 'Q3199915': 'massacre',
    'Q2401485': 'expedition', 'Q209480': 'coronation', 'Q3882219': 'assassination',
}

EXCLUDED_TYPES: Set[str] = {
    'Q16521', 'Q7889', 'Q11424', 'Q5398426', 'Q7725634',
}

# ============================================
# DATA CLASSES
# ============================================

@dataclass
class ExtractedSource:
    """Wikidata 출처"""
    qid: str
    title: str
    content_raw: str  # description + sitelink info
    url: str

@dataclass
class ExtractedMention:
    """출처 → 엔티티 연결"""
    source_qid: str  # source의 wikidata_id
    target_type: str  # person, location, etc.
    target_qid: str
    evidence_raw: str

@dataclass
class ExtractedLocation:
    qid: str
    name: str
    name_ko: Optional[str]
    latitude: float
    longitude: float
    location_type: str
    parent_qid: Optional[str] = None

@dataclass
class ExtractedTerritory:
    qid: str
    name: str
    name_ko: Optional[str]
    territory_type: str
    founded_year: Optional[int] = None
    dissolved_year: Optional[int] = None
    capital_qids: List[str] = field(default_factory=list)

@dataclass
class ExtractedPerson:
    qid: str
    name: str
    name_ko: Optional[str]
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    birthplace_qid: Optional[str] = None
    deathplace_qid: Optional[str] = None
    description: Optional[str] = None

@dataclass
class ExtractedGroup:
    qid: str
    name: str
    name_ko: Optional[str]
    group_type: str
    founded_year: Optional[int] = None
    dissolved_year: Optional[int] = None
    territory_qid: Optional[str] = None

@dataclass
class ExtractedEvent:
    qid: str
    title: str
    title_ko: Optional[str]
    event_type: str
    date_start: Optional[int] = None
    date_end: Optional[int] = None
    description: Optional[str] = None
    location_qids: List[str] = field(default_factory=list)
    territory_qids: List[str] = field(default_factory=list)
    participant_qids: List[str] = field(default_factory=list)
    parent_qid: Optional[str] = None

# ============================================
# PARSING HELPERS
# ============================================

def get_label(entity: dict, lang: str = 'en') -> Optional[str]:
    labels = entity.get('labels', {})
    if lang in labels:
        return labels[lang].get('value')
    return None

def get_description(entity: dict, lang: str = 'en') -> Optional[str]:
    descs = entity.get('descriptions', {})
    if lang in descs:
        return descs[lang].get('value')
    return None

def get_sitelink(entity: dict, site: str = 'enwiki') -> Optional[str]:
    sitelinks = entity.get('sitelinks', {})
    if site in sitelinks:
        return sitelinks[site].get('title')
    return None

def get_claim_values(entity: dict, prop: str) -> List[dict]:
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
    values = get_claim_values(entity, prop)
    qids = []
    for v in values:
        if v['type'] == 'wikibase-entityid':
            qid = v['value'].get('id')
            if qid:
                qids.append(qid)
    return qids

def get_first_qid(entity: dict, prop: str) -> Optional[str]:
    qids = get_qid_values(entity, prop)
    return qids[0] if qids else None

def get_coordinate(entity: dict) -> Optional[tuple]:
    values = get_claim_values(entity, 'P625')
    for v in values:
        if v['type'] == 'globecoordinate':
            coord = v['value']
            return (coord.get('latitude'), coord.get('longitude'))
    return None

def parse_time_value(time_value: dict) -> Optional[int]:
    if not time_value:
        return None
    time_str = time_value.get('time', '')
    if not time_str:
        return None
    try:
        sign = 1 if time_str[0] == '+' else -1
        year_str = time_str[1:].split('-')[0]
        year = int(year_str)
        return sign * year if year != 0 else None
    except:
        return None

def get_year(entity: dict, prop: str) -> Optional[int]:
    values = get_claim_values(entity, prop)
    for v in values:
        if v['type'] == 'time':
            year = parse_time_value(v['value'])
            if year is not None:
                return year
    return None

def get_p31_types(entity: dict) -> Set[str]:
    return set(get_qid_values(entity, 'P31'))

# ============================================
# SOURCE/MENTION GENERATION
# ============================================

def create_source_and_mention(entity: dict, entity_type: str) -> tuple:
    """엔티티에서 source와 mention 생성"""
    qid = entity['id']
    name = get_label(entity, 'en') or qid
    desc_en = get_description(entity, 'en') or ''
    desc_ko = get_description(entity, 'ko') or ''
    wiki_title = get_sitelink(entity, 'enwiki')

    # content_raw 구성: description + Wikipedia 링크 정보
    content_parts = []
    if desc_en:
        content_parts.append(f"Description: {desc_en}")
    if desc_ko:
        content_parts.append(f"Description (ko): {desc_ko}")
    if wiki_title:
        content_parts.append(f"Wikipedia: {wiki_title}")

    content_raw = '\n'.join(content_parts) if content_parts else f"Wikidata entity {qid}"

    # URL
    url = f"https://www.wikidata.org/wiki/{qid}"

    source = ExtractedSource(
        qid=qid,
        title=f"{name} - Wikidata",
        content_raw=content_raw,
        url=url
    )

    # mention: 이 source가 이 entity를 설명함
    evidence = desc_en if desc_en else f"Wikidata entity for {name}"
    mention = ExtractedMention(
        source_qid=qid,
        target_type=entity_type,
        target_qid=qid,
        evidence_raw=evidence
    )

    return source, mention

# ============================================
# ENTITY EXTRACTORS
# ============================================

def classify_entity(entity: dict) -> Optional[str]:
    p31_types = get_p31_types(entity)
    if p31_types & EXCLUDED_TYPES:
        return None
    if 'Q5' in p31_types:
        return 'person'
    for qid in p31_types:
        if qid in LOCATION_TYPES:
            coord = get_coordinate(entity)
            if coord and coord[0] is not None:
                return 'location'
    for qid in p31_types:
        if qid in TERRITORY_TYPES:
            return 'territory'
    for qid in p31_types:
        if qid in GROUP_TYPES:
            return 'group'
    for qid in p31_types:
        if qid in EVENT_TYPES:
            return 'event'
    return None

def extract_location(entity: dict) -> Optional[ExtractedLocation]:
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
        capital_qids=get_qid_values(entity, 'P36')
    )

def extract_person(entity: dict) -> Optional[ExtractedPerson]:
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
        territory_qid=get_first_qid(entity, 'P17')
    )

def extract_event(entity: dict) -> Optional[ExtractedEvent]:
    p31_types = get_p31_types(entity)
    evt_type = 'historical_event'
    for qid in p31_types:
        if qid in EVENT_TYPES:
            evt_type = EVENT_TYPES[qid]
            break
    date_start = get_year(entity, 'P585')
    date_end = None
    if date_start is None:
        date_start = get_year(entity, 'P580')
        date_end = get_year(entity, 'P582')
    if date_start is None:
        return None
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
    counts = {
        'location': 0, 'territory': 0, 'person': 0, 'group': 0, 'event': 0,
        'source': 0, 'mention': 0
    }
    limits = {k: limit // 5 if limit else None for k in ['location', 'territory', 'person', 'group', 'event']}

    processed = 0
    start_time = time.time()

    print(f"Opening dump: {DUMP_PATH}")
    print(f"Limit per entity type: {limits['location'] if limit else 'unlimited'}")
    print()

    with bz2.open(DUMP_PATH, 'rt', encoding='utf-8') as dump_file:
        with open(output_path, 'w', encoding='utf-8') as out_file:

            for line in dump_file:
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

                if processed % 100000 == 0:
                    elapsed = time.time() - start_time
                    rate = processed / elapsed
                    print(f"Processed: {processed:,} ({rate:.0f}/s) | "
                          f"L:{counts['location']} T:{counts['territory']} "
                          f"P:{counts['person']} G:{counts['group']} E:{counts['event']} "
                          f"S:{counts['source']} M:{counts['mention']}")

                if limit:
                    all_done = all(
                        counts[k] >= limits[k]
                        for k in limits if limits[k]
                    )
                    if all_done:
                        print(f"\nAll limits reached at entity #{processed:,}")
                        break

                entity_type = classify_entity(entity)
                if not entity_type:
                    continue

                if limit and counts[entity_type] >= limits[entity_type]:
                    continue

                # Extract entity
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

                    # Write entity
                    record = {'type': entity_type, 'data': asdict(extracted)}
                    out_file.write(json.dumps(record, ensure_ascii=False) + '\n')

                    # Create and write source + mention
                    source, mention = create_source_and_mention(entity, entity_type)

                    source_record = {'type': 'source', 'data': asdict(source)}
                    out_file.write(json.dumps(source_record, ensure_ascii=False) + '\n')
                    counts['source'] += 1

                    mention_record = {'type': 'mention', 'data': asdict(mention)}
                    out_file.write(json.dumps(mention_record, ensure_ascii=False) + '\n')
                    counts['mention'] += 1

    elapsed = time.time() - start_time
    print()
    print(f"=== Extraction Complete ===")
    print(f"Total processed: {processed:,}")
    print(f"Time: {elapsed:.1f}s")
    print(f"Extracted:")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    print(f"Output: {output_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract entities with sources from Wikidata dump')
    parser.add_argument('--output', '-o', required=True, help='Output JSONL file')
    parser.add_argument('--limit', '-l', type=int, help='Total limit (divided by 5 per type)')

    args = parser.parse_args()
    extract_from_dump(args.output, args.limit)
