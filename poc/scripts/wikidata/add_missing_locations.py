"""
Case A 해결: P276 미해결 위치 QID → Wikidata API 조회 → DB 추가 → 재매칭

1. 미해결 location QID 5,298개 수집
2. Wikidata API wbgetentities (50개/배치) → 좌표, 이름 추출
3. locations 테이블에 INSERT
4. event_coords.json 재생성
5. --match 재실행
"""
import os
import sys
import json
import time
import requests
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
CACHE_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'wikidata', 'missing_locations_cache.json')
WIKIDATA_API = 'https://www.wikidata.org/w/api.php'


def get_unresolved_location_qids():
    """미해결 P276 위치 QID 수집."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 현재 DB에 있는 location QIDs
    cur.execute("SELECT wikidata_id FROM locations WHERE wikidata_id IS NOT NULL")
    db_loc_qids = set(r['wikidata_id'] for r in cur.fetchall())

    # 위치 없는 이벤트들
    cur.execute("SELECT id FROM events WHERE primary_location_id IS NULL")
    unlinked_ids = set(r['id'] for r in cur.fetchall())

    conn.close()

    # Sitelinks에서 미해결 location QIDs 수집
    qid_to_events = {}  # location_qid → [event_ids]

    with open(SITELINKS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            if rec['event_id'] not in unlinked_ids:
                continue
            if rec.get('coordinate'):
                continue  # 좌표 있는 건 이미 매칭됨 (Case C 제외)

            for loc_qid in rec.get('location_qids', []):
                if loc_qid not in db_loc_qids:
                    if loc_qid not in qid_to_events:
                        qid_to_events[loc_qid] = []
                    qid_to_events[loc_qid].append(rec['event_id'])

    return qid_to_events


def fetch_wikidata_batch(qids: list) -> dict:
    """Wikidata API에서 엔티티 배치 조회 (최대 50개)."""
    params = {
        'action': 'wbgetentities',
        'ids': '|'.join(qids),
        'props': 'labels|claims|sitelinks',
        'languages': 'en|ko|ja',
        'sitefilter': 'enwiki|kowiki|jawiki',
        'format': 'json'
    }

    headers = {
        'User-Agent': 'ChaldeasBot/1.0 (https://www.chaldeas.site; chaldeas@example.com) python-requests'
    }
    resp = requests.get(WIKIDATA_API, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get('entities', {})


def extract_location_info(entity: dict) -> dict:
    """엔티티에서 위치 정보 추출."""
    qid = entity.get('id', '')
    labels = entity.get('labels', {})
    claims = entity.get('claims', {})
    sitelinks = entity.get('sitelinks', {})

    name_en = labels.get('en', {}).get('value')
    name_ko = labels.get('ko', {}).get('value')
    name_ja = labels.get('ja', {}).get('value')
    name = name_en or name_ko or name_ja or qid

    # P625 좌표
    lat, lng = None, None
    for claim in claims.get('P625', []):
        dv = claim.get('mainsnak', {}).get('datavalue', {})
        if dv.get('type') == 'globecoordinate':
            val = dv.get('value', {})
            lat = val.get('latitude')
            lng = val.get('longitude')
            break

    # P625 없으면 P36 (수도) 참조 → 나중에 처리
    # 일단 좌표 없으면 스킵

    enwiki = sitelinks.get('enwiki', {}).get('title')

    return {
        'qid': qid,
        'name': name,
        'name_ko': name_ko,
        'name_ja': name_ja,
        'latitude': lat,
        'longitude': lng,
        'enwiki': enwiki
    }


def main():
    print("=== Case A: 미해결 P276 위치 추가 ===\n")

    # Step 1: 미해결 QID 수집
    print("Step 1: 미해결 location QID 수집...")
    qid_to_events = get_unresolved_location_qids()
    all_qids = list(qid_to_events.keys())
    total_events_affected = sum(len(v) for v in qid_to_events.values())
    print(f"  미해결 위치 QID: {len(all_qids)}개")
    print(f"  영향 이벤트: {total_events_affected}건")

    # Step 2: Wikidata API 배치 조회
    print(f"\nStep 2: Wikidata API 조회 ({len(all_qids)}개, 50개/배치)...")

    # 캐시 로드
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        print(f"  캐시 로드: {len(cache)}개")

    to_fetch = [q for q in all_qids if q not in cache]
    print(f"  새로 조회 필요: {len(to_fetch)}개")

    BATCH_SIZE = 50
    fetched = 0
    errors = 0

    for i in range(0, len(to_fetch), BATCH_SIZE):
        batch = to_fetch[i:i+BATCH_SIZE]
        try:
            entities = fetch_wikidata_batch(batch)
            for qid, entity in entities.items():
                if 'missing' in entity:
                    cache[qid] = {'qid': qid, 'missing': True}
                else:
                    cache[qid] = extract_location_info(entity)
            fetched += len(batch)

            if fetched % 500 == 0 or fetched == len(to_fetch):
                print(f"  {fetched}/{len(to_fetch)} 조회 완료...")
                # 중간 캐시 저장
                os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
                with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(cache, f, ensure_ascii=False)

            time.sleep(0.1)  # Rate limit 준수

        except Exception as e:
            errors += 1
            print(f"  ERROR batch {i}: {e}")
            if errors > 10:
                print("  Too many errors, stopping.")
                break
            time.sleep(2)

    # 최종 캐시 저장
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False)
    print(f"  캐시 저장: {len(cache)}개")

    # Step 3: 분석
    print(f"\nStep 3: 결과 분석...")
    with_coords = []
    without_coords = []
    missing = []

    for qid in all_qids:
        info = cache.get(qid)
        if not info or info.get('missing'):
            missing.append(qid)
        elif info.get('latitude') is not None and info.get('longitude') is not None:
            with_coords.append(info)
        else:
            without_coords.append(info)

    events_resolvable = sum(len(qid_to_events.get(loc['qid'], [])) for loc in with_coords)

    print(f"  좌표 있음: {len(with_coords)}개 위치 → {events_resolvable}건 이벤트 해결 가능")
    print(f"  좌표 없음: {len(without_coords)}개")
    print(f"  삭제됨/없음: {len(missing)}개")

    # Step 4: DB에 INSERT
    print(f"\nStep 4: DB에 {len(with_coords)}개 위치 추가...")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 중복 체크
    cur.execute("SELECT wikidata_id FROM locations WHERE wikidata_id IS NOT NULL")
    existing = set(r['wikidata_id'] for r in cur.fetchall())

    inserted = 0
    skipped = 0
    for loc in with_coords:
        if loc['qid'] in existing:
            skipped += 1
            continue

        cur.execute("""
            INSERT INTO locations (name, name_ko, latitude, longitude, wikidata_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
        """, (
            loc['name'],
            loc.get('name_ko'),
            loc['latitude'],
            loc['longitude'],
            loc['qid']
        ))
        new_id = cur.fetchone()['id']
        inserted += 1

        if inserted % 500 == 0:
            conn.commit()
            print(f"  {inserted}개 추가됨...")

    conn.commit()
    print(f"  추가 완료: {inserted}개 (스킵: {skipped}개)")

    # 새 로케이션 수 확인
    cur.execute("SELECT COUNT(*) as cnt FROM locations")
    total_locs = cur.fetchone()['cnt']
    print(f"  전체 로케이션 노드: {total_locs}")

    conn.close()


if __name__ == '__main__':
    main()
