"""
Create or import History Shift narratives (YAML-based workflow).

Modes:
  --generate "topic"           GPT generates outline + content → YAML
  --generate-from-event ID     Use existing aggregate event as seed
  --generate-from-person ID    Use person biography as seed
  --import file.yaml           Insert YAML into DB (with validation)
  --batch-discover             Find shifts needing enhancement + uncovered events
  --list                       List existing shifts

Import validation:
  - Entity IDs checked against DB (invalid → null, fallback to nearest location)
  - Widget schemas validated (required fields per widget type)
  - parent_shift_slug auto-resolved to parent_shift_id

Options:
  --translate          Auto-translate empty English fields (with --import)
  --dry-run            Preview without writing to DB
  --force              Overwrite existing slug
  --type TYPE          Chain type (aggregate/person_story/place_story/era_story/causal_chain)
  --model MODEL        Outline model (default: gpt-5.2)
  --max-pages N        Max pages per shift (default: 20)
  --min-importance N   Min importance for batch discovery (default: 3)
  --limit N            Max results in batch discovery (default: 50)

Usage:
    cd backend

    # Generate from topic
    python scripts/create_shift.py --generate "그리스-페르시아 전쟁" --type aggregate

    # Generate from existing aggregate event
    python scripts/create_shift.py --generate-from-event 19595 --type aggregate

    # Generate from person
    python scripts/create_shift.py --generate-from-person 5432 --type person_story

    # Import YAML to DB (validates entity IDs + widgets)
    python scripts/create_shift.py --import scripts/output/shift-greco-persian-wars.yaml
    python scripts/create_shift.py --import scripts/output/shift-greco-persian-wars.yaml --translate

    # Discover enhancement candidates
    python scripts/create_shift.py --batch-discover --min-importance 4

    # List existing
    python scripts/create_shift.py --list
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# === .env loading ===
ENV_PATH = Path(__file__).resolve().parent.parent.parent / '.env'
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            os.environ.setdefault(key.strip(), val.strip().strip('"'))

OUTPUT_DIR = Path(__file__).parent / "output"

# ─── YAML handling ───

def _parse_yaml(text: str) -> dict:
    import yaml
    return yaml.safe_load(text)


def _dump_yaml(data: dict) -> str:
    import yaml
    return yaml.dump(data, allow_unicode=True, default_flow_style=False,
                     sort_keys=False, width=120)


def _check_yaml():
    try:
        import yaml  # noqa: F401
        return True
    except ImportError:
        print("ERROR: PyYAML required. Install with: pip install pyyaml")
        sys.exit(1)


# ─── OpenAI ───

def _get_openai_client():
    from openai import OpenAI
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in env or .env")
    return OpenAI(api_key=api_key)


def _estimate_cost(model: str, usage) -> float:
    """Estimate API cost in USD."""
    prices = {
        "gpt-5.2": (1.75, 14.00),
        "gpt-5.2-chat-latest": (1.75, 14.00),
        "gpt-5.1-chat-latest": (1.25, 10.00),
        "gpt-5-mini": (0.25, 2.00),
    }
    in_price, out_price = prices.get(model, (1.75, 14.00))
    in_tokens = getattr(usage, 'prompt_tokens', 0) or 0
    out_tokens = getattr(usage, 'completion_tokens', 0) or 0
    return (in_tokens * in_price + out_tokens * out_price) / 1_000_000


# ─── Slug utility ───

def slugify(title: str) -> str:
    slug = title.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug[:200]


def _find_archive_slug(db, slug: str) -> str:
    """Find next available archive slug: {slug}-v1, {slug}-v2, etc."""
    from sqlalchemy import text as sql_text
    for v in range(1, 100):
        candidate = f"{slug}-v{v}"
        exists = db.execute(
            sql_text("SELECT 1 FROM historical_chains WHERE slug = :s"),
            {"s": candidate}
        ).fetchone()
        if not exists:
            return candidate
    return f"{slug}-v{int(time.time())}"


# ─── DB context gathering ───

def _get_db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.config import get_settings

    settings = get_settings()
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    return Session()


def find_nearest_location(db, lat: float, lng: float, max_distance_deg: float = 1.0):
    """Find the nearest location in DB given coordinates.

    Args:
        lat, lng: target coordinates
        max_distance_deg: maximum distance in degrees (~111km per degree at equator)

    Returns:
        dict with id, name, name_ko, lat, lng, distance or None if nothing within threshold
    """
    from sqlalchemy import text as sql_text

    row = db.execute(sql_text("""
        SELECT id, name, name_ko, latitude, longitude,
               SQRT(POWER(CAST(latitude AS float) - :lat, 2)
                  + POWER(CAST(longitude AS float) - :lng, 2)) AS dist
        FROM locations
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
          AND ABS(CAST(latitude AS float) - :lat) < :max_dist
          AND ABS(CAST(longitude AS float) - :lng) < :max_dist
        ORDER BY dist
        LIMIT 1
    """), {"lat": lat, "lng": lng, "max_dist": max_distance_deg}).fetchone()

    if not row:
        return None

    return {
        "id": row[0], "name": row[1], "name_ko": row[2],
        "lat": float(row[3]), "lng": float(row[4]),
        "distance": float(row[5]),
    }


def gather_context(db, topic: str, chain_type: str,
                   event_id: int = None, person_id: int = None,
                   max_events: int = 50, max_persons: int = 20,
                   max_locations: int = 30) -> dict:
    """Gather DB entities relevant to the topic for GPT context."""
    from sqlalchemy import text as sql_text

    context = {"events": [], "persons": [], "locations": []}

    if event_id:
        # Aggregate event → get children
        # Detect table structure: event_parents table vs parent_event_id column
        has_event_parents = False
        try:
            db.execute(sql_text("SELECT 1 FROM event_parents LIMIT 1"))
            has_event_parents = True
        except Exception:
            db.rollback()

        if has_event_parents:
            children_sql = """
                SELECT e.id, e.title, e.title_ko, e.date_start, e.date_end,
                       e.importance, e.primary_location_id,
                       l.latitude, l.longitude, l.name as loc_name, l.name_ko as loc_name_ko,
                       ed.description
                FROM event_parents ep
                JOIN events e ON e.id = ep.event_id
                LEFT JOIN locations l ON l.id = e.primary_location_id
                LEFT JOIN event_details ed ON ed.event_id = e.id
                WHERE ep.parent_event_id = :parent_id
                ORDER BY e.date_start NULLS LAST, e.importance DESC
                LIMIT :limit
            """
        else:
            children_sql = """
                SELECT e.id, e.title, e.title_ko, e.date_start, e.date_end,
                       e.importance, e.primary_location_id,
                       l.latitude, l.longitude, l.name as loc_name, l.name_ko as loc_name_ko,
                       ed.description
                FROM events e
                LEFT JOIN locations l ON l.id = e.primary_location_id
                LEFT JOIN event_details ed ON ed.event_id = e.id
                WHERE e.parent_event_id = :parent_id
                ORDER BY e.date_start NULLS LAST, e.importance DESC
                LIMIT :limit
            """

        children = db.execute(
            sql_text(children_sql),
            {"parent_id": event_id, "limit": max_events}
        ).fetchall()

        for c in children:
            context["events"].append({
                "id": c[0], "title": c[1], "title_ko": c[2],
                "date_start": c[3], "date_end": c[4],
                "importance": c[5], "location_id": c[6],
                "lat": float(c[7]) if c[7] else None,
                "lng": float(c[8]) if c[8] else None,
                "location_name": c[9], "location_name_ko": c[10],
                "description": (c[11] or "")[:300],
            })

        # Also get parent event info
        parent = db.execute(sql_text("""
            SELECT e.id, e.title, e.title_ko, e.date_start, e.date_end,
                   e.importance, ed.description, ed.description_ko
            FROM events e
            LEFT JOIN event_details ed ON ed.event_id = e.id
            WHERE e.id = :id
        """), {"id": event_id}).fetchone()
        if parent:
            context["parent_event"] = {
                "id": parent[0], "title": parent[1], "title_ko": parent[2],
                "date_start": parent[3], "date_end": parent[4],
                "importance": parent[5],
                "description": (parent[6] or "")[:500],
                "description_ko": (parent[7] or "")[:500],
            }

    elif person_id:
        # Person story → get person + related events
        person = db.execute(sql_text("""
            SELECT p.id, p.name, p.name_ko, p.birth_year, p.death_year,
                   p.global_score, p.importance_score,
                   pd.description
            FROM persons p
            LEFT JOIN person_details pd ON pd.person_id = p.id
            WHERE p.id = :id
        """), {"id": person_id}).fetchone()

        if person:
            context["focal_person"] = {
                "id": person[0], "name": person[1], "name_ko": person[2],
                "birth_year": person[3], "death_year": person[4],
                "global_score": person[5], "importance_score": person[6],
                "description": (person[7] or "")[:500],
            }

        # Get events linked to this person
        events = db.execute(sql_text("""
            SELECT e.id, e.title, e.title_ko, e.date_start, e.date_end,
                   e.importance, e.primary_location_id,
                   l.latitude, l.longitude, l.name as loc_name, l.name_ko as loc_name_ko
            FROM event_persons ep
            JOIN events e ON e.id = ep.event_id
            LEFT JOIN locations l ON l.id = e.primary_location_id
            WHERE ep.person_id = :person_id
            ORDER BY e.date_start NULLS LAST
            LIMIT :limit
        """), {"person_id": person_id, "limit": max_events}).fetchall()

        for ev in events:
            context["events"].append({
                "id": ev[0], "title": ev[1], "title_ko": ev[2],
                "date_start": ev[3], "date_end": ev[4],
                "importance": ev[5], "location_id": ev[6],
                "lat": float(ev[7]) if ev[7] else None,
                "lng": float(ev[8]) if ev[8] else None,
                "location_name": ev[9], "location_name_ko": ev[10],
            })

    else:
        # Topic search → ILIKE matching
        events = db.execute(sql_text("""
            SELECT e.id, e.title, e.title_ko, e.date_start, e.date_end,
                   e.importance, e.primary_location_id,
                   l.latitude, l.longitude, l.name as loc_name, l.name_ko as loc_name_ko,
                   ed.description
            FROM events e
            LEFT JOIN locations l ON l.id = e.primary_location_id
            LEFT JOIN event_details ed ON ed.event_id = e.id
            WHERE e.title ILIKE :pat OR e.title_ko ILIKE :pat
            ORDER BY e.importance DESC NULLS LAST, e.date_start
            LIMIT :limit
        """), {"pat": f"%{topic}%", "limit": max_events}).fetchall()

        for ev in events:
            context["events"].append({
                "id": ev[0], "title": ev[1], "title_ko": ev[2],
                "date_start": ev[3], "date_end": ev[4],
                "importance": ev[5], "location_id": ev[6],
                "lat": float(ev[7]) if ev[7] else None,
                "lng": float(ev[8]) if ev[8] else None,
                "location_name": ev[9], "location_name_ko": ev[10],
                "description": (ev[11] or "")[:300],
            })

        # Search persons too
        persons = db.execute(sql_text("""
            SELECT p.id, p.name, p.name_ko, p.birth_year, p.death_year,
                   p.global_score
            FROM persons p
            WHERE p.name ILIKE :pat OR p.name_ko ILIKE :pat
            ORDER BY p.global_score DESC NULLS LAST
            LIMIT :limit
        """), {"pat": f"%{topic}%", "limit": max_persons}).fetchall()

        for p in persons:
            context["persons"].append({
                "id": p[0], "name": p[1], "name_ko": p[2],
                "birth_year": p[3], "death_year": p[4],
                "global_score": p[5],
            })

    # Collect unique location IDs from events
    loc_ids = set()
    for ev in context["events"]:
        if ev.get("location_id"):
            loc_ids.add(ev["location_id"])

    # Fetch all relevant locations with coordinates
    if loc_ids:
        locs = db.execute(sql_text("""
            SELECT id, name, name_ko, latitude, longitude
            FROM locations
            WHERE id = ANY(:ids) AND latitude IS NOT NULL
        """), {"ids": list(loc_ids)}).fetchall()

        for loc in locs:
            context["locations"].append({
                "id": loc[0], "name": loc[1], "name_ko": loc[2],
                "lat": float(loc[3]), "lng": float(loc[4]),
            })

    return context


# ─── Step 1: Outline (Reasoning Model) ───

OUTLINE_SYSTEM_PROMPT = """\
You are a senior history content architect for CHALDEAS, a 3D globe history system.
Your job: design the OUTLINE for a History Shift — a multi-page narrative that plays on a 3D globe.

