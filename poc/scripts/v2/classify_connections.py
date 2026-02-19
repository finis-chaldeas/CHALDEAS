"""
추출된 연결에서 unique 타이틀 추출 후 QID 해석 및 DB 매칭.
인물/이벤트/장소 분류.

Usage:
    python classify_connections.py extract_20260201_200938.json
"""

import sys
import os
import json
import argparse
import psycopg2
from datetime import datetime
from collections import defaultdict
from libzim.reader import Archive

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

INPUT_DIR = 'poc/data/wikipedia_extract'
OUTPUT_DIR = 'poc/data/wikipedia_extract'
ZIM_PATH = 'C:/Projects/Chaldeas/data/kiwix/wikipedia_en_nopic.zim'

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}


def extract_unique_titles(data):
    """추출 결과에서 unique target_title 추출."""
    titles = set()
    for event_data in data['events']:
        for conn in event_data.get('body_connections', []):
            titles.add(conn.get('target_title'))
        for conn in event_data.get('navbox_connections', []):
            titles.add(conn.get('target_title'))
    titles.discard(None)
    return titles


def get_qid_from_zim(zim, title):
    """ZIM에서 문서의 Wikidata QID 추출."""
    import re
    try:
        path = f"A/{title.replace(' ', '_')}"
        entry = zim.get_entry_by_path(path)
        item = entry.get_item()
        html = bytes(item.content).decode('utf-8', errors='replace')
        match = re.search(r'wikidata\.org/wiki/(Q\d+)', html)
        if match:
            return match.group(1)
    except:
        pass
    return None


def load_db_qid_mapping(conn):
    """DB에서 QID → 엔티티 매핑 로드."""
    cur = conn.cursor()
    mappings = {
        'persons': {},
        'events': {},
        'locations': {}
    }

    cur.execute("SELECT wikidata_id, id, name FROM persons WHERE wikidata_id IS NOT NULL")
    for qid, id_, name in cur.fetchall():
        mappings['persons'][qid] = {'id': id_, 'name': name}

    cur.execute("SELECT wikidata_id, id, title FROM events WHERE wikidata_id IS NOT NULL")
    for qid, id_, title in cur.fetchall():
        mappings['events'][qid] = {'id': id_, 'name': title}

    cur.execute("SELECT wikidata_id, id, name FROM locations WHERE wikidata_id IS NOT NULL")
    for qid, id_, name in cur.fetchall():
        mappings['locations'][qid] = {'id': id_, 'name': name}

    return mappings


def classify_qid(qid, db_mappings):
    """QID를 인물/이벤트/장소로 분류."""
    if qid in db_mappings['persons']:
        return 'person', db_mappings['persons'][qid]
    elif qid in db_mappings['events']:
        return 'event', db_mappings['events'][qid]
    elif qid in db_mappings['locations']:
        return 'location', db_mappings['locations'][qid]
    return None, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help='추출 결과 JSON 파일명')
    parser.add_argument('--limit', type=int, default=0, help='처리할 타이틀 수 제한 (0=무제한)')
    args = parser.parse_args()

    # 입력 파일 로드
    input_path = os.path.join(INPUT_DIR, args.input_file)
    if not os.path.exists(input_path):
        input_path = args.input_file

    print(f"Loading: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Events in file: {len(data['events'])}")

    # Unique 타이틀 추출
    unique_titles = extract_unique_titles(data)
    print(f"Unique target titles: {len(unique_titles):,}")

    # 제한 적용
    if args.limit > 0:
        unique_titles = list(unique_titles)[:args.limit]
        print(f"Processing limited to: {len(unique_titles)}")

    # DB 연결 및 매핑 로드
    print("\nConnecting to DB...")
    conn = psycopg2.connect(**DB_CONFIG)
    db_mappings = load_db_qid_mapping(conn)
    print(f"DB mappings: persons={len(db_mappings['persons']):,}, events={len(db_mappings['events']):,}, locations={len(db_mappings['locations']):,}")

    # ZIM 열기
    print(f"\nOpening ZIM: {ZIM_PATH}")
    zim = Archive(ZIM_PATH)

    # QID 해석 및 분류
    print("\nResolving QIDs and classifying...")
    title_info = {}
    stats = defaultdict(int)

    for i, title in enumerate(unique_titles):
        if i % 1000 == 0 and i > 0:
            print(f"  Processed: {i:,}/{len(unique_titles):,}")

        qid = get_qid_from_zim(zim, title)
        if qid:
            entity_type, db_match = classify_qid(qid, db_mappings)
            title_info[title] = {
                'qid': qid,
                'type': entity_type,
                'db_match': db_match
            }
            if entity_type:
                stats[f'matched_{entity_type}'] += 1
            else:
                stats['qid_not_in_db'] += 1
        else:
            title_info[title] = {'qid': None, 'type': None, 'db_match': None}
            stats['no_qid'] += 1

    # 통계 출력
    print("\n" + "=" * 60)
    print("CLASSIFICATION SUMMARY")
    print("=" * 60)
    print(f"Total unique titles: {len(unique_titles):,}")
    print(f"With QID: {len(unique_titles) - stats['no_qid']:,}")
    print(f"  - Matched as person: {stats['matched_person']:,}")
    print(f"  - Matched as event: {stats['matched_event']:,}")
    print(f"  - Matched as location: {stats['matched_location']:,}")
    print(f"  - QID not in DB: {stats['qid_not_in_db']:,}")
    print(f"Without QID: {stats['no_qid']:,}")

    # 저장
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(OUTPUT_DIR, f'classified_{timestamp}.json')

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'classified_at': timestamp,
            'source_file': args.input_file,
            'stats': dict(stats),
            'title_info': title_info
        }, f, ensure_ascii=False, indent=2)

    print(f"\nSaved to: {output_file}")

    conn.close()


if __name__ == '__main__':
    main()
