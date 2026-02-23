"""
Seed Test Histories - Insert hardcoded sample histories for system verification.

Inserts 3 sample histories using real entity IDs from the compact DB,
with [Name](entity:type:id) body tagging. No LLM calls.

Usage:
    cd backend
    python ../poc/scripts/seed_test_histories.py
    python ../poc/scripts/seed_test_histories.py --clean   # Delete seeded histories first
"""

import argparse
import sys

import psycopg2

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_URL = "postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas"


def get_conn():
    return psycopg2.connect(DB_URL)


def clean_seeded(conn):
    """Delete previously seeded test histories."""
    cur = conn.cursor()
    cur.execute("DELETE FROM histories WHERE author_name = 'seed_test'")
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    print(f"  Cleaned {deleted} seeded histories.")
    return deleted


def lookup_entities(cur):
    """Look up real entity IDs from the database."""
    entities = {}

    # Key persons
    person_names = [
        'Julius Caesar', 'Napoleon', 'Genghis Khan', 'Abraham Lincoln',
        'Muhammad', 'Aristotle', 'Adolf Hitler', 'Alexander the Great',
    ]
    cur.execute("""
        SELECT id, name, birth_year, death_year
        FROM persons
        WHERE name = ANY(%s)
        ORDER BY importance_score DESC NULLS LAST
    """, (person_names,))
    for row in cur.fetchall():
        entities[f"person:{row[1]}"] = {
            "id": row[0], "name": row[1],
            "birth_year": row[2], "death_year": row[3],
        }

    # Key events
    event_titles = [
        'assassination of Julius Caesar',
        'Battle of Alesia',
        "Caesar's Civil War",
        'crossing the Rubicon',
        'Gallic War',
        'American Civil War',
        'Napoleonic Wars',
        'Mongol conquest of the Jin dynasty',
        'Battle of Indus',
    ]
    cur.execute("""
        SELECT id, title, date_start, date_end
        FROM events
        WHERE title = ANY(%s)
    """, (event_titles,))
    for row in cur.fetchall():
        entities[f"event:{row[1]}"] = {
            "id": row[0], "title": row[1],
            "date_start": row[2], "date_end": row[3],
        }

    # Key locations
    location_names = ['France', 'Japan', 'United States', 'Spain']
    cur.execute("""
        SELECT id, name, latitude, longitude
        FROM locations
        WHERE name = ANY(%s)
        LIMIT 10
    """, (location_names,))
    for row in cur.fetchall():
        entities[f"location:{row[1]}"] = {
            "id": row[0], "name": row[1],
        }

    return entities


def e(entities, key):
    """Get entity, return placeholder if missing."""
    ent = entities.get(key)
    if not ent:
        return None
    return ent


def tag(entities, key):
    """Build [Name](entity:type:id) tag from entity key."""
    ent = entities.get(key)
    if not ent:
        return f"[{key}](entity:person:0)"
    etype = key.split(":")[0]
    name = ent.get("name") or ent.get("title")
    return f"[{name}](entity:{etype}:{ent['id']})"