Each shift is a sequence of pages. Each page shows a location on the globe + narrative + widgets.
Pages are grouped into chapters (1-4 chapters per shift).

CRITICAL CONSTRAINTS:
1. Every page MUST link to at least one DB entity (event_id, person_id, or location_id).
   You will receive a list of available DB entities. Use their IDs.
2. If a page has no matching event_id or person_id, it MUST have a location_id.
3. transition_type: one of "causes", "follows", "parallel", "background", "consequence", "enables", "opposes"
4. transition_strength: integer 1-5
5. importance: integer 1-5
6. widget_hints: suggest 1-3 widget types per page from this list:
   primary_quote, faction_vs, dramatic_stat, person_card, battle_stats,
   mini_timeline, era_context, narrator_aside, modern_equivalent,
   what_if, historian_note, we_dont_know, conflicting_accounts,
   territory_change, alliance_diagram
7. key_facts: 3-5 specific facts (numbers, names, dates) the content writer should use.
8. GLOBE MOVEMENT: The globe camera moves to each page's location.
   - Prefer DIFFERENT locations for consecutive pages so the globe visibly moves.
   - If two consecutive pages MUST share the same location (e.g., two phases of one battle),
     use different camera_altitude values to change the viewer's perspective.
   - For the opening/closing pages, DO NOT reuse the parent aggregate event_id.
     Find a relevant specific location_id instead.
9. camera_altitude: float controlling globe zoom per page.
   - 0.1-0.3: Close (single city, battlefield detail)
   - 0.4-0.8: Medium (region, country)
   - 1.0-1.5: Wide (continent, multiple regions)
   - 2.0+: Overview (full theater, zoomed out)
   Default 0.5 for most pages. Use higher for overview/transition pages.
10. highlight_locations: Optional array for overview pages that discuss multiple regions.
    Format: [{"lat": 35.1, "lng": 114.3, "label": "Jingxing", "label_ko": "정형"}, ...]
    Maximum 5 locations. The globe will show these as additional markers.

OUTPUT: JSON with this structure:
{
  "slug": "kebab-case-english",
  "chain_type": "aggregate",
  "title": "English Title",
  "title_ko": "한국어 제목",
  "summary_ko": "2~3문장 한국어 요약",
  "year_start": -499,
  "year_end": -449,
  "globe_importance": 4,
  "chapters": [{
    "chapter_number": 1,
    "chapter_title": "Chapter Title",
    "chapter_title_ko": "챕터 제목",
    "pages": [{
      "sequence": 0,
      "title": "Page Title",
      "title_ko": "페이지 제목",
      "narrative_ko": "한 줄 요약",
      "event_id": 19580,
      "person_id": null,
      "location_id": 8100,
      "importance": 3,
      "is_keystone": false,
      "transition_type": "causes",
      "transition_strength": 3,
      "widget_hints": ["primary_quote", "era_context"],
      "key_facts": ["499 BCE", "20 Athenian ships", "Sardis burned"],
      "camera_altitude": 0.5,
      "highlight_locations": null
    }]
  }],
  "entity_roles": [
    {"person_id": 1234, "role": "protagonist", "importance": 5, "first_appearance": 0}
  ]
}

RULES:
- {max_pages} pages maximum. Quality > quantity.
- Chapters: use 1 for short shifts (≤6 pages), 2-3 for medium (7-15), 3-4 for long (16+).
- Narrative arc: 왜? → 누가? → 어떻게? → 전환점 → 그래서?
- First page should hook the reader. Last page should provide legacy/reflection.
- entity_roles: list key persons with roles (protagonist/antagonist/supporting/catalyst/witness).
- Use ONLY entity IDs from the provided DB context. Do NOT invent IDs.
"""

OUTLINE_USER_TEMPLATE = """\
Topic: {topic}
Chain type: {chain_type}
Max pages: {max_pages}

=== DB CONTEXT (available entities) ===

{db_context}

=== END DB CONTEXT ===

Design a detailed shift outline. Use the DB entity IDs above.
Every page must have at least one entity ID (event_id, person_id, or location_id).
Output ONLY valid JSON. No markdown code blocks.
"""


# ─── Step 2: Content (Chat Model, per page) ───

CONTENT_SYSTEM_PROMPT = """\
You are a history content writer for CHALDEAS, a 3D globe history system.
You write engaging narratives + widget data for shift pages.

For each page, output a JSON object with:
{
  "page_narrative_ko": "200~400자 한국어 내러티브. 현장감 있게.",
  "page_narrative": "",
  "widgets": [
    {
      "type": "widget_type",
      "slot": "left|right|bottom",
      "priority": 1,
      "data": { ... }
    }
  ]
}

STYLE for page_narrative_ko:
- 다큐멘터리 내레이션처럼. 현장감 + 인과관계.
- 구체적 숫자, 인용, 일화 사용.
- "너라면 어땠을까?" 같은 직접적 질문 OK.
- 200~400자 (너무 길지 않게).

WIDGET DATA RULES:
- All text fields need both English and Korean: "text" + "text_ko", "label" + "label_ko" etc.
- Each widget must have: type, slot, priority, data.
- slot: "left" (default), "right" (faction_vs/battle_stats), "bottom" (era_context).
- priority: 1 = most important, 5 = least.

AVAILABLE WIDGET TYPES and their data fields:

primary_quote: {text, text_ko, source, source_ko, speaker, speaker_ko, year}
faction_vs: {left_name, left_name_ko, left_commander, left_commander_ko, left_strength, left_strength_ko, right_name, right_name_ko, right_commander, right_commander_ko, right_strength, right_strength_ko, outcome, outcome_ko}
dramatic_stat: {number, suffix, label, label_ko, context, context_ko}
person_card: {name, name_ko, role, role_ko, birth_year, death_year, summary, summary_ko}
battle_stats: {heading, heading_ko, stats: [{label, label_ko, value, value_ko}], significance, significance_ko}
mini_timeline: {heading, heading_ko, events: [{year, label, label_ko, highlight?}]}
era_context: {heading, heading_ko, items: [{region, region_ko, text, text_ko}]}
narrator_aside: {text, text_ko, tone: "reflective|humorous|dramatic"}
modern_equivalent: {ancient, ancient_ko, modern, modern_ko, explanation, explanation_ko}
what_if: {question, question_ko, scenario, scenario_ko}
historian_note: {claim, claim_ko, source, source_ko, note, note_ko}
we_dont_know: {question, question_ko, theories: [{theory, theory_ko}]}
conflicting_accounts: {topic, topic_ko, accounts: [{source, source_ko, claim, claim_ko}]}

Output ONLY valid JSON. No markdown code blocks.
"""

CONTENT_USER_TEMPLATE = """\
Shift: {shift_title}
Page {page_num}/{total_pages}: "{page_title}"
Chapter: {chapter_title}

Key facts: {key_facts}
Widget hints: {widget_hints}
Transition: {transition_type} (strength {transition_strength})

Previous page summary: {prev_summary}

