"""
Step 2: Wikidata 전체 속성 추출

모든 엔티티 (person, location, territory, group, event)를
전체 속성과 함께 추출.

Usage:
    python 02_extract_wikidata.py [--limit N] [--test]
"""

import json
import sys
import time
import argparse
from pathlib import Path
from typing import Optional, Dict, List, Set, Any

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from config import (
    WIKIDATA_JSON, WIKIDATA_EXTRACTED, CHECKPOINT_DIR,
    PERSON_TYPES, LOCATION_TYPES, TERRITORY_TYPES,
    GROUP_TYPES, EVENT_TYPES, EXCLUDED_TYPES,
    PROPERTY_NAMES, LOG_INTERVAL, CHECKPOINT_INTERVAL
)

# ============================================
# 파싱 헬퍼
# ============================================

def parse_time_to_year(time_value: dict) -> Optional[int]:
    """Wikidata 시간 → 연도 (BCE는 음수)"""
    if not time_value:
        return None
    time_str = time_value.get('time', '')
    if not time_str:
        return None
    try:
        sign = 1 if time_str[0] == '+' else -1
        year_str = time_str[1:].split('-')[0]
        year = int(year_str)
        return sign * year if year != 0 else None
    except:
        return None

def extract_claim_value(claim: dict) -> Optional[Dict]:
    """Wikidata claim에서 값 추출"""
    mainsnak = claim.get('mainsnak', {})
    if mainsnak.get('snaktype') != 'value':
        return None

    datavalue = mainsnak.get('datavalue', {})
    vtype = datavalue.get('type')
    value = datavalue.get('value')

    if not value:
        return None

    result = {'value_type': vtype}

    if vtype == 'wikibase-entityid':
        result['value_qid'] = value.get('id')
    elif vtype == 'string':
        result['value_string'] = value
    elif vtype == 'time':
        result['value_year'] = parse_time_to_year(value)
    elif vtype == 'quantity':
        try:
            result['value_quantity'] = float(value.get('amount', 0))
        except:
            pass
    elif vtype == 'globecoordinate':
        result['value_lat'] = value.get('latitude')
        result['value_lon'] = value.get('longitude')
    elif vtype == 'monolingualtext':
        result['value_string'] = value.get('text')

    # Qualifiers
    qualifiers = claim.get('qualifiers', {})
    if 'P580' in qualifiers:
        for q in qualifiers['P580']:
            if q.get('snaktype') == 'value':
                try:
                    result['qualifier_start'] = parse_time_to_year(
                        q['datavalue']['value']
                    )
                except:
                    pass
    if 'P582' in qualifiers:
        for q in qualifiers['P582']:
            if q.get('snaktype') == 'value':
                try:
                    result['qualifier_end'] = parse_time_to_year(
                        q['datavalue']['value']
                    )
                except:
                    pass

    return result

def get_p31_types(entity: dict) -> Set[str]:
    """P31 (instance of) 값들 추출"""
    p31_qids = set()
    for claim in entity.get('claims', {}).get('P31', []):
        try:
            qid = claim['mainsnak']['datavalue']['value']['id']
            p31_qids.add(qid)
        except:
            pass
    return p31_qids

def classify_entity(p31_types: Set[str]) -> Optional[str]:
    """P31 기반 엔티티 타입 분류"""
    # 제외 타입 체크
    if p31_types & EXCLUDED_TYPES:
        return None

    # 우선순위: person > location > territory > group > event
    if p31_types & PERSON_TYPES:
        return 'person'

    if p31_types & LOCATION_TYPES:
        return 'location'

    if p31_types & TERRITORY_TYPES:
        return 'territory'

    if p31_types & GROUP_TYPES:
        return 'group'

    if p31_types & EVENT_TYPES:
        return 'event'

    return None

def get_coordinate(entity: dict) -> Optional[tuple]:
    """좌표 추출"""
    for claim in entity.get('claims', {}).get('P625', []):
        val = extract_claim_value(claim)
        if val and val.get('value_lat') is not None:
            return (val['value_lat'], val['value_lon'])
    return None

# ============================================
# 엔티티 추출
# ============================================

