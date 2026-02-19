"""
Guided Entity Extraction - 개선된 추출 파이프라인

1. 책 메타데이터/목차에서 엔티티 예측
2. DB에서 예측된 엔티티 조회
3. Sliding Window (3청크) 컨텍스트로 추출
4. LLM에 힌트 제공하여 정확도 향상
"""

import sys
import json
import re
import httpx
from pathlib import Path
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field
from collections import deque

sys.path.insert(0, str(Path(__file__).parent))
from entity_matcher import EntityMatcher

# Ollama 설정
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1:8b-instruct-q4_0"

@dataclass
class ChunkResult:
    """청크 추출 결과"""
    chunk_index: int
    persons: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    events: List[str] = field(default_factory=list)


def predict_entities_from_toc(toc_text: str) -> Dict[str, List[str]]:
    """목차/서문에서 등장할 엔티티 예측"""

    prompt = f"""Analyze this table of contents/preface and predict which historical figures, places, and events will appear in this book.

TEXT:
{toc_text[:2000]}

Return a JSON object with predicted entities:
{{
    "persons": ["name1", "name2", ...],
    "locations": ["place1", "place2", ...],
    "events": ["event1", "event2", ...]
}}

Focus on historical figures mentioned or implied. Return ONLY the JSON, no explanation."""

    try:
        response = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=60
        )
        result = response.json()["response"]

        # Parse JSON from response
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"Prediction error: {e}")

    return {"persons": [], "locations": [], "events": []}


def lookup_predictions_in_db(predictions: Dict[str, List[str]], matcher: EntityMatcher) -> Dict[str, List[Dict]]:
    """예측된 엔티티를 DB에서 조회"""
    found = {"persons": [], "locations": [], "events": []}

    for name in predictions.get("persons", []):
        result = matcher.match("person", name)
        if result.matched:
            found["persons"].append({
                "name": name,
                "db_name": result.entity_name,
                "id": result.entity_id
            })

    for name in predictions.get("locations", []):
        result = matcher.match("location", name)
        if result.matched:
            found["locations"].append({
                "name": name,
                "db_name": result.entity_name,
                "id": result.entity_id
            })

    return found


def extract_with_hints(chunk_text: str, hints: Set[str], chunk_index: int) -> ChunkResult:
    """힌트를 제공하여 엔티티 추출"""

    hints_str = ", ".join(list(hints)[:30]) if hints else "None"

    prompt = f"""Extract named entities from this historical text.

KNOWN ENTITIES (look for these):
{hints_str}

TEXT:
{chunk_text[:2500]}

Return a JSON object:
{{
    "persons": ["name1", "name2", ...],
    "locations": ["place1", "place2", ...],
    "events": ["event1", "event2", ...]
}}

Include both the known entities if they appear AND any new entities you find.
Return ONLY the JSON, no explanation."""

    try:
        response = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_ctx": 4096}
            },
            timeout=120
        )
        result = response.json()["response"]

        # Parse JSON
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            data = json.loads(json_match.group())
            return ChunkResult(
                chunk_index=chunk_index,
                persons=data.get("persons", []),
                locations=data.get("locations", []),
                events=data.get("events", [])
            )
    except Exception as e:
        print(f"Extraction error (chunk {chunk_index}): {e}")

    return ChunkResult(chunk_index=chunk_index)


def guided_extract_book(book_text: str, chunk_size: int = 2500, max_chunks: int = None) -> Dict:
    """Guided extraction으로 책 전체 추출"""

    matcher = EntityMatcher(fast_mode=True)

    # 1. 목차/서문에서 예측
    print("Step 1: 목차에서 엔티티 예측...")
    toc_section = book_text[:5000]  # 앞부분 (목차 포함)
    predictions = predict_entities_from_toc(toc_section)
    print(f"  예측된 인물: {len(predictions.get('persons', []))}명")
    print(f"  샘플: {predictions.get('persons', [])[:10]}")

    # 2. DB에서 예측된 엔티티 조회
    print("\nStep 2: DB에서 예측 엔티티 조회...")
    found_predictions = lookup_predictions_in_db(predictions, matcher)
    print(f"  DB 매칭: {len(found_predictions['persons'])}명")

    # 예측된 엔티티 이름 세트
    predicted_names = set(predictions.get("persons", []) + predictions.get("locations", []))

    # 3. 청크 분할
    chunks = []
    for i in range(0, len(book_text), chunk_size):
        chunk = book_text[i:i+chunk_size]
        if len(chunk.strip()) > 100:  # 너무 짧은 청크 제외
            chunks.append(chunk)

    if max_chunks:
        chunks = chunks[:max_chunks]

    print(f"\nStep 3: {len(chunks)}개 청크 추출 (sliding window=3)...")

    # 4. Sliding window 추출
    recent_results = deque(maxlen=3)  # 최근 3청크 결과
    all_results = []
    all_persons = set()
    all_locations = set()
    all_events = set()

    for i, chunk in enumerate(chunks):
        # 힌트 = 예측 + 최근 3청크 결과
        recent_entities = set()
        for r in recent_results:
            recent_entities.update(r.persons)
            recent_entities.update(r.locations)

        hints = predicted_names | recent_entities

        # 추출
        result = extract_with_hints(chunk, hints, i)
        all_results.append(result)
        recent_results.append(result)

        # 누적
        all_persons.update(result.persons)
        all_locations.update(result.locations)
        all_events.update(result.events)

        print(f"  Chunk {i+1}/{len(chunks)}: +{len(result.persons)} persons, +{len(result.locations)} locations")

    matcher.close()

    return {
        "predictions": predictions,
        "found_in_db": found_predictions,
        "total_chunks": len(chunks),
        "results": {
            "persons": list(all_persons),
            "locations": list(all_locations),
            "events": list(all_events)
        },
        "stats": {
            "total_persons": len(all_persons),
            "total_locations": len(all_locations),
            "total_events": len(all_events)
        }
    }


if __name__ == "__main__":
    # 테스트: Plutarch's Lives
    from libzim.reader import Archive
    from bs4 import BeautifulSoup

    ZIM_PATH = Path(__file__).parent.parent.parent / "data" / "kiwix" / "gutenberg_en_all.zim"
    archive = Archive(str(ZIM_PATH))

    # Volume 1 로드
    entry = archive.get_entry_by_path("Plutarch's Lives, Volume 1 (of 4).14033")
    html = bytes(entry.get_item().content).decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()

    print("=" * 60)
    print("GUIDED EXTRACTION TEST: Plutarch's Lives Vol.1")
    print("=" * 60)

    # 10청크만 테스트
    result = guided_extract_book(text, chunk_size=2500, max_chunks=10)

    print("\n" + "=" * 60)
    print("결과 요약")
    print("=" * 60)
    print(f"추출된 인물: {result['stats']['total_persons']}명")
    print(f"추출된 장소: {result['stats']['total_locations']}개")
    print(f"추출된 사건: {result['stats']['total_events']}개")
    print(f"\n인물 샘플: {result['results']['persons'][:20]}")
