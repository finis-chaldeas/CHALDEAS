"""
Phase 2+3: Wikipedia ZIM에서 본문 추출 → DB sources/mentions 임포트

Phase 1의 sitelinks.jsonl 결과를 사용하여:
1. Wikipedia ZIM 파일에서 문서 본문 추출
2. sources 테이블에 source_type='wikipedia' 저장
3. event_sources 연결 생성
4. mentions 테이블에 event → source 연결 생성
5. events.wikipedia_url 업데이트
6. events.primary_location_id 좌표 근접 매칭으로 업데이트

Usage:
    python import_wikipedia_sources.py
    python import_wikipedia_sources.py --skip-text          # 본문 없이 메타만
    python import_wikipedia_sources.py --limit 100          # 테스트
    python import_wikipedia_sources.py --fix-locations-only  # 위치만 수정
"""

import json
import sys
import os
import time
import argparse
import math
from pathlib import Path
from typing import Optional

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 경로
SITELINKS_FILE = Path("C:/Projects/Chaldeas/data/compact_export/event_sitelinks.jsonl")
ZIM_EN = "E:/chaldeas_data/kiwix/wikipedia_en_nopic.zim"
ZIM_KO = "E:/chaldeas_data/kiwix/wikipedia_ko_all_nopic_2026-01.zim"
ZIM_JA = "E:/chaldeas_data/kiwix/wikipedia_ja_all_nopic_2025-10.zim"

DB_URL = "postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas"

# 좌표 근접 매칭 임계값 (km)
PROXIMITY_THRESHOLD_KM = 50


def haversine_km(lat1, lon1, lat2, lon2):
    """두 좌표 간 거리 (km)"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def load_sitelinks(path: Path, limit: int = 0):
    """Phase 1 결과 로드"""
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if limit > 0 and i >= limit:
                break
            records.append(json.loads(line))
    return records


def extract_text_from_zim(zim_path: str, title: str) -> Optional[str]:
    """ZIM 파일에서 문서 본문 추출 (HTML → plain text)"""
    try:
        from libzim.reader import Archive
        from bs4 import BeautifulSoup
    except ImportError as e:
        print(f"  라이브러리 없음: {e}")
        return None

    try:
        archive = extract_text_from_zim._archive_cache.get(zim_path)
        if archive is None:
            archive = Archive(zim_path)
            extract_text_from_zim._archive_cache[zim_path] = archive
    except Exception as e:
        print(f"  ZIM 열기 실패: {e}")
        return None

    # Wikipedia ZIM의 문서 경로 형식
    # 공백 → 언더스코어
    article_path = title.replace(' ', '_')

    try:
        entry = archive.get_entry_by_path(f"A/{article_path}")
    except KeyError:
        try:
            entry = archive.get_entry_by_path(article_path)
        except KeyError:
            return None

    try:
        item = entry.get_item()
        content = bytes(item.content).decode('utf-8', errors='replace')
    except Exception:
        return None

    # HTML → plain text
    if content.strip().startswith('<'):
        try:
            soup = BeautifulSoup(content, 'html.parser')

            # 불필요한 요소 제거
            for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()

            # References/See also 이후 제거 (핵심 본문만)
            for heading in soup.find_all(['h2', 'h3']):
                text = heading.get_text().strip().lower()
                if text in ('references', 'see also', 'external links',
                           'further reading', 'notes', 'bibliography',
                           'footnotes', 'citations'):
                    # 이 heading 이후 모든 sibling 제거
                    for sibling in list(heading.find_next_siblings()):
                        sibling.decompose()
                    heading.decompose()
                    break

            text = soup.get_text(separator='\n')

            # 빈 줄 정리
            lines = [l.strip() for l in text.split('\n')]
            lines = [l for l in lines if l]
            text = '\n'.join(lines)

            return text if len(text) > 100 else None

        except Exception:
            return content[:50000] if len(content) > 100 else None
    else:
        return content if len(content) > 100 else None

extract_text_from_zim._archive_cache = {}


def load_city_locations(conn):
    """DB에서 도시 위치 로드 (좌표 근접 매칭용)"""
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, latitude, longitude, wikidata_id
        FROM locations
        WHERE is_light = TRUE
          AND is_region = FALSE
          AND latitude IS NOT NULL
          AND longitude IS NOT NULL
    """)
    rows = cur.fetchall()
    cur.close()

    locations = []
    wikidata_map = {}
    for row in rows:
        loc = {
            'id': row[0],
            'name': row[1],
            'latitude': float(row[2]),
            'longitude': float(row[3]),
            'wikidata_id': row[4],
        }
        locations.append(loc)
        if row[4]:
            wikidata_map[row[4]] = loc

    return locations, wikidata_map


