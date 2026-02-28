"""
Seed Trismegistus Portal data.

Step 1: Showcase JSON -> portal_items (16 items)
Step 2: FGO servant index -> fgo_servants (449 servants, 124 person links)
Step 3: Initial collections (3 collections with entries)

Usage:
    cd backend
    python scripts/seed_portal.py
    python scripts/seed_portal.py --portal-only    # Step 1 only
    python scripts/seed_portal.py --servants-only   # Step 2 only
    python scripts/seed_portal.py --collections-only # Step 3 only
    python scripts/seed_portal.py --dry-run          # Preview without writing
"""
import argparse
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.session import SessionLocal

# === Paths ===
SHOWCASE_DIR = Path(__file__).parent.parent / "app" / "data" / "showcases"
FGO_INDEX = Path("E:/chaldeas_data/fgo_db/servants/index.json")
FGO_COMPARISON = Path("E:/chaldeas_data/processed/fgo/person_links/fgo_db_comparison.json")

# Map JSON 'type' to portal_items 'item_type'
TYPE_MAP = {
    "singularity": "singularity",
    "lostbelt": "lostbelt",
    "servant": "servant_column",
    "article": None,  # Determined by filename
}

# Map filename to item_type for articles
FILENAME_TYPE_MAP = {
    "singularities.json": "singularity",
    "lostbelts.json": "lostbelt",
    "servants.json": "servant_column",
    "history.json": "history",
    "literature.json": "literature",
    "music.json": "music",
}


def seed_portal_items(db, dry_run=False):
    """Step 1: Load showcase JSONs into portal_items table."""
    print("\n=== Step 1: Seeding portal_items ===")

    files = ["singularities.json", "lostbelts.json", "servants.json",
             "history.json", "literature.json", "music.json"]

    items = []
    for filename in files:
        filepath = SHOWCASE_DIR / filename
        if not filepath.exists():
            print(f"  SKIP: {filename} not found")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            raw_items = json.load(f)

        item_type = FILENAME_TYPE_MAP[filename]
        for i, raw in enumerate(raw_items):
            items.append({
                "slug": raw["id"],
                "item_type": item_type,
                "title": raw["title"],
                "title_ko": raw.get("title_ko"),
                "title_ja": raw.get("title_ja"),
                "subtitle": raw.get("subtitle"),
                "subtitle_ko": raw.get("subtitle_ko"),
                "subtitle_ja": raw.get("subtitle_ja"),
                "description": raw["description"],
                "description_ko": raw.get("description_ko"),
                "description_ja": raw.get("description_ja"),
                "chapter": raw.get("chapter"),
                "era": raw.get("era"),
                "year": raw.get("year"),
                "location": raw.get("location"),
                "historical_basis": raw.get("historical_basis"),
                "historical_basis_ko": raw.get("historical_basis_ko"),
                "historical_basis_ja": raw.get("historical_basis_ja"),
                "sections": json.dumps(raw.get("sections", []), ensure_ascii=False),
                "related_servants": json.dumps(raw.get("related_servants", []), ensure_ascii=False),
                "related_event_ids": json.dumps(raw.get("related_event_ids", []), ensure_ascii=False),
                "sources": json.dumps(raw.get("sources", []), ensure_ascii=False),
                "sort_order": i,
                "is_featured": i == 0,  # First item per file is featured
            })

        print(f"  {filename}: {len(raw_items)} items")

    if dry_run:
        print(f"  DRY RUN: Would insert {len(items)} portal_items")
        return len(items)

    # Upsert: delete existing then insert
    db.execute(text("DELETE FROM portal_items"))
    for item in items:
        db.execute(text("""
            INSERT INTO portal_items (
                slug, item_type, title, title_ko, title_ja,
                subtitle, subtitle_ko, subtitle_ja,
                description, description_ko, description_ja,
                chapter, era, year, location,
                historical_basis, historical_basis_ko, historical_basis_ja,
                sections, related_servants, related_event_ids, sources,
                sort_order, is_featured
            ) VALUES (
                :slug, :item_type, :title, :title_ko, :title_ja,
                :subtitle, :subtitle_ko, :subtitle_ja,
                :description, :description_ko, :description_ja,
                :chapter, :era, :year, :location,
                :historical_basis, :historical_basis_ko, :historical_basis_ja,
                CAST(:sections AS jsonb), CAST(:related_servants AS jsonb),
                CAST(:related_event_ids AS jsonb), CAST(:sources AS jsonb),
                :sort_order, :is_featured
            )
        """), item)

    db.commit()
    print(f"  Inserted {len(items)} portal_items")
    return len(items)


