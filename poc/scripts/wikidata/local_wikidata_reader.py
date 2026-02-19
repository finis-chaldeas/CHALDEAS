"""
로컬 Wikidata 덤프 리더

Wikidata JSON dump (latest-all.json.bz2)를 스트리밍으로 읽어서 처리.
메모리 효율적: 한 줄씩 읽어서 처리.

Usage:
    # 이벤트 추출
    python local_wikidata_reader.py --type events --output events.jsonl

    # 특정 QID 조회
    python local_wikidata_reader.py --qid Q83224

    # 통계만
    python local_wikidata_reader.py --stats
"""

import bz2
import json
import sys
import os
import argparse
from typing import Dict, List, Optional, Generator, Any
from dataclasses import dataclass, asdict
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# 기본 경로
DUMP_PATH = "C:/Projects/Chaldeas/data/wikidata/latest-all.json.bz2"


# 이벤트로 인정되는 P31 (instance of) QID
EVENT_TYPES = {
    'Q178561',    # battle
    'Q198',       # war
    'Q180684',    # military conflict
    'Q188055',    # siege
    'Q131569',    # treaty
    'Q10931',     # revolution
    'Q124734',    # rebellion
    'Q45382',     # coup d'état
    'Q8465',      # civil war
    'Q13418847',  # historical event
    'Q3199915',   # massacre
    'Q2401485',   # expedition
    'Q12772',     # discovery
    'Q209480',    # coronation
    'Q3882219',   # assassination
    'Q1190554',   # occurrence
    'Q192909',    # natural disaster
    'Q173065',    # crusade
    'Q11514315',  # historical period
}

# 제외할 타입 (이벤트가 아님)
EXCLUDED_TYPES = {
    'Q515',       # city
    'Q6256',      # country
    'Q35657',     # state
    'Q82794',     # region
    'Q23442',     # island
    'Q8502',      # mountain
    'Q4022',      # river
    'Q23397',     # lake
    'Q5',         # human
    'Q16521',     # taxon
}


@dataclass
class WikidataEntity:
    """Wikidata 엔티티"""
    qid: str
    label: str
    label_ko: Optional[str]
    description: Optional[str]
    description_ko: Optional[str]
    instance_of: List[str]  # P31 값들
    properties: Dict[str, Any]  # 주요 속성들


def get_claim_values(entity: dict, property_id: str) -> List[str]:
    """엔티티에서 특정 속성의 값들을 추출"""
    values = []
    claims = entity.get('claims', {}).get(property_id, [])

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
            if lat and lng:
                values.append(f"{lat},{lng}")
        elif datavalue.get('type') == 'string':
            values.append(datavalue.get('value', ''))

    return values


def get_label(entity: dict, lang: str = 'en') -> Optional[str]:
    """라벨 추출"""
    labels = entity.get('labels', {})
    if lang in labels:
        return labels[lang].get('value')
    return None


def get_description(entity: dict, lang: str = 'en') -> Optional[str]:
    """설명 추출"""
    descriptions = entity.get('descriptions', {})
    if lang in descriptions:
        return descriptions[lang].get('value')
    return None


def parse_wikidata_time(time_str: str) -> Optional[int]:
    """Wikidata 시간 문자열 → 연도"""
    if not time_str:
        return None
    try:
        # +1066-10-14T00:00:00Z or -0055-01-01T00:00:00Z
        if time_str.startswith('+'):
            time_str = time_str[1:]
        year_str = time_str.split('T')[0].split('-')[0]
        if time_str.startswith('-'):
            return -int(time_str[1:].split('-')[0])
        return int(year_str)
    except:
        return None


def parse_entity(raw_entity: dict) -> Optional[WikidataEntity]:
    """raw JSON → WikidataEntity 변환"""
    qid = raw_entity.get('id')
    if not qid or not qid.startswith('Q'):
        return None

    # P31 (instance of)
    instance_of = get_claim_values(raw_entity, 'P31')

    # 주요 속성 추출
    properties = {
        # 시간
        'P585': get_claim_values(raw_entity, 'P585'),  # point in time
        'P580': get_claim_values(raw_entity, 'P580'),  # start time
        'P582': get_claim_values(raw_entity, 'P582'),  # end time

        # 위치
        'P276': get_claim_values(raw_entity, 'P276'),  # location
        'P17': get_claim_values(raw_entity, 'P17'),    # country
        'P625': get_claim_values(raw_entity, 'P625'),  # coordinates

        # 관계
        'P710': get_claim_values(raw_entity, 'P710'),  # participant
        'P361': get_claim_values(raw_entity, 'P361'),  # part of
        'P1542': get_claim_values(raw_entity, 'P1542'), # has effect
        'P828': get_claim_values(raw_entity, 'P828'),  # has cause
    }

    return WikidataEntity(
        qid=qid,
        label=get_label(raw_entity, 'en'),
        label_ko=get_label(raw_entity, 'ko'),
        description=get_description(raw_entity, 'en'),
        description_ko=get_description(raw_entity, 'ko'),
        instance_of=instance_of,
        properties=properties
    )


