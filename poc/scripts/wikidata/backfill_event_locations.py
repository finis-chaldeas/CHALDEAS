"""
이벤트 위치 백필 스크립트

기존 events 테이블의 이벤트들에 대해:
1. Wikidata에서 P276 (location) 정보 조회
2. locations 테이블에 위치 레코드 생성 (wikidata_id 포함)
3. events.primary_location_id 연결
4. 좌표 데이터(P625)도 가져와서 locations.latitude/longitude 설정

Usage:
    python backfill_event_locations.py --test          # 10개만 테스트
    python backfill_event_locations.py --limit=100    # 100개 처리
    python backfill_event_locations.py --all          # 전체 처리
"""

import os
import sys
import time
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests
import psycopg2
from psycopg2.extras import RealDictCursor

# Windows 콘솔 유니코드
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Wikidata SPARQL endpoint
WIKIDATA_ENDPOINT = 'https://query.wikidata.org/sparql'

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}


def sparql_query(query: str, timeout: int = 60) -> List[Dict]:
    """SPARQL 쿼리 실행."""
    try:
        response = requests.get(
            WIKIDATA_ENDPOINT,
            params={'query': query, 'format': 'json'},
            timeout=timeout,
            headers={'User-Agent': 'CHALDEAS/1.0 (Historical Knowledge System)'}
        )
        if response.status_code == 200:
            return response.json()['results']['bindings']
        elif response.status_code == 429:
            print(f"  Rate limited, waiting 30s...")
            time.sleep(30)
            return sparql_query(query, timeout)
        else:
            print(f"  SPARQL error: {response.status_code}")
            return []
    except requests.exceptions.Timeout:
        print(f"  SPARQL timeout")
        return []
    except Exception as e:
        print(f"  SPARQL error: {e}")
        return []


def fetch_event_location(event_qid: str) -> Optional[Dict]:
    """이벤트의 위치 정보를 Wikidata에서 가져옴."""
    query = f"""
    SELECT ?location ?locationLabel ?coord ?countryLabel WHERE {{
        wd:{event_qid} wdt:P276 ?location.

        OPTIONAL {{ ?location wdt:P625 ?coord. }}
        OPTIONAL {{ ?location wdt:P17 ?country. }}

        SERVICE wikibase:label {{
            bd:serviceParam wikibase:language "en".
            ?location rdfs:label ?locationLabel.
            ?country rdfs:label ?countryLabel.
        }}
    }}
    LIMIT 1
    """

    results = sparql_query(query, timeout=30)

    if not results:
        return None

    r = results[0]
    location_qid = r.get('location', {}).get('value', '').split('/')[-1]

    if not location_qid.startswith('Q'):
        return None

    # 좌표 파싱
    coord = r.get('coord', {}).get('value', '')
    latitude, longitude = None, None
    if coord:
        # Format: Point(longitude latitude)
        try:
            coord = coord.replace('Point(', '').replace(')', '')
            parts = coord.split()
            longitude = float(parts[0])
            latitude = float(parts[1])
        except:
            pass

    return {
        'location_qid': location_qid,
        'location_label': r.get('locationLabel', {}).get('value', ''),
        'country_label': r.get('countryLabel', {}).get('value'),
        'latitude': latitude,
        'longitude': longitude,
    }


