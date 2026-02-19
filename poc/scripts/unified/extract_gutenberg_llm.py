"""
Gutenberg 책에서 LLM으로 엔티티 추출.

1. 책 청킹
2. LLM으로 엔티티 추출 (Ollama llama3.1 또는 OpenAI)
3. DB 엔티티와 매칭
4. sources + mentions 저장

Usage:
    python extract_gutenberg_llm.py --book "Life of Napoleon" --save
    python extract_gutenberg_llm.py --list --search "history"
"""

import sys
import os
import re
import json
import argparse
import psycopg2
import requests
from datetime import datetime

try:
    from libzim.reader import Archive
except ImportError:
    print("Error: libzim not installed")
    sys.exit(1)

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ZIM_PATH = 'C:/Projects/Chaldeas/data/kiwix/gutenberg_en_all.zim'
SITELINKS_FILE = 'poc/data/wikipedia_extract/wiki_sitelinks.json'

# Ollama 설정 (로컬 LLM)
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.1:8b-instruct-q4_0')

# OpenAI 폴백
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}

CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200

# 엔티티 추출 프롬프트
EXTRACT_PROMPT = """Extract HISTORICAL entities from this text. Return JSON only.

IMPORTANT: Only extract entities that are part of the HISTORICAL NARRATIVE, not:
- Book authors, editors, translators, publishers
- Modern people who wrote about history
- Copyright holders or project contributors

TEXT:
{text}

Extract:
1. PERSONS: Historical figures (kings, generals, politicians, etc.) - NOT modern authors
2. LOCATIONS: Historical places, cities, countries, battlefields
3. EVENTS: Historical events (battles, wars, treaties, revolutions)

Return ONLY valid JSON:
{{"persons": ["Name 1", "Name 2"], "locations": ["Place 1"], "events": ["Event 1"]}}

If none found: {{"persons": [], "locations": [], "events": []}}
JSON:"""


