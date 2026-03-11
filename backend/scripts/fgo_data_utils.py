"""
FGO Data Loading Utilities
==========================
Shared utilities for loading FGO data files from disk:
  - Bond text (JP + EN + KR) from Atlas Academy exports
  - Story summaries by chapter
  - Dialogue stats / top speakers
  - Confirmed person links
  - Story index (singularities + lostbelts)

Paths:
    E:/chaldeas_data/fgo_db/            — Atlas Academy structured data
    E:/chaldeas_data/processed/fgo/     — Processed outputs (summaries, links, dialogues)

Usage:
    from scripts.fgo_data_utils import (
        load_servant_data, load_story_summary, load_story_index,
        load_confirmed_links, get_servant_bond_context,
        get_chapter_servants, get_chapter_summary_context,
    )
"""

import json
from pathlib import Path
from typing import Optional

# ─── Base Paths ──────────────────────────────────────────

FGO_DB_DIR = Path(r"E:\chaldeas_data\fgo_db")
PROCESSED_DIR = Path(r"E:\chaldeas_data\processed\fgo")
SERVANTS_DIR = FGO_DB_DIR / "servants"
SERVANTS_BY_ID = SERVANTS_DIR / "by_id"
STORIES_DIR = FGO_DB_DIR / "stories"
SUMMARIES_DIR = PROCESSED_DIR / "summaries" / "by_chapter"
DIALOGUES_DIR = PROCESSED_DIR / "dialogues"
PERSON_LINKS_DIR = PROCESSED_DIR / "person_links"


# ─── JSON Helpers ────────────────────────────────────────

def _load_json(path: Path) -> Optional[dict | list]:
    """Load JSON file, return None if not found."""
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# ─── Servant Data ────────────────────────────────────────

def load_servant_index() -> list[dict]:
    """Load servants/index.json — all servants summary."""
    data = _load_json(SERVANTS_DIR / "index.json")
    return data if isinstance(data, list) else []


def load_servant_data(atlas_id: int) -> Optional[dict]:
    """Load individual servant data by Atlas Academy ID.

    Returns dict with: id, name, className, rarity, bond_text, profile, etc.
    """
    path = SERVANTS_BY_ID / f"{atlas_id}.json"
    return _load_json(path)


def get_servant_bond_context(atlas_id: int, lang: str = "en", max_chars: int = 3000) -> str:
    """Get formatted bond text for GPT context injection.

    Args:
        atlas_id: Atlas Academy servant ID
        lang: 'en', 'ja', or 'ko'
        max_chars: Max total characters

    Returns:
        Formatted bond text string for prompt injection.
    """
    data = load_servant_data(atlas_id)
    if not data:
        return "(No servant data found)"

    name = data.get("name", {}).get(lang, data.get("name", {}).get("en", "Unknown"))
    class_name = data.get("className", "Unknown")
    rarity = data.get("rarity", 0)

    lines = [f"=== {name} ({class_name}, ★{rarity}) ==="]

    # Profile
    profile = data.get("profile", {})
    if profile:
        stats = profile.get("stats", {})
        if stats:
            stat_line = ", ".join(f"{k}: {v}" for k, v in stats.items()
                                  if k not in ("policy", "personality", "deity"))
            lines.append(f"Stats: {stat_line}")

    # Bond text
    bond = data.get("bond_text", {})
    bond_texts = bond.get(lang, bond.get("en", []))
    if bond_texts:
        for i, text in enumerate(bond_texts):
            if text:
                label = f"Bond {i+1}" if i < 5 else f"Extra {i-4}"
                lines.append(f"\n[{label}]")
                lines.append(text.strip())

    result = "\n".join(lines)
    if len(result) > max_chars:
        result = result[:max_chars] + "\n... (truncated)"
    return result


def get_servant_bond_texts(atlas_id: int, lang: str = "en") -> list[str]:
    """Get raw bond text list for a servant."""
    data = load_servant_data(atlas_id)
    if not data:
        return []
    bond = data.get("bond_text", {})
    return bond.get(lang, bond.get("en", []))


# ─── Story Data ──────────────────────────────────────────

def load_story_index() -> list[dict]:
    """Load stories/index.json — all chapters metadata."""
    data = _load_json(STORIES_DIR / "index.json")
    return data if isinstance(data, list) else []


def load_story_data(slug: str) -> Optional[dict]:
    """Load individual story file by slug.

    Tries multiple filename patterns:
      - singularity_{number}_{slug}.json
      - lostbelt_{number}_{slug}.json
      - direct {slug}.json
    """
    # Try direct match first
    for f in STORIES_DIR.glob("*.json"):
        if f.stem == slug or f.stem.endswith(f"_{slug}"):
            return _load_json(f)
    return None