def find_nearest_city(lat, lng, cities, threshold_km=PROXIMITY_THRESHOLD_KM):
    """좌표에서 가장 가까운 도시 찾기"""
    best = None
    best_dist = float('inf')

    for city in cities:
        dist = haversine_km(lat, lng, city['latitude'], city['longitude'])
        if dist < best_dist:
            best_dist = dist
            best = city

    if best and best_dist <= threshold_km:
        return best, best_dist
    return None, None


def main():
    parser = argparse.ArgumentParser(description='Phase 2+3: Wikipedia 본문 추출 → DB 임포트')
    parser.add_argument('--sitelinks', default=str(SITELINKS_FILE), help='Phase 1 출력 파일')
    parser.add_argument('--limit', type=int, default=0, help='처리할 최대 이벤트 수')
    parser.add_argument('--skip-text', action='store_true', help='Wikipedia 본문 추출 건너뜀')
    parser.add_argument('--fix-locations-only', action='store_true', help='위치 매핑만 수행')
    parser.add_argument('--dry-run', action='store_true', help='DB 변경 없이 통계만')
    args = parser.parse_args()

    sitelinks_path = Path(args.sitelinks)
    if not sitelinks_path.exists():
        print(f"ERROR: Phase 1 결과 파일 없음: {sitelinks_path}")
        print("  먼저 extract_event_sitelinks.py 실행 필요")
        sys.exit(1)

    print("=== Phase 2+3: Wikipedia 본문 → DB 임포트 ===")
    print()

    # sitelinks 로드
    print("Phase 1 결과 로드 중...")
    records = load_sitelinks(sitelinks_path, args.limit)
    print(f"  이벤트: {len(records):,}개")
    print()

    # DB 연결
    import psycopg2
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False

    # 도시 위치 로드 (좌표 매칭용)
    print("도시 위치 데이터 로드 중...")
    cities, wikidata_loc_map = load_city_locations(conn)
    print(f"  도시: {len(cities):,}개")
    print(f"  Wikidata ID 매핑: {len(wikidata_loc_map):,}개")
    print()

    start_time = time.time()

    # === Phase 2: Wikipedia 본문 추출 ===
    if not args.fix_locations_only and not args.skip_text:
        print("=== Phase 2: Wikipedia ZIM에서 본문 추출 ===")

        articles_extracted = 0
        articles_failed = 0

        for i, record in enumerate(records):
            enwiki_title = record.get('sitelinks', {}).get('en')
            if not enwiki_title:
                continue

            text = extract_text_from_zim(ZIM_EN, enwiki_title)
            if text:
                record['article_text'] = text
                record['article_word_count'] = len(text.split())
                articles_extracted += 1
            else:
                articles_failed += 1

            if (articles_extracted + articles_failed) % 500 == 0:
                elapsed = time.time() - start_time
                print(f"  추출: {articles_extracted:,} | 실패: {articles_failed:,} | "
                      f"경과: {elapsed:.1f}초")

        print(f"\n  Wikipedia 본문 추출 완료:")
        print(f"    성공: {articles_extracted:,}")
        print(f"    실패: {articles_failed:,}")
        print(f"    enwiki 없음: {len(records) - articles_extracted - articles_failed:,}")
        print()

    # === Phase 3: DB 임포트 ===
    print("=== Phase 3: DB 임포트 ===")

    cur = conn.cursor()

    # 통계
    sources_created = 0
    event_sources_created = 0
    mentions_created = 0
    locations_fixed = 0
    locations_by_qid = 0
    locations_by_coord = 0
    wiki_urls_set = 0

    for i, record in enumerate(records):
        event_id = record['event_id']
        qid = record['qid']
        sitelinks = record.get('sitelinks', {})
        coordinate = record.get('coordinate')
        location_qids = record.get('location_qids', [])
        enwiki_title = sitelinks.get('en')

        # 1. Wikipedia URL 업데이트
        if enwiki_title and not args.fix_locations_only:
            wiki_url = f"https://en.wikipedia.org/wiki/{enwiki_title.replace(' ', '_')}"

            if not args.dry_run:
                cur.execute(
                    "UPDATE events SET wikipedia_url = %s WHERE id = %s AND (wikipedia_url IS NULL OR wikipedia_url = '')",
                    (wiki_url, event_id)
                )
                if cur.rowcount > 0:
                    wiki_urls_set += 1
            else:
                wiki_urls_set += 1

        # 2. Wikipedia source 생성
        article_text = record.get('article_text')
        if article_text and not args.fix_locations_only:
            source_title = f"{enwiki_title} - Wikipedia"
            word_count = record.get('article_word_count', 0)

            if not args.dry_run:
                # 기존 wikipedia source가 있는지 확인
                cur.execute(
                    "SELECT id FROM sources WHERE source_type = 'wikipedia' AND title = %s",
                    (source_title,)
                )
                existing = cur.fetchone()

                if existing:
                    source_id = existing[0]
                    # 본문 업데이트
                    cur.execute(
                        "UPDATE sources SET content_raw = %s, word_count = %s WHERE id = %s",
                        (article_text, word_count, source_id)
                    )
                else:
                    wiki_url = f"https://en.wikipedia.org/wiki/{enwiki_title.replace(' ', '_')}"
                    cur.execute("""
                        INSERT INTO sources (source_type, title, content_raw, url, language, reliability, word_count)
                        VALUES ('wikipedia', %s, %s, %s, 'en', 3, %s)
                        RETURNING id
                    """, (source_title, article_text, wiki_url, word_count))
                    source_id = cur.fetchone()[0]
                    sources_created += 1

                # event_sources 연결
                cur.execute("""
                    INSERT INTO event_sources (event_id, source_id)
                    VALUES (%s, %s)
                    ON CONFLICT (event_id, source_id) DO NOTHING
                """, (event_id, source_id))
                if cur.rowcount > 0:
                    event_sources_created += 1

                # mentions 생성
                # 첫 500자를 evidence로 사용
                evidence = article_text[:500] if article_text else f"Wikipedia article: {enwiki_title}"
                cur.execute("""
                    INSERT INTO mentions (source_id, target_type, target_id, evidence_raw)
                    VALUES (%s, 'event', %s, %s)
                """, (source_id, event_id, evidence))
                mentions_created += 1
            else:
                sources_created += 1
                event_sources_created += 1
                mentions_created += 1

        # 3. 위치 매핑 (primary_location_id가 NULL인 경우만)
        cur.execute(
            "SELECT primary_location_id FROM events WHERE id = %s",
            (event_id,)
        )
        current_loc = cur.fetchone()
        if current_loc and current_loc[0] is not None:
            continue  # 이미 위치가 있음

        matched_location = None
        match_method = None

        # 3a. P276 location QID로 직접 매칭
        for loc_qid in location_qids:
            if loc_qid in wikidata_loc_map:
                matched_location = wikidata_loc_map[loc_qid]
                match_method = 'qid'
                break

        # 3b. P625 좌표로 근접 매칭
        if not matched_location and coordinate:
            lat = coordinate.get('latitude')
            lng = coordinate.get('longitude')
            if lat is not None and lng is not None:
                city, dist = find_nearest_city(lat, lng, cities)
                if city:
                    matched_location = city
                    match_method = 'coordinate'

        if matched_location:
            if not args.dry_run:
                cur.execute(
                    "UPDATE events SET primary_location_id = %s WHERE id = %s",
                    (matched_location['id'], event_id)
                )
            locations_fixed += 1
            if match_method == 'qid':
                locations_by_qid += 1
            else:
                locations_by_coord += 1

        # 진행 출력
        if (i + 1) % 1000 == 0:
            elapsed = time.time() - start_time
            print(f"  처리: {i+1:,}/{len(records):,} | "
                  f"sources: {sources_created:,} | locations: {locations_fixed:,} | "
                  f"경과: {elapsed:.1f}초")

    # 커밋
    if not args.dry_run:
        conn.commit()
        print("\n  DB 커밋 완료")
    else:
        conn.rollback()
        print("\n  [DRY RUN] 변경사항 롤백")

    cur.close()
    conn.close()

    elapsed = time.time() - start_time

    print()
    print("=== 결과 ===")
    print(f"  Wikipedia URL 설정: {wiki_urls_set:,}")
    print(f"  Wikipedia sources 생성: {sources_created:,}")
    print(f"  event_sources 연결: {event_sources_created:,}")
    print(f"  mentions 생성: {mentions_created:,}")
    print(f"  위치 매핑 수정: {locations_fixed:,}")
    print(f"    - QID 직접 매칭: {locations_by_qid:,}")
    print(f"    - 좌표 근접 매칭: {locations_by_coord:,}")
    print(f"  소요 시간: {elapsed:.1f}초")


if __name__ == '__main__':
    main()