Write the page narrative (200~400자 Korean) and generate {widget_count} widgets.
Output ONLY valid JSON.
"""


# ─── Step 3: Translation ───

TRANSLATE_SYSTEM_PROMPT = """\
You are a professional translator for a history education platform.
Translate the given Korean text to English.
Maintain the same tone: documentary-style, engaging, educational.
Keep proper nouns in their conventional English forms.
Output ONLY the translated text, nothing else.
"""


def _translate_text(client, text_ko: str) -> str:
    if not text_ko or not text_ko.strip():
        return ""
    resp = client.chat.completions.create(
        model="gpt-5.1-chat-latest",
        messages=[
            {"role": "system", "content": TRANSLATE_SYSTEM_PROMPT},
            {"role": "user", "content": text_ko.strip()},
        ],
        max_completion_tokens=4096,
    )
    return resp.choices[0].message.content.strip()


# ─── Format DB context for prompt ───

def _format_db_context(context: dict) -> str:
    lines = []

    if context.get("parent_event"):
        pe = context["parent_event"]
        lines.append("=== PARENT EVENT ===")
        lines.append(f"  id={pe['id']}  {pe['title']}  ({pe.get('title_ko', '')})")
        lines.append(f"  date: {pe.get('date_start')} ~ {pe.get('date_end')}")
        if pe.get("description"):
            lines.append(f"  desc: {pe['description'][:300]}")
        lines.append("")

    if context.get("focal_person"):
        fp = context["focal_person"]
        lines.append("=== FOCAL PERSON ===")
        lines.append(f"  id={fp['id']}  {fp['name']}  ({fp.get('name_ko', '')})")
        lines.append(f"  born: {fp.get('birth_year')}  died: {fp.get('death_year')}")
        if fp.get("description"):
            lines.append(f"  desc: {fp['description'][:300]}")
        lines.append("")

    if context["events"]:
        lines.append(f"=== EVENTS ({len(context['events'])}) ===")
        for ev in context["events"]:
            loc_info = ""
            if ev.get("location_name"):
                loc_info = f"  @{ev['location_name']}(loc_id={ev.get('location_id')})"
            desc_snip = ""
            if ev.get("description"):
                desc_snip = f"  | {ev['description'][:150]}"
            lines.append(
                f"  event_id={ev['id']}  {ev['title']}"
                f"  ({ev.get('title_ko', '')})"
                f"  [{ev.get('date_start')} ~ {ev.get('date_end')}]"
                f"  imp={ev.get('importance')}"
                f"{loc_info}{desc_snip}"
            )
        lines.append("")

    if context["persons"]:
        lines.append(f"=== PERSONS ({len(context['persons'])}) ===")
        for p in context["persons"]:
            lines.append(
                f"  person_id={p['id']}  {p['name']}"
                f"  ({p.get('name_ko', '')})"
                f"  [{p.get('birth_year')} ~ {p.get('death_year')}]"
                f"  score={p.get('global_score')}"
            )
        lines.append("")

    if context["locations"]:
        lines.append(f"=== LOCATIONS ({len(context['locations'])}) ===")
        for loc in context["locations"]:
            lines.append(
                f"  location_id={loc['id']}  {loc['name']}"
                f"  ({loc.get('name_ko', '')})"
                f"  [{loc['lat']:.2f}, {loc['lng']:.2f}]"
            )
        lines.append("")

    return "\n".join(lines) if lines else "(No DB entities found for this topic)"


# ─── Generate command ───

def cmd_generate(args):
    """Generate shift via 3-step agent: context → outline → content."""
    client = _get_openai_client()
    db = _get_db_session()

    topic = args.generate or ""
    chain_type = args.type or "aggregate"
    outline_model = args.model or "gpt-5.2"
    content_model = "gpt-5.2-chat-latest"
    max_pages = args.max_pages or 20
    total_cost = 0.0
    t_start = time.time()

    event_id = args.generate_from_event
    person_id = args.generate_from_person

    # Determine topic from DB if using --generate-from-event/person
    if event_id and not topic:
        from sqlalchemy import text as sql_text
        row = db.execute(sql_text(
            "SELECT title, title_ko FROM events WHERE id = :id"
        ), {"id": event_id}).fetchone()
        if row:
            topic = row[1] or row[0]
        else:
            print(f"ERROR: Event {event_id} not found")
            return

    if person_id and not topic:
        from sqlalchemy import text as sql_text
        row = db.execute(sql_text(
            "SELECT name, name_ko FROM persons WHERE id = :id"
        ), {"id": person_id}).fetchone()
        if row:
            topic = row[1] or row[0]
            chain_type = "person_story"
        else:
            print(f"ERROR: Person {person_id} not found")
            return

    print(f"=== Shift Generation (3-step agent) ===")
    print(f"  Topic: {topic}")
    print(f"  Type: {chain_type}")
    print(f"  Max pages: {max_pages}")
    print(f"  Step 1 model: {outline_model} (reasoning)")
    print(f"  Step 2 model: {content_model} (writing)")

    # ─── Step 0: Gather DB context ───
    print(f"\n--- Step 0: Gathering DB context ---")
    t0 = time.time()
    context = gather_context(db, topic, chain_type,
                             event_id=event_id, person_id=person_id)
    db.close()

    n_events = len(context["events"])
    n_persons = len(context["persons"])
    n_locations = len(context["locations"])
    print(f"  Found: {n_events} events, {n_persons} persons, {n_locations} locations")
    print(f"  Time: {time.time() - t0:.1f}s")

    if n_events == 0 and n_persons == 0:
        print("  WARNING: No DB entities found. GPT will work without entity IDs.")
        print("  Pages may fail the segment_has_entity constraint on import.")

    db_context_str = _format_db_context(context)

    # ─── Step 1: Generate outline ───
    print(f"\n--- Step 1: Outline ({outline_model}) ---")
    t1 = time.time()

    resp1 = client.chat.completions.create(
        model=outline_model,
        messages=[
            {"role": "system", "content": OUTLINE_SYSTEM_PROMPT.replace("{max_pages}", str(max_pages))},
            {"role": "user", "content": OUTLINE_USER_TEMPLATE.format(
                topic=topic, chain_type=chain_type,
                max_pages=max_pages, db_context=db_context_str,
            )},
        ],
        max_completion_tokens=16384,
    )

    outline_raw = resp1.choices[0].message.content.strip()
    u1 = resp1.usage
    cost1 = _estimate_cost(outline_model, u1)
    total_cost += cost1

    # Extract JSON
    json_match = re.search(r'\{[\s\S]*\}', outline_raw)
    if not json_match:
        print(f"  ERROR: No JSON found in outline response")
        print(f"  Raw: {outline_raw[:500]}")
        return

    try:
        outline = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        print(f"  ERROR: Invalid JSON: {e}")
        print(f"  Raw: {outline_raw[:500]}")
        return

    slug = outline.get("slug", slugify(topic))
    chapters = outline.get("chapters", [])
    total_pages = sum(len(ch.get("pages", [])) for ch in chapters)

    print(f"  Slug: {slug}")
    print(f"  Title: {outline.get('title_ko', outline.get('title', '?'))}")
    print(f"  Chapters: {len(chapters)}, Pages: {total_pages}")
    print(f"  Time: {time.time() - t1:.1f}s | "
          f"Tokens: {u1.prompt_tokens}in/{u1.completion_tokens}out | "
          f"Cost: ${cost1:.3f}")

    # ─── Step 2: Write content for each page ───
    print(f"\n--- Step 2: Writing {total_pages} pages ({content_model}) ---")

    all_pages = []  # flat list with chapter info
    for ch in chapters:
        for page in ch.get("pages", []):
            page["_chapter_number"] = ch.get("chapter_number", 1)
            page["_chapter_title"] = ch.get("chapter_title", "")
            page["_chapter_title_ko"] = ch.get("chapter_title_ko", "")
            all_pages.append(page)

    prev_summary = "(This is the first page)"
    for i, page in enumerate(all_pages):
        page_title = page.get("title_ko", page.get("title", f"Page {i+1}"))
        widget_hints = page.get("widget_hints", [])
        key_facts = page.get("key_facts", [])
        widget_count = min(len(widget_hints), 3) if widget_hints else 1

        print(f"  [{i+1}/{total_pages}] {page_title}...", end="", flush=True)
        t2 = time.time()

        resp2 = client.chat.completions.create(
            model=content_model,
            messages=[
                {"role": "system", "content": CONTENT_SYSTEM_PROMPT},
                {"role": "user", "content": CONTENT_USER_TEMPLATE.format(
                    shift_title=outline.get("title_ko", topic),
                    page_num=i + 1,
                    total_pages=total_pages,
                    page_title=page_title,
                    chapter_title=page.get("_chapter_title_ko", ""),
                    key_facts=", ".join(str(f) for f in key_facts) if key_facts else "none",
                    widget_hints=", ".join(widget_hints) if widget_hints else "none",
                    transition_type=page.get("transition_type", "follows"),
                    transition_strength=page.get("transition_strength", 3),
                    prev_summary=prev_summary,
                    widget_count=widget_count,
                )},
            ],
            max_completion_tokens=4096,
        )

        content_raw = resp2.choices[0].message.content.strip()
        u2 = resp2.usage
        cost2 = _estimate_cost(content_model, u2)
        total_cost += cost2

        # Parse JSON response
        content_json_match = re.search(r'\{[\s\S]*\}', content_raw)
        if content_json_match:
            try:
                content_data = json.loads(content_json_match.group())
            except json.JSONDecodeError:
                content_data = {"page_narrative_ko": content_raw, "widgets": []}
        else:
            content_data = {"page_narrative_ko": content_raw, "widgets": []}

        page["_page_narrative_ko"] = content_data.get("page_narrative_ko", "")
        page["_page_narrative"] = content_data.get("page_narrative", "")
        page["_widgets"] = content_data.get("widgets", [])

        char_count = len(page["_page_narrative_ko"])
        n_widgets = len(page["_widgets"])
        print(f" {char_count}자, {n_widgets}w | {time.time() - t2:.1f}s | ${cost2:.3f}")

        # Set prev_summary for next page
        prev_summary = page.get("narrative_ko", page.get("title_ko", ""))[:100]

    # ─── Assemble YAML ───
    yaml_chapters = []
    for ch in chapters:
        yaml_pages = []
        for page in ch.get("pages", []):
            yaml_pages.append({
                "sequence": page.get("sequence", 0),
                "title": page.get("title", ""),
                "title_ko": page.get("title_ko", ""),
                "narrative_ko": page.get("narrative_ko", ""),
                "narrative": page.get("narrative", ""),
                "page_narrative_ko": page.get("_page_narrative_ko", ""),
                "page_narrative": page.get("_page_narrative", ""),
                "year_start": page.get("year_start"),
                "year_end": page.get("year_end"),
                "event_id": page.get("event_id"),
                "person_id": page.get("person_id"),
                "location_id": page.get("location_id"),
                "period_id": page.get("period_id"),
                "importance": page.get("importance", 3),
                "is_keystone": page.get("is_keystone", False),
                "transition_type": page.get("transition_type"),
                "transition_strength": page.get("transition_strength"),
                "camera_altitude": page.get("camera_altitude"),
                "highlight_locations": page.get("highlight_locations"),
                "widgets": page.get("_widgets", []),
            })

        yaml_chapters.append({
            "chapter_number": ch.get("chapter_number", 1),
            "chapter_title": ch.get("chapter_title", ""),
            "chapter_title_ko": ch.get("chapter_title_ko", ""),
            "pages": yaml_pages,
        })

    shift_data = {
        "slug": slug,
        "chain_type": chain_type,
        "title": outline.get("title", ""),
        "title_ko": outline.get("title_ko", ""),
        "summary_ko": outline.get("summary_ko", ""),
        "summary": outline.get("summary", ""),
        "focal_event_id": event_id,
        "focal_person_id": person_id,
        "focal_location_id": outline.get("focal_location_id"),
        "focal_period_id": outline.get("focal_period_id"),
        "year_start": outline.get("year_start"),
        "year_end": outline.get("year_end"),
        "globe_importance": outline.get("globe_importance", 3),
        "display_type": "split",
        "is_auto_generated": True,
        "generation_model": f"{outline_model} + {content_model}",
        "status": "user",
        "chapters": yaml_chapters,
        "entity_roles": outline.get("entity_roles", []),
    }

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"shift-{slug}.yaml"
    out_path.write_text(_dump_yaml(shift_data), encoding='utf-8')

    total_elapsed = time.time() - t_start
    total_chars = sum(
        len(p.get("_page_narrative_ko", ""))
        for p in all_pages
    )

    print(f"\n=== Done ===")
    print(f"  Saved: {out_path}")
    print(f"  Total: {len(yaml_chapters)} chapters, {total_pages} pages, {total_chars}자")
    print(f"  Time: {total_elapsed:.1f}s")
    print(f"  Cost: ~${total_cost:.3f}")
    print(f"\n  Next steps:")
    print(f"    1. Review: {out_path}")
    print(f"    2. Import: python scripts/create_shift.py --import {out_path}")
    print(f"    3. With translation: add --translate flag")


# ─── Validation ───

def _validate_entity_ids(db, chapters: list, entity_roles: list = None) -> list:
    """Validate all entity IDs in pages exist in DB. Fix missing ones.

    - Invalid IDs → set to None + warn
    - Pages with no entity left → try find_nearest_location() from lat/lng in YAML
    - Returns list of warning strings
    """
    from sqlalchemy import text as sql_text

    # Collect all unique IDs
    event_ids = set()
    person_ids = set()
    location_ids = set()
    period_ids = set()

    for ch in chapters:
        for page in ch.get("pages", []):
            if page.get("event_id"):
                event_ids.add(page["event_id"])
            if page.get("person_id"):
                person_ids.add(page["person_id"])
            if page.get("location_id"):
                location_ids.add(page["location_id"])
            if page.get("period_id"):
                period_ids.add(page["period_id"])

    # Also check entity_roles
    role_person_ids = set()
    role_event_ids = set()
    role_location_ids = set()
    if entity_roles:
        for role in entity_roles:
            if role.get("person_id"):
                role_person_ids.add(role["person_id"])
            if role.get("event_id"):
                role_event_ids.add(role["event_id"])
            if role.get("location_id"):
                role_location_ids.add(role["location_id"])

    all_event_ids = event_ids | role_event_ids
    all_person_ids = person_ids | role_person_ids
    all_location_ids = location_ids | role_location_ids

    # Batch-check existence
    valid_events = set()
    if all_event_ids:
        rows = db.execute(sql_text(
            "SELECT id FROM events WHERE id = ANY(:ids)"
        ), {"ids": list(all_event_ids)}).fetchall()
        valid_events = {r[0] for r in rows}

    valid_persons = set()
    if all_person_ids:
        rows = db.execute(sql_text(
            "SELECT id FROM persons WHERE id = ANY(:ids)"
        ), {"ids": list(all_person_ids)}).fetchall()
        valid_persons = {r[0] for r in rows}

    valid_locations = set()
    if all_location_ids:
        rows = db.execute(sql_text(
            "SELECT id FROM locations WHERE id = ANY(:ids)"
        ), {"ids": list(all_location_ids)}).fetchall()
        valid_locations = {r[0] for r in rows}

    valid_periods = set()
    if period_ids:
        rows = db.execute(sql_text(
            "SELECT id FROM periods WHERE id = ANY(:ids)"
        ), {"ids": list(period_ids)}).fetchall()
        valid_periods = {r[0] for r in rows}

    warnings = []

    # Fix pages
    seq = 0
    for ch in chapters:
        for page in ch.get("pages", []):
            title = page.get("title", page.get("title_ko", f"seq={seq}"))

            if page.get("event_id") and page["event_id"] not in valid_events:
                warnings.append(f"  Page '{title}': event_id={page['event_id']} not found → null")
                page["event_id"] = None

            if page.get("person_id") and page["person_id"] not in valid_persons:
                warnings.append(f"  Page '{title}': person_id={page['person_id']} not found → null")
                page["person_id"] = None

            if page.get("location_id") and page["location_id"] not in valid_locations:
                warnings.append(f"  Page '{title}': location_id={page['location_id']} not found → null")
                page["location_id"] = None

            if page.get("period_id") and page["period_id"] not in valid_periods:
                warnings.append(f"  Page '{title}': period_id={page['period_id']} not found → null")
                page["period_id"] = None

            # Check if page still has at least one entity
            has_entity = any([
                page.get("event_id"), page.get("person_id"),
                page.get("location_id"), page.get("period_id"),
            ])

            if not has_entity:
                # Try coordinate-based fallback
                lat = page.get("lat")
                lng = page.get("lng")
                if lat is not None and lng is not None:
                    nearest = find_nearest_location(db, float(lat), float(lng))
                    if nearest:
                        page["location_id"] = nearest["id"]
                        warnings.append(
                            f"  Page '{title}': no entity → mapped to location "
                            f"'{nearest['name']}' (id={nearest['id']}, dist={nearest['distance']:.3f}°)"
                        )
                    else:
                        warnings.append(
                            f"  Page '{title}': NO ENTITY and no nearby location found! "
                            f"Import will fail (segment_has_entity constraint)."
                        )
                else:
                    warnings.append(
                        f"  Page '{title}': NO ENTITY and no lat/lng for fallback! "
                        f"Import will fail (segment_has_entity constraint)."
                    )

            seq += 1

    # Fix entity_roles
    if entity_roles:
        to_remove = []
        for i, role in enumerate(entity_roles):
            if role.get("person_id") and role["person_id"] not in valid_persons:
                warnings.append(f"  Entity role: person_id={role['person_id']} not found → removed")
                to_remove.append(i)
            elif role.get("event_id") and role["event_id"] not in valid_events:
                warnings.append(f"  Entity role: event_id={role['event_id']} not found → removed")
                to_remove.append(i)
            elif role.get("location_id") and role["location_id"] not in valid_locations:
                warnings.append(f"  Entity role: location_id={role['location_id']} not found → removed")
                to_remove.append(i)

        for i in reversed(to_remove):
            entity_roles.pop(i)

    return warnings


# ─── Widget schema validation ───

WIDGET_REQUIRED_FIELDS = {
    "primary_quote": ["text_ko"],
    "faction_vs": ["left_name_ko", "right_name_ko"],
    "dramatic_stat": ["number", "label_ko"],
    "person_card": ["name_ko"],
    "battle_stats": ["stats"],
    "mini_timeline": ["events"],
    "era_context": ["items"],
    "narrator_aside": ["text_ko"],
    "modern_equivalent": ["ancient_ko", "modern_ko"],
    "what_if": ["question_ko"],
    "historian_note": ["claim_ko"],
    "we_dont_know": ["question_ko"],
    "conflicting_accounts": ["accounts"],
    "territory_change": ["changes"],
    "alliance_diagram": ["groups"],
}


def _validate_widgets(chapters: list) -> list:
    """Validate widget JSONB structure in all pages.

    Checks:
    - Required fields: type, slot, data
    - Known widget type
    - Required data fields per widget type
    - Valid slot value

    Returns list of warning strings.
    """
    warnings = []
    valid_slots = {"left", "right", "bottom", "overlay"}

    seq = 0
    for ch in chapters:
        for page in ch.get("pages", []):
            title = page.get("title", page.get("title_ko", f"seq={seq}"))
            widgets = page.get("widgets", [])

            if not isinstance(widgets, list):
                warnings.append(f"  Page '{title}': widgets is not a list → reset to []")
                page["widgets"] = []
                seq += 1
                continue

            for wi, widget in enumerate(widgets):
                prefix = f"  Page '{title}' widget[{wi}]"

                if not isinstance(widget, dict):
                    warnings.append(f"{prefix}: not a dict → removed")
                    widgets[wi] = None
                    continue

                # Check required top-level fields
                wtype = widget.get("type")
                if not wtype:
                    warnings.append(f"{prefix}: missing 'type' → removed")
                    widgets[wi] = None
                    continue

                if wtype not in WIDGET_REQUIRED_FIELDS:
                    warnings.append(f"{prefix}: unknown type '{wtype}' → kept (frontend will ignore)")

                slot = widget.get("slot", "left")
                if slot not in valid_slots:
                    warnings.append(f"{prefix}: invalid slot '{slot}' → 'left'")
                    widget["slot"] = "left"

                if "priority" not in widget:
                    widget["priority"] = wi + 1

                data = widget.get("data")
                if not data or not isinstance(data, dict):
                    warnings.append(f"{prefix}: missing or invalid 'data' → removed")
                    widgets[wi] = None
                    continue

                # Check required data fields
                required = WIDGET_REQUIRED_FIELDS.get(wtype, [])
                for field in required:
                    if field not in data or data[field] is None:
                        warnings.append(f"{prefix} ({wtype}): missing required field '{field}'")

            # Remove None entries
            page["widgets"] = [w for w in widgets if w is not None]
            seq += 1

    return warnings


def _validate_camera_and_highlights(chapters: list) -> list:
    """Validate camera_altitude and highlight_locations in all pages.

    Checks:
    - camera_altitude: range 0.05~3.0, clamp if out of bounds
    - highlight_locations: lat/lng required, max 5, label_ko recommended
    - Consecutive same-location pages without camera_altitude → warning

    Returns list of warning strings.
    """
    warnings = []

    prev_event_id = None
    prev_location_id = None
    seq = 0

    for ch in chapters:
        for page in ch.get("pages", []):
            title = page.get("title", page.get("title_ko", f"seq={seq}"))

            # camera_altitude validation
            alt = page.get("camera_altitude")
            if alt is not None:
                try:
                    alt = float(alt)
                    if alt < 0.05:
                        warnings.append(f"  Page '{title}': camera_altitude={alt} < 0.05 → clamped to 0.05")
                        page["camera_altitude"] = 0.05
                    elif alt > 3.0:
                        warnings.append(f"  Page '{title}': camera_altitude={alt} > 3.0 → clamped to 3.0")
                        page["camera_altitude"] = 3.0
                    else:
                        page["camera_altitude"] = alt
                except (ValueError, TypeError):
                    warnings.append(f"  Page '{title}': camera_altitude='{alt}' invalid → removed")
                    page["camera_altitude"] = None

            # highlight_locations validation
            hl = page.get("highlight_locations")
            if hl is not None:
                if not isinstance(hl, list):
                    warnings.append(f"  Page '{title}': highlight_locations not a list → removed")
                    page["highlight_locations"] = None
                else:
                    if len(hl) > 5:
                        warnings.append(f"  Page '{title}': {len(hl)} highlight_locations > 5 → truncated")
                        hl = hl[:5]
                        page["highlight_locations"] = hl

                    valid_hl = []
                    for hi, h in enumerate(hl):
                        if not isinstance(h, dict):
                            warnings.append(f"  Page '{title}': highlight[{hi}] not a dict → skipped")
                            continue
                        if h.get("lat") is None or h.get("lng") is None:
                            warnings.append(f"  Page '{title}': highlight[{hi}] missing lat/lng → skipped")
                            continue
                        # Coerce lat/lng to float
                        try:
                            h["lat"] = float(h["lat"])
                            h["lng"] = float(h["lng"])
                        except (ValueError, TypeError):
                            warnings.append(f"  Page '{title}': highlight[{hi}] lat/lng not numeric → skipped")
                            continue
                        if not h.get("label_ko"):
                            warnings.append(f"  Page '{title}': highlight[{hi}] missing label_ko (recommended)")
                        valid_hl.append(h)

                    page["highlight_locations"] = valid_hl if valid_hl else None

            # Consecutive same-location detection
            cur_event_id = page.get("event_id")
            cur_location_id = page.get("location_id")

            if seq > 0:
                same_event = (cur_event_id and cur_event_id == prev_event_id)
                same_location = (cur_location_id and cur_location_id == prev_location_id)

                if (same_event or same_location) and not page.get("camera_altitude"):
                    shared = f"event_id={cur_event_id}" if same_event else f"location_id={cur_location_id}"
                    warnings.append(
                        f"  Page '{title}' (seq={seq}): same {shared} as previous page — "
                        f"consider adding camera_altitude for perspective change"
                    )

            prev_event_id = cur_event_id
            prev_location_id = cur_location_id
            seq += 1

    return warnings


# ─── Import command ───

def cmd_import(args):
    """Import YAML shift into historical_chains + chain_segments + chain_entity_roles."""
    from sqlalchemy import text as sql_text

    yaml_path = Path(args.import_file)
    if not yaml_path.exists():
        print(f"ERROR: File not found: {yaml_path}")
        sys.exit(1)

    data = _parse_yaml(yaml_path.read_text(encoding='utf-8'))
    slug = data.get("slug", "")
    if not slug:
        print("ERROR: 'slug' field is required")
        sys.exit(1)

    chain_type = args.type or data.get("chain_type", "aggregate")

    # Validate chapters/pages
    chapters = data.get("chapters", [])
    total_pages = sum(len(ch.get("pages", [])) for ch in chapters)
    if total_pages == 0:
        print("ERROR: No pages found in YAML")
        sys.exit(1)

    entity_roles = data.get("entity_roles", [])

    # Open DB for validation (entity IDs + widget schemas)
    db = _get_db_session()

    # --- Entity ID validation ---
    print("  Validating entity IDs...")
    entity_warnings = _validate_entity_ids(db, chapters, entity_roles)
    if entity_warnings:
        print(f"  Entity validation ({len(entity_warnings)} warnings):")
        for w in entity_warnings:
            print(w)

    # Check if any page still has no entity after fixes
    entity_errors = []
    seq = 0
    for ch in chapters:
        for page in ch.get("pages", []):
            has_entity = any([
                page.get("event_id"), page.get("person_id"),
                page.get("location_id"), page.get("period_id"),
            ])
            if not has_entity:
                entity_errors.append(
                    f"  Page seq={seq} '{page.get('title', '?')}' has no valid entity ID")
            seq += 1

    if entity_errors:
        print("\nERROR: segment_has_entity constraint still violated after fixes:")
        for e in entity_errors:
            print(e)
        print("\nEvery page must have at least one of: event_id, person_id, location_id, period_id")
        db.close()
        sys.exit(1)

    # --- Widget schema validation ---
    print("  Validating widgets...")
    widget_warnings = _validate_widgets(chapters)
    if widget_warnings:
        print(f"  Widget validation ({len(widget_warnings)} warnings):")
        for w in widget_warnings:
            print(w)

    # --- Camera + highlight validation ---
    print("  Validating camera & highlights...")
    camera_warnings = _validate_camera_and_highlights(chapters)
    if camera_warnings:
        print(f"  Camera/highlight validation ({len(camera_warnings)} warnings):")
        for w in camera_warnings:
            print(w)

    # --- Resolve parent_shift_slug ---
    parent_shift_id = data.get("parent_shift_id")
    parent_shift_slug = data.get("parent_shift_slug")
    if parent_shift_slug and not parent_shift_id:
        row = db.execute(sql_text(
            "SELECT id FROM historical_chains WHERE slug = :slug"
        ), {"slug": parent_shift_slug}).fetchone()
        if row:
            parent_shift_id = row[0]
            print(f"  Resolved parent_shift_slug '{parent_shift_slug}' → id={parent_shift_id}")
        else:
            print(f"  WARNING: parent_shift_slug '{parent_shift_slug}' not found → ignored")

    # Translate if requested
    if args.translate:
        print("  Auto-translating empty English fields...")
        client = _get_openai_client()
        data = _translate_shift(client, data)

    # Titles
    title = data.get("title") or data.get("title_ko") or slug
    title_ko = data.get("title_ko") or data.get("title") or slug

    print(f"\n  Shift: {title_ko}")
    print(f"  Slug: {slug}")
    print(f"  Type: {chain_type}")
    print(f"  Chapters: {len(chapters)}, Pages: {total_pages}")
    print(f"  Year: {data.get('year_start')} ~ {data.get('year_end')}")

    if args.dry_run:
        print("\n  DRY RUN: Would insert into historical_chains + chain_segments")
        _preview_pages(chapters)
        db.close()
        return
    try:
        # Check if slug exists
        existing = db.execute(
            sql_text("SELECT id, slug FROM historical_chains WHERE slug = :slug"),
            {"slug": slug}
        ).fetchone()

        if existing:
            if not args.force:
                print(f"\n  ERROR: Slug '{slug}' already exists (id={existing[0]})")
                print(f"  Use --force to replace (old version archived)")
                return
            else:
                old_id = existing[0]
                # Archive: rename slug → {slug}-v{N}, status → 'cached'
                archive_slug = _find_archive_slug(db, slug)
                db.execute(sql_text("""
                    UPDATE historical_chains
                    SET slug = :new_slug, status = 'cached'
                    WHERE id = :id
                """), {"new_slug": archive_slug, "id": old_id})
                print(f"  Archived existing shift (id={old_id}) → slug='{archive_slug}', status='cached'")

        # INSERT historical_chains
        result = db.execute(sql_text("""
            INSERT INTO historical_chains
            (chain_type, slug, title, title_ko, summary, summary_ko,
             focal_event_id, focal_person_id, focal_location_id, focal_period_id,
             year_start, year_end, segment_count, status,
             is_auto_generated, generation_model,
             display_type, chapter_count, globe_importance,
             parent_shift_id)
            VALUES
            (:chain_type, :slug, :title, :title_ko, :summary, :summary_ko,
             :focal_event_id, :focal_person_id, :focal_location_id, :focal_period_id,
             :year_start, :year_end, :segment_count, :status,
             :is_auto_generated, :generation_model,
             :display_type, :chapter_count, :globe_importance,
             :parent_shift_id)
            RETURNING id
        """), {
            "chain_type": chain_type,
            "slug": slug,
            "title": title,
            "title_ko": title_ko,
            "summary": data.get("summary", ""),
            "summary_ko": data.get("summary_ko", ""),
            "focal_event_id": data.get("focal_event_id"),
            "focal_person_id": data.get("focal_person_id"),
            "focal_location_id": data.get("focal_location_id"),
            "focal_period_id": data.get("focal_period_id"),
            "year_start": data.get("year_start", 0),
            "year_end": data.get("year_end"),
            "segment_count": total_pages,
            "status": data.get("status", "user"),
            "is_auto_generated": data.get("is_auto_generated", True),
            "generation_model": data.get("generation_model"),
            "display_type": data.get("display_type", "split"),
            "chapter_count": len(chapters),
            "globe_importance": data.get("globe_importance", 3),
            "parent_shift_id": parent_shift_id,
        })
        chain_id = result.fetchone()[0]
        print(f"\n  Inserted historical_chain id={chain_id}")

        # INSERT chain_segments
        seq = 0
        for ch in chapters:
            ch_num = ch.get("chapter_number", 1)
            ch_title = ch.get("chapter_title", "")

            for page in ch.get("pages", []):
                widgets_json = json.dumps(page.get("widgets", []), ensure_ascii=False) \
                    if page.get("widgets") else None

                hl_json = json.dumps(page.get("highlight_locations"), ensure_ascii=False) \
                    if page.get("highlight_locations") else None

                db.execute(sql_text("""
                    INSERT INTO chain_segments
                    (chain_id, sequence_number, title, narrative, narrative_ko,
                     event_id, person_id, location_id, period_id,
                     year_start, year_end,
                     transition_type, transition_strength,
                     chapter_number, chapter_title,
                     page_narrative, page_narrative_ko,
                     importance, is_keystone,
                     widgets, camera_altitude, highlight_locations)
                    VALUES
                    (:chain_id, :seq, :title, :narrative, :narrative_ko,
                     :event_id, :person_id, :location_id, :period_id,
                     :year_start, :year_end,
                     :transition_type, :transition_strength,
                     :chapter_number, :chapter_title,
                     :page_narrative, :page_narrative_ko,
                     :importance, :is_keystone,
                     CAST(:widgets AS jsonb),
                     :camera_altitude,
                     CAST(:highlight_locations AS jsonb))
                """), {
                    "chain_id": chain_id,
                    "seq": seq,
                    "title": page.get("title", ""),
                    "narrative": page.get("narrative", ""),
                    "narrative_ko": page.get("narrative_ko", ""),
                    "event_id": page.get("event_id"),
                    "person_id": page.get("person_id"),
                    "location_id": page.get("location_id"),
                    "period_id": page.get("period_id"),
                    "year_start": page.get("year_start"),
                    "year_end": page.get("year_end"),
                    "transition_type": page.get("transition_type"),
                    "transition_strength": page.get("transition_strength"),
                    "chapter_number": ch_num,
                    "chapter_title": ch_title,
                    "page_narrative": page.get("page_narrative", ""),
                    "page_narrative_ko": page.get("page_narrative_ko", ""),
                    "importance": page.get("importance", 3),
                    "is_keystone": page.get("is_keystone", False),
                    "widgets": widgets_json,
                    "camera_altitude": page.get("camera_altitude"),
                    "highlight_locations": hl_json,
                })
                seq += 1

        print(f"  Inserted {seq} chain_segments")

        # INSERT chain_entity_roles
        entity_roles = data.get("entity_roles", [])
        for role in entity_roles:
            # Determine entity type
            entity_params = {
                "chain_id": chain_id,
                "person_id": role.get("person_id"),
                "location_id": role.get("location_id"),
                "event_id": role.get("event_id"),
                "role": role.get("role", "supporting"),
                "importance": role.get("importance", 3),
                "first_appearance": role.get("first_appearance"),
            }

            # Validate exactly one entity
            entity_count = sum(1 for k in ["person_id", "location_id", "event_id"]
                               if entity_params.get(k))
            if entity_count != 1:
                print(f"  WARNING: Skipping entity_role with {entity_count} entities: {role}")
                continue

            db.execute(sql_text("""
                INSERT INTO chain_entity_roles
                (chain_id, person_id, location_id, event_id,
                 role, importance, first_appearance)
                VALUES
                (:chain_id, :person_id, :location_id, :event_id,
                 :role, :importance, :first_appearance)
            """), entity_params)

        if entity_roles:
            print(f"  Inserted {len(entity_roles)} chain_entity_roles")

        db.commit()
        print(f"\n  Done! Shift '{title_ko}' imported (id={chain_id})")
        print(f"  View: http://localhost:8100/api/v1/shifts/{chain_id}")

    except Exception as e:
        db.rollback()
        print(f"\n  ERROR: {e}")
        raise
    finally:
        db.close()


def _preview_pages(chapters):
    """Print a preview of pages for dry-run."""
    seq = 0
    for ch in chapters:
        ch_num = ch.get("chapter_number", 1)
        ch_title = ch.get("chapter_title", "")
        print(f"\n  Chapter {ch_num}: {ch_title}")
        for page in ch.get("pages", []):
            entity_parts = []
            if page.get("event_id"):
                entity_parts.append(f"event={page['event_id']}")
            if page.get("person_id"):
                entity_parts.append(f"person={page['person_id']}")
            if page.get("location_id"):
                entity_parts.append(f"loc={page['location_id']}")
            if page.get("period_id"):
                entity_parts.append(f"period={page['period_id']}")
            entities = ", ".join(entity_parts) if entity_parts else "NO ENTITY!"

            n_widgets = len(page.get("widgets", []))
            narrative_len = len(page.get("page_narrative_ko", ""))

            title = page.get("title_ko", page.get("title", "?"))
            print(f"    [{seq}] {title}  ({entities})  "
                  f"{narrative_len}자  {n_widgets}w")
            seq += 1


# ─── Translate command ───

def _translate_shift(client, data: dict) -> dict:
    """Fill in empty English fields by translating from Korean."""
    translated = 0

    # Top-level fields
    for ko_field, en_field in [
        ("title_ko", "title"),
        ("summary_ko", "summary"),
    ]:
        ko_val = data.get(ko_field, "")
        if ko_val and not data.get(en_field):
            print(f"    Translating {ko_field} -> en...")
            data[en_field] = _translate_text(client, ko_val)
            translated += 1

    # Page-level fields
    for ch in data.get("chapters", []):
        # Chapter title
        ch_title_ko = ch.get("chapter_title_ko", "")
        if ch_title_ko and not ch.get("chapter_title"):
            print(f"    Translating chapter '{ch_title_ko}' -> en...")
            ch["chapter_title"] = _translate_text(client, ch_title_ko)
            translated += 1

        for page in ch.get("pages", []):
            # Page narrative
            ko_narrative = page.get("page_narrative_ko", "")
            if ko_narrative and not page.get("page_narrative"):
                title = page.get("title_ko", page.get("title", "?"))
                print(f"    Translating page '{title}' narrative -> en...")
                page["page_narrative"] = _translate_text(client, ko_narrative)
                translated += 1

            # Page title
            title_ko = page.get("title_ko", "")
            if title_ko and not page.get("title"):
                page["title"] = _translate_text(client, title_ko)
                translated += 1

            # Narrative (short)
            narrative_ko = page.get("narrative_ko", "")
            if narrative_ko and not page.get("narrative"):
                page["narrative"] = _translate_text(client, narrative_ko)
                translated += 1

    print(f"    Translated {translated} fields")
    return data


def cmd_translate(args):
    """Translate an existing YAML file's empty English fields."""
    yaml_path = Path(args.translate_file)
    if not yaml_path.exists():
        print(f"ERROR: File not found: {yaml_path}")
        sys.exit(1)

    data = _parse_yaml(yaml_path.read_text(encoding='utf-8'))
    client = _get_openai_client()

    print(f"  Translating: {yaml_path}")
    data = _translate_shift(client, data)

    yaml_path.write_text(_dump_yaml(data), encoding='utf-8')
    print(f"  Saved: {yaml_path}")


