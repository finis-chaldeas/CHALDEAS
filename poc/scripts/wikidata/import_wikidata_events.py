"""
Wikidata 이벤트 전체 임포트 스크립트.

Phase 1: 이벤트 임포트 (전투, 전쟁, 조약, 왕조 등)
Phase 2: 연결된 인물 임포트 (P710 참여자)
Phase 3: 연결된 장소 임포트 (P276)
Phase 4: 이벤트 간 관계 구축 (P361, P155/P156)

Usage:
    python import_wikidata_events.py --region uk --test  # 영국만 테스트
    python import_wikidata_events.py --region all        # 전체 임포트
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

import requests
import psycopg2
from psycopg2.extras import execute_values

from event_type_classifier import EventTypeClassifier, get_classifier

# Wikidata SPARQL endpoint
WIKIDATA_ENDPOINT = 'https://query.wikidata.org/sparql'

# 이벤트 타입 정의 (P31 instance of)
EVENT_TYPES = {
    # 군사/정치
    'battle': 'Q178561',
    'war': 'Q198',
    'military_conflict': 'Q180684',
    'siege': 'Q188055',
    'treaty': 'Q131569',
    'revolution': 'Q10931',
    'rebellion': 'Q124734',
    'coup_detat': 'Q45382',
    'civil_war': 'Q8465',

    # 왕조/국가
    'dynasty': 'Q164950',
    'empire': 'Q48349',
    'kingdom': 'Q3024240',
    'historical_country': 'Q3024240',

    # 종교/신화
    'religious_movement': 'Q2061186',
    'religious_war': 'Q1827102',
    'crusade': 'Q173065',

    # 문화/예술
    'art_movement': 'Q968159',
    'cultural_movement': 'Q2198855',
    'literary_movement': 'Q3326717',

    # 철학/사상
    'philosophical_movement': 'Q3235978',
    'school_of_thought': 'Q1387659',

    # 기타 역사적 사건
    'historical_event': 'Q13418847',
    'massacre': 'Q3199915',
    'expedition': 'Q2401485',
    'discovery': 'Q12772',
    'coronation': 'Q209480',
    'assassination': 'Q3882219',

    # 시대/기간
    'historical_period': 'Q11514315',
    'era': 'Q6428674',
}

# 지역별 필터 (P276 location 또는 P17 country)
REGION_FILTERS = {
    'uk': {
        'locations': [
            'Q145',    # United Kingdom
            'Q21',     # England
            'Q22',     # Scotland
            'Q25',     # Wales
            'Q26',     # Northern Ireland
            'Q179876', # Kingdom of England
            'Q192280', # Roman Britain
        ],
        'name': 'United Kingdom'
    },
    'france': {
        'locations': ['Q142', 'Q70972'],  # France, First French Empire
        'name': 'France'
    },
    'germany': {
        'locations': ['Q183', 'Q43287'],  # Germany, Holy Roman Empire
        'name': 'Germany'
    },
    'rome': {
        'locations': ['Q2277', 'Q17'],    # Roman Empire, Japan... wait
        'name': 'Roman Empire'
    },
    'greece': {
        'locations': ['Q41', 'Q11772'],   # Greece, Ancient Greece
        'name': 'Greece'
    },
    'korea': {
        'locations': ['Q18097', 'Q28233', 'Q884', 'Q423'],  # 조선, 고려, 한국, 북한
        'name': 'Korea'
    },
    'japan': {
        'locations': ['Q17'],
        'name': 'Japan'
    },
    'china': {
        'locations': ['Q148', 'Q9903'],   # China, Ming dynasty
        'name': 'China'
    },
    # 'all' - 지역 필터 없이 전체
}


@dataclass
class WikidataEvent:
    """Wikidata에서 가져온 이벤트."""
    qid: str
    label: str
    label_ko: Optional[str]
    description: Optional[str]
    event_type: str
    event_type_qid: str

    # CHALDEAS 분류 (event_type_classifier로 결정)
    category: str = 'unknown'  # military, political, dynasty, religious, etc.
    nature: str = 'unknown'    # battle, war, treaty, etc.

    # 시간
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    point_in_time: Optional[str] = None

    # 장소
    location_qid: Optional[str] = None
    location_label: Optional[str] = None
    country_qid: Optional[str] = None
    country_label: Optional[str] = None

    # 관계
    part_of_qid: Optional[str] = None
    part_of_label: Optional[str] = None

    # 참여자 (나중에 채움)
    participants: List[str] = None

    # Wikipedia
    wikipedia_url: Optional[str] = None

    def __post_init__(self):
        if self.participants is None:
            self.participants = []


class WikidataImporter:
    """Wikidata 이벤트 임포터."""

    def __init__(self, db_config: Dict = None, dry_run: bool = False):
        self.dry_run = dry_run
        self.db_config = db_config or {
            'host': 'localhost',
            'port': 5432,
            'database': 'chaldeas',
            'user': 'chaldeas',
            'password': 'chaldeas_dev'
        }
        self.conn = None
        self.classifier = get_classifier()  # 이벤트 타입 분류기
        self.stats = {
            'events_fetched': 0,
            'events_inserted': 0,
            'events_updated': 0,
            'events_excluded': 0,
            'events_unknown_type': 0,
            'persons_fetched': 0,
            'locations_fetched': 0,
            'relations_created': 0,
            'errors': 0,
        }

    def connect_db(self):
        """DB 연결."""
        if not self.dry_run:
            self.conn = psycopg2.connect(**self.db_config)

    def close_db(self):
        """DB 연결 종료."""
        if self.conn:
            self.conn.close()

    def sparql_query(self, query: str, timeout: int = 120) -> List[Dict]:
        """SPARQL 쿼리 실행."""
        try:
            response = requests.get(
                WIKIDATA_ENDPOINT,
                params={'query': query, 'format': 'json'},
                timeout=timeout,
                headers={'User-Agent': 'CHALDEAS/1.0 (Historical Knowledge System)'}
            )
            if response.status_code == 200:
                return response.json()['results']['bindings']
            else:
                print(f"  SPARQL error: {response.status_code}")
                return []
        except requests.exceptions.Timeout:
            print(f"  SPARQL timeout")
            return []
        except Exception as e:
            print(f"  SPARQL error: {e}")
            return []

    def fetch_events_by_type(self, event_type: str, event_qid: str,
                             region: str = None, limit: int = 1000) -> List[WikidataEvent]:
        """특정 타입의 이벤트들을 가져옴."""

        # 지역 필터 구성 (단순화)
        region_filter = ""
        if region and region != 'all' and region in REGION_FILTERS:
            locations = REGION_FILTERS[region]['locations']
            location_values = " ".join([f"wd:{loc}" for loc in locations])
            region_filter = f"""
            ?item wdt:P276/wdt:P131* ?loc.
            VALUES ?loc {{ {location_values} }}
            """

        # 단순화된 쿼리
        query = f"""
        SELECT DISTINCT
            ?item ?itemLabel ?itemDescription
            ?pointInTime ?startTime
            ?location ?locationLabel
            ?partOf ?partOfLabel
        WHERE {{
            ?item wdt:P31 wd:{event_qid}.

            {region_filter}

            OPTIONAL {{ ?item wdt:P585 ?pointInTime. }}
            OPTIONAL {{ ?item wdt:P580 ?startTime. }}
            OPTIONAL {{ ?item wdt:P276 ?location. }}
            OPTIONAL {{ ?item wdt:P361 ?partOf. }}

            SERVICE wikibase:label {{
                bd:serviceParam wikibase:language "en".
            }}
        }}
        LIMIT {limit}
        """

        results = self.sparql_query(query, timeout=180)
        events = []

        for r in results:
            try:
                qid = r.get('item', {}).get('value', '').split('/')[-1]
                if not qid.startswith('Q'):
                    continue

                # 이벤트 타입 분류 (event_type_qid로 분류)
                category, nature = self.classifier.classify(event_qid, event_type)

                # 제외 목록에 있으면 스킵
                if category == 'excluded':
                    self.stats['events_excluded'] += 1
                    continue

                # 알 수 없는 타입 카운트
                if category == 'unknown':
                    self.stats['events_unknown_type'] += 1

                event = WikidataEvent(
                    qid=qid,
                    label=r.get('itemLabel', {}).get('value', ''),
                    label_ko=None,  # 나중에 별도 쿼리로
                    description=r.get('itemDescription', {}).get('value'),
                    event_type=event_type,
                    event_type_qid=event_qid,
                    category=category,
                    nature=nature,
                    start_time=r.get('startTime', {}).get('value'),
                    end_time=None,  # 나중에
                    point_in_time=r.get('pointInTime', {}).get('value'),
                    location_qid=r.get('location', {}).get('value', '').split('/')[-1] if r.get('location') else None,
                    location_label=r.get('locationLabel', {}).get('value'),
                    country_qid=None,
                    country_label=None,
                    part_of_qid=r.get('partOf', {}).get('value', '').split('/')[-1] if r.get('partOf') else None,
                    part_of_label=r.get('partOfLabel', {}).get('value'),
                    wikipedia_url=None,
                )
                events.append(event)

            except Exception as e:
                self.stats['errors'] += 1
                continue

        return events

    def fetch_participants(self, event_qid: str) -> List[Dict]:
        """이벤트의 참여자들을 가져옴."""
        query = f"""
        SELECT ?person ?personLabel ?personLabel_ko ?role ?roleLabel WHERE {{
            wd:{event_qid} wdt:P710 ?person.
            OPTIONAL {{
                ?statement ps:P710 ?person.
                ?statement pq:P3831 ?role.
            }}
            SERVICE wikibase:label {{
                bd:serviceParam wikibase:language "en,ko".
                ?person rdfs:label ?personLabel.
                ?person rdfs:label ?personLabel_ko. FILTER(LANG(?personLabel_ko) = "ko")
                ?role rdfs:label ?roleLabel.
            }}
        }}
        """

        results = self.sparql_query(query, timeout=30)
        participants = []

        for r in results:
            person_qid = r.get('person', {}).get('value', '').split('/')[-1]
            if person_qid.startswith('Q'):
                participants.append({
                    'qid': person_qid,
                    'label': r.get('personLabel', {}).get('value', ''),
                    'label_ko': r.get('personLabel_ko', {}).get('value'),
                    'role': r.get('roleLabel', {}).get('value'),
                })

        return participants

    def parse_wikidata_time(self, time_str: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """Wikidata 시간 문자열을 year, month, day로 파싱."""
        if not time_str:
            return None, None, None

        try:
            # Format: +1066-10-14T00:00:00Z or -0055-01-01T00:00:00Z
            if time_str.startswith('+'):
                time_str = time_str[1:]

            parts = time_str.split('T')[0].split('-')

            if time_str.startswith('-'):
                # BCE
                year = -int(parts[0][1:]) if parts[0].startswith('-') else -int(parts[1])
                month = int(parts[2]) if len(parts) > 2 else None
                day = int(parts[3]) if len(parts) > 3 else None
            else:
                year = int(parts[0])
                month = int(parts[1]) if len(parts) > 1 and parts[1] != '01' else None
                day = int(parts[2]) if len(parts) > 2 and parts[2] != '01' else None

            return year, month, day

        except Exception as e:
            return None, None, None

    def insert_event(self, event: WikidataEvent) -> Optional[int]:
        """이벤트를 DB에 삽입."""
        if self.dry_run:
            return None

        year, month, day = self.parse_wikidata_time(
            event.point_in_time or event.start_time
        )
        end_year, end_month, end_day = self.parse_wikidata_time(event.end_time)

        # date_start는 NOT NULL이므로 없으면 스킵
        if year is None:
            self.stats['errors'] += 1
            return None

        # slug 생성
        import re
        slug = re.sub(r'[^a-z0-9]+', '-', event.label.lower()).strip('-')[:100]

        cur = self.conn.cursor()

        # 이미 존재하는지 확인
        cur.execute("SELECT id FROM events WHERE wikidata_id = %s", (event.qid,))
        existing = cur.fetchone()

        if existing:
            # 업데이트
            cur.execute("""
                UPDATE events SET
                    title = COALESCE(title, %s),
                    title_ko = COALESCE(title_ko, %s),
                    description = COALESCE(description, %s),
                    date_start = COALESCE(date_start, %s),
                    date_start_month = COALESCE(date_start_month, %s),
                    date_start_day = COALESCE(date_start_day, %s),
                    date_end = COALESCE(date_end, %s),
                    wikipedia_url = COALESCE(wikipedia_url, %s),
                    updated_at = NOW()
                WHERE wikidata_id = %s
                RETURNING id
            """, (
                event.label, event.label_ko, event.description,
                year, month, day, end_year,
                event.wikipedia_url,
                event.qid
            ))
            self.stats['events_updated'] += 1
            return cur.fetchone()[0]
        else:
            # slug 중복 체크
            cur.execute("SELECT COUNT(*) FROM events WHERE slug LIKE %s", (slug + '%',))
            slug_count = cur.fetchone()[0]
            if slug_count > 0:
                slug = f"{slug}-{event.qid.lower()}"

            # 새로 삽입 (source_reliability는 integer: 5=high)
            cur.execute("""
                INSERT INTO events (
                    title, title_ko, slug, description,
                    date_start, date_start_month, date_start_day,
                    date_end, date_end_month, date_end_day,
                    wikidata_id, wikipedia_url,
                    source_reliability, certainty,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    5, 'confirmed',
                    NOW(), NOW()
                )
                RETURNING id
            """, (
                event.label, event.label_ko, slug, event.description,
                year, month, day,
                end_year, end_month, end_day,
                event.qid, event.wikipedia_url
            ))
            self.stats['events_inserted'] += 1
            return cur.fetchone()[0]

    def import_region(self, region: str, event_types: List[str] = None,
                      limit_per_type: int = 500) -> Dict:
        """특정 지역의 이벤트들을 임포트."""

        if event_types is None:
            event_types = list(EVENT_TYPES.keys())

        region_name = REGION_FILTERS.get(region, {}).get('name', region)
        print(f"\n{'='*60}")
        print(f"Importing events for: {region_name}")
        print(f"{'='*60}")

        all_events = []

        for event_type in event_types:
            event_qid = EVENT_TYPES.get(event_type)
            if not event_qid:
                continue

            print(f"\n  Fetching {event_type}...", end=' ')

            events = self.fetch_events_by_type(
                event_type, event_qid,
                region=region,
                limit=limit_per_type
            )

            print(f"found {len(events)}")

            self.stats['events_fetched'] += len(events)
            all_events.extend(events)

            # Rate limiting
            time.sleep(1)

        # 중복 제거 (같은 QID)
        unique_events = {e.qid: e for e in all_events}
        all_events = list(unique_events.values())

        print(f"\n  Total unique events: {len(all_events)}")

        # 인류 역사만 필터링 (지질학적 시대 제외)
        all_events = self.filter_human_history(all_events)
        print(f"  After human history filter: {len(all_events)}")

        # DB 삽입
        if not self.dry_run:
            self.connect_db()

            for event in all_events:
                try:
                    self.insert_event(event)
                except Exception as e:
                    print(f"    Error inserting {event.qid}: {e}")
                    self.stats['errors'] += 1

            self.conn.commit()
            self.close_db()

        return {
            'region': region,
            'events': all_events,
            'stats': self.stats.copy()
        }

    def filter_human_history(self, events: List[WikidataEvent]) -> List[WikidataEvent]:
        """인류 역사만 필터링 (100,000 BCE 이후)."""
        MIN_YEAR = -100000  # 100,000 BCE
        MAX_YEAR = 2100     # Reasonable future limit

        filtered = []
        excluded = 0

        for e in events:
            year, _, _ = self.parse_wikidata_time(e.point_in_time or e.start_time)
            if year is None:
                filtered.append(e)  # 날짜 없으면 일단 포함
            elif MIN_YEAR <= year <= MAX_YEAR:
                filtered.append(e)
            else:
                excluded += 1

        if excluded > 0:
            print(f"  Filtered out {excluded} non-human-history events")

        return filtered

    def print_timeline(self, events: List[WikidataEvent]):
        """이벤트들을 타임라인으로 출력."""

        # 시간 파싱 및 정렬
        timed_events = []
        for e in events:
            year, _, _ = self.parse_wikidata_time(e.point_in_time or e.start_time)
            if year is not None:
                timed_events.append((year, e))

        timed_events.sort(key=lambda x: x[0])

        # 시대별 그룹핑
        print(f"\n{'='*70}")
        print("TIMELINE")
        print(f"{'='*70}")

        current_era = None
        for year, event in timed_events:
            # 시대 판정
            if year < -500:
                era = "Ancient (BC 500+)"
            elif year < 0:
                era = "Classical (500 BC - 1 AD)"
            elif year < 500:
                era = "Late Antiquity (1-500)"
            elif year < 1000:
                era = "Early Medieval (500-1000)"
            elif year < 1500:
                era = "High/Late Medieval (1000-1500)"
            elif year < 1800:
                era = "Early Modern (1500-1800)"
            else:
                era = "Modern (1800+)"

            if era != current_era:
                print(f"\n--- {era} ---")
                current_era = era

            year_str = f"{abs(year)} {'BCE' if year < 0 else 'CE'}"
            cat_nat = f"{event.category[:8]}/{event.nature[:8]}"
            # Encode safely for Windows console
            label_safe = event.label[:40].encode('ascii', 'replace').decode('ascii')
            print(f"  {year_str:12} {cat_nat:18} {label_safe}")

    def print_stats(self):
        """통계 출력."""
        print(f"\n{'='*40}")
        print("IMPORT STATISTICS")
        print(f"{'='*40}")
        for key, value in self.stats.items():
            print(f"  {key}: {value}")

        # 분류기 통계
        self.classifier.print_stats()

    def finalize(self):
        """종료 처리 (알 수 없는 타입 저장 등)."""
        self.classifier.finalize()
        print("\n  Unknown types logged for review.")


def main():
    parser = argparse.ArgumentParser(description='Wikidata Event Importer')
    parser.add_argument('--region', type=str, default='uk',
                        help='Region to import: uk, france, germany, rome, greece, korea, japan, china, all')
    parser.add_argument('--types', type=str, nargs='+', default=None,
                        help='Event types to import (default: all)')
    parser.add_argument('--limit', type=int, default=500,
                        help='Limit per event type')
    parser.add_argument('--dry-run', action='store_true',
                        help='Dry run (no DB insert)')
    parser.add_argument('--test', action='store_true',
                        help='Test mode (small limit)')

    args = parser.parse_args()

    if args.test:
        args.limit = 50
        args.dry_run = True

    importer = WikidataImporter(dry_run=args.dry_run)

    # 이벤트 타입 선택
    if args.types:
        event_types = args.types
    else:
        # 기본: 주요 타입만
        event_types = ['battle', 'war', 'treaty', 'siege', 'rebellion',
                       'dynasty', 'coronation', 'revolution']

    result = importer.import_region(
        args.region,
        event_types=event_types,
        limit_per_type=args.limit
    )

    # 타임라인 출력
    importer.print_timeline(result['events'])

    # 통계 출력
    importer.print_stats()

    # 종료 처리 (알 수 없는 타입 로그 저장)
    importer.finalize()

    # 결과 저장
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'wikidata')
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, f"events_{args.region}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'region': args.region,
            'timestamp': datetime.now().isoformat(),
            'stats': result['stats'],
            'events': [asdict(e) for e in result['events']]
        }, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to: {output_file}")


if __name__ == '__main__':
    main()
