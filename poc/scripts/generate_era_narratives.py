"""
Era Narrative Generation Pipeline (v2 - Regional).

Generates AI-powered historical narratives per 50-year period,
broken down by world region. Each period can produce:
- 1 global overview (cross-region synthesis)
- N regional sub-narratives (1 per active region)

Regions: europe, near_east, south_asia, east_asia, africa, americas

Usage:
    python generate_era_narratives.py                     # Full run
    python generate_era_narratives.py --test 3            # Test with 3 periods
    python generate_era_narratives.py --resume            # Resume from checkpoint
    python generate_era_narratives.py --apply             # Apply JSONL to DB
    python generate_era_narratives.py --stats             # Show checkpoint stats

Output: poc/data/timeline/era_narratives_v2.jsonl
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# --- Config ---
DB_URL = "postgresql://chaldeas:chaldeas_dev@127.0.0.1:5432/chaldeas"
CHECKPOINT_FILE = Path(__file__).parent.parent / "data" / "timeline" / "era_narratives_v2.jsonl"
WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary"
WIKI_HEADERS = {"User-Agent": "CHALDEAS/1.0 (historical-atlas; contact@chaldeas.site)"}
LLM_MODEL = "gpt-5.1-chat-latest"
MIN_SCORE = 70
MIN_YEAR = -3500
MAX_YEAR = 2100

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# --- Regions ---
REGIONS = [
    {
        "id": "europe",
        "name": "Europe & Mediterranean",
        "lat_range": (35, 72),
        "lng_range": (-15, 40),
    },
    {
        "id": "near_east",
        "name": "Near East & Central Asia",
        "lat_range": (15, 50),
        "lng_range": (25, 70),
    },
    {
        "id": "south_asia",
        "name": "South Asia",
        "lat_range": (5, 40),
        "lng_range": (60, 100),
    },
    {
        "id": "east_asia",
        "name": "East Asia & Pacific",
        "lat_range": (10, 55),
        "lng_range": (100, 150),
    },
    {
        "id": "africa",
        "name": "Africa",
        "lat_range": (-35, 35),
        "lng_range": (-20, 55),
    },
    {
        "id": "americas",
        "name": "Americas",
        "lat_range": (-55, 70),
        "lng_range": (-170, -30),
    },
]

# Build SQL CASE for region classification
def _region_case_sql(lat_col="l.latitude", lng_col="l.longitude"):
    parts = []
    for r in REGIONS:
        lat_min, lat_max = r["lat_range"]
        lng_min, lng_max = r["lng_range"]
        parts.append(
            f"WHEN {lat_col} BETWEEN {lat_min} AND {lat_max} "
            f"AND {lng_col} BETWEEN {lng_min} AND {lng_max} THEN '{r['id']}'"
        )
    return "CASE " + " ".join(parts) + " ELSE 'other' END"


REGION_CASE = _region_case_sql()

ERA_MAP = [
    (-3500, -500, "ancient", "Ancient World"),
    (-500, 500, "classical", "Classical Era"),
    (500, 1500, "medieval", "Medieval Period"),
    (1500, 1800, "early-modern", "Early Modern"),
    (1800, 1945, "modern", "Modern Era"),
    (1945, 2030, "contemporary", "Contemporary"),
]

def classify_era(year):
    for start, end, era_id, era_name in ERA_MAP:
        if start <= year < end:
            return era_id, era_name
    return "ancient", "Ancient World"

def format_year(year):
    if year < 0:
        return f"{abs(year)} BCE"
    return f"{year} CE"

def region_name(region_id):
    for r in REGIONS:
        if r["id"] == region_id:
            return r["name"]
    return region_id


# --- DB ---
def get_db_session():
    engine = create_engine(DB_URL, pool_pre_ping=True)
    return sessionmaker(bind=engine)()


def get_openai_client():
    from openai import OpenAI
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding='utf-8').splitlines():
                if line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found")
    return OpenAI(api_key=api_key)


# --- Data Queries ---

def get_periods_with_data(db):
    """Get all 50-year periods with high-score entities within human history."""
    rows = db.execute(text(f"""
        WITH event_periods AS (
            SELECT FLOOR(date_start::float / 50) * 50 AS ps, COUNT(*) AS cnt,
                   MAX(importance_score) AS max_score
            FROM events
            WHERE date_start IS NOT NULL AND importance_score >= :min_score
              AND date_start >= :min_year AND date_start <= :max_year
            GROUP BY FLOOR(date_start::float / 50) * 50
        ),
        person_periods AS (
            SELECT FLOOR(COALESCE(birth_year, floruit_start)::float / 50) * 50 AS ps,
                   COUNT(*) AS cnt, MAX(COALESCE(global_score, importance_score)) AS max_score
            FROM persons
            WHERE COALESCE(birth_year, floruit_start) IS NOT NULL
              AND COALESCE(global_score, importance_score) >= :min_score
              AND COALESCE(birth_year, floruit_start) >= :min_year
              AND COALESCE(birth_year, floruit_start) <= :max_year
            GROUP BY FLOOR(COALESCE(birth_year, floruit_start)::float / 50) * 50
        )
        SELECT COALESCE(e.ps, p.ps) AS ps,
               COALESCE(e.cnt, 0), COALESCE(e.max_score, 0),
               COALESCE(p.cnt, 0), COALESCE(p.max_score, 0)
        FROM event_periods e
        FULL OUTER JOIN person_periods p ON e.ps = p.ps
        ORDER BY COALESCE(e.ps, p.ps)
    """), {"min_score": MIN_SCORE, "min_year": MIN_YEAR, "max_year": MAX_YEAR}).fetchall()

    periods = []
    for row in rows:
        ps = int(row[0])
        era_id, era_name = classify_era(ps)
        periods.append({
            "period_start": ps, "period_end": ps + 49,
            "era_id": era_id, "era_name": era_name,
            "event_count": row[1], "max_event_score": row[2],
            "person_count": row[3], "max_person_score": row[4],
        })
    return periods


def get_regional_data(db, period_start, period_end):
    """Get events and persons grouped by region for a period."""
    # Events with location -> region
    event_rows = db.execute(text(f"""
        SELECT {REGION_CASE} AS region,
               e.id, e.title, e.date_start, e.importance_score,
               ed.description, ed.wikipedia_url, l.name AS location_name
        FROM events e
        LEFT JOIN event_details ed ON ed.event_id = e.id
        LEFT JOIN locations l ON l.id = e.primary_location_id
        WHERE e.date_start >= :start AND e.date_start <= :end
          AND e.importance_score >= :min_score
          AND l.latitude IS NOT NULL
        ORDER BY e.importance_score DESC
    """), {"start": period_start, "end": period_end, "min_score": MIN_SCORE - 10}).fetchall()

    # Events without location
    no_loc_events = db.execute(text("""
        SELECT e.id, e.title, e.date_start, e.importance_score,
               ed.description, ed.wikipedia_url
        FROM events e
        LEFT JOIN event_details ed ON ed.event_id = e.id
        WHERE e.date_start >= :start AND e.date_start <= :end
          AND e.importance_score >= :min_score
          AND e.primary_location_id IS NULL
        ORDER BY e.importance_score DESC LIMIT 5
    """), {"start": period_start, "end": period_end, "min_score": MIN_SCORE}).fetchall()

    # Persons with birthplace -> region
    person_rows = db.execute(text(f"""
        SELECT {_region_case_sql('l.latitude', 'l.longitude')} AS region,
               p.id, p.name, p.birth_year, p.death_year, p.role, p.domain,
               COALESCE(p.global_score, p.importance_score) AS score,
               pd.biography, pd.wikipedia_url
        FROM persons p
        LEFT JOIN person_details pd ON pd.person_id = p.id
        LEFT JOIN locations l ON l.id = p.birthplace_id
        WHERE COALESCE(p.birth_year, p.floruit_start) >= :start
          AND COALESCE(p.birth_year, p.floruit_start) <= :end
          AND COALESCE(p.global_score, p.importance_score) >= :min_score
          AND l.latitude IS NOT NULL
        ORDER BY COALESCE(p.global_score, p.importance_score) DESC
    """), {"start": period_start, "end": period_end, "min_score": MIN_SCORE - 10}).fetchall()

    # Group by region
    regions = {}
    for row in event_rows:
        rid = row[0]
        if rid not in regions:
            regions[rid] = {"events": [], "persons": []}
        if len(regions[rid]["events"]) < 5:
            regions[rid]["events"].append({
                "id": row[1], "title": row[2], "date_start": row[3],
                "importance_score": row[4], "description": row[5],
                "wikipedia_url": row[6], "location_name": row[7],
            })

    for row in person_rows:
        rid = row[0]
        if rid not in regions:
            regions[rid] = {"events": [], "persons": []}
        if len(regions[rid]["persons"]) < 5:
            regions[rid]["persons"].append({
                "id": row[1], "name": row[2], "birth_year": row[3],
                "death_year": row[4], "role": row[5], "domain": row[6],
                "score": row[7], "biography": row[8], "wikipedia_url": row[9],
            })

    # Add locationless events to 'global'
    if no_loc_events:
        if "global" not in regions:
            regions["global"] = {"events": [], "persons": []}
        for row in no_loc_events:
            regions["global"]["events"].append({
                "id": row[0], "title": row[1], "date_start": row[2],
                "importance_score": row[3], "description": row[4],
                "wikipedia_url": row[5], "location_name": None,
            })

    # Filter out regions with too little data
    filtered = {}
    for rid, data in regions.items():
        if rid == "other":
            continue
        total_items = len(data["events"]) + len(data["persons"])
        max_score = max(
            [e["importance_score"] for e in data["events"]] +
            [p["score"] for p in data["persons"]] +
            [0]
        )
        if total_items >= 1 and max_score >= MIN_SCORE:
            filtered[rid] = data

    return filtered


# --- Wikipedia ---
def fetch_wiki_summary(url_or_title):
    if not url_or_title:
        return None
    title = url_or_title.rstrip("/").split("/")[-1] if "wikipedia.org" in url_or_title else url_or_title
    try:
        resp = requests.get(f"{WIKI_API}/{title}", headers=WIKI_HEADERS, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("extract", "")
    except Exception as e:
        print(f"    [WARN] Wiki fetch failed: {e}")
    return None


# --- LLM ---
def llm_call(client, prompt, max_tokens=800):
    """Single LLM call with JSON output."""
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_completion_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"    [ERROR] LLM failed: {e}")
        return None


def generate_regional_narrative(client, period, region_id, events, persons):
    """Generate a narrative for a specific region in a specific period."""
    event_lines = []
    for e in events[:3]:
        desc = (e.get("description") or "")[:200]
        loc = e.get("location_name") or ""
        event_lines.append(f"  - {e['title']} ({format_year(e['date_start'])}) [score:{e['importance_score']}] {loc} - {desc}")

    person_lines = []
    for p in persons[:3]:
        lifespan = format_year(p["birth_year"]) if p.get("birth_year") else "?"
        if p.get("death_year"):
            lifespan += f" ~ {format_year(p['death_year'])}"
        bio = (p.get("biography") or "")[:200]
        person_lines.append(f"  - {p['name']} ({lifespan}) [{p.get('domain', '?')}] - {bio}")

    rname = region_name(region_id)

    prompt = f"""You are a world history expert writing for an interactive atlas.

