"""
LLM Curation Pipeline - GPT-5.1-chat-latest

Reads Wikipedia/Gutenberg source text from DB and generates rich narratives,
enhanced descriptions, and relationship explanations via LLM.

Steps:
  Step 0: Build source text cache from DB (no API calls)
  Step 1: Generate event narratives → entity_narratives + event_details
  Step 2: Enhance event relationship descriptions
  Step 3: Upgrade period narratives (llama → GPT-5.1)
  Step 4: Quality report
  Step 5: Generate person narratives → entity_narratives + persons.description

Usage:
    cd backend
    python ../poc/scripts/curate_with_llm.py --step 0
    python ../poc/scripts/curate_with_llm.py --step 1 --tier A --test 5
    python ../poc/scripts/curate_with_llm.py --step 1 --min-importance 2 --skip-existing
    python ../poc/scripts/curate_with_llm.py --step 1 --tier B
    python ../poc/scripts/curate_with_llm.py --step 1 --tier C
    python ../poc/scripts/curate_with_llm.py --step 2 --test 5 --skip-existing
    python ../poc/scripts/curate_with_llm.py --step 2
    python ../poc/scripts/curate_with_llm.py --step 3 --skip-existing
    python ../poc/scripts/curate_with_llm.py --step 4
    python ../poc/scripts/curate_with_llm.py --step 5 --min-importance 2 --skip-existing
    python ../poc/scripts/curate_with_llm.py --step 5 --tier A --test 5
    python ../poc/scripts/curate_with_llm.py --resume   # All steps, resume from checkpoint
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

SOURCE_CACHE_FILE = DATA_DIR / "source_cache.jsonl"
NARRATIVES_CHECKPOINT = DATA_DIR / "narratives_checkpoint.jsonl"
RELATIONSHIPS_CHECKPOINT = DATA_DIR / "relationships_checkpoint.jsonl"
PERIODS_CHECKPOINT = DATA_DIR / "periods_checkpoint.jsonl"
PERSON_NARRATIVES_CHECKPOINT = DATA_DIR / "person_narratives_checkpoint.jsonl"

# Tier thresholds (importance_score 0-100)
TIER_A_MIN = 90
TIER_B_MIN = 70
TIER_C_MIN = 50

# Smart truncation limits
MAX_SOURCE_FRONT = 8000   # First N chars
MAX_SOURCE_BACK = 2000    # Last N chars

# Rate limiting
LLM_DELAY = 0.3  # seconds between API calls


# ═══════════════════════════════════════════
# Helpers
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


def llm_call(client, system_prompt, user_prompt, max_tokens=800):
    """Single LLM call expecting JSON output."""
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            max_completion_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"    [ERROR] LLM call failed: {e}")
        return None


def smart_truncate(text, front=MAX_SOURCE_FRONT, back=MAX_SOURCE_BACK):
    """Smart truncation: keep front + back portions of long text."""
    if not text or len(text) <= front + back:
        return text
    return text[:front] + "\n\n[...truncated...]\n\n" + text[-back:]


def format_year(year):
    if year is None:
        return "Unknown"
    if year < 0:
        return f"{abs(year)} BCE"
    return f"{year} CE"


def load_checkpoint(filepath):
    """Load checkpoint file, return set of done keys."""
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
    """Append an entry to checkpoint JSONL file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def detect_importance_column(cur, table="events"):
    """Detect whether importance_score or importance column exists."""
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = %s AND column_name IN ('importance_score', 'importance')
        ORDER BY column_name DESC
    """, (table,))
    cols = [row[0] for row in cur.fetchall()]
    if 'importance_score' in cols:
        return 'importance_score'
    if 'importance' in cols:
        return 'importance'
    return None


# ═══════════════════════════════════════════
# Step 0: Source Text Cache
# ═══════════════════════════════════════════

def step0_source_cache():
    """Extract Wikipedia source text from DB for high-importance events."""
    print("\n" + "=" * 60)
    print("STEP 0: Build Source Text Cache")
    print("=" * 60)

    conn = get_conn()
    cur = conn.cursor()

    # Detect importance column
    imp_col = detect_importance_column(cur, "events")
    if not imp_col:
        print("  [ERROR] No importance column found on events table")
        cur.close()
        conn.close()
        return

    # Check if importance uses 1-5 or 0-100 scale
    cur.execute(f"SELECT MAX({imp_col}) FROM events")
    max_imp = cur.fetchone()[0]
    if max_imp and max_imp <= 5:
        # 1-5 scale: map tiers → A:5, B:4, C:3
        threshold = 3
        scale_info = "1-5 scale (threshold: >= 3)"
    else:
        threshold = TIER_C_MIN
        scale_info = f"0-100 scale (threshold: >= {TIER_C_MIN})"

    print(f"  Importance column: {imp_col} ({scale_info})")

    # Get events with their Wikipedia source text
    # Join through event_sources to sources to get content_raw
    cur.execute(f"""
        SELECT e.id, e.title, e.date_start, e.date_end,
               {imp_col} AS importance_score,
               ed.description,
               l.name AS location_name,
               s.id AS source_id, s.content_raw, s.url AS source_url
        FROM events e
        LEFT JOIN event_details ed ON ed.event_id = e.id
        LEFT JOIN locations l ON l.id = e.primary_location_id
        LEFT JOIN event_sources es ON es.event_id = e.id
        LEFT JOIN sources s ON s.id = es.source_id
            AND s.content_raw IS NOT NULL
            AND LENGTH(s.content_raw) > 100
        WHERE {imp_col} >= %s
        ORDER BY {imp_col} DESC, e.id
    """, (threshold,))

    rows = cur.fetchall()
    print(f"  Raw rows (event × source): {len(rows):,}")

    # Deduplicate: keep best source per event (longest content_raw)
    events = {}
    for row in rows:
        event_id = row[0]
        content_raw = row[8]
        content_len = len(content_raw) if content_raw else 0

        if event_id not in events or content_len > len(events[event_id].get("source_text", "") or ""):
            events[event_id] = {
                "event_id": event_id,
                "title": row[1],
                "date_start": row[2],
                "date_end": row[3],
                "importance_score": row[4],
                "description": row[5],
                "location_name": row[6],
                "source_id": row[7],
                "source_text": smart_truncate(content_raw) if content_raw else None,
                "source_url": row[9],
                "source_text_len": content_len,
            }

    # Get related persons for each event
    event_ids = list(events.keys())
    if event_ids:
        # Batch fetch persons
        cur.execute("""
            SELECT ep.event_id, p.name, p.role
            FROM event_persons ep
            JOIN persons p ON p.id = ep.person_id
            WHERE ep.event_id = ANY(%s)
            ORDER BY ep.event_id
        """, (event_ids,))

        persons_by_event = {}
        for row in cur.fetchall():
            eid = row[0]
            if eid not in persons_by_event:
                persons_by_event[eid] = []
            persons_by_event[eid].append({"name": row[1], "role": row[2]})

        for eid, plist in persons_by_event.items():
            if eid in events:
                events[eid]["persons"] = plist[:10]  # Max 10 persons

    # Count by tier
    tier_a = tier_b = tier_c = with_source = 0
    for ev in events.values():
        score = ev["importance_score"] or 0
        if max_imp and max_imp <= 5:
            if score >= 5: tier_a += 1
            elif score >= 4: tier_b += 1
            else: tier_c += 1
        else:
            if score >= TIER_A_MIN: tier_a += 1
            elif score >= TIER_B_MIN: tier_b += 1
            else: tier_c += 1
        if ev.get("source_text"):
            with_source += 1

    # Write cache
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SOURCE_CACHE_FILE, "w", encoding="utf-8") as f:
        for ev in sorted(events.values(), key=lambda x: -(x["importance_score"] or 0)):
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    print(f"\n  === Step 0 Results ===")
    print(f"  Events cached: {len(events):,}")
    print(f"    Tier A (>= {TIER_A_MIN if max_imp and max_imp > 5 else 5}): {tier_a:,}")
    print(f"    Tier B (>= {TIER_B_MIN if max_imp and max_imp > 5 else 4}): {tier_b:,}")
    print(f"    Tier C (>= {TIER_C_MIN if max_imp and max_imp > 5 else 3}): {tier_c:,}")
    print(f"  With Wikipedia source text: {with_source:,}")
    print(f"  Cache file: {SOURCE_CACHE_FILE}")

    cur.close()
    conn.close()
    return {"events": len(events), "with_source": with_source}


# ═══════════════════════════════════════════
# Step 1: Event Narrative Generation
# ═══════════════════════════════════════════

SYSTEM_PROMPT_NARRATIVE = (
    "You are a historical encyclopedia editor writing for an interactive historical atlas. "
    "Write clear, engaging, and factually accurate content in English only. "
    "No Korean, Japanese, Chinese or other non-English languages in any field. "
    "Always respond with valid JSON only."
)


def build_narrative_prompt_with_source(event):
    """Build prompt for events with source text (Wikipedia/Gutenberg)."""
    persons = event.get("persons", [])
    person_list = ", ".join(
        f"{p['name']} ({p.get('role', '?')})" for p in persons[:5]
    ) if persons else "None listed"

    source_text = event.get("source_text", "")
    # Truncate source to ~3000 chars for cost control
    if source_text and len(source_text) > 3000:
        source_text = source_text[:2500] + "\n\n[...truncated...]\n\n" + source_text[-500:]

    return f"""# Event: {event['title']} ({format_year(event.get('date_start'))} ~ {format_year(event.get('date_end'))})
