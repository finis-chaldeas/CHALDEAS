"""
빠른 통합 테스트
- Wikidata 앞부분에서 person 5개 추출
- Wikipedia에서 Alexander the Great 테스트
"""

import json
import sys
import re
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

WIKIDATA_JSON = "D:/project/wikidata/latest-all.json"
WIKIPEDIA_ZIM = "C:/Projects/Chaldeas/data/kiwix/wikipedia_en_nopic.zim"

# ============================================
# TEST 1: Wikidata 전체 속성 추출
# ============================================

def test_wikidata():
    print("=" * 60)
    print("[TEST 1] Wikidata 속성 추출")
    print("=" * 60)

    persons = []
    scanned = 0

    with open(WIKIDATA_JSON, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line in ['[', ']', '']:
                continue
            if line.endswith(','):
                line = line[:-1]

            scanned += 1
            if scanned % 50000 == 0:
                print(f"  Scanned {scanned:,}, found {len(persons)} persons")

            try:
                entity = json.loads(line)
            except:
                continue

            # Check if person (P31 = Q5)
            claims = entity.get('claims', {})
            p31 = claims.get('P31', [])
            is_person = False
            for claim in p31:
                try:
                    qid = claim['mainsnak']['datavalue']['value']['id']
                    if qid == 'Q5':
                        is_person = True
                        break
                except:
                    pass

            if not is_person:
                continue

            # Extract all properties
            qid = entity.get('id')
            labels = entity.get('labels', {})
            name = labels.get('en', {}).get('value', qid)

            # Count properties
            prop_count = sum(len(v) for v in claims.values())

            # Get Wikipedia link
            sitelinks = entity.get('sitelinks', {})
            wiki = sitelinks.get('enwiki', {}).get('title')

            persons.append({
                'qid': qid,
                'name': name,
                'properties': prop_count,
                'wikipedia': wiki
            })

            print(f"  Found: {qid} - {name} ({prop_count} props)")

            if len(persons) >= 5:
                break

            if scanned > 500000:
                print("  Reached scan limit")
                break

    print(f"\nWikidata Result: {len(persons)} persons from {scanned:,} entities")
    return persons

# ============================================
# TEST 2: Wikipedia 본문 + 링크 추출
# ============================================

def test_wikipedia():
    print("\n" + "=" * 60)
    print("[TEST 2] Wikipedia 본문 추출")
    print("=" * 60)

    try:
        from libzim.reader import Archive
        from bs4 import BeautifulSoup
    except ImportError as e:
        print(f"Error: {e}")
        return None

    zim = Archive(WIKIPEDIA_ZIM)
    print(f"ZIM loaded: {zim.entry_count} entries")

    # Test with Alexander the Great
    test_title = "Alexander_the_Great"

    try:
        entry = zim.get_entry_by_path(f"A/{test_title}")
        html = entry.get_item().content.tobytes().decode('utf-8')
        print(f"Found article: {test_title}")
    except Exception as e:
        print(f"Error: {e}")
        return None

    soup = BeautifulSoup(html, 'html.parser')

    # Extract links
    links = []
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        text = a.get_text()

        # Skip external links, anchors, special pages
        if href.startswith('http') or href.startswith('#') or ':' in href:
            continue
        if not href or href.startswith('javascript'):
            continue

        # Internal wiki link - just the article title
        target = href.replace('_', ' ')
        if text and target:
            links.append({
                'text': text[:50],
                'target': target[:50]
            })

    # Extract text
    for tag in soup(['script', 'style', 'nav']):
        tag.decompose()
    text = soup.get_text(separator=' ', strip=True)
    text = re.sub(r'\s+', ' ', text)

    print(f"\nArticle: {test_title}")
    print(f"  - Text length: {len(text):,} chars")
    print(f"  - Word count: {len(text.split()):,}")
    print(f"  - Links found: {len(links)}")

    print(f"\n  First 500 chars:")
    print(f"  {text[:500]}...")

    print(f"\n  Sample links (first 10):")
    for link in links[:10]:
        print(f"    [{link['text']}] → {link['target']}")

    return {
        'title': test_title,
        'text_len': len(text),
        'word_count': len(text.split()),
        'link_count': len(links),
        'sample_text': text[:1000],
        'sample_links': links[:20]
    }

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("통합 추출 빠른 테스트\n")

    # Test 1: Wikidata
    persons = test_wikidata()

    # Test 2: Wikipedia
    wiki = test_wikipedia()

    # Summary
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    if persons:
        print(f"\n[Wikidata]")
        print(f"  Persons found: {len(persons)}")
        total_props = sum(p['properties'] for p in persons)
        print(f"  Total properties: {total_props}")
        print(f"  Avg properties/person: {total_props/len(persons):.1f}")

    if wiki:
        print(f"\n[Wikipedia]")
        print(f"  Article: {wiki['title']}")
        print(f"  Words: {wiki['word_count']:,}")
        print(f"  Links: {wiki['link_count']}")

    print("\n테스트 완료!")
