"""
Translate portal_items content from English to Korean.

Fixes the issue where content was generated in English but _ko fields either
contain English text (due to import fallback) or are empty.

Uses gpt-5.1-chat-latest per AI model policy (translation = "기타 잡것").

Usage:
    cd backend
    python scripts/translate_portal_items.py --dry-run                  # Preview only
    python scripts/translate_portal_items.py --limit 2                  # Test with 2 items
    python scripts/translate_portal_items.py --type singularity         # Singularities only
    python scripts/translate_portal_items.py --type lostbelt            # Lostbelts only
    python scripts/translate_portal_items.py --type servant_column      # Servants only
    python scripts/translate_portal_items.py                            # All 46 FGO items
    python scripts/translate_portal_items.py --slug gilgamesh-archer    # Single item

Cost estimate: ~46 items × ~5 sections × ~600 words ≈ ~$3-5 total
"""

import argparse
import json
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
            os.environ.setdefault(key.strip(), val.strip().strip('"'))

import psycopg2
from openai import OpenAI

DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://chaldeas:chaldeas_dev@127.0.0.1:5432/chaldeas'
)

MODEL = "gpt-5.1-chat-latest"
# Pricing per 1M tokens
INPUT_PRICE = 1.25
OUTPUT_PRICE = 10.00


SYSTEM_PROMPT_SHORT = """\
You are a professional translator for CHALDEAS, a history education platform \
bridging Fate/Grand Order and real history.

Translate the given English text to natural Korean.
- Use proper Korean historical terminology (e.g., "Battle of Marathon" → "마라톤 전투")
- FGO terms: Singularity=특이점, Lostbelt=이문대, Servant=서번트, Noble Phantasm=보구, \
Master=마스터, Grand Order=그랜드 오더, Holy Grail=성배
- Keep the same tone: engaging, documentary-style, educational
- Keep proper nouns in their commonly known Korean form
- Output ONLY the translated text, nothing else."""

SYSTEM_PROMPT_LONG = """\
You are a professional translator for CHALDEAS, a history education platform \
bridging Fate/Grand Order and real history.

Translate the given English article section to natural, fluent Korean.

RULES:
- Use proper Korean historical terminology
- FGO terms: Singularity=특이점, Lostbelt=이문대, Servant=서번트, Noble Phantasm=보구, \
Master=마스터, Grand Order=그랜드 오더, Holy Grail=성배, Chaldea=칼데아
- Servant class names: Saber=세이버, Archer=아처, Lancer=랜서, Rider=라이더, \
Caster=캐스터, Assassin=어새신, Berserker=버서커, Avenger=어벤저, Ruler=룰러
- Keep the same engaging, documentary-style tone
- Maintain paragraph breaks
- Preserve specific numbers, dates, and proper nouns
- Output ONLY the Korean translation, nothing else."""


def translate_text(client: OpenAI, text: str, is_long: bool = False) -> tuple[str, float]:
    """Translate English text to Korean. Returns (translated_text, cost_usd)."""
    if not text or not text.strip():
        return "", 0.0

    system = SYSTEM_PROMPT_LONG if is_long else SYSTEM_PROMPT_SHORT
    max_tokens = 8192 if is_long else 2048

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": text.strip()},
        ],
        max_completion_tokens=max_tokens,
    )

    result = resp.choices[0].message.content.strip()
    usage = resp.usage
    cost = (
        (usage.prompt_tokens * INPUT_PRICE + usage.completion_tokens * OUTPUT_PRICE)
        / 1_000_000
    )
    return result, cost


def needs_translation(en_text: str, ko_text: str | None) -> bool:
    """Check if ko field needs translation (missing, empty, or same as English)."""
    if not ko_text or not ko_text.strip():
        return True
    # If ko text is identical to en text, it's likely the import fallback
    if ko_text.strip() == en_text.strip():
        return True
    # If ko text starts with common English patterns, it's probably English
    en_starts = [
        'The ', 'A ', 'An ', 'In ', 'This ', 'FGO', 'Singularity', 'Lostbelt',
        'Gilgamesh', 'Nero', 'Jeanne', 'Alexander', 'Napoleon', 'Caesar',
    ]
    for prefix in en_starts:
        if ko_text.strip().startswith(prefix):
            return True
    return False


