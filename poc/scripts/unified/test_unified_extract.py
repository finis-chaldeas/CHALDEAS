"""
통합 추출 테스트
- Wikidata: 전체 속성 추출
- Wikipedia: 본문 + 하이퍼링크 추출

Usage:
    python test_unified_extract.py
"""

import json
import sys
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict

# Windows encoding fix
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================
# CONFIG
# ============================================

WIKIDATA_JSON = "D:/project/wikidata/latest-all.json"
WIKIPEDIA_ZIM = "C:/Projects/Chaldeas/data/kiwix/wikipedia_en_nopic.zim"
OUTPUT_DIR = Path("C:/Projects/Chaldeas/poc/data/unified")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Test targets - famous historical figures with Wikipedia articles
TEST_QIDS = [
    "Q8409",   # Alexander the Great
    "Q859",    # Aristotle
    "Q8877",   # Philip II of Macedon
    "Q1001",   # Julius Caesar
    "Q5879",   # Cleopatra
]

# Wikidata property definitions
PROPERTY_NAMES = {
    # Family
    "P22": "father", "P25": "mother", "P26": "spouse", "P40": "child",
    "P3373": "sibling", "P451": "partner", "P1038": "relative",
    # Career
    "P106": "occupation", "P39": "position_held", "P108": "employer",
    "P463": "member_of", "P102": "political_party", "P140": "religion",
    "P69": "educated_at", "P512": "academic_degree",
    # Events
    "P607": "conflict", "P1344": "participant_in", "P793": "significant_event",
    # Space
    "P625": "coordinate", "P17": "country", "P131": "located_in",
    "P276": "location", "P19": "birthplace", "P20": "deathplace",
    "P119": "burial_place", "P551": "residence", "P937": "work_location",
    # Time
    "P569": "birth_date", "P570": "death_date", "P580": "start_time",
    "P582": "end_time", "P585": "point_in_time", "P571": "inception",
    "P576": "dissolved",
    # Hierarchy
    "P361": "part_of", "P527": "has_part", "P155": "follows",
    "P156": "followed_by", "P279": "subclass_of", "P31": "instance_of",
    # External
    "P18": "image", "P373": "commons_category",
}

# ============================================
# DATA CLASSES
# ============================================

@dataclass
class WikidataEntity:
    qid: str
    name: str
    name_ko: Optional[str]
    description: Optional[str]
    description_ko: Optional[str]
    wikipedia_title: Optional[str]
    entity_type: str  # person, location, etc.
    properties: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class WikipediaSource:
    qid: str
    title: str
    content_raw: str  # plain text
    content_html: str  # original HTML
    word_count: int
    links: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class WikidataSource:
    qid: str
    title: str
    content_raw: str  # short description

@dataclass
class Mention:
    source_qid: str
    source_type: str  # wikidata or wikipedia
    target_qid: str
    target_type: str  # person, location, etc.
    evidence_raw: str
    link_text: Optional[str] = None
    position_start: Optional[int] = None
    position_end: Optional[int] = None

# ============================================
# WIKIDATA EXTRACTION
# ============================================

def parse_time_to_year(time_value: dict) -> Optional[int]:
    """Parse Wikidata time to year (BCE as negative)"""
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

def extract_property_value(claim: dict) -> Dict[str, Any]:
    """Extract value from a Wikidata claim"""
    mainsnak = claim.get('mainsnak', {})
    if mainsnak.get('snaktype') != 'value':
        return None

    datavalue = mainsnak.get('datavalue', {})
    value_type = datavalue.get('type')
    value = datavalue.get('value')

    result = {'value_type': value_type}

    if value_type == 'wikibase-entityid':
        result['value_qid'] = value.get('id')
    elif value_type == 'string':
        result['value_string'] = value
    elif value_type == 'time':
        result['value_year'] = parse_time_to_year(value)
    elif value_type == 'quantity':
        result['value_quantity'] = float(value.get('amount', 0))
    elif value_type == 'globecoordinate':
        result['value_lat'] = value.get('latitude')
        result['value_lon'] = value.get('longitude')
    elif value_type == 'monolingualtext':
        result['value_string'] = value.get('text')
    else:
        result['value_string'] = str(value)

    # Extract qualifiers (start/end time)
    qualifiers = claim.get('qualifiers', {})
    if 'P580' in qualifiers:  # start time
        for q in qualifiers['P580']:
            if q.get('snaktype') == 'value':
                result['qualifier_start_year'] = parse_time_to_year(
                    q['datavalue']['value']
                )
    if 'P582' in qualifiers:  # end time
        for q in qualifiers['P582']:
            if q.get('snaktype') == 'value':
                result['qualifier_end_year'] = parse_time_to_year(
                    q['datavalue']['value']
                )

    return result

