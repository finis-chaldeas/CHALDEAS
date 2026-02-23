"""
Gap 1: 이벤트 계층 채우기

Wikidata API로 모든 이벤트의 P361(part of) + P31(instance of)을 가져와서:
- parent_event_id 설정
- hierarchy_level 분류 (1=시대, 2=전쟁, 3=전투/사건)
- temporal_scale 분류 (longue_duree, conjuncture, evenementielle)
- is_aggregate 마킹

Usage:
    cd backend
    python ../poc/scripts/fill_event_hierarchy.py
    python ../poc/scripts/fill_event_hierarchy.py --fetch-only   # API만 호출, DB 미수정
    python ../poc/scripts/fill_event_hierarchy.py --apply-only   # 캐시에서 DB 수정
"""

import sys
import os
import json
import time
import argparse
import requests
import psycopg2
from pathlib import Path
from collections import defaultdict

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_URL = 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas'
CACHE_PATH = Path(r'C:\Projects\Chaldeas\poc\data\wikidata\event_hierarchy_cache.json')
WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
BATCH_SIZE = 50

# ═══════════════════════════════════════════
# P31 (instance of) → hierarchy_level + temporal_scale 매핑
# ═══════════════════════════════════════════

P31_CLASSIFICATION = {
    # Level 1 (longue_duree) — 시대, 문명, 대규모 구조
    'Q11514315': (1, 'longue_duree', 'historical_period'),
    'Q12136': (1, 'longue_duree', 'historical_era'),      # era (not found often)
    'Q6428674': (1, 'longue_duree', 'historical_period'),  # historical period (general)

    # Level 2 (conjuncture) — 전쟁, 혁명, 운동
    'Q198': (2, 'conjuncture', 'war'),
    'Q180684': (2, 'conjuncture', 'military_conflict'),
    'Q8465': (2, 'conjuncture', 'civil_war'),
    'Q10931': (2, 'conjuncture', 'revolution'),
    'Q124734': (2, 'conjuncture', 'rebellion'),
    'Q173065': (2, 'conjuncture', 'crusade'),
    'Q2401485': (2, 'conjuncture', 'expedition'),
    'Q831663': (2, 'conjuncture', 'religious_conflict'),
    'Q1348639': (2, 'conjuncture', 'conquest'),

    # Level 3 (evenementielle) — 개별 사건
    'Q178561': (3, 'evenementielle', 'battle'),
    'Q188055': (3, 'evenementielle', 'siege'),
    'Q131569': (3, 'evenementielle', 'treaty'),
    'Q45382': (3, 'evenementielle', 'coup'),
    'Q3882219': (3, 'evenementielle', 'assassination'),
    'Q209480': (3, 'evenementielle', 'coronation'),
    'Q3199915': (3, 'evenementielle', 'massacre'),
    'Q192909': (3, 'evenementielle', 'natural_disaster'),
    'Q5389': (3, 'evenementielle', 'earthquake'),
    'Q168983': (3, 'evenementielle', 'epidemic'),
    'Q13418847': (3, 'evenementielle', 'historical_event'),
    'Q1190554': (3, 'evenementielle', 'occurrence'),
    'Q1656682': (3, 'evenementielle', 'event'),
}

# 제목 패턴 → 분류 (P31 폴백)
TITLE_PATTERNS = [
    # Level 3 patterns
    ('Battle of ', 3, 'evenementielle'),
    ('Siege of ', 3, 'evenementielle'),
    ('Treaty of ', 3, 'evenementielle'),
    ('Assassination of ', 3, 'evenementielle'),
    ('Execution of ', 3, 'evenementielle'),
    ('Coronation of ', 3, 'evenementielle'),
    ('Death of ', 3, 'evenementielle'),
    ('Birth of ', 3, 'evenementielle'),
    ('Fall of ', 3, 'evenementielle'),
    ('Sack of ', 3, 'evenementielle'),
    ('Bombing of ', 3, 'evenementielle'),
    # Level 2 patterns
    ('War of ', 2, 'conjuncture'),
    (' War', 2, 'conjuncture'),
    (' Wars', 2, 'conjuncture'),
    ('Revolution', 2, 'conjuncture'),
    ('Rebellion', 2, 'conjuncture'),
    ('Revolt', 2, 'conjuncture'),
    ('Crusade', 2, 'conjuncture'),
    ('Conquest of ', 2, 'conjuncture'),
    ('Invasion of ', 2, 'conjuncture'),
    ('Campaign', 2, 'conjuncture'),
]


