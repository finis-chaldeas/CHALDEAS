"""
Enhance Person Biographies — Wikipedia + Papers + GPT
=====================================================
기존 wikidata 스켈레톤 biography (~32자)를 400-600자 양질 에세이로 업그레이드.

Sources:
  1. Wikipedia EN/KO/JA extracts (Wikidata sitelinks)
  2. Academic paper abstracts (OpenAlex, via event_persons)
  3. Related event descriptions (event_details)
  4. GPT-5.2-chat → EN biography
  5. GPT-5.1-chat → KO/JA translation

Usage:
    cd backend
    python scripts/enhance_person_bios.py --fetch --min-imp 95       # Wikipedia 수집 (530명)
    python scripts/enhance_person_bios.py --generate --min-imp 95    # GPT 인리치먼트 (EN)
    python scripts/enhance_person_bios.py --generate --limit 1       # 테스트 (1배치=5명)
    python scripts/enhance_person_bios.py --translate --min-imp 95   # KO/JA 번역
    python scripts/enhance_person_bios.py --apply --min-imp 95       # DB 적용
    python scripts/enhance_person_bios.py --apply --dry-run          # 미리보기
    python scripts/enhance_person_bios.py --status                   # 현황
"""

import argparse
import io
import json
import sys
import time
from pathlib import Path

import psycopg2
import psycopg2.extras
import requests

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
OUTPUT_DIR = SCRIPT_DIR / "output" / "person_bios"

GPT_MODEL_GENERATE = "gpt-5.2-chat-latest"
GPT_MODEL_TRANSLATE = "gpt-5.1-chat-latest"
BATCH_SIZE = 5

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIPEDIA_API_TMPL = "https://{lang}.wikipedia.org/w/api.php"

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "CHALDEAS/1.0 (history-globe; contact@chaldeas.site)"


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def get_output_paths(min_imp: int, fgo_only: bool = False):
    """Return file paths for a given run."""
    tag = "fgo" if fgo_only else f"imp{min_imp}"
    return {
        "targets": OUTPUT_DIR / f"targets_{tag}.json",
        "wiki": OUTPUT_DIR / f"wiki_data_{tag}.json",
        "enrichment": OUTPUT_DIR / f"enrichment_{tag}.json",
    }


def init_openai():
    from dotenv import load_dotenv
    import os
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not found")
    from openai import OpenAI
    return OpenAI(api_key=api_key)


def call_gpt(client, model: str, system: str, prompt: str,
             batch_num: int, max_tokens: int = 3000) -> dict | None:
    """Call GPT and return parsed JSON response."""
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
            if not content or len(content) < 50:
                print(f"  [WARN] Batch {batch_num}: short response ({len(content or '')} chars), attempt {attempt+1}")
                if attempt < 2:
                    time.sleep(3)
                continue

            data = json.loads(content)
            usage = resp.usage
            cost = (usage.prompt_tokens / 1e6) * in_price + (usage.completion_tokens / 1e6) * out_price
            print(f"  Batch {batch_num}: tokens={usage.prompt_tokens}+{usage.completion_tokens}, cost=${cost:.3f}")
            return data

        except json.JSONDecodeError as e:
            print(f"  [ERROR] Batch {batch_num}: JSON parse (attempt {attempt+1}): {e}")
            if attempt < 2:
                time.sleep(2)
        except Exception as e:
            print(f"  [ERROR] Batch {batch_num}: {e} (attempt {attempt+1})")
            if attempt < 2:
                time.sleep(5)

    print(f"  [FAIL] Batch {batch_num}: all attempts failed")
    return None


# ──────────────────────────────────────────────────────────────
# Phase 0: Target selection from DB
# ──────────────────────────────────────────────────────────────