class GutenbergLLMExtractor:
    def __init__(self, dry_run=False, use_openai=False):
        self.dry_run = dry_run
        self.use_openai = use_openai
        self.zim = Archive(ZIM_PATH)
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cur = self.conn.cursor()

        # 매핑 로드
        self.wiki_to_entity = {}
        self.entity_by_name = {}
        self._load_mappings()

        self.stats = {
            'books_processed': 0,
            'chunks_processed': 0,
            'llm_calls': 0,
            'entities_extracted': 0,
            'entities_matched': 0,
            'mentions_created': 0,
        }

    def _load_mappings(self):
        """매핑 로드."""
        print("Loading mappings...")

        # sitelinks
        if os.path.exists(SITELINKS_FILE):
            with open(SITELINKS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.wiki_to_entity = data.get('wiki_to_entity', {})
            print(f"  sitelinks: {len(self.wiki_to_entity):,}")

        # DB 엔티티 이름
        for table, etype, name_col in [
            ('persons', 'person', 'name'),
            ('events', 'event', 'title'),
            ('locations', 'location', 'name')
        ]:
            self.cur.execute(f"SELECT id, {name_col}, wikidata_id FROM {table} WHERE {name_col} IS NOT NULL AND wikidata_id IS NOT NULL")
            for row in self.cur.fetchall():
                name = row[1]
                self.entity_by_name[name.lower()] = (etype, row[0], row[2])
                # 공백 변형도
                self.entity_by_name[name.lower().replace(' ', '_')] = (etype, row[0], row[2])

        print(f"  entity names: {len(self.entity_by_name):,}")

    def call_llm(self, prompt):
        """LLM 호출."""
        self.stats['llm_calls'] += 1

        if self.use_openai and OPENAI_API_KEY:
            return self._call_openai(prompt)
        else:
            return self._call_ollama(prompt)

    def _call_ollama(self, prompt):
        """Ollama 호출."""
        try:
            resp = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1}
                },
                timeout=60
            )
            if resp.status_code == 200:
                return resp.json().get('response', '')
        except Exception as e:
            print(f"  Ollama error: {e}")
        return None

    def _call_openai(self, prompt):
        """OpenAI 호출."""
        try:
            import openai
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"  OpenAI error: {e}")
        return None

    def extract_entities_from_chunk(self, text):
        """청크에서 LLM으로 엔티티 추출."""
        prompt = EXTRACT_PROMPT.format(text=text[:1500])  # 토큰 제한
        response = self.call_llm(prompt)

        if not response:
            return {'persons': [], 'locations': [], 'events': []}

        # JSON 파싱
        try:
            # JSON 부분만 추출
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

        return {'persons': [], 'locations': [], 'events': []}

    def match_entity(self, name, expected_type=None):
        """추출된 이름을 DB 엔티티에 매칭."""
        name_lower = name.lower().strip()

        # 1. 정확한 매칭
        if name_lower in self.entity_by_name:
            etype, eid, qid = self.entity_by_name[name_lower]
            if expected_type is None or etype == expected_type:
                return (etype, eid, qid)

        # 2. sitelinks에서
        if name in self.wiki_to_entity:
            info = self.wiki_to_entity[name]
            if expected_type is None or info['type'] == expected_type:
                return (info['type'], info['id'], info['qid'])

        # 3. 부분 매칭 (이름의 마지막 부분)
        parts = name_lower.split()
        if len(parts) > 1:
            last_name = parts[-1]
            for db_name, (etype, eid, qid) in self.entity_by_name.items():
                if db_name.endswith(last_name) and expected_type in (None, etype):
                    # 추가 검증: 첫 이름도 매칭
                    if parts[0] in db_name:
                        return (etype, eid, qid)

        return None

    def get_book_content(self, search_term):
        """책 내용 가져오기."""
        for i in range(self.zim.entry_count):
            try:
                entry = self.zim._get_entry_by_id(i)
                path = entry.path

                if '.epub' in path or '_cover' in path:
                    continue

                match = re.search(r'\.(\d+)$', path)
                if not match:
                    continue

                if search_term.lower() in entry.title.lower():
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
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = re.sub(r'&#?\w+;', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def chunk_text(self, text, max_chunks=50):
        """텍스트 청킹 (메모리 효율적)."""
        # 텍스트가 너무 길면 앞부분만 사용
        max_text_len = CHUNK_SIZE * max_chunks * 2
        if len(text) > max_text_len:
            text = text[:max_text_len]

        chunks = []
        start = 0
        while start < len(text) and len(chunks) < max_chunks:
            end = min(start + CHUNK_SIZE, len(text))

            # 문장 경계
            if end < len(text):
                for sep in ['. ', '! ', '? ']:
                    last = text[start:end].rfind(sep)
                    if last > CHUNK_SIZE // 2:
                        end = start + last + len(sep)
                        break

            chunk = text[start:end].strip()
            if chunk and len(chunk) > 100:
                chunks.append(chunk)

            start = end - CHUNK_OVERLAP

        return chunks

    def process_book(self, search_term, max_chunks=10, skip_first=2):
        """책 처리. skip_first: 메타데이터 청크 스킵 수."""
        print(f"\nSearching: {search_term}")

        book = self.get_book_content(search_term)
        if not book:
            print("  Book not found")
            return None

        print(f"  Title: {book['title']}")

        text = self.clean_html(book['html'])
        print(f"  Text: {len(text):,} chars")

        chunks = self.chunk_text(text)
        total_chunks = len(chunks)
        chunks = chunks[skip_first:]  # 메타데이터 스킵
        print(f"  Chunks: {total_chunks} (skip {skip_first}, process {min(len(chunks), max_chunks)})")

        all_mentions = []

        for i, chunk in enumerate(chunks[:max_chunks]):
            print(f"  Chunk {i+1}...", end=' ', flush=True)

            # LLM으로 엔티티 추출
            extracted = self.extract_entities_from_chunk(chunk)
            self.stats['chunks_processed'] += 1

            persons = extracted.get('persons', [])
            locations = extracted.get('locations', [])
            events = extracted.get('events', [])

            total_extracted = len(persons) + len(locations) + len(events)
            self.stats['entities_extracted'] += total_extracted

            # DB 매칭
            matched = 0
            for name in persons:
                entity = self.match_entity(name, 'person')
                if entity:
                    matched += 1
                    all_mentions.append({
                        'chunk_idx': i,
                        'name': name,
                        'entity': entity,
                        'context': chunk[:200]
                    })

            for name in locations:
                entity = self.match_entity(name, 'location')
                if entity:
                    matched += 1
                    all_mentions.append({
                        'chunk_idx': i,
                        'name': name,
                        'entity': entity,
                        'context': chunk[:200]
                    })

            for name in events:
                entity = self.match_entity(name, 'event')
                if entity:
                    matched += 1
                    all_mentions.append({
                        'chunk_idx': i,
                        'name': name,
                        'entity': entity,
                        'context': chunk[:200]
                    })

            self.stats['entities_matched'] += matched
            print(f"extracted: {total_extracted}, matched: {matched}")

        # DB 저장
        if not self.dry_run and all_mentions:
            # source 저장
            self.cur.execute("""
                INSERT INTO sources (source_type, title, content_raw)
                VALUES (%s, %s, %s)
                RETURNING id
            """, ('gutenberg', book['title'], text[:5000]))
            source_id = self.cur.fetchone()[0]

            # mentions 저장
            for m in all_mentions:
                etype, eid, qid = m['entity']
                self.cur.execute("""
                    INSERT INTO mentions (source_id, target_type, target_id, evidence_raw)
                    VALUES (%s, %s, %s, %s)
                """, (source_id, etype, eid, m['context']))
                self.stats['mentions_created'] += 1

            self.conn.commit()

        self.stats['books_processed'] += 1

        print(f"\n  Total mentions: {len(all_mentions)}")
        return {'title': book['title'], 'mentions': len(all_mentions)}

    def print_summary(self):
        """통계."""
        print("\n" + "=" * 60)
        print("GUTENBERG LLM EXTRACTION SUMMARY")
        print("=" * 60)
        for k, v in self.stats.items():
            print(f"  {k}: {v:,}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--search', default='')
    parser.add_argument('--book', help='책 제목 검색어')
    parser.add_argument('--max-chunks', type=int, default=10)
    parser.add_argument('--skip-first', type=int, default=2, help='메타데이터 청크 스킵')
    parser.add_argument('--use-openai', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--save', action='store_true')
    args = parser.parse_args()

    extractor = GutenbergLLMExtractor(
        dry_run=args.dry_run or not args.save,
        use_openai=args.use_openai
    )

    if args.book:
        extractor.process_book(args.book, max_chunks=args.max_chunks, skip_first=args.skip_first)
        extractor.print_summary()
    else:
        print("Usage: --book 'search term' [--max-chunks N] [--save]")


if __name__ == '__main__':
    main()
