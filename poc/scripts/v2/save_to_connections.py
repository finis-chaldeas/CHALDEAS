"""
분류된 연결을 통합 connections 테이블에 저장.
CLEAN_SCHEMA_PLAN.md 기반 - 모든 연결에 evidence 필수.

Usage:
    python save_to_connections.py extract_*.json classified_*.json --dry-run
    python save_to_connections.py extract_*.json classified_*.json --save
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


def infer_relation(target_type, connection_type):
    """연결 유형 추론 - CLEAN_SCHEMA_PLAN.md 기준"""
    if connection_type == 'body':
        if target_type == 'person':
            return 'participant'  # 이벤트에 인물 참여
        elif target_type == 'location':
            return 'occurred_at'  # 이벤트 발생 장소
        elif target_type == 'event':
            return 'related_to'  # 관련 이벤트
    else:  # navbox
        return 'related_to'  # 관련 항목
    return 'mentioned_in'


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

        # 본문 연결 - evidence_text 있는 것만
        for conn_data in event_data.get('body_connections', []):
            target_title = conn_data.get('target_title')
            evidence_text = conn_data.get('evidence_text', '').strip()

            # 근거 없으면 스킵
            if not evidence_text:
                stats['no_evidence'] += 1
                continue

            if not target_title or target_title not in title_info:
                continue

            info = title_info[target_title]
            if not info.get('type') or not info.get('db_match'):
                stats['target_not_matched'] += 1
                continue

            relation = infer_relation(info['type'], 'body')

            batch.append((
                'event',  # from_type
                event_id,  # from_id
                event_qid,  # from_qid
                info['type'],  # to_type
                info['db_match']['id'],  # to_id
                info['qid'],  # to_qid
                relation,
                evidence_text[:2000],  # evidence (필수!)
                conn_data.get('source', {}).get('url', ''),
                'wikipedia',
                0.7
            ))
            stats[f'{info["type"]}_body'] += 1

        # Navbox 연결 - navbox_group 있는 것만
        for conn_data in event_data.get('navbox_connections', []):
            target_title = conn_data.get('target_title')
            navbox_group = conn_data.get('navbox_group', '').strip()

            # navbox_group을 evidence로 사용
            if not navbox_group:
                stats['no_evidence'] += 1
                continue

            if not target_title or target_title not in title_info:
                continue

            info = title_info[target_title]
            if not info.get('type') or not info.get('db_match'):
                stats['target_not_matched'] += 1
                continue

            relation = infer_relation(info['type'], 'navbox')
            evidence = f"Wikipedia Navbox: {navbox_group}"

            batch.append((
                'event',
                event_id,
                event_qid,
                info['type'],
                info['db_match']['id'],
                info['qid'],
                relation,
                evidence,  # evidence (필수!)
                conn_data.get('source', {}).get('url', ''),
                'wikipedia',
                0.6
            ))
            stats[f'{info["type"]}_navbox'] += 1

        # 배치 저장
        if args.save and len(batch) >= batch_size:
            cur.executemany("""
                INSERT INTO connections
                (from_type, from_id, from_qid, to_type, to_id, to_qid,
                 relation, evidence, source_url, source_type, confidence)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, batch)
            conn.commit()
            print(f"  Saved batch: {len(batch)}")
            batch = []

    # 남은 배치 저장
    if args.save and batch:
        cur.executemany("""
            INSERT INTO connections
            (from_type, from_id, from_qid, to_type, to_id, to_qid,
             relation, evidence, source_url, source_type, confidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, batch)
        conn.commit()

    # 결과
    print("\n" + "=" * 60)
    print("SAVE SUMMARY" if args.save else "DRY RUN SUMMARY")
    print("=" * 60)
    print(f"Events processed: {stats['events_processed']}")
    print(f"Events skipped: no_qid={stats['event_no_qid']}, not_in_db={stats['event_not_in_db']}")
    print(f"Skipped (no evidence): {stats['no_evidence']}")
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
    print(f"\nTotal connections with evidence: {total:,}")

    if args.save:
        cur.execute("SELECT COUNT(*) FROM connections")
        print(f"connections table now has: {cur.fetchone()[0]:,} rows")

    conn.close()


if __name__ == '__main__':
    main()
