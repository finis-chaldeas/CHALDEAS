"""
Wikidata 전체 데이터 가져오기 (순차 실행).

1. Aliases (labels + aliases)
2. Properties (coordinates, relationships, classifications)

Usage:
    python run_wikidata_full.py
    python run_wikidata_full.py --skip-aliases  # aliases 이미 완료된 경우
"""

import subprocess
import sys
import argparse
from datetime import datetime

def run_script(script_name, args=[]):
    """스크립트 실행."""
    cmd = [sys.executable, '-u', script_name] + args
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print(f"Started: {datetime.now()}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, cwd='poc/scripts/unified')

    print(f"\n{'='*60}")
    print(f"Finished: {datetime.now()}")
    print(f"Exit code: {result.returncode}")
    print(f"{'='*60}\n")

    return result.returncode

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-aliases', action='store_true', help='Skip aliases (already done)')
    args = parser.parse_args()

    start = datetime.now()
    print(f"Wikidata Full Extraction Started: {start}")

    # 1. Aliases
    if not args.skip_aliases:
        print("\n\n" + "="*60)
        print("PHASE 1: ALIASES")
        print("="*60)
        run_script('fetch_wikidata_aliases.py', ['--type', 'all'])
    else:
        print("Skipping aliases (--skip-aliases)")

    # 2. Properties
    print("\n\n" + "="*60)
    print("PHASE 2: PROPERTIES")
    print("="*60)
    run_script('fetch_wikidata_properties.py', ['--type', 'all'])

    end = datetime.now()
    print(f"\n\n{'='*60}")
    print(f"ALL COMPLETED")
    print(f"{'='*60}")
    print(f"Total duration: {end - start}")

if __name__ == '__main__':
    main()
