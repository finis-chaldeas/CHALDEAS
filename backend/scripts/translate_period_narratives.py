"""
Translate period_narratives (headline, narrative) into Korean/Japanese.

Usage:
    cd backend
    python scripts/translate_period_narratives.py --dry-run          # cost estimate only
    python scripts/translate_period_narratives.py                     # run all Korean (global + regional)
    python scripts/translate_period_narratives.py --lang ja           # run all Japanese
    python scripts/translate_period_narratives.py --global-only       # global overviews only
    python scripts/translate_period_narratives.py --regional-only     # regional only
    python scripts/translate_period_narratives.py --limit 5           # test with 5 rows

Cost estimate: ~$0.10-0.20 per language for all 391 periods
"""

import argparse
import os
import sys
import time
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import functools
print = functools.partial(print, flush=True)

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

SYSTEM_PROMPTS = {
    'ko': """You are a professional historian and Korean translator.
Translate historical period headlines and narratives into natural Korean.
- Use proper Korean historical terminology
- Keep proper nouns in their commonly known Korean form
- Maintain academic yet accessible tone
- Return ONLY the translation, no explanations""",

    'ja': """You are a professional historian and Japanese translator.
Translate historical period headlines and narratives into natural Japanese.
- Use proper Japanese historical terminology
- Keep proper nouns in their standard Japanese form (katakana for Western names)
- Maintain academic yet accessible tone
- Return ONLY the translation, no explanations""",
}

LANG_NAMES = {'ko': 'Korean', 'ja': 'Japanese'}


def main():
    parser = argparse.ArgumentParser(description='Translate period narratives')
    parser.add_argument('--lang', type=str, default='ko', choices=['ko', 'ja'],
                        help='Target language (default: ko)')
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--global-only', action='store_true', help='Only translate global overviews (region IS NULL)')
    parser.add_argument('--regional-only', action='store_true', help='Only translate regional narratives')
    args = parser.parse_args()

    lang = args.lang
    lang_name = LANG_NAMES[lang]
    headline_col = f'headline_{lang}'
    narrative_col = f'narrative_{lang}'
    system_prompt = SYSTEM_PROMPTS[lang]

    print(f"[INFO] Target language: {lang_name} (_{lang} suffix)")

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
          AND ({headline_col} IS NULL OR {headline_col} = '')
          {region_filter}
        ORDER BY period_start, region NULLS FIRST
    """
    if args.limit:
        query += f" LIMIT {args.limit}"

    cur.execute(query)
    rows = cur.fetchall()
    print(f"[INFO] {len(rows)} periods to translate to {lang_name}")

    if len(rows) == 0:
        print("[DONE] Nothing to translate!")
        conn.close()
        return

    # Cost estimate
    total_chars = sum(len(r[2] or '') + len(r[3] or '') for r in rows)
    est_tokens = total_chars // 3
    est_cost = (est_tokens * 1.25 + est_tokens * 10.00) / 1_000_000
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
            resp = client.chat.completions.create(
                model="gpt-5.1-chat-latest",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Translate this historical period headline to {lang_name} (under 60 chars):\n\n{headline}"},
                ],
                max_completion_tokens=500,
            )
            headline_translated = resp.choices[0].message.content.strip().strip('"')

            # Translate narrative if exists
            narrative_translated = None
            if narrative:
                resp2 = client.chat.completions.create(
                    model="gpt-5.1-chat-latest",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Translate this historical period overview to {lang_name}:\n\n{narrative}"},
                    ],
                    max_completion_tokens=4000,
                )
                narrative_translated = resp2.choices[0].message.content.strip()

            # Save
            cur.execute(f"""
                UPDATE period_narratives
                SET {headline_col} = %s, {narrative_col} = %s
                WHERE id = %s
            """, (headline_translated, narrative_translated, row_id))
            conn.commit()

            success += 1
            if (i + 1) % 20 == 0 or i == 0:
                elapsed = time.time() - start
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                eta = (len(rows) - i - 1) / rate if rate > 0 else 0
                print(f"  [{i+1}/{len(rows)}] [{region_label}] {period_start}: {headline_translated[:40]}... | {rate:.1f}/s ETA {eta:.0f}s")

        except Exception as e:
            errors += 1
            print(f"  [{i+1}/{len(rows)}] ERROR {period_start}: {str(e)[:80]}")

    elapsed = time.time() - start
    print(f"\n{'='*50}")
    print(f"[DONE] {success}/{len(rows)} translated to {lang_name}, {errors} errors, {elapsed:.1f}s")
    conn.close()


if __name__ == '__main__':
    main()
