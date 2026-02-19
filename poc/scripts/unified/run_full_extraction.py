"""
전체 추출 배치 스크립트.

1. events 전체 추출
2. persons 전체 추출 (Wikipedia 문서 있는 것만)
3. locations 전체 추출 (Wikipedia 문서 있는 것만)

Usage:
    python run_full_extraction.py --type events --limit 1000
    python run_full_extraction.py --type all
"""

import sys
import os
import argparse
import psycopg2
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from extract_wikipedia import WikiExtractor

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}


def get_entities_to_process(entity_type, limit=None):
    """처리할 엔티티 목록 가져오기 - sitelinks 사용."""
    import json

    # sitelinks 로드 (Wikipedia 제목 → DB 엔티티)
    sitelinks_file = 'poc/data/wikipedia_extract/wiki_sitelinks.json'
    wiki_to_entity = {}
    try:
        with open(sitelinks_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        wiki_to_entity = data.get('wiki_to_entity', {})
    except:
        pass

    # sitelinks에서 해당 타입만 필터링
    rows = []
    for wiki_title, info in wiki_to_entity.items():
        if info['type'] == entity_type[:-1]:  # 'events' -> 'event'
            rows.append((info['id'], wiki_title, info['qid']))

    print(f"  Found {len(rows):,} {entity_type} with Wikipedia articles (from sitelinks)")

    if limit:
        rows = rows[:limit]

    return rows


def run_extraction(entity_type, limit=None, batch_size=100):
    """엔티티 타입별 추출 실행."""
    print(f"\n{'='*60}")
    print(f"EXTRACTING: {entity_type.upper()}")
    print(f"{'='*60}")

    entities = get_entities_to_process(entity_type, limit)
    total = len(entities)
    print(f"Total entities: {total:,}")

    extractor = WikiExtractor(dry_run=False)

    processed = 0
    errors = 0
    skipped = 0

    for i, (eid, title, qid) in enumerate(entities):
        try:
            # Wikipedia 타이틀로 변환
            wiki_title = title.replace(' ', '_') if title else None
            if not wiki_title:
                skipped += 1
                continue

            # 이미 처리됐는지 확인 (source 존재 여부)
            extractor.cur.execute(
                "SELECT id FROM sources WHERE title = %s AND source_type = 'wikipedia'",
                (title,)
            )
            if extractor.cur.fetchone():
                skipped += 1
                continue

            # 추출
            result = extractor.process_article(title)
            if result:
                processed += 1
            else:
                skipped += 1

        except Exception as e:
            errors += 1
            # 트랜잭션 롤백 (다음 처리를 위해)
            try:
                extractor.conn.rollback()
            except:
                pass
            if errors < 10:  # 처음 10개 에러만 출력
                print(f"  Error [{title}]: {e}")

        # 진행률 출력
        if (i + 1) % batch_size == 0:
            pct = (i + 1) / total * 100
            print(f"  Progress: {i+1:,}/{total:,} ({pct:.1f}%) - processed: {processed}, skipped: {skipped}, errors: {errors}")

    print(f"\nCompleted {entity_type}:")
    print(f"  Processed: {processed:,}")
    print(f"  Skipped: {skipped:,}")
    print(f"  Errors: {errors:,}")

    extractor.print_summary()

    return processed, skipped, errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', choices=['events', 'persons', 'locations', 'all'], default='events')
    parser.add_argument('--limit', type=int, help='최대 처리 수')
    parser.add_argument('--batch-size', type=int, default=100, help='진행률 출력 간격')
    args = parser.parse_args()

    start_time = datetime.now()
    print(f"Started at: {start_time}")

    if args.type == 'all':
        types = ['events', 'persons', 'locations']
    else:
        types = [args.type]

    total_results = {}
    for t in types:
        total_results[t] = run_extraction(t, args.limit, args.batch_size)

    end_time = datetime.now()
    duration = end_time - start_time

    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"Duration: {duration}")
    for t, (processed, skipped, errors) in total_results.items():
        print(f"  {t}: {processed:,} processed, {skipped:,} skipped, {errors:,} errors")


if __name__ == '__main__':
    main()
