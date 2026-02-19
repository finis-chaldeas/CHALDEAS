"""
로컬 덤프 파일 데이터 소스 구현
"""

import bz2
import json
from typing import Iterator, Optional, List, Dict, Set
from .base import DataSource, RawEvent, RawLocation, RawPerson


# 이벤트 타입 QID
EVENT_TYPE_QIDS = {
    'Q1190554': 'occurrence',
    'Q1656682': 'event',
    'Q178561': 'battle',
    'Q198': 'war',
    'Q124757': 'riot',
    'Q8065': 'natural_disaster',
    'Q7283': 'terrorism',
    'Q1261499': 'massacre',
    'Q12184': 'pandemic',
    'Q131569': 'treaty',
    'Q11514315': 'historical_period',
    'Q188055': 'siege',
    'Q41397': 'revolution',
    'Q8684': 'assassination',
    'Q56019': 'military_operation',
    'Q180684': 'conflict',
    'Q350604': 'armed_conflict',
    'Q645883': 'military_offensive',
    'Q2334719': 'naval_battle',
    'Q1261499': 'genocide',
    'Q124490': 'mutiny',
    'Q1318941': 'civil_war',
    'Q124757': 'rebellion',
}

# 위치 타입 QID
LOCATION_TYPE_QIDS = {
    'Q515': 'city',
    'Q6256': 'country',
    'Q3024240': 'historical_country',
    'Q82794': 'region',
    'Q23442': 'island',
    'Q8502': 'mountain',
    'Q4022': 'river',
    'Q23397': 'lake',
    'Q5107': 'continent',
}

# 인물 타입 QID
PERSON_TYPE_QIDS = {
    'Q5': 'human',
}


