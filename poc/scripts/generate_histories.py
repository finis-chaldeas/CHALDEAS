"""
Auto-Generate Histories via GPT-5.1 - Creates entity-tagged historical essays.

Strategies:
  A. Cluster mode: Parent events with children → essay/era_overview
  B. Person mode: High-importance persons → biography

Follows curate_with_llm.py patterns:
  - psycopg2 direct DB connection
  - OpenAI JSON response mode
  - JSONL checkpoint for resumability
  - 0.3s rate limiting

Usage:
    cd backend
    python ../poc/scripts/generate_histories.py --mode cluster --limit 3
    python ../poc/scripts/generate_histories.py --mode person --limit 3
    python ../poc/scripts/generate_histories.py --mode cluster --dry-run
    python ../poc/scripts/generate_histories.py --mode person --limit 10 --skip-existing
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import psycopg2

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ═══════════════════════════════════════════
# Config
# ═══════════════════════════════════════════

DB_URL = "postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas"
LLM_MODEL = "gpt-5.1-chat-latest"
DATA_DIR = Path(__file__).parent.parent / "data" / "curation"
CHECKPOINT_FILE = DATA_DIR / "histories_checkpoint.jsonl"
LLM_DELAY = 0.3


# ═══════════════════════════════════════════
# Helpers (from curate_with_llm.py)
# ═══════════════════════════════════════════

def get_conn():
    return psycopg2.connect(DB_URL)


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
        raise ValueError("OPENAI_API_KEY not found in environment or .env file")
    return OpenAI(api_key=api_key)


def llm_call(client, system_prompt, user_prompt, max_tokens=1200):
    """Single LLM call expecting JSON output."""
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"    [ERROR] LLM call failed: {e}")
        return None


def format_year(year):
    if year is None:
        return "Unknown"
    if year < 0:
        return f"{abs(year)} BCE"
    return f"{year} CE"


def load_checkpoint(filepath):
    done = set()
    if filepath.exists():
        for line in filepath.read_text(encoding='utf-8').splitlines():
            if line.strip():
                try:
                    entry = json.loads(line)
                    key = entry.get("_key", "")
                    if key:
                        done.add(key)
                except json.JSONDecodeError:
                    pass
    return done


def save_checkpoint(filepath, entry):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ═══════════════════════════════════════════
# System Prompt
# ═══════════════════════════════════════════

SYSTEM_PROMPT = (
    "You are a historian writing for CHALDEAS, an interactive historical knowledge system. "
    "Write clear, engaging, factually accurate essays in English. "
    "Tag EVERY person, event, and location mentioned using the format: [Name](entity:type:id). "
    "Only use entity IDs from the provided context. Do not invent IDs. "
    "Always respond with valid JSON only."
)


# ═══════════════════════════════════════════
# Mode A: Cluster (parent events with children)
# ═══════════════════════════════════════════

def fetch_clusters(cur, limit=20):
    """Fetch parent events with child events for essay generation."""
    cur.execute("""
        SELECT e.id, e.title, e.date_start, e.date_end, e.importance, ed.description,
               COUNT(c.id) as child_count
        FROM events e
        JOIN events c ON c.parent_event_id = e.id
        LEFT JOIN event_details ed ON ed.event_id = e.id
        WHERE e.is_aggregate = TRUE
        GROUP BY e.id, ed.description HAVING COUNT(c.id) >= 3
        ORDER BY e.importance DESC NULLS LAST, child_count DESC
        LIMIT %s
    """, (limit,))
    return cur.fetchall()


def fetch_cluster_context(cur, parent_id):
    """Get children, persons, locations, and narratives for a parent event."""
    # Children events
    cur.execute("""
        SELECT e.id, e.title, e.date_start, e.date_end, ed.description
        FROM events e
        LEFT JOIN event_details ed ON ed.event_id = e.id
        WHERE e.parent_event_id = %s
        ORDER BY e.date_start NULLS LAST
        LIMIT 15
    """, (parent_id,))
    children = cur.fetchall()

    # Persons linked to parent or children
    event_ids = [parent_id] + [c[0] for c in children]
    cur.execute("""
        SELECT p.id, p.name, p.birth_year, p.death_year, p.role
        FROM persons p
        WHERE p.id IN (
            SELECT DISTINCT ep.person_id FROM event_persons ep WHERE ep.event_id = ANY(%s)
        )
        ORDER BY p.importance_score DESC NULLS LAST
        LIMIT 10
    """, (event_ids,))
    persons = cur.fetchall()

    # Location of parent event
    cur.execute("""
        SELECT l.id, l.name
        FROM events e
        JOIN locations l ON l.id = e.primary_location_id
        WHERE e.id = %s
    """, (parent_id,))
    location = cur.fetchone()

    # Existing narrative if available
    cur.execute("""
        SELECT narrative, significance
        FROM entity_narratives
        WHERE entity_type = 'event' AND entity_id = %s
        LIMIT 1
    """, (parent_id,))
    narrative = cur.fetchone()

    return {
        "children": children,
        "persons": persons,
        "location": location,
        "narrative": narrative,
    }


def build_cluster_prompt(parent, context):
    """Build LLM prompt for cluster (parent + children) essay."""
    pid, title, date_start, date_end, importance, description, child_count = parent
    children = context["children"]
    persons = context["persons"]
    location = context["location"]
    narrative = context["narrative"]

    # Build entity context
    lines = [
        f"# Parent Event: {title} (id={pid})",
        f"  Period: {format_year(date_start)} ~ {format_year(date_end)}",
        f"  Description: {description or 'None'}",
    ]

    if narrative:
        lines.append(f"  Existing narrative: {(narrative[0] or '')[:300]}")

    if location:
        lines.append(f"  Location: {location[1]} (id={location[0]})")

    lines.append(f"\n## Child Events ({len(children)}):")
    for c in children:
        desc_snippet = f" - {c[4][:80]}..." if c[4] else ""
        lines.append(f"  - {c[1]} (id={c[0]}, {format_year(c[2])}~{format_year(c[3])}){desc_snippet}")

    lines.append(f"\n## Key Persons ({len(persons)}):")
    for p in persons:
        lines.append(f"  - {p[1]} (id={p[0]}, {format_year(p[2])}~{format_year(p[3])}, role={p[4] or '?'})")

    lines.append("""
