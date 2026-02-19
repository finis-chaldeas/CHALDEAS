"""
Core 이벤트 추출 (sitelink >= 10)

Usage:
    python extract_events_core.py --output events_core.jsonl
    python extract_events_core.py --output events_core.jsonl --limit 1000  # 테스트
"""

import json
import sys
import os
import argparse
import time
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass, asdict, field
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# E 드라이브의 압축 해제된 덤프
DUMP_PATH = "E:/wikidata/latest-all.json"

# 최소 sitelink 수 (이 이상이어야 추출)
MIN_SITELINKS = 10

# Core 이벤트 타입 (P31 instance of)
CORE_EVENT_TYPES: Dict[str, str] = {
    # 전쟁/군사
    'Q178561': 'battle',
    'Q198': 'war',
    'Q180684': 'military_conflict',
    'Q188055': 'siege',
    'Q8465': 'civil_war',
    'Q173065': 'crusade',
    'Q2401485': 'expedition',

    # 정치
    'Q131569': 'treaty',
    'Q10931': 'revolution',
    'Q124734': 'rebellion',
    'Q45382': 'coup',
    'Q3882219': 'assassination',
    'Q209480': 'coronation',

    # 재해
    'Q192909': 'natural_disaster',
    'Q5389': 'earthquake',
    'Q8065': 'flood',
    'Q8084': 'volcanic_eruption',
    'Q8070': 'hurricane',
    'Q168983': 'epidemic',
    'Q3199915': 'massacre',

    # 역사
    'Q13418847': 'historical_event',
    'Q11514315': 'historical_period',
    'Q1190554': 'occurrence',
}

# 제외할 타입 (이 타입이면 스킵)
EXCLUDED_TYPES: Set[str] = {
    'Q515',       # city
    'Q6256',      # country
    'Q5',         # human
    'Q16521',     # taxon
    'Q7889',      # video game
    'Q11424',     # film
    'Q5398426',   # TV series
    'Q7725634',   # literary work
    'Q482994',    # album
    'Q476028',    # sports competition (개별 경기)
    'Q27020041',  # sports season
    'Q18608583',  # recurring sporting event
}


@dataclass
class ExtractedEvent:
    """추출된 이벤트"""
    qid: str
    title: str
    title_ko: Optional[str] = None
    description: Optional[str] = None
    event_type: str = ''
    sitelink_count: int = 0

    # 시간
    point_in_time: Optional[str] = None  # P585
    start_time: Optional[str] = None     # P580
    end_time: Optional[str] = None       # P582

    # 위치 (QID)
    location_qids: list = field(default_factory=list)  # P276
    country_qids: list = field(default_factory=list)   # P17

    # 관계
    participant_qids: list = field(default_factory=list)  # P710
    part_of_qid: Optional[str] = None    # P361


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


def get_first_claim_value(entity: dict, property_id: str) -> Optional[str]:
    """첫 번째 값만 반환"""
    values = get_claim_values(entity, property_id)
    return values[0] if values else None


def get_sitelink_count(entity: dict) -> int:
    """sitelink 수 반환"""
    return len(entity.get('sitelinks', {}))


def get_event_type(entity: dict) -> Optional[str]:
    """이벤트 타입 판별"""
    p31_values = get_claim_values(entity, 'P31')

    # 제외 타입 체크
    for qid in p31_values:
        if qid in EXCLUDED_TYPES:
            return None

    # Core 타입 체크
    for qid in p31_values:
        if qid in CORE_EVENT_TYPES:
            return CORE_EVENT_TYPES[qid]

    return None