# Location: {event.get('location_name') or 'Unknown'}
# Current description: {event.get('description') or 'None'}
# Related persons: {person_list}

## Source Material:
{source_text}

Based on the source material above, generate:
1. narrative: 150-250 word narrative explaining what happened, why it matters, and its historical context
2. significance: One sentence on global historical significance
3. causes: Array of 2-4 causes/preconditions (each 1 sentence)
4. consequences: Array of 2-4 consequences/effects (each 1 sentence)
5. description_enriched: 2-3 sentence enhanced description for the event card

IMPORTANT: Write in English only. No Korean, Japanese, or other languages.

Respond ONLY as valid JSON:
{{"narrative": "...", "significance": "...", "causes": ["..."], "consequences": ["..."], "description_enriched": "..."}}"""


def build_narrative_prompt_no_source(event):
    """Build prompt for Tier C events (no source text, use LLM knowledge)."""
    persons = event.get("persons", [])
    person_list = ", ".join(
        f"{p['name']} ({p.get('role', '?')})" for p in persons[:5]
    ) if persons else "None listed"

    return f"""# Event: {event['title']} ({format_year(event.get('date_start'))})
# Description: {event.get('description') or 'None'}
# Related persons: {person_list}

Using your historical knowledge, generate a brief narrative about this event.

