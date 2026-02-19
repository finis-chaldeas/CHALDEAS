"""
통합 파이프라인 테스트
1. Wikidata에서 person 10명 추출 (전체 속성)
2. Wikipedia 제목 → QID 매핑 생성
3. Wikipedia 본문 + 하이퍼링크 추출
4. 하이퍼링크 → QID 변환
5. DB 임포트

Usage:
    python pipeline_test.py
"""

import json
import sys
import re
import psycopg2
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================
# CONFIG
# ============================================

WIKIDATA_JSON = "D:/project/wikidata/latest-all.json"
WIKIPEDIA_ZIM = "C:/Projects/Chaldeas/data/kiwix/wikipedia_en_nopic.zim"

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}

PERSON_LIMIT = 10
SCAN_LIMIT = 100000

# Property names for human readability
PROPERTY_NAMES = {
    "P22": "father", "P25": "mother", "P26": "spouse", "P40": "child",
    "P3373": "sibling", "P106": "occupation", "P39": "position_held",
    "P108": "employer", "P463": "member_of", "P607": "conflict",
    "P1344": "participant_in", "P19": "birthplace", "P20": "deathplace",
    "P569": "birth_date", "P570": "death_date", "P27": "country_of_citizenship",
    "P21": "sex_or_gender", "P31": "instance_of", "P18": "image",
}

# ============================================
# STEP 1: Extract persons from Wikidata
# ============================================

def parse_time_to_year(time_value: dict) -> Optional[int]:
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

def extract_claim_value(claim: dict) -> Optional[Dict]:
    mainsnak = claim.get('mainsnak', {})
    if mainsnak.get('snaktype') != 'value':
        return None

    datavalue = mainsnak.get('datavalue', {})
    vtype = datavalue.get('type')
    value = datavalue.get('value')

    result = {'value_type': vtype}

    if vtype == 'wikibase-entityid':
        result['value_qid'] = value.get('id')
    elif vtype == 'string':
        result['value_string'] = value
    elif vtype == 'time':
        result['value_year'] = parse_time_to_year(value)
    elif vtype == 'quantity':
        try:
            result['value_quantity'] = float(value.get('amount', 0))
        except:
            pass
    elif vtype == 'globecoordinate':
        result['value_lat'] = value.get('latitude')
        result['value_lon'] = value.get('longitude')
    elif vtype == 'monolingualtext':
        result['value_string'] = value.get('text')

    # Qualifiers
    qualifiers = claim.get('qualifiers', {})
    if 'P580' in qualifiers:
        for q in qualifiers['P580']:
            if q.get('snaktype') == 'value':
                result['qualifier_start'] = parse_time_to_year(q['datavalue']['value'])
    if 'P582' in qualifiers:
        for q in qualifiers['P582']:
            if q.get('snaktype') == 'value':
                result['qualifier_end'] = parse_time_to_year(q['datavalue']['value'])

    return result

