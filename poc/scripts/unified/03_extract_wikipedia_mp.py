"""
Step 3: Wikipedia 본문 + 하이퍼링크 추출 (멀티프로세싱)

Wikidata에서 추출한 엔티티들의 Wikipedia 문서를 가져와서
본문과 하이퍼링크 추출. 멀티프로세싱으로 병렬 처리.

Usage:
    python 03_extract_wikipedia_mp.py [--workers N] [--limit N] [--resume]
"""

import json
import sys
import time
import re
import argparse
from pathlib import Path
from typing import Optional, Dict, List
from multiprocessing import Pool, cpu_count, Manager
import os

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from config import (
    WIKIPEDIA_ZIM, WIKIDATA_EXTRACTED, WIKIPEDIA_EXTRACTED,
    QID_WIKI_MAP, CHECKPOINT_DIR
)

# 체크포인트 파일
CHECKPOINT_FILE = CHECKPOINT_DIR / "wiki_extract_checkpoint.json"
OUTPUT_PARTIAL = WIKIPEDIA_EXTRACTED.parent / "wikipedia_partial.jsonl"

# 전역 변수 (워커용)
_zim = None
_title_to_qid = None


def init_worker(zim_path: str, mapping_path: str):
    """워커 초기화 - 각 프로세스에서 ZIM과 매핑 로드"""
    global _zim, _title_to_qid
    from libzim.reader import Archive
    _zim = Archive(zim_path)
    # 각 워커가 직접 매핑 파일 로드
    with open(mapping_path, 'r', encoding='utf-8') as f:
        _title_to_qid = json.load(f)


def extract_one(entity: dict) -> Optional[Dict]:
    """단일 엔티티의 Wikipedia 추출"""
    global _zim, _title_to_qid
    from bs4 import BeautifulSoup

    title = entity.get('wikipedia_title')
    if not title:
        return None

    # ZIM에서 문서 찾기
    paths = [
        f"A/{title.replace(' ', '_')}",
        f"{title.replace(' ', '_')}",
    ]

    entry = None
    for path in paths:
        try:
            entry = _zim.get_entry_by_path(path)
            break
        except:
            continue

    if not entry:
        return None

    try:
        html = entry.get_item().content.tobytes().decode('utf-8')
    except:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    # 링크 추출
    links = []
    mentions = []
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        text = a.get_text()

        if href.startswith('http') or href.startswith('#') or ':' in href:
            continue
        if not href or href.startswith('javascript'):
            continue

        target = href
        if text and target:
            links.append({'text': text[:200], 'target': target})

            # QID 변환
            target_qid = _title_to_qid.get(target) or \
                        _title_to_qid.get(target.replace('_', ' '))
            if target_qid:
                mentions.append({
                    'target_qid': target_qid,
                    'link_text': text[:200],
                })

    # 텍스트 추출
    for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
        tag.decompose()

    text = soup.get_text(separator=' ', strip=True)
    text = re.sub(r'\s+', ' ', text)

    return {
        'qid': entity['qid'],
        'type': entity['type'],
        'name': entity['name'],
        'wikipedia_title': title,
        'content_raw': text[:100000],
        'word_count': len(text.split()),
        'link_count': len(links),
        'mentions': mentions
    }