Respond ONLY as valid JSON:
{{"narrative": "...", "significance": "...", "causes": ["..."], "consequences": ["..."]}}"""


def step1_narratives(tier="A", test_limit=None, resume=True, min_importance=None, skip_existing=False):
    """Generate event narratives and save to entity_narratives + event_details."""
    print("\n" + "=" * 60)
    label = f"Tier {tier}" if not min_importance else f"importance >= {min_importance}"
    print(f"STEP 1: Event Narrative Generation ({label})")
    print("=" * 60)

    # Load source cache
    if not SOURCE_CACHE_FILE.exists():
        print("  [ERROR] Source cache not found. Run --step 0 first.")
        return

    all_events = []
    for line in SOURCE_CACHE_FILE.read_text(encoding='utf-8').splitlines():
        if line.strip():
            all_events.append(json.loads(line))

    print(f"  Source cache: {len(all_events):,} events")

    # Detect scale from cache
    max_score = max((e.get("importance_score") or 0) for e in all_events) if all_events else 0
    use_small_scale = max_score <= 5

    # Filter by min_importance or tier
    if min_importance is not None:
        events = [e for e in all_events
                  if (e.get("importance_score") or 0) >= min_importance
                  and (e.get("importance_score") or 0) != -1]
    elif use_small_scale:
        if tier == "A":
            events = [e for e in all_events if (e.get("importance_score") or 0) >= 5]
        elif tier == "B":
            events = [e for e in all_events if 4 <= (e.get("importance_score") or 0) < 5]
        else:  # C
            events = [e for e in all_events if (e.get("importance_score") or 0) < 4]
    else:
        if tier == "A":
            events = [e for e in all_events if (e.get("importance_score") or 0) >= TIER_A_MIN]
        elif tier == "B":
            events = [e for e in all_events if TIER_B_MIN <= (e.get("importance_score") or 0) < TIER_A_MIN]
        else:  # C
            events = [e for e in all_events if TIER_C_MIN <= (e.get("importance_score") or 0) < TIER_B_MIN]

    print(f"  Filtered events: {len(events):,}")
    has_source = sum(1 for e in events if e.get("source_text"))
    print(f"  With source text: {has_source:,}")

    # Skip existing narratives if requested
    existing_ids = set()
    if skip_existing:
        conn_check = get_conn()
        cur_check = conn_check.cursor()
        cur_check.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'entity_narratives'
            )
        """)
        if cur_check.fetchone()[0]:
            cur_check.execute("SELECT entity_id FROM entity_narratives WHERE entity_type = 'event'")
            existing_ids = {row[0] for row in cur_check.fetchall()}
            events = [e for e in events if e["event_id"] not in existing_ids]
            print(f"  After skipping existing: {len(events):,} (skipped {len(existing_ids):,})")
        cur_check.close()
        conn_check.close()

    if test_limit:
        events = events[:test_limit]
        print(f"  [TEST] Limited to {len(events)} events")

    # Load checkpoint
    done = load_checkpoint(NARRATIVES_CHECKPOINT) if resume else set()
    if done:
        print(f"  Resuming: {len(done)} already done")

    # Connect
    client = get_openai_client()
    conn = get_conn()
    cur = conn.cursor()

    # Check if entity_narratives table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'entity_narratives'
        )
    """)
    has_entity_narratives = cur.fetchone()[0]
    if not has_entity_narratives:
        print("  [WARN] entity_narratives table does not exist. Will skip narrative inserts.")

    # Check if event_details table exists for description updates
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'event_details'
        )
    """)
    has_event_details = cur.fetchone()[0]

    total_calls = 0
    total_saved = 0
    total_desc_updated = 0

    for i, event in enumerate(events):
        eid = event["event_id"]
        key = f"narrative:{tier}:{eid}"

        if key in done:
            continue

        title = event.get("title", "?")
        score = event.get("importance_score", 0)
        print(f"  [{i+1}/{len(events)}] {title} (score: {score})", end="", flush=True)

        # Build prompt based on tier
        if tier in ("A", "B") and event.get("source_text"):
            prompt = build_narrative_prompt_with_source(event)
            max_tokens = 800
        else:
            prompt = build_narrative_prompt_no_source(event)
            max_tokens = 500

        result = llm_call(client, SYSTEM_PROMPT_NARRATIVE, prompt, max_tokens=max_tokens)
        total_calls += 1

        if result:
            # Save to DB: entity_narratives
            if has_entity_narratives:
                try:
                    cur.execute("""
                        INSERT INTO entity_narratives
                            (entity_type, entity_id, narrative, significance, causes, consequences,
                             model_used, source_url, curated_status)
                        VALUES ('event', %s, %s, %s, %s, %s, %s, %s, 'auto')
                        ON CONFLICT DO NOTHING
                    """, (
                        eid,
                        result.get("narrative"),
                        result.get("significance"),
                        result.get("causes"),
                        result.get("consequences"),
                        LLM_MODEL,
                        event.get("source_url"),
                    ))
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    print(f" [DB-ERR: {e}]", end="")

            # Update event_details.description if enriched
            enriched = result.get("description_enriched")
            if enriched and has_event_details:
                try:
                    cur.execute("""
                        UPDATE event_details
                        SET description = %s,
                            description_source = %s,
                            updated_at = NOW()
                        WHERE event_id = %s
                    """, (enriched, "gpt-5.1", eid))
                    if cur.rowcount > 0:
                        total_desc_updated += 1
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    print(f" [DESC-ERR: {e}]", end="")

            # Also try updating description on events table directly (archive DB schema)
            if enriched:
                try:
                    cur.execute("""
                        UPDATE events
                        SET description = %s,
                            description_model = %s,
                            description_at = NOW(),
                            updated_at = NOW()
                        WHERE id = %s AND (description IS NULL OR LENGTH(description) < %s)
                    """, (enriched, LLM_MODEL, eid, len(enriched)))
                    conn.commit()
                except Exception:
                    conn.rollback()

            # Save checkpoint
            save_checkpoint(NARRATIVES_CHECKPOINT, {
                "_key": key,
                "event_id": eid,
                "tier": tier,
                "title": title,
                "narrative_len": len(result.get("narrative", "")),
                "has_enriched_desc": bool(enriched),
                "timestamp": datetime.now().isoformat(),
            })
            total_saved += 1
            print(f" -> OK ({len(result.get('narrative', ''))} chars)")
        else:
            print(f" -> FAILED")

        time.sleep(LLM_DELAY)

    # Summary
    est_cost_per_call = 0.008 if tier in ("A", "B") else 0.004
    est_cost = total_calls * est_cost_per_call
    print(f"\n  === Step 1 Tier {tier} Results ===")
    print(f"  LLM calls: {total_calls}")
    print(f"  Narratives saved: {total_saved}")
    print(f"  Descriptions updated: {total_desc_updated}")
    print(f"  Estimated cost: ~${est_cost:.2f}")

    cur.close()
    conn.close()
    return {"calls": total_calls, "saved": total_saved, "cost": est_cost}