# ─── List command ───

def cmd_list(args):
    """List all shifts in DB."""
    from sqlalchemy import text as sql_text

    db = _get_db_session()
    try:
        rows = db.execute(sql_text("""
            SELECT id, slug, chain_type, COALESCE(title_ko, title),
                   year_start, year_end, segment_count,
                   globe_importance, status, is_auto_generated,
                   chapter_count
            FROM historical_chains
            ORDER BY chain_type, globe_importance DESC, year_start
        """)).fetchall()

        current_type = None
        for row in rows:
            (sid, slug, ctype, title, yr_s, yr_e,
             seg_count, g_imp, status, auto, ch_count) = row

            if ctype != current_type:
                current_type = ctype
                print(f"\n  [{ctype}]")

            auto_mark = " [auto]" if auto else ""
            yr_range = f"{yr_s}" + (f"~{yr_e}" if yr_e else "")
            print(f"    {sid:5d}  {slug:40s}  {yr_range:>12s}  "
                  f"{seg_count or 0:3d}p {ch_count or 1}ch  "
                  f"imp={g_imp or 3}  {status}{auto_mark}  {title}")

        print(f"\n  Total: {len(rows)} shifts")
    finally:
        db.close()


# ─── Enhance command ───

def _gather_segment_context(db, seg, chain_title: str = "") -> dict:
    """Gather entity details for a single segment to feed GPT."""
    from sqlalchemy import text as sql_text

    ctx = {"event": None, "person": None, "location": None, "shift_title": chain_title}

    if seg.event_id:
        row = db.execute(sql_text("""
            SELECT e.title, e.title_ko, e.date_start, e.date_end, e.importance,
                   ed.description, ed.description_ko,
                   l.name as loc_name, l.name_ko as loc_name_ko
            FROM events e
            LEFT JOIN event_details ed ON ed.event_id = e.id
            LEFT JOIN locations l ON l.id = e.primary_location_id
            WHERE e.id = :id
        """), {"id": seg.event_id}).fetchone()
        if row:
            ctx["event"] = {
                "title": row[0], "title_ko": row[1],
                "date_start": row[2], "date_end": row[3],
                "importance": row[4],
                "description": (row[5] or "")[:400],
                "description_ko": (row[6] or "")[:400],
                "location": row[7], "location_ko": row[8],
            }

    if seg.person_id:
        row = db.execute(sql_text("""
            SELECT p.name, p.name_ko, p.birth_year, p.death_year,
                   pd.description
            FROM persons p
            LEFT JOIN person_details pd ON pd.person_id = p.id
            WHERE p.id = :id
        """), {"id": seg.person_id}).fetchone()
        if row:
            ctx["person"] = {
                "name": row[0], "name_ko": row[1],
                "birth_year": row[2], "death_year": row[3],
                "description": (row[4] or "")[:400],
            }

    if seg.location_id:
        row = db.execute(sql_text("""
            SELECT name, name_ko, latitude, longitude, country
            FROM locations WHERE id = :id
        """), {"id": seg.location_id}).fetchone()
        if row:
            ctx["location"] = {
                "name": row[0], "name_ko": row[1],
                "lat": float(row[2]) if row[2] else None,
                "lng": float(row[3]) if row[3] else None,
                "country": row[4],
            }

    return ctx


