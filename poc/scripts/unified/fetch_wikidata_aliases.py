"""
Wikidata에서 모든 엔티티의 별칭(aliases) 가져오기.

Usage:
    python fetch_wikidata_aliases.py --type all          # 전체 (persons + events + locations)
    python fetch_wikidata_aliases.py --type persons      # persons만
    python fetch_wikidata_aliases.py --type events       # events만
    python fetch_wikidata_aliases.py --incremental       # 아직 안 가져온 것만

Features:
    - Wikidata API 배치 요청 (50개씩)
    - entity_aliases 테이블에 저장
    - 중복 방지 (ON CONFLICT DO NOTHING)
    - 진행률 표시
"""

import psycopg2
import json
import urllib.request
import urllib.parse
import time
import argparse
import sys
from datetime import datetime

# Unbuffered output for background execution
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
BATCH_SIZE = 50  # Wikidata API 최대 배치 크기
LANGUAGES = ['en', 'ko', 'ja', 'zh', 'la', 'de', 'fr', 'es', 'it', 'ru', 'ar', 'grc', 'cy']  # 주요 언어


class WikidataAliasFetcher:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cur = self.conn.cursor()
        self.stats = {
            'total': 0,
            'processed': 0,
            'aliases_added': 0,
            'errors': 0,
            'skipped': 0
        }

    def get_entities_to_process(self, entity_type, incremental=False):
        """처리할 엔티티 목록 가져오기."""
        table_map = {
            'person': 'persons',
            'event': 'events',
            'location': 'locations'
        }
        table = table_map[entity_type]

        if incremental:
            # 아직 alias가 없는 엔티티만
            query = f"""
                SELECT DISTINCT p.id, p.wikidata_id
                FROM {table} p
                LEFT JOIN entity_aliases ea ON ea.entity_type = %s AND ea.entity_id = p.id
                WHERE p.wikidata_id IS NOT NULL
                  AND ea.id IS NULL
                ORDER BY p.id
            """
            self.cur.execute(query, (entity_type,))
        else:
            # 전체
            query = f"""
                SELECT id, wikidata_id
                FROM {table}
                WHERE wikidata_id IS NOT NULL
                ORDER BY id
            """
            self.cur.execute(query)

        return self.cur.fetchall()

    def fetch_wikidata_batch(self, qids):
        """Wikidata API로 여러 엔티티 정보 배치 요청."""
        params = {
            'action': 'wbgetentities',
            'ids': '|'.join(qids),
            'props': 'labels|aliases',
            'languages': '|'.join(LANGUAGES),
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
            return {}

    def save_aliases(self, entity_type, entity_id, qid, entity_data):
        """엔티티의 별칭을 DB에 저장."""
        aliases_added = 0

        # 1. labels (각 언어별 메인 이름) - 'translation' 타입 사용
        labels = entity_data.get('labels', {})
        for lang, label_info in labels.items():
            label = label_info.get('value', '')
            if label:
                try:
                    self.cur.execute("""
                        INSERT INTO entity_aliases (entity_type, entity_id, alias, alias_type, language)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (entity_type, entity_id, label, 'translation', lang))
                    if self.cur.rowcount > 0:
                        aliases_added += 1
                except Exception as e:
                    pass  # 중복 무시

        # 2. aliases (각 언어별 별칭들) - 'wikidata' 타입 사용
        aliases = entity_data.get('aliases', {})
        for lang, alias_list in aliases.items():
            for alias_info in alias_list:
                alias = alias_info.get('value', '')
                if alias:
                    try:
                        self.cur.execute("""
                            INSERT INTO entity_aliases (entity_type, entity_id, alias, alias_type, language)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (entity_type, entity_id, alias, 'wikidata', lang))
                        if self.cur.rowcount > 0:
                            aliases_added += 1
                    except Exception as e:
                        pass

        return aliases_added

    def process_entity_type(self, entity_type, incremental=False):
        """특정 엔티티 타입의 모든 별칭 가져오기."""
        print(f"\n{'='*60}")
        print(f"Processing: {entity_type.upper()}")
        print(f"{'='*60}")

        entities = self.get_entities_to_process(entity_type, incremental)
        total = len(entities)
        print(f"Total entities to process: {total:,}")

        if total == 0:
            print("  No entities to process.")
            return

        # QID별로 entity_id 매핑
        qid_to_entity = {}
        for entity_id, qid in entities:
            if qid:
                qid_to_entity[qid] = entity_id

        # 배치 처리
        qids = list(qid_to_entity.keys())
        processed = 0

        for i in range(0, len(qids), BATCH_SIZE):
            batch = qids[i:i+BATCH_SIZE]

            # API 요청
            entities_data = self.fetch_wikidata_batch(batch)

            if not entities_data:
                self.stats['errors'] += len(batch)
                continue

            # 각 엔티티 처리
            for qid in batch:
                entity_id = qid_to_entity.get(qid)
                if not entity_id:
                    continue

                entity_data = entities_data.get(qid, {})
                if entity_data and 'missing' not in entity_data:
                    aliases_added = self.save_aliases(entity_type, entity_id, qid, entity_data)
                    self.stats['aliases_added'] += aliases_added
                    self.stats['processed'] += 1
                else:
                    self.stats['skipped'] += 1

            # 커밋 및 진행률
            self.conn.commit()
            processed += len(batch)

            if processed % 500 == 0 or processed == len(qids):
                pct = processed / len(qids) * 100
                print(f"  Progress: {processed:,}/{len(qids):,} ({pct:.1f}%) - aliases added: {self.stats['aliases_added']:,}")

            # Rate limiting (be nice to Wikidata)
            time.sleep(0.1)

        print(f"\nCompleted {entity_type}:")
        print(f"  Processed: {self.stats['processed']:,}")
        print(f"  Aliases added: {self.stats['aliases_added']:,}")
        print(f"  Skipped: {self.stats['skipped']:,}")
        print(f"  Errors: {self.stats['errors']:,}")

    def run(self, types, incremental=False):
        """전체 실행."""
        start_time = datetime.now()
        print(f"Started at: {start_time}")
        print(f"Incremental mode: {incremental}")

        for entity_type in types:
            self.process_entity_type(entity_type, incremental)
            # 타입별 통계 리셋
            self.stats = {k: 0 for k in self.stats}

        end_time = datetime.now()
        duration = end_time - start_time
        print(f"\n{'='*60}")
        print(f"COMPLETED")
        print(f"{'='*60}")
        print(f"Duration: {duration}")

        # 최종 통계
        self.cur.execute("SELECT entity_type, COUNT(*) FROM entity_aliases GROUP BY entity_type ORDER BY entity_type")
        print("\nFinal alias counts:")
        for row in self.cur.fetchall():
            print(f"  {row[0]}: {row[1]:,}")

    def close(self):
        self.conn.close()


def main():
    parser = argparse.ArgumentParser(description='Fetch Wikidata aliases for all entities')
    parser.add_argument('--type', choices=['all', 'persons', 'events', 'locations', 'person', 'event', 'location'],
                        default='all', help='Entity type to process')
    parser.add_argument('--incremental', action='store_true',
                        help='Only fetch for entities without aliases')
    args = parser.parse_args()

    # 타입 매핑
    type_map = {
        'all': ['person', 'event', 'location'],
        'persons': ['person'],
        'events': ['event'],
        'locations': ['location'],
        'person': ['person'],
        'event': ['event'],
        'location': ['location']
    }
    types = type_map[args.type]

    fetcher = WikidataAliasFetcher()
    try:
        fetcher.run(types, args.incremental)
    finally:
        fetcher.close()


if __name__ == '__main__':
    main()