def save_checkpoint(processed_qids: set, stats: dict):
    """체크포인트 저장"""
    checkpoint = {
        'processed_qids': list(processed_qids),
        'stats': stats,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump(checkpoint, f)


def load_checkpoint() -> tuple:
    """체크포인트 로드"""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return set(data.get('processed_qids', [])), data.get('stats', {})
    return set(), {}


def extract_all_wikipedia_mp(workers: int = None, limit: int = None, resume: bool = False):
    """Wikipedia 멀티프로세싱 추출"""

    print("=" * 60)
    print("Step 3: Wikipedia 본문 + 하이퍼링크 추출 (멀티프로세싱)")
    print("=" * 60)

    # 의존성 체크
    try:
        from libzim.reader import Archive
        from bs4 import BeautifulSoup
    except ImportError as e:
        print(f"Error: {e}")
        print("Install: pip install libzim beautifulsoup4")
        return

    workers = workers or min(4, max(1, cpu_count() - 1))  # 최대 4개 워커 (메모리 절약)
    print(f"Workers: {workers}")

    # QID → Wikipedia 매핑 로드
    print(f"\nLoading QID mapping from {QID_WIKI_MAP}...")
    if not QID_WIKI_MAP.exists():
        print("  Error: QID mapping not found.")
        return

    with open(QID_WIKI_MAP, 'r', encoding='utf-8') as f:
        title_to_qid = json.load(f)
    print(f"  Loaded {len(title_to_qid):,} mappings")

    # 체크포인트 로드
    processed_qids = set()
    stats = {'extracted': 0, 'failed': 0, 'total_words': 0, 'total_links': 0}

    if resume and CHECKPOINT_FILE.exists():
        processed_qids, stats = load_checkpoint()
        print(f"\nResuming from checkpoint: {len(processed_qids):,} already processed")

    # Wikidata 추출 결과 로드
    print(f"\nLoading extracted entities from {WIKIDATA_EXTRACTED}...")
    entities_with_wiki = []
    with open(WIKIDATA_EXTRACTED, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entity = json.loads(line)
                if entity.get('wikipedia_title'):
                    qid = entity['qid']
                    if qid not in processed_qids:
                        entities_with_wiki.append({
                            'qid': qid,
                            'type': entity['type'],
                            'name': entity['name'],
                            'wikipedia_title': entity['wikipedia_title']
                        })
            except:
                continue

    total_entities = len(entities_with_wiki) + len(processed_qids)
    print(f"  Total with Wikipedia: {total_entities:,}")
    print(f"  To process: {len(entities_with_wiki):,}")

    if limit:
        entities_with_wiki = entities_with_wiki[:limit]
        print(f"  Limited to: {limit}")

    if not entities_with_wiki:
        print("\nNothing to process!")
        return

    # 출력 파일 모드
    output_mode = 'a' if resume and OUTPUT_PARTIAL.exists() else 'w'

    # 멀티프로세싱 실행 - 단일 Pool 사용
    print(f"\nExtracting with {workers} workers...")
    print("  (Workers loading mapping file - may take a minute...)")
    start_time = time.time()

    batch_size = 5000  # 큰 배치로 효율성 향상

    with open(OUTPUT_PARTIAL, output_mode, encoding='utf-8') as f_out:
        with Pool(
            processes=workers,
            initializer=init_worker,
            initargs=(str(WIKIPEDIA_ZIM), str(QID_WIKI_MAP))
        ) as pool:

            # imap_unordered로 스트리밍 처리
            processed_count = 0
            entity_iter = iter(entities_with_wiki)

            for result in pool.imap_unordered(extract_one, entities_with_wiki, chunksize=100):
                processed_count += 1

                if result:
                    processed_qids.add(result['qid'])
                    f_out.write(json.dumps(result, ensure_ascii=False) + '\n')
                    stats['extracted'] += 1
                    stats['total_words'] += result['word_count']
                    stats['total_links'] += result['link_count']
                else:
                    stats['failed'] += 1

                # 진행률 출력
                if processed_count % 1000 == 0:
                    elapsed = time.time() - start_time
                    rate = processed_count / elapsed if elapsed > 0 else 0
                    remaining = len(entities_with_wiki) - processed_count
                    eta = remaining / rate if rate > 0 else 0

                    print(f"  Processed: {processed_count:,}/{len(entities_with_wiki):,} | "
                          f"Extracted: {stats['extracted']:,} | "
                          f"Rate: {rate:.1f}/s | "
                          f"ETA: {eta/3600:.1f}h")

                # 체크포인트 저장 (10000개마다)
                if processed_count % 10000 == 0:
                    save_checkpoint(processed_qids, stats)
                    f_out.flush()

    # 완료 후 파일 이동
    if OUTPUT_PARTIAL.exists():
        OUTPUT_PARTIAL.rename(WIKIPEDIA_EXTRACTED)

    # 체크포인트 삭제
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()

    elapsed = time.time() - start_time

    print()
    print("=" * 60)
    print("완료!")
    print("=" * 60)
    print(f"Processed: {len(processed_qids):,}")
    print(f"Extracted: {stats['extracted']:,}")
    print(f"Failed: {stats['failed']:,}")
    print(f"Total words: {stats['total_words']:,}")
    print(f"Total links: {stats['total_links']:,}")
    print(f"Time: {elapsed/60:.1f} min")
    print(f"Output: {WIKIPEDIA_EXTRACTED}")
    if WIKIPEDIA_EXTRACTED.exists():
        print(f"Size: {WIKIPEDIA_EXTRACTED.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', '-w', type=int, help='Number of workers')
    parser.add_argument('--limit', '-l', type=int, help='Limit entities')
    parser.add_argument('--resume', '-r', action='store_true', help='Resume from checkpoint')
    args = parser.parse_args()

    extract_all_wikipedia_mp(
        workers=args.workers,
        limit=args.limit,
        resume=args.resume
    )
