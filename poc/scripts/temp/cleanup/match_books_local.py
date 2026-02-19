"""
Book Entity Matcher v3: EntityMatcher 통합 버전

매칭 파이프라인:
1. Exact Match - 이름 정확히 일치
2. Alias Match - entity_aliases 테이블
3. Wikidata QID - Wikidata 검색 → DB QID 매칭
4. Embedding Similarity - 벡터 유사도
5. LLM Verification - AI 검증
6. Fuzzy Match - Trigram 유사도 (pg_trgm)

Usage:
    python match_books_local.py --limit=5           # 테스트 (dry-run, fast mode)
    python match_books_local.py --execute           # 실제 실행 (fast mode)
    python match_books_local.py --execute --slow    # 외부 API 포함 (느림/정확)
    python match_books_local.py --execute --limit=10
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
import time
import sys
from pathlib import Path
from datetime import datetime

# Windows 콘솔 유니코드 지원
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 프로젝트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools" / "book_extractor"))

# EntityMatcher 임포트
from entity_matcher import EntityMatcher, MatchResult

CONTEXTS_DIR = PROJECT_ROOT / "poc" / "data" / "book_contexts"
CHANGE_LOG_DIR = PROJECT_ROOT / "docs" / "logs" / "gutenberg_runs"
CHANGE_LOG_DIR.mkdir(parents=True, exist_ok=True)

# DB 설정
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}


def get_or_create_source(cur, title: str, book_id: str, author: str = None) -> int:
    """Source 조회 또는 생성

    sources 테이블 스키마:
    - id, source_type (NOT NULL), title (NOT NULL), author, year, chapter,
      chunk_index, content_raw (NOT NULL), url, created_at
    """
    # gutenberg: URL prefix로 조회
    cur.execute("SELECT id FROM sources WHERE url = %s", (f"gutenberg:{book_id}",))
    result = cur.fetchone()
    if result:
        return result['id']

    # 또는 title로 조회
    cur.execute("SELECT id FROM sources WHERE title = %s AND source_type = 'gutenberg'", (title,))
    result = cur.fetchone()
    if result:
        return result['id']

    # 새로 생성 (실제 스키마에 맞게)
    cur.execute("""
        INSERT INTO sources (source_type, title, author, url, content_raw, created_at)
        VALUES ('gutenberg', %s, %s, %s, '', NOW())
        RETURNING id
    """, (title, author, f"gutenberg:{book_id}"))
    return cur.fetchone()['id']


def create_text_mention(cur, entity_type: str, entity_id: int, source_id: int,
                       mention_text: str, context_text: str, chunk_id: int,
                       confidence: float, match_method: str, batch_id: str):
    """text_mention 생성 (batch_id로 나중에 삭제 가능)"""
    cur.execute("""
        INSERT INTO text_mentions
        (entity_type, entity_id, source_id, mention_text, context_text,
         chunk_index, confidence, extraction_model, batch_id, extracted_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT DO NOTHING
    """, (entity_type, entity_id, source_id, mention_text,
          context_text[:500] if context_text else '', chunk_id, confidence, match_method, batch_id))


def match_book_entities(book_file: Path, matcher: EntityMatcher, conn, stats: dict,
                        batch_id: str, dry_run: bool = True):
    """단일 책의 엔티티 매칭 - EntityMatcher 사용"""
    cur = conn.cursor(cursor_factory=RealDictCursor)

    with open(book_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    book_id = data.get('book_id', book_file.stem)
    title = data.get('title', book_id)
    author = data.get('author')

    if not dry_run:
        source_id = get_or_create_source(cur, title, book_id, author)
    else:
        source_id = None

    # Person 매칭
    persons = data.get('entities', {}).get('persons', {})
    for name, info in persons.items():
        contexts = info.get('contexts', [])
        context_text = contexts[0]['text'] if contexts else None

        # EntityMatcher 사용
        result = matcher.match('person', name, context=context_text)

        # 통계 업데이트
        if result.matched:
            stats[f'match_{result.method}'] = stats.get(f'match_{result.method}', 0) + 1
            stats['total_matched'] += 1

            if not dry_run:
                for ctx in contexts[:5]:  # 최대 5개 context
                    create_text_mention(
                        cur, 'person', result.entity_id, source_id,
                        name, ctx.get('text', ''), ctx.get('chunk_id', 0),
                        result.confidence, result.method, batch_id
                    )
                    stats['mentions_created'] += 1
        else:
            stats['not_found'] += 1
            if stats.get('not_found_names') is None:
                stats['not_found_names'] = []
            if len(stats['not_found_names']) < 100:  # 최대 100개까지만 기록
                stats['not_found_names'].append(name)

    # Location 매칭
    locations = data.get('entities', {}).get('locations', {})
    for name, info in locations.items():
        contexts = info.get('contexts', [])
        context_text = contexts[0]['text'] if contexts else None

        result = matcher.match('location', name, context=context_text)

        if result.matched:
            stats[f'loc_match_{result.method}'] = stats.get(f'loc_match_{result.method}', 0) + 1
            stats['loc_total_matched'] = stats.get('loc_total_matched', 0) + 1

            if not dry_run:
                for ctx in contexts[:5]:
                    create_text_mention(
                        cur, 'location', result.entity_id, source_id,
                        name, ctx.get('text', ''), ctx.get('chunk_id', 0),
                        result.confidence, result.method, batch_id
                    )
                    stats['mentions_created'] += 1
        else:
            stats['loc_not_found'] = stats.get('loc_not_found', 0) + 1

    # Event 매칭
    events = data.get('entities', {}).get('events', {})
    for name, info in events.items():
        contexts = info.get('contexts', [])
        context_text = contexts[0]['text'] if contexts else None

        result = matcher.match('event', name, context=context_text)

        if result.matched:
            stats[f'evt_match_{result.method}'] = stats.get(f'evt_match_{result.method}', 0) + 1
            stats['evt_total_matched'] = stats.get('evt_total_matched', 0) + 1

            if not dry_run:
                for ctx in contexts[:5]:
                    create_text_mention(
                        cur, 'event', result.entity_id, source_id,
                        name, ctx.get('text', ''), ctx.get('chunk_id', 0),
                        result.confidence, result.method, batch_id
                    )
                    stats['mentions_created'] += 1
        else:
            stats['evt_not_found'] = stats.get('evt_not_found', 0) + 1

    if not dry_run:
        conn.commit()


def match_all_books(limit: int = None, dry_run: bool = True, fast_mode: bool = True):
    """모든 책 매칭

    Args:
        limit: 처리할 책 수 제한
        dry_run: True면 실제 저장 안 함
        fast_mode: True면 로컬 DB만 사용 (빠름), False면 외부 API도 사용 (느림/정확)
    """
    conn = psycopg2.connect(**DB_CONFIG)
    # V2 모드: wikidata_id 있는 엔티티만 매칭
    matcher = EntityMatcher(auto_create=False, fast_mode=fast_mode, wikidata_only=True)

    # batch_id 생성 (나중에 삭제 가능하도록) - V2 prefix
    batch_id = f"gutenberg_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Batch ID: {batch_id}")
    print(f"  → 나중에 삭제: DELETE FROM text_mentions WHERE batch_id = '{batch_id}'")

    context_files = list(CONTEXTS_DIR.glob("*_contexts.json"))
    context_files = [f for f in context_files if not f.name.startswith('_')]

    print(f"처리할 책: {len(context_files)}권")

    if limit:
        context_files = context_files[:limit]
        print(f"(limit={limit})")

    if dry_run:
        print("(dry_run=True - 실제 저장 안 함)")

    print(f"모드: V2 (wikidata_id 있는 엔티티만 매칭)")
    if fast_mode:
        print(f"매칭 파이프라인: exact → alias → trigram (FAST)")
    else:
        print(f"매칭 파이프라인: exact → alias → wikidata → embedding → llm → trigram (SLOW)")
    print("=" * 60)

    stats = {
        'books_processed': 0,
        'total_matched': 0,
        'not_found': 0,
        'mentions_created': 0,
    }

    start_time = time.time()

    for i, book_file in enumerate(context_files):
        elapsed = time.time() - start_time

        # 진행 상황 출력
        if i % 5 == 0:
            match_rate = (stats['total_matched'] / (stats['total_matched'] + stats['not_found']) * 100) if (stats['total_matched'] + stats['not_found']) > 0 else 0
            print(f"[{i+1}/{len(context_files)}] {elapsed:.0f}s | 매칭: {stats['total_matched']:,} ({match_rate:.1f}%) | 미발견: {stats['not_found']:,}")

        try:
            match_book_entities(book_file, matcher, conn, stats, batch_id, dry_run=dry_run)
            stats['books_processed'] += 1
        except Exception as e:
            print(f"  오류 ({book_file.name}): {e}")
            # Rollback to clear failed transaction
            conn.rollback()

    elapsed = time.time() - start_time
    matcher.close()

    # 결과 출력
    print("\n" + "=" * 60)
    print(f"완료: {elapsed:.1f}초")
    print(f"\n=== Person 매칭 결과 ===")
    print(f"총 매칭: {stats['total_matched']:,}")

    # 방법별 통계
    for key in sorted(stats.keys()):
        if key.startswith('match_'):
            method = key.replace('match_', '')
            print(f"  - {method}: {stats[key]:,}")

    print(f"미발견: {stats['not_found']:,}")

    # Location/Event 통계
    if stats.get('loc_total_matched', 0) > 0:
        print(f"\n=== Location 매칭 ===")
        print(f"총 매칭: {stats.get('loc_total_matched', 0):,}")
        print(f"미발견: {stats.get('loc_not_found', 0):,}")

    if stats.get('evt_total_matched', 0) > 0:
        print(f"\n=== Event 매칭 ===")
        print(f"총 매칭: {stats.get('evt_total_matched', 0):,}")
        print(f"미발견: {stats.get('evt_not_found', 0):,}")

    if not dry_run:
        print(f"\n생성된 mentions: {stats['mentions_created']:,}")

    # 매칭률
    total = stats['total_matched'] + stats['not_found']
    if total > 0:
        match_rate = stats['total_matched'] / total * 100
        print(f"\n전체 매칭률: {match_rate:.1f}%")

    # 미발견 샘플 출력
    not_found_names = stats.get('not_found_names', [])
    if not_found_names:
        print(f"\n미발견 샘플 (최대 20개):")
        for name in not_found_names[:20]:
            print(f"  - {name}")

    # 변경 이력 저장
    log_file = CHANGE_LOG_DIR / f"match_books_v3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    # not_found_names는 로그에서 제외 (너무 큼)
    log_stats = {k: v for k, v in stats.items() if k != 'not_found_names'}
    log_stats['not_found_sample'] = not_found_names[:50] if not_found_names else []

    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'batch_id': batch_id,
            'delete_command': f"DELETE FROM text_mentions WHERE batch_id = '{batch_id}'",
            'elapsed_seconds': elapsed,
            'dry_run': dry_run,
            'books_count': len(context_files),
            **log_stats
        }, f, indent=2, ensure_ascii=False)
    print(f"\n로그 저장: {log_file}")

    conn.close()
    return stats


if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv
    fast_mode = "--slow" not in sys.argv  # default: fast_mode=True
    limit = None
    for arg in sys.argv:
        if arg.startswith("--limit="):
            limit = int(arg.split("=")[1])

    if fast_mode:
        print("모드: FAST (로컬 DB만 사용 - exact/alias/trigram)")
    else:
        print("모드: SLOW (외부 API 포함 - wikidata/embedding/llm)")

    match_all_books(limit=limit, dry_run=dry_run, fast_mode=fast_mode)
