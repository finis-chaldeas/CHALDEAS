"""
Wikipedia 추출 결과를 DB와 매칭.
QID로 persons/events/locations 테이블과 매칭하여 연결 가능 여부 확인.

Usage:
    python match_wiki_to_db.py extract_20260201_192508.json
    python match_wiki_to_db.py extract_20260201_192508.json --save
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
OUTPUT_DIR = 'poc/data/wikipedia_extract'

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}


def load_db_qid_mapping(conn):
    """DB에서 QID → 엔티티 매핑 로드."""
    cur = conn.cursor()

    mappings = {
        'persons': {},
        'events': {},
        'locations': {}
    }

    # Persons
    cur.execute("SELECT id, name, wikidata_id FROM persons WHERE wikidata_id IS NOT NULL")
    for row in cur.fetchall():
        mappings['persons'][row[2]] = {'id': row[0], 'name': row[1]}

    # Events (title 컬럼 사용)
    cur.execute("SELECT id, title, wikidata_id FROM events WHERE wikidata_id IS NOT NULL")
    for row in cur.fetchall():
        mappings['events'][row[2]] = {'id': row[0], 'name': row[1]}

    # Locations
    cur.execute("SELECT id, name, wikidata_id FROM locations WHERE wikidata_id IS NOT NULL")
    for row in cur.fetchall():
        mappings['locations'][row[2]] = {'id': row[0], 'name': row[1]}

    return mappings


def match_connections(data, mappings):
    """추출된 연결을 DB와 매칭."""
    results = []

    for event_data in data['events']:
        event_title = event_data['event']
        event_qid = event_data.get('event_qid')

        # 이벤트 자체 매칭
        event_match = None
        if event_qid and event_qid in mappings['events']:
            event_match = mappings['events'][event_qid]

        event_result = {
            'event': event_title,
            'event_qid': event_qid,
            'event_db_match': event_match,
            'connections': []
        }

        # 모든 연결 처리
        all_connections = (
            event_data.get('body_connections', []) +
            event_data.get('navbox_connections', [])
        )

        for conn in all_connections:
            target_qid = conn.get('target_qid')
            if not target_qid:
                continue

            # 각 테이블에서 매칭 시도
            match_result = {
                'target_title': conn.get('target_title'),
                'target_qid': target_qid,
                'display_text': conn.get('display_text'),
                'evidence_text': conn.get('evidence_text'),
                'navbox_group': conn.get('navbox_group'),
                'source': conn.get('source'),
                'db_match': None,
                'db_type': None
            }

            # 매칭 순서: persons → events → locations
            if target_qid in mappings['persons']:
                match_result['db_match'] = mappings['persons'][target_qid]
                match_result['db_type'] = 'person'
            elif target_qid in mappings['events']:
                match_result['db_match'] = mappings['events'][target_qid]
                match_result['db_type'] = 'event'
            elif target_qid in mappings['locations']:
                match_result['db_match'] = mappings['locations'][target_qid]
                match_result['db_type'] = 'location'

            event_result['connections'].append(match_result)

        results.append(event_result)

    return results


def print_summary(results):
    """결과 요약 출력."""
    total_connections = 0
    matched_connections = 0
    type_counts = defaultdict(int)

    for event_result in results:
        event_match_status = "MATCHED" if event_result['event_db_match'] else "NOT FOUND"
        print(f"\n=== {event_result['event']} ({event_result['event_qid']}) [{event_match_status}] ===")

        if event_result['event_db_match']:
            print(f"  DB: events.id={event_result['event_db_match']['id']}")

        # 연결 통계
        conns = event_result['connections']
        matched = [c for c in conns if c['db_match']]

        print(f"  Connections: {len(matched)}/{len(conns)} matched")

        # 유형별 통계
        for conn in matched:
            type_counts[conn['db_type']] += 1

        # 샘플 출력
        print(f"  Matched samples:")
        for conn in matched[:5]:
            print(f"    - [{conn['db_type']}] {conn['display_text']} -> {conn['db_match']['name']} (id={conn['db_match']['id']})")

        total_connections += len(conns)
        matched_connections += len(matched)

    # 전체 요약
    print("\n" + "=" * 60)
    print("OVERALL SUMMARY")
    print("=" * 60)
    print(f"Events processed: {len(results)}")
    print(f"Events matched to DB: {sum(1 for r in results if r['event_db_match'])}")
    print(f"Total connections with QID: {total_connections}")
    print(f"Connections matched to DB: {matched_connections} ({100*matched_connections/total_connections:.1f}%)" if total_connections > 0 else "N/A")
    print(f"By type: {dict(type_counts)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help='추출 결과 JSON 파일명')
    parser.add_argument('--save', action='store_true', help='매칭 결과 저장')
    args = parser.parse_args()

    # 입력 파일 로드
    input_path = os.path.join(INPUT_DIR, args.input_file)
    if not os.path.exists(input_path):
        input_path = args.input_file  # 절대 경로로 시도

    print(f"Loading: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Events in file: {len(data['events'])}")

    # DB 연결
    print("Connecting to DB...")
    conn = psycopg2.connect(**DB_CONFIG)

    # QID 매핑 로드
    print("Loading QID mappings from DB...")
    mappings = load_db_qid_mapping(conn)
    print(f"  Persons with QID: {len(mappings['persons']):,}")
    print(f"  Events with QID: {len(mappings['events']):,}")
    print(f"  Locations with QID: {len(mappings['locations']):,}")

    # 매칭 실행
    print("\nMatching connections...")
    results = match_connections(data, mappings)

    # 요약 출력
    print_summary(results)

    # 저장
    if args.save:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(OUTPUT_DIR, f'matched_{timestamp}.json')

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'matched_at': timestamp,
                'results': results
            }, f, ensure_ascii=False, indent=2)

        print(f"\nSaved to: {output_file}")

    conn.close()


if __name__ == '__main__':
    main()
