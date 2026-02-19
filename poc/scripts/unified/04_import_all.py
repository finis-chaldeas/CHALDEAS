"""
Step 4: DB 임포트

추출된 Wikidata + Wikipedia 데이터를 DB에 임포트.

Usage:
    python 04_import_all.py [--limit N] [--test]
"""

import json
import sys
import time
import argparse
import psycopg2
from pathlib import Path
from typing import Dict, List

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from config import (
    DB_CONFIG, WIKIDATA_EXTRACTED, WIKIPEDIA_EXTRACTED,
    BATCH_SIZE, LOG_INTERVAL
)

# ============================================
# DB 임포트
# ============================================

def import_all(limit: int = None, test_mode: bool = False):
    """전체 데이터 DB 임포트"""

    print("=" * 60)
    print("Step 4: DB 임포트")
    print("=" * 60)

    # 파일 체크
    if not WIKIDATA_EXTRACTED.exists():
        print(f"Error: {WIKIDATA_EXTRACTED} not found")
        return

    # DB 연결
    print("Connecting to DB...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    # 통계
    counts = {
        'persons': 0, 'locations': 0, 'territories': 0,
        'groups': 0, 'events': 0, 'properties': 0,
        'sources_wd': 0, 'sources_wiki': 0, 'mentions': 0
    }
    qid_to_id = {}  # QID → (type, db_id)
    start_time = time.time()

    try:
        # ========================================
        # Step 4.1: Wikidata 엔티티 임포트
        # ========================================
        print("\n[4.1] Wikidata 엔티티 임포트...")

        line_count = 0
        with open(WIKIDATA_EXTRACTED, 'r', encoding='utf-8') as f:
            batch = []

            for line in f:
                line_count += 1
                if limit and line_count > limit:
                    break

                try:
                    entity = json.loads(line)
                except:
                    continue

                batch.append(entity)

                if len(batch) >= BATCH_SIZE:
                    process_entity_batch(cur, batch, counts, qid_to_id)
                    batch = []

                    if line_count % LOG_INTERVAL == 0:
                        print(f"  Processed: {line_count:,} | "
                              f"P:{counts['persons']} L:{counts['locations']} "
                              f"T:{counts['territories']} G:{counts['groups']} E:{counts['events']}")

            # 마지막 배치
            if batch:
                process_entity_batch(cur, batch, counts, qid_to_id)

        print(f"  Entities imported: {sum(counts[k] for k in ['persons', 'locations', 'territories', 'groups', 'events']):,}")

        # ========================================
        # Step 4.2: Entity Properties 임포트
        # ========================================
        print("\n[4.2] Entity Properties 임포트...")

        line_count = 0
        with open(WIKIDATA_EXTRACTED, 'r', encoding='utf-8') as f:
            for line in f:
                line_count += 1
                if limit and line_count > limit:
                    break

                try:
                    entity = json.loads(line)
                except:
                    continue

                qid = entity['qid']
                entity_type = entity['type']

                if qid not in qid_to_id:
                    continue

                db_id = qid_to_id[qid][1]

                for prop in entity.get('properties', []):
                    import_property(cur, entity_type, db_id, qid, prop)
                    counts['properties'] += 1

                if line_count % LOG_INTERVAL == 0:
                    print(f"  Properties: {counts['properties']:,}")

        print(f"  Properties imported: {counts['properties']:,}")

        # ========================================
        # Step 4.3: Wikidata Sources 임포트
        # ========================================
        print("\n[4.3] Wikidata Sources 임포트...")

        line_count = 0
        source_ids = {}  # (qid, type) -> source_id

        with open(WIKIDATA_EXTRACTED, 'r', encoding='utf-8') as f:
            for line in f:
                line_count += 1
                if limit and line_count > limit:
                    break

                try:
                    entity = json.loads(line)
                except:
                    continue

                qid = entity['qid']

                # Wikidata source 생성
                cur.execute("""
                    INSERT INTO sources (source_type, title, content_raw, url, wikidata_id)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (wikidata_id) DO UPDATE SET title = EXCLUDED.title
                    RETURNING id
                """, (
                    'wikidata',
                    f"{entity['name']} - Wikidata",
                    entity.get('description') or f"Wikidata entity {qid}",
                    f"https://www.wikidata.org/wiki/{qid}",
                    qid
                ))
                source_id = cur.fetchone()[0]
                source_ids[(qid, 'wikidata')] = source_id
                counts['sources_wd'] += 1

                # Wikidata mention (self-reference)
                if qid in qid_to_id:
                    entity_type, db_id = qid_to_id[qid]
                    cur.execute("""
                        INSERT INTO mentions (source_id, target_type, target_id, evidence_raw)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        source_id, entity_type, db_id,
                        entity.get('description') or f"Wikidata entity {qid}"
                    ))
                    counts['mentions'] += 1

        print(f"  Wikidata sources: {counts['sources_wd']:,}")

        # ========================================
        # Step 4.4: Wikipedia Sources + Mentions 임포트
        # ========================================
        if WIKIPEDIA_EXTRACTED.exists():
            print("\n[4.4] Wikipedia Sources + Mentions 임포트...")

            line_count = 0
            with open(WIKIPEDIA_EXTRACTED, 'r', encoding='utf-8') as f:
                for line in f:
                    line_count += 1
                    if limit and line_count > limit:
                        break

                    try:
                        wiki = json.loads(line)
                    except:
                        continue

                    qid = wiki['qid']

                    # Wikipedia source
                    cur.execute("""
                        INSERT INTO sources (source_type, title, content_raw, word_count, link_count, url)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        'wikipedia',
                        f"{wiki['name']} - Wikipedia",
                        wiki['content_raw'][:50000],  # 50KB limit
                        wiki['word_count'],
                        wiki['link_count'],
                        f"https://en.wikipedia.org/wiki/{wiki['wikipedia_title'].replace(' ', '_')}"
                    ))
                    source_id = cur.fetchone()[0]
                    source_ids[(qid, 'wikipedia')] = source_id
                    counts['sources_wiki'] += 1

                    # Wikipedia mentions (hyperlinks)
                    for mention in wiki.get('mentions', []):
                        target_qid = mention.get('target_qid')
                        if target_qid and target_qid in qid_to_id:
                            target_type, target_id = qid_to_id[target_qid]
                            link_text = mention.get('link_text', '')
                            cur.execute("""
                                INSERT INTO mentions (source_id, target_type, target_id, evidence_raw, link_text)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (
                                source_id, target_type, target_id,
                                link_text,  # evidence_raw = link_text
                                link_text
                            ))
                            counts['mentions'] += 1

                    if line_count % 1000 == 0:
                        print(f"  Wikipedia: {counts['sources_wiki']:,} | Mentions: {counts['mentions']:,}")

            print(f"  Wikipedia sources: {counts['sources_wiki']:,}")
            print(f"  Total mentions: {counts['mentions']:,}")

        # 커밋
        print("\nCommitting...")
        conn.commit()
        print("Done!")

    except Exception as e:
        print(f"\nError: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    # 결과
    elapsed = time.time() - start_time

    print()
    print("=" * 60)
    print("임포트 완료!")
    print("=" * 60)
    for k, v in counts.items():
        print(f"  {k}: {v:,}")
    print(f"Time: {elapsed/60:.1f} min")

def process_entity_batch(cur, batch: List[Dict], counts: dict, qid_to_id: dict):
    """엔티티 배치 처리"""
    for entity in batch:
        qid = entity['qid']
        entity_type = entity['type']

        # 타입별 테이블에 삽입
        if entity_type == 'person':
            cur.execute("""
                INSERT INTO persons (wikidata_id, name, name_ko, birth_year, death_year, description)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (wikidata_id) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
            """, (
                qid, entity['name'], entity.get('name_ko'),
                entity.get('birth_year'), entity.get('death_year'),
                entity.get('description')
            ))
            db_id = cur.fetchone()[0]
            qid_to_id[qid] = ('person', db_id)
            counts['persons'] += 1

        elif entity_type == 'location':
            cur.execute("""
                INSERT INTO locations (wikidata_id, name, name_ko, latitude, longitude)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (wikidata_id) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
            """, (
                qid, entity['name'], entity.get('name_ko'),
                entity.get('latitude'), entity.get('longitude')
            ))
            db_id = cur.fetchone()[0]
            qid_to_id[qid] = ('location', db_id)
            counts['locations'] += 1

        elif entity_type == 'territory':
            cur.execute("""
                INSERT INTO territories (wikidata_id, name, name_ko, territory_type, founded_year, dissolved_year)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (wikidata_id) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
            """, (
                qid, entity['name'], entity.get('name_ko'),
                'country',  # default
                entity.get('founded_year'), entity.get('dissolved_year')
            ))
            db_id = cur.fetchone()[0]
            qid_to_id[qid] = ('territory', db_id)
            counts['territories'] += 1

        elif entity_type == 'group':
            cur.execute("""
                INSERT INTO groups (wikidata_id, name, name_ko, group_type, founded_year, dissolved_year)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (wikidata_id) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
            """, (
                qid, entity['name'], entity.get('name_ko'),
                'organization',  # default
                entity.get('founded_year'), entity.get('dissolved_year')
            ))
            db_id = cur.fetchone()[0]
            qid_to_id[qid] = ('group', db_id)
            counts['groups'] += 1

        elif entity_type == 'event':
            # date_start 필수 - 없으면 스킵
            date_start = entity.get('date_start') or entity.get('start_year')
            if not date_start:
                continue  # 날짜 없는 이벤트 스킵

            cur.execute("""
                INSERT INTO events (wikidata_id, title, title_ko, event_type, date_start, date_end, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (wikidata_id) DO UPDATE SET title = EXCLUDED.title
                RETURNING id
            """, (
                qid, entity['name'], entity.get('name_ko'),
                'historical_event',
                date_start, entity.get('date_end') or entity.get('end_year'),
                entity.get('description')
            ))
            db_id = cur.fetchone()[0]
            qid_to_id[qid] = ('event', db_id)
            counts['events'] += 1

def import_property(cur, entity_type: str, entity_id: int, qid: str, prop: dict):
    """속성 임포트"""
    cur.execute("""
        INSERT INTO entity_properties
        (entity_type, entity_id, property, property_name, value_type,
         value_qid, value_string, value_year, value_quantity, value_lat, value_lon,
         qualifier_start_year, qualifier_end_year, wikidata_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        entity_type, entity_id,
        prop.get('property'), prop.get('property_name'),
        prop.get('value_type'),
        prop.get('value_qid'),
        prop.get('value_string'),
        prop.get('value_year'),
        prop.get('value_quantity'),
        prop.get('value_lat'),
        prop.get('value_lon'),
        prop.get('qualifier_start'),
        prop.get('qualifier_end'),
        qid
    ))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', '-l', type=int, help='Limit lines')
    parser.add_argument('--test', action='store_true', help='Test mode')
    args = parser.parse_args()

    import_all(limit=args.limit, test_mode=args.test)