## Task
Write a 3-4 paragraph historical essay (300-500 words) about this event cluster.
Tag EVERY person/event/location using: [Name](entity:type:id)
Only use entity IDs from the context above. Do not invent new IDs.

Respond ONLY as valid JSON:
{
  "title": "Essay title in English",
  "title_ko": "Korean title",
  "summary": "1-2 sentence summary (no tags)",
  "body": "Full essay with [Name](entity:type:id) tags",
  "category": "essay or era_overview",
  "tags": ["tag1", "tag2", "tag3"],
  "featured_entity_ids": [
    {"type": "event", "id": <parent_event_id>},
    {"type": "person", "id": <most_important_person_id>}
  ]
}""")

    return "\n".join(lines)


# ═══════════════════════════════════════════
# Mode B: Person biography
# ═══════════════════════════════════════════

def fetch_important_persons(cur, limit=15):
    """Fetch high-importance persons with multiple events."""
    cur.execute("""
        SELECT p.id, p.name, p.birth_year, p.death_year, p.importance_score,
               p.description, p.role, p.domain,
               COUNT(ep.event_id) as event_count
        FROM persons p
        JOIN event_persons ep ON ep.person_id = p.id
        GROUP BY p.id HAVING COUNT(ep.event_id) >= 3
        ORDER BY p.importance_score DESC NULLS LAST
        LIMIT %s
    """, (limit,))
    return cur.fetchall()


def fetch_person_context(cur, person_id):
    """Get events, locations, and narratives for a person."""
    # Events
    cur.execute("""
        SELECT e.id, e.title, e.date_start, e.date_end, ed.description,
               l.id as loc_id, l.name as loc_name
        FROM event_persons ep
        JOIN events e ON e.id = ep.event_id
        LEFT JOIN event_details ed ON ed.event_id = e.id
        LEFT JOIN locations l ON l.id = e.primary_location_id
        WHERE ep.person_id = %s
        ORDER BY e.date_start NULLS LAST
        LIMIT 10
    """, (person_id,))
    events = cur.fetchall()

    # Existing narrative
    cur.execute("""
        SELECT narrative, significance
        FROM entity_narratives
        WHERE entity_type = 'person' AND entity_id = %s
        LIMIT 1
    """, (person_id,))
    narrative = cur.fetchone()

    return {
        "events": events,
        "narrative": narrative,
    }


def build_person_prompt(person, context):
    """Build LLM prompt for person biography."""
    pid, name, birth, death, imp, desc, role, domain, event_count = person
    events = context["events"]
    narrative = context["narrative"]

    lines = [
        f"# Person: {name} (id={pid})",
        f"  Life: {format_year(birth)} ~ {format_year(death)}",
        f"  Role: {role or 'Unknown'}, Domain: {domain or 'Unknown'}",
        f"  Description: {desc or 'None'}",
    ]

    if narrative:
        lines.append(f"  Existing narrative: {(narrative[0] or '')[:300]}")

    lines.append(f"\n## Key Events ({len(events)}):")
    for ev in events:
        loc_info = f", location: {ev[6]} (id={ev[5]})" if ev[5] else ""
        desc_snippet = f" - {ev[4][:80]}..." if ev[4] else ""
        lines.append(f"  - {ev[1]} (id={ev[0]}, {format_year(ev[2])}~{format_year(ev[3])}{loc_info}){desc_snippet}")

    lines.append("""
