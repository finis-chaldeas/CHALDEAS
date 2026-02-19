"""
Enrich all entities with Wikidata data via API.

Fills gaps:
- wikipedia_url (from sitelinks)
- image_url (from P18)
- name_ko / title_ko (from labels)
- description_source (set to 'wikidata')

Batch: 50 QIDs per request via wbgetentities API.

Usage:
    cd backend
    python ../poc/scripts/enrich_from_wikidata_api.py [events|persons|locations|all]
"""
import sys
import json
import time
import requests
import psycopg2

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_URL = 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas'
WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
BATCH_SIZE = 50
REQUEST_DELAY = 0.25
COMMONS_URL = 'https://commons.wikimedia.org/wiki/Special:FilePath/'


def fetch_batch(qids):
    """Fetch batch of entities from Wikidata API."""
    params = {
        'action': 'wbgetentities',
        'ids': '|'.join(qids),
        'props': 'labels|sitelinks|claims',
        'languages': 'ko|ja|en',
        'sitefilter': 'enwiki|kowiki|jawiki',
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
            else:
                time.sleep(1)
        except Exception as e:
            time.sleep(2)
    return None


def get_image_url(entity):
    """Extract image URL from P18 claim."""
    claims = entity.get('claims', {})
    p18 = claims.get('P18', [])
    for claim in p18:
        mainsnak = claim.get('mainsnak', {})
        dv = mainsnak.get('datavalue', {})
        if dv.get('type') == 'string':
            filename = dv.get('value', '').replace(' ', '_')
            if filename:
                url = COMMONS_URL + requests.utils.quote(filename)
                return url[:500] if len(url) > 500 else url
    return None


def get_wikipedia_url(entity, lang='en'):
    """Extract Wikipedia URL from sitelinks."""
    sitelinks = entity.get('sitelinks', {})
    site_key = f'{lang}wiki'
    site = sitelinks.get(site_key, {})
    title = site.get('title')
    if title:
        url = f'https://{lang}.wikipedia.org/wiki/{requests.utils.quote(title.replace(" ", "_"))}'
        return url[:500] if len(url) > 500 else url
    return None


def get_label(entity, lang):
    """Extract label in given language."""
    labels = entity.get('labels', {})
    label = labels.get(lang, {})
    return label.get('value')


# ==========================================
# EVENTS
# ==========================================
def enrich_events():
    """Enrich events: title_ko, event_details.wikipedia_url/image_url/description_source."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute("SELECT id, wikidata_id, title_ko FROM events WHERE wikidata_id IS NOT NULL")
    rows = cur.fetchall()
    print(f"\n=== EVENTS: {len(rows)} to process ===\n", flush=True)

    qid_to_event = {}
    for eid, qid, title_ko in rows:
        qid_to_event[qid] = {'id': eid, 'title_ko': title_ko}

    all_qids = list(qid_to_event.keys())
    total_batches = (len(all_qids) + BATCH_SIZE - 1) // BATCH_SIZE

    updated_title_ko = 0
    updated_wiki_url = 0
    updated_image = 0
    updated_source = 0
    start_time = time.time()

    for batch_idx in range(total_batches):
        batch = all_qids[batch_idx * BATCH_SIZE:(batch_idx + 1) * BATCH_SIZE]
        data = fetch_batch(batch)
        if not data:
            continue

        entities = data.get('entities', {})
        for qid in batch:
            entity = entities.get(qid)
            if not entity or 'missing' in entity:
                continue

            info = qid_to_event[qid]
            eid = info['id']

            # title_ko from labels
            if not info['title_ko']:
                ko_label = get_label(entity, 'ko')
                if ko_label:
                    cur.execute("UPDATE events SET title_ko = %s WHERE id = %s", (ko_label, eid))
                    updated_title_ko += 1

            # event_details: wikipedia_url, image_url, description_source
            wiki_url = get_wikipedia_url(entity, 'en')
            image_url = get_image_url(entity)

            updates = []
            params = []
            if wiki_url:
                updates.append("wikipedia_url = %s")
                params.append(wiki_url)
                updated_wiki_url += 1
            if image_url:
                updates.append("image_url = %s")
                params.append(image_url)
                updated_image += 1
            updates.append("description_source = COALESCE(description_source, 'wikidata')")

            if updates:
                params.append(eid)
                cur.execute(f"""
                    UPDATE event_details SET {', '.join(updates)}
                    WHERE event_id = %s AND (wikipedia_url IS NULL OR image_url IS NULL OR description_source IS NULL)
                """, params)
                if cur.rowcount > 0:
                    updated_source += 1

        if (batch_idx + 1) % 20 == 0 or batch_idx == total_batches - 1:
            conn.commit()
            elapsed = time.time() - start_time
            pct = (batch_idx + 1) / total_batches * 100
            print(f"  [{pct:.0f}%] title_ko: +{updated_title_ko}, wiki_url: +{updated_wiki_url}, "
                  f"image: +{updated_image} | {elapsed:.0f}s", flush=True)

        time.sleep(REQUEST_DELAY)

    conn.commit()
    elapsed = time.time() - start_time
    print(f"\n  Events done in {elapsed:.0f}s: title_ko +{updated_title_ko}, "
          f"wiki_url +{updated_wiki_url}, image +{updated_image}, source +{updated_source}", flush=True)
    cur.close()
    conn.close()


# ==========================================
# PERSONS
# ==========================================
def enrich_persons():
    """Enrich persons: name_ko, person_details.wikipedia_url/image_url/biography_source."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Only fetch persons that have gaps
    cur.execute("""
        SELECT p.id, p.wikidata_id, p.name_ko
        FROM persons p
        WHERE p.wikidata_id IS NOT NULL
    """)
    rows = cur.fetchall()
    print(f"\n=== PERSONS: {len(rows)} to process ===\n", flush=True)

    qid_to_person = {}
    for pid, qid, name_ko in rows:
        qid_to_person[qid] = {'id': pid, 'name_ko': name_ko}

    all_qids = list(qid_to_person.keys())
    total_batches = (len(all_qids) + BATCH_SIZE - 1) // BATCH_SIZE

    updated_name_ko = 0
    updated_wiki_url = 0
    updated_image = 0
    updated_source = 0
    start_time = time.time()

    for batch_idx in range(total_batches):
        batch = all_qids[batch_idx * BATCH_SIZE:(batch_idx + 1) * BATCH_SIZE]
        data = fetch_batch(batch)
        if not data:
            continue

        entities = data.get('entities', {})
        for qid in batch:
            entity = entities.get(qid)
            if not entity or 'missing' in entity:
                continue

            info = qid_to_person[qid]
            pid = info['id']

            # name_ko
            if not info['name_ko']:
                ko_label = get_label(entity, 'ko')
                if ko_label:
                    cur.execute("UPDATE persons SET name_ko = %s WHERE id = %s", (ko_label, pid))
                    updated_name_ko += 1

            # person_details
            wiki_url = get_wikipedia_url(entity, 'en')
            image_url = get_image_url(entity)

            # Check if person_details row exists
            cur.execute("SELECT 1 FROM person_details WHERE person_id = %s", (pid,))
            has_detail = cur.fetchone() is not None

            if has_detail:
                updates = []
                params = []
                if wiki_url:
                    updates.append("wikipedia_url = COALESCE(wikipedia_url, %s)")
                    params.append(wiki_url)
                    updated_wiki_url += 1
                if image_url:
                    updates.append("image_url = COALESCE(image_url, %s)")
                    params.append(image_url)
                    updated_image += 1
                updates.append("biography_source = COALESCE(biography_source, 'wikidata')")

                if updates:
                    params.append(pid)
                    cur.execute(f"UPDATE person_details SET {', '.join(updates)} WHERE person_id = %s", params)
                    if cur.rowcount > 0:
                        updated_source += 1
            else:
                # Create person_details row if we have data
                if wiki_url or image_url:
                    cur.execute("""
                        INSERT INTO person_details (person_id, wikipedia_url, image_url, biography_source)
                        VALUES (%s, %s, %s, 'wikidata')
                        ON CONFLICT (person_id) DO NOTHING
                    """, (pid, wiki_url, image_url))
                    updated_source += 1

        if (batch_idx + 1) % 50 == 0 or batch_idx == total_batches - 1:
            conn.commit()
            elapsed = time.time() - start_time
            pct = (batch_idx + 1) / total_batches * 100
            eta = (elapsed / (batch_idx + 1)) * (total_batches - batch_idx - 1)
            print(f"  [{pct:.0f}%] name_ko: +{updated_name_ko}, wiki_url: +{updated_wiki_url}, "
                  f"image: +{updated_image} | {elapsed:.0f}s | ETA {eta:.0f}s", flush=True)

        time.sleep(REQUEST_DELAY)

    conn.commit()
    elapsed = time.time() - start_time
    print(f"\n  Persons done in {elapsed:.0f}s ({elapsed/60:.1f}min): name_ko +{updated_name_ko}, "
          f"wiki_url +{updated_wiki_url}, image +{updated_image}, source +{updated_source}", flush=True)
    cur.close()
    conn.close()


# ==========================================
# LOCATIONS
# ==========================================
def enrich_locations():
    """Enrich locations: name_ko, location_details (create if needed)."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute("SELECT id, wikidata_id, name_ko FROM locations WHERE wikidata_id IS NOT NULL")
    rows = cur.fetchall()
    print(f"\n=== LOCATIONS: {len(rows)} to process ===\n", flush=True)

    qid_to_loc = {}
    for lid, qid, name_ko in rows:
        qid_to_loc[qid] = {'id': lid, 'name_ko': name_ko}

    all_qids = list(qid_to_loc.keys())
    total_batches = (len(all_qids) + BATCH_SIZE - 1) // BATCH_SIZE

    updated_name_ko = 0
    created_details = 0
    start_time = time.time()

    for batch_idx in range(total_batches):
        batch = all_qids[batch_idx * BATCH_SIZE:(batch_idx + 1) * BATCH_SIZE]
        data = fetch_batch(batch)
        if not data:
            continue

        entities = data.get('entities', {})
        for qid in batch:
            entity = entities.get(qid)
            if not entity or 'missing' in entity:
                continue

            info = qid_to_loc[qid]
            lid = info['id']

            # name_ko
            if not info['name_ko']:
                ko_label = get_label(entity, 'ko')
                if ko_label:
                    cur.execute("UPDATE locations SET name_ko = %s WHERE id = %s", (ko_label, lid))
                    updated_name_ko += 1

            # location_details - create with wikipedia_url
            wiki_url = get_wikipedia_url(entity, 'en')
            image_url = get_image_url(entity)

            if wiki_url or image_url:
                cur.execute("""
                    INSERT INTO location_details (location_id, wikipedia_url, description_source)
                    VALUES (%s, %s, 'wikidata')
                    ON CONFLICT (location_id) DO UPDATE SET
                        wikipedia_url = COALESCE(location_details.wikipedia_url, EXCLUDED.wikipedia_url)
                """, (lid, wiki_url))
                if cur.rowcount > 0:
                    created_details += 1

        if (batch_idx + 1) % 20 == 0 or batch_idx == total_batches - 1:
            conn.commit()
            elapsed = time.time() - start_time
            pct = (batch_idx + 1) / total_batches * 100
            print(f"  [{pct:.0f}%] name_ko: +{updated_name_ko}, details: +{created_details} | {elapsed:.0f}s",
                  flush=True)

        time.sleep(REQUEST_DELAY)

    conn.commit()
    elapsed = time.time() - start_time
    print(f"\n  Locations done in {elapsed:.0f}s: name_ko +{updated_name_ko}, details +{created_details}",
          flush=True)
    cur.close()
    conn.close()


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'all'

    if target in ('events', 'all'):
        enrich_events()
    if target in ('persons', 'all'):
        enrich_persons()
    if target in ('locations', 'all'):
        enrich_locations()

    print("\n=== ALL DONE ===", flush=True)
