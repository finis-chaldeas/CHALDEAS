"""
Wikipedia ZIM에서 근거 있는 연결만 추출.
이벤트 페이지에서 인물/이벤트 언급 찾아서 context와 함께 저장.

데이터 소스:
- 본문 링크: 문맥과 함께 추출
- Navbox: 관련 전투, 참전국 등 구조화된 데이터

Usage:
    python extract_wiki_connections.py --test 5
    python extract_wiki_connections.py --test 5 --save
"""

import sys
import os
import re
import json
import argparse
from datetime import datetime
from libzim.reader import Archive
from html.parser import HTMLParser
from urllib.parse import unquote

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ZIM_PATH = 'C:/Projects/Chaldeas/data/kiwix/wikipedia_en_nopic.zim'
OUTPUT_DIR = 'poc/data/wikipedia_extract'

# QID 캐시 (메모리)
_qid_cache = {}


class HTMLTextExtractor(HTMLParser):
    """HTML에서 순수 텍스트 추출."""
    def __init__(self):
        super().__init__()
        self.text = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript', 'sup', 'sub'):
            self.skip = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'sup', 'sub'):
            self.skip = False
        if tag in ('p', 'div', 'h1', 'h2', 'h3', 'h4', 'li'):
            self.text.append('\n')

    def handle_data(self, data):
        if not self.skip:
            self.text.append(data)

    def get_text(self):
        return ''.join(self.text)


class WikiLinkExtractor(HTMLParser):
    """Wikipedia 링크 추출."""
    def __init__(self):
        super().__init__()
        self.links = []
        self.current_link = None
        self.current_text = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            attrs_dict = dict(attrs)
            href = attrs_dict.get('href', '')
            # ZIM 링크: Article_Name 형식 (네임스페이스, 리소스 제외)
            if (href and
                not href.startswith(('_mw_', '_res_', 'http', '#', 'Category:', 'File:', 'Help:', 'Wikipedia:', 'Template:', 'Special:')) and
                ':' not in href.split('#')[0]):
                # URL 디코딩 및 정리
                href_clean = unquote(href.split('#')[0]).replace('_', ' ')
                self.current_link = href_clean
                self.current_text = []

    def handle_endtag(self, tag):
        if tag == 'a' and self.current_link:
            text = ''.join(self.current_text).strip()
            if text and len(text) > 1:
                self.links.append({
                    'title': self.current_link,
                    'text': text
                })
            self.current_link = None

    def handle_data(self, data):
        if self.current_link is not None:
            self.current_text.append(data)


def get_zim_article(zim, title):
    """ZIM에서 문서 HTML 가져오기."""
    try:
        path = f"A/{title.replace(' ', '_')}"
        entry = zim.get_entry_by_path(path)
        item = entry.get_item()
        return bytes(item.content).decode('utf-8', errors='replace')
    except:
        return None


def extract_wikidata_id(html):
    """HTML에서 Wikidata ID (Q숫자) 추출."""
    if not html:
        return None
    # wikidata.org/wiki/Q12345 형식
    match = re.search(r'wikidata\.org/wiki/(Q\d+)', html)
    if match:
        return match.group(1)
    return None


def get_qid_for_title(zim, title):
    """Wikipedia 타이틀의 Wikidata QID 가져오기 (캐시 사용)."""
    if title in _qid_cache:
        return _qid_cache[title]

    html = get_zim_article(zim, title)
    qid = extract_wikidata_id(html)
    _qid_cache[title] = qid
    return qid


def extract_context(text, name, window=150):
    """텍스트에서 이름 주변 context 추출."""
    pattern = re.escape(name)
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        start = max(0, match.start() - window)
        end = min(len(text), match.end() + window)
        context = text[start:end].strip()
        if start > 0:
            context = '...' + context
        if end < len(text):
            context = context + '...'
        return context
    return None


