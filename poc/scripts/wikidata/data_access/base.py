"""
데이터 소스 추상 인터페이스

구현체:
- SparqlSource: Wikidata SPARQL API
- DumpSource: 로컬 덤프 파일
"""

from abc import ABC, abstractmethod
from typing import Iterator, Optional, List
from dataclasses import dataclass


@dataclass
class RawEvent:
    """원시 이벤트 데이터"""
    qid: str
    name: str
    name_ko: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    point_in_time: Optional[str] = None
    location_qids: List[str] = None
    participant_qids: List[str] = None
    part_of_qid: Optional[str] = None

    def __post_init__(self):
        if self.location_qids is None:
            self.location_qids = []
        if self.participant_qids is None:
            self.participant_qids = []


@dataclass
class RawLocation:
    """원시 위치 데이터"""
    qid: str
    name: str
    name_ko: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_type: Optional[str] = None
    country_qid: Optional[str] = None
    parent_qid: Optional[str] = None


@dataclass
class RawPerson:
    """원시 인물 데이터"""
    qid: str
    name: str
    name_ko: Optional[str] = None
    description: Optional[str] = None
    birth_date: Optional[str] = None
    death_date: Optional[str] = None
    birth_place_qid: Optional[str] = None
    occupation_qids: List[str] = None

    def __post_init__(self):
        if self.occupation_qids is None:
            self.occupation_qids = []


class DataSource(ABC):
    """데이터 소스 추상 인터페이스"""

    @abstractmethod
    def get_events(self, limit: int = None, offset: int = 0) -> Iterator[RawEvent]:
        """이벤트 목록 조회"""
        pass

    @abstractmethod
    def get_event(self, qid: str) -> Optional[RawEvent]:
        """단일 이벤트 조회"""
        pass

    @abstractmethod
    def get_location(self, qid: str) -> Optional[RawLocation]:
        """단일 위치 조회"""
        pass

    @abstractmethod
    def get_person(self, qid: str) -> Optional[RawPerson]:
        """단일 인물 조회"""
        pass

    @abstractmethod
    def get_locations(self, limit: int = None) -> Iterator[RawLocation]:
        """위치 목록 조회"""
        pass

    @abstractmethod
    def get_persons(self, limit: int = None) -> Iterator[RawPerson]:
        """인물 목록 조회"""
        pass
