"""
추출된 위치를 DB에 임포트

이벤트 임포트 전에 실행하여 위치 데이터를 미리 준비
SPARQL 쿼리 없이 빠른 임포트

Usage:
    python import_extracted_locations.py --input locations.jsonl
    python import_extracted_locations.py --input locations.jsonl --limit 10000
"""

import json
import sys
import os
import argparse
import time
import math
from typing import Optional, Dict, Set

import psycopg2

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas'
)


class LocationImporter:
    """위치 임포터 (SPARQL 없이 로컬 데이터만 사용)"""

    def __init__(self, db_url: str):
        self.conn = psycopg2.connect(db_url)

        # 캐시
        self._existing_qids: Set[str] = set()
        self._coord_to_id: Dict[str, int] = {}  # "lat,lng" → location_id
        self._qid_to_id: Dict[str, int] = {}    # qid → location_id

        self._load_existing()

    def _load_existing(self):
        """기존 위치 로드"""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT id, wikidata_id, latitude, longitude
                FROM locations
                WHERE wikidata_id IS NOT NULL
            """)
            for row in cur:
                loc_id, qid, lat, lng = row
                self._existing_qids.add(qid)
                self._qid_to_id[qid] = loc_id

                if lat and lng:
                    key = f"{float(lat):.4f},{float(lng):.4f}"
                    self._coord_to_id[key] = loc_id

        print(f"  기존 위치: {len(self._existing_qids)}개")

    def _find_nearby(self, lat: float, lng: float, threshold_km: float = 0.5) -> Optional[int]:
        """좌표 근처의 기존 위치 검색 (캐시 기반)"""
        key = f"{lat:.4f},{lng:.4f}"
        if key in self._coord_to_id:
            return self._coord_to_id[key]

        # 500m 범위 내 검색
        lat_range = threshold_km / 111.0
        lng_range = threshold_km / (111.0 * max(0.1, math.cos(math.radians(lat))))

        for cached_key, loc_id in self._coord_to_id.items():
            try:
                c_lat, c_lng = map(float, cached_key.split(','))
                if abs(c_lat - lat) <= lat_range and abs(c_lng - lng) <= lng_range:
                    return loc_id
            except:
                continue

        return None

    def import_location(self, loc_data: dict) -> Optional[int]:
        """위치 임포트"""
        qid = loc_data['qid']

        # 이미 존재하면 건너뛰기
        if qid in self._existing_qids:
            return self._qid_to_id.get(qid)

        name = loc_data['name']
        name_ko = loc_data.get('name_ko')
        lat = loc_data.get('latitude')
        lng = loc_data.get('longitude')
        location_type = loc_data.get('location_type', 'unknown')

        # 좌표 없으면 스킵 (나중에 상속받을 수 있음)
        if lat is None or lng is None:
            return None

        # 좌표 기반 중복 검사
        nearby_id = self._find_nearby(lat, lng)
        if nearby_id:
            # 기존 위치에 명칭만 추가
            self._add_name_to_location(nearby_id, name, name_ko, qid)
            self._existing_qids.add(qid)
            self._qid_to_id[qid] = nearby_id
            return nearby_id

        # 새 위치 생성
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO locations (
                    name, name_ko, latitude, longitude, type,
                    wikidata_id, is_region, coords_source,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'exact', NOW(), NOW())
                RETURNING id
            """, (
                name,
                name_ko,
                lat,
                lng,
                location_type,
                qid,
                location_type in ('region', 'continent', 'historical_country')
            ))
            loc_id = cur.fetchone()[0]

            # location_names에도 추가
            cur.execute("""
                INSERT INTO location_names (
                    location_id, name, name_ko, language, is_primary,
                    wikidata_id, source
                )
                VALUES (%s, %s, %s, 'en', TRUE, %s, 'wikidata')
            """, (loc_id, name, name_ko, qid))

            self.conn.commit()

        # 캐시 업데이트
        self._existing_qids.add(qid)
        self._qid_to_id[qid] = loc_id
        key = f"{lat:.4f},{lng:.4f}"
        self._coord_to_id[key] = loc_id

        return loc_id

    def _add_name_to_location(
        self,
        location_id: int,
        name: str,
        name_ko: Optional[str],
        wikidata_id: str
    ):
        """기존 위치에 명칭 추가"""
        with self.conn.cursor() as cur:
            # 이미 있는지 확인
            cur.execute("""
                SELECT id FROM location_names
                WHERE location_id = %s AND name = %s
            """, (location_id, name))

            if cur.fetchone():
                return

            cur.execute("""
                INSERT INTO location_names (
                    location_id, name, name_ko, language, is_primary,
                    wikidata_id, source
                )
                VALUES (%s, %s, %s, 'en', FALSE, %s, 'wikidata')
            """, (location_id, name, name_ko, wikidata_id))

            self.conn.commit()

    def close(self):
        """연결 종료"""
        self.conn.close()


def import_locations(input_path: str, limit: int = None):
    """추출된 위치 파일 임포트"""
    print("=== 위치 임포트 ===")
    print(f"입력: {input_path}")
    print(f"제한: {limit or '없음'}")
    print()

    if not os.path.exists(input_path):
        print(f"Error: 파일 없음: {input_path}")
        return

    importer = LocationImporter(DATABASE_URL)

    start_time = time.time()
    total = 0
    imported = 0
    skipped_exists = 0
    skipped_no_coords = 0
    merged = 0
    failed = 0

    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if limit and total >= limit:
                break

            try:
                loc_data = json.loads(line.strip())
                total += 1

                qid = loc_data['qid']
                was_existing = qid in importer._existing_qids

                loc_id = importer.import_location(loc_data)

                if loc_id:
                    if was_existing:
                        skipped_exists += 1
                    elif qid in importer._existing_qids:
                        # 새로 추가됨
                        if importer._find_nearby(
                            loc_data.get('latitude', 0),
                            loc_data.get('longitude', 0)
                        ):
                            merged += 1
                        else:
                            imported += 1
                else:
                    skipped_no_coords += 1

                if total % 10000 == 0:
                    elapsed = time.time() - start_time
                    rate = total / elapsed if elapsed > 0 else 0
                    print(f"  처리: {total:,} | 임포트: {imported:,} | 병합: {merged:,} | {rate:.0f}/s")

            except Exception as e:
                failed += 1
                if failed <= 5:
                    print(f"  Error: {e}")

    importer.close()
    elapsed = time.time() - start_time

    print()
    print("=== 완료 ===")
    print(f"총 처리: {total:,}")
    print(f"새로 생성: {imported:,}")
    print(f"기존 위치에 병합: {merged:,}")
    print(f"스킵 (이미 존재): {skipped_exists:,}")
    print(f"스킵 (좌표 없음): {skipped_no_coords:,}")
    print(f"실패: {failed}")
    print(f"소요 시간: {elapsed:.1f}초")


def main():
    parser = argparse.ArgumentParser(description='Import extracted locations to DB')
    parser.add_argument('--input', required=True, help='추출된 위치 파일 (JSONL)')
    parser.add_argument('--limit', type=int, help='임포트 개수 제한')

    args = parser.parse_args()

    import_locations(args.input, args.limit)


if __name__ == '__main__':
    main()
