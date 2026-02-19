"""
Wikidata SPARQL client for hierarchy fetching.

Fetches P361 (part of) relationships to build event hierarchy.
"""
import asyncio
import time
from dataclasses import dataclass
from typing import Optional
import httpx


WIKIDATA_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "CHALDEAS/1.0 (https://chaldeas.site)"


@dataclass
class WikidataEvent:
    """Wikidata event with hierarchy info."""
    qid: str
    label: str
    label_ko: Optional[str]
    parent_qid: Optional[str]
    parent_label: Optional[str]
    event_type_qid: Optional[str]
    start_date: Optional[int]
    end_date: Optional[int]


# P31 (instance of) -> aggregate_type mapping
EVENT_TYPE_MAPPING = {
    # Wars
    "Q198": "war",           # war
    "Q178561": "war",        # battle
    "Q188055": "war",        # siege
    "Q645883": "war",        # military operation
    "Q1261499": "war",       # naval battle
    "Q180684": "war",        # conflict

    # Politics/Revolution
    "Q8016240": "revolution",  # political revolution
    "Q124734": "revolution",   # revolution
    "Q7278": "revolution",     # political revolution

    # Movements
    "Q28640": "movement",      # social movement
    "Q49773": "movement",      # social movement

    # Art/Culture
    "Q968159": "artistic_period",   # art movement
    "Q3326717": "artistic_period",  # cultural movement
    "Q2743": "artistic_period",     # art movement

    # Philosophy
    "Q5891": "philosophical_school",      # philosophy
    "Q1387659": "philosophical_school",   # philosophical movement
    "Q33104279": "philosophical_school",  # school of thought

    # Religion
    "Q9174": "religious",      # religion
    "Q1068640": "religious",   # religious movement
    "Q879146": "religious",    # religious event

    # Science
    "Q1297532": "scientific_era",  # scientific revolution

    # Exploration
    "Q2401485": "expedition",  # expedition
    "Q150388": "expedition",   # exploration

    # Dynasty
    "Q164950": "dynasty",      # dynasty
    "Q3024240": "dynasty",     # historical period
}


