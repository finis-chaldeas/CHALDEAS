"""
추출된 이벤트를 DB에 임포트

Usage:
    python import_extracted_events.py --input events.jsonl --limit 1000
    python import_extracted_events.py --input events.jsonl  # 전체 임포트
"""

import json
import sys
import os
import argparse
import time
from typing import Optional, Dict, Set
from dataclasses import dataclass

import psycopg2
from psycopg2.extras import RealDictCursor

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# SmartLocationImporter 임포트
sys.path.insert(0, '.')
from importers.smart_location_importer import SmartLocationImporter


DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas'
)


def parse_wikidata_time(time_str: str) -> Optional[int]:
    """Wikidata 시간 문자열 → 연도"""
    if not time_str:
        return None
    try:
        if time_str.startswith('+'):
            time_str = time_str[1:]
            year_str = time_str.split('T')[0].split('-')[0]
            return int(year_str)
        elif time_str.startswith('-'):
            year_str = time_str[1:].split('T')[0].split('-')[0]
            return -int(year_str)
        else:
            year_str = time_str.split('T')[0].split('-')[0]
            return int(year_str)
    except (ValueError, IndexError):
        return None


class EventImporter:
    """이벤트 임포터"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn = psycopg2.connect(db_url)
        self.location_importer = SmartLocationImporter(db_url)

        # 캐시
        self._existing_events: Set[str] = set()
        self._load_existing_events()

    def _load_existing_events(self):
        """기존 이벤트 QID 로드"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT wikidata_id FROM events WHERE wikidata_id IS NOT NULL")
            for row in cur:
                self._existing_events.add(row[0])
        print(f"  기존 이벤트: {len(self._existing_events)}개")

    def import_event(self, event_data: dict) -> Optional[int]:
        """이벤트 임포트"""
        qid = event_data['qid']

        # 이미 존재하면 건너뛰기
        if qid in self._existing_events:
            return None

        title = event_data['name']
        title_ko = event_data.get('name_ko')
        description = event_data.get('description')
        event_type = event_data.get('event_type', 'unknown')

        # 연도 파싱
        date_start = parse_wikidata_time(
            event_data.get('point_in_time') or event_data.get('start_time')
        )
        date_end = parse_wikidata_time(event_data.get('end_time'))

        # 날짜가 없으면 임포트 불가 (date_start는 NOT NULL)
        if date_start is None:
            return None

        # slug 생성 (고유해야 함)
        import re
        slug_base = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        slug = f"{slug_base}-{qid.lower()}"

        # 위치 처리
        primary_location_id = None
        location_qids = event_data.get('location_qids', []) + event_data.get('country_qids', [])

        if location_qids:
            # 첫 번째 위치를 primary로
            primary_location_id = self.location_importer.get_or_create(location_qids[0])

        # 이벤트 삽입
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO events (
                    title, title_ko, description, slug,
                    date_start, date_end, wikidata_id,
                    primary_location_id, temporal_scale,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'evenementielle', NOW(), NOW())
                RETURNING id
            """, (
                title, title_ko, description, slug,
                date_start, date_end, qid, primary_location_id
            ))
            event_id = cur.fetchone()[0]

            # event_locations 연결 (모든 위치)
            for loc_qid in location_qids:
                loc_id = self.location_importer.get_or_create(loc_qid)
                if loc_id:
                    try:
                        cur.execute("""
                            INSERT INTO event_locations (event_id, location_id, role)
                            VALUES (%s, %s, 'location')
                            ON CONFLICT DO NOTHING
                        """, (event_id, loc_id))
                    except Exception:
                        pass

            self.conn.commit()
            self._existing_events.add(qid)
            return event_id

    def close(self):
        """연결 종료"""
        self.location_importer.close()
        self.conn.close()


def import_events(input_path: str, limit: int = None):
    """추출된 이벤트 파일 임포트"""
    print("=== 이벤트 임포트 ===")
    print(f"입력: {input_path}")
    print(f"제한: {limit or '없음'}")
    print()

    if not os.path.exists(input_path):
        print(f"Error: 파일 없음: {input_path}")
        return

    importer = EventImporter(DATABASE_URL)

    start_time = time.time()
    total = 0
    imported = 0
    skipped = 0
    failed = 0
    with_location = 0

    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if limit and total >= limit:
                break

            try:
                event_data = json.loads(line.strip())
                total += 1

                event_id = importer.import_event(event_data)

                if event_id:
                    imported += 1
                    if event_data.get('location_qids') or event_data.get('country_qids'):
                        with_location += 1

                    if imported % 100 == 0:
                        elapsed = time.time() - start_time
                        rate = imported / elapsed if elapsed > 0 else 0
                        print(f"  임포트: {imported} / 스킵: {skipped} / 실패: {failed} ({rate:.1f}/s)")
                else:
                    skipped += 1

            except Exception as e:
                failed += 1
                if failed <= 5:
                    print(f"  Error: {e}")

    importer.close()
    elapsed = time.time() - start_time

    print()
    print("=== 완료 ===")
    print(f"총 처리: {total}")
    print(f"임포트: {imported}")
    print(f"스킵 (이미 존재): {skipped}")
    print(f"실패: {failed}")
    print(f"위치 연결: {with_location} ({100*with_location/imported:.1f}%)" if imported else "")
    print(f"소요 시간: {elapsed:.1f}초")


def main():
    parser = argparse.ArgumentParser(description='Import extracted events to DB')
    parser.add_argument('--input', required=True, help='추출된 이벤트 파일 (JSONL)')
    parser.add_argument('--limit', type=int, help='임포트 개수 제한')

    args = parser.parse_args()

    import_events(args.input, args.limit)


if __name__ == '__main__':
    main()
