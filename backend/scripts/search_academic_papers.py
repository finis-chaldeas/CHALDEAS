"""
Academic Paper Search via OpenAlex API
- events importance >= 3 부터 시작
- 초록(abstract) 텍스트로 바로 저장 (PDF 불필요)
- 품질 스코어링 후 상위 논문만 선별
"""

import sys
import time
import json
import requests
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# unbuffered output for background execution
import functools
print = functools.partial(print, flush=True)

OPENALEX_BASE = "https://api.openalex.org"
OPENALEX_EMAIL = "chaldeas@chaldeas.site"  # polite pool
DELAY = 1.0  # seconds between requests (safe for rate limit)

OUTPUT_DIR = Path("C:/Projects/Chaldeas/data/compact_export/academic_papers")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def reconstruct_abstract(inverted_index: dict) -> str:
    """OpenAlex abstract_inverted_index → plaintext"""
    if not inverted_index:
        return ""
    length = max(pos for positions in inverted_index.values() for pos in positions) + 1
    words = [''] * length
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word
    return ' '.join(words)


def quality_score(paper: dict) -> int:
    """논문 품질 점수 (0~100)"""
    score = 0

    # 1. 인용 백분위 (최대 40점)
    percentile = paper.get('cited_by_percentile_year', {})
    pmin = percentile.get('min', 0) if percentile else 0
    if pmin >= 95:
        score += 40
    elif pmin >= 90:
        score += 35
    elif pmin >= 75:
        score += 25
    elif pmin >= 50:
        score += 15

    # 2. 인용수 보너스 (최대 15점)
    citations = paper.get('cited_by_count', 0)
    if citations >= 100:
        score += 15
    elif citations >= 50:
        score += 10
    elif citations >= 20:
        score += 7
    elif citations >= 5:
        score += 3

    # 3. 토픽 관련성 (최대 15점)
    primary_topic = paper.get('primary_topic') or {}
    topic_score = primary_topic.get('score', 0)
    score += int(topic_score * 15)

    # 4. 분야 매칭 (최대 10점)
    subfield = (primary_topic.get('subfield') or {}).get('display_name', '')
    field = (primary_topic.get('field') or {}).get('display_name', '')
    if 'History' in subfield:
        score += 10
    elif field == 'Arts and Humanities':
        score += 7
    elif field == 'Social Sciences':
        score += 4

    # 5. 초록 있음 + OA 보너스 (최대 5점)
    if paper.get('abstract_inverted_index'):
        score += 3
    if paper.get('open_access', {}).get('is_oa'):
        score += 2

    # 6. 철회 논문
    if paper.get('is_retracted'):
        score = 0

    return score


def grade(score: int) -> str:
    if score >= 70: return 'A'
    if score >= 50: return 'B'
    if score >= 30: return 'C'
    return 'D'


def search_openalex(query: str, max_results: int = 20) -> list:
    """OpenAlex에서 논문 검색 + 품질 스코어링"""
    # 정확한 구문 검색 (따옴표 포함) + 관련성 정렬
    params = {
        'search': f'"{query}"',
        'per_page': min(max_results, 50),
        'sort': 'relevance_score:desc',
        'select': ','.join([
            'id', 'title', 'publication_year', 'cited_by_count',
            'cited_by_percentile_year', 'type', 'authorships',
            'primary_topic', 'open_access', 'abstract_inverted_index',
            'doi', 'referenced_works_count', 'is_retracted'
        ]),
        'mailto': OPENALEX_EMAIL,
    }

    for attempt in range(3):
        try:
            resp = requests.get(f"{OPENALEX_BASE}/works", params=params, timeout=15)
            if resp.status_code == 429:
                if attempt < 2:
                    wait = 10 * (attempt + 1)
                    print(f"  [RATE LIMIT] waiting {wait}s...")
                    time.sleep(wait)
                    continue
                else:
                    # 3번 다 429면 일일 한도 소진 → 'BUDGET_EXHAUSTED' 시그널
                    print(f"  [BUDGET EXHAUSTED] daily limit reached")
                    return 'BUDGET_EXHAUSTED'
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as e:
            if attempt == 2:
                print(f"  [ERROR] {query}: {e}")
                return []
            time.sleep(3)
    else:
        return 'BUDGET_EXHAUSTED'

    results = []
    for paper in data.get('results', []):
        abstract = reconstruct_abstract(paper.get('abstract_inverted_index', {}))
        score = quality_score(paper)
        g = grade(score)

        # D급은 버림
        if g == 'D':
            continue

        authors = []
        for a in (paper.get('authorships') or [])[:5]:
            name = (a.get('author') or {}).get('display_name', '')
            if name:
                authors.append(name)

        results.append({
            'openalex_id': paper.get('id', '').replace('https://openalex.org/', ''),
            'title': paper.get('title', ''),
            'authors': authors,
            'year': paper.get('publication_year'),
            'cited_by_count': paper.get('cited_by_count', 0),
            'percentile_min': (paper.get('cited_by_percentile_year') or {}).get('min', 0),
            'type': paper.get('type', ''),
            'doi': paper.get('doi', ''),
            'is_oa': paper.get('open_access', {}).get('is_oa', False),
            'oa_url': paper.get('open_access', {}).get('oa_url', ''),
            'topic': (paper.get('primary_topic') or {}).get('display_name', ''),
            'subfield': ((paper.get('primary_topic') or {}).get('subfield') or {}).get('display_name', ''),
            'field': ((paper.get('primary_topic') or {}).get('field') or {}).get('display_name', ''),
            'abstract': abstract,
            'abstract_len': len(abstract),
            'quality_score': score,
            'quality_grade': g,
        })

    results.sort(key=lambda x: x['quality_score'], reverse=True)
    return results


