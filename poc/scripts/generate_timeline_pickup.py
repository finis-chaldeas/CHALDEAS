"""
Generate 50-year period timeline pickup from importance scores.

Produces a structured JSON with top events and persons per 50-year period,
including location coordinates for globe positioning.

Usage:
    python generate_timeline_pickup.py
    python generate_timeline_pickup.py --top 5        # Top 5 per period
    python generate_timeline_pickup.py --min-score 50  # Minimum importance score
    python generate_timeline_pickup.py --format ts     # Output TypeScript
"""
import sys
import json
import argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / '.env')

from sqlalchemy import create_engine, text

engine = create_engine('postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas')
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "timeline"


def generate_periods(top_n: int = 3, min_score: int = 60):
    """Generate 50-year period data with top events and persons."""

    query = text("""
    WITH period_events AS (
        SELECT
            CASE
                WHEN e.date_start < 0 THEN ((e.date_start - 49) / 50) * 50
                ELSE (e.date_start / 50) * 50
            END as period,
            e.id, e.title, e.date_start, e.date_end,
            e.importance_score, e.importance,
            LEFT(ed.description, 200) as description,
            l.latitude, l.longitude
        FROM events e
        LEFT JOIN event_details ed ON ed.event_id = e.id
        LEFT JOIN event_locations el ON el.event_id = e.id
        LEFT JOIN locations l ON l.id = el.location_id
        WHERE e.importance_score >= :min_score
          AND e.date_start >= -3100 AND e.date_start <= 2025
    ),
    period_persons AS (
        SELECT
            CASE
                WHEN p.birth_year < 0 THEN ((p.birth_year - 49) / 50) * 50
                ELSE (p.birth_year / 50) * 50
            END as period,
            p.id, p.name AS title,
            p.birth_year AS date_start, p.death_year AS date_end,
            COALESCE(p.global_score, p.importance_score) as importance_score,
            p.importance,
            LEFT(p.description, 200) as description,
            NULL::numeric as latitude, NULL::numeric as longitude,
            p.role
        FROM persons p
        WHERE COALESCE(p.global_score, p.importance_score) >= :min_score
          AND p.birth_year IS NOT NULL
          AND p.birth_year >= -3100 AND p.birth_year <= 2025
    ),
    ranked_events AS (
        SELECT *,
            ROW_NUMBER() OVER (PARTITION BY period ORDER BY importance_score DESC, id) as rn,
            COUNT(*) OVER (PARTITION BY period) as total_in_period
        FROM period_events
    ),
    ranked_persons AS (
        SELECT *,
            ROW_NUMBER() OVER (PARTITION BY period ORDER BY importance_score DESC, id) as rn,
            COUNT(*) OVER (PARTITION BY period) as total_in_period
        FROM period_persons
    )
    SELECT 'event' as type,
           re.period, re.id, re.title as name, re.date_start, re.date_end,
           re.importance_score, re.importance, re.description,
           re.latitude, re.longitude, NULL::varchar as role,
           re.total_in_period, re.rn
    FROM ranked_events re
    WHERE re.rn <= :top_n
    UNION ALL
    SELECT 'person' as type,
           rp.period, rp.id, rp.title as name, rp.date_start, rp.date_end,
           rp.importance_score, rp.importance, rp.description,
           rp.latitude, rp.longitude, rp.role,
           rp.total_in_period, rp.rn
    FROM ranked_persons rp
    WHERE rp.rn <= :top_n
    ORDER BY period, type DESC, rn
    """)

    with engine.connect() as conn:
        rows = conn.execute(query, {"top_n": top_n, "min_score": min_score}).fetchall()

    # Group by period
    periods = {}
    for r in rows:
        p = r[1]  # period
        if p not in periods:
            periods[p] = {
                "period_start": p,
                "period_end": p + 49,
                "events": [],
                "persons": [],
                "event_total": 0,
                "person_total": 0,
            }

        item = {
            "id": r[2],
            "name": r[3],
            "date_start": r[4],
            "date_end": r[5],
            "importance_score": r[6],
            "importance": r[7],
            "description": r[8] or "",
        }

        if r[0] == 'event':
            item["latitude"] = float(r[9]) if r[9] is not None else None
            item["longitude"] = float(r[10]) if r[10] is not None else None
            periods[p]["events"].append(item)
            periods[p]["event_total"] = r[12]
        else:
            item["role"] = r[11] or ""
            periods[p]["persons"].append(item)
            periods[p]["person_total"] = r[12]

    # Also note: persons CTE now uses birth_year/death_year as date_start/date_end
    # The UNION expects matching column names, so we alias them in the CTE

    # Sort by period
    result = sorted(periods.values(), key=lambda x: x["period_start"])
    return result


