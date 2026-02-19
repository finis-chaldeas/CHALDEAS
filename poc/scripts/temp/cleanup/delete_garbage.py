"""
Task 3: 쓰레기 데이터 삭제
품질 낮은 데이터 삭제
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime
from pathlib import Path
import random

# 변경 이력 저장
CHANGE_LOG_DIR = Path("C:/Projects/Chaldeas/backups/change_logs")
CHANGE_LOG_DIR.mkdir(parents=True, exist_ok=True)

def delete_garbage(dry_run=True, limit=None):
    conn = psycopg2.connect(
        host='localhost', port=5432, dbname='chaldeas',
        user='chaldeas', password='chaldeas_dev'
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 삭제 대상 찾기
    # 더 보수적인 조건 사용
    # - "1st", "2nd", "III" 같은 서수/로마숫자는 제외
    # - 연도(1800, 1900 등)도 제외
    cur.execute("""
        SELECT id, name,
            CASE
                WHEN name ~ '[0-9]' AND name !~ '(1st|2nd|3rd|[0-9]th|[IVX]+|[0-9]{4})' THEN 'contains_bad_numbers'
                WHEN LENGTH(name) <= 2 THEN 'too_short'
                WHEN LENGTH(name) >= 100 THEN 'too_long'
                WHEN name ILIKE '%not a person%' THEN 'not_a_person_flag'
                WHEN name ILIKE '%unknown%' AND LENGTH(name) < 20 THEN 'unknown_flag'
                WHEN name ~ '^[^a-zA-ZÀ-ÿ]' THEN 'non_alpha_start'
                ELSE 'other'
            END as reason
        FROM persons
        WHERE wikidata_id IS NULL
        AND (
            (name ~ '[0-9]' AND name !~ '(1st|2nd|3rd|[0-9]th|[IVX]+|[0-9]{4})')  -- 나쁜 숫자만
            OR LENGTH(name) <= 2                    -- 너무 짧음
            OR LENGTH(name) >= 100                  -- 너무 김
            OR name ILIKE '%not a person%'          -- 명시적 표시
            OR (name ILIKE '%unknown%' AND LENGTH(name) < 20)
            OR name ~ '^[^a-zA-ZÀ-ÿ]'               -- 문자로 시작 안 함 (악센트 문자 허용)
        )
    """)
    garbage = cur.fetchall()

    print(f"삭제 대상: {len(garbage)}개")

    # 이유별 통계
    reason_counts = {}
    for g in garbage:
        reason = g['reason']
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    print("\n이유별 분포:")
    for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
        print(f"  {reason}: {count:,}")

    # 랜덤 샘플 출력
    print("\n랜덤 샘플 20개:")
    samples = random.sample(garbage, min(20, len(garbage)))
    for g in samples:
        print(f"  [{g['id']}] ({g['reason']}) {g['name'][:60]}")

    if dry_run:
        print(f"\n(dry_run=True, 실제 삭제 안 함)")
        print(f"--execute 플래그로 실행하세요.")
        conn.close()
        return

    # 실제 삭제
    if limit:
        garbage = garbage[:limit]
        print(f"\n(limit={limit}, {limit}개만 삭제)")

    ids = [g['id'] for g in garbage]

    # 변경 이력 저장
    changes = {
        'timestamp': datetime.now().isoformat(),
        'action': 'delete_garbage',
        'total_deleted': len(ids),
        'reason_counts': reason_counts,
        'deleted_records': [{'id': g['id'], 'name': g['name'], 'reason': g['reason']} for g in garbage]
    }

    print(f"\n삭제 진행 중...")

    # 관련 데이터 먼저 삭제
    cur.execute("DELETE FROM text_mentions WHERE entity_type = 'person' AND entity_id = ANY(%s)", (ids,))
    deleted_mentions = cur.rowcount
    print(f"  text_mentions: {deleted_mentions}개 삭제")

    cur.execute("DELETE FROM entity_aliases WHERE entity_type = 'person' AND entity_id = ANY(%s)", (ids,))
    deleted_aliases = cur.rowcount
    print(f"  entity_aliases: {deleted_aliases}개 삭제")

    cur.execute("DELETE FROM event_persons WHERE person_id = ANY(%s)", (ids,))
    deleted_ep = cur.rowcount
    print(f"  event_persons: {deleted_ep}개 삭제")

    cur.execute("DELETE FROM person_locations WHERE person_id = ANY(%s)", (ids,))
    deleted_pl = cur.rowcount
    print(f"  person_locations: {deleted_pl}개 삭제")

    cur.execute("DELETE FROM person_relationships WHERE person_id = ANY(%s) OR related_person_id = ANY(%s)", (ids, ids))
    deleted_pr = cur.rowcount
    print(f"  person_relationships: {deleted_pr}개 삭제")

    cur.execute("DELETE FROM person_sources WHERE person_id = ANY(%s)", (ids,))
    deleted_ps = cur.rowcount
    print(f"  person_sources: {deleted_ps}개 삭제")

    cur.execute("DELETE FROM person_polities WHERE person_id = ANY(%s)", (ids,))
    deleted_pp = cur.rowcount
    print(f"  person_polities: {deleted_pp}개 삭제")

    # persons 삭제
    cur.execute("DELETE FROM persons WHERE id = ANY(%s)", (ids,))
    deleted_persons = cur.rowcount
    print(f"  persons: {deleted_persons}개 삭제")

    conn.commit()

    changes['related_deletions'] = {
        'text_mentions': deleted_mentions,
        'entity_aliases': deleted_aliases,
        'event_persons': deleted_ep,
        'person_locations': deleted_pl,
        'person_relationships': deleted_pr,
        'person_sources': deleted_ps,
        'person_polities': deleted_pp
    }

    # 변경 이력 저장
    log_file = CHANGE_LOG_DIR / f"delete_garbage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(changes, f, ensure_ascii=False, indent=2)

    print(f"\n총 {deleted_persons}개 삭제 완료")
    print(f"변경 이력: {log_file}")

    # 삭제 후 검증
    print("\n=== 삭제 후 검증 ===")
    cur.execute("SELECT COUNT(*) as cnt FROM persons WHERE wikidata_id IS NULL AND name ~ '[0-9]'")
    remaining = cur.fetchone()['cnt']
    print(f"숫자 포함 이름 남은 것: {remaining}개")

    cur.execute("SELECT COUNT(*) as cnt FROM persons WHERE wikidata_id IS NULL AND LENGTH(name) <= 2")
    remaining_short = cur.fetchone()['cnt']
    print(f"짧은 이름 남은 것: {remaining_short}개")

    conn.close()

if __name__ == "__main__":
    import sys
    dry_run = "--execute" not in sys.argv
    limit = None
    for arg in sys.argv:
        if arg.startswith("--limit="):
            limit = int(arg.split("=")[1])
    delete_garbage(dry_run=dry_run, limit=limit)
