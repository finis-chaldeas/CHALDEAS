"""
십자군 전쟁 완전 임포트 테스트

목표: 완벽한 구조 입증
- 십자군 전쟁 (상위)
- 제1차 십자군 등 (하위)
- 각 이벤트의 위치, 인물, 설명 완전 수집

Usage:
    python test_crusades_import.py
"""

import sys
import json
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests

WIKIDATA_ENDPOINT = 'https://query.wikidata.org/sparql'


def sparql_query(query: str, timeout: int = 60) -> List[Dict]:
    """SPARQL 쿼리 실행"""
    try:
        response = requests.get(
            WIKIDATA_ENDPOINT,
            params={'query': query, 'format': 'json'},
            timeout=timeout,
            headers={'User-Agent': 'CHALDEAS/2.0 (Crusades Test)'}
        )
        if response.status_code == 200:
            return response.json()['results']['bindings']
        elif response.status_code == 429:
            print(f"  Rate limited, waiting 30s...")
            time.sleep(30)
            return sparql_query(query, timeout)
        else:
            print(f"  SPARQL error: {response.status_code}")
            return []
    except Exception as e:
        print(f"  SPARQL error: {e}")
        return []


@dataclass
class Location:
    qid: str
    name: str
    name_ko: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    type: str


@dataclass
class Person:
    qid: str
    name: str
    name_ko: Optional[str]
    role: Optional[str]


@dataclass
class Event:
    qid: str
    name: str
    name_ko: Optional[str]
    description: Optional[str]
    start_year: Optional[int]
    end_year: Optional[int]
    locations: List[Location]
    participants: List[Person]
    part_of_qid: Optional[str]
    part_of_name: Optional[str]

    def is_complete(self) -> tuple:
        """완전성 검사"""
        issues = []
        if not self.name:
            issues.append("이름 없음")
        if self.start_year is None:
            issues.append("날짜 없음")
        if not self.locations:
            issues.append("위치 없음")
        if not self.description:
            issues.append("설명 없음")
        return len(issues) == 0, issues


def parse_coord(coord_str: str) -> tuple:
    """좌표 파싱"""
    if not coord_str:
        return None, None
    try:
        coord = coord_str.replace('Point(', '').replace(')', '')
        parts = coord.split()
        return float(parts[1]), float(parts[0])  # lat, lng
    except:
        return None, None


def parse_year(time_str: str) -> Optional[int]:
    """연도 파싱"""
    if not time_str:
        return None
    try:
        if time_str.startswith('+'):
            time_str = time_str[1:]
        year_str = time_str.split('T')[0].split('-')[0]
        if time_str.startswith('-'):
            return -int(year_str)
        return int(year_str)
    except:
        return None


def get_crusade_events() -> List[str]:
    """십자군 전쟁 관련 이벤트 QID 수집"""
    print("=== 십자군 전쟁 이벤트 수집 ===\n")

    # Q12546 = Crusades (십자군 전쟁)
    # Q173065 = crusade (십자군 타입)
    query = """
    SELECT DISTINCT ?event ?eventLabel WHERE {
        {
            # 십자군 전쟁 자체
            VALUES ?event { wd:Q12546 }
        } UNION {
            # 십자군의 직접 하위 이벤트
            ?event wdt:P361 wd:Q12546.
        } UNION {
            # P31이 crusade인 이벤트
            ?event wdt:P31 wd:Q173065.
        } UNION {
            # 제1차~제9차 십자군의 하위 이벤트 (전투 등)
            ?event wdt:P361 ?parent.
            ?parent wdt:P361 wd:Q12546.
            ?event wdt:P31 wd:Q178561.  # battle
        }

        SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }
    ORDER BY ?eventLabel
    LIMIT 50
    """

    results = sparql_query(query)
    events = []

    for r in results:
        qid = r.get('event', {}).get('value', '').split('/')[-1]
        label = r.get('eventLabel', {}).get('value', '')
        if qid.startswith('Q'):
            events.append(qid)
            print(f"  {qid}: {label}")

    print(f"\n총 {len(events)}개 이벤트 발견\n")
    return events


