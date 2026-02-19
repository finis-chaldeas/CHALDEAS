"""
이벤트 데이터 페처 - Wikidata에서 이벤트 원시 데이터만 가져옴

처리 로직 없음. 순수 데이터 가져오기만.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from .sparql_client import get_client, SPARQLResult


@dataclass
class RawEvent:
    """원시 이벤트 데이터 - Wikidata에서 가져온 그대로"""
    qid: str
    raw_data: Dict[str, Any]  # SPARQL 결과 그대로


@dataclass
class FetchResult:
    """페치 결과"""
    success: bool
    events: List[RawEvent] = field(default_factory=list)
    error: Optional[str] = None
    total_query_time_ms: int = 0


class EventFetcher:
    """이벤트 데이터 페처"""

    def __init__(self):
        self.client = get_client()

    def fetch_by_qids(self, qids: List[str]) -> FetchResult:
        """QID 목록으로 이벤트 가져오기"""
        if not qids:
            return FetchResult(success=True, events=[])

        events = []
        total_time = 0

        for qid in qids:
            result = self._fetch_single(qid)
            total_time += result.query_time_ms

            if result.success and result.data:
                events.append(RawEvent(
                    qid=qid,
                    raw_data=result.data
                ))

        return FetchResult(
            success=True,
            events=events,
            total_query_time_ms=total_time
        )

    def fetch_events_of_parent(self, parent_qid: str, limit: int = 100) -> FetchResult:
        """상위 이벤트의 하위 이벤트들 가져오기"""
        query = f"""
        SELECT DISTINCT ?event WHERE {{
            ?event wdt:P361 wd:{parent_qid}.
            ?event wdt:P31 ?type.
            FILTER(?type IN (wd:Q178561, wd:Q198, wd:Q188055, wd:Q180684))
        }}
        LIMIT {limit}
        """

        result = self.client.query(query)

        if not result.success:
            return FetchResult(success=False, error=result.error)

        qids = [
            r['event']['value'].split('/')[-1]
            for r in result.data
            if 'event' in r
        ]

        return self.fetch_by_qids(qids)

    def fetch_events_by_type(self, type_qid: str, limit: int = 100) -> FetchResult:
        """타입별 이벤트 가져오기 (예: Q178561 = battle)"""
        query = f"""
        SELECT DISTINCT ?event WHERE {{
            ?event wdt:P31 wd:{type_qid}.
        }}
        LIMIT {limit}
        """

        result = self.client.query(query)

        if not result.success:
            return FetchResult(success=False, error=result.error)

        qids = [
            r['event']['value'].split('/')[-1]
            for r in result.data
            if 'event' in r
        ]

        return self.fetch_by_qids(qids)

    def _fetch_single(self, qid: str) -> SPARQLResult:
        """단일 이벤트 상세 가져오기"""
        query = f"""
        SELECT DISTINCT
            ?label ?labelKo ?description
            ?pointInTime ?startTime ?endTime
            ?location ?locationLabel ?locationCoord
            ?country ?countryLabel ?countryCoord
            ?participant ?participantLabel ?participantRole
            ?partOf ?partOfLabel
            ?instanceOf ?instanceOfLabel
        WHERE {{
            # 기본 정보
            wd:{qid} rdfs:label ?label. FILTER(LANG(?label) = "en")
            OPTIONAL {{ wd:{qid} rdfs:label ?labelKo. FILTER(LANG(?labelKo) = "ko") }}
            OPTIONAL {{ wd:{qid} schema:description ?description. FILTER(LANG(?description) = "en") }}

            # 타입
            OPTIONAL {{
                wd:{qid} wdt:P31 ?instanceOf.
                ?instanceOf rdfs:label ?instanceOfLabel. FILTER(LANG(?instanceOfLabel) = "en")
            }}

            # 시간
            OPTIONAL {{ wd:{qid} wdt:P585 ?pointInTime. }}
            OPTIONAL {{ wd:{qid} wdt:P580 ?startTime. }}
            OPTIONAL {{ wd:{qid} wdt:P582 ?endTime. }}

            # 위치 (P276)
            OPTIONAL {{
                wd:{qid} wdt:P276 ?location.
                OPTIONAL {{ ?location rdfs:label ?locationLabel. FILTER(LANG(?locationLabel) = "en") }}
                OPTIONAL {{ ?location wdt:P625 ?locationCoord. }}
            }}

            # 국가 (P17)
            OPTIONAL {{
                wd:{qid} wdt:P17 ?country.
                OPTIONAL {{ ?country rdfs:label ?countryLabel. FILTER(LANG(?countryLabel) = "en") }}
                OPTIONAL {{ ?country wdt:P625 ?countryCoord. }}
            }}

            # 참여자 (P710)
            OPTIONAL {{
                wd:{qid} wdt:P710 ?participant.
                OPTIONAL {{ ?participant rdfs:label ?participantLabel. FILTER(LANG(?participantLabel) = "en") }}
            }}

            # 상위 (P361)
            OPTIONAL {{
                wd:{qid} wdt:P361 ?partOf.
                ?partOf rdfs:label ?partOfLabel. FILTER(LANG(?partOfLabel) = "en")
            }}
        }}
        LIMIT 100
        """

        return self.client.query_with_retry(query)