def select_targets(min_imp: int, fgo_only: bool = False) -> list[dict]:
    """Select persons from DB that need biography upgrade."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if fgo_only:
        cur.execute("""
            SELECT DISTINCT p.id, p.name, p.name_ko, p.name_ja, p.wikidata_id,
                   p.importance_score, p.global_score, p.certainty,
                   p.birth_year, p.death_year, p.role, p.domain,
                   pd.biography, pd.biography_source, pd.era,
                   length(pd.biography) as bio_len
            FROM persons p
            JOIN person_details pd ON pd.person_id = p.id
            JOIN fgo_servants fs ON fs.person_id = p.id
            WHERE p.wikidata_id IS NOT NULL
              AND (pd.biography_source = 'wikidata'
                   OR pd.biography IS NULL
                   OR length(pd.biography) < 150)
            ORDER BY p.importance_score DESC, p.global_score DESC NULLS LAST
        """)
    else:
        cur.execute("""
            SELECT p.id, p.name, p.name_ko, p.name_ja, p.wikidata_id,
                   p.importance_score, p.global_score, p.certainty,
                   p.birth_year, p.death_year, p.role, p.domain,
                   pd.biography, pd.biography_source, pd.era,
                   length(pd.biography) as bio_len
            FROM persons p
            JOIN person_details pd ON pd.person_id = p.id
            WHERE p.importance_score >= %s
              AND p.wikidata_id IS NOT NULL
              AND (pd.biography_source = 'wikidata'
                   OR pd.biography IS NULL
                   OR length(pd.biography) < 150)
            ORDER BY p.importance_score DESC, p.global_score DESC NULLS LAST
        """, (min_imp,))

    targets = []
    for row in cur.fetchall():
        targets.append({
            "person_id": row["id"],
            "name": row["name"],
            "name_ko": row["name_ko"],
            "name_ja": row["name_ja"],
            "wikidata_id": row["wikidata_id"],
            "importance_score": row["importance_score"],
            "global_score": row["global_score"],
            "certainty": row["certainty"],
            "birth_year": row["birth_year"],
            "death_year": row["death_year"],
            "role": row["role"],
            "domain": row["domain"],
            "current_bio": row["biography"],
            "current_bio_len": row["bio_len"] or 0,
            "era": row["era"],
        })

    conn.close()
    return targets


def load_event_context(person_ids: list[int]) -> dict[int, list[dict]]:
    """Load related events + descriptions for persons."""
    if not person_ids:
        return {}

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        SELECT ep.person_id, e.id as event_id, e.title as event_name,
               e.date_start, e.date_end,
               ed.description
        FROM event_persons ep
        JOIN events e ON e.id = ep.event_id
        LEFT JOIN event_details ed ON ed.event_id = e.id
        WHERE ep.person_id = ANY(%s)
        ORDER BY ep.person_id, e.importance DESC NULLS LAST, e.date_start
    """, (person_ids,))

    result: dict[int, list[dict]] = {}
    for row in cur.fetchall():
        pid = row["person_id"]
        if pid not in result:
            result[pid] = []
        if len(result[pid]) < 5:  # Max 5 events per person
            result[pid].append({
                "event_id": row["event_id"],
                "name": row["event_name"],
                "date_start": row["date_start"],
                "date_end": row["date_end"],
                "description": (row["description"] or "")[:300],
            })

    conn.close()
    return result


def load_paper_context(event_context: dict[int, list[dict]]) -> dict[int, str]:
    """Load academic papers for person's events and format for prompt."""
    sys.path.insert(0, str(SCRIPT_DIR))
    from paper_utils import get_papers_for_events, format_papers_for_prompt

    # Collect all event IDs across all persons
    all_event_ids = set()
    person_event_ids: dict[int, list[int]] = {}
    for pid, events in event_context.items():
        eids = [e["event_id"] for e in events]
        person_event_ids[pid] = eids
        all_event_ids.update(eids)

    if not all_event_ids:
        return {}

    # Batch fetch papers
    event_papers = get_papers_for_events(list(all_event_ids), max_per_event=2)

    # Aggregate per person
    result: dict[int, str] = {}
    for pid, eids in person_event_ids.items():
        papers = []
        for eid in eids:
            papers.extend(event_papers.get(eid, []))
        if papers:
            # Deduplicate and take top 3
            seen = set()
            unique = []
            for p in papers:
                oa_id = p.get("openalex_id", "")
                if oa_id not in seen:
                    seen.add(oa_id)
                    unique.append(p)
            unique.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
            result[pid] = format_papers_for_prompt(unique[:3], max_chars=1500)

    return result


