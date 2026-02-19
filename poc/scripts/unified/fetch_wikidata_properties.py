"""
Wikidata에서 엔티티 속성(properties) 가져오기.

가져오는 데이터:
- P625: 좌표 (locations)
- P710: 이벤트 참가자 (events → persons)
- P1344: 참여한 이벤트 (persons → events)
- P22/P25/P26/P40: 가족관계 (부/모/배우자/자녀)
- P31/P279: 분류 (instance of / subclass of)

Usage:
    python fetch_wikidata_properties.py --type all
    python fetch_wikidata_properties.py --type locations --prop coordinates
    python fetch_wikidata_properties.py --type persons --prop family
    python fetch_wikidata_properties.py --incremental

"""

import psycopg2
import json
import urllib.request
import urllib.parse
import time
import argparse
import sys
from datetime import datetime

# Unbuffered output
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
BATCH_SIZE = 50

# Property IDs
PROPS = {
    # 좌표
    'P625': 'coordinate_location',
    # 가족관계
    'P22': 'father',
    'P25': 'mother',
    'P26': 'spouse',
    'P40': 'child',
    # 이벤트 참가
    'P710': 'participant',      # event → person
    'P1344': 'participant_in',  # person → event
    # 분류
    'P31': 'instance_of',
    'P279': 'subclass_of',
    # 위치 관련
    'P17': 'country',
    'P131': 'located_in',
    'P36': 'capital',
}