def extract_event(entity: dict) -> Optional[ExtractedEvent]:
    """엔티티에서 이벤트 추출"""
    qid = entity.get('id', '')
    if not qid.startswith('Q'):
        return None

    # sitelink 필터
    sitelink_count = get_sitelink_count(entity)
    if sitelink_count < MIN_SITELINKS:
        return None

    # 타입 체크
    event_type = get_event_type(entity)
    if not event_type:
        return None

    # 라벨
    labels = entity.get('labels', {})
    title = labels.get('en', {}).get('value', '')
    title_ko = labels.get('ko', {}).get('value')

    if not title:
        return None

    # 설명
    descriptions = entity.get('descriptions', {})
    description = descriptions.get('en', {}).get('value')

    # 시간
    point_in_time = get_first_claim_value(entity, 'P585')
    start_time = get_first_claim_value(entity, 'P580')
    end_time = get_first_claim_value(entity, 'P582')

    # 위치
    location_qids = get_claim_values(entity, 'P276')
    country_qids = get_claim_values(entity, 'P17')

    # 관계
    participant_qids = get_claim_values(entity, 'P710')
    part_of_qid = get_first_claim_value(entity, 'P361')

    return ExtractedEvent(
        qid=qid,
        title=title,
        title_ko=title_ko,
        description=description,
        event_type=event_type,
        sitelink_count=sitelink_count,
        point_in_time=point_in_time,
        start_time=start_time,
        end_time=end_time,
        location_qids=location_qids,
        country_qids=country_qids,
        participant_qids=participant_qids,
        part_of_qid=part_of_qid,
    )


def stream_wikidata(dump_path: str, limit: int = 0):
    """Wikidata JSON 덤프 스트리밍"""
    print(f"Opening: {dump_path}")

    with open(dump_path, 'r', encoding='utf-8') as f:
        count = 0
        for line in f:
            line = line.strip()
            if not line or line in ['[', ']']:
                continue

            # 마지막 콤마 제거
            if line.endswith(','):
                line = line[:-1]

            try:
                entity = json.loads(line)
                yield entity
                count += 1

                if limit > 0 and count >= limit:
                    break

            except json.JSONDecodeError:
                continue


def main():
    global MIN_SITELINKS

    parser = argparse.ArgumentParser(description='Core 이벤트 추출')
    parser.add_argument('--output', default='events_core.jsonl', help='출력 파일')
    parser.add_argument('--dump', default=DUMP_PATH, help='덤프 파일 경로')
    parser.add_argument('--limit', type=int, default=0, help='처리할 최대 엔티티 수 (0=전체)')
    parser.add_argument('--min-sitelinks', type=int, default=10, help='최소 sitelink 수')
    args = parser.parse_args()

    MIN_SITELINKS = args.min_sitelinks

    output_path = Path(args.output)

    print(f"=== Core 이벤트 추출 ===")
    print(f"Dump: {args.dump}")
    print(f"Output: {output_path}")
    print(f"Min sitelinks: {MIN_SITELINKS}")
    print(f"Limit: {args.limit if args.limit > 0 else 'None'}")
    print(f"Event types: {len(CORE_EVENT_TYPES)}")
    print()

    if not os.path.exists(args.dump):
        print(f"ERROR: Dump file not found: {args.dump}")
        sys.exit(1)

    start_time = time.time()
    scanned = 0
    extracted = 0
    type_counts: Dict[str, int] = {}

    with open(output_path, 'w', encoding='utf-8') as out:
        for entity in stream_wikidata(args.dump, args.limit):
            scanned += 1

            if scanned % 1000000 == 0:
                elapsed = time.time() - start_time
                rate = scanned / elapsed
                print(f"Scanned: {scanned:,} | Extracted: {extracted:,} | Rate: {rate:,.0f}/s | Elapsed: {elapsed/60:.1f}m")

            event = extract_event(entity)
            if event:
                out.write(json.dumps(asdict(event), ensure_ascii=False) + '\n')
                extracted += 1
                type_counts[event.event_type] = type_counts.get(event.event_type, 0) + 1

    elapsed = time.time() - start_time

    print()
    print(f"=== 완료 ===")
    print(f"Scanned: {scanned:,}")
    print(f"Extracted: {extracted:,}")
    print(f"Time: {elapsed/60:.1f} minutes")
    print()
    print("Type distribution:")
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c:,}")


if __name__ == '__main__':
    main()