def fetch_location_details(location_qid: str) -> Optional[Dict]:
    """위치의 상세 정보를 Wikidata에서 가져옴."""
    query = f"""
    SELECT ?label ?label_ko ?description ?coord ?countryLabel ?instanceLabel WHERE {{
        BIND(wd:{location_qid} AS ?loc)

        OPTIONAL {{ ?loc rdfs:label ?label. FILTER(LANG(?label) = "en") }}
        OPTIONAL {{ ?loc rdfs:label ?label_ko. FILTER(LANG(?label_ko) = "ko") }}
        OPTIONAL {{ ?loc schema:description ?description. FILTER(LANG(?description) = "en") }}
        OPTIONAL {{ ?loc wdt:P625 ?coord. }}
        OPTIONAL {{ ?loc wdt:P17 ?country. }}
        OPTIONAL {{ ?loc wdt:P31 ?instance. }}

        SERVICE wikibase:label {{
            bd:serviceParam wikibase:language "en".
            ?country rdfs:label ?countryLabel.
            ?instance rdfs:label ?instanceLabel.
        }}
    }}
    LIMIT 1
    """

    results = sparql_query(query, timeout=30)

    if not results:
        return None

    r = results[0]

    # 좌표 파싱
    coord = r.get('coord', {}).get('value', '')
    latitude, longitude = None, None
    if coord:
        try:
            coord = coord.replace('Point(', '').replace(')', '')
            parts = coord.split()
            longitude = float(parts[0])
            latitude = float(parts[1])
        except:
            pass

    return {
        'label': r.get('label', {}).get('value', f'Location {location_qid}'),
        'label_ko': r.get('label_ko', {}).get('value'),
        'description': r.get('description', {}).get('value'),
        'latitude': latitude,
        'longitude': longitude,
        'country': r.get('countryLabel', {}).get('value'),
        'instance_of': r.get('instanceLabel', {}).get('value'),
    }


def get_or_create_location(conn, location_qid: str, location_label: str,
                           latitude: float = None, longitude: float = None) -> Optional[int]:
    """위치 레코드를 조회하거나 생성."""
    cur = conn.cursor()

    # 이미 존재하는지 확인
    cur.execute("SELECT id FROM locations WHERE wikidata_id = %s", (location_qid,))
    existing = cur.fetchone()

    if existing:
        location_id = existing[0]
        # 좌표가 없으면 업데이트
        if latitude and longitude:
            cur.execute("""
                UPDATE locations
                SET latitude = COALESCE(latitude, %s),
                    longitude = COALESCE(longitude, %s),
                    updated_at = NOW()
                WHERE id = %s AND (latitude IS NULL OR longitude IS NULL)
            """, (latitude, longitude, location_id))
        return location_id

    # 새로 생성
    # 먼저 Wikidata에서 상세 정보 가져오기
    details = fetch_location_details(location_qid)

    if details:
        label = details.get('label') or location_label
        label_ko = details.get('label_ko')
        description = details.get('description')
        lat = details.get('latitude') or latitude
        lng = details.get('longitude') or longitude
    else:
        label = location_label
        label_ko = None
        description = None
        lat = latitude
        lng = longitude

    # type 추론 (instance_of 기반)
    location_type = 'unknown'
    if details:
        instance_of = (details.get('instance_of') or '').lower()
        if any(x in instance_of for x in ['city', 'town', 'village', 'municipality', 'commune']):
            location_type = 'city'
        elif any(x in instance_of for x in ['county', 'district', 'province', 'region', 'prefecture']):
            location_type = 'region'
        elif any(x in instance_of for x in ['river', 'lake', 'sea', 'ocean', 'bay', 'harbor']):
            location_type = 'water'
        elif any(x in instance_of for x in ['mountain', 'hill', 'volcano', 'peak']):
            location_type = 'mountain'
        elif any(x in instance_of for x in ['country', 'nation', 'kingdom', 'empire']):
            location_type = 'country'
        elif any(x in instance_of for x in ['battlefield', 'site', 'field']):
            location_type = 'site'
        elif any(x in instance_of for x in ['island', 'peninsula']):
            location_type = 'island'
        else:
            location_type = 'place'

    try:
        cur.execute("""
            INSERT INTO locations (
                name, name_ko, description,
                latitude, longitude,
                type,
                wikidata_id,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s,
                %s, %s,
                %s,
                %s,
                NOW(), NOW()
            )
            RETURNING id
        """, (
            label, label_ko, description,
            lat, lng,
            location_type,
            location_qid
        ))
        return cur.fetchone()[0]
    except Exception as e:
        print(f"  Error creating location {location_qid}: {e}")
        conn.rollback()
        return None