# ═══════════════════════════════════════════
# Step 2: Event Relationship Enhancement
# ═══════════════════════════════════════════

SYSTEM_PROMPT_RELATIONSHIP = (
    "You are a world history expert analyzing causal relationships between events. "
    "Write precise, scholarly, factually grounded explanations. "
    "Always respond with valid JSON only."
)


def step2_relationships(test_limit=None, resume=True):
    """Enhance event_relationships descriptions with historical context."""
    print("\n" + "=" * 60)
    print("STEP 2: Event Relationship Description Enhancement")
    print("=" * 60)

    conn = get_conn()
    cur = conn.cursor()

    # Detect importance column
    imp_col = detect_importance_column(cur, "events")
    if not imp_col:
        print("  [ERROR] No importance column found")
        cur.close()
        conn.close()
        return

    # Check scale
    cur.execute(f"SELECT MAX({imp_col}) FROM events")
    max_imp = cur.fetchone()[0]
    if max_imp and max_imp <= 5:
        threshold = 4  # 1-5 scale: >= 4
    else:
        threshold = TIER_B_MIN  # 0-100 scale: >= 70

    # Get relationships where both events are high-importance
    cur.execute(f"""
        SELECT er.id, er.from_event_id, er.to_event_id,
               er.relationship_type, er.description AS current_desc,
               e1.title AS from_title, e1.date_start AS from_date,
               e2.title AS to_title, e2.date_start AS to_date
        FROM event_relationships er
        JOIN events e1 ON e1.id = er.from_event_id
        JOIN events e2 ON e2.id = er.to_event_id
        WHERE er.relationship_type IN ('follows', 'causes')
          AND e1.{imp_col} >= %s
          AND e2.{imp_col} >= %s
        ORDER BY GREATEST(e1.{imp_col}, e2.{imp_col}) DESC
    """, (threshold, threshold))

    relationships = cur.fetchall()
    print(f"  High-importance relationships: {len(relationships):,}")

    if test_limit:
        relationships = relationships[:test_limit]
        print(f"  [TEST] Limited to {len(relationships)}")

    # Load checkpoint
    done = load_checkpoint(RELATIONSHIPS_CHECKPOINT) if resume else set()
    if done:
        print(f"  Resuming: {len(done)} already done")

    client = get_openai_client()
    total_calls = 0
    total_updated = 0

    for i, rel in enumerate(relationships):
        rel_id, from_id, to_id, rel_type, current_desc = rel[0], rel[1], rel[2], rel[3], rel[4]
        from_title, from_date, to_title, to_date = rel[5], rel[6], rel[7], rel[8]

        key = f"rel:{rel_id}"
        if key in done:
            continue

        print(f"  [{i+1}/{len(relationships)}] {from_title} → {to_title} ({rel_type})", end="", flush=True)

        prompt = f"""Event A: {from_title} ({format_year(from_date)})
Event B: {to_title} ({format_year(to_date)})
Relationship type: {rel_type}
Current description: {current_desc or 'None'}

Write a 1-2 sentence historical explanation of how Event A led to or caused Event B.
Also rate the causal strength (1-5, where 5 is direct causation) and certainty (certain/probable/possible).

Respond ONLY as valid JSON:
{{"description": "...", "strength": 3, "certainty": "probable"}}"""

        result = llm_call(client, SYSTEM_PROMPT_RELATIONSHIP, prompt, max_tokens=200)
        total_calls += 1

        if result:
            try:
                cur.execute("""
                    UPDATE event_relationships
                    SET description = %s,
                        strength = %s,
                        certainty = %s
                    WHERE id = %s
                """, (
                    result.get("description"),
                    result.get("strength", 3),
                    result.get("certainty", "probable"),
                    rel_id,
                ))
                conn.commit()
                total_updated += 1
                print(f" -> OK")
            except Exception as e:
                conn.rollback()
                print(f" -> DB-ERR: {e}")
        else:
            print(f" -> FAILED")

        save_checkpoint(RELATIONSHIPS_CHECKPOINT, {
            "_key": key,
            "rel_id": rel_id,
            "from_title": from_title,
            "to_title": to_title,
            "success": result is not None,
            "timestamp": datetime.now().isoformat(),
        })

        time.sleep(LLM_DELAY)

    est_cost = total_calls * 0.002
    print(f"\n  === Step 2 Results ===")
    print(f"  LLM calls: {total_calls}")
    print(f"  Relationships updated: {total_updated}")
    print(f"  Estimated cost: ~${est_cost:.2f}")

    cur.close()
    conn.close()
    return {"calls": total_calls, "updated": total_updated, "cost": est_cost}


# ═══════════════════════════════════════════
# Step 3: Period Narratives Upgrade
# ═══════════════════════════════════════════

SYSTEM_PROMPT_PERIOD = (
    "You are a world history expert writing narrative overviews for 50-year historical periods. "
    "Write engaging, insightful content that connects events to broader historical patterns. "
    "Always respond with valid JSON only."
)