def translate_item(client: OpenAI, item: dict, dry_run: bool = False) -> tuple[dict, float, int]:
    """Translate a single portal item's fields. Returns (updates_dict, cost, field_count)."""
    updates = {}
    total_cost = 0.0
    field_count = 0

    slug = item['slug']
    sections = item.get('sections') or []
    if isinstance(sections, str):
        sections = json.loads(sections)

    # --- subtitle_ko ---
    subtitle = item.get('subtitle') or ''
    subtitle_ko = item.get('subtitle_ko')
    if subtitle and needs_translation(subtitle, subtitle_ko):
        if dry_run:
            print(f"    [DRY] Would translate subtitle ({len(subtitle)} chars)")
            field_count += 1
        else:
            print(f"    subtitle...", end="", flush=True)
            translated, cost = translate_text(client, subtitle)
            updates['subtitle_ko'] = translated
            total_cost += cost
            field_count += 1
            print(f" ${cost:.3f}")

    # --- description_ko ---
    desc = item.get('description') or ''
    desc_ko = item.get('description_ko')
    if desc and needs_translation(desc, desc_ko):
        if dry_run:
            print(f"    [DRY] Would translate description ({len(desc)} chars)")
            field_count += 1
        else:
            print(f"    description...", end="", flush=True)
            translated, cost = translate_text(client, desc, is_long=len(desc) > 500)
            updates['description_ko'] = translated
            total_cost += cost
            field_count += 1
            print(f" ${cost:.3f}")

    # --- historical_basis_ko ---
    hist = item.get('historical_basis') or ''
    hist_ko = item.get('historical_basis_ko')
    if hist and needs_translation(hist, hist_ko):
        if dry_run:
            print(f"    [DRY] Would translate historical_basis ({len(hist)} chars)")
            field_count += 1
        else:
            print(f"    historical_basis...", end="", flush=True)
            translated, cost = translate_text(client, hist, is_long=True)
            updates['historical_basis_ko'] = translated
            total_cost += cost
            field_count += 1
            print(f" ${cost:.3f}")

    # --- sections[].title_ko + content_ko ---
    sections_updated = False
    for i, sec in enumerate(sections):
        sec_title = sec.get('title', '')
        sec_title_ko = sec.get('title_ko')
        sec_content = sec.get('content', '')
        sec_content_ko = sec.get('content_ko')

        if sec_title and needs_translation(sec_title, sec_title_ko):
            if dry_run:
                print(f"    [DRY] Would translate section[{i}].title ({len(sec_title)} chars)")
                field_count += 1
            else:
                print(f"    section[{i}].title...", end="", flush=True)
                translated, cost = translate_text(client, sec_title)
                sec['title_ko'] = translated
                total_cost += cost
                field_count += 1
                sections_updated = True
                print(f" ${cost:.3f}")

        if sec_content and needs_translation(sec_content, sec_content_ko):
            if dry_run:
                word_count = len(sec_content.split())
                print(f"    [DRY] Would translate section[{i}].content ({word_count} words)")
                field_count += 1
            else:
                word_count = len(sec_content.split())
                print(f"    section[{i}].content ({word_count}w)...", end="", flush=True)
                translated, cost = translate_text(client, sec_content, is_long=True)
                sec['content_ko'] = translated
                total_cost += cost
                field_count += 1
                sections_updated = True
                print(f" ${cost:.3f}")

    if sections_updated:
        updates['sections'] = json.dumps(sections, ensure_ascii=False)

    return updates, total_cost, field_count


def main():
    parser = argparse.ArgumentParser(
        description='Translate portal_items en→ko',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without translating or updating DB')
    parser.add_argument('--limit', type=int, default=0,
                        help='Max items to process (0=all)')
    parser.add_argument('--type', type=str,
                        choices=['singularity', 'lostbelt', 'servant_column'],
                        help='Filter by item_type')
    parser.add_argument('--slug', type=str,
                        help='Translate a single item by slug')
    parser.add_argument('--sections-only', action='store_true',
                        help='Only translate section content (skip subtitle/desc)')
    args = parser.parse_args()

    client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # --- Fetch items ---
    where_clauses = ["item_type IN ('singularity', 'lostbelt', 'servant_column')"]
    params: list = []

    if args.type:
        where_clauses = [f"item_type = %s"]
        params.append(args.type)

    if args.slug:
        where_clauses.append("slug = %s")
        params.append(args.slug)

    query = f"""
        SELECT id, slug, item_type, title, title_ko,
               subtitle, subtitle_ko,
               description, description_ko,
               historical_basis, historical_basis_ko,
               sections
        FROM portal_items
        WHERE {' AND '.join(where_clauses)}
        ORDER BY item_type, sort_order, slug
    """
    if args.limit:
        query += f" LIMIT {args.limit}"

    cur.execute(query, params)
    columns = [desc[0] for desc in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]

    print(f"=== Portal Items en→ko Translation ===")
    print(f"  Model: {MODEL}")
    print(f"  Items: {len(rows)}")
    if args.dry_run:
        print(f"  Mode: DRY RUN")
    print()

    total_cost = 0.0
    total_fields = 0
    total_items = 0
    t_start = time.time()

    for idx, item in enumerate(rows):
        slug = item['slug']
        item_type = item['item_type']
        sections = item.get('sections') or []
        if isinstance(sections, str):
            sections = json.loads(sections)
        sec_count = len(sections)

        print(f"[{idx+1}/{len(rows)}] {slug} ({item_type}, {sec_count} sections)")

        if args.sections_only:
            # Skip subtitle/desc, only do sections
            item_for_translate = {**item, 'subtitle': '', 'description': '', 'historical_basis': ''}
        else:
            item_for_translate = item

        updates, cost, field_count = translate_item(
            client, item_for_translate, dry_run=args.dry_run
        )

        if field_count == 0:
            print(f"    (already translated)")
            continue

        total_cost += cost
        total_fields += field_count
        total_items += 1

        if not args.dry_run and updates:
            # Build UPDATE query
            set_clauses = []
            update_params: list = []
            for key, val in updates.items():
                if key == 'sections':
                    set_clauses.append(f"sections = CAST(%s AS jsonb)")
                else:
                    set_clauses.append(f"{key} = %s")
                update_params.append(val)

            set_clauses.append("updated_at = NOW()")
            update_params.append(item['id'])

            cur.execute(
                f"UPDATE portal_items SET {', '.join(set_clauses)} WHERE id = %s",
                update_params
            )
            conn.commit()
            print(f"    -> Updated {field_count} fields (${cost:.3f})")

    elapsed = time.time() - t_start
    print(f"\n{'=' * 60}")
    print(f"Results:")
    print(f"  Items translated: {total_items}/{len(rows)}")
    print(f"  Fields translated: {total_fields}")
    print(f"  Total cost: ~${total_cost:.2f}")
    print(f"  Time: {elapsed:.1f}s ({elapsed/60:.1f}min)")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
