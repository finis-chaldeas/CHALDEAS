"""
분류된 연결을 wiki_connections 테이블에 저장.
evidence_text, source_url 등 완전한 정보 포함.

Usage:
    python save_to_wiki_connections.py extract_*.json classified_*.json --dry-run
    python save_to_wiki_connections.py extract_*.json classified_*.json --save
"""

import sys
import os
import json
import argparse
import psycopg2
from datetime import datetime
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

INPUT_DIR = 'poc/data/wikipedia_extract'

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}


def load_json(filepath):
    path = os.path.join(INPUT_DIR, filepath) if not os.path.isabs(filepath) else filepath
    if not os.path.exists(path):
        path = filepath
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_event_id_by_qid(cur, qid):
    cur.execute("SELECT id FROM events WHERE wikidata_id = %s", (qid,))
    row = cur.fetchone()
    return row[0] if row else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('extract_file', help='추출 결과 JSON')
    parser.add_argument('classified_file', help='분류 결과 JSON')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--save', action='store_true')
    args = parser.parse_args()

    if not args.dry_run and not args.save:
        print("Error: --dry-run or --save required")
        return

    print(f"Loading extract: {args.extract_file}")
    extract_data = load_json(args.extract_file)

    print(f"Loading classified: {args.classified_file}")
    classified_data = load_json(args.classified_file)
    title_info = classified_data.get('title_info', {})

    print(f"Events: {len(extract_data['events'])}, Titles: {len(title_info):,}")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    stats = defaultdict(int)
    batch = []
    batch_size = 1000

    for event_data in extract_data['events']:
        event_title = event_data['event']
        event_qid = event_data.get('event_qid')

        if not event_qid:
            stats['event_no_qid'] += 1
            continue

        event_id = get_event_id_by_qid(cur, event_qid)
        if not event_id:
            stats['event_not_in_db'] += 1
            continue

        stats['events_processed'] += 1

        # 본문 연결
        for conn_data in event_data.get('body_connections', []):
            target_title = conn_data.get('target_title')
            if not target_title or target_title not in title_info:
                continue

            info = title_info[target_title]
            if not info.get('type') or not info.get('db_match'):
                stats['target_not_matched'] += 1
                continue

            batch.append((
                event_id,
                event_qid,
                event_title,
                info['db_match']['id'],
                info['type'],
                info['qid'],
                target_title,
                'body',
                None,  # navbox_group
                conn_data.get('evidence_text', '')[:2000],
                conn_data.get('source', {}).get('url', ''),
                0.7
            ))
            stats[f'{info["type"]}_body'] += 1

        # Navbox 연결
        for conn_data in event_data.get('navbox_connections', []):
            target_title = conn_data.get('target_title')
            if not target_title or target_title not in title_info:
                continue

            info = title_info[target_title]
            if not info.get('type') or not info.get('db_match'):
                stats['target_not_matched'] += 1
                continue

            batch.append((
                event_id,
                event_qid,
                event_title,
                info['db_match']['id'],
                info['type'],
                info['qid'],
                target_title,
                'navbox',
                conn_data.get('navbox_group', '')[:200],
                None,  # evidence_text (navbox has no context)
                conn_data.get('source', {}).get('url', ''),
                0.6
            ))
            stats[f'{info["type"]}_navbox'] += 1

        # 배치 저장
        if args.save and len(batch) >= batch_size:
            cur.executemany("""
                INSERT INTO wiki_connections
                (from_event_id, from_event_qid, from_event_title,
                 to_entity_id, to_entity_type, to_entity_qid, to_entity_title,
                 connection_type, navbox_group, evidence_text, source_url, confidence)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, batch)
            conn.commit()
            print(f"  Saved batch: {len(batch)}")
            batch = []

    # 남은 배치 저장
    if args.save and batch:
        cur.executemany("""
            INSERT INTO wiki_connections
            (from_event_id, from_event_qid, from_event_title,
             to_entity_id, to_entity_type, to_entity_qid, to_entity_title,
             connection_type, navbox_group, evidence_text, source_url, confidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, batch)
        conn.commit()

    # 결과
    print("\n" + "=" * 60)
    print("SAVE SUMMARY" if args.save else "DRY RUN SUMMARY")
    print("=" * 60)
    print(f"Events processed: {stats['events_processed']}")
    print(f"Events skipped: no_qid={stats['event_no_qid']}, not_in_db={stats['event_not_in_db']}")
    print()
    print("Connections by type:")
    print(f"  Person (body): {stats['person_body']}")
    print(f"  Person (navbox): {stats['person_navbox']}")
    print(f"  Event (body): {stats['event_body']}")
    print(f"  Event (navbox): {stats['event_navbox']}")
    print(f"  Location (body): {stats['location_body']}")
    print(f"  Location (navbox): {stats['location_navbox']}")
    print(f"  Target not matched: {stats['target_not_matched']}")

    total = sum(v for k, v in stats.items() if k.endswith('_body') or k.endswith('_navbox'))
    print(f"\nTotal connections: {total:,}")

    if args.save:
        cur.execute("SELECT COUNT(*) FROM wiki_connections")
        print(f"wiki_connections table now has: {cur.fetchone()[0]:,} rows")

    conn.close()


if __name__ == '__main__':
    main()
