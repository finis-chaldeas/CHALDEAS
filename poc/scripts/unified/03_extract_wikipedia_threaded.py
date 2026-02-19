"""
Step 3: Wikipedia 본문 + 하이퍼링크 추출 (스레딩)

스레드 사용으로 메모리 공유하면서 병렬 처리.

Usage:
    python 03_extract_wikipedia_threaded.py [--workers N] [--resume]
"""

import json
import sys
import time
import re
import argparse
from pathlib import Path
from typing import Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import queue

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from config import (
    WIKIPEDIA_ZIM, WIKIDATA_EXTRACTED, WIKIPEDIA_EXTRACTED,
    QID_WIKI_MAP, CHECKPOINT_DIR
)

CHECKPOINT_FILE = CHECKPOINT_DIR / "wiki_extract_checkpoint.json"
OUTPUT_PARTIAL = WIKIPEDIA_EXTRACTED.parent / "wikipedia_partial.jsonl"

# 전역 변수 (스레드 공유)
_zim = None
_title_to_qid = None
_write_lock = Lock()


def init_globals():
    """전역 변수 초기화"""
    global _zim, _title_to_qid
    from libzim.reader import Archive

    print("Loading ZIM archive...")
    _zim = Archive(str(WIKIPEDIA_ZIM))
    print(f"  Entries: {_zim.entry_count:,}")

    print("Loading QID mapping...")
    with open(QID_WIKI_MAP, 'r', encoding='utf-8') as f:
        _title_to_qid = json.load(f)
    print(f"  Mappings: {len(_title_to_qid):,}")


def extract_one(entity: dict) -> Optional[Dict]:
    """단일 엔티티의 Wikipedia 추출"""
    from bs4 import BeautifulSoup

    title = entity.get('wikipedia_title')
    if not title:
        return None

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
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'processed_qids': list(processed_qids),
            'stats': stats,
        }, f)


def load_checkpoint() -> tuple:
    """체크포인트 로드"""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return set(data.get('processed_qids', [])), data.get('stats', {})
    return set(), {}


def extract_all(workers: int = 8, resume: bool = False):
    """Wikipedia 스레드 풀 추출"""

    print("=" * 60)
    print("Step 3: Wikipedia 본문 + 하이퍼링크 추출 (스레딩)")
    print("=" * 60)
    print(f"Workers: {workers}")

    # 전역 초기화
    init_globals()

    # 체크포인트
    processed_qids = set()
    stats = {'extracted': 0, 'failed': 0, 'total_words': 0, 'total_links': 0}

    if resume and CHECKPOINT_FILE.exists():
        processed_qids, stats = load_checkpoint()
        print(f"\nResuming: {len(processed_qids):,} already processed")

    # 엔티티 로드
    print(f"\nLoading entities from {WIKIDATA_EXTRACTED}...")
    entities = []
    with open(WIKIDATA_EXTRACTED, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                e = json.loads(line)
                if e.get('wikipedia_title') and e['qid'] not in processed_qids:
                    entities.append({
                        'qid': e['qid'],
                        'type': e['type'],
                        'name': e['name'],
                        'wikipedia_title': e['wikipedia_title']
                    })
            except:
                pass

    total = len(entities) + len(processed_qids)
    print(f"  Total with Wikipedia: {total:,}")
    print(f"  To process: {len(entities):,}")

    if not entities:
        print("\nNothing to process!")
        return

    # 추출
    print(f"\nExtracting with {workers} threads...")
    start_time = time.time()

    output_mode = 'a' if resume and OUTPUT_PARTIAL.exists() else 'w'

    with open(OUTPUT_PARTIAL, output_mode, encoding='utf-8') as f_out:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(extract_one, e): e for e in entities}

            for i, future in enumerate(as_completed(futures)):
                entity = futures[future]
                try:
                    result = future.result()
                    if result:
                        with _write_lock:
                            f_out.write(json.dumps(result, ensure_ascii=False) + '\n')
                            processed_qids.add(result['qid'])
                            stats['extracted'] += 1
                            stats['total_words'] += result['word_count']
                            stats['total_links'] += result['link_count']
                    else:
                        stats['failed'] += 1
                except Exception as e:
                    stats['failed'] += 1

                # 진행률
                if (i + 1) % 1000 == 0:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed
                    eta = (len(entities) - i - 1) / rate if rate > 0 else 0
                    print(f"  Progress: {i+1:,}/{len(entities):,} | "
                          f"Extracted: {stats['extracted']:,} | "
                          f"Rate: {rate:.1f}/s | ETA: {eta/3600:.1f}h")

                # 체크포인트
                if (i + 1) % 10000 == 0:
                    save_checkpoint(processed_qids, stats)
                    f_out.flush()

    # 완료
    if OUTPUT_PARTIAL.exists():
        OUTPUT_PARTIAL.rename(WIKIPEDIA_EXTRACTED)
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()

    elapsed = time.time() - start_time
    print()
    print("=" * 60)
    print("완료!")
    print("=" * 60)
    print(f"Extracted: {stats['extracted']:,}")
    print(f"Failed: {stats['failed']:,}")
    print(f"Words: {stats['total_words']:,}")
    print(f"Links: {stats['total_links']:,}")
    print(f"Time: {elapsed/60:.1f} min")
    if WIKIPEDIA_EXTRACTED.exists():
        print(f"Size: {WIKIPEDIA_EXTRACTED.stat().st_size/1024/1024:.1f} MB")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', '-w', type=int, default=8)
    parser.add_argument('--resume', '-r', action='store_true')
    args = parser.parse_args()

    extract_all(workers=args.workers, resume=args.resume)