def step3_period_narratives(test_limit=None, resume=True):
    """Upgrade llama-generated period narratives to GPT-5.1 quality."""
    print("\n" + "=" * 60)
    print("STEP 3: Period Narrative Upgrade")
    print("=" * 60)

    conn = get_conn()
    cur = conn.cursor()

    # Check if table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'period_narratives'
        )
    """)
    if not cur.fetchone()[0]:
        print("  [ERROR] period_narratives table does not exist")
        cur.close()
        conn.close()
        return

    # Get llama-generated narratives
    cur.execute("""
        SELECT id, period_start, period_end, region, era_id,
               headline, narrative, model_used
        FROM period_narratives
        WHERE model_used LIKE '%llama%'
           OR model_used IS NULL
           OR LENGTH(narrative) < 100
        ORDER BY period_start, region NULLS FIRST
    """)
    narratives = cur.fetchall()
    print(f"  Low-quality narratives to upgrade: {len(narratives):,}")

    if test_limit:
        narratives = narratives[:test_limit]
        print(f"  [TEST] Limited to {len(narratives)}")

    # Load checkpoint
    done = load_checkpoint(PERIODS_CHECKPOINT) if resume else set()
    if done:
        print(f"  Resuming: {len(done)} already done")

    # Get event/person context per period
    imp_col = detect_importance_column(cur, "events") or "importance"

    client = get_openai_client()
    total_calls = 0
    total_updated = 0

    for i, row in enumerate(narratives):
        pn_id, ps, pe, region, era_id, headline, narrative, model_used = row

        key = f"period:{pn_id}"
        if key in done:
            continue

        region_display = region or "Global"
        print(f"  [{i+1}/{len(narratives)}] {format_year(ps)}~{format_year(pe)} ({region_display})", end="", flush=True)

        # Get top events and persons for this period
        if region:
            # Regional: we need location-based filtering, but simplify for now
            cur.execute(f"""
                SELECT e.title, e.date_start, {imp_col} AS score
                FROM events e
                WHERE e.date_start >= %s AND e.date_start <= %s
                  AND {imp_col} >= 3
                ORDER BY {imp_col} DESC
                LIMIT 5
            """, (ps, pe))
        else:
            cur.execute(f"""
                SELECT e.title, e.date_start, {imp_col} AS score
                FROM events e
                WHERE e.date_start >= %s AND e.date_start <= %s
                ORDER BY {imp_col} DESC NULLS LAST
                LIMIT 5
            """, (ps, pe))

        top_events = cur.fetchall()
        event_lines = "\n".join(
            f"  - {t[0]} ({format_year(t[1])}, score: {t[2]})"
            for t in top_events
        ) if top_events else "  (none)"

        prompt = f"""Period: {format_year(ps)} to {format_year(pe)}
Region: {region_display}
Era: {era_id or 'Unknown'}

Top events in this period:
{event_lines}

Previous headline: {headline or 'None'}
Previous narrative (low quality): {(narrative or '')[:200]}...

Write an improved narrative for this period (200-300 words) that:
1. Explains the major developments and themes
2. Connects events to broader historical patterns
3. Highlights what makes this period significant
4. Mentions key transitions (what changed, what led to the next era)

Also provide:
- A headline (max 80 chars) capturing the defining theme
- 2-4 keywords
- A defining moment (one sentence)

