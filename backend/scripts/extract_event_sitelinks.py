"""
Phase 1: Wikidata 덤프에서 이벤트 sitelinks + 좌표 추출

DB에 있는 28K 이벤트의 wikidata_id를 기준으로
로컬 Wikidata 덤프를 스캔하여 추출:
  - sitelinks.enwiki.title (Wikipedia 문서 제목)
  - sitelinks.kowiki.title (한국어 Wikipedia)
  - sitelinks.jawiki.title (일본어 Wikipedia)
  - claims.P625 (좌표)
  - claims.P276 (location QID)

Usage:
    python extract_event_sitelinks.py
    python extract_event_sitelinks.py --limit 1000000  # 테스트 (첫 100만 엔티티)
"""

import json
import sys
import os
import time
import argparse
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 경로
DUMP_PATH = "E:/wikidata/latest-all.json"
OUTPUT_DIR = Path("C:/Projects/Chaldeas/data/compact_export")
OUTPUT_FILE = OUTPUT_DIR / "event_sitelinks.jsonl"

# DB 연결
DB_URL = "postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas"


def load_event_qids():
    """DB에서 모든 이벤트의 wikidata_id 로드"""
    import psycopg2

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT id, wikidata_id FROM events WHERE wikidata_id IS NOT NULL")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    qid_to_event_id = {}
    for event_id, wikidata_id in rows:
        qid_to_event_id[wikidata_id] = event_id

    return qid_to_event_id


def extract_coordinate(entity: dict):
    """P625 (coordinate location) 추출"""
    claims = entity.get('claims', {}).get('P625', [])
    for claim in claims:
        mainsnak = claim.get('mainsnak', {})
        if mainsnak.get('snaktype') != 'value':
            continue
        datavalue = mainsnak.get('datavalue', {})
        if datavalue.get('type') == 'globecoordinate':
            coord = datavalue.get('value', {})
            lat = coord.get('latitude')
            lng = coord.get('longitude')
            if lat is not None and lng is not None:
                return {'latitude': lat, 'longitude': lng}
    return None


def extract_location_qids(entity: dict):
    """P276 (location) QID 추출"""
    qids = []
    claims = entity.get('claims', {}).get('P276', [])
    for claim in claims:
        mainsnak = claim.get('mainsnak', {})
        if mainsnak.get('snaktype') != 'value':
            continue
        datavalue = mainsnak.get('datavalue', {})
        if datavalue.get('type') == 'wikibase-entityid':
            qid = datavalue.get('value', {}).get('id')
            if qid:
                qids.append(qid)
    return qids


def extract_sitelinks(entity: dict):
    """sitelinks에서 en/ko/ja wiki 제목 추출"""
    sitelinks = entity.get('sitelinks', {})
    result = {}

    for site_key, lang_key in [('enwiki', 'en'), ('kowiki', 'ko'), ('jawiki', 'ja')]:
        if site_key in sitelinks:
            result[lang_key] = sitelinks[site_key].get('title')

    return result


