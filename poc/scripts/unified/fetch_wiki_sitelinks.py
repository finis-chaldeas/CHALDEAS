"""
Wikidata API에서 enwiki sitelinks 일괄 조회.
QID → Wikipedia 타이틀 매핑 파일 생성.

한 번만 실행하면 됨. 결과 파일로 계속 사용.

Usage:
    python fetch_wiki_sitelinks.py --batch-size 50 --output wiki_sitelinks.json
"""

import sys
import os
import json
import time
import argparse
import psycopg2
import requests
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}

WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
OUTPUT_DIR = 'poc/data/wikipedia_extract'


HEADERS = {
    'User-Agent': 'ChaldeasBot/1.0 (https://github.com/chaldeas; contact@chaldeas.site)'
}


def fetch_sitelinks_batch(qids):
    """Wikidata API로 QID 배치의 enwiki sitelink 조회."""
    if not qids:
        return {}

    params = {
        'action': 'wbgetentities',
        'ids': '|'.join(qids),
        'props': 'sitelinks',
        'sitefilter': 'enwiki',
        'format': 'json'
    }

    try:
        resp = requests.get(WIKIDATA_API, params=params, headers=HEADERS, timeout=30)
        data = resp.json()

        results = {}
        entities = data.get('entities', {})
        for qid, entity in entities.items():
            sitelinks = entity.get('sitelinks', {})
            if 'enwiki' in sitelinks:
                wiki_title = sitelinks['enwiki'].get('title')
                if wiki_title:
                    results[qid] = wiki_title
        return results
    except Exception as e:
        print(f"  API error: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch-size', type=int, default=50)
    parser.add_argument('--output', default='wiki_sitelinks.json')
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, args.output)

    # 기존 결과 로드 (resume)
    existing = {}
    if args.resume and os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            existing = data.get('qid_to_wiki', {})
        print(f"Resume: {len(existing):,} existing")

    # DB에서 QID 수집
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    qid_to_entity = {}  # QID -> (type, id)

    print("Loading QIDs from DB...")
    for table, etype in [('persons', 'person'), ('events', 'event'), ('locations', 'location')]:
        cur.execute(f"SELECT id, wikidata_id FROM {table} WHERE wikidata_id IS NOT NULL")
        count = 0
        for row in cur.fetchall():
            qid_to_entity[row[1]] = (etype, row[0])
            count += 1
        print(f"  {table}: {count:,}")

    print(f"Total QIDs: {len(qid_to_entity):,}")

    # 처리할 QID (기존 제외)
    qids_to_process = [q for q in qid_to_entity if q not in existing]
    if args.limit:
        qids_to_process = qids_to_process[:args.limit]
    print(f"To process: {len(qids_to_process):,}")

    # 배치 처리
    qid_to_wiki = dict(existing)
    processed = 0
    start = time.time()

    for i in range(0, len(qids_to_process), args.batch_size):
        batch = qids_to_process[i:i + args.batch_size]
        results = fetch_sitelinks_batch(batch)
        qid_to_wiki.update(results)
        processed += len(batch)

        # 진행률
        if processed % 1000 == 0 or processed == len(qids_to_process):
            elapsed = time.time() - start
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (len(qids_to_process) - processed) / rate / 60 if rate > 0 else 0
            found = len(qid_to_wiki) - len(existing)
            print(f"  {processed:,}/{len(qids_to_process):,} - found: {found:,} - ETA: {eta:.1f}min")

        # Rate limit
        time.sleep(0.05)

        # 중간 저장
        if processed % 10000 == 0:
            save_result(output_path, qid_to_wiki, qid_to_entity)

    # 최종 저장
    save_result(output_path, qid_to_wiki, qid_to_entity)
    conn.close()

    print(f"\n{'='*60}")
    print(f"Total QIDs: {len(qid_to_entity):,}")
    print(f"Wikipedia titles found: {len(qid_to_wiki):,}")
    print(f"Coverage: {100*len(qid_to_wiki)/len(qid_to_entity):.1f}%")
    print(f"Output: {output_path}")


def save_result(output_path, qid_to_wiki, qid_to_entity):
    """결과 저장."""
    # Wikipedia title → entity 매핑도 생성
    wiki_to_entity = {}
    for qid, wiki_title in qid_to_wiki.items():
        if qid in qid_to_entity:
            etype, eid = qid_to_entity[qid]
            wiki_to_entity[wiki_title] = {'type': etype, 'id': eid, 'qid': qid}
            # 언더스코어 버전도
            wiki_to_entity[wiki_title.replace(' ', '_')] = {'type': etype, 'id': eid, 'qid': qid}

    data = {
        'created_at': datetime.now().isoformat(),
        'total_qids': len(qid_to_entity),
        'found': len(qid_to_wiki),
        'qid_to_wiki': qid_to_wiki,
        'wiki_to_entity': wiki_to_entity
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

    print(f"  Saved: {len(qid_to_wiki):,} mappings")


if __name__ == '__main__':
    main()
