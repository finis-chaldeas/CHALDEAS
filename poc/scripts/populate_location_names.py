"""
Populate location_names from Wikidata API.

Fetches:
- P1448 (official name) with temporal qualifiers (P580/P582)
- aliases in multiple languages (en, ko, ja, la, ar, zh, fa)
- sitelink titles as additional names

Usage:
    cd backend
    python ../poc/scripts/populate_location_names.py
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
LANGUAGES = ['en', 'ko', 'ja', 'la', 'ar', 'zh', 'fa', 'el', 'he', 'sa', 'fr', 'de', 'es', 'ru', 'tr', 'it', 'pt']


def fetch_batch(qids):
    params = {
        'action': 'wbgetentities',
        'ids': '|'.join(qids),
        'props': 'labels|aliases|claims',
        'languages': '|'.join(LANGUAGES),
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


def parse_year(time_value):
    if not time_value:
        return None
    try:
        t = time_value.lstrip('+')
        if t.startswith('-'):
            return -int(t[1:].split('-')[0])
        return int(t.split('-')[0])
    except (ValueError, IndexError):
        return None


def extract_p1448(entity):
    """Extract P1448 (official name) claims with temporal qualifiers."""
    claims = entity.get('claims', {})
    results = []
    for claim in claims.get('P1448', []):
        mainsnak = claim.get('mainsnak', {})
        dv = mainsnak.get('datavalue', {})
        if dv.get('type') != 'monolingualtext':
            continue
        value = dv.get('value', {})
        name = value.get('text')
        lang = value.get('language', 'en')
        if not name:
            continue

        qualifiers = claim.get('qualifiers', {})
        start_year = None
        end_year = None
        for q in qualifiers.get('P580', []):
            d = q.get('datavalue', {})
            if d.get('type') == 'time':
                start_year = parse_year(d['value'].get('time'))
        for q in qualifiers.get('P582', []):
            d = q.get('datavalue', {})
            if d.get('type') == 'time':
                end_year = parse_year(d['value'].get('time'))

        results.append({
            'name': name,
            'language': lang,
            'valid_from': start_year,
            'valid_until': end_year,
            'name_type': 'official',
            'is_primary': claim.get('rank') == 'preferred',
        })
    return results


def run():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute("SELECT id, wikidata_id, name, name_ko, name_ja FROM locations WHERE wikidata_id IS NOT NULL")
    rows = cur.fetchall()
    print(f"=== LOCATION NAMES: {len(rows)} locations ===\n", flush=True)

    qid_map = {}
    for lid, qid, name, name_ko, name_ja in rows:
        qid_map[qid] = {'id': lid, 'name': name, 'name_ko': name_ko, 'name_ja': name_ja}

    all_qids = list(qid_map.keys())
    total_batches = (len(all_qids) + BATCH_SIZE - 1) // BATCH_SIZE
    inserted = 0
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

            info = qid_map[qid]
            lid = info['id']
            names_to_insert = []

            # 1. P1448 official names with temporal qualifiers
            for p1448 in extract_p1448(entity):
                names_to_insert.append(p1448)

            # 2. Labels in various languages (as current names)
            labels = entity.get('labels', {})
            for lang_code in LANGUAGES:
                label = labels.get(lang_code, {}).get('value')
                if not label:
                    continue
                # Skip if same as the location's primary name
                if lang_code == 'en' and label == info['name']:
                    continue
                if lang_code == 'ko' and label == info.get('name_ko'):
                    continue
                if lang_code == 'ja' and label == info.get('name_ja'):
                    continue

                names_to_insert.append({
                    'name': label,
                    'language': lang_code,
                    'valid_from': None,
                    'valid_until': None,
                    'name_type': 'label',
                    'is_primary': False,
                })

            # 3. Aliases
            aliases = entity.get('aliases', {})
            for lang_code in LANGUAGES:
                for alias in aliases.get(lang_code, []):
                    alias_val = alias.get('value')
                    if not alias_val:
                        continue
                    # Avoid duplicates with labels
                    if any(n['name'] == alias_val and n['language'] == lang_code for n in names_to_insert):
                        continue
                    names_to_insert.append({
                        'name': alias_val,
                        'language': lang_code,
                        'valid_from': None,
                        'valid_until': None,
                        'name_type': 'alias',
                        'is_primary': False,
                    })

            # Insert
            for n in names_to_insert:
                name_ko = None
                name_ja = None
                if n['language'] == 'ko':
                    name_ko = n['name']
                elif n['language'] == 'ja':
                    name_ja = n['name']

                try:
                    cur.execute("""
                        INSERT INTO location_names (location_id, name, name_ko, name_ja, valid_from, valid_until, language, is_primary, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """, (lid, n['name'][:255], name_ko, name_ja, n['valid_from'], n['valid_until'],
                          n['language'][:10], n.get('is_primary', False)))
                    inserted += 1
                except Exception as e:
                    conn.rollback()
                    continue

        if (batch_idx + 1) % 20 == 0 or batch_idx == total_batches - 1:
            conn.commit()
            elapsed = time.time() - start_time
            pct = (batch_idx + 1) / total_batches * 100
            print(f"  [{pct:.0f}%] inserted: {inserted} | {elapsed:.0f}s", flush=True)

        time.sleep(REQUEST_DELAY)

    conn.commit()
    elapsed = time.time() - start_time
    print(f"\n=== Done in {elapsed:.0f}s ({elapsed/60:.1f}min): {inserted} location names inserted ===", flush=True)

    cur.execute("SELECT COUNT(*) FROM location_names")
    print(f"Total location_names: {cur.fetchone()[0]}", flush=True)
    cur.close()
    conn.close()


if __name__ == '__main__':
    run()
