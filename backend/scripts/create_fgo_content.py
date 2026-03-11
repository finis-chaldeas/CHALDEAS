"""
FGO Content Pipeline — Batch Runner
====================================
Orchestrates Phase 1 (servant columns) and Phase 2 (singularity/LB articles)
of the FGO content pipeline.

Usage:
    cd backend

    # Phase 1: Servant columns (30 servants)
    python scripts/create_fgo_content.py --phase 1
    python scripts/create_fgo_content.py --phase 1 --limit 3       # Test with 3
    python scripts/create_fgo_content.py --phase 1 --dry-run       # Preview only
    python scripts/create_fgo_content.py --phase 1 --import-after  # Generate + import

    # Phase 2: Singularity/LB articles (15 chapters)
    python scripts/create_fgo_content.py --phase 2
    python scripts/create_fgo_content.py --phase 2 --limit 2

    # Both phases
    python scripts/create_fgo_content.py --phase all

    # Phase 4: Cross-linking + collections
    python scripts/create_fgo_content.py --phase 4

    # Status check
    python scripts/create_fgo_content.py --status
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"

# ─── Phase 1: Servant Column Targets ───

# Historical persons (have person_id in DB)
# Using fgo_servants.servant_id (not atlas_id) — these match the DB column directly
HISTORICAL_SERVANTS = [
    # (servant_id, name_en, notes)
    (12, "Gilgamesh", "King of Uruk"),
    (108, "Iskandar", "Alexander the Great"),
    (5, "Nero Claudius", "Roman Emperor"),       # servant_id=5 (Saber, ★4)
    (7, "Gaius Julius Caesar", "Roman Dictator"),
    (253, "Leonardo da Vinci", "Renaissance Polymath"),  # Rider form
    (59, "Jeanne d'Arc", "Maid of Orleans"),
    (65, "Francis Drake", "Privateer"),
    (118, "Ozymandias", "Ramesses II"),
    (139, "Cleopatra", "Last Pharaoh"),
    (250, "Oda Nobunaga", "Unifier of Japan"),    # Avenger form
    (212, "Napoleon", "French Emperor"),
    (77, "Nikola Tesla", "Inventor"),
    (229, "Qin Shi Huang", "First Emperor"),
    (97, "Florence Nightingale", "Lady with the Lamp"),
    (21, "Leonidas I", "King of Sparta"),
    (37, "Zhuge Liang", "Strategist"),
    (50, "Spartacus", "Gladiator Rebel"),
    (52, "Vlad III", "The Impaler"),
    (29, "Marie Antoinette", "Queen of France"),
    (205, "Ivan the Terrible", "Tsar"),
]

# Mythological/legendary (no person_id, but high content value)
MYTHOLOGICAL_SERVANTS = [
    (2, "Altria Pendragon", "King Arthur"),
    (17, "Cú Chulainn", "Irish Hero"),
    (206, "Achilles", "Trojan War Hero"),
    (47, "Heracles", "Greek Demigod"),
    (85, "Karna", "Mahabharata Hero"),
    (84, "Arjuna", "Mahabharata Hero"),
    (76, "Mordred", "Arthurian Rebel"),
    (31, "Medea", "Colchis Sorceress"),
    (27, "Ushiwakamaru", "Yoshitsune"),
    (153, "Miyamoto Musashi", "Legendary Swordsman"),
]

# ─── Phase 2: Chapter Targets ───

SINGULARITY_TARGETS = ["F", "I", "II", "III", "IV", "V", "VI", "VII", "Final"]
LOSTBELT_TARGETS = [1, 2, 3, 4, 5, 6, 7]

# ─── Phase 3: FGO-linked History Shifts ───
# Topics not covered by existing 896 shifts
# Format: (topic_for_generate, chain_type, notes)
FGO_SHIFT_TOPICS = [
    ("Ancient Mesopotamia and the City of Uruk", "aggregate", "Singularity VII backdrop"),
    ("Jeanne d'Arc and the Siege of Orleans", "person_story", "Singularity I key figure"),
    ("Oda Nobunaga's Unification of Japan", "person_story", "Major FGO servant"),
    ("Cleopatra and the Fall of Ptolemaic Egypt", "person_story", "FGO servant + Singularity link"),
    ("The Age of Exploration: Drake and the Circumnavigation", "aggregate", "Singularity III backdrop"),
    ("Nikola Tesla and the Age of Electricity", "person_story", "Singularity IV key figure"),
    ("The Battle of Thermopylae: Leonidas and the 300", "aggregate", "Major FGO servant"),
    ("Spartacus and the Gladiator Revolt", "person_story", "FGO servant"),
    ("Vlad III and the Ottoman Wars in Wallachia", "person_story", "FGO servant"),
    ("The Trojan War: Bronze Age Collapse", "aggregate", "Multiple FGO servants"),
    ("The Mahabharata: India's Great Epic War", "aggregate", "Karna, Arjuna backdrop"),
    ("Celtic Mythology and the Ulster Cycle", "aggregate", "Cu Chulainn backdrop"),
    ("Arthurian Britain: History and Legend", "aggregate", "Altria, Mordred, Round Table"),
    ("Miyamoto Musashi and the Edo Swordsmen", "person_story", "Major FGO servant"),
    ("Ivan the Terrible and the Russian Oprichnina", "person_story", "Lostbelt 1 backdrop"),
]


def run_command(cmd: list[str], label: str, dry_run: bool = False) -> tuple[bool, float, float]:
    """Run a subprocess command, return (success, elapsed_seconds, cost_estimate)."""
    if dry_run:
        print(f"  [DRY] Would run: {' '.join(cmd)}")
        return True, 0.0, 0.0

    print(f"  Running: {label}...")
    t0 = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=str(SCRIPT_DIR.parent),
            timeout=600,  # 10 min timeout per article
            env={**__import__('os').environ, "PYTHONIOENCODING": "utf-8"},
        )
        elapsed = time.time() - t0
        # Extract cost from output
        cost = 0.0
        for line in result.stdout.split('\n'):
            if 'Cost:' in line and '$' in line:
                try:
                    cost = float(line.split('$')[-1].strip())
                except ValueError:
                    pass

        if result.returncode != 0:
            print(f"    FAILED ({elapsed:.1f}s)")
            if result.stderr:
                print(f"    Error: {result.stderr[:300]}")
            return False, elapsed, cost

        # Print summary from output
        for line in result.stdout.split('\n'):
            if any(k in line for k in ['Done', 'Total:', 'Saved:', 'Cost:', 'sections,']):
                print(f"    {line.strip()}")

        return True, elapsed, cost

    except subprocess.TimeoutExpired:
        print(f"    TIMEOUT after 600s")
        return False, 600.0, 0.0
    except Exception as e:
        print(f"    ERROR: {e}")
        return False, 0.0, 0.0


def phase1_servants(args):
    """Phase 1: Generate servant columns."""
    servants = HISTORICAL_SERVANTS + MYTHOLOGICAL_SERVANTS
    if args.limit:
        servants = servants[:args.limit]

    print(f"=== Phase 1: Servant Columns ({len(servants)} servants) ===\n")

    results = {"success": 0, "failed": 0, "skipped": 0,
               "total_time": 0.0, "total_cost": 0.0}

    for i, (sid, name, notes) in enumerate(servants):
        print(f"\n[{i+1}/{len(servants)}] {name} ({notes})")

        # Check if YAML already exists
        expected_slugs = [
            f"servant-{name.lower().replace(' ', '-')}",
            name.lower().replace(' ', '-'),
        ]
        existing = None
        for slug in expected_slugs:
            path = OUTPUT_DIR / f"{slug}.yaml"
            if path.exists() and not args.force:
                existing = path
                break

        if existing:
            print(f"  SKIP — already exists: {existing.name}")
            if args.import_after:
                # Import existing
                import_cmd = [
                    sys.executable, "scripts/create_portal_article.py",
                    "--import", str(existing),
                    "--type", "servant_column",
                    "--collection", "fgo-servant-columns",
                ]
                run_command(import_cmd, f"Import {existing.name}", args.dry_run)
            results["skipped"] += 1
            continue

        cmd = [
            sys.executable, "scripts/create_portal_article.py",
            "--servant-id", str(sid),
        ]
        if args.model:
            cmd.extend(["--model", args.model])
        if args.import_after:
            cmd.append("--import-after")

        ok, elapsed, cost = run_command(cmd, name, args.dry_run)
        results["total_time"] += elapsed
        results["total_cost"] += cost

        if ok:
            results["success"] += 1
        else:
            results["failed"] += 1

    print(f"\n{'=' * 60}")
    print(f"Phase 1 Results:")
    print(f"  Success: {results['success']}")
    print(f"  Failed:  {results['failed']}")
    print(f"  Skipped: {results['skipped']}")
    print(f"  Time:    {results['total_time']:.1f}s ({results['total_time']/60:.1f}min)")
    print(f"  Cost:    ~${results['total_cost']:.2f}")
    return results


def phase2_chapters(args):
    """Phase 2: Generate singularity/lostbelt articles."""
    targets = []
    for s in SINGULARITY_TARGETS:
        targets.append(("singularity", s))
    for lb in LOSTBELT_TARGETS:
        targets.append(("lostbelt", str(lb)))

    if args.limit:
        targets = targets[:args.limit]

    print(f"=== Phase 2: Chapter Articles ({len(targets)} chapters) ===\n")

    results = {"success": 0, "failed": 0, "skipped": 0,
               "total_time": 0.0, "total_cost": 0.0}

    for i, (ch_type, ch_num) in enumerate(targets):
        label = f"{ch_type} {ch_num}"
        print(f"\n[{i+1}/{len(targets)}] {label}")

        cmd = [
            sys.executable, "scripts/create_portal_article.py",
            f"--{ch_type}", ch_num,
        ]
        if args.model:
            cmd.extend(["--model", args.model])
        if args.import_after:
            cmd.append("--import-after")

        ok, elapsed, cost = run_command(cmd, label, args.dry_run)
        results["total_time"] += elapsed
        results["total_cost"] += cost

        if ok:
            results["success"] += 1
        else:
            results["failed"] += 1

    print(f"\n{'=' * 60}")
    print(f"Phase 2 Results:")
    print(f"  Success: {results['success']}")
    print(f"  Failed:  {results['failed']}")
    print(f"  Skipped: {results['skipped']}")
    print(f"  Time:    {results['total_time']:.1f}s ({results['total_time']/60:.1f}min)")
    print(f"  Cost:    ~${results['total_cost']:.2f}")
    return results


def phase3_shifts(args):
    """Phase 3: Generate FGO-linked history shifts."""
    targets = FGO_SHIFT_TOPICS
    if args.limit:
        targets = targets[:args.limit]

    print(f"=== Phase 3: FGO-Linked History Shifts ({len(targets)} topics) ===\n")

    results = {"success": 0, "failed": 0, "skipped": 0,
               "total_time": 0.0, "total_cost": 0.0}

    for i, (topic, chain_type, notes) in enumerate(targets):
        print(f"\n[{i+1}/{len(targets)}] {topic} ({chain_type})")
        print(f"    Notes: {notes}")

        cmd = [
            sys.executable, "scripts/create_shift.py",
            "--generate", topic,
            "--type", chain_type,
        ]
        if args.model:
            cmd.extend(["--model", args.model])

        ok, elapsed, cost = run_command(cmd, topic, args.dry_run)
        results["total_time"] += elapsed
        results["total_cost"] += cost

        if ok:
            results["success"] += 1
        else:
            results["failed"] += 1

    print(f"\n{'=' * 60}")
    print(f"Phase 3 Results:")
    print(f"  Success: {results['success']}")
    print(f"  Failed:  {results['failed']}")
    print(f"  Time:    {results['total_time']:.1f}s ({results['total_time']/60:.1f}min)")
    print(f"  Cost:    ~${results['total_cost']:.2f}")
    return results


def phase4_crosslink(args):
    """Phase 4: Cross-linking + collections."""
    from sqlalchemy import text as sql_text

    sys.path.insert(0, str(SCRIPT_DIR.parent))
    from app.db.session import SessionLocal

    db = SessionLocal()
    print(f"=== Phase 4: Cross-Linking + Collections ===\n")

    # ─── 4-1: Create collections if not exist ───
    collections = [
        ("fgo-singularities", "fgo_storyline", "FGO Singularities",
         "FGO 특이점", "Explore the real history behind each Singularity"),
        ("fgo-lostbelts", "fgo_storyline", "FGO Lostbelts",
         "FGO 이문대", "Explore the real history behind each Lostbelt"),
        ("fgo-servant-columns", "content", "FGO Servant Columns",
         "FGO 서번트 칼럼", "Deep dives: FGO Servants vs. Real History"),
        ("fgo-history-bridge", "theme", "FGO × History Bridge",
         "FGO × 역사 브릿지", "Where Fate/Grand Order meets real history"),
    ]

    for slug, ctype, title, title_ko, desc in collections:
        existing = db.execute(
            sql_text("SELECT id FROM collections WHERE slug = :slug"),
            {"slug": slug}
        ).fetchone()

        if existing:
            print(f"  Collection '{slug}' already exists (id={existing[0]})")
        else:
            if not args.dry_run:
                db.execute(sql_text("""
                    INSERT INTO collections (slug, collection_type, title, title_ko, description, is_featured)
                    VALUES (:slug, :ctype, :title, :title_ko, :desc, true)
                """), {"slug": slug, "ctype": ctype, "title": title,
                       "title_ko": title_ko, "desc": desc})
                print(f"  Created collection: {slug}")
            else:
                print(f"  [DRY] Would create collection: {slug}")

    # ─── 4-2: Link articles to collections ───
    # Get all portal_items and link them to appropriate collections
    items = db.execute(sql_text("""
        SELECT id, slug, item_type FROM portal_items
        WHERE item_type IN ('singularity', 'lostbelt', 'servant_column')
    """)).fetchall()

    linked = 0
    for item_id, item_slug, item_type in items:
        coll_slug = {
            "singularity": "fgo-singularities",
            "lostbelt": "fgo-lostbelts",
            "servant_column": "fgo-servant-columns",
        }.get(item_type)

        if not coll_slug:
            continue

        coll = db.execute(
            sql_text("SELECT id FROM collections WHERE slug = :slug"),
            {"slug": coll_slug}
        ).fetchone()

        if not coll:
            continue

        existing_entry = db.execute(sql_text("""
            SELECT id FROM collection_entries
            WHERE collection_id = :coll_id AND portal_item_id = :item_id
        """), {"coll_id": coll[0], "item_id": item_id}).fetchone()

        if not existing_entry:
            if not args.dry_run:
                db.execute(sql_text("""
                    INSERT INTO collection_entries
                        (collection_id, entry_type, portal_item_id, sort_order)
                    VALUES (:coll_id, 'portal_item', :item_id, 0)
                """), {"coll_id": coll[0], "item_id": item_id})
            linked += 1

    print(f"  Linked {linked} articles to collections")

    # ─── 4-3: Auto-fill related_servants for articles ───
    # For servant_columns: find related servants from same person_id
    servant_items = db.execute(sql_text("""
        SELECT pi.id, pi.slug, pi.related_servants
        FROM portal_items pi
        WHERE pi.item_type = 'servant_column'
          AND (pi.related_servants IS NULL OR pi.related_servants = '[]'::jsonb)
    """)).fetchall()

    enriched = 0
    for item_id, item_slug, _ in servant_items:
        # Try to find the servant by slug pattern
        servant_name = item_slug.replace("servant-", "").replace("-", " ").title()
        # Look up in fgo_servants
        servant_row = db.execute(sql_text("""
            SELECT fs.name, fs.class_name, fs.rarity, fs.person_id
            FROM fgo_servants fs
            WHERE lower(fs.name) LIKE :pat
            LIMIT 1
        """), {"pat": f"%{servant_name.lower()}%"}).fetchone()

        if servant_row and servant_row[3]:
            # Get related servants with same person_id or related events
            related = db.execute(sql_text("""
                SELECT DISTINCT fs.name, fs.class_name, fs.rarity
                FROM fgo_servants fs
                WHERE fs.person_id IN (
                    SELECT DISTINCT ep2.person_id
                    FROM event_persons ep1
                    JOIN event_persons ep2 ON ep1.event_id = ep2.event_id
                    WHERE ep1.person_id = :pid AND ep2.person_id != :pid
                )
                AND fs.person_id IS NOT NULL
                LIMIT 5
            """), {"pid": servant_row[3]}).fetchall()

            if related and not args.dry_run:
                related_list = [{"name": r[0], "class": r[1], "rarity": r[2]} for r in related]
                db.execute(sql_text("""
                    UPDATE portal_items SET related_servants = CAST(:rs AS jsonb)
                    WHERE id = :id
                """), {"id": item_id, "rs": json.dumps(related_list, ensure_ascii=False)})
                enriched += 1

    print(f"  Enriched {enriched} servant columns with related_servants")

    if not args.dry_run:
        db.commit()
    db.close()

    print(f"\n  Phase 4 complete!")
    if args.dry_run:
        print("  (DRY RUN — no changes written)")


def cmd_status(args):
    """Show current pipeline status."""
    sys.path.insert(0, str(SCRIPT_DIR.parent))
    from app.db.session import SessionLocal
    from sqlalchemy import text as sql_text

    db = SessionLocal()

    print("=== FGO Content Pipeline Status ===\n")

    # Servant linking
    linked = db.execute(sql_text(
        "SELECT count(*) FROM fgo_servants WHERE person_id IS NOT NULL"
    )).scalar()
    total = db.execute(sql_text("SELECT count(*) FROM fgo_servants")).scalar()
    print(f"  Servant linking: {linked}/{total}")

    # Portal items by type
    types = db.execute(sql_text("""
        SELECT item_type, count(*), avg(jsonb_array_length(COALESCE(sections, '[]'::jsonb)))
        FROM portal_items
        GROUP BY item_type ORDER BY item_type
    """)).fetchall()
    print(f"\n  Portal items:")
    for t in types:
        print(f"    {t[0]:20s}: {t[1]:3d} items (avg {t[2]:.1f} sections)")

    # Collections
    colls = db.execute(sql_text("""
        SELECT c.slug, c.title, count(ce.id) as entries
        FROM collections c
        LEFT JOIN collection_entries ce ON ce.collection_id = c.id
        GROUP BY c.id ORDER BY c.slug
    """)).fetchall()
    if colls:
        print(f"\n  Collections:")
        for c in colls:
            print(f"    {c[0]:30s}: {c[2]:3d} entries  [{c[1]}]")

    # YAML files on disk
    yaml_files = list(OUTPUT_DIR.glob("*.yaml"))
    servant_yamls = [f for f in yaml_files if f.stem.startswith("servant-")]
    chapter_yamls = [f for f in yaml_files
                     if any(f.stem.startswith(p)
                            for p in ["singularity", "lb", "fuyuki", "orleans", "septem",
                                      "okeanos", "london", "america", "camelot", "babylonia",
                                      "solomon"])]
    print(f"\n  YAML files on disk:")
    print(f"    Total:     {len(yaml_files)}")
    print(f"    Servants:  {len(servant_yamls)}")
    print(f"    Chapters:  {len(chapter_yamls)}")

    # Shifts
    shifts = db.execute(sql_text("SELECT count(*) FROM historical_chains")).scalar()
    pages = db.execute(sql_text("SELECT count(*) FROM chain_segments")).scalar()
    print(f"\n  History shifts: {shifts} shifts, {pages} pages")

    db.close()


def main():
    parser = argparse.ArgumentParser(
        description="FGO Content Pipeline — batch runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/create_fgo_content.py --phase 1 --limit 3     # Test 3 servants
  python scripts/create_fgo_content.py --phase 2 --limit 2     # Test 2 chapters
  python scripts/create_fgo_content.py --phase all              # Full pipeline
  python scripts/create_fgo_content.py --phase 4                # Cross-linking
  python scripts/create_fgo_content.py --status                 # Check status
        """,
    )
    parser.add_argument("--phase", type=str,
                        choices=["1", "2", "3", "4", "all"],
                        help="Phase to run (1=servants, 2=chapters, 3=shifts, 4=crosslink, all)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of items to process (0=all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without running generation")
    parser.add_argument("--import-after", action="store_true",
                        help="Auto-import generated YAML to DB")
    parser.add_argument("--force", action="store_true",
                        help="Force regeneration even if YAML exists")
    parser.add_argument("--model", type=str,
                        help="Override OpenAI model")
    parser.add_argument("--status", action="store_true",
                        help="Show pipeline status")

    args = parser.parse_args()

    if args.status:
        cmd_status(args)
        return

    if not args.phase:
        parser.print_help()
        return

    t_start = time.time()
    all_results = []

    if args.phase in ("1", "all"):
        r = phase1_servants(args)
        all_results.append(("Phase 1", r))

    if args.phase in ("2", "all"):
        r = phase2_chapters(args)
        all_results.append(("Phase 2", r))

    if args.phase in ("3", "all"):
        r = phase3_shifts(args)
        all_results.append(("Phase 3", r))

    if args.phase in ("4", "all"):
        phase4_crosslink(args)

    if len(all_results) > 1:
        total_time = time.time() - t_start
        total_cost = sum(r["total_cost"] for _, r in all_results)
        total_success = sum(r["success"] for _, r in all_results)
        total_failed = sum(r["failed"] for _, r in all_results)
        print(f"\n{'=' * 60}")
        print(f"TOTAL: {total_success} success, {total_failed} failed")
        print(f"  Time: {total_time:.1f}s ({total_time/60:.1f}min)")
        print(f"  Cost: ~${total_cost:.2f}")


if __name__ == "__main__":
    main()