class DumpSource(DataSource):
    """로컬 Wikidata 덤프 데이터 소스"""

    def __init__(self, dump_path: str):
        self.dump_path = dump_path
        self._entity_index: Dict[str, int] = {}  # qid -> file offset (for random access)

    def _iter_entities(self) -> Iterator[dict]:
        """덤프 파일에서 엔티티 순회"""
        with bz2.open(self.dump_path, 'rt', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line in ['[', ']']:
                    continue
                if line.endswith(','):
                    line = line[:-1]
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def _get_label(self, entity: dict, lang: str = 'en') -> Optional[str]:
        """엔티티에서 레이블 추출"""
        labels = entity.get('labels', {})
        if lang in labels:
            return labels[lang].get('value')
        if labels:
            return list(labels.values())[0].get('value')
        return None

    def _get_description(self, entity: dict, lang: str = 'en') -> Optional[str]:
        """엔티티에서 설명 추출"""
        descs = entity.get('descriptions', {})
        if lang in descs:
            return descs[lang].get('value')
        return None

    def _get_claim_values(self, entity: dict, prop: str) -> List[str]:
        """P 속성의 값(QID) 목록 추출"""
        result = []
        claims = entity.get('claims', {})
        if prop not in claims:
            return result

        for claim in claims[prop]:
            mainsnak = claim.get('mainsnak', {})
            datavalue = mainsnak.get('datavalue', {})
            value = datavalue.get('value', {})
            qid = value.get('id')
            if qid:
                result.append(qid)
        return result

    def _get_claim_time(self, entity: dict, prop: str) -> Optional[str]:
        """P 속성의 시간 값 추출"""
        claims = entity.get('claims', {})
        if prop not in claims:
            return None

        for claim in claims[prop]:
            mainsnak = claim.get('mainsnak', {})
            datavalue = mainsnak.get('datavalue', {})
            value = datavalue.get('value', {})
            time = value.get('time')
            if time:
                return time
        return None

    def _get_coordinates(self, entity: dict) -> tuple:
        """P625 좌표 추출"""
        claims = entity.get('claims', {})
        if 'P625' not in claims:
            return None, None

        for claim in claims['P625']:
            mainsnak = claim.get('mainsnak', {})
            datavalue = mainsnak.get('datavalue', {})
            value = datavalue.get('value', {})
            lat = value.get('latitude')
            lng = value.get('longitude')
            if lat is not None and lng is not None:
                return lat, lng
        return None, None

    def _is_instance_of(self, entity: dict, type_qids: Set[str]) -> tuple:
        """P31 instance of 확인"""
        instance_of = self._get_claim_values(entity, 'P31')
        for qid in instance_of:
            if qid in type_qids:
                return True, type_qids.get(qid, 'unknown')
        return False, None

    def get_events(self, limit: int = None, offset: int = 0) -> Iterator[RawEvent]:
        """이벤트 목록 조회"""
        count = 0
        skipped = 0
        type_qids = set(EVENT_TYPE_QIDS.keys())

        for entity in self._iter_entities():
            if entity.get('type') != 'item':
                continue

            is_event, event_type = self._is_instance_of(entity, type_qids)
            if not is_event:
                continue

            if skipped < offset:
                skipped += 1
                continue

            qid = entity.get('id')
            name = self._get_label(entity, 'en')
            if not name:
                continue

            yield RawEvent(
                qid=qid,
                name=name,
                name_ko=self._get_label(entity, 'ko'),
                description=self._get_description(entity, 'en'),
                start_time=self._get_claim_time(entity, 'P580'),
                end_time=self._get_claim_time(entity, 'P582'),
                point_in_time=self._get_claim_time(entity, 'P585'),
                location_qids=self._get_claim_values(entity, 'P276'),
                participant_qids=self._get_claim_values(entity, 'P710'),
                part_of_qid=(self._get_claim_values(entity, 'P361') or [None])[0],
            )

            count += 1
            if limit and count >= limit:
                break

    def get_event(self, qid: str) -> Optional[RawEvent]:
        """단일 이벤트 조회 (전체 스캔 - 비효율적)"""
        for entity in self._iter_entities():
            if entity.get('id') == qid:
                name = self._get_label(entity, 'en')
                if not name:
                    return None
                return RawEvent(
                    qid=qid,
                    name=name,
                    name_ko=self._get_label(entity, 'ko'),
                    description=self._get_description(entity, 'en'),
                    start_time=self._get_claim_time(entity, 'P580'),
                    end_time=self._get_claim_time(entity, 'P582'),
                    point_in_time=self._get_claim_time(entity, 'P585'),
                    location_qids=self._get_claim_values(entity, 'P276'),
                    participant_qids=self._get_claim_values(entity, 'P710'),
                    part_of_qid=(self._get_claim_values(entity, 'P361') or [None])[0],
                )
        return None

    def get_location(self, qid: str) -> Optional[RawLocation]:
        """단일 위치 조회 (전체 스캔 - 비효율적)"""
        for entity in self._iter_entities():
            if entity.get('id') == qid:
                name = self._get_label(entity, 'en')
                if not name:
                    return None
                lat, lng = self._get_coordinates(entity)
                return RawLocation(
                    qid=qid,
                    name=name,
                    name_ko=self._get_label(entity, 'ko'),
                    latitude=lat,
                    longitude=lng,
                    country_qid=(self._get_claim_values(entity, 'P17') or [None])[0],
                    parent_qid=(self._get_claim_values(entity, 'P131') or [None])[0],
                )
        return None

    def get_person(self, qid: str) -> Optional[RawPerson]:
        """단일 인물 조회 (전체 스캔 - 비효율적)"""
        for entity in self._iter_entities():
            if entity.get('id') == qid:
                name = self._get_label(entity, 'en')
                if not name:
                    return None
                return RawPerson(
                    qid=qid,
                    name=name,
                    name_ko=self._get_label(entity, 'ko'),
                    description=self._get_description(entity, 'en'),
                    birth_date=self._get_claim_time(entity, 'P569'),
                    death_date=self._get_claim_time(entity, 'P570'),
                    birth_place_qid=(self._get_claim_values(entity, 'P19') or [None])[0],
                    occupation_qids=self._get_claim_values(entity, 'P106'),
                )
        return None

    def get_locations(self, limit: int = None) -> Iterator[RawLocation]:
        """위치 목록 조회"""
        count = 0
        type_qids = set(LOCATION_TYPE_QIDS.keys())

        for entity in self._iter_entities():
            if entity.get('type') != 'item':
                continue

            is_loc, loc_type = self._is_instance_of(entity, type_qids)
            if not is_loc:
                continue

            qid = entity.get('id')
            name = self._get_label(entity, 'en')
            if not name:
                continue

            lat, lng = self._get_coordinates(entity)

            yield RawLocation(
                qid=qid,
                name=name,
                name_ko=self._get_label(entity, 'ko'),
                latitude=lat,
                longitude=lng,
                location_type=loc_type,
                country_qid=(self._get_claim_values(entity, 'P17') or [None])[0],
                parent_qid=(self._get_claim_values(entity, 'P131') or [None])[0],
            )

            count += 1
            if limit and count >= limit:
                break

    def get_persons(self, limit: int = None) -> Iterator[RawPerson]:
        """인물 목록 조회"""
        count = 0

        for entity in self._iter_entities():
            if entity.get('type') != 'item':
                continue

            is_human, _ = self._is_instance_of(entity, {'Q5'})
            if not is_human:
                continue

            qid = entity.get('id')
            name = self._get_label(entity, 'en')
            if not name:
                continue

            yield RawPerson(
                qid=qid,
                name=name,
                name_ko=self._get_label(entity, 'ko'),
                description=self._get_description(entity, 'en'),
                birth_date=self._get_claim_time(entity, 'P569'),
                death_date=self._get_claim_time(entity, 'P570'),
                birth_place_qid=(self._get_claim_values(entity, 'P19') or [None])[0],
                occupation_qids=self._get_claim_values(entity, 'P106'),
            )

            count += 1
            if limit and count >= limit:
                break
