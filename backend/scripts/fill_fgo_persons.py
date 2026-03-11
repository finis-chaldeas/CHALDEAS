"""
FGO 서번트 전체 인물 데이터 생성
=================================
모든 비-타입문 오리지널 서번트에 대해:
  1. GPT-5.2-chat으로 역사/신화/전설 인물 메타데이터 생성
  2. persons 테이블 INSERT
  3. person_details INSERT (약전, 시대)
  4. locations 할당 (birthplace_id)
  5. fgo_servants.person_id 링크

Usage:
    cd backend
    python scripts/fill_fgo_persons.py --generate                # GPT enrichment 생성
    python scripts/fill_fgo_persons.py --generate --limit 3      # 테스트 (3 배치)
    python scripts/fill_fgo_persons.py --generate --resume       # 이어서 생성
    python scripts/fill_fgo_persons.py --apply                   # DB에 적용
    python scripts/fill_fgo_persons.py --apply --dry-run         # 미리보기
    python scripts/fill_fgo_persons.py --status                  # 현황
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

FGO_DATA_ROOT = Path("E:/chaldeas_data/fgo_db/servants/by_id")
PERSON_LINKS_DIR = Path("E:/chaldeas_data/processed/fgo/person_links")
OUTPUT_DIR = Path(__file__).parent / "output"
ENRICHMENT_FILE = OUTPUT_DIR / "fgo_enrichment.json"

GPT_MODEL = "gpt-5.2-chat-latest"
BATCH_SIZE = 10

# ──────────────────────────────────────────────────────────────
# GPT System Prompt
# ──────────────────────────────────────────────────────────────

ENRICHMENT_SYSTEM = """\
You are a historical/mythological research assistant for the CHALDEAS project — \
a 3D globe-based history exploration system.

For each FGO (Fate/Grand Order) servant, identify the underlying real historical, \
mythological, or legendary figure and provide structured metadata.

## Classification Rules

