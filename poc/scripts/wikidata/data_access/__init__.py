# Data Access Layer - Wikidata 데이터 접근
#
# 데이터 소스 추상화:
# - SparqlSource: API 기반 (덤프 전)
# - DumpSource: 로컬 덤프 기반 (덤프 후)
#
# 사용법:
#   from data_access import SparqlSource, DumpSource
#
#   # API 사용
#   source = SparqlSource()
#
#   # 덤프 사용
#   source = DumpSource('/path/to/dump.json.bz2')
#
#   # 동일한 인터페이스
#   for event in source.get_events(limit=100):
#       print(event.name, event.location_qids)

from .base import DataSource, RawEvent, RawLocation, RawPerson
from .sparql_source import SparqlSource
from .dump_source import DumpSource

__all__ = [
    'DataSource',
    'RawEvent',
    'RawLocation',
    'RawPerson',
    'SparqlSource',
    'DumpSource',
]