# ──────────────────────────────────────────────────────────────
# Phase 1: --fetch (Wikipedia)
# ──────────────────────────────────────────────────────────────

def fetch_wikidata_batch(qids: list[str]) -> dict:
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
        for qid, entity in data.get("entities", {}).items():
            if "missing" in entity:
                continue
            labels = entity.get("labels", {})
            sitelinks = entity.get("sitelinks", {})
            results[qid] = {
                "label_en": labels.get("en", {}).get("value"),
                "label_ko": labels.get("ko", {}).get("value"),
                "label_ja": labels.get("ja", {}).get("value"),
                "enwiki": sitelinks.get("enwiki", {}).get("title"),
                "kowiki": sitelinks.get("kowiki", {}).get("title"),
                "jawiki": sitelinks.get("jawiki", {}).get("title"),
            }
        if i + 50 < len(qids):
            time.sleep(0.5)
    return results


def fetch_wikipedia_extracts(titles: list[str], lang: str = "en") -> dict:
    api_url = WIKIPEDIA_API_TMPL.format(lang=lang)
    results = {}
    for i in range(0, len(titles), 20):
        batch = titles[i:i+20]
        params = {
            "action": "query",
            "titles": "|".join(batch),
            "prop": "extracts",
            "exintro": "true",
            "explaintext": "true",
            "exlimit": len(batch),
            "format": "json",
        }
        try:
            resp = SESSION.get(api_url, params=params, timeout=30)
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", {})
            for pid, page in pages.items():
                if int(pid) < 0:
                    continue
                title = page.get("title", "")
                extract = page.get("extract", "")
                results[title] = (extract[:2000] if extract else None)
        except Exception as e:
            print(f"  [WARN] Wikipedia {lang} batch error: {e}")
        if i + 20 < len(titles):
            time.sleep(0.3)
    return results


def cmd_fetch(min_imp: int, fgo_only: bool = False):
    """Fetch Wikipedia data for target persons."""
    paths = get_output_paths(min_imp, fgo_only)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Select targets
    targets = select_targets(min_imp, fgo_only)
    label = "FGO-linked" if fgo_only else f"importance >= {min_imp}"
    print("=" * 60)
    print(f"Person Bio Enhance — Fetch ({label})")
    print("=" * 60)
    print(f"\nTargets: {len(targets)} persons need upgrade")

    if not targets:
        print("Nothing to do!")
        return

    # Save targets
    with open(paths["targets"], "w", encoding="utf-8") as f:
        json.dump(targets, f, ensure_ascii=False, indent=2)

    # Collect wikidata IDs
    qid_map = {}
    for t in targets:
        qid = t.get("wikidata_id")
        if qid and qid.startswith("Q"):
            qid_map[qid] = t["person_id"]

    print(f"Wikidata IDs: {len(qid_map)}")

    # Wikidata fetch
    print(f"\n--- Fetching Wikidata entities ---")
    wikidata = fetch_wikidata_batch(list(qid_map.keys()))
    print(f"  Fetched: {len(wikidata)}")

    # Collect Wikipedia titles
    en_titles, ko_titles, ja_titles = {}, {}, {}
    for qid, wd in wikidata.items():
        if wd.get("enwiki"):
            en_titles[wd["enwiki"]] = qid
        if wd.get("kowiki"):
            ko_titles[wd["kowiki"]] = qid
        if wd.get("jawiki"):
            ja_titles[wd["jawiki"]] = qid

    print(f"Wikipedia articles: EN={len(en_titles)}, KO={len(ko_titles)}, JA={len(ja_titles)}")

    # Fetch Wikipedia extracts
    print(f"\n--- Fetching EN Wikipedia ---")
    en_ext = fetch_wikipedia_extracts(list(en_titles.keys()), "en")
    print(f"  {len(en_ext)} articles")

    print(f"\n--- Fetching KO Wikipedia ---")
    ko_ext = fetch_wikipedia_extracts(list(ko_titles.keys()), "ko")
    print(f"  {len(ko_ext)} articles")

    print(f"\n--- Fetching JA Wikipedia ---")
    ja_ext = fetch_wikipedia_extracts(list(ja_titles.keys()), "ja")
    print(f"  {len(ja_ext)} articles")

    # Combine
    wiki_data = {}
    for qid, wd in wikidata.items():
        entry = {**wd}
        en_title = wd.get("enwiki")
        if en_title and en_title in en_ext:
            entry["extract_en"] = en_ext[en_title]
        ko_title = wd.get("kowiki")
        if ko_title and ko_title in ko_ext:
            entry["extract_ko"] = ko_ext[ko_title]
        ja_title = wd.get("jawiki")
        if ja_title and ja_title in ja_ext:
            entry["extract_ja"] = ja_ext[ja_title]
        wiki_data[qid] = entry

    with open(paths["wiki"], "w", encoding="utf-8") as f:
        json.dump(wiki_data, f, ensure_ascii=False, indent=2)

    has_en = sum(1 for v in wiki_data.values() if v.get("extract_en"))
    has_ko = sum(1 for v in wiki_data.values() if v.get("extract_ko"))
    has_ja = sum(1 for v in wiki_data.values() if v.get("extract_ja"))

    print(f"\n{'='*60}")
    print(f"Saved: {paths['wiki']}")
    print(f"  EN: {has_en}, KO: {has_ko}, JA: {has_ja}")