def stream_entities(dump_path: str = DUMP_PATH) -> Generator[dict, None, None]:
    """Wikidata 덤프를 스트리밍으로 읽기"""
    if not os.path.exists(dump_path):
        raise FileNotFoundError(f"Dump file not found: {dump_path}")

    print(f"Reading: {dump_path}")
    print(f"File size: {os.path.getsize(dump_path) / 1024**3:.2f} GB")

    with bz2.open(dump_path, 'rt', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # 첫 줄과 마지막 줄은 JSON 배열 괄호
            if line in ('[', ']', ''):
                continue

            # 마지막 쉼표 제거
            if line.endswith(','):
                line = line[:-1]

            try:
                entity = json.loads(line)
                yield entity
            except json.JSONDecodeError as e:
                if line_num % 100000 == 0:
                    print(f"  JSON error at line {line_num}: {e}")
                continue

            if line_num % 500000 == 0:
                print(f"  Processed {line_num:,} lines...")


def is_event(entity: WikidataEntity) -> bool:
    """이벤트인지 판별"""
    # P31 (instance of) 확인
    for type_qid in entity.instance_of:
        if type_qid in EXCLUDED_TYPES:
            return False
        if type_qid in EVENT_TYPES:
            return True

    # 날짜가 있으면 이벤트일 가능성
    has_date = bool(
        entity.properties.get('P585') or
        entity.properties.get('P580')
    )

    # 위치가 있으면 이벤트일 가능성
    has_location = bool(
        entity.properties.get('P276') or
        entity.properties.get('P17')
    )

    return has_date and has_location


def extract_events(dump_path: str, output_path: str, limit: int = None):
    """이벤트만 추출"""
    print(f"\n=== 이벤트 추출 ===")
    print(f"Output: {output_path}")
    print(f"Limit: {limit or 'None'}")

    count = 0
    event_count = 0

    with open(output_path, 'w', encoding='utf-8') as out:
        for raw_entity in stream_entities(dump_path):
            count += 1

            entity = parse_entity(raw_entity)
            if not entity:
                continue

            if is_event(entity):
                out.write(json.dumps(asdict(entity), ensure_ascii=False) + '\n')
                event_count += 1

                if event_count % 10000 == 0:
                    print(f"  Found {event_count:,} events...")

                if limit and event_count >= limit:
                    break

    print(f"\n=== 완료 ===")
    print(f"총 엔티티: {count:,}")
    print(f"이벤트: {event_count:,}")
    print(f"저장: {output_path}")


def find_entity(dump_path: str, target_qid: str) -> Optional[WikidataEntity]:
    """특정 QID 찾기"""
    print(f"\nSearching for {target_qid}...")

    for raw_entity in stream_entities(dump_path):
        qid = raw_entity.get('id')
        if qid == target_qid:
            entity = parse_entity(raw_entity)
            return entity

    return None


def print_stats(dump_path: str, sample_size: int = 100000):
    """덤프 통계"""
    print(f"\n=== 덤프 통계 (샘플: {sample_size:,}) ===\n")

    stats = {
        'total': 0,
        'items': 0,
        'properties': 0,
        'with_p31': 0,
        'with_date': 0,
        'with_location': 0,
        'potential_events': 0,
    }

    type_counts = {}

    for raw_entity in stream_entities(dump_path):
        stats['total'] += 1

        qid = raw_entity.get('id', '')
        if qid.startswith('Q'):
            stats['items'] += 1
        elif qid.startswith('P'):
            stats['properties'] += 1

        # P31 분석
        p31_values = get_claim_values(raw_entity, 'P31')
        if p31_values:
            stats['with_p31'] += 1
            for type_qid in p31_values:
                type_counts[type_qid] = type_counts.get(type_qid, 0) + 1

        # 날짜
        if get_claim_values(raw_entity, 'P585') or get_claim_values(raw_entity, 'P580'):
            stats['with_date'] += 1

        # 위치
        if get_claim_values(raw_entity, 'P276') or get_claim_values(raw_entity, 'P17'):
            stats['with_location'] += 1

        # 잠재적 이벤트
        entity = parse_entity(raw_entity)
        if entity and is_event(entity):
            stats['potential_events'] += 1

        if stats['total'] >= sample_size:
            break

    print("기본 통계:")
    for key, value in stats.items():
        pct = 100 * value / stats['total'] if stats['total'] else 0
        print(f"  {key}: {value:,} ({pct:.1f}%)")

    print("\n상위 P31 타입:")
    sorted_types = sorted(type_counts.items(), key=lambda x: -x[1])[:20]
    for type_qid, count in sorted_types:
        print(f"  {type_qid}: {count:,}")


def main():
    parser = argparse.ArgumentParser(description='Local Wikidata Reader')
    parser.add_argument('--dump', default=DUMP_PATH, help='덤프 파일 경로')
    parser.add_argument('--type', choices=['events', 'persons', 'locations'], help='추출 타입')
    parser.add_argument('--output', help='출력 파일')
    parser.add_argument('--qid', help='특정 QID 조회')
    parser.add_argument('--stats', action='store_true', help='통계만 출력')
    parser.add_argument('--limit', type=int, help='추출 개수 제한')

    args = parser.parse_args()

    if not os.path.exists(args.dump):
        print(f"Error: 덤프 파일이 없습니다: {args.dump}")
        print("다운로드 필요: powershell -File data/wikidata/download_wikidata.ps1")
        return

    if args.stats:
        print_stats(args.dump)

    elif args.qid:
        entity = find_entity(args.dump, args.qid)
        if entity:
            print(f"\n=== {entity.qid}: {entity.label} ===")
            print(f"한국어: {entity.label_ko}")
            print(f"설명: {entity.description}")
            print(f"P31: {entity.instance_of}")
            print(f"\n속성:")
            for prop, values in entity.properties.items():
                if values:
                    print(f"  {prop}: {values}")
        else:
            print(f"Not found: {args.qid}")

    elif args.type == 'events':
        output = args.output or 'wikidata_events.jsonl'
        extract_events(args.dump, output, args.limit)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