def extract_wikidata_entity(entity: dict) -> Optional[WikidataEntity]:
    """Extract all properties from a Wikidata entity"""
    qid = entity.get('id')
    if not qid:
        return None

    # Labels
    labels = entity.get('labels', {})
    name = labels.get('en', {}).get('value') or qid
    name_ko = labels.get('ko', {}).get('value')

    # Descriptions
    descs = entity.get('descriptions', {})
    desc = descs.get('en', {}).get('value')
    desc_ko = descs.get('ko', {}).get('value')

    # Wikipedia title
    sitelinks = entity.get('sitelinks', {})
    wiki_title = sitelinks.get('enwiki', {}).get('title')

    # Determine entity type from P31
    p31_values = []
    for claim in entity.get('claims', {}).get('P31', []):
        val = extract_property_value(claim)
        if val and val.get('value_qid'):
            p31_values.append(val['value_qid'])

    entity_type = 'unknown'
    if 'Q5' in p31_values:
        entity_type = 'person'
    # Add more type detection as needed

    # Extract ALL properties
    properties = []
    claims = entity.get('claims', {})

    for prop, claim_list in claims.items():
        prop_name = PROPERTY_NAMES.get(prop, prop)

        for claim in claim_list:
            val = extract_property_value(claim)
            if val:
                val['property'] = prop
                val['property_name'] = prop_name
                properties.append(val)

    return WikidataEntity(
        qid=qid,
        name=name,
        name_ko=name_ko,
        description=desc,
        description_ko=desc_ko,
        wikipedia_title=wiki_title,
        entity_type=entity_type,
        properties=properties
    )

def find_entities_in_wikidata(target_qids: set) -> Dict[str, WikidataEntity]:
    """Find specific entities in Wikidata JSON dump"""
    found = {}

    print(f"Searching for {len(target_qids)} entities in Wikidata...")
    print(f"Reading from: {WIKIDATA_JSON}")

    with open(WIKIDATA_JSON, 'r', encoding='utf-8') as f:
        line_count = 0
        for line in f:
            line = line.strip()
            if line in ['[', ']', '']:
                continue
            if line.endswith(','):
                line = line[:-1]

            line_count += 1
            if line_count % 100000 == 0:
                print(f"  Scanned {line_count:,} lines, found {len(found)}/{len(target_qids)}")

            # Quick check before parsing
            if not any(qid in line for qid in target_qids - set(found.keys())):
                continue

            try:
                entity = json.loads(line)
                qid = entity.get('id')
                if qid in target_qids and qid not in found:
                    extracted = extract_wikidata_entity(entity)
                    if extracted:
                        found[qid] = extracted
                        print(f"  Found: {qid} - {extracted.name}")

                    if len(found) == len(target_qids):
                        print(f"  All entities found at line {line_count:,}")
                        break
            except json.JSONDecodeError:
                continue

    return found

# ============================================
# WIKIPEDIA EXTRACTION
# ============================================

def extract_wikipedia_content(title: str) -> Optional[WikipediaSource]:
    """Extract content and links from Wikipedia ZIM"""
    try:
        from libzim.reader import Archive
        from bs4 import BeautifulSoup
    except ImportError as e:
        print(f"Missing dependency: {e}")
        return None

    try:
        zim = Archive(WIKIPEDIA_ZIM)
    except Exception as e:
        print(f"Failed to open ZIM: {e}")
        return None

    # Try to find the article
    # ZIM paths vary, try common patterns
    paths_to_try = [
        f"A/{title.replace(' ', '_')}",
        f"{title.replace(' ', '_')}",
        f"A/{title}",
    ]

    entry = None
    for path in paths_to_try:
        try:
            entry = zim.get_entry_by_path(path)
            break
        except:
            continue

    if not entry:
        print(f"  Wikipedia article not found: {title}")
        return None

    try:
        html = entry.get_item().content.tobytes().decode('utf-8')
    except:
        return None

    # Parse HTML
    soup = BeautifulSoup(html, 'html.parser')

    # Extract links
    links = []
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        text = a.get_text()

        # Internal wiki links
        if href.startswith('../A/') or href.startswith('/A/'):
            target = href.split('/')[-1].replace('_', ' ')

            # Find position in text
            links.append({
                'text': text,
                'target_title': target,
                'href': href
            })

    # Extract plain text
    # Remove script, style, nav elements
    for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
        tag.decompose()

    text = soup.get_text(separator=' ', strip=True)
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)

    return WikipediaSource(
        qid='',  # Will be filled later
        title=title,
        content_raw=text,
        content_html=html,
        word_count=len(text.split()),
        links=links
    )

# ============================================
# BUILD QID MAPPING
# ============================================

def build_title_to_qid_map(entities: Dict[str, WikidataEntity]) -> Dict[str, str]:
    """Build Wikipedia title -> QID mapping"""
    mapping = {}
    for qid, entity in entities.items():
        if entity.wikipedia_title:
            mapping[entity.wikipedia_title.replace(' ', '_')] = qid
            mapping[entity.wikipedia_title] = qid
    return mapping

