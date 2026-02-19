"""
Fill missing wikipedia_url for all entities using Wikidata sitelinks.

Strategy:
1. Try enwiki first (English Wikipedia)
2. If no enwiki, try kowiki, jawiki, dewiki, frwiki, eswiki, etc.
3. Create missing detail rows for entities that have no detail record yet

Usage:
    cd backend
    python ../poc/scripts/fill_wikipedia_urls.py
"""
import sys
import time
import requests
import psycopg2

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_URL = 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas'
WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
BATCH_SIZE = 50
REQUEST_DELAY = 0.2

# Ordered by preference
WIKI_SITELINKS = [
    ('enwiki', 'https://en.wikipedia.org/wiki/'),
    ('kowiki', 'https://ko.wikipedia.org/wiki/'),
    ('jawiki', 'https://ja.wikipedia.org/wiki/'),
    ('dewiki', 'https://de.wikipedia.org/wiki/'),
    ('frwiki', 'https://fr.wikipedia.org/wiki/'),
    ('eswiki', 'https://es.wikipedia.org/wiki/'),
    ('ruwiki', 'https://ru.wikipedia.org/wiki/'),
    ('zhwiki', 'https://zh.wikipedia.org/wiki/'),
    ('arwiki', 'https://ar.wikipedia.org/wiki/'),
    ('itwiki', 'https://it.wikipedia.org/wiki/'),
    ('ptwiki', 'https://pt.wikipedia.org/wiki/'),
    ('nlwiki', 'https://nl.wikipedia.org/wiki/'),
    ('plwiki', 'https://pl.wikipedia.org/wiki/'),
    ('trwiki', 'https://tr.wikipedia.org/wiki/'),
    ('fawiki', 'https://fa.wikipedia.org/wiki/'),
    ('hewiki', 'https://he.wikipedia.org/wiki/'),
    ('svwiki', 'https://sv.wikipedia.org/wiki/'),
    ('elwiki', 'https://el.wikipedia.org/wiki/'),
    ('lawiki', 'https://la.wikipedia.org/wiki/'),
]


