"""
Translate entity_narratives (narrative, significance, causes, consequences)
into Korean and Japanese using GPT-5-mini.

Usage:
    cd backend
    python scripts/translate_narratives.py --lang ko
    python scripts/translate_narratives.py --lang ja
    python scripts/translate_narratives.py --lang ko --dry-run   # cost estimate only
    python scripts/translate_narratives.py --lang ko --limit 10  # test with 10 rows
    python scripts/translate_narratives.py --lang ko --workers 10 # parallel workers

Cost estimate: ~$1.50/language, ~$3 total for ko+ja
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# UTF-8 stdout for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Load .env
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if env_path.exists():
    for line in env_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            os.environ.setdefault(key.strip(), val.strip())

import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from openai import OpenAI

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://chaldeas:chaldeas_dev@127.0.0.1:5432/chaldeas')
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

client = OpenAI(api_key=OPENAI_API_KEY)

LANG_NAMES = {'ko': 'Korean', 'ja': 'Japanese'}

SYSTEM_PROMPT_TEMPLATE = """You are a professional historian and translator. Translate the following historical narrative content into {lang_name}.

Rules:
- Maintain academic historical tone
- Keep proper nouns (person names, place names) in their commonly known {lang_name} form
- For causes and consequences arrays, translate each item separately
- Return valid JSON with the exact same keys
- Do NOT add or remove any items from arrays
- If a field is null, keep it null"""

USER_PROMPT_TEMPLATE = """Translate to {lang_name}. Return JSON only:

{content}"""


def ensure_columns(conn):
    """Add translation columns if they don't exist."""
    columns_to_add = [
        # narrative_ko already exists
        ("narrative_ja", "TEXT"),
        ("significance_ko", "VARCHAR"),
        ("significance_ja", "VARCHAR"),
        ("causes_ko", "TEXT[]"),
        ("causes_ja", "TEXT[]"),
        ("consequences_ko", "TEXT[]"),
        ("consequences_ja", "TEXT[]"),
    ]

    cur = conn.cursor()
    for col_name, col_type in columns_to_add:
        cur.execute(f"""
            DO $$
            BEGIN
                ALTER TABLE entity_narratives ADD COLUMN {col_name} {col_type};
            EXCEPTION WHEN duplicate_column THEN
                NULL;
            END $$;
        """)
    conn.commit()
    cur.close()
    print(f"[OK] DB columns verified")


def fetch_untranslated(conn, lang: str, limit: int | None = None):
    """Fetch rows that haven't been translated yet for the given language."""
    narrative_col = f"narrative_{lang}"

    cur = conn.cursor()
    query = f"""
        SELECT id, entity_type, entity_id, narrative, significance, causes, consequences
        FROM entity_narratives
        WHERE narrative IS NOT NULL
          AND ({narrative_col} IS NULL OR {narrative_col} = '')
        ORDER BY id
    """
    if limit:
        query += f" LIMIT {limit}"

    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    return rows


def estimate_cost(rows):
    """Estimate API cost for translating rows."""
    total_input_tokens = 0
    for row in rows:
        _id, entity_type, entity_id, narrative, significance, causes, consequences = row
        text_len = len(narrative or '')
        text_len += len(significance or '')
        if causes:
            text_len += sum(len(c) for c in causes)
        if consequences:
            text_len += sum(len(c) for c in consequences)
        # Rough: 4 chars ≈ 1 token, plus JSON overhead
        total_input_tokens += (text_len // 4) + 100  # 100 tokens overhead per item

    total_output_tokens = total_input_tokens  # Output ≈ same size as input

    # GPT-5-mini pricing (approximate)
    input_cost = total_input_tokens * 0.15 / 1_000_000
    output_cost = total_output_tokens * 0.60 / 1_000_000
    total_cost = input_cost + output_cost

    return total_input_tokens, total_output_tokens, total_cost


def translate_one(narrative: str, significance: str | None,
                  causes: list | None, consequences: list | None,
                  lang: str) -> tuple[dict, object]:
    """Translate one entity's narrative content."""
    content = {
        "narrative": narrative,
        "significance": significance,
        "causes": causes if causes else [],
        "consequences": consequences if consequences else [],
    }

    lang_name = LANG_NAMES[lang]
    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(lang_name=lang_name)},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                lang_name=lang_name,
                content=json.dumps(content, ensure_ascii=False, indent=2)
            )},
        ],
        response_format={"type": "json_object"},
        max_completion_tokens=10000,
    )

    result_text = response.choices[0].message.content
    result = json.loads(result_text)

    usage = response.usage
    return result, usage


