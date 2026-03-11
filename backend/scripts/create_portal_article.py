"""
Create or import portal articles (YAML-based workflow).

Two modes:
  --generate "topic"   GPT generates a YAML draft → human reviews → --import
  --import file.yaml   Insert YAML into portal_items (+ optional collection link)

Options:
  --translate          Auto-translate empty en/ja fields (with --import)
  --dry-run            Preview without writing to DB
  --type TYPE          item_type override (history/essay/literature/music)
  --theme THEME        Theme hint for GPT generation
  --collection SLUG    Override collection slug for --import
  --list               List all portal_items in DB

Usage:
    cd backend

    # Auto-generate from topic
    python scripts/create_portal_article.py --generate "마라톤 전투의 팔랑크스" --type history
    python scripts/create_portal_article.py --generate "소크라테스의 독배" --type essay --theme ideas

    # Import YAML to DB
    python scripts/create_portal_article.py --import scripts/output/warfare-phalanx.yaml
    python scripts/create_portal_article.py --import scripts/output/warfare-phalanx.yaml --translate
    python scripts/create_portal_article.py --import scripts/output/warfare-phalanx.yaml --dry-run

    # List existing
    python scripts/create_portal_article.py --list
"""
import argparse
import json
import os
import re
import sys
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

TEMPLATE_PATH = Path(__file__).parent / "templates" / "article_template.yaml"
OUTPUT_DIR = Path(__file__).parent / "output"

from scripts.paper_utils import load_paper_index, get_papers_for_events, format_papers_for_prompt, format_papers_as_sources
from scripts.fgo_data_utils import (
    load_servant_data, get_servant_bond_context, load_confirmed_links,
    get_person_context_from_db, get_events_for_person,
    SINGULARITY_META, LOSTBELT_META,
    get_chapter_summary_context, load_story_summary,
)


def _get_db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.config import get_settings

    settings = get_settings()
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    return Session()


# ─── YAML handling (no external dependency) ───

def _parse_yaml(text: str) -> dict:
    """Minimal YAML parser for our article template format.

    Handles: scalars, quoted strings, multiline |, lists of dicts, simple lists.
    NOT a full YAML parser — tailored to article_template.yaml structure.
    """
    import yaml
    return yaml.safe_load(text)


def _dump_yaml(data: dict) -> str:
    """Dump article dict to readable YAML."""
    import yaml
    return yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False, width=120)


def _check_yaml():
    """Check if PyYAML is available."""
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


# ─── Step 1: Outline (reasoning model — structure + key points) ───

OUTLINE_SYSTEM_PROMPT = """\
You are a senior history content architect for CHALDEAS, a 3D globe history system.
Your job: design the OUTLINE for a detailed, engaging article.

Target audience: curious high school students.
Tone reference: best Wikipedia feature articles + BBC documentaries.

OUTPUT: JSON outline with this structure:
{
  "slug": "kebab-case-english",
  "title": "Compelling English Title — with Subtitle",
  "subtitle": "One-line subtitle",
  "description": "2-3 sentence description",
  "era": "English era name",
  "year": -490,
  "location": "English location",
  "sections": [
    {
      "title": "Compelling section title (question-form or dramatic)",
      "key_points": ["Point 1 that must be covered", "Point 2", ...],
      "hook": "The core surprising fact or question for this section",
      "target_length": "400-600 words"
    },
    ...
  ],
  "sources": ["Source 1", "Source 2"],
  "related_servants": [],
  "collection": "collection-slug"
}

RULES:
- 6~8 sections. Each section title must be compelling, NOT generic.
- key_points: 3~5 specific points per section (facts, anecdotes, names, numbers).
- hook: each section needs one "wait, really?" moment.
- Think about narrative ARC: Why? → Who? → How? → Turning point → So what? → Today?
- Section titles: "Background" (X) → "Why Did Darius Cross the Sea?" (O)
"""

OUTLINE_USER_TEMPLATE = """\
Topic: {topic}
Type: {item_type}
Theme: {theme}

=== ACADEMIC SOURCES ===
{academic_papers}

Use these sources to inform your outline.
Include the most relevant ones in the "sources" field.

Design a detailed article outline. Think carefully about:
1. What makes this topic fascinating? What's the "wait, really?" hook?
2. What's the narrative arc? (cause → people → events → turning point → legacy)
3. What specific anecdotes, quotes, numbers should be included?
4. How do sections connect? Each should be independently interesting but flow naturally.

Output ONLY valid JSON. No markdown code blocks.
"""

# ─── Step 2: Section writing (chat model — rich content per section) ───

SECTION_SYSTEM_PROMPT = """\
You are a history content writer for CHALDEAS, a 3D globe history system.
You write in English for curious high school students.

STYLE — well-written popular history (engaging and vivid):
- Rich and detailed. Minimum 400 words, aim for 500-600 words.
- Use specific numbers, anecdotes, and quotes for vividness.
- Always explain cause-and-effect and "why?" first.
- Focus on people's choices and motivations. "What would you have done?"
- Weave in surprising facts and connections naturally.
- Sentences should be concise and rhythmic. Avoid long run-on paragraphs.
- Tone: like a smart friend explaining — not textbook dry, not internet meme casual.
- Break into paragraphs for readability.

Output ONLY the English content text. No title, no YAML, no markdown — just the content.
"""

SECTION_USER_TEMPLATE = """\
Article: {article_title}
Section title: {section_title}
Key points to cover: {key_points}
Hook/surprising fact: {hook}
Target length: {target_length}

Academic sources for reference:
{academic_papers}

Ground your writing in these research findings where relevant.
Write this section in English. Be detailed, specific, and engaging.
Minimum 400 words. Aim for 500-600.
"""

TRANSLATE_SYSTEM_PROMPT = """\
You are a professional translator for a history education platform.
Translate the given Korean text to {target_lang}.
Maintain the same tone: documentary-style, engaging, educational.
Keep proper nouns in their conventional {target_lang} forms.
Output ONLY the translated text, nothing else.
"""


# ─── Servant Column Prompts ───

