"""
SmartLocationImporter - 지능적 위치 임포트

기능:
1. 좌표 기반 중복 검사 (500m 이내 = 같은 장소)
2. 시대별 명칭 관리 (London/Londinium)
3. 광역 위치 시드 데이터
4. 좌표 상속 (상위 위치에서)

Usage:
    from importers.smart_location_importer import SmartLocationImporter

    importer = SmartLocationImporter(db_url)
    location_id = importer.get_or_create('Q84')  # London
"""

import math
import time
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

import psycopg2
from psycopg2.extras import RealDictCursor

# 데이터 접근 레이어
import sys
sys.path.insert(0, '..')
from data_access.sparql_client import get_client


# 광역 위치 시드 데이터 (수동 정의)
REGION_SEEDS = {
    'Q46': {'name': 'Europe', 'name_ko': '유럽', 'lat': 54.0, 'lng': 25.0, 'type': 'continent'},
    'Q48': {'name': 'Asia', 'name_ko': '아시아', 'lat': 34.0, 'lng': 100.0, 'type': 'continent'},
    'Q15': {'name': 'Africa', 'name_ko': '아프리카', 'lat': 8.0, 'lng': 20.0, 'type': 'continent'},
    'Q49': {'name': 'North America', 'name_ko': '북아메리카', 'lat': 45.0, 'lng': -100.0, 'type': 'continent'},
    'Q18': {'name': 'South America', 'name_ko': '남아메리카', 'lat': -15.0, 'lng': -60.0, 'type': 'continent'},
    'Q55643': {'name': 'Oceania', 'name_ko': '오세아니아', 'lat': -25.0, 'lng': 140.0, 'type': 'continent'},

    # 역사적 광역 지역
    'Q37707': {'name': 'Holy Land', 'name_ko': '성지', 'lat': 31.5, 'lng': 35.0, 'type': 'region'},
    'Q4412': {'name': 'Mediterranean', 'name_ko': '지중해', 'lat': 35.0, 'lng': 18.0, 'type': 'sea'},
    'Q12546': {'name': 'Levant', 'name_ko': '레반트', 'lat': 33.0, 'lng': 36.0, 'type': 'region'},
    'Q11708': {'name': 'Anatolia', 'name_ko': '아나톨리아', 'lat': 39.0, 'lng': 32.0, 'type': 'region'},
    'Q7204': {'name': 'Middle East', 'name_ko': '중동', 'lat': 29.0, 'lng': 41.0, 'type': 'region'},
    'Q27509': {'name': 'Near East', 'name_ko': '근동', 'lat': 35.0, 'lng': 38.0, 'type': 'region'},
    'Q11767': {'name': 'Mesopotamia', 'name_ko': '메소포타미아', 'lat': 33.0, 'lng': 44.0, 'type': 'region'},
    'Q19828': {'name': 'Balkans', 'name_ko': '발칸반도', 'lat': 42.0, 'lng': 21.0, 'type': 'region'},
    'Q12837': {'name': 'Iberian Peninsula', 'name_ko': '이베리아반도', 'lat': 40.0, 'lng': -4.0, 'type': 'region'},
}


@dataclass
class LocationData:
    """위치 데이터"""
    qid: str
    name: str
    name_ko: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_type: str = 'unknown'
    is_region: bool = False
    parent_qid: Optional[str] = None
    valid_from: Optional[int] = None
    valid_until: Optional[int] = None


