"""
Task 4: Wikidata 정보 보강
QID 있는데 birth_year, biography 없는 것 채우기
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import urllib3
import json
import time
from datetime import datetime
from pathlib import Path

# SSL 경고 무시 (필요시)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 변경 이력 저장
CHANGE_LOG_DIR = Path("C:/Projects/Chaldeas/backups/change_logs")
CHANGE_LOG_DIR.mkdir(parents=True, exist_ok=True)

WIKIDATA_API = "https://www.wikidata.org/w/api.php"

# Wikidata API requires proper User-Agent
HEADERS = {
    'User-Agent': 'ChaldeasBot/1.0 (https://chaldeas.site; chaldeas@example.com) Python/3.10'
}

def fetch_wikidata_info(qid):
    """Wikidata에서 정보 가져오기"""
    params = {
        'action': 'wbgetentities',
        'ids': qid,
        'format': 'json',
        'languages': 'en|ko',
        'props': 'labels|descriptions|claims'
    }

    try:
        resp = requests.get(WIKIDATA_API, params=params, headers=HEADERS, timeout=30, verify=True)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        print(f"  API 오류 ({qid}): {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"  JSON 오류 ({qid}): {e}, response: {resp.text[:100]}")
        return None

    if 'entities' not in data or qid not in data['entities']:
        return None

    entity = data['entities'][qid]

    # 이름
    name_en = entity.get('labels', {}).get('en', {}).get('value')
    name_ko = entity.get('labels', {}).get('ko', {}).get('value')

    # 설명 (biography로 사용)
    desc_en = entity.get('descriptions', {}).get('en', {}).get('value')
    desc_ko = entity.get('descriptions', {}).get('ko', {}).get('value')

    # 생년/몰년
    claims = entity.get('claims', {})
    birth_year = None
    death_year = None

    if 'P569' in claims:  # date of birth
        try:
            birth_str = claims['P569'][0]['mainsnak']['datavalue']['value']['time']
            if birth_str[0] == '+':
                birth_year = int(birth_str[1:5])
            else:  # BCE
                birth_year = -int(birth_str[1:5])
        except:
            pass

    if 'P570' in claims:  # date of death
        try:
            death_str = claims['P570'][0]['mainsnak']['datavalue']['value']['time']
            if death_str[0] == '+':
                death_year = int(death_str[1:5])
            else:  # BCE
                death_year = -int(death_str[1:5])
        except:
            pass

    # 위키피디아 URL
    wikipedia_url = None
    if 'sitelinks' in entity and 'enwiki' in entity.get('sitelinks', {}):
        title = entity['sitelinks']['enwiki']['title']
        wikipedia_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"

    return {
        'name_en': name_en,
        'name_ko': name_ko,
        'biography': desc_en,
        'biography_ko': desc_ko,
        'birth_year': birth_year,
        'death_year': death_year,
        'wikipedia_url': wikipedia_url
    }


def enrich_persons(limit=100, offset=0, dry_run=True):
    conn = psycopg2.connect(
        host='localhost', port=5432, dbname='chaldeas',
        user='chaldeas', password='chaldeas_dev'
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 정보 부족한 것 찾기 (우선 birth_year 없는 것)
    cur.execute("""
        SELECT id, wikidata_id, name, birth_year, death_year, biography, name_ko
        FROM persons
        WHERE wikidata_id IS NOT NULL
        AND (birth_year IS NULL OR biography IS NULL OR name_ko IS NULL)
        ORDER BY id
        OFFSET %s
        LIMIT %s
    """, (offset, limit))
    persons = cur.fetchall()

    print(f"보강 대상: {len(persons)}개 (offset={offset}, limit={limit})")

    if not persons:
        print("보강할 것 없음!")
        conn.close()
        return

    if dry_run:
        # dry run: 첫 5개만 테스트
        print("\n=== Dry Run: 첫 5개 테스트 ===")
        for p in persons[:5]:
            print(f"\n[{p['id']}] {p['name']} ({p['wikidata_id']})")
            print(f"  현재: birth={p['birth_year']}, death={p['death_year']}, bio={p['biography'] is not None}, ko={p['name_ko'] is not None}")

            info = fetch_wikidata_info(p['wikidata_id'])
            if info:
                print(f"  Wikidata: birth={info['birth_year']}, death={info['death_year']}, bio={info['biography'] is not None}, ko={info['name_ko']}")
            else:
                print(f"  Wikidata: 정보 없음")
            time.sleep(0.2)

        print(f"\n(dry_run=True, 실제 업데이트 안 함)")
        conn.close()
        return

    # 실제 보강
    changes = []
    enriched = 0
    skipped = 0

    for i, p in enumerate(persons):
        if i % 50 == 0:
            print(f"진행: {i}/{len(persons)}")

        info = fetch_wikidata_info(p['wikidata_id'])
        if not info:
            skipped += 1
            continue

        # 변경 사항 추적
        change = {
            'id': p['id'],
            'qid': p['wikidata_id'],
            'name': p['name'],
            'updates': {}
        }

        # 업데이트할 필드 결정
        updates = []
        params = []

        if p['birth_year'] is None and info['birth_year'] is not None:
            updates.append("birth_year = %s")
            params.append(info['birth_year'])
            change['updates']['birth_year'] = info['birth_year']

        if p['death_year'] is None and info['death_year'] is not None:
            updates.append("death_year = %s")
            params.append(info['death_year'])
            change['updates']['death_year'] = info['death_year']

        if p['biography'] is None and info['biography'] is not None:
            updates.append("biography = %s")
            params.append(info['biography'])
            change['updates']['biography'] = info['biography']

        if p['name_ko'] is None and info['name_ko'] is not None:
            updates.append("name_ko = %s")
            params.append(info['name_ko'])
            change['updates']['name_ko'] = info['name_ko']

        if info['wikipedia_url'] is not None:
            updates.append("wikipedia_url = COALESCE(wikipedia_url, %s)")
            params.append(info['wikipedia_url'])

        # 업데이트 표시
        updates.append("enriched_by = 'wikidata_cleanup'")
        updates.append("enriched_at = NOW()")

        if updates:
            params.append(p['id'])
            cur.execute(f"""
                UPDATE persons SET {', '.join(updates)}
                WHERE id = %s
            """, params)
            enriched += 1
            changes.append(change)

        time.sleep(0.1)  # rate limit

        # 100개마다 커밋
        if (i + 1) % 100 == 0:
            conn.commit()
            print(f"  커밋: {i + 1}개")

    conn.commit()

    # 변경 이력 저장
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'action': 'enrich_from_wikidata',
        'offset': offset,
        'limit': limit,
        'total_processed': len(persons),
        'enriched': enriched,
        'skipped': skipped,
        'changes': changes
    }

    log_file = CHANGE_LOG_DIR / f"enrich_wikidata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    print(f"\n총 {enriched}개 보강 완료 (스킵: {skipped})")
    print(f"변경 이력: {log_file}")

    # 샘플 확인
    print("\n=== 보강 후 샘플 ===")
    cur.execute("""
        SELECT id, name, name_ko, birth_year, death_year, biography
        FROM persons
        WHERE enriched_by = 'wikidata_cleanup'
        ORDER BY enriched_at DESC
        LIMIT 5
    """)
    for row in cur.fetchall():
        bio = row['biography'][:50] if row['biography'] else None
        print(f"  [{row['id']}] {row['name']} ({row['name_ko']}) {row['birth_year']}-{row['death_year']}")
        print(f"      bio: {bio}...")

    conn.close()


if __name__ == "__main__":
    import sys
    dry_run = "--execute" not in sys.argv
    limit = 100
    offset = 0

    for arg in sys.argv:
        if arg.startswith("--limit="):
            limit = int(arg.split("=")[1])
        if arg.startswith("--offset="):
            offset = int(arg.split("=")[1])

    enrich_persons(limit=limit, offset=offset, dry_run=dry_run)