## Task
Write a 3-4 paragraph biography (300-500 words) about this historical figure.
Tag EVERY person/event/location using: [Name](entity:type:id)
Only use entity IDs from the context above. Do not invent new IDs.

Respond ONLY as valid JSON:
{
  "title": "Biography title in English",
  "title_ko": "Korean title",
  "summary": "1-2 sentence summary (no tags)",
  "body": "Full biography with [Name](entity:type:id) tags",
  "category": "biography",
  "tags": ["tag1", "tag2", "tag3"],
  "featured_entity_ids": [
    {"type": "person", "id": """ + str(pid) + """}
  ]
}""")

    return "\n".join(lines)


# ═══════════════════════════════════════════
# Insert History via API pattern
# ═══════════════════════════════════════════

def insert_history_to_db(cur, conn, result, mode):
    """Insert a generated history + entities into the database."""
    import re

    title = result.get("title", "Untitled")
    title_ko = result.get("title_ko")
    summary = result.get("summary")
    body = result.get("body", "")
    category = result.get("category", "essay")
    tags = result.get("tags", [])

    # Determine era from body context or tags
    era_start = result.get("era_start")
    era_end = result.get("era_end")

    cur.execute("""
        INSERT INTO histories (title, title_ko, summary, era_start, era_end, body,
                               category, tags, author_type, author_name, importance, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'system', 'gpt-5.1-auto', 4, 'published')
        RETURNING id
    """, (title, title_ko, summary, era_start, era_end, body, category, tags))
    history_id = cur.fetchone()[0]

    # Parse entity tags from body
    entity_pattern = re.compile(r'\[([^\]]+)\]\(entity:(person|event|location):(\d+)\)')
    seen = set()
    mentioned_entities = []
    for match in entity_pattern.finditer(body):
        etype = match.group(2)
        eid = int(match.group(3))
        ename = match.group(1)
        key = (etype, eid)
        if key not in seen:
            seen.add(key)
            mentioned_entities.append((etype, eid, ename))

    # Featured entities from LLM response
    featured_keys = set()
    for fe in result.get("featured_entity_ids", []):
        ftype = fe.get("type", "")
        fid = fe.get("id", 0)
        if ftype and fid:
            featured_keys.add((ftype, fid))

    # Insert history_entities
    for etype, eid, ename in mentioned_entities:
        role = "featured" if (etype, eid) in featured_keys else "mentioned"
        cur.execute("""
            INSERT INTO history_entities (history_id, entity_type, entity_id, entity_name, role)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (history_id, etype, eid, ename, role))

    # Add featured entities not in body mentions
    for ftype, fid in featured_keys:
        if (ftype, fid) not in seen:
            cur.execute("""
                INSERT INTO history_entities (history_id, entity_type, entity_id, entity_name, role)
                VALUES (%s, %s, %s, NULL, 'featured')
                ON CONFLICT DO NOTHING
            """, (history_id, ftype, fid))

    conn.commit()
    return history_id


