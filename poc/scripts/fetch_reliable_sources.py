"""
Phase 1.7: Fetch reliable sources for top persons/events/locations.

Fetches full-text content from free, reliable APIs:
  1. Wikipedia (action=parse) - Full article HTML→text
  2. Wikisource (action=parse) - Primary source texts (speeches, letters, treaties)
  3. Internet Archive (_djvu.txt) - Public domain history books

Usage:
  python fetch_reliable_sources.py --step audit
  python fetch_reliable_sources.py --step wikipedia --era classical --limit 50
  python fetch_reliable_sources.py --step wikipedia --entity-type location --limit 100
  python fetch_reliable_sources.py --step wikisource --era classical --limit 20
  python fetch_reliable_sources.py --step archive --era modern --limit 30
  python fetch_reliable_sources.py --step report
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote

import psycopg2
import requests

# Windows UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================================
# Constants
# ============================================================

DB_URL = 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas'

CHECKPOINT_DIR = Path(__file__).parent.parent / 'data' / 'source_fetch'

HEADERS = {
    'User-Agent': 'ChaldeasBot/1.0 (https://www.chaldeas.site; chaldeas.site@gmail.com)'
}

# Rate limit: 1 request/second (Wikimedia guideline)
RATE_LIMIT = 1.0

# Max content length per source
MAX_CONTENT_LEN = 200_000  # 200K chars for wikipedia
MAX_ARCHIVE_LEN = 50_000   # 50K chars for internet archive

# Era definitions (year ranges, BCE as negative)
ERAS = {
    'ancient':      (-3000, -500),
    'classical':    (-500, 500),
    'medieval':     (500, 1500),
    'early_modern': (1500, 1800),
    'modern':       (1800, 2000),
}

# Wikipedia / Wikimedia APIs
WIKIPEDIA_API = 'https://en.wikipedia.org/w/api.php'
WIKISOURCE_API = 'https://en.wikisource.org/w/api.php'
WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
INTERNET_ARCHIVE_API = 'https://archive.org'


# ============================================================
# HTML → Plain Text Converter (stdlib only)
# ============================================================

class HTMLToText(HTMLParser):
    """Convert HTML to clean plain text."""

    SKIP_TAGS = {'script', 'style', 'nav', 'header', 'footer', 'aside',
                 'sup', 'sub', 'table', 'figure', 'figcaption'}
    BLOCK_TAGS = {'p', 'div', 'br', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                  'blockquote', 'pre', 'dt', 'dd', 'tr'}

    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self.skip_depth > 0:
            self.skip_depth -= 1
        if tag in self.BLOCK_TAGS:
            self.parts.append('\n')

    def handle_data(self, data):
        if self.skip_depth == 0:
            self.parts.append(data)

    def get_text(self) -> str:
        text = ''.join(self.parts)
        # Remove [edit] links
        text = re.sub(r'\[edit\]', '', text)
        # Clean excessive whitespace
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()


def html_to_text(html: str) -> str:
    """Convert HTML string to plain text."""
    parser = HTMLToText()
    parser.feed(html)
    return parser.get_text()


def remove_references_sections(html: str) -> str:
    """Remove References, See Also, External Links etc. from Wikipedia HTML."""
    # These sections are typically at the end and not useful for content
    patterns = [
        r'<h2[^>]*>\s*<span[^>]*>(?:References|See also|External links|'
        r'Further reading|Notes|Bibliography|Sources)</span>\s*</h2>.*',
    ]
    for pat in patterns:
        html = re.sub(pat, '', html, flags=re.DOTALL | re.IGNORECASE)
    return html


# ============================================================
# Checkpoint (JSONL)
# ============================================================

def checkpoint_path(step: str, entity_type: str) -> Path:
    """Get checkpoint file path for a step + entity type."""
    return CHECKPOINT_DIR / f'{step}_{entity_type}_checkpoint.jsonl'


def load_checkpoint_ids(filepath: Path) -> set:
    """Load already-processed IDs from JSONL checkpoint."""
    processed = set()
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        processed.add(record['id'])
                    except (json.JSONDecodeError, KeyError):
                        continue
    return processed


def save_checkpoint_line(filepath: Path, record: dict):
    """Append one record to JSONL checkpoint."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')


# ============================================================
# Database Helpers
# ============================================================

def get_db():
    """Get psycopg2 connection."""
    conn = psycopg2.connect(DB_URL)
    conn.set_client_encoding('UTF8')
    return conn


def get_era_filter(era: str):
    """Return (year_start, year_end) for era name, or None for 'all'."""
    if era == 'all':
        return None
    return ERAS.get(era)


def query_top_persons(conn, era_range, limit: int):
    """Query top persons for a given era range."""
    cur = conn.cursor()
    if era_range:
        year_start, year_end = era_range
        cur.execute("""
            SELECT id, name, wikidata_id, birth_year, death_year, importance_score
            FROM persons
            WHERE wikidata_id IS NOT NULL
              AND importance_score IS NOT NULL
              AND (
                (birth_year IS NOT NULL AND birth_year >= %s AND birth_year < %s)
                OR (floruit_start IS NOT NULL AND floruit_start >= %s AND floruit_start < %s)
              )
            ORDER BY importance_score DESC, id
            LIMIT %s
        """, (year_start, year_end, year_start, year_end, limit))
    else:
        cur.execute("""
            SELECT id, name, wikidata_id, birth_year, death_year, importance_score
            FROM persons
            WHERE wikidata_id IS NOT NULL
              AND importance_score IS NOT NULL
            ORDER BY importance_score DESC, id
            LIMIT %s
        """, (limit,))
    rows = cur.fetchall()
    cur.close()
    return [
        {'id': r[0], 'name': r[1], 'wikidata_id': r[2],
         'birth_year': r[3], 'death_year': r[4], 'importance_score': r[5]}
        for r in rows
    ]


