"""
데이터 품질 정리 (Data Quality Cleanup)

DB에 Wikidata 대량 임포트 과정에서 발생한 품질 문제를 정리:
1. QID-only 이름 해석 (Wikidata API로 라벨 가져오기)
2. 잘못 분류된 이벤트 처리 (인물/장소가 events에 들어간 경우)
3. 인물 날짜 수정 (birth_year > death_year)
4. 이벤트-인물 시간 불일치 정리
5. 결과 리포트 출력

Usage:
    cd backend
    python ../poc/scripts/cleanup_data_quality.py --dry-run          # 리포트만
    python ../poc/scripts/cleanup_data_quality.py                     # 전체 실행
    python ../poc/scripts/cleanup_data_quality.py --step 1            # Step 1만 실행
    python ../poc/scripts/cleanup_data_quality.py --step 1 --dry-run  # Step 1 리포트만
"""

import sys
import os
import json
import time
import argparse
import requests
import psycopg2
from pathlib import Path
from collections import defaultdict
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ═══════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════

DB_URL = 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas'
CACHE_PATH = Path(r'C:\Projects\Chaldeas\poc\data\wikidata\entity_labels_cache.json')
WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
BATCH_SIZE = 50
HEADERS = {
    'User-Agent': 'ChaldeasBot/1.0 (https://www.chaldeas.site; chaldeas.archive@gmail.com)',
    'Accept': 'application/json',
}

# P31 values that indicate a human
HUMAN_P31 = {'Q5'}

# P31 values that indicate a location/geographic entity
LOCATION_P31 = {
    'Q515',       # city
    'Q6256',      # country
    'Q3624078',   # sovereign state
    'Q35657',     # state (US)
    'Q82794',     # geographic region
    'Q123705',    # neighborhood
    'Q486972',    # human settlement
    'Q532',       # village
    'Q3957',      # town
    'Q5119',      # capital city
    'Q1549591',   # big city
    'Q15284',     # municipality
    'Q34763',     # peninsula
    'Q23442',     # island
    'Q35145263',  # historical country
    'Q1496967',   # territorial entity
    'Q2327196',   # geographic location
    'Q2467461',   # ancient city
    'Q839954',    # archaeological site
    'Q3024240',   # historical location
    'Q123480',    # continent
    'Q5107',      # continent
    'Q4022',      # river
    'Q23397',     # lake
    'Q8502',      # mountain
    'Q46831',     # mountain range
    'Q47521',     # stream
    'Q35509',     # cave
    'Q180874',    # steppe
    'Q8514',      # desert
    'Q1233637',   # plateau
    'Q15324',     # body of water
    'Q165',       # sea
    'Q9430',      # ocean
}


# ═══════════════════════════════════════════
# Cache management
# ═══════════════════════════════════════════

