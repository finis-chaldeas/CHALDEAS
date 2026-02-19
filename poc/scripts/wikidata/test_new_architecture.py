"""
새 아키텍처 테스트 - 데이터 접근과 처리 분리 검증

Usage:
    python test_new_architecture.py
"""

import sys
import time

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 데이터 접근 레이어
from data_access.sparql_client import get_client
from data_access.event_fetcher import EventFetcher

# 처리 레이어
from processing.transformers import SPARQLResultTransformer
from processing.validators import BatchValidator


def test_crusades():
    """십자군 전쟁 테스트"""
    print("=" * 60)
    print("새 아키텍처 테스트: 십자군 전쟁")
    print("=" * 60)
    print()

    # 1. 데이터 접근: 십자군 전쟁 이벤트 QID 수집
    print("[1] 데이터 접근: 이벤트 QID 수집")
    print("-" * 40)

    client = get_client()

    query = """
    SELECT DISTINCT ?event WHERE {
        {
            VALUES ?event { wd:Q12546 }
        } UNION {
            ?event wdt:P361 wd:Q12546.
        } UNION {
            ?event wdt:P31 wd:Q173065.
        } UNION {
            ?event wdt:P361 ?parent.
            ?parent wdt:P361 wd:Q12546.
            ?event wdt:P31 wd:Q178561.
        }
    }
    LIMIT 30
    """

    result = client.query(query)
    print(f"  쿼리 결과: success={result.success}, rows={len(result.data)}")

    qids = [r['event']['value'].split('/')[-1] for r in result.data]
    print(f"  발견된 QID: {len(qids)}개")
    print()

    # 2. 데이터 접근: 각 이벤트 상세 페치
    print("[2] 데이터 접근: 이벤트 상세 페치")
    print("-" * 40)

    fetcher = EventFetcher()
    fetch_result = fetcher.fetch_by_qids(qids[:15])  # 15개만 테스트

    print(f"  페치 결과: {len(fetch_result.events)}개 이벤트")
    print(f"  총 쿼리 시간: {fetch_result.total_query_time_ms}ms")
    print()

    # 3. 처리: 변환
    print("[3] 처리: 도메인 모델로 변환")
    print("-" * 40)

    transformer = SPARQLResultTransformer()
    events = []

    for raw_event in fetch_result.events:
        event = transformer.transform_event(raw_event.qid, raw_event.raw_data)
        if event:
            events.append(event)
            print(f"  {event.qid}: {event.name[:40]}...")

    print(f"\n  변환 성공: {len(events)}개")
    print()

    # 4. 처리: 검증
    print("[4] 처리: 검증")
    print("-" * 40)

    validator = BatchValidator()
    stats = validator.validate_events(events)

    print(f"  총 이벤트: {stats['total']}")
    print(f"  유효: {stats['valid']} ({stats['valid_pct']:.1f}%)")
    print(f"  완전: {stats['complete']} ({stats['complete_pct']:.1f}%)")
    print(f"  평균 완전성: {stats['avg_completeness']*100:.1f}%")
    print(f"\n  이슈별 현황:")
    for issue, count in stats['issues'].items():
        print(f"    - {issue}: {count}개")

    print()

    # 5. 예시 출력
    print("[5] 예시: 가장 완전한 이벤트")
    print("-" * 40)

    from processing.validators import EventValidator
    ev = EventValidator()

    best = None
    best_score = 0

    for event in events:
        result = ev.validate(event)
        if result.completeness_score > best_score:
            best_score = result.completeness_score
            best = event

    if best:
        print(f"  이름: {best.name}")
        print(f"  한국어: {best.name_ko or 'N/A'}")
        print(f"  설명: {(best.description or 'N/A')[:60]}...")
        print(f"  시간: {best.start_year} - {best.end_year or '?'}")
        print(f"  타입: {best.event_type}")
        print(f"  상위: {best.part_of_name or 'N/A'}")
        print(f"  위치: {len(best.locations)}개")
        for loc in best.locations[:3]:
            coord = f"({loc.latitude}, {loc.longitude})" if loc.latitude else "좌표 없음"
            print(f"    - {loc.name} {coord}")
        print(f"  참여자: {len(best.participants)}개")
        for p in best.participants[:3]:
            print(f"    - {p.name}")

    print()
    print("=" * 60)
    print("테스트 완료")
    print("=" * 60)


if __name__ == '__main__':
    test_crusades()
