"""
Step 1.5: 한국어/일본어 Wikipedia 매핑 추가 (1회성)

Step 1에서 생성된 QID ↔ enwiki 매핑에 kowiki, jawiki 추가.

Usage:
    python 01b_enrich_multilang_map.py
"""

import json
import sys
import time

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from config import WIKIDATA_JSON, QID_WIKI_MAP, LOG_INTERVAL

# 출력 파일
MULTILANG_MAP = QID_WIKI_MAP.parent / "qid_wiki_map_multilang.json"


def load_existing_map() -> dict:
    """기존 매핑 로드"""
    print(f"Loading existing map from {QID_WIKI_MAP}...")
    with open(QID_WIKI_MAP, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"  Loaded {len(data):,} entries")
    return data


def scan_for_multilang() -> tuple:
    """Wikidata 스캔하여 KO/JA 매핑 추출"""
    print(f"\nScanning for KO/JA Wikipedia links...")
    print(f"Input: {WIKIDATA_JSON}")

    ko_map = {}  # title -> qid
    ja_map = {}  # title -> qid
    qid_to_langs = {}  # qid -> {ko: title, ja: title}

    scanned = 0
    found_ko = 0
    found_ja = 0
    start_time = time.time()

    with open(WIKIDATA_JSON, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line in ['[', ']', '']:
                continue
            if line.endswith(','):
                line = line[:-1]

            scanned += 1

            if scanned % LOG_INTERVAL == 0:
                elapsed = time.time() - start_time
                rate = scanned / elapsed if elapsed > 0 else 0
                print(f"  Scanned: {scanned:,} | KO: {found_ko:,} | JA: {found_ja:,} | Rate: {rate:,.0f}/s")

            try:
                entity = json.loads(line)
                qid = entity.get('id')
                if not qid or not qid.startswith('Q'):
                    continue

                sitelinks = entity.get('sitelinks', {})

                ko_title = sitelinks.get('kowiki', {}).get('title')
                ja_title = sitelinks.get('jawiki', {}).get('title')

                if ko_title or ja_title:
                    qid_to_langs[qid] = {}

                if ko_title:
                    ko_map[ko_title] = qid
                    qid_to_langs[qid]['ko'] = ko_title
                    found_ko += 1

                if ja_title:
                    ja_map[ja_title] = qid
                    qid_to_langs[qid]['ja'] = ja_title
                    found_ja += 1

            except json.JSONDecodeError:
                continue

    elapsed = time.time() - start_time
    print(f"\nScan complete in {elapsed/60:.1f} min")
    print(f"  Korean Wikipedia: {found_ko:,}")
    print(f"  Japanese Wikipedia: {found_ja:,}")

    return ko_map, ja_map, qid_to_langs


def merge_and_save(existing_map: dict, ko_map: dict, ja_map: dict, qid_to_langs: dict):
    """매핑 병합 및 저장"""
    print(f"\nMerging maps...")

    # 새 구조: {qid: {en: title, ko: title, ja: title}, title_en: qid, title_ko: qid, ...}
    merged = {
        'by_qid': {},      # qid -> {en, ko, ja}
        'by_title_en': {}, # en_title -> qid
        'by_title_ko': {}, # ko_title -> qid
        'by_title_ja': {}, # ja_title -> qid
    }

    # 기존 영어 매핑 (title -> qid 형식이었음)
    for key, val in existing_map.items():
        if key.startswith('Q'):
            # qid -> title
            qid = key
            merged['by_qid'].setdefault(qid, {})['en'] = val
        else:
            # title -> qid
            merged['by_title_en'][key] = val

    # 한국어/일본어 추가
    merged['by_title_ko'] = ko_map
    merged['by_title_ja'] = ja_map

    for qid, langs in qid_to_langs.items():
        merged['by_qid'].setdefault(qid, {}).update(langs)

    # 저장
    print(f"Saving to {MULTILANG_MAP}...")
    with open(MULTILANG_MAP, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False)

    size_mb = MULTILANG_MAP.stat().st_size / 1024 / 1024
    print(f"  Size: {size_mb:.1f} MB")

    # 통계
    print("\n통계:")
    print(f"  QID entries: {len(merged['by_qid']):,}")
    print(f"  EN title mappings: {len(merged['by_title_en']):,}")
    print(f"  KO title mappings: {len(merged['by_title_ko']):,}")
    print(f"  JA title mappings: {len(merged['by_title_ja']):,}")


def main():
    print("=" * 60)
    print("Step 1.5: 다국어 Wikipedia 매핑 추가 (1회성)")
    print("=" * 60)

    # 1. 기존 매핑 로드
    existing = load_existing_map()

    # 2. Wikidata 스캔
    ko_map, ja_map, qid_to_langs = scan_for_multilang()

    # 3. 병합 및 저장
    merge_and_save(existing, ko_map, ja_map, qid_to_langs)

    print("\n" + "=" * 60)
    print("완료!")
    print("=" * 60)


if __name__ == '__main__':
    main()
