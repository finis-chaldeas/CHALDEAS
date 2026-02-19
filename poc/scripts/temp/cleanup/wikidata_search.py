"""
Wikidata 검색 모듈
Context를 활용한 정확한 엔티티 매칭
"""

import requests
import time
from dataclasses import dataclass
from typing import Optional, List

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
HEADERS = {
    'User-Agent': 'ChaldeasBot/1.0 (https://chaldeas.site; chaldeas@example.com) Python/3.10'
}

@dataclass
class WikidataCandidate:
    qid: str
    name: str
    description: str
    score: float = 0.0

@dataclass
class MatchResult:
    qid: Optional[str]
    name: str
    description: str
    confidence: float
    match_reason: str
    candidates_count: int


def search_wikidata(name: str, limit: int = 10) -> List[WikidataCandidate]:
    """Wikidata에서 이름으로 검색"""
    params = {
        'action': 'wbsearchentities',
        'search': name,
        'language': 'en',
        'limit': limit,
        'format': 'json',
        'type': 'item'
    }

    try:
        resp = requests.get(WIKIDATA_API, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  검색 오류 ({name}): {e}")
        return []

    candidates = []
    for item in data.get('search', []):
        candidates.append(WikidataCandidate(
            qid=item.get('id', ''),
            name=item.get('label', ''),
            description=item.get('description', ''),
            score=0.0
        ))

    return candidates


def calculate_context_score(candidate: WikidataCandidate, context: str) -> float:
    """Context와 description의 유사도 점수 계산"""
    if not candidate.description:
        return 0.1  # description 없으면 매우 낮은 점수

    desc_lower = candidate.description.lower()

    # 일반명사 (given name, surname 등) 페널티
    generic_terms = ['given name', 'surname', 'family name', 'disambiguation',
                     'wikimedia', 'category', 'template', 'list of']
    for term in generic_terms:
        if term in desc_lower:
            return 0.05  # 거의 0점

    if not context:
        return 0.3  # context 없으면 기본 점수

    context_lower = context.lower()

    # 핵심 키워드 추출 (description에서)
    keywords = desc_lower.split()[:10]  # 처음 10개 단어

    # context에서 키워드 매칭
    matches = sum(1 for kw in keywords if len(kw) > 3 and kw in context_lower)

    # 점수 계산 (매칭된 키워드 비율)
    if len(keywords) == 0:
        return 0.3

    score = 0.3 + (matches / len(keywords)) * 0.7  # 0.3 ~ 1.0

    # 특별 보너스: 직업/역할 매칭
    role_keywords = ['king', 'queen', 'emperor', 'pope', 'saint', 'prophet',
                     'philosopher', 'scientist', 'author', 'poet', 'warrior',
                     'general', 'president', 'minister', 'duke', 'count']
    for role in role_keywords:
        if role in desc_lower and role in context_lower:
            score = min(1.0, score + 0.2)
            break

    # 시대 매칭 보너스
    centuries = ['century', 'bc', 'bce', 'ad', 'ce', 'ancient', 'medieval', 'modern']
    for century in centuries:
        if century in desc_lower and century in context_lower:
            score = min(1.0, score + 0.1)
            break

    return min(1.0, score)


def match_entity_to_wikidata(name: str, context: str = "", limit: int = 10) -> MatchResult:
    """
    이름과 context로 Wikidata 매칭

    Returns:
        MatchResult with qid, confidence, etc.
    """
    # 1. Wikidata 검색
    candidates = search_wikidata(name, limit=limit)

    if not candidates:
        return MatchResult(
            qid=None,
            name=name,
            description="",
            confidence=0.0,
            match_reason="no_candidates",
            candidates_count=0
        )

    # 2. 각 후보에 context 점수 계산
    for candidate in candidates:
        candidate.score = calculate_context_score(candidate, context)

    # 3. 점수로 정렬
    candidates.sort(key=lambda x: x.score, reverse=True)
    best = candidates[0]

    # 4. 신뢰도 결정
    # - 첫 번째와 두 번째 점수 차이도 고려
    if len(candidates) > 1:
        gap = best.score - candidates[1].score
        if gap > 0.3:
            confidence = best.score
        else:
            confidence = best.score * 0.8  # 점수 차이 적으면 페널티
    else:
        confidence = best.score

    # 5. 매칭 이유 결정
    if confidence >= 0.8:
        match_reason = "high_confidence"
    elif confidence >= 0.5:
        match_reason = "medium_confidence"
    else:
        match_reason = "low_confidence"

    return MatchResult(
        qid=best.qid if confidence >= 0.3 else None,
        name=best.name,
        description=best.description,
        confidence=confidence,
        match_reason=match_reason,
        candidates_count=len(candidates)
    )


def get_wikidata_details(qid: str) -> dict:
    """QID로 상세 정보 가져오기"""
    params = {
        'action': 'wbgetentities',
        'ids': qid,
        'format': 'json',
        'languages': 'en|ko',
        'props': 'labels|descriptions|claims'
    }

    try:
        resp = requests.get(WIKIDATA_API, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {}

    if 'entities' not in data or qid not in data['entities']:
        return {}

    entity = data['entities'][qid]

    # 이름
    name_en = entity.get('labels', {}).get('en', {}).get('value')
    name_ko = entity.get('labels', {}).get('ko', {}).get('value')

    # 설명
    desc_en = entity.get('descriptions', {}).get('en', {}).get('value')

    # 생년/몰년
    claims = entity.get('claims', {})
    birth_year = None
    death_year = None

    if 'P569' in claims:
        try:
            birth_str = claims['P569'][0]['mainsnak']['datavalue']['value']['time']
            if birth_str[0] == '+':
                birth_year = int(birth_str[1:5])
            else:
                birth_year = -int(birth_str[1:5])
        except:
            pass

    if 'P570' in claims:
        try:
            death_str = claims['P570'][0]['mainsnak']['datavalue']['value']['time']
            if death_str[0] == '+':
                death_year = int(death_str[1:5])
            else:
                death_year = -int(death_str[1:5])
        except:
            pass

    return {
        'qid': qid,
        'name': name_en,
        'name_ko': name_ko,
        'description': desc_en,
        'birth_year': birth_year,
        'death_year': death_year
    }


# 테스트
if __name__ == "__main__":
    print("=== Wikidata 검색 테스트 ===\n")

    test_cases = [
        ("Richard", "King of England who led the Third Crusade"),
        ("Richard", "Playwright known for Richard III"),
        ("Hrothgar", "Danish king in the hall of Heorot"),
        ("Beowulf", "Geatish hero who fought Grendel"),
        ("Napoleon", "French emperor who conquered Europe"),
    ]

    for name, context in test_cases:
        result = match_entity_to_wikidata(name, context)
        print(f"{name} + \"{context[:40]}...\"")
        print(f"  → {result.qid}: {result.name}")
        print(f"     {result.description[:60] if result.description else 'N/A'}...")
        print(f"     confidence: {result.confidence:.2f}, reason: {result.match_reason}")
        print()
        time.sleep(0.5)
