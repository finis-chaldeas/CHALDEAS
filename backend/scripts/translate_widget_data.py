"""
Translate widget JSONB data fields into Korean/Japanese for all chain_segments.

Processes each chain_segment row, extracts translatable text fields from each widget,
batches them into GPT API calls, and writes _{lang} suffixed fields back to JSONB.

Usage:
    cd backend
    python scripts/translate_widget_data.py --dry-run          # cost estimate only
    python scripts/translate_widget_data.py --limit 10         # test with 10 segments
    python scripts/translate_widget_data.py                     # translate all (Korean)
    python scripts/translate_widget_data.py --lang ja           # translate to Japanese
    python scripts/translate_widget_data.py --batch-size 20    # larger batches (default 10)
    python scripts/translate_widget_data.py --type dramatic_stat  # one widget type only
    python scripts/translate_widget_data.py --force --limit 10   # re-translate even if _ko exists

Cost estimate: ~$6-8 per language for all 6,000+ widgets (gpt-5.1-chat-latest)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Force unbuffered output for background runs
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
import psycopg2.extras
from openai import OpenAI

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://chaldeas:chaldeas_dev@127.0.0.1:5432/chaldeas')
client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

# ── Translatable fields per widget type ──────────────────────────────────────
# flat: top-level string fields
# array_objects: {array_name: [sub_fields]} — array of objects with translatable fields
# array_strings: [array_name] — array of plain strings

WIDGET_FIELDS = {
    'dramatic_stat': {
        'flat': ['label', 'suffix', 'context', 'prefix'],
    },
    'primary_quote': {
        'flat': ['text', 'speaker', 'source'],
    },
    'era_context': {
        'flat': ['heading'],
        'array_objects': {'items': ['text', 'region']},
    },
    'what_if': {
        'flat': ['hypothesis', 'consequence', 'question', 'scenario'],
    },
    'narrator_aside': {
        'flat': ['text'],
    },
    'historian_note': {
        'flat': ['note', 'historian', 'work'],
    },
    'faction_vs': {
        'flat': ['left_name', 'right_name', 'left_commander', 'right_commander',
                 'left_strength', 'right_strength', 'outcome'],
        'array_strings': ['left_details', 'right_details'],
    },
    'modern_equivalent': {
        'flat': ['ancient', 'modern', 'explanation', 'heading'],
    },
    'person_card': {
        'flat': ['name', 'role', 'summary'],
    },
    'battle_stats': {
        'flat': ['heading', 'significance'],
        'array_objects': {'stats': ['label', 'value']},
    },
    'we_dont_know': {
        'flat': ['question', 'detail', 'theories'],
    },
    'mini_timeline': {
        'flat': ['heading'],
        'array_objects': {'events': ['label']},
    },
    'conflicting_accounts': {
        'flat': ['heading', 'verdict', 'topic'],
        'array_objects': {'accounts': ['source', 'claim']},
    },
    'alliance_diagram': {
        'flat': ['heading'],
        'array_objects': {'nodes': ['label'], 'edges': ['label']},
    },
    'territory_change': {
        'flat': ['heading'],
        'array_objects': {'changes': ['label', 'before', 'after']},
    },
}

SYSTEM_PROMPTS = {
    'ko': """You are a professional historian and Korean translator.
Translate the JSON values from English to Korean.
Rules:
- Return ONLY a valid JSON object with the same keys and Korean translations as values.
- Use proper Korean historical terminology (e.g. 페르시아 제국, 로마 공화국, 십자군).
- Keep well-known proper nouns in their standard Korean form.
- Translate ALL text including units and suffixes: "years" → "년", "people" → "명", "oracle bone fragments" → "갑골 조각" etc.
- Only keep pure numbers unchanged (e.g. "300,000" stays "300,000").
- Maintain the tone: dramatic text stays dramatic, academic stays academic.
- Do NOT add explanations or commentary — just the JSON.""",

    'ja': """You are a professional historian and Japanese translator.
