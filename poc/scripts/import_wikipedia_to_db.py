"""
Import Wikipedia article text from local ZIM into DB.

Flow:
1. Wikidata API -> enwiki article titles for all entities
2. Local ZIM file -> extract article plain text
3. sources table -> store as source_type='wikipedia'
4. event_sources / person_sources -> link entities to sources
5. detail tables -> set wikipedia_url + fill empty descriptions

Usage:
    cd backend
    python ../poc/scripts/import_wikipedia_to_db.py
    python ../poc/scripts/import_wikipedia_to_db.py --entity-type persons --limit 1000
"""
import sys
import time
import argparse
import requests
import psycopg2

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_URL = 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas'
WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
ZIM_EN = "E:/chaldeas_data/kiwix/wikipedia_en_nopic.zim"
BATCH_SIZE = 50
REQUEST_DELAY = 0.2

# Lazy-loaded ZIM archive
_archive = None

def get_archive():
    global _archive
    if _archive is None:
        from libzim.reader import Archive
        _archive = Archive(ZIM_EN)
        print(f"  ZIM opened: {_archive.article_count:,} articles", flush=True)
    return _archive


def extract_text(title):
    """Extract plain text from ZIM. Returns (text, word_count) or (None, 0)."""
    archive = get_archive()
    article_path = title.replace(' ', '_')

    try:
        entry = archive.get_entry_by_path(f"A/{article_path}")
    except KeyError:
        try:
            entry = archive.get_entry_by_path(article_path)
        except KeyError:
            return None, 0

    try:
        item = entry.get_item()
        content = bytes(item.content).decode('utf-8', errors='replace')
    except Exception:
        return None, 0

    if not content or len(content) < 100:
        return None, 0

    # HTML -> plain text
    if content.strip().startswith('<'):
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header',
                                       'table', 'sup', 'sub']):
                tag.decompose()
            # Remove References and below
            for heading in soup.find_all(['h2', 'h3']):
                ht = heading.get_text().strip().lower()
                if ht in ('references', 'see also', 'external links',
                          'further reading', 'notes', 'bibliography',
                          'footnotes', 'citations', 'sources'):
                    for sib in list(heading.find_next_siblings()):
                        sib.decompose()
                    heading.decompose()
                    break
            text = soup.get_text(separator='\n')
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            text = '\n'.join(lines)
        except Exception:
            text = content[:50000]
    else:
        text = content

    if len(text) < 50:
        return None, 0
    return text, len(text.split())