def extract_navbox_groups(html):
    """Navbox에서 그룹-항목 쌍 추출."""
    pairs = re.findall(
        r'<th[^>]*class="navbox-group"[^>]*>(.*?)</th>\s*<td[^>]*class="navbox-list[^"]*"[^>]*>(.*?)</td>',
        html, re.DOTALL
    )

    results = []
    for group_html, list_html in pairs:
        # 그룹명 추출
        group = re.sub(r'<[^>]+>', ' ', group_html).strip()
        group = re.sub(r'\s+', ' ', group)

        # 리스트 내 링크 추출
        links = re.findall(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', list_html)
        items = []
        for href, text in links:
            if not href.startswith(('_', 'http', '#', 'Category')):
                href_clean = unquote(href.split('#')[0]).replace('_', ' ')
                items.append({
                    'title': href_clean,
                    'text': text.strip()
                })

        if items:
            results.append({
                'group': group,
                'items': items
            })

    return results


def extract_infobox(html):
    """Infobox에서 기본 정보 추출."""
    infobox_match = re.search(r'<table class="infobox[^"]*"[^>]*>.*?</table>', html, re.DOTALL)
    if not infobox_match:
        return {}

    infobox = infobox_match.group(0)
    result = {}

    # 행에서 레이블-값 쌍 추출
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', infobox, re.DOTALL)
    for row in rows:
        th = re.search(r'<th[^>]*>(.*?)</th>', row, re.DOTALL)
        td = re.search(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        if th and td:
            label = re.sub(r'<[^>]+>', '', th.group(1)).strip().lower()
            value = re.sub(r'<[^>]+>', ' ', td.group(1)).strip()
            value = re.sub(r'\s+', ' ', value)
            if label and value:
                result[label] = value

    return result


def process_event(zim, event_title, resolve_qids=False):
    """이벤트 페이지 처리."""
    html = get_zim_article(zim, event_title)
    if not html:
        return None

    # 이벤트 자체의 QID
    event_qid = extract_wikidata_id(html)

    # 링크 추출
    link_extractor = WikiLinkExtractor()
    link_extractor.feed(html)
    links = link_extractor.links

    # 텍스트 추출
    text_extractor = HTMLTextExtractor()
    text_extractor.feed(html)
    full_text = text_extractor.get_text()

    # Navbox 추출
    navbox_groups = extract_navbox_groups(html)

    # Infobox 추출
    infobox = extract_infobox(html)

    # 본문 연결 (context 포함)
    body_connections = []
    for link in links:
        context = extract_context(full_text, link['text'])
        if context:
            conn = {
                'target_title': link['title'],
                'display_text': link['text'],
                'evidence_text': context,
                'source': {
                    'type': 'wikipedia_body',
                    'article': event_title,
                    'url': f"https://en.wikipedia.org/wiki/{event_title.replace(' ', '_')}"
                }
            }
            # QID 해석 (옵션)
            if resolve_qids:
                conn['target_qid'] = get_qid_for_title(zim, link['title'])
            body_connections.append(conn)

    # Navbox 연결
    navbox_connections = []
    for group in navbox_groups:
        for item in group['items']:
            conn = {
                'target_title': item['title'],
                'display_text': item['text'],
                'navbox_group': group['group'],
                'source': {
                    'type': 'wikipedia_navbox',
                    'article': event_title,
                    'url': f"https://en.wikipedia.org/wiki/{event_title.replace(' ', '_')}"
                }
            }
            # QID 해석 (옵션)
            if resolve_qids:
                conn['target_qid'] = get_qid_for_title(zim, item['title'])
            navbox_connections.append(conn)

    return {
        'event': event_title,
        'event_qid': event_qid,
        'infobox': infobox,
        'body_connections': body_connections,
        'navbox_connections': navbox_connections,
        'stats': {
            'total_links': len(links),
            'body_with_context': len(body_connections),
            'navbox_items': len(navbox_connections),
            'text_length': len(full_text)
        }
    }


def load_event_list(filepath):
    """파일에서 이벤트 목록 로드 (# 주석 무시)."""
    events = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                events.append(line)
    return events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', type=int, default=5, help='테스트할 이벤트 수')
    parser.add_argument('--events-file', type=str, help='이벤트 목록 파일 경로')
    parser.add_argument('--save', action='store_true', help='결과 JSON 저장')
    parser.add_argument('--resolve-qids', action='store_true', help='각 연결의 Wikidata QID 해석 (느림)')
    args = parser.parse_args()

    print(f"Opening ZIM: {ZIM_PATH}")
    zim = Archive(ZIM_PATH)
    print(f"ZIM articles: {zim.entry_count:,}")
    print()

    # 이벤트 목록 로드
    if args.events_file:
        test_events = load_event_list(args.events_file)
        print(f"Loaded {len(test_events)} events from {args.events_file}")
    else:
        test_events = [
            "Battle of Waterloo",
            "Battle of Hastings",
            "French Revolution",
            "World War I",
            "American Revolution",
            "Battle of Thermopylae",
            "Siege of Constantinople",
            "Russian Revolution",
            "Korean War",
            "Napoleonic Wars",
        ][:args.test]

    results = []

    for event_title in test_events:
        print(f"=== {event_title} ===")

        result = process_event(zim, event_title, resolve_qids=args.resolve_qids)
        if not result:
            print("  [NOT FOUND in ZIM]")
            print()
            continue

        stats = result['stats']
        print(f"  QID: {result.get('event_qid', 'N/A')}")
        print(f"  Body links: {stats['total_links']} -> with context: {stats['body_with_context']}")
        print(f"  Navbox items: {stats['navbox_items']}")

        # Infobox 샘플
        if result['infobox']:
            print(f"  Infobox: {list(result['infobox'].keys())[:5]}")

        # 본문 연결 샘플
        print(f"  Body samples:")
        for conn in result['body_connections'][:3]:
            ctx = conn['evidence_text'].replace('\n', ' ')[:80]
            print(f"    - {conn['display_text']}: \"{ctx}...\"")

        # Navbox 연결 샘플
        print(f"  Navbox samples:")
        for conn in result['navbox_connections'][:3]:
            print(f"    - [{conn['navbox_group']}] {conn['display_text']}")

        print()
        results.append(result)

    # 요약
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    total_body = sum(r['stats']['body_with_context'] for r in results)
    total_navbox = sum(r['stats']['navbox_items'] for r in results)
    print(f"Events processed: {len(results)}")
    print(f"Body connections with evidence: {total_body}")
    print(f"Navbox connections: {total_navbox}")
    print(f"Total connections: {total_body + total_navbox}")

    # 저장
    if args.save and results:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(OUTPUT_DIR, f'extract_{timestamp}.json')

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'extracted_at': timestamp,
                'events': results
            }, f, ensure_ascii=False, indent=2)

        print(f"\nSaved to: {output_file}")


if __name__ == '__main__':
    main()