def load_event_qids():
    """DB에서 모든 이벤트의 QID와 메타데이터를 로드."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, wikidata_id, title, date_start, date_end,
               hierarchy_level, parent_event_id, temporal_scale
        FROM events
        WHERE wikidata_id IS NOT NULL
    """)
    events = {}
    for row in cur.fetchall():
        events[row[1]] = {
            'id': row[0],
            'qid': row[1],
            'title': row[2],
            'date_start': row[3],
            'date_end': row[4],
            'current_level': row[5],
            'current_parent': row[6],
            'current_scale': row[7],
        }
    cur.close()
    conn.close()
    return events


def fetch_wikidata_batch(qids, retries=3):
    """Wikidata API에서 배치로 P361, P31 가져오기."""
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
            if resp.status_code == 429 or resp.status_code == 403:
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


def extract_claims(entity_data, prop):
    """엔티티 데이터에서 특정 속성의 QID 값들을 추출."""
    claims = entity_data.get('claims', {})
    values = []
    for claim in claims.get(prop, []):
        mainsnak = claim.get('mainsnak', {})
        datavalue = mainsnak.get('datavalue', {})
        if datavalue.get('type') == 'wikibase-entityid':
            qid = 'Q' + str(datavalue['value']['numeric-id'])
            values.append(qid)
    return values


