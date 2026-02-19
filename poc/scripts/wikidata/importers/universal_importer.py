"""
범용 임포터 - 데이터 소스에 상관없이 동작

Usage:
    from data_access import SparqlSource, DumpSource
    from importers.universal_importer import UniversalImporter

    # API 사용
    source = SparqlSource()
    importer = UniversalImporter(db_url)
    importer.import_all(source, event_limit=1000)

    # 덤프 사용
    source = DumpSource('/path/to/dump.bz2')
    importer.import_all(source, event_limit=100000)
"""

import sys
import os
import time
import re
from typing import Optional, Set, Dict

import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_access.base import DataSource, RawEvent, RawLocation, RawPerson


def parse_wikidata_time(time_str: str) -> Optional[int]:
    """Wikidata 시간 문자열 → 연도"""
    if not time_str:
        return None
    try:
        if time_str.startswith('+'):
            time_str = time_str[1:]
        if time_str.startswith('-'):
            year_str = time_str[1:].split('T')[0].split('-')[0]
            return -int(year_str)
        year_str = time_str.split('T')[0].split('-')[0]
        return int(year_str)
    except (ValueError, IndexError):
        return None


class UniversalImporter:
    """범용 임포터 - 어떤 데이터 소스든 동일하게 처리"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn = psycopg2.connect(db_url)

        # 캐시
        self._location_qid_to_id: Dict[str, int] = {}
        self._person_qid_to_id: Dict[str, int] = {}
        self._event_qids: Set[str] = set()

        self._load_caches()

    def _load_caches(self):
        """기존 데이터 캐시 로드"""
        with self.conn.cursor() as cur:
            # 위치
            cur.execute("SELECT id, wikidata_id FROM locations WHERE wikidata_id IS NOT NULL")
            for row in cur:
                self._location_qid_to_id[row[1]] = row[0]

            # 인물
            cur.execute("SELECT id, wikidata_id FROM persons WHERE wikidata_id IS NOT NULL")
            for row in cur:
                self._person_qid_to_id[row[1]] = row[0]

            # 이벤트
            cur.execute("SELECT wikidata_id FROM events WHERE wikidata_id IS NOT NULL")
            for row in cur:
                self._event_qids.add(row[0])

        print(f"캐시 로드: 위치 {len(self._location_qid_to_id)}, 인물 {len(self._person_qid_to_id)}, 이벤트 {len(self._event_qids)}")

    def import_all(self, source: DataSource, event_limit: int = None):
        """전체 임포트 (위치 → 인물 → 이벤트)"""
        print("=" * 50)
        print("범용 임포트 시작")
        print("=" * 50)

        # 1. 이벤트 가져오면서 필요한 위치/인물 QID 수집
        print("\n[1/4] 이벤트 스캔 및 위치/인물 QID 수집...")
        events = []
        needed_location_qids = set()
        needed_person_qids = set()

        for event in source.get_events(limit=event_limit):
            events.append(event)
            for qid in event.location_qids:
                if qid not in self._location_qid_to_id:
                    needed_location_qids.add(qid)
            for qid in event.participant_qids:
                if qid not in self._person_qid_to_id:
                    needed_person_qids.add(qid)

        print(f"  이벤트: {len(events)}")
        print(f"  필요한 새 위치: {len(needed_location_qids)}")
        print(f"  필요한 새 인물: {len(needed_person_qids)}")

        # 2. 위치 임포트
        print(f"\n[2/4] 위치 임포트 ({len(needed_location_qids)}개)...")
        loc_imported = 0
        for qid in needed_location_qids:
            loc = source.get_location(qid)
            if loc:
                loc_id = self._import_location(loc)
                if loc_id:
                    loc_imported += 1
        print(f"  임포트됨: {loc_imported}")

        # 3. 인물 임포트
        print(f"\n[3/4] 인물 임포트 ({len(needed_person_qids)}개)...")
        person_imported = 0
        for qid in needed_person_qids:
            person = source.get_person(qid)
            if person:
                person_id = self._import_person(person)
                if person_id:
                    person_imported += 1
        print(f"  임포트됨: {person_imported}")

        # 4. 이벤트 임포트
        print(f"\n[4/4] 이벤트 임포트 ({len(events)}개)...")
        event_imported = 0
        event_with_loc = 0
        event_with_person = 0

        for event in events:
            result = self._import_event(event)
            if result:
                event_imported += 1
                if result['has_location']:
                    event_with_loc += 1
                if result['has_person']:
                    event_with_person += 1

        print(f"  임포트됨: {event_imported}")
        print(f"  위치 연결: {event_with_loc} ({100*event_with_loc/event_imported:.1f}%)" if event_imported else "")
        print(f"  인물 연결: {event_with_person} ({100*event_with_person/event_imported:.1f}%)" if event_imported else "")

        print("\n" + "=" * 50)
        print("완료")

    def _import_location(self, loc: RawLocation) -> Optional[int]:
        """위치 임포트"""
        if loc.qid in self._location_qid_to_id:
            return self._location_qid_to_id[loc.qid]

        if loc.latitude is None or loc.longitude is None:
            return None

        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO locations (
                    name, name_ko, latitude, longitude, type,
                    wikidata_id, coords_source, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'exact', NOW(), NOW())
                RETURNING id
            """, (
                loc.name,
                loc.name_ko,
                loc.latitude,
                loc.longitude,
                loc.location_type or 'unknown',
                loc.qid,
            ))
            loc_id = cur.fetchone()[0]

            # location_names에도 추가
            cur.execute("""
                INSERT INTO location_names (
                    location_id, name, name_ko, language, is_primary,
                    wikidata_id, source
                )
                VALUES (%s, %s, %s, 'en', TRUE, %s, 'wikidata')
            """, (loc_id, loc.name, loc.name_ko, loc.qid))

            self.conn.commit()

        self._location_qid_to_id[loc.qid] = loc_id
        return loc_id

    def _import_person(self, person: RawPerson) -> Optional[int]:
        """인물 임포트"""
        if person.qid in self._person_qid_to_id:
            return self._person_qid_to_id[person.qid]

        birth_year = parse_wikidata_time(person.birth_date)
        death_year = parse_wikidata_time(person.death_date)

        # slug 생성
        slug_base = re.sub(r'[^a-z0-9]+', '-', person.name.lower()).strip('-')
        slug = f"{slug_base}-{person.qid.lower()}"

        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO persons (
                    name, name_ko, slug, biography,
                    birth_year, death_year, wikidata_id,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id
            """, (
                person.name,
                person.name_ko,
                slug,
                person.description,
                birth_year,
                death_year,
                person.qid,
            ))
            person_id = cur.fetchone()[0]
            self.conn.commit()

        self._person_qid_to_id[person.qid] = person_id
        return person_id

    def _import_event(self, event: RawEvent) -> Optional[dict]:
        """이벤트 임포트"""
        if event.qid in self._event_qids:
            return None

        date_start = parse_wikidata_time(event.point_in_time or event.start_time)
        if date_start is None:
            return None

        date_end = parse_wikidata_time(event.end_time)

        # slug 생성
        slug_base = re.sub(r'[^a-z0-9]+', '-', event.name.lower()).strip('-')
        slug = f"{slug_base}-{event.qid.lower()}"

        # primary location
        primary_location_id = None
        for qid in event.location_qids:
            if qid in self._location_qid_to_id:
                primary_location_id = self._location_qid_to_id[qid]
                break

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
                event.name,
                event.name_ko,
                event.description,
                slug,
                date_start,
                date_end,
                event.qid,
                primary_location_id,
            ))
            event_id = cur.fetchone()[0]

            # event_locations 연결
            has_location = False
            for qid in event.location_qids:
                loc_id = self._location_qid_to_id.get(qid)
                if loc_id:
                    has_location = True
                    try:
                        cur.execute("""
                            INSERT INTO event_locations (event_id, location_id, role)
                            VALUES (%s, %s, 'location')
                            ON CONFLICT DO NOTHING
                        """, (event_id, loc_id))
                    except:
                        pass

            # event_persons 연결
            has_person = False
            for qid in event.participant_qids:
                person_id = self._person_qid_to_id.get(qid)
                if person_id:
                    has_person = True
                    try:
                        cur.execute("""
                            INSERT INTO event_persons (event_id, person_id, role)
                            VALUES (%s, %s, 'participant')
                            ON CONFLICT DO NOTHING
                        """, (event_id, person_id))
                    except:
                        pass

            self.conn.commit()

        self._event_qids.add(event.qid)
        return {'has_location': has_location, 'has_person': has_person}

    def close(self):
        self.conn.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--source', choices=['sparql', 'dump'], default='sparql')
    parser.add_argument('--dump-path', help='덤프 파일 경로 (--source dump 시)')
    parser.add_argument('--limit', type=int, default=100, help='이벤트 제한')
    args = parser.parse_args()

    db_url = os.environ.get('DATABASE_URL', 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas')

    if args.source == 'sparql':
        from data_access import SparqlSource
        source = SparqlSource()
    else:
        from data_access import DumpSource
        source = DumpSource(args.dump_path)

    importer = UniversalImporter(db_url)
    importer.import_all(source, event_limit=args.limit)
    importer.close()
