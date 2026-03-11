"""
Portal article entity linking — DB matching + optional LLM extraction.

Two modes:
  --mode db    Direct text matching: loads high-importance entities from DB,
               searches article content for name occurrences, inserts entity tags.
  --mode llm   LLM extraction: sends text to local Ollama (llama3.1:8b) to
               extract entity mentions, then resolves each against DB.

Both modes output updated YAML files with [Name](entity:type:id) tags inline.

Usage:
    cd backend

    # DB matching (fast, high precision, lower recall)
    python scripts/link_article_entities.py --mode db

    # LLM extraction (slower, higher recall, needs Ollama running)
    python scripts/link_article_entities.py --mode llm

    # Process single file
    python scripts/link_article_entities.py --mode db --file output/battle-of-salamis.yaml

    # Dry run (show what would change without writing)
    python scripts/link_article_entities.py --mode db --dry-run

    # Both modes sequentially (DB first, then LLM fills gaps)
    python scripts/link_article_entities.py --mode both
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import yaml

# ─── Constants ───

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"

# Entity tag regex — matches [Display](entity:type:id)
ENTITY_TAG_RE = re.compile(
    r'\[([^\]]+)\]\(entity:(person|event|location|shift|item|collection):([^)]+)\)'
)

# Min name length to consider for matching (avoid "Li", "Wu", etc.)
MIN_NAME_LENGTH = 4

# Importance thresholds for preloading entities
PERSON_MIN_IMPORTANCE = 80
EVENT_MIN_IMPORTANCE = 4
LOCATION_MIN_IMPORTANCE = 0  # locations don't have a single importance field

# Common English words that should never match as entity names
STOP_NAMES = {
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "the", "that", "this", "with", "from", "into", "over", "under", "about",
    "battle", "war", "city", "king", "lord", "duke", "general", "emperor",
    "north", "south", "east", "west", "great", "old", "new", "long", "young",
    "black", "white", "house", "church", "castle", "fort", "island", "river",
    "march", "may", "august", "triumph", "victory", "conquest", "fall", "rise",
    "first", "second", "third", "last", "final", "golden", "iron", "stone",
    "hope", "grace", "faith", "liberty", "justice", "union", "republic",
    "prince", "princess", "queen", "count", "knight",
}


# ─── DB Session ───

def _get_db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.config import get_settings

    settings = get_settings()
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    return Session()


# ─── Entity Loading ───

def load_entities_from_db(db) -> dict:
    """Load persons, events, locations from DB for text matching.

    Returns dict with keys 'person', 'event', 'location', each mapping to
    a list of {id, names: [str, ...], sort_key: int} dicts.
    Names are sorted longest-first to prefer specific matches.
    """
    from sqlalchemy import text as sql_text

    entities = {"person": [], "event": [], "location": []}

    # Persons — importance_score >= threshold
    rows = db.execute(sql_text("""
        SELECT id, name, name_ko
        FROM persons
        WHERE importance_score >= :min_imp
          AND name IS NOT NULL
          AND length(name) >= :min_len
        ORDER BY importance_score DESC
    """), {"min_imp": PERSON_MIN_IMPORTANCE, "min_len": MIN_NAME_LENGTH}).fetchall()

    for r in rows:
        names = []
        if r[1] and len(r[1]) >= MIN_NAME_LENGTH:
            names.append(r[1])
        if r[2] and len(r[2]) >= 2:  # Korean names can be shorter
            names.append(r[2])
        if names:
            entities["person"].append({"id": r[0], "names": names, "sort_key": 0})

    # Events — importance >= threshold
    rows = db.execute(sql_text("""
        SELECT id, title, title_ko
        FROM events
        WHERE importance >= :min_imp
          AND title IS NOT NULL
          AND length(title) >= :min_len
        ORDER BY importance DESC
    """), {"min_imp": EVENT_MIN_IMPORTANCE, "min_len": MIN_NAME_LENGTH}).fetchall()

    for r in rows:
        names = []
        if r[1] and len(r[1]) >= MIN_NAME_LENGTH:
            names.append(r[1])
        if r[2] and len(r[2]) >= 2:
            names.append(r[2])
        if names:
            entities["event"].append({"id": r[0], "names": names, "sort_key": 0})

    # Locations — name length >= 5 to avoid short ambiguous names
    rows = db.execute(sql_text("""
        SELECT id, name, name_ko
        FROM locations
        WHERE name IS NOT NULL
          AND length(name) >= 5
        ORDER BY id
    """)).fetchall()

    for r in rows:
        names = []
        if r[1] and len(r[1]) >= MIN_NAME_LENGTH:
            names.append(r[1])
        if r[2] and len(r[2]) >= 2:
            names.append(r[2])
        if names:
            entities["location"].append({"id": r[0], "names": names, "sort_key": 0})

    print(f"  Loaded: {len(entities['person'])} persons, "
          f"{len(entities['event'])} events, "
          f"{len(entities['location'])} locations")

    return entities


def build_name_index(entities: dict) -> list[tuple]:
    """Build a flat list of (name, entity_type, entity_id) sorted by name length DESC.

    Longer names are matched first to avoid partial matches
    (e.g., "Alexander the Great" before "Alexander").
    Filters out common English stop words.
    Deduplicates: if a name appears in multiple types, person > event > location.
    """
    TYPE_PRIORITY = {"person": 0, "event": 1, "location": 2}

    # Build set of person base names (strip trailing numerals like "I", "II", "III")
    person_base_names = set()
    for ent in entities.get("person", []):
        for name in ent["names"]:
            base = re.sub(r'\s+[IVX]+$', '', name).strip().lower()
            if len(base) >= MIN_NAME_LENGTH:
                person_base_names.add(base)

    # Collect all (name_lower -> [(name, type, id, priority)])
    name_map: dict[str, list] = {}
    for etype, elist in entities.items():
        for ent in elist:
            for name in ent["names"]:
                if name.lower() in STOP_NAMES:
                    continue
                # Skip locations whose name matches a known person base name
                if etype == "location" and name.lower() in person_base_names:
                    continue
                key = name.lower()
                if key not in name_map:
                    name_map[key] = []
                name_map[key].append((name, etype, ent["id"], TYPE_PRIORITY.get(etype, 9)))

    # Pick best entry per name (lowest priority = person first)
    index = []
    for key, entries in name_map.items():
        entries.sort(key=lambda x: x[3])  # sort by priority
        best = entries[0]
        index.append((best[0], best[1], best[2]))

    # Sort by name length descending — longest matches first
    index.sort(key=lambda x: len(x[0]), reverse=True)
    return index


# ─── Text Matching (DB mode) ───

def find_matches_in_text(text: str, name_index: list[tuple],
                         max_per_entity: int = 1) -> list[dict]:
    """Find entity name occurrences in text using exact matching.

    Args:
        text: Article section content (plain text or markdown)
        name_index: sorted (name, type, id) tuples from build_name_index
        max_per_entity: max times to link same entity (1 = first occurrence only)

    Returns:
        List of {start, end, name, entity_type, entity_id} sorted by start position.
    """
    # Track which character positions are already claimed
    claimed = set()
    # Track how many times each entity has been linked
    entity_counts: dict[tuple, int] = {}
    matches = []

    text_lower = text.lower()

    for name, etype, eid in name_index:
        key = (etype, eid)
        if entity_counts.get(key, 0) >= max_per_entity:
            continue

        # Fast pre-filter: skip if name not in text at all
        if name.lower() not in text_lower:
            continue

        # Use word boundary matching to avoid partial matches
        # For CJK names, don't require word boundaries
        if re.match(r'^[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', name):
            pattern = re.escape(name)
        else:
            pattern = r'\b' + re.escape(name) + r'\b'

        for m in re.finditer(pattern, text):
            start, end = m.start(), m.end()

            # Check if this span overlaps with already-claimed positions
            span = set(range(start, end))
            if span & claimed:
                continue

            # Check if already inside an entity tag
            # Look backward for [... and forward for ](entity:...)
            before = text[max(0, start - 200):start]
            after = text[end:end + 200]
            if re.search(r'\[[^\]]*$', before) and re.search(r'^\]\(entity:', after):
                continue

            # Also skip if inside a markdown link already
            if re.search(r'\[[^\]]*$', before) and re.search(r'^\]\(', after):
                continue

            claimed.update(span)
            entity_counts[key] = entity_counts.get(key, 0) + 1
            matches.append({
                "start": start,
                "end": end,
                "name": m.group(),
                "entity_type": etype,
                "entity_id": eid,
            })

            if entity_counts[key] >= max_per_entity:
                break

    # Sort by position for replacement
    matches.sort(key=lambda x: x["start"])
    return matches


def apply_entity_tags(text: str, matches: list[dict]) -> str:
    """Replace matched spans with entity tags, working backwards to preserve positions."""
    # Apply in reverse order to preserve earlier positions
    for m in reversed(matches):
        tag = f'[{m["name"]}](entity:{m["entity_type"]}:{m["entity_id"]})'
        text = text[:m["start"]] + tag + text[m["end"]:]
    return text


# ─── LLM Extraction (LLM mode) ───

def extract_entities_with_llm(text: str, section_title: str = "") -> list[dict]:
    """Use local Ollama llama3.1:8b to extract entity mentions from text.

    Returns list of {mention, type} where type is person/event/location.
    """
    import urllib.request

    prompt = f"""Extract all named historical entities from this text. Return a JSON array.