def fetch_sitelinks_batch(qids):
    """Fetch enwiki sitelinks for a batch of QIDs."""
    params = {
        'action': 'wbgetentities',
        'ids': '|'.join(qids),
        'props': 'sitelinks',
        'sitefilter': 'enwiki',
        'format': 'json',
    }
    headers = {'User-Agent': 'Chaldeas/1.0 (historical data project)'}
    for attempt in range(3):
        try:
            resp = requests.get(WIKIDATA_API, params=params, headers=headers, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                time.sleep(2 ** (attempt + 1))
        except Exception:
            time.sleep(2)
    return None


def get_first_paragraph(text, max_chars=2000):
    """Extract first meaningful paragraph as description."""
    if not text:
        return None
    lines = text.split('\n')
    for line in lines:
        if len(line) > 80 and not line.startswith('#'):
            return line[:max_chars]
    return text[:max_chars]


def process_entity_type(conn, entity_type, limit=0):
    """Process one entity type (events/persons/locations)."""
    cur = conn.cursor()

    if entity_type == 'events':
        table = 'events'
        link_table = 'event_sources'
        link_col = 'event_id'
        detail_table = 'event_details'
        detail_id_col = 'event_id'
        desc_col = 'description'
        url_col = 'wikipedia_url'
    elif entity_type == 'persons':
        table = 'persons'
        link_table = 'person_sources'
        link_col = 'person_id'
        detail_table = 'person_details'
        detail_id_col = 'person_id'
        desc_col = 'biography'
        url_col = 'wikipedia_url'
    elif entity_type == 'locations':
        table = 'locations'
        link_table = None
        link_col = None
        detail_table = 'location_details'
        detail_id_col = 'location_id'
        desc_col = 'description'
        url_col = 'wikipedia_url'
    else:
        return

    sql = f"SELECT id, wikidata_id FROM {table} WHERE wikidata_id IS NOT NULL"
    if limit:
        sql += f" LIMIT {limit}"
    cur.execute(sql)
    rows = cur.fetchall()
    qid_map = {qid: eid for eid, qid in rows}
    all_qids = list(qid_map.keys())

    print(f"\n=== {entity_type.upper()}: {len(all_qids):,} entities ===", flush=True)

    # Phase 1: Get enwiki titles
    print("  Phase 1: Fetching enwiki titles...", flush=True)
    qid_to_title = {}
    total_batches = (len(all_qids) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx in range(total_batches):
        batch = all_qids[batch_idx * BATCH_SIZE:(batch_idx + 1) * BATCH_SIZE]
        data = fetch_sitelinks_batch(batch)
        if not data:
            continue

        entities = data.get('entities', {})
        for qid in batch:
            entity = entities.get(qid)
            if not entity or 'missing' in entity:
                continue
            enwiki = entity.get('sitelinks', {}).get('enwiki', {}).get('title')
            if enwiki:
                qid_to_title[qid] = enwiki

        if (batch_idx + 1) % 100 == 0 or batch_idx == total_batches - 1:
            pct = (batch_idx + 1) / total_batches * 100
            print(f"    [{pct:.0f}%] titles: {len(qid_to_title):,}", flush=True)

        time.sleep(REQUEST_DELAY)

    no_enwiki = len(all_qids) - len(qid_to_title)
    print(f"  Titles: {len(qid_to_title):,} / {len(all_qids):,} (no enwiki: {no_enwiki:,})", flush=True)

    # Phase 2: ZIM extraction + DB import
    print("  Phase 2: ZIM extraction + DB import...", flush=True)

    sources_created = 0
    links_created = 0
    descs_filled = 0
    urls_set = 0
    extract_fail = 0
    start_time = time.time()
    total = len(qid_to_title)

    for i, (qid, enwiki_title) in enumerate(qid_to_title.items()):
        entity_id = qid_map[qid]
        wiki_url = f"https://en.wikipedia.org/wiki/{enwiki_title.replace(' ', '_')}"[:500]

        # Extract text from ZIM
        text, word_count = extract_text(enwiki_title)
        if not text:
            extract_fail += 1
            # Still set wikipedia_url
            try:
                cur.execute(f"""
                    INSERT INTO {detail_table} ({detail_id_col}, {url_col})
                    VALUES (%s, %s)
                    ON CONFLICT ({detail_id_col}) DO UPDATE
                    SET {url_col} = COALESCE({detail_table}.{url_col}, EXCLUDED.{url_col})
                """, (entity_id, wiki_url))
                urls_set += 1
            except Exception:
                conn.rollback()
            continue

        # Create/find source
        source_title = f"{enwiki_title} - Wikipedia"[:500]
        try:
            cur.execute(
                "SELECT id FROM sources WHERE source_type = 'wikipedia' AND url = %s",
                (wiki_url,)
            )
            existing = cur.fetchone()
            if existing:
                source_id = existing[0]
                cur.execute(
                    "UPDATE sources SET content_raw = %s, word_count = %s WHERE id = %s AND content_raw IS NULL",
                    (text, word_count, source_id)
                )
            else:
                cur.execute("""
                    INSERT INTO sources (source_type, title, content_raw, url, language, reliability, word_count)
                    VALUES ('wikipedia', %s, %s, %s, 'en', 3, %s)
                    RETURNING id
                """, (source_title, text, wiki_url, word_count))
                source_id = cur.fetchone()[0]
                sources_created += 1
        except Exception:
            conn.rollback()
            continue

        # Link entity to source
        if link_table and link_col:
            try:
                cur.execute(f"""
                    INSERT INTO {link_table} ({link_col}, source_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (entity_id, source_id))
                if cur.rowcount > 0:
                    links_created += 1
            except Exception:
                conn.rollback()

        # Update detail table
        first_para = get_first_paragraph(text)
        try:
            cur.execute(f"""
                INSERT INTO {detail_table} ({detail_id_col}, {url_col}, {desc_col})
                VALUES (%s, %s, %s)
                ON CONFLICT ({detail_id_col}) DO UPDATE SET
                    {url_col} = COALESCE({detail_table}.{url_col}, EXCLUDED.{url_col}),
                    {desc_col} = COALESCE({detail_table}.{desc_col}, EXCLUDED.{desc_col})
            """, (entity_id, wiki_url, first_para))
            urls_set += 1
            if first_para:
                descs_filled += 1
        except Exception:
            conn.rollback()

        if (i + 1) % 500 == 0:
            conn.commit()
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            eta = (total - i - 1) / rate if rate > 0 else 0
            pct = (i + 1) / total * 100
            print(f"    [{pct:.0f}%] src: +{sources_created} | link: +{links_created} | "
                  f"desc: +{descs_filled} | url: +{urls_set} | "
                  f"fail: {extract_fail} | {elapsed:.0f}s | ETA {eta:.0f}s", flush=True)

    conn.commit()
    elapsed = time.time() - start_time

    print(f"\n  {entity_type} done in {elapsed:.0f}s ({elapsed/60:.1f}min):", flush=True)
    print(f"    Sources created: {sources_created:,}", flush=True)
    print(f"    Links created: {links_created:,}", flush=True)
    print(f"    Descriptions filled: {descs_filled:,}", flush=True)
    print(f"    URLs set: {urls_set:,}", flush=True)
    print(f"    ZIM extract failed: {extract_fail:,}", flush=True)

    cur.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--entity-type', choices=['events', 'persons', 'locations', 'all'],
                        default='all')
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()

    conn = psycopg2.connect(DB_URL)
    start = time.time()

    print("=== IMPORT WIKIPEDIA FROM LOCAL ZIM ===", flush=True)
    print(f"  ZIM: {ZIM_EN}", flush=True)

    types = ['events', 'persons', 'locations'] if args.entity_type == 'all' else [args.entity_type]
    for t in types:
        process_entity_type(conn, t, limit=args.limit)

    elapsed = time.time() - start
    print(f"\n=== ALL DONE in {elapsed:.0f}s ({elapsed/60:.1f}min) ===", flush=True)

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM sources WHERE source_type = 'wikipedia'")
    print(f"  Total wikipedia sources: {cur.fetchone()[0]:,}")
    cur.execute("SELECT ROUND(100.0 * COUNT(wikipedia_url) / NULLIF(COUNT(*), 0), 1) FROM event_details")
    print(f"  Events wikipedia_url: {cur.fetchone()[0]}%")
    cur.execute("SELECT ROUND(100.0 * COUNT(wikipedia_url) / NULLIF(COUNT(*), 0), 1) FROM person_details")
    print(f"  Persons wikipedia_url: {cur.fetchone()[0]}%")
    cur.execute("SELECT ROUND(100.0 * COUNT(wikipedia_url) / NULLIF(COUNT(*), 0), 1) FROM location_details")
    print(f"  Locations wikipedia_url: {cur.fetchone()[0]}%")
    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