Translate the JSON values from English to Japanese.
Rules:
- Return ONLY a valid JSON object with the same keys and Japanese translations as values.
- Use proper Japanese historical terminology (e.g. ペルシア帝国, ローマ共和国, 十字軍).
- Keep well-known proper nouns in their standard Japanese form (katakana for Western names).
- Translate ALL text including units and suffixes: "years" → "年", "people" → "人", "oracle bone fragments" → "甲骨片" etc.
- Only keep pure numbers unchanged (e.g. "300,000" stays "300,000").
- Maintain the tone: dramatic text stays dramatic, academic stays academic.
- Do NOT add explanations or commentary — just the JSON.""",
}


def extract_translatable(widget_type: str, data: dict, lang: str = 'ko', force: bool = False) -> dict:
    """Extract translatable text fields from widget data. Returns {key: text}."""
    suffix = f'_{lang}'
    result = {}
    config = WIDGET_FIELDS.get(widget_type, {})
    if not config:
        return result

    # Flat string fields
    for field in config.get('flat', []):
        val = data.get(field)
        if isinstance(val, str) and val.strip():
            if force or f'{field}{suffix}' not in data:
                result[field] = val

    # Array of objects with translatable sub-fields
    for arr_name, sub_fields in config.get('array_objects', {}).items():
        arr = data.get(arr_name, [])
        if isinstance(arr, list):
            for i, item in enumerate(arr):
                if isinstance(item, dict):
                    for sf in sub_fields:
                        val = item.get(sf)
                        if isinstance(val, str) and val.strip():
                            if force or f'{sf}{suffix}' not in item:
                                result[f'{arr_name}.{i}.{sf}'] = val

    # Array of plain strings
    for arr_name in config.get('array_strings', []):
        arr = data.get(arr_name, [])
        lang_arr = data.get(f'{arr_name}{suffix}')
        if isinstance(arr, list) and arr and (force or not lang_arr):
            for i, val in enumerate(arr):
                if isinstance(val, str) and val.strip():
                    result[f'{arr_name}.{i}'] = val

    return result


def apply_translations(widget_type: str, data: dict, translations: dict, lang: str = 'ko') -> bool:
    """Apply translated values back to widget data. Returns True if anything changed."""
    suffix = f'_{lang}'
    config = WIDGET_FIELDS.get(widget_type, {})
    if not config:
        return False

    changed = False

    # Flat fields
    for field in config.get('flat', []):
        if field in translations and translations[field]:
            data[f'{field}{suffix}'] = translations[field]
            changed = True

    # Array of objects
    for arr_name, sub_fields in config.get('array_objects', {}).items():
        arr = data.get(arr_name, [])
        if isinstance(arr, list):
            for i, item in enumerate(arr):
                if isinstance(item, dict):
                    for sf in sub_fields:
                        key = f'{arr_name}.{i}.{sf}'
                        if key in translations and translations[key]:
                            item[f'{sf}{suffix}'] = translations[key]
                            changed = True

    # Array of strings → create _{lang} array
    for arr_name in config.get('array_strings', []):
        arr = data.get(arr_name, [])
        if not isinstance(arr, list) or not arr:
            continue
        lang_vals = []
        has_any = False
        for i in range(len(arr)):
            key = f'{arr_name}.{i}'
            if key in translations and translations[key]:
                lang_vals.append(translations[key])
                has_any = True
            else:
                lang_vals.append(arr[i] if isinstance(arr[i], str) else '')
        if has_any:
            data[f'{arr_name}{suffix}'] = lang_vals
            changed = True

    return changed


def estimate_tokens(text: str) -> int:
    """Rough token count estimate (1 token ≈ 4 chars for English)."""
    return len(text) // 4 + 1


def translate_batch(batch: dict, lang: str = 'ko', retries: int = 2) -> dict:
    """Send a batch of {key: text} to GPT and return {key: translated_text}."""
    if not batch:
        return {}

    system_prompt = SYSTEM_PROMPTS[lang]
    user_msg = json.dumps(batch, ensure_ascii=False, indent=None)
    input_tokens = estimate_tokens(user_msg) + estimate_tokens(system_prompt)

    for attempt in range(retries + 1):
        try:
            resp = client.chat.completions.create(
                model="gpt-5.1-chat-latest",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                max_completion_tokens=max(input_tokens * 2, 2000),
            )

            content = resp.choices[0].message.content.strip()

            # Strip markdown code fence if present
            if content.startswith('```'):
                lines = content.split('\n')
                lines = [l for l in lines if not l.strip().startswith('```')]
                content = '\n'.join(lines)

            return json.loads(content)
        except (json.JSONDecodeError, Exception) as e:
            if attempt < retries:
                time.sleep(2)
                continue
            raise


def main():
    parser = argparse.ArgumentParser(description='Translate widget data to target language')
    parser.add_argument('--lang', type=str, default='ko', choices=['ko', 'ja'],
                        help='Target language (default: ko)')
    parser.add_argument('--limit', type=int, default=None, help='Max segments to process')
    parser.add_argument('--dry-run', action='store_true', help='Cost estimate only')
    parser.add_argument('--batch-size', type=int, default=10,
                        help='Segments per API batch (default 10)')
    parser.add_argument('--type', type=str, default=None,
                        help='Only translate this widget type (e.g. dramatic_stat)')
    parser.add_argument('--force', action='store_true',
                        help='Re-translate even if target lang fields already exist')
    args = parser.parse_args()

    lang = args.lang
    lang_name = {'ko': 'Korean', 'ja': 'Japanese'}[lang]
    print(f"[INFO] Target language: {lang_name} (_{lang} suffix)")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Fetch all segments with widgets
    cur.execute("""
        SELECT id, widgets
        FROM chain_segments
        WHERE widgets IS NOT NULL
          AND jsonb_array_length(widgets) > 0
        ORDER BY id
    """)
    rows = cur.fetchall()
    print(f"[INFO] {len(rows)} segments with widgets")

    # ── Phase 1: Scan and collect work ────────────────────────────────────────
    # Each work item: (segment_id, widget_index, widget_type, {key: text})
    work_items = []
    total_chars = 0

    for seg_id, widgets in rows:
        if not isinstance(widgets, list):
            continue
        for wi, widget in enumerate(widgets):
            wtype = widget.get('type', '')
            wdata = widget.get('data', {})
            if not isinstance(wdata, dict):
                continue
            if args.type and wtype != args.type:
                continue

            texts = extract_translatable(wtype, wdata, lang=lang, force=args.force)
            if texts:
                work_items.append((seg_id, wi, wtype, texts))
                total_chars += sum(len(v) for v in texts.values())

    total_fields = sum(len(item[3]) for item in work_items)
    est_input_tokens = total_chars // 4 + len(work_items) * 50  # overhead per widget
    est_output_tokens = est_input_tokens  # Korean is roughly same length
    est_cost = (est_input_tokens * 1.25 + est_output_tokens * 10.00) / 1_000_000

    print(f"[INFO] {len(work_items)} widgets need translation ({total_fields} fields, {total_chars:,} chars)")
    print(f"[COST] ~{est_input_tokens + est_output_tokens:,} tokens, ~${est_cost:.2f}")

    if args.dry_run or len(work_items) == 0:
        if len(work_items) == 0:
            print("[DONE] Nothing to translate!")
        conn.close()
        return

    # ── Phase 2: Group by segment and batch ───────────────────────────────────
    # Group work items by segment_id
    from collections import defaultdict
    seg_work = defaultdict(list)
    for seg_id, wi, wtype, texts in work_items:
        seg_work[seg_id].append((wi, wtype, texts))

    seg_ids = list(seg_work.keys())
    if args.limit:
        seg_ids = seg_ids[:args.limit]

    print(f"[INFO] Processing {len(seg_ids)} segments...")

    success = 0
    errors = 0
    widgets_done = 0
    start = time.time()

    # Process in batches of segments
    for batch_start in range(0, len(seg_ids), args.batch_size):
        batch_seg_ids = seg_ids[batch_start:batch_start + args.batch_size]

        # Collect all translatable text for this batch with prefixed keys
        # Format: "s{seg_id}_w{widget_index}_{field_key}" → text
        batch_texts = {}
        batch_meta = {}  # key → (seg_id, wi, field_key)

        for seg_id in batch_seg_ids:
            for wi, wtype, texts in seg_work[seg_id]:
                for field_key, text_val in texts.items():
                    bkey = f"s{seg_id}_w{wi}_{field_key}"
                    batch_texts[bkey] = text_val
                    batch_meta[bkey] = (seg_id, wi, field_key)

        if not batch_texts:
            continue

        try:
            translated = translate_batch(batch_texts, lang=lang)

            # Group translations back by (seg_id, wi)
            seg_translations = defaultdict(lambda: defaultdict(dict))
            for bkey, ko_val in translated.items():
                if bkey in batch_meta:
                    seg_id, wi, field_key = batch_meta[bkey]
                    seg_translations[seg_id][wi][field_key] = ko_val

            # Apply translations and update DB
            for seg_id in batch_seg_ids:
                if seg_id not in seg_translations:
                    continue

                # Re-fetch current widgets to avoid stale data
                cur.execute("SELECT widgets FROM chain_segments WHERE id = %s", (seg_id,))
                row = cur.fetchone()
                if not row:
                    continue
                widgets = row[0]
                if not isinstance(widgets, list):
                    continue

                any_changed = False
                for wi, field_translations in seg_translations[seg_id].items():
                    if wi < len(widgets):
                        wtype = widgets[wi].get('type', '')
                        wdata = widgets[wi].get('data', {})
                        if apply_translations(wtype, wdata, field_translations, lang=lang):
                            any_changed = True
                            widgets_done += 1

                if any_changed:
                    cur.execute(
                        "UPDATE chain_segments SET widgets = %s WHERE id = %s",
                        (json.dumps(widgets, ensure_ascii=False), seg_id)
                    )
                    conn.commit()
                    success += 1

        except Exception as e:
            errors += 1
            err_msg = str(e)[:120]
            print(f"  [BATCH ERROR] segs {batch_seg_ids[0]}-{batch_seg_ids[-1]}: {err_msg}")
            conn.rollback()

        # Progress
        processed = min(batch_start + args.batch_size, len(seg_ids))
        if processed % 50 == 0 or processed == len(seg_ids) or batch_start == 0:
            elapsed = time.time() - start
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (len(seg_ids) - processed) / rate if rate > 0 else 0
            print(f"  [{processed}/{len(seg_ids)}] {widgets_done} widgets | "
                  f"{rate:.1f} seg/s | ETA {eta:.0f}s | {errors} errors")

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"[DONE] {success} segments updated, {widgets_done} widgets translated")
    print(f"       {errors} errors, {elapsed:.1f}s total")
    conn.close()


if __name__ == '__main__':
    main()