Respond ONLY as valid JSON:
{{"headline": "...", "narrative": "...", "keywords": ["..."], "defining_moment": "..."}}"""

        result = llm_call(client, SYSTEM_PROMPT_PERIOD, prompt, max_tokens=600)
        total_calls += 1

        if result:
            try:
                cur.execute("""
                    UPDATE period_narratives
                    SET headline = %s,
                        narrative = %s,
                        keywords = %s,
                        defining_moment = %s,
                        model_used = %s,
                        generated_at = NOW(),
                        updated_at = NOW()
                    WHERE id = %s
                """, (
                    result.get("headline"),
                    result.get("narrative"),
                    result.get("keywords"),
                    result.get("defining_moment"),
                    LLM_MODEL,
                    pn_id,
                ))
                conn.commit()
                total_updated += 1
                print(f" -> OK ({result.get('headline', '?')[:50]})")
            except Exception as e:
                conn.rollback()
                print(f" -> DB-ERR: {e}")
        else:
            print(f" -> FAILED")

        save_checkpoint(PERIODS_CHECKPOINT, {
            "_key": key,
            "pn_id": pn_id,
            "period_start": ps,
            "period_end": pe,
            "region": region,
            "success": result is not None,
            "timestamp": datetime.now().isoformat(),
        })

        time.sleep(LLM_DELAY)

    est_cost = total_calls * 0.006
    print(f"\n  === Step 3 Results ===")
    print(f"  LLM calls: {total_calls}")
    print(f"  Narratives upgraded: {total_updated}")
    print(f"  Estimated cost: ~${est_cost:.2f}")

    cur.close()
    conn.close()
    return {"calls": total_calls, "updated": total_updated, "cost": est_cost}


# ═══════════════════════════════════════════
# Step 5: Person Narrative Generation
# ═══════════════════════════════════════════

SYSTEM_PROMPT_PERSON = (
    "You are a historical encyclopedia editor writing biographical narratives for an interactive historical atlas. "
    "Write clear, engaging, and factually accurate content about historical figures in English only. "
    "No Korean, Japanese, Chinese or other non-English languages in any field. "
    "Always respond with valid JSON only."
)


def step5_person_narratives(tier="A", test_limit=None, resume=True, min_importance=None, skip_existing=False):
    """Generate person narratives from Wikipedia/Gutenberg sources and save to entity_narratives + persons."""
    print("\n" + "=" * 60)
    label = f"Tier {tier}" if not min_importance else f"importance >= {min_importance}"
    print(f"STEP 5: Person Narrative Generation ({label})")
    print("=" * 60)

    conn = get_conn()
    cur = conn.cursor()

    # Detect importance column for persons
    imp_col = detect_importance_column(cur, "persons")
    if not imp_col:
        print("  [ERROR] No importance column found on persons table")
        cur.close()
        conn.close()
        return

    # Check scale
    cur.execute(f"SELECT MAX({imp_col}) FROM persons")
    max_imp = cur.fetchone()[0]
    use_small_scale = max_imp and max_imp <= 5

    # Set thresholds based on --min-importance or --tier
    if min_importance is not None:
        t_min = min_importance
        t_max = 999999
    else:
        if use_small_scale:
            tier_ranges = {"A": (5, 999), "B": (4, 5), "C": (3, 4)}
        else:
            tier_ranges = {"A": (TIER_A_MIN, 999), "B": (TIER_B_MIN, TIER_A_MIN), "C": (TIER_C_MIN, TIER_B_MIN)}
        t_min, t_max = tier_ranges.get(tier, (TIER_A_MIN, 999))

    # Get persons with their best source (Wikipedia or Gutenberg)
    cur.execute(f"""
        SELECT p.id, p.name, p.name_ko, p.birth_year, p.death_year,
               p.description, p.role, p.domain, p.{imp_col} AS importance_score,
               s.content_raw, s.url AS source_url
        FROM persons p
        LEFT JOIN LATERAL (
            SELECT s2.content_raw, s2.url
            FROM person_sources ps
            JOIN sources s2 ON s2.id = ps.source_id
            WHERE ps.person_id = p.id
              AND s2.content_raw IS NOT NULL
              AND LENGTH(s2.content_raw) > 100
            ORDER BY LENGTH(s2.content_raw) DESC
            LIMIT 1
        ) s ON TRUE
        WHERE p.{imp_col} >= %s AND p.{imp_col} < %s
          AND p.{imp_col} != -1
        ORDER BY p.{imp_col} DESC, p.id
    """, (t_min, t_max))

    persons = cur.fetchall()
    total_persons = len(persons)
    with_source = sum(1 for p in persons if p[9])

    print(f"  Filtered persons: {total_persons:,}")
    print(f"  With source text: {with_source:,}")

    # Skip existing narratives if requested
    if skip_existing:
        cur.execute("SELECT entity_id FROM entity_narratives WHERE entity_type = 'person'")
        existing_ids = {row[0] for row in cur.fetchall()}
        before = len(persons)
        persons = [p for p in persons if p[0] not in existing_ids]
        print(f"  After skipping existing: {len(persons):,} (skipped {before - len(persons):,})")

    if test_limit:
        persons = persons[:test_limit]
        print(f"  [TEST] Limited to {len(persons)} persons")

    # Load checkpoint
    done = load_checkpoint(PERSON_NARRATIVES_CHECKPOINT) if resume else set()
    if done:
        print(f"  Resuming: {len(done)} already done")

    # Check entity_narratives table
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'entity_narratives'
        )
    """)
    has_entity_narratives = cur.fetchone()[0]
    if not has_entity_narratives:
        print("  [WARN] entity_narratives table does not exist. Will skip narrative inserts.")

    client = get_openai_client()
    total_calls = 0
    total_saved = 0
    total_desc_updated = 0

    for i, row in enumerate(persons):
        pid, name, name_ko, birth, death, desc, role, domain, score = row[:9]
        content_raw, source_url = row[9], row[10]

        key = f"person:{tier}:{pid}"
        if key in done:
            continue

        print(f"  [{i+1}/{len(persons)}] {name} (score: {score})", end="", flush=True)

        # Get related events for context
        cur.execute("""
            SELECT e.title, e.date_start
            FROM event_persons ep
            JOIN events e ON e.id = ep.event_id
            WHERE ep.person_id = %s
            ORDER BY e.date_start
            LIMIT 8
        """, (pid,))
        events = cur.fetchall()
        event_list = ", ".join(f"{e[0]} ({format_year(e[1])})" for e in events) if events else "None listed"

        # Build prompt
        life_span = ""
        if birth is not None:
            life_span = f"{format_year(birth)}"
            if death is not None:
                life_span += f" – {format_year(death)}"

        if content_raw:
            # Truncate to ~3000 chars for cost control
            source_text = content_raw[:2500] + "\n[...truncated...]\n" + content_raw[-500:] if len(content_raw) > 3000 else content_raw
            prompt = f"""# Person: {name} ({life_span})
# Role: {role or 'Unknown'}
# Domain: {domain or 'Unknown'}
# Current description: {desc or 'None'}
# Key events: {event_list}

## Source Material:
{source_text}

Based on the source material above, generate:
1. narrative: 200-300 word biographical narrative covering their life, achievements, and historical impact
2. significance: One sentence on their global historical significance
3. key_achievements: Array of 3-5 key achievements or contributions (each 1 sentence)
4. description_enriched: 2-3 sentence enhanced biography for the person card

IMPORTANT: Write in English only. No Korean, Japanese, or other languages.

Respond ONLY as valid JSON:
{{"narrative": "...", "significance": "...", "key_achievements": ["..."], "description_enriched": "..."}}"""
            max_tokens = 800
        else:
            prompt = f"""# Person: {name} ({life_span})
# Role: {role or 'Unknown'}
# Domain: {domain or 'Unknown'}
# Current description: {desc or 'None'}
# Key events: {event_list}

Using your historical knowledge, generate a brief biographical narrative.
IMPORTANT: Write in English only. No Korean, Japanese, or other languages.

Respond ONLY as valid JSON:
{{"narrative": "...", "significance": "...", "key_achievements": ["..."], "description_enriched": "..."}}"""
            max_tokens = 600

        result = llm_call(client, SYSTEM_PROMPT_PERSON, prompt, max_tokens=max_tokens)
        total_calls += 1

        if result:
            # Save to entity_narratives
            if has_entity_narratives:
                try:
                    cur.execute("""
                        INSERT INTO entity_narratives
                            (entity_type, entity_id, narrative, significance, causes, consequences,
                             model_used, source_url, curated_status)
                        VALUES ('person', %s, %s, %s, %s, %s, %s, %s, 'auto')
                        ON CONFLICT DO NOTHING
                    """, (
                        pid,
                        result.get("narrative"),
                        result.get("significance"),
                        result.get("key_achievements"),  # stored in causes array
                        None,  # no consequences for persons
                        LLM_MODEL,
                        source_url,
                    ))
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    print(f" [DB-ERR: {e}]", end="")

            # Update persons.description if enriched
            enriched = result.get("description_enriched")
            if enriched:
                try:
                    cur.execute("""
                        UPDATE persons
                        SET description = %s,
                            description_model = %s,
                            description_at = NOW(),
                            updated_at = NOW()
                        WHERE id = %s AND (description IS NULL OR LENGTH(description) < %s)
                    """, (enriched, LLM_MODEL, pid, len(enriched)))
                    if cur.rowcount > 0:
                        total_desc_updated += 1
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    print(f" [DESC-ERR: {e}]", end="")

            # Save checkpoint
            save_checkpoint(PERSON_NARRATIVES_CHECKPOINT, {
                "_key": key,
                "person_id": pid,
                "tier": tier,
                "name": name,
                "narrative_len": len(result.get("narrative", "")),
                "has_enriched_desc": bool(enriched),
                "had_source": bool(content_raw),
                "timestamp": datetime.now().isoformat(),
            })
            total_saved += 1
            print(f" -> OK ({len(result.get('narrative', ''))} chars)")
        else:
            print(f" -> FAILED")

        time.sleep(LLM_DELAY)

    # Summary
    est_cost_per_call = 0.008 if tier in ("A", "B") else 0.004
    est_cost = total_calls * est_cost_per_call
    print(f"\n  === Step 5 Tier {tier} Results ===")
    print(f"  LLM calls: {total_calls}")
    print(f"  Person narratives saved: {total_saved}")
    print(f"  Descriptions updated: {total_desc_updated}")
    print(f"  Estimated cost: ~${est_cost:.2f}")

    cur.close()
    conn.close()
    return {"calls": total_calls, "saved": total_saved, "cost": est_cost}


