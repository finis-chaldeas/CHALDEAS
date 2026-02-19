"""
Populate person_names from Wikidata API.

Fetches:
- P1477 (birth name)
- P1559 (name in native language)
- aliases in multiple languages
- labels as alternate names

Usage:
    cd backend
    python ../poc/scripts/populate_person_names.py
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
LANGUAGES = ['en', 'ko', 'ja', 'la', 'ar', 'zh', 'fa', 'el', 'he', 'sa', 'fr', 'de', 'es', 'ru', 'tr']


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


def extract_monolingual_claims(entity, prop):
    """Extract monolingual text claims (P1477 birth name, P1559 native name, etc.)."""
    claims = entity.get('claims', {})
    results = []
    for claim in claims.get(prop, []):
        mainsnak = claim.get('mainsnak', {})
        dv = mainsnak.get('datavalue', {})
        if dv.get('type') != 'monolingualtext':
            continue
        value = dv.get('value', {})
        name = value.get('text')
        lang = value.get('language', 'en')
        if name:
            results.append({'name': name, 'language': lang})
    return results


def run():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute("SELECT id, wikidata_id, name, name_ko, name_ja FROM persons WHERE wikidata_id IS NOT NULL")
    rows = cur.fetchall()
    print(f"=== PERSON NAMES: {len(rows)} persons ===\n", flush=True)

    qid_map = {}
    for pid, qid, name, name_ko, name_ja in rows:
        qid_map[qid] = {'id': pid, 'name': name, 'name_ko': name_ko, 'name_ja': name_ja}

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
            pid = info['id']
            names_to_insert = []
            seen = set()  # (name, language) dedup

            # 1. P1477 birth name
            for bn in extract_monolingual_claims(entity, 'P1477'):
                key = (bn['name'], bn['language'])
                if key not in seen:
                    seen.add(key)
                    names_to_insert.append({
                        'name': bn['name'],
                        'language': bn['language'],
                        'name_type': 'birth',
                        'is_primary': False,
                        'source': 'wikidata',
                    })

            # 2. P1559 name in native language
            for nn in extract_monolingual_claims(entity, 'P1559'):
                key = (nn['name'], nn['language'])
                if key not in seen:
                    seen.add(key)
                    names_to_insert.append({
                        'name': nn['name'],
                        'language': nn['language'],
                        'name_type': 'native',
                        'is_primary': False,
                        'source': 'wikidata',
                    })

            # 3. P1786 posthumous name
            for pn in extract_monolingual_claims(entity, 'P1786'):
                key = (pn['name'], pn['language'])
                if key not in seen:
                    seen.add(key)
                    names_to_insert.append({
                        'name': pn['name'],
                        'language': pn['language'],
                        'name_type': 'regnal',
                        'is_primary': False,
                        'source': 'wikidata',
                    })

            # 4. Labels in various languages
            labels = entity.get('labels', {})
            for lang_code in LANGUAGES:
                label = labels.get(lang_code, {}).get('value')
                if not label:
                    continue
                if lang_code == 'en' and label == info['name']:
                    continue
                if lang_code == 'ko' and label == info.get('name_ko'):
                    continue
                if lang_code == 'ja' and label == info.get('name_ja'):
                    continue

                key = (label, lang_code)
                if key not in seen:
                    seen.add(key)
                    names_to_insert.append({
                        'name': label,
                        'language': lang_code,
                        'name_type': 'alternate',
                        'is_primary': lang_code == 'en',
                        'source': 'wikidata',
                    })

            # 5. Aliases (limited to 3 per language to avoid explosion)
            aliases = entity.get('aliases', {})
            for lang_code in LANGUAGES:
                for alias in aliases.get(lang_code, [])[:3]:
                    alias_val = alias.get('value')
                    if not alias_val:
                        continue
                    key = (alias_val, lang_code)
                    if key not in seen:
                        seen.add(key)
                        names_to_insert.append({
                            'name': alias_val,
                            'language': lang_code,
                            'name_type': 'alternate',
                            'is_primary': False,
                            'source': 'wikidata',
                        })

            # Insert all names
            for n in names_to_insert:
                name_ko = n['name'] if n['language'] == 'ko' else None
                name_ja = n['name'] if n['language'] == 'ja' else None

                try:
                    cur.execute("""
                        INSERT INTO person_names (person_id, name, name_ko, name_ja, language, is_primary, name_type, source, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """, (pid, n['name'][:255], name_ko, name_ja, n['language'][:10],
                          n.get('is_primary', False), n.get('name_type', 'alternate')[:30],
                          n.get('source', 'wikidata')[:100]))
                    inserted += 1
                except Exception:
                    conn.rollback()
                    continue

        if (batch_idx + 1) % 50 == 0 or batch_idx == total_batches - 1:
            conn.commit()
            elapsed = time.time() - start_time
            pct = (batch_idx + 1) / total_batches * 100
            eta = (elapsed / (batch_idx + 1)) * (total_batches - batch_idx - 1) if batch_idx > 0 else 0
            print(f"  [{pct:.0f}%] inserted: {inserted} | {elapsed:.0f}s | ETA {eta:.0f}s", flush=True)

        time.sleep(REQUEST_DELAY)

    conn.commit()
    elapsed = time.time() - start_time
    print(f"\n=== Done in {elapsed:.0f}s ({elapsed/60:.1f}min): {inserted} person names ===", flush=True)

    cur.execute("SELECT COUNT(*) FROM person_names")
    print(f"Total person_names: {cur.fetchone()[0]}", flush=True)

    # Stats
    cur.execute("SELECT name_type, COUNT(*) FROM person_names GROUP BY name_type ORDER BY COUNT(*) DESC")
    print("\nBy type:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")

    cur.execute("SELECT language, COUNT(*) FROM person_names GROUP BY language ORDER BY COUNT(*) DESC LIMIT 10")
    print("\nTop languages:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")

    cur.close()
    conn.close()


if __name__ == '__main__':
    run()