def extract_entity(entity: dict, entity_type: str) -> Dict:
    """엔티티에서 모든 정보 추출"""
    qid = entity.get('id')
    labels = entity.get('labels', {})
    descs = entity.get('descriptions', {})
    sitelinks = entity.get('sitelinks', {})
    claims = entity.get('claims', {})

    # 기본 정보
    result = {
        'qid': qid,
        'type': entity_type,
        'name': labels.get('en', {}).get('value', qid),
        'name_ko': labels.get('ko', {}).get('value'),
        'name_ja': labels.get('ja', {}).get('value'),
        'description': descs.get('en', {}).get('value'),
        'description_ko': descs.get('ko', {}).get('value'),
        'description_ja': descs.get('ja', {}).get('value'),
        'wikipedia_title': sitelinks.get('enwiki', {}).get('title'),
        'wikipedia_title_ko': sitelinks.get('kowiki', {}).get('title'),
        'wikipedia_title_ja': sitelinks.get('jawiki', {}).get('title'),
        # 언어별 Wikipedia 존재 여부
        'has_wiki_en': 'enwiki' in sitelinks,
        'has_wiki_ko': 'kowiki' in sitelinks,
        'has_wiki_ja': 'jawiki' in sitelinks,
    }

    # 타입별 추가 정보
    if entity_type == 'person':
        result['birth_year'] = None
        result['death_year'] = None
        result['birthplace_qid'] = None
        result['deathplace_qid'] = None

        for claim in claims.get('P569', []):
            val = extract_claim_value(claim)
            if val and val.get('value_year'):
                result['birth_year'] = val['value_year']
                break

        for claim in claims.get('P570', []):
            val = extract_claim_value(claim)
            if val and val.get('value_year'):
                result['death_year'] = val['value_year']
                break

        for claim in claims.get('P19', []):
            val = extract_claim_value(claim)
            if val and val.get('value_qid'):
                result['birthplace_qid'] = val['value_qid']
                break

        for claim in claims.get('P20', []):
            val = extract_claim_value(claim)
            if val and val.get('value_qid'):
                result['deathplace_qid'] = val['value_qid']
                break

    elif entity_type == 'location':
        coord = get_coordinate(entity)
        if coord:
            result['latitude'] = coord[0]
            result['longitude'] = coord[1]
        else:
            result['latitude'] = None
            result['longitude'] = None

        # Parent location
        for claim in claims.get('P131', []):
            val = extract_claim_value(claim)
            if val and val.get('value_qid'):
                result['parent_qid'] = val['value_qid']
                break

    elif entity_type == 'territory':
        result['founded_year'] = None
        result['dissolved_year'] = None

        for claim in claims.get('P571', []):
            val = extract_claim_value(claim)
            if val and val.get('value_year'):
                result['founded_year'] = val['value_year']
                break

        for claim in claims.get('P576', []):
            val = extract_claim_value(claim)
            if val and val.get('value_year'):
                result['dissolved_year'] = val['value_year']
                break

    elif entity_type == 'event':
        result['date_start'] = None
        result['date_end'] = None

        # Point in time
        for claim in claims.get('P585', []):
            val = extract_claim_value(claim)
            if val and val.get('value_year'):
                result['date_start'] = val['value_year']
                break

        # Or start/end time
        if result['date_start'] is None:
            for claim in claims.get('P580', []):
                val = extract_claim_value(claim)
                if val and val.get('value_year'):
                    result['date_start'] = val['value_year']
                    break

            for claim in claims.get('P582', []):
                val = extract_claim_value(claim)
                if val and val.get('value_year'):
                    result['date_end'] = val['value_year']
                    break

    # 모든 속성 추출
    properties = []
    for prop, claim_list in claims.items():
        prop_name = PROPERTY_NAMES.get(prop, prop)

        for claim in claim_list:
            val = extract_claim_value(claim)
            if val:
                val['property'] = prop
                val['property_name'] = prop_name
                properties.append(val)

    result['properties'] = properties

    return result

# ============================================
# 메인 추출
# ============================================

