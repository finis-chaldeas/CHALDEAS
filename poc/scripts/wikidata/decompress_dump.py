"""
Wikidata 덤프 압축 해제
bz2 → json (D:/project/wikidata/)
"""

import bz2
import sys
import time

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

INPUT = "C:/Projects/Chaldeas/data/wikidata/latest-all.json.bz2"
OUTPUT = "D:/project/wikidata/latest-all.json"

CHUNK_SIZE = 1024 * 1024 * 10  # 10MB chunks

def decompress():
    print(f"Input: {INPUT}")
    print(f"Output: {OUTPUT}")
    print(f"Chunk size: {CHUNK_SIZE // 1024 // 1024}MB")
    print()

    start_time = time.time()
    total_written = 0

    with bz2.open(INPUT, 'rb') as f_in:
        with open(OUTPUT, 'wb') as f_out:
            while True:
                chunk = f_in.read(CHUNK_SIZE)
                if not chunk:
                    break
                f_out.write(chunk)
                total_written += len(chunk)

                elapsed = time.time() - start_time
                speed = total_written / elapsed / 1024 / 1024  # MB/s

                print(f"\rWritten: {total_written / 1024 / 1024 / 1024:.2f} GB | "
                      f"Speed: {speed:.1f} MB/s | "
                      f"Time: {elapsed / 60:.1f} min", end='', flush=True)

    elapsed = time.time() - start_time
    print()
    print(f"\n=== Complete ===")
    print(f"Total: {total_written / 1024 / 1024 / 1024:.2f} GB")
    print(f"Time: {elapsed / 60:.1f} min")

if __name__ == '__main__':
    decompress()
