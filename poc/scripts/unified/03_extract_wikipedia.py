"""
Step 3: Wikipedia 본문 + 하이퍼링크 추출

Wikidata에서 추출한 엔티티들의 Wikipedia 문서를 가져와서
본문과 하이퍼링크 추출.

Usage:
    python 03_extract_wikipedia.py [--limit N] [--test]
"""

import json
import sys
import time
import re
import argparse
from pathlib import Path
from typing import Optional, Dict, List

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from config import (
    WIKIPEDIA_ZIM, WIKIDATA_EXTRACTED, WIKIPEDIA_EXTRACTED,
    QID_WIKI_MAP, CHECKPOINT_DIR, LOG_INTERVAL
)

# ============================================
# Wikipedia 추출
# ============================================

def extract_wikipedia_article(zim, title: str) -> Optional[Dict]:
    """ZIM에서 Wikipedia 문서 추출"""
    from bs4 import BeautifulSoup

    # 경로 시도
    paths = [
        f"A/{title.replace(' ', '_')}",
        f"{title.replace(' ', '_')}",
    ]

    entry = None
    for path in paths:
        try:
            entry = zim.get_entry_by_path(path)
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
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        text = a.get_text()

        # 외부 링크, 앵커, 특수 페이지 제외
        if href.startswith('http') or href.startswith('#') or ':' in href:
            continue
        if not href or href.startswith('javascript'):
            continue

        target = href  # 원본 유지 (매핑용)
        if text and target:
            links.append({
                'text': text[:200],
                'target': target
            })

    # 텍스트 추출
    for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
        tag.decompose()

    text = soup.get_text(separator=' ', strip=True)
    text = re.sub(r'\s+', ' ', text)

    return {
        'content_raw': text,
        'content_html': html,
        'word_count': len(text.split()),
        'links': links
    }

def extract_all_wikipedia(limit: int = None, test_mode: bool = False):
    """Wikipedia 전체 추출"""

    print("=" * 60)
    print("Step 3: Wikipedia 본문 + 하이퍼링크 추출")
    print("=" * 60)

    # 의존성 체크
    try:
        from libzim.reader import Archive
        from bs4 import BeautifulSoup
    except ImportError as e:
        print(f"Error: {e}")
        print("Install: pip install libzim beautifulsoup4")
        return

    # QID → Wikipedia 매핑 로드
    print(f"Loading QID mapping from {QID_WIKI_MAP}...")
    if not QID_WIKI_MAP.exists():
        print("  Error: QID mapping not found. Run 01_build_qid_mapping.py first.")
        return

    with open(QID_WIKI_MAP, 'r', encoding='utf-8') as f:
        title_to_qid = json.load(f)
    print(f"  Loaded {len(title_to_qid):,} mappings")

    # Wikidata 추출 결과 로드 (Wikipedia 있는 것만)
    print(f"\nLoading extracted entities from {WIKIDATA_EXTRACTED}...")
    if not WIKIDATA_EXTRACTED.exists():
        print("  Error: Wikidata extraction not found. Run 02_extract_wikidata.py first.")
        return

    entities_with_wiki = []
    with open(WIKIDATA_EXTRACTED, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entity = json.loads(line)
                if entity.get('wikipedia_title'):
                    entities_with_wiki.append({
                        'qid': entity['qid'],
                        'type': entity['type'],
                        'name': entity['name'],
                        'wikipedia_title': entity['wikipedia_title']
                    })
            except:
                continue

    print(f"  Found {len(entities_with_wiki):,} entities with Wikipedia")

    if limit:
        entities_with_wiki = entities_with_wiki[:limit]
        print(f"  Limited to {limit}")

    # ZIM 열기
    print(f"\nOpening ZIM: {WIKIPEDIA_ZIM}...")
    zim = Archive(str(WIKIPEDIA_ZIM))
    print(f"  Entries: {zim.entry_count:,}")

    # 추출
    print(f"\nExtracting Wikipedia articles...")

    extracted = 0
    failed = 0
    total_words = 0
    total_links = 0
    start_time = time.time()

    with open(WIKIPEDIA_EXTRACTED, 'w', encoding='utf-8') as f_out:
        for i, entity in enumerate(entities_with_wiki):
            if (i + 1) % 100 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                print(f"  Progress: {i+1:,}/{len(entities_with_wiki):,} | "
                      f"Extracted: {extracted} | Failed: {failed} | "
                      f"Rate: {rate:.1f}/s")

            title = entity['wikipedia_title']
            wiki = extract_wikipedia_article(zim, title)

            if not wiki:
                failed += 1
                continue

            # mentions 생성 (하이퍼링크 → QID)
            mentions = []
            for link in wiki['links']:
                target_title = link['target']
                target_qid = title_to_qid.get(target_title) or \
                             title_to_qid.get(target_title.replace('_', ' '))

                if target_qid:
                    mentions.append({
                        'target_qid': target_qid,
                        'link_text': link['text'],
                        'evidence': f"Wikipedia link: {link['text']}"
                    })

            # 출력
            result = {
                'qid': entity['qid'],
                'type': entity['type'],
                'name': entity['name'],
                'wikipedia_title': title,
                'content_raw': wiki['content_raw'][:100000],  # 100KB 제한
                'word_count': wiki['word_count'],
                'link_count': len(wiki['links']),
                'mentions': mentions
            }

            f_out.write(json.dumps(result, ensure_ascii=False) + '\n')

            extracted += 1
            total_words += wiki['word_count']
            total_links += len(wiki['links'])

    # 완료
    elapsed = time.time() - start_time

    print()
    print("=" * 60)
    print("완료!")
    print("=" * 60)
    print(f"Processed: {len(entities_with_wiki):,}")
    print(f"Extracted: {extracted:,}")
    print(f"Failed: {failed:,}")
    print(f"Total words: {total_words:,}")
    print(f"Total links: {total_links:,}")
    print(f"Mentions (with QID): calculated per article")
    print(f"Time: {elapsed/60:.1f} min")
    print(f"Output: {WIKIPEDIA_EXTRACTED}")
    if WIKIPEDIA_EXTRACTED.exists():
        print(f"Size: {WIKIPEDIA_EXTRACTED.stat().st_size / 1024 / 1024:.1f} MB")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', '-l', type=int, help='Limit entities')
    parser.add_argument('--test', action='store_true', help='Test mode')
    args = parser.parse_args()

    extract_all_wikipedia(limit=args.limit, test_mode=args.test)
