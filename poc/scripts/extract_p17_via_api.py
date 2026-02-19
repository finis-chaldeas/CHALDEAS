"""
Extract P17 (country) claims via Wikidata API instead of dump scanning.

Much faster approach:
- wbgetentities API: 50 QIDs per request
- 17,723 locations / 50 = 355 requests
- ~6-10 minutes total

Usage:
    cd backend
    python ../poc/scripts/extract_p17_via_api.py
"""
import sys
import json
import time
import requests
import psycopg2
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_URL = 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas'
OUTPUT_PATH = Path(r'C:\Projects\Chaldeas\poc\data\wikidata\p17_extractions.json')
CHECKPOINT_PATH = Path(r'C:\Projects\Chaldeas\poc\data\wikidata\p17_checkpoint.json')
WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
BATCH_SIZE = 50
MAX_WORKERS = 4  # Parallel requests (be nice to Wikidata)
REQUEST_DELAY = 0.25  # seconds between batches


def load_location_qids():
    """Load all location wikidata_ids from DB."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT wikidata_id, id, name FROM locations WHERE wikidata_id IS NOT NULL")
    qid_map = {}
    for qid, loc_id, name in cur.fetchall():
        qid_map[qid] = {'id': loc_id, 'name': name}
    cur.close()
    conn.close()
    return qid_map


def parse_year_from_time(time_value):
    """Parse year from Wikidata time value like '+1453-00-00T00:00:00Z'."""
    if not time_value:
        return None
    try:
        t = time_value.lstrip('+')
        if t.startswith('-'):
            parts = t[1:].split('-')
            return -int(parts[0])
        else:
            parts = t.split('-')
            return int(parts[0])
    except (ValueError, IndexError):
        return None


def extract_p17_from_entity(entity_data):
    """Extract P17 (country) claims with temporal qualifiers."""
    claims = entity_data.get('claims', {})
    p17_claims = claims.get('P17', [])

    results = []
    for claim in p17_claims:
        mainsnak = claim.get('mainsnak', {})
        datavalue = mainsnak.get('datavalue', {})

        if datavalue.get('type') != 'wikibase-entityid':
            continue

        country_qid = 'Q' + str(datavalue.get('value', {}).get('numeric-id', ''))

        qualifiers = claim.get('qualifiers', {})
        start_time = None
        end_time = None

        for q in qualifiers.get('P580', []):
            dv = q.get('datavalue', {})
            if dv.get('type') == 'time':
                start_time = parse_year_from_time(dv.get('value', {}).get('time'))

        for q in qualifiers.get('P582', []):
            dv = q.get('datavalue', {})
            if dv.get('type') == 'time':
                end_time = parse_year_from_time(dv.get('value', {}).get('time'))

        rank = claim.get('rank', 'normal')

        results.append({
            'country_qid': country_qid,
            'start_year': start_time,
            'end_year': end_time,
            'rank': rank,
        })

    return results


def fetch_batch(qids):
    """Fetch a batch of entities from Wikidata API."""
    params = {
        'action': 'wbgetentities',
        'ids': '|'.join(qids),
        'props': 'claims',
        'format': 'json',
    }
    headers = {
        'User-Agent': 'Chaldeas/1.0 (historical data project; contact@chaldeas.site)'
    }

    for attempt in range(3):
        try:
            resp = requests.get(WIKIDATA_API, params=params, headers=headers, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                # Rate limited
                wait = 2 ** (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...", flush=True)
                time.sleep(wait)
            else:
                print(f"  HTTP {resp.status_code} for batch, attempt {attempt+1}", flush=True)
                time.sleep(1)
        except requests.exceptions.Timeout:
            print(f"  Timeout, attempt {attempt+1}", flush=True)
            time.sleep(2)
        except Exception as e:
            print(f"  Error: {e}, attempt {attempt+1}", flush=True)
            time.sleep(1)

    return None


def load_checkpoint():
    """Load checkpoint if exists."""
    if CHECKPOINT_PATH.exists():
        with open(CHECKPOINT_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_checkpoint(results, processed_count):
    """Save checkpoint periodically."""
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        'processed_count': processed_count,
        'results': results,
    }
    with open(CHECKPOINT_PATH, 'w', encoding='utf-8') as f:
        json.dump(checkpoint, f, ensure_ascii=False)


def run_extraction():
    """Main extraction loop."""
    print("=== P17 Extraction via Wikidata API ===\n", flush=True)

    # Load location QIDs
    print("Loading location QIDs from DB...", flush=True)
    qid_map = load_location_qids()
    all_qids = list(qid_map.keys())
    print(f"  {len(all_qids)} locations to process\n", flush=True)

    # Load checkpoint
    checkpoint = load_checkpoint()
    results = checkpoint.get('results', {})
    start_from = checkpoint.get('processed_count', 0)

    if start_from > 0:
        print(f"Resuming from checkpoint: {start_from} already processed, {len(results)} with P17\n", flush=True)

    # Batch processing
    total_batches = (len(all_qids) - start_from + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"Processing {len(all_qids) - start_from} QIDs in {total_batches} batches of {BATCH_SIZE}\n", flush=True)

    start_time = time.time()
    with_p17 = len(results)
    with_temporal = sum(1 for r in results.values() if any(p.get('start_year') or p.get('end_year') for p in r.get('p17', [])))
    processed = start_from
    errors = 0

    for batch_idx in range(total_batches):
        batch_start = start_from + batch_idx * BATCH_SIZE
        batch_end = min(batch_start + BATCH_SIZE, len(all_qids))
        batch_qids = all_qids[batch_start:batch_end]

        data = fetch_batch(batch_qids)
        if data is None:
            errors += 1
            print(f"  FAILED batch {batch_idx+1}/{total_batches}", flush=True)
            continue

        entities = data.get('entities', {})
        for qid in batch_qids:
            entity = entities.get(qid)
            if not entity or 'claims' not in entity:
                continue

            p17_data = extract_p17_from_entity(entity)
            if p17_data:
                loc_info = qid_map[qid]
                results[qid] = {
                    'location_id': loc_info['id'],
                    'location_name': loc_info['name'],
                    'p17': p17_data,
                }
                with_p17 += 1
                if any(d['start_year'] or d['end_year'] for d in p17_data):
                    with_temporal += 1

        processed = batch_end

        # Progress every 10 batches
        if (batch_idx + 1) % 10 == 0 or batch_idx == total_batches - 1:
            elapsed = time.time() - start_time
            pct = processed / len(all_qids) * 100
            rate = (processed - start_from) / elapsed if elapsed > 0 else 0
            eta = (len(all_qids) - processed) / rate if rate > 0 else 0
            print(f"  [{pct:.1f}%] {processed}/{len(all_qids)} | "
                  f"{with_p17} with P17 | {with_temporal} temporal | "
                  f"{errors} errors | {elapsed:.0f}s | ETA {eta:.0f}s",
                  flush=True)

        # Checkpoint every 50 batches
        if (batch_idx + 1) % 50 == 0:
            save_checkpoint(results, processed)

        # Rate limiting
        time.sleep(REQUEST_DELAY)

    elapsed = time.time() - start_time
    print(f"\n=== Extraction complete ===", flush=True)
    print(f"Processed: {processed}/{len(all_qids)}", flush=True)
    print(f"With P17: {with_p17}", flush=True)
    print(f"With temporal qualifiers: {with_temporal}", flush=True)
    print(f"Errors: {errors}", flush=True)
    print(f"Time: {elapsed:.0f}s ({elapsed/60:.1f}min)", flush=True)

    # Save final results
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(results)} results to {OUTPUT_PATH}", flush=True)

    # Clean up checkpoint
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()
        print("Checkpoint cleaned up.", flush=True)

    print("\nNext: run import_territory_locations.py", flush=True)


if __name__ == '__main__':
    run_extraction()