def extract_persons_from_wikidata() -> List[Dict]:
    print(f"\n[Step 1] Wikidata에서 person 추출 (limit: {PERSON_LIMIT})")
    print(f"  Source: {WIKIDATA_JSON}")

    persons = []
    scanned = 0

    with open(WIKIDATA_JSON, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line in ['[', ']', '']:
                continue
            if line.endswith(','):
                line = line[:-1]

            scanned += 1
            if scanned % 20000 == 0:
                print(f"    Scanned {scanned:,}, found {len(persons)}")

            try:
                entity = json.loads(line)
            except:
                continue

            # Check if person
            claims = entity.get('claims', {})
            p31_claims = claims.get('P31', [])
            is_person = any(
                c.get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id') == 'Q5'
                for c in p31_claims
            )

            if not is_person:
                continue

            qid = entity.get('id')
            labels = entity.get('labels', {})
            descs = entity.get('descriptions', {})
            sitelinks = entity.get('sitelinks', {})

            # Basic info
            person = {
                'qid': qid,
                'name': labels.get('en', {}).get('value', qid),
                'name_ko': labels.get('ko', {}).get('value'),
                'description': descs.get('en', {}).get('value'),
                'description_ko': descs.get('ko', {}).get('value'),
                'wikipedia_title': sitelinks.get('enwiki', {}).get('title'),
                'properties': []
            }

            # Extract birth/death years
            for prop in ['P569', 'P570']:
                for claim in claims.get(prop, []):
                    val = extract_claim_value(claim)
                    if val and val.get('value_year'):
                        if prop == 'P569':
                            person['birth_year'] = val['value_year']
                        else:
                            person['death_year'] = val['value_year']
                        break

            # Extract all properties
            for prop, claim_list in claims.items():
                prop_name = PROPERTY_NAMES.get(prop, prop)
                for claim in claim_list:
                    val = extract_claim_value(claim)
                    if val:
                        val['property'] = prop
                        val['property_name'] = prop_name
                        person['properties'].append(val)

            persons.append(person)
            print(f"    Found: {qid} - {person['name']} ({len(person['properties'])} props)")

            if len(persons) >= PERSON_LIMIT:
                break
            if scanned >= SCAN_LIMIT:
                print(f"    Reached scan limit ({SCAN_LIMIT:,})")
                break

    print(f"  Result: {len(persons)} persons, {scanned:,} entities scanned")
    return persons

# ============================================
# STEP 2: Build QID ↔ Wikipedia mapping
# ============================================

def build_qid_wiki_mapping(persons: List[Dict]) -> Dict[str, str]:
    print(f"\n[Step 2] QID ↔ Wikipedia 매핑 생성")

    # title -> qid (for reverse lookup from links)
    title_to_qid = {}
    # qid -> title
    qid_to_title = {}

    for person in persons:
        qid = person['qid']
        title = person.get('wikipedia_title')
        if title:
            normalized = title.replace(' ', '_')
            title_to_qid[normalized] = qid
            title_to_qid[title] = qid
            qid_to_title[qid] = title

    print(f"  Mapped: {len(qid_to_title)} QID → Wikipedia")
    return title_to_qid, qid_to_title

# ============================================
# STEP 3: Extract Wikipedia content + links
# ============================================

def extract_wikipedia_content(title: str) -> Optional[Dict]:
    try:
        from libzim.reader import Archive
        from bs4 import BeautifulSoup
    except ImportError as e:
        print(f"  Error: {e}")
        return None

    zim = Archive(WIKIPEDIA_ZIM)

    try:
        entry = zim.get_entry_by_path(f"A/{title.replace(' ', '_')}")
        html = entry.get_item().content.tobytes().decode('utf-8')
    except:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    # Extract links
    links = []
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        text = a.get_text()

        if href.startswith('http') or href.startswith('#') or ':' in href:
            continue
        if not href or href.startswith('javascript'):
            continue

        target = href.replace('_', ' ')
        if text and target:
            links.append({
                'text': text,
                'target': href,  # Keep original for matching
                'target_normalized': target
            })

    # Extract plain text
    for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
        tag.decompose()
    text = soup.get_text(separator=' ', strip=True)
    text = re.sub(r'\s+', ' ', text)

    return {
        'content_raw': text,
        'content_html': html,
        'word_count': len(text.split()),
        'links': links
    }

def extract_wikipedia_for_persons(persons: List[Dict], qid_to_title: Dict) -> Dict[str, Dict]:
    print(f"\n[Step 3] Wikipedia 본문 + 링크 추출")

    wiki_data = {}

    for person in persons:
        qid = person['qid']
        title = person.get('wikipedia_title')

        if not title:
            continue

        content = extract_wikipedia_content(title)
        if content:
            wiki_data[qid] = content
            print(f"    {qid}: {content['word_count']:,} words, {len(content['links'])} links")

    print(f"  Result: {len(wiki_data)} Wikipedia articles extracted")
    return wiki_data

# ============================================
# STEP 4: Convert links to QIDs
# ============================================

def convert_links_to_mentions(wiki_data: Dict, title_to_qid: Dict, persons: List[Dict]) -> List[Dict]:
    print(f"\n[Step 4] 하이퍼링크 → QID 변환 (mentions 생성)")

    mentions = []
    matched = 0
    unmatched = 0

    for source_qid, data in wiki_data.items():
        for link in data['links']:
            target_title = link['target']
            target_qid = title_to_qid.get(target_title) or title_to_qid.get(
                target_title.replace('_', ' ')
            )

            if target_qid:
                mentions.append({
                    'source_qid': source_qid,
                    'target_qid': target_qid,
                    'link_text': link['text'],
                    'evidence_raw': f"Wikipedia link: {link['text']}"
                })
                matched += 1
            else:
                unmatched += 1

    print(f"  Matched: {matched} links → QID")
    print(f"  Unmatched: {unmatched} (target not in our dataset)")
    return mentions

# ============================================
# STEP 5: Import to DB
# ============================================

def import_to_db(persons: List[Dict], wiki_data: Dict, mentions: List[Dict]):
    print(f"\n[Step 5] DB 임포트")

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # Insert persons
        print("  Inserting persons...")
        person_ids = {}  # qid -> db_id

        for person in persons:
            cur.execute("""
                INSERT INTO persons (wikidata_id, name, name_ko, birth_year, death_year, description)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (wikidata_id) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
            """, (
                person['qid'],
                person['name'],
                person.get('name_ko'),
                person.get('birth_year'),
                person.get('death_year'),
                person.get('description')
            ))
            person_ids[person['qid']] = cur.fetchone()[0]

        print(f"    Inserted {len(person_ids)} persons")

        # Insert entity_properties
        print("  Inserting properties...")
        prop_count = 0

        for person in persons:
            person_id = person_ids[person['qid']]

            for prop in person['properties']:
                cur.execute("""
                    INSERT INTO entity_properties
                    (entity_type, entity_id, property, property_name, value_type,
                     value_qid, value_string, value_year, value_quantity, value_lat, value_lon,
                     qualifier_start_year, qualifier_end_year, wikidata_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    'person', person_id,
                    prop['property'], prop.get('property_name'),
                    prop.get('value_type'),
                    prop.get('value_qid'),
                    prop.get('value_string'),
                    prop.get('value_year'),
                    prop.get('value_quantity'),
                    prop.get('value_lat'),
                    prop.get('value_lon'),
                    prop.get('qualifier_start'),
                    prop.get('qualifier_end'),
                    person['qid']
                ))
                prop_count += 1

        print(f"    Inserted {prop_count} properties")

        # Insert sources (Wikidata + Wikipedia)
        print("  Inserting sources...")
        source_ids = {}  # (qid, type) -> db_id

        for person in persons:
            qid = person['qid']

            # Wikidata source (short description)
            cur.execute("""
                INSERT INTO sources (source_type, title, content_raw, url, wikidata_id)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (wikidata_id) DO UPDATE SET title = EXCLUDED.title
                RETURNING id
            """, (
                'wikidata',
                f"{person['name']} - Wikidata",
                person.get('description') or f"Wikidata entity {qid}",
                f"https://www.wikidata.org/wiki/{qid}",
                qid
            ))
            source_ids[(qid, 'wikidata')] = cur.fetchone()[0]

            # Wikipedia source (full text)
            if qid in wiki_data:
                wiki = wiki_data[qid]
                # Generate unique ID for Wikipedia source
                wiki_source_id = f"{qid}_wiki"

                cur.execute("""
                    INSERT INTO sources (source_type, title, content_raw, content_html, word_count, link_count, url)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    'wikipedia',
                    f"{person['name']} - Wikipedia",
                    wiki['content_raw'][:50000],  # Limit for now
                    wiki['content_html'][:100000],
                    wiki['word_count'],
                    len(wiki['links']),
                    f"https://en.wikipedia.org/wiki/{person.get('wikipedia_title', '').replace(' ', '_')}"
                ))
                source_ids[(qid, 'wikipedia')] = cur.fetchone()[0]

        print(f"    Inserted {len(source_ids)} sources")

        # Insert mentions
        print("  Inserting mentions...")
        mention_count = 0

        # Wikidata mentions (each entity mentioned by its own Wikidata page)
        for person in persons:
            qid = person['qid']
            source_id = source_ids.get((qid, 'wikidata'))
            person_id = person_ids.get(qid)

            if source_id and person_id:
                cur.execute("""
                    INSERT INTO mentions (source_id, target_type, target_id, evidence_raw)
                    VALUES (%s, %s, %s, %s)
                """, (
                    source_id, 'person', person_id,
                    person.get('description') or f"Wikidata entity {qid}"
                ))
                mention_count += 1

        # Wikipedia mentions (cross-references)
        for mention in mentions:
            source_qid = mention['source_qid']
            target_qid = mention['target_qid']

            source_id = source_ids.get((source_qid, 'wikipedia'))
            target_id = person_ids.get(target_qid)

            if source_id and target_id:
                cur.execute("""
                    INSERT INTO mentions (source_id, target_type, target_id, evidence_raw, link_text)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    source_id, 'person', target_id,
                    mention['evidence_raw'],
                    mention['link_text']
                ))
                mention_count += 1

        print(f"    Inserted {mention_count} mentions")

        conn.commit()
        print("  Committed!")

    except Exception as e:
        conn.rollback()
        print(f"  Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()

# ============================================
# STEP 6: Verify
# ============================================

def verify_import():
    print(f"\n[Step 6] 검증")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Count tables
    tables = ['persons', 'sources', 'mentions', 'entity_properties']

    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  {table}: {count}")

    # Check mention coverage
    cur.execute("""
        SELECT COUNT(*) FROM persons p
        WHERE NOT EXISTS (
            SELECT 1 FROM mentions m
            WHERE m.target_type = 'person' AND m.target_id = p.id
        )
    """)
    no_mention = cur.fetchone()[0]
    print(f"\n  Persons without mentions: {no_mention}")

    # Sample data
    print("\n  Sample person with properties:")
    cur.execute("""
        SELECT p.name, p.wikidata_id,
               (SELECT COUNT(*) FROM entity_properties ep WHERE ep.entity_type='person' AND ep.entity_id=p.id) as prop_count,
               (SELECT COUNT(*) FROM mentions m WHERE m.target_type='person' AND m.target_id=p.id) as mention_count
        FROM persons p
        LIMIT 3
    """)
    for row in cur.fetchall():
        print(f"    {row[0]} ({row[1]}): {row[2]} props, {row[3]} mentions")

    # Sample Wikipedia mention
    print("\n  Sample Wikipedia cross-reference:")
    cur.execute("""
        SELECT s.title, p.name, m.link_text
        FROM mentions m
        JOIN sources s ON m.source_id = s.id
        JOIN persons p ON m.target_id = p.id AND m.target_type = 'person'
        WHERE s.source_type = 'wikipedia' AND m.link_text IS NOT NULL
        LIMIT 3
    """)
    for row in cur.fetchall():
        print(f"    {row[0]} → {row[1]} (link: \"{row[2]}\")")

    cur.close()
    conn.close()

# ============================================
# MAIN
# ============================================

def main():
    print("=" * 70)
    print("통합 파이프라인 테스트")
    print("=" * 70)

    # Step 1: Extract from Wikidata
    persons = extract_persons_from_wikidata()

    # Step 2: Build mapping
    title_to_qid, qid_to_title = build_qid_wiki_mapping(persons)

    # Step 3: Extract Wikipedia
    wiki_data = extract_wikipedia_for_persons(persons, qid_to_title)

    # Step 4: Convert links to mentions
    mentions = convert_links_to_mentions(wiki_data, title_to_qid, persons)

    # Step 5: Import to DB
    import_to_db(persons, wiki_data, mentions)

    # Step 6: Verify
    verify_import()

    print("\n" + "=" * 70)
    print("파이프라인 테스트 완료!")
    print("=" * 70)

if __name__ == '__main__':
    main()