def get_period_locations(periods: list) -> list:
    """Add representative location per period from top event coordinates."""
    for p in periods:
        # Use the first event with coordinates
        lat, lng = None, None
        for ev in p["events"]:
            if ev.get("latitude") and ev.get("longitude"):
                lat = ev["latitude"]
                lng = ev["longitude"]
                break

        p["latitude"] = lat
        p["longitude"] = lng

    return periods


def assign_eras(periods: list) -> list:
    """Assign era labels to periods."""
    era_ranges = [
        (-3100, -500, "ancient", "Ancient World", "고대"),
        (-500, 500, "classical", "Classical Antiquity", "고전 고대"),
        (500, 1500, "medieval", "Medieval Period", "중세"),
        (1500, 1800, "early_modern", "Early Modern", "근세"),
        (1800, 1945, "modern", "Modern Era", "근대"),
        (1945, 2100, "contemporary", "Contemporary", "현대"),
    ]

    for p in periods:
        start = p["period_start"]
        for era_start, era_end, era_id, era_name, era_name_ko in era_ranges:
            if era_start <= start < era_end:
                p["era_id"] = era_id
                p["era_name"] = era_name
                p["era_name_ko"] = era_name_ko
                break
        else:
            p["era_id"] = "ancient"
            p["era_name"] = "Ancient World"
            p["era_name_ko"] = "고대"

    return periods


def format_year(year: int) -> str:
    """Format year for display."""
    if year < 0:
        return f"{abs(year)} BCE"
    return f"{year} CE"