def extract_all(limit: int = None, test_mode: bool = False):
    """Wikidata에서 모든 엔티티 추출"""

    print("=" * 60)
    print("Step 2: Wikidata 전체 속성 추출")
    print("=" * 60)
    print(f"Input: {WIKIDATA_JSON}")
    print(f"Output: {WIKIDATA_EXTRACTED}")
    if limit:
        print(f"Limit: {limit:,}")
    print()

    # 통계
    counts = {
        'person': 0, 'location': 0, 'territory': 0,
        'group': 0, 'event': 0, 'properties': 0
    }
    scanned = 0
    start_time = time.time()

    # 체크포인트 복구
    checkpoint_file = CHECKPOINT_DIR / "extract_checkpoint.json"
    resume_line = 0

    if checkpoint_file.exists() and not test_mode:
        print("Loading checkpoint...")
        checkpoint = json.load(open(checkpoint_file, encoding='utf-8'))
        counts = checkpoint.get('counts', counts)
        resume_line = checkpoint.get('scanned', 0)
        print(f"  Resuming from line {resume_line:,}")
        print(f"  Previous counts: {counts}")

    # 출력 파일 열기 (append if resuming)
    mode = 'a' if resume_line > 0 else 'w'

    try:
        with open(WIKIDATA_JSON, 'r', encoding='utf-8') as f_in:
            with open(WIKIDATA_EXTRACTED, mode, encoding='utf-8') as f_out:

                # Skip to checkpoint
                if resume_line > 0:
                    print(f"Skipping to line {resume_line:,}...")
                    for _ in range(resume_line):
                        next(f_in, None)
                    scanned = resume_line

                for line in f_in:
                    line = line.strip()
                    if line in ['[', ']', '']:
                        continue
                    if line.endswith(','):
                        line = line[:-1]

                    scanned += 1

                    # 로그
                    if scanned % LOG_INTERVAL == 0:
                        elapsed = time.time() - start_time
                        rate = (scanned - resume_line) / elapsed if elapsed > 0 else 0
                        total = sum(counts[k] for k in ['person', 'location', 'territory', 'group', 'event'])
                        print(f"  Scanned: {scanned:,} | Extracted: {total:,} | "
                              f"Props: {counts['properties']:,} | Rate: {rate:,.0f}/s")

                    # 체크포인트
                    if scanned % CHECKPOINT_INTERVAL == 0 and not test_mode:
                        save_checkpoint(checkpoint_file, counts, scanned)

                    # Limit
                    if limit and scanned >= limit:
                        print(f"  Reached limit: {limit:,}")
                        break

                    # 파싱
                    try:
                        entity = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # 타입 분류
                    p31_types = get_p31_types(entity)
                    entity_type = classify_entity(p31_types)

                    if not entity_type:
                        continue

                    # Location은 좌표 필수
                    if entity_type == 'location':
                        if not get_coordinate(entity):
                            continue

                    # 추출
                    extracted = extract_entity(entity, entity_type)
                    counts[entity_type] += 1
                    counts['properties'] += len(extracted.get('properties', []))

                    # 저장
                    f_out.write(json.dumps(extracted, ensure_ascii=False) + '\n')

    except KeyboardInterrupt:
        print("\n\nInterrupted! Saving checkpoint...")
        save_checkpoint(checkpoint_file, counts, scanned)
        return

    # 완료
    elapsed = time.time() - start_time

    if checkpoint_file.exists():
        checkpoint_file.unlink()

    print()
    print("=" * 60)
    print("완료!")
    print("=" * 60)
    print(f"Scanned: {scanned:,}")
    print(f"Extracted:")
    for k in ['person', 'location', 'territory', 'group', 'event']:
        print(f"  {k}: {counts[k]:,}")
    print(f"Total properties: {counts['properties']:,}")
    print(f"Time: {elapsed/60:.1f} min")
    print(f"Output: {WIKIDATA_EXTRACTED}")
    print(f"Size: {WIKIDATA_EXTRACTED.stat().st_size / 1024 / 1024:.1f} MB")

def save_checkpoint(path: Path, counts: dict, scanned: int):
    checkpoint = {'scanned': scanned, 'counts': counts}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(checkpoint, f)
    print(f"    [Checkpoint saved at {scanned:,}]")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', '-l', type=int, help='Limit lines')
    parser.add_argument('--test', action='store_true', help='Test mode')
    args = parser.parse_args()

    extract_all(limit=args.limit, test_mode=args.test)
