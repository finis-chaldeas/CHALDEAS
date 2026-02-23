"""
Gap 2: 장소 이름 시간 범위 채우기

Wikidata API로 장소의 P1448(official name) + P580/P582(start/end time) 추출하여
location_names 테이블의 valid_from/valid_until 채우기.

Usage:
    cd backend
    python ../poc/scripts/fill_location_name_dates.py
"""

import sys
import os
import json
import time
import requests
import psycopg2
from pathlib import Path
from collections import defaultdict

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_URL = 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas'
CACHE_PATH = Path(r'C:\Projects\Chaldeas\poc\data\wikidata\location_names_cache.json')
WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
BATCH_SIZE = 50


def parse_year_from_time(time_value):
    """Parse year from Wikidata time value like '+1453-00-00T00:00:00Z'."""
    if not time_value:
        return None
    try:
        t = time_value.lstrip('+')
        if t.startswith('-'):
            parts = t[1:].split('-')
            return -int(parts[0])
        else:
            parts = t.split('-')
            return int(parts[0])
    except (ValueError, IndexError):
        return None


def load_locations():
    """DB에서 장소 로드."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, wikidata_id, name
        FROM locations
        WHERE wikidata_id IS NOT NULL
    """)
    locs = {}
    for row in cur.fetchall():
        locs[row[1]] = {'id': row[0], 'qid': row[1], 'name': row[2]}
    cur.close()
    conn.close()
    return locs


def fetch_wikidata_batch(qids, retries=3):
    """Wikidata API 배치 호출."""
    headers = {
        'User-Agent': 'ChaldeasBot/1.0 (https://www.chaldeas.site; chaldeas.archive@gmail.com)',
        'Accept': 'application/json',
    }
    params = {
        'action': 'wbgetentities',
        'ids': '|'.join(qids),
        'props': 'claims',
        'format': 'json',
    }
    for attempt in range(retries):
        try:
            resp = requests.get(WIKIDATA_API, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.json().get('entities', {})
        except requests.exceptions.HTTPError as e:
            if hasattr(resp, 'status_code') and resp.status_code in (429, 403):
                wait = (attempt + 1) * 2
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  API error: {e}")
                return {}
        except Exception as e:
            print(f"  API error: {e}")
            if attempt < retries - 1:
                time.sleep(1)
    return {}


def extract_named_claims(entity_data):
    """P1448 (official name) + P1705 (native label) with time qualifiers 추출."""
    claims = entity_data.get('claims', {})
    names = []

    for prop in ['P1448', 'P1705']:
        for claim in claims.get(prop, []):
            mainsnak = claim.get('mainsnak', {})
            datavalue = mainsnak.get('datavalue', {})

            if datavalue.get('type') != 'monolingualtext':
                continue

            text_value = datavalue.get('value', {})
            name = text_value.get('text', '')
            lang = text_value.get('language', '')

            if not name:
                continue

            # Extract time qualifiers
            qualifiers = claim.get('qualifiers', {})
            valid_from = None
            valid_until = None

            for q in qualifiers.get('P580', []):  # start time
                dv = q.get('datavalue', {})
                if dv.get('type') == 'time':
                    valid_from = parse_year_from_time(dv['value'].get('time'))

            for q in qualifiers.get('P582', []):  # end time
                dv = q.get('datavalue', {})
                if dv.get('type') == 'time':
                    valid_until = parse_year_from_time(dv['value'].get('time'))

            if valid_from is not None or valid_until is not None:
                names.append({
                    'name': name,
                    'language': lang,
                    'valid_from': valid_from,
                    'valid_until': valid_until,
                    'property': prop,
                })

    return names


def fetch_all_location_names(locations):
    """모든 장소의 이름 데이터 가져오기."""
    qids = list(locations.keys())
    total = len(qids)
    results = {}

    print(f"\n=== Fetching P1448/P1705 for {total} locations ===")

    for i in range(0, total, BATCH_SIZE):
        batch = qids[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

        if batch_num % 50 == 0 or batch_num == 1:
            print(f"  Batch {batch_num}/{total_batches} ({i}/{total})...")

        entities = fetch_wikidata_batch(batch)

        for qid in batch:
            entity = entities.get(qid, {})
            names = extract_named_claims(entity)
            if names:
                results[qid] = names

        time.sleep(0.2)

    print(f"  Done! Found temporal names for {len(results)} locations.")
    return results


def apply_to_db(locations, name_data):
    """결과를 DB에 적용."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    stats = {'updated': 0, 'inserted': 0, 'locations_affected': 0}

    print(f"\n=== Applying name dates for {len(name_data)} locations ===")

    for qid, names in name_data.items():
        if qid not in locations:
            continue

        loc = locations[qid]
        loc_id = loc['id']
        stats['locations_affected'] += 1

        for name_entry in names:
            name = name_entry['name']
            valid_from = name_entry['valid_from']
            valid_until = name_entry['valid_until']

            # 기존 location_names에서 매칭 시도
            cur.execute("""
                SELECT id, valid_from, valid_until
                FROM location_names
                WHERE location_id = %s AND name = %s
                LIMIT 1
            """, (loc_id, name))

            row = cur.fetchone()
            if row:
                # 기존 행 업데이트 (시간 범위가 비어있으면)
                existing_from = row[1]
                existing_until = row[2]
                if existing_from is None and valid_from is not None:
                    cur.execute("""
                        UPDATE location_names SET valid_from = %s WHERE id = %s
                    """, (valid_from, row[0]))
                    stats['updated'] += 1
                if existing_until is None and valid_until is not None:
                    cur.execute("""
                        UPDATE location_names SET valid_until = %s WHERE id = %s
                    """, (valid_until, row[0]))
                    stats['updated'] += 1
            else:
                # 새 행 삽입
                lang = name_entry.get('language', 'en')
                # 한국어/일본어가 아닌 경우만 삽입 (중복 방지)
                if lang in ('en', 'la', 'grc', 'ar', 'fa', 'tr', 'zh'):
                    cur.execute("""
                        INSERT INTO location_names
                            (location_id, name, language, valid_from, valid_until, is_primary, name_type, source)
                        VALUES (%s, %s, %s, %s, %s, false, 'official', 'wikidata_api')
                        ON CONFLICT DO NOTHING
                    """, (loc_id, name, lang, valid_from, valid_until))
                    stats['inserted'] += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"\n=== Done! ===")
    print(f"  Locations affected: {stats['locations_affected']}")
    print(f"  Names updated: {stats['updated']}")
    print(f"  Names inserted: {stats['inserted']}")
    return stats


def main():
    print("Loading locations from DB...")
    locations = load_locations()
    print(f"  Loaded {len(locations)} locations")

    # Fetch or load cache
    if CACHE_PATH.exists():
        print(f"Loading cache from {CACHE_PATH}...")
        with open(CACHE_PATH, 'r', encoding='utf-8') as f:
            name_data = json.load(f)
        print(f"  Loaded cache with {len(name_data)} locations")
    else:
        name_data = fetch_all_location_names(locations)
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(name_data, f, ensure_ascii=False)
        print(f"  Cache saved to {CACHE_PATH}")

    # Apply
    stats = apply_to_db(locations, name_data)


if __name__ == '__main__':
    main()
