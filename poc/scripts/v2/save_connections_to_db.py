"""
분류된 연결을 DB에 저장.
- event-person → person_event_roles
- event-event → event_relations_v2
- event-location → event_locations

Usage:
    python save_connections_to_db.py extract_*.json classified_*.json --dry-run
    python save_connections_to_db.py extract_*.json classified_*.json --save
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
    """JSON 파일 로드."""
    path = os.path.join(INPUT_DIR, filepath) if not os.path.isabs(filepath) else filepath
    if not os.path.exists(path):
        path = filepath
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_event_id_by_qid(cur, qid):
    """QID로 events 테이블에서 id 조회."""
    cur.execute("SELECT id FROM events WHERE wikidata_id = %s", (qid,))
    row = cur.fetchone()
    return row[0] if row else None


def save_person_event_connection(cur, event_id, person_id, evidence_text, source_url, dry_run=True):
    """event_persons (V0)에 저장."""
    if dry_run:
        return True

    # 중복 체크
    cur.execute("""
        SELECT event_id FROM event_persons
        WHERE event_id = %s AND person_id = %s
    """, (event_id, person_id))

    if cur.fetchone():
        return False  # 이미 존재

    cur.execute("""
        INSERT INTO event_persons
        (event_id, person_id, role, description)
        VALUES (%s, %s, %s, %s)
    """, (event_id, person_id, 'participant',
          f"Wikipedia: {source_url}" if source_url else None))
    return True


def save_event_event_connection(cur, from_event_id, to_event_id, evidence_text, source_url, dry_run=True):
    """event_relationships (V0)에 저장."""
    if dry_run:
        return True

    # 중복 체크
    cur.execute("""
        SELECT id FROM event_relationships
        WHERE from_event_id = %s AND to_event_id = %s AND relationship_type = 'wikipedia_mention'
    """, (from_event_id, to_event_id))

    if cur.fetchone():
        return False

    cur.execute("""
        INSERT INTO event_relationships
        (from_event_id, to_event_id, relationship_type, evidence_type, scholarly_citation, confidence)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (from_event_id, to_event_id, 'wikipedia_mention', 'wikipedia',
          json.dumps({'text': evidence_text[:500], 'url': source_url}),
          0.7))
    return True


def save_location_event_connection(cur, event_id, location_id, dry_run=True):
    """event_locations에 저장."""
    if dry_run:
        return True

    # 중복 체크
    cur.execute("""
        SELECT event_id FROM event_locations
        WHERE event_id = %s AND location_id = %s
    """, (event_id, location_id))

    if cur.fetchone():
        return False

    cur.execute("""
        INSERT INTO event_locations (event_id, location_id, role)
        VALUES (%s, %s, %s)
    """, (event_id, location_id, 'location'))
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('extract_file', help='추출 결과 JSON 파일')
    parser.add_argument('classified_file', help='분류 결과 JSON 파일')
    parser.add_argument('--dry-run', action='store_true', help='저장하지 않고 통계만 출력')
    parser.add_argument('--save', action='store_true', help='실제로 DB에 저장')
    args = parser.parse_args()

    if not args.dry_run and not args.save:
        print("Error: --dry-run 또는 --save 옵션 필요")
        return

    # 파일 로드
    print(f"Loading extract: {args.extract_file}")
    extract_data = load_json(args.extract_file)

    print(f"Loading classified: {args.classified_file}")
    classified_data = load_json(args.classified_file)

    title_info = classified_data.get('title_info', {})
    print(f"Title info entries: {len(title_info):,}")

    # DB 연결
    print("\nConnecting to DB...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # 통계
    stats = defaultdict(int)

    # 각 이벤트 처리
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

        # 본문 연결 처리
        for conn_data in event_data.get('body_connections', []):
            target_title = conn_data.get('target_title')
            if not target_title or target_title not in title_info:
                continue

            info = title_info[target_title]
            if not info.get('type') or not info.get('db_match'):
                continue

            target_type = info['type']
            target_id = info['db_match']['id']
            evidence = conn_data.get('evidence_text', '')[:500]
            source_url = conn_data.get('source', {}).get('url', '')

            if target_type == 'person':
                if save_person_event_connection(cur, event_id, target_id, evidence, source_url, args.dry_run):
                    stats['person_event_new'] += 1
                else:
                    stats['person_event_dup'] += 1

            elif target_type == 'event':
                if save_event_event_connection(cur, event_id, target_id, evidence, source_url, args.dry_run):
                    stats['event_event_new'] += 1
                else:
                    stats['event_event_dup'] += 1

            elif target_type == 'location':
                if save_location_event_connection(cur, event_id, target_id, args.dry_run):
                    stats['location_event_new'] += 1
                else:
                    stats['location_event_dup'] += 1

    # 결과 출력
    print("\n" + "=" * 60)
    print("SAVE SUMMARY" if args.save else "DRY RUN SUMMARY")
    print("=" * 60)
    print(f"Events processed: {stats['events_processed']}")
    print(f"Events skipped (no QID): {stats['event_no_qid']}")
    print(f"Events skipped (not in DB): {stats['event_not_in_db']}")
    print()
    print(f"Person-Event connections: {stats['person_event_new']} new, {stats['person_event_dup']} duplicates")
    print(f"Event-Event connections: {stats['event_event_new']} new, {stats['event_event_dup']} duplicates")
    print(f"Location-Event connections: {stats['location_event_new']} new, {stats['location_event_dup']} duplicates")

    if args.save:
        conn.commit()
        print("\nChanges committed to DB.")
    else:
        print("\nDry run - no changes made.")

    conn.close()


if __name__ == '__main__':
    main()
