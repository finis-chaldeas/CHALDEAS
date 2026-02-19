"""
Convert event_sitelinks.jsonl → event_coords.json
(Bridges the sitelinks scan output to match_event_locations.py --match format)
"""
import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}

SITELINKS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'compact_export', 'event_sitelinks.jsonl')
COORDS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'wikidata', 'event_coords.json')


def main():
    print("=== Sitelinks → Coords 변환 ===")

    # DB에서 location QID → location_id 맵 로드
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT id, wikidata_id FROM locations WHERE wikidata_id IS NOT NULL")
    loc_qid_map = {r['wikidata_id']: r['id'] for r in cur.fetchall()}
    print(f"  DB 로케이션 (QID 있는): {len(loc_qid_map)}")

    # 이미 primary_location_id가 있는 이벤트 제외
    cur.execute("SELECT id FROM events WHERE primary_location_id IS NOT NULL")
    already_linked = set(r['id'] for r in cur.fetchall())
    print(f"  이미 위치 연결된 이벤트: {len(already_linked)}")

    conn.close()

    # Sitelinks JSONL 읽기
    coords = {}
    source_breakdown = {}
    unresolved_p276 = {}
    skipped_already_linked = 0
    no_location_data = 0

    with open(SITELINKS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line.strip())
            qid = rec['qid']
            event_id = rec['event_id']

            # 이미 위치가 있는 이벤트 건너뛰기
            if event_id in already_linked:
                skipped_already_linked += 1
                continue

            # 1) P625 직접 좌표
            if rec.get('coordinate'):
                lat = rec['coordinate']['latitude']
                lng = rec['coordinate']['longitude']
                coords[qid] = {
                    'lat': lat,
                    'lng': lng,
                    'source': 'P625',
                    'event_id': event_id
                }
                source_breakdown['P625'] = source_breakdown.get('P625', 0) + 1
                continue

            # 2) location_qids → DB 매칭
            loc_qids = rec.get('location_qids', [])
            matched = False
            for loc_qid in loc_qids:
                if loc_qid in loc_qid_map:
                    coords[qid] = {
                        'lat': 0,
                        'lng': 0,
                        'source': 'P276_direct',
                        'event_id': event_id,
                        'location_id': loc_qid_map[loc_qid]
                    }
                    source_breakdown['P276_direct'] = source_breakdown.get('P276_direct', 0) + 1
                    matched = True
                    break

            if matched:
                continue

            # 3) location_qids가 있지만 DB에 없음 → unresolved
            if loc_qids:
                for loc_qid in loc_qids:
                    if loc_qid not in unresolved_p276:
                        unresolved_p276[loc_qid] = []
                    unresolved_p276[loc_qid].append(qid)
                source_breakdown['unresolved_p276'] = source_breakdown.get('unresolved_p276', 0) + 1
                continue

            # 4) 아무 위치 데이터 없음
            no_location_data += 1

    print(f"\n  결과:")
    print(f"  좌표 수집: {len(coords)}")
    print(f"  소스별: {source_breakdown}")
    print(f"  이미 연결됨 (건너뜀): {skipped_already_linked}")
    print(f"  미해결 P276: {sum(len(v) for v in unresolved_p276.values())} events ({len(unresolved_p276)} locations)")
    print(f"  위치 데이터 없음: {no_location_data}")

    # 저장
    os.makedirs(os.path.dirname(COORDS_FILE), exist_ok=True)
    result = {
        'timestamp': datetime.now().isoformat(),
        'total_coords': len(coords),
        'coords': coords,
        'unresolved_p276': unresolved_p276,
        'source_breakdown': source_breakdown
    }

    with open(COORDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n  저장: {COORDS_FILE}")
    print(f"  총 {len(coords)}개 좌표 (--match 실행 가능)")


if __name__ == '__main__':
    main()