def find_story_file(chapter_type: str, number: str) -> Optional[dict]:
    """Load story by type and number.

    Args:
        chapter_type: 'singularity', 'lostbelt', or 'remnant'
        number: 'F', 'I', 'II', ..., '1', '2', etc.
    """
    prefix_map = {
        "singularity": "singularity",
        "lostbelt": "lostbelt",
        "remnant": "remnant",
    }
    prefix = prefix_map.get(chapter_type, chapter_type)

    for f in STORIES_DIR.glob(f"{prefix}_{number}_*.json"):
        return _load_json(f)

    # Try numeric for lostbelts
    for f in STORIES_DIR.glob(f"{prefix}_{number}.json"):
        return _load_json(f)

    return None


# ─── Story Summaries ─────────────────────────────────────

def load_story_summary(slug: str) -> Optional[dict]:
    """Load chapter summary by slug (e.g., 'babylonia', 'lb1').

    Checks both file and directory variants:
      - summaries/by_chapter/{slug}.json
      - summaries/by_chapter/{slug}/ (directory with parts)
    """
    # Direct file
    direct = SUMMARIES_DIR / f"{slug}.json"
    if direct.exists():
        return _load_json(direct)

    # Directory with parts
    dir_path = SUMMARIES_DIR / slug
    if dir_path.is_dir():
        parts = []
        for f in sorted(dir_path.glob("*.json")):
            part = _load_json(f)
            if part:
                parts.append(part)
        if parts:
            return {"slug": slug, "parts": parts}

    return None


# Chapter slug mapping for singularities/lostbelts
CHAPTER_SLUG_MAP = {
    # Singularities
    "singularity_F": "fuyuki",
    "singularity_I": "orleans",
    "singularity_II": "septem",
    "singularity_III": "okeanos",
    "singularity_IV": "london",
    "singularity_V": "america",
    "singularity_VI": "camelot",
    "singularity_VII": "babylonia",
    "singularity_Final": "solomon",
    # Lostbelts
    "lostbelt_1": "lb1",
    "lostbelt_2": "lb2",
    "lostbelt_3": "lb3",
    "lostbelt_4": "lb4",
    "lostbelt_5": "lb5",
    "lostbelt_5.5": "lb5.5",
    "lostbelt_6": "lb6",
    "lostbelt_7": "lb7",
}


def get_chapter_summary_context(slug: str, max_chars: int = 5000) -> str:
    """Get formatted chapter summary for GPT context injection.

    Args:
        slug: Chapter slug (e.g., 'babylonia', 'lb1')
        max_chars: Max total characters

    Returns:
        Formatted summary text.
    """
    data = load_story_summary(slug)
    if not data:
        return f"(No summary found for chapter: {slug})"

    lines = [f"=== FGO Story Summary: {slug} ==="]

    if data.get("parts"):
        # Multi-part summary
        for part in data["parts"]:
            if isinstance(part, dict):
                # Could be nested structure from directory
                parts_list = part.get("parts", [part])
                for p in (parts_list if isinstance(parts_list, list) else [parts_list]):
                    title = p.get("title_en", p.get("title_ja", f"Part {p.get('part', '?')}"))
                    summary = p.get("summary", "")
                    if summary:
                        lines.append(f"\n## {title}")
                        lines.append(summary.strip())

                    # Key characters
                    chars = p.get("key_characters", [])
                    if chars:
                        char_names = [c.get("name", "") for c in chars[:10]]
                        lines.append(f"Key characters: {', '.join(char_names)}")
    else:
        # Single summary — either top-level summary or flat parts list
        summary = data.get("summary", "")
        if summary:
            lines.append(f"\n{summary.strip()}")
        chars = data.get("key_characters", [])
        if chars:
            char_names = [c.get("name", "") for c in chars[:10]]
            lines.append(f"Key characters: {', '.join(char_names)}")

    result = "\n".join(lines)
    if len(result) > max_chars:
        result = result[:max_chars] + "\n... (truncated)"
    return result


# ─── Confirmed Links ─────────────────────────────────────

def load_confirmed_links() -> list[dict]:
    """Load confirmed servant → person links.

    Returns list of dicts with: servant_id, name_en, person_id, person_name, etc.
    """
    data = _load_json(PERSON_LINKS_DIR / "confirmed_links.json")
    return data if isinstance(data, list) else []


def load_enriched_servants() -> list[dict]:
    """Load enriched servants with person matches + metadata."""
    data = _load_json(PERSON_LINKS_DIR / "enriched_servants.json")
    return data if isinstance(data, list) else []