def backfill_event_locations(limit: int = None, dry_run: bool = False):
    """이벤트 위치 백필 실행."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 위치가 없는 이벤트 조회
    query = """
        SELECT id, title, wikidata_id
        FROM events
        WHERE wikidata_id IS NOT NULL
          AND primary_location_id IS NULL
        ORDER BY id
    """
    if limit:
        query += f" LIMIT {limit}"

    cur.execute(query)
    events = cur.fetchall()

    print(f"위치 없는 이벤트: {len(events)}개")

    stats = {
        'total': len(events),
        'processed': 0,
        'location_found': 0,
        'location_created': 0,
        'location_linked': 0,
        'no_location': 0,
        'errors': 0,
    }

    for i, event in enumerate(events):
        if i % 10 == 0:
            print(f"[{i+1}/{len(events)}] 처리 중... (found: {stats['location_found']}, linked: {stats['location_linked']})", end='\r')

        event_qid = event['wikidata_id']

        # Wikidata에서 위치 정보 가져오기
        location_data = fetch_event_location(event_qid)

        stats['processed'] += 1

        if not location_data:
            stats['no_location'] += 1
            continue

        stats['location_found'] += 1

        if dry_run:
            print(f"\n  {event['title']}: {location_data['location_label']} ({location_data['location_qid']})")
            continue

        # 위치 레코드 생성 또는 조회
        location_id = get_or_create_location(
            conn,
            location_data['location_qid'],
            location_data['location_label'],
            location_data.get('latitude'),
            location_data.get('longitude')
        )

        if location_id:
            stats['location_created'] += 1

            # 이벤트에 primary_location_id 연결
            cur.execute("""
                UPDATE events
                SET primary_location_id = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (location_id, event['id']))

            stats['location_linked'] += 1

            # 주기적 커밋
            if i % 50 == 0:
                conn.commit()

        # Rate limiting
        time.sleep(0.5)

    if not dry_run:
        conn.commit()

    print(f"\n\n=== 결과 ===")
    print(f"총 이벤트: {stats['total']}")
    print(f"처리됨: {stats['processed']}")
    print(f"위치 발견: {stats['location_found']}")
    print(f"위치 생성/조회: {stats['location_created']}")
    print(f"이벤트 연결: {stats['location_linked']}")
    print(f"위치 없음: {stats['no_location']}")
    print(f"오류: {stats['errors']}")

    # 최종 현황
    if not dry_run:
        cur.execute("SELECT COUNT(*) FROM events WHERE primary_location_id IS NOT NULL")
        with_location = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) FROM events WHERE wikidata_id IS NOT NULL")
        total_v2 = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) FROM locations WHERE wikidata_id IS NOT NULL")
        wikidata_locations = cur.fetchone()['count']

        print(f"\n=== DB 현황 ===")
        print(f"V2 이벤트 (wikidata_id): {total_v2}")
        print(f"위치 연결된 이벤트: {with_location} ({100*with_location/total_v2:.1f}%)")
        print(f"Wikidata 위치: {wikidata_locations}")

    conn.close()
    return stats


def main():
    parser = argparse.ArgumentParser(description='Event Location Backfill')
    parser.add_argument('--limit', type=int, default=None, help='처리할 이벤트 수')
    parser.add_argument('--test', action='store_true', help='테스트 모드 (10개, dry-run)')
    parser.add_argument('--dry-run', action='store_true', help='DB 변경 없이 확인만')
    parser.add_argument('--all', action='store_true', help='전체 처리')

    args = parser.parse_args()

    limit = args.limit
    dry_run = args.dry_run

    if args.test:
        limit = 10
        dry_run = True

    if args.all:
        limit = None

    print(f"=== Event Location Backfill ===")
    print(f"Limit: {limit or 'All'}")
    print(f"Dry-run: {dry_run}")
    print()

    backfill_event_locations(limit=limit, dry_run=dry_run)


if __name__ == '__main__':
    main()
