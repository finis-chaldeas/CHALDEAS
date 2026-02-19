"""
Wikidata 덤프에서 위치 엔티티 추출

이벤트 임포트 전에 실행하여 위치 데이터를 미리 준비
SPARQL 쿼리 없이 로컬에서 위치 정보 추출

Usage:
    python extract_locations_from_dump.py --output locations.jsonl
    python extract_locations_from_dump.py --output locations.jsonl --limit 10000
"""

import bz2
import json
import argparse
import sys
import time
from typing import Optional, Dict, Any, Set

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 위치 타입 QID들 (P31 instance of)
LOCATION_TYPE_QIDS = {
    # 도시/정착지
    'Q515': 'city',
    'Q1549591': 'big_city',
    'Q1637706': 'city_with_more_than_1m',
    'Q208511': 'global_city',
    'Q3957': 'town',
    'Q532': 'village',
    'Q486972': 'settlement',
    'Q123705': 'neighborhood',

    # 국가/지역
    'Q6256': 'country',
    'Q3024240': 'historical_country',
    'Q417175': 'sovereign_state',
    'Q7275': 'state',
    'Q35657': 'territory',
    'Q82794': 'region',
    'Q15642541': 'administrative_region',

    # 자연 지형
    'Q23442': 'island',
    'Q34763': 'peninsula',
    'Q8502': 'mountain',
    'Q46831': 'mountain_range',
    'Q4022': 'river',
    'Q23397': 'lake',
    'Q9430': 'ocean',
    'Q165': 'sea',
    'Q39816': 'valley',
    'Q8514': 'desert',
    'Q35509': 'cave',

    # 역사적 장소
    'Q839954': 'archaeological_site',
    'Q2065736': 'cultural_site',
    'Q751876': 'castle',
    'Q57821': 'fortification',
    'Q16970': 'church_building',
    'Q32815': 'mosque',
    'Q34627': 'synagogue',
    'Q44613': 'monastery',
    'Q34038': 'waterfall',

    # 전장/역사적 위치
    'Q4895508': 'battlefield',

    # 대륙
    'Q5107': 'continent',
}

# 추가로 추출할 중요 위치들 (역사적 지역)
IMPORTANT_LOCATION_QIDS = {
    'Q37707',  # Holy Land
    'Q12546',  # Levant
    'Q11708',  # Anatolia
    'Q7204',   # Middle East
    'Q27509',  # Near East
    'Q11767',  # Mesopotamia
    'Q19828',  # Balkans
    'Q12837',  # Iberian Peninsula
    'Q4412',   # Mediterranean Sea
}


def get_label(entity: dict, lang: str = 'en') -> Optional[str]:
    """엔티티에서 레이블 추출"""
    labels = entity.get('labels', {})
    if lang in labels:
        return labels[lang].get('value')
    # 영어 없으면 첫 번째 사용
    if labels:
        return list(labels.values())[0].get('value')
    return None


def get_coordinates(entity: dict) -> Optional[tuple]:
    """P625 좌표 추출"""
    claims = entity.get('claims', {})
    if 'P625' not in claims:
        return None

    for claim in claims['P625']:
        mainsnak = claim.get('mainsnak', {})
        datavalue = mainsnak.get('datavalue', {})
        value = datavalue.get('value', {})

        lat = value.get('latitude')
        lng = value.get('longitude')

        if lat is not None and lng is not None:
            return (lat, lng)

    return None


def get_instance_of(entity: dict) -> Set[str]:
    """P31 instance of QID들 추출"""
    result = set()
    claims = entity.get('claims', {})

    if 'P31' not in claims:
        return result

    for claim in claims['P31']:
        mainsnak = claim.get('mainsnak', {})
        datavalue = mainsnak.get('datavalue', {})
        value = datavalue.get('value', {})
        qid = value.get('id')
        if qid:
            result.add(qid)

    return result


def get_country(entity: dict) -> Optional[str]:
    """P17 country QID 추출"""
    claims = entity.get('claims', {})

    if 'P17' not in claims:
        return None

    for claim in claims['P17']:
        mainsnak = claim.get('mainsnak', {})
        datavalue = mainsnak.get('datavalue', {})
        value = datavalue.get('value', {})
        return value.get('id')

    return None


