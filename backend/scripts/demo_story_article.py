"""
Demo: Story-flow based singularity/lostbelt article generation.
Phase 2 new structure — follows the FGO story progression,
weaving in historical context as characters appear.

Usage:
    cd backend
    PYTHONPATH=. PYTHONIOENCODING=utf-8 python scripts/demo_story_article.py
"""
import json
import os
import re
import sys
import time
from pathlib import Path

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

from scripts.fgo_data_utils import (
    load_story_summary, get_servant_bond_context,
    SINGULARITY_META,
)

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# === Pricing ===
PRICING = {
    "gpt-5.2-chat-latest": {"input": 1.75, "output": 14.00},
}

def estimate_cost(usage, model="gpt-5.2-chat-latest"):
    p = PRICING.get(model, PRICING["gpt-5.2-chat-latest"])
    in_cost = usage.prompt_tokens * p["input"] / 1_000_000
    out_cost = usage.completion_tokens * p["output"] / 1_000_000
    return in_cost + out_cost


# === Shift matching (simple keyword search) ===
def find_matching_shifts(keywords: list[str]) -> list[dict]:
    """Query DB for existing shifts matching keywords."""
    from sqlalchemy import create_engine, text as sql_text
    from app.config import get_settings

    settings = get_settings()
    engine = create_engine(settings.database_url)
    conditions = " OR ".join([f"title ILIKE '%{kw}%'" for kw in keywords])
    query = f"""
        SELECT slug, title, chain_type, year_start, year_end, globe_importance
        FROM historical_chains
        WHERE {conditions}
        ORDER BY globe_importance DESC
        LIMIT 20
    """
    with engine.connect() as conn:
        rows = conn.execute(sql_text(query)).fetchall()
    return [
        {"slug": r[0], "title": r[1], "chain_type": r[2],
         "year_start": r[3], "year_end": r[4], "importance": r[5]}
        for r in rows
    ]


# === GPT Prompts ===

STORY_OUTLINE_SYSTEM = """\
You are a senior content architect for CHALDEAS, a 3D globe history system that bridges
Fate/Grand Order (FGO) and real history.

You are designing a STORY-FLOW article for an FGO chapter. Unlike traditional static articles,
this follows the FGO story progression, weaving in real historical context as characters appear.

STRUCTURE (output JSON):
{
  "slug": "singularity-7",
  "title": "Compelling Title — with Subtitle",
  "subtitle": "One-line subtitle",
  "description": "2-3 sentence description",
  "sections": [
    {
      "section_type": "historical_setting",
      "title": "The Real [Place] — [Compelling hook]",
      "key_points": ["Historical fact 1", "Fact 2", ...],
      "hook": "Surprising historical fact",
      "target_length": "600-800 words"
    },
    {
      "section_type": "story_part",
      "part_number": 1,
      "title": "Story part title from source data",
      "key_points": ["Story beat 1", "Character intro + history", ...],
      "characters_to_introduce": ["Character 1 — their real history angle", ...],
      "hook": "Surprising connection between FGO and history",
      "target_length": "800-1000 words"
    },
    ...more story_parts...,
    {
      "section_type": "themes",
      "title": "What This Story Is Really About",
      "key_points": ["Theme 1", "FGO vs history comparison", ...],
      "hook": "The deeper meaning",
      "target_length": "500-700 words"
    }
  ],
  "related_servants": [{"name": "Name", "class": "Class", "rarity": 5}]
}

RULES:
- historical_setting: ONE section. The real history of this era/place.
- story_parts: Follow the provided part divisions. Each part introduces characters
  with their real historical/mythological background INLINE — not in a separate section.
- themes: ONE final section. The big picture, FGO vs history comparison, what it all means.
- Characters' real history should feel natural in the story flow, not like a Wikipedia insert.
- Section titles must be specific and compelling.
"""

STORY_OUTLINE_USER = """\
Chapter: {chapter_title}
Era: {era} | Year: {year} | Location: {location}

=== STORY SUMMARY (OVERALL) ===
{overall_summary}

=== STORY PARTS ===
{parts_summary}

=== KEY CHARACTERS ===
{characters_summary}

=== THEMES ===
{themes}

=== EXISTING HISTORY SHIFTS (can be linked, don't need to explain in detail) ===
{existing_shifts}

Design the story-flow article outline. The article should read like a guided tour
through the FGO story, with historical context emerging naturally as the story unfolds.
Output ONLY valid JSON.
"""

STORY_SECTION_SYSTEM = """\
You are a history-and-FGO content writer for CHALDEAS, a 3D globe history system.

STYLE:
- Engaging narrative that follows the FGO story while weaving in real history.
- When a character appears, naturally introduce their historical/mythological background.
  Don't make it feel like a separate "history box" — integrate it into the story flow.
- Reference specific FGO scenes, dialogue, and character moments from the story summary.
- Use bond text quotes where they illuminate the character.
- Compare FGO's creative choices against real history inline — "In the Epic, Gilgamesh...
  but FGO's version..." — not as a separate comparison block.
- Tone: like a knowledgeable friend narrating the story while pointing out real history.
  Not dry, not meme casual. Think BBC documentary host who plays FGO.
- Break into readable paragraphs. Minimum target length.

Output ONLY the English content text. No titles, no YAML, no markdown headers.
"""

