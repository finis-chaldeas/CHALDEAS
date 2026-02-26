"""
Translate period_narratives (headline, narrative) into Korean using GPT-5-mini.

Usage:
    cd backend
    python scripts/translate_period_narratives.py --dry-run          # cost estimate only
    python scripts/translate_period_narratives.py                     # run all (global + regional)
    python scripts/translate_period_narratives.py --global-only       # global overviews only
    python scripts/translate_period_narratives.py --regional-only     # regional only
    python scripts/translate_period_narratives.py --limit 5           # test with 5 rows

Cost estimate: ~$0.10-0.20 for all 391 periods
"""

import argparse
import os
import sys
import time
from pathlib import Path

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
from openai import OpenAI

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://chaldeas:chaldeas_dev@127.0.0.1:5432/chaldeas')
client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

SYSTEM_PROMPT = """You are a professional historian and Korean translator.
Translate historical period headlines and narratives into natural Korean.
- Use proper Korean historical terminology
- Keep proper nouns in their commonly known Korean form
- Maintain academic yet accessible tone
- Return ONLY the translation, no explanations"""


def main():
    parser = argparse.ArgumentParser(description='Translate period narratives to Korean')
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--global-only', action='store_true', help='Only translate global overviews (region IS NULL)')
    parser.add_argument('--regional-only', action='store_true', help='Only translate regional narratives')
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Fetch untranslated headlines
    region_filter = ""
    if args.global_only:
        region_filter = "AND region IS NULL"
    elif args.regional_only:
        region_filter = "AND region IS NOT NULL"

    query = f"""
        SELECT id, period_start, headline, narrative, region
        FROM period_narratives
        WHERE headline IS NOT NULL
          AND (headline_ko IS NULL OR headline_ko = '')
          {region_filter}
        ORDER BY period_start, region NULLS FIRST
    """
    if args.limit:
        query += f" LIMIT {args.limit}"

    cur.execute(query)
    rows = cur.fetchall()
    print(f"[INFO] {len(rows)} periods to translate")

    if len(rows) == 0:
        print("[DONE] Nothing to translate!")
        conn.close()
        return

    # Cost estimate
    total_chars = sum(len(r[2] or '') + len(r[3] or '') for r in rows)
    est_tokens = total_chars // 3  # rough estimate
    est_cost = est_tokens * 2 * 0.15 / 1_000_000 + est_tokens * 2 * 0.60 / 1_000_000
    print(f"[COST] ~{est_tokens*2:,} tokens, ~${est_cost:.3f}")

    if args.dry_run:
        conn.close()
        return

    success = 0
    errors = 0
    start = time.time()

    for i, (row_id, period_start, headline, narrative, region) in enumerate(rows):
        try:
            region_label = region or 'global'
            # Translate headline
            # gpt-5-mini is a reasoning model: max_completion_tokens includes reasoning tokens (~400)
            resp = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Translate this historical period headline to Korean (under 60 chars):\n\n{headline}"},
                ],
                max_completion_tokens=2000,
            )
            headline_ko = resp.choices[0].message.content.strip().strip('"')

            # Translate narrative if exists
            narrative_ko = None
            if narrative:
                resp2 = client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Translate this historical period overview to Korean:\n\n{narrative}"},
                    ],
                    max_completion_tokens=8000,
                    )
                narrative_ko = resp2.choices[0].message.content.strip()

            # Save
            cur.execute("""
                UPDATE period_narratives
                SET headline_ko = %s, narrative_ko = %s
                WHERE id = %s
            """, (headline_ko, narrative_ko, row_id))
            conn.commit()

            success += 1
            if (i + 1) % 20 == 0 or i == 0:
                elapsed = time.time() - start
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                eta = (len(rows) - i - 1) / rate if rate > 0 else 0
                print(f"  [{i+1}/{len(rows)}] [{region_label}] {period_start}: {headline_ko[:40]}... | {rate:.1f}/s ETA {eta:.0f}s")

        except Exception as e:
            errors += 1
            print(f"  [{i+1}/{len(rows)}] ERROR {period_start}: {str(e)[:80]}")

    elapsed = time.time() - start
    print(f"\n{'='*50}")
    print(f"[DONE] {success}/{len(rows)} translated, {errors} errors, {elapsed:.1f}s")
    conn.close()


if __name__ == '__main__':
    main()
