"""
Event Importer - Wikidata 이벤트 임포트

핵심 원칙:
1. 위치를 먼저 생성하고 이벤트에 연결
2. 비이벤트 (도시, 국가 등) 필터링
3. 날짜 없으면 스킵
"""

import re
from typing import Dict, List, Optional
from .base import BaseImporter
from .location_importer import LocationImporter


class EventImporter(BaseImporter):
    """이벤트 임포터"""

    TABLE = 'events'

    # 제외할 P31 타입 (이벤트가 아닌 것들)
    EXCLUDED_INSTANCE_TYPES = {
        # 지리
        'Q515',       # city
        'Q1549591',   # big city
        'Q3957',      # town
        'Q532',       # village
        'Q6256',      # country
        'Q3624078',   # sovereign state
        'Q35657',     # state (of country)
        'Q82794',     # geographic region
        'Q23442',     # island
        'Q8502',      # mountain
        'Q4022',      # river
        'Q23397',     # lake
        'Q165',       # sea

        # 인물
        'Q5',         # human

        # 생물
        'Q16521',     # taxon

        # 물건
        'Q39546',     # tool
        'Q2424752',   # product

        # 추상 개념
        'Q35120',     # entity (너무 추상적)
        'Q7184903',   # abstract object
        'Q151885',    # concept
    }

    # 이벤트로 인정되는 P31 타입
    EVENT_INSTANCE_TYPES = {
        'Q178561',    # battle
        'Q198',       # war
        'Q180684',    # military conflict
        'Q188055',    # siege
        'Q131569',    # treaty
        'Q10931',     # revolution
        'Q124734',    # rebellion
        'Q45382',     # coup d'état
        'Q8465',      # civil war
        'Q13418847',  # historical event
        'Q3199915',   # massacre
        'Q2401485',   # expedition
        'Q12772',     # discovery
        'Q209480',    # coronation
        'Q3882219',   # assassination
        'Q1190554',   # occurrence
        'Q192909',    # natural disaster
    }

    def __init__(self, db_config=None, conn=None):
        super().__init__(db_config, conn)
        # 위치 임포터 (연결 공유)
        self.location_importer = LocationImporter(db_config, self.conn)

    def fetch_from_wikidata(self, qid: str) -> Optional[Dict]:
        """Wikidata에서 이벤트 정보 가져오기"""

        # SERVICE wikibase:label을 제대로 사용해서 정확한 라벨 가져오기
        query = f"""
        SELECT ?label ?labelKo ?description
               ?pointInTime ?startTime ?endTime
               ?location ?locationLabel
               ?partOf ?partOfLabel
               ?instanceOf
        WHERE {{
            wd:{qid} rdfs:label ?label. FILTER(LANG(?label) = "en")

            OPTIONAL {{ wd:{qid} rdfs:label ?labelKo. FILTER(LANG(?labelKo) = "ko") }}
            OPTIONAL {{ wd:{qid} schema:description ?description. FILTER(LANG(?description) = "en") }}

            OPTIONAL {{ wd:{qid} wdt:P585 ?pointInTime. }}
            OPTIONAL {{ wd:{qid} wdt:P580 ?startTime. }}
            OPTIONAL {{ wd:{qid} wdt:P582 ?endTime. }}

            OPTIONAL {{ wd:{qid} wdt:P276 ?location. }}
            OPTIONAL {{ wd:{qid} wdt:P361 ?partOf. }}
            OPTIONAL {{ wd:{qid} wdt:P31 ?instanceOf. }}

            SERVICE wikibase:label {{
                bd:serviceParam wikibase:language "en".
                ?location rdfs:label ?locationLabel.
                ?partOf rdfs:label ?partOfLabel.
            }}
        }}
        LIMIT 1
        """

        results = self.sparql_query(query, timeout=30)
        self.stats['fetched'] += 1

        if not results:
            return None

        r = results[0]

        # 시간 파싱 (point_in_time 우선, 없으면 start_time)
        point_in_time = r.get('pointInTime', {}).get('value')
        start_time = r.get('startTime', {}).get('value')
        end_time = r.get('endTime', {}).get('value')

        start_year, start_month, start_day = self.parse_wikidata_time(point_in_time or start_time)
        end_year, end_month, end_day = self.parse_wikidata_time(end_time)

        return {
            'qid': qid,
            'label': r.get('label', {}).get('value', f'Event {qid}'),
            'label_ko': r.get('labelKo', {}).get('value'),
            'description': r.get('description', {}).get('value'),

            'start_year': start_year,
            'start_month': start_month,
            'start_day': start_day,
            'end_year': end_year,
            'end_month': end_month,
            'end_day': end_day,

            'location_qid': self.parse_qid(r.get('location', {}).get('value')),
            'location_label': r.get('locationLabel', {}).get('value'),

            'part_of_qid': self.parse_qid(r.get('partOf', {}).get('value')),
            'part_of_label': r.get('partOfLabel', {}).get('value'),

            'instance_of_qid': self.parse_qid(r.get('instanceOf', {}).get('value')),
        }

    def fetch_participants(self, event_qid: str) -> List[Dict]:
        """이벤트 참여자 가져오기 (P710)"""

        query = f"""
        SELECT ?person ?personLabel ?roleLabel WHERE {{
            wd:{event_qid} wdt:P710 ?person.

            OPTIONAL {{
                ?statement ps:P710 ?person.
                ?statement pq:P3831 ?role.
            }}

            SERVICE wikibase:label {{
                bd:serviceParam wikibase:language "en".
                ?person rdfs:label ?personLabel.
                ?role rdfs:label ?roleLabel.
            }}
        }}
        LIMIT 100
        """

        results = self.sparql_query(query, timeout=30)
        participants = []

        for r in results:
            person_qid = self.parse_qid(r.get('person', {}).get('value'))
            if person_qid:
                participants.append({
                    'qid': person_qid,
                    'label': r.get('personLabel', {}).get('value', ''),
                    'role': r.get('roleLabel', {}).get('value', 'participant'),
                })

        return participants

    def validate(self, entity: Dict) -> bool:
        """이벤트 유효성 검증"""

        # 1. 제외 타입 체크
        instance_qid = entity.get('instance_of_qid')
        if instance_qid in self.EXCLUDED_INSTANCE_TYPES:
            self.stats['skipped'] += 1
            return False

        # 2. 날짜 필수
        if entity.get('start_year') is None:
            self.stats['skipped'] += 1
            return False

        # 3. 인류 역사 범위 (-100000 ~ 2100)
        year = entity.get('start_year')
        if year < -100000 or year > 2100:
            self.stats['skipped'] += 1
            return False

        return True

    def insert(self, entity: Dict) -> Optional[int]:
        """이벤트 저장 (위치 연결 포함!)"""

        if not self.validate(entity):
            return None

        cur = self.conn.cursor()

        # ========================================
        # 핵심: 위치 먼저 생성/조회
        # ========================================
        location_id = None
        if entity.get('location_qid'):
            location_id = self.location_importer.get_or_create(entity['location_qid'])

        # slug 생성
        slug = re.sub(r'[^a-z0-9]+', '-', entity['label'].lower()).strip('-')[:100]

        # slug 중복 체크
        cur.execute("SELECT COUNT(*) FROM events WHERE slug LIKE %s", (slug + '%',))
        slug_count = cur.fetchone()[0]
        if slug_count > 0:
            slug = f"{slug}-{entity['qid'].lower()}"

        try:
            # ========================================
            # 이벤트 저장 (primary_location_id 포함!)
            # ========================================
            cur.execute("""
                INSERT INTO events (
                    title, title_ko, slug, description,
                    date_start, date_start_month, date_start_day,
                    date_end, date_end_month, date_end_day,
                    primary_location_id,
                    wikidata_id,
                    source_reliability, certainty,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s,
                    %s,
                    5, 'confirmed',
                    NOW(), NOW()
                )
                RETURNING id
            """, (
                entity['label'],
                entity.get('label_ko'),
                slug,
                entity.get('description'),
                entity['start_year'],
                entity.get('start_month'),
                entity.get('start_day'),
                entity.get('end_year'),
                entity.get('end_month'),
                entity.get('end_day'),
                location_id,  # ← 핵심!
                entity['qid']
            ))

            event_id = cur.fetchone()[0]
            self.stats['inserted'] += 1

            # ========================================
            # event_locations 브릿지 생성
            # ========================================
            if location_id:
                cur.execute("""
                    INSERT INTO event_locations (event_id, location_id, role)
                    VALUES (%s, %s, 'occurred_at')
                    ON CONFLICT DO NOTHING
                """, (event_id, location_id))

            # ========================================
            # 부모 이벤트 연결 (P361 part_of)
            # ========================================
            if entity.get('part_of_qid'):
                cur.execute("""
                    SELECT id FROM events WHERE wikidata_id = %s
                """, (entity['part_of_qid'],))
                parent = cur.fetchone()

                if parent:
                    cur.execute("""
                        INSERT INTO event_relationships (source_id, target_id, role)
                        VALUES (%s, %s, 'part_of')
                        ON CONFLICT DO NOTHING
                    """, (event_id, parent[0]))

            return event_id

        except Exception as e:
            print(f"  Error inserting event {entity['qid']}: {e}")
            self.conn.rollback()
            self.stats['errors'] += 1
            return None

    def get_or_create(self, qid: str) -> Optional[int]:
        """이벤트 조회 또는 생성"""
        # 기존 레코드 확인
        existing_id = self.find_by_wikidata_id(qid, self.TABLE)

        if existing_id:
            return existing_id

        # 새로 생성
        entity = self.fetch_from_wikidata(qid)
        if not entity:
            return None

        return self.insert(entity)

    def import_with_participants(self, qid: str) -> Optional[int]:
        """이벤트 + 참여자 임포트"""
        event_id = self.get_or_create(qid)

        if not event_id:
            return None

        # 참여자 연결
        participants = self.fetch_participants(qid)
        cur = self.conn.cursor()

        for p in participants:
            # TODO: PersonImporter 구현 후 연결
            # person_id = self.person_importer.get_or_create(p['qid'])
            # if person_id:
            #     cur.execute("""
            #         INSERT INTO event_persons (event_id, person_id, role)
            #         VALUES (%s, %s, %s)
            #         ON CONFLICT DO NOTHING
            #     """, (event_id, person_id, p.get('role', 'participant')))
            pass

        return event_id

    def print_stats(self):
        """통계 출력"""
        super().print_stats()
        print(f"\n=== LocationImporter Stats (nested) ===")
        self.location_importer.print_stats()