# ═══════════════════════════════════════════
# Main Runners
# ═══════════════════════════════════════════

def run_cluster_mode(limit=20, dry_run=False, skip_existing=False):
    """Generate histories from parent event clusters."""
    print("\n" + "=" * 60)
    print("  Mode: CLUSTER (parent events with children)")
    print("=" * 60)

    conn = get_conn()
    cur = conn.cursor()

    clusters = fetch_clusters(cur, limit=limit * 2)  # fetch extra for filtering
    print(f"  Found {len(clusters)} aggregate events with >= 3 children")

    # Skip existing
    if skip_existing:
        cur.execute("""
            SELECT he.entity_id
            FROM history_entities he
            JOIN histories h ON h.id = he.history_id
            WHERE he.entity_type = 'event' AND he.role = 'featured'
              AND h.author_name = 'gpt-5.1-auto'
        """)
        existing_ids = {row[0] for row in cur.fetchall()}
        before = len(clusters)
        clusters = [c for c in clusters if c[0] not in existing_ids]
        print(f"  After skipping existing: {len(clusters)} (skipped {before - len(clusters)})")

    clusters = clusters[:limit]
    print(f"  Processing: {len(clusters)}")

    if dry_run:
        print("\n  [DRY RUN] Queries only, no LLM calls.")
        for c in clusters:
            ctx = fetch_cluster_context(cur, c[0])
            print(f"  - {c[1]} (id={c[0]}, children={c[6]}, persons={len(ctx['persons'])})")
        cur.close()
        conn.close()
        return

    # Load checkpoint
    done = load_checkpoint(CHECKPOINT_FILE)
    if done:
        print(f"  Resuming: {len(done)} already done")

    client = get_openai_client()
    total_calls = 0
    total_saved = 0

    for i, cluster in enumerate(clusters):
        parent_id = cluster[0]
        key = f"cluster:{parent_id}"
        if key in done:
            continue

        title = cluster[1]
        print(f"\n  [{i+1}/{len(clusters)}] {title} (id={parent_id}, children={cluster[6]})", flush=True)

        context = fetch_cluster_context(cur, parent_id)
        prompt = build_cluster_prompt(cluster, context)

        result = llm_call(client, SYSTEM_PROMPT, prompt, max_tokens=1200)
        total_calls += 1

        if result and result.get("body"):
            # Set era from parent event dates
            result["era_start"] = cluster[2]
            result["era_end"] = cluster[3]

            history_id = insert_history_to_db(cur, conn, result, "cluster")
            total_saved += 1
            print(f"    -> history_id={history_id}, body={len(result.get('body', ''))} chars")

            save_checkpoint(CHECKPOINT_FILE, {
                "_key": key,
                "history_id": history_id,
                "parent_event_id": parent_id,
                "title": result.get("title", ""),
                "body_len": len(result.get("body", "")),
                "timestamp": datetime.now().isoformat(),
            })
        else:
            print(f"    -> FAILED")
            save_checkpoint(CHECKPOINT_FILE, {
                "_key": key,
                "parent_event_id": parent_id,
                "failed": True,
                "timestamp": datetime.now().isoformat(),
            })

        time.sleep(LLM_DELAY)

    est_cost = total_calls * 0.01
    print(f"\n  === Cluster Mode Results ===")
    print(f"  LLM calls: {total_calls}")
    print(f"  Histories created: {total_saved}")
    print(f"  Estimated cost: ~${est_cost:.2f}")

    cur.close()
    conn.close()