def load_cache():
    """Load Wikidata entity labels cache."""
    if CACHE_PATH.exists():
        with open(CACHE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_cache(cache):
    """Save Wikidata entity labels cache."""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════
# Wikidata API helpers
# ═══════════════════════════════════════════

def fetch_wikidata_batch(qids, props='labels|claims', retries=3):
    """Wikidata API에서 배치로 엔티티 데이터 가져오기."""
    params = {
        'action': 'wbgetentities',
        'ids': '|'.join(qids),
        'props': props,
        'format': 'json',
    }
    # Don't filter by language - fetch all labels to maximize resolution

    for attempt in range(retries):
        try:
            resp = requests.get(WIKIDATA_API, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return resp.json().get('entities', {})
        except requests.exceptions.HTTPError:
            if resp.status_code in (429, 403):
                wait = (attempt + 1) * 2
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  API error: HTTP {resp.status_code}")
                return {}
        except Exception as e:
            print(f"  API error: {e}")
            if attempt < retries - 1:
                time.sleep(1)
    return {}


def extract_labels(entity_data):
    """엔티티에서 라벨 추출. en > ko > ja > 아무 언어 순으로 fallback."""
    labels = entity_data.get('labels', {})
    en = labels.get('en', {}).get('value')
    ko = labels.get('ko', {}).get('value')
    ja = labels.get('ja', {}).get('value')

    # Fallback: use any available label if en/ko/ja all missing
    fallback = None
    if not en and labels:
        # Prefer Latin-script languages for readability
        for lang in ['de', 'fr', 'es', 'it', 'pt', 'nl', 'pl', 'la', 'ca', 'sv', 'da', 'no']:
            if lang in labels:
                fallback = labels[lang].get('value')
                break
        if not fallback:
            # Use any available label
            for lang_data in labels.values():
                val = lang_data.get('value') if isinstance(lang_data, dict) else None
                if val:
                    fallback = val
                    break

    return {
        'en': en or fallback,
        'ko': ko,
        'ja': ja,
    }


def extract_p31(entity_data):
    """엔티티에서 P31 (instance of) QID 목록 추출."""
    claims = entity_data.get('claims', {})
    values = []
    for claim in claims.get('P31', []):
        mainsnak = claim.get('mainsnak', {})
        datavalue = mainsnak.get('datavalue', {})
        if datavalue.get('type') == 'wikibase-entityid':
            qid = 'Q' + str(datavalue['value']['numeric-id'])
            values.append(qid)
    return values


def extract_time_claim(entity_data, prop):
    """엔티티에서 시간 속성(P569/P570) 값을 연도로 추출."""
    claims = entity_data.get('claims', {})
    for claim in claims.get(prop, []):
        mainsnak = claim.get('mainsnak', {})
        datavalue = mainsnak.get('datavalue', {})
        if datavalue.get('type') == 'time':
            time_str = datavalue['value'].get('time', '')
            # Format: +YYYYYYYYYY-MM-DDT00:00:00Z (11-digit year with leading zeros)
            # e.g. +00000001727-01-01T00:00:00Z or -00000000490-01-01T00:00:00Z
            try:
                sign = time_str[0]
                # Find the first dash after the sign to isolate the year
                dash_pos = time_str.index('-', 1)
                year = int(time_str[1:dash_pos])
                if sign == '-':
                    year = -year
                return year
            except (ValueError, IndexError):
                continue
    return None


# ═══════════════════════════════════════════
# Step 1: QID Name Resolution
# ═══════════════════════════════════════════

def step1_resolve_qid_names(dry_run=False):
    """QID-only 이름을 Wikidata API로 해석하여 업데이트."""
    print("\n" + "=" * 60)
    print("STEP 1: QID Name Resolution")
    print("=" * 60)

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Collect QID-only records from all tables
    qid_records = {}  # qid -> {'tables': [('events', id, 'title'), ...]}

    # Events with QID-only title
    cur.execute("SELECT id, title FROM events WHERE title ~ '^Q[0-9]+$'")
    event_qids = cur.fetchall()
    print(f"  Events with QID-only title: {len(event_qids)}")
    for row in event_qids:
        qid = row[1]
        if qid not in qid_records:
            qid_records[qid] = {'tables': []}
        qid_records[qid]['tables'].append(('events', row[0], 'title'))

    # Persons with QID-only name
    cur.execute("SELECT id, name FROM persons WHERE name ~ '^Q[0-9]+$'")
    person_qids = cur.fetchall()
    print(f"  Persons with QID-only name: {len(person_qids)}")
    for row in person_qids:
        qid = row[1]
        if qid not in qid_records:
            qid_records[qid] = {'tables': []}
        qid_records[qid]['tables'].append(('persons', row[0], 'name'))

    # Locations with QID-only name
    cur.execute("SELECT id, name FROM locations WHERE name ~ '^Q[0-9]+$'")
    location_qids = cur.fetchall()
    print(f"  Locations with QID-only name: {len(location_qids)}")
    for row in location_qids:
        qid = row[1]
        if qid not in qid_records:
            qid_records[qid] = {'tables': []}
        qid_records[qid]['tables'].append(('locations', row[0], 'name'))

    all_qids = list(qid_records.keys())
    total = len(all_qids)
    print(f"\n  Total unique QIDs to resolve: {total}")

    if total == 0:
        print("  Nothing to resolve!")
        cur.close()
        conn.close()
        return {'resolved': 0, 'not_found': 0, 'misclassified_humans': [], 'misclassified_locations': []}

    # Load cache
    cache = load_cache()
    cached_count = sum(1 for q in all_qids if q in cache)
    to_fetch = [q for q in all_qids if q not in cache]
    print(f"  Cached: {cached_count}, Need to fetch: {len(to_fetch)}")

    # Fetch from Wikidata API
    if to_fetch:
        total_batches = (len(to_fetch) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  Fetching {len(to_fetch)} QIDs in {total_batches} batches...")

        for i in range(0, len(to_fetch), BATCH_SIZE):
            batch = to_fetch[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1

            if batch_num % 50 == 0 or batch_num == 1 or batch_num == total_batches:
                print(f"    Batch {batch_num}/{total_batches}...")

            entities = fetch_wikidata_batch(batch, props='labels|claims')

            for qid in batch:
                entity = entities.get(qid, {})
                if 'missing' in entity:
                    cache[qid] = {'labels': {'en': None, 'ko': None, 'ja': None}, 'p31': [], 'missing': True}
                else:
                    labels = extract_labels(entity)
                    p31 = extract_p31(entity)
                    cache[qid] = {'labels': labels, 'p31': p31}

            time.sleep(0.2)

            # Save cache every 100 batches
            if batch_num % 100 == 0:
                save_cache(cache)

        save_cache(cache)
        print(f"  Cache saved ({len(cache)} entries)")

    # Process results
    stats = {
        'resolved': defaultdict(int),
        'not_found': defaultdict(int),
        'misclassified_humans': [],
        'misclassified_locations': [],
    }

    updates = []  # (table, id, column, en_name, ko_name, ja_name)

    for qid, info in qid_records.items():
        cached = cache.get(qid, {})
        labels = cached.get('labels', {})
        p31_list = cached.get('p31', [])
        en_name = labels.get('en')

        for table, record_id, column in info['tables']:
            if en_name:
                ko_name = labels.get('ko')
                ja_name = labels.get('ja')
                updates.append((table, record_id, column, en_name, ko_name, ja_name))
                stats['resolved'][table] += 1
            else:
                stats['not_found'][table] += 1

            # Check for misclassified events
            if table == 'events':
                if any(p in HUMAN_P31 for p in p31_list):
                    stats['misclassified_humans'].append({
                        'event_id': record_id,
                        'qid': qid,
                        'name': en_name or qid,
                        'p31': p31_list,
                    })
                elif any(p in LOCATION_P31 for p in p31_list):
                    stats['misclassified_locations'].append({
                        'event_id': record_id,
                        'qid': qid,
                        'name': en_name or qid,
                        'p31': p31_list,
                    })

    # Also check events that have resolved names but might be misclassified
    # Query all events with wikidata_id to check P31 from cache
    cur.execute("SELECT id, wikidata_id, title FROM events WHERE wikidata_id IS NOT NULL")
    all_events = cur.fetchall()
    for event_id, wikidata_id, title in all_events:
        if wikidata_id in cache and title and not title.startswith('Q'):
            # Already has a name, but check P31 for misclassification
            cached = cache.get(wikidata_id, {})
            p31_list = cached.get('p31', [])
            if any(p in HUMAN_P31 for p in p31_list):
                # Check if not already in the list
                existing_ids = {m['event_id'] for m in stats['misclassified_humans']}
                if event_id not in existing_ids:
                    stats['misclassified_humans'].append({
                        'event_id': event_id,
                        'qid': wikidata_id,
                        'name': title,
                        'p31': p31_list,
                    })
            elif any(p in LOCATION_P31 for p in p31_list):
                existing_ids = {m['event_id'] for m in stats['misclassified_locations']}
                if event_id not in existing_ids:
                    stats['misclassified_locations'].append({
                        'event_id': event_id,
                        'qid': wikidata_id,
                        'name': title,
                        'p31': p31_list,
                    })

    # Apply updates
    if not dry_run and updates:
        print(f"\n  Applying {len(updates)} name updates...")
        for table, record_id, column, en_name, ko_name, ja_name in updates:
            ko_col = column + '_ko' if column == 'title' else 'name_ko'
            ja_col = column + '_ja' if column == 'title' else 'name_ja'

            set_parts = [f"{column} = %s"]
            params = [en_name]

            if ko_name:
                set_parts.append(f"{ko_col} = COALESCE({ko_col}, %s)")
                params.append(ko_name)
            if ja_name:
                set_parts.append(f"{ja_col} = COALESCE({ja_col}, %s)")
                params.append(ja_name)

            params.append(record_id)
            cur.execute(
                f"UPDATE {table} SET {', '.join(set_parts)} WHERE id = %s",
                params
            )

        conn.commit()
        print(f"  Updates committed.")
    elif dry_run:
        print(f"\n  [DRY RUN] Would apply {len(updates)} name updates")

    # Print summary
    print(f"\n  --- Step 1 Results ---")
    for table in ['events', 'persons', 'locations']:
        r = stats['resolved'].get(table, 0)
        nf = stats['not_found'].get(table, 0)
        print(f"    {table}: {r} resolved, {nf} not found on Wikidata")
    print(f"    Misclassified as events (actually humans): {len(stats['misclassified_humans'])}")
    print(f"    Misclassified as events (actually locations): {len(stats['misclassified_locations'])}")

    if stats['misclassified_humans'][:10]:
        print(f"\n    Sample misclassified humans:")
        for m in stats['misclassified_humans'][:10]:
            print(f"      event_id={m['event_id']} qid={m['qid']} name={m['name']}")

    if stats['misclassified_locations'][:10]:
        print(f"\n    Sample misclassified locations:")
        for m in stats['misclassified_locations'][:10]:
            print(f"      event_id={m['event_id']} qid={m['qid']} name={m['name']}")

    cur.close()
    conn.close()

    return stats


# ═══════════════════════════════════════════
# Step 2: Misclassified Events
# ═══════════════════════════════════════════

def step2_fix_misclassified_events(dry_run=False, misclassified_humans=None):
    """이벤트 테이블에서 인물/장소로 잘못 분류된 엔티티 처리."""
    print("\n" + "=" * 60)
    print("STEP 2: Fix Misclassified Events")
    print("=" * 60)

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cache = load_cache()

    # If not passed from step 1, find misclassified events ourselves
    if misclassified_humans is None:
        misclassified_humans = []
        cur.execute("SELECT id, wikidata_id, title FROM events WHERE wikidata_id IS NOT NULL")
        for event_id, wikidata_id, title in cur.fetchall():
            cached = cache.get(wikidata_id, {})
            p31_list = cached.get('p31', [])
            if any(p in HUMAN_P31 for p in p31_list):
                misclassified_humans.append({
                    'event_id': event_id,
                    'qid': wikidata_id,
                    'name': title or wikidata_id,
                })

    print(f"  Misclassified humans in events table: {len(misclassified_humans)}")

    if not misclassified_humans:
        print("  Nothing to fix!")
        cur.close()
        conn.close()
        return {'moved_to_persons': 0, 'deleted_duplicates': 0, 'cleaned_references': 0}

    stats = {'moved_to_persons': 0, 'deleted_duplicates': 0, 'cleaned_references': 0}

    for m in misclassified_humans:
        event_id = m['event_id']
        qid = m['qid']
        name = m['name']

        # Check if this person already exists in persons table
        cur.execute("SELECT id FROM persons WHERE wikidata_id = %s", (qid,))
        existing_person = cur.fetchone()

        if existing_person:
            person_id = existing_person[0]
            if dry_run:
                print(f"    [DRY RUN] Would delete event {event_id} ({name}) - already in persons as id={person_id}")
            else:
                # Delete references first
                cur.execute("DELETE FROM event_persons WHERE event_id = %s", (event_id,))
                cur.execute("DELETE FROM event_locations WHERE event_id = %s", (event_id,))
                cur.execute("DELETE FROM event_sources WHERE event_id = %s", (event_id,))
                cur.execute("DELETE FROM event_details WHERE event_id = %s", (event_id,))
                cur.execute("DELETE FROM event_relationships WHERE from_event_id = %s OR to_event_id = %s", (event_id, event_id))
                # Update children to remove parent reference
                cur.execute("UPDATE events SET parent_event_id = NULL WHERE parent_event_id = %s", (event_id,))
                cur.execute("DELETE FROM events WHERE id = %s", (event_id,))
                stats['cleaned_references'] += 1
            stats['deleted_duplicates'] += 1
        else:
            # Get cached labels for this entity
            cached = cache.get(qid, {})
            labels = cached.get('labels', {})
            en_name = labels.get('en') or name
            ko_name = labels.get('ko')
            ja_name = labels.get('ja')

            # Get birth/death from cache or fetch
            birth_year = None
            death_year = None
            entity_data = None

            # We need claims data - check if we have P569/P570 cached
            # For this we need to fetch with claims
            if qid not in cache or 'birth_year' not in cache.get(qid, {}):
                entities = fetch_wikidata_batch([qid], props='claims')
                entity_data = entities.get(qid, {})
                birth_year = extract_time_claim(entity_data, 'P569')
                death_year = extract_time_claim(entity_data, 'P570')
                # Update cache
                if qid in cache:
                    cache[qid]['birth_year'] = birth_year
                    cache[qid]['death_year'] = death_year
                time.sleep(0.2)

            if dry_run:
                print(f"    [DRY RUN] Would move event {event_id} ({en_name}) to persons table")
            else:
                # Insert into persons
                cur.execute("""
                    INSERT INTO persons (wikidata_id, name, name_ko, name_ja, birth_year, death_year)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (qid, en_name, ko_name, ja_name, birth_year, death_year))
                new_person_id = cur.fetchone()[0]

                # Clean up event references
                cur.execute("DELETE FROM event_persons WHERE event_id = %s", (event_id,))
                cur.execute("DELETE FROM event_locations WHERE event_id = %s", (event_id,))
                cur.execute("DELETE FROM event_sources WHERE event_id = %s", (event_id,))
                cur.execute("DELETE FROM event_details WHERE event_id = %s", (event_id,))
                cur.execute("DELETE FROM event_relationships WHERE from_event_id = %s OR to_event_id = %s", (event_id, event_id))
                cur.execute("UPDATE events SET parent_event_id = NULL WHERE parent_event_id = %s", (event_id,))
                cur.execute("DELETE FROM events WHERE id = %s", (event_id,))
                stats['cleaned_references'] += 1

            stats['moved_to_persons'] += 1

    if not dry_run:
        conn.commit()
        save_cache(cache)

    print(f"\n  --- Step 2 Results ---")
    print(f"    Moved to persons: {stats['moved_to_persons']}")
    print(f"    Deleted (already in persons): {stats['deleted_duplicates']}")
    print(f"    Cleaned event references: {stats['cleaned_references']}")

    cur.close()
    conn.close()
    return stats


# ═══════════════════════════════════════════
# Step 3: Fix Person Dates
# ═══════════════════════════════════════════

def step3_fix_person_dates(dry_run=False):
    """birth_year > death_year인 인물의 날짜를 Wikidata에서 재확인하여 수정."""
    print("\n" + "=" * 60)
    print("STEP 3: Fix Person Dates (birth > death)")
    print("=" * 60)

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, wikidata_id, name, birth_year, death_year
        FROM persons
        WHERE birth_year IS NOT NULL AND death_year IS NOT NULL
          AND birth_year > death_year
    """)
    bad_dates = cur.fetchall()
    print(f"  Persons with birth > death: {len(bad_dates)}")

    if not bad_dates:
        print("  Nothing to fix!")
        cur.close()
        conn.close()
        return {'fixed_from_wikidata': 0, 'nullified': 0, 'no_wikidata': 0}

    stats = {'fixed_from_wikidata': 0, 'nullified': 0, 'no_wikidata': 0, 'swapped': 0}

    # Collect QIDs to fetch
    qids_to_fetch = [row[1] for row in bad_dates if row[1]]
    qid_data = {}

    if qids_to_fetch:
        total_batches = (len(qids_to_fetch) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  Fetching {len(qids_to_fetch)} QIDs in {total_batches} batches...")

        for i in range(0, len(qids_to_fetch), BATCH_SIZE):
            batch = qids_to_fetch[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1

            entities = fetch_wikidata_batch(batch, props='claims')

            for qid in batch:
                entity = entities.get(qid, {})
                birth = extract_time_claim(entity, 'P569')
                death = extract_time_claim(entity, 'P570')
                qid_data[qid] = {'birth': birth, 'death': death}

            time.sleep(0.2)

    # Process each person
    for person_id, wikidata_id, name, db_birth, db_death in bad_dates:
        wd = qid_data.get(wikidata_id, {}) if wikidata_id else {}
        wd_birth = wd.get('birth')
        wd_death = wd.get('death')

        action = None
        new_birth = db_birth
        new_death = db_death

        if wd_birth is not None and wd_death is not None:
            if wd_birth <= wd_death:
                # Wikidata has correct dates
                new_birth = wd_birth
                new_death = wd_death
                action = 'wikidata_fix'
                stats['fixed_from_wikidata'] += 1
            else:
                # Wikidata also has birth > death (same import source)
                # Swap: these dates are usually just reversed
                new_birth = wd_death
                new_death = wd_birth
                action = 'swap_wd'
                stats['swapped'] += 1
        elif wd_birth is not None or wd_death is not None:
            # Partial Wikidata data - use what we have
            new_birth = wd_birth
            new_death = wd_death
            action = 'wikidata_partial'
            stats['fixed_from_wikidata'] += 1
        else:
            # No date claims from Wikidata - swap DB values if it fixes the issue
            if not wikidata_id:
                stats['no_wikidata'] += 1
            new_birth = db_death
            new_death = db_birth
            if new_birth <= new_death:
                action = 'swap'
                stats['swapped'] += 1
            else:
                new_birth = None
                new_death = None
                action = 'nullify'
                stats['nullified'] += 1

        if dry_run:
            print(f"    [DRY RUN] {name} (id={person_id}): {db_birth}→{db_death} => "
                  f"{new_birth}→{new_death} ({action})")
        else:
            cur.execute(
                "UPDATE persons SET birth_year = %s, death_year = %s WHERE id = %s",
                (new_birth, new_death, person_id)
            )

    if not dry_run:
        conn.commit()

    print(f"\n  --- Step 3 Results ---")
    print(f"    Fixed from Wikidata: {stats['fixed_from_wikidata']}")
    print(f"    Swapped (birth/death reversed): {stats['swapped']}")
    print(f"    Nullified (unresolvable): {stats['nullified']}")
    print(f"    No Wikidata ID: {stats['no_wikidata']}")

    cur.close()
    conn.close()
    return stats


# ═══════════════════════════════════════════
# Step 4: Event-Person Time Mismatch
# ═══════════════════════════════════════════

def step4_fix_event_person_mismatch(dry_run=False):
    """이벤트-인물 시간 불일치 링크 정리."""
    print("\n" + "=" * 60)
    print("STEP 4: Fix Event-Person Time Mismatches")
    print("=" * 60)

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Find mismatches: person lived > 50 years before/after event
    cur.execute("""
        SELECT ep.event_id, ep.person_id, ep.role,
               e.title, e.date_start, e.date_end,
               p.name, p.birth_year, p.death_year
        FROM event_persons ep
        JOIN events e ON e.id = ep.event_id
        JOIN persons p ON p.id = ep.person_id
        WHERE p.birth_year IS NOT NULL
          AND e.date_start IS NOT NULL
          AND e.date_end IS NOT NULL
          AND (
              p.birth_year > e.date_end + 50
              OR (p.death_year IS NOT NULL AND p.death_year < e.date_start - 50)
          )
    """)
    mismatches = cur.fetchall()
    print(f"  Event-person time mismatches (50yr threshold): {len(mismatches)}")

    if not mismatches:
        print("  Nothing to fix!")
        cur.close()
        conn.close()
        return {'removed': 0, 'kept': 0}

    stats = {'removed': 0, 'kept': 0, 'details': []}

    for event_id, person_id, role, event_title, e_start, e_end, p_name, p_birth, p_death in mismatches:
        # Calculate overlap
        person_start = p_birth
        person_end = p_death if p_death else p_birth + 80  # Assume ~80 year lifespan if no death

        # Check if there's any reasonable overlap
        overlap_start = max(person_start, e_start)
        overlap_end = min(person_end, e_end)
        gap = overlap_start - overlap_end if overlap_start > overlap_end else 0

        detail = {
            'event_id': event_id,
            'person_id': person_id,
            'event': event_title,
            'person': p_name,
            'event_range': f"{e_start}-{e_end}",
            'person_range': f"{p_birth}-{p_death or '?'}",
            'gap_years': gap,
        }

        if gap > 50:
            # Clear mismatch - remove the link
            stats['removed'] += 1
            detail['action'] = 'remove'

            if not dry_run:
                cur.execute(
                    "DELETE FROM event_persons WHERE event_id = %s AND person_id = %s",
                    (event_id, person_id)
                )
        else:
            stats['kept'] += 1
            detail['action'] = 'keep'

        stats['details'].append(detail)

    if not dry_run:
        conn.commit()

    # Print sample removals
    removals = [d for d in stats['details'] if d['action'] == 'remove']
    if removals:
        print(f"\n  Sample removals:")
        for d in removals[:15]:
            prefix = "[DRY RUN] " if dry_run else ""
            print(f"    {prefix}{d['person']} ({d['person_range']}) <-> {d['event']} ({d['event_range']}) gap={d['gap_years']}yr")

    print(f"\n  --- Step 4 Results ---")
    print(f"    Links removed: {stats['removed']}")
    print(f"    Links kept (within tolerance): {stats['kept']}")

    cur.close()
    conn.close()
    return stats


# ═══════════════════════════════════════════
# Step 5: Final Report
# ═══════════════════════════════════════════

def step5_report():
    """현재 DB 상태의 데이터 품질 리포트."""
    print("\n" + "=" * 60)
    print("STEP 5: Data Quality Report (Current State)")
    print("=" * 60)

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # QID-only names remaining
    cur.execute("SELECT COUNT(*) FROM events WHERE title ~ '^Q[0-9]+$'")
    qid_events = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM persons WHERE name ~ '^Q[0-9]+$'")
    qid_persons = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM locations WHERE name ~ '^Q[0-9]+$'")
    qid_locations = cur.fetchone()[0]

    # Person date errors
    cur.execute("SELECT COUNT(*) FROM persons WHERE birth_year IS NOT NULL AND death_year IS NOT NULL AND birth_year > death_year")
    bad_dates = cur.fetchone()[0]

    # Event-person mismatches
    cur.execute("""
        SELECT COUNT(*) FROM event_persons ep
        JOIN events e ON e.id = ep.event_id
        JOIN persons p ON p.id = ep.person_id
        WHERE p.birth_year IS NOT NULL AND e.date_start IS NOT NULL AND e.date_end IS NOT NULL
        AND (p.birth_year > e.date_end + 50 OR (p.death_year IS NOT NULL AND p.death_year < e.date_start - 50))
    """)
    mismatches = cur.fetchone()[0]

    # Total counts
    cur.execute("SELECT COUNT(*) FROM events")
    total_events = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM persons")
    total_persons = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM locations")
    total_locations = cur.fetchone()[0]

    print(f"""
  === Data Quality Report ===

  Total Records:
    Events:    {total_events:,}
    Persons:   {total_persons:,}
    Locations: {total_locations:,}

  QID-Only Names (no human-readable name):
    Events:    {qid_events:,} / {total_events:,}
    Persons:   {qid_persons:,} / {total_persons:,} ({qid_persons/max(total_persons,1)*100:.1f}%)
    Locations: {qid_locations:,} / {total_locations:,}

  Date Errors:
    Persons with birth > death: {bad_dates}

  Relationship Errors:
    Event-person time mismatches (50yr+): {mismatches}
""")

    cur.close()
    conn.close()

    return {
        'qid_events': qid_events,
        'qid_persons': qid_persons,
        'qid_locations': qid_locations,
        'bad_dates': bad_dates,
        'mismatches': mismatches,
    }


# ═══════════════════════════════════════════
# Main
# ═══════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='Data Quality Cleanup')
    parser.add_argument('--dry-run', action='store_true', help='Report only, no DB modifications')
    parser.add_argument('--step', type=int, choices=[1, 2, 3, 4, 5], help='Run specific step only')
    args = parser.parse_args()

    start_time = datetime.now()
    mode = "DRY RUN" if args.dry_run else "LIVE"
    step_desc = f"Step {args.step}" if args.step else "All Steps"

    print(f"╔{'═' * 58}╗")
    print(f"║  Data Quality Cleanup - {mode} - {step_desc:<20}     ║")
    print(f"║  Started: {start_time.strftime('%Y-%m-%d %H:%M:%S'):<46} ║")
    print(f"╚{'═' * 58}╝")

    all_stats = {}

    # Step 5 first as baseline (report only)
    if args.step is None or args.step == 5:
        if args.step == 5:
            step5_report()
            return

    # Show baseline
    if args.step is None:
        print("\n  --- BASELINE (before cleanup) ---")
        step5_report()

    # Step 1: QID Name Resolution
    if args.step is None or args.step == 1:
        step1_stats = step1_resolve_qid_names(dry_run=args.dry_run)
        all_stats['step1'] = step1_stats

    # Step 2: Misclassified Events
    if args.step is None or args.step == 2:
        misclassified = None
        if 'step1' in all_stats:
            misclassified = all_stats['step1'].get('misclassified_humans')
        step2_stats = step2_fix_misclassified_events(
            dry_run=args.dry_run,
            misclassified_humans=misclassified
        )
        all_stats['step2'] = step2_stats

    # Step 3: Person Dates
    if args.step is None or args.step == 3:
        step3_stats = step3_fix_person_dates(dry_run=args.dry_run)
        all_stats['step3'] = step3_stats

    # Step 4: Event-Person Mismatches
    if args.step is None or args.step == 4:
        step4_stats = step4_fix_event_person_mismatch(dry_run=args.dry_run)
        all_stats['step4'] = step4_stats

    # Final report
    if args.step is None:
        print("\n  --- AFTER CLEANUP ---")
        step5_report()

    # Summary
    elapsed = datetime.now() - start_time
    print(f"\n{'=' * 60}")
    print(f"  Completed in {elapsed.total_seconds():.1f}s")
    if args.dry_run:
        print(f"  [DRY RUN] No changes were made to the database.")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