def _format_segment_context(ctx: dict) -> str:
    """Format segment context for GPT user prompt."""
    lines = []
    if ctx.get("event"):
        e = ctx["event"]
        lines.append(f"Event: {e['title']} ({e.get('title_ko', '')})")
        lines.append(f"  Date: {e.get('date_start')} ~ {e.get('date_end')}")
        if e.get("location"):
            lines.append(f"  Location: {e['location']} ({e.get('location_ko', '')})")
        if e.get("description_ko"):
            lines.append(f"  Description: {e['description_ko']}")
        elif e.get("description"):
            lines.append(f"  Description: {e['description']}")

    if ctx.get("person"):
        p = ctx["person"]
        lines.append(f"Person: {p['name']} ({p.get('name_ko', '')})")
        lines.append(f"  Life: {p.get('birth_year')} ~ {p.get('death_year')}")
        if p.get("description"):
            lines.append(f"  Bio: {p['description'][:300]}")

    if ctx.get("location"):
        loc = ctx["location"]
        lines.append(f"Location: {loc['name']} ({loc.get('name_ko', '')}) [{loc.get('country', '')}]")

    return "\n".join(lines) if lines else "(No entity details available)"


def _pick_widget_hints(page_index: int, total_pages: int,
                       has_event: bool, has_person: bool,
                       is_keystone: bool) -> list:
    """Pick diverse widget hints based on page position and entity type.

    Avoids repeating the same combo on every page by rotating through pools.
    """
    # Position in narrative arc
    is_first = page_index == 0
    is_last = page_index == total_pages - 1
    is_middle = not is_first and not is_last

    # Widget pools by narrative role
    OPENING = ["era_context", "mini_timeline", "dramatic_stat"]
    ACTION = ["faction_vs", "battle_stats", "primary_quote", "dramatic_stat"]
    DEPTH = ["historian_note", "we_dont_know", "conflicting_accounts"]
    REFLECTION = ["modern_equivalent", "what_if", "narrator_aside"]
    PERSON = ["person_card", "primary_quote"]

    hints = []

    if is_first:
        # Opening: set the scene
        hints.append(OPENING[page_index % len(OPENING)])
        if has_person:
            hints.append("person_card")
        else:
            hints.append("primary_quote")
    elif is_last:
        # Closing: reflection + legacy
        hints.append(REFLECTION[page_index % len(REFLECTION)])
        hints.append("narrator_aside" if "narrator_aside" not in hints else "what_if")
    elif is_keystone:
        # Climax: action + depth
        hints.append(ACTION[page_index % len(ACTION)])
        hints.append(DEPTH[page_index % len(DEPTH)])
    else:
        # Middle pages: rotate through diverse combos
        combos = [
            ["primary_quote", "narrator_aside"],
            ["faction_vs", "dramatic_stat"],
            ["person_card", "historian_note"],
            ["battle_stats", "what_if"],
            ["dramatic_stat", "modern_equivalent"],
            ["primary_quote", "we_dont_know"],
            ["era_context", "primary_quote"],
        ]
        combo = combos[page_index % len(combos)]
        hints.extend(combo)

    # Person override: ensure person_card appears at least once
    if has_person and "person_card" not in hints:
        hints[0] = "person_card"

    # Event battle pages: ensure at least one combat widget
    if has_event and not any(h in hints for h in ["faction_vs", "battle_stats", "dramatic_stat"]):
        hints.append("dramatic_stat")

    return hints[:3]


