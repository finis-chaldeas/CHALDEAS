"""
Wikidata 인물/장소 연결 및 계층 구조 임포트.

Phase 1: 이벤트에 연결된 인물 임포트 (P710 participant)
Phase 2: 이벤트 계층 구조 구축 (P361 part of)
Phase 3: 이벤트-장소 연결 (P276 location)
Phase 4: 클러스터 자동 생성

Usage:
    python import_persons_locations.py --phase 1  # 인물만
    python import_persons_locations.py --phase 2  # 계층만
    python import_persons_locations.py --phase 3  # 장소만
    python import_persons_locations.py --phase 4  # 클러스터
    python import_persons_locations.py --all      # 전체
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import requests
import psycopg2

WIKIDATA_ENDPOINT = 'https://query.wikidata.org/sparql'


class WikidataEnricher:
    """Wikidata 기반 데이터 강화."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.conn = None
        self.stats = {
            'persons_found': 0,
            'persons_created': 0,
            'persons_linked': 0,
            'locations_found': 0,
            'locations_created': 0,
            'locations_linked': 0,
            'hierarchy_links': 0,
            'clusters_created': 0,
            'errors': 0,
        }

    def connect_db(self):
        self.conn = psycopg2.connect(
            host='localhost', port=5432,
            database='chaldeas', user='chaldeas', password='chaldeas_dev'
        )

    def close_db(self):
        if self.conn:
            self.conn.close()

    def sparql_query(self, query: str, timeout: int = 60) -> List[Dict]:
        """SPARQL 쿼리 실행."""
        try:
            response = requests.get(
                WIKIDATA_ENDPOINT,
                params={'query': query, 'format': 'json'},
                timeout=timeout,
                headers={'User-Agent': 'CHALDEAS/1.0'}
            )
            if response.status_code == 200:
                return response.json()['results']['bindings']
            else:
                print(f"    SPARQL error: {response.status_code}")
                return []
        except Exception as e:
            print(f"    SPARQL error: {e}")
            return []

    # =========================================
    # Phase 1: 인물 연결
    # =========================================

    def phase1_import_persons(self, batch_size: int = 100):
        """이벤트에 연결된 인물들을 임포트 - 배치 처리."""
        print("\n" + "="*60)
        print("PHASE 1: Import Persons (P710 participants)")
        print("="*60)

        self.connect_db()
        cur = self.conn.cursor()

        # QID가 있는 이벤트 목록
        cur.execute("""
            SELECT id, wikidata_id, title
            FROM events
            WHERE wikidata_id IS NOT NULL
            ORDER BY id
        """)
        events = cur.fetchall()
        event_qid_to_id = {qid: eid for eid, qid, _ in events}
        all_qids = [qid for _, qid, _ in events]
        print(f"\nTotal events with QID: {len(events)}")

        # 배치로 P710 관계 가져오기
        for i in range(0, len(all_qids), batch_size):
            batch = all_qids[i:i+batch_size]
            print(f"  Batch {i//batch_size + 1}/{(len(all_qids)-1)//batch_size + 1}... (linked: {self.stats['persons_linked']})")

            # 배치 SPARQL 쿼리 - P607 (conflict) 사용 (역방향)
            # Wikidata에서 인물-이벤트 관계는 인물 쪽에 저장됨
            values = " ".join([f"wd:{qid}" for qid in batch])
            query = f"""
            SELECT ?event ?person ?personLabel ?personDescription
                   ?birthDate ?deathDate
            WHERE {{
                VALUES ?event {{ {values} }}
                ?person wdt:P607 ?event.  # person participated in event
                ?person wdt:P31 wd:Q5.
                OPTIONAL {{ ?person wdt:P569 ?birthDate. }}
                OPTIONAL {{ ?person wdt:P570 ?deathDate. }}
                SERVICE wikibase:label {{
                    bd:serviceParam wikibase:language "en".
                }}
            }}
            """
            results = self.sparql_query(query, timeout=120)

            for r in results:
                try:
                    event_qid = r.get('event', {}).get('value', '').split('/')[-1]
                    person_qid = r.get('person', {}).get('value', '').split('/')[-1]

                    if event_qid not in event_qid_to_id:
                        continue
                    if not person_qid.startswith('Q'):
                        continue

                    self.stats['persons_found'] += 1
                    event_id = event_qid_to_id[event_qid]

                    person = {
                        'qid': person_qid,
                        'name': r.get('personLabel', {}).get('value', '') or f'Person {person_qid}',
                        'description': r.get('personDescription', {}).get('value'),
                        'birth': r.get('birthDate', {}).get('value'),
                        'death': r.get('deathDate', {}).get('value'),
                    }
                    self._link_person_to_event(cur, event_id, person)

                except Exception as e:
                    self.conn.rollback()
                    self.stats['errors'] += 1
                    continue

            try:
                self.conn.commit()
            except:
                self.conn.rollback()

            time.sleep(1.5)  # Rate limiting between batches

        self.close_db()
        print(f"\nPhase 1 Complete:")
        print(f"  Persons found: {self.stats['persons_found']}")
        print(f"  Persons created: {self.stats['persons_created']}")
        print(f"  Links created: {self.stats['persons_linked']}")

    def _fetch_participants(self, event_qid: str) -> List[Dict]:
        """이벤트의 참여자 목록 가져오기."""
        query = f"""
        SELECT DISTINCT ?person ?personLabel ?personDescription
               ?birthDate ?deathDate
        WHERE {{
            wd:{event_qid} wdt:P710 ?person.
            ?person wdt:P31 wd:Q5.  # human only
            OPTIONAL {{ ?person wdt:P569 ?birthDate. }}
            OPTIONAL {{ ?person wdt:P570 ?deathDate. }}
            SERVICE wikibase:label {{
                bd:serviceParam wikibase:language "en".
            }}
        }}
        LIMIT 50
        """
        results = self.sparql_query(query, timeout=30)
        participants = []

        for r in results:
            person_qid = r.get('person', {}).get('value', '').split('/')[-1]
            if not person_qid.startswith('Q'):
                continue

            self.stats['persons_found'] += 1
            participants.append({
                'qid': person_qid,
                'name': r.get('personLabel', {}).get('value', ''),
                'description': r.get('personDescription', {}).get('value'),
                'birth': r.get('birthDate', {}).get('value'),
                'death': r.get('deathDate', {}).get('value'),
            })

        return participants

    def _link_person_to_event(self, cur, event_id: int, person: Dict):
        """인물을 이벤트에 연결."""
        if self.dry_run:
            return

        # 인물이 DB에 있는지 확인
        cur.execute("SELECT id FROM persons WHERE wikidata_id = %s", (person['qid'],))
        existing = cur.fetchone()

        if existing:
            person_id = existing[0]
        else:
            # 새 인물 생성
            try:
                import re
                slug = re.sub(r'[^a-z0-9]+', '-', person['name'].lower()).strip('-')[:100]

                # slug 중복 체크
                cur.execute("SELECT COUNT(*) FROM persons WHERE slug LIKE %s", (slug + '%',))
                if cur.fetchone()[0] > 0:
                    slug = f"{slug}-{person['qid'].lower()}"

                birth_year = self._parse_year(person.get('birth'))
                death_year = self._parse_year(person.get('death'))

                cur.execute("""
                    INSERT INTO persons (name, slug, description, birth_year, death_year,
                                        wikidata_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
                """, (person['name'], slug, person.get('description'),
                      birth_year, death_year, person['qid']))
                person_id = cur.fetchone()[0]
                self.stats['persons_created'] += 1
            except Exception as e:
                self.stats['errors'] += 1
                return

        # 연결 생성 (중복 무시)
        try:
            cur.execute("""
                INSERT INTO event_persons (event_id, person_id, role)
                VALUES (%s, %s, 'participant')
                ON CONFLICT DO NOTHING
            """, (event_id, person_id))
            self.stats['persons_linked'] += 1
        except Exception as e:
            self.stats['errors'] += 1

    def _parse_year(self, date_str: str) -> Optional[int]:
        """Wikidata 날짜에서 연도 추출."""
        if not date_str:
            return None
        try:
            if date_str.startswith('-'):
                return -int(date_str[1:5])
            elif date_str.startswith('+'):
                return int(date_str[1:5])
            else:
                return int(date_str[:4])
        except:
            return None

    # =========================================
    # Phase 2: 계층 구조
    # =========================================

    def phase2_build_hierarchy(self):
        """이벤트 계층 구조 구축 (P361 part of) - 배치 처리."""
        print("\n" + "="*60)
        print("PHASE 2: Build Event Hierarchy (P361 part of)")
        print("="*60)

        self.connect_db()
        cur = self.conn.cursor()

        # QID가 있는 이벤트들
        cur.execute("""
            SELECT id, wikidata_id, title
            FROM events
            WHERE wikidata_id IS NOT NULL
        """)
        events = cur.fetchall()
        event_qid_to_id = {qid: eid for eid, qid, _ in events}
        print(f"\nEvents with QID: {len(events)}")

        # 배치로 P361 관계 가져오기 (100개씩)
        all_qids = [qid for _, qid, _ in events]
        batch_size = 100
        linked = 0

        for i in range(0, len(all_qids), batch_size):
            batch = all_qids[i:i+batch_size]
            print(f"  Batch {i//batch_size + 1}/{(len(all_qids)-1)//batch_size + 1}...")

            # 배치 SPARQL 쿼리
            values = " ".join([f"wd:{qid}" for qid in batch])
            query = f"""
            SELECT ?item ?parent WHERE {{
                VALUES ?item {{ {values} }}
                ?item wdt:P361 ?parent.
            }}
            """
            results = self.sparql_query(query, timeout=60)

            for r in results:
                item_qid = r.get('item', {}).get('value', '').split('/')[-1]
                parent_qid = r.get('parent', {}).get('value', '').split('/')[-1]

                if item_qid in event_qid_to_id and parent_qid in event_qid_to_id:
                    event_id = event_qid_to_id[item_qid]
                    parent_id = event_qid_to_id[parent_qid]

                    if not self.dry_run:
                        try:
                            cur.execute("""
                                UPDATE events SET parent_event_id = %s
                                WHERE id = %s AND parent_event_id IS NULL
                            """, (parent_id, event_id))
                            if cur.rowcount > 0:
                                linked += 1
                                self.stats['hierarchy_links'] += 1
                        except:
                            self.conn.rollback()

            try:
                self.conn.commit()
            except:
                self.conn.rollback()

            time.sleep(1)  # Rate limit between batches

        self.close_db()
        print(f"\nPhase 2 Complete:")
        print(f"  Hierarchy links created: {self.stats['hierarchy_links']}")

    def _fetch_part_of(self, event_qid: str) -> Optional[str]:
        """이벤트의 상위 이벤트 QID 가져오기."""
        query = f"""
        SELECT ?parent WHERE {{
            wd:{event_qid} wdt:P361 ?parent.
        }}
        LIMIT 1
        """
        results = self.sparql_query(query, timeout=10)
        if results:
            parent_url = results[0].get('parent', {}).get('value', '')
            parent_qid = parent_url.split('/')[-1]
            if parent_qid.startswith('Q'):
                return parent_qid
        return None

    # =========================================
    # Phase 3: 장소 연결
    # =========================================

    def phase3_link_locations(self):
        """이벤트-장소 연결 (P276 location) - 배치 처리."""
        print("\n" + "="*60)
        print("PHASE 3: Link Locations (P276 location)")
        print("="*60)

        self.connect_db()
        cur = self.conn.cursor()

        # 장소가 없는 QID 이벤트
        cur.execute("""
            SELECT id, wikidata_id, title
            FROM events
            WHERE wikidata_id IS NOT NULL
              AND primary_location_id IS NULL
        """)
        events = cur.fetchall()
        event_qid_to_id = {qid: (eid, title) for eid, qid, title in events}
        print(f"\nEvents without location: {len(events)}")

        # 배치로 P276 관계 가져오기 (100개씩)
        all_qids = [qid for _, qid, _ in events]
        batch_size = 100

        for i in range(0, len(all_qids), batch_size):
            batch = all_qids[i:i+batch_size]
            print(f"  Batch {i//batch_size + 1}/{(len(all_qids)-1)//batch_size + 1}...")

            # 배치 SPARQL 쿼리
            values = " ".join([f"wd:{qid}" for qid in batch])
            query = f"""
            SELECT ?item ?location ?locationLabel ?coord WHERE {{
                VALUES ?item {{ {values} }}
                ?item wdt:P276 ?location.
                OPTIONAL {{ ?location wdt:P625 ?coord. }}
                SERVICE wikibase:label {{
                    bd:serviceParam wikibase:language "en".
                }}
            }}
            """
            results = self.sparql_query(query, timeout=90)

            for r in results:
                try:
                    item_qid = r.get('item', {}).get('value', '').split('/')[-1]
                    loc_qid = r.get('location', {}).get('value', '').split('/')[-1]

                    if item_qid not in event_qid_to_id:
                        continue
                    if not loc_qid.startswith('Q'):
                        continue

                    self.stats['locations_found'] += 1
                    event_id = event_qid_to_id[item_qid][0]

                    # 좌표 파싱
                    coord = r.get('coord', {}).get('value', '')
                    lat, lon = None, None
                    if coord.startswith('Point('):
                        try:
                            parts = coord[6:-1].split(' ')
                            lon, lat = float(parts[0]), float(parts[1])
                        except:
                            pass

                    location = {
                        'qid': loc_qid,
                        'name': r.get('locationLabel', {}).get('value', '') or f'Location {loc_qid}',
                        'lat': lat,
                        'lon': lon,
                    }
                    self._link_location_to_event(cur, event_id, location)
                except Exception as e:
                    self.conn.rollback()
                    self.stats['errors'] += 1
                    continue

            try:
                self.conn.commit()
            except:
                self.conn.rollback()

            time.sleep(1)

        self.close_db()
        print(f"\nPhase 3 Complete:")
        print(f"  Locations found: {self.stats['locations_found']}")
        print(f"  Locations created: {self.stats['locations_created']}")
        print(f"  Events linked: {self.stats['locations_linked']}")

    def _fetch_location(self, event_qid: str) -> Optional[Dict]:
        """이벤트의 장소 정보 가져오기."""
        query = f"""
        SELECT ?location ?locationLabel ?coord WHERE {{
            wd:{event_qid} wdt:P276 ?location.
            OPTIONAL {{ ?location wdt:P625 ?coord. }}
            SERVICE wikibase:label {{
                bd:serviceParam wikibase:language "en".
            }}
        }}
        LIMIT 1
        """
        results = self.sparql_query(query, timeout=15)
        if results:
            r = results[0]
            loc_qid = r.get('location', {}).get('value', '').split('/')[-1]
            if loc_qid.startswith('Q'):
                self.stats['locations_found'] += 1

                # 좌표 파싱
                coord = r.get('coord', {}).get('value', '')
                lat, lon = None, None
                if coord.startswith('Point('):
                    try:
                        parts = coord[6:-1].split(' ')
                        lon, lat = float(parts[0]), float(parts[1])
                    except:
                        pass

                return {
                    'qid': loc_qid,
                    'name': r.get('locationLabel', {}).get('value', ''),
                    'lat': lat,
                    'lon': lon,
                }
        return None

    def _link_location_to_event(self, cur, event_id: int, location: Dict):
        """장소를 이벤트에 연결."""
        if self.dry_run:
            return

        try:
            # 장소가 DB에 있는지 확인
            cur.execute("SELECT id FROM locations WHERE wikidata_id = %s", (location['qid'],))
            existing = cur.fetchone()

            if existing:
                location_id = existing[0]
            else:
                # 새 장소 생성
                import re
                slug = re.sub(r'[^a-z0-9]+', '-', location['name'].lower()).strip('-')[:100]
                if not slug:
                    slug = f"loc-{location['qid'].lower()}"

                cur.execute("SELECT COUNT(*) FROM locations WHERE slug LIKE %s", (slug + '%',))
                if cur.fetchone()[0] > 0:
                    slug = f"{slug}-{location['qid'].lower()}"

                # NOT NULL 필드들 기본값 설정
                lat = location['lat'] if location['lat'] is not None else 0.0
                lon = location['lon'] if location['lon'] is not None else 0.0

                cur.execute("""
                    INSERT INTO locations (name, slug, latitude, longitude, type,
                                          wikidata_id, display_level, display_zoom_min, display_zoom_max,
                                          created_at, updated_at)
                    VALUES (%s, %s, %s, %s, 'place', %s, 3, 0, 22, NOW(), NOW())
                    RETURNING id
                """, (location['name'], slug, lat, lon, location['qid']))
                location_id = cur.fetchone()[0]
                self.stats['locations_created'] += 1

            # 이벤트에 연결
            cur.execute("""
                UPDATE events SET primary_location_id = %s
                WHERE id = %s
            """, (location_id, event_id))
            self.stats['locations_linked'] += 1

        except Exception as e:
            self.conn.rollback()
            self.stats['errors'] += 1

    # =========================================
    # Phase 4: 클러스터 생성
    # =========================================

    def phase4_create_clusters(self):
        """관련 이벤트 클러스터 자동 생성."""
        print("\n" + "="*60)
        print("PHASE 4: Create Event Clusters")
        print("="*60)

        self.connect_db()
        cur = self.conn.cursor()

        # 1. 전쟁/캠페인 기반 클러스터 (parent_event_id 사용)
        print("\n  Creating war-based clusters...")
        cur.execute("""
            SELECT DISTINCT e1.parent_event_id, e2.title
            FROM events e1
            JOIN events e2 ON e1.parent_event_id = e2.id
            WHERE e1.parent_event_id IS NOT NULL
            GROUP BY e1.parent_event_id, e2.title
            HAVING COUNT(*) >= 3
        """)
        wars = cur.fetchall()
        print(f"    Found {len(wars)} potential war clusters")

        for parent_id, parent_title in wars:
            try:
                self._create_cluster(cur, f"Events of {parent_title}", 'war', parent_id)
            except:
                self.conn.rollback()
        try:
            self.conn.commit()
        except:
            self.conn.rollback()

        # 2. 시간+공간 근접 클러스터
        print("\n  Creating spatiotemporal clusters...")
        cur.execute("""
            SELECT e.primary_location_id, l.name,
                   FLOOR(e.date_start / 50) * 50 as era,
                   COUNT(*) as cnt
            FROM events e
            JOIN locations l ON e.primary_location_id = l.id
            WHERE e.wikidata_id IS NOT NULL
            GROUP BY e.primary_location_id, l.name, era
            HAVING COUNT(*) >= 5
            ORDER BY cnt DESC
            LIMIT 100
        """)
        spatiotemporal = cur.fetchall()
        print(f"    Found {len(spatiotemporal)} spatiotemporal clusters")

        for loc_id, loc_name, era, cnt in spatiotemporal:
            try:
                era_str = f"{int(abs(era))} {'BCE' if era < 0 else 'CE'}"
                cluster_name = f"{loc_name} ({era_str}s)"
                self._create_cluster(cur, cluster_name, 'spatiotemporal',
                                    location_id=loc_id, era=int(era))
            except:
                self.conn.rollback()

        self.conn.commit()
        self.close_db()
        print(f"\nPhase 4 Complete:")
        print(f"  Clusters created: {self.stats['clusters_created']}")

    def _create_cluster(self, cur, name: str, cluster_type: str,
                       parent_event_id: int = None, location_id: int = None, era: int = None):
        """클러스터 생성."""
        if self.dry_run:
            return

        try:
            import re
            slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')[:100]
            if not slug:
                slug = f"cluster-{cluster_type}"

            # 중복 slug 처리
            cur.execute("SELECT COUNT(*) FROM clusters WHERE slug = %s", (slug,))
            if cur.fetchone()[0] > 0:
                return  # 이미 존재

            cur.execute("""
                INSERT INTO clusters (name, slug, cluster_type, is_auto_generated,
                                     focal_location_id, created_at, updated_at)
                VALUES (%s, %s, %s, TRUE, %s, NOW(), NOW())
                RETURNING id
            """, (name, slug, cluster_type, location_id))

            result = cur.fetchone()
            if result:
                self.stats['clusters_created'] += 1
        except Exception as e:
            self.conn.rollback()
            self.stats['errors'] += 1

    def print_stats(self):
        print("\n" + "="*40)
        print("FINAL STATISTICS")
        print("="*40)
        for k, v in self.stats.items():
            print(f"  {k}: {v}")


def main():
    parser = argparse.ArgumentParser(description='Wikidata Enrichment')
    parser.add_argument('--phase', type=int, choices=[1, 2, 3, 4],
                        help='Run specific phase (1=persons, 2=hierarchy, 3=locations, 4=clusters)')
    parser.add_argument('--all', action='store_true', help='Run all phases')
    parser.add_argument('--dry-run', action='store_true', help='Dry run')

    args = parser.parse_args()

    enricher = WikidataEnricher(dry_run=args.dry_run)

    if args.all:
        enricher.phase1_import_persons()
        enricher.phase2_build_hierarchy()
        enricher.phase3_link_locations()
        enricher.phase4_create_clusters()
    elif args.phase == 1:
        enricher.phase1_import_persons()
    elif args.phase == 2:
        enricher.phase2_build_hierarchy()
    elif args.phase == 3:
        enricher.phase3_link_locations()
    elif args.phase == 4:
        enricher.phase4_create_clusters()
    else:
        print("Usage: --phase 1|2|3|4 or --all")
        return

    enricher.print_stats()


if __name__ == '__main__':
    main()
