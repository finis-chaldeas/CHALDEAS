"""
Wikidata API로 Wikipedia 타이틀 → DB ID 매핑 생성.

DB의 각 엔티티(persons, events, locations)에 대해:
1. Wikidata API로 해당 QID의 enwiki sitelink (Wikipedia 타이틀) 조회
2. wikipedia_title → (type, id) 매핑 저장

Usage:
    python build_wiki_mapping.py --batch-size 50 --output wiki_title_map.json
"""

import sys
import os
import json
import time
import argparse
import psycopg2
import requests
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}

WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
OUTPUT_DIR = 'poc/data/wikipedia_extract'


def get_wiki_titles_batch(qids):
    """Wikidata API로 QID 배치의 enwiki 타이틀 조회."""
    if not qids:
        return {}

    params = {
        'action': 'wbgetentities',
        'ids': '|'.join(qids),
        'props': 'sitelinks',
        'sitefilter': 'enwiki',
        'format': 'json'
    }

    try:
        resp = requests.get(WIKIDATA_API, params=params, timeout=30)
        data = resp.json()

        results = {}
        entities = data.get('entities', {})
        for qid, entity in entities.items():
            sitelinks = entity.get('sitelinks', {})
            if 'enwiki' in sitelinks:
                wiki_title = sitelinks['enwiki'].get('title')
                if wiki_title:
                    results[qid] = wiki_title
        return results
    except Exception as e:
        print(f"  API error: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch-size', type=int, default=50)
    parser.add_argument('--output', default='wiki_title_map.json')
    parser.add_argument('--limit', type=int, default=None, help='Limit entities to process')
    parser.add_argument('--resume', action='store_true', help='Resume from existing file')
    args = parser.parse_args()

    output_path = os.path.join(OUTPUT_DIR, args.output)

    # Load existing mapping if resuming
    existing_map = {}
    if args.resume and os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            existing_map = data.get('qid_to_title', {})
        print(f"Resuming from {len(existing_map)} existing mappings")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Collect all QIDs from DB
    all_qids = {}  # qid -> (type, id)

    print("Loading QIDs from DB...")

    cur.execute("SELECT id, wikidata_id FROM persons WHERE wikidata_id IS NOT NULL")
    for row in cur.fetchall():
        all_qids[row[1]] = ('person', row[0])
    print(f"  persons: {len([q for q in all_qids if all_qids[q][0] == 'person']):,}")

    cur.execute("SELECT id, wikidata_id FROM events WHERE wikidata_id IS NOT NULL")
    for row in cur.fetchall():
        all_qids[row[1]] = ('event', row[0])
    print(f"  events: {len([q for q in all_qids if all_qids[q][0] == 'event']):,}")

    cur.execute("SELECT id, wikidata_id FROM locations WHERE wikidata_id IS NOT NULL")
    for row in cur.fetchall():
        all_qids[row[1]] = ('location', row[0])
    print(f"  locations: {len([q for q in all_qids if all_qids[q][0] == 'location']):,}")

    print(f"Total QIDs: {len(all_qids):,}")

    # Filter out already processed
    qids_to_process = [q for q in all_qids.keys() if q not in existing_map]
    if args.limit:
        qids_to_process = qids_to_process[:args.limit]

    print(f"QIDs to process: {len(qids_to_process):,}")

    # Process in batches
    qid_to_title = dict(existing_map)
    processed = 0
    start_time = time.time()

    for i in range(0, len(qids_to_process), args.batch_size):
        batch = qids_to_process[i:i + args.batch_size]
        titles = get_wiki_titles_batch(batch)
        qid_to_title.update(titles)
        processed += len(batch)

        # Progress
        if processed % 500 == 0 or processed == len(qids_to_process):
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (len(qids_to_process) - processed) / rate if rate > 0 else 0
            print(f"  Processed: {processed:,}/{len(qids_to_process):,} ({len(qid_to_title):,} titles found) - ETA: {eta/60:.1f}min")

        # Rate limiting
        time.sleep(0.1)

        # Save periodically
        if processed % 5000 == 0:
            save_mapping(output_path, qid_to_title, all_qids)

    # Final save
    save_mapping(output_path, qid_to_title, all_qids)

    conn.close()

    print(f"\n{'='*60}")
    print("MAPPING COMPLETE")
    print(f"{'='*60}")
    print(f"Total QIDs: {len(all_qids):,}")
    print(f"Wikipedia titles found: {len(qid_to_title):,}")
    print(f"Coverage: {100*len(qid_to_title)/len(all_qids):.1f}%")
    print(f"Output: {output_path}")


def save_mapping(output_path, qid_to_title, all_qids):
    """매핑 저장 - Wikipedia 타이틀 → (type, id) 형태로."""
    # Build title -> entity mapping
    title_to_entity = {}
    for qid, wiki_title in qid_to_title.items():
        if qid in all_qids:
            entity_type, entity_id = all_qids[qid]
            # Store both original and underscore versions
            title_to_entity[wiki_title] = {'type': entity_type, 'id': entity_id, 'qid': qid}
            title_to_entity[wiki_title.replace(' ', '_')] = {'type': entity_type, 'id': entity_id, 'qid': qid}

    data = {
        'created_at': datetime.now().isoformat(),
        'total_qids': len(all_qids),
        'titles_found': len(qid_to_title),
        'qid_to_title': qid_to_title,
        'title_to_entity': title_to_entity
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
