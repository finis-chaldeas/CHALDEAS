"""
Batch translate location and person names to KO/JA.

Sends batches of 50 names per API call for efficiency.
Uses gpt-5-mini.

Usage:
    cd backend
    python scripts/enrich_names.py locations              # Translate location names
    python scripts/enrich_names.py persons                # Translate person names (event-linked)
    python scripts/enrich_names.py locations --test 100   # Test with 100
    python scripts/enrich_names.py persons --min-importance 4  # Only imp 4+ linked persons
"""
import argparse
import json
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.session import SessionLocal

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# --- Config ---
LLM_MODEL = "gpt-5-mini"
NAMES_PER_PROMPT = 50      # Names per API call
CONCURRENCY = 50            # Parallel API calls per wave
CHECKPOINT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "compact_export"


def get_openai_client():
    from openai import OpenAI
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding='utf-8').splitlines():
                if line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found")
    return OpenAI(api_key=api_key)


# --- Data Loading ---

def get_locations_needing_translation(db):
    """Get locations needing KO or JA name."""
    rows = db.execute(text("""
        SELECT id, name, name_ko, name_ja
        FROM locations
        WHERE name IS NOT NULL AND name != ''
          AND (name_ko IS NULL OR name_ko = '' OR name_ja IS NULL OR name_ja = '')
        ORDER BY id
    """)).fetchall()
    return [{"id": r[0], "name": r[1], "name_ko": r[2], "name_ja": r[3]} for r in rows]


def get_persons_needing_translation(db, min_importance=3):
    """Get persons linked to events needing KO or JA name."""
    rows = db.execute(text("""
        SELECT DISTINCT p.id, p.name, p.name_ko, p.name_ja
        FROM persons p
        JOIN event_persons ep ON ep.person_id = p.id
        JOIN events e ON e.id = ep.event_id
        WHERE e.importance >= :min_imp
          AND p.name IS NOT NULL AND p.name != ''
          AND (p.name_ko IS NULL OR p.name_ko = '' OR p.name_ja IS NULL OR p.name_ja = '')
        ORDER BY p.id
    """), {"min_imp": min_importance}).fetchall()
    return [{"id": r[0], "name": r[1], "name_ko": r[2], "name_ja": r[3]} for r in rows]


# --- LLM ---

TRANSLATE_PROMPT = """Translate these {entity_type} names to Korean (한국어) and Japanese (日本語).
Use standard historical naming conventions for each language.
For well-known historical places/persons, use the established translations.
For less known names, transliterate phonetically.

Names to translate:
{names_list}

Respond in JSON format:
{{
  "translations": [
    {{"id": <id>, "ko": "한국어 이름", "ja": "日本語名"}},
    ...
  ]
}}"""


def call_llm_batch(client, batch, entity_type):
    """Translate a batch of names via LLM."""
    names_list = "\n".join(f"- id={item['id']}: {item['name']}" for item in batch)
    prompt = TRANSLATE_PROMPT.format(entity_type=entity_type, names_list=names_list)

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_completion_tokens=16384,
        )
        content = response.choices[0].message.content
        if not content:
            return None, response.usage
        result = json.loads(content)
        return result, response.usage
    except Exception as e:
        print(f"  [ERROR] Batch: {e}")
        return None, None


# --- Checkpoint ---

def load_checkpoint(filepath):
    done = set()
    if filepath.exists():
        for line in filepath.read_text(encoding='utf-8', errors='replace').splitlines():
            if line.strip():
                try:
                    data = json.loads(line)
                    done.add(data.get("id"))
                except (json.JSONDecodeError, ValueError):
                    pass
    return done


def save_checkpoint(filepath, items):
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'a', encoding='utf-8') as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


# --- Apply ---

def apply_translations(db, translations, items_map, table, dry_run=False):
    """Apply translation results to DB."""
    applied = 0
    for t in translations:
        item_id = t.get("id")
        ko = t.get("ko", "").strip()
        ja = t.get("ja", "").strip()
        if not item_id:
            continue

        original = items_map.get(item_id)
        if not original:
            continue

        if dry_run:
            print(f"    [DRY] {original['name']} -> KO:{ko} JA:{ja}")
            applied += 1
            continue

        updates = []
        params = {"eid": item_id}
        if ko and not original.get("name_ko"):
            updates.append("name_ko = :ko")
            params["ko"] = ko
        if ja and not original.get("name_ja"):
            updates.append("name_ja = :ja")
            params["ja"] = ja

        if updates:
            db.execute(text(f"UPDATE {table} SET {', '.join(updates)} WHERE id = :eid"), params)
            applied += 1

    if not dry_run and applied > 0:
        db.commit()
    return applied