def seed_fgo_servants(db, dry_run=False):
    """Step 2: Load FGO servant index + comparison data into fgo_servants."""
    print("\n=== Step 2: Seeding fgo_servants ===")

    if not FGO_INDEX.exists():
        print(f"  SKIP: {FGO_INDEX} not found")
        return 0

    with open(FGO_INDEX, "r", encoding="utf-8") as f:
        servants = json.load(f)
    print(f"  Index: {len(servants)} servants")

    # Load comparison data for person_id matching
    comparison_map = {}  # name_en -> {db_match, dialogue_lines}
    if FGO_COMPARISON.exists():
        with open(FGO_COMPARISON, "r", encoding="utf-8") as f:
            comparison = json.load(f)
        for entry in comparison.get("found_in_db", []):
            comparison_map[entry["name_en"]] = entry
        print(f"  Comparison: {len(comparison_map)} matched servants")

    if dry_run:
        print(f"  DRY RUN: Would upsert {len(servants)} fgo_servants")
        return len(servants)

    # Build person name -> id lookup
    person_lookup = {}
    if comparison_map:
        db_matches = set(e["db_match"] for e in comparison_map.values())
        # Batch lookup
        for name in db_matches:
            result = db.execute(
                text("SELECT id FROM persons WHERE name = :name LIMIT 1"),
                {"name": name}
            ).fetchone()
            if result:
                person_lookup[name] = result[0]
        print(f"  Person lookup: {len(person_lookup)} matched in DB")

    # Clear existing and insert
    db.execute(text("DELETE FROM fgo_servants"))

    inserted = 0
    linked = 0
    for s in servants:
        name_en = s.get("name_en", "")
        comp = comparison_map.get(name_en, {})
        db_match = comp.get("db_match")
        person_id = person_lookup.get(db_match) if db_match else None

        db.execute(text("""
            INSERT INTO fgo_servants (
                servant_id, name, name_jp, name_ko, class_name, rarity,
                person_id, dialogue_lines, atlas_id
            ) VALUES (
                :servant_id, :name, :name_jp, :name_ko, :class_name, :rarity,
                :person_id, :dialogue_lines, :atlas_id
            )
        """), {
            "servant_id": s["collectionNo"],
            "name": name_en,
            "name_jp": s.get("name_ja"),
            "name_ko": s.get("name_ko"),
            "class_name": s.get("className", "unknown"),
            "rarity": s.get("rarity"),
            "person_id": person_id,
            "dialogue_lines": comp.get("dialogue_lines", 0),
            "atlas_id": s.get("id"),
        })
        inserted += 1
        if person_id:
            linked += 1

    db.commit()
    print(f"  Inserted {inserted} fgo_servants ({linked} linked to persons)")
    return inserted