def get_located_in(entity: dict) -> Optional[str]:
    """P131 located in administrative entity QID 추출"""
    claims = entity.get('claims', {})

    if 'P131' not in claims:
        return None

    for claim in claims['P131']:
        mainsnak = claim.get('mainsnak', {})
        datavalue = mainsnak.get('datavalue', {})
        value = datavalue.get('value', {})
        return value.get('id')

    return None


def is_location_entity(entity: dict, important_qids: set) -> tuple:
    """엔티티가 위치인지 확인

    Returns:
        (is_location, location_type)
    """
    if entity.get('type') != 'item':
        return False, None

    qid = entity.get('id')

    # 중요 위치 목록에 있으면 무조건 포함
    if qid in important_qids:
        return True, 'region'

    # P31 (instance of) 확인
    instance_of = get_instance_of(entity)

    for type_qid, type_name in LOCATION_TYPE_QIDS.items():
        if type_qid in instance_of:
            return True, type_name

    return False, None


def extract_location(entity: dict, location_type: str) -> Optional[dict]:
    """엔티티에서 위치 데이터 추출"""
    qid = entity.get('id')

    name = get_label(entity, 'en')
    if not name:
        return None

    name_ko = get_label(entity, 'ko')
    coords = get_coordinates(entity)
    country_qid = get_country(entity)
    parent_qid = get_located_in(entity) or country_qid

    # 좌표 없어도 일단 추출 (상위 위치에서 상속 가능)
    return {
        'qid': qid,
        'name': name,
        'name_ko': name_ko,
        'latitude': coords[0] if coords else None,
        'longitude': coords[1] if coords else None,
        'location_type': location_type,
        'country_qid': country_qid,
        'parent_qid': parent_qid,
    }


def extract_locations(dump_path: str, output_path: str, limit: int = None):
    """덤프에서 위치 추출"""
    print(f"=== 위치 추출 ===")
    print(f"덤프: {dump_path}")
    print(f"출력: {output_path}")
    print(f"제한: {limit or '없음'}")
    print()

    start_time = time.time()
    entity_count = 0
    location_count = 0
    with_coords = 0

    # 중요 위치 QID 세트
    important_qids = IMPORTANT_LOCATION_QIDS.copy()

    with bz2.open(dump_path, 'rt', encoding='utf-8') as f_in, \
         open(output_path, 'w', encoding='utf-8') as f_out:

        for line in f_in:
            entity_count += 1

            if limit and location_count >= limit:
                break

            # 진행 상황 출력
            if entity_count % 100000 == 0:
                elapsed = time.time() - start_time
                rate = entity_count / elapsed if elapsed > 0 else 0
                print(f"  처리: {entity_count:,} 엔티티 | 위치: {location_count:,} | {rate:.0f}/s")

            # JSON 파싱
            line = line.strip()
            if not line or line in ['[', ']']:
                continue
            if line.endswith(','):
                line = line[:-1]

            try:
                entity = json.loads(line)
            except json.JSONDecodeError:
                continue

            # 위치 엔티티인지 확인
            is_loc, loc_type = is_location_entity(entity, important_qids)
            if not is_loc:
                continue

            # 위치 데이터 추출
            location = extract_location(entity, loc_type)
            if not location:
                continue

            # 저장
            f_out.write(json.dumps(location, ensure_ascii=False) + '\n')
            location_count += 1

            if location['latitude'] is not None:
                with_coords += 1

    elapsed = time.time() - start_time

    print()
    print(f"=== 완료 ===")
    print(f"처리: {entity_count:,} 엔티티")
    print(f"추출: {location_count:,} 위치")
    print(f"좌표 있음: {with_coords:,} ({100*with_coords/location_count:.1f}%)" if location_count else "")
    print(f"소요 시간: {elapsed:.1f}초")


def main():
    parser = argparse.ArgumentParser(description='Extract locations from Wikidata dump')
    parser.add_argument('--dump', default='C:/Projects/Chaldeas/data/wikidata/latest-all.json.bz2',
                        help='Wikidata 덤프 파일 경로')
    parser.add_argument('--output', required=True, help='출력 JSONL 파일')
    parser.add_argument('--limit', type=int, help='추출 개수 제한')

    args = parser.parse_args()

    extract_locations(args.dump, args.output, args.limit)


if __name__ == '__main__':
    main()
