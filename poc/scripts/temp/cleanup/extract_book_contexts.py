"""
Task 5: 167권 Context 역추적
chunk_results에서 엔티티별 context 추출
"""

import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

RESULTS_DIR = Path("C:/Projects/Chaldeas/poc/data/book_samples/extraction_results")

def sanitize_filename(name: str) -> str:
    """파일명에 사용 불가능한 문자 제거"""
    # Windows에서 금지된 문자: \ / : * ? " < > |
    return re.sub(r'[\\/:*?"<>|]', '_', name)

OUTPUT_DIR = Path("C:/Projects/Chaldeas/poc/data/book_contexts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def extract_contexts_from_book(filepath: Path) -> dict:
    """단일 책에서 엔티티별 context 추출"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    book_id = data.get('book_id', filepath.stem)
    title = data.get('title', book_id)

    # 엔티티별 context 수집
    entity_contexts = {
        'persons': defaultdict(lambda: {'name': '', 'contexts': [], 'mention_count': 0}),
        'locations': defaultdict(lambda: {'name': '', 'contexts': [], 'mention_count': 0}),
        'events': defaultdict(lambda: {'name': '', 'contexts': [], 'mention_count': 0})
    }

    chunk_results = data.get('chunk_results', [])

    for chunk in chunk_results:
        text = chunk.get('text_preview', '')
        chunk_id = chunk.get('chunk_id', 0)

        if not text:
            continue

        for entity_type in ['persons', 'locations', 'events']:
            entities = chunk.get(entity_type, [])
            for entity in entities:
                if not entity or not isinstance(entity, str):
                    continue

                entity_contexts[entity_type][entity]['name'] = entity
                entity_contexts[entity_type][entity]['contexts'].append({
                    'text': text[:500],  # 500자로 제한
                    'chunk_id': chunk_id
                })
                entity_contexts[entity_type][entity]['mention_count'] += 1

    # defaultdict를 일반 dict로 변환
    result = {
        'book_id': book_id,
        'title': title,
        'source_file': filepath.name,
        'extracted_at': datetime.now().isoformat(),
        'stats': {
            'persons': len(entity_contexts['persons']),
            'locations': len(entity_contexts['locations']),
            'events': len(entity_contexts['events']),
            'total_chunks': len(chunk_results)
        },
        'entities': {
            'persons': dict(entity_contexts['persons']),
            'locations': dict(entity_contexts['locations']),
            'events': dict(entity_contexts['events'])
        }
    }

    return result


def extract_all_contexts(limit=None):
    """모든 책에서 context 추출"""
    extraction_files = list(RESULTS_DIR.glob("*_extraction.json"))
    print(f"처리할 책: {len(extraction_files)}권")

    if limit:
        extraction_files = extraction_files[:limit]
        print(f"(limit={limit})")

    total_stats = {
        'books_processed': 0,
        'total_persons': 0,
        'total_locations': 0,
        'total_events': 0,
        'total_contexts': 0
    }

    for i, filepath in enumerate(extraction_files):
        if i % 20 == 0:
            print(f"진행: {i}/{len(extraction_files)}")

        try:
            result = extract_contexts_from_book(filepath)

            # 저장 (파일명 정규화)
            safe_book_id = sanitize_filename(result['book_id'])
            output_file = OUTPUT_DIR / f"{safe_book_id}_contexts.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            # 통계
            total_stats['books_processed'] += 1
            total_stats['total_persons'] += result['stats']['persons']
            total_stats['total_locations'] += result['stats']['locations']
            total_stats['total_events'] += result['stats']['events']

            for entity_type in ['persons', 'locations', 'events']:
                for entity_data in result['entities'][entity_type].values():
                    total_stats['total_contexts'] += len(entity_data['contexts'])

        except Exception as e:
            print(f"  오류 ({filepath.name}): {e}")

    print(f"\n=== 완료 ===")
    print(f"처리한 책: {total_stats['books_processed']}권")
    print(f"추출된 persons: {total_stats['total_persons']:,}")
    print(f"추출된 locations: {total_stats['total_locations']:,}")
    print(f"추출된 events: {total_stats['total_events']:,}")
    print(f"총 context 수: {total_stats['total_contexts']:,}")
    print(f"\n출력 디렉토리: {OUTPUT_DIR}")

    # 통계 저장
    stats_file = OUTPUT_DIR / "_extraction_stats.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            **total_stats
        }, f, indent=2)

    return total_stats


def verify_sample(book_id: str = "Beowulf_981"):
    """샘플 검증"""
    context_file = OUTPUT_DIR / f"{book_id}_contexts.json"

    if not context_file.exists():
        print(f"파일 없음: {context_file}")
        return

    with open(context_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"=== {data['title']} ===")
    print(f"Persons: {data['stats']['persons']}")
    print(f"Locations: {data['stats']['locations']}")
    print(f"Events: {data['stats']['events']}")

    print("\n--- Top 5 Persons (by mentions) ---")
    persons = data['entities']['persons']
    sorted_persons = sorted(persons.items(), key=lambda x: x[1]['mention_count'], reverse=True)

    for name, info in sorted_persons[:5]:
        print(f"\n{name} (mentions: {info['mention_count']})")
        if info['contexts']:
            ctx = info['contexts'][0]['text'][:150]
            print(f"  Context: \"{ctx}...\"")


if __name__ == "__main__":
    import sys

    if "--verify" in sys.argv:
        book_id = sys.argv[sys.argv.index("--verify") + 1] if len(sys.argv) > sys.argv.index("--verify") + 1 else "Beowulf_981"
        verify_sample(book_id)
    else:
        limit = None
        for arg in sys.argv:
            if arg.startswith("--limit="):
                limit = int(arg.split("=")[1])
        extract_all_contexts(limit=limit)
