"""
Task 1: QID 중복 합치기
같은 Wikidata QID를 가진 여러 레코드를 하나로 합침
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime
from pathlib import Path

# 변경 이력 저장
CHANGE_LOG_DIR = Path("C:/Projects/Chaldeas/backups/change_logs")
CHANGE_LOG_DIR.mkdir(parents=True, exist_ok=True)

def log_changes(changes: list, filename: str):
    """변경 이력 JSON으로 저장"""
    log_file = CHANGE_LOG_DIR / f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(changes, f, ensure_ascii=False, indent=2)
    print(f"변경 이력 저장: {log_file}")
    return log_file

def get_random_samples(cur, qid_list: list, n: int = 5):
    """랜덤 샘플 추출 (검증용)"""
    import random
    samples = random.sample(qid_list, min(n, len(qid_list)))
    result = []
    for qid in samples:
        cur.execute("""
            SELECT id, name, wikidata_id, birth_year, death_year
            FROM persons WHERE wikidata_id = %s
        """, (qid,))
        rows = cur.fetchall()
        result.append({
            'qid': qid,
            'records': [dict(r) for r in rows]
        })
    return result

def merge_qid_duplicates(dry_run=True, limit=None):
    conn = psycopg2.connect(
        host='localhost', port=5432, dbname='chaldeas',
        user='chaldeas', password='chaldeas_dev'
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 1. 중복 QID 찾기
    cur.execute("""
        SELECT wikidata_id,
               array_agg(id ORDER BY id) as ids,
               array_agg(name ORDER BY id) as names,
               COUNT(*) as cnt
        FROM persons
        WHERE wikidata_id IS NOT NULL
        GROUP BY wikidata_id
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC
    """)
    duplicates = cur.fetchall()
    print(f"중복 QID 개수: {len(duplicates)}")

    if not duplicates:
        print("중복 없음!")
        conn.close()
        return

    # 2. 랜덤 샘플 5개 출력 (검증용)
    print("\n=== 랜덤 샘플 (작업 전) ===")
    qid_list = [d['wikidata_id'] for d in duplicates]
    samples = get_random_samples(cur, qid_list)
    for sample in samples:
        print(f"\n{sample['qid']}:")
        for r in sample['records']:
            print(f"  [{r['id']}] {r['name']} ({r['birth_year']}-{r['death_year']})")

    if dry_run:
        print(f"\n(dry_run=True, 실제 작업 안 함)")
        print(f"총 {len(duplicates)}개 QID, {sum(d['cnt']-1 for d in duplicates)}개 레코드 합쳐질 예정")
        conn.close()
        return

    # 3. 실제 합치기
    changes = []
    merged_count = 0
    error_count = 0

    process_list = duplicates[:limit] if limit else duplicates

    for i, dup in enumerate(process_list):
        if i % 100 == 0:
            print(f"진행: {i}/{len(process_list)}")

        qid = dup['wikidata_id']
        ids = dup['ids']
        names = dup['names']

        # primary 선택 (첫 번째 = 가장 오래된 것)
        primary_id = ids[0]
        primary_name = names[0]
        other_ids = ids[1:]
        other_names = names[1:]

        change = {
            'qid': qid,
            'primary': {'id': primary_id, 'name': primary_name},
            'merged': [{'id': oid, 'name': oname} for oid, oname in zip(other_ids, other_names)],
            'aliases_added': [],
            'status': 'success'
        }

        try:
            # 다른 이름들 alias로 저장
            for other_id, other_name in zip(other_ids, other_names):
                if other_name != primary_name:
                    cur.execute("""
                        INSERT INTO entity_aliases (entity_type, entity_id, alias, alias_type)
                        VALUES ('person', %s, %s, 'merged')
                        ON CONFLICT (entity_type, entity_id, alias) DO NOTHING
                    """, (primary_id, other_name))
                    change['aliases_added'].append(other_name)

            # 관계 데이터 이전
            for other_id in other_ids:
                # event_persons - 중복 아닌 것만 업데이트
                cur.execute("""
                    UPDATE event_persons ep SET person_id = %s
                    WHERE ep.person_id = %s
                    AND NOT EXISTS (
                        SELECT 1 FROM event_persons ep2
                        WHERE ep2.person_id = %s AND ep2.event_id = ep.event_id
                    )
                """, (primary_id, other_id, primary_id))

                # person_locations - 중복 아닌 것만 업데이트
                cur.execute("""
                    UPDATE person_locations pl SET person_id = %s
                    WHERE pl.person_id = %s
                    AND NOT EXISTS (
                        SELECT 1 FROM person_locations pl2
                        WHERE pl2.person_id = %s AND pl2.location_id = pl.location_id
                    )
                """, (primary_id, other_id, primary_id))

                # person_relationships - person_id 업데이트
                cur.execute("""
                    UPDATE person_relationships pr SET person_id = %s
                    WHERE pr.person_id = %s
                    AND NOT EXISTS (
                        SELECT 1 FROM person_relationships pr2
                        WHERE pr2.person_id = %s AND pr2.related_person_id = pr.related_person_id
                    )
                """, (primary_id, other_id, primary_id))
                # person_relationships - related_person_id 업데이트
                cur.execute("""
                    UPDATE person_relationships pr SET related_person_id = %s
                    WHERE pr.related_person_id = %s
                    AND NOT EXISTS (
                        SELECT 1 FROM person_relationships pr2
                        WHERE pr2.person_id = pr.person_id AND pr2.related_person_id = %s
                    )
                """, (primary_id, other_id, primary_id))

                # text_mentions
                cur.execute("""
                    UPDATE text_mentions SET entity_id = %s
                    WHERE entity_type = 'person' AND entity_id = %s
                """, (primary_id, other_id))

                # person_sources
                cur.execute("""
                    UPDATE person_sources ps SET person_id = %s
                    WHERE ps.person_id = %s
                    AND NOT EXISTS (
                        SELECT 1 FROM person_sources ps2
                        WHERE ps2.person_id = %s AND ps2.source_id = ps.source_id
                    )
                """, (primary_id, other_id, primary_id))

                # person_polities
                cur.execute("""
                    UPDATE person_polities pp SET person_id = %s
                    WHERE pp.person_id = %s
                    AND NOT EXISTS (
                        SELECT 1 FROM person_polities pp2
                        WHERE pp2.person_id = %s AND pp2.polity_id = pp.polity_id
                    )
                """, (primary_id, other_id, primary_id))

            # 중복 레코드 삭제 (관련 테이블 먼저 정리)
            for other_id in other_ids:
                # 남은 관계 삭제 (중복으로 인해 UPDATE 안 된 것들)
                cur.execute("DELETE FROM event_persons WHERE person_id = %s", (other_id,))
                cur.execute("DELETE FROM person_locations WHERE person_id = %s", (other_id,))
                cur.execute("DELETE FROM person_relationships WHERE person_id = %s OR related_person_id = %s", (other_id, other_id))
                cur.execute("DELETE FROM person_sources WHERE person_id = %s", (other_id,))
                cur.execute("DELETE FROM person_polities WHERE person_id = %s", (other_id,))
                cur.execute("DELETE FROM entity_aliases WHERE entity_type = 'person' AND entity_id = %s", (other_id,))

            # persons 삭제
            cur.execute("DELETE FROM persons WHERE id = ANY(%s)", (other_ids,))

            # 개별 커밋 (안전하게)
            conn.commit()
            merged_count += len(other_ids)

        except Exception as e:
            conn.rollback()
            change['status'] = 'error'
            change['error'] = str(e)
            error_count += 1
            print(f"  오류 ({qid}): {e}")

        changes.append(change)

    # 변경 이력 저장
    log_file = log_changes(changes, 'merge_qid_duplicates')

    # 작업 후 랜덤 샘플 확인
    print("\n=== 랜덤 샘플 (작업 후) ===")
    merged_qids = [c['qid'] for c in changes[:10]]
    for qid in merged_qids[:5]:
        cur.execute("SELECT id, name, wikidata_id FROM persons WHERE wikidata_id = %s", (qid,))
        rows = cur.fetchall()
        print(f"{qid}: {len(rows)}개 → ", end="")
        if len(rows) == 1:
            print(f"OK [{rows[0]['id']}] {rows[0]['name']}")
        else:
            print(f"ERROR! {len(rows)}개 남음")

    print(f"\n총 {merged_count}개 레코드 합침 (오류: {error_count}건)")
    print(f"변경 이력: {log_file}")
    conn.close()

if __name__ == "__main__":
    import sys
    dry_run = "--execute" not in sys.argv
    limit = None
    for arg in sys.argv:
        if arg.startswith("--limit="):
            limit = int(arg.split("=")[1])
    merge_qid_duplicates(dry_run=dry_run, limit=limit)
