"""
Gap 4: 이벤트 위치 보강

primary_location_id가 없는 7,060개 이벤트에 대해
Wikidata API에서 P276(location), P625(coordinates)를 가져와서 위치 설정.

Usage:
    cd backend
    python ../poc/scripts/fill_event_locations.py
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
CACHE_PATH = Path(r'C:\Projects\Chaldeas\poc\data\wikidata\event_locations_cache.json')
WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
BATCH_SIZE = 50


def load_events_without_location():
    """위치 없는 이벤트 로드."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, wikidata_id, title
        FROM events
        WHERE primary_location_id IS NULL AND wikidata_id IS NOT NULL
    """)
    events = {}
    for row in cur.fetchall():
        events[row[1]] = {'id': row[0], 'qid': row[1], 'title': row[2]}
    cur.close()
    conn.close()
    return events


def load_location_qid_map():
    """QID → location_id 매핑."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT wikidata_id, id FROM locations WHERE wikidata_id IS NOT NULL")
    qid_map = {r[0]: r[1] for r in cur.fetchall()}
    cur.close()
    conn.close()
    return qid_map


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


def extract_location_claims(entity_data):
    """P276 (location), P625 (coordinates), P17 (country) 추출."""
    claims = entity_data.get('claims', {})
    result = {'location_qids': [], 'coordinates': None, 'country_qids': []}

    # P276: location
    for claim in claims.get('P276', []):
        dv = claim.get('mainsnak', {}).get('datavalue', {})
        if dv.get('type') == 'wikibase-entityid':
            qid = 'Q' + str(dv['value']['numeric-id'])
            result['location_qids'].append(qid)

    # P625: coordinate location
    for claim in claims.get('P625', []):
        dv = claim.get('mainsnak', {}).get('datavalue', {})
        if dv.get('type') == 'globecoordinate':
            result['coordinates'] = {
                'lat': dv['value']['latitude'],
                'lng': dv['value']['longitude'],
            }
            break

    # P17: country (fallback)
    for claim in claims.get('P17', []):
        dv = claim.get('mainsnak', {}).get('datavalue', {})
        if dv.get('type') == 'wikibase-entityid':
            qid = 'Q' + str(dv['value']['numeric-id'])
            result['country_qids'].append(qid)

    return result


def fetch_all_location_data(events):
    """위치 없는 이벤트들의 위치 데이터 가져오기."""
    qids = list(events.keys())
    total = len(qids)
    results = {}

    print(f"\n=== Fetching P276/P625/P17 for {total} events ===")

    for i in range(0, total, BATCH_SIZE):
        batch = qids[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

        if batch_num % 50 == 0 or batch_num == 1:
            print(f"  Batch {batch_num}/{total_batches} ({i}/{total})...")

        entities = fetch_wikidata_batch(batch)

        for qid in batch:
            entity = entities.get(qid, {})
            loc_data = extract_location_claims(entity)
            if loc_data['location_qids'] or loc_data['coordinates'] or loc_data['country_qids']:
                results[qid] = loc_data

        time.sleep(0.2)

    print(f"  Done! Found location data for {len(results)} events.")
    return results


def apply_to_db(events, location_data, loc_qid_map):
    """위치 데이터를 DB에 적용."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    stats = defaultdict(int)

    print(f"\n=== Applying locations for {len(location_data)} events ===")

    for qid, loc_info in location_data.items():
        if qid not in events:
            continue

        event = events[qid]
        event_id = event['id']
        matched_location_id = None

        # 1차: P276 location → DB 매칭
        for loc_qid in loc_info.get('location_qids', []):
            if loc_qid in loc_qid_map:
                matched_location_id = loc_qid_map[loc_qid]
                stats['matched_p276'] += 1
                break

        # 2차: P17 country → DB 매칭 (폴백)
        if not matched_location_id:
            for country_qid in loc_info.get('country_qids', []):
                if country_qid in loc_qid_map:
                    matched_location_id = loc_qid_map[country_qid]
                    stats['matched_p17'] += 1
                    break

        # 3차: P625 coordinates → 가장 가까운 DB 장소 (느리므로 스킵)
        # TODO: 필요시 구현

        if matched_location_id:
            cur.execute("""
                UPDATE events SET primary_location_id = %s WHERE id = %s
            """, (matched_location_id, event_id))
            stats['updated'] += 1
        else:
            stats['no_match'] += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"\n=== Done! ===")
    for key in sorted(stats.keys()):
        print(f"  {key}: {stats[key]}")
    return stats


def main():
    print("Loading events without location...")
    events = load_events_without_location()
    print(f"  Found {len(events)} events without primary_location_id")

    if not events:
        print("  All events have locations. Nothing to do.")
        return

    print("Loading location QID map...")
    loc_qid_map = load_location_qid_map()
    print(f"  {len(loc_qid_map)} locations with QIDs")

    # Fetch or load cache
    if CACHE_PATH.exists():
        print(f"Loading cache from {CACHE_PATH}...")
        with open(CACHE_PATH, 'r', encoding='utf-8') as f:
            location_data = json.load(f)
        print(f"  Loaded cache with {len(location_data)} entries")
    else:
        location_data = fetch_all_location_data(events)
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(location_data, f, ensure_ascii=False)
        print(f"  Cache saved to {CACHE_PATH}")

    # Apply
    apply_to_db(events, location_data, loc_qid_map)


if __name__ == '__main__':
    main()