def fetch_event_complete(qid: str) -> Optional[Event]:
    """이벤트 완전 정보 수집"""

    # 기본 정보 + 위치 + 참여자
    query = f"""
    SELECT DISTINCT
        ?label ?labelKo ?description
        ?pointInTime ?startTime ?endTime
        ?location ?locationLabel ?locationLabelKo ?locationCoord ?locationType
        ?country ?countryLabel ?countryLabelKo ?countryCoord
        ?participant ?participantLabel ?participantLabelKo ?roleLabel
        ?partOf ?partOfLabel
    WHERE {{
        # 기본 정보
        wd:{qid} rdfs:label ?label. FILTER(LANG(?label) = "en")
        OPTIONAL {{ wd:{qid} rdfs:label ?labelKo. FILTER(LANG(?labelKo) = "ko") }}
        OPTIONAL {{ wd:{qid} schema:description ?description. FILTER(LANG(?description) = "en") }}

        # 시간
        OPTIONAL {{ wd:{qid} wdt:P585 ?pointInTime. }}
        OPTIONAL {{ wd:{qid} wdt:P580 ?startTime. }}
        OPTIONAL {{ wd:{qid} wdt:P582 ?endTime. }}

        # 위치 (P276)
        OPTIONAL {{
            wd:{qid} wdt:P276 ?location.
            OPTIONAL {{ ?location rdfs:label ?locationLabel. FILTER(LANG(?locationLabel) = "en") }}
            OPTIONAL {{ ?location rdfs:label ?locationLabelKo. FILTER(LANG(?locationLabelKo) = "ko") }}
            OPTIONAL {{ ?location wdt:P625 ?locationCoord. }}
            OPTIONAL {{ ?location wdt:P31 ?locationType. }}
        }}

        # 국가 (P17) - fallback
        OPTIONAL {{
            wd:{qid} wdt:P17 ?country.
            OPTIONAL {{ ?country rdfs:label ?countryLabel. FILTER(LANG(?countryLabel) = "en") }}
            OPTIONAL {{ ?country rdfs:label ?countryLabelKo. FILTER(LANG(?countryLabelKo) = "ko") }}
            OPTIONAL {{ ?country wdt:P625 ?countryCoord. }}
        }}

        # 참여자 (P710)
        OPTIONAL {{
            wd:{qid} wdt:P710 ?participant.
            OPTIONAL {{ ?participant rdfs:label ?participantLabel. FILTER(LANG(?participantLabel) = "en") }}
            OPTIONAL {{ ?participant rdfs:label ?participantLabelKo. FILTER(LANG(?participantLabelKo) = "ko") }}
            OPTIONAL {{
                wd:{qid} p:P710 ?stmt.
                ?stmt ps:P710 ?participant.
                ?stmt pq:P3831 ?role.
                ?role rdfs:label ?roleLabel. FILTER(LANG(?roleLabel) = "en")
            }}
        }}

        # 관계
        OPTIONAL {{
            wd:{qid} wdt:P361 ?partOf.
            ?partOf rdfs:label ?partOfLabel. FILTER(LANG(?partOfLabel) = "en")
        }}

        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 100
    """

    results = sparql_query(query)

    if not results:
        return None

    # 첫 번째 결과에서 기본 정보
    r = results[0]

    # 위치 수집 (중복 제거)
    locations = {}
    for row in results:
        # P276 location
        loc_uri = row.get('location', {}).get('value', '')
        if loc_uri:
            loc_qid = loc_uri.split('/')[-1]
            if loc_qid.startswith('Q') and loc_qid not in locations:
                lat, lng = parse_coord(row.get('locationCoord', {}).get('value', ''))
                locations[loc_qid] = Location(
                    qid=loc_qid,
                    name=row.get('locationLabel', {}).get('value', ''),
                    name_ko=row.get('locationLabelKo', {}).get('value'),
                    latitude=lat,
                    longitude=lng,
                    type='place'
                )

        # P17 country (fallback)
        country_uri = row.get('country', {}).get('value', '')
        if country_uri:
            country_qid = country_uri.split('/')[-1]
            if country_qid.startswith('Q') and country_qid not in locations:
                lat, lng = parse_coord(row.get('countryCoord', {}).get('value', ''))
                locations[country_qid] = Location(
                    qid=country_qid,
                    name=row.get('countryLabel', {}).get('value', ''),
                    name_ko=row.get('countryLabelKo', {}).get('value'),
                    latitude=lat,
                    longitude=lng,
                    type='country'
                )

    # 참여자 수집 (중복 제거)
    participants = {}
    for row in results:
        part_uri = row.get('participant', {}).get('value', '')
        if part_uri:
            part_qid = part_uri.split('/')[-1]
            if part_qid.startswith('Q') and part_qid not in participants:
                participants[part_qid] = Person(
                    qid=part_qid,
                    name=row.get('participantLabel', {}).get('value', ''),
                    name_ko=row.get('participantLabelKo', {}).get('value'),
                    role=row.get('roleLabel', {}).get('value')
                )

    # 시간
    start_year = parse_year(
        r.get('pointInTime', {}).get('value') or
        r.get('startTime', {}).get('value')
    )
    end_year = parse_year(r.get('endTime', {}).get('value'))

    # part_of
    part_of_uri = r.get('partOf', {}).get('value', '')
    part_of_qid = part_of_uri.split('/')[-1] if part_of_uri else None

    return Event(
        qid=qid,
        name=r.get('label', {}).get('value', ''),
        name_ko=r.get('labelKo', {}).get('value'),
        description=r.get('description', {}).get('value'),
        start_year=start_year,
        end_year=end_year,
        locations=list(locations.values()),
        participants=list(participants.values()),
        part_of_qid=part_of_qid if part_of_qid and part_of_qid.startswith('Q') else None,
        part_of_name=r.get('partOfLabel', {}).get('value')
    )


