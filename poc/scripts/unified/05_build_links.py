"""
Step 5: entity_properties의 QID → links 테이블 변환

entity_properties에 저장된 QID 참조를 실제 DB ID로 변환하여
links 테이블에 엔티티 간 직접 연결 생성.

Usage:
    python 05_build_links.py [--test]
"""

import sys
import time
import argparse
import psycopg2

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from config import DB_CONFIG

# 관계 속성 정의
RELATIONSHIP_PROPERTIES = {
    # 가족 관계
    'father': ('person', 'person', 'family'),
    'mother': ('person', 'person', 'family'),
    'spouse': ('person', 'person', 'family'),
    'child': ('person', 'person', 'family'),
    'sibling': ('person', 'person', 'family'),

    # 소속/직위
    'employer': ('person', 'group', 'membership'),
    'member_of': ('person', 'group', 'membership'),
    'educated_at': ('person', 'group', 'membership'),
    'position_held': ('person', 'group', 'position'),

    # 장소 관계
    'birthplace': ('person', 'location', 'birth'),
    'deathplace': ('person', 'location', 'death'),
    'residence': ('person', 'location', 'residence'),
    'work_location': ('person', 'location', 'work'),
    'burial_place': ('person', 'location', 'burial'),

    # 국가/영역
    'country': ('person', 'territory', 'citizenship'),
    'country_of_citizenship': ('person', 'territory', 'citizenship'),

    # 이벤트 참여
    'participant_in': ('person', 'event', 'participation'),
    'conflict': ('person', 'event', 'participation'),
    'significant_event': ('person', 'event', 'participation'),

    # 장소 계층
    'located_in': ('location', 'territory', 'contains'),
    'capital': ('territory', 'location', 'capital'),

    # 이벤트-장소
    'location': ('event', 'location', 'location'),
}

# 엔티티 타입 → 테이블 매핑
TYPE_TO_TABLE = {
    'person': 'persons',
    'location': 'locations',
    'territory': 'territories',
    'group': 'groups',
    'event': 'events',
}


def build_qid_cache(cur) -> dict:
    """모든 엔티티의 QID → (type, id) 캐시 생성"""
    print("  Building QID cache...")
    cache = {}

    for entity_type, table in TYPE_TO_TABLE.items():
        cur.execute(f"SELECT id, wikidata_id FROM {table} WHERE wikidata_id IS NOT NULL")
        for row in cur.fetchall():
            cache[row[1]] = (entity_type, row[0])

    print(f"    Cached {len(cache):,} QIDs")
    return cache


def build_links(test_mode: bool = False):
    """entity_properties → links 변환"""

    print("=" * 60)
    print("Step 5: QID → Links 변환")
    print("=" * 60)

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    # QID 캐시 생성
    qid_cache = build_qid_cache(cur)

    # links 테이블 (기존 스키마 사용)
    # from_type, from_id, to_type, to_id, category
    print("\n  Using existing links table schema...")

    # 기존 링크 삭제 (재실행 시)
    if not test_mode:
        cur.execute("DELETE FROM links")
        print("    Cleared existing links")

    # 관계 속성별 처리
    print("\n  Processing relationship properties...")

    stats = {
        'processed': 0,
        'created': 0,
        'skipped_no_source': 0,
        'skipped_no_target': 0,
        'skipped_type_mismatch': 0,
    }

    for prop_name, (expected_source, expected_target, link_category) in RELATIONSHIP_PROPERTIES.items():
        cur.execute("""
            SELECT ep.entity_type, ep.entity_id, ep.value_qid,
                   ep.qualifier_start_year, ep.qualifier_end_year, ep.property
            FROM entity_properties ep
            WHERE ep.property_name = %s AND ep.value_qid IS NOT NULL
        """, (prop_name,))

        rows = cur.fetchall()
        prop_created = 0

        for row in rows:
            source_type, source_id, target_qid, start_year, end_year, prop_code = row
            stats['processed'] += 1

            # 소스 타입 확인
            if source_type != expected_source:
                stats['skipped_type_mismatch'] += 1
                continue

            # 타겟 QID → DB ID
            if target_qid not in qid_cache:
                stats['skipped_no_target'] += 1
                continue

            target_type, target_id = qid_cache[target_qid]

            # 타겟 타입 확인
            if target_type != expected_target:
                # 유연하게 처리 (location/territory 혼용 등)
                if not (expected_target in ['location', 'territory'] and
                        target_type in ['location', 'territory']):
                    stats['skipped_type_mismatch'] += 1
                    continue

            # 링크 생성 (기존 스키마: from_type, from_id, to_type, to_id, category)
            try:
                cur.execute("""
                    INSERT INTO links (from_type, from_id, to_type, to_id, category,
                                      date_start, date_end, evidence)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    source_type, source_id, target_type, target_id,
                    f"{link_category}:{prop_name}",
                    start_year, end_year,
                    f"Wikidata {prop_code}"
                ))
                if cur.rowcount > 0:
                    stats['created'] += 1
                    prop_created += 1
            except Exception as e:
                print(f"    Error: {e}")

        if prop_created > 0:
            print(f"    {prop_name}: {prop_created:,} links")

    # 커밋
    conn.commit()

    # 결과 확인
    print("\n  Verifying links...")

    print("\n" + "=" * 60)
    print("완료!")
    print("=" * 60)
    print(f"Processed: {stats['processed']:,}")
    print(f"Created: {stats['created']:,}")
    print(f"Skipped (no target in DB): {stats['skipped_no_target']:,}")
    print(f"Skipped (type mismatch): {stats['skipped_type_mismatch']:,}")

    print("\nLinks by category:")
    cur.execute("SELECT category, COUNT(*) FROM links GROUP BY category ORDER BY COUNT(*) DESC LIMIT 10")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:,}")

    # 샘플 출력
    print("\nSample links:")
    cur.execute("""
        SELECT p1.name, l.category,
               CASE l.to_type
                   WHEN 'person' THEN (SELECT name FROM persons WHERE id = l.to_id)
                   WHEN 'location' THEN (SELECT name FROM locations WHERE id = l.to_id)
                   WHEN 'territory' THEN (SELECT name FROM territories WHERE id = l.to_id)
                   WHEN 'group' THEN (SELECT name FROM groups WHERE id = l.to_id)
                   WHEN 'event' THEN (SELECT title FROM events WHERE id = l.to_id)
               END as target_name
        FROM links l
        JOIN persons p1 ON l.from_type = 'person' AND l.from_id = p1.id
        WHERE l.category LIKE 'family%'
        LIMIT 5
    """)
    for row in cur.fetchall():
        print(f"  {row[0]} --[{row[1]}]--> {row[2]}")

    cur.close()
    conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Test mode (no delete)')
    args = parser.parse_args()

    build_links(test_mode=args.test)
