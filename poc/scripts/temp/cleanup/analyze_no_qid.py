"""
Task 2: QID 없는 것 분석
184,641개 QID 없는 엔티티가 어디서 왔는지 파악
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime
from pathlib import Path
from collections import Counter

# 결과 저장
OUTPUT_DIR = Path("C:/Projects/Chaldeas/backups/analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def analyze_no_qid():
    conn = psycopg2.connect(
        host='localhost', port=5432, dbname='chaldeas',
        user='chaldeas', password='chaldeas_dev'
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)

    results = {
        'timestamp': datetime.now().isoformat(),
        'summary': {},
        'patterns': {},
        'sources': {},
        'samples': {},
        'recommendations': {}
    }

    print("=== QID 없는 persons 분석 ===\n")

    # 1. 총 개수
    cur.execute("SELECT COUNT(*) as cnt FROM persons WHERE wikidata_id IS NULL")
    total = cur.fetchone()['cnt']
    print(f"총 개수: {total:,}")
    results['summary']['total_without_qid'] = total

    cur.execute("SELECT COUNT(*) as cnt FROM persons WHERE wikidata_id IS NOT NULL")
    with_qid = cur.fetchone()['cnt']
    results['summary']['total_with_qid'] = with_qid
    print(f"QID 있는 것: {with_qid:,}")

    # 2. 이름 패턴 분석
    print("\n--- 이름 패턴 분석 ---")
    cur.execute("""
        SELECT
            CASE
                WHEN name ~ '^[A-Z][a-z]+ [A-Z][a-z]+$' THEN 'First Last (정상)'
                WHEN name ~ '^[A-Z][a-z]+$' THEN 'Single Name (단일명)'
                WHEN name ~ '^Dr\.' THEN 'Dr. prefix (타이틀)'
                WHEN name ~ '^[A-Z]+$' THEN 'ALL CAPS (대문자)'
                WHEN name ~ '[0-9]' THEN 'Contains numbers (숫자 포함)'
                WHEN LENGTH(name) <= 2 THEN 'Too short (너무 짧음)'
                WHEN LENGTH(name) >= 100 THEN 'Too long (너무 김)'
                WHEN name ~ '^[a-z]' THEN 'Lowercase start (소문자 시작)'
                WHEN name ~ '[,;:]' THEN 'Contains punctuation (구두점)'
                WHEN name ~ ' [A-Z]\. ' THEN 'Middle initial (중간 이니셜)'
                WHEN name ~ ' (of|the|de|von|van) ' THEN 'Noble/Title pattern (귀족/칭호)'
                ELSE 'Other (기타)'
            END as pattern,
            COUNT(*) as cnt
        FROM persons
        WHERE wikidata_id IS NULL
        GROUP BY pattern
        ORDER BY cnt DESC
    """)
    patterns = cur.fetchall()
    for row in patterns:
        print(f"  {row['pattern']}: {row['cnt']:,}")
        results['patterns'][row['pattern']] = row['cnt']

    # 3. 이름 길이 분포
    print("\n--- 이름 길이 분포 ---")
    cur.execute("""
        SELECT
            CASE
                WHEN LENGTH(name) <= 2 THEN '1-2자'
                WHEN LENGTH(name) <= 10 THEN '3-10자'
                WHEN LENGTH(name) <= 20 THEN '11-20자'
                WHEN LENGTH(name) <= 50 THEN '21-50자'
                WHEN LENGTH(name) <= 100 THEN '51-100자'
                ELSE '100자 이상'
            END as length_range,
            COUNT(*) as cnt
        FROM persons
        WHERE wikidata_id IS NULL
        GROUP BY 1
        ORDER BY MIN(LENGTH(name))
    """)
    for row in cur.fetchall():
        print(f"  {row['length_range']}: {row['cnt']:,}")
        results['summary'][f"length_{row['length_range']}"] = row['cnt']

    # 4. 출처별 분포
    print("\n--- 출처별 분포 (text_mentions 기준) ---")
    cur.execute("""
        SELECT s.title, COUNT(DISTINCT p.id) as person_count
        FROM persons p
        LEFT JOIN text_mentions tm ON p.id = tm.entity_id AND tm.entity_type = 'person'
        LEFT JOIN sources s ON tm.source_id = s.id
        WHERE p.wikidata_id IS NULL
        GROUP BY s.title
        ORDER BY person_count DESC
        LIMIT 20
    """)
    sources = cur.fetchall()
    for row in sources:
        source = row['title'] or '(출처 없음)'
        print(f"  {source}: {row['person_count']:,}")
        results['sources'][source] = row['person_count']

    # 5. person_sources 테이블 분석
    print("\n--- person_sources 연결 분석 ---")
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE ps.source_id IS NOT NULL) as has_person_source,
            COUNT(*) FILTER (WHERE ps.source_id IS NULL) as no_person_source,
            COUNT(*) as total
        FROM persons p
        LEFT JOIN person_sources ps ON p.id = ps.person_id
        WHERE p.wikidata_id IS NULL
    """)
    ps_stats = cur.fetchone()
    print(f"  person_sources 연결됨: {ps_stats['has_person_source']:,}")
    print(f"  person_sources 없음: {ps_stats['no_person_source']:,}")
    results['summary']['has_person_source'] = ps_stats['has_person_source']
    results['summary']['no_person_source'] = ps_stats['no_person_source']

    # 6. 쓰레기 후보 분석
    print("\n--- 쓰레기 후보 (삭제 권장) ---")
    garbage_criteria = {
        'contains_numbers': "name ~ '[0-9]'",
        'too_short': "LENGTH(name) <= 2",
        'too_long': "LENGTH(name) >= 100",
        'not_a_person_flag': "name ILIKE '%not a person%'",
        'unknown_flag': "name ILIKE '%unknown%'",
        'non_alpha_start': "name ~ '^[^a-zA-Z]'",
        'all_caps': "name ~ '^[A-Z]+$' AND LENGTH(name) > 3",
        'no_source_no_relations': """
            NOT EXISTS (SELECT 1 FROM text_mentions tm WHERE tm.entity_id = p.id)
            AND NOT EXISTS (SELECT 1 FROM person_sources ps WHERE ps.person_id = p.id)
            AND NOT EXISTS (SELECT 1 FROM event_persons ep WHERE ep.person_id = p.id)
            AND NOT EXISTS (SELECT 1 FROM person_locations pl WHERE pl.person_id = p.id)
            AND NOT EXISTS (SELECT 1 FROM person_relationships pr WHERE pr.person_id = p.id OR pr.related_person_id = p.id)
        """
    }

    garbage_counts = {}
    for name, condition in garbage_criteria.items():
        cur.execute(f"""
            SELECT COUNT(*) as cnt FROM persons p
            WHERE wikidata_id IS NULL AND ({condition})
        """)
        count = cur.fetchone()['cnt']
        garbage_counts[name] = count
        print(f"  {name}: {count:,}")

    results['recommendations']['garbage_candidates'] = garbage_counts

    # 전체 쓰레기 후보 (중복 제외)
    cur.execute("""
        SELECT COUNT(*) as cnt FROM persons p
        WHERE wikidata_id IS NULL AND (
            name ~ '[0-9]'
            OR LENGTH(name) <= 2
            OR LENGTH(name) >= 100
            OR name ILIKE '%not a person%'
            OR name ILIKE '%unknown%'
            OR name ~ '^[^a-zA-Z]'
        )
    """)
    total_garbage = cur.fetchone()['cnt']
    print(f"\n  총 쓰레기 후보 (위 조건 OR): {total_garbage:,}")
    results['recommendations']['total_garbage_candidates'] = total_garbage

    # 7. 샘플 추출
    print("\n--- 랜덤 샘플 (QID 없는 것) ---")
    cur.execute("""
        SELECT id, name FROM persons
        WHERE wikidata_id IS NULL
        ORDER BY RANDOM()
        LIMIT 30
    """)
    samples = cur.fetchall()
    results['samples']['random'] = []
    for row in samples:
        print(f"  [{row['id']}] {row['name']}")
        results['samples']['random'].append({'id': row['id'], 'name': row['name']})

    # 8. 유망한 후보 (Wikidata 매칭 가능성 높음)
    print("\n--- 유망한 후보 (context 있음, 정상 이름) ---")
    cur.execute("""
        SELECT DISTINCT p.id, p.name, COUNT(tm.id) as mention_count
        FROM persons p
        JOIN text_mentions tm ON p.id = tm.entity_id AND tm.entity_type = 'person'
        WHERE p.wikidata_id IS NULL
        AND p.name ~ '^[A-Z][a-z]+'
        AND LENGTH(p.name) BETWEEN 5 AND 50
        AND p.name !~ '[0-9]'
        GROUP BY p.id, p.name
        HAVING COUNT(tm.id) >= 2
        ORDER BY mention_count DESC
        LIMIT 20
    """)
    promising = cur.fetchall()
    results['samples']['promising'] = []
    for row in promising:
        print(f"  [{row['id']}] {row['name']} (mentions: {row['mention_count']})")
        results['samples']['promising'].append({
            'id': row['id'],
            'name': row['name'],
            'mention_count': row['mention_count']
        })

    # 결과 저장
    output_file = OUTPUT_DIR / f"no_qid_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n분석 결과 저장: {output_file}")

    conn.close()

    # 권장 사항 출력
    print("\n=== 권장 사항 ===")
    print(f"1. 즉시 삭제 가능: {total_garbage:,}개 (숫자 포함, 너무 짧음/김, 명시적 표시)")
    print(f"2. 유망한 후보: {len(promising)}개 (context 있고 정상 이름)")
    print(f"3. 출처 없는 것: {results['sources'].get('(출처 없음)', 0):,}개 (추가 분석 필요)")

if __name__ == "__main__":
    analyze_no_qid()