def main():
    print("=" * 60)
    print("십자군 전쟁 완전 임포트 테스트")
    print("=" * 60)
    print()

    # 1. 이벤트 목록 수집
    event_qids = get_crusade_events()

    if not event_qids:
        print("이벤트를 찾을 수 없습니다.")
        return

    # 2. 각 이벤트 상세 수집
    print("=== 이벤트 상세 수집 ===\n")

    events = []
    complete_count = 0
    incomplete_events = []

    for i, qid in enumerate(event_qids):
        print(f"[{i+1}/{len(event_qids)}] {qid}...", end=' ')

        event = fetch_event_complete(qid)

        if event:
            events.append(event)

            is_complete, issues = event.is_complete()

            if is_complete:
                complete_count += 1
                print(f"✓ {event.name}")
            else:
                incomplete_events.append((event, issues))
                print(f"⚠ {event.name} - {', '.join(issues)}")
        else:
            print(f"✗ 가져오기 실패")

        time.sleep(0.5)

    # 3. 결과 출력
    print("\n" + "=" * 60)
    print("=== 결과 요약 ===")
    print("=" * 60)

    print(f"\n총 이벤트: {len(events)}")
    print(f"완전한 이벤트: {complete_count} ({100*complete_count/len(events):.1f}%)")
    print(f"불완전한 이벤트: {len(incomplete_events)}")

    # 위치 통계
    with_location = sum(1 for e in events if e.locations)
    print(f"\n위치 있는 이벤트: {with_location} ({100*with_location/len(events):.1f}%)")

    # 인물 통계
    with_participants = sum(1 for e in events if e.participants)
    print(f"인물 있는 이벤트: {with_participants} ({100*with_participants/len(events):.1f}%)")

    # 설명 통계
    with_description = sum(1 for e in events if e.description)
    print(f"설명 있는 이벤트: {with_description} ({100*with_description/len(events):.1f}%)")

    # 불완전한 이벤트 상세
    if incomplete_events:
        print("\n=== 불완전한 이벤트 ===")
        for event, issues in incomplete_events[:10]:
            print(f"  [{event.qid}] {event.name}")
            for issue in issues:
                print(f"       - {issue}")

    # 4. 예시 이벤트 출력
    if events:
        print("\n" + "=" * 60)
        print("=== 예시: 완전한 이벤트 ===")
        print("=" * 60)

        # 완전한 이벤트 하나 선택
        complete_event = next((e for e in events if e.is_complete()[0]), events[0])

        print(f"\n{complete_event.name}")
        print(f"  QID: {complete_event.qid}")
        print(f"  한국어: {complete_event.name_ko or 'N/A'}")
        print(f"  설명: {(complete_event.description or 'N/A')[:100]}...")
        print(f"  시간: {complete_event.start_year} - {complete_event.end_year or '?'}")
        print(f"  상위: {complete_event.part_of_name or 'N/A'}")

        print(f"\n  위치 ({len(complete_event.locations)}):")
        for loc in complete_event.locations[:5]:
            coord = f"({loc.latitude}, {loc.longitude})" if loc.latitude else "좌표 없음"
            print(f"    - {loc.name} ({loc.qid}) {coord}")

        print(f"\n  참여자 ({len(complete_event.participants)}):")
        for p in complete_event.participants[:5]:
            role = f"[{p.role}]" if p.role else ""
            print(f"    - {p.name} ({p.qid}) {role}")

        if len(complete_event.participants) > 5:
            print(f"    ... 외 {len(complete_event.participants) - 5}명")

    # 5. JSON 저장
    output = {
        'total': len(events),
        'complete': complete_count,
        'events': [asdict(e) for e in events]
    }

    with open('crusades_test_result.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장: crusades_test_result.json")


if __name__ == '__main__':
    main()