def cmd_enhance(args):
    """Enhance existing shift pages with narrative + widgets via GPT."""
    from sqlalchemy import text as sql_text
    from app.models.v1.chain import HistoricalChain, ChainSegment

    shift_id = args.enhance
    max_pages = args.max_pages or 20
    content_model = "gpt-5.2-chat-latest"
    total_cost = 0.0
    t_start = time.time()

    db = _get_db_session()
    try:
        # 1. Load shift
        chain = db.execute(sql_text("""
            SELECT id, slug, chain_type, title, title_ko, summary_ko,
                   segment_count, globe_importance
            FROM historical_chains WHERE id = :id
        """), {"id": shift_id}).fetchone()

        if not chain:
            print(f"ERROR: Shift id={shift_id} not found")
            return

        chain_id, slug, chain_type, title, title_ko, summary_ko, seg_count, g_imp = chain
        shift_title = title_ko or title or slug

        print(f"=== Enhance Shift (id={chain_id}) ===")
        print(f"  Title: {shift_title}")
        print(f"  Type: {chain_type}  Pages: {seg_count}  Importance: {g_imp}")

        # 2. Load segments
        segments = db.execute(sql_text("""
            SELECT id, sequence_number, title, narrative_ko,
                   page_narrative_ko, widgets,
                   event_id, person_id, location_id, period_id,
                   importance, is_keystone, chapter_number, chapter_title,
                   year_start, year_end
            FROM chain_segments
            WHERE chain_id = :chain_id
            ORDER BY sequence_number
        """), {"chain_id": chain_id}).fetchall()

        # 3. Filter: pages needing enhancement
        targets = []
        for seg in segments:
            (seg_id, seq, seg_title, narrative_ko,
             page_narr_ko, widgets,
             event_id, person_id, location_id, period_id,
             importance, is_keystone, ch_num, ch_title,
             year_start, year_end) = seg

            needs_narrative = not page_narr_ko or len(page_narr_ko) < 50
            needs_widgets = not widgets or (isinstance(widgets, list) and len(widgets) == 0)

            if args.force or needs_narrative or needs_widgets:
                targets.append({
                    "id": seg_id, "seq": seq, "title": seg_title,
                    "narrative_ko": narrative_ko,
                    "page_narrative_ko": page_narr_ko,
                    "widgets": widgets,
                    "event_id": event_id, "person_id": person_id,
                    "location_id": location_id, "period_id": period_id,
                    "importance": importance or 3,
                    "is_keystone": is_keystone or False,
                    "ch_num": ch_num, "ch_title": ch_title,
                    "year_start": year_start, "year_end": year_end,
                    "needs_narrative": needs_narrative,
                    "needs_widgets": needs_widgets,
                })

        total_segs = len(segments)
        print(f"  Segments needing enhancement: {len(targets)}/{total_segs}")

        if not targets:
            print("  Nothing to enhance. Use --force to rewrite all.")
            return

        # 4. Page range filter
        if args.page_range:
            parts = args.page_range.split("-")
            range_start = int(parts[0])
            range_end = int(parts[1]) if len(parts) > 1 else range_start
            targets = [t for t in targets if range_start <= t["seq"] <= range_end]
            print(f"  After page-range {args.page_range}: {len(targets)} targets")

        # 5. Select top N by importance
        if len(targets) > max_pages:
            targets.sort(key=lambda s: (s["is_keystone"], s["importance"]), reverse=True)
            targets = targets[:max_pages]
            print(f"  Limited to top {max_pages} by importance")

        # Sort back by sequence for coherent prev_summary
        targets.sort(key=lambda s: s["seq"])

        if args.dry_run:
            print(f"\n  DRY RUN: Would enhance {len(targets)} pages")
            for t in targets:
                flags = []
                if t["needs_narrative"]:
                    flags.append("narrative")
                if t["needs_widgets"]:
                    flags.append("widgets")
                print(f"    [{t['seq']:3d}] {t['title'] or '?':40s}  "
                      f"imp={t['importance']}  needs: {', '.join(flags)}")
            return

        # 6. Generate content for each page
        client = _get_openai_client()
        print(f"\n--- Enhancing {len(targets)} pages ({content_model}) ---")

        updated = 0
        prev_summary = "(첫 번째 페이지)"

        for i, target in enumerate(targets):
            seg_title = target["narrative_ko"] or target["title"] or f"Page {target['seq']}"
            print(f"  [{i+1}/{len(targets)}] seq={target['seq']} {seg_title}...",
                  end="", flush=True)
            t2 = time.time()

            # Gather entity context
            class SegProxy:
                pass
            seg_proxy = SegProxy()
            seg_proxy.event_id = target["event_id"]
            seg_proxy.person_id = target["person_id"]
            seg_proxy.location_id = target["location_id"]
            ctx = _gather_segment_context(db, seg_proxy, shift_title)
            ctx_str = _format_segment_context(ctx)

            # Determine widget hints from event type
            widget_hints = _pick_widget_hints(
                page_index=i, total_pages=len(targets),
                has_event=bool(target["event_id"]),
                has_person=bool(target["person_id"]),
                is_keystone=target["is_keystone"],
            )
            widget_count = min(len(widget_hints), 3)

            year_display = ""
            if target["year_start"]:
                yr = target["year_start"]
                year_display = f"{abs(yr)} BCE" if yr < 0 else f"{yr} CE"

            resp = client.chat.completions.create(
                model=content_model,
                messages=[
                    {"role": "system", "content": CONTENT_SYSTEM_PROMPT},
                    {"role": "user", "content": CONTENT_USER_TEMPLATE.format(
                        shift_title=shift_title,
                        page_num=target["seq"] + 1,
                        total_pages=total_segs,
                        page_title=seg_title,
                        chapter_title=target.get("ch_title") or "",
                        key_facts=ctx_str,
                        widget_hints=", ".join(widget_hints),
                        transition_type="follows",
                        transition_strength=3,
                        prev_summary=prev_summary,
                        widget_count=widget_count,
                    )},
                ],
                max_completion_tokens=4096,
            )

            content_raw = resp.choices[0].message.content.strip()
            usage = resp.usage
            cost = _estimate_cost(content_model, usage)
            total_cost += cost

            # Parse JSON
            json_match = re.search(r'\{[\s\S]*\}', content_raw)
            if json_match:
                try:
                    content_data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    content_data = {"page_narrative_ko": content_raw, "widgets": []}
            else:
                content_data = {"page_narrative_ko": content_raw, "widgets": []}

            new_narrative = content_data.get("page_narrative_ko", "")
            new_widgets = content_data.get("widgets", [])

            char_count = len(new_narrative)
            n_widgets = len(new_widgets)
            elapsed = time.time() - t2
            print(f" {char_count}자, {n_widgets}w | {elapsed:.1f}s | ${cost:.3f}")

            # 7. UPDATE in DB
            update_parts = []
            update_params = {"seg_id": target["id"]}

            if target["needs_narrative"] or args.force:
                if new_narrative:
                    update_parts.append("page_narrative_ko = :narr")
                    update_params["narr"] = new_narrative

            if target["needs_widgets"] or args.force:
                if new_widgets:
                    update_parts.append("widgets = CAST(:widgets AS jsonb)")
                    update_params["widgets"] = json.dumps(new_widgets, ensure_ascii=False)

            if update_parts:
                db.execute(sql_text(
                    f"UPDATE chain_segments SET {', '.join(update_parts)} WHERE id = :seg_id"
                ), update_params)
                updated += 1

            prev_summary = (new_narrative or seg_title)[:100]

        db.commit()

        total_elapsed = time.time() - t_start
        print(f"\n=== Done ===")
        print(f"  Enhanced: {updated}/{len(targets)} pages")
        print(f"  Time: {total_elapsed:.1f}s")
        print(f"  Cost: ~${total_cost:.3f}")
        print(f"  View: http://localhost:8100/api/v1/shifts/{chain_id}")

    except Exception as e:
        db.rollback()
        print(f"\n  ERROR: {e}")
        raise
    finally:
        db.close()