# ─── Chapter Servants ────────────────────────────────────

def get_chapter_servants(story_data: dict, top_n: int = 10) -> list[dict]:
    """Extract top servants/characters from a story chapter.

    Uses stats.top_speakers for ranking by dialogue frequency.

    Returns list of {name_en, name_ja, lines, chapters} sorted by lines DESC.
    """
    stats = story_data.get("stats", {})
    top_speakers = stats.get("top_speakers", [])

    result = []
    for sp in top_speakers[:top_n]:
        result.append({
            "name": sp.get("name", sp.get("name_ja", "")),
            "name_ja": sp.get("name_ja", sp.get("name", "")),
            "lines": sp.get("lines", sp.get("total_lines", 0)),
        })

    return result


# ─── Dialogue Data ───────────────────────────────────────

def load_dialogue_stats() -> Optional[dict]:
    """Load global dialogue statistics."""
    return _load_json(DIALOGUES_DIR / "stats.json")


def get_chapter_dialogue_excerpt(slug: str, max_lines: int = 20) -> str:
    """Get notable dialogue lines from a chapter for context.

    Reads from by_chapter/{slug}/ directory if available.
    """
    chapter_dir = DIALOGUES_DIR / "by_chapter" / slug
    if not chapter_dir.is_dir():
        return "(No dialogue data for this chapter)"

    lines = []
    for f in sorted(chapter_dir.glob("*.json"))[:5]:
        data = _load_json(f)
        if not data:
            continue
        dialogues = data if isinstance(data, list) else data.get("dialogues", [])
        for d in dialogues[:max_lines]:
            if isinstance(d, dict):
                speaker = d.get("speaker", d.get("name", "???"))
                text = d.get("text", d.get("line", ""))
                if text and len(text) > 10:
                    lines.append(f"[{speaker}] {text.strip()}")
            if len(lines) >= max_lines:
                break
        if len(lines) >= max_lines:
            break

    return "\n".join(lines) if lines else "(No notable dialogues found)"


# ─── DB Helpers ──────────────────────────────────────────

def get_person_context_from_db(db, person_id: int, max_events: int = 10) -> str:
    """Get historical person context from DB for GPT prompt.

    Args:
        db: SQLAlchemy session
        person_id: Person ID in DB
        max_events: Max related events to include

    Returns:
        Formatted context string.
    """
    from sqlalchemy import text as sql_text

    # Person info
    person = db.execute(sql_text("""
        SELECT name, name_ko, birth_year, death_year, role,
               importance_score, certainty
        FROM persons WHERE id = :pid
    """), {"pid": person_id}).fetchone()

    if not person:
        return f"(Person {person_id} not found in DB)"

    lines = [f"=== Historical Person: {person[0]} ==="]
    if person[1]:
        lines.append(f"Korean name: {person[1]}")
    if person[2] or person[3]:
        birth = f"{abs(person[2])} {'BCE' if person[2] < 0 else 'CE'}" if person[2] else "?"
        death = f"{abs(person[3])} {'BCE' if person[3] < 0 else 'CE'}" if person[3] else "?"
        lines.append(f"Life: {birth} — {death}")
    if person[4]:
        lines.append(f"Role: {person[4]}")

    # Person details (biography)
    details = db.execute(sql_text("""
        SELECT biography FROM person_details WHERE person_id = :pid LIMIT 1
    """), {"pid": person_id}).fetchone()
    if details and details[0]:
        bio = details[0][:1500]
        lines.append(f"\nBiography:\n{bio}")

    # Related events
    events = db.execute(sql_text("""
        SELECT e.title, e.date_start, e.date_end, e.importance
        FROM events e
        JOIN event_persons ep ON ep.event_id = e.id
        WHERE ep.person_id = :pid
        ORDER BY e.importance DESC, e.date_start
        LIMIT :limit
    """), {"pid": person_id, "limit": max_events}).fetchall()

    if events:
        lines.append(f"\nRelated events ({len(events)}):")
        for ev in events:
            year_str = str(ev[1]) if ev[1] else "?"
            lines.append(f"  - {ev[0]} ({year_str})")

    return "\n".join(lines)


def get_events_for_person(db, person_id: int) -> list[int]:
    """Get event IDs related to a person."""
    from sqlalchemy import text as sql_text
    rows = db.execute(sql_text("""
        SELECT DISTINCT ep.event_id FROM event_persons ep
        WHERE ep.person_id = :pid
    """), {"pid": person_id}).fetchall()
    return [r[0] for r in rows]


# ─── Singularity/LB Metadata ────────────────────────────

