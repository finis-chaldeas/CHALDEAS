"""
기존 이벤트 위치 백필 (새 임포터 사용)

새 임포터를 사용해서 기존 이벤트들의 위치 데이터를 보완합니다.

Usage:
    python backfill_with_new_importer.py --test          # 10개 테스트
    python backfill_with_new_importer.py --limit=100    # 100개 처리
    python backfill_with_new_importer.py --all          # 전체 처리
"""

import sys
import time
import argparse

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import psycopg2
from psycopg2.extras import RealDictCursor

from importers import EventImporter, LocationImporter


DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}


def backfill_locations(limit: int = None, dry_run: bool = False):
    """기존 이벤트의 위치 데이터 백필"""

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 위치 없는 이벤트 조회
    query = """
        SELECT id, title, wikidata_id
        FROM events
        WHERE wikidata_id IS NOT NULL
          AND primary_location_id IS NULL
        ORDER BY id
    """
    if limit:
        query += f" LIMIT {limit}"

    cur.execute(query)
    events = cur.fetchall()

    print(f"위치 없는 이벤트: {len(events)}개")
    print()

    # 새 임포터 초기화 (연결 공유)
    event_importer = EventImporter(conn=conn)
    location_importer = event_importer.location_importer

    stats = {
        'total': len(events),
        'processed': 0,
        'location_found': 0,
        'location_created': 0,
        'location_linked': 0,
        'no_location': 0,
        'errors': 0,
    }

    for i, event in enumerate(events):
        if i % 10 == 0:
            pct = 100 * i / len(events) if events else 0
            print(f"[{i+1}/{len(events)}] ({pct:.1f}%) found: {stats['location_found']}, linked: {stats['location_linked']}", end='\r')

        event_qid = event['wikidata_id']
        stats['processed'] += 1

        # Wikidata에서 이벤트 정보 가져오기
        entity = event_importer.fetch_from_wikidata(event_qid)

        if not entity:
            stats['errors'] += 1
            continue

        location_qid = entity.get('location_qid')

        if not location_qid:
            stats['no_location'] += 1
            continue

        stats['location_found'] += 1

        if dry_run:
            print(f"\n  {event['title']}: {entity.get('location_label')} ({location_qid})")
            continue

        # 위치 생성/조회
        location_id = location_importer.get_or_create(location_qid)

        if not location_id:
            stats['errors'] += 1
            continue

        stats['location_created'] += 1

        # 이벤트에 위치 연결
        try:
            cur.execute("""
                UPDATE events
                SET primary_location_id = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (location_id, event['id']))

            # event_locations 브릿지도 생성
            cur.execute("""
                INSERT INTO event_locations (event_id, location_id, role)
                VALUES (%s, %s, 'occurred_at')
                ON CONFLICT DO NOTHING
            """, (event['id'], location_id))

            stats['location_linked'] += 1

            # 주기적 커밋
            if i % 50 == 0:
                conn.commit()

        except Exception as e:
            print(f"\n  Error linking {event['id']}: {e}")
            conn.rollback()
            stats['errors'] += 1

        # Rate limiting
        time.sleep(0.3)

    if not dry_run:
        conn.commit()

    print(f"\n\n{'='*50}")
    print("=== 결과 ===")
    print(f"{'='*50}")
    print(f"총 이벤트: {stats['total']}")
    print(f"처리됨: {stats['processed']}")
    print(f"위치 발견: {stats['location_found']}")
    print(f"위치 생성/조회: {stats['location_created']}")
    print(f"이벤트 연결: {stats['location_linked']}")
    print(f"위치 없음: {stats['no_location']}")
    print(f"오류: {stats['errors']}")

    # 최종 현황
    if not dry_run:
        cur.execute("SELECT COUNT(*) FROM events WHERE primary_location_id IS NOT NULL")
        with_location = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) FROM events WHERE wikidata_id IS NOT NULL")
        total_v2 = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) FROM locations WHERE wikidata_id IS NOT NULL")
        wikidata_locations = cur.fetchone()['count']

        print(f"\n{'='*50}")
        print("=== DB 현황 ===")
        print(f"{'='*50}")
        print(f"V2 이벤트 (wikidata_id): {total_v2}")
        print(f"위치 연결된 이벤트: {with_location} ({100*with_location/total_v2:.1f}%)")
        print(f"Wikidata 위치: {wikidata_locations}")

    # 임포터 통계
    print()
    location_importer.print_stats()

    conn.close()
    return stats


def main():
    parser = argparse.ArgumentParser(description='Backfill Event Locations (New Importer)')
    parser.add_argument('--limit', type=int, default=None, help='처리할 이벤트 수')
    parser.add_argument('--test', action='store_true', help='테스트 모드 (10개, dry-run)')
    parser.add_argument('--dry-run', action='store_true', help='DB 변경 없이 확인만')
    parser.add_argument('--all', action='store_true', help='전체 처리')

    args = parser.parse_args()

    limit = args.limit
    dry_run = args.dry_run

    if args.test:
        limit = 10
        dry_run = True

    if args.all:
        limit = None

    print(f"{'='*50}")
    print("=== Event Location Backfill (New Importer) ===")
    print(f"{'='*50}")
    print(f"Limit: {limit or 'All'}")
    print(f"Dry-run: {dry_run}")
    print()

    backfill_locations(limit=limit, dry_run=dry_run)


if __name__ == '__main__':
    main()