SERVANT_OUTLINE_SYSTEM = """\
You are a senior content architect for CHALDEAS, a 3D globe history system that bridges
Fate/Grand Order (FGO) and real history. You design article outlines for "Servant Columns"
— deep essays that compare FGO's Servants with their real historical/mythological origins.

Target audience: FGO players curious about real history, and history enthusiasts curious about FGO.
Tone: BBC documentary meets expert FGO analysis. Engaging, specific, surprising.

OUTPUT: JSON with this structure:
{
  "slug": "servant-name-kebab",
  "title": "Compelling English Title",
  "subtitle": "One-line subtitle",
  "description": "2-3 sentence description",
  "era": "Historical era",
  "year": -490,
  "location": "Historical location",
  "sections": [
    {
      "title": "Section title (compelling, not generic)",
      "key_points": ["Point 1", "Point 2", ...],
      "hook": "The core surprising fact or question",
      "target_length": "500-700 words"
    }
  ],
  "sources": ["Source 1", ...],
  "related_servants": [{"name": "Servant Name", "class": "Saber", "rarity": 5}],
  "collection": "fgo-servant-columns"
}

REQUIRED 5 SECTIONS:
1. "Who Was the Real [Person]?" — Historical/mythological background (500-700 words)
2. "FGO's [Servant] — [Epithet]" — FGO interpretation, bond text analysis (400-600 words)
3. "History vs. Fate — What Changed?" — FGO ↔ history comparison (400-600 words)
4. "[Era/Event Context]" — Historical era backdrop, lasting impact (400-600 words)
5. "Connections — The Servant Network" — Related servants/persons network (300-400 words)

RULES:
- Each section title must be specific to THIS servant — not generic.
- Use bond text details to highlight FGO-specific characterization.
- Compare specific historical facts vs. FGO's creative liberties.
- Include surprising connections between history and FGO.
- related_servants: list other FGO servants related to this person.
"""

SERVANT_SECTION_SYSTEM = """\
You are a history-and-FGO content writer for CHALDEAS, a 3D globe history system.
You write in English for FGO players and history enthusiasts.

STYLE — expert FGO analysis meets popular history:
- Rich and detailed. Minimum specified target length.
- Reference specific FGO bond texts, skills, Noble Phantasms with quotes where relevant.
- Compare FGO characterization against historical record with specific examples.
- Use anecdotes, quotes, and numbers from history for vividness.
- Explain cause-and-effect. "Why did this person matter?"
- Tone: like a knowledgeable friend who plays FGO AND reads history — not dry, not meme casual.
- Break into paragraphs for readability.

Output ONLY the English content text. No title, no YAML, no markdown headers.
"""

SERVANT_SECTION_USER = """\
Servant: {servant_name} ({class_name}, ★{rarity})
Article: {article_title}
Section: {section_title}
Key points: {key_points}
Hook: {hook}
Target length: {target_length}

=== FGO BOND TEXT ===
{bond_context}

=== HISTORICAL PERSON ===
{person_context}

=== ACADEMIC SOURCES ===
{academic_papers}

Write this section. Be detailed, specific, and engaging.
Ground FGO analysis in the bond texts. Ground history in the sources.
"""

# ─── Singularity/Lostbelt Prompts ───

CHAPTER_OUTLINE_SYSTEM = """\
You are a senior content architect for CHALDEAS, a 3D globe history system that bridges
Fate/Grand Order (FGO) and real history. You design outlines for deep essays about
FGO's Singularities and Lostbelts — exploring both the FGO story AND the real history behind them.

Target audience: FGO players curious about real history.
Tone: BBC documentary meets expert FGO analysis.

OUTPUT: JSON with this structure:
{
  "slug": "chapter-slug",
  "title": "Compelling English Title",
  "subtitle": "One-line subtitle",
  "description": "2-3 sentence description",
  "era": "Historical era",
  "year": -490,
  "location": "Historical location",
  "sections": [
    {
      "title": "Section title",
      "key_points": ["Point 1", ...],
      "hook": "Surprising fact",
      "target_length": "500-700 words"
    }
  ],
  "sources": ["Source 1", ...],
  "related_servants": [{"name": "Servant", "class": "Class", "rarity": 5}],
  "collection": "fgo-singularities"
}

REQUIRED 5-7 SECTIONS (adapt to chapter):
1. "The Real [Era/Place]" — Actual historical background (500-700 words)
2. "[Key Servants] — History and Mythology" — Historical/mythological origins of key characters (500-700 words)
3. "What FGO Gets Right (and Wrong)" — Game vs history comparison (400-600 words)
4. "The [Chapter] Story" — FGO story summary with key moments (500-700 words)
5. "Explore the Real History" — Related history shifts and globe features (300-400 words)
Optional:
6. "Behind the Scenes — Design Choices" — Why Nasu/FGO made specific creative decisions
7. "Legacy — [How This Era Changed the World]" — Lasting historical impact

RULES:
- Section titles must be specific to THIS chapter.
- FGO story sections should reference actual dialogue and key scenes.
- History sections must provide real scholarly context.
- related_servants: list ALL major servants from this chapter.
"""

CHAPTER_SECTION_SYSTEM = """\
You are a history-and-FGO content writer for CHALDEAS, a 3D globe history system.
You write in English for FGO players and history enthusiasts.

STYLE — expert FGO analysis meets popular history:
- Rich and detailed. Minimum specified target length.
- For FGO story sections: reference specific scenes, dialogue, and character moments.
- For history sections: use specific facts, anecdotes, dates, and scholarly references.
- Compare FGO's creative liberties against historical record where relevant.
- Tone: knowledgeable, engaging, not dry. Like a great history documentary host who also plays FGO.
- Break into paragraphs for readability.

Output ONLY the English content text.
"""

CHAPTER_SECTION_USER = """\
Chapter: {chapter_title}
Article: {article_title}
Section: {section_title}
Key points: {key_points}
Hook: {hook}
Target length: {target_length}

=== FGO STORY SUMMARY ===
{story_context}

=== KEY SERVANTS BOND TEXT ===
{bond_context}

=== HISTORICAL CONTEXT ===
{historical_context}

=== ACADEMIC SOURCES ===
{academic_papers}

Write this section. Be detailed, specific, and engaging.
"""


# ─── Servant Column Generator ───

