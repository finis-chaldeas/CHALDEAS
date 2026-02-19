"""
로컬 Wikidata 덤프에서 이벤트 추출

Usage:
    python extract_events_from_dump.py --output events.jsonl --limit 100000
    python extract_events_from_dump.py --output events.jsonl  # 전체 추출
"""

import bz2
import json
import sys
import os
import argparse
import time
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass, asdict

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


DUMP_PATH = "C:/Projects/Chaldeas/data/wikidata/latest-all.json.bz2"

# 이벤트 타입 (P31 instance of)
EVENT_TYPES: Dict[str, str] = {
    'Q178561': 'battle',
    'Q198': 'war',
    'Q180684': 'military_conflict',
    'Q188055': 'siege',
    'Q131569': 'treaty',
    'Q10931': 'revolution',
    'Q124734': 'rebellion',
    'Q45382': 'coup',
    'Q8465': 'civil_war',
    'Q13418847': 'historical_event',
    'Q173065': 'crusade',
    'Q192909': 'natural_disaster',
    'Q3199915': 'massacre',
    'Q2401485': 'expedition',
    'Q209480': 'coronation',
    'Q3882219': 'assassination',
}

# 제외할 타입
EXCLUDED_TYPES: Set[str] = {
    'Q515',       # city
    'Q6256',      # country
    'Q5',         # human
    'Q16521',     # taxon
    'Q7889',      # video game
    'Q11424',     # film
    'Q5398426',   # TV series
}


@dataclass
class ExtractedEvent:
    """추출된 이벤트"""
    qid: str
    name: str
    name_ko: Optional[str]
    description: Optional[str]
    event_type: str

    # 시간
    point_in_time: Optional[str]  # P585
    start_time: Optional[str]     # P580
    end_time: Optional[str]       # P582

    # 위치 (QID만, 나중에 조회)
    location_qids: list          # P276
    country_qids: list           # P17

    # 관계
    participant_qids: list       # P710
    part_of_qid: Optional[str]   # P361


def get_claim_values(entity: dict, property_id: str) -> list:
    """엔티티에서 특정 속성의 값들 추출"""
    values = []
    claims = entity.get('claims', {}).get(property_id, [])

    for claim in claims:
        mainsnak = claim.get('mainsnak', {})
        datavalue = mainsnak.get('datavalue', {})
        dtype = datavalue.get('type')

        if dtype == 'wikibase-entityid':
            qid = datavalue.get('value', {}).get('id')
            if qid:
                values.append(qid)
        elif dtype == 'time':
            time_value = datavalue.get('value', {}).get('time')
            if time_value:
                values.append(time_value)
        elif dtype == 'string':
            val = datavalue.get('value')
            if val:
                values.append(val)

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


def is_event(entity: dict) -> tuple[bool, str]:
    """이벤트인지 판별, (is_event, event_type) 반환"""
    instance_of = get_claim_values(entity, 'P31')

    # 제외 타입 먼저 체크
    for type_qid in instance_of:
        if type_qid in EXCLUDED_TYPES:
            return False, ''

    # 이벤트 타입 체크
    for type_qid in instance_of:
        if type_qid in EVENT_TYPES:
            return True, EVENT_TYPES[type_qid]

    return False, ''


def extract_event(entity: dict, event_type: str) -> Optional[ExtractedEvent]:
    """엔티티에서 이벤트 데이터 추출"""
    qid = entity.get('id')
    if not qid:
        return None

    name = get_label(entity, 'en')
    if not name:
        return None

    # 시간
    point_in_time = get_claim_values(entity, 'P585')  # point in time
    start_time = get_claim_values(entity, 'P580')     # start time
    end_time = get_claim_values(entity, 'P582')       # end time

    # 위치
    location_qids = get_claim_values(entity, 'P276')  # location
    country_qids = get_claim_values(entity, 'P17')    # country

    # 참여자
    participant_qids = get_claim_values(entity, 'P710')  # participant

    # 상위 이벤트
    part_of = get_claim_values(entity, 'P361')  # part of

    return ExtractedEvent(
        qid=qid,
        name=name,
        name_ko=get_label(entity, 'ko'),
        description=get_description(entity, 'en'),
        event_type=event_type,
        point_in_time=point_in_time[0] if point_in_time else None,
        start_time=start_time[0] if start_time else None,
        end_time=end_time[0] if end_time else None,
        location_qids=location_qids,
        country_qids=country_qids,
        participant_qids=participant_qids,
        part_of_qid=part_of[0] if part_of else None
    )


