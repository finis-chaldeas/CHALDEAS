"""
Base Importer - 모든 Wikidata 임포터의 기본 클래스
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

import requests
import psycopg2
from psycopg2.extras import RealDictCursor


WIKIDATA_ENDPOINT = 'https://query.wikidata.org/sparql'

DEFAULT_DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}


class BaseImporter(ABC):
    """모든 임포터의 기본 클래스"""

    def __init__(self, db_config: Dict = None, conn=None):
        """
        Args:
            db_config: DB 연결 설정
            conn: 기존 DB 연결 (공유 시)
        """
        self.db_config = db_config or DEFAULT_DB_CONFIG
        self._conn = conn
        self._owns_connection = conn is None
        self.stats = {
            'fetched': 0,
            'inserted': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }

    @property
    def conn(self):
        """DB 연결 (lazy initialization)"""
        if self._conn is None:
            self._conn = psycopg2.connect(**self.db_config)
        return self._conn

    def close(self):
        """DB 연결 종료 (자체 연결만)"""
        if self._owns_connection and self._conn:
            self._conn.close()
            self._conn = None

    def sparql_query(self, query: str, timeout: int = 60) -> List[Dict]:
        """SPARQL 쿼리 실행"""
        try:
            response = requests.get(
                WIKIDATA_ENDPOINT,
                params={'query': query, 'format': 'json'},
                timeout=timeout,
                headers={'User-Agent': 'CHALDEAS/2.0 (Historical Knowledge System)'}
            )

            if response.status_code == 200:
                return response.json()['results']['bindings']
            elif response.status_code == 429:
                print(f"  Rate limited, waiting 30s...")
                time.sleep(30)
                return self.sparql_query(query, timeout)
            else:
                print(f"  SPARQL error: {response.status_code}")
                self.stats['errors'] += 1
                return []

        except requests.exceptions.Timeout:
            print(f"  SPARQL timeout")
            self.stats['errors'] += 1
            return []
        except Exception as e:
            print(f"  SPARQL error: {e}")
            self.stats['errors'] += 1
            return []

    def parse_qid(self, uri: str) -> Optional[str]:
        """Wikidata URI에서 QID 추출"""
        if not uri:
            return None
        qid = uri.split('/')[-1]
        return qid if qid.startswith('Q') else None

    def parse_coordinates(self, coord_str: str) -> tuple:
        """좌표 문자열 파싱 (Point(lon lat) 형식)"""
        if not coord_str:
            return None, None
        try:
            coord = coord_str.replace('Point(', '').replace(')', '')
            parts = coord.split()
            longitude = float(parts[0])
            latitude = float(parts[1])
            return latitude, longitude
        except:
            return None, None

    def parse_wikidata_time(self, time_str: str) -> tuple:
        """Wikidata 시간 문자열 파싱 → (year, month, day)"""
        if not time_str:
            return None, None, None

        try:
            # Format: +1066-10-14T00:00:00Z or -0055-01-01T00:00:00Z
            if time_str.startswith('+'):
                time_str = time_str[1:]

            date_part = time_str.split('T')[0]

            if date_part.startswith('-'):
                # BCE
                parts = date_part[1:].split('-')
                year = -int(parts[0])
                month = int(parts[1]) if len(parts) > 1 else None
                day = int(parts[2]) if len(parts) > 2 else None
            else:
                parts = date_part.split('-')
                year = int(parts[0])
                month = int(parts[1]) if len(parts) > 1 and parts[1] != '01' else None
                day = int(parts[2]) if len(parts) > 2 and parts[2] != '01' else None

            return year, month, day

        except Exception:
            return None, None, None

    @abstractmethod
    def fetch_from_wikidata(self, qid: str) -> Optional[Dict]:
        """Wikidata에서 엔티티 가져오기"""
        pass

    @abstractmethod
    def validate(self, entity: Dict) -> bool:
        """엔티티 유효성 검증"""
        pass

    @abstractmethod
    def insert(self, entity: Dict) -> Optional[int]:
        """DB에 저장하고 ID 반환"""
        pass

    def find_by_wikidata_id(self, qid: str, table: str) -> Optional[int]:
        """wikidata_id로 기존 레코드 조회"""
        cur = self.conn.cursor()
        cur.execute(f"SELECT id FROM {table} WHERE wikidata_id = %s", (qid,))
        result = cur.fetchone()
        return result[0] if result else None

    def get_or_create(self, qid: str) -> Optional[int]:
        """조회 또는 생성"""
        # 서브클래스에서 table 지정 필요
        raise NotImplementedError("Subclass must implement get_or_create with table name")

    def print_stats(self):
        """통계 출력"""
        print(f"\n=== {self.__class__.__name__} Stats ===")
        for key, value in self.stats.items():
            print(f"  {key}: {value}")
