"""
SPARQL 클라이언트 - Wikidata SPARQL 엔드포인트 접근

순수 데이터 접근만. 처리 로직 없음.
"""

import time
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


WIKIDATA_ENDPOINT = 'https://query.wikidata.org/sparql'
USER_AGENT = 'CHALDEAS/2.0 (https://github.com/finis-chaldeas/chaldeas)'


@dataclass
class SPARQLResult:
    """SPARQL 쿼리 결과"""
    success: bool
    data: List[Dict[str, Any]]
    error: Optional[str] = None
    query_time_ms: int = 0


class SPARQLClient:
    """Wikidata SPARQL 클라이언트"""

    def __init__(self, endpoint: str = WIKIDATA_ENDPOINT, rate_limit: float = 1.0):
        self.endpoint = endpoint
        self.rate_limit = rate_limit  # 초당 최대 요청
        self.last_request_time = 0
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT

    def _wait_for_rate_limit(self):
        """Rate limit 대기"""
        now = time.time()
        elapsed = now - self.last_request_time
        min_interval = 1.0 / self.rate_limit

        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)

        self.last_request_time = time.time()

    def query(self, sparql: str, timeout: int = 60) -> SPARQLResult:
        """SPARQL 쿼리 실행"""
        self._wait_for_rate_limit()

        start = time.time()

        try:
            response = self.session.get(
                self.endpoint,
                params={'query': sparql, 'format': 'json'},
                timeout=timeout
            )

            query_time = int((time.time() - start) * 1000)

            if response.status_code == 200:
                data = response.json()['results']['bindings']
                return SPARQLResult(
                    success=True,
                    data=data,
                    query_time_ms=query_time
                )
            elif response.status_code == 429:
                # Rate limited - 대기 후 재시도
                time.sleep(30)
                return self.query(sparql, timeout)
            else:
                return SPARQLResult(
                    success=False,
                    data=[],
                    error=f"HTTP {response.status_code}: {response.text[:200]}",
                    query_time_ms=query_time
                )

        except requests.Timeout:
            return SPARQLResult(
                success=False,
                data=[],
                error="Query timeout"
            )
        except Exception as e:
            return SPARQLResult(
                success=False,
                data=[],
                error=str(e)
            )

    def query_with_retry(self, sparql: str, max_retries: int = 3, timeout: int = 60) -> SPARQLResult:
        """재시도 포함 쿼리"""
        for i in range(max_retries):
            result = self.query(sparql, timeout)
            if result.success:
                return result
            time.sleep(2 ** i)  # Exponential backoff

        return result


# 싱글톤 인스턴스
_client: Optional[SPARQLClient] = None


def get_client() -> SPARQLClient:
    """싱글톤 클라이언트"""
    global _client
    if _client is None:
        _client = SPARQLClient()
    return _client
