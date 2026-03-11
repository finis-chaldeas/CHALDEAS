"""
Mythology/Legend Persons — DB Import Script
============================================
mythology_persons_master.yaml 기반으로:
  1. Wikidata API로 엔티티 정보 수집 (labels, sitelinks)
  2. Wikipedia 요약(EN/KO/JA) 일괄 수집
  3. GPT-5.2-chat으로 biography(EN)/role/coordinates 생성
  4. GPT-5.1-chat으로 biography 한국어/일본어 번역
  5. persons + person_details 테이블 INSERT
  6. fgo_servants.person_id 재연결 (fgo_link 항목)

Usage:
    cd backend
    python scripts/fill_mythology_persons.py --fetch               # Wikipedia/Wikidata 수집
    python scripts/fill_mythology_persons.py --generate            # GPT 인리치먼트 (EN)
    python scripts/fill_mythology_persons.py --generate --limit 3  # 테스트 (3배치)
    python scripts/fill_mythology_persons.py --translate           # KO/JA 번역 (gpt-5.1)
    python scripts/fill_mythology_persons.py --translate --limit 3 # 테스트
    python scripts/fill_mythology_persons.py --apply               # DB 적용
    python scripts/fill_mythology_persons.py --apply --dry-run     # 미리보기
    python scripts/fill_mythology_persons.py --status              # 현황
"""

import argparse
import io
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import psycopg2
import psycopg2.extras
import requests
import yaml

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ──────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "chaldeas",
    "user": "chaldeas",
    "password": "chaldeas_dev",
}

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
YAML_FILE = OUTPUT_DIR / "mythology_persons_master.yaml"
WIKI_DATA_FILE = OUTPUT_DIR / "mythology_wiki_data.json"
ENRICHMENT_FILE = OUTPUT_DIR / "mythology_enrichment.json"

GPT_MODEL_GENERATE = "gpt-5.2-chat-latest"  # EN biography generation
GPT_MODEL_TRANSLATE = "gpt-5.1-chat-latest"  # KO/JA translation
BATCH_SIZE = 10

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIPEDIA_API_TMPL = "https://{lang}.wikipedia.org/w/api.php"

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "CHALDEAS/1.0 (history-globe; contact@chaldeas.site)"


# ──────────────────────────────────────────────────────────────
# YAML Loading
# ──────────────────────────────────────────────────────────────

