"""
Step 3: Wikipedia 본문 추출 (SQLite 매핑 버전)

QID 매핑을 SQLite에 저장하여 메모리 문제 해결 + 멀티프로세싱.

Usage:
    python 03_extract_wikipedia_fast.py [--workers N] [--resume]
"""

import json
import sys
import time
import re
import argparse
import sqlite3
from pathlib import Path
from typing import Optional, Dict
from multiprocessing import Pool, cpu_count

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from config import (
    WIKIPEDIA_ZIM, WIKIDATA_EXTRACTED, WIKIPEDIA_EXTRACTED,
    QID_WIKI_MAP, CHECKPOINT_DIR
)

CHECKPOINT_FILE = CHECKPOINT_DIR / "wiki_fast_checkpoint.json"
OUTPUT_PARTIAL = WIKIPEDIA_EXTRACTED.parent / "wikipedia_fast_partial.jsonl"
MAPPING_DB = CHECKPOINT_DIR / "qid_mapping.db"

# 워커별 전역 변수
_zim = None
_db_conn = None


def build_sqlite_mapping():
    """JSON 매핑을 SQLite로 변환 (ijson 스트리밍)"""
    import ijson

    if MAPPING_DB.exists():
        try:
            conn = sqlite3.connect(str(MAPPING_DB))
            count = conn.execute("SELECT COUNT(*) FROM mapping").fetchone()[0]
            conn.close()
            if count > 1000000:  # 최소 100만개 이상이면 OK
                print(f"  SQLite mapping exists: {count:,} entries")
                return
        except:
            pass
        MAPPING_DB.unlink()

    print("  Building SQLite mapping from JSON (ijson streaming)...")

    conn = sqlite3.connect(str(MAPPING_DB))
    conn.execute("DROP TABLE IF EXISTS mapping")
    conn.execute("CREATE TABLE mapping (title TEXT PRIMARY KEY, qid TEXT)")
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")

    batch = []
    count = 0

    with open(QID_WIKI_MAP, 'rb') as f:
        # ijson으로 key-value 쌍 스트리밍
        for title, qid in ijson.kvitems(f, ''):
            batch.append((title, qid))
            count += 1

            if len(batch) >= 100000:
                conn.executemany("INSERT OR IGNORE INTO mapping VALUES (?, ?)", batch)
                print(f"    Inserted: {count:,}", flush=True)
                batch = []

    if batch:
        conn.executemany("INSERT OR IGNORE INTO mapping VALUES (?, ?)", batch)

    conn.commit()
    print(f"  Creating index...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_title ON mapping(title)")
    conn.commit()
    conn.close()

    print(f"  SQLite mapping created: {count:,} entries")


def init_worker(zim_path: str, db_path: str):
    """워커 초기화 - ZIM + SQLite 연결"""
    global _zim, _db_conn
    from libzim.reader import Archive
    _zim = Archive(zim_path)
    _db_conn = sqlite3.connect(db_path, check_same_thread=False)
    _db_conn.execute("PRAGMA query_only=ON")


def lookup_qid(title: str) -> Optional[str]:
    """SQLite에서 QID 조회"""
    global _db_conn
    result = _db_conn.execute(
        "SELECT qid FROM mapping WHERE title = ?", (title,)
    ).fetchone()
    return result[0] if result else None


def extract_one(entity: dict) -> Optional[Dict]:
    """단일 엔티티 추출"""
    global _zim
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

    soup = BeautifulSoup(html, 'lxml')

    # 링크 추출 + QID 변환
    mentions = []
    link_count = 0
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        text = a.get_text()

        if href.startswith('http') or href.startswith('#') or ':' in href:
            continue
        if not href or href.startswith('javascript'):
            continue

        link_count += 1
        if text and href:
            # QID 조회
            target_qid = lookup_qid(href) or lookup_qid(href.replace('_', ' '))
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
        'link_count': link_count,
        'mentions': mentions
    }


def save_checkpoint(processed_qids: set, stats: dict):
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'processed_qids': list(processed_qids),
            'stats': stats,
        }, f)


def load_checkpoint() -> tuple:
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return set(data.get('processed_qids', [])), data.get('stats', {})
    return set(), {}


def extract_all(workers: int = None, resume: bool = False):
    """Wikipedia 멀티프로세싱 추출"""

    print("=" * 60)
    print("Step 3: Wikipedia 추출 (SQLite 매핑)")
    print("=" * 60)

    try:
        from libzim.reader import Archive
        from bs4 import BeautifulSoup
        import lxml
    except ImportError as e:
        print(f"Error: {e}")
        print("Install: pip install libzim beautifulsoup4 lxml")
        return

    workers = workers or min(6, max(1, cpu_count() - 2))
    print(f"Workers: {workers}")

    # SQLite 매핑 빌드
    print("\nPreparing QID mapping...")
    build_sqlite_mapping()

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

    print(f"\nExtracting with {workers} workers...")
    start_time = time.time()

    output_mode = 'a' if resume and OUTPUT_PARTIAL.exists() else 'w'

    with open(OUTPUT_PARTIAL, output_mode, encoding='utf-8') as f_out:
        with Pool(
            processes=workers,
            initializer=init_worker,
            initargs=(str(WIKIPEDIA_ZIM), str(MAPPING_DB))
        ) as pool:

            processed_count = 0
            batch_results = []

            for result in pool.imap_unordered(extract_one, entities, chunksize=50):
                processed_count += 1

                if result:
                    batch_results.append(result)
                    processed_qids.add(result['qid'])
                    stats['extracted'] += 1
                    stats['total_words'] += result['word_count']
                    stats['total_links'] += result['link_count']
                else:
                    stats['failed'] += 1

                # 배치 쓰기
                if len(batch_results) >= 500:
                    for r in batch_results:
                        f_out.write(json.dumps(r, ensure_ascii=False) + '\n')
                    batch_results = []
                    f_out.flush()

                # 진행률
                if processed_count % 1000 == 0:
                    elapsed = time.time() - start_time
                    rate = processed_count / elapsed if elapsed > 0 else 0
                    remaining = len(entities) - processed_count
                    eta = remaining / rate if rate > 0 else 0

                    print(f"  Progress: {processed_count:,}/{len(entities):,} | "
                          f"Extracted: {stats['extracted']:,} | "
                          f"Rate: {rate:.1f}/s | "
                          f"ETA: {eta/3600:.1f}h")

                # 체크포인트
                if processed_count % 10000 == 0:
                    for r in batch_results:
                        f_out.write(json.dumps(r, ensure_ascii=False) + '\n')
                    batch_results = []
                    f_out.flush()
                    save_checkpoint(processed_qids, stats)

            # 마지막 배치
            for r in batch_results:
                f_out.write(json.dumps(r, ensure_ascii=False) + '\n')

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
    print(f"Rate: {stats['extracted']/elapsed:.1f}/s")
    if WIKIPEDIA_EXTRACTED.exists():
        print(f"Size: {WIKIPEDIA_EXTRACTED.stat().st_size/1024/1024:.1f} MB")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', '-w', type=int, default=6)
    parser.add_argument('--resume', '-r', action='store_true')
    args = parser.parse_args()

    extract_all(workers=args.workers, resume=args.resume)