def cmd_servant(args):
    """Generate servant column article via 2-step agent."""
    import time
    from sqlalchemy import text as sql_text

    client = _get_openai_client()
    outline_model = args.model or "gpt-5.2"
    section_model = "gpt-5.2-chat-latest"
    total_cost = 0.0
    t_start = time.time()

    # ─── Resolve servant ───
    servant_id = args.servant_id
    db = _get_db_session()

    # Get FGO servant from DB — try servant_id first, then atlas_id, then pk id
    row = None
    for col in ("servant_id", "atlas_id", "id"):
        row = db.execute(sql_text(f"""
            SELECT fs.servant_id, fs.name, fs.name_ko, fs.class_name, fs.rarity,
                   fs.person_id, fs.atlas_id, fs.noble_phantasm
            FROM fgo_servants fs
            WHERE fs.{col} = :sid
            LIMIT 1
        """), {"sid": servant_id}).fetchone()
        if row:
            break

    if not row:
        print(f"ERROR: Servant not found for ID {servant_id}")
        db.close()
        return

    servant_name = row[1]
    servant_name_ko = row[2]
    class_name = row[3]
    rarity = row[4]
    person_id = row[5]
    atlas_id = row[6] or row[0]
    noble_phantasm = row[7]

    print(f"=== Servant Column Generation ===")
    print(f"  Servant: {servant_name} ({class_name}, ★{rarity})")
    if servant_name_ko:
        print(f"  Korean: {servant_name_ko}")
    print(f"  Atlas ID: {atlas_id}, Person ID: {person_id}")

    # ─── Gather context ───
    # Bond text
    bond_context = get_servant_bond_context(atlas_id, lang="en", max_chars=4000)
    print(f"  Bond text: {'loaded' if 'Bond 1' in bond_context else 'not found'}")

    # Person context from DB
    person_context = "(No linked historical person)"
    event_ids = []
    if person_id:
        person_context = get_person_context_from_db(db, person_id, max_events=10)
        event_ids = get_events_for_person(db, person_id)
        print(f"  Person: loaded ({len(event_ids)} events)")

    # Academic papers
    paper_context = "(No academic papers available)"
    all_papers: list[dict] = []
    if event_ids:
        papers_by_event = get_papers_for_events(event_ids, max_per_event=2)
        all_papers = [p for ps in papers_by_event.values() for p in ps]
        if all_papers:
            paper_context = format_papers_for_prompt(all_papers, max_chars=3000)
            print(f"  Papers: {len(all_papers)} papers")

    # Related servants (from same person_id or FGO lore)
    related_servants = []
    if person_id:
        rel_rows = db.execute(sql_text("""
            SELECT name, class_name, rarity FROM fgo_servants
            WHERE person_id = :pid AND servant_id != :sid
            LIMIT 5
        """), {"pid": person_id, "sid": row[0]}).fetchall()
        related_servants = [{"name": r[0], "class": r[1], "rarity": r[2]} for r in rel_rows]

    db.close()

    # ─── Step 1: Outline ───
    print(f"\n--- Step 1: Outline (model={outline_model}) ---")
    t1 = time.time()

    outline_user = f"""\
Servant: {servant_name} ({class_name}, ★{rarity})
Noble Phantasm: {noble_phantasm or 'Unknown'}
Person ID link: {person_id or 'None (mythological/legendary)'}

=== BOND TEXT (ENGLISH) ===
{bond_context}

=== HISTORICAL/MYTHOLOGICAL PERSON ===
{person_context}

=== ACADEMIC SOURCES ===
{paper_context}

Design the article outline. Think about:
1. What makes this servant's history fascinating? What's the "wait, really?" hook?
2. How does FGO reinterpret the real person? What's brilliant vs. what's creative license?
3. What era/context is essential for understanding this person?
4. Which other servants are historically/mythologically connected?

Output ONLY valid JSON. No markdown code blocks.
"""

    resp1 = client.chat.completions.create(
        model=outline_model,
        messages=[
            {"role": "system", "content": SERVANT_OUTLINE_SYSTEM},
            {"role": "user", "content": outline_user},
        ],
        max_completion_tokens=16384,
    )

    outline_raw = resp1.choices[0].message.content.strip()
    u1 = resp1.usage
    cost1 = _estimate_cost(outline_model, u1)
    total_cost += cost1
    print(f"  Time: {time.time()-t1:.1f}s | Cost: ${cost1:.3f}")

    # Parse JSON
    import re as _re
    json_match = _re.search(r'\{[\s\S]*\}', outline_raw)
    if not json_match:
        print(f"  ERROR: No JSON in outline response")
        print(f"  Raw: {outline_raw[:500]}")
        return

    try:
        outline = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        print(f"  ERROR: Invalid JSON: {e}")
        return

    sections_plan = outline.get("sections", [])
    slug = outline.get("slug", f"servant-{servant_name.lower().replace(' ', '-')}")
    print(f"  Slug: {slug}")
    print(f"  Sections: {len(sections_plan)}")

    # Merge sources
    if all_papers:
        gpt_sources = outline.get("sources", [])
        paper_sources = format_papers_as_sources(all_papers[:10])
        outline["sources"] = gpt_sources + [s for s in paper_sources if s not in gpt_sources]

    # Merge related servants
    outline_servants = outline.get("related_servants", [])
    for rs in related_servants:
        if not any(s.get("name") == rs["name"] for s in outline_servants):
            outline_servants.append(rs)
    outline["related_servants"] = outline_servants

    # ─── Step 2: Write sections ───
    print(f"\n--- Step 2: Writing {len(sections_plan)} sections ---")
    written_sections = []

    for i, sec_plan in enumerate(sections_plan):
        sec_title = sec_plan.get("title", f"Section {i+1}")
        key_points = sec_plan.get("key_points", [])
        hook = sec_plan.get("hook", "")
        target_length = sec_plan.get("target_length", "500-600 words")

        print(f"  [{i+1}/{len(sections_plan)}] {sec_title}...", end="", flush=True)
        t2 = time.time()

        resp2 = client.chat.completions.create(
            model=section_model,
            messages=[
                {"role": "system", "content": SERVANT_SECTION_SYSTEM},
                {"role": "user", "content": SERVANT_SECTION_USER.format(
                    servant_name=servant_name,
                    class_name=class_name,
                    rarity=rarity,
                    article_title=outline.get("title", servant_name),
                    section_title=sec_title,
                    key_points="\n".join(f"- {p}" for p in key_points),
                    hook=hook,
                    target_length=target_length,
                    bond_context=bond_context,
                    person_context=person_context,
                    academic_papers=paper_context,
                )},
            ],
            max_completion_tokens=4096,
        )

        content = resp2.choices[0].message.content.strip()
        u2 = resp2.usage
        cost2 = _estimate_cost(section_model, u2)
        total_cost += cost2
        word_count = len(content.split())
        print(f" {word_count}w | {time.time()-t2:.1f}s | ${cost2:.3f}")

        written_sections.append({
            "title": sec_title,
            "title_ko": "",
            "content": content,
            "content_ko": "",
            "content_ja": "",
        })

    # ─── Assemble YAML ───
    article = {
        "slug": slug,
        "item_type": "servant_column",
        "title": outline.get("title", f"Servant Column: {servant_name}"),
        "title_ko": "",
        "title_ja": "",
        "subtitle": outline.get("subtitle", ""),
        "subtitle_ko": "",
        "subtitle_ja": "",
        "description": outline.get("description", ""),
        "description_ko": "",
        "description_ja": "",
        "era": outline.get("era", ""),
        "year": outline.get("year", 0),
        "location": outline.get("location", ""),
        "sections": written_sections,
        "historical_basis": "",
        "historical_basis_ko": "",
        "historical_basis_ja": "",
        "related_servants": outline.get("related_servants", []),
        "related_event_ids": outline.get("related_event_ids", []),
        "sources": outline.get("sources", []),
        "is_featured": False,
        "sort_order": 0,
        "collection": "fgo-servant-columns",
    }

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"{slug}.yaml"
    out_path.write_text(_dump_yaml(article), encoding='utf-8')

    total_elapsed = time.time() - t_start
    total_words = sum(len(s["content"].split()) for s in written_sections)

    print(f"\n=== Done ===")
    print(f"  Saved: {out_path}")
    print(f"  Total: {len(written_sections)} sections, {total_words} words")
    print(f"  Time: {total_elapsed:.1f}s | Cost: ~${total_cost:.3f}")

    if args.import_after:
        print(f"\n  Auto-importing to DB...")
        args.import_file = str(out_path)
        args.type = "servant_column"
        args.collection = "fgo-servant-columns"
        cmd_import(args)