For each entity, provide:
- "mention": the exact text as it appears (e.g., "Themistocles", "Battle of Salamis")
- "type": one of "person", "event", "location"

Rules:
- Only include specific, named entities (not "the Greeks" or "the army")
- For persons: historical figures, leaders, generals, philosophers, etc.
- For events: battles, treaties, wars, revolutions, etc.
- For locations: cities, countries, regions, seas, mountains, etc.
- Return ONLY the JSON array, no other text

Text:
{text[:3000]}

JSON array:"""

    payload = json.dumps({
        "model": "llama3.1:8b-instruct-q4_0",
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 2048},
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            raw = result.get("response", "").strip()
    except Exception as e:
        print(f"    [LLM error] {e}")
        return []

    # Parse JSON from response (handle markdown code blocks, truncation)
    # Strip leading/trailing backtick blocks
    raw = re.sub(r'^```(?:json)?\s*\n?', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'\n?```\s*$', '', raw, flags=re.MULTILINE)

    # If truncated mid-JSON, try to close it
    raw = raw.strip()
    if raw.startswith('[') and not raw.endswith(']'):
        # Find last complete object
        last_brace = raw.rfind('}')
        if last_brace > 0:
            raw = raw[:last_brace + 1] + ']'

    try:
        entities = json.loads(raw)
        if isinstance(entities, list):
            return [e for e in entities if isinstance(e, dict)
                    and "mention" in e and "type" in e
                    and e["type"] in ("person", "event", "location")]
    except json.JSONDecodeError:
        print(f"    [LLM parse error] Could not parse: {raw[:200]}")

    return []


def resolve_llm_entities(db, mentions: list[dict]) -> list[dict]:
    """Resolve LLM-extracted mentions against the DB.

    Returns list of {mention, entity_type, entity_id} for successfully resolved entities.
    """
    from sqlalchemy import text as sql_text

    resolved = []
    seen = set()

    for m in mentions:
        mention = m["mention"]
        etype = m["type"]

        if mention in seen:
            continue
        seen.add(mention)

        if len(mention) < MIN_NAME_LENGTH:
            continue

        # Search DB by type
        if etype == "person":
            row = db.execute(sql_text("""
                SELECT id, name FROM persons
                WHERE (name ILIKE :pat OR name_ko ILIKE :pat)
                  AND importance_score >= 10
                ORDER BY importance_score DESC
                LIMIT 1
            """), {"pat": f"%{mention}%"}).fetchone()
        elif etype == "event":
            row = db.execute(sql_text("""
                SELECT id, title FROM events
                WHERE (title ILIKE :pat OR title_ko ILIKE :pat)
                  AND importance >= 3
                ORDER BY importance DESC
                LIMIT 1
            """), {"pat": f"%{mention}%"}).fetchone()
        elif etype == "location":
            row = db.execute(sql_text("""
                SELECT id, name FROM locations
                WHERE (name ILIKE :pat OR name_ko ILIKE :pat)
                LIMIT 1
            """), {"pat": f"%{mention}%"}).fetchone()
        else:
            continue

        if row:
            resolved.append({
                "mention": mention,
                "entity_type": etype,
                "entity_id": row[0],
                "db_name": row[1],
            })

    return resolved


def apply_llm_tags(text: str, resolved: list[dict]) -> str:
    """Apply entity tags for LLM-resolved entities using text search."""
    # Sort by mention length descending to match longest first
    resolved.sort(key=lambda x: len(x["mention"]), reverse=True)

    claimed = set()
    replacements = []

    for ent in resolved:
        mention = ent["mention"]

        # Word boundary matching
        if re.match(r'^[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', mention):
            pattern = re.escape(mention)
        else:
            pattern = r'\b' + re.escape(mention) + r'\b'

        for m in re.finditer(pattern, text):
            start, end = m.start(), m.end()
            span = set(range(start, end))
            if span & claimed:
                continue

            # Skip if already inside an entity tag
            before = text[max(0, start - 200):start]
            after = text[end:end + 200]
            if re.search(r'\[[^\]]*$', before) and re.search(r'^\]\(entity:', after):
                continue
            if re.search(r'\[[^\]]*$', before) and re.search(r'^\]\(', after):
                continue

            claimed.update(span)
            replacements.append({
                "start": start,
                "end": end,
                "name": m.group(),
                "entity_type": ent["entity_type"],
                "entity_id": ent["entity_id"],
            })
            break  # First occurrence only

    # Apply in reverse order
    replacements.sort(key=lambda x: x["start"], reverse=True)
    for r in replacements:
        tag = f'[{r["name"]}](entity:{r["entity_type"]}:{r["entity_id"]})'
        text = text[:r["start"]] + tag + text[r["end"]:]

    return text


# ─── YAML Processing ───

def load_yaml(path: Path) -> dict:
    """Load a YAML article file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(path: Path, data: dict):
    """Save a YAML article file with proper formatting."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False,
                  width=120, sort_keys=False)


def count_existing_tags(text: str) -> int:
    """Count how many entity tags already exist in text."""
    return len(ENTITY_TAG_RE.findall(text))


def process_article_db(article: dict, name_index: list[tuple]) -> tuple[dict, int]:
    """Process a single article with DB matching mode.

    Each entity is linked only once across the entire article (first occurrence).
    Returns (updated_article, total_links_added).
    """
    total_added = 0
    # Track entities already linked across all sections
    linked_entities: set[tuple] = set()

    for section in article.get("sections", []):
        # Process English content (primary)
        content = section.get("content", "")
        if not content or len(content) < 50:
            continue

        matches = find_matches_in_text(content, name_index)
        # Filter out already-linked entities
        matches = [m for m in matches
                   if (m["entity_type"], m["entity_id"]) not in linked_entities]
        if matches:
            section["content"] = apply_entity_tags(content, matches)
            total_added += len(matches)
            for m in matches:
                linked_entities.add((m["entity_type"], m["entity_id"]))

    return article, total_added


def process_article_llm(article: dict, db) -> tuple[dict, int]:
    """Process a single article with LLM extraction mode.

    Returns (updated_article, total_links_added).
    """
    total_added = 0

    for section in article.get("sections", []):
        content = section.get("content", "")
        if not content or len(content) < 50:
            continue

        existing = count_existing_tags(content)
        title = section.get("title", "")

        # Extract entities with LLM
        mentions = extract_entities_with_llm(content, title)
        if not mentions:
            continue

        # Resolve against DB
        resolved = resolve_llm_entities(db, mentions)
        if not resolved:
            continue

        # Filter out entities that are already tagged
        # Apply tags
        new_content = apply_llm_tags(content, resolved)
        new_count = count_existing_tags(new_content)
        added = new_count - existing

        if added > 0:
            section["content"] = new_content
            total_added += added

    return article, total_added


# ─── Main ───

def cmd_link(args):
    """Main entry point for entity linking."""
    mode = args.mode
    dry_run = args.dry_run

    # Collect YAML files
    if args.file:
        files = [Path(args.file)]
        if not files[0].is_absolute():
            files = [OUTPUT_DIR / args.file]
    else:
        files = sorted(OUTPUT_DIR.glob("*.yaml"))

    if not files:
        print("No YAML files found.")
        return

    print(f"Entity linking — mode={mode}, files={len(files)}, dry_run={dry_run}")
    print()

    db = _get_db_session()

    # For DB mode: preload entities and build index
    name_index = None
    if mode in ("db", "both"):
        print("Loading entities from DB...")
        entities = load_entities_from_db(db)
        name_index = build_name_index(entities)
        print(f"  Name index: {len(name_index)} name variants")
        print()

    total_files = 0
    total_links = 0
    t0 = time.time()

    for fpath in files:
        if not fpath.exists():
            print(f"  SKIP {fpath.name} — not found")
            continue

        article = load_yaml(fpath)
        if not article or "sections" not in article:
            print(f"  SKIP {fpath.name} — no sections")
            continue

        added = 0
        title = article.get("title", "") or article.get("title_ko", "") or fpath.stem

        # DB matching
        if mode in ("db", "both") and name_index:
            article, db_added = process_article_db(article, name_index)
            added += db_added

        # LLM extraction
        if mode in ("llm", "both"):
            article, llm_added = process_article_llm(article, db)
            added += llm_added

        if added > 0:
            status = "DRY" if dry_run else "OK"
            print(f"  {status} {fpath.name}: +{added} links  [{title}]")
            if not dry_run:
                save_yaml(fpath, article)
            total_links += added
            total_files += 1
        else:
            print(f"  --- {fpath.name}: no new links  [{title}]")

    elapsed = time.time() - t0
    db.close()

    print()
    print(f"Done in {elapsed:.1f}s — {total_files} files updated, {total_links} links added")
    if dry_run:
        print("(dry run — no files were modified)")


def main():
    global PERSON_MIN_IMPORTANCE, EVENT_MIN_IMPORTANCE

    parser = argparse.ArgumentParser(description="Entity linking for portal articles")
    parser.add_argument("--mode", choices=["db", "llm", "both"], default="db",
                        help="Linking mode: db (text matching), llm (Ollama), both")
    parser.add_argument("--file", type=str, default=None,
                        help="Process a single YAML file (relative to output/ or absolute)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show changes without writing files")
    parser.add_argument("--person-importance", type=int, default=PERSON_MIN_IMPORTANCE,
                        help=f"Min person importance_score (default: {PERSON_MIN_IMPORTANCE})")
    parser.add_argument("--event-importance", type=int, default=EVENT_MIN_IMPORTANCE,
                        help=f"Min event importance (default: {EVENT_MIN_IMPORTANCE})")
    args = parser.parse_args()

    PERSON_MIN_IMPORTANCE = args.person_importance
    EVENT_MIN_IMPORTANCE = args.event_importance

    cmd_link(args)


if __name__ == "__main__":
    main()