def fetch_all_hierarchy_data(events):
    """모든 이벤트의 P361/P31을 Wikidata API에서 가져오기."""
    qids = list(events.keys())
    total = len(qids)
    results = {}

    print(f"\n=== Fetching P361/P31 for {total} events from Wikidata API ===")
    print(f"    Batches: {(total + BATCH_SIZE - 1) // BATCH_SIZE}")

    for i in range(0, total, BATCH_SIZE):
        batch = qids[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

        if batch_num % 50 == 0 or batch_num == 1:
            print(f"  Batch {batch_num}/{total_batches} ({i}/{total})...")

        entities = fetch_wikidata_batch(batch)

        for qid in batch:
            entity = entities.get(qid, {})
            p361 = extract_claims(entity, 'P361')  # part of
            p31 = extract_claims(entity, 'P31')    # instance of
            results[qid] = {'part_of': p361, 'instance_of': p31}

        # Rate limiting: ~5 req/sec
        time.sleep(0.2)

    print(f"  Done! Fetched data for {len(results)} events.")
    return results


def classify_event(event, wikidata):
    """이벤트를 분류하여 hierarchy_level, temporal_scale, parent 후보 반환."""
    result = {
        'hierarchy_level': None,
        'temporal_scale': None,
        'parent_qids': [],
        'classification_source': None,
        'event_type': None,
    }

    # Part of (parent 후보)
    part_of = wikidata.get('part_of', [])
    result['parent_qids'] = part_of

    # 1차: P31 (instance of) 기반 분류
    instance_of = wikidata.get('instance_of', [])
    for p31_qid in instance_of:
        if p31_qid in P31_CLASSIFICATION:
            level, scale, etype = P31_CLASSIFICATION[p31_qid]
            result['hierarchy_level'] = level
            result['temporal_scale'] = scale
            result['classification_source'] = f'P31:{p31_qid}'
            result['event_type'] = etype
            return result

    # 2차: 제목 패턴 기반 분류
    title = event.get('title', '')
    for pattern, level, scale in TITLE_PATTERNS:
        if pattern in title:
            result['hierarchy_level'] = level
            result['temporal_scale'] = scale
            result['classification_source'] = f'title:{pattern.strip()}'
            return result

    # 3차: date_span 기반 분류
    date_start = event.get('date_start')
    date_end = event.get('date_end')
    if date_start is not None and date_end is not None:
        span = abs(date_end - date_start)
        if span > 50:
            result['hierarchy_level'] = 1
            result['temporal_scale'] = 'longue_duree'
            result['classification_source'] = f'span:{span}y'
        elif span > 10:
            result['hierarchy_level'] = 2
            result['temporal_scale'] = 'conjuncture'
            result['classification_source'] = f'span:{span}y'
        elif span >= 1:
            result['hierarchy_level'] = 2
            result['temporal_scale'] = 'conjuncture'
            result['classification_source'] = f'span:{span}y'
        else:
            result['hierarchy_level'] = 3
            result['temporal_scale'] = 'evenementielle'
            result['classification_source'] = 'span:0'
    else:
        # 폴백: 단일 시점 이벤트 → evenementielle
        result['hierarchy_level'] = 3
        result['temporal_scale'] = 'evenementielle'
        result['classification_source'] = 'default'

    return result


def apply_to_db(events, wikidata_cache):
    """분류 결과를 DB에 적용."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # QID → event_id 매핑
    qid_to_id = {qid: ev['id'] for qid, ev in events.items()}

    stats = defaultdict(int)
    parent_set = set()
    updates = []

    print("\n=== Classifying events ===")

    for qid, event in events.items():
        wd = wikidata_cache.get(qid, {'part_of': [], 'instance_of': []})
        classification = classify_event(event, wd)

        # parent_event_id 결정
        parent_id = None
        for parent_qid in classification['parent_qids']:
            if parent_qid in qid_to_id:
                parent_id = qid_to_id[parent_qid]
                parent_set.add(parent_id)
                break

        updates.append({
            'event_id': event['id'],
            'hierarchy_level': classification['hierarchy_level'],
            'temporal_scale': classification['temporal_scale'],
            'parent_event_id': parent_id,
            'source': classification['classification_source'],
        })

        stats[f"level_{classification['hierarchy_level']}"] += 1
        stats[f"scale_{classification['temporal_scale']}"] += 1
        if parent_id:
            stats['has_parent'] += 1
        stats[f"src_{classification['classification_source'].split(':')[0]}"] += 1

    # 통계 출력
    print(f"\n--- Classification Stats ---")
    for key in sorted(stats.keys()):
        print(f"  {key}: {stats[key]}")

    # DB 업데이트
    print(f"\n=== Applying {len(updates)} updates to DB ===")

    updated = 0
    for u in updates:
        cur.execute("""
            UPDATE events
            SET hierarchy_level = %s,
                temporal_scale = %s,
                parent_event_id = %s
            WHERE id = %s
        """, (
            u['hierarchy_level'],
            u['temporal_scale'],
            u['parent_event_id'],
            u['event_id'],
        ))
        updated += 1
        if updated % 5000 == 0:
            print(f"  Updated {updated}/{len(updates)}...")
            conn.commit()

    # is_aggregate 마킹: parent가 된 이벤트
    print(f"\n=== Marking {len(parent_set)} aggregate events ===")
    if parent_set:
        cur.execute("""
            UPDATE events SET is_aggregate = true WHERE id = ANY(%s)
        """, (list(parent_set),))

    # 나머지는 is_aggregate = false
    cur.execute("""
        UPDATE events SET is_aggregate = false WHERE id != ALL(%s)
    """, (list(parent_set),))

    conn.commit()
    cur.close()
    conn.close()

    print(f"\n=== Done! ===")
    print(f"  Total events updated: {updated}")
    print(f"  Events with parent: {stats.get('has_parent', 0)}")
    print(f"  Aggregate events: {len(parent_set)}")

    return stats


def main():
    parser = argparse.ArgumentParser(description='Fill event hierarchy from Wikidata')
    parser.add_argument('--fetch-only', action='store_true', help='Only fetch from API, save cache')
    parser.add_argument('--apply-only', action='store_true', help='Only apply from cache to DB')
    args = parser.parse_args()

    # 1. Load events from DB
    print("Loading events from DB...")
    events = load_event_qids()
    print(f"  Loaded {len(events)} events")

    # 2. Fetch or load cache
    if args.apply_only and CACHE_PATH.exists():
        print(f"Loading cache from {CACHE_PATH}...")
        with open(CACHE_PATH, 'r', encoding='utf-8') as f:
            wikidata_cache = json.load(f)
        print(f"  Loaded {len(wikidata_cache)} cached entries")
    else:
        wikidata_cache = fetch_all_hierarchy_data(events)

        # Save cache
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(wikidata_cache, f, ensure_ascii=False)
        print(f"  Cache saved to {CACHE_PATH}")

    if args.fetch_only:
        print("Fetch-only mode. Exiting.")
        return

    # 3. Apply to DB
    stats = apply_to_db(events, wikidata_cache)

    # 4. Print summary
    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"{'='*50}")
    for key in sorted(stats.keys()):
        print(f"  {key}: {stats[key]}")


if __name__ == '__main__':
    main()
