"""
Gutenberg 책에서 통합 스키마로 추출.

1. Gutenberg ZIM에서 책 내용 추출
2. 청킹 (2500자 + 200자 오버랩)
3. 엔티티 언급 찾기 (sitelinks 매핑 사용)
4. sources + mentions 테이블에 저장

Usage:
    python extract_gutenberg.py --book "The History of the Decline and Fall" --save
    python extract_gutenberg.py --list --limit 20
"""

import sys
import os
import re
import json
import argparse
import psycopg2
from datetime import datetime
from pathlib import Path

try:
    from libzim.reader import Archive
except ImportError:
    print("Error: libzim not installed. Run: pip install libzim")
    sys.exit(1)

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ZIM_PATH = 'C:/Projects/Chaldeas/data/kiwix/gutenberg_en_all.zim'
SITELINKS_FILE = 'poc/data/wikipedia_extract/wiki_sitelinks.json'

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}

CHUNK_SIZE = 2500
CHUNK_OVERLAP = 200


class GutenbergExtractor:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.zim = Archive(ZIM_PATH)
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cur = self.conn.cursor()

        # sitelinks 매핑 로드
        self.wiki_to_entity = {}
        self._load_sitelinks()

        # 엔티티 이름 매핑 (DB에서)
        self.entity_names = {}
        self._load_entity_names()

        self.stats = {
            'books_processed': 0,
            'chunks_created': 0,
            'mentions_created': 0,
        }

    def _load_sitelinks(self):
        """Wikidata sitelinks 매핑 로드."""
        if not os.path.exists(SITELINKS_FILE):
            print(f"  sitelinks: NOT FOUND")
            return

        with open(SITELINKS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.wiki_to_entity = data.get('wiki_to_entity', {})
        print(f"  sitelinks: {len(self.wiki_to_entity):,}")

    def _load_entity_names(self):
        """DB에서 엔티티 이름 로드."""
        print("Loading entity names...")

        # persons
        self.cur.execute("SELECT id, name, wikidata_id FROM persons WHERE name IS NOT NULL")
        for row in self.cur.fetchall():
            self.entity_names[row[1]] = ('person', row[0], row[2])

        # events
        self.cur.execute("SELECT id, title, wikidata_id FROM events WHERE title IS NOT NULL")
        for row in self.cur.fetchall():
            self.entity_names[row[1]] = ('event', row[0], row[2])

        # locations
        self.cur.execute("SELECT id, name, wikidata_id FROM locations WHERE name IS NOT NULL")
        for row in self.cur.fetchall():
            self.entity_names[row[1]] = ('location', row[0], row[2])

        print(f"  entity names: {len(self.entity_names):,}")

    def list_books(self, limit=20, search=None):
        """사용 가능한 책 목록."""
        books = []
        seen = set()

        for i in range(self.zim.entry_count):
            try:
                entry = self.zim._get_entry_by_id(i)
                path = entry.path

                # HTML 엔트리만 (epub, cover 제외)
                if '.epub' in path or '_cover' in path:
                    continue

                # 숫자로 끝나는 것만 (book_id)
                match = re.search(r'\.(\d+)$', path)
                if not match:
                    continue

                book_id = match.group(1)
                title = entry.title

                if book_id in seen:
                    continue
                seen.add(book_id)

                if search and search.lower() not in title.lower():
                    continue

                books.append({
                    'id': book_id,
                    'title': title,
                    'path': path
                })

                if len(books) >= limit:
                    break
            except:
                continue

        return books

    def get_book_content(self, book_id_or_title):
        """책 내용 가져오기."""
        # 제목으로 검색
        for i in range(self.zim.entry_count):
            try:
                entry = self.zim._get_entry_by_id(i)
                path = entry.path

                if '.epub' in path or '_cover' in path:
                    continue

                match = re.search(r'\.(\d+)$', path)
                if not match:
                    continue

                if book_id_or_title in entry.title or book_id_or_title == match.group(1):
                    html = bytes(entry.get_item().content).decode('utf-8', errors='replace')
                    return {
                        'id': match.group(1),
                        'title': entry.title,
                        'html': html
                    }
            except:
                continue
        return None

    def clean_html(self, html):
        """HTML → 텍스트."""
        # 스크립트, 스타일 제거
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', ' ', text)
        # HTML 엔티티
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = re.sub(r'&#\d+;', ' ', text)
        text = re.sub(r'&[a-z]+;', ' ', text)
        # 공백 정리
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def chunk_text(self, text):
        """텍스트를 청크로 분할."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + CHUNK_SIZE
            if end < len(text):
                # 문장 경계에서 자르기
                for sep in ['. ', '! ', '? ', '\n']:
                    last_sep = text[start:end].rfind(sep)
                    if last_sep > CHUNK_SIZE // 2:
                        end = start + last_sep + len(sep)
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append({
                    'text': chunk,
                    'start': start,
                    'end': end
                })

            start = end - CHUNK_OVERLAP

        return chunks

    def find_entity_mentions(self, text):
        """텍스트에서 엔티티 언급 찾기."""
        mentions = []

        # 긴 이름부터 매칭 (부분 매칭 방지)
        sorted_names = sorted(self.entity_names.keys(), key=len, reverse=True)

        found_positions = set()  # 중복 방지

        for name in sorted_names:
            if len(name) < 4:  # 너무 짧은 이름 제외
                continue

            # 단어 경계에서 매칭
            pattern = r'\b' + re.escape(name) + r'\b'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                pos = match.start()

                # 이미 매칭된 위치면 스킵
                if any(abs(pos - p) < 10 for p in found_positions):
                    continue

                entity_type, entity_id, qid = self.entity_names[name]

                # 컨텍스트 추출 (앞뒤 100자)
                ctx_start = max(0, pos - 100)
                ctx_end = min(len(text), match.end() + 100)
                context = text[ctx_start:ctx_end]

                mentions.append({
                    'name': name,
                    'entity_type': entity_type,
                    'entity_id': entity_id,
                    'qid': qid,
                    'position': pos,
                    'context': context
                })

                found_positions.add(pos)

        return mentions

    def process_book(self, book_id_or_title):
        """책 하나 처리."""
        print(f"\nProcessing: {book_id_or_title}")

        book = self.get_book_content(book_id_or_title)
        if not book:
            print("  Book not found")
            return None

        print(f"  Title: {book['title']}")
        print(f"  ID: {book['id']}")

        # HTML → 텍스트
        text = self.clean_html(book['html'])
        print(f"  Text length: {len(text):,} chars")

        # 청킹
        chunks = self.chunk_text(text)
        print(f"  Chunks: {len(chunks)}")

        # 각 청크에서 엔티티 찾기 및 저장
        total_mentions = 0

        for i, chunk in enumerate(chunks):
            mentions = self.find_entity_mentions(chunk['text'])

            if not self.dry_run and mentions:
                # source 저장
                self.cur.execute("""
                    INSERT INTO sources (source_type, title, chunk_index, content_raw)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, ('gutenberg', book['title'], i, chunk['text'][:5000]))
                source_id = self.cur.fetchone()[0]

                # mentions 저장
                for m in mentions:
                    self.cur.execute("""
                        INSERT INTO mentions (source_id, target_type, target_id, evidence_raw, position_start)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (source_id, m['entity_type'], m['entity_id'], m['context'], m['position']))

                self.conn.commit()
                self.stats['chunks_created'] += 1

            total_mentions += len(mentions)

        self.stats['books_processed'] += 1
        self.stats['mentions_created'] += total_mentions

        print(f"  Mentions found: {total_mentions}")

        return {
            'title': book['title'],
            'chunks': len(chunks),
            'mentions': total_mentions
        }

    def print_summary(self):
        """통계 출력."""
        print("\n" + "=" * 60)
        print("GUTENBERG EXTRACTION SUMMARY")
        print("=" * 60)
        for key, value in self.stats.items():
            print(f"  {key}: {value:,}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--list', action='store_true', help='책 목록 표시')
    parser.add_argument('--search', help='책 검색')
    parser.add_argument('--book', help='추출할 책 제목/ID')
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--save', action='store_true')
    args = parser.parse_args()

    extractor = GutenbergExtractor(dry_run=args.dry_run or not args.save)

    if args.list or args.search:
        books = extractor.list_books(limit=args.limit, search=args.search)
        print(f"\nFound {len(books)} books:")
        for b in books:
            print(f"  [{b['id']}] {b['title']}")
        return

    if args.book:
        extractor.process_book(args.book)
        extractor.print_summary()
        return

    print("Usage: --list, --search TERM, or --book TITLE")


if __name__ == '__main__':
    main()