# ═══════════════════════════════════════════
# Step 4: Quality Report
# ═══════════════════════════════════════════

def step4_report():
    """Generate quality report of all curation work."""
    print("\n" + "=" * 60)
    print("STEP 4: LLM Curation Quality Report")
    print("=" * 60)

    conn = get_conn()
    cur = conn.cursor()

    # --- entity_narratives ---
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'entity_narratives'
        )
    """)
    has_en = cur.fetchone()[0]

    if has_en:
        cur.execute("""
            SELECT entity_type, COUNT(*), AVG(LENGTH(narrative))::int
            FROM entity_narratives
            GROUP BY entity_type
        """)
        en_stats = cur.fetchall()

        cur.execute("""
            SELECT model_used, COUNT(*)
            FROM entity_narratives
            GROUP BY model_used
            ORDER BY COUNT(*) DESC
        """)
        en_models = cur.fetchall()
    else:
        en_stats = []
        en_models = []

    # --- event descriptions ---
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'event_details'
        )
    """)
    has_ed = cur.fetchone()[0]

    if has_ed:
        cur.execute("""
            SELECT description_source, COUNT(*), AVG(LENGTH(description))::int
            FROM event_details
            WHERE description IS NOT NULL
            GROUP BY description_source
            ORDER BY COUNT(*) DESC
        """)
        ed_stats = cur.fetchall()
    else:
        ed_stats = []

    # --- event_relationships ---
    cur.execute("SELECT COUNT(*) FROM event_relationships")
    total_rels = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM event_relationships WHERE LENGTH(description) > 100")
    enriched_rels = cur.fetchone()[0]

    cur.execute("""
        SELECT certainty, COUNT(*)
        FROM event_relationships
        WHERE certainty IS NOT NULL
        GROUP BY certainty
        ORDER BY COUNT(*) DESC
    """)
    rel_certainty = cur.fetchall()

    # --- period_narratives ---
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'period_narratives'
        )
    """)
    has_pn = cur.fetchone()[0]

    if has_pn:
        cur.execute("""
            SELECT model_used, COUNT(*), AVG(LENGTH(narrative))::int
            FROM period_narratives
            GROUP BY model_used
            ORDER BY COUNT(*) DESC
        """)
        pn_stats = cur.fetchall()
    else:
        pn_stats = []

    # --- Checkpoint stats ---
    narr_count = 0
    if NARRATIVES_CHECKPOINT.exists():
        narr_count = sum(1 for line in NARRATIVES_CHECKPOINT.read_text(encoding='utf-8').splitlines() if line.strip())

    rel_count = 0
    if RELATIONSHIPS_CHECKPOINT.exists():
        rel_count = sum(1 for line in RELATIONSHIPS_CHECKPOINT.read_text(encoding='utf-8').splitlines() if line.strip())

    period_count = 0
    if PERIODS_CHECKPOINT.exists():
        period_count = sum(1 for line in PERIODS_CHECKPOINT.read_text(encoding='utf-8').splitlines() if line.strip())

    person_narr_count = 0
    if PERSON_NARRATIVES_CHECKPOINT.exists():
        person_narr_count = sum(1 for line in PERSON_NARRATIVES_CHECKPOINT.read_text(encoding='utf-8').splitlines() if line.strip())

    total_llm_calls = narr_count + rel_count + period_count + person_narr_count

    # --- Print Report ---
    print(f"""
  ╔══════════════════════════════════════════════════╗
  ║         LLM Curation Quality Report              ║
  ╚══════════════════════════════════════════════════╝

  === Entity Narratives ===
  By type:""")
    if en_stats:
        for etype, cnt, avg_len in en_stats:
            print(f"    {etype}: {cnt:,} (avg {avg_len or 0} chars)")
    else:
        print("    (no data or table missing)")

    print(f"  By model:")
    if en_models:
        for model, cnt in en_models:
            print(f"    {model}: {cnt:,}")
    else:
        print("    (no data)")

    print(f"""
  === Event Descriptions ===
  By source:""")
    if ed_stats:
        for source, cnt, avg_len in ed_stats:
            print(f"    {source or 'null'}: {cnt:,} (avg {avg_len or 0} chars)")
    else:
        print("    (no data or table missing)")

    print(f"""
  === Event Relationships ===
  Total: {total_rels:,}
  With rich description (>100 chars): {enriched_rels:,}
  By certainty:""")
    for cert, cnt in rel_certainty:
        print(f"    {cert}: {cnt:,}")

    print(f"""
  === Period Narratives ===
  By model:""")
    if pn_stats:
        for model, cnt, avg_len in pn_stats:
            print(f"    {model or 'null'}: {cnt:,} (avg {avg_len or 0} chars)")
    else:
        print("    (no data or table missing)")

    print(f"""
  === Pipeline Stats ===
  Checkpoint entries:
    Event narratives (Step 1): {narr_count:,}
    Relationships (Step 2): {rel_count:,}
    Period upgrades (Step 3): {period_count:,}
    Person narratives (Step 5): {person_narr_count:,}
  Total LLM calls: {total_llm_calls:,}
  Estimated total cost: ~${total_llm_calls * 0.005:.2f}
