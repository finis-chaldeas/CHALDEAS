"""
파서들 - 원시 데이터를 파싱하는 순수 함수들

데이터 접근 없음. 순수 변환만.
"""

from typing import Optional, Tuple, List, Dict, Any


def parse_wikidata_time(time_str: str) -> Optional[int]:
    """Wikidata 시간 문자열 → 연도

    예: "+1066-10-14T00:00:00Z" → 1066
        "-0055-01-01T00:00:00Z" → -55
    """
    if not time_str:
        return None

    try:
        if time_str.startswith('+'):
            time_str = time_str[1:]
            year_str = time_str.split('T')[0].split('-')[0]
            return int(year_str)
        elif time_str.startswith('-'):
            year_str = time_str[1:].split('T')[0].split('-')[0]
            return -int(year_str)
        else:
            year_str = time_str.split('T')[0].split('-')[0]
            return int(year_str)
    except (ValueError, IndexError):
        return None


def parse_coordinate(coord_str: str) -> Tuple[Optional[float], Optional[float]]:
    """좌표 문자열 파싱

    예: "Point(2.74667 39.6331)" → (39.6331, 2.74667)  # (lat, lng)
    """
    if not coord_str:
        return None, None

    try:
        # "Point(lng lat)" 형식
        coord = coord_str.replace('Point(', '').replace(')', '')
        parts = coord.split()
        lng = float(parts[0])
        lat = float(parts[1])
        return lat, lng
    except (ValueError, IndexError):
        return None, None


def extract_qid(uri: str) -> Optional[str]:
    """URI에서 QID 추출

    예: "http://www.wikidata.org/entity/Q12546" → "Q12546"
    """
    if not uri:
        return None

    qid = uri.split('/')[-1]
    return qid if qid.startswith('Q') else None


def extract_value(binding: Dict[str, Any], key: str) -> Optional[str]:
    """SPARQL 바인딩에서 값 추출"""
    if key not in binding:
        return None
    return binding[key].get('value')


def get_claim_values(entity: Dict[str, Any], property_id: str) -> List[str]:
    """덤프 엔티티에서 claim 값들 추출"""
    values = []
    claims = entity.get('claims', {}).get(property_id, [])

    for claim in claims:
        mainsnak = claim.get('mainsnak', {})
        datavalue = mainsnak.get('datavalue', {})
        dtype = datavalue.get('type')

        if dtype == 'wikibase-entityid':
            qid = datavalue.get('value', {}).get('id')
            if qid:
                values.append(qid)
        elif dtype == 'time':
            time_value = datavalue.get('value', {}).get('time')
            if time_value:
                values.append(time_value)
        elif dtype == 'globecoordinate':
            lat = datavalue.get('value', {}).get('latitude')
            lng = datavalue.get('value', {}).get('longitude')
            if lat is not None and lng is not None:
                values.append(f"{lat},{lng}")
        elif dtype == 'string':
            val = datavalue.get('value')
            if val:
                values.append(val)

    return values


def get_label(entity: Dict[str, Any], lang: str = 'en') -> Optional[str]:
    """덤프 엔티티에서 라벨 추출"""
    labels = entity.get('labels', {})
    if lang in labels:
        return labels[lang].get('value')
    return None


def get_description(entity: Dict[str, Any], lang: str = 'en') -> Optional[str]:
    """덤프 엔티티에서 설명 추출"""
    descriptions = entity.get('descriptions', {})
    if lang in descriptions:
        return descriptions[lang].get('value')
    return None