# ─── Singularity/Lostbelt Generator ───

def cmd_chapter(args):
    """Generate singularity or lostbelt article via 2-step agent."""
    import time
    from sqlalchemy import text as sql_text

    client = _get_openai_client()
    outline_model = args.model or "gpt-5.2"
    section_model = "gpt-5.2-chat-latest"
    total_cost = 0.0
    t_start = time.time()

    # ─── Resolve chapter ───
    if args.singularity:
        chapter_key = args.singularity
        meta = SINGULARITY_META.get(chapter_key)
        if not meta:
            print(f"ERROR: Unknown singularity '{chapter_key}'")
            print(f"  Valid: {', '.join(SINGULARITY_META.keys())}")
            return
        chapter_type = "singularity"
        collection = "fgo-singularities"
    elif args.lostbelt:
        chapter_key = args.lostbelt
        meta = LOSTBELT_META.get(int(chapter_key))
        if not meta:
            print(f"ERROR: Unknown lostbelt '{chapter_key}'")
            print(f"  Valid: {', '.join(str(k) for k in LOSTBELT_META.keys())}")
            return
        chapter_type = "lostbelt"
        collection = "fgo-lostbelts"
    else:
        print("ERROR: Specify --singularity or --lostbelt")
        return

    slug = meta["slug"]
    title = meta["title"]
    story_slug = meta["story_slug"]

    print(f"=== {chapter_type.title()} Article Generation ===")
    print(f"  Chapter: {title}")
    print(f"  Story slug: {story_slug}")

    # ─── Gather context ───
    db = _get_db_session()

    # Story summary
    story_context = get_chapter_summary_context(story_slug, max_chars=6000)
    print(f"  Story summary: {'loaded' if 'Summary' not in story_context[:30] else 'not found'}")

    # Bond text for key servants in this chapter
    # Get servants linked to confirmed_links that appear in chapter
    confirmed = load_confirmed_links()
    bond_snippets = []

    # Get chapter servants from story data
    summary_data = load_story_summary(story_slug)
    key_character_names = set()
    if summary_data:
        parts = summary_data.get("parts") or []
        if parts:
            for part in parts:
                for char in part.get("key_characters", []):
                    key_character_names.add(char.get("name", ""))
        else:
            # Single-summary format (no parts, key_characters at top level)
            for char in summary_data.get("key_characters", []):
                key_character_names.add(char.get("name", ""))

    # Match servant names to get bond text
    servant_bonds_loaded = 0
    for link in confirmed[:50]:
        name = link.get("name_en", "")
        # Check if this servant appears in the chapter (fuzzy)
        base_name = name.split("(")[0].strip()
        if any(base_name.lower() in kc.lower() or kc.lower() in base_name.lower()
               for kc in key_character_names):
            atlas_id = link.get("servant_id")
            if atlas_id:
                bond = get_servant_bond_context(atlas_id, lang="en", max_chars=1500)
                if "Bond 1" in bond:
                    bond_snippets.append(bond)
                    servant_bonds_loaded += 1
                    if servant_bonds_loaded >= 5:
                        break

    bond_context = "\n\n".join(bond_snippets) if bond_snippets else "(No servant bond texts available)"
    print(f"  Servant bonds: {servant_bonds_loaded} loaded")

    # Historical context from DB events matching era/location
    historical_context = f"Era: {meta['era']}\nYear: {meta['year']}\nLocation: {meta['location']}"
    events = db.execute(sql_text("""
        SELECT id, title, date_start, importance FROM events
        WHERE date_start BETWEEN :y1 AND :y2
          AND importance >= 3
        ORDER BY importance DESC
        LIMIT 15
    """), {"y1": meta["year"] - 100, "y2": meta["year"] + 100}).fetchall()
    if events:
        event_ids = [e[0] for e in events]
        historical_context += f"\n\nRelated events ({len(events)}):"
        for ev in events:
            historical_context += f"\n  - {ev[1]} ({ev[2]})"
    else:
        event_ids = []

    print(f"  Historical events: {len(events)} in era range")

    # Academic papers
    paper_context = "(No academic papers available)"
    all_papers: list[dict] = []
    if event_ids:
        papers_by_event = get_papers_for_events(event_ids[:10], max_per_event=2)
        all_papers = [p for ps in papers_by_event.values() for p in ps]
        if all_papers:
            paper_context = format_papers_for_prompt(all_papers, max_chars=3000)
            print(f"  Papers: {len(all_papers)}")

    db.close()

    # ─── Step 1: Outline ───
    print(f"\n--- Step 1: Outline ---")
    t1 = time.time()

    outline_user = f"""\
Chapter: {title}
Type: {chapter_type}
Year: {meta['year']}
Location: {meta['location']}
Era: {meta['era']}

=== FGO STORY SUMMARY ===
{story_context}

=== KEY SERVANTS BOND TEXT ===
{bond_context}

=== HISTORICAL CONTEXT ===
{historical_context}

=== ACADEMIC SOURCES ===
{paper_context}

Design the article outline. Think about:
1. What real history underlies this {chapter_type}?
2. Which servants are historically fascinating and why?
3. What does FGO get right vs. creative license?
4. What would the "explore real history" section highlight?

Output ONLY valid JSON.
"""

    resp1 = client.chat.completions.create(
        model=outline_model,
        messages=[
            {"role": "system", "content": CHAPTER_OUTLINE_SYSTEM},
            {"role": "user", "content": outline_user},
        ],
        max_completion_tokens=16384,
    )

    outline_raw = resp1.choices[0].message.content.strip()
    u1 = resp1.usage
    cost1 = _estimate_cost(outline_model, u1)
    total_cost += cost1
    print(f"  Time: {time.time()-t1:.1f}s | Cost: ${cost1:.3f}")

    import re as _re
    json_match = _re.search(r'\{[\s\S]*\}', outline_raw)
    if not json_match:
        print(f"  ERROR: No JSON found")
        return

    try:
        outline = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        print(f"  ERROR: Invalid JSON: {e}")
        return

    sections_plan = outline.get("sections", [])
    outline_slug = outline.get("slug", slug)
    print(f"  Slug: {outline_slug}")
    print(f"  Sections: {len(sections_plan)}")

    if all_papers:
        gpt_sources = outline.get("sources", [])
        paper_sources = format_papers_as_sources(all_papers[:10])
        outline["sources"] = gpt_sources + [s for s in paper_sources if s not in gpt_sources]

    # ─── Step 2: Write sections ───
    print(f"\n--- Step 2: Writing {len(sections_plan)} sections ---")
    written_sections = []

    for i, sec_plan in enumerate(sections_plan):
        sec_title = sec_plan.get("title", f"Section {i+1}")
        key_points = sec_plan.get("key_points", [])
        hook = sec_plan.get("hook", "")
        target_length = sec_plan.get("target_length", "500-600 words")

        print(f"  [{i+1}/{len(sections_plan)}] {sec_title}...", end="", flush=True)
        t2 = time.time()

        resp2 = client.chat.completions.create(
            model=section_model,
            messages=[
                {"role": "system", "content": CHAPTER_SECTION_SYSTEM},
                {"role": "user", "content": CHAPTER_SECTION_USER.format(
                    chapter_title=title,
                    article_title=outline.get("title", title),
                    section_title=sec_title,
                    key_points="\n".join(f"- {p}" for p in key_points),
                    hook=hook,
                    target_length=target_length,
                    story_context=story_context,
                    bond_context=bond_context,
                    historical_context=historical_context,
                    academic_papers=paper_context,
                )},
            ],
            max_completion_tokens=4096,
        )

        content = resp2.choices[0].message.content.strip()
        u2 = resp2.usage
        cost2 = _estimate_cost(section_model, u2)
        total_cost += cost2
        word_count = len(content.split())
        print(f" {word_count}w | {time.time()-t2:.1f}s | ${cost2:.3f}")

        written_sections.append({
            "title": sec_title,
            "title_ko": "",
            "content": content,
            "content_ko": "",
            "content_ja": "",
        })

    # ─── Assemble YAML ───
    article = {
        "slug": outline_slug,
        "item_type": chapter_type,
        "title": outline.get("title", title),
        "title_ko": meta.get("title_ko", ""),
        "title_ja": "",
        "subtitle": outline.get("subtitle", ""),
        "subtitle_ko": "",
        "subtitle_ja": "",
        "description": outline.get("description", ""),
        "description_ko": "",
        "description_ja": "",
        "chapter": f"{'Singularity' if chapter_type == 'singularity' else 'Lostbelt No.'}{chapter_key}",
        "era": meta.get("era", outline.get("era", "")),
        "year": meta.get("year", outline.get("year", 0)),
        "location": meta.get("location", outline.get("location", "")),
        "sections": written_sections,
        "historical_basis": outline.get("historical_basis", ""),
        "historical_basis_ko": "",
        "historical_basis_ja": "",
        "related_servants": outline.get("related_servants", []),
        "related_event_ids": outline.get("related_event_ids", []),
        "sources": outline.get("sources", []),
        "is_featured": False,
        "sort_order": 0,
        "collection": collection,
    }

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"{outline_slug}.yaml"
    out_path.write_text(_dump_yaml(article), encoding='utf-8')

    total_elapsed = time.time() - t_start
    total_words = sum(len(s["content"].split()) for s in written_sections)

    print(f"\n=== Done ===")
    print(f"  Saved: {out_path}")
    print(f"  Total: {len(written_sections)} sections, {total_words} words")
    print(f"  Time: {total_elapsed:.1f}s | Cost: ~${total_cost:.3f}")

    if args.import_after:
        print(f"\n  Auto-importing to DB...")
        args.import_file = str(out_path)
        args.type = chapter_type
        args.collection = collection
        cmd_import(args)