def extract_events(dump_path: str, output_path: str, limit: int = None):
    """덤프에서 이벤트 추출"""
    print(f"=== 이벤트 추출 ===")
    print(f"입력: {dump_path}")
    print(f"출력: {output_path}")
    print(f"제한: {limit or '없음'}")
    print()

    if not os.path.exists(dump_path):
        print(f"Error: 덤프 파일 없음: {dump_path}")
        return

    file_size_gb = os.path.getsize(dump_path) / (1024**3)
    print(f"덤프 크기: {file_size_gb:.2f} GB")
    print()

    start_time = time.time()
    entity_count = 0
    event_count = 0

    # 통계
    type_counts: Dict[str, int] = {}
    with_location = 0
    with_date = 0

    with open(output_path, 'w', encoding='utf-8') as out:
        with bz2.open(dump_path, 'rt', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                if line in ('[', ']', ''):
                    continue

                if line.endswith(','):
                    line = line[:-1]

                try:
                    entity = json.loads(line)
                    entity_count += 1

                    # 이벤트 체크
                    is_evt, event_type = is_event(entity)

                    if is_evt:
                        event = extract_event(entity, event_type)

                        if event:
                            out.write(json.dumps(asdict(event), ensure_ascii=False) + '\n')
                            event_count += 1

                            # 통계
                            type_counts[event_type] = type_counts.get(event_type, 0) + 1
                            if event.location_qids or event.country_qids:
                                with_location += 1
                            if event.point_in_time or event.start_time:
                                with_date += 1

                            if event_count % 1000 == 0:
                                elapsed = time.time() - start_time
                                rate = entity_count / elapsed if elapsed > 0 else 0
                                print(f"  엔티티: {entity_count:,} | 이벤트: {event_count:,} | 속도: {rate:.0f}/s")

                            if limit and event_count >= limit:
                                break

                    if entity_count % 500000 == 0:
                        elapsed = time.time() - start_time
                        rate = entity_count / elapsed if elapsed > 0 else 0
                        print(f"  진행: {entity_count:,} 엔티티 ({rate:.0f}/s)")

                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    if entity_count < 100:
                        print(f"  Error at {entity_count}: {e}")
                    continue

    elapsed = time.time() - start_time

    print()
    print("=== 완료 ===")
    print(f"총 엔티티: {entity_count:,}")
    print(f"추출된 이벤트: {event_count:,}")
    print(f"이벤트 비율: {100*event_count/entity_count:.3f}%")
    print(f"소요 시간: {elapsed/60:.1f}분")
    print()
    print("=== 이벤트 통계 ===")
    print(f"위치 있음: {with_location} ({100*with_location/event_count:.1f}%)")
    print(f"날짜 있음: {with_date} ({100*with_date/event_count:.1f}%)")
    print()
    print("타입별:")
    for etype, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {etype}: {cnt}")
    print()
    print(f"출력 파일: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Extract events from Wikidata dump')
    parser.add_argument('--dump', default=DUMP_PATH, help='덤프 파일 경로')
    parser.add_argument('--output', default='extracted_events.jsonl', help='출력 파일')
    parser.add_argument('--limit', type=int, help='추출 개수 제한')

    args = parser.parse_args()

    extract_events(args.dump, args.output, args.limit)


if __name__ == '__main__':
    main()
