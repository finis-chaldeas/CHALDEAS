"""
새 임포터 테스트 스크립트

기존 임포터 vs 새 임포터 비교:
- 기존: location_qid 무시, primary_location_id = NULL
- 새것: location 먼저 생성 후 연결
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from importers import EventImporter, LocationImporter


def test_location_importer():
    """LocationImporter 테스트"""
    print("=== LocationImporter Test ===\n")

    importer = LocationImporter()

    # 테스트 QID들
    test_qids = [
        'Q737593',   # Battle (town in England) - 전투 위치
        'Q127091',   # Pearl Harbor
        'Q90',       # Paris
        'Q84',       # London
    ]

    for qid in test_qids:
        print(f"\nFetching {qid}...")
        entity = importer.fetch_from_wikidata(qid)

        if entity:
            print(f"  Label: {entity['label']}")
            print(f"  Type: {entity['type']}")
            print(f"  Coords: ({entity.get('latitude')}, {entity.get('longitude')})")
            print(f"  Country: {entity.get('country')}")
        else:
            print(f"  Failed to fetch")

    importer.close()


def test_event_importer():
    """EventImporter 테스트 - 위치 연결 확인"""
    print("\n=== EventImporter Test ===\n")

    importer = EventImporter()

    # 테스트 QID들 (실제 역사 이벤트)
    test_qids = [
        'Q83224',    # Battle of Hastings
        'Q52418',    # Attack on Pearl Harbor
        'Q131969',   # Battle of Thermopylae
    ]

    for qid in test_qids:
        print(f"\nFetching {qid}...")
        entity = importer.fetch_from_wikidata(qid)

        if entity:
            print(f"  Title: {entity['label']}")
            print(f"  Date: {entity.get('start_year')}")
            print(f"  Location QID: {entity.get('location_qid')}")
            print(f"  Location Label: {entity.get('location_label')}")
            print(f"  Part Of: {entity.get('part_of_label')}")
            print(f"  Valid: {importer.validate(entity)}")
        else:
            print(f"  Failed to fetch")

    importer.close()


def test_full_import():
    """전체 임포트 테스트 (실제 DB 저장)"""
    print("\n=== Full Import Test (DB) ===\n")

    importer = EventImporter()

    # 테스트: Battle of Hastings
    qid = 'Q83224'
    print(f"Importing {qid} (Battle of Hastings)...")

    event_id = importer.get_or_create(qid)

    if event_id:
        print(f"  Event ID: {event_id}")

        # 위치 연결 확인
        cur = importer.conn.cursor()
        cur.execute("""
            SELECT e.title, e.primary_location_id, l.name, l.wikidata_id
            FROM events e
            LEFT JOIN locations l ON e.primary_location_id = l.id
            WHERE e.id = %s
        """, (event_id,))
        result = cur.fetchone()

        if result:
            title, loc_id, loc_name, loc_qid = result
            print(f"  Title: {title}")
            print(f"  Location ID: {loc_id}")
            print(f"  Location Name: {loc_name}")
            print(f"  Location QID: {loc_qid}")

            if loc_id:
                print(f"\n  ✓ 위치 연결 성공!")
            else:
                print(f"\n  ✗ 위치 연결 실패!")

        importer.conn.commit()
    else:
        print(f"  Failed to import")

    importer.print_stats()
    importer.close()


def compare_old_vs_new():
    """기존 데이터 vs 새 임포터 비교"""
    print("\n=== Old vs New Comparison ===\n")

    import psycopg2

    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        dbname='chaldeas',
        user='chaldeas',
        password='chaldeas_dev'
    )
    cur = conn.cursor()

    # 기존 데이터: 위치 연결률
    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(primary_location_id) as with_location,
            ROUND(100.0 * COUNT(primary_location_id) / COUNT(*), 1) as pct
        FROM events
        WHERE wikidata_id IS NOT NULL
    """)
    total, with_loc, pct = cur.fetchone()

    print(f"현재 DB 상태:")
    print(f"  총 이벤트: {total}")
    print(f"  위치 연결: {with_loc} ({pct}%)")
    print(f"  위치 없음: {total - with_loc} ({100-float(pct):.1f}%)")

    conn.close()


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == 'location':
            test_location_importer()
        elif sys.argv[1] == 'event':
            test_event_importer()
        elif sys.argv[1] == 'full':
            test_full_import()
        elif sys.argv[1] == 'compare':
            compare_old_vs_new()
    else:
        print("Usage: python test_new_importer.py [location|event|full|compare]")
        print()
        compare_old_vs_new()