def cmd_generate(args):
    """Generate article via 2-step agent: outline (reasoning) → sections (chat)."""
    import time
    client = _get_openai_client()

    topic = args.generate
    item_type = args.type or "history"
    theme = args.theme or ""
    outline_model = args.model or "gpt-5.2"
    section_model = "gpt-5.2-chat-latest"
    collection_hint = theme if theme else ""
    total_cost = 0.0
    t_start = time.time()

    print(f"=== Article Generation (2-step agent) ===")
    print(f"  Topic: {topic}")
    print(f"  Type: {item_type}, Theme: {theme}")
    print(f"  Step 1 model: {outline_model} (reasoning)")
    print(f"  Step 2 model: {section_model} (writing)")

    # ─── Gather academic papers via topic → events → papers ───
    from sqlalchemy import text as sql_text
    paper_context = "(No academic papers available for this topic)"
    all_papers: list[dict] = []
    try:
        db = _get_db_session()
        events = db.execute(sql_text("""
            SELECT id, title FROM events
            WHERE (title ILIKE :pat OR title_ko ILIKE :pat)
              AND importance >= 3
            ORDER BY importance DESC LIMIT 10
        """), {"pat": f"%{topic}%"}).fetchall()
        db.close()

        if events:
            event_ids = [e[0] for e in events]
            papers_by_event = get_papers_for_events(event_ids, max_per_event=2)
            all_papers = [p for ps in papers_by_event.values() for p in ps]
            if all_papers:
                paper_context = format_papers_for_prompt(all_papers, max_chars=4000)
                print(f"  Academic papers: {len(all_papers)} papers from {len(papers_by_event)} events")
            else:
                print(f"  Academic papers: none found for {len(events)} matching events")
        else:
            print(f"  Academic papers: no matching events in DB")
    except Exception as e:
        print(f"  Academic papers: lookup failed ({e})")

    # ─── Step 1: Generate outline via reasoning model ───
    print(f"\n--- Step 1: Outline ---")
    t1 = time.time()

    resp1 = client.chat.completions.create(
        model=outline_model,
        messages=[
            {"role": "system", "content": OUTLINE_SYSTEM_PROMPT},
            {"role": "user", "content": OUTLINE_USER_TEMPLATE.format(
                topic=topic, item_type=item_type, theme=theme,
                academic_papers=paper_context,
            )},
        ],
        max_completion_tokens=16384,
    )

    outline_raw = resp1.choices[0].message.content.strip()
    u1 = resp1.usage
    t1_elapsed = time.time() - t1
    cost1 = _estimate_cost(outline_model, u1)
    total_cost += cost1

    # Extract JSON from response
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

    slug = outline.get("slug", "article")
    sections_plan = outline.get("sections", [])
    print(f"  Slug: {slug}")
    print(f"  Title: {outline.get('title_ko', '?')}")
    print(f"  Sections: {len(sections_plan)}")
    print(f"  Time: {t1_elapsed:.1f}s | Tokens: {u1.prompt_tokens}in/{u1.completion_tokens}out | Cost: ${cost1:.3f}")

    # Merge academic paper sources into outline sources
    if all_papers:
        gpt_sources = outline.get("sources", [])
        paper_sources = format_papers_as_sources(all_papers[:10])
        outline["sources"] = gpt_sources + [s for s in paper_sources if s not in gpt_sources]
        print(f"  Sources: {len(gpt_sources)} GPT + {len(outline['sources']) - len(gpt_sources)} papers")

    # ─── Step 2: Write each section via chat model ───
    print(f"\n--- Step 2: Writing {len(sections_plan)} sections ---")
    written_sections = []

    for i, sec_plan in enumerate(sections_plan):
        sec_title = sec_plan.get("title", sec_plan.get("title_ko", f"Section {i+1}"))
        key_points = sec_plan.get("key_points", [])
        hook = sec_plan.get("hook", "")
        target_length = sec_plan.get("target_length", "400-600 words")

        print(f"  [{i+1}/{len(sections_plan)}] {sec_title}...", end="", flush=True)
        t2 = time.time()

        resp2 = client.chat.completions.create(
            model=section_model,
            messages=[
                {"role": "system", "content": SECTION_SYSTEM_PROMPT},
                {"role": "user", "content": SECTION_USER_TEMPLATE.format(
                    article_title=outline.get("title", topic),
                    section_title=sec_title,
                    key_points="\n".join(f"- {p}" for p in key_points),
                    hook=hook,
                    target_length=target_length,
                    academic_papers=paper_context,
                )},
            ],
            max_completion_tokens=4096,
        )

        content = resp2.choices[0].message.content.strip()
        u2 = resp2.usage
        t2_elapsed = time.time() - t2
        cost2 = _estimate_cost(section_model, u2)
        total_cost += cost2
        char_count = len(content)
        word_count = len(content.split())

        print(f" {word_count}w ({char_count}c) | {t2_elapsed:.1f}s | ${cost2:.3f}")

        written_sections.append({
            "title": sec_title,
            "title_ko": "",
            "content": content,
            "content_ko": "",
            "content_ja": "",
        })

    # ─── Assemble YAML ───
    article = {
        "slug": slug,
        "item_type": item_type,
        "title": outline.get("title", topic),
        "title_ko": "",
        "title_ja": "",
        "subtitle": outline.get("subtitle", ""),
        "subtitle_ko": "",
        "subtitle_ja": "",
        "description": outline.get("description", ""),
        "description_ko": "",
        "description_ja": "",
        "era": outline.get("era", ""),
        "year": outline.get("year", 0),
        "location": outline.get("location", ""),
        "sections": written_sections,
        "historical_basis": "",
        "historical_basis_ko": "",
        "historical_basis_ja": "",
        "related_servants": outline.get("related_servants", []),
        "related_event_ids": outline.get("related_event_ids", []),
        "sources": outline.get("sources", []),
        "is_featured": False,
        "sort_order": 0,
        "collection": outline.get("collection", collection_hint),
    }

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"{slug}.yaml"
    out_path.write_text(_dump_yaml(article), encoding='utf-8')

    total_elapsed = time.time() - t_start
    total_words = sum(len(s["content"].split()) for s in written_sections)

    print(f"\n=== Done ===")
    print(f"  Saved: {out_path}")
    print(f"  Total: {len(written_sections)} sections, {total_words} words")
    print(f"  Time: {total_elapsed:.1f}s")
    print(f"  Cost: ~${total_cost:.3f}")
    print(f"\n  Next steps:")
    print(f"    1. Review: {out_path}")
    print(f"    2. Import: python scripts/create_portal_article.py --import {out_path}")
    print(f"    3. With translation: add --translate flag")


