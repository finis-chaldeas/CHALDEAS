"""
Step 2.5: 다국어 보강 (Fast 버전)

qid_wiki_map_multilang.json을 활용하여 빠르게 보강.
700GB Wikidata 스캔 불필요.

Usage:
    python 02b_enrich_multilang_fast.py [--resume]
"""

import json
import sys
import time
import argparse
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from config import WIKIDATA_EXTRACTED, OUTPUT_DIR, CHECKPOINT_DIR

# 파일 경로
MULTILANG_MAP = OUTPUT_DIR / "qid_wiki_map_multilang.json"
ENRICHED_OUTPUT = OUTPUT_DIR / "wikidata_full_multilang.jsonl"
CHECKPOINT_FILE = CHECKPOINT_DIR / "multilang_enrich_checkpoint.json"

LOG_INTERVAL = 100000


def load_multilang_map() -> dict:
    """다국어 매핑 로드 - 역매핑하여 QID → {ko, ja} 생성"""
    print(f"Loading multilang map from {MULTILANG_MAP}...")
    start = time.time()

    with open(MULTILANG_MAP, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # by_title_ko, by_title_ja를 역매핑
    # {한국어_제목: QID} → {QID: 한국어_제목}
    by_title_ko = data.get('by_title_ko', {})
    by_title_ja = data.get('by_title_ja', {})

    print(f"  by_title_ko: {len(by_title_ko):,}")
    print(f"  by_title_ja: {len(by_title_ja):,}")

    # 역매핑 생성
    qid_to_names = {}

    print("  Creating reverse mapping (KO)...")
    for title, qid in by_title_ko.items():
        if qid not in qid_to_names:
            qid_to_names[qid] = {}
        qid_to_names[qid]['name_ko'] = title.replace('_', ' ')

    print("  Creating reverse mapping (JA)...")
    for title, qid in by_title_ja.items():
        if qid not in qid_to_names:
            qid_to_names[qid] = {}
        qid_to_names[qid]['name_ja'] = title.replace('_', ' ')

    print(f"  Final mapping: {len(qid_to_names):,} QIDs with KO/JA names")
    print(f"  Loaded in {time.time()-start:.1f}s")
    return qid_to_names


def load_checkpoint() -> int:
    """체크포인트 로드 - 처리된 줄 수 반환"""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('processed_lines', 0)
    return 0


def save_checkpoint(processed_lines: int):
    """체크포인트 저장"""
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump({'processed_lines': processed_lines}, f)


def count_lines(filepath: Path) -> int:
    """파일 줄 수 빠르게 카운트"""
    count = 0
    with open(filepath, 'rb') as f:
        for _ in f:
            count += 1
    return count


def enrich_entities(multilang_map: dict, resume_from: int = 0):
    """엔티티에 다국어 정보 추가"""

    print(f"\nInput: {WIKIDATA_EXTRACTED}")
    print(f"Output: {ENRICHED_OUTPUT}")

    if resume_from > 0:
        print(f"Resuming from line {resume_from:,}")

    total_lines = count_lines(WIKIDATA_EXTRACTED)
    print(f"Total lines: {total_lines:,}")

    processed = 0
    enriched = 0
    start_time = time.time()

    # resume 모드면 기존 파일에 append, 아니면 새로 시작
    mode = 'a' if resume_from > 0 else 'w'

    with open(WIKIDATA_EXTRACTED, 'r', encoding='utf-8') as f_in:
        with open(ENRICHED_OUTPUT, mode, encoding='utf-8') as f_out:
            for i, line in enumerate(f_in):
                # resume: 이미 처리된 줄 스킵
                if i < resume_from:
                    continue

                processed += 1

                try:
                    entity = json.loads(line.strip())
                    qid = entity.get('qid')

                    # 다국어 정보 추가
                    if qid and qid in multilang_map:
                        ml = multilang_map[qid]
                        # 구조에 따라 처리
                        if isinstance(ml, dict):
                            entity['name_ko'] = ml.get('ko') or ml.get('name_ko')
                            entity['name_ja'] = ml.get('ja') or ml.get('name_ja')
                            entity['wikipedia_title_ko'] = ml.get('wiki_ko')
                            entity['wikipedia_title_ja'] = ml.get('wiki_ja')
                        else:
                            # 단순 문자열이면 ko로 취급
                            entity['name_ko'] = ml
                        enriched += 1
                    else:
                        entity.setdefault('name_ko', None)
                        entity.setdefault('name_ja', None)

                    f_out.write(json.dumps(entity, ensure_ascii=False) + '\n')

                except Exception as e:
                    # 에러나도 원본 라인 그대로 쓰기
                    f_out.write(line)

                # 진행 상황 출력
                if processed % LOG_INTERVAL == 0:
                    elapsed = time.time() - start_time
                    rate = processed / elapsed if elapsed > 0 else 0
                    pct = (resume_from + processed) / total_lines * 100
                    print(f"  Progress: {resume_from + processed:,}/{total_lines:,} ({pct:.1f}%) | "
                          f"Enriched: {enriched:,} | Rate: {rate:,.0f}/s")

                    # 체크포인트 저장
                    save_checkpoint(resume_from + processed)

    # 최종 체크포인트
    save_checkpoint(resume_from + processed)

    elapsed = time.time() - start_time
    print(f"\nComplete: {processed:,} lines in {elapsed/60:.1f} min")
    print(f"Enriched: {enriched:,} ({enriched/processed*100:.1f}%)")

    return processed, enriched


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    args = parser.parse_args()

    print("=" * 60)
    print("Step 2.5: 다국어 보강 (Fast)")
    print("=" * 60)

    # 다국어 매핑 로드
    multilang_map = load_multilang_map()

    # resume 체크
    resume_from = 0
    if args.resume:
        resume_from = load_checkpoint()
        if resume_from > 0:
            print(f"Checkpoint found: {resume_from:,} lines already processed")

    # 보강 실행
    enrich_entities(multilang_map, resume_from)

    print("\n" + "=" * 60)
    print("완료!")
    print(f"Output: {ENRICHED_OUTPUT}")
    print("=" * 60)


if __name__ == '__main__':
    main()
