"""
Step 4: DB 임포트 (최적화 버전)

싱글 패스 + 배치 INSERT로 빠른 임포트.

Usage:
    python 04_import_fast.py [--limit N] [--skip-props] [--skip-wiki]
"""

import json
import sys
import time
import argparse
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path
from typing import Dict, List, Tuple

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from config import (
    DB_CONFIG, WIKIDATA_EXTRACTED, WIKIPEDIA_EXTRACTED,
    LOG_INTERVAL
)

# 배치 크기
ENTITY_BATCH = 5000
PROPERTY_BATCH = 10000
SOURCE_BATCH = 5000
MENTION_BATCH = 10000
COMMIT_INTERVAL = 100000  # 10만 줄마다 커밋

def flush_print(*args, **kwargs):
    """출력 후 즉시 플러시"""
    print(*args, **kwargs)
    sys.stdout.flush()


def import_fast(limit: int = None, skip_props: bool = False, skip_wiki: bool = False):
    """최적화된 DB 임포트 (싱글 패스)"""

    flush_print("=" * 60)
    flush_print("Step 4: DB 임포트 (Fast)")
    flush_print("=" * 60)

    if not WIKIDATA_EXTRACTED.exists():
        flush_print(f"Error: {WIKIDATA_EXTRACTED} not found")
        return

    flush_print(f"Input: {WIKIDATA_EXTRACTED}")
    flush_print(f"Skip properties: {skip_props}")
    flush_print(f"Skip Wikipedia: {skip_wiki}")

    # DB 연결
    flush_print("\nConnecting to DB...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    # 통계
    counts = {
        'persons': 0, 'locations': 0, 'territories': 0,
        'groups': 0, 'events': 0, 'properties': 0,
        'sources_wd': 0, 'sources_wiki': 0, 'mentions': 0,
        'skipped': 0
    }
    qid_to_id = {}  # QID → (type, db_id)
    start_time = time.time()
    last_commit_time = start_time

    # 배치 버퍼
    entity_batches = {
        'person': [], 'location': [], 'territory': [], 'group': [], 'event': []
    }
    property_batch = []
    source_batch = []
    mention_batch = []

    def flush_entities():
        """엔티티 배치 플러시"""
        for etype, batch in entity_batches.items():
            if not batch:
                continue

            if etype == 'person':
                execute_values(cur, """
                    INSERT INTO persons (wikidata_id, name, name_ko, birth_year, death_year, description)
                    VALUES %s
                    ON CONFLICT (wikidata_id) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id, wikidata_id
                """, batch, template="(%s, %s, %s, %s, %s, %s)")
                for row in cur.fetchall():
                    qid_to_id[row[1]] = ('person', row[0])

            elif etype == 'location':
                execute_values(cur, """
                    INSERT INTO locations (wikidata_id, name, name_ko, latitude, longitude)
                    VALUES %s
                    ON CONFLICT (wikidata_id) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id, wikidata_id
                """, batch, template="(%s, %s, %s, %s, %s)")
                for row in cur.fetchall():
                    qid_to_id[row[1]] = ('location', row[0])

            elif etype == 'territory':
                execute_values(cur, """
                    INSERT INTO territories (wikidata_id, name, name_ko, territory_type, founded_year, dissolved_year)
                    VALUES %s
                    ON CONFLICT (wikidata_id) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id, wikidata_id
                """, batch, template="(%s, %s, %s, %s, %s, %s)")
                for row in cur.fetchall():
                    qid_to_id[row[1]] = ('territory', row[0])

            elif etype == 'group':
                execute_values(cur, """
                    INSERT INTO groups (wikidata_id, name, name_ko, group_type, founded_year, dissolved_year)
                    VALUES %s
                    ON CONFLICT (wikidata_id) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id, wikidata_id
                """, batch, template="(%s, %s, %s, %s, %s, %s)")
                for row in cur.fetchall():
                    qid_to_id[row[1]] = ('group', row[0])

            elif etype == 'event':
                execute_values(cur, """
                    INSERT INTO events (wikidata_id, title, title_ko, event_type, date_start, date_end, description)
                    VALUES %s
                    ON CONFLICT (wikidata_id) DO UPDATE SET title = EXCLUDED.title
                    RETURNING id, wikidata_id
                """, batch, template="(%s, %s, %s, %s, %s, %s, %s)")
                for row in cur.fetchall():
                    qid_to_id[row[1]] = ('event', row[0])

            entity_batches[etype] = []

    def flush_properties():
        """속성 배치 플러시"""
        nonlocal property_batch
        if not property_batch:
            return

        execute_values(cur, """
            INSERT INTO entity_properties
            (entity_type, entity_id, property, property_name, value_type,
             value_qid, value_string, value_year, value_quantity, value_lat, value_lon,
             qualifier_start_year, qualifier_end_year, wikidata_id)
            VALUES %s
        """, property_batch)
        property_batch = []

    def flush_sources():
        """소스 배치 플러시"""
        nonlocal source_batch
        if not source_batch:
            return {}

        execute_values(cur, """
            INSERT INTO sources (source_type, title, content_raw, url, wikidata_id)
            VALUES %s
            ON CONFLICT (wikidata_id) DO UPDATE SET title = EXCLUDED.title
            RETURNING id, wikidata_id
        """, source_batch, template="(%s, %s, %s, %s, %s)")

        # source_id 매핑 반환 (나중에 mention에서 사용)
        result = {row[1]: row[0] for row in cur.fetchall()}
        source_batch = []
        return result

    def flush_mentions():
        """멘션 배치 플러시"""
        nonlocal mention_batch
        if not mention_batch:
            return

        execute_values(cur, """
            INSERT INTO mentions (source_id, target_type, target_id, evidence_raw, link_text)
            VALUES %s
        """, mention_batch)
        mention_batch = []

    try:
        # ========================================
        # Phase 1: Wikidata 임포트 (싱글 패스)
        # ========================================
        flush_print("\n[Phase 1] Wikidata 임포트 (싱글 패스)...")

        line_count = 0
        pending_sources = []  # (qid, name, description) for later source creation

        with open(WIKIDATA_EXTRACTED, 'r', encoding='utf-8') as f:
            for line in f:
                line_count += 1
                if limit and line_count > limit:
                    break

                try:
                    entity = json.loads(line)
                except:
                    counts['skipped'] += 1
                    continue

                qid = entity['qid']
                etype = entity['type']
                name = entity.get('name', '')
                name_ko = entity.get('name_ko')
                desc = entity.get('description')

                # 엔티티 배치에 추가
                if etype == 'person':
                    entity_batches['person'].append((
                        qid, name, name_ko,
                        entity.get('birth_year'), entity.get('death_year'), desc
                    ))
                    counts['persons'] += 1

                elif etype == 'location':
                    entity_batches['location'].append((
                        qid, name, name_ko,
                        entity.get('latitude'), entity.get('longitude')
                    ))
                    counts['locations'] += 1

                elif etype == 'territory':
                    entity_batches['territory'].append((
                        qid, name, name_ko, 'country',
                        entity.get('founded_year'), entity.get('dissolved_year')
                    ))
                    counts['territories'] += 1

                elif etype == 'group':
                    entity_batches['group'].append((
                        qid, name, name_ko, 'organization',
                        entity.get('founded_year'), entity.get('dissolved_year')
                    ))
                    counts['groups'] += 1

                elif etype == 'event':
                    date_start = entity.get('date_start') or entity.get('start_year')
                    if date_start:
                        entity_batches['event'].append((
                            qid, name, name_ko, 'historical_event',
                            date_start, entity.get('date_end') or entity.get('end_year'), desc
                        ))
                        counts['events'] += 1
                    else:
                        counts['skipped'] += 1
                        continue

                # Wikidata source 정보 저장 (나중에 배치 처리)
                source_batch.append((
                    'wikidata',
                    f"{name} - Wikidata",
                    desc or f"Wikidata entity {qid}",
                    f"https://www.wikidata.org/wiki/{qid}",
                    qid
                ))
                pending_sources.append((qid, etype, desc))
                counts['sources_wd'] += 1  # 추가 시 카운트

                # 배치 플러시
                total_entities = sum(len(b) for b in entity_batches.values())
                if total_entities >= ENTITY_BATCH:
                    flush_entities()

                if len(source_batch) >= SOURCE_BATCH:
                    source_ids = flush_sources()
                    # 멘션 생성 (self-reference)
                    for pqid, petype, pdesc in pending_sources:
                        if pqid in source_ids and pqid in qid_to_id:
                            target_type, target_id = qid_to_id[pqid]
                            mention_batch.append((
                                source_ids[pqid], target_type, target_id,
                                pdesc or f"Wikidata {pqid}", None
                            ))
                            counts['mentions'] += 1
                    pending_sources = []

                    if len(mention_batch) >= MENTION_BATCH:
                        flush_mentions()

                # 진행 상황 출력 및 중간 커밋
                if line_count % LOG_INTERVAL == 0:
                    elapsed = time.time() - start_time
                    rate = line_count / elapsed if elapsed > 0 else 0
                    flush_print(f"  {line_count:,} lines | "
                          f"P:{counts['persons']:,} L:{counts['locations']:,} "
                          f"T:{counts['territories']:,} G:{counts['groups']:,} E:{counts['events']:,} | "
                          f"{rate:,.0f}/s")

                # 중간 커밋 (10만 줄마다)
                if line_count % COMMIT_INTERVAL == 0:
                    flush_entities()
                    source_ids = flush_sources()
                    if source_ids:
                        for pqid, petype, pdesc in pending_sources:
                            if pqid in source_ids and pqid in qid_to_id:
                                target_type, target_id = qid_to_id[pqid]
                                mention_batch.append((
                                    source_ids[pqid], target_type, target_id,
                                    pdesc or f"Wikidata {pqid}", None
                                ))
                                counts['mentions'] += 1
                        pending_sources = []
                    flush_mentions()
                    conn.commit()
                    flush_print(f"  [Checkpoint] Committed at {line_count:,} lines")

        # 마지막 배치 플러시
        flush_entities()
        source_ids = flush_sources()
        if source_ids:
            for pqid, petype, pdesc in pending_sources:
                if pqid in source_ids and pqid in qid_to_id:
                    target_type, target_id = qid_to_id[pqid]
                    mention_batch.append((
                        source_ids[pqid], target_type, target_id,
                        pdesc or f"Wikidata {pqid}", None
                    ))
                    counts['mentions'] += 1
        flush_mentions()
        conn.commit()

        flush_print(f"\n  Wikidata import complete!")
        flush_print(f"  Entities: {counts['persons'] + counts['locations'] + counts['territories'] + counts['groups'] + counts['events']:,}")
        flush_print(f"  Sources: {counts['sources_wd']:,}")

        # ========================================
        # Phase 2: Wikipedia 임포트
        # ========================================
        if not skip_wiki and WIKIPEDIA_EXTRACTED.exists():
            flush_print("\n[Phase 2] Wikipedia 임포트...")

            line_count = 0
            wiki_source_batch = []
            wiki_pending = []  # (qid, mentions_list)

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
                    wiki_source_batch.append((
                        'wikipedia',
                        f"{wiki['name']} - Wikipedia",
                        wiki.get('content_raw', '')[:50000],
                        wiki.get('word_count', 0),
                        wiki.get('link_count', 0),
                        f"https://en.wikipedia.org/wiki/{wiki.get('wikipedia_title', '').replace(' ', '_')}"
                    ))
                    wiki_pending.append((qid, wiki.get('mentions', [])))
                    counts['sources_wiki'] += 1

                    # 배치 플러시
                    if len(wiki_source_batch) >= SOURCE_BATCH:
                        execute_values(cur, """
                            INSERT INTO sources (source_type, title, content_raw, word_count, link_count, url)
                            VALUES %s
                            RETURNING id
                        """, wiki_source_batch, template="(%s, %s, %s, %s, %s, %s)")

                        source_ids_list = [r[0] for r in cur.fetchall()]

                        # 멘션 생성
                        for i, (wqid, wmentions) in enumerate(wiki_pending):
                            if i < len(source_ids_list):
                                src_id = source_ids_list[i]
                                for m in wmentions:
                                    target_qid = m.get('target_qid')
                                    if target_qid and target_qid in qid_to_id:
                                        target_type, target_id = qid_to_id[target_qid]
                                        link_text = m.get('link_text', '')
                                        mention_batch.append((
                                            src_id, target_type, target_id, link_text, link_text
                                        ))
                                        counts['mentions'] += 1

                        wiki_source_batch = []
                        wiki_pending = []

                        if len(mention_batch) >= MENTION_BATCH:
                            flush_mentions()

                    if line_count % 10000 == 0:
                        flush_print(f"  Wikipedia: {counts['sources_wiki']:,} | Mentions: {counts['mentions']:,}")

                    # 중간 커밋
                    if line_count % COMMIT_INTERVAL == 0:
                        if wiki_source_batch:
                            execute_values(cur, """
                                INSERT INTO sources (source_type, title, content_raw, word_count, link_count, url)
                                VALUES %s
                                RETURNING id
                            """, wiki_source_batch, template="(%s, %s, %s, %s, %s, %s)")
                            source_ids_list = [r[0] for r in cur.fetchall()]
                            for i, (wqid, wmentions) in enumerate(wiki_pending):
                                if i < len(source_ids_list):
                                    src_id = source_ids_list[i]
                                    for m in wmentions:
                                        target_qid = m.get('target_qid')
                                        if target_qid and target_qid in qid_to_id:
                                            target_type, target_id = qid_to_id[target_qid]
                                            link_text = m.get('link_text', '')
                                            mention_batch.append((
                                                src_id, target_type, target_id, link_text, link_text
                                            ))
                                            counts['mentions'] += 1
                            wiki_source_batch = []
                            wiki_pending = []
                        flush_mentions()
                        conn.commit()
                        flush_print(f"  [Checkpoint] Committed at {line_count:,} Wikipedia lines")

            # 마지막 배치
            if wiki_source_batch:
                execute_values(cur, """
                    INSERT INTO sources (source_type, title, content_raw, word_count, link_count, url)
                    VALUES %s
                    RETURNING id
                """, wiki_source_batch, template="(%s, %s, %s, %s, %s, %s)")
                source_ids_list = [r[0] for r in cur.fetchall()]
                for i, (wqid, wmentions) in enumerate(wiki_pending):
                    if i < len(source_ids_list):
                        src_id = source_ids_list[i]
                        for m in wmentions:
                            target_qid = m.get('target_qid')
                            if target_qid and target_qid in qid_to_id:
                                target_type, target_id = qid_to_id[target_qid]
                                link_text = m.get('link_text', '')
                                mention_batch.append((
                                    src_id, target_type, target_id, link_text, link_text
                                ))
                                counts['mentions'] += 1
            flush_mentions()

            flush_print(f"\n  Wikipedia import complete!")
            flush_print(f"  Sources: {counts['sources_wiki']:,}")
            flush_print(f"  Mentions: {counts['mentions']:,}")

        # 최종 커밋
        flush_print("\nFinal commit...")
        conn.commit()
        flush_print("Done!")

    except Exception as e:
        flush_print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    # 결과
    elapsed = time.time() - start_time

    flush_print()
    flush_print("=" * 60)
    flush_print("임포트 완료!")
    flush_print("=" * 60)
    for k, v in counts.items():
        if v > 0:
            flush_print(f"  {k}: {v:,}")
    flush_print(f"Time: {elapsed/60:.1f} min ({elapsed/3600:.2f} hr)")
    flush_print(f"Rate: {line_count/elapsed:,.0f} lines/sec")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', '-l', type=int, help='Limit lines')
    parser.add_argument('--skip-props', action='store_true', help='Skip properties (faster)')
    parser.add_argument('--skip-wiki', action='store_true', help='Skip Wikipedia import')
    args = parser.parse_args()

    import_fast(limit=args.limit, skip_props=args.skip_props, skip_wiki=args.skip_wiki)