Period: {format_year(period['period_start'])} to {format_year(period['period_end'])}
Region: {rname}

Events in this region during this period:
{chr(10).join(event_lines) if event_lines else '  (none in database - use your knowledge)'}

Key figures from this region during this period:
{chr(10).join(person_lines) if person_lines else '  (none in database - use your knowledge)'}

Write about what was happening in {rname} during this period (150-250 words).
- Focus on this region specifically
- Explain WHY these developments matter in world history context
- If the database has few entries, supplement with your own knowledge of what was happening in this region
- Mention connections to other regions if relevant

Also provide:
- A headline for this region during this period (max 80 chars)
- 2-4 keywords

Respond ONLY as valid JSON:
{{
  "headline": "...",
  "narrative": "...",
  "keywords": ["..."]
}}"""

    return llm_call(client, prompt, max_tokens=600)


def generate_global_overview(client, period, regional_headlines):
    """Generate a global synthesis connecting all active regions."""
    region_lines = []
    for rid, headline in regional_headlines.items():
        region_lines.append(f"  - {region_name(rid)}: {headline}")

    prompt = f"""You are a world history expert writing a global synthesis for an interactive atlas.

Period: {format_year(period['period_start'])} to {format_year(period['period_end'])}
Era: {period['era_name']}

What was happening in each region:
{chr(10).join(region_lines)}

