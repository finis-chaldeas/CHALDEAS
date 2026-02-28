"""
DB 상태 체크 — 서버 시작 전 실행 권장.

검사 항목:
1. PostgreSQL 연결 가능 여부
2. alembic_version이 기대 버전인지
3. 핵심 테이블 존재 여부
4. 핵심 테이블 row count 최소값

Usage:
    python tools/check-db.py
    python tools/check-db.py --fix   (alembic upgrade head 자동 실행)
"""
import sys
import subprocess

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

DB_URL = "host=127.0.0.1 port=5432 dbname=chaldeas user=chaldeas password=chaldeas_dev"

# Expected state
EXPECTED_HEAD = "602_trismegistus_portal"
CRITICAL_TABLES = {
    "events": 1000,
    "persons": 1000,
    "locations": 1000,
    "historical_chains": 100,
    "chain_segments": 1000,
    "period_narratives": 50,
    "portal_items": 10,
}


def check():
    errors = []
    warnings = []

    # 1. Connection
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()
        print("[OK] PostgreSQL connection")
    except Exception as e:
        print(f"[FAIL] PostgreSQL connection: {e}")
        print("\n  PostgreSQL이 실행 중인지 확인하세요:")
        print("  net start postgresql-x64-18")
        sys.exit(1)

    # 2. alembic_version
    cur.execute("SELECT version_num FROM alembic_version")
    row = cur.fetchone()
    if not row:
        errors.append("alembic_version table is empty!")
    else:
        version = row[0]
        if version == EXPECTED_HEAD:
            print(f"[OK] alembic version: {version}")
        elif version.startswith("200"):
            errors.append(
                f"alembic version is {version} — import_compact.py가 리셋한 것으로 보입니다!\n"
                "       해결: pg_restore로 백업 복원 또는 alembic upgrade head 실행"
            )
        else:
            warnings.append(f"alembic version: {version} (expected {EXPECTED_HEAD})")

    # 3. Critical tables
    cur.execute("""
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    """)
    existing = {r[0] for r in cur.fetchall()}

    for table, min_rows in CRITICAL_TABLES.items():
        if table not in existing:
            errors.append(f"Table '{table}' MISSING")
            continue

        cur.execute(f"SELECT count(*) FROM {table}")
        count = cur.fetchone()[0]
        if count < min_rows:
            warnings.append(f"Table '{table}': {count:,} rows (expected >= {min_rows:,})")
        else:
            print(f"[OK] {table}: {count:,} rows")

    cur.close()
    conn.close()

    # Summary
    if errors:
        print(f"\n{'='*50}")
        print(f"  ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  [!] {e}")
    if warnings:
        print(f"\n  WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  [?] {w}")

    if not errors and not warnings:
        print(f"\n  DB is healthy. Ready to start server.")

    return len(errors)


def fix():
    """Try to fix by running alembic upgrade head."""
    print("\nRunning alembic upgrade head...")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd="backend",
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"FAILED: {result.stderr}")
    return result.returncode


if __name__ == "__main__":
    error_count = check()
    if error_count > 0 and "--fix" in sys.argv:
        fix()
        print("\nRe-checking...")
        check()
    elif error_count > 0:
        print("\n  --fix 옵션으로 자동 수정 시도 가능")
        sys.exit(1)