# ============================================
# CREATE SOURCES AND MENTIONS
# ============================================

def create_wikidata_source(entity: WikidataEntity) -> WikidataSource:
    """Create Wikidata source (short description)"""
    content = entity.description or f"Wikidata entity {entity.qid}"
    if entity.description_ko:
        content += f"\n{entity.description_ko}"

    return WikidataSource(
        qid=entity.qid,
        title=f"{entity.name} - Wikidata",
        content_raw=content
    )

def create_mentions_from_wikipedia(
    wiki_source: WikipediaSource,
    source_qid: str,
    title_to_qid: Dict[str, str]
) -> List[Mention]:
    """Create mentions from Wikipedia hyperlinks"""
    mentions = []

    for link in wiki_source.links:
        target_title = link['target_title']
        target_qid = title_to_qid.get(target_title) or title_to_qid.get(
            target_title.replace(' ', '_')
        )

        if target_qid:
            # Extract context around link
            link_text = link['text']

            mentions.append(Mention(
                source_qid=source_qid,
                source_type='wikipedia',
                target_qid=target_qid,
                target_type='unknown',  # Would need lookup
                evidence_raw=f"Link: {link_text}",
                link_text=link_text
            ))

    return mentions

# ============================================
# MAIN
# ============================================

def main():
    print("=" * 60)
    print("통합 추출 테스트")
    print("=" * 60)

    # Step 1: Find entities in Wikidata
    print("\n[1/4] Wikidata 엔티티 추출...")
    entities = find_entities_in_wikidata(set(TEST_QIDS))
    print(f"Found {len(entities)} entities")

    for qid, entity in entities.items():
        print(f"  {qid}: {entity.name}")
        print(f"    - Properties: {len(entity.properties)}")
        print(f"    - Wikipedia: {entity.wikipedia_title}")

    # Step 2: Build title->QID mapping
    print("\n[2/4] QID 매핑 생성...")
    title_to_qid = build_title_to_qid_map(entities)
    print(f"Mapped {len(title_to_qid)} titles")

    # Step 3: Extract Wikipedia content
    print("\n[3/4] Wikipedia 본문 추출...")
    wiki_sources = {}

    for qid, entity in entities.items():
        if entity.wikipedia_title:
            print(f"  Extracting: {entity.wikipedia_title}")
            wiki = extract_wikipedia_content(entity.wikipedia_title)
            if wiki:
                wiki.qid = qid
                wiki_sources[qid] = wiki
                print(f"    - Words: {wiki.word_count:,}")
                print(f"    - Links: {len(wiki.links)}")

    # Step 4: Create output
    print("\n[4/4] 결과 저장...")

    output_file = OUTPUT_DIR / "test_unified.jsonl"

    with open(output_file, 'w', encoding='utf-8') as f:
        # Write entities with all properties
        for qid, entity in entities.items():
            record = {
                'type': 'entity',
                'data': asdict(entity)
            }
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

        # Write Wikidata sources (short description)
        for qid, entity in entities.items():
            wd_source = create_wikidata_source(entity)
            record = {
                'type': 'source_wikidata',
                'data': asdict(wd_source)
            }
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

        # Write Wikipedia sources (full text)
        for qid, wiki in wiki_sources.items():
            record = {
                'type': 'source_wikipedia',
                'data': {
                    'qid': wiki.qid,
                    'title': f"{wiki.title} - Wikipedia",
                    'content_raw': wiki.content_raw[:5000] + '...' if len(wiki.content_raw) > 5000 else wiki.content_raw,
                    'word_count': wiki.word_count,
                    'link_count': len(wiki.links)
                }
            }
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

        # Write mentions from Wikipedia links
        mention_count = 0
        for qid, wiki in wiki_sources.items():
            mentions = create_mentions_from_wikipedia(wiki, qid, title_to_qid)
            for mention in mentions:
                record = {
                    'type': 'mention',
                    'data': asdict(mention)
                }
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
                mention_count += 1

    print(f"\nOutput: {output_file}")

    # Summary
    print("\n" + "=" * 60)
    print("결과 요약")
    print("=" * 60)
    print(f"Entities: {len(entities)}")
    print(f"  - Total properties: {sum(len(e.properties) for e in entities.values())}")
    print(f"Sources (Wikidata): {len(entities)}")
    print(f"Sources (Wikipedia): {len(wiki_sources)}")
    print(f"  - Total words: {sum(w.word_count for w in wiki_sources.values()):,}")
    print(f"  - Total links: {sum(len(w.links) for w in wiki_sources.values()):,}")
    print(f"Mentions (cross-links): {mention_count}")

if __name__ == '__main__':
    main()
