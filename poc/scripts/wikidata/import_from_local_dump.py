"""
로컬 Wikidata 덤프에서 완전 임포트

완전한 구조로 임포트:
1. 이벤트 → events 테이블
2. 위치 → locations 테이블 (먼저)
3. 인물 → persons 테이블 (먼저)
4. 연결 → event_locations, event_persons

Usage:
    # 1단계: 덤프에서 이벤트 추출
    python import_from_local_dump.py --extract --limit=10000

    # 2단계: DB에 임포트
    python import_from_local_dump.py --import

    # 전체 (추출 + 임포트)
    python import_from_local_dump.py --all
"""

import bz2
import json
import sys
import os
import argparse
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# 경로
DUMP_PATH = "C:/Projects/Chaldeas/data/wikidata/latest-all.json.bz2"
EVENTS_JSONL = "C:/Projects/Chaldeas/data/wikidata/extracted_events.jsonl"
LOCATIONS_JSONL = "C:/Projects/Chaldeas/data/wikidata/extracted_locations.jsonl"
PERSONS_JSONL = "C:/Projects/Chaldeas/data/wikidata/extracted_persons.jsonl"

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}


# ========================================
# 이벤트 타입 정의
# ========================================

EVENT_TYPES = {
    # 군사
    'Q178561': 'battle',
    'Q198': 'war',
    'Q180684': 'military_conflict',
    'Q188055': 'siege',
    'Q8465': 'civil_war',
    'Q173065': 'crusade',

    # 정치
    'Q131569': 'treaty',
    'Q10931': 'revolution',
    'Q124734': 'rebellion',
    'Q45382': 'coup',
    'Q209480': 'coronation',

    # 기타
    'Q13418847': 'historical_event',
    'Q3199915': 'massacre',
    'Q2401485': 'expedition',
    'Q12772': 'discovery',
    'Q3882219': 'assassination',
    'Q192909': 'natural_disaster',
    'Q1190554': 'occurrence',
}

EXCLUDED_TYPES = {
    'Q515', 'Q6256', 'Q35657', 'Q82794', 'Q23442',  # 지리
    'Q8502', 'Q4022', 'Q23397', 'Q165',              # 자연
    'Q5', 'Q16521',                                   # 인물/생물
    'Q35120', 'Q7184903', 'Q151885',                 # 추상
}


# ========================================
# 유틸리티 함수
# ========================================

def get_claim_values(entity: dict, prop: str) -> List[str]:
    """속성 값 추출"""
    values = []
    claims = entity.get('claims', {}).get(prop, [])

    for claim in claims:
        mainsnak = claim.get('mainsnak', {})
        datavalue = mainsnak.get('datavalue', {})

        if datavalue.get('type') == 'wikibase-entityid':
            qid = datavalue.get('value', {}).get('id')
            if qid:
                values.append(qid)
        elif datavalue.get('type') == 'time':
            time_value = datavalue.get('value', {}).get('time')
            if time_value:
                values.append(time_value)
        elif datavalue.get('type') == 'globecoordinate':
            lat = datavalue.get('value', {}).get('latitude')
            lng = datavalue.get('value', {}).get('longitude')
            if lat is not None and lng is not None:
                values.append({'lat': lat, 'lng': lng})

    return values


def get_label(entity: dict, lang: str) -> Optional[str]:
    """라벨 추출"""
    labels = entity.get('labels', {})
    if lang in labels:
        return labels[lang].get('value')
    return None


def get_description(entity: dict, lang: str) -> Optional[str]:
    """설명 추출"""
    descriptions = entity.get('descriptions', {})
    if lang in descriptions:
        return descriptions[lang].get('value')
    return None


def parse_year(time_str: str) -> Optional[int]:
    """연도 파싱"""
    if not time_str or not isinstance(time_str, str):
        return None
    try:
        if time_str.startswith('+'):
            time_str = time_str[1:]
        if time_str.startswith('-'):
            year = -int(time_str[1:].split('-')[0])
        else:
            year = int(time_str.split('-')[0].split('T')[0])
        return year
    except:
        return None