Write a brief global overview (100-150 words) that:
1. Synthesizes what's happening worldwide during this half-century
2. Highlights connections, contrasts, or parallel developments between regions
3. Identifies the most globally significant development
4. Explains what this period leads to next

Also provide:
- A period headline (max 80 chars) - the single most important theme
- The defining moment of this period (one sentence)

Respond ONLY as valid JSON:
{{
  "headline": "...",
  "narrative": "...",
  "defining_moment": "..."
}}"""

    return llm_call(client, prompt, max_tokens=500)


# --- Checkpoint ---
def load_checkpoint():
    done = set()
    if CHECKPOINT_FILE.exists():
        for line in CHECKPOINT_FILE.read_text(encoding='utf-8').splitlines():
            if line.strip():
                try:
                    e = json.loads(line)
                    key = f"{e.get('type')}:{e.get('period_start')}:{e.get('region', 'global')}"
                    done.add(key)
                except json.JSONDecodeError:
                    pass
    return done


def save_checkpoint(entry):
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# --- DB Apply ---
def apply_to_db(db):
    if not CHECKPOINT_FILE.exists():
        print("No checkpoint file found.")
        return

    count = 0
    for line in CHECKPOINT_FILE.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)

        if entry["type"] in ("regional", "global_overview"):
            region = entry.get("region")
            ps = entry["period_start"]
            pe = entry["period_end"]

            existing = db.execute(text(
                "SELECT id FROM period_narratives WHERE period_start = :ps AND period_end = :pe "
                "AND (region = :region OR (region IS NULL AND :region IS NULL))"
            ), {"ps": ps, "pe": pe, "region": region}).fetchone()

            data = {
                "ps": ps, "pe": pe, "region": region,
                "era_id": entry.get("era_id"),
                "headline": entry.get("headline"),
                "narrative": entry.get("narrative"),
                "keywords": entry.get("keywords"),
                "defining_moment": entry.get("defining_moment"),
                "model_used": entry.get("model_used"),
                "event_count": entry.get("event_count", 0),
                "person_count": entry.get("person_count", 0),
                "top_events": json.dumps(entry.get("top_events", []), ensure_ascii=False) if entry.get("top_events") else None,
                "top_persons": json.dumps(entry.get("top_persons", []), ensure_ascii=False) if entry.get("top_persons") else None,
            }

            if existing:
                db.execute(text("""
                    UPDATE period_narratives
                    SET headline=:headline, narrative=:narrative, keywords=:keywords,
                        defining_moment=:defining_moment, era_id=:era_id, model_used=:model_used,
                        event_count=:event_count, person_count=:person_count,
                        top_events=:top_events, top_persons=:top_persons,
                        generated_at=NOW(), updated_at=NOW()
                    WHERE id=:id
                """), {**data, "id": existing[0]})
            else:
                db.execute(text("""
                    INSERT INTO period_narratives
                        (period_start, period_end, region, era_id, headline, narrative,
                         keywords, defining_moment, model_used, event_count, person_count,
                         top_events, top_persons)
                    VALUES (:ps, :pe, :region, :era_id, :headline, :narrative,
                            :keywords, :defining_moment, :model_used, :event_count, :person_count,
                            :top_events, :top_persons)
                """), data)
            count += 1

    db.commit()
    print(f"Applied {count} narrative entries to DB.")


# --- Main Pipeline ---
def run_pipeline(test_limit=None, resume=True):
    db = get_db_session()
    client = get_openai_client()

    periods = get_periods_with_data(db)
    print(f"Found {len(periods)} periods")

    if test_limit:
        # Pick interesting periods (not just the earliest)
        # Find periods near -500 (Classical Greece/Persia/Buddha/Confucius)
        interesting = [p for p in periods if -600 <= p["period_start"] <= -400]
        if len(interesting) >= test_limit:
            periods = interesting[:test_limit]
        else:
            periods = periods[:test_limit]
        print(f"[TEST] Processing {len(periods)} periods: {[p['period_start'] for p in periods]}")

    done = load_checkpoint() if resume else set()
    if done:
        print(f"Resuming: {len(done)} entries done")

    total_calls = 0

    for i, period in enumerate(periods):
        ps = period["period_start"]
        pe = period["period_end"]
        print(f"\n[{i+1}/{len(periods)}] {format_year(ps)} ~ {format_year(pe)} ({period['era_name']})")

        # Get regional data
        regional_data = get_regional_data(db, ps, pe)
        if not regional_data:
            print("  No regional data, skipping")
            continue

        active_regions = sorted(regional_data.keys())
        print(f"  Active regions: {active_regions}")

        regional_headlines = {}

        # --- Generate regional narratives ---
        for rid in active_regions:
            rdata = regional_data[rid]
            key = f"regional:{ps}:{rid}"

            if key in done:
                # Load headline from checkpoint for global synthesis
                for line in CHECKPOINT_FILE.read_text(encoding='utf-8').splitlines():
                    if line.strip():
                        e = json.loads(line)
                        if e.get("period_start") == ps and e.get("region") == rid:
                            regional_headlines[rid] = e.get("headline", "")
                            break
                continue

            events = rdata["events"]
            persons = rdata["persons"]
            print(f"  [{region_name(rid)}] {len(events)} events, {len(persons)} persons")

            result = generate_regional_narrative(client, period, rid, events, persons)
            if result:
                regional_headlines[rid] = result.get("headline", "")

                # Build top entity names for quick display
                top_ev = [{"title": e["title"], "date": format_year(e["date_start"]), "score": e["importance_score"]} for e in events[:3]]
                top_pe = [{"name": p["name"], "domain": p.get("domain"), "score": p["score"]} for p in persons[:3]]

                save_checkpoint({
                    "type": "regional",
                    "period_start": ps, "period_end": pe,
                    "region": rid,
                    "era_id": period["era_id"],
                    "model_used": LLM_MODEL,
                    "event_count": len(events),
                    "person_count": len(persons),
                    "top_events": top_ev,
                    "top_persons": top_pe,
                    **result,
                })
                total_calls += 1
                print(f"    -> {result.get('headline', '?')}")
            time.sleep(0.3)

        # --- Generate global overview ---
        global_key = f"global_overview:{ps}:global"
        if global_key not in done and len(regional_headlines) >= 1:
            print(f"  [GLOBAL] Synthesizing {len(regional_headlines)} regions...")
            result = generate_global_overview(client, period, regional_headlines)
            if result:
                save_checkpoint({
                    "type": "global_overview",
                    "period_start": ps, "period_end": pe,
                    "region": None,
                    "era_id": period["era_id"],
                    "model_used": LLM_MODEL,
                    **result,
                })
                total_calls += 1
                print(f"    -> {result.get('headline', '?')}")
            time.sleep(0.3)

    est_cost = total_calls * 0.003  # ~$0.003 per call based on test
    print(f"\n{'='*60}")
    print(f"Done! LLM calls: {total_calls}, est cost: ~${est_cost:.2f}")
    print(f"Checkpoint: {CHECKPOINT_FILE}")
    print(f"\nTo apply: python generate_era_narratives.py --apply")
    db.close()


def main():
    parser = argparse.ArgumentParser(description="Generate era narratives (v2 - regional)")
    parser.add_argument("--test", type=int, help="Test with N periods")
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--stats", action="store_true")
    args = parser.parse_args()

    if args.apply:
        db = get_db_session()
        apply_to_db(db)
        db.close()
        return

    if args.stats:
        if not CHECKPOINT_FILE.exists():
            print("No checkpoint file.")
            return
        entries = [json.loads(l) for l in CHECKPOINT_FILE.read_text(encoding='utf-8').splitlines() if l.strip()]
        types = {}
        regions = {}
        for e in entries:
            t = e.get("type", "?")
            types[t] = types.get(t, 0) + 1
            r = e.get("region", "global")
            regions[r] = regions.get(r, 0) + 1
        print(f"Entries: {len(entries)}")
        print(f"Types: {types}")
        print(f"Regions: {regions}")
        return

    run_pipeline(test_limit=args.test, resume=not args.no_resume)


if __name__ == "__main__":
    main()
