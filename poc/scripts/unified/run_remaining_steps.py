"""
남은 단계 자동 실행 스크립트

Step 2 완료 후:
1. Step 2.5 실행 (다국어 보강)
2. Step 1.5 완료 대기
3. Step 3 실행 (Wikipedia 추출)
4. Step 4 실행 (DB 임포트)
5. Step 5 실행 (링크 생성)

Usage:
    python run_remaining_steps.py
"""

import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent

def run_script(name: str, script: str):
    """스크립트 실행 및 완료 대기"""
    print(f"\n{'='*60}")
    print(f"Starting: {name}")
    print(f"{'='*60}\n")

    result = subprocess.run(
        [sys.executable, "-u", script],
        cwd=SCRIPTS_DIR,
        capture_output=False
    )

    if result.returncode != 0:
        print(f"\n❌ {name} failed with code {result.returncode}")
        return False

    print(f"\n✅ {name} completed!")
    return True


def check_step2_done():
    """Step 2 완료 여부 확인"""
    output_file = SCRIPTS_DIR / "../../data/unified/wikidata_full.jsonl"
    checkpoint = SCRIPTS_DIR / "../../data/unified/checkpoints/extract_checkpoint.json"

    # 체크포인트 없으면 완료
    return output_file.exists() and not checkpoint.exists()


def main():
    print("="*60)
    print("남은 단계 자동 실행")
    print("="*60)

    # Step 2 완료 확인
    print("\nStep 2 완료 대기 중...")
    while not check_step2_done():
        time.sleep(60)  # 1분마다 체크
        print(".", end="", flush=True)

    print("\n\nStep 2 완료 확인!")

    # Step 2.5: 다국어 보강
    if not run_script("Step 2.5: 다국어 보강", "02b_enrich_multilang.py"):
        return

    # Step 3: Wikipedia 추출
    if not run_script("Step 3: Wikipedia 추출", "03_extract_wikipedia.py"):
        return

    # Step 4: DB 임포트
    if not run_script("Step 4: DB 임포트", "04_import_all.py"):
        return

    # Step 5: 링크 생성
    if not run_script("Step 5: 링크 생성", "05_build_links.py"):
        return

    print("\n" + "="*60)
    print("🎉 모든 단계 완료!")
    print("="*60)


if __name__ == '__main__':
    main()