# ─── Batch discovery ───

def cmd_batch_discover(args):
    """Discover shifts that need enhancement or aggregate events without shifts."""
    from sqlalchemy import text as sql_text

    db = _get_db_session()
    min_importance = args.min_importance or 3
    limit = args.limit or 50

    try:
        # 1. Existing shifts with no widgets (candidates for --enhance)
        no_widgets = db.execute(sql_text("""
            SELECT hc.id, hc.slug, hc.chain_type,
                   COALESCE(hc.title_ko, hc.title) as title,
                   hc.segment_count, hc.globe_importance,
                   COUNT(cs.id) as total_pages,
                   COUNT(cs.widgets) as pages_with_widgets,
                   SUM(CASE WHEN cs.page_narrative_ko IS NOT NULL
                            AND LENGTH(cs.page_narrative_ko) > 50 THEN 1 ELSE 0 END)
                   as pages_with_narrative
            FROM historical_chains hc
            LEFT JOIN chain_segments cs ON cs.chain_id = hc.id
            WHERE hc.globe_importance >= :min_imp
            GROUP BY hc.id, hc.slug, hc.chain_type, hc.title, hc.title_ko, hc.segment_count, hc.globe_importance
            HAVING COUNT(cs.widgets) = 0
            ORDER BY hc.globe_importance DESC, hc.segment_count DESC
            LIMIT :limit
        """), {"min_imp": min_importance, "limit": limit}).fetchall()

        print(f"\n=== Shifts needing enhancement (no widgets, imp>={min_importance}) ===")
        if no_widgets:
            for row in no_widgets:
                (sid, slug, ctype, title, seg_count,
                 g_imp, total_pages, w_pages, n_pages) = row
                print(f"  {sid:5d}  imp={g_imp}  {total_pages or 0:3d}p  "
                      f"narrative={n_pages or 0}p  {ctype:15s}  {title}")
            print(f"\n  Found: {len(no_widgets)} shifts without widgets")
        else:
            print("  None found.")

        # 2. Aggregate events that don't have corresponding shifts
        # Detect if event_parents table exists (vs parent_event_id column)
        has_event_parents = False
        try:
            db.execute(sql_text("SELECT 1 FROM event_parents LIMIT 1"))
            has_event_parents = True
        except Exception:
            db.rollback()

        if has_event_parents:
            child_count_sql = "(SELECT COUNT(*) FROM event_parents ep WHERE ep.parent_event_id = e.id)"
        else:
            child_count_sql = "(SELECT COUNT(*) FROM events c WHERE c.parent_event_id = e.id)"

        no_shift = db.execute(sql_text(f"""
            SELECT e.id, e.title, COALESCE(e.title_ko, e.title) as title_display,
                   e.date_start, e.importance,
                   {child_count_sql} as child_count
            FROM events e
            WHERE e.is_aggregate = true
              AND e.importance >= :min_imp
              AND NOT EXISTS (
                  SELECT 1 FROM historical_chains hc
                  WHERE hc.focal_event_id = e.id AND hc.chain_type = 'aggregate'
              )
              AND {child_count_sql} >= 3
            ORDER BY e.importance DESC, child_count DESC
            LIMIT :limit
        """), {"min_imp": min_importance, "limit": limit}).fetchall()

        print(f"\n=== Aggregate events without shifts (imp>={min_importance}, 3+ children) ===")
        if no_shift:
            for row in no_shift:
                (eid, title, title_disp, yr, imp, children) = row
                yr_str = f"{abs(yr)} BCE" if yr and yr < 0 else f"{yr} CE" if yr else "?"
                print(f"  event_id={eid:6d}  imp={imp}  {children:3d} children  "
                      f"{yr_str:>10s}  {title_disp}")
            print(f"\n  Found: {len(no_shift)} aggregate events without shifts")
            print(f"\n  To generate:")
            print(f"    python scripts/create_shift.py "
                  f"--generate-from-event <EVENT_ID> --type aggregate")
        else:
            print("  None found.")

    finally:
        db.close()


