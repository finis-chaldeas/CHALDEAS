"""
Step 5: 링크 생성

Wikidata properties에서 엔티티 간 관계 추출.

Phase 1: 핵심 관계 (빠름)
Phase 2: 전체 Properties (느림)

Usage:
    python 05_create_links.py [--phase 1|2|all] [--limit N]
"""

import json
import sys
import time
import argparse
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path
from collections import defaultdict

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from config import DB_CONFIG, WIKIDATA_EXTRACTED, LOG_INTERVAL

# ============================================
# 핵심 관계 정의
# ============================================

# 가족 관계 (person → person)
FAMILY_PROPS = {
    'P22': 'father',
    'P25': 'mother',
    'P26': 'spouse',
    'P40': 'child',
    'P3373': 'sibling',
    'P451': 'partner',
    'P1038': 'relative',
}

# 위치 관계 (person → location)
LOCATION_PROPS = {
    'P19': 'birthplace',
    'P20': 'deathplace',
    'P119': 'burial_place',
    'P551': 'residence',
    'P937': 'work_location',
}

# 이벤트 관계 (person → event)
EVENT_PROPS = {
    'P607': 'conflict',
    'P1344': 'participant_in',
    'P793': 'significant_event',
}

# 그룹 관계 (person → group/organization)
GROUP_PROPS = {
    'P463': 'member_of',
    'P102': 'political_party',
    'P108': 'employer',
    'P69': 'educated_at',
}

# 배치 크기
LINK_BATCH = 10000
COMMIT_INTERVAL = 500000

# PostgreSQL integer 범위
INT_MIN = -2147483648
INT_MAX = 2147483647


def clamp_int(val):
    """정수 값을 PostgreSQL integer 범위로 제한"""
    if val is None:
        return None
    try:
        val = int(val)
        if val < INT_MIN:
            return INT_MIN
        if val > INT_MAX:
            return INT_MAX
        return val
    except (ValueError, TypeError):
        return None