def _estimate_cost(model: str, usage) -> float:
    """Estimate API cost in USD."""
    # Pricing per 1M tokens (input / output)
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


def _translate_text(client, text_ko: str, target_lang: str) -> str:
    """Translate Korean text to target language."""
    if not text_ko or not text_ko.strip():
        return ""

    lang_name = "English" if target_lang == "en" else "Japanese"
    resp = client.chat.completions.create(
        model="gpt-5.1-chat-latest",
        messages=[
            {"role": "system", "content": TRANSLATE_SYSTEM_PROMPT.format(target_lang=lang_name)},
            {"role": "user", "content": text_ko.strip()},
        ],
        max_completion_tokens=4096,
    )
    return resp.choices[0].message.content.strip()


def _translate_article(client, data: dict) -> dict:
    """Fill in empty en/ja fields by translating from ko."""
    fields_to_translate = [
        ("title_ko", "title", "title_ja"),
        ("subtitle_ko", "subtitle", "subtitle_ja"),
        ("description_ko", "description", "description_ja"),
        ("historical_basis_ko", "historical_basis", "historical_basis_ja"),
    ]

    translated = 0
    for ko_field, en_field, ja_field in fields_to_translate:
        ko_val = data.get(ko_field, "")
        if not ko_val:
            continue

        if not data.get(en_field):
            print(f"    Translating {ko_field} -> en...")
            data[en_field] = _translate_text(client, ko_val, "en")
            translated += 1

        if not data.get(ja_field):
            print(f"    Translating {ko_field} -> ja...")
            data[ja_field] = _translate_text(client, ko_val, "ja")
            translated += 1

    # Translate sections
    for i, sec in enumerate(data.get("sections", [])):
        ko_title = sec.get("title_ko", "")
        ko_content = sec.get("content_ko", "")

        if ko_title and not sec.get("title"):
            print(f"    Translating section[{i}].title -> en...")
            sec["title"] = _translate_text(client, ko_title, "en")
            translated += 1
        if ko_title and not sec.get("title_ja"):
            print(f"    Translating section[{i}].title -> ja...")
            sec["title_ja"] = _translate_text(client, ko_title, "ja")
            translated += 1

        if ko_content and not sec.get("content"):
            print(f"    Translating section[{i}].content -> en...")
            sec["content"] = _translate_text(client, ko_content, "en")
            translated += 1
        if ko_content and not sec.get("content_ja"):
            print(f"    Translating section[{i}].content -> ja...")
            sec["content_ja"] = _translate_text(client, ko_content, "ja")
            translated += 1

    print(f"    Translated {translated} fields")
    return data