def output_json(periods: list, filepath: Path):
    """Write periods to JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(periods, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(periods)} periods to {filepath}")


def output_typescript(periods: list, filepath: Path):
    """Generate TypeScript file compatible with LaplaceEra interface."""

    # Group by era
    eras = {}
    for p in periods:
        era_id = p["era_id"]
        if era_id not in eras:
            eras[era_id] = {
                "id": era_id,
                "name": p["era_name"],
                "name_ko": p["era_name_ko"],
                "start_year": p["period_start"],
                "end_year": p["period_end"],
                "entries": [],
            }
        else:
            eras[era_id]["end_year"] = max(eras[era_id]["end_year"], p["period_end"])

        # Create entries from top events/persons in this period
        top_event = p["events"][0] if p["events"] else None
        top_person = p["persons"][0] if p["persons"] else None

        # Use top event as the entry title, or top person if no events
        if top_event:
            entry_title = top_event["name"]
            desc_parts = []
            if top_event["description"]:
                desc_parts.append(top_event["description"][:100])
            if top_person:
                desc_parts.append(f"Key figure: {top_person['name']}")
            description = ". ".join(desc_parts) if desc_parts else entry_title

            entry = {
                "id": f"p{p['period_start']}",
                "title": entry_title,
                "description": description,
                "dateRange": {
                    "start": p["period_start"],
                    "end": p["period_end"],
                },
                "latitude": top_event.get("latitude"),
                "longitude": top_event.get("longitude"),
            }
            eras[era_id]["entries"].append(entry)

    # Generate TypeScript
    lines = [
        "/**",
        " * Auto-generated timeline data from importance scoring",
        f" * Generated with top events/persons per 50-year period",
        " * Source: poc/scripts/generate_timeline_pickup.py",
        " */",
        "",
        "import type { LaplaceEra } from './laplaceTimeline'",
        "",
        "export const GENERATED_ERAS: LaplaceEra[] = [",
    ]

    era_order = ["ancient", "classical", "medieval", "early_modern", "modern", "contemporary"]
    for era_id in era_order:
        if era_id not in eras:
            continue
        era = eras[era_id]
        lines.append(f"  {{")
        lines.append(f"    id: '{era['id']}',")
        lines.append(f"    name: '{era['name']}',")
        lines.append(f"    name_ko: '{era['name_ko']}',")
        lines.append(f"    start_year: {era['start_year']},")
        lines.append(f"    end_year: {era['end_year']},")
        lines.append(f"    entries: [")

        for entry in era["entries"]:
            title_escaped = entry["title"].replace("'", "\\'")
            desc_escaped = entry["description"].replace("'", "\\'")
            lines.append(f"      {{")
            lines.append(f"        id: '{entry['id']}',")
            lines.append(f"        title: '{title_escaped}',")
            lines.append(f"        description: '{desc_escaped}',")
            lines.append(f"        dateRange: {{ start: {entry['dateRange']['start']}, end: {entry['dateRange']['end']} }},")
            if entry.get("latitude") is not None and entry.get("longitude") is not None:
                lines.append(f"        latitude: {entry['latitude']}, longitude: {entry['longitude']},")
            lines.append(f"      }},")

        lines.append(f"    ],")
        lines.append(f"  }},")

    lines.append("]")
    lines.append("")

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print(f"Wrote TypeScript to {filepath}")


def print_summary(periods: list):
    """Print human-readable summary."""
    print(f"\n{'='*80}")
    print(f"Timeline Pickup: {len(periods)} periods ({format_year(periods[0]['period_start'])} ~ {format_year(periods[-1]['period_end'])})")
    print(f"{'='*80}\n")

    current_era = None
    for p in periods:
        if p["era_id"] != current_era:
            current_era = p["era_id"]
            print(f"\n--- {p['era_name']} ({p['era_name_ko']}) ---\n")

        period_label = f"{format_year(p['period_start'])} ~ {format_year(p['period_end'])}"
        top_ev = p["events"][0]["name"] if p["events"] else "-"
        top_ev_score = p["events"][0]["importance_score"] if p["events"] else 0
        top_per = p["persons"][0]["name"] if p["persons"] else "-"
        top_per_score = p["persons"][0]["importance_score"] if p["persons"] else 0

        print(f"  {period_label:30s} | E: {top_ev[:35]:35s} ({top_ev_score:3d}) | P: {top_per[:25]:25s} ({top_per_score:3d})")


def main():
    parser = argparse.ArgumentParser(description="Generate timeline pickup from importance scores")
    parser.add_argument("--top", type=int, default=3, help="Top N items per period (default: 3)")
    parser.add_argument("--min-score", type=int, default=60, help="Minimum importance score (default: 60)")
    parser.add_argument("--format", choices=["json", "ts", "both"], default="both",
                        help="Output format (default: both)")
    args = parser.parse_args()

    print(f"Generating timeline pickup: top {args.top} per period, min score {args.min_score}")

    periods = generate_periods(top_n=args.top, min_score=args.min_score)
    periods = get_period_locations(periods)
    periods = assign_eras(periods)

    print_summary(periods)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.format in ("json", "both"):
        output_json(periods, OUTPUT_DIR / "timeline_pickup.json")

    if args.format in ("ts", "both"):
        output_typescript(periods, OUTPUT_DIR / "generated_eras.ts")

    # Also output a compact version with just top 1 per period
    compact = []
    for p in periods:
        compact.append({
            "period": f"{format_year(p['period_start'])} ~ {format_year(p['period_end'])}",
            "era": p["era_name_ko"],
            "top_event": p["events"][0]["name"] if p["events"] else None,
            "event_score": p["events"][0]["importance_score"] if p["events"] else None,
            "top_person": p["persons"][0]["name"] if p["persons"] else None,
            "person_score": p["persons"][0]["importance_score"] if p["persons"] else None,
            "event_total": p["event_total"],
            "person_total": p["person_total"],
        })

    compact_path = OUTPUT_DIR / "timeline_compact.json"
    with open(compact_path, 'w', encoding='utf-8') as f:
        json.dump(compact, f, ensure_ascii=False, indent=2)
    print(f"Wrote compact summary to {compact_path}")


if __name__ == "__main__":
    main()