def fetch_sitelinks_batch(qids):
    params = {
        'action': 'wbgetentities',
        'ids': '|'.join(qids),
        'props': 'sitelinks',
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


def get_best_wiki_url(entity):
    """Get best available Wikipedia URL from sitelinks."""
    sitelinks = entity.get('sitelinks', {})
    for site_key, base_url in WIKI_SITELINKS:
        sl = sitelinks.get(site_key)
        if sl and sl.get('title'):
            url = base_url + sl['title'].replace(' ', '_')
            return url[:500]  # Truncate for VARCHAR(500)
    return None


def fill_events(conn):
    cur = conn.cursor()

    # Events missing wikipedia_url (have event_details but no url)
    cur.execute("""
        SELECT e.id, e.wikidata_id
        FROM events e
        JOIN event_details ed ON ed.event_id = e.id
        WHERE e.wikidata_id IS NOT NULL AND ed.wikipedia_url IS NULL
    """)
    missing_with_detail = {qid: eid for eid, qid in cur.fetchall()}

    # Events with no event_details row at all
    cur.execute("""
        SELECT e.id, e.wikidata_id
        FROM events e
        WHERE e.wikidata_id IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM event_details ed WHERE ed.event_id = e.id)
    """)
    missing_no_detail = {qid: eid for eid, qid in cur.fetchall()}

    all_qids = list(set(list(missing_with_detail.keys()) + list(missing_no_detail.keys())))
    print(f"\n--- EVENTS: {len(all_qids)} missing wikipedia_url ({len(missing_with_detail)} have detail, {len(missing_no_detail)} need detail row) ---", flush=True)

    if not all_qids:
        print("  Nothing to do.", flush=True)
        return 0

    total_batches = (len(all_qids) + BATCH_SIZE - 1) // BATCH_SIZE
    updated = 0
    created = 0
    no_wiki = 0

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

            url = get_best_wiki_url(entity)
            if not url:
                no_wiki += 1
                continue

            eid = missing_with_detail.get(qid) or missing_no_detail.get(qid)
            if not eid:
                continue

            try:
                if qid in missing_with_detail:
                    cur.execute("UPDATE event_details SET wikipedia_url = %s WHERE event_id = %s AND wikipedia_url IS NULL",
                                (url, eid))
                    updated += 1
                else:
                    cur.execute("INSERT INTO event_details (event_id, wikipedia_url) VALUES (%s, %s)",
                                (eid, url))
                    created += 1
            except Exception:
                conn.rollback()
                continue

        if (batch_idx + 1) % 20 == 0 or batch_idx == total_batches - 1:
            conn.commit()
            pct = (batch_idx + 1) / total_batches * 100
            print(f"  [{pct:.0f}%] updated: {updated}, created: {created}, no_wiki: {no_wiki}", flush=True)

        time.sleep(REQUEST_DELAY)

    conn.commit()
    print(f"  Events done: updated {updated}, created {created}, no_wiki {no_wiki}", flush=True)
    return updated + created


def fill_persons(conn):
    cur = conn.cursor()

    cur.execute("""
        SELECT p.id, p.wikidata_id
        FROM persons p
        JOIN person_details pd ON pd.person_id = p.id
        WHERE p.wikidata_id IS NOT NULL AND pd.wikipedia_url IS NULL
    """)
    missing_with_detail = {qid: pid for pid, qid in cur.fetchall()}

    cur.execute("""
        SELECT p.id, p.wikidata_id
        FROM persons p
        WHERE p.wikidata_id IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM person_details pd WHERE pd.person_id = p.id)
    """)
    missing_no_detail = {qid: pid for pid, qid in cur.fetchall()}

    all_qids = list(set(list(missing_with_detail.keys()) + list(missing_no_detail.keys())))
    print(f"\n--- PERSONS: {len(all_qids)} missing wikipedia_url ({len(missing_with_detail)} have detail, {len(missing_no_detail)} need detail row) ---", flush=True)

    if not all_qids:
        print("  Nothing to do.", flush=True)
        return 0

    total_batches = (len(all_qids) + BATCH_SIZE - 1) // BATCH_SIZE
    updated = 0
    created = 0
    no_wiki = 0

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

            url = get_best_wiki_url(entity)
            if not url:
                no_wiki += 1
                continue

            pid = missing_with_detail.get(qid) or missing_no_detail.get(qid)
            if not pid:
                continue

            try:
                if qid in missing_with_detail:
                    cur.execute("UPDATE person_details SET wikipedia_url = %s WHERE person_id = %s AND wikipedia_url IS NULL",
                                (url, pid))
                    updated += 1
                else:
                    cur.execute("INSERT INTO person_details (person_id, wikipedia_url) VALUES (%s, %s)",
                                (pid, url))
                    created += 1
            except Exception:
                conn.rollback()
                continue

        if (batch_idx + 1) % 50 == 0 or batch_idx == total_batches - 1:
            conn.commit()
            elapsed_pct = (batch_idx + 1) / total_batches * 100
            print(f"  [{elapsed_pct:.0f}%] updated: {updated}, created: {created}, no_wiki: {no_wiki}", flush=True)

        time.sleep(REQUEST_DELAY)

    conn.commit()
    print(f"  Persons done: updated {updated}, created {created}, no_wiki {no_wiki}", flush=True)
    return updated + created


def fill_locations(conn):
    cur = conn.cursor()

    cur.execute("""
        SELECT l.id, l.wikidata_id
        FROM locations l
        JOIN location_details ld ON ld.location_id = l.id
        WHERE l.wikidata_id IS NOT NULL AND ld.wikipedia_url IS NULL
    """)
    missing_with_detail = {qid: lid for lid, qid in cur.fetchall()}

    cur.execute("""
        SELECT l.id, l.wikidata_id
        FROM locations l
        WHERE l.wikidata_id IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM location_details ld WHERE ld.location_id = l.id)
    """)
    missing_no_detail = {qid: lid for lid, qid in cur.fetchall()}

    all_qids = list(set(list(missing_with_detail.keys()) + list(missing_no_detail.keys())))
    print(f"\n--- LOCATIONS: {len(all_qids)} missing wikipedia_url ({len(missing_with_detail)} have detail, {len(missing_no_detail)} need detail row) ---", flush=True)

    if not all_qids:
        print("  Nothing to do.", flush=True)
        return 0

    total_batches = (len(all_qids) + BATCH_SIZE - 1) // BATCH_SIZE
    updated = 0
    created = 0
    no_wiki = 0

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

            url = get_best_wiki_url(entity)
            if not url:
                no_wiki += 1
                continue

            lid = missing_with_detail.get(qid) or missing_no_detail.get(qid)
            if not lid:
                continue

            try:
                if qid in missing_with_detail:
                    cur.execute("UPDATE location_details SET wikipedia_url = %s WHERE location_id = %s AND wikipedia_url IS NULL",
                                (url, lid))
                    updated += 1
                else:
                    cur.execute("INSERT INTO location_details (location_id, wikipedia_url) VALUES (%s, %s)",
                                (lid, url))
                    created += 1
            except Exception:
                conn.rollback()
                continue

        if (batch_idx + 1) % 20 == 0 or batch_idx == total_batches - 1:
            conn.commit()
            pct = (batch_idx + 1) / total_batches * 100
            print(f"  [{pct:.0f}%] updated: {updated}, created: {created}, no_wiki: {no_wiki}", flush=True)

        time.sleep(REQUEST_DELAY)

    conn.commit()
    print(f"  Locations done: updated {updated}, created {created}, no_wiki {no_wiki}", flush=True)
    return updated + created


def run():
    conn = psycopg2.connect(DB_URL)
    start = time.time()

    print("=== FILL WIKIPEDIA URLs (19 language fallback) ===\n", flush=True)

    total = 0
    total += fill_events(conn)
    total += fill_persons(conn)
    total += fill_locations(conn)

    elapsed = time.time() - start
    print(f"\n=== ALL DONE in {elapsed:.0f}s ({elapsed/60:.1f}min): {total} URLs filled ===", flush=True)

    # Final coverage
    cur = conn.cursor()
    cur.execute("SELECT ROUND(100.0 * COUNT(wikipedia_url) / NULLIF(COUNT(*), 0), 1) FROM event_details")
    print(f"  Events wikipedia_url: {cur.fetchone()[0]}%")
    cur.execute("SELECT ROUND(100.0 * COUNT(wikipedia_url) / NULLIF(COUNT(*), 0), 1) FROM person_details")
    print(f"  Persons wikipedia_url: {cur.fetchone()[0]}%")
    cur.execute("SELECT ROUND(100.0 * COUNT(wikipedia_url) / NULLIF(COUNT(*), 0), 1) FROM location_details")
    print(f"  Locations wikipedia_url: {cur.fetchone()[0]}%")

    cur.close()
    conn.close()


if __name__ == '__main__':
    run()