def query_top_events(conn, era_range, limit: int):
    """Query top events for a given era range."""
    cur = conn.cursor()
    if era_range:
        year_start, year_end = era_range
        cur.execute("""
            SELECT id, title, wikidata_id, date_start, date_end, importance
            FROM events
            WHERE wikidata_id IS NOT NULL
              AND importance IS NOT NULL
              AND date_start IS NOT NULL
              AND date_start >= %s AND date_start < %s
            ORDER BY importance DESC, id
            LIMIT %s
        """, (year_start, year_end, limit))
    else:
        cur.execute("""
            SELECT id, title, wikidata_id, date_start, date_end, importance
            FROM events
            WHERE wikidata_id IS NOT NULL
              AND importance IS NOT NULL
            ORDER BY importance DESC, id
            LIMIT %s
        """, (limit,))
    rows = cur.fetchall()
    cur.close()
    return [
        {'id': r[0], 'title': r[1], 'wikidata_id': r[2],
         'date_start': r[3], 'date_end': r[4], 'importance': r[5]}
        for r in rows
    ]


def query_top_locations(conn, limit: int):
    """Query top locations ranked by event count (proxy for importance)."""
    cur = conn.cursor()
    cur.execute("""
        SELECT l.id, l.name, l.wikidata_id, l.location_type, l.country,
               COUNT(el.event_id) as event_count
        FROM locations l
        LEFT JOIN event_locations el ON el.location_id = l.id
        WHERE l.wikidata_id IS NOT NULL
        GROUP BY l.id
        ORDER BY COUNT(el.event_id) DESC, l.id
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    return [
        {'id': r[0], 'name': r[1], 'wikidata_id': r[2],
         'location_type': r[3], 'country': r[4], 'event_count': r[5]}
        for r in rows
    ]


def count_sources_for_entity(conn, entity_type: str, entity_id: int) -> dict:
    """Count sources linked to an entity, grouped by source_type."""
    cur = conn.cursor()
    if entity_type == 'person':
        cur.execute("""
            SELECT s.source_type, COUNT(*), SUM(CASE WHEN LENGTH(s.content_raw) > 500 THEN 1 ELSE 0 END)
            FROM person_sources ps
            JOIN sources s ON s.id = ps.source_id
            WHERE ps.person_id = %s
            GROUP BY s.source_type
        """, (entity_id,))
    elif entity_type == 'location':
        cur.execute("""
            SELECT s.source_type, COUNT(*), SUM(CASE WHEN LENGTH(s.content_raw) > 500 THEN 1 ELSE 0 END)
            FROM location_sources ls
            JOIN sources s ON s.id = ls.source_id
            WHERE ls.location_id = %s
            GROUP BY s.source_type
        """, (entity_id,))
    else:
        cur.execute("""
            SELECT s.source_type, COUNT(*), SUM(CASE WHEN LENGTH(s.content_raw) > 500 THEN 1 ELSE 0 END)
            FROM event_sources es
            JOIN sources s ON s.id = es.source_id
            WHERE es.event_id = %s
            GROUP BY s.source_type
        """, (entity_id,))
    rows = cur.fetchall()
    cur.close()
    return {r[0]: {'count': r[1], 'with_content': int(r[2] or 0)} for r in rows}


def insert_source(conn, source_type: str, title: str, content_raw: str,
                  url: str = None, language: str = 'en', reliability: int = 3,
                  author: str = None, original_year: int = None,
                  wikidata_id: str = None) -> int | None:
    """Insert a source record and return its ID. Returns None if duplicate URL exists."""
    cur = conn.cursor()

    # Check for duplicate by URL
    if url:
        cur.execute("SELECT id FROM sources WHERE url = %s", (url,))
        existing = cur.fetchone()
        if existing:
            cur.close()
            return existing[0]

    word_count = len(content_raw.split()) if content_raw else 0

    cur.execute("""
        INSERT INTO sources (source_type, title, content_raw, url, language,
                            reliability, author, original_year, word_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (source_type, title, content_raw, url, language,
          reliability, author, original_year, word_count))

    source_id = cur.fetchone()[0]
    cur.close()
    return source_id


def link_person_source(conn, person_id: int, source_id: int):
    """Link a person to a source (idempotent)."""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO person_sources (person_id, source_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
    """, (person_id, source_id))
    cur.close()


def link_event_source(conn, event_id: int, source_id: int):
    """Link an event to a source (idempotent)."""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO event_sources (event_id, source_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
    """, (event_id, source_id))
    cur.close()


def link_location_source(conn, location_id: int, source_id: int):
    """Link a location to a source (idempotent)."""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO location_sources (location_id, source_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
    """, (location_id, source_id))
    cur.close()


# ============================================================
# API Helpers
# ============================================================

def qid_to_wikipedia_title(qid: str, session: requests.Session) -> str | None:
    """Convert Wikidata QID to English Wikipedia article title."""
    try:
        resp = session.get(WIKIDATA_API, params={
            'action': 'wbgetentities',
            'ids': qid,
            'props': 'sitelinks',
            'sitefilter': 'enwiki',
            'format': 'json',
        }, headers=HEADERS, timeout=30)

        if resp.status_code == 429:
            time.sleep(5)
            return None

        if resp.status_code == 200:
            data = resp.json()
            entities = data.get('entities', {})
            if qid in entities:
                sitelinks = entities[qid].get('sitelinks', {})
                if 'enwiki' in sitelinks:
                    return sitelinks['enwiki']['title']
    except Exception as e:
        print(f"  Error getting wiki title for {qid}: {e}")
    return None


def qid_to_wikisource_title(qid: str, session: requests.Session) -> str | None:
    """Convert Wikidata QID to English Wikisource author page title."""
    try:
        resp = session.get(WIKIDATA_API, params={
            'action': 'wbgetentities',
            'ids': qid,
            'props': 'sitelinks',
            'sitefilter': 'enwikisource',
            'format': 'json',
        }, headers=HEADERS, timeout=30)

        if resp.status_code == 200:
            data = resp.json()
            entities = data.get('entities', {})
            if qid in entities:
                sitelinks = entities[qid].get('sitelinks', {})
                if 'enwikisource' in sitelinks:
                    return sitelinks['enwikisource']['title']
    except Exception as e:
        print(f"  Error getting wikisource title for {qid}: {e}")
    return None


def fetch_wikipedia_fulltext(title: str, session: requests.Session) -> tuple[str | None, str | None]:
    """Fetch full Wikipedia article text via action=parse API.

    Returns (text, url) tuple.
    """
    try:
        resp = session.get(WIKIPEDIA_API, params={
            'action': 'parse',
            'page': title,
            'prop': 'text',
            'format': 'json',
            'disabletoc': '1',
            'disableeditsection': '1',
        }, headers=HEADERS, timeout=60)

        if resp.status_code == 429:
            time.sleep(5)
            return None, None

        if resp.status_code == 200:
            data = resp.json()
            if 'parse' in data:
                html = data['parse']['text']['*']
                html = remove_references_sections(html)
                text = html_to_text(html)

                if len(text) > MAX_CONTENT_LEN:
                    text = text[:MAX_CONTENT_LEN]

                url = f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
                return text, url

            if 'error' in data:
                print(f"  Wikipedia API error: {data['error'].get('info', 'unknown')}")
    except Exception as e:
        print(f"  Error fetching Wikipedia for '{title}': {e}")
    return None, None


def fetch_wikisource_works(author_title: str, session: requests.Session) -> list[dict]:
    """Get list of works from a Wikisource Author: page.

    Returns list of {'title': ..., 'url': ...} dicts.
    """
    # Prefixes to skip (encyclopedia articles, not primary works)
    SKIP_PREFIXES = (
        'Portal:', 'Wikisource:', 'Author:', 'Category:',
        '1911 Encyclop', 'Catholic Encyclopedia', 'Encyclop',
        'Dictionary of National Biography', 'A Short Biographical Dictionary',
        'The New Student', 'Collier',
    )
    works = []
    try:
        # Get links from the author page
        resp = session.get(WIKISOURCE_API, params={
            'action': 'parse',
            'page': author_title,
            'prop': 'links',
            'format': 'json',
        }, headers=HEADERS, timeout=30)

        if resp.status_code == 200:
            data = resp.json()
            if 'parse' in data:
                links = data['parse'].get('links', [])
                for link in links:
                    # Only include main namespace pages (ns=0) that exist
                    if link.get('ns', -1) == 0 and 'exists' in link:
                        title = link.get('*', '')
                        if title and not title.startswith(SKIP_PREFIXES):
                            works.append({
                                'title': title,
                                'url': f"https://en.wikisource.org/wiki/{quote(title.replace(' ', '_'))}"
                            })
    except Exception as e:
        print(f"  Error getting Wikisource works for '{author_title}': {e}")

    return works[:10]  # Limit to 10 works per author


def search_wikisource(query: str, session: requests.Session, max_results: int = 10) -> list[dict]:
    """Search Wikisource by keyword for texts ABOUT a person/event.

    Uses the MediaWiki search API with multiple query variations to
    find all relevant texts - biographies, histories, primary sources, etc.

    Returns list of {'title': ..., 'url': ..., 'snippet': ..., 'wordcount': ...} dicts.
    """
    SKIP_PREFIXES = (
        'Portal:', 'Wikisource:', 'Author:', 'Category:', 'Page:',
        'Translation:', 'Index:', 'MediaWiki:',
    )
    SKIP_CONTAINS = (
        '1911 Encyclopædia Britannica',
        'Catholic Encyclopedia',
        'A Short Biographical Dictionary',
        'The New Student',
        'Collier\'s New Encyclopedia',
        'Nuttall Encyclop',
        'The American Cyclopædia',
        'Easton\'s Bible Dictionary',
        'Appletons\' Cyclopædia',
    )

    seen_titles = set()
    results = []

    # Try multiple search queries for broader coverage
    queries = [
        query,                      # exact name
        f'{query} history',         # historical context
        f'"{query}"',              # exact phrase match
    ]

    for q in queries:
        if len(results) >= max_results:
            break

        try:
            resp = session.get(WIKISOURCE_API, params={
                'action': 'query',
                'list': 'search',
                'srsearch': q,
                'srnamespace': '0',
                'srlimit': '20',
                'srprop': 'snippet|titlesnippet|wordcount',
                'format': 'json',
            }, headers=HEADERS, timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                search_results = data.get('query', {}).get('search', [])
                for sr in search_results:
                    title = sr.get('title', '')
                    wordcount = sr.get('wordcount', 0)

                    if title in seen_titles:
                        continue
                    seen_titles.add(title)

                    if title.startswith(SKIP_PREFIXES):
                        continue
                    if any(skip in title for skip in SKIP_CONTAINS):
                        continue
                    if wordcount < 500:
                        continue

                    results.append({
                        'title': title,
                        'url': f"https://en.wikisource.org/wiki/{quote(title.replace(' ', '_'))}",
                        'snippet': sr.get('snippet', ''),
                        'wordcount': wordcount,
                    })

                    if len(results) >= max_results:
                        break

            time.sleep(RATE_LIMIT)

        except Exception as e:
            print(f"  Error searching Wikisource for '{q}': {e}")

    # Sort by word count descending - prefer longer, more substantial texts
    results.sort(key=lambda x: x['wordcount'], reverse=True)
    return results[:max_results]


def fetch_wikisource_text(title: str, session: requests.Session) -> str | None:
    """Fetch full text of a Wikisource page via action=parse."""
    try:
        resp = session.get(WIKISOURCE_API, params={
            'action': 'parse',
            'page': title,
            'prop': 'text',
            'format': 'json',
            'disabletoc': '1',
            'disableeditsection': '1',
        }, headers=HEADERS, timeout=60)

        if resp.status_code == 429:
            time.sleep(5)
            return None

        if resp.status_code == 200:
            data = resp.json()
            if 'parse' in data:
                html = data['parse']['text']['*']
                text = html_to_text(html)
                if len(text) > MAX_CONTENT_LEN:
                    text = text[:MAX_CONTENT_LEN]
                return text
    except Exception as e:
        print(f"  Error fetching Wikisource '{title}': {e}")
    return None


def search_internet_archive(query: str, session: requests.Session) -> list[dict]:
    """Search Internet Archive for public domain texts with downloadable full text.

    Returns list of {'identifier': ..., 'title': ..., 'year': ...}.
    """
    results = []
    try:
        # Target public domain books published before 1930 that have DjVu text
        # Exclude lending library items (they don't allow text download)
        search_q = (
            f'{query} AND mediatype:texts'
            f' AND -lending___status:is_lendable'
            f' AND date:[1800-01-01 TO 1930-12-31]'
            f' AND format:(DjVuTXT OR "Text PDF")'
        )
        resp = session.get(f'{INTERNET_ARCHIVE_API}/advancedsearch.php', params={
            'q': search_q,
            'fl[]': ['identifier', 'title', 'year', 'language'],
            'rows': 10,
            'page': 1,
            'output': 'json',
            'sort[]': 'downloads desc',
        }, headers=HEADERS, timeout=30)

        if resp.status_code == 200:
            data = resp.json()
            docs = data.get('response', {}).get('docs', [])
            for doc in docs:
                lang = doc.get('language', '')
                # Accept English or unspecified language
                if isinstance(lang, list):
                    lang = lang[0] if lang else ''
                if lang and lang.lower() not in ('english', 'eng', 'en', ''):
                    continue
                results.append({
                    'identifier': doc.get('identifier', ''),
                    'title': doc.get('title', ''),
                    'year': doc.get('year'),
                })
    except Exception as e:
        print(f"  Error searching Internet Archive for '{query}': {e}")

    return results[:3]  # Top 3 results


def fetch_internet_archive_text(identifier: str, session: requests.Session) -> str | None:
    """Fetch full text from Internet Archive via _djvu.txt file."""
    url = f'{INTERNET_ARCHIVE_API}/download/{identifier}/{identifier}_djvu.txt'
    try:
        resp = session.get(url, headers=HEADERS, timeout=120, stream=True)

        if resp.status_code == 200:
            # Stream and limit size
            chunks = []
            total = 0
            for chunk in resp.iter_content(chunk_size=8192, decode_unicode=True):
                if chunk:
                    chunks.append(chunk)
                    total += len(chunk)
                    if total > MAX_ARCHIVE_LEN:
                        break
            text = ''.join(chunks)
            if len(text) > MAX_ARCHIVE_LEN:
                text = text[:MAX_ARCHIVE_LEN]
            # Clean up OCR artifacts
            text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
            return text if len(text) > 200 else None  # Skip tiny results

        # Try plain .txt fallback
        url2 = f'{INTERNET_ARCHIVE_API}/download/{identifier}/{identifier}.txt'
        resp2 = session.get(url2, headers=HEADERS, timeout=120, stream=True)
        if resp2.status_code == 200:
            chunks = []
            total = 0
            for chunk in resp2.iter_content(chunk_size=8192, decode_unicode=True):
                if chunk:
                    chunks.append(chunk)
                    total += len(chunk)
                    if total > MAX_ARCHIVE_LEN:
                        break
            text = ''.join(chunks)
            if len(text) > MAX_ARCHIVE_LEN:
                text = text[:MAX_ARCHIVE_LEN]
            text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
            return text if len(text) > 200 else None

    except Exception as e:
        print(f"  Error fetching IA text for '{identifier}': {e}")
    return None


# ============================================================
# Step: Audit
# ============================================================

def step_audit(conn, era: str, limit: int):
    """Audit source coverage for top persons and events."""
    print("=" * 70)
    print("  SOURCE COVERAGE AUDIT")
    print("=" * 70)

    eras_to_check = [era] if era != 'all' else list(ERAS.keys())

    for era_name in eras_to_check:
        era_range = ERAS[era_name]
        print(f"\n{'─' * 60}")
        print(f"  ERA: {era_name.upper()} ({era_range[0]} ~ {era_range[1]})")
        print(f"{'─' * 60}")

        # --- Persons ---
        persons = query_top_persons(conn, era_range, limit)
        print(f"\n  TOP {len(persons)} PERSONS:")
        print(f"  {'Name':<35} {'Imp':>4} {'Born':>8} {'Wiki':>4} {'WkSrc':>5} {'IA':>3} {'Other':>5}")
        print(f"  {'─'*35} {'─'*4} {'─'*8} {'─'*4} {'─'*5} {'─'*3} {'─'*5}")

        persons_missing = 0
        for p in persons:
            sources = count_sources_for_entity(conn, 'person', p['id'])
            wiki_cnt = sources.get('wikipedia', {}).get('with_content', 0)
            wksrc_cnt = sources.get('wikisource', {}).get('with_content', 0)
            ia_cnt = sources.get('internet_archive', {}).get('with_content', 0)
            other_cnt = sum(v['count'] for k, v in sources.items()
                          if k not in ('wikipedia', 'wikisource', 'internet_archive'))

            birth_str = str(p['birth_year']) if p['birth_year'] else '?'
            if p['birth_year'] and p['birth_year'] < 0:
                birth_str = f"{abs(p['birth_year'])} BCE"

            marker = '' if wiki_cnt > 0 else ' [MISSING]'
            if wiki_cnt == 0:
                persons_missing += 1

            print(f"  {p['name']:<35} {p['importance_score']:>4} {birth_str:>8} "
                  f"{wiki_cnt:>4} {wksrc_cnt:>5} {ia_cnt:>3} {other_cnt:>5}{marker}")

        print(f"\n  Summary: {len(persons) - persons_missing}/{len(persons)} have Wikipedia sources")

        # --- Events ---
        events = query_top_events(conn, era_range, limit)
        print(f"\n  TOP {len(events)} EVENTS:")
        print(f"  {'Title':<40} {'Imp':>3} {'Year':>8} {'Wiki':>4} {'Other':>5}")
        print(f"  {'─'*40} {'─'*3} {'─'*8} {'─'*4} {'─'*5}")

        events_missing = 0
        for e in events:
            sources = count_sources_for_entity(conn, 'event', e['id'])
            wiki_cnt = sources.get('wikipedia', {}).get('with_content', 0)
            other_cnt = sum(v['count'] for k, v in sources.items() if k != 'wikipedia')

            year_str = str(e['date_start']) if e['date_start'] else '?'
            if e['date_start'] and e['date_start'] < 0:
                year_str = f"{abs(e['date_start'])} BCE"

            marker = '' if wiki_cnt > 0 else ' [MISSING]'
            if wiki_cnt == 0:
                events_missing += 1

            title_display = e['title'][:40]
            print(f"  {title_display:<40} {e['importance']:>3} {year_str:>8} "
                  f"{wiki_cnt:>4} {other_cnt:>5}{marker}")

        print(f"\n  Summary: {len(events) - events_missing}/{len(events)} have Wikipedia sources")

    # --- Locations (not era-based, ranked by event count) ---
    print(f"\n{'─' * 60}")
    print(f"  TOP LOCATIONS (by event count)")
    print(f"{'─' * 60}")

    locations = query_top_locations(conn, limit)
    print(f"\n  {'Name':<30} {'Events':>6} {'Wiki':>4} {'Other':>5}")
    print(f"  {'─'*30} {'─'*6} {'─'*4} {'─'*5}")

    locs_missing = 0
    for loc in locations:
        sources = count_sources_for_entity(conn, 'location', loc['id'])
        wiki_cnt = sources.get('wikipedia', {}).get('with_content', 0)
        other_cnt = sum(v['count'] for k, v in sources.items() if k != 'wikipedia')

        marker = '' if wiki_cnt > 0 else ' [MISSING]'
        if wiki_cnt == 0:
            locs_missing += 1

        print(f"  {loc['name']:<30} {loc['event_count']:>6} "
              f"{wiki_cnt:>4} {other_cnt:>5}{marker}")

    print(f"\n  Summary: {len(locations) - locs_missing}/{len(locations)} have Wikipedia sources")

    print(f"\n{'=' * 70}")
    print("  Audit complete. Review above and proceed with --step wikipedia/wikisource/archive.")
    print(f"{'=' * 70}")


# ============================================================
# Step: Wikipedia
# ============================================================

def step_wikipedia(conn, era: str, limit: int, entity_types: list[str]):
    """Fetch full Wikipedia articles for top entities."""
    session = requests.Session()

    for etype in entity_types:
        era_range = get_era_filter(era)
        ckpt_file = checkpoint_path('wikipedia', f'{era}_{etype}')
        processed_ids = load_checkpoint_ids(ckpt_file)

        if etype == 'person':
            entities = query_top_persons(conn, era_range, limit)
            label_key, qid_key, id_key = 'name', 'wikidata_id', 'id'
        elif etype == 'location':
            # Locations don't have era filtering - use global ranking by event_count
            entities = query_top_locations(conn, limit)
            label_key, qid_key, id_key = 'name', 'wikidata_id', 'id'
        else:
            entities = query_top_events(conn, era_range, limit)
            label_key, qid_key, id_key = 'title', 'wikidata_id', 'id'

        # Filter already processed
        entities = [e for e in entities if e[id_key] not in processed_ids]

        print(f"\n{'=' * 60}")
        print(f"  WIKIPEDIA: {etype.upper()}s ({era}) - {len(entities)} to process")
        print(f"{'=' * 60}")

        success, skipped, failed = 0, 0, 0

        for i, entity in enumerate(entities):
            eid = entity[id_key]
            name = entity[label_key]
            qid = entity[qid_key]

            print(f"\n[{i+1}/{len(entities)}] {name} ({qid})")

            # Check if already has a wikipedia source with substantial content
            existing = count_sources_for_entity(conn, etype, eid)
            wiki_content = existing.get('wikipedia', {}).get('with_content', 0)
            if wiki_content > 0:
                print(f"  Already has Wikipedia source with content, skipping")
                save_checkpoint_line(ckpt_file, {
                    'id': eid, 'name': name, 'status': 'already_exists',
                    'timestamp': datetime.now().isoformat()
                })
                skipped += 1
                continue

            # Step 1: QID → Wikipedia title
            wiki_title = qid_to_wikipedia_title(qid, session)
            time.sleep(RATE_LIMIT)

            if not wiki_title:
                print(f"  No English Wikipedia article found")
                save_checkpoint_line(ckpt_file, {
                    'id': eid, 'name': name, 'status': 'no_wiki_title',
                    'timestamp': datetime.now().isoformat()
                })
                failed += 1
                continue

            print(f"  Wikipedia: {wiki_title}")

            # Step 2: Fetch full text
            text, url = fetch_wikipedia_fulltext(wiki_title, session)
            time.sleep(RATE_LIMIT)

            if not text or len(text) < 100:
                print(f"  No meaningful content retrieved")
                save_checkpoint_line(ckpt_file, {
                    'id': eid, 'name': name, 'wiki_title': wiki_title,
                    'status': 'no_content',
                    'timestamp': datetime.now().isoformat()
                })
                failed += 1
                continue

            print(f"  Got {len(text):,} chars")

            # Step 3: Insert source
            source_id = insert_source(
                conn,
                source_type='wikipedia',
                title=f"{wiki_title} - Wikipedia",
                content_raw=text,
                url=url,
                language='en',
                reliability=3,
            )

            # Step 4: Link to entity
            if etype == 'person':
                link_person_source(conn, eid, source_id)
            elif etype == 'location':
                link_location_source(conn, eid, source_id)
            else:
                link_event_source(conn, eid, source_id)

            conn.commit()

            save_checkpoint_line(ckpt_file, {
                'id': eid, 'name': name, 'wiki_title': wiki_title,
                'source_id': source_id, 'chars': len(text),
                'status': 'success',
                'timestamp': datetime.now().isoformat()
            })

            success += 1
            print(f"  Saved source #{source_id} and linked to {etype} #{eid}")

        print(f"\n{'─' * 40}")
        print(f"  Results: {success} success, {skipped} skipped, {failed} failed")
        print(f"{'─' * 40}")


# ============================================================
# Step: Wikisource
# ============================================================

def step_wikisource(conn, era: str, limit: int, entity_types: list[str] = None):
    """Fetch source texts from Wikisource for top persons and events.

    Uses SEARCH-based approach: searches Wikisource for texts ABOUT each
    person/event, not just works BY them. This captures biographies,
    histories, analyses, treaties, etc.
    """
    if entity_types is None:
        entity_types = ['person']

    session = requests.Session()

    for etype in entity_types:
        era_range = get_era_filter(era)
        ckpt_file = checkpoint_path('wikisource_v2', f'{era}_{etype}')
        processed_ids = load_checkpoint_ids(ckpt_file)

        if etype == 'person':
            entities = query_top_persons(conn, era_range, limit)
            label_key = 'name'
        elif etype == 'location':
            entities = query_top_locations(conn, limit)
            label_key = 'name'
        else:
            entities = query_top_events(conn, era_range, limit)
            label_key = 'title'

        entities = [e for e in entities if e['id'] not in processed_ids]

        print(f"\n{'=' * 60}")
        print(f"  WIKISOURCE SEARCH: {etype.upper()}s ({era}) - {len(entities)} to process")
        print(f"{'=' * 60}")

        success, skipped, failed = 0, 0, 0

        for i, entity in enumerate(entities):
            eid = entity['id']
            name = entity[label_key]

            print(f"\n[{i+1}/{len(entities)}] {name}")

            # Check if already has wikisource content (3+ sources = enough)
            existing = count_sources_for_entity(conn, etype, eid)
            ws_content = existing.get('wikisource', {}).get('with_content', 0)
            if ws_content >= 3:
                print(f"  Already has {ws_content} Wikisource sources, skipping")
                save_checkpoint_line(ckpt_file, {
                    'id': eid, 'name': name, 'status': 'already_exists',
                    'timestamp': datetime.now().isoformat()
                })
                skipped += 1
                continue

            # Search Wikisource for texts about this entity
            search_results = search_wikisource(name, session, max_results=8)
            time.sleep(RATE_LIMIT)

            if not search_results:
                print(f"  No Wikisource results found")
                save_checkpoint_line(ckpt_file, {
                    'id': eid, 'name': name, 'status': 'no_results',
                    'timestamp': datetime.now().isoformat()
                })
                failed += 1
                continue

            print(f"  Found {len(search_results)} search results")

            works_saved = 0
            for result in search_results[:5]:  # Max 5 texts per entity
                work_title = result['title']
                work_url = result['url']

                print(f"    Fetching: {work_title} ({result['wordcount']:,} words)")

                text = fetch_wikisource_text(work_title, session)
                time.sleep(RATE_LIMIT)

                if not text or len(text) < 200:
                    print(f"    Too short or empty, skipping")
                    continue

                print(f"    Got {len(text):,} chars")

                source_id = insert_source(
                    conn,
                    source_type='wikisource',
                    title=f"{work_title} - Wikisource",
                    content_raw=text,
                    url=work_url,
                    language='en',
                    reliability=4,
                )

                if etype == 'person':
                    link_person_source(conn, eid, source_id)
                elif etype == 'location':
                    link_location_source(conn, eid, source_id)
                else:
                    link_event_source(conn, eid, source_id)

                conn.commit()
                works_saved += 1
                print(f"    Saved source #{source_id}")

            save_checkpoint_line(ckpt_file, {
                'id': eid, 'name': name,
                'results_found': len(search_results), 'works_saved': works_saved,
                'status': 'success' if works_saved > 0 else 'no_usable_works',
                'timestamp': datetime.now().isoformat()
            })

            if works_saved > 0:
                success += 1
            else:
                failed += 1

        print(f"\n{'─' * 40}")
        print(f"  Results: {success} success, {skipped} skipped, {failed} failed")
        print(f"{'─' * 40}")


# ============================================================
# Step: Internet Archive
# ============================================================

def step_archive(conn, era: str, limit: int, entity_types: list[str]):
    """Fetch texts from Internet Archive for top entities."""
    session = requests.Session()

    for etype in entity_types:
        era_range = get_era_filter(era)
        ckpt_file = checkpoint_path('archive', f'{era}_{etype}')
        processed_ids = load_checkpoint_ids(ckpt_file)

        if etype == 'person':
            entities = query_top_persons(conn, era_range, limit)
            label_key = 'name'
        elif etype == 'location':
            entities = query_top_locations(conn, limit)
            label_key = 'name'
        else:
            entities = query_top_events(conn, era_range, limit)
            label_key = 'title'

        entities = [e for e in entities if e['id'] not in processed_ids]

        print(f"\n{'=' * 60}")
        print(f"  INTERNET ARCHIVE: {etype.upper()}s ({era}) - {len(entities)} to process")
        print(f"{'=' * 60}")

        success, skipped, failed = 0, 0, 0

        for i, entity in enumerate(entities):
            eid = entity['id']
            name = entity[label_key]

            print(f"\n[{i+1}/{len(entities)}] {name}")

            # Check if already has IA content
            existing = count_sources_for_entity(conn, etype, eid)
            ia_content = existing.get('internet_archive', {}).get('with_content', 0)
            if ia_content > 0:
                print(f"  Already has Internet Archive content, skipping")
                save_checkpoint_line(ckpt_file, {
                    'id': eid, 'name': name, 'status': 'already_exists',
                    'timestamp': datetime.now().isoformat()
                })
                skipped += 1
                continue

            # Search IA
            search_query = f'"{name}" subject:(biography OR history)'
            results = search_internet_archive(search_query, session)
            time.sleep(RATE_LIMIT)

            if not results:
                # Try simpler search
                search_query = f'"{name}" history'
                results = search_internet_archive(search_query, session)
                time.sleep(RATE_LIMIT)

            if not results:
                print(f"  No results on Internet Archive")
                save_checkpoint_line(ckpt_file, {
                    'id': eid, 'name': name, 'status': 'no_results',
                    'timestamp': datetime.now().isoformat()
                })
                failed += 1
                continue

            print(f"  Found {len(results)} results")

            books_saved = 0
            for result in results[:2]:  # Max 2 books per entity
                identifier = result['identifier']
                book_title = result['title']
                book_year = result.get('year')

                print(f"    Fetching: {book_title} ({identifier})")

                text = fetch_internet_archive_text(identifier, session)
                time.sleep(RATE_LIMIT)

                if not text:
                    print(f"    No text available, skipping")
                    continue

                print(f"    Got {len(text):,} chars")

                ia_url = f"https://archive.org/details/{identifier}"
                source_id = insert_source(
                    conn,
                    source_type='internet_archive',
                    title=f"{book_title[:450]} - Internet Archive",
                    content_raw=text,
                    url=ia_url,
                    language='en',
                    reliability=3,
                    original_year=int(book_year) if book_year else None,
                )

                if etype == 'person':
                    link_person_source(conn, eid, source_id)
                elif etype == 'location':
                    link_location_source(conn, eid, source_id)
                else:
                    link_event_source(conn, eid, source_id)

                conn.commit()
                books_saved += 1
                print(f"    Saved source #{source_id}")

            save_checkpoint_line(ckpt_file, {
                'id': eid, 'name': name,
                'results_found': len(results), 'books_saved': books_saved,
                'status': 'success' if books_saved > 0 else 'no_usable_texts',
                'timestamp': datetime.now().isoformat()
            })

            if books_saved > 0:
                success += 1
            else:
                failed += 1

        print(f"\n{'─' * 40}")
        print(f"  Results: {success} success, {skipped} skipped, {failed} failed")
        print(f"{'─' * 40}")


# ============================================================
# Step: Report
# ============================================================

def step_report(conn, era: str, limit: int):
    """Generate coverage report."""
    cur = conn.cursor()

    print("=" * 70)
    print("  SOURCE COVERAGE REPORT")
    print("=" * 70)

    # Overall source stats
    cur.execute("""
        SELECT source_type, COUNT(*) as cnt,
               AVG(LENGTH(content_raw)) as avg_len,
               SUM(word_count) as total_words
        FROM sources
        GROUP BY source_type
        ORDER BY cnt DESC
    """)
    rows = cur.fetchall()

    print(f"\n  SOURCE TYPE SUMMARY:")
    print(f"  {'Type':<20} {'Count':>8} {'Avg Len':>10} {'Total Words':>14}")
    print(f"  {'─'*20} {'─'*8} {'─'*10} {'─'*14}")
    for r in rows:
        avg_len = int(r[2]) if r[2] else 0
        total_words = int(r[3]) if r[3] else 0
        print(f"  {r[0]:<20} {r[1]:>8,} {avg_len:>10,} {total_words:>14,}")

    # Per-era coverage for top entities
    eras_to_check = [era] if era != 'all' else list(ERAS.keys())

    for era_name in eras_to_check:
        era_range = ERAS[era_name]
        print(f"\n  {'─' * 50}")
        print(f"  ERA: {era_name.upper()} ({era_range[0]} ~ {era_range[1]})")

        # Person coverage
        persons = query_top_persons(conn, era_range, limit)
        p_with_wiki = 0
        p_with_ws = 0
        p_with_ia = 0
        p_with_any = 0

        for p in persons:
            sources = count_sources_for_entity(conn, 'person', p['id'])
            has_wiki = sources.get('wikipedia', {}).get('with_content', 0) > 0
            has_ws = sources.get('wikisource', {}).get('with_content', 0) > 0
            has_ia = sources.get('internet_archive', {}).get('with_content', 0) > 0
            if has_wiki:
                p_with_wiki += 1
            if has_ws:
                p_with_ws += 1
            if has_ia:
                p_with_ia += 1
            if has_wiki or has_ws or has_ia:
                p_with_any += 1

        total_p = len(persons)
        print(f"  Persons (top {total_p}):")
        print(f"    Wikipedia:        {p_with_wiki}/{total_p} ({p_with_wiki/max(total_p,1)*100:.0f}%)")
        print(f"    Wikisource:       {p_with_ws}/{total_p} ({p_with_ws/max(total_p,1)*100:.0f}%)")
        print(f"    Internet Archive: {p_with_ia}/{total_p} ({p_with_ia/max(total_p,1)*100:.0f}%)")
        print(f"    Any source:       {p_with_any}/{total_p} ({p_with_any/max(total_p,1)*100:.0f}%)")

        # Event coverage
        events = query_top_events(conn, era_range, limit)
        e_with_wiki = 0
        e_with_any = 0

        for e in events:
            sources = count_sources_for_entity(conn, 'event', e['id'])
            has_wiki = sources.get('wikipedia', {}).get('with_content', 0) > 0
            if has_wiki:
                e_with_wiki += 1
            if any(v.get('with_content', 0) > 0 for v in sources.values()):
                e_with_any += 1

        total_e = len(events)
        print(f"  Events (top {total_e}):")
        print(f"    Wikipedia:        {e_with_wiki}/{total_e} ({e_with_wiki/max(total_e,1)*100:.0f}%)")
        print(f"    Any source:       {e_with_any}/{total_e} ({e_with_any/max(total_e,1)*100:.0f}%)")

    # Location coverage (not era-based)
    print(f"\n  {'─' * 50}")
    print(f"  LOCATIONS (top {limit} by event count)")
    locations = query_top_locations(conn, limit)
    l_with_wiki = 0
    l_with_any = 0
    for loc in locations:
        sources = count_sources_for_entity(conn, 'location', loc['id'])
        has_wiki = sources.get('wikipedia', {}).get('with_content', 0) > 0
        if has_wiki:
            l_with_wiki += 1
        if any(v.get('with_content', 0) > 0 for v in sources.values()):
            l_with_any += 1
    total_l = len(locations)
    print(f"    Wikipedia:        {l_with_wiki}/{total_l} ({l_with_wiki/max(total_l,1)*100:.0f}%)")
    print(f"    Any source:       {l_with_any}/{total_l} ({l_with_any/max(total_l,1)*100:.0f}%)")

    # Phase 3 readiness check
    print(f"\n{'=' * 70}")
    print("  PHASE 3 READINESS CHECK")
    print(f"{'=' * 70}")

    cur.execute("""
        SELECT COUNT(DISTINCT ps.person_id)
        FROM person_sources ps
        JOIN sources s ON s.id = ps.source_id
        WHERE LENGTH(s.content_raw) > 500
    """)
    persons_with_sources = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(DISTINCT es.event_id)
        FROM event_sources es
        JOIN sources s ON s.id = es.source_id
        WHERE LENGTH(s.content_raw) > 500
    """)
    events_with_sources = cur.fetchone()[0]

    print(f"  Persons with substantial sources: {persons_with_sources:,}")
    print(f"  Events with substantial sources:  {events_with_sources:,}")
    print(f"  Ready for Phase 3 curation: {'YES' if persons_with_sources > 100 else 'NEEDS MORE DATA'}")

    cur.close()


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='Phase 1.7: Fetch reliable sources for top persons/events',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Steps:
  audit       Report source coverage gaps
  wikipedia   Fetch full Wikipedia articles (action=parse)
  wikisource  Fetch primary source texts from Wikisource
  archive     Fetch public domain texts from Internet Archive
  report      Generate coverage report

Eras:
  ancient (-3000~-500), classical (-500~500), medieval (500~1500),
  early_modern (1500~1800), modern (1800~2000), all

Examples:
  python fetch_reliable_sources.py --step audit
  python fetch_reliable_sources.py --step wikipedia --era classical --limit 50
  python fetch_reliable_sources.py --step wikisource --era ancient --limit 20
  python fetch_reliable_sources.py --step archive --era all --limit 30
  python fetch_reliable_sources.py --step report
        """
    )
    parser.add_argument('--step', required=True,
                        choices=['audit', 'wikipedia', 'wikisource', 'archive', 'report'],
                        help='Step to execute')
    parser.add_argument('--era', default='all',
                        choices=['ancient', 'classical', 'medieval', 'early_modern', 'modern', 'all'],
                        help='Era to process (default: all)')
    parser.add_argument('--limit', type=int, default=50,
                        help='Max entities per era (default: 50)')
    parser.add_argument('--entity-type', default='all',
                        choices=['person', 'event', 'location', 'all'],
                        help='Entity type to process (default: all)')
    parser.add_argument('--reset', action='store_true',
                        help='Reset checkpoint for this step/era')

    args = parser.parse_args()

    # Reset checkpoint if requested
    if args.reset:
        import glob
        pattern = str(CHECKPOINT_DIR / f'{args.step}_{args.era}_*.jsonl')
        for f in glob.glob(pattern):
            Path(f).unlink()
            print(f"Removed checkpoint: {f}")

    entity_types = ['person', 'event', 'location'] if args.entity_type == 'all' else [args.entity_type]

    print(f"Step: {args.step} | Era: {args.era} | Limit: {args.limit} | Types: {entity_types}")
    print(f"Checkpoint dir: {CHECKPOINT_DIR}")
    print(f"Started: {datetime.now().isoformat()}")
    print()

    conn = get_db()

    try:
        if args.step == 'audit':
            step_audit(conn, args.era, args.limit)

        elif args.step == 'wikipedia':
            step_wikipedia(conn, args.era, args.limit, entity_types)

        elif args.step == 'wikisource':
            step_wikisource(conn, args.era, args.limit, entity_types)

        elif args.step == 'archive':
            step_archive(conn, args.era, args.limit, entity_types)

        elif args.step == 'report':
            step_report(conn, args.era, args.limit)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Progress saved in checkpoint.")
        conn.commit()
    finally:
        conn.close()

    print(f"\nFinished: {datetime.now().isoformat()}")


if __name__ == '__main__':
    main()
