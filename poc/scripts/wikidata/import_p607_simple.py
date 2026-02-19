"""
P607 (conflict) 기반 인물-이벤트 연결 임포트.
Wikidata에서 인물이 참여한 전투/전쟁/이벤트 연결.

Usage:
    python import_p607_simple.py           # 처음부터 시작
    python import_p607_simple.py --resume  # 이전 위치에서 재개
"""

import sys
import os
import json
import time
import argparse
import requests
import psycopg2
import re

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

WIKIDATA_ENDPOINT = 'https://query.wikidata.org/sparql'
PROGRESS_FILE = os.path.join(os.path.dirname(__file__), 'p607_progress.json')


def load_progress():
    """진행 상황 로드."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'last_batch': 0, 'stats': {'found': 0, 'linked': 0, 'created': 0, 'errors': 0}}


def save_progress(batch_num, stats):
    """진행 상황 저장."""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump({'last_batch': batch_num, 'stats': stats}, f)


def sparql_query_with_retry(query, max_retries=3):
    """재시도 로직이 있는 SPARQL 쿼리."""
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
            elif resp.status_code == 429:  # Too Many Requests
                wait_time = 30 * (retry + 1)
                print(f"Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            elif resp.status_code >= 500:  # Server error
                wait_time = 15 * (retry + 1)
                print(f"Server error {resp.status_code}, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"SPARQL error {resp.status_code}")
                return None

        except requests.exceptions.Timeout:
            wait_time = 30 * (retry + 1)
            print(f"Timeout, waiting {wait_time}s (retry {retry+1}/{max_retries})...")
            time.sleep(wait_time)
        except Exception as e:
            wait_time = 15 * (retry + 1)
            print(f"Error: {e}, waiting {wait_time}s...")
            time.sleep(wait_time)

    print(f"Failed after {max_retries} retries")
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', action='store_true', help='Resume from last position')
    args = parser.parse_args()

    conn = psycopg2.connect(
        host='localhost', port=5432,
        database='chaldeas', user='chaldeas', password='chaldeas_dev'
    )
    cur = conn.cursor()

    # QID 있는 이벤트 목록
    cur.execute("""
        SELECT id, wikidata_id FROM events
        WHERE wikidata_id IS NOT NULL
        ORDER BY id
    """)
    events = cur.fetchall()
    event_qid_to_id = {qid: eid for eid, qid in events}
    all_qids = list(event_qid_to_id.keys())

    print(f"Total events with QID: {len(all_qids)}")

    # 진행 상황 로드/초기화
    batch_size = 25  # Reduced from 100 to avoid timeouts
    if args.resume:
        progress = load_progress()
        start_batch = progress['last_batch']
        stats = progress['stats']
        print(f"Resuming from batch {start_batch + 1}")
    else:
        start_batch = 0
        stats = {'found': 0, 'linked': 0, 'created': 0, 'errors': 0}

    total_batches = (len(all_qids) - 1) // batch_size + 1

    for i in range(start_batch * batch_size, len(all_qids), batch_size):
        batch = all_qids[i:i+batch_size]
        batch_num = i // batch_size + 1

        print(f"  Batch {batch_num}/{total_batches}... ", end='', flush=True)
        sys.stdout.flush()

        # P607 쿼리 (라벨 없이 - 속도 최적화)
        values = ' '.join([f'wd:{q}' for q in batch])
        query = f"""
        SELECT ?event ?person WHERE {{
            VALUES ?event {{ {values} }}
            ?person wdt:P607 ?event.
            ?person wdt:P31 wd:Q5.
        }}
        """

        results = sparql_query_with_retry(query)

        if results is None:
            stats['errors'] += 1
            save_progress(batch_num, stats)
            time.sleep(5)
            continue

        batch_found = len(results)
        batch_linked = 0
        batch_created = 0

        # 결과에서 유니크 person QID 수집
        person_qids = set()
        event_person_pairs = []
        for r in results:
            event_qid = r.get('event', {}).get('value', '').split('/')[-1]
            person_qid = r.get('person', {}).get('value', '').split('/')[-1]
            if event_qid in event_qid_to_id:
                person_qids.add(person_qid)
                event_person_pairs.append((event_qid, person_qid))

        # 기존 인물 조회 (한번에)
        if person_qids:
            cur.execute(
                "SELECT wikidata_id, id FROM persons WHERE wikidata_id = ANY(%s)",
                (list(person_qids),)
            )
            existing_persons = dict(cur.fetchall())
        else:
            existing_persons = {}

        # 없는 인물 생성
        new_person_qids = person_qids - set(existing_persons.keys())
        for pqid in new_person_qids:
            try:
                cur.execute("""
                    INSERT INTO persons (name, slug, wikidata_id, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                    RETURNING id
                """, (f"Person {pqid}", f"person-{pqid.lower()}", pqid))
                existing_persons[pqid] = cur.fetchone()[0]
                batch_created += 1
            except Exception:
                conn.rollback()
                stats['errors'] += 1

        # 연결 생성
        for event_qid, person_qid in event_person_pairs:
            if person_qid not in existing_persons:
                continue
            event_id = event_qid_to_id[event_qid]
            person_id = existing_persons[person_qid]
            try:
                cur.execute("""
                    INSERT INTO event_persons (event_id, person_id, role)
                    VALUES (%s, %s, 'participant')
                    ON CONFLICT DO NOTHING
                """, (event_id, person_id))
                if cur.rowcount > 0:
                    batch_linked += 1
            except Exception:
                conn.rollback()

        stats['found'] += batch_found
        stats['created'] += batch_created
        stats['linked'] += batch_linked
        conn.commit()
        print(f"found {batch_found}, linked {batch_linked}")

        # 진행 상황 저장
        save_progress(batch_num, stats)

        time.sleep(2)  # Rate limiting

    conn.close()

    # 완료 시 진행 파일 삭제
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

    print("\n" + "="*50)
    print("P607 IMPORT COMPLETE")
    print("="*50)
    print(f"  Persons found: {stats['found']}")
    print(f"  Persons created: {stats['created']}")
    print(f"  Links created: {stats['linked']}")
    print(f"  Errors: {stats['errors']}")


if __name__ == '__main__':
    main()