# ──────────────────────────────────────────────────────────────
# Phase 2: --generate (GPT-5.2 EN biography)
# ──────────────────────────────────────────────────────────────

GENERATE_SYSTEM = """\
You are a historical research assistant for the CHALDEAS project — \
a 3D globe-based history exploration system.

For each historical person, generate a concise biography using the provided \
Wikipedia extract, related events, and academic paper context.

## Output Format
Return a JSON object {"persons": [...]} with one entry per person, in order:
{
  "person_id": <int>,
  "biography": "<4-6 sentences, 400-600 characters. Cover: who they are, major achievements, \
historical significance, and key relationships. Factual, encyclopedic tone.>"
}

## Biography Style Guide
Target: **400-600 characters**.
Structure: Identity/role → Major achievements → Historical significance → Legacy/relationships.

Example (Napoleon, 510 chars):
"Napoleon Bonaparte rose from Corsican obscurity to become Emperor of the French, reshaping \
European politics and warfare in the early nineteenth century. His military campaigns from \
Austerlitz to Waterloo redrew the map of the continent, while the Napoleonic Code reformed \
civil law across much of Europe. He centralized French administration, promoted meritocracy, \
and spread revolutionary ideals even as his imperial ambitions provoked coalitions that \
ultimately led to his exile and death on Saint Helena."

## Rules
- Use Wikipedia extract as PRIMARY source; augment with event/paper context
- Factual and encyclopedic — no speculation, no pop culture references
- Do NOT repeat birth/death years (the system already shows those)
- If the person is obscure, write what is known without padding
- English only (translation is done separately)
"""


def build_generate_prompt(batch: list[dict], wiki_data: dict,
                          event_ctx: dict, paper_ctx: dict) -> str:
    """Build GPT prompt with Wikipedia + events + papers context."""
    lines = [f"Generate biographies for {len(batch)} historical persons.\n"]

    for i, t in enumerate(batch, 1):
        pid = t["person_id"]
        lines.append(f"--- Person {i} (id={pid}) ---")
        lines.append(f"Name: {t['name']}")
        if t.get("role"):
            lines.append(f"Role: {t['role']}")
        if t.get("birth_year"):
            lines.append(f"Dates: {t['birth_year']} ~ {t.get('death_year', '?')}")
        lines.append(f"Certainty: {t.get('certainty', 'historical')}")
        lines.append(f"Importance: {t['importance_score']}")

        # Wikipedia context
        qid = t.get("wikidata_id")
        if qid and qid in wiki_data:
            wd = wiki_data[qid]
            extract = wd.get("extract_en", "")
            if extract:
                if len(extract) > 600:
                    extract = extract[:600] + "..."
                lines.append(f"\nWikipedia: {extract}")

        # Event context
        events = event_ctx.get(pid, [])
        if events:
            lines.append("\nRelated events:")
            for ev in events[:3]:
                desc = ev.get("description", "")
                if desc:
                    desc = f" — {desc[:200]}"
                lines.append(f"  - {ev['name']} ({ev.get('date_start', '?')}){desc}")

        # Paper context
        papers_text = paper_ctx.get(pid)
        if papers_text:
            lines.append(f"\nAcademic papers:\n{papers_text[:800]}")

        lines.append("")

    lines.append('Return JSON: {"persons": [...]} with one entry per person above, in order.')
    return "\n".join(lines)