# ─── Main ───

def main():
    parser = argparse.ArgumentParser(
        description="Create or import History Shift narratives (YAML workflow)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from topic
  python scripts/create_shift.py --generate "그리스-페르시아 전쟁" --type aggregate

  # Generate from existing aggregate event
  python scripts/create_shift.py --generate-from-event 19595 --type aggregate

  # Generate from person
  python scripts/create_shift.py --generate-from-person 5432 --type person_story

  # Import YAML to DB
  python scripts/create_shift.py --import scripts/output/shift-greco-persian-wars.yaml

  # Import with English translation
  python scripts/create_shift.py --import scripts/output/shift-greco-persian-wars.yaml --translate

  # Translate existing YAML
  python scripts/create_shift.py --translate-file scripts/output/shift-greco-persian-wars.yaml

  # List existing shifts
  python scripts/create_shift.py --list

  # Discover shifts needing enhancement
  python scripts/create_shift.py --batch-discover --min-importance 4
        """,
    )

    # Generation modes (mutually exclusive)
    gen_group = parser.add_mutually_exclusive_group()
    gen_group.add_argument("--generate", type=str, metavar="TOPIC",
                           help="Generate shift YAML from topic via GPT")
    gen_group.add_argument("--generate-from-event", type=int, metavar="EVENT_ID",
                           help="Generate from existing aggregate event ID")
    gen_group.add_argument("--generate-from-person", type=int, metavar="PERSON_ID",
                           help="Generate from person ID (person_story)")

    # Enhance existing shift
    parser.add_argument("--enhance", type=int, metavar="SHIFT_ID",
                        help="Enhance existing shift with narrative + widgets via GPT")
    parser.add_argument("--page-range", type=str, metavar="START-END",
                        help="Page range for --enhance (e.g., 0-19)")

    # Import
    parser.add_argument("--import", dest="import_file", type=str, metavar="FILE",
                        help="Import YAML file into DB")

    # Translate standalone
    parser.add_argument("--translate-file", type=str, metavar="FILE",
                        help="Translate empty English fields in YAML file")

    # Batch discovery
    parser.add_argument("--batch-discover", action="store_true",
                        help="List shifts needing enhancement + aggregate events without shifts")
    parser.add_argument("--min-importance", type=int, default=3,
                        help="Minimum globe_importance for batch discovery (default: 3)")
    parser.add_argument("--limit", type=int, default=50,
                        help="Max results per category in batch discovery (default: 50)")

    # Options
    parser.add_argument("--translate", action="store_true",
                        help="Auto-translate empty English fields (with --import)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing to DB")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing slug")
    parser.add_argument("--type", type=str,
                        choices=["aggregate", "person_story", "place_story",
                                 "era_story", "causal_chain"],
                        help="Chain type")
    parser.add_argument("--model", type=str,
                        help="OpenAI model for outline (default: gpt-5.2)")
    parser.add_argument("--max-pages", type=int, default=20,
                        help="Max pages per shift (default: 20)")
    parser.add_argument("--list", action="store_true",
                        help="List all shifts in DB")

    args = parser.parse_args()

    _check_yaml()

    if args.generate or args.generate_from_event or args.generate_from_person:
        cmd_generate(args)
    elif args.enhance:
        cmd_enhance(args)
    elif args.import_file:
        cmd_import(args)
    elif args.translate_file:
        cmd_translate(args)
    elif args.batch_discover:
        cmd_batch_discover(args)
    elif args.list:
        cmd_list(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