def main():
    parser = argparse.ArgumentParser(description='Phase 1: Wikidata 덤프에서 이벤트 sitelinks 추출')
    parser.add_argument('--dump', default=DUMP_PATH, help='Wikidata 덤프 경로')
    parser.add_argument('--output', default=str(OUTPUT_FILE), help='출력 파일')
    parser.add_argument('--limit', type=int, default=0, help='스캔할 최대 엔티티 수 (0=전체)')
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("=== Phase 1: Wikidata 덤프에서 sitelinks 추출 ===")
    print(f"  Dump: {args.dump}")
    print(f"  Output: {output_path}")
    print()

    # DB에서 이벤트 QID 로드
    print("DB에서 이벤트 QID 로드 중...")
    qid_to_event_id = load_event_qids()
    target_qids = set(qid_to_event_id.keys())
    print(f"  대상 이벤트: {len(target_qids):,}개")
    print()

    if not os.path.exists(args.dump):
        print(f"ERROR: 덤프 파일 없음: {args.dump}")
        sys.exit(1)

    file_size_gb = os.path.getsize(args.dump) / (1024**3)
    print(f"  덤프 크기: {file_size_gb:.1f} GB")
    print()

    start_time = time.time()
    scanned = 0
    found = 0
    with_enwiki = 0
    with_coords = 0
    with_location = 0

    with open(output_path, 'w', encoding='utf-8') as out:
        with open(args.dump, 'r', encoding='utf-8') as f:
            for line in f:
                scanned += 1

                # 빠른 QID 추출 (JSON 파싱 없이)
                # Wikidata 라인 형식: {"type":"item","id":"Q12345",...}
                # "id":" 패턴은 항상 처음 100자 내에 있음
                id_pos = line.find('"id":"', 0, 100)
                if id_pos == -1:
                    continue

                qid_start = id_pos + 6
                qid_end = line.find('"', qid_start)
                if qid_end == -1:
                    continue

                qid = line[qid_start:qid_end]
                if qid not in target_qids:
                    if scanned % 2000000 == 0:
                        elapsed = time.time() - start_time
                        rate = scanned / elapsed if elapsed > 0 else 0
                        remaining = len(target_qids) - found
                        print(f"  스캔: {scanned:,} | 발견: {found:,}/{len(target_qids):,} | "
                              f"속도: {rate:,.0f}/s | 경과: {elapsed/60:.1f}분 | 남은: {remaining:,}")
                    if args.limit > 0 and scanned >= args.limit:
                        break
                    continue

                # 매칭된 QID — JSON 파싱
                stripped = line.strip()
                if stripped.endswith(','):
                    stripped = stripped[:-1]

                try:
                    entity = json.loads(stripped)
                except json.JSONDecodeError:
                    continue

                # 매칭! 데이터 추출
                found += 1
                event_id = qid_to_event_id[qid]

                sitelinks = extract_sitelinks(entity)
                coordinate = extract_coordinate(entity)
                location_qids = extract_location_qids(entity)

                record = {
                    'qid': qid,
                    'event_id': event_id,
                    'sitelinks': sitelinks,
                    'coordinate': coordinate,
                    'location_qids': location_qids,
                    'sitelink_count': len(entity.get('sitelinks', {})),
                }

                out.write(json.dumps(record, ensure_ascii=False) + '\n')

                if sitelinks.get('en'):
                    with_enwiki += 1
                if coordinate:
                    with_coords += 1
                if location_qids:
                    with_location += 1

                # 진행 출력
                if found % 500 == 0 or found == len(target_qids):
                    elapsed = time.time() - start_time
                    rate = scanned / elapsed if elapsed > 0 else 0
                    print(f"  스캔: {scanned:,} | 발견: {found:,}/{len(target_qids):,} | "
                          f"enwiki: {with_enwiki} | coords: {with_coords} | "
                          f"속도: {rate:,.0f}/s | 경과: {elapsed/60:.1f}분")

                # 모든 대상을 찾았으면 중단
                if found >= len(target_qids):
                    print(f"\n  모든 대상 이벤트를 찾았습니다! 스캔 중단.")
                    break

                if args.limit > 0 and scanned >= args.limit:
                    break

    elapsed = time.time() - start_time

    print()
    print("=== Phase 1 완료 ===")
    print(f"  스캔 엔티티: {scanned:,}")
    print(f"  발견 이벤트: {found:,} / {len(target_qids):,}")
    print(f"  enwiki sitelink: {with_enwiki:,} ({100*with_enwiki/max(found,1):.1f}%)")
    print(f"  좌표 (P625): {with_coords:,} ({100*with_coords/max(found,1):.1f}%)")
    print(f"  위치 QID (P276): {with_location:,} ({100*with_location/max(found,1):.1f}%)")
    print(f"  소요 시간: {elapsed/60:.1f}분")
    print(f"  출력 파일: {output_path}")


if __name__ == '__main__':
    main()