# Canonical metadata for FGO chapters
SINGULARITY_META = {
    "F": {
        "slug": "fuyuki", "title": "Singularity F: Fuyuki",
        "title_ko": "특이점 F: 후유키", "year": 2004,
        "location": "Fuyuki, Japan", "era": "Modern Era",
        "story_slug": "fuyuki",
    },
    "I": {
        "slug": "orleans", "title": "Singularity I: Orleans",
        "title_ko": "특이점 I: 오를레앙", "year": 1431,
        "location": "France", "era": "Hundred Years' War",
        "story_slug": "orleans",
    },
    "II": {
        "slug": "septem", "title": "Singularity II: Septem",
        "title_ko": "특이점 II: 셉템", "year": 60,
        "location": "Roman Empire", "era": "Roman Imperial Period",
        "story_slug": "septem",
    },
    "III": {
        "slug": "okeanos", "title": "Singularity III: Okeanos",
        "title_ko": "특이점 III: 오케아노스", "year": 1573,
        "location": "Atlantic Ocean", "era": "Age of Exploration",
        "story_slug": "okeanos",
    },
    "IV": {
        "slug": "london", "title": "Singularity IV: London",
        "title_ko": "특이점 IV: 런던", "year": 1888,
        "location": "London, England", "era": "Victorian Era",
        "story_slug": "london",
    },
    "V": {
        "slug": "america", "title": "Singularity V: E Pluribus Unum",
        "title_ko": "특이점 V: 이 플루리버스 우눔", "year": 1783,
        "location": "North America", "era": "American Independence Era",
        "story_slug": "america",
    },
    "VI": {
        "slug": "camelot", "title": "Singularity VI: Camelot",
        "title_ko": "특이점 VI: 카멜롯", "year": 1273,
        "location": "Holy Land (Jerusalem)", "era": "Crusades Era",
        "story_slug": "camelot",
    },
    "VII": {
        "slug": "babylonia", "title": "Singularity VII: Babylonia",
        "title_ko": "특이점 VII: 바빌로니아", "year": -2655,
        "location": "Mesopotamia (Uruk)", "era": "Age of Gods / Ancient Mesopotamia",
        "story_slug": "babylonia",
    },
    "Final": {
        "slug": "solomon", "title": "Final Singularity: Solomon",
        "title_ko": "종장 특이점: 솔로몬", "year": 2016,
        "location": "Temple of Time", "era": "Modern Era",
        "story_slug": "solomon",
    },
}

LOSTBELT_META = {
    1: {
        "slug": "lb1-anastasia", "title": "Lostbelt No.1: Anastasia",
        "title_ko": "이문대 No.1: 아나스타시아", "year": 1570,
        "location": "Russia", "era": "Russian Empire / Ivan the Terrible",
        "story_slug": "lb1",
    },
    2: {
        "slug": "lb2-gotterdammerung", "title": "Lostbelt No.2: Götterdämmerung",
        "title_ko": "이문대 No.2: 신들의 황혼", "year": 1000,
        "location": "Scandinavia", "era": "Norse Age / Viking Era",
        "story_slug": "lb2",
    },
    3: {
        "slug": "lb3-sin", "title": "Lostbelt No.3: SIN",
        "title_ko": "이문대 No.3: 인지천명시대", "year": -210,
        "location": "China", "era": "Qin Dynasty / Warring States",
        "story_slug": "lb3",
    },
    4: {
        "slug": "lb4-yuga-kshetra", "title": "Lostbelt No.4: Yuga Kshetra",
        "title_ko": "이문대 No.4: 유가 크셰트라", "year": -3000,
        "location": "India", "era": "Mythological India",
        "story_slug": "lb4",
    },
    5: {
        "slug": "lb5-atlantis-olympus", "title": "Lostbelt No.5: Atlantis / Olympus",
        "title_ko": "이문대 No.5: 아틀란티스/올림포스", "year": -12000,
        "location": "Greece / Atlantic", "era": "Age of Gods / Greek Mythology",
        "story_slug": "lb5",
    },
    6: {
        "slug": "lb6-avalon", "title": "Lostbelt No.6: Avalon le Fae",
        "title_ko": "이문대 No.6: 요정 원무 아발론", "year": 500,
        "location": "Britain (Fairy)", "era": "Arthurian / Fairy Britain",
        "story_slug": "lb6",
    },
    7: {
        "slug": "lb7-nahui-mictlan", "title": "Lostbelt No.7: Nahui Mictlan",
        "title_ko": "이문대 No.7: 나우이 믹틀란", "year": -6000,
        "location": "South America", "era": "Mesoamerican Mythology",
        "story_slug": "lb7",
    },
}
