"""
트랜스포머 - 원시 데이터를 도메인 모델로 변환

데이터 접근 없음. 순수 변환만.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from .parsers import (
    parse_wikidata_time, parse_coordinate, extract_qid, extract_value,
    get_claim_values, get_label, get_description
)


@dataclass
class Location:
    """위치 도메인 모델"""
    qid: str
    name: str
    name_ko: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_type: str = 'unknown'


@dataclass
class Person:
    """인물 도메인 모델"""
    qid: str
    name: str
    name_ko: Optional[str] = None
    role: Optional[str] = None


@dataclass
class Event:
    """이벤트 도메인 모델"""
    qid: str
    name: str
    name_ko: Optional[str] = None
    description: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    event_type: str = 'unknown'
    locations: List[Location] = field(default_factory=list)
    participants: List[Person] = field(default_factory=list)
    part_of_qid: Optional[str] = None
    part_of_name: Optional[str] = None


class SPARQLResultTransformer:
    """SPARQL 결과 → 도메인 모델 변환"""

    def transform_event(self, qid: str, rows: List[Dict[str, Any]]) -> Optional[Event]:
        """SPARQL 결과 행들을 Event로 변환"""
        if not rows:
            return None

        first = rows[0]

        # 기본 정보
        name = extract_value(first, 'label')
        if not name:
            return None

        name_ko = extract_value(first, 'labelKo')
        description = extract_value(first, 'description')

        # 시간
        start_year = (
            parse_wikidata_time(extract_value(first, 'pointInTime')) or
            parse_wikidata_time(extract_value(first, 'startTime'))
        )
        end_year = parse_wikidata_time(extract_value(first, 'endTime'))

        # 타입
        event_type = extract_value(first, 'instanceOfLabel') or 'unknown'

        # 상위 이벤트
        part_of_qid = extract_qid(extract_value(first, 'partOf'))
        part_of_name = extract_value(first, 'partOfLabel')

        # 위치 수집 (중복 제거)
        locations = {}
        for row in rows:
            # P276 location
            loc_qid = extract_qid(extract_value(row, 'location'))
            if loc_qid and loc_qid not in locations:
                lat, lng = parse_coordinate(extract_value(row, 'locationCoord'))
                locations[loc_qid] = Location(
                    qid=loc_qid,
                    name=extract_value(row, 'locationLabel') or loc_qid,
                    latitude=lat,
                    longitude=lng,
                    location_type='place'
                )

            # P17 country (fallback)
            country_qid = extract_qid(extract_value(row, 'country'))
            if country_qid and country_qid not in locations:
                lat, lng = parse_coordinate(extract_value(row, 'countryCoord'))
                locations[country_qid] = Location(
                    qid=country_qid,
                    name=extract_value(row, 'countryLabel') or country_qid,
                    latitude=lat,
                    longitude=lng,
                    location_type='country'
                )

        # 참여자 수집 (중복 제거)
        participants = {}
        for row in rows:
            part_qid = extract_qid(extract_value(row, 'participant'))
            if part_qid and part_qid not in participants:
                participants[part_qid] = Person(
                    qid=part_qid,
                    name=extract_value(row, 'participantLabel') or part_qid,
                    role=extract_value(row, 'participantRole')
                )

        return Event(
            qid=qid,
            name=name,
            name_ko=name_ko,
            description=description,
            start_year=start_year,
            end_year=end_year,
            event_type=event_type,
            locations=list(locations.values()),
            participants=list(participants.values()),
            part_of_qid=part_of_qid,
            part_of_name=part_of_name
        )


class DumpEntityTransformer:
    """덤프 엔티티 → 도메인 모델 변환"""

    # 이벤트 타입 QID → 이름
    EVENT_TYPES = {
        'Q178561': 'battle',
        'Q198': 'war',
        'Q180684': 'conflict',
        'Q188055': 'siege',
        'Q131569': 'treaty',
        'Q10931': 'revolution',
        'Q124734': 'rebellion',
        'Q45382': 'coup',
        'Q8465': 'civil_war',
        'Q13418847': 'historical_event',
        'Q173065': 'crusade',
        'Q192909': 'natural_disaster',
    }

    # 위치 타입 QID → 이름
    LOCATION_TYPES = {
        'Q515': 'city',
        'Q6256': 'country',
        'Q35657': 'state',
        'Q82794': 'region',
        'Q23442': 'island',
        'Q5119': 'capital',
        'Q1549591': 'big_city',
    }

    def transform_event(self, entity: Dict[str, Any]) -> Optional[Event]:
        """덤프 엔티티를 Event로 변환"""
        qid = entity.get('id')
        if not qid or not qid.startswith('Q'):
            return None

        name = get_label(entity, 'en')
        if not name:
            return None

        # P31 (instance of) → 이벤트 타입
        instance_of = get_claim_values(entity, 'P31')
        event_type = 'unknown'
        for type_qid in instance_of:
            if type_qid in self.EVENT_TYPES:
                event_type = self.EVENT_TYPES[type_qid]
                break

        # 시간
        point_in_time = get_claim_values(entity, 'P585')  # point in time
        start_time = get_claim_values(entity, 'P580')     # start time
        end_time = get_claim_values(entity, 'P582')       # end time

        start_year = None
        if point_in_time:
            start_year = parse_wikidata_time(point_in_time[0])
        elif start_time:
            start_year = parse_wikidata_time(start_time[0])

        end_year = None
        if end_time:
            end_year = parse_wikidata_time(end_time[0])

        # 위치 QID들 (나중에 별도 조회 필요)
        location_qids = get_claim_values(entity, 'P276')  # location
        country_qids = get_claim_values(entity, 'P17')    # country

        # 참여자 QID들 (나중에 별도 조회 필요)
        participant_qids = get_claim_values(entity, 'P710')  # participant

        # 상위 이벤트
        part_of = get_claim_values(entity, 'P361')
        part_of_qid = part_of[0] if part_of else None

        return Event(
            qid=qid,
            name=name,
            name_ko=get_label(entity, 'ko'),
            description=get_description(entity, 'en'),
            start_year=start_year,
            end_year=end_year,
            event_type=event_type,
            locations=[Location(qid=q, name='') for q in location_qids + country_qids],
            participants=[Person(qid=q, name='') for q in participant_qids],
            part_of_qid=part_of_qid
        )

    def transform_location(self, entity: Dict[str, Any]) -> Optional[Location]:
        """덤프 엔티티를 Location으로 변환"""
        qid = entity.get('id')
        if not qid or not qid.startswith('Q'):
            return None

        name = get_label(entity, 'en')
        if not name:
            return None

        # P31 → 위치 타입
        instance_of = get_claim_values(entity, 'P31')
        location_type = 'unknown'
        for type_qid in instance_of:
            if type_qid in self.LOCATION_TYPES:
                location_type = self.LOCATION_TYPES[type_qid]
                break

        # P625 좌표
        coords = get_claim_values(entity, 'P625')
        lat, lng = None, None
        if coords:
            try:
                parts = coords[0].split(',')
                lat = float(parts[0])
                lng = float(parts[1])
            except (ValueError, IndexError):
                pass

        return Location(
            qid=qid,
            name=name,
            name_ko=get_label(entity, 'ko'),
            latitude=lat,
            longitude=lng,
            location_type=location_type
        )

    def transform_person(self, entity: Dict[str, Any]) -> Optional[Person]:
        """덤프 엔티티를 Person으로 변환"""
        qid = entity.get('id')
        if not qid or not qid.startswith('Q'):
            return None

        name = get_label(entity, 'en')
        if not name:
            return None

        return Person(
            qid=qid,
            name=name,
            name_ko=get_label(entity, 'ko')
        )
