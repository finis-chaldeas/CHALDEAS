"""
Placeholder 인물 이름을 Wikidata에서 채우기.
'Person Q...' 형태의 인물들의 실제 이름을 가져옴.

Usage:
    python fill_person_names.py           # 처음부터 시작
    python fill_person_names.py --resume  # 이전 위치에서 재개
"""

import sys
import os
import json
import time
import argparse
import requests
import psycopg2

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

WIKIDATA_ENDPOINT = 'https://query.wikidata.org/sparql'
PROGRESS_FILE = os.path.join(os.path.dirname(__file__), 'fill_names_progress.json')


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'last_batch': 0, 'stats': {'updated': 0, 'not_found': 0, 'errors': 0}}


def save_progress(batch_num, stats):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump({'last_batch': batch_num, 'stats': stats}, f)


def sparql_query_with_retry(query, max_retries=3):
    for retry in range(max_retries):
        try:
            resp = requests.get(
                WIKIDATA_ENDPOINT,
                params={'query': query, 'format': 'json'},
                headers={'User-Agent': 'CHALDEAS/1.0'},
                timeout=60
            )
            if resp.status_code == 200:
                return resp.json()['results']['bindings']
            elif resp.status_code == 429:
                wait_time = 30 * (retry + 1)
                print(f"Rate limited, waiting {wait_time}s...", flush=True)
                time.sleep(wait_time)
            elif resp.status_code >= 500:
                wait_time = 15 * (retry + 1)
                print(f"Server error {resp.status_code}, waiting {wait_time}s...", flush=True)
                time.sleep(wait_time)
            else:
                print(f"SPARQL error {resp.status_code}", flush=True)
                return None
        except requests.exceptions.Timeout:
            wait_time = 30 * (retry + 1)
            print(f"Timeout, waiting {wait_time}s (retry {retry+1}/{max_retries})...", flush=True)
            time.sleep(wait_time)
        except Exception as e:
            wait_time = 15 * (retry + 1)
            print(f"Error: {e}, waiting {wait_time}s...", flush=True)
            time.sleep(wait_time)
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()

    conn = psycopg2.connect(
        host='localhost', port=5432,
        database='chaldeas', user='chaldeas', password='chaldeas_dev'
    )
    cur = conn.cursor()

    # Placeholder 인물 목록
    cur.execute("""
        SELECT id, wikidata_id FROM persons
        WHERE name LIKE 'Person Q%' AND wikidata_id IS NOT NULL
        ORDER BY id
    """)
    persons = cur.fetchall()
    person_qid_to_id = {qid: pid for pid, qid in persons}
    all_qids = [qid for _, qid in persons]

    print(f"Total placeholder persons: {len(all_qids)}")

    batch_size = 200  # Wikidata labels are fast
    if args.resume:
        progress = load_progress()
        start_batch = progress['last_batch']
        stats = progress['stats']
        print(f"Resuming from batch {start_batch + 1}")
    else:
        start_batch = 0
        stats = {'updated': 0, 'not_found': 0, 'errors': 0}

    total_batches = (len(all_qids) - 1) // batch_size + 1

    for i in range(start_batch * batch_size, len(all_qids), batch_size):
        batch = all_qids[i:i+batch_size]
        batch_num = i // batch_size + 1

        print(f"  Batch {batch_num}/{total_batches}... ", end='', flush=True)

        # 라벨 + 생년/몰년 쿼리
        values = ' '.join([f'wd:{q}' for q in batch])
        query = f"""
        SELECT ?person ?personLabel ?birthDate ?deathDate WHERE {{
            VALUES ?person {{ {values} }}
            OPTIONAL {{ ?person wdt:P569 ?birthDate. }}
            OPTIONAL {{ ?person wdt:P570 ?deathDate. }}
            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,ko". }}
        }}
        """

        results = sparql_query_with_retry(query)

        if results is None:
            stats['errors'] += 1
            save_progress(batch_num, stats)
            time.sleep(5)
            continue

        batch_updated = 0

        # QID -> data 매핑
        person_data = {}
        for r in results:
            qid = r.get('person', {}).get('value', '').split('/')[-1]
            label = r.get('personLabel', {}).get('value', '')
            birth = r.get('birthDate', {}).get('value', '')
            death = r.get('deathDate', {}).get('value', '')

            # 라벨이 QID 자체면 스킵
            if label and not label.startswith('Q'):
                person_data[qid] = {
                    'label': label,
                    'birth': birth,
                    'death': death
                }

        # DB 업데이트
        for qid in batch:
            if qid not in person_data:
                stats['not_found'] += 1
                continue

            data = person_data[qid]
            person_id = person_qid_to_id[qid]

            # 생년/몰년 파싱
            birth_year = None
            death_year = None
            if data['birth']:
                try:
                    if data['birth'][0] == '-':
                        birth_year = -int(data['birth'][1:5])
                    elif data['birth'][0] == '+':
                        birth_year = int(data['birth'][1:5])
                    else:
                        birth_year = int(data['birth'][:4])
                except:
                    pass
            if data['death']:
                try:
                    if data['death'][0] == '-':
                        death_year = -int(data['death'][1:5])
                    elif data['death'][0] == '+':
                        death_year = int(data['death'][1:5])
                    else:
                        death_year = int(data['death'][:4])
                except:
                    pass

            try:
                cur.execute("""
                    UPDATE persons
                    SET name = %s, birth_year = COALESCE(%s, birth_year),
                        death_year = COALESCE(%s, death_year), updated_at = NOW()
                    WHERE id = %s
                """, (data['label'], birth_year, death_year, person_id))
                batch_updated += 1
                stats['updated'] += 1
            except Exception as e:
                conn.rollback()
                stats['errors'] += 1

        conn.commit()
        print(f"updated {batch_updated}, not_found {len(batch) - batch_updated}")

        save_progress(batch_num, stats)
        time.sleep(1)  # Rate limiting

    conn.close()

    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

    print("\n" + "="*50)
    print("FILL NAMES COMPLETE")
    print("="*50)
    print(f"  Updated: {stats['updated']}")
    print(f"  Not found: {stats['not_found']}")
    print(f"  Errors: {stats['errors']}")


if __name__ == '__main__':
    main()