def cmd_import(args):
    """Import YAML article into portal_items."""
    from sqlalchemy import text as sql_text
    from app.db.session import SessionLocal

    yaml_path = Path(args.import_file)
    if not yaml_path.exists():
        print(f"ERROR: File not found: {yaml_path}")
        sys.exit(1)

    data = _parse_yaml(yaml_path.read_text(encoding='utf-8'))
    slug = data.get("slug", "")
    if not slug:
        print("ERROR: 'slug' field is required")
        sys.exit(1)

    item_type = args.type or data.get("item_type", "history")

    # Ensure description exists (required field)
    desc = data.get("description") or data.get("description_ko") or ""
    desc_ko = data.get("description_ko") or data.get("description") or ""
    if not desc and not desc_ko:
        print("ERROR: description or description_ko required")
        sys.exit(1)

    # Title: fallback between languages
    title = data.get("title") or data.get("title_ko") or slug
    title_ko = data.get("title_ko") or data.get("title") or slug

    # Translate if requested
    if args.translate:
        print("  Auto-translating empty fields...")
        client = _get_openai_client()
        data = _translate_article(client, data)
        # Re-read after translation
        title = data.get("title") or title
        desc = data.get("description") or desc

    # Build record
    record = {
        "slug": slug,
        "item_type": item_type,
        "title": data.get("title") or title,
        "title_ko": data.get("title_ko") or title_ko,
        "title_ja": data.get("title_ja"),
        "subtitle": data.get("subtitle"),
        "subtitle_ko": data.get("subtitle_ko"),
        "subtitle_ja": data.get("subtitle_ja"),
        "description": data.get("description") or desc,
        "description_ko": data.get("description_ko") or desc_ko,
        "description_ja": data.get("description_ja"),
        "era": data.get("era"),
        "year": data.get("year"),
        "location": data.get("location"),
        "historical_basis": data.get("historical_basis"),
        "historical_basis_ko": data.get("historical_basis_ko"),
        "historical_basis_ja": data.get("historical_basis_ja"),
        "sections": json.dumps(data.get("sections", []), ensure_ascii=False),
        "related_servants": json.dumps(data.get("related_servants", []), ensure_ascii=False),
        "related_event_ids": json.dumps(data.get("related_event_ids", []), ensure_ascii=False),
        "sources": json.dumps(data.get("sources", []), ensure_ascii=False),
        "sort_order": data.get("sort_order", 0),
        "is_featured": data.get("is_featured", False),
    }

    collection_slug = args.collection or data.get("collection", "")

    print(f"\n  Article: {record['title_ko'] or record['title']}")
    print(f"  Slug: {slug}")
    print(f"  Type: {item_type}")
    print(f"  Year: {record['year']}")
    print(f"  Sections: {len(data.get('sections', []))}")
    if collection_slug:
        print(f"  Collection: {collection_slug}")

    if args.dry_run:
        print("\n  DRY RUN: Would insert into portal_items")
        return

    db = SessionLocal()
    try:
        # Check if slug exists
        existing = db.execute(
            sql_text("SELECT id FROM portal_items WHERE slug = :slug"),
            {"slug": slug}
        ).fetchone()

        if existing:
            # Update
            db.execute(sql_text("""
                UPDATE portal_items SET
                    item_type = :item_type,
                    title = :title, title_ko = :title_ko, title_ja = :title_ja,
                    subtitle = :subtitle, subtitle_ko = :subtitle_ko, subtitle_ja = :subtitle_ja,
                    description = :description, description_ko = :description_ko, description_ja = :description_ja,
                    era = :era, year = :year, location = :location,
                    historical_basis = :historical_basis,
                    historical_basis_ko = :historical_basis_ko,
                    historical_basis_ja = :historical_basis_ja,
                    sections = CAST(:sections AS jsonb),
                    related_servants = CAST(:related_servants AS jsonb),
                    related_event_ids = CAST(:related_event_ids AS jsonb),
                    sources = CAST(:sources AS jsonb),
                    sort_order = :sort_order, is_featured = :is_featured,
                    updated_at = NOW()
                WHERE slug = :slug
            """), record)
            print(f"\n  Updated existing portal_item (slug={slug})")
        else:
            # Insert
            db.execute(sql_text("""
                INSERT INTO portal_items (
                    slug, item_type, title, title_ko, title_ja,
                    subtitle, subtitle_ko, subtitle_ja,
                    description, description_ko, description_ja,
                    era, year, location,
                    historical_basis, historical_basis_ko, historical_basis_ja,
                    sections, related_servants, related_event_ids, sources,
                    sort_order, is_featured
                ) VALUES (
                    :slug, :item_type, :title, :title_ko, :title_ja,
                    :subtitle, :subtitle_ko, :subtitle_ja,
                    :description, :description_ko, :description_ja,
                    :era, :year, :location,
                    :historical_basis, :historical_basis_ko, :historical_basis_ja,
                    CAST(:sections AS jsonb), CAST(:related_servants AS jsonb),
                    CAST(:related_event_ids AS jsonb), CAST(:sources AS jsonb),
                    :sort_order, :is_featured
                )
            """), record)
            print(f"\n  Inserted new portal_item (slug={slug})")

        # Link to collection if specified
        if collection_slug:
            coll = db.execute(
                sql_text("SELECT id FROM collections WHERE slug = :slug"),
                {"slug": collection_slug}
            ).fetchone()

            if coll:
                item_id_row = db.execute(
                    sql_text("SELECT id FROM portal_items WHERE slug = :slug"),
                    {"slug": slug}
                ).fetchone()

                if item_id_row:
                    # Check if entry already exists
                    existing_entry = db.execute(sql_text("""
                        SELECT id FROM collection_entries
                        WHERE collection_id = :coll_id AND portal_item_id = :item_id
                    """), {"coll_id": coll[0], "item_id": item_id_row[0]}).fetchone()

                    if not existing_entry:
                        db.execute(sql_text("""
                            INSERT INTO collection_entries
                                (collection_id, entry_type, portal_item_id, sort_order)
                            VALUES (:coll_id, 'portal_item', :item_id, :sort_order)
                        """), {
                            "coll_id": coll[0],
                            "item_id": item_id_row[0],
                            "sort_order": record["sort_order"],
                        })
                        print(f"  Linked to collection: {collection_slug}")
                    else:
                        print(f"  Already in collection: {collection_slug}")
            else:
                print(f"  WARNING: Collection '{collection_slug}' not found — skipped linking")

        db.commit()
        print("  Done!")

    except Exception as e:
        db.rollback()
        print(f"\n  ERROR: {e}")
        raise
    finally:
        db.close()