class WikidataClient:
    """Async Wikidata SPARQL client with rate limiting."""

    def __init__(self, rate_limit: float = 2.0):
        """
        Args:
            rate_limit: Requests per second (Wikidata recommends 1-2)
        """
        self.rate_limit = rate_limit
        self.last_request = 0.0
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": USER_AGENT}
        )

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def _throttle(self):
        """Rate limiting."""
        now = time.time()
        wait = (1.0 / self.rate_limit) - (now - self.last_request)
        if wait > 0:
            await asyncio.sleep(wait)
        self.last_request = time.time()

    async def query_sparql(self, query: str) -> list[dict]:
        """Execute SPARQL query."""
        await self._throttle()

        try:
            response = await self.client.get(
                WIKIDATA_SPARQL_ENDPOINT,
                params={"query": query, "format": "json"}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", {}).get("bindings", [])
        except Exception as e:
            print(f"SPARQL error: {e}")
            return []

    async def get_event_hierarchy(self, qid: str) -> WikidataEvent:
        """Get single event's hierarchy info."""
        query = f"""
        SELECT ?label ?labelKo ?parent ?parentLabel ?eventType ?startDate ?endDate WHERE {{
          OPTIONAL {{ wd:{qid} rdfs:label ?label . FILTER(LANG(?label) = "en") }}
          OPTIONAL {{ wd:{qid} rdfs:label ?labelKo . FILTER(LANG(?labelKo) = "ko") }}
          OPTIONAL {{ wd:{qid} wdt:P361 ?parent . }}
          OPTIONAL {{ ?parent rdfs:label ?parentLabel . FILTER(LANG(?parentLabel) = "en") }}
          OPTIONAL {{ wd:{qid} wdt:P31 ?eventType . }}
          OPTIONAL {{ wd:{qid} wdt:P580 ?startDate . }}
          OPTIONAL {{ wd:{qid} wdt:P582 ?endDate . }}
          OPTIONAL {{ wd:{qid} wdt:P585 ?startDate . }}
        }}
        LIMIT 1
        """

        results = await self.query_sparql(query)
        if not results:
            return WikidataEvent(
                qid=qid, label="", label_ko=None,
                parent_qid=None, parent_label=None,
                event_type_qid=None, start_date=None, end_date=None
            )

        r = results[0]
        return WikidataEvent(
            qid=qid,
            label=self._get_value(r, "label"),
            label_ko=self._get_value(r, "labelKo"),
            parent_qid=self._extract_qid(self._get_value(r, "parent")),
            parent_label=self._get_value(r, "parentLabel"),
            event_type_qid=self._extract_qid(self._get_value(r, "eventType")),
            start_date=self._parse_date(self._get_value(r, "startDate")),
            end_date=self._parse_date(self._get_value(r, "endDate")),
        )

    async def get_events_bulk(self, qids: list[str], batch_size: int = 50) -> list[WikidataEvent]:
        """Bulk fetch events (batched for efficiency)."""
        results = []

        for i in range(0, len(qids), batch_size):
            batch = qids[i:i + batch_size]
            batch_results = await self._query_batch(batch)
            results.extend(batch_results)

            if i + batch_size < len(qids):
                print(f"  Fetched {i + batch_size}/{len(qids)}...")

        return results

    async def _query_batch(self, qids: list[str]) -> list[WikidataEvent]:
        """Batch SPARQL query for multiple QIDs."""
        values = " ".join(f"wd:{qid}" for qid in qids)
        query = f"""
        SELECT ?event ?label ?labelKo ?parent ?parentLabel ?eventType WHERE {{
          VALUES ?event {{ {values} }}
          OPTIONAL {{ ?event rdfs:label ?label . FILTER(LANG(?label) = "en") }}
          OPTIONAL {{ ?event rdfs:label ?labelKo . FILTER(LANG(?labelKo) = "ko") }}
          OPTIONAL {{ ?event wdt:P361 ?parent . }}
          OPTIONAL {{ ?parent rdfs:label ?parentLabel . FILTER(LANG(?parentLabel) = "en") }}
          OPTIONAL {{ ?event wdt:P31 ?eventType . }}
        }}
        """

        rows = await self.query_sparql(query)

        # Group by QID (may have multiple parents)
        by_qid = {}
        for r in rows:
            qid = self._extract_qid(self._get_value(r, "event"))
            if qid and qid not in by_qid:
                by_qid[qid] = r

        # Build results (preserve input order, handle missing)
        results = []
        for qid in qids:
            if qid in by_qid:
                r = by_qid[qid]
                results.append(WikidataEvent(
                    qid=qid,
                    label=self._get_value(r, "label"),
                    label_ko=self._get_value(r, "labelKo"),
                    parent_qid=self._extract_qid(self._get_value(r, "parent")),
                    parent_label=self._get_value(r, "parentLabel"),
                    event_type_qid=self._extract_qid(self._get_value(r, "eventType")),
                    start_date=None,
                    end_date=None,
                ))
            else:
                results.append(WikidataEvent(
                    qid=qid, label="", label_ko=None,
                    parent_qid=None, parent_label=None,
                    event_type_qid=None, start_date=None, end_date=None
                ))

        return results

    async def get_parent_info(self, parent_qid: str) -> WikidataEvent:
        """Get parent event's full info for creating aggregate."""
        query = f"""
        SELECT ?label ?labelKo ?startDate ?endDate ?eventType WHERE {{
          OPTIONAL {{ wd:{parent_qid} rdfs:label ?label . FILTER(LANG(?label) = "en") }}
          OPTIONAL {{ wd:{parent_qid} rdfs:label ?labelKo . FILTER(LANG(?labelKo) = "ko") }}
          OPTIONAL {{ wd:{parent_qid} wdt:P580 ?startDate . }}
          OPTIONAL {{ wd:{parent_qid} wdt:P582 ?endDate . }}
          OPTIONAL {{ wd:{parent_qid} wdt:P585 ?startDate . }}
          OPTIONAL {{ wd:{parent_qid} wdt:P31 ?eventType . }}
        }}
        LIMIT 1
        """

        results = await self.query_sparql(query)
        if not results:
            return WikidataEvent(
                qid=parent_qid, label="", label_ko=None,
                parent_qid=None, parent_label=None,
                event_type_qid=None, start_date=None, end_date=None
            )

        r = results[0]
        return WikidataEvent(
            qid=parent_qid,
            label=self._get_value(r, "label"),
            label_ko=self._get_value(r, "labelKo"),
            parent_qid=None,
            parent_label=None,
            event_type_qid=self._extract_qid(self._get_value(r, "eventType")),
            start_date=self._parse_date(self._get_value(r, "startDate")),
            end_date=self._parse_date(self._get_value(r, "endDate")),
        )

    @staticmethod
    def _get_value(row: dict, key: str) -> Optional[str]:
        """Extract value from SPARQL result row."""
        if key in row and "value" in row[key]:
            return row[key]["value"]
        return None

    @staticmethod
    def _extract_qid(uri: Optional[str]) -> Optional[str]:
        """http://www.wikidata.org/entity/Q12345 -> Q12345"""
        if not uri:
            return None
        if uri.startswith("http://www.wikidata.org/entity/"):
            return uri.split("/")[-1]
        if uri.startswith("Q"):
            return uri
        return None

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[int]:
        """Parse ISO date to year integer."""
        if not date_str:
            return None
        try:
            # +1415-10-25T00:00:00Z -> 1415
            # -0490-01-01T00:00:00Z -> -490
            if date_str.startswith("+"):
                return int(date_str[1:5])
            elif date_str.startswith("-"):
                return -int(date_str[1:5])
            return int(date_str[:4])
        except (ValueError, IndexError):
            return None

    @staticmethod
    def get_aggregate_type(event_type_qid: Optional[str]) -> Optional[str]:
        """Map P31 (instance of) QID to aggregate_type."""
        if not event_type_qid:
            return None
        return EVENT_TYPE_MAPPING.get(event_type_qid)


# Test
async def test_client():
    async with WikidataClient() as client:
        # Test single event
        print("Testing single event (Battle of Agincourt)...")
        event = await client.get_event_hierarchy("Q215380")
        print(f"  Label: {event.label}")
        print(f"  Parent: {event.parent_label} ({event.parent_qid})")
        print(f"  Type: {event.event_type_qid}")

        # Test bulk
        print("\nTesting bulk query...")
        qids = ["Q215380", "Q12544", "Q8740"]  # Agincourt, 100 Years War, WW1
        events = await client.get_events_bulk(qids)
        for e in events:
            print(f"  {e.qid}: {e.label} -> {e.parent_label}")


if __name__ == "__main__":
    asyncio.run(test_client())