def cmd_generate(min_imp: int, limit: int | None = None, resume: bool = False, fgo_only: bool = False):
    """Generate EN biographies using GPT-5.2."""
    paths = get_output_paths(min_imp, fgo_only)

    if not paths["targets"].exists():
        print(f"ERROR: {paths['targets']} not found. Run --fetch first.")
        return

    with open(paths["targets"], encoding="utf-8") as f:
        targets = json.load(f)

    wiki_data = {}
    if paths["wiki"].exists():
        with open(paths["wiki"], encoding="utf-8") as f:
            wiki_data = json.load(f)

    label = "FGO-linked" if fgo_only else f"importance >= {min_imp}"
    print("=" * 60)
    print(f"Person Bio Enhance — Generate ({label})")
    print(f"Model: {GPT_MODEL_GENERATE}, Batch size: {BATCH_SIZE}")
    print("=" * 60)
    print(f"\nTargets: {len(targets)}, Wiki data: {len(wiki_data)}")

    # Load event + paper context
    print("Loading event context...")
    person_ids = [t["person_id"] for t in targets]
    event_ctx = load_event_context(person_ids)
    print(f"  {len(event_ctx)} persons have events")

    print("Loading paper context...")
    paper_ctx = load_paper_context(event_ctx)
    print(f"  {len(paper_ctx)} persons have papers")

    # Resume support
    existing = {}
    if resume and paths["enrichment"].exists():
        with open(paths["enrichment"], encoding="utf-8") as f:
            existing = {e["person_id"]: e for e in json.load(f)}
        print(f"Resuming: {len(existing)} already done")

    to_process = [t for t in targets if t["person_id"] not in existing]
    print(f"To process: {len(to_process)}")

    if not to_process:
        print("Nothing to process!")
        return

    client = init_openai()
    all_results = list(existing.values())
    batches = [to_process[i:i+BATCH_SIZE] for i in range(0, len(to_process), BATCH_SIZE)]

    if limit:
        batches = batches[:limit]
        print(f"Limited to {limit} batches ({min(limit * BATCH_SIZE, len(to_process))} persons)")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for batch_num, batch in enumerate(batches, 1):
        names = [t["name"] for t in batch]
        print(f"\n--- Batch {batch_num}/{len(batches)} ---")
        print(f"  {', '.join(names)}")

        prompt = build_generate_prompt(batch, wiki_data, event_ctx, paper_ctx)
        data = call_gpt(client, GPT_MODEL_GENERATE, GENERATE_SYSTEM, prompt, batch_num)

        if data:
            results = data.get("persons", [])
            if isinstance(data, list):
                results = data

            for j, r in enumerate(results):
                if j < len(batch):
                    r["person_id"] = batch[j]["person_id"]
                    r["name"] = batch[j]["name"]
                all_results.append(r)

        # Save incrementally
        with open(paths["enrichment"], "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        if batch_num < len(batches):
            time.sleep(1)

    print(f"\n{'='*60}")
    print(f"Generate complete: {len(all_results)} entries")
    print(f"Saved: {paths['enrichment']}")


# ──────────────────────────────────────────────────────────────
# Phase 3: --translate (GPT-5.1 KO/JA)
# ──────────────────────────────────────────────────────────────

TRANSLATE_SYSTEM = """\
You are a professional translator for the CHALDEAS project — \
a 3D globe-based history exploration system.

Translate English biographies of historical persons into Korean and Japanese.

## Output Format
Return JSON: {"translations": [{
  "person_id": <int>,
  "biography_ko": "<Korean translation>",
  "biography_ja": "<Japanese translation>"
}]}

## Rules
- Maintain factual accuracy
- Korean: **~다 서술체** (예: ~이다, ~했다, ~전해진다). 존댓말/합쇼체 금지.
- Japanese: である調 (dearu-chō), academic tone
- Use standard localized proper nouns (e.g., Napoleon→나폴레옹/ナポレオン)
- Match original length (~400-600 chars per translation)
"""


def build_translate_prompt(batch: list[dict]) -> str:
    lines = [f"Translate {len(batch)} biographies to Korean and Japanese.\n"]
    for i, entry in enumerate(batch, 1):
        lines.append(f"--- Person {i} (id={entry.get('person_id', '?')}: {entry.get('name', '?')}) ---")
        lines.append(entry.get("biography", ""))
        lines.append("")
    lines.append('Return JSON: {"translations": [...]} in same order.')
    return "\n".join(lines)


def cmd_translate(min_imp: int, limit: int | None = None, fgo_only: bool = False):
    """Translate biographies to KO/JA using GPT-5.1."""
    paths = get_output_paths(min_imp, fgo_only)

    if not paths["enrichment"].exists():
        print(f"ERROR: {paths['enrichment']} not found. Run --generate first.")
        return

    with open(paths["enrichment"], encoding="utf-8") as f:
        enrichment = json.load(f)

    label = "FGO-linked" if fgo_only else f"importance >= {min_imp}"
    print("=" * 60)
    print(f"Person Bio Enhance — Translate ({label})")
    print(f"Model: {GPT_MODEL_TRANSLATE}, Batch size: {BATCH_SIZE}")
    print("=" * 60)

    to_translate = [e for e in enrichment
                    if e.get("biography") and (not e.get("biography_ko") or not e.get("biography_ja"))]

    print(f"\nTotal entries: {len(enrichment)}")
    print(f"Need translation: {len(to_translate)}")

    if not to_translate:
        print("All translated!")
        return

    client = init_openai()
    enrich_by_id = {e["person_id"]: e for e in enrichment}
    batches = [to_translate[i:i+BATCH_SIZE] for i in range(0, len(to_translate), BATCH_SIZE)]

    if limit:
        batches = batches[:limit]
        print(f"Limited to {limit} batches")

    translated = 0

    for batch_num, batch in enumerate(batches, 1):
        names = [e.get("name", "?") for e in batch]
        print(f"\n--- Batch {batch_num}/{len(batches)} ---")
        print(f"  {', '.join(names)}")

        prompt = build_translate_prompt(batch)
        data = call_gpt(client, GPT_MODEL_TRANSLATE, TRANSLATE_SYSTEM, prompt, batch_num)

        if data:
            translations = data.get("translations", [])
            if isinstance(data, list):
                translations = data

            for j, tr in enumerate(translations):
                pid = tr.get("person_id") or (batch[j]["person_id"] if j < len(batch) else None)
                if pid and pid in enrich_by_id:
                    enrich_by_id[pid]["biography_ko"] = tr.get("biography_ko")
                    enrich_by_id[pid]["biography_ja"] = tr.get("biography_ja")
                    translated += 1

        # Save incrementally
        with open(paths["enrichment"], "w", encoding="utf-8") as f:
            json.dump(enrichment, f, ensure_ascii=False, indent=2)

        if batch_num < len(batches):
            time.sleep(1)

    print(f"\n{'='*60}")
    print(f"Translated: {translated} entries")


# ──────────────────────────────────────────────────────────────
# Phase 4: --apply (DB update)
# ──────────────────────────────────────────────────────────────

def cmd_apply(min_imp: int, dry_run: bool = False, fgo_only: bool = False):
    """Apply enriched biographies to DB."""
    paths = get_output_paths(min_imp, fgo_only)

    if not paths["enrichment"].exists():
        print(f"ERROR: {paths['enrichment']} not found.")
        return

    with open(paths["enrichment"], encoding="utf-8") as f:
        enrichment = json.load(f)

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    label = "FGO-linked" if fgo_only else f"importance >= {min_imp}"
    print("=" * 60)
    print(f"Person Bio Enhance — Apply ({label})")
    print("=" * 60)

    stats = {"updated": 0, "skipped_short": 0, "skipped_no_bio": 0, "errors": 0}

    for entry in enrichment:
        pid = entry.get("person_id")
        name = entry.get("name", "?")
        bio = entry.get("biography")
        bio_ko = entry.get("biography_ko")
        bio_ja = entry.get("biography_ja")

        if not bio or len(bio) < 100:
            stats["skipped_short"] += 1
            continue

        if dry_run:
            has_ko = "KO" if bio_ko else "--"
            has_ja = "JA" if bio_ja else "--"
            print(f"  [DRY] {name:35s} | {len(bio):3d}c | {has_ko} {has_ja}")
            stats["updated"] += 1
            continue

        try:
            cur.execute("""
                UPDATE person_details SET
                    biography = %s,
                    biography_ko = %s,
                    biography_ja = %s,
                    biography_source = 'gpt-5.2+wikipedia+papers',
                    updated_at = NOW()
                WHERE person_id = %s
            """, (bio, bio_ko, bio_ja, pid))
            stats["updated"] += 1
        except Exception as e:
            print(f"  [ERROR] {name}: {e}")
            stats["errors"] += 1
            conn.rollback()

        if stats["updated"] % 100 == 0 and stats["updated"] > 0:
            conn.commit()

    if not dry_run:
        conn.commit()

    print(f"\n{'='*60}")
    print(f"Results:")
    print(f"  Updated:       {stats['updated']}")
    print(f"  Skipped short: {stats['skipped_short']}")
    print(f"  Skipped no bio:{stats['skipped_no_bio']}")
    print(f"  Errors:        {stats['errors']}")
    if dry_run:
        print("  (DRY RUN)")

    conn.close()


# ──────────────────────────────────────────────────────────────
# --status
# ──────────────────────────────────────────────────────────────

def cmd_status():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    print("=" * 60)
    print("Person Bio Enhance — Status")
    print("=" * 60)

    # DB overview
    for threshold in [95, 90, 85, 80]:
        cur.execute("""
            SELECT count(*) as total,
                   sum(CASE WHEN pd.biography_source = 'wikidata' OR pd.biography IS NULL
                            OR length(pd.biography) < 150 THEN 1 ELSE 0 END) as needs_upgrade,
                   sum(CASE WHEN pd.biography_source LIKE 'gpt-5.2%%' THEN 1 ELSE 0 END) as good
            FROM persons p
            JOIN person_details pd ON pd.person_id = p.id
            WHERE p.importance_score >= %s
        """, (threshold,))
        r = cur.fetchone()
        print(f"\n  imp >= {threshold}: {r['total']} total, "
              f"{r['needs_upgrade']} need upgrade, {r['good']} already good")

    # File status
    print(f"\nOutput files:")
    for threshold in [95, 90, 85, 80]:
        paths = get_output_paths(threshold)
        for key, path in paths.items():
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                count = len(data) if isinstance(data, list) else len(data.keys())
                print(f"  imp{threshold}/{key}: {count} entries")

    conn.close()


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Enhance person biographies (Wikipedia + Papers + GPT)"
    )
    parser.add_argument("--fetch", action="store_true",
                        help="Fetch Wikipedia data for targets")
    parser.add_argument("--generate", action="store_true",
                        help="Generate EN biographies (gpt-5.2)")
    parser.add_argument("--translate", action="store_true",
                        help="Translate to KO/JA (gpt-5.1)")
    parser.add_argument("--apply", action="store_true",
                        help="Apply to DB")
    parser.add_argument("--status", action="store_true",
                        help="Show status")
    parser.add_argument("--min-imp", type=int, default=95,
                        help="Minimum importance score (default: 95)")
    parser.add_argument("--fgo-only", action="store_true",
                        help="Only FGO-linked persons (ignores --min-imp)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit batches (test)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from existing enrichment")
    args = parser.parse_args()

    if args.status:
        cmd_status()
    elif args.fetch:
        cmd_fetch(args.min_imp, fgo_only=args.fgo_only)
    elif args.generate:
        cmd_generate(args.min_imp, limit=args.limit, resume=args.resume, fgo_only=args.fgo_only)
    elif args.translate:
        cmd_translate(args.min_imp, limit=args.limit, fgo_only=args.fgo_only)
    elif args.apply:
        cmd_apply(args.min_imp, dry_run=args.dry_run, fgo_only=args.fgo_only)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
