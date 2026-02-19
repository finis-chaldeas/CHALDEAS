"""
Task 6: 167권 DB 매칭
추출된 엔티티를 DB와 연결하고 text_mentions 생성
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
import time
from pathlib import Path
from datetime import datetime
from wikidata_search import match_entity_to_wikidata, get_wikidata_details

CONTEXTS_DIR = Path("C:/Projects/Chaldeas/poc/data/book_contexts")
CHANGE_LOG_DIR = Path("C:/Projects/Chaldeas/backups/change_logs")
CHANGE_LOG_DIR.mkdir(parents=True, exist_ok=True)

def get_or_create_source(cur, title: str, book_id: str) -> int:
    """Source 조회 또는 생성"""
    cur.execute("SELECT id FROM sources WHERE title = %s", (title,))
    result = cur.fetchone()
    if result:
        return result['id']

    # 새로 생성
    cur.execute("""
        INSERT INTO sources (title, name, type, document_id, created_at, updated_at)
        VALUES (%s, %s, 'gutenberg', %s, NOW(), NOW())
        RETURNING id
    """, (title, title, book_id))
    return cur.fetchone()['id']


def find_person_in_db(cur, name: str, qid: str = None) -> dict:
    """DB에서 person 조회"""
    if qid:
        cur.execute("""
            SELECT id, name, wikidata_id FROM persons WHERE wikidata_id = %s
        """, (qid,))
        result = cur.fetchone()
        if result:
            return dict(result)

    # 이름으로 검색
    cur.execute("""
        SELECT id, name, wikidata_id FROM persons
        WHERE name ILIKE %s OR name ILIKE %s
        LIMIT 1
    """, (name, f"%{name}%"))
    result = cur.fetchone()
    return dict(result) if result else None


def create_or_update_person(cur, name: str, qid: str, wikidata_info: dict) -> int:
    """Person 생성 또는 업데이트"""
    # QID로 기존 레코드 확인
    if qid:
        cur.execute("SELECT id FROM persons WHERE wikidata_id = %s", (qid,))
        result = cur.fetchone()
        if result:
            return result['id']

    # 이름으로 확인
    cur.execute("SELECT id, wikidata_id FROM persons WHERE name ILIKE %s", (name,))
    result = cur.fetchone()

    if result:
        # 기존 레코드가 QID 없으면 업데이트
        if not result['wikidata_id'] and qid:
            cur.execute("""
                UPDATE persons SET
                    wikidata_id = %s,
                    name_ko = COALESCE(name_ko, %s),
                    birth_year = COALESCE(birth_year, %s),
                    death_year = COALESCE(death_year, %s),
                    biography = COALESCE(biography, %s),
                    data_quality = 'matched',
                    updated_at = NOW()
                WHERE id = %s
            """, (
                qid,
                wikidata_info.get('name_ko'),
                wikidata_info.get('birth_year'),
                wikidata_info.get('death_year'),
                wikidata_info.get('description'),
                result['id']
            ))
        return result['id']

    # 새로 생성
    import re
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    slug = f"{slug}-{int(time.time())}"  # 유니크하게

    cur.execute("""
        INSERT INTO persons (
            name, slug, wikidata_id, name_ko, birth_year, death_year,
            biography, data_quality, source_type, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'book_extraction', NOW(), NOW())
        RETURNING id
    """, (
        wikidata_info.get('name', name),
        slug,
        qid,
        wikidata_info.get('name_ko'),
        wikidata_info.get('birth_year'),
        wikidata_info.get('death_year'),
        wikidata_info.get('description'),
        'matched' if qid else 'extracted'
    ))
    return cur.fetchone()['id']


def create_text_mention(cur, entity_type: str, entity_id: int, source_id: int,
                       mention_text: str, context_text: str, chunk_id: int,
                       confidence: float):
    """text_mention 생성"""
    cur.execute("""
        INSERT INTO text_mentions
        (entity_type, entity_id, source_id, mention_text, context_text, chunk_index, confidence, extracted_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT DO NOTHING
    """, (entity_type, entity_id, source_id, mention_text, context_text[:500], chunk_id, confidence))


def match_book_entities(book_file: Path, conn, stats: dict, dry_run: bool = True):
    """단일 책의 엔티티 매칭"""
    cur = conn.cursor(cursor_factory=RealDictCursor)

    with open(book_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    book_id = data['book_id']
    title = data['title']

    # Source 가져오기
    source_id = get_or_create_source(cur, title, book_id)

    # Persons 처리
    persons = data['entities'].get('persons', {})

    for name, info in persons.items():
        # context 합치기 (처음 3개)
        combined_context = " ".join([c['text'][:200] for c in info['contexts'][:3]])

        # Wikidata 매칭
        match_result = match_entity_to_wikidata(name, combined_context)

        # 높은 신뢰도만 처리
        if match_result.confidence >= 0.5:
            stats['matched'] += 1

            if not dry_run:
                # Wikidata 상세 정보
                wikidata_info = {}
                if match_result.qid:
                    wikidata_info = get_wikidata_details(match_result.qid)

                # DB에 저장/연결
                person_id = create_or_update_person(
                    cur, name, match_result.qid, wikidata_info
                )

                # text_mentions 생성
                for ctx in info['contexts']:
                    create_text_mention(
                        cur, 'person', person_id, source_id,
                        name, ctx['text'], ctx['chunk_id'],
                        match_result.confidence
                    )
                    stats['mentions_created'] += 1

        elif match_result.confidence >= 0.3:
            stats['low_confidence'] += 1
        else:
            stats['unmatched'] += 1

        time.sleep(0.1)  # Rate limit

    if not dry_run:
        conn.commit()


def match_all_books(limit: int = None, dry_run: bool = True):
    """모든 책 매칭"""
    conn = psycopg2.connect(
        host='localhost', port=5432, dbname='chaldeas',
        user='chaldeas', password='chaldeas_dev'
    )

    context_files = list(CONTEXTS_DIR.glob("*_contexts.json"))
    # 통계 파일 제외
    context_files = [f for f in context_files if not f.name.startswith('_')]

    print(f"처리할 책: {len(context_files)}권")

    if limit:
        context_files = context_files[:limit]
        print(f"(limit={limit})")

    if dry_run:
        print("(dry_run=True)")

    stats = {
        'books_processed': 0,
        'matched': 0,
        'low_confidence': 0,
        'unmatched': 0,
        'mentions_created': 0
    }

    for i, book_file in enumerate(context_files):
        if i % 10 == 0:
            print(f"진행: {i}/{len(context_files)} - matched: {stats['matched']}")

        try:
            match_book_entities(book_file, conn, stats, dry_run=dry_run)
            stats['books_processed'] += 1
        except Exception as e:
            print(f"  오류 ({book_file.name}): {e}")

    print(f"\n=== 완료 ===")
    print(f"처리한 책: {stats['books_processed']}권")
    print(f"매칭 성공 (>=0.5): {stats['matched']:,}")
    print(f"낮은 신뢰도 (0.3-0.5): {stats['low_confidence']:,}")
    print(f"매칭 실패 (<0.3): {stats['unmatched']:,}")
    if not dry_run:
        print(f"생성된 mentions: {stats['mentions_created']:,}")

    # 변경 이력 저장
    if not dry_run:
        log_file = CHANGE_LOG_DIR / f"match_books_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                **stats
            }, f, indent=2)
        print(f"변경 이력: {log_file}")

    conn.close()
    return stats


if __name__ == "__main__":
    import sys
    dry_run = "--execute" not in sys.argv
    limit = None
    for arg in sys.argv:
        if arg.startswith("--limit="):
            limit = int(arg.split("=")[1])
    match_all_books(limit=limit, dry_run=dry_run)
