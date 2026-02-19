"""
Step 2.5: 기존 추출 데이터에 한국어/일본어 정보 추가 (1회성)

Step 2에서 추출된 데이터에 KO/JA 이름, 설명, Wikipedia 링크 추가.
Wikidata JSON을 다시 스캔하여 기존 QID에 대해 다국어 정보 병합.

Usage:
    python 02b_enrich_multilang.py
"""

import json
import sys
import time
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from config import WIKIDATA_JSON, WIKIDATA_EXTRACTED, LOG_INTERVAL

# 출력 파일
ENRICHED_OUTPUT = WIKIDATA_EXTRACTED.parent / "wikidata_full_multilang.jsonl"


def load_existing_qids() -> set:
    """기존 추출 데이터에서 QID 목록 로드"""
    print("Loading existing QIDs from Step 2 output...")
    qids = set()

    with open(WIKIDATA_EXTRACTED, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entity = json.loads(line.strip())
                qids.add(entity['qid'])
            except:
                pass

    print(f"  Loaded {len(qids):,} QIDs")
    return qids


def extract_multilang_info(entity: dict) -> dict:
    """엔티티에서 다국어 정보만 추출"""
    labels = entity.get('labels', {})
    descs = entity.get('descriptions', {})
    sitelinks = entity.get('sitelinks', {})

    return {
        'qid': entity.get('id'),
        'name_ja': labels.get('ja', {}).get('value'),
        'description_ja': descs.get('ja', {}).get('value'),
        'wikipedia_title_ko': sitelinks.get('kowiki', {}).get('title'),
        'wikipedia_title_ja': sitelinks.get('jawiki', {}).get('title'),
        'has_wiki_en': 'enwiki' in sitelinks,
        'has_wiki_ko': 'kowiki' in sitelinks,
        'has_wiki_ja': 'jawiki' in sitelinks,
    }


def scan_wikidata_for_multilang(target_qids: set) -> dict:
    """Wikidata JSON 스캔하여 대상 QID의 다국어 정보 추출"""
    print(f"\nScanning Wikidata for {len(target_qids):,} QIDs...")
    print(f"Input: {WIKIDATA_JSON}")

    multilang_data = {}
    scanned = 0
    found = 0
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
                print(f"  Scanned: {scanned:,} | Found: {found:,} | Rate: {rate:,.0f}/s")

            try:
                entity = json.loads(line)
                qid = entity.get('id')

                if qid in target_qids:
                    multilang_data[qid] = extract_multilang_info(entity)
                    found += 1

                    # 모두 찾으면 조기 종료
                    if found >= len(target_qids):
                        print(f"  Found all {found:,} QIDs!")
                        break

            except json.JSONDecodeError:
                continue

    elapsed = time.time() - start_time
    print(f"\nScan complete: {scanned:,} lines, {found:,} found in {elapsed/60:.1f} min")

    return multilang_data


def merge_and_write(multilang_data: dict):
    """기존 데이터와 병합하여 새 파일 작성"""
    print(f"\nMerging and writing to {ENRICHED_OUTPUT}...")

    merged = 0
    total = 0

    with open(WIKIDATA_EXTRACTED, 'r', encoding='utf-8') as f_in:
        with open(ENRICHED_OUTPUT, 'w', encoding='utf-8') as f_out:
            for line in f_in:
                try:
                    entity = json.loads(line.strip())
                    qid = entity['qid']
                    total += 1

                    # 다국어 정보 병합
                    if qid in multilang_data:
                        ml = multilang_data[qid]
                        entity['name_ja'] = ml.get('name_ja')
                        entity['description_ja'] = ml.get('description_ja')
                        entity['wikipedia_title_ko'] = ml.get('wikipedia_title_ko')
                        entity['wikipedia_title_ja'] = ml.get('wikipedia_title_ja')
                        entity['has_wiki_en'] = ml.get('has_wiki_en', False)
                        entity['has_wiki_ko'] = ml.get('has_wiki_ko', False)
                        entity['has_wiki_ja'] = ml.get('has_wiki_ja', False)
                        merged += 1
                    else:
                        # 다국어 정보 없으면 기본값
                        entity.setdefault('name_ja', None)
                        entity.setdefault('description_ja', None)
                        entity.setdefault('wikipedia_title_ko', None)
                        entity.setdefault('wikipedia_title_ja', None)
                        entity.setdefault('has_wiki_en', bool(entity.get('wikipedia_title')))
                        entity.setdefault('has_wiki_ko', False)
                        entity.setdefault('has_wiki_ja', False)

                    f_out.write(json.dumps(entity, ensure_ascii=False) + '\n')

                except Exception as e:
                    continue

    print(f"  Total: {total:,}, Merged: {merged:,}")


def print_stats():
    """결과 통계 출력"""
    print("\n" + "=" * 60)
    print("통계")
    print("=" * 60)

    tier_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    lang_counts = {'en': 0, 'ko': 0, 'ja': 0}

    with open(ENRICHED_OUTPUT, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                e = json.loads(line.strip())
                has_en = e.get('has_wiki_en', False)
                has_ko = e.get('has_wiki_ko', False)
                has_ja = e.get('has_wiki_ja', False)

                if has_en: lang_counts['en'] += 1
                if has_ko: lang_counts['ko'] += 1
                if has_ja: lang_counts['ja'] += 1

                # Tier 분류
                count = sum([has_en, has_ko, has_ja])
                if count == 3:
                    tier_counts[1] += 1
                elif count == 2 and has_en:
                    tier_counts[2] += 1
                elif count == 1 and has_en:
                    tier_counts[3] += 1
                elif count >= 1:
                    tier_counts[4] += 1
                else:
                    tier_counts[5] += 1
            except:
                pass

    print("\n언어별 Wikipedia 보유:")
    print(f"  영어: {lang_counts['en']:,}")
    print(f"  한국어: {lang_counts['ko']:,}")
    print(f"  일본어: {lang_counts['ja']:,}")

    print("\nTier 분류:")
    print(f"  Tier 1 (EN+KO+JA): {tier_counts[1]:,}")
    print(f"  Tier 2 (EN+1):     {tier_counts[2]:,}")
    print(f"  Tier 3 (EN only):  {tier_counts[3]:,}")
    print(f"  Tier 4 (KO/JA):    {tier_counts[4]:,}")
    print(f"  Tier 5 (None):     {tier_counts[5]:,}")

    print(f"\nOutput: {ENRICHED_OUTPUT}")
    print(f"Size: {ENRICHED_OUTPUT.stat().st_size / 1024 / 1024:.1f} MB")


def main():
    print("=" * 60)
    print("Step 2.5: 다국어 정보 보강 (1회성)")
    print("=" * 60)

    # 1. 기존 QID 로드
    qids = load_existing_qids()

    # 2. Wikidata 스캔하여 다국어 정보 추출
    multilang = scan_wikidata_for_multilang(qids)

    # 3. 병합 및 저장
    merge_and_write(multilang)

    # 4. 통계 출력
    print_stats()

    print("\n" + "=" * 60)
    print("완료!")
    print("=" * 60)


if __name__ == '__main__':
    main()