class SmartLocationImporter:
    """지능적 위치 임포터"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn = psycopg2.connect(db_url)
        self.sparql = get_client()

        # 캐시
        self._qid_cache: Dict[str, int] = {}  # qid → location_id
        self._coord_cache: Dict[str, int] = {}  # "lat,lng" → location_id

    def get_or_create(self, qid: str) -> Optional[int]:
        """위치 가져오거나 생성

        Returns:
            location_id or None if failed
        """
        # 1. 캐시 확인
        if qid in self._qid_cache:
            return self._qid_cache[qid]

        # 2. DB에서 wikidata_id로 검색
        existing = self._find_by_wikidata_id(qid)
        if existing:
            self._qid_cache[qid] = existing
            return existing

        # 3. 시드 데이터 확인
        if qid in REGION_SEEDS:
            seed = REGION_SEEDS[qid]
            location_id = self._create_location(LocationData(
                qid=qid,
                name=seed['name'],
                name_ko=seed.get('name_ko'),
                latitude=seed['lat'],
                longitude=seed['lng'],
                location_type=seed.get('type', 'region'),
                is_region=True
            ))
            self._qid_cache[qid] = location_id
            return location_id

        # 4. Wikidata에서 가져오기
        location_data = self._fetch_from_wikidata(qid)
        if not location_data:
            return None

        # 5. 좌표 기반 중복 검사
        if location_data.latitude and location_data.longitude:
            nearby = self._find_nearby(location_data.latitude, location_data.longitude)
            if nearby:
                # 기존 위치에 명칭만 추가
                self._add_name_to_location(
                    nearby,
                    name=location_data.name,
                    name_ko=location_data.name_ko,
                    wikidata_id=qid,
                    valid_from=location_data.valid_from,
                    valid_until=location_data.valid_until
                )
                self._qid_cache[qid] = nearby
                return nearby

        # 6. 좌표 없으면 상위 위치에서 상속
        if not location_data.latitude and location_data.parent_qid:
            parent_id = self.get_or_create(location_data.parent_qid)
            if parent_id:
                parent_coords = self._get_coords(parent_id)
                if parent_coords:
                    location_data.latitude = parent_coords[0]
                    location_data.longitude = parent_coords[1]

        # 7. 새 위치 생성
        if location_data.latitude is None:
            # 좌표 없으면 생성 불가
            print(f"  [!] No coordinates for {qid}: {location_data.name}")
            return None

        location_id = self._create_location(location_data)
        self._qid_cache[qid] = location_id
        return location_id

    def _find_by_wikidata_id(self, qid: str) -> Optional[int]:
        """wikidata_id로 위치 검색"""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM locations WHERE wikidata_id = %s",
                (qid,)
            )
            row = cur.fetchone()
            return row[0] if row else None

    def _find_nearby(self, lat: float, lng: float, threshold_km: float = 0.5) -> Optional[int]:
        """좌표 근처의 기존 위치 검색

        threshold_km: 같은 장소로 판단할 거리 (기본 500m)
        """
        # 간단한 거리 계산 (위도 1도 ≈ 111km)
        lat_range = threshold_km / 111.0
        lng_range = threshold_km / (111.0 * math.cos(math.radians(lat)))

        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, latitude, longitude
                FROM locations
                WHERE latitude BETWEEN %s AND %s
                  AND longitude BETWEEN %s AND %s
                LIMIT 1
            """, (lat - lat_range, lat + lat_range, lng - lng_range, lng + lng_range))
            row = cur.fetchone()
            return row[0] if row else None

    def _get_coords(self, location_id: int) -> Optional[tuple]:
        """위치 좌표 가져오기"""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT latitude, longitude FROM locations WHERE id = %s",
                (location_id,)
            )
            row = cur.fetchone()
            if row and row[0] and row[1]:
                return (float(row[0]), float(row[1]))
            return None

    def _fetch_from_wikidata(self, qid: str) -> Optional[LocationData]:
        """Wikidata에서 위치 정보 가져오기"""
        query = f"""
        SELECT ?label ?labelKo ?coord ?type ?typeLabel ?country ?countryLabel
        WHERE {{
            wd:{qid} rdfs:label ?label. FILTER(LANG(?label) = "en")
            OPTIONAL {{ wd:{qid} rdfs:label ?labelKo. FILTER(LANG(?labelKo) = "ko") }}
            OPTIONAL {{ wd:{qid} wdt:P625 ?coord. }}
            OPTIONAL {{
                wd:{qid} wdt:P31 ?type.
                ?type rdfs:label ?typeLabel. FILTER(LANG(?typeLabel) = "en")
            }}
            OPTIONAL {{
                wd:{qid} wdt:P17 ?country.
                ?country rdfs:label ?countryLabel. FILTER(LANG(?countryLabel) = "en")
            }}
        }}
        LIMIT 10
        """

        result = self.sparql.query(query)
        if not result.success or not result.data:
            return None

        row = result.data[0]

        # 이름
        name = row.get('label', {}).get('value')
        if not name:
            return None

        name_ko = row.get('labelKo', {}).get('value')

        # 좌표
        lat, lng = None, None
        coord_str = row.get('coord', {}).get('value', '')
        if coord_str:
            try:
                # "Point(lng lat)" 형식
                coord = coord_str.replace('Point(', '').replace(')', '')
                parts = coord.split()
                lng = float(parts[0])
                lat = float(parts[1])
            except:
                pass

        # 타입
        location_type = row.get('typeLabel', {}).get('value', 'unknown')
        if location_type:
            location_type = location_type.lower().replace(' ', '_')

        # 상위 위치 (국가)
        parent_qid = None
        country_uri = row.get('country', {}).get('value', '')
        if country_uri:
            parent_qid = country_uri.split('/')[-1]

        return LocationData(
            qid=qid,
            name=name,
            name_ko=name_ko,
            latitude=lat,
            longitude=lng,
            location_type=location_type,
            parent_qid=parent_qid
        )

    def _create_location(self, data: LocationData) -> int:
        """새 위치 생성"""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO locations (
                    name, name_ko, latitude, longitude, type,
                    wikidata_id, is_region, coords_source,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id
            """, (
                data.name,
                data.name_ko,
                data.latitude,
                data.longitude,
                data.location_type or 'unknown',
                data.qid,
                data.is_region,
                'exact' if data.latitude else 'inherited'
            ))
            location_id = cur.fetchone()[0]

            # location_names에도 추가
            cur.execute("""
                INSERT INTO location_names (
                    location_id, name, name_ko, language, is_primary,
                    valid_from, valid_until, wikidata_id, source
                )
                VALUES (%s, %s, %s, 'en', TRUE, %s, %s, %s, 'wikidata')
            """, (
                location_id,
                data.name,
                data.name_ko,
                data.valid_from,
                data.valid_until,
                data.qid
            ))

            self.conn.commit()
            return location_id

    def _add_name_to_location(
        self,
        location_id: int,
        name: str,
        name_ko: Optional[str] = None,
        wikidata_id: Optional[str] = None,
        valid_from: Optional[int] = None,
        valid_until: Optional[int] = None
    ):
        """기존 위치에 명칭 추가"""
        with self.conn.cursor() as cur:
            # 이미 있는지 확인
            cur.execute("""
                SELECT id FROM location_names
                WHERE location_id = %s AND name = %s
            """, (location_id, name))

            if cur.fetchone():
                return  # 이미 존재

            cur.execute("""
                INSERT INTO location_names (
                    location_id, name, name_ko, language, is_primary,
                    valid_from, valid_until, wikidata_id, source
                )
                VALUES (%s, %s, %s, 'en', FALSE, %s, %s, %s, 'wikidata')
            """, (
                location_id,
                name,
                name_ko,
                valid_from,
                valid_until,
                wikidata_id
            ))
            self.conn.commit()

    def seed_regions(self):
        """광역 위치 시드 데이터 삽입"""
        print("광역 위치 시드 데이터 삽입...")

        for qid, data in REGION_SEEDS.items():
            existing = self._find_by_wikidata_id(qid)
            if existing:
                print(f"  [skip] {qid}: {data['name']} (already exists)")
                continue

            self._create_location(LocationData(
                qid=qid,
                name=data['name'],
                name_ko=data.get('name_ko'),
                latitude=data['lat'],
                longitude=data['lng'],
                location_type=data.get('type', 'region'),
                is_region=True
            ))
            print(f"  [created] {qid}: {data['name']}")

        print(f"완료: {len(REGION_SEEDS)}개 광역 위치")

    def close(self):
        """연결 종료"""
        self.conn.close()


# 테스트
if __name__ == '__main__':
    import os

    db_url = os.environ.get('DATABASE_URL', 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas')

    importer = SmartLocationImporter(db_url)

    # 시드 데이터 삽입
    # importer.seed_regions()

    # 테스트: 런던
    print("\n테스트: Q84 (London)")
    london_id = importer.get_or_create('Q84')
    print(f"  London ID: {london_id}")

    # 테스트: 예루살렘
    print("\n테스트: Q1218 (Jerusalem)")
    jerusalem_id = importer.get_or_create('Q1218')
    print(f"  Jerusalem ID: {jerusalem_id}")

    importer.close()
