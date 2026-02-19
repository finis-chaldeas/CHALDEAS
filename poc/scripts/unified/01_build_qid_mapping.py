"""
Step 1: QID ↔ Wikipedia 매핑 생성 (다국어 지원)

Wikidata JSON에서 sitelinks (enwiki, kowiki, jawiki) 추출하여 매핑 테이블 생성.
나중에 Wikipedia 하이퍼링크 → QID 변환에 사용.

출력 구조:
{
    "by_qid": {qid: {"en": title, "ko": title, "ja": title}},
    "by_title_en": {title: qid},
    "by_title_ko": {title: qid},
    "by_title_ja": {title: qid}
}

Usage:
    python 01_build_qid_mapping.py [--limit N] [--test]
"""

import json
import sys
import time
import argparse
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from config import (
    WIKIDATA_JSON, QID_WIKI_MAP, CHECKPOINT_DIR,
    LOG_INTERVAL, CHECKPOINT_INTERVAL
)

def build_mapping(limit: int = None, test_mode: bool = False):
    """Wikidata에서 QID ↔ Wikipedia 제목 매핑 생성"""

    print("=" * 60)
    print("Step 1: QID ↔ Wikipedia 매핑 생성")
    print("=" * 60)
    print(f"Input: {WIKIDATA_JSON}")
    print(f"Output: {QID_WIKI_MAP}")
    if limit:
        print(f"Limit: {limit:,}")
    print()

    # 다국어 매핑 구조
    mapping = {
        'by_qid': {},       # qid -> {en, ko, ja}
        'by_title_en': {},  # en_title -> qid
        'by_title_ko': {},  # ko_title -> qid
        'by_title_ja': {},  # ja_title -> qid
    }

    # 통계
    scanned = 0
    stats = {'en': 0, 'ko': 0, 'ja': 0, 'any': 0}
    start_time = time.time()

    # 체크포인트에서 복구
    checkpoint_file = CHECKPOINT_DIR / "mapping_checkpoint.json"
    if checkpoint_file.exists() and not test_mode:
        print("Loading checkpoint...")
        checkpoint = json.load(open(checkpoint_file, encoding='utf-8'))
        mapping = checkpoint.get('mapping', mapping)
        scanned = checkpoint.get('scanned', 0)
        stats = checkpoint.get('stats', stats)
        print(f"  Resumed from line {scanned:,}, EN:{stats['en']:,} KO:{stats['ko']:,} JA:{stats['ja']:,}")

    try:
        with open(WIKIDATA_JSON, 'r', encoding='utf-8') as f:
            # Skip to checkpoint position
            if scanned > 0:
                print(f"Skipping to line {scanned:,}...")
                for _ in range(scanned):
                    next(f, None)

            for line in f:
                line = line.strip()
                if line in ['[', ']', '']:
                    continue
                if line.endswith(','):
                    line = line[:-1]

                scanned += 1

                # 진행률 로그
                if scanned % LOG_INTERVAL == 0:
                    elapsed = time.time() - start_time
                    rate = scanned / elapsed if elapsed > 0 else 0
                    print(f"  Scanned: {scanned:,} | EN:{stats['en']:,} KO:{stats['ko']:,} JA:{stats['ja']:,} | "
                          f"Rate: {rate:,.0f}/s")

                # 체크포인트 저장
                if scanned % CHECKPOINT_INTERVAL == 0 and not test_mode:
                    save_checkpoint(checkpoint_file, mapping, scanned, stats)

                # Limit 체크
                if limit and scanned >= limit:
                    print(f"  Reached limit: {limit:,}")
                    break

                # 파싱
                try:
                    entity = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # QID 추출
                qid = entity.get('id')
                if not qid or not qid.startswith('Q'):
                    continue

                # Wikipedia 제목 추출 (3개 언어)
                sitelinks = entity.get('sitelinks', {})
                has_any = False
                qid_langs = {}

                # 영어
                en_title = sitelinks.get('enwiki', {}).get('title')
                if en_title:
                    normalized = en_title.replace(' ', '_')
                    mapping['by_title_en'][normalized] = qid
                    if en_title != normalized:
                        mapping['by_title_en'][en_title] = qid
                    qid_langs['en'] = en_title
                    stats['en'] += 1
                    has_any = True

                # 한국어
                ko_title = sitelinks.get('kowiki', {}).get('title')
                if ko_title:
                    mapping['by_title_ko'][ko_title] = qid
                    qid_langs['ko'] = ko_title
                    stats['ko'] += 1
                    has_any = True

                # 일본어
                ja_title = sitelinks.get('jawiki', {}).get('title')
                if ja_title:
                    mapping['by_title_ja'][ja_title] = qid
                    qid_langs['ja'] = ja_title
                    stats['ja'] += 1
                    has_any = True

                if has_any:
                    mapping['by_qid'][qid] = qid_langs
                    stats['any'] += 1

    except KeyboardInterrupt:
        print("\n\nInterrupted! Saving checkpoint...")
        save_checkpoint(checkpoint_file, mapping, scanned, stats)
        return

    # 결과 저장
    elapsed = time.time() - start_time

    print()
    print(f"Saving to {QID_WIKI_MAP}...")

    with open(QID_WIKI_MAP, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False)

    # 체크포인트 삭제
    if checkpoint_file.exists():
        checkpoint_file.unlink()

    total_titles = len(mapping['by_title_en']) + len(mapping['by_title_ko']) + len(mapping['by_title_ja'])

    print()
    print("=" * 60)
    print("완료!")
    print("=" * 60)
    print(f"Scanned: {scanned:,}")
    print(f"With Wikipedia (any): {stats['any']:,}")
    print(f"  - English: {stats['en']:,}")
    print(f"  - Korean: {stats['ko']:,}")
    print(f"  - Japanese: {stats['ja']:,}")
    print(f"Total title mappings: {total_titles:,}")
    print(f"Time: {elapsed/60:.1f} min")
    print(f"Output: {QID_WIKI_MAP}")
    print(f"Size: {QID_WIKI_MAP.stat().st_size / 1024 / 1024:.1f} MB")

def save_checkpoint(path: Path, mapping: dict, scanned: int, stats: dict):
    """체크포인트 저장"""
    checkpoint = {
        'scanned': scanned,
        'mapping': mapping,
        'stats': stats
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(checkpoint, f)
    print(f"    [Checkpoint saved at {scanned:,}]")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', '-l', type=int, help='Limit lines to process')
    parser.add_argument('--test', action='store_true', help='Test mode (no checkpoint)')
    args = parser.parse_args()

    build_mapping(limit=args.limit, test_mode=args.test)