def flush_print(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()


def load_qid_mapping(conn) -> dict:
    """DB에서 QID → (type, id) 매핑 로드"""
    flush_print("Loading QID mapping from DB...")
    start = time.time()

    qid_map = {}
    cur = conn.cursor()

    tables = [
        ('persons', 'person'),
        ('locations', 'location'),
        ('events', 'event'),
        ('territories', 'territory'),
        ('groups', 'group'),
    ]

    for table, etype in tables:
        cur.execute(f"SELECT wikidata_id, id FROM {table} WHERE wikidata_id IS NOT NULL")
        count = 0
        for row in cur.fetchall():
            qid_map[row[0]] = (etype, row[1])
            count += 1
        flush_print(f"  {table}: {count:,}")

    cur.close()
    flush_print(f"  Total: {len(qid_map):,} mappings in {time.time()-start:.1f}s")
    return qid_map


def extract_core_relations(limit: int = None):
    """Phase 1: 핵심 관계 추출"""

    flush_print("=" * 60)
    flush_print("Phase 1: 핵심 관계 추출")
    flush_print("=" * 60)

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    # QID 매핑 로드
    qid_map = load_qid_mapping(conn)

    # 통계
    counts = {
        'family': 0,
        'location': 0,
        'event': 0,
        'group': 0,
        'skipped_no_target': 0,
        'skipped_no_source': 0,
    }

    # 배치 버퍼
    link_batch = []
    event_participant_batch = []
    group_member_batch = []

    start_time = time.time()
    line_count = 0

    def flush_links():
        nonlocal link_batch
        if not link_batch:
            return
        execute_values(cur, """
            INSERT INTO links (from_type, from_id, to_type, to_id, category)
            VALUES %s
            ON CONFLICT DO NOTHING
        """, link_batch)
        link_batch = []

    def flush_event_participants():
        nonlocal event_participant_batch
        if not event_participant_batch:
            return
        execute_values(cur, """
            INSERT INTO event_participants (event_id, participant_type, participant_id, role)
            VALUES %s
            ON CONFLICT DO NOTHING
        """, event_participant_batch)
        event_participant_batch = []

    def flush_group_members():
        nonlocal group_member_batch
        if not group_member_batch:
            return
        execute_values(cur, """
            INSERT INTO group_members (group_id, person_id, role)
            VALUES %s
            ON CONFLICT DO NOTHING
        """, group_member_batch)
        group_member_batch = []

    flush_print(f"\nProcessing {WIKIDATA_EXTRACTED}...")

    try:
        with open(WIKIDATA_EXTRACTED, 'r', encoding='utf-8') as f:
            for line in f:
                line_count += 1
                if limit and line_count > limit:
                    break

                try:
                    entity = json.loads(line)
                except:
                    continue

                qid = entity.get('qid')
                etype = entity.get('type')

                if qid not in qid_map:
                    counts['skipped_no_source'] += 1
                    continue

                source_type, source_id = qid_map[qid]

                # Properties 처리
                for prop in entity.get('properties', []):
                    prop_id = prop.get('property')
                    value_qid = prop.get('value_qid')

                    if not value_qid or value_qid not in qid_map:
                        counts['skipped_no_target'] += 1
                        continue

                    target_type, target_id = qid_map[value_qid]

                    # 가족 관계 (person → person)
                    if prop_id in FAMILY_PROPS and source_type == 'person' and target_type == 'person':
                        category = FAMILY_PROPS[prop_id]
                        link_batch.append((source_type, source_id, target_type, target_id, category))
                        counts['family'] += 1

                    # 위치 관계 (person → location)
                    elif prop_id in LOCATION_PROPS and source_type == 'person' and target_type == 'location':
                        category = LOCATION_PROPS[prop_id]
                        link_batch.append((source_type, source_id, target_type, target_id, category))
                        counts['location'] += 1

                    # 이벤트 관계 (person → event)
                    elif prop_id in EVENT_PROPS and source_type == 'person' and target_type == 'event':
                        category = EVENT_PROPS[prop_id]
                        event_participant_batch.append((target_id, source_type, source_id, category))
                        counts['event'] += 1

                    # 그룹 관계 (person → group)
                    elif prop_id in GROUP_PROPS and source_type == 'person' and target_type == 'group':
                        category = GROUP_PROPS[prop_id]
                        group_member_batch.append((target_id, source_id, category))
                        counts['group'] += 1

                # 배치 플러시
                if len(link_batch) >= LINK_BATCH:
                    flush_links()
                if len(event_participant_batch) >= LINK_BATCH:
                    flush_event_participants()
                if len(group_member_batch) >= LINK_BATCH:
                    flush_group_members()

                # 진행 상황
                if line_count % LOG_INTERVAL == 0:
                    elapsed = time.time() - start_time
                    rate = line_count / elapsed if elapsed > 0 else 0
                    flush_print(f"  {line_count:,} lines | "
                          f"Family:{counts['family']:,} Loc:{counts['location']:,} "
                          f"Event:{counts['event']:,} Group:{counts['group']:,} | "
                          f"{rate:,.0f}/s")

                # 중간 커밋
                if line_count % COMMIT_INTERVAL == 0:
                    flush_links()
                    flush_event_participants()
                    flush_group_members()
                    conn.commit()
                    flush_print(f"  [Checkpoint] Committed at {line_count:,}")

        # 마지막 배치 플러시
        flush_links()
        flush_event_participants()
        flush_group_members()
        conn.commit()

        flush_print("\nPhase 1 Complete!")

    except Exception as e:
        flush_print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    elapsed = time.time() - start_time
    total_links = counts['family'] + counts['location'] + counts['event'] + counts['group']

    flush_print()
    flush_print("=" * 60)
    flush_print("Phase 1 결과")
    flush_print("=" * 60)
    flush_print(f"  Family links: {counts['family']:,}")
    flush_print(f"  Location links: {counts['location']:,}")
    flush_print(f"  Event participants: {counts['event']:,}")
    flush_print(f"  Group members: {counts['group']:,}")
    flush_print(f"  Total: {total_links:,}")
    flush_print(f"  Skipped (no target): {counts['skipped_no_target']:,}")
    flush_print(f"  Time: {elapsed/60:.1f} min")

    return counts


def import_all_properties(limit: int = None, resume_from: int = 0):
    """Phase 2: 전체 Properties 임포트"""

    flush_print("=" * 60)
    flush_print("Phase 2: 전체 Properties 임포트")
    flush_print("=" * 60)

    if resume_from > 0:
        flush_print(f"Resuming from line {resume_from:,}")

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    # QID 매핑 로드
    qid_map = load_qid_mapping(conn)

    counts = {'properties': 0, 'skipped': 0}
    property_batch = []
    start_time = time.time()
    line_count = 0

    def flush_properties():
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

    flush_print(f"\nProcessing {WIKIDATA_EXTRACTED}...")

    try:
        with open(WIKIDATA_EXTRACTED, 'r', encoding='utf-8') as f:
            for line in f:
                line_count += 1

                # Resume: 이미 처리된 줄 스킵
                if line_count <= resume_from:
                    if line_count % 1000000 == 0:
                        flush_print(f"  Skipping... {line_count:,}")
                    continue

                if limit and line_count > limit:
                    break

                try:
                    entity = json.loads(line)
                except:
                    continue

                qid = entity.get('qid')
                etype = entity.get('type')

                if qid not in qid_map:
                    counts['skipped'] += 1
                    continue

                source_type, source_id = qid_map[qid]

                for prop in entity.get('properties', []):
                    property_batch.append((
                        source_type, source_id,
                        prop.get('property'), prop.get('property_name'),
                        prop.get('value_type'),
                        prop.get('value_qid'),
                        prop.get('value_string'),
                        clamp_int(prop.get('value_year')),
                        prop.get('value_quantity'),  # numeric, no clamp needed
                        prop.get('value_lat'),
                        prop.get('value_lon'),
                        clamp_int(prop.get('qualifier_start')),
                        clamp_int(prop.get('qualifier_end')),
                        qid
                    ))
                    counts['properties'] += 1

                if len(property_batch) >= LINK_BATCH:
                    flush_properties()

                if line_count % LOG_INTERVAL == 0:
                    elapsed = time.time() - start_time
                    rate = line_count / elapsed if elapsed > 0 else 0
                    flush_print(f"  {line_count:,} lines | Props:{counts['properties']:,} | {rate:,.0f}/s")

                if line_count % COMMIT_INTERVAL == 0:
                    flush_properties()
                    conn.commit()
                    flush_print(f"  [Checkpoint] Committed at {line_count:,}")

        flush_properties()
        conn.commit()

        flush_print("\nPhase 2 Complete!")

    except Exception as e:
        flush_print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    elapsed = time.time() - start_time

    flush_print()
    flush_print("=" * 60)
    flush_print("Phase 2 결과")
    flush_print("=" * 60)
    flush_print(f"  Properties: {counts['properties']:,}")
    flush_print(f"  Skipped: {counts['skipped']:,}")
    flush_print(f"  Time: {elapsed/60:.1f} min ({elapsed/3600:.2f} hr)")

    return counts


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['1', '2', 'all'], default='all', help='Phase to run')
    parser.add_argument('--limit', '-l', type=int, help='Limit lines')
    parser.add_argument('--resume', '-r', type=int, default=0, help='Resume from line N (Phase 2 only)')
    args = parser.parse_args()

    if args.phase in ['1', 'all']:
        extract_core_relations(limit=args.limit)

    if args.phase in ['2', 'all']:
        import_all_properties(limit=args.limit, resume_from=args.resume)

    flush_print("\n" + "=" * 60)
    flush_print("모든 작업 완료!")
    flush_print("=" * 60)