# ========================================
# 1단계: 덤프에서 추출
# ========================================

def extract_from_dump(limit: int = None):
    """덤프에서 이벤트, 위치, 인물 추출"""

    print(f"=== 덤프에서 추출 ===")
    print(f"Dump: {DUMP_PATH}")
    print(f"Limit: {limit or 'None'}")

    if not os.path.exists(DUMP_PATH):
        print(f"Error: 덤프 파일 없음")
        return

    # 출력 파일
    events_file = open(EVENTS_JSONL, 'w', encoding='utf-8')
    locations_file = open(LOCATIONS_JSONL, 'w', encoding='utf-8')
    persons_file = open(PERSONS_JSONL, 'w', encoding='utf-8')

    stats = {
        'total': 0,
        'events': 0,
        'locations': 0,
        'persons': 0,
    }

    # 연관 엔티티 수집 (나중에 조회)
    needed_locations: Set[str] = set()
    needed_persons: Set[str] = set()

    print(f"\n1단계: 이벤트 추출...")

    with bz2.open(DUMP_PATH, 'rt', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line in ('[', ']', ''):
                continue
            if line.endswith(','):
                line = line[:-1]

            try:
                entity = json.loads(line)
            except:
                continue

            stats['total'] += 1
            qid = entity.get('id', '')

            if not qid.startswith('Q'):
                continue

            # P31 (instance of) 확인
            p31 = get_claim_values(entity, 'P31')

            # 제외 타입 체크
            if any(t in EXCLUDED_TYPES for t in p31):
                continue

            # 이벤트 체크
            event_type = None
            for t in p31:
                if t in EVENT_TYPES:
                    event_type = EVENT_TYPES[t]
                    break

            if not event_type:
                # 날짜와 위치가 있으면 이벤트로 간주
                has_date = bool(get_claim_values(entity, 'P585') or get_claim_values(entity, 'P580'))
                has_location = bool(get_claim_values(entity, 'P276') or get_claim_values(entity, 'P17'))

                if not (has_date and has_location):
                    continue

                event_type = 'unknown'

            # 이벤트 추출
            time_values = get_claim_values(entity, 'P585') or get_claim_values(entity, 'P580')
            start_year = parse_year(time_values[0]) if time_values else None

            if start_year is None:
                continue  # 날짜 필수

            # 위치 QID
            location_qids = get_claim_values(entity, 'P276')
            country_qids = get_claim_values(entity, 'P17')

            # 참여자 QID
            participant_qids = get_claim_values(entity, 'P710')

            # 연관 엔티티 수집
            for loc_qid in location_qids + country_qids:
                if isinstance(loc_qid, str):
                    needed_locations.add(loc_qid)

            for person_qid in participant_qids:
                if isinstance(person_qid, str):
                    needed_persons.add(person_qid)

            # 이벤트 데이터
            event_data = {
                'qid': qid,
                'label': get_label(entity, 'en'),
                'label_ko': get_label(entity, 'ko'),
                'description': get_description(entity, 'en'),
                'description_ko': get_description(entity, 'ko'),
                'event_type': event_type,
                'start_year': start_year,
                'end_year': parse_year((get_claim_values(entity, 'P582') or [None])[0]),
                'location_qids': [q for q in location_qids if isinstance(q, str)],
                'country_qids': [q for q in country_qids if isinstance(q, str)],
                'participant_qids': [q for q in participant_qids if isinstance(q, str)],
                'part_of_qid': (get_claim_values(entity, 'P361') or [None])[0],
            }

            events_file.write(json.dumps(event_data, ensure_ascii=False) + '\n')
            stats['events'] += 1

            if stats['events'] % 5000 == 0:
                print(f"  이벤트: {stats['events']:,}, 총: {stats['total']:,}")

            if limit and stats['events'] >= limit:
                break

    events_file.close()

    print(f"\n이벤트 추출 완료: {stats['events']:,}개")
    print(f"필요한 위치: {len(needed_locations):,}개")
    print(f"필요한 인물: {len(needed_persons):,}개")

    # 2단계: 위치/인물 추출 (2차 스캔)
    print(f"\n2단계: 위치/인물 추출...")

    with bz2.open(DUMP_PATH, 'rt', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line in ('[', ']', ''):
                continue
            if line.endswith(','):
                line = line[:-1]

            try:
                entity = json.loads(line)
            except:
                continue

            qid = entity.get('id', '')

            # 위치
            if qid in needed_locations:
                coords = get_claim_values(entity, 'P625')
                coord = coords[0] if coords and isinstance(coords[0], dict) else None

                loc_data = {
                    'qid': qid,
                    'label': get_label(entity, 'en'),
                    'label_ko': get_label(entity, 'ko'),
                    'description': get_description(entity, 'en'),
                    'latitude': coord['lat'] if coord else None,
                    'longitude': coord['lng'] if coord else None,
                    'country_qid': (get_claim_values(entity, 'P17') or [None])[0],
                }

                locations_file.write(json.dumps(loc_data, ensure_ascii=False) + '\n')
                stats['locations'] += 1
                needed_locations.discard(qid)

            # 인물
            if qid in needed_persons:
                person_data = {
                    'qid': qid,
                    'label': get_label(entity, 'en'),
                    'label_ko': get_label(entity, 'ko'),
                    'description': get_description(entity, 'en'),
                    'birth_year': parse_year((get_claim_values(entity, 'P569') or [None])[0]),
                    'death_year': parse_year((get_claim_values(entity, 'P570') or [None])[0]),
                }

                persons_file.write(json.dumps(person_data, ensure_ascii=False) + '\n')
                stats['persons'] += 1
                needed_persons.discard(qid)

            if line_num % 500000 == 0:
                print(f"  스캔: {line_num:,}, 위치: {stats['locations']:,}, 인물: {stats['persons']:,}")

            # 모두 찾으면 종료
            if not needed_locations and not needed_persons:
                break

    locations_file.close()
    persons_file.close()

    print(f"\n=== 추출 완료 ===")
    print(f"이벤트: {stats['events']:,} → {EVENTS_JSONL}")
    print(f"위치: {stats['locations']:,} → {LOCATIONS_JSONL}")
    print(f"인물: {stats['persons']:,} → {PERSONS_JSONL}")
    print(f"못 찾은 위치: {len(needed_locations):,}")
    print(f"못 찾은 인물: {len(needed_persons):,}")


# ========================================
# 2단계: DB 임포트
# ========================================

def import_to_db():
    """추출된 데이터를 DB에 임포트"""

    print(f"\n=== DB 임포트 ===")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    stats = {
        'locations_inserted': 0,
        'persons_inserted': 0,
        'events_inserted': 0,
        'event_locations': 0,
        'event_persons': 0,
    }

    # 1. 위치 임포트
    print(f"\n1. 위치 임포트...")
    location_map = {}  # qid → id

    if os.path.exists(LOCATIONS_JSONL):
        with open(LOCATIONS_JSONL, 'r', encoding='utf-8') as f:
            for line in f:
                loc = json.loads(line)

                # 이미 존재하는지 확인
                cur.execute("SELECT id FROM locations WHERE wikidata_id = %s", (loc['qid'],))
                existing = cur.fetchone()

                if existing:
                    location_map[loc['qid']] = existing[0]
                    continue

                # 새로 삽입
                try:
                    cur.execute("""
                        INSERT INTO locations (name, name_ko, description, latitude, longitude, wikidata_id, type, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        RETURNING id
                    """, (
                        loc['label'],
                        loc.get('label_ko'),
                        loc.get('description'),
                        loc.get('latitude'),
                        loc.get('longitude'),
                        loc['qid'],
                        'place'
                    ))
                    location_map[loc['qid']] = cur.fetchone()[0]
                    stats['locations_inserted'] += 1
                except Exception as e:
                    conn.rollback()
                    continue

        conn.commit()
        print(f"  위치 삽입: {stats['locations_inserted']:,}")

    # 2. 인물 임포트
    print(f"\n2. 인물 임포트...")
    person_map = {}  # qid → id

    if os.path.exists(PERSONS_JSONL):
        with open(PERSONS_JSONL, 'r', encoding='utf-8') as f:
            for line in f:
                person = json.loads(line)

                cur.execute("SELECT id FROM persons WHERE wikidata_id = %s", (person['qid'],))
                existing = cur.fetchone()

                if existing:
                    person_map[person['qid']] = existing[0]
                    continue

                try:
                    cur.execute("""
                        INSERT INTO persons (name, name_ko, description, birth_year, death_year, wikidata_id, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                        RETURNING id
                    """, (
                        person['label'],
                        person.get('label_ko'),
                        person.get('description'),
                        person.get('birth_year'),
                        person.get('death_year'),
                        person['qid'],
                    ))
                    person_map[person['qid']] = cur.fetchone()[0]
                    stats['persons_inserted'] += 1
                except Exception as e:
                    conn.rollback()
                    continue

        conn.commit()
        print(f"  인물 삽입: {stats['persons_inserted']:,}")

    # 3. 이벤트 임포트
    print(f"\n3. 이벤트 임포트...")

    if os.path.exists(EVENTS_JSONL):
        with open(EVENTS_JSONL, 'r', encoding='utf-8') as f:
            for line in f:
                event = json.loads(line)

                # 이미 존재하는지 확인
                cur.execute("SELECT id FROM events WHERE wikidata_id = %s", (event['qid'],))
                if cur.fetchone():
                    continue

                # primary_location_id
                primary_location_id = None
                for loc_qid in event.get('location_qids', []) + event.get('country_qids', []):
                    if loc_qid in location_map:
                        primary_location_id = location_map[loc_qid]
                        break

                # slug 생성
                import re
                slug = re.sub(r'[^a-z0-9]+', '-', (event['label'] or '').lower()).strip('-')[:100]

                try:
                    cur.execute("""
                        INSERT INTO events (
                            title, title_ko, description, slug,
                            date_start, date_end,
                            primary_location_id, wikidata_id,
                            source_reliability, certainty,
                            created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s,
                            %s, %s,
                            5, 'confirmed',
                            NOW(), NOW()
                        )
                        RETURNING id
                    """, (
                        event['label'],
                        event.get('label_ko'),
                        event.get('description'),
                        slug + '-' + event['qid'].lower(),
                        event['start_year'],
                        event.get('end_year'),
                        primary_location_id,
                        event['qid'],
                    ))

                    event_id = cur.fetchone()[0]
                    stats['events_inserted'] += 1

                    # event_locations 연결
                    for loc_qid in event.get('location_qids', []):
                        if loc_qid in location_map:
                            cur.execute("""
                                INSERT INTO event_locations (event_id, location_id, role)
                                VALUES (%s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """, (event_id, location_map[loc_qid], 'occurred_at'))
                            stats['event_locations'] += 1

                    # event_persons 연결
                    for person_qid in event.get('participant_qids', []):
                        if person_qid in person_map:
                            cur.execute("""
                                INSERT INTO event_persons (event_id, person_id, role)
                                VALUES (%s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """, (event_id, person_map[person_qid], 'participant'))
                            stats['event_persons'] += 1

                except Exception as e:
                    conn.rollback()
                    continue

                if stats['events_inserted'] % 1000 == 0:
                    conn.commit()
                    print(f"  이벤트: {stats['events_inserted']:,}")

        conn.commit()

    print(f"\n=== 임포트 완료 ===")
    for key, value in stats.items():
        print(f"  {key}: {value:,}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Import from Local Wikidata Dump')
    parser.add_argument('--extract', action='store_true', help='덤프에서 추출')
    parser.add_argument('--import', dest='do_import', action='store_true', help='DB에 임포트')
    parser.add_argument('--all', action='store_true', help='전체 (추출 + 임포트)')
    parser.add_argument('--limit', type=int, help='이벤트 추출 제한')

    args = parser.parse_args()

    if args.extract or args.all:
        extract_from_dump(args.limit)

    if args.do_import or args.all:
        import_to_db()

    if not (args.extract or args.do_import or args.all):
        parser.print_help()


if __name__ == '__main__':
    main()