STORY_SETTING_USER = """\
Article: {article_title}
Section: {section_title} (historical_setting)
Key points: {key_points}
Hook: {hook}
Target length: {target_length}

Era: {era} | Year: {year} | Location: {location}

This section sets the stage: the REAL history of this time and place,
before the FGO story begins. What was this era actually like?
What would a visitor to this place and time have seen?

Write this section. Be vivid, specific, and grounded in history.
"""

STORY_PART_USER = """\
Article: {article_title}
Section: {section_title} (story_part {part_number})
Key points: {key_points}
Characters to introduce: {characters_to_introduce}
Hook: {hook}
Target length: {target_length}

=== FGO STORY SUMMARY FOR THIS PART ===
{part_summary}

=== KEY CHARACTERS IN THIS PART ===
{part_characters}

=== BOND TEXTS (for characters with historical backgrounds) ===
{bond_texts}

=== EXISTING HISTORY SHIFTS THAT CAN BE REFERENCED ===
{related_shifts}

Write this section. Follow the story flow, and when characters appear,
naturally weave in their real historical/mythological background.
Use bond text quotes where they illuminate the character.
Don't list history facts — let them emerge from the story.
"""

STORY_THEMES_USER = """\
Article: {article_title}
Section: {section_title} (themes)
Key points: {key_points}
Hook: {hook}
Target length: {target_length}

=== OVERALL THEMES FROM THE STORY ===
{themes}

=== WHAT FGO TAKES FROM REAL HISTORY ===
{history_connections}

=== ALL RELATED HISTORY SHIFTS ===
{all_shifts}

Write the concluding section. Tie together:
1. The major themes of this FGO chapter
2. What FGO gets right about the real history/mythology
3. What FGO reimagines or invents (and why it works/doesn't)
4. Why this era/place matters in real history
5. Pointers to related history shifts for deeper exploration
"""