def cmd_list(args):
    """List all portal_items."""
    from sqlalchemy import text as sql_text
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        rows = db.execute(sql_text("""
            SELECT slug, item_type, COALESCE(title_ko, title), year,
                   is_featured, jsonb_array_length(COALESCE(sections, '[]'::jsonb)) as sec_count
            FROM portal_items
            ORDER BY item_type, sort_order, slug
        """)).fetchall()

        current_type = None
        for row in rows:
            if row[1] != current_type:
                current_type = row[1]
                print(f"\n  [{current_type}]")
            feat = " *" if row[4] else ""
            print(f"    {row[0]:30s}  {row[3] or '':>6}  {row[5]} sections{feat}  {row[2]}")

        print(f"\n  Total: {len(rows)} items")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Create or import portal articles (YAML workflow)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate article from topic
  python scripts/create_portal_article.py --generate "마라톤 전투" --type history

  # Generate servant column
  python scripts/create_portal_article.py --servant-id 100800  # Gilgamesh
  python scripts/create_portal_article.py --servant-id 100800 --import-after

  # Generate singularity/lostbelt article
  python scripts/create_portal_article.py --singularity VII    # Babylonia
  python scripts/create_portal_article.py --lostbelt 3         # SIN
  python scripts/create_portal_article.py --singularity I --import-after

  # Import to DB
  python scripts/create_portal_article.py --import scripts/output/warfare-phalanx.yaml

  # Import with auto-translation
  python scripts/create_portal_article.py --import scripts/output/warfare-phalanx.yaml --translate

  # List existing items
  python scripts/create_portal_article.py --list
        """,
    )
    parser.add_argument("--generate", type=str, metavar="TOPIC",
                        help="Generate article YAML from topic via GPT")
    parser.add_argument("--servant-id", type=int, metavar="ID",
                        help="Generate servant column (FGO servant_id or atlas_id)")
    parser.add_argument("--singularity", type=str, metavar="NUM",
                        help="Generate singularity article (F, I, II, ..., VII, Final)")
    parser.add_argument("--lostbelt", type=str, metavar="NUM",
                        help="Generate lostbelt article (1-7)")
    parser.add_argument("--import", dest="import_file", type=str, metavar="FILE",
                        help="Import YAML file into portal_items")
    parser.add_argument("--import-after", action="store_true",
                        help="Auto-import to DB after generation")
    parser.add_argument("--translate", action="store_true",
                        help="Auto-translate empty en/ja fields (requires OpenAI)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing to DB")
    parser.add_argument("--type", type=str,
                        choices=["history", "essay", "literature", "music",
                                 "singularity", "lostbelt", "servant_column"],
                        help="Override item_type")
    parser.add_argument("--theme", type=str,
                        help="Theme hint for generation (e.g., warfare, ideas)")
    parser.add_argument("--collection", type=str,
                        help="Override collection slug for import")
    parser.add_argument("--model", type=str,
                        help="OpenAI model (default: gpt-5.2-chat-latest)")
    parser.add_argument("--force", action="store_true",
                        help="Force overwrite existing article")
    parser.add_argument("--list", action="store_true",
                        help="List all portal_items in DB")

    args = parser.parse_args()

    _check_yaml()

    if args.servant_id:
        cmd_servant(args)
    elif args.singularity or args.lostbelt:
        cmd_chapter(args)
    elif args.generate:
        cmd_generate(args)
    elif args.import_file:
        cmd_import(args)
    elif args.list:
        cmd_list(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