""")

    cur.close()
    conn.close()


# ═══════════════════════════════════════════
# Main
# ═══════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="LLM Curation Pipeline (GPT-5.1-chat-latest)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python curate_with_llm.py --step 0                              # Build source cache
  python curate_with_llm.py --step 1 --tier A --test 5            # Test 5 Tier A narratives
  python curate_with_llm.py --step 1 --min-importance 2 --skip-existing  # importance >= 2, skip done
  python curate_with_llm.py --step 1 --tier B                     # Full Tier B
  python curate_with_llm.py --step 2 --test 5 --skip-existing     # Test 5 relationships
  python curate_with_llm.py --step 2                              # Full relationship enhancement
  python curate_with_llm.py --step 3 --skip-existing              # Upgrade period narratives
  python curate_with_llm.py --step 4                              # Quality report
  python curate_with_llm.py --step 5 --min-importance 2 --skip-existing  # Person narratives
  python curate_with_llm.py --step 5 --tier A --test 5            # Test 5 person narratives
  python curate_with_llm.py --resume                              # All steps (resume)
        """
    )
    parser.add_argument("--step", type=int, choices=[0, 1, 2, 3, 4, 5],
                        help="Run specific step only")
    parser.add_argument("--tier", type=str, choices=["A", "B", "C"], default="A",
                        help="Tier for Step 1/5 (default: A)")
    parser.add_argument("--min-importance", type=int, default=None,
                        help="Minimum importance score filter (overrides --tier)")
    parser.add_argument("--skip-existing", action="store_true", default=False,
                        help="Skip entities that already have narratives in entity_narratives")
    parser.add_argument("--test", type=int, help="Test with N items only")
    parser.add_argument("--resume", action="store_true", default=False,
                        help="Run all steps, resuming from checkpoints")
    parser.add_argument("--no-resume", action="store_true",
                        help="Start fresh (ignore checkpoints)")
    args = parser.parse_args()

    start_time = datetime.now()
    resume = not args.no_resume

    print(f"╔{'═' * 58}╗")
    print(f"║  LLM Curation Pipeline - GPT-5.1-chat-latest             ║")
    print(f"║  Started: {start_time.strftime('%Y-%m-%d %H:%M:%S'):<46} ║")
    if args.min_importance:
        print(f"║  Min importance: {args.min_importance:<41} ║")
    if args.skip_existing:
        print(f"║  Skip existing: YES{' ' * 38}║")
    print(f"╚{'═' * 58}╝")

    if args.step is not None:
        if args.step == 0:
            step0_source_cache()
        elif args.step == 1:
            step1_narratives(tier=args.tier, test_limit=args.test, resume=resume,
                             min_importance=args.min_importance, skip_existing=args.skip_existing)
        elif args.step == 2:
            step2_relationships(test_limit=args.test, resume=resume)
        elif args.step == 3:
            step3_period_narratives(test_limit=args.test, resume=resume)
        elif args.step == 4:
            step4_report()
        elif args.step == 5:
            step5_person_narratives(tier=args.tier, test_limit=args.test, resume=resume,
                                    min_importance=args.min_importance, skip_existing=args.skip_existing)
    elif args.resume:
        print("\n  Running all steps with resume...")
        step0_source_cache()
        step1_narratives(tier="A", resume=True, skip_existing=args.skip_existing)
        step1_narratives(tier="B", resume=True, skip_existing=args.skip_existing)
        step2_relationships(resume=True)
        step3_period_narratives(resume=True)
        step5_person_narratives(tier="A", resume=True, skip_existing=args.skip_existing)
        step5_person_narratives(tier="B", resume=True, skip_existing=args.skip_existing)
        step4_report()
    else:
        print("\n  Specify --step N or --resume. Use --help for options.")

    elapsed = datetime.now() - start_time
    print(f"\n{'=' * 60}")
    print(f"  Completed in {elapsed.total_seconds():.1f}s")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