class WikidataPropertyFetcher:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cur = self.conn.cursor()
        self.stats = {
            'processed': 0,
            'coordinates_added': 0,
            'relationships_added': 0,
            'classifications_added': 0,
            'errors': 0
        }
        self._build_qid_cache()

    def _build_qid_cache(self):
        """QID → (entity_type, entity_id) 캐시 구축."""
        print("Building QID cache...")
        self.qid_cache = {}

        for entity_type, table in [('person', 'persons'), ('event', 'events'), ('location', 'locations')]:
            self.cur.execute(f"SELECT id, wikidata_id FROM {table} WHERE wikidata_id IS NOT NULL")
            for row in self.cur.fetchall():
                self.qid_cache[row[1]] = (entity_type, row[0])

        print(f"  Cached {len(self.qid_cache):,} QIDs")

    def get_entities_to_process(self, entity_type):
        """처리할 엔티티 목록."""
        table_map = {'person': 'persons', 'event': 'events', 'location': 'locations'}
        table = table_map[entity_type]

        self.cur.execute(f"""
            SELECT id, wikidata_id FROM {table}
            WHERE wikidata_id IS NOT NULL
            ORDER BY id
        """)
        return self.cur.fetchall()

    def fetch_wikidata_batch(self, qids):
        """Wikidata API로 claims 가져오기."""
        params = {
            'action': 'wbgetentities',
            'ids': '|'.join(qids),
            'props': 'claims',
            'format': 'json'
        }

        url = f"{WIKIDATA_API}?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'CHALDEAS/1.0 (https://chaldeas.site; historical-knowledge-system) Python/3.10'
            })
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
            return data.get('entities', {})
        except Exception as e:
            print(f"  API Error: {e}")
            self.stats['errors'] += 1
            return {}

    def extract_qid_from_claim(self, claim):
        """claim에서 QID 추출."""
        try:
            mainsnak = claim.get('mainsnak', {})
            datavalue = mainsnak.get('datavalue', {})
            if datavalue.get('type') == 'wikibase-entityid':
                return 'Q' + str(datavalue['value']['numeric-id'])
        except:
            pass
        return None

    def extract_coordinates(self, claim):
        """claim에서 좌표 추출."""
        try:
            mainsnak = claim.get('mainsnak', {})
            datavalue = mainsnak.get('datavalue', {})
            if datavalue.get('type') == 'globecoordinate':
                value = datavalue['value']
                return (value.get('latitude'), value.get('longitude'))
        except:
            pass
        return None

    def save_coordinate(self, entity_id, lat, lng):
        """좌표 저장."""
        try:
            self.cur.execute("""
                UPDATE locations
                SET latitude = %s, longitude = %s
                WHERE id = %s AND (latitude IS NULL OR longitude IS NULL)
            """, (lat, lng, entity_id))
            if self.cur.rowcount > 0:
                self.stats['coordinates_added'] += 1
                return True
        except Exception as e:
            pass
        return False

    def save_relationship(self, from_type, from_id, to_type, to_id, category):
        """관계 저장 (links 테이블)."""
        try:
            self.cur.execute("""
                INSERT INTO links (from_type, from_id, to_type, to_id, category)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (from_type, from_id, to_type, to_id, category))
            if self.cur.rowcount > 0:
                self.stats['relationships_added'] += 1
                return True
        except Exception as e:
            pass
        return False

    def save_classification(self, entity_type, entity_id, classification_qid, prop_type):
        """분류 정보 저장 (entity_tags 또는 별도 처리)."""
        # 분류 정보는 나중에 LLM 분류 대신 사용할 수 있음
        # 지금은 통계만 수집
        self.stats['classifications_added'] += 1
        return True

    def process_entity(self, entity_type, entity_id, qid, claims):
        """단일 엔티티의 claims 처리."""

        # 1. 좌표 (locations만)
        if entity_type == 'location' and 'P625' in claims:
            for claim in claims['P625']:
                coords = self.extract_coordinates(claim)
                if coords:
                    self.save_coordinate(entity_id, coords[0], coords[1])
                    break  # 첫 번째 좌표만

        # 2. 가족관계 (persons만)
        if entity_type == 'person':
            family_props = {'P22': 'father', 'P25': 'mother', 'P26': 'spouse', 'P40': 'child'}
            for prop, rel_type in family_props.items():
                if prop in claims:
                    for claim in claims[prop]:
                        target_qid = self.extract_qid_from_claim(claim)
                        if target_qid and target_qid in self.qid_cache:
                            target_type, target_id = self.qid_cache[target_qid]
                            if target_type == 'person':
                                self.save_relationship('person', entity_id, 'person', target_id, rel_type)

        # 3. 이벤트 참가자
        if entity_type == 'event' and 'P710' in claims:
            for claim in claims['P710']:
                target_qid = self.extract_qid_from_claim(claim)
                if target_qid and target_qid in self.qid_cache:
                    target_type, target_id = self.qid_cache[target_qid]
                    if target_type == 'person':
                        self.save_relationship('event', entity_id, 'person', target_id, 'participant')

        if entity_type == 'person' and 'P1344' in claims:
            for claim in claims['P1344']:
                target_qid = self.extract_qid_from_claim(claim)
                if target_qid and target_qid in self.qid_cache:
                    target_type, target_id = self.qid_cache[target_qid]
                    if target_type == 'event':
                        self.save_relationship('person', entity_id, 'event', target_id, 'participated_in')

        # 4. 분류 정보
        for prop in ['P31', 'P279']:
            if prop in claims:
                for claim in claims[prop]:
                    target_qid = self.extract_qid_from_claim(claim)
                    if target_qid:
                        self.save_classification(entity_type, entity_id, target_qid, PROPS[prop])

        self.stats['processed'] += 1

    def process_entity_type(self, entity_type):
        """특정 엔티티 타입 처리."""
        print(f"\n{'='*60}")
        print(f"Processing: {entity_type.upper()}")
        print(f"{'='*60}")

        entities = self.get_entities_to_process(entity_type)
        total = len(entities)
        print(f"Total entities: {total:,}")

        if total == 0:
            return

        # QID → entity_id 매핑
        qid_to_entity = {qid: eid for eid, qid in entities if qid}
        qids = list(qid_to_entity.keys())

        # 배치 처리
        for i in range(0, len(qids), BATCH_SIZE):
            batch = qids[i:i+BATCH_SIZE]

            entities_data = self.fetch_wikidata_batch(batch)

            for qid in batch:
                entity_id = qid_to_entity.get(qid)
                if not entity_id:
                    continue

                entity_data = entities_data.get(qid, {})
                claims = entity_data.get('claims', {})

                if claims:
                    self.process_entity(entity_type, entity_id, qid, claims)

            self.conn.commit()

            processed = min(i + BATCH_SIZE, len(qids))
            if processed % 500 == 0 or processed == len(qids):
                pct = processed / len(qids) * 100
                print(f"  Progress: {processed:,}/{len(qids):,} ({pct:.1f}%) - "
                      f"coords: {self.stats['coordinates_added']}, "
                      f"rels: {self.stats['relationships_added']}")

            time.sleep(0.1)  # Rate limiting

        print(f"\nCompleted {entity_type}:")
        print(f"  Processed: {self.stats['processed']:,}")
        print(f"  Coordinates added: {self.stats['coordinates_added']:,}")
        print(f"  Relationships added: {self.stats['relationships_added']:,}")
        print(f"  Errors: {self.stats['errors']:,}")

    def run(self, types):
        """전체 실행."""
        start_time = datetime.now()
        print(f"Started at: {start_time}")

        for entity_type in types:
            self.process_entity_type(entity_type)
            # Reset stats for next type
            for key in self.stats:
                self.stats[key] = 0

        end_time = datetime.now()
        duration = end_time - start_time
        print(f"\n{'='*60}")
        print(f"COMPLETED")
        print(f"{'='*60}")
        print(f"Duration: {duration}")

        # 최종 통계
        self.cur.execute("SELECT COUNT(*) FROM locations WHERE latitude IS NOT NULL")
        print(f"\nLocations with coordinates: {self.cur.fetchone()[0]:,}")

        self.cur.execute("SELECT category, COUNT(*) FROM links WHERE category IS NOT NULL GROUP BY category ORDER BY COUNT(*) DESC LIMIT 10")
        print("\nRelationship categories:")
        for row in self.cur.fetchall():
            print(f"  {row[0]}: {row[1]:,}")

    def close(self):
        self.conn.close()


def main():
    parser = argparse.ArgumentParser(description='Fetch Wikidata properties')
    parser.add_argument('--type', choices=['all', 'persons', 'events', 'locations'],
                        default='all', help='Entity type to process')
    args = parser.parse_args()

    type_map = {
        'all': ['location', 'person', 'event'],  # locations first for coordinates
        'persons': ['person'],
        'events': ['event'],
        'locations': ['location']
    }
    types = type_map[args.type]

    fetcher = WikidataPropertyFetcher()
    try:
        fetcher.run(types)
    finally:
        fetcher.close()


if __name__ == '__main__':
    main()
