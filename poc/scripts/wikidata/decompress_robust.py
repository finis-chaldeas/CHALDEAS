"""
강건한 bz2 압축 해제 (에러 처리 + 로깅)
"""

import bz2
import sys
import time
import os
import traceback
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

INPUT = "C:/Projects/Chaldeas/data/wikidata/latest-all.json.bz2"
OUTPUT = "D:/project/wikidata/latest-all.json"
LOG_FILE = "D:/project/wikidata/decompress.log"
CHUNK_SIZE = 1024 * 1024 * 10  # 10MB

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def decompress():
    log(f"=== 압축 해제 시작 ===")
    log(f"Input: {INPUT}")
    log(f"Output: {OUTPUT}")
    log(f"Chunk size: {CHUNK_SIZE // 1024 // 1024}MB")

    # 기존 파일 삭제 (처음부터 시작)
    if os.path.exists(OUTPUT):
        size = os.path.getsize(OUTPUT) / 1024**3
        log(f"기존 파일 삭제: {size:.2f} GB")
        os.remove(OUTPUT)

    start_time = time.time()
    total_written = 0
    last_log_time = start_time

    try:
        with bz2.open(INPUT, 'rb') as f_in:
            with open(OUTPUT, 'wb') as f_out:
                while True:
                    try:
                        chunk = f_in.read(CHUNK_SIZE)
                        if not chunk:
                            break

                        f_out.write(chunk)
                        f_out.flush()  # 즉시 디스크에 쓰기
                        total_written += len(chunk)

                        # 1분마다 로그
                        current_time = time.time()
                        if current_time - last_log_time >= 60:
                            elapsed = current_time - start_time
                            speed = total_written / elapsed / 1024 / 1024
                            gb_written = total_written / 1024**3
                            log(f"진행: {gb_written:.2f} GB | 속도: {speed:.1f} MB/s | 시간: {elapsed/60:.1f}분")
                            last_log_time = current_time

                    except Exception as e:
                        log(f"청크 읽기 오류: {e}")
                        log(traceback.format_exc())
                        raise

    except Exception as e:
        log(f"치명적 오류: {e}")
        log(traceback.format_exc())
        raise

    elapsed = time.time() - start_time
    log(f"=== 완료 ===")
    log(f"총 크기: {total_written / 1024**3:.2f} GB")
    log(f"총 시간: {elapsed / 60:.1f}분")

if __name__ == '__main__':
    try:
        decompress()
    except KeyboardInterrupt:
        log("사용자 중단")
    except Exception as e:
        log(f"프로그램 종료: {e}")
        sys.exit(1)
