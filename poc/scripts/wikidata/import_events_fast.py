"""
추출된 이벤트를 DB에 빠르게 임포트 (SPARQL 없이)

위치는 이미 DB에 있다고 가정 (import_extracted_locations.py 먼저 실행)
DB 조회만 하므로 매우 빠름

Usage:
    python import_events_fast.py --input events.jsonl
    python import_events_fast.py --input events.jsonl --limit 10000
"""

import json
import sys
import os
import argparse
import time
import re
from typing import Optional, Set, Dict

import psycopg2

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

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


class FastEventImporter:
    """빠른 이벤트 임포터 (DB 조회만)"""

    def __init__(self, db_url: str):
        self.conn = psycopg2.connect(db_url)

        # 캐시
        self._existing_events: Set[str] = set()
        self._location_cache: Dict[str, int] = {}  # qid → location_id

        self._load_caches()

    def _load_caches(self):
        """캐시 로드"""
        with self.conn.cursor() as cur:
            # 기존 이벤트
            cur.execute("SELECT wikidata_id FROM events WHERE wikidata_id IS NOT NULL")
            for row in cur:
                self._existing_events.add(row[0])
            print(f"  기존 이벤트: {len(self._existing_events):,}개")

            # 위치 캐시 (wikidata_id → id)
            cur.execute("SELECT id, wikidata_id FROM locations WHERE wikidata_id IS NOT NULL")
            for row in cur:
                self._location_cache[row[1]] = row[0]
            print(f"  위치 캐시: {len(self._location_cache):,}개")

    def get_location_id(self, qid: str) -> Optional[int]:
        """위치 ID 가져오기 (캐시만 사용)"""
        return self._location_cache.get(qid)

    def import_event(self, event_data: dict) -> Optional[int]:
        """이벤트 임포트"""
        qid = event_data['qid']

        # 이미 존재하면 건너뛰기
        if qid in self._existing_events:
            return None

        title = event_data['name']
        title_ko = event_data.get('name_ko')
        description = event_data.get('description')

        # 연도 파싱
        date_start = parse_wikidata_time(
            event_data.get('point_in_time') or event_data.get('start_time')
        )
        date_end = parse_wikidata_time(event_data.get('end_time'))

        # 날짜가 없으면 임포트 불가
        if date_start is None:
            return None

        # slug 생성
        slug_base = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        slug = f"{slug_base}-{qid.lower()}"

        # 위치 처리 (DB 조회만)
        primary_location_id = None
        location_qids = event_data.get('location_qids', []) + event_data.get('country_qids', [])

        location_ids = []
        for loc_qid in location_qids:
            loc_id = self.get_location_id(loc_qid)
            if loc_id:
                location_ids.append(loc_id)
                if primary_location_id is None:
                    primary_location_id = loc_id

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

            # event_locations 연결
            for loc_id in location_ids:
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
        self.conn.close()


def import_events(input_path: str, limit: int = None):
    """추출된 이벤트 파일 임포트"""
    print("=== 빠른 이벤트 임포트 (SPARQL 없음) ===")
    print(f"입력: {input_path}")
    print(f"제한: {limit or '없음'}")
    print()

    if not os.path.exists(input_path):
        print(f"Error: 파일 없음: {input_path}")
        return

    importer = FastEventImporter(DATABASE_URL)

    start_time = time.time()
    total = 0
    imported = 0
    skipped_exists = 0
    skipped_no_date = 0
    with_location = 0
    failed = 0

    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if limit and total >= limit:
                break

            try:
                event_data = json.loads(line.strip())
                total += 1

                # 날짜 확인
                has_date = event_data.get('point_in_time') or event_data.get('start_time')
                if not has_date:
                    skipped_no_date += 1
                    continue

                # 이미 존재 확인
                if event_data['qid'] in importer._existing_events:
                    skipped_exists += 1
                    continue

                event_id = importer.import_event(event_data)

                if event_id:
                    imported += 1
                    if event_data.get('location_qids') or event_data.get('country_qids'):
                        # 위치 QID 있고, 실제 연결됐는지 확인
                        has_loc = any(
                            importer.get_location_id(q)
                            for q in (event_data.get('location_qids', []) +
                                     event_data.get('country_qids', []))
                        )
                        if has_loc:
                            with_location += 1

                if total % 5000 == 0:
                    elapsed = time.time() - start_time
                    rate = total / elapsed if elapsed > 0 else 0
                    print(f"  처리: {total:,} | 임포트: {imported:,} | 위치연결: {with_location:,} | {rate:.0f}/s")

            except Exception as e:
                failed += 1
                if failed <= 5:
                    print(f"  Error: {e}")

    importer.close()
    elapsed = time.time() - start_time

    print()
    print("=== 완료 ===")
    print(f"총 처리: {total:,}")
    print(f"임포트: {imported:,}")
    print(f"위치 연결: {with_location:,} ({100*with_location/imported:.1f}%)" if imported else "")
    print(f"스킵 (이미 존재): {skipped_exists:,}")
    print(f"스킵 (날짜 없음): {skipped_no_date:,}")
    print(f"실패: {failed}")
    print(f"소요 시간: {elapsed:.1f}초 ({imported/elapsed:.0f} 이벤트/초)" if elapsed > 0 else "")


def main():
    parser = argparse.ArgumentParser(description='Fast import of extracted events to DB')
    parser.add_argument('--input', required=True, help='추출된 이벤트 파일 (JSONL)')
    parser.add_argument('--limit', type=int, help='임포트 개수 제한')

    args = parser.parse_args()

    import_events(args.input, args.limit)


if __name__ == '__main__':
    main()