def load_yaml() -> list[dict]:
    """Load mythology_persons_master.yaml"""
    with open(YAML_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["persons"]


# ──────────────────────────────────────────────────────────────
# Phase 1: --fetch (Wikidata + Wikipedia)
# ──────────────────────────────────────────────────────────────

def fetch_wikidata_batch(qids: list[str]) -> dict:
    """Fetch Wikidata entities in batches of 50"""
    results = {}
    for i in range(0, len(qids), 50):
        batch = qids[i:i+50]
        params = {
            "action": "wbgetentities",
            "ids": "|".join(batch),
            "props": "labels|descriptions|sitelinks",
            "languages": "en|ko|ja",
            "sitefilter": "enwiki|kowiki|jawiki",
            "format": "json",
        }
        resp = SESSION.get(WIKIDATA_API, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        entities = data.get("entities", {})
        for qid, entity in entities.items():
            if "missing" in entity:
                continue
            labels = entity.get("labels", {})
            descs = entity.get("descriptions", {})
            sitelinks = entity.get("sitelinks", {})
            results[qid] = {
                "label_en": labels.get("en", {}).get("value"),
                "label_ko": labels.get("ko", {}).get("value"),
                "label_ja": labels.get("ja", {}).get("value"),
                "desc_en": descs.get("en", {}).get("value"),
                "desc_ko": descs.get("ko", {}).get("value"),
                "desc_ja": descs.get("ja", {}).get("value"),
                "enwiki": sitelinks.get("enwiki", {}).get("title"),
                "kowiki": sitelinks.get("kowiki", {}).get("title"),
                "jawiki": sitelinks.get("jawiki", {}).get("title"),
            }
        if i + 50 < len(qids):
            time.sleep(0.5)
    return results


def fetch_wikipedia_extracts(titles: list[str], lang: str = "en") -> dict:
    """Fetch Wikipedia extracts in batches of 50"""
    api_url = WIKIPEDIA_API_TMPL.format(lang=lang)
    results = {}
    for i in range(0, len(titles), 20):
        batch = titles[i:i+20]
        params = {
            "action": "query",
            "titles": "|".join(batch),
            "prop": "extracts|coordinates",
            "exintro": "true",
            "explaintext": "true",
            "exlimit": len(batch),
            "format": "json",
        }
        try:
            resp = SESSION.get(api_url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            for pid, page in pages.items():
                if int(pid) < 0:
                    continue
                title = page.get("title", "")
                extract = page.get("extract", "")
                coords = page.get("coordinates", [{}])
                coord = coords[0] if coords else {}
                results[title] = {
                    "extract": extract[:2000] if extract else None,
                    "lat": coord.get("lat"),
                    "lon": coord.get("lon"),
                }
        except Exception as e:
            print(f"  [WARN] Wikipedia {lang} batch error: {e}")
        if i + 20 < len(titles):
            time.sleep(0.3)
    return results


def cmd_fetch():
    """Fetch Wikidata + Wikipedia data for all persons"""
    persons = load_yaml()
    print("=" * 60)
    print("Mythology Persons — Fetch Wikipedia/Wikidata")
    print("=" * 60)
    print(f"\nTotal persons in YAML: {len(persons)}")

    # Collect wikidata IDs
    qid_map = {}  # qid -> yaml entry index
    for i, p in enumerate(persons):
        qid = p.get("wikidata_id")
        if qid and qid.startswith("Q"):
            qid_map[qid] = i

    print(f"Persons with Wikidata ID: {len(qid_map)}")

    # Step 1: Fetch Wikidata entities
    print(f"\n--- Fetching Wikidata entities ({len(qid_map)} IDs) ---")
    wikidata = fetch_wikidata_batch(list(qid_map.keys()))
    print(f"  Fetched: {len(wikidata)} entities")

    # Step 2: Collect Wikipedia titles by language
    en_titles = {}  # title -> qid
    ko_titles = {}
    ja_titles = {}
    for qid, wd in wikidata.items():
        if wd.get("enwiki"):
            en_titles[wd["enwiki"]] = qid
        if wd.get("kowiki"):
            ko_titles[wd["kowiki"]] = qid
        if wd.get("jawiki"):
            ja_titles[wd["jawiki"]] = qid

    print(f"\nWikipedia articles: EN={len(en_titles)}, KO={len(ko_titles)}, JA={len(ja_titles)}")

    # Step 3: Fetch Wikipedia extracts
    print(f"\n--- Fetching English Wikipedia extracts ---")
    en_extracts = fetch_wikipedia_extracts(list(en_titles.keys()), "en")
    print(f"  Fetched: {len(en_extracts)} articles")

    print(f"\n--- Fetching Korean Wikipedia extracts ---")
    ko_extracts = fetch_wikipedia_extracts(list(ko_titles.keys()), "ko")
    print(f"  Fetched: {len(ko_extracts)} articles")

    print(f"\n--- Fetching Japanese Wikipedia extracts ---")
    ja_extracts = fetch_wikipedia_extracts(list(ja_titles.keys()), "ja")
    print(f"  Fetched: {len(ja_extracts)} articles")

    # Step 4: Combine into per-person records
    wiki_data = {}
    for qid, wd in wikidata.items():
        entry = {**wd}
        # EN extract
        en_title = wd.get("enwiki")
        if en_title and en_title in en_extracts:
            entry["extract_en"] = en_extracts[en_title].get("extract")
            if en_extracts[en_title].get("lat"):
                entry["coord_lat"] = en_extracts[en_title]["lat"]
                entry["coord_lon"] = en_extracts[en_title]["lon"]
        # KO extract
        ko_title = wd.get("kowiki")
        if ko_title and ko_title in ko_extracts:
            entry["extract_ko"] = ko_extracts[ko_title].get("extract")
        # JA extract
        ja_title = wd.get("jawiki")
        if ja_title and ja_title in ja_extracts:
            entry["extract_ja"] = ja_extracts[ja_title].get("extract")

        wiki_data[qid] = entry

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(WIKI_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(wiki_data, f, ensure_ascii=False, indent=2)

    # Stats
    has_en = sum(1 for v in wiki_data.values() if v.get("extract_en"))
    has_ko = sum(1 for v in wiki_data.values() if v.get("extract_ko"))
    has_ja = sum(1 for v in wiki_data.values() if v.get("extract_ja"))
    has_coord = sum(1 for v in wiki_data.values() if v.get("coord_lat"))

    print(f"\n{'='*60}")
    print(f"Wiki data saved: {WIKI_DATA_FILE}")
    print(f"  Total: {len(wiki_data)} entities")
    print(f"  EN extracts: {has_en}")
    print(f"  KO extracts: {has_ko}")
    print(f"  JA extracts: {has_ja}")
    print(f"  Coordinates: {has_coord}")
    print(f"\nPersons without Wikidata ID: {len(persons) - len(qid_map)}")


# ──────────────────────────────────────────────────────────────
# Phase 2: --generate (GPT enrichment)
# ──────────────────────────────────────────────────────────────

ENRICHMENT_SYSTEM = """\
You are a historical/mythological research assistant for the CHALDEAS project — \
a 3D globe-based history exploration system.

For each mythological/legendary/fictional person, generate enriched metadata \
using the provided Wikipedia context and YAML metadata.

## Output Format
Return a JSON object {"persons": [...]} with one entry per person input, in same order:
{
  "name": "<English canonical name>",
  "name_ko": "<Korean name>",
  "name_ja": "<Japanese name (kanji/kana)>",
  "biography": "<4-6 sentences, 400-600 characters. Cover: who they are, their major deeds/role in mythology, cultural significance, and key relationships. Use Wikipedia as primary source. Factual tone, no pop culture.>",
  "role": "<brief role: king, war goddess, trickster god, thunder god, epic hero, etc.>",
  "domain": "<political|military|religion|myth|arts|philosophy|science|exploration|other>",
  "era": "<Bronze Age|Iron Age|Classical|Hellenistic|Early Medieval|Medieval|Renaissance|Early Modern|Modern|Ancient|Prehistoric>",
  "region_modern": "<modern country: Greece, Norway, India, Iraq, Egypt, etc.>",
  "region_historical": "<ancient region: Olympus, Asgard, Ulster, Uruk, Thebes, etc.>",
  "latitude": <float, approximate coords of primary associated location>,
  "longitude": <float>
}

## Biography Length & Style Guide
Target: **400-600 characters** (similar to event descriptions in the system).
Structure: Origin/identity → Major deeds/mythology → Cultural significance → Key relationships.
Example (Zeus, 520 chars):
"Zeus is the supreme deity of the Greek pantheon, ruling as king of the Olympian gods from \
Mount Olympus. Attested in Mycenaean Linear B tablets as 'di-we,' his worship spans from the \
Bronze Age through late antiquity. He overthrew his father Kronos and the Titans to establish \
the current divine order, then divided the cosmos with his brothers Poseidon and Hades. \
As god of the sky, thunder, and justice, Zeus presided over both divine and mortal affairs, \
and his many liaisons produced heroes including Heracles, Perseus, and Helen of Troy."

## Rules
- biography in **English only** (translation is done separately)
- biography MUST be factual (mythology/history), not FGO or pop culture
- If Wikipedia extract is provided, use it as primary source
- If no Wikipedia extract, use your knowledge
- domain "myth" for deities/mythological beings, "religion" for religious figures
- For mythological locations: Olympus→37.97/22.35 (Greece), Asgard→59.33/18.07 (Scandinavia), etc.
- era should reflect the mythology's cultural context, not modern classifications
"""


TRANSLATE_SYSTEM = """\
You are a professional translator for the CHALDEAS project — \
a 3D globe-based history exploration system.

Translate the given English biographies of mythological/legendary/fictional persons \
into Korean and Japanese.

## Output Format
Return a JSON object {"translations": [...]} with one entry per input, in same order:
{
  "name": "<person name (English, for matching)>",
  "biography_ko": "<Korean translation, natural Korean style, 400-600 characters>",
  "biography_ja": "<Japanese translation, natural Japanese style, appropriate kanji/kana>"
}

## Translation Rules
- Maintain factual accuracy — do not add, remove, or alter historical/mythological content
- Use natural, fluent target language (not machine-translation style)
- Preserve the same structure: origin → deeds → significance → relationships
- Korean: **~다 서술체** (예: "~이다", "~했다", "~전해진다"). 존댓말/합쇼체 금지.
- Japanese: である調 (dearu-chō), academic tone
- Keep proper nouns in their standard localized forms (e.g., Zeus→제우스/ゼウス)
- Match the length of the original (~400-600 chars per translation)
"""


def init_openai():
    """Initialize OpenAI client"""
    from dotenv import load_dotenv
    import os
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(f"OPENAI_API_KEY not found in {env_path}")
    from openai import OpenAI
    return OpenAI(api_key=api_key)


def build_batch_prompt(batch: list[dict], wiki_data: dict) -> str:
    """Build GPT prompt for a batch of persons"""
    lines = [f"Enrich the following {len(batch)} mythological/legendary/fictional persons.\n"]

    for i, p in enumerate(batch, 1):
        lines.append(f"--- Person {i} ---")
        lines.append(f"Name: {p['name']}")
        lines.append(f"Korean: {p.get('name_ko', '?')}")
        lines.append(f"Category: {p.get('category', '?')}")
        lines.append(f"Certainty: {p.get('certainty', '?')}")
        lines.append(f"Dates: {p.get('birth_year', '?')} ~ {p.get('death_year', '?')}")
        if p.get("subcategory"):
            lines.append(f"Subcategory: {p['subcategory']}")
        if p.get("notes"):
            lines.append(f"Notes: {p['notes']}")

        # Add Wikipedia context if available
        qid = p.get("wikidata_id")
        if qid and qid in wiki_data:
            wd = wiki_data[qid]
            extract = wd.get("extract_en", "")
            if extract:
                # Truncate to ~500 chars for prompt efficiency
                if len(extract) > 500:
                    extract = extract[:500] + "..."
                lines.append(f"Wikipedia EN: {extract}")
            if wd.get("label_ja"):
                lines.append(f"Japanese name (Wikidata): {wd['label_ja']}")
            if wd.get("extract_ko"):
                ko_ext = wd["extract_ko"]
                if len(ko_ext) > 300:
                    ko_ext = ko_ext[:300] + "..."
                lines.append(f"Wikipedia KO: {ko_ext}")
        lines.append("")

    lines.append(
        'Return a JSON object {"persons": [...]} with one entry per person above, '
        "in the same order. Follow the output format exactly."
    )
    return "\n".join(lines)


def call_gpt(client, model: str, system: str, prompt: str,
             batch_num: int, max_tokens: int = 4096) -> dict | list | None:
    """Call GPT and return parsed JSON response"""
    # Pricing per 1M tokens
    pricing = {
        "gpt-5.2-chat-latest": (1.75, 14.00),
        "gpt-5.1-chat-latest": (1.25, 10.00),
    }
    in_price, out_price = pricing.get(model, (1.75, 14.00))

    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_completion_tokens=max_tokens,
            )

            content = resp.choices[0].message.content
            if not content:
                print(f"  [WARN] Batch {batch_num}: empty response (attempt {attempt+1})")
                continue

            data = json.loads(content)

            # Cost calc
            usage = resp.usage
            input_cost = (usage.prompt_tokens / 1_000_000) * in_price
            output_cost = (usage.completion_tokens / 1_000_000) * out_price
            total_cost = input_cost + output_cost
            print(f"  Batch {batch_num}: "
                  f"tokens={usage.prompt_tokens}+{usage.completion_tokens}, "
                  f"cost=${total_cost:.3f}")

            return data

        except json.JSONDecodeError as e:
            print(f"  [ERROR] Batch {batch_num}: JSON parse error (attempt {attempt+1}): {e}")
            if attempt < 2:
                time.sleep(2)
        except Exception as e:
            print(f"  [ERROR] Batch {batch_num}: {e} (attempt {attempt+1})")
            if attempt < 2:
                time.sleep(5)

    print(f"  [FAIL] Batch {batch_num}: all attempts failed")
    return None


def call_gpt_batch(client, batch: list[dict], wiki_data: dict, batch_num: int) -> list[dict]:
    """Call GPT for a batch of persons (enrichment)"""
    prompt = build_batch_prompt(batch, wiki_data)
    data = call_gpt(client, GPT_MODEL_GENERATE, ENRICHMENT_SYSTEM, prompt, batch_num)

    if not data:
        return []

    results = data.get("persons", data.get("results", []))
    if isinstance(data, list):
        results = data

    if len(results) != len(batch):
        print(f"  [WARN] Batch {batch_num}: expected {len(batch)}, got {len(results)}")

    return results if results else []


def cmd_generate(limit: int | None = None, resume: bool = False):
    """Generate enrichment data using GPT"""
    persons = load_yaml()

    # Load wiki data
    wiki_data = {}
    if WIKI_DATA_FILE.exists():
        with open(WIKI_DATA_FILE, encoding="utf-8") as f:
            wiki_data = json.load(f)
        print(f"Loaded wiki data: {len(wiki_data)} entities")
    else:
        print("[WARN] No wiki data found. Run --fetch first for better results.")

    print("=" * 60)
    print("Mythology Persons — GPT Enrichment")
    print("=" * 60)
    print(f"\nTotal persons: {len(persons)}")

    # Load existing enrichment if resuming
    existing = {}
    if resume and ENRICHMENT_FILE.exists():
        with open(ENRICHMENT_FILE, encoding="utf-8") as f:
            existing_list = json.load(f)
        existing = {e["name"]: e for e in existing_list}
        print(f"Loaded {len(existing)} existing enrichment entries")

    # Filter out already processed
    to_process = []
    for p in persons:
        if resume and p["name"] in existing:
            continue
        to_process.append(p)

    print(f"To process: {len(to_process)}")

    if not to_process:
        print("\nNothing to process!")
        return

    # Batch processing
    client = init_openai()
    all_results = list(existing.values())
    batches = [to_process[i:i+BATCH_SIZE] for i in range(0, len(to_process), BATCH_SIZE)]

    if limit:
        batches = batches[:limit]
        print(f"Limited to {limit} batches ({min(limit * BATCH_SIZE, len(to_process))} persons)")

    total_cost = 0.0
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for batch_num, batch in enumerate(batches, 1):
        print(f"\n--- Batch {batch_num}/{len(batches)} ({len(batch)} persons) ---")
        names = [p["name"] for p in batch]
        print(f"  {', '.join(names[:5])}{'...' if len(names) > 5 else ''}")

        results = call_gpt_batch(client, batch, wiki_data, batch_num)

        if results:
            for i, r in enumerate(results):
                # Merge YAML metadata into GPT result
                if i < len(batch):
                    yaml_entry = batch[i]
                    r["_yaml"] = {
                        "name": yaml_entry["name"],
                        "name_ko": yaml_entry.get("name_ko"),
                        "certainty": yaml_entry.get("certainty"),
                        "birth_year": yaml_entry.get("birth_year"),
                        "death_year": yaml_entry.get("death_year"),
                        "importance": yaml_entry.get("importance"),
                        "category": yaml_entry.get("category"),
                        "wikidata_id": yaml_entry.get("wikidata_id"),
                        "status": yaml_entry.get("status"),
                        "fgo_servant": yaml_entry.get("fgo_servant", False),
                        "fgo_servant_name": yaml_entry.get("fgo_servant_name"),
                        "existing_person_id": yaml_entry.get("existing_person_id"),
                    }
                    # Use YAML name as key
                    r["name"] = yaml_entry["name"]
                all_results.append(r)

        # Save incrementally
        with open(ENRICHMENT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        # Rate limiting
        if batch_num < len(batches):
            time.sleep(1)

    # Summary
    print(f"\n{'='*60}")
    print(f"Enrichment complete: {len(all_results)} entries")
    print(f"Saved to: {ENRICHMENT_FILE}")


# ──────────────────────────────────────────────────────────────
# Phase 2.5: --translate (KO/JA via gpt-5.1)
# ──────────────────────────────────────────────────────────────

TRANSLATE_BATCH_SIZE = 10


def build_translate_prompt(batch: list[dict]) -> str:
    """Build translation prompt for a batch of biographies"""
    lines = [f"Translate the following {len(batch)} biographies to Korean and Japanese.\n"]

    for i, entry in enumerate(batch, 1):
        name = entry.get("name", "?")
        bio = entry.get("biography", "")
        lines.append(f"--- Person {i}: {name} ---")
        lines.append(bio)
        lines.append("")

    lines.append(
        'Return a JSON object {"translations": [...]} with one entry per person above, '
        "in the same order. Include the person's name for matching."
    )
    return "\n".join(lines)


def cmd_translate(limit: int | None = None):
    """Translate biographies to KO/JA using gpt-5.1"""
    if not ENRICHMENT_FILE.exists():
        print(f"ERROR: {ENRICHMENT_FILE} not found. Run --generate first.")
        return

    with open(ENRICHMENT_FILE, encoding="utf-8") as f:
        enrichment = json.load(f)

    print("=" * 60)
    print("Mythology Persons — Translate (KO/JA)")
    print(f"Model: {GPT_MODEL_TRANSLATE}")
    print("=" * 60)

    # Filter: only entries with biography but missing biography_ko or biography_ja
    to_translate = []
    for entry in enrichment:
        if entry.get("biography") and (not entry.get("biography_ko") or not entry.get("biography_ja")):
            to_translate.append(entry)

    print(f"\nTotal enrichment entries: {len(enrichment)}")
    print(f"Need translation: {len(to_translate)}")

    if not to_translate:
        print("\nAll entries already have KO/JA translations!")
        return

    client = init_openai()
    batches = [to_translate[i:i+TRANSLATE_BATCH_SIZE]
               for i in range(0, len(to_translate), TRANSLATE_BATCH_SIZE)]

    if limit:
        batches = batches[:limit]
        print(f"Limited to {limit} batches ({min(limit * TRANSLATE_BATCH_SIZE, len(to_translate))} persons)")

    # Index enrichment by name for merging
    enrich_by_name = {}
    for entry in enrichment:
        name = entry.get("name") or entry.get("_yaml", {}).get("name", "?")
        enrich_by_name[name] = entry

    translated_count = 0

    for batch_num, batch in enumerate(batches, 1):
        names = [e.get("name", "?") for e in batch]
        print(f"\n--- Batch {batch_num}/{len(batches)} ({len(batch)} persons) ---")
        print(f"  {', '.join(names[:5])}{'...' if len(names) > 5 else ''}")

        prompt = build_translate_prompt(batch)
        data = call_gpt(client, GPT_MODEL_TRANSLATE, TRANSLATE_SYSTEM, prompt,
                        batch_num, max_tokens=4096)

        if data:
            translations = data.get("translations", [])
            if isinstance(data, list):
                translations = data

            for i, tr in enumerate(translations):
                # Match by index (same order) or name
                if i < len(batch):
                    target_name = batch[i].get("name", "?")
                else:
                    target_name = tr.get("name", "?")

                if target_name in enrich_by_name:
                    enrich_by_name[target_name]["biography_ko"] = tr.get("biography_ko")
                    enrich_by_name[target_name]["biography_ja"] = tr.get("biography_ja")
                    translated_count += 1

        # Save incrementally
        with open(ENRICHMENT_FILE, "w", encoding="utf-8") as f:
            json.dump(enrichment, f, ensure_ascii=False, indent=2)

        if batch_num < len(batches):
            time.sleep(1)

    print(f"\n{'='*60}")
    print(f"Translation complete: {translated_count} entries translated")
    print(f"Saved to: {ENRICHMENT_FILE}")


# ──────────────────────────────────────────────────────────────
# Phase 3: --apply
# ──────────────────────────────────────────────────────────────

def cmd_apply(dry_run: bool = False):
    """Apply enrichment to DB"""
    if not ENRICHMENT_FILE.exists():
        print(f"ERROR: {ENRICHMENT_FILE} not found. Run --generate first.")
        return

    with open(ENRICHMENT_FILE, encoding="utf-8") as f:
        enrichment = json.load(f)

    # Load wiki data for coordinates fallback
    wiki_data = {}
    if WIKI_DATA_FILE.exists():
        with open(WIKI_DATA_FILE, encoding="utf-8") as f:
            wiki_data = json.load(f)

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    print("=" * 60)
    print("Mythology Persons — Apply to DB")
    print("=" * 60)

    # Current stats
    cur.execute("SELECT count(*) FROM persons WHERE certainty IN ('mythological','legendary','fictional')")
    before_myth = cur.fetchone()[0]
    print(f"Before: {before_myth} myth/legend/fiction persons in DB\n")

    stats = {
        "persons_created": 0, "persons_found": 0, "persons_updated": 0,
        "details_created": 0, "locations_linked": 0,
        "fgo_linked": 0, "skipped": 0, "errors": 0,
    }

    for entry in enrichment:
        yaml_meta = entry.get("_yaml", {})
        name = entry.get("name") or yaml_meta.get("name", "?")
        wikidata_id = yaml_meta.get("wikidata_id")
        status = yaml_meta.get("status", "new")
        certainty = yaml_meta.get("certainty", "mythological")
        birth_year = yaml_meta.get("birth_year")
        death_year = yaml_meta.get("death_year")
        importance_grade = yaml_meta.get("importance", "B")

        # Importance score from grade
        imp_score = {"A": 65, "B": 60, "C": 55}.get(importance_grade, 60)
        if certainty == "fictional":
            imp_score = min(imp_score, 50)

        # ── Step 1: Find or create person ──
        person_id = None

        # Handle "update" status (existing person needs dates/certainty)
        if status == "update":
            existing_id = yaml_meta.get("existing_person_id")
            if existing_id:
                person_id = existing_id
                if not dry_run:
                    cur.execute("""
                        UPDATE persons SET
                            certainty = %s, birth_year = %s, death_year = %s,
                            name_ko = COALESCE(name_ko, %s),
                            name_ja = COALESCE(name_ja, %s),
                            role = COALESCE(role, %s),
                            domain = COALESCE(domain, %s),
                            updated_at = NOW()
                        WHERE id = %s
                    """, (
                        certainty, birth_year, death_year,
                        entry.get("name_ko") or yaml_meta.get("name_ko"),
                        entry.get("name_ja"),
                        entry.get("role"),
                        entry.get("domain"),
                        person_id,
                    ))
                print(f"  UPDATE {name:35s} → id={person_id}")
                stats["persons_updated"] += 1
            else:
                print(f"  [SKIP] {name:35s} (update but no existing_person_id)")
                stats["skipped"] += 1
                continue

        # Check by wikidata_id
        if not person_id and wikidata_id:
            cur.execute("SELECT id FROM persons WHERE wikidata_id = %s", (wikidata_id,))
            row = cur.fetchone()
            if row:
                person_id = row[0]
                print(f"  FOUND  {name:35s} → id={person_id} (wikidata={wikidata_id})")
                stats["persons_found"] += 1

        # Check by exact name
        if not person_id:
            cur.execute(
                "SELECT id FROM persons WHERE name = %s AND certainty IN ('mythological','legendary','fictional')",
                (name,)
            )
            row = cur.fetchone()
            if row:
                person_id = row[0]
                print(f"  FOUND  {name:35s} → id={person_id} (name)")
                stats["persons_found"] += 1

        # Create new person
        if not person_id:
            if dry_run:
                print(f"  [DRY]  CREATE {name:35s} ({certainty})")
                stats["persons_created"] += 1
            else:
                try:
                    name_ko = entry.get("name_ko") or yaml_meta.get("name_ko")
                    name_ja = entry.get("name_ja")
                    role = entry.get("role", "")
                    domain = entry.get("domain")

                    cur.execute("""
                        INSERT INTO persons (
                            name, name_ko, name_ja, wikidata_id,
                            birth_year, death_year,
                            role, domain, certainty,
                            importance_score, global_score
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        name, name_ko, name_ja, wikidata_id,
                        birth_year, death_year,
                        role, domain, certainty,
                        imp_score, imp_score,
                    ))
                    person_id = cur.fetchone()[0]
                    print(f"  CREATE {name:35s} → id={person_id} ({certainty})")
                    stats["persons_created"] += 1
                except Exception as e:
                    print(f"  ERROR  {name:35s}: {e}")
                    stats["errors"] += 1
                    conn.rollback()
                    continue

        # ── Step 2: Create person_details ──
        if person_id and not dry_run:
            biography = entry.get("biography")
            if biography:
                try:
                    cur.execute("SELECT person_id FROM person_details WHERE person_id = %s", (person_id,))
                    if not cur.fetchone():
                        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
                        biography_ko = entry.get("biography_ko")
                        biography_ja = entry.get("biography_ja")
                        era = entry.get("era")

                        wikipedia_url = None
                        if wikidata_id:
                            # Use actual Wikipedia URL if available
                            wd = wiki_data.get(wikidata_id, {})
                            enwiki_title = wd.get("enwiki")
                            if enwiki_title:
                                wikipedia_url = f"https://en.wikipedia.org/wiki/{enwiki_title.replace(' ', '_')}"
                            else:
                                wikipedia_url = f"https://www.wikidata.org/wiki/{wikidata_id}"

                        cur.execute("""
                            INSERT INTO person_details (
                                person_id, slug, biography, biography_ko, biography_ja,
                                biography_source, era, wikipedia_url
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            person_id, slug, biography, biography_ko, biography_ja,
                            "gpt-5.2+wikipedia", era, wikipedia_url,
                        ))
                        stats["details_created"] += 1
                except Exception as e:
                    if "duplicate" not in str(e).lower():
                        print(f"    [WARN] Details for {name}: {e}")
                    conn.rollback()

        # ── Step 3: Link birthplace ──
        if person_id and not dry_run:
            lat = entry.get("latitude")
            lon = entry.get("longitude")
            # Fallback to wiki coordinates
            if not lat and wikidata_id:
                wd = wiki_data.get(wikidata_id, {})
                lat = wd.get("coord_lat")
                lon = wd.get("coord_lon")

            if lat and lon:
                try:
                    cur.execute("SELECT birthplace_id FROM persons WHERE id = %s", (person_id,))
                    row = cur.fetchone()
                    if row and not row[0]:
                        cur.execute("""
                            SELECT id, name,
                                   (6371 * acos(
                                       cos(radians(%s)) * cos(radians(latitude)) *
                                       cos(radians(longitude) - radians(%s)) +
                                       sin(radians(%s)) * sin(radians(latitude))
                                   )) AS distance_km
                            FROM locations
                            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                            ORDER BY (latitude - %s)^2 + (longitude - %s)^2
                            LIMIT 1
                        """, (lat, lon, lat, lat, lon))
                        loc = cur.fetchone()
                        if loc and loc["distance_km"] < 200:
                            cur.execute(
                                "UPDATE persons SET birthplace_id = %s WHERE id = %s",
                                (loc["id"], person_id)
                            )
                            stats["locations_linked"] += 1
                except Exception:
                    pass

        # ── Step 4: Link FGO servant ──
        if person_id and yaml_meta.get("fgo_servant") and not dry_run:
            fgo_name = yaml_meta.get("fgo_servant_name") or name
            try:
                # Find matching servant(s)
                cur.execute("""
                    SELECT id, name FROM fgo_servants
                    WHERE person_id IS NULL
                    AND (name ILIKE %s OR name ILIKE %s)
                """, (f"%{fgo_name}%", f"%{name}%"))
                servants = cur.fetchall()
                for servant in servants:
                    cur.execute(
                        "UPDATE fgo_servants SET person_id = %s, updated_at = NOW() WHERE id = %s",
                        (person_id, servant["id"])
                    )
                    print(f"    FGO LINK: {servant['name']} → person_id={person_id}")
                    stats["fgo_linked"] += 1
            except Exception as e:
                print(f"    [WARN] FGO link for {name}: {e}")

        # Commit periodically
        if not dry_run and stats["persons_created"] % 50 == 0 and stats["persons_created"] > 0:
            conn.commit()

    if not dry_run:
        conn.commit()

    # Final report
    cur.execute("SELECT count(*) FROM persons WHERE certainty IN ('mythological','legendary','fictional')")
    after_myth = cur.fetchone()[0]

    print(f"\n{'='*60}")
    print(f"Results:")
    print(f"  Persons created:  {stats['persons_created']}")
    print(f"  Persons found:    {stats['persons_found']}")
    print(f"  Persons updated:  {stats['persons_updated']}")
    print(f"  Details created:  {stats['details_created']}")
    print(f"  Locations linked: {stats['locations_linked']}")
    print(f"  FGO linked:       {stats['fgo_linked']}")
    print(f"  Skipped:          {stats['skipped']}")
    print(f"  Errors:           {stats['errors']}")
    print(f"  Myth persons: {before_myth} → {after_myth}")
    if dry_run:
        print("  (DRY RUN - no changes made)")

    conn.close()


# ──────────────────────────────────────────────────────────────
# --status
# ──────────────────────────────────────────────────────────────

def cmd_status():
    """Show current pipeline status"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    print("=" * 60)
    print("Mythology Persons — Status")
    print("=" * 60)

    # YAML
    if YAML_FILE.exists():
        persons = load_yaml()
        from collections import Counter
        cats = Counter(p["category"] for p in persons)
        statuses = Counter(p["status"] for p in persons)
        print(f"\nYAML: {len(persons)} persons")
        print(f"  By status: {dict(statuses)}")
    else:
        print(f"\nYAML: NOT FOUND")

    # Wiki data
    if WIKI_DATA_FILE.exists():
        with open(WIKI_DATA_FILE, encoding="utf-8") as f:
            wd = json.load(f)
        has_en = sum(1 for v in wd.values() if v.get("extract_en"))
        has_ko = sum(1 for v in wd.values() if v.get("extract_ko"))
        print(f"\nWiki data: {len(wd)} entities (EN={has_en}, KO={has_ko})")
    else:
        print(f"\nWiki data: NOT FOUND (run --fetch)")

    # Enrichment
    if ENRICHMENT_FILE.exists():
        with open(ENRICHMENT_FILE, encoding="utf-8") as f:
            enrich = json.load(f)
        has_bio = sum(1 for e in enrich if e.get("biography"))
        print(f"\nEnrichment: {len(enrich)} entries ({has_bio} with biography)")
    else:
        print(f"\nEnrichment: NOT FOUND (run --generate)")

    # DB status
    cur.execute("""
        SELECT certainty, count(*)
        FROM persons
        WHERE certainty IN ('mythological','legendary','fictional')
        GROUP BY certainty ORDER BY count(*) DESC
    """)
    rows = cur.fetchall()
    total_myth = sum(r[1] for r in rows)
    print(f"\nDB myth/legend/fiction: {total_myth}")
    for r in rows:
        print(f"  {r[0]:15s} {r[1]}")

    conn.close()


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Mythology/Legend Persons -> DB Import (Wikidata + GPT)"
    )
    parser.add_argument("--fetch", action="store_true",
                        help="Wikidata + Wikipedia data fetch")
    parser.add_argument("--generate", action="store_true",
                        help="GPT enrichment generate (EN biography, gpt-5.2)")
    parser.add_argument("--translate", action="store_true",
                        help="Translate biographies to KO/JA (gpt-5.1)")
    parser.add_argument("--apply", action="store_true",
                        help="DB apply")
    parser.add_argument("--status", action="store_true",
                        help="Status check")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview (no DB changes)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit GPT batches (test)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from existing enrichment")
    args = parser.parse_args()

    if args.status:
        cmd_status()
    elif args.fetch:
        cmd_fetch()
    elif args.generate:
        cmd_generate(limit=args.limit, resume=args.resume)
    elif args.translate:
        cmd_translate(limit=args.limit)
    elif args.apply:
        cmd_apply(dry_run=args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