def run_person_mode(limit=15, dry_run=False, skip_existing=False):
    """Generate biography histories for important persons."""
    print("\n" + "=" * 60)
    print("  Mode: PERSON (biography)")
    print("=" * 60)

    conn = get_conn()
    cur = conn.cursor()

    persons = fetch_important_persons(cur, limit=limit * 2)
    print(f"  Found {len(persons)} persons with >= 3 events")

    # Skip existing
    if skip_existing:
        cur.execute("""
            SELECT he.entity_id
            FROM history_entities he
            JOIN histories h ON h.id = he.history_id
            WHERE he.entity_type = 'person' AND he.role = 'featured'
              AND h.author_name = 'gpt-5.1-auto'
        """)
        existing_ids = {row[0] for row in cur.fetchall()}
        before = len(persons)
        persons = [p for p in persons if p[0] not in existing_ids]
        print(f"  After skipping existing: {len(persons)} (skipped {before - len(persons)})")

    persons = persons[:limit]
    print(f"  Processing: {len(persons)}")

    if dry_run:
        print("\n  [DRY RUN] Queries only, no LLM calls.")
        for p in persons:
            ctx = fetch_person_context(cur, p[0])
            print(f"  - {p[1]} (id={p[0]}, imp={p[4]}, events={p[8]})")
        cur.close()
        conn.close()
        return

    # Load checkpoint
    done = load_checkpoint(CHECKPOINT_FILE)
    if done:
        print(f"  Resuming: {len(done)} already done")

    client = get_openai_client()
    total_calls = 0
    total_saved = 0

    for i, person in enumerate(persons):
        person_id = person[0]
        key = f"person:{person_id}"
        if key in done:
            continue

        name = person[1]
        print(f"\n  [{i+1}/{len(persons)}] {name} (id={person_id}, imp={person[4]}, events={person[8]})", flush=True)

        context = fetch_person_context(cur, person_id)
        prompt = build_person_prompt(person, context)

        result = llm_call(client, SYSTEM_PROMPT, prompt, max_tokens=1200)
        total_calls += 1

        if result and result.get("body"):
            # Set era from birth/death
            result["era_start"] = person[2]
            result["era_end"] = person[3]

            history_id = insert_history_to_db(cur, conn, result, "person")
            total_saved += 1
            print(f"    -> history_id={history_id}, body={len(result.get('body', ''))} chars")

            save_checkpoint(CHECKPOINT_FILE, {
                "_key": key,
                "history_id": history_id,
                "person_id": person_id,
                "name": name,
                "title": result.get("title", ""),
                "body_len": len(result.get("body", "")),
                "timestamp": datetime.now().isoformat(),
            })
        else:
            print(f"    -> FAILED")
            save_checkpoint(CHECKPOINT_FILE, {
                "_key": key,
                "person_id": person_id,
                "failed": True,
                "timestamp": datetime.now().isoformat(),
            })

        time.sleep(LLM_DELAY)

    est_cost = total_calls * 0.01
    print(f"\n  === Person Mode Results ===")
    print(f"  LLM calls: {total_calls}")
    print(f"  Histories created: {total_saved}")
    print(f"  Estimated cost: ~${est_cost:.2f}")

    cur.close()
    conn.close()


# ═══════════════════════════════════════════
# Main
# ═══════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Generate histories via GPT-5.1 with entity tagging.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_histories.py --mode cluster --limit 3          # 3 cluster essays
  python generate_histories.py --mode person --limit 3           # 3 biographies
  python generate_histories.py --mode cluster --dry-run          # Preview only
  python generate_histories.py --mode person --limit 10 --skip-existing
        """
    )
    parser.add_argument("--mode", type=str, choices=["cluster", "person"], required=True,
                        help="Generation strategy: cluster (parent events) or person (biographies)")
    parser.add_argument("--limit", type=int, default=5,
                        help="Max histories to generate (default: 5)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview queries without LLM calls")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Skip entities that already have auto-generated histories")

    args = parser.parse_args()

    start_time = datetime.now()
    print(f"{'=' * 60}")
    print(f"  History Generator - GPT-5.1")
    print(f"  Mode: {args.mode}, Limit: {args.limit}")
    print(f"  Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}")

    if args.mode == "cluster":
        run_cluster_mode(limit=args.limit, dry_run=args.dry_run, skip_existing=args.skip_existing)
    elif args.mode == "person":
        run_person_mode(limit=args.limit, dry_run=args.dry_run, skip_existing=args.skip_existing)

    elapsed = datetime.now() - start_time
    print(f"\n{'=' * 60}")
    print(f"  Completed in {elapsed.total_seconds():.1f}s")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
