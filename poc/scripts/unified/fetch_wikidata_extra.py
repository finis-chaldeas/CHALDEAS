"""
Wikidata 추가 속성 가져오기.

수집 항목:
- P106: 직업 (occupation)
- P39: 직위 (position held)
- P19/P20: 출생/사망지 (birthplace/deathplace)
- P607: 참전 전쟁 (conflict)
- P1542/P1536: 원인/결과 (cause/effect) - 이벤트용

Usage:
    python fetch_wikidata_extra.py --type all
    python fetch_wikidata_extra.py --type persons
    python fetch_wikidata_extra.py --type events
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

# 추가 수집할 속성들
EXTRA_PROPS = {
    # 인물용
    'P106': 'occupation',        # 직업
    'P39': 'position_held',      # 직위
    'P19': 'birthplace',         # 출생지
    'P20': 'deathplace',         # 사망지
    'P607': 'conflict',          # 참전 전쟁
    'P27': 'citizenship',        # 국적
    'P69': 'educated_at',        # 교육 기관
    'P119': 'burial_place',      # 매장지
    'P410': 'military_rank',     # 군사 계급
    'P509': 'cause_of_death',    # 사망 원인
    'P1066': 'student_of',       # 스승
    'P802': 'student',           # 제자

    # 이벤트용
    'P1542': 'has_cause',        # 원인
    'P1536': 'has_effect',       # 결과
    'P276': 'location',          # 발생 장소
    'P361': 'part_of',           # 상위 이벤트
    'P527': 'has_part',          # 하위 이벤트
}


class WikidataExtraFetcher:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cur = self.conn.cursor()
        self.stats = {
            'processed': 0,
            'sitelinks': 0,
            'occupations': 0,
            'positions': 0,
            'military_ranks': 0,
            'birthplaces': 0,
            'deathplaces': 0,
            'burial_places': 0,
            'educated_at': 0,
            'student_of': 0,
            'students': 0,
            'conflicts': 0,
            'causes': 0,
            'effects': 0,
            'locations': 0,
            'errors': 0
        }
        self._build_qid_cache()
        self._ensure_tables()

    def _build_qid_cache(self):
        """QID → (entity_type, entity_id) 캐시."""
        print("Building QID cache...")
        self.qid_cache = {}

        for entity_type, table in [('person', 'persons'), ('event', 'events'), ('location', 'locations')]:
            self.cur.execute(f"SELECT id, wikidata_id FROM {table} WHERE wikidata_id IS NOT NULL")
            for row in self.cur.fetchall():
                self.qid_cache[row[1]] = (entity_type, row[0])

        print(f"  Cached {len(self.qid_cache):,} QIDs")

    def _ensure_tables(self):
        """필요한 테이블/컬럼 확인."""
        # entity_attributes 테이블 (직업, 직위, 국적 등 저장)
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS entity_attributes (
                id SERIAL PRIMARY KEY,
                entity_type VARCHAR(20) NOT NULL,
                entity_id INTEGER NOT NULL,
                attribute_type VARCHAR(50) NOT NULL,
                attribute_value TEXT,
                attribute_qid VARCHAR(20),
                source VARCHAR(20) DEFAULT 'wikidata',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(entity_type, entity_id, attribute_type, attribute_qid)
            )
        """)

        # 인덱스
        self.cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_attr_lookup
            ON entity_attributes(entity_type, entity_id)
        """)
        self.cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_attr_type
            ON entity_attributes(attribute_type)
        """)

        # sitelinks_count 컬럼 추가 (각 테이블에)
        for table in ['persons', 'events', 'locations']:
            try:
                self.cur.execute(f"""
                    ALTER TABLE {table} ADD COLUMN IF NOT EXISTS sitelinks_count INTEGER
                """)
            except:
                pass  # 이미 존재하면 무시

        self.conn.commit()
        print("  Tables ready")

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
        """Wikidata API로 claims + sitelinks 가져오기."""
        params = {
            'action': 'wbgetentities',
            'ids': '|'.join(qids),
            'props': 'claims|labels|sitelinks',
            'languages': 'en',
            'format': 'json'
        }

        url = f"{WIKIDATA_API}?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'CHALDEAS/1.0 (https://chaldeas.site) Python/3.10'
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

    def get_label_for_qid(self, qid, entities_data):
        """QID의 영문 라벨 가져오기."""
        entity = entities_data.get(qid, {})
        labels = entity.get('labels', {})
        en_label = labels.get('en', {})
        return en_label.get('value', qid)

    def save_attribute(self, entity_type, entity_id, attr_type, attr_value, attr_qid=None):
        """속성 저장."""
        try:
            self.cur.execute("""
                INSERT INTO entity_attributes
                (entity_type, entity_id, attribute_type, attribute_value, attribute_qid)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (entity_type, entity_id, attribute_type, attribute_qid) DO NOTHING
            """, (entity_type, entity_id, attr_type, attr_value, attr_qid))
            return self.cur.rowcount > 0
        except Exception as e:
            return False

    def save_link(self, from_type, from_id, to_type, to_id, category):
        """관계 저장 (links 테이블)."""
        try:
            self.cur.execute("""
                INSERT INTO links (from_type, from_id, to_type, to_id, category)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (from_type, from_id, to_type, to_id, category))
            return self.cur.rowcount > 0
        except:
            return False

    def save_sitelinks_count(self, entity_type, entity_id, count):
        """sitelinks 수 저장."""
        table_map = {'person': 'persons', 'event': 'events', 'location': 'locations'}
        table = table_map.get(entity_type)
        if not table:
            return False
        try:
            self.cur.execute(f"""
                UPDATE {table} SET sitelinks_count = %s WHERE id = %s
            """, (count, entity_id))
            return self.cur.rowcount > 0
        except:
            return False

    def process_person(self, entity_id, qid, claims, entity_data):
        """인물 속성 처리."""

        # Sitelinks 수 저장
        sitelinks = entity_data.get('sitelinks', {})
        if sitelinks:
            if self.save_sitelinks_count('person', entity_id, len(sitelinks)):
                self.stats['sitelinks'] += 1

        # P106: 직업
        if 'P106' in claims:
            for claim in claims['P106']:
                occ_qid = self.extract_qid_from_claim(claim)
                if occ_qid:
                    occ_label = self.get_label_for_qid(occ_qid, {})
                    if self.save_attribute('person', entity_id, 'occupation', occ_label, occ_qid):
                        self.stats['occupations'] += 1

        # P39: 직위
        if 'P39' in claims:
            for claim in claims['P39']:
                pos_qid = self.extract_qid_from_claim(claim)
                if pos_qid:
                    pos_label = self.get_label_for_qid(pos_qid, {})
                    if self.save_attribute('person', entity_id, 'position_held', pos_label, pos_qid):
                        self.stats['positions'] += 1

        # P410: 군사 계급
        if 'P410' in claims:
            for claim in claims['P410']:
                rank_qid = self.extract_qid_from_claim(claim)
                if rank_qid:
                    rank_label = self.get_label_for_qid(rank_qid, {})
                    if self.save_attribute('person', entity_id, 'military_rank', rank_label, rank_qid):
                        self.stats['military_ranks'] += 1

        # P509: 사망 원인
        if 'P509' in claims:
            for claim in claims['P509'][:1]:
                cause_qid = self.extract_qid_from_claim(claim)
                if cause_qid:
                    cause_label = self.get_label_for_qid(cause_qid, {})
                    self.save_attribute('person', entity_id, 'cause_of_death', cause_label, cause_qid)

        # P19: 출생지
        if 'P19' in claims:
            for claim in claims['P19'][:1]:
                place_qid = self.extract_qid_from_claim(claim)
                if place_qid and place_qid in self.qid_cache:
                    target_type, target_id = self.qid_cache[place_qid]
                    if target_type == 'location':
                        if self.save_link('person', entity_id, 'location', target_id, 'birthplace'):
                            self.stats['birthplaces'] += 1

        # P20: 사망지
        if 'P20' in claims:
            for claim in claims['P20'][:1]:
                place_qid = self.extract_qid_from_claim(claim)
                if place_qid and place_qid in self.qid_cache:
                    target_type, target_id = self.qid_cache[place_qid]
                    if target_type == 'location':
                        if self.save_link('person', entity_id, 'location', target_id, 'deathplace'):
                            self.stats['deathplaces'] += 1

        # P119: 매장지
        if 'P119' in claims:
            for claim in claims['P119'][:1]:
                place_qid = self.extract_qid_from_claim(claim)
                if place_qid and place_qid in self.qid_cache:
                    target_type, target_id = self.qid_cache[place_qid]
                    if target_type == 'location':
                        if self.save_link('person', entity_id, 'location', target_id, 'burial_place'):
                            self.stats['burial_places'] += 1

        # P69: 교육 기관
        if 'P69' in claims:
            for claim in claims['P69']:
                school_qid = self.extract_qid_from_claim(claim)
                if school_qid and school_qid in self.qid_cache:
                    target_type, target_id = self.qid_cache[school_qid]
                    if target_type == 'location':
                        if self.save_link('person', entity_id, 'location', target_id, 'educated_at'):
                            self.stats['educated_at'] += 1

        # P1066: 스승
        if 'P1066' in claims:
            for claim in claims['P1066']:
                teacher_qid = self.extract_qid_from_claim(claim)
                if teacher_qid and teacher_qid in self.qid_cache:
                    target_type, target_id = self.qid_cache[teacher_qid]
                    if target_type == 'person':
                        if self.save_link('person', entity_id, 'person', target_id, 'student_of'):
                            self.stats['student_of'] += 1

        # P802: 제자
        if 'P802' in claims:
            for claim in claims['P802']:
                student_qid = self.extract_qid_from_claim(claim)
                if student_qid and student_qid in self.qid_cache:
                    target_type, target_id = self.qid_cache[student_qid]
                    if target_type == 'person':
                        if self.save_link('person', entity_id, 'person', target_id, 'teacher_of'):
                            self.stats['students'] += 1

        # P607: 참전 전쟁
        if 'P607' in claims:
            for claim in claims['P607']:
                event_qid = self.extract_qid_from_claim(claim)
                if event_qid and event_qid in self.qid_cache:
                    target_type, target_id = self.qid_cache[event_qid]
                    if target_type == 'event':
                        if self.save_link('person', entity_id, 'event', target_id, 'fought_in'):
                            self.stats['conflicts'] += 1

    def process_event(self, entity_id, qid, claims, entity_data):
        """이벤트 속성 처리."""

        # Sitelinks 수 저장
        sitelinks = entity_data.get('sitelinks', {})
        if sitelinks:
            if self.save_sitelinks_count('event', entity_id, len(sitelinks)):
                self.stats['sitelinks'] += 1

        # P276: 발생 장소
        if 'P276' in claims:
            for claim in claims['P276'][:1]:
                place_qid = self.extract_qid_from_claim(claim)
                if place_qid and place_qid in self.qid_cache:
                    target_type, target_id = self.qid_cache[place_qid]
                    if target_type == 'location':
                        if self.save_link('event', entity_id, 'location', target_id, 'occurred_at'):
                            self.stats['locations'] += 1

        # P1542: 원인
        if 'P1542' in claims:
            for claim in claims['P1542']:
                cause_qid = self.extract_qid_from_claim(claim)
                if cause_qid and cause_qid in self.qid_cache:
                    target_type, target_id = self.qid_cache[cause_qid]
                    if target_type == 'event':
                        if self.save_link('event', entity_id, 'event', target_id, 'caused_by'):
                            self.stats['causes'] += 1

        # P1536: 결과
        if 'P1536' in claims:
            for claim in claims['P1536']:
                effect_qid = self.extract_qid_from_claim(claim)
                if effect_qid and effect_qid in self.qid_cache:
                    target_type, target_id = self.qid_cache[effect_qid]
                    if target_type == 'event':
                        if self.save_link('event', entity_id, 'event', target_id, 'resulted_in'):
                            self.stats['effects'] += 1

        # P361: 상위 이벤트 (part of)
        if 'P361' in claims:
            for claim in claims['P361']:
                parent_qid = self.extract_qid_from_claim(claim)
                if parent_qid and parent_qid in self.qid_cache:
                    target_type, target_id = self.qid_cache[parent_qid]
                    if target_type == 'event':
                        self.save_link('event', entity_id, 'event', target_id, 'part_of')

        # P527: 하위 이벤트 (has part)
        if 'P527' in claims:
            for claim in claims['P527']:
                child_qid = self.extract_qid_from_claim(claim)
                if child_qid and child_qid in self.qid_cache:
                    target_type, target_id = self.qid_cache[child_qid]
                    if target_type == 'event':
                        self.save_link('event', entity_id, 'event', target_id, 'has_part')

    def process_location(self, entity_id, qid, claims, entity_data):
        """장소 속성 처리."""

        # Sitelinks 수 저장
        sitelinks = entity_data.get('sitelinks', {})
        if sitelinks:
            if self.save_sitelinks_count('location', entity_id, len(sitelinks)):
                self.stats['sitelinks'] += 1

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

        qid_to_entity = {qid: eid for eid, qid in entities if qid}
        qids = list(qid_to_entity.keys())

        for i in range(0, len(qids), BATCH_SIZE):
            batch = qids[i:i+BATCH_SIZE]

            # 추가로 참조되는 QID들의 라벨도 가져오기 위해 두 번 요청
            entities_data = self.fetch_wikidata_batch(batch)

            for qid in batch:
                entity_id = qid_to_entity.get(qid)
                if not entity_id:
                    continue

                entity_data = entities_data.get(qid, {})
                claims = entity_data.get('claims', {})

                if entity_type == 'person':
                    self.process_person(entity_id, qid, claims, entity_data)
                elif entity_type == 'event':
                    self.process_event(entity_id, qid, claims, entity_data)
                elif entity_type == 'location':
                    self.process_location(entity_id, qid, claims, entity_data)

                self.stats['processed'] += 1

            self.conn.commit()

            processed = min(i + BATCH_SIZE, len(qids))
            if processed % 500 == 0 or processed == len(qids):
                pct = processed / len(qids) * 100
                print(f"  Progress: {processed:,}/{len(qids):,} ({pct:.1f}%) - "
                      f"occ:{self.stats['occupations']}, pos:{self.stats['positions']}, "
                      f"birth:{self.stats['birthplaces']}, death:{self.stats['deathplaces']}")

            time.sleep(0.1)

        print(f"\nCompleted {entity_type}:")
        for key, value in self.stats.items():
            if value > 0:
                print(f"  {key}: {value:,}")

    def run(self, types):
        """전체 실행."""
        start_time = datetime.now()
        print(f"Started at: {start_time}")

        for entity_type in types:
            self.process_entity_type(entity_type)
            # Reset stats
            for key in self.stats:
                self.stats[key] = 0

        end_time = datetime.now()
        print(f"\n{'='*60}")
        print(f"COMPLETED")
        print(f"{'='*60}")
        print(f"Duration: {end_time - start_time}")

        # 최종 통계
        self.cur.execute("""
            SELECT attribute_type, COUNT(*)
            FROM entity_attributes
            GROUP BY attribute_type
            ORDER BY COUNT(*) DESC
        """)
        print("\nAttribute counts:")
        for row in self.cur.fetchall():
            print(f"  {row[0]}: {row[1]:,}")

        self.cur.execute("""
            SELECT category, COUNT(*)
            FROM links
            WHERE category IN ('birthplace', 'deathplace', 'fought_in', 'occurred_at', 'caused_by', 'resulted_in')
            GROUP BY category
        """)
        print("\nNew link categories:")
        for row in self.cur.fetchall():
            print(f"  {row[0]}: {row[1]:,}")

    def close(self):
        self.conn.close()


def main():
    parser = argparse.ArgumentParser(description='Fetch extra Wikidata properties')
    parser.add_argument('--type', choices=['all', 'persons', 'events', 'locations'],
                        default='all', help='Entity type to process')
    args = parser.parse_args()

    type_map = {
        'all': ['person', 'event', 'location'],
        'persons': ['person'],
        'events': ['event'],
        'locations': ['location'],
    }
    types = type_map[args.type]

    fetcher = WikidataExtraFetcher()
    try:
        fetcher.run(types)
    finally:
        fetcher.close()


if __name__ == '__main__':
    main()