**category** — pick ONE:
- "historical": Real person with documented existence (Caesar, Napoleon, Tesla, Nightingale)
- "mythological": Deity or figure from mythology/religion (Gilgamesh, Karna, Cu Chulainn, Medea)
- "legendary": Semi-historical figure, heavily mythologized (King Arthur, Robin Hood, Vlad III as "Dracula")
- "fictional": Character from literature, not mythology (Sherlock Holmes, Frankenstein's monster, Captain Nemo, Dr. Jekyll)
- "fgo_original": Fate franchise original with no real-world basis (Mash Kyrielight, BB, Emiya)

**certainty** — maps to category:
- historical → "fact" or "probable"
- mythological → "mythological"
- legendary → "legendary"
- fictional → "fictional"
- fgo_original → skip

## Date Rules
- Negative integers for BCE: -490 = 490 BCE, 476 = 476 CE
- For mythological figures: use floruit_start/floruit_end for the mythology's estimated era
  (e.g., Trojan War heroes: floruit_start=-1250, floruit_end=-1180)
- For historical: use birth_year/death_year
- For legendary with estimated dates: use birth_year/death_year with best estimates

## Region Rules
- region_modern: modern country name (e.g., "Greece", "Iraq", "India", "Ireland")
- region_historical: ancient/mythological region (e.g., "Sumer, Uruk", "Ulster", "Thessaly")
- latitude/longitude: approximate coordinates of the primary associated location
- For mythological figures: use the main location from the mythology
  (e.g., Cu Chulainn → Emain Macha in Ulster, ~54.35, -6.65)

## Variant Handling
Multiple FGO servants represent the same person. Use identical "canonical_name" for all variants.
Examples:
- Cu Chulainn (Lancer/Caster/Alter/Prototype) → canonical_name: "Cú Chulainn"
- Altria Pendragon (all variants) → canonical_name: "King Arthur"
- Nero Claudius (all variants) → canonical_name: "Nero"
- Tamamo-no-Mae (all variants) → canonical_name: "Tamamo-no-Mae"

## Output Format
Return a JSON object with key "servants" containing an array. Each element:
{
  "atlas_id": <integer>,
  "fgo_name": "<FGO display name>",
  "action": "create" | "skip",
  "skip_reason": null | "fgo_original" | "cannot_identify",
  "canonical_name": "<identical for all variants of same person>",
  "real_name": "<canonical historical/mythological name>",
  "name_ko": "<Korean name>",
  "name_ja": "<Japanese name (kanji/kana)>",
  "category": "historical" | "mythological" | "legendary" | "fictional" | "fgo_original",
  "certainty": "fact" | "probable" | "legendary" | "mythological" | "fictional",
  "mythology_tradition": "<e.g., Greek mythology, Hindu (Mahabharata), Arthurian legend, Norse mythology>" | null,
  "birth_year": <int or null>,
  "death_year": <int or null>,
  "floruit_start": <int or null>,
  "floruit_end": <int or null>,
  "era": "<Bronze Age, Classical, Medieval, Renaissance, Early Modern, Modern>",
  "role": "<brief role: king, warrior, goddess, philosopher, etc.>",
  "domain": "<political, military, science, philosophy, arts, religion, exploration, other>",
  "region_modern": "<modern country>",
  "region_historical": "<historical/mythological region>",
  "latitude": <float>,
  "longitude": <float>,
  "wikidata_id": "<QID>" | null,
  "biography": "<2-3 sentences about the REAL figure, not FGO version>",
  "biography_ko": "<Korean biography, 2-3 sentences>"
}

IMPORTANT:
- Every servant MUST have an entry in the output, even if action is "skip"
- For FGO originals, set action="skip", skip_reason="fgo_original", and fill minimal fields
- biography should be about the REAL historical/mythological figure
- wikidata_id only if you are confident (better null than wrong)
"""


# ──────────────────────────────────────────────────────────────
# Data Loading
# ──────────────────────────────────────────────────────────────

def load_fgo_originals() -> set:
    """fgo_originals.json에서 atlas_id 집합 로드"""
    path = PERSON_LINKS_DIR / "fgo_originals.json"
    if not path.exists():
        return set()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {entry["servant_id"] for entry in data}


def load_bond_text(atlas_id: int) -> dict | None:
    """Load bond text from FGO servant data file"""
    path = FGO_DATA_ROOT / f"{atlas_id}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("bond_text")


def parse_origin_region(bond_text: dict | None) -> str:
    """Extract Origin/Region from bond text field 2 (EN)"""
    if not bond_text:
        return ""
    en_texts = bond_text.get("en", [])
    if len(en_texts) < 2:
        return ""
    field2 = en_texts[1]
    # Extract "Origin: ..." and "Region: ..." lines
    lines = []
    for line in field2.split("\n"):
        line_s = line.strip()
        if line_s.startswith(("Origin:", "Region:", "Source:", "出典:", "地域:")):
            lines.append(line_s)
    return " / ".join(lines) if lines else field2[:200]


def get_condensed_bond_text(bond_text: dict | None) -> str:
    """Get condensed bond text for GPT context (EN fields 0 and 1 only)"""
    if not bond_text:
        return "(no bond text available)"
    en_texts = bond_text.get("en", [])
    if not en_texts:
        # Fall back to Japanese
        ja_texts = bond_text.get("ja", [])
        if not ja_texts:
            return "(no bond text available)"
        return "\n".join(ja_texts[:2])[:500]
    return "\n".join(en_texts[:2])[:500]


def load_unlinked_servants(cur) -> list[dict]:
    """Get all unlinked servants from DB with their atlas_id"""
    cur.execute("""
        SELECT id, servant_id, atlas_id, name, name_jp, name_ko, class_name, rarity
        FROM fgo_servants
        WHERE person_id IS NULL
        ORDER BY atlas_id
    """)
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def load_confirmed_links(cur) -> set:
    """Get atlas_ids of already-linked servants"""
    cur.execute("SELECT atlas_id FROM fgo_servants WHERE person_id IS NOT NULL")
    return {r[0] for r in cur.fetchall()}


# ──────────────────────────────────────────────────────────────
# GPT Enrichment
# ──────────────────────────────────────────────────────────────

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


def build_batch_prompt(servants_batch: list[dict]) -> str:
    """Build user prompt for a batch of servants"""
    lines = [f"Classify and enrich the following {len(servants_batch)} FGO servants.\n"]

    for i, s in enumerate(servants_batch, 1):
        atlas_id = s["atlas_id"]
        bond_text = load_bond_text(atlas_id)
        condensed = get_condensed_bond_text(bond_text)
        origin = parse_origin_region(bond_text)

        lines.append(f"--- Servant {i} ---")
        lines.append(f"atlas_id: {atlas_id}")
        lines.append(f"FGO Name: {s['name']} ({s['class_name']})")
        if s.get("name_ko"):
            lines.append(f"Korean Name: {s['name_ko']}")
        lines.append(f"Rarity: {s.get('rarity', '?')}★")
        if origin:
            lines.append(f"Origin/Region: {origin}")
        lines.append(f"Bond Text:\n{condensed}")
        lines.append("")

    lines.append(
        "Return a JSON object {\"servants\": [...]} with one entry per servant above, "
        "in the same order. Follow the output format exactly."
    )
    return "\n".join(lines)


def call_gpt_batch(client, servants_batch: list[dict], batch_num: int) -> list[dict]:
    """Call GPT for a batch of servants"""
    prompt = build_batch_prompt(servants_batch)

    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": ENRICHMENT_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_completion_tokens=4096,
            )

            content = resp.choices[0].message.content
            if not content:
                print(f"  [WARN] Batch {batch_num}: empty response (attempt {attempt+1})")
                continue

            data = json.loads(content)
            servants = data.get("servants", data.get("results", []))
            if not servants:
                # Maybe the response is the array directly
                if isinstance(data, list):
                    servants = data

            if len(servants) != len(servants_batch):
                print(f"  [WARN] Batch {batch_num}: expected {len(servants_batch)} results, got {len(servants)}")
                # Try to use what we got
                if not servants:
                    continue

            # Calculate cost
            usage = resp.usage
            input_cost = (usage.prompt_tokens / 1_000_000) * 1.75
            output_cost = (usage.completion_tokens / 1_000_000) * 14.00
            total_cost = input_cost + output_cost
            print(f"  Batch {batch_num}: {len(servants)} results, "
                  f"tokens={usage.prompt_tokens}+{usage.completion_tokens}, "
                  f"cost=${total_cost:.3f}")

            return servants

        except json.JSONDecodeError as e:
            print(f"  [ERROR] Batch {batch_num}: JSON parse error (attempt {attempt+1}): {e}")
            if attempt < 2:
                time.sleep(2)
        except Exception as e:
            print(f"  [ERROR] Batch {batch_num}: {e} (attempt {attempt+1})")
            if attempt < 2:
                time.sleep(5)

    print(f"  [FAIL] Batch {batch_num}: all attempts failed")
    return []


# ──────────────────────────────────────────────────────────────
# --generate
# ──────────────────────────────────────────────────────────────

def cmd_generate(limit: int | None = None, resume: bool = False):
    """Generate enrichment data using GPT"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    print("=" * 60)
    print("FGO Servant Enrichment — Generate")
    print("=" * 60)

    # Load existing enrichment if resuming
    existing = {}
    if resume and ENRICHMENT_FILE.exists():
        with open(ENRICHMENT_FILE, encoding="utf-8") as f:
            existing = {e["atlas_id"]: e for e in json.load(f)}
        print(f"Loaded {len(existing)} existing enrichment entries")

    # Get unlinked servants
    servants = load_unlinked_servants(cur)
    fgo_originals = load_fgo_originals()
    linked = load_confirmed_links(cur)
    conn.close()

    print(f"\nTotal servants: 449")
    print(f"Already linked: {len(linked)}")
    print(f"Unlinked: {len(servants)}")
    print(f"Known FGO originals: {len(fgo_originals)}")

    # Filter: skip already enriched (resume) and known FGO originals
    to_process = []
    auto_skip = []
    for s in servants:
        aid = s["atlas_id"]
        if resume and aid in existing:
            continue
        if aid in fgo_originals:
            auto_skip.append({
                "atlas_id": aid,
                "fgo_name": s["name"],
                "action": "skip",
                "skip_reason": "fgo_original",
                "canonical_name": None,
                "real_name": None,
                "category": "fgo_original",
            })
            continue
        to_process.append(s)

    print(f"To process with GPT: {len(to_process)}")
    print(f"Auto-skip (FGO originals): {len(auto_skip)}")

    if not to_process:
        print("\nNothing to process!")
        return

    # Batch processing
    client = init_openai()
    all_results = list(existing.values()) + auto_skip
    batches = [to_process[i:i+BATCH_SIZE] for i in range(0, len(to_process), BATCH_SIZE)]

    if limit:
        batches = batches[:limit]
        print(f"Limited to {limit} batches ({min(limit * BATCH_SIZE, len(to_process))} servants)")

    total_cost = 0.0
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for batch_num, batch in enumerate(batches, 1):
        print(f"\n--- Batch {batch_num}/{len(batches)} ({len(batch)} servants) ---")
        names = [s["name"] for s in batch]
        print(f"  {', '.join(names[:5])}{'...' if len(names) > 5 else ''}")

        results = call_gpt_batch(client, batch, batch_num)

        if results:
            # Match results to input by atlas_id or position
            for i, r in enumerate(results):
                # Ensure atlas_id is set
                if "atlas_id" not in r and i < len(batch):
                    r["atlas_id"] = batch[i]["atlas_id"]
                all_results.append(r)

        # Save incrementally
        with open(ENRICHMENT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        # Rate limiting
        if batch_num < len(batches):
            time.sleep(1)

    # Final summary
    actions = defaultdict(int)
    categories = defaultdict(int)
    for r in all_results:
        actions[r.get("action", "unknown")] += 1
        categories[r.get("category", "unknown")] += 1

    print(f"\n{'='*60}")
    print(f"Enrichment complete — {len(all_results)} entries")
    print(f"\nActions: {dict(actions)}")
    print(f"Categories: {dict(categories)}")
    print(f"Saved to: {ENRICHMENT_FILE}")


# ──────────────────────────────────────────────────────────────
# --apply
# ──────────────────────────────────────────────────────────────

def cmd_apply(dry_run: bool = False):
    """Apply enrichment data to DB"""
    if not ENRICHMENT_FILE.exists():
        print(f"ERROR: {ENRICHMENT_FILE} not found. Run --generate first.")
        return

    with open(ENRICHMENT_FILE, encoding="utf-8") as f:
        enrichment = json.load(f)

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    print("=" * 60)
    print("FGO Servant Enrichment — Apply to DB")
    print("=" * 60)

    # Current status
    cur.execute("SELECT count(*) FROM fgo_servants WHERE person_id IS NOT NULL")
    before_linked = cur.fetchone()[0]
    print(f"Before: {before_linked}/449 linked\n")

    # Filter to actionable entries
    to_apply = [e for e in enrichment if e.get("action") == "create"]
    skipped = [e for e in enrichment if e.get("action") == "skip"]
    print(f"Entries: {len(enrichment)} total, {len(to_apply)} to create, {len(skipped)} skip")

    # Group by canonical_name to deduplicate (multiple servants → same person)
    person_groups = defaultdict(list)
    for entry in to_apply:
        cname = entry.get("canonical_name") or entry.get("real_name") or entry.get("fgo_name")
        if cname:
            person_groups[cname].append(entry)

    print(f"Unique persons to create/find: {len(person_groups)}")

    # Process each unique person
    stats = {"persons_created": 0, "persons_found": 0, "details_created": 0,
             "locations_linked": 0, "servants_linked": 0, "errors": 0}

    for canonical_name, entries in sorted(person_groups.items()):
        # Use the first entry as the primary (best data)
        primary = _pick_primary(entries)
        real_name = primary.get("real_name", canonical_name)
        wikidata_id = primary.get("wikidata_id")
        category = primary.get("category", "legendary")
        certainty = primary.get("certainty", "legendary")

        # ── Step 1: Find or create person ──
        person_id = None

        # Check by wikidata_id
        if wikidata_id:
            cur.execute("SELECT id FROM persons WHERE wikidata_id = %s", (wikidata_id,))
            row = cur.fetchone()
            if row:
                person_id = row[0]
                print(f"  FOUND  {real_name:35s} → id={person_id} (wikidata={wikidata_id})")
                stats["persons_found"] += 1

        # Check by exact name
        if not person_id:
            cur.execute("SELECT id FROM persons WHERE name = %s", (real_name,))
            row = cur.fetchone()
            if row:
                person_id = row[0]
                print(f"  FOUND  {real_name:35s} → id={person_id} (name match)")
                stats["persons_found"] += 1

        # Check by canonical_name if different
        if not person_id and canonical_name != real_name:
            cur.execute("SELECT id FROM persons WHERE name = %s", (canonical_name,))
            row = cur.fetchone()
            if row:
                person_id = row[0]
                print(f"  FOUND  {real_name:35s} → id={person_id} (canonical match)")
                stats["persons_found"] += 1

        # Create new person
        if not person_id:
            if dry_run:
                print(f"  [DRY]  CREATE {real_name:35s} ({category}/{certainty})")
                stats["persons_created"] += 1
            else:
                try:
                    person_id = _create_person(cur, primary, canonical_name)
                    print(f"  CREATE {real_name:35s} → id={person_id} ({category})")
                    stats["persons_created"] += 1
                except Exception as e:
                    print(f"  ERROR  {real_name:35s}: {e}")
                    stats["errors"] += 1
                    continue

        # ── Step 2: Create person_details (if person was just created) ──
        if person_id and not dry_run:
            biography = primary.get("biography")
            if biography:
                try:
                    _create_person_details(cur, person_id, primary)
                    stats["details_created"] += 1
                except Exception:
                    pass  # Details already exist or error

        # ── Step 3: Find and link birthplace location ──
        if person_id and not dry_run:
            lat = primary.get("latitude")
            lon = primary.get("longitude")
            if lat and lon:
                try:
                    _link_birthplace(cur, person_id, primary)
                    stats["locations_linked"] += 1
                except Exception:
                    pass

        # ── Step 4: Link all variant fgo_servants ──
        for entry in entries:
            atlas_id = entry.get("atlas_id")
            if not atlas_id:
                continue
            fgo_name = entry.get("fgo_name", "?")

            cur.execute("SELECT id, person_id FROM fgo_servants WHERE atlas_id = %s", (atlas_id,))
            servant_row = cur.fetchone()
            if not servant_row:
                continue

            if servant_row["person_id"] == person_id:
                continue  # Already linked correctly

            if dry_run:
                status = "NEW" if servant_row["person_id"] is None else f"CHANGE→{person_id}"
                print(f"    [DRY] LINK {fgo_name:35s} (atlas={atlas_id}) → person_id={person_id} ({status})")
            elif person_id:
                cur.execute(
                    "UPDATE fgo_servants SET person_id = %s, updated_at = NOW() WHERE id = %s",
                    (person_id, servant_row["id"])
                )
            stats["servants_linked"] += 1

    if not dry_run:
        conn.commit()

    # Final report
    cur.execute("SELECT count(*) FROM fgo_servants WHERE person_id IS NOT NULL")
    after_linked = cur.fetchone()[0]

    print(f"\n{'='*60}")
    print(f"Results:")
    print(f"  Persons created:  {stats['persons_created']}")
    print(f"  Persons found:    {stats['persons_found']}")
    print(f"  Details created:  {stats['details_created']}")
    print(f"  Locations linked: {stats['locations_linked']}")
    print(f"  Servants linked:  {stats['servants_linked']}")
    print(f"  Errors:           {stats['errors']}")
    print(f"  DB linked: {before_linked} → {after_linked}")
    if dry_run:
        print("  (DRY RUN — no changes made)")

    conn.close()


def _pick_primary(entries: list[dict]) -> dict:
    """Pick the best entry from variant group (prefer most complete data)"""
    def score(e):
        s = 0
        if e.get("wikidata_id"):
            s += 10
        if e.get("biography"):
            s += 5
        if e.get("birth_year") is not None or e.get("floruit_start") is not None:
            s += 3
        if e.get("latitude"):
            s += 2
        return s
    return max(entries, key=score)


def _create_person(cur, entry: dict, canonical_name: str) -> int:
    """Create a new person entry in DB"""
    real_name = entry.get("real_name", canonical_name)
    birth_year = entry.get("birth_year")
    death_year = entry.get("death_year")
    floruit_start = entry.get("floruit_start")
    floruit_end = entry.get("floruit_end")
    certainty = entry.get("certainty", "legendary")
    role = entry.get("role", "")
    domain = entry.get("domain")
    wikidata_id = entry.get("wikidata_id")

    # For mythological: use floruit if no birth/death
    if not birth_year and floruit_start:
        birth_year = floruit_start
    if not death_year and floruit_end:
        death_year = floruit_end

    # Importance score based on category
    category = entry.get("category", "legendary")
    importance = 60  # default
    if category == "historical":
        importance = 70
    elif category == "mythological":
        importance = 65
    elif category == "fictional":
        importance = 50

    cur.execute("""
        INSERT INTO persons (
            name, name_ko, name_ja, wikidata_id,
            birth_year, death_year, floruit_start, floruit_end,
            role, domain, certainty,
            importance_score, global_score
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        real_name,
        entry.get("name_ko"),
        entry.get("name_ja"),
        wikidata_id,
        birth_year,
        death_year,
        floruit_start,
        floruit_end,
        role,
        domain,
        certainty,
        importance,
        importance,  # global_score = importance for now
    ))
    return cur.fetchone()[0]


def _create_person_details(cur, person_id: int, entry: dict):
    """Create person_details entry with biography"""
    # Check if already exists
    cur.execute("SELECT person_id FROM person_details WHERE person_id = %s", (person_id,))
    if cur.fetchone():
        return

    real_name = entry.get("real_name", "")
    slug = re.sub(r"[^a-z0-9]+", "-", real_name.lower()).strip("-")
    era = entry.get("era")
    biography = entry.get("biography")
    biography_ko = entry.get("biography_ko")
    wikidata_id = entry.get("wikidata_id")

    wikipedia_url = None
    if wikidata_id:
        wikipedia_url = f"https://www.wikidata.org/wiki/{wikidata_id}"

    cur.execute("""
        INSERT INTO person_details (
            person_id, slug, biography, biography_ko,
            biography_source, era, wikipedia_url
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        person_id, slug, biography, biography_ko,
        "gpt-5.2", era, wikipedia_url,
    ))


def _link_birthplace(cur, person_id: int, entry: dict):
    """Find nearest location and set as birthplace"""
    lat = entry.get("latitude")
    lon = entry.get("longitude")
    if not lat or not lon:
        return

    # Check if already has birthplace
    cur.execute("SELECT birthplace_id FROM persons WHERE id = %s", (person_id,))
    row = cur.fetchone()
    if row and row[0]:
        return  # Already has birthplace

    # Find nearest location within 200km
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


# ──────────────────────────────────────────────────────────────
# --status
# ──────────────────────────────────────────────────────────────

def cmd_status():
    """Show current pipeline status"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT count(*) FROM fgo_servants")
    total = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM fgo_servants WHERE person_id IS NOT NULL")
    linked = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM fgo_servants WHERE person_id IS NULL")
    unlinked = cur.fetchone()[0]

    print("=" * 60)
    print("FGO Servant Enrichment — Status")
    print("=" * 60)
    print(f"\nDB: {linked}/{total} linked ({linked*100/total:.1f}%), {unlinked} unlinked")

    # Enrichment file status
    if ENRICHMENT_FILE.exists():
        with open(ENRICHMENT_FILE, encoding="utf-8") as f:
            enrichment = json.load(f)
        actions = defaultdict(int)
        categories = defaultdict(int)
        for e in enrichment:
            actions[e.get("action", "unknown")] += 1
            categories[e.get("category", "unknown")] += 1
        print(f"\nEnrichment file: {len(enrichment)} entries")
        print(f"  Actions: {dict(actions)}")
        print(f"  Categories: {dict(categories)}")

        # Count unique canonical names
        canon = set()
        for e in enrichment:
            cn = e.get("canonical_name")
            if cn and e.get("action") == "create":
                canon.add(cn)
        print(f"  Unique persons to create: {len(canon)}")
    else:
        print(f"\nEnrichment file: NOT FOUND (run --generate first)")

    # FGO originals
    fgo_originals = load_fgo_originals()
    print(f"\nKnown FGO originals: {len(fgo_originals)}")

    # Category breakdown of linked servants
    cur.execute("""
        SELECT p.certainty, count(*)
        FROM fgo_servants fs
        JOIN persons p ON fs.person_id = p.id
        GROUP BY p.certainty
        ORDER BY count(*) DESC
    """)
    rows = cur.fetchall()
    if rows:
        print(f"\nLinked servants by certainty:")
        for r in rows:
            print(f"  {r[0] or 'NULL':20s} {r[1]}")

    conn.close()


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="FGO Servant → Person 전체 데이터 생성 (GPT-powered)"
    )
    parser.add_argument("--generate", action="store_true",
                        help="GPT로 enrichment JSON 생성")
    parser.add_argument("--apply", action="store_true",
                        help="enrichment JSON → DB 적용")
    parser.add_argument("--status", action="store_true",
                        help="현황 확인")
    parser.add_argument("--dry-run", action="store_true",
                        help="미리보기 (DB 변경 없음)")
    parser.add_argument("--limit", type=int, default=None,
                        help="GPT 배치 수 제한 (테스트용)")
    parser.add_argument("--resume", action="store_true",
                        help="기존 enrichment 이어서 생성")
    args = parser.parse_args()

    if args.status:
        cmd_status()
    elif args.generate:
        cmd_generate(limit=args.limit, resume=args.resume)
    elif args.apply:
        cmd_apply(dry_run=args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
