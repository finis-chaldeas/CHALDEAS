"""
Location Importer - Wikidata 위치 임포트
"""

from typing import Dict, Optional
from .base import BaseImporter


class LocationImporter(BaseImporter):
    """위치 임포터"""

    TABLE = 'locations'

    # P31 (instance of) → location type 매핑
    TYPE_MAPPING = {
        'Q515': 'city',           # city
        'Q1549591': 'city',       # big city
        'Q3957': 'city',          # town
        'Q532': 'village',        # village
        'Q6256': 'country',       # country
        'Q3624078': 'country',    # sovereign state
        'Q35657': 'region',       # state (of country)
        'Q82794': 'region',       # geographic region
        'Q1352230': 'region',     # administrative territorial entity
        'Q23442': 'island',       # island
        'Q40080': 'water',        # beach
        'Q8502': 'mountain',      # mountain
        'Q39816': 'mountain',     # valley
        'Q4022': 'water',         # river
        'Q23397': 'water',        # lake
        'Q165': 'water',          # sea
        'Q9430': 'water',         # ocean
        'Q34763': 'water',        # peninsula... wait that's land
        'Q34763': 'landform',     # peninsula
        'Q35509': 'water',        # cave
        'Q811979': 'site',        # architectural structure
        'Q174782': 'site',        # plaza/square
        'Q839954': 'site',        # archaeological site
    }

    def fetch_from_wikidata(self, qid: str) -> Optional[Dict]:
        """Wikidata에서 위치 정보 가져오기"""

        query = f"""
        SELECT ?label ?labelKo ?description ?coord ?instanceOf ?countryLabel WHERE {{
            BIND(wd:{qid} AS ?loc)

            OPTIONAL {{ ?loc rdfs:label ?label. FILTER(LANG(?label) = "en") }}
            OPTIONAL {{ ?loc rdfs:label ?labelKo. FILTER(LANG(?labelKo) = "ko") }}
            OPTIONAL {{ ?loc schema:description ?description. FILTER(LANG(?description) = "en") }}
            OPTIONAL {{ ?loc wdt:P625 ?coord. }}
            OPTIONAL {{ ?loc wdt:P31 ?instanceOf. }}
            OPTIONAL {{ ?loc wdt:P17 ?country. }}

            SERVICE wikibase:label {{
                bd:serviceParam wikibase:language "en".
                ?country rdfs:label ?countryLabel.
            }}
        }}
        LIMIT 1
        """

        results = self.sparql_query(query, timeout=30)
        self.stats['fetched'] += 1

        if not results:
            return None

        r = results[0]

        # 좌표 파싱
        latitude, longitude = self.parse_coordinates(
            r.get('coord', {}).get('value', '')
        )

        # 타입 추론
        instance_qid = self.parse_qid(r.get('instanceOf', {}).get('value', ''))
        location_type = self.TYPE_MAPPING.get(instance_qid, 'place')

        return {
            'qid': qid,
            'label': r.get('label', {}).get('value', f'Location {qid}'),
            'label_ko': r.get('labelKo', {}).get('value'),
            'description': r.get('description', {}).get('value'),
            'latitude': latitude,
            'longitude': longitude,
            'type': location_type,
            'country': r.get('countryLabel', {}).get('value'),
            'instance_of_qid': instance_qid,
        }

    def validate(self, entity: Dict) -> bool:
        """위치 유효성 검증"""
        # 최소한 이름은 있어야 함
        if not entity.get('label'):
            self.stats['skipped'] += 1
            return False

        # 좌표 필수 (DB 스키마 제약)
        if entity.get('latitude') is None or entity.get('longitude') is None:
            # 좌표 없으면 스킵 (TODO: 스키마 변경 후 제거)
            self.stats['skipped'] += 1
            return False

        return True

    def insert(self, entity: Dict) -> Optional[int]:
        """위치 저장"""
        if not self.validate(entity):
            return None

        cur = self.conn.cursor()

        try:
            cur.execute("""
                INSERT INTO locations (
                    name, name_ko, description,
                    latitude, longitude,
                    type, country,
                    wikidata_id,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s,
                    NOW(), NOW()
                )
                RETURNING id
            """, (
                entity['label'],
                entity.get('label_ko'),
                entity.get('description'),
                entity.get('latitude'),
                entity.get('longitude'),
                entity.get('type', 'place'),
                entity.get('country'),
                entity['qid']
            ))

            location_id = cur.fetchone()[0]
            self.stats['inserted'] += 1
            return location_id

        except Exception as e:
            print(f"  Error inserting location {entity['qid']}: {e}")
            self.conn.rollback()
            self.stats['errors'] += 1
            return None

    def update(self, location_id: int, entity: Dict) -> bool:
        """위치 정보 업데이트 (좌표 등 보완)"""
        cur = self.conn.cursor()

        try:
            cur.execute("""
                UPDATE locations SET
                    name = COALESCE(name, %s),
                    name_ko = COALESCE(name_ko, %s),
                    description = COALESCE(description, %s),
                    latitude = COALESCE(latitude, %s),
                    longitude = COALESCE(longitude, %s),
                    type = COALESCE(NULLIF(type, 'unknown'), %s),
                    country = COALESCE(country, %s),
                    updated_at = NOW()
                WHERE id = %s
            """, (
                entity['label'],
                entity.get('label_ko'),
                entity.get('description'),
                entity.get('latitude'),
                entity.get('longitude'),
                entity.get('type', 'place'),
                entity.get('country'),
                location_id
            ))

            self.stats['updated'] += 1
            return True

        except Exception as e:
            print(f"  Error updating location {location_id}: {e}")
            self.conn.rollback()
            self.stats['errors'] += 1
            return False

    def get_or_create(self, qid: str) -> Optional[int]:
        """위치 조회 또는 생성"""
        # 기존 레코드 확인
        existing_id = self.find_by_wikidata_id(qid, self.TABLE)

        if existing_id:
            # 좌표 등 누락 데이터 보완
            cur = self.conn.cursor()
            cur.execute("SELECT latitude FROM locations WHERE id = %s", (existing_id,))
            result = cur.fetchone()

            if result and result[0] is None:
                # 좌표 없으면 Wikidata에서 가져와서 업데이트
                entity = self.fetch_from_wikidata(qid)
                if entity and entity.get('latitude'):
                    self.update(existing_id, entity)

            return existing_id

        # 새로 생성
        entity = self.fetch_from_wikidata(qid)
        if not entity:
            return None

        return self.insert(entity)
