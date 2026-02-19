"""
SPARQL API 데이터 소스 구현
"""

from typing import Iterator, Optional, List, Dict, Any
from .base import DataSource, RawEvent, RawLocation, RawPerson
from .sparql_client import get_client


class SparqlSource(DataSource):
    """Wikidata SPARQL API 데이터 소스"""

    # 역사적 이벤트 타입 (solar eclipse 등 제외)
    HISTORICAL_EVENT_TYPES = [
        'Q198',      # war
        'Q178561',   # battle
        'Q131569',   # treaty
        'Q188055',   # siege
        'Q124757',   # riot/rebellion
        'Q8065',     # natural disaster
        'Q1261499',  # massacre
        'Q41397',    # revolution
        'Q645883',   # military offensive
        'Q180684',   # conflict
        'Q1318941',  # civil war
        'Q7283',     # terrorism
        'Q8684',     # assassination
        'Q350604',   # armed conflict
        'Q2334719',  # naval battle
    ]

    def __init__(self):
        self.client = get_client()
        self._location_cache: Dict[str, RawLocation] = {}
        self._person_cache: Dict[str, RawPerson] = {}

    def get_events(self, limit: int = None, offset: int = 0, event_types: list = None) -> Iterator[RawEvent]:
        """이벤트 목록 조회 (SPARQL) - 위치/인물 포함

        Args:
            event_types: 이벤트 타입 QID 목록. None이면 역사적 이벤트만
        """
        limit_clause = f"LIMIT {limit * 5 if limit else 50000}"  # 중복 row 고려
        offset_clause = f"OFFSET {offset}" if offset > 0 else ""

        # 이벤트 타입 필터
        types = event_types or self.HISTORICAL_EVENT_TYPES
        type_values = " ".join(f"wd:{t}" for t in types)

        # 한 번의 쿼리로 이벤트+위치+인물 모두 가져옴
        query = f"""
        SELECT ?event ?eventLabel ?eventLabelKo ?desc
               ?startTime ?endTime ?pointInTime ?partOf
               ?location ?country ?participant
        WHERE {{
          VALUES ?eventType {{ {type_values} }}
          ?event wdt:P31 ?eventType.
          ?event rdfs:label ?eventLabel. FILTER(LANG(?eventLabel) = "en")

          OPTIONAL {{ ?event rdfs:label ?eventLabelKo. FILTER(LANG(?eventLabelKo) = "ko") }}
          OPTIONAL {{ ?event schema:description ?desc. FILTER(LANG(?desc) = "en") }}
          OPTIONAL {{ ?event wdt:P580 ?startTime. }}
          OPTIONAL {{ ?event wdt:P582 ?endTime. }}
          OPTIONAL {{ ?event wdt:P585 ?pointInTime. }}
          OPTIONAL {{ ?event wdt:P361 ?partOf. }}
          OPTIONAL {{ ?event wdt:P276 ?location. }}
          OPTIONAL {{ ?event wdt:P17 ?country. }}
          OPTIONAL {{ ?event wdt:P710 ?participant. }}
        }}
        {limit_clause}
        {offset_clause}
        """

        result = self.client.query(query)
        if not result.success:
            return

        # 이벤트별로 데이터 집계
        event_data = {}

        for row in result.data:
            qid = row.get('event', {}).get('value', '').split('/')[-1]
            if not qid:
                continue

            if qid not in event_data:
                event_data[qid] = {
                    'name': row.get('eventLabel', {}).get('value'),
                    'name_ko': row.get('eventLabelKo', {}).get('value'),
                    'description': row.get('desc', {}).get('value'),
                    'start_time': row.get('startTime', {}).get('value'),
                    'end_time': row.get('endTime', {}).get('value'),
                    'point_in_time': row.get('pointInTime', {}).get('value'),
                    'part_of_qid': row.get('partOf', {}).get('value', '').split('/')[-1] or None,
                    'locations': set(),
                    'participants': set(),
                }

            # 위치 추가 (P276 location)
            loc = row.get('location', {}).get('value', '').split('/')[-1]
            if loc:
                event_data[qid]['locations'].add(loc)

            # 국가 추가 (P17 country - fallback)
            country = row.get('country', {}).get('value', '').split('/')[-1]
            if country:
                event_data[qid]['locations'].add(country)

            # 인물 추가
            part = row.get('participant', {}).get('value', '').split('/')[-1]
            if part:
                event_data[qid]['participants'].add(part)

        # limit 적용하여 yield
        count = 0
        for qid, data in event_data.items():
            if limit and count >= limit:
                break

            yield RawEvent(
                qid=qid,
                name=data['name'],
                name_ko=data['name_ko'],
                description=data['description'],
                start_time=data['start_time'],
                end_time=data['end_time'],
                point_in_time=data['point_in_time'],
                part_of_qid=data['part_of_qid'],
                location_qids=list(data['locations']),
                participant_qids=list(data['participants']),
            )
            count += 1

    def _batch_get_event_locations(self, event_qids: List[str]) -> Dict[str, List[str]]:
        """이벤트들의 위치 일괄 조회"""
        if not event_qids:
            return {}

        values = " ".join(f"wd:{qid}" for qid in event_qids[:100])
        query = f"""
        SELECT ?event ?location WHERE {{
          VALUES ?event {{ {values} }}
          ?event wdt:P276 ?location.
        }}
        """

        result = self.client.query(query)
        if not result.success:
            return {}

        locations = {}
        for row in result.data:
            event_qid = row.get('event', {}).get('value', '').split('/')[-1]
            loc_qid = row.get('location', {}).get('value', '').split('/')[-1]
            if event_qid and loc_qid:
                if event_qid not in locations:
                    locations[event_qid] = []
                locations[event_qid].append(loc_qid)

        return locations

    def _batch_get_event_participants(self, event_qids: List[str]) -> Dict[str, List[str]]:
        """이벤트들의 참가자 일괄 조회"""
        if not event_qids:
            return {}

        values = " ".join(f"wd:{qid}" for qid in event_qids[:100])
        query = f"""
        SELECT ?event ?participant WHERE {{
          VALUES ?event {{ {values} }}
          ?event wdt:P710 ?participant.
        }}
        """

        result = self.client.query(query)
        if not result.success:
            return {}

        participants = {}
        for row in result.data:
            event_qid = row.get('event', {}).get('value', '').split('/')[-1]
            part_qid = row.get('participant', {}).get('value', '').split('/')[-1]
            if event_qid and part_qid:
                if event_qid not in participants:
                    participants[event_qid] = []
                participants[event_qid].append(part_qid)

        return participants

    def get_event(self, qid: str) -> Optional[RawEvent]:
        """단일 이벤트 조회"""
        query = f"""
        SELECT ?eventLabel ?eventLabelKo ?desc
               ?startTime ?endTime ?pointInTime ?partOf
               ?location ?participant
        WHERE {{
          OPTIONAL {{ wd:{qid} rdfs:label ?eventLabel. FILTER(LANG(?eventLabel) = "en") }}
          OPTIONAL {{ wd:{qid} rdfs:label ?eventLabelKo. FILTER(LANG(?eventLabelKo) = "ko") }}
          OPTIONAL {{ wd:{qid} schema:description ?desc. FILTER(LANG(?desc) = "en") }}
          OPTIONAL {{ wd:{qid} wdt:P580 ?startTime. }}
          OPTIONAL {{ wd:{qid} wdt:P582 ?endTime. }}
          OPTIONAL {{ wd:{qid} wdt:P585 ?pointInTime. }}
          OPTIONAL {{ wd:{qid} wdt:P361 ?partOf. }}
          OPTIONAL {{ wd:{qid} wdt:P276 ?location. }}
          OPTIONAL {{ wd:{qid} wdt:P710 ?participant. }}
        }}
        """

        result = self.client.query(query)
        if not result.success or not result.data:
            return None

        locations = set()
        participants = set()
        data = None

        for row in result.data:
            if data is None:
                data = {
                    'name': row.get('eventLabel', {}).get('value'),
                    'name_ko': row.get('eventLabelKo', {}).get('value'),
                    'description': row.get('desc', {}).get('value'),
                    'start_time': row.get('startTime', {}).get('value'),
                    'end_time': row.get('endTime', {}).get('value'),
                    'point_in_time': row.get('pointInTime', {}).get('value'),
                    'part_of_qid': row.get('partOf', {}).get('value', '').split('/')[-1] or None,
                }

            loc = row.get('location', {}).get('value', '').split('/')[-1]
            if loc:
                locations.add(loc)

            part = row.get('participant', {}).get('value', '').split('/')[-1]
            if part:
                participants.add(part)

        if not data or not data['name']:
            return None

        return RawEvent(
            qid=qid,
            name=data['name'],
            name_ko=data['name_ko'],
            description=data['description'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            point_in_time=data['point_in_time'],
            part_of_qid=data['part_of_qid'],
            location_qids=list(locations),
            participant_qids=list(participants),
        )

    def get_location(self, qid: str) -> Optional[RawLocation]:
        """단일 위치 조회"""
        if qid in self._location_cache:
            return self._location_cache[qid]

        query = f"""
        SELECT ?label ?labelKo ?coord ?type ?country ?parent
        WHERE {{
          OPTIONAL {{ wd:{qid} rdfs:label ?label. FILTER(LANG(?label) = "en") }}
          OPTIONAL {{ wd:{qid} rdfs:label ?labelKo. FILTER(LANG(?labelKo) = "ko") }}
          OPTIONAL {{ wd:{qid} wdt:P625 ?coord. }}
          OPTIONAL {{ wd:{qid} wdt:P31 ?type. }}
          OPTIONAL {{ wd:{qid} wdt:P17 ?country. }}
          OPTIONAL {{ wd:{qid} wdt:P131 ?parent. }}
        }}
        LIMIT 1
        """

        result = self.client.query(query)
        if not result.success or not result.data:
            return None

        row = result.data[0]
        name = row.get('label', {}).get('value')
        if not name:
            return None

        lat, lng = None, None
        coord_str = row.get('coord', {}).get('value', '')
        if coord_str:
            try:
                coord = coord_str.replace('Point(', '').replace(')', '')
                parts = coord.split()
                lng = float(parts[0])
                lat = float(parts[1])
            except:
                pass

        location = RawLocation(
            qid=qid,
            name=name,
            name_ko=row.get('labelKo', {}).get('value'),
            latitude=lat,
            longitude=lng,
            location_type=row.get('type', {}).get('value', '').split('/')[-1] or None,
            country_qid=row.get('country', {}).get('value', '').split('/')[-1] or None,
            parent_qid=row.get('parent', {}).get('value', '').split('/')[-1] or None,
        )

        self._location_cache[qid] = location
        return location

    def get_person(self, qid: str) -> Optional[RawPerson]:
        """단일 인물 조회"""
        if qid in self._person_cache:
            return self._person_cache[qid]

        query = f"""
        SELECT ?label ?labelKo ?desc ?birthDate ?deathDate ?birthPlace ?occupation
        WHERE {{
          OPTIONAL {{ wd:{qid} rdfs:label ?label. FILTER(LANG(?label) = "en") }}
          OPTIONAL {{ wd:{qid} rdfs:label ?labelKo. FILTER(LANG(?labelKo) = "ko") }}
          OPTIONAL {{ wd:{qid} schema:description ?desc. FILTER(LANG(?desc) = "en") }}
          OPTIONAL {{ wd:{qid} wdt:P569 ?birthDate. }}
          OPTIONAL {{ wd:{qid} wdt:P570 ?deathDate. }}
          OPTIONAL {{ wd:{qid} wdt:P19 ?birthPlace. }}
          OPTIONAL {{ wd:{qid} wdt:P106 ?occupation. }}
        }}
        """

        result = self.client.query(query)
        if not result.success or not result.data:
            return None

        occupations = set()
        data = None

        for row in result.data:
            if data is None:
                name = row.get('label', {}).get('value')
                if not name:
                    return None
                data = {
                    'name': name,
                    'name_ko': row.get('labelKo', {}).get('value'),
                    'description': row.get('desc', {}).get('value'),
                    'birth_date': row.get('birthDate', {}).get('value'),
                    'death_date': row.get('deathDate', {}).get('value'),
                    'birth_place_qid': row.get('birthPlace', {}).get('value', '').split('/')[-1] or None,
                }

            occ = row.get('occupation', {}).get('value', '').split('/')[-1]
            if occ:
                occupations.add(occ)

        if not data:
            return None

        person = RawPerson(
            qid=qid,
            name=data['name'],
            name_ko=data['name_ko'],
            description=data['description'],
            birth_date=data['birth_date'],
            death_date=data['death_date'],
            birth_place_qid=data['birth_place_qid'],
            occupation_qids=list(occupations),
        )

        self._person_cache[qid] = person
        return person

    def get_locations(self, limit: int = None) -> Iterator[RawLocation]:
        """위치 목록 조회 - 이벤트에서 참조된 위치들"""
        # 이벤트의 위치들을 수집
        limit_clause = f"LIMIT {limit}" if limit else "LIMIT 10000"

        query = f"""
        SELECT DISTINCT ?location ?locationLabel ?locationLabelKo ?coord ?type ?country
        WHERE {{
          ?event wdt:P31/wdt:P279* wd:Q1190554.
          ?event wdt:P276 ?location.
          ?location rdfs:label ?locationLabel. FILTER(LANG(?locationLabel) = "en")
          OPTIONAL {{ ?location rdfs:label ?locationLabelKo. FILTER(LANG(?locationLabelKo) = "ko") }}
          OPTIONAL {{ ?location wdt:P625 ?coord. }}
          OPTIONAL {{ ?location wdt:P31 ?type. }}
          OPTIONAL {{ ?location wdt:P17 ?country. }}
        }}
        {limit_clause}
        """

        result = self.client.query(query)
        if not result.success:
            return

        seen = set()
        for row in result.data:
            qid = row.get('location', {}).get('value', '').split('/')[-1]
            if not qid or qid in seen:
                continue
            seen.add(qid)

            lat, lng = None, None
            coord_str = row.get('coord', {}).get('value', '')
            if coord_str:
                try:
                    coord = coord_str.replace('Point(', '').replace(')', '')
                    parts = coord.split()
                    lng = float(parts[0])
                    lat = float(parts[1])
                except:
                    pass

            yield RawLocation(
                qid=qid,
                name=row.get('locationLabel', {}).get('value'),
                name_ko=row.get('locationLabelKo', {}).get('value'),
                latitude=lat,
                longitude=lng,
                location_type=row.get('type', {}).get('value', '').split('/')[-1] or None,
                country_qid=row.get('country', {}).get('value', '').split('/')[-1] or None,
            )

    def get_persons(self, limit: int = None) -> Iterator[RawPerson]:
        """인물 목록 조회 - 이벤트에서 참조된 인물들"""
        limit_clause = f"LIMIT {limit}" if limit else "LIMIT 10000"

        query = f"""
        SELECT DISTINCT ?person ?personLabel ?personLabelKo ?desc ?birthDate ?deathDate
        WHERE {{
          ?event wdt:P31/wdt:P279* wd:Q1190554.
          ?event wdt:P710 ?person.
          ?person rdfs:label ?personLabel. FILTER(LANG(?personLabel) = "en")
          OPTIONAL {{ ?person rdfs:label ?personLabelKo. FILTER(LANG(?personLabelKo) = "ko") }}
          OPTIONAL {{ ?person schema:description ?desc. FILTER(LANG(?desc) = "en") }}
          OPTIONAL {{ ?person wdt:P569 ?birthDate. }}
          OPTIONAL {{ ?person wdt:P570 ?deathDate. }}
        }}
        {limit_clause}
        """

        result = self.client.query(query)
        if not result.success:
            return

        seen = set()
        for row in result.data:
            qid = row.get('person', {}).get('value', '').split('/')[-1]
            if not qid or qid in seen:
                continue
            seen.add(qid)

            yield RawPerson(
                qid=qid,
                name=row.get('personLabel', {}).get('value'),
                name_ko=row.get('personLabelKo', {}).get('value'),
                description=row.get('desc', {}).get('value'),
                birth_date=row.get('birthDate', {}).get('value'),
                death_date=row.get('deathDate', {}).get('value'),
            )