def search_for_event(event_title: str, event_id: int, importance: int) -> dict | str:
    """하나의 이벤트에 대해 논문 검색. 'BUDGET_EXHAUSTED' 반환 시 중단."""
    papers = search_openalex(event_title, max_results=20)

    if papers == 'BUDGET_EXHAUSTED':
        return 'BUDGET_EXHAUSTED'

    return {
        'event_id': event_id,
        'event_title': event_title,
        'importance': importance,
        'query': event_title,
        'papers_found': len(papers),
        'papers': papers[:10],
        'searched_at': datetime.now().isoformat(),
    }


def main():
    import psycopg2

    print("=" * 60)
    print("Academic Paper Search - Events (importance >= 3)")
    print("=" * 60)

    # DB에서 이벤트 가져오기 (importance 5부터)
    conn = psycopg2.connect(
        host='localhost', port=5432,
        dbname='chaldeas', user='chaldeas', password='chaldeas_dev'
    )
    cur = conn.cursor()

    # importance를 커맨드라인 인자로 받기 (기본값 5)
    target_imp = int(sys.argv[1]) if len(sys.argv) > 1 else 5

    cur.execute("""
        SELECT id, title, importance
        FROM events
        WHERE importance = %s
        ORDER BY id
    """, (target_imp,))
    events = cur.fetchall()
    cur.close()
    conn.close()

    print(f"\n대상 이벤트: {len(events)}개 (importance={target_imp})")
    print("-" * 60)

    # 체크포인트: 이전 결과 이어서 하기
    checkpoint_file = OUTPUT_DIR / f"events_imp{target_imp}_checkpoint.json"
    all_results = []
    done_ids = set()

    if checkpoint_file.exists():
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoint = json.load(f)
            all_results = checkpoint.get('results', [])
            done_ids = {r['event_id'] for r in all_results}
        print(f"  체크포인트 로드: {len(done_ids)}개 완료, 이어서 진행")

    remaining = [(eid, title, imp) for eid, title, imp in events if eid not in done_ids]
    total_papers = sum(r['papers_found'] for r in all_results)
    total_with_abstract = sum(
        sum(1 for p in r['papers'] if p['abstract_len'] > 0)
        for r in all_results
    )
    errors = 0

    print(f"  남은 이벤트: {len(remaining)}개")
    print("-" * 60)

    for i, (eid, title, imp) in enumerate(remaining):
        progress = len(done_ids) + i + 1
        print(f"\n[{progress}/{len(events)}] {title} (imp={imp})")

        result = search_for_event(title, eid, imp)

        if result == 'BUDGET_EXHAUSTED':
            print("\n  !!! 일일 한도 소진 — 체크포인트 저장 후 종료 !!!")
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'results': all_results,
                    'saved_at': datetime.now().isoformat(),
                }, f, ensure_ascii=False)
            print(f"  체크포인트 저장: {len(all_results)}개 완료")
            print(f"  내일 다시 실행하면 자동으로 이어서 진행합니다.")
            break

        all_results.append(result)

        for p in result['papers']:
            total_papers += 1
            if p['abstract_len'] > 0:
                total_with_abstract += 1
            mark = '*' if p['quality_grade'] == 'A' else ' '
            print(f"  {mark} [{p['quality_grade']}:{p['quality_score']:2d}] "
                  f"{p['title'][:55]}  "
                  f"({p['year']}, c:{p['cited_by_count']}, "
                  f"abs:{p['abstract_len']})")

        if result['papers_found'] == 0:
            print("  (논문 없음)")

        # 50건마다 체크포인트 저장
        if (i + 1) % 50 == 0:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'results': all_results,
                    'saved_at': datetime.now().isoformat(),
                }, f, ensure_ascii=False)
            print(f"\n  >>> 체크포인트 저장 ({progress}/{len(events)})")

        time.sleep(DELAY)

    # 최종 결과 저장
    budget_exhausted = (result == 'BUDGET_EXHAUSTED') if 'result' in dir() else False
    output_file = OUTPUT_DIR / f"events_imp{target_imp}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'search_type': 'events',
            'importance_filter': target_imp,
            'events_searched': len(events),
            'events_with_papers': sum(1 for r in all_results if r['papers_found'] > 0),
            'events_no_papers': sum(1 for r in all_results if r['papers_found'] == 0),
            'total_papers': total_papers,
            'total_with_abstract': total_with_abstract,
            'abstract_rate': f"{total_with_abstract/max(total_papers,1)*100:.1f}%",
            'complete': not budget_exhausted,
            'results': all_results,
        }, f, ensure_ascii=False, indent=2)

    # 체크포인트 정리: 완전히 끝났을 때만 삭제
    if not budget_exhausted and checkpoint_file.exists():
        checkpoint_file.unlink()

    print(f"\n{'=' * 60}")
    print(f"결과 요약:")
    print(f"  이벤트 검색: {len(events)}개")
    print(f"  논문 발견: {total_papers}편")
    print(f"  초록 있음: {total_with_abstract}편 ({total_with_abstract/max(total_papers,1)*100:.1f}%)")
    print(f"  저장: {output_file}")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