def process_row(row, lang: str, db_pool):
    """Process a single row: translate + save. Used by thread pool."""
    row_id, entity_type, entity_id, narrative, significance, causes, consequences = row

    translated, usage = translate_one(narrative, significance, causes, consequences, lang)

    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(f"""
            UPDATE entity_narratives SET
                narrative_{lang} = %s,
                significance_{lang} = %s,
                causes_{lang} = %s,
                consequences_{lang} = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (
            translated.get('narrative'),
            translated.get('significance'),
            translated.get('causes') if translated.get('causes') else None,
            translated.get('consequences') if translated.get('consequences') else None,
            row_id,
        ))
        conn.commit()
        cur.close()
    finally:
        db_pool.putconn(conn)

    return entity_type, entity_id, usage


# Thread-safe counters
class Stats:
    def __init__(self):
        self.lock = threading.Lock()
        self.success = 0
        self.errors = 0
        self.total_input = 0
        self.total_output = 0


def main():
    parser = argparse.ArgumentParser(description='Translate entity narratives')
    parser.add_argument('--lang', required=True, choices=['ko', 'ja'], help='Target language')
    parser.add_argument('--limit', type=int, default=None, help='Limit rows to translate')
    parser.add_argument('--dry-run', action='store_true', help='Estimate cost only')
    parser.add_argument('--workers', type=int, default=8, help='Parallel workers (default: 8)')
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    print(f"[DB] Connected")

    # Ensure columns exist
    ensure_columns(conn)

    # Fetch untranslated rows
    rows = fetch_untranslated(conn, args.lang, args.limit)
    print(f"[INFO] {len(rows)} rows to translate ({args.lang})")
    conn.close()

    if len(rows) == 0:
        print("[DONE] Nothing to translate!")
        return

    # Cost estimate
    input_tokens, output_tokens, estimated_cost = estimate_cost(rows)
    print(f"[COST] Estimated: {input_tokens:,} input + {output_tokens:,} output tokens")
    print(f"[COST] Estimated cost: ${estimated_cost:.2f}")
    print(f"[WORKERS] {args.workers} parallel threads")

    if args.dry_run:
        return

    # Create connection pool for parallel workers
    db_pool = ThreadedConnectionPool(2, args.workers + 2, DATABASE_URL)

    # Translate with thread pool
    total = len(rows)
    stats = Stats()
    start_time = time.time()

    def on_done(future, idx):
        elapsed = time.time() - start_time
        try:
            entity_type, entity_id, usage = future.result()
            with stats.lock:
                stats.success += 1
                stats.total_input += usage.prompt_tokens
                stats.total_output += usage.completion_tokens
                done = stats.success + stats.errors

            if done % 50 == 0 or done == 1:
                rate = done / elapsed if elapsed > 0 else 0
                eta = (total - done) / rate if rate > 0 else 0
                actual_cost = stats.total_input * 0.15 / 1_000_000 + stats.total_output * 0.60 / 1_000_000
                print(f"  [{done}/{total}] {entity_type}:{entity_id} "
                      f"| {rate:.1f}/s | ETA {eta/60:.1f}min | ${actual_cost:.3f}")
        except Exception as e:
            with stats.lock:
                stats.errors += 1
                done = stats.success + stats.errors
            # Print error concisely
            err_msg = str(e)[:100]
            print(f"  [{done}/{total}] ERROR: {err_msg}")

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = []
        for i, row in enumerate(rows):
            future = executor.submit(process_row, row, args.lang, db_pool)
            future.add_done_callback(lambda f, idx=i: on_done(f, idx))
            futures.append(future)

        # Wait for all to complete
        for f in as_completed(futures):
            pass  # Callbacks handle reporting

    # Final stats
    elapsed = time.time() - start_time
    actual_cost = stats.total_input * 0.15 / 1_000_000 + stats.total_output * 0.60 / 1_000_000
    print(f"\n{'='*50}")
    print(f"[DONE] {stats.success}/{total} translated, {stats.errors} errors")
    print(f"[TIME] {elapsed:.1f}s ({elapsed/60:.1f}min)")
    print(f"[TOKENS] {stats.total_input:,} input + {stats.total_output:,} output")
    print(f"[COST] ${actual_cost:.3f}")

    db_pool.closeall()


if __name__ == '__main__':
    main()