def seed_collections(db, dry_run=False):
    """Step 3: Create initial collections with entries."""
    print("\n=== Step 3: Seeding collections ===")

    collections = [
        {
            "slug": "fgo-main-story",
            "collection_type": "fgo_storyline",
            "title": "FGO Main Story",
            "title_ko": "FGO 메인 스토리",
            "title_ja": "FGO メインストーリー",
            "description": "The complete Fate/Grand Order main storyline, from the first Singularity to the final Lostbelt.",
            "description_ko": "첫 번째 특이점부터 마지막 이문대까지, Fate/Grand Order의 완전한 메인 스토리라인.",
            "description_ja": "最初の特異点から最後の異聞帯まで、Fate/Grand Orderのメインストーリー全編。",
            "icon": "🔮",
            "sort_order": 0,
            "is_featured": True,
            "tags": json.dumps(["fgo", "singularity", "lostbelt"]),
            "year_start": -2600,
            "year_end": 2018,
            "region": None,
            # Entries: all singularities + lostbelts portal_items
            "entry_slugs": [
                "singularity-f", "singularity-1", "singularity-2",
                "lostbelt-1", "lostbelt-2",
            ],
        },
        {
            "slug": "greece-rome",
            "collection_type": "era",
            "title": "Greece & Rome",
            "title_ko": "그리스·로마",
            "title_ja": "ギリシャ・ローマ",
            "description": "The classical world of heroes, philosophers, and empires that shaped Western civilization.",
            "description_ko": "서양 문명을 형성한 영웅, 철학자, 제국의 고전 세계.",
            "description_ja": "西洋文明を形作った英雄・哲学者・帝国の古典世界。",
            "icon": "🏛️",
            "sort_order": 1,
            "is_featured": True,
            "tags": json.dumps(["greece", "rome", "classical", "ancient"]),
            "year_start": -2000,
            "year_end": 476,
            "region": "Mediterranean",
            "entry_slugs": ["history-alexander", "servant-gilgamesh", "servant-leonidas"],
        },
        {
            "slug": "arts-culture",
            "collection_type": "content",
            "title": "Arts & Culture",
            "title_ko": "예술과 문화",
            "title_ja": "芸術と文化",
            "description": "Literature, music, and artistic achievements across history.",
            "description_ko": "역사를 관통하는 문학, 음악, 예술적 성취.",
            "description_ja": "歴史を貫く文学・音楽・芸術的成果。",
            "icon": "🎭",
            "sort_order": 2,
            "is_featured": True,
            "tags": json.dumps(["literature", "music", "art", "culture"]),
            "year_start": None,
            "year_end": None,
            "region": None,
            "entry_slugs": ["literature-iliad", "music-mozart"],
        },
    ]

    if dry_run:
        print(f"  DRY RUN: Would create {len(collections)} collections")
        return len(collections)

    # Clear existing
    db.execute(text("DELETE FROM collection_entries"))
    db.execute(text("DELETE FROM collections"))

    created = 0
    for coll in collections:
        entry_slugs = coll.pop("entry_slugs")

        db.execute(text("""
            INSERT INTO collections (
                slug, collection_type, title, title_ko, title_ja,
                description, description_ko, description_ja,
                icon, sort_order, is_featured, tags,
                year_start, year_end, region
            ) VALUES (
                :slug, :collection_type, :title, :title_ko, :title_ja,
                :description, :description_ko, :description_ja,
                :icon, :sort_order, :is_featured, CAST(:tags AS jsonb),
                :year_start, :year_end, :region
            )
        """), coll)

        # Get the collection id
        result = db.execute(
            text("SELECT id FROM collections WHERE slug = :slug"),
            {"slug": coll["slug"]}
        ).fetchone()
        collection_id = result[0]

        # Link portal_items as entries
        for i, slug in enumerate(entry_slugs):
            item = db.execute(
                text("SELECT id FROM portal_items WHERE slug = :slug"),
                {"slug": slug}
            ).fetchone()
            if item:
                db.execute(text("""
                    INSERT INTO collection_entries (
                        collection_id, entry_type, portal_item_id,
                        sort_order, is_highlighted
                    ) VALUES (
                        :collection_id, 'portal_item', :portal_item_id,
                        :sort_order, :is_highlighted
                    )
                """), {
                    "collection_id": collection_id,
                    "portal_item_id": item[0],
                    "sort_order": i,
                    "is_highlighted": i == 0,
                })
            else:
                print(f"    WARNING: portal_item '{slug}' not found, skipping")

        created += 1
        print(f"  Collection '{coll['slug']}': {len(entry_slugs)} entries")

    db.commit()
    print(f"  Created {created} collections")
    return created


def main():
    parser = argparse.ArgumentParser(description="Seed Trismegistus Portal data")
    parser.add_argument("--portal-only", action="store_true", help="Only seed portal_items")
    parser.add_argument("--servants-only", action="store_true", help="Only seed fgo_servants")
    parser.add_argument("--collections-only", action="store_true", help="Only seed collections")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    run_all = not (args.portal_only or args.servants_only or args.collections_only)

    print("=" * 60)
    print("  Trismegistus Portal Seeder")
    print("=" * 60)
    if args.dry_run:
        print("  MODE: DRY RUN (no writes)")

    db = SessionLocal()
    try:
        if run_all or args.portal_only:
            seed_portal_items(db, args.dry_run)
        if run_all or args.servants_only:
            seed_fgo_servants(db, args.dry_run)
        if run_all or args.collections_only:
            seed_collections(db, args.dry_run)

        print("\n" + "=" * 60)
        print("  Seeding complete!")
        print("=" * 60)
    except Exception as e:
        db.rollback()
        print(f"\n  ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