# --- Main ---

def run(args):
    client = get_openai_client()
    db = SessionLocal()

    entity_type = args.entity_type
    table = "locations" if entity_type == "locations" else "persons"
    checkpoint_file = CHECKPOINT_DIR / f"name_enrichment_{entity_type}.jsonl"

    print(f"=== Name Translation: {entity_type} ===")
    print(f"Model: {LLM_MODEL}")
    print(f"Batch size: {NAMES_PER_PROMPT} names/prompt, {CONCURRENCY} parallel")

    # Load items
    if entity_type == "locations":
        items = get_locations_needing_translation(db)
    else:
        items = get_persons_needing_translation(db, args.min_importance)

    print(f"Found {len(items)} {entity_type} needing translation")

    if args.test:
        items = items[:args.test]
        print(f"Test mode: {len(items)}")

    # Checkpoint filter
    done = load_checkpoint(checkpoint_file)
    items = [i for i in items if i["id"] not in done]
    print(f"After checkpoint: {len(items)} remaining")

    if not items:
        print("Nothing to do!")
        return

    # Group into batches of NAMES_PER_PROMPT
    batches = []
    for i in range(0, len(items), NAMES_PER_PROMPT):
        batches.append(items[i:i + NAMES_PER_PROMPT])

    total_batches = len(batches)
    print(f"Total API calls needed: {total_batches}")
    print()

    total_input = 0
    total_output = 0
    processed = 0
    errors = 0
    start_time = time.time()

    # Process in waves of CONCURRENCY
    for wave_start in range(0, total_batches, CONCURRENCY):
        wave = batches[wave_start:wave_start + CONCURRENCY]
        wave_num = wave_start // CONCURRENCY + 1
        total_waves = (total_batches + CONCURRENCY - 1) // CONCURRENCY
        print(f"=== Wave {wave_num}/{total_waves} ({len(wave)} API calls, ~{len(wave) * NAMES_PER_PROMPT} names) ===")

        def process_batch(batch):
            return (batch, *call_llm_batch(client, batch, entity_type))

        wave_ok = 0
        wave_err = 0

        with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
            futures = {executor.submit(process_batch, b): b for b in wave}
            for future in as_completed(futures):
                batch, result, usage = future.result()

                if result and "translations" in result:
                    if usage:
                        total_input += usage.prompt_tokens
                        total_output += usage.completion_tokens

                    items_map = {item["id"]: item for item in batch}
                    translations = result["translations"]

                    applied = apply_translations(db, translations, items_map, table, dry_run=args.dry_run)

                    # Save checkpoint
                    save_checkpoint(checkpoint_file, translations)

                    processed += len(translations)
                    wave_ok += 1

                    # Show a sample
                    if translations:
                        sample = translations[0]
                        print(f"  [{processed}/{len(items)}] {sample.get('ko', '?')} / {sample.get('ja', '?')}")
                else:
                    errors += 1
                    wave_err += 1

        elapsed = time.time() - start_time
        rate = processed / elapsed if elapsed > 0 else 0
        eta = (len(items) - processed) / rate if rate > 0 else 0
        cost = (total_input * 0.4 + total_output * 1.6) / 1_000_000
        print(f"  Wave done: {wave_ok} ok, {wave_err} err | Total: {processed}/{len(items)} ({processed/len(items)*100:.1f}%)")
        print(f"  Rate: {rate:.0f}/s | ETA: {eta/60:.1f}min | Cost: ${cost:.2f}")

        if wave_start + CONCURRENCY < total_batches:
            time.sleep(1)

    elapsed = time.time() - start_time
    cost = (total_input * 0.4 + total_output * 1.6) / 1_000_000
    print(f"\n=== Done ===")
    print(f"Processed: {processed} | Errors: {errors}")
    print(f"Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"Tokens: {total_input:,} in + {total_output:,} out")
    print(f"Est. cost: ${cost:.3f}")

    db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch translate names to KO/JA")
    parser.add_argument("entity_type", choices=["locations", "persons"])
    parser.add_argument("--min-importance", type=int, default=3)
    parser.add_argument("--test", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args)