SEED_HISTORIES = [
    {
        "title": "The Fall of the Roman Republic: Caesar's Final Act",
        "title_ko": "로마 공화정의 몰락: 카이사르의 마지막 막",
        "summary": "How Julius Caesar's crossing of the Rubicon and subsequent civil war led to the end of the Roman Republic.",
        "category": "essay",
        "tags": ["rome", "republic", "civil-war", "ancient"],
        "importance": 5,
        "era_start": -52,
        "era_end": -44,
        "body_template": (
            "The last decades of the Roman Republic witnessed one of history's most dramatic political collapses. "
            "At the center stood {caesar}, whose military genius and political ambition would reshape the Mediterranean world.\n\n"
            "After years of campaigning in Gaul during the {gallic_war}, Caesar had built an army of legendary loyalty. "
            "The {battle_alesia} in 52 BCE broke the back of Gallic resistance, establishing Rome's control over what is now {france}. "
            "But Caesar's growing power alarmed the Roman Senate. When ordered to disband his legions, Caesar instead made his fateful decision: "
            "{crossing_rubicon}, an act of defiance that plunged Rome into {civil_war}.\n\n"
            "The civil war was swift but devastating. Caesar pursued his rivals across the Mediterranean, defeating Pompey's forces in a series of brilliant campaigns. "
            "By 45 BCE, he stood as the undisputed master of Rome, accepting the title of dictator perpetuo.\n\n"
            "Yet absolute power bred absolute fear. On the Ides of March, 44 BCE, the {assassination} ended Caesar's life but not his legacy. "
            "The Republic he had overthrown was already dead; the Empire he inadvertently created would endure for centuries."
        ),
        "body_keys": {
            "caesar": "person:Julius Caesar",
            "gallic_war": "event:Gallic War",
            "battle_alesia": "event:Battle of Alesia",
            "france": "location:France",
            "crossing_rubicon": "event:crossing the Rubicon",
            "civil_war": "event:Caesar's Civil War",
            "assassination": "event:assassination of Julius Caesar",
        },
        "featured_persons": ["person:Julius Caesar"],
        "featured_events": ["event:assassination of Julius Caesar", "event:Battle of Alesia"],
        "location_keys": ["location:France"],
    },
    {
        "title": "Napoleon and the Reshaping of Europe",
        "title_ko": "나폴레옹과 유럽의 재편",
        "summary": "How Napoleon Bonaparte's campaigns transformed the political landscape of early 19th-century Europe.",
        "category": "biography",
        "tags": ["napoleon", "france", "warfare", "modern-era"],
        "importance": 5,
        "era_start": 1803,
        "era_end": 1815,
        "body_template": (
            "{napoleon} rose from the chaos of the French Revolution to become the most powerful ruler in Europe. "
            "His military campaigns during the {napoleonic_wars} reshaped borders, toppled monarchies, and spread revolutionary ideals across the continent.\n\n"
            "From 1803 to 1815, Napoleon's Grande Armée fought across {france}, {spain}, and beyond. "
            "His victories at Austerlitz, Jena, and Wagram demonstrated a mastery of warfare that rewrote military doctrine. "
            "The Napoleonic Code, his legal reform, proved more durable than any battlefield conquest, influencing legal systems worldwide.\n\n"
            "Yet Napoleon's ambition proved his undoing. The disastrous invasion of Russia in 1812, followed by the Battle of Leipzig and eventual exile, "
            "marked the end of an era. His brief return during the Hundred Days ended at Waterloo.\n\n"
            "Napoleon's legacy is paradoxical: a champion of revolutionary ideals who crowned himself Emperor, a liberator who imposed his will by force. "
            "The Congress of Vienna that followed his defeat attempted to restore the old order, but Europe had been irrevocably changed."
        ),
        "body_keys": {
            "napoleon": "person:Napoleon",
            "napoleonic_wars": "event:Napoleonic Wars",
            "france": "location:France",
            "spain": "location:Spain",
        },
        "featured_persons": ["person:Napoleon"],
        "featured_events": ["event:Napoleonic Wars"],
        "location_keys": ["location:France", "location:Spain"],
    },
    {
        "title": "Genghis Khan and the Mongol Conquest",
        "title_ko": "칭기즈 칸과 몽골 정복",
        "summary": "The rise of Genghis Khan and how the Mongol Empire reshaped Eurasia through unprecedented military campaigns.",
        "category": "era_overview",
        "tags": ["mongol", "conquest", "medieval", "eurasia"],
        "importance": 5,
        "era_start": 1206,
        "era_end": 1227,
        "body_template": (
            "{genghis} united the fractious Mongol tribes through a combination of military genius, political cunning, and ruthless determination. "
            "Born as Temüjin around 1162, he would forge the largest contiguous land empire in human history.\n\n"
            "After consolidating power on the steppe, Genghis Khan turned his attention to the settled civilizations. "
            "The {jin_conquest} demonstrated the Mongol army's ability to adapt from steppe warfare to siege operations. "
            "The {battle_indus} showed their reach extended far beyond the grasslands of their homeland.\n\n"
            "The Mongol conquests were devastating in their immediate impact but transformative in their long-term consequences. "
            "The Pax Mongolica that followed opened trade routes connecting East and West, facilitating the exchange of goods, ideas, and diseases "
            "that would reshape the world.\n\n"
            "Genghis Khan died in 1227, but the empire he built continued to expand under his successors. "
            "His legacy endures not just in the vast territories he conquered, but in the cultural and commercial connections he forged across Eurasia."
        ),
        "body_keys": {
            "genghis": "person:Genghis Khan",
            "jin_conquest": "event:Mongol conquest of the Jin dynasty",
            "battle_indus": "event:Battle of Indus",
        },
        "featured_persons": ["person:Genghis Khan"],
        "featured_events": ["event:Mongol conquest of the Jin dynasty", "event:Battle of Indus"],
        "location_keys": [],
    },
]


