"""
Core 이벤트 DB 임포트

Usage:
    python import_events_core.py --input E:/chaldeas_data/events_core.jsonl
"""

import json
import sys
import argparse
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}


def parse_wikidata_time(time_str: str) -> tuple:
    """Wikidata 시간 문자열을 (year, precision) 튜플로 변환"""
    if not time_str:
        return None, None

    try:
        # +1945-08-15T00:00:00Z or -0490-01-01T00:00:00Z
        sign = 1 if time_str[0] == '+' else -1
        date_part = time_str[1:].split('T')[0]
        parts = date_part.split('-')

        year = sign * int(parts[0])
        return year, 'year'
    except:
        return None, None


def main():
    parser = argparse.ArgumentParser(description='Core 이벤트 DB 임포트')
    parser.add_argument('--input', default='E:/chaldeas_data/events_core.jsonl', help='입력 파일')
    parser.add_argument('--batch-size', type=int, default=1000, help='배치 크기')
    args = parser.parse_args()

    print(f"=== Core 이벤트 임포트 ===")
    print(f"Input: {args.input}")
    print()

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # 기존 이벤트 QID 조회
    cur.execute("SELECT wikidata_id FROM events WHERE wikidata_id IS NOT NULL")
    existing_qids = set(row[0] for row in cur.fetchall())
    print(f"Existing events with QID: {len(existing_qids)}")

    # 파일 읽기 및 임포트
    events_to_insert = []
    skipped = 0
    updated = 0

    with open(args.input, 'r', encoding='utf-8') as f:
        for line in f:
            event = json.loads(line)
            qid = event['qid']

            if qid in existing_qids:
                skipped += 1
                continue

            # 시간 파싱
            start_year, _ = parse_wikidata_time(event.get('start_time'))
            end_year, _ = parse_wikidata_time(event.get('end_time'))
            point_year, _ = parse_wikidata_time(event.get('point_in_time'))

            # point_in_time이 있으면 start/end로 사용
            if point_year and not start_year:
                start_year = point_year
            if point_year and not end_year:
                end_year = point_year

            events_to_insert.append((
                qid,
                event['title'],
                event.get('title_ko'),
                start_year,
                end_year,
                'year',
                event['event_type'],
                event.get('description'),
            ))

    print(f"Events to insert: {len(events_to_insert)}")
    print(f"Skipped (already exists): {skipped}")

    if not events_to_insert:
        print("Nothing to insert.")
        conn.close()
        return

    # 배치 삽입
    insert_sql = """
        INSERT INTO events (wikidata_id, title, title_ko, date_start, date_end, date_precision, event_type, description, created_at, updated_at)
        VALUES %s
        ON CONFLICT (wikidata_id) DO UPDATE SET
            title = EXCLUDED.title,
            title_ko = EXCLUDED.title_ko,
            date_start = EXCLUDED.date_start,
            date_end = EXCLUDED.date_end,
            event_type = EXCLUDED.event_type,
            description = EXCLUDED.description,
            updated_at = NOW()
    """

    now = datetime.now()
    batch_data = [(e[0], e[1], e[2], e[3], e[4], e[5], e[6], e[7], now, now) for e in events_to_insert]

    print(f"Inserting {len(batch_data)} events...")

    try:
        execute_values(cur, insert_sql, batch_data, page_size=args.batch_size)
        conn.commit()
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
        raise

    # 결과 확인
    cur.execute("SELECT COUNT(*) FROM events")
    total = cur.fetchone()[0]
    print(f"\nTotal events in DB: {total}")

    cur.execute("SELECT event_type, COUNT(*) FROM events GROUP BY event_type ORDER BY COUNT(*) DESC LIMIT 10")
    print("\nTop event types:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")

    conn.close()


if __name__ == '__main__':
    main()
