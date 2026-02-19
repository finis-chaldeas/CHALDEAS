"""
Event Classification Checker
- LLM을 사용해 events 테이블의 항목이 진짜 이벤트인지 확인
- 오분류된 항목 (장소, 개념, 인물 등) 식별

Usage:
    python check_event_classification.py --limit=100        # 테스트 (100개)
    python check_event_classification.py --suspicious       # 의심 항목만
    python check_event_classification.py --all              # 전체 검사
    python check_event_classification.py --fix              # 오분류 삭제
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
import sys
import os
from datetime import datetime

# Windows 콘솔 유니코드
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Ollama 설정
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.1:8b-instruct-q4_0')

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}

# 의심 패턴 (이벤트가 아닐 가능성)
SUSPICIOUS_PATTERNS = [
    'section of',
    'geological',
    'landform',
    'mountain',
    'river',
    'lake',
    'region',
    'area of',
    'district',
    'province',
    'city in',
    'town in',
    'village in',
    'island',
    'peninsula',
    'valley',
    'desert',
    'forest',
    'species of',
    'genus of',
    'family of',
    'type of',
    'concept',
    'theory',
    'philosophy',
    'religion',
    'language',
    'ethnic group',
]


def call_ollama(prompt: str) -> str:
    """Ollama API 호출"""
    import requests

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json().get('response', '').strip()
    except Exception as e:
        print(f"Ollama error: {e}")
    return ""


def classify_entity(title: str, description: str) -> dict:
    """LLM으로 엔티티 분류"""

    prompt = f"""Classify this item into one of: EVENT, LOCATION, PERSON, CONCEPT, OTHER

An EVENT is something that happened at a specific time (battles, treaties, disasters, ceremonies, etc.)
A LOCATION is a geographical place (cities, mountains, rivers, regions, buildings, etc.)
A PERSON is a human being
A CONCEPT is an abstract idea, theory, religion, language, etc.
OTHER is anything else (species, objects, etc.)

Title: {title}
Description: {description}

Reply with ONLY one word: EVENT, LOCATION, PERSON, CONCEPT, or OTHER"""

    result = call_ollama(prompt)

    # Parse response
    result_upper = result.upper().strip()
    if 'EVENT' in result_upper:
        return {'type': 'EVENT', 'raw': result}
    elif 'LOCATION' in result_upper:
        return {'type': 'LOCATION', 'raw': result}
    elif 'PERSON' in result_upper:
        return {'type': 'PERSON', 'raw': result}
    elif 'CONCEPT' in result_upper:
        return {'type': 'CONCEPT', 'raw': result}
    else:
        return {'type': 'OTHER', 'raw': result}


def get_suspicious_events(conn, limit: int = None):
    """의심스러운 이벤트 조회"""
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 패턴 기반 필터
    pattern_conditions = " OR ".join([f"description ILIKE '%{p}%'" for p in SUSPICIOUS_PATTERNS])

    query = f"""
        SELECT id, title, description, wikidata_id
        FROM events
        WHERE {pattern_conditions}
        ORDER BY id
    """
    if limit:
        query += f" LIMIT {limit}"

    cur.execute(query)
    return cur.fetchall()


def get_all_events(conn, limit: int = None, offset: int = 0):
    """전체 이벤트 조회"""
    cur = conn.cursor(cursor_factory=RealDictCursor)

    query = "SELECT id, title, description, wikidata_id FROM events ORDER BY id"
    if limit:
        query += f" LIMIT {limit} OFFSET {offset}"

    cur.execute(query)
    return cur.fetchall()


def check_events(suspicious_only: bool = True, limit: int = None, fix: bool = False):
    """이벤트 분류 검사"""
    conn = psycopg2.connect(**DB_CONFIG)

    if suspicious_only:
        events = get_suspicious_events(conn, limit)
        print(f"의심 이벤트 {len(events)}개 검사")
    else:
        events = get_all_events(conn, limit)
        print(f"이벤트 {len(events)}개 검사")

    misclassified = []

    for i, event in enumerate(events):
        if i % 10 == 0:
            print(f"[{i+1}/{len(events)}] 검사 중...", end='\r')

        result = classify_entity(event['title'], event['description'] or '')

        if result['type'] != 'EVENT':
            misclassified.append({
                'id': event['id'],
                'title': event['title'],
                'description': event['description'],
                'wikidata_id': event['wikidata_id'],
                'detected_type': result['type'],
                'llm_response': result['raw']
            })

    print(f"\n\n=== 결과 ===")
    print(f"검사: {len(events)}개")
    print(f"오분류: {len(misclassified)}개")

    if misclassified:
        print(f"\n=== 오분류 목록 ===")
        for item in misclassified[:20]:  # 최대 20개 출력
            print(f"  [{item['id']}] {item['title']}")
            print(f"       → {item['detected_type']}: {item['description'][:60] if item['description'] else 'N/A'}...")

        if len(misclassified) > 20:
            print(f"  ... 외 {len(misclassified) - 20}개")

    # 결과 저장
    output_file = f"misclassified_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(misclassified, f, indent=2, ensure_ascii=False)
    print(f"\n결과 저장: {output_file}")

    # 삭제 옵션
    if fix and misclassified:
        print(f"\n오분류 {len(misclassified)}개 삭제 중...")
        cur = conn.cursor()
        ids = [item['id'] for item in misclassified]
        cur.execute("DELETE FROM events WHERE id = ANY(%s)", (ids,))
        conn.commit()
        print(f"삭제 완료: {cur.rowcount}개")

    conn.close()
    return misclassified


if __name__ == "__main__":
    suspicious_only = "--all" not in sys.argv
    fix = "--fix" in sys.argv

    limit = None
    for arg in sys.argv:
        if arg.startswith("--limit="):
            limit = int(arg.split("=")[1])

    if suspicious_only:
        print("모드: 의심 항목만 검사 (--all 로 전체 검사)")
    else:
        print("모드: 전체 검사")

    if fix:
        print("주의: --fix 옵션으로 오분류 항목 삭제됨")

    check_events(suspicious_only=suspicious_only, limit=limit, fix=fix)