def build_body(template, keys, entities):
    """Replace {key} placeholders with [Name](entity:type:id) tags."""
    body = template
    for placeholder, entity_key in keys.items():
        body = body.replace("{" + placeholder + "}", tag(entities, entity_key))
    return body


def insert_history(cur, conn, history_data, entities):
    """Insert one history + its history_entities."""
    body = build_body(
        history_data["body_template"],
        history_data["body_keys"],
        entities,
    )

    cur.execute("""
        INSERT INTO histories (title, title_ko, summary, era_start, era_end, body,
                               category, tags, author_type, author_name, importance, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'system', 'seed_test', %s, 'published')
        RETURNING id
    """, (
        history_data["title"],
        history_data.get("title_ko"),
        history_data.get("summary"),
        history_data.get("era_start"),
        history_data.get("era_end"),
        body,
        history_data.get("category", "essay"),
        history_data.get("tags", []),
        history_data.get("importance", 3),
    ))
    history_id = cur.fetchone()[0]

    # Insert featured entities
    entity_entries = []
    for key in history_data.get("featured_persons", []):
        ent = e(entities, key)
        if ent:
            entity_entries.append(("person", ent["id"], ent["name"], "featured"))
    for key in history_data.get("featured_events", []):
        ent = e(entities, key)
        if ent:
            entity_entries.append(("event", ent["id"], ent.get("title"), "featured"))
    for key in history_data.get("location_keys", []):
        ent = e(entities, key)
        if ent:
            entity_entries.append(("location", ent["id"], ent["name"], "location"))

    # Parse mentioned entities from body
    import re
    pattern = re.compile(r'\[([^\]]+)\]\(entity:(person|event|location):(\d+)\)')
    seen = set()
    for match in pattern.finditer(body):
        etype = match.group(2)
        eid = int(match.group(3))
        ename = match.group(1)
        key = (etype, eid)
        if key not in seen:
            seen.add(key)
            # Only add as mentioned if not already featured/location
            if not any(ee[0] == etype and ee[1] == eid for ee in entity_entries):
                entity_entries.append((etype, eid, ename, "mentioned"))

    for etype, eid, ename, role in entity_entries:
        cur.execute("""
            INSERT INTO history_entities (history_id, entity_type, entity_id, entity_name, role)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (history_id, etype, eid, ename, role))

    conn.commit()
    return history_id


def main():
    parser = argparse.ArgumentParser(description="Seed test histories into the database.")
    parser.add_argument("--clean", action="store_true", help="Delete previously seeded histories first")
    args = parser.parse_args()

    print("=" * 60)
    print("  Seed Test Histories")
    print("=" * 60)

    conn = get_conn()
    cur = conn.cursor()

    if args.clean:
        clean_seeded(conn)

    # Check if already seeded
    cur.execute("SELECT COUNT(*) FROM histories WHERE author_name = 'seed_test'")
    existing = cur.fetchone()[0]
    if existing > 0:
        print(f"  Already {existing} seeded histories. Use --clean to re-seed.")
        cur.close()
        conn.close()
        return

    # Look up real entity IDs
    print("\n  Looking up entities...")
    entities = lookup_entities(cur)
    found = len(entities)
    print(f"  Found {found} entities in DB.")

    for key, val in sorted(entities.items()):
        eid = val.get("id")
        name = val.get("name") or val.get("title")
        print(f"    {key} -> id={eid} ({name})")

    # Insert histories
    print(f"\n  Inserting {len(SEED_HISTORIES)} histories...")
    for i, hist in enumerate(SEED_HISTORIES):
        history_id = insert_history(cur, conn, hist, entities)
        print(f"  [{i+1}] id={history_id}: {hist['title']}")

    # Verify
    cur.execute("""
        SELECT h.id, h.title, h.category,
               (SELECT COUNT(*) FROM history_entities he WHERE he.history_id = h.id) as entity_count
        FROM histories h
        WHERE h.author_name = 'seed_test'
        ORDER BY h.id
    """)
    print("\n  === Verification ===")
    for row in cur.fetchall():
        print(f"  id={row[0]}: {row[1]} (cat={row[2]}, entities={row[3]})")

    print(f"\n  Done! Inserted {len(SEED_HISTORIES)} test histories.")
    print("  Test with: curl http://localhost:8100/api/v1/histories")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