def generate_babylonia():
    """Generate Babylonia article with story-flow structure."""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = "gpt-5.2-chat-latest"
    total_cost = 0.0
    t_start = time.time()

    meta = SINGULARITY_META["VII"]
    slug = meta["slug"]
    print(f"\n{'='*60}")
    print(f"  Generating: Singularity VII — Babylonia")
    print(f"  Model: {model}")
    print(f"{'='*60}\n")

    # === Load data ===
    print("[1/6] Loading story summary...")
    summary = load_story_summary("babylonia")

    # Load parts
    parts_dir = Path(r"E:\chaldeas_data\processed\fgo\summaries\by_chapter\babylonia")
    parts = []
    for i in range(1, 4):
        part_file = parts_dir / f"part_{i}.json"
        if part_file.exists():
            parts.append(json.loads(part_file.read_text(encoding='utf-8')))
    print(f"   Loaded {len(parts)} story parts")

    # Bond texts for key characters
    print("[2/6] Loading bond texts...")
    bond_chars = {
        "Gilgamesh": 200200,
        "Enkidu": 200600,
    }
    bond_context = ""
    for name, atlas_id in bond_chars.items():
        try:
            ctx = get_servant_bond_context(atlas_id)
            bond_context += f"\n--- {name} (Atlas ID: {atlas_id}) ---\n{ctx}\n"
        except Exception as e:
            print(f"   Warning: Could not load bond text for {name}: {e}")

    # Find matching shifts
    print("[3/6] Finding matching shifts...")
    keywords = ["mesopotamia", "babylon", "uruk", "sumer", "assyri",
                 "persian", "crusade", "greek"]
    shifts = find_matching_shifts(keywords)
    shifts_text = "\n".join([
        f"- {s['slug']}: {s['title']} ({s['year_start']} to {s['year_end']}, importance {s['importance']})"
        for s in shifts[:15]
    ])
    print(f"   Found {len(shifts)} matching shifts")

    # Prepare parts summary
    parts_summary = ""
    characters_summary = ""
    themes_list = []
    for p in parts:
        parts_summary += f"\n=== Part {p['part']}: {p['title_en']} ===\n"
        parts_summary += f"Quests: {p['quests_range']}\n"
        parts_summary += f"Summary: {p['summary'][:1500]}...\n"
        parts_summary += f"Key plot points:\n"
        for kp in p['key_plot_points']:
            parts_summary += f"  - {kp}\n"

        for ch in p['key_characters']:
            characters_summary += f"- {ch['name']}: {ch['role']}\n"

        themes_list.extend(p.get('themes', []))

    # === Step 1: Outline ===
    print("[4/6] Generating outline...")
    outline_resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": STORY_OUTLINE_SYSTEM},
            {"role": "user", "content": STORY_OUTLINE_USER.format(
                chapter_title=f"Singularity VII: Babylonia — {meta['title']}",
                era=meta["era"],
                year=meta["year"],
                location=meta["location"],
                overall_summary=summary.get("summary", "")[:3000],
                parts_summary=parts_summary[:4000],
                characters_summary=characters_summary[:2000],
                themes="\n".join(f"- {t}" for t in set(themes_list)),
                existing_shifts=shifts_text,
            )}
        ],
        max_completion_tokens=4096,
    )
    cost = estimate_cost(outline_resp.usage, model)
    total_cost += cost
    print(f"   Outline: {outline_resp.usage.completion_tokens} tokens, ${cost:.3f}")

    # Parse outline
    outline_text = outline_resp.choices[0].message.content
    outline_match = re.search(r'\{[\s\S]*\}', outline_text)
    if not outline_match:
        print("ERROR: Could not parse outline JSON")
        print(outline_text[:500])
        return
    outline = json.loads(outline_match.group())

    print(f"   Title: {outline.get('title', 'N/A')}")
    print(f"   Sections: {len(outline.get('sections', []))}")
    for s in outline.get('sections', []):
        print(f"     [{s.get('section_type', '?')}] {s.get('title', 'N/A')}")

    # === Step 2: Generate each section ===
    print("\n[5/6] Generating sections...")
    sections_output = []

    for i, sec in enumerate(outline['sections']):
        sec_type = sec.get('section_type', 'story_part')
        sec_title = sec.get('title', f'Section {i+1}')
        print(f"\n   --- Section {i+1}/{len(outline['sections'])}: {sec_title} ---")

        if sec_type == 'historical_setting':
            user_msg = STORY_SETTING_USER.format(
                article_title=outline['title'],
                section_title=sec_title,
                key_points=json.dumps(sec.get('key_points', []), ensure_ascii=False),
                hook=sec.get('hook', ''),
                target_length=sec.get('target_length', '600-800 words'),
                era=meta["era"],
                year=meta["year"],
                location=meta["location"],
            )
        elif sec_type == 'story_part':
            part_num = sec.get('part_number', 1)
            part_data = parts[part_num - 1] if part_num <= len(parts) else parts[-1]

            user_msg = STORY_PART_USER.format(
                article_title=outline['title'],
                section_title=sec_title,
                part_number=part_num,
                key_points=json.dumps(sec.get('key_points', []), ensure_ascii=False),
                characters_to_introduce=json.dumps(
                    sec.get('characters_to_introduce', []), ensure_ascii=False),
                hook=sec.get('hook', ''),
                target_length=sec.get('target_length', '800-1000 words'),
                part_summary=part_data['summary'][:3000],
                part_characters="\n".join(
                    f"- {c['name']}: {c['role']}"
                    for c in part_data.get('key_characters', [])
                ),
                bond_texts=bond_context[:3000],
                related_shifts=shifts_text,
            )
        elif sec_type == 'themes':
            user_msg = STORY_THEMES_USER.format(
                article_title=outline['title'],
                section_title=sec_title,
                key_points=json.dumps(sec.get('key_points', []), ensure_ascii=False),
                hook=sec.get('hook', ''),
                target_length=sec.get('target_length', '500-700 words'),
                themes="\n".join(f"- {t}" for t in set(themes_list)),
                history_connections="Gilgamesh Epic, Mesopotamian mythology, Enuma Elish creation myth",
                all_shifts=shifts_text,
            )
        else:
            continue

        sec_resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": STORY_SECTION_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            max_completion_tokens=4096,
        )
        cost = estimate_cost(sec_resp.usage, model)
        total_cost += cost
        content = sec_resp.choices[0].message.content.strip()
        word_count = len(content.split())
        print(f"   {word_count} words, {sec_resp.usage.completion_tokens} tokens, ${cost:.3f}")

        sections_output.append({
            "title": sec_title,
            "section_type": sec_type,
            "part_number": sec.get('part_number'),
            "content": content,
        })

    # === Step 3: Assemble YAML ===
    print("\n[6/6] Assembling YAML...")
    import yaml

    article = {
        "slug": outline.get("slug", "singularity-7"),
        "item_type": "singularity",
        "number": "VII",
        "title": outline.get("title", ""),
        "subtitle": outline.get("subtitle", ""),
        "description": outline.get("description", ""),
        "year": meta["year"],
        "location": meta["location"],
        "era": meta["era"],
        "location_coords": {"lat": 31.32, "lng": 45.64},
        "sections": [],
        "related_servants": outline.get("related_servants", []),
        "related_shifts": [
            {"slug": s["slug"], "title": s["title"]}
            for s in shifts[:10]
        ],
    }

    for sec in sections_output:
        entry = {
            "title": sec["title"],
            "section_type": sec["section_type"],
            "content": sec["content"],
        }
        if sec.get("part_number"):
            entry["part_number"] = sec["part_number"]
        article["sections"].append(entry)

    out_path = OUTPUT_DIR / "singularity-7-babylonia.yaml"
    out_path.write_text(
        yaml.dump(article, allow_unicode=True, default_flow_style=False,
                  sort_keys=False, width=120),
        encoding='utf-8'
    )

    elapsed = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"  Done! {len(sections_output)} sections generated")
    print(f"  Total cost: ${total_cost:.3f}")
    print(f"  Time: {elapsed:.0f}s")
    print(f"  Output: {out_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    generate_babylonia()
