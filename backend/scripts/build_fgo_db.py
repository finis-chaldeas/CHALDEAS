"""
FGO Local Database Builder
===========================
raw 데이터 → 정리된 로컬 FGO DB 파일.

입력:
    E:/chaldeas_data/raw/atlas_academy/
        scripts_jp/*.json         — JP 스크립트 (일본어 원문)
        scripts/*.json            — NA 스크립트 (영어)
        scripts_kr/*.json         — KR 스크립트 (한국어)
        servant_profiles_jp.json  — JP 서번트 프로필 (본드 텍스트)
        servant_profiles_na.json  — NA 서번트 프로필 (본드 텍스트)
        servants_basic_jp.json    — JP 서번트 기본 정보
        servants_basic_na.json    — NA 서번트 기본 정보
        servant_person_mapping.json — 서번트 ↔ 실제 역사인물 매핑
        story_info_na.json        — 스토리 구조

출력:
    E:/chaldeas_data/fgo_db/
        meta.json                  — DB 메타정보
        stories/
            singularity_F_fuyuki.json
            singularity_I_orleans.json
            ...
            lostbelt_1_anastasia.json
            ...
        servants/
            index.json             — 전 서번트 인덱스 (요약)
            by_id/
                100100.json        — 개별 서번트 상세 (JP+NA 통합)
                ...
        mappings/
            servant_to_person.json — 서번트 → DB persons 매핑
            story_locations.json   — 스토리 → 좌표/시대 매핑

사용법:
    python -m scripts.build_fgo_db                  # 전체 빌드
    python -m scripts.build_fgo_db --only stories   # 스토리만
    python -m scripts.build_fgo_db --only servants  # 서번트만
    python -m scripts.build_fgo_db --only mappings  # 매핑만
"""

import argparse
import io
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# Windows UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── Paths ──────────────────────────────────────────────

RAW_DIR = Path(r"E:\chaldeas_data\raw\atlas_academy")
OUTPUT_DIR = Path(r"E:\chaldeas_data\fgo_db")

# ─── Story metadata ────────────────────────────────────

CHAPTER_META = {
    # Singularities
    100: {"slug": "fuyuki",    "type": "singularity", "number": "F",     "name_en": "Fuyuki",          "name_ja": "冬木",          "name_ko": "후유키",        "lat": 34.38, "lng": 131.60, "year": 2004},
    101: {"slug": "orleans",   "type": "singularity", "number": "I",     "name_en": "Orleans",         "name_ja": "オルレアン",      "name_ko": "오를레앙",       "lat": 47.90, "lng": 1.90,   "year": 1431},
    102: {"slug": "septem",    "type": "singularity", "number": "II",    "name_en": "Septem",          "name_ja": "セプテム",        "name_ko": "세프템",        "lat": 41.89, "lng": 12.49,  "year": 60},
    103: {"slug": "okeanos",   "type": "singularity", "number": "III",   "name_en": "Okeanos",         "name_ja": "オケアノス",      "name_ko": "오케아노스",     "lat": 20.0,  "lng": -60.0,  "year": 1573},
    104: {"slug": "london",    "type": "singularity", "number": "IV",    "name_en": "London",          "name_ja": "ロンドン",        "name_ko": "런던",          "lat": 51.51, "lng": -0.12,  "year": 1888},
    105: {"slug": "america",   "type": "singularity", "number": "V",     "name_en": "E Pluribus Unum", "name_ja": "イ・プルーリバス・ウナム", "name_ko": "이 플루리버스 우넘", "lat": 39.0, "lng": -98.0, "year": 1783},
    106: {"slug": "camelot",   "type": "singularity", "number": "VI",    "name_en": "Camelot",         "name_ja": "キャメロット",     "name_ko": "캬멜롯",        "lat": 31.77, "lng": 35.23,  "year": 1273},
    107: {"slug": "babylonia", "type": "singularity", "number": "VII",   "name_en": "Babylonia",       "name_ja": "バビロニア",      "name_ko": "바빌로니아",     "lat": 31.32, "lng": 45.64,  "year": -2655},
    108: {"slug": "solomon",   "type": "singularity", "number": "Final", "name_en": "Solomon",         "name_ja": "ソロモン",        "name_ko": "솔로몬",        "lat": 31.77, "lng": 35.23,  "year": 2016},
    # Epic of Remnant
    201: {"slug": "shinjuku",  "type": "remnant",    "number": "I",     "name_en": "Shinjuku",         "name_ja": "新宿",           "name_ko": "신주쿠",        "lat": 35.69, "lng": 139.70, "year": 1999},
    202: {"slug": "agartha",   "type": "remnant",    "number": "II",    "name_en": "Agartha",          "name_ja": "アガルタ",        "name_ko": "아가르타",       "lat": 0.0,   "lng": 0.0,   "year": 2000},
    203: {"slug": "shimosa",   "type": "remnant",    "number": "III",   "name_en": "Shimosa",          "name_ja": "下総国",          "name_ko": "시모사",        "lat": 35.70, "lng": 140.10, "year": 1639},
    204: {"slug": "salem",     "type": "remnant",    "number": "IV",    "name_en": "Salem",            "name_ja": "セイレム",        "name_ko": "세일럼",        "lat": 42.52, "lng": -70.90, "year": 1692},
    # Lostbelts
    301: {"slug": "lb1",   "type": "lostbelt", "number": "1",   "name_en": "Anastasia",        "name_ja": "アナスタシア",       "name_ko": "아나스타시아",    "lat": 55.75, "lng": 37.62, "year": 1570},
    302: {"slug": "lb2",   "type": "lostbelt", "number": "2",   "name_en": "Götterdämmerung",  "name_ja": "ゲッテルデメルング",   "name_ko": "괴터데머룽",     "lat": 63.0,  "lng": 15.0,  "year": -1000},
    303: {"slug": "lb3",   "type": "lostbelt", "number": "3",   "name_en": "SIN",              "name_ja": "シン",              "name_ko": "신",            "lat": 34.26, "lng": 108.94, "year": -210},
    304: {"slug": "lb4",   "type": "lostbelt", "number": "4",   "name_en": "Yuga Kshetra",     "name_ja": "ユガ・クシェートラ",   "name_ko": "유가 크셰트라",   "lat": 20.59, "lng": 78.96, "year": 11900},
    305: {"slug": "lb5",   "type": "lostbelt", "number": "5",   "name_en": "Atlantis/Olympus", "name_ja": "アトランティス/オリュンポス", "name_ko": "아틀란티스/올림포스", "lat": 37.97, "lng": 23.73, "year": -12000},
    306: {"slug": "lb5.5", "type": "lostbelt", "number": "5.5", "name_en": "Heian-kyo",        "name_ja": "平安京",             "name_ko": "헤이안쿄",       "lat": 35.01, "lng": 135.77, "year": -12000},
    308: {"slug": "lb6",   "type": "lostbelt", "number": "6",   "name_en": "Avalon le Fae",    "name_ja": "アヴァロン・ル・フェ",  "name_ko": "아발론 르 페",    "lat": 51.5,  "lng": -2.0,  "year": 500},
    311: {"slug": "lb7",   "type": "lostbelt", "number": "7",   "name_en": "Nahui Mictlan",    "name_ja": "ナウイ・ミクトラン",    "name_ko": "나우이 믹틀란",   "lat": 19.43, "lng": -99.13, "year": -2655},
}


# ─── Helpers ────────────────────────────────────────────

def load_json(path: Path) -> list | dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def analyze_speakers(data: dict) -> list[dict]:
    """Get top speakers from a story chapter."""
    counter: Counter = Counter()
    for spot in data.get("spots", []):
        for quest in spot.get("quests", []):
            for script in quest.get("scripts", []):
                for dlg in script.get("dialogues", []):
                    speaker = dlg.get("speaker", "")
                    if not speaker.startswith("__"):
                        counter[speaker] += 1
    return [{"name": n, "lines": c} for n, c in counter.most_common(20)]


# ─── Story Builder ──────────────────────────────────────

def build_stories():
    """Build structured story files from JP/NA scripts."""
    print("=" * 60)
    print("Building stories...")
    print("=" * 60)

    stories_dir = OUTPUT_DIR / "stories"
    stories_dir.mkdir(parents=True, exist_ok=True)

    story_index = []

    for war_id, meta in sorted(CHAPTER_META.items()):
        slug = meta["slug"]
        ctype = meta["type"]
        number = meta["number"]

        # Load JP, NA, and KR data
        jp_path = RAW_DIR / "scripts_jp" / f"{slug}_jp.json"
        na_path = RAW_DIR / "scripts" / f"{slug}_na.json"
        if not na_path.exists():
            na_path = RAW_DIR / "scripts_na" / f"{slug}_na.json"
        kr_path = RAW_DIR / "scripts_kr" / f"{slug}_kr.json"

        jp_data = load_json(jp_path)
        na_data = load_json(na_path)
        kr_data = load_json(kr_path)

        if not jp_data and not na_data:
            print(f"  SKIP {slug} (no data)")
            continue

        primary = jp_data or na_data  # JP is primary

        # Analyze
        speakers = analyze_speakers(primary) if primary else []
        total_dialogues = sum(
            s.get("dialogue_count", 0)
            for spot in primary.get("spots", [])
            for q in spot.get("quests", [])
            for s in q.get("scripts", [])
        ) if primary else 0
        total_scripts = sum(
            len(q.get("scripts", []))
            for spot in primary.get("spots", [])
            for q in spot.get("quests", [])
        ) if primary else 0

        # Build quest list (from JP primary, fallback to NA)
        quests = []
        for spot in primary.get("spots", []):
            for quest in spot.get("quests", []):
                q_dialogues = sum(s.get("dialogue_count", 0) for s in quest.get("scripts", []))
                quests.append({
                    "id": quest["id"],
                    "name_ja": quest["name"] if jp_data else None,
                    "name_en": None,  # Fill from NA below
                    "name_ko": None,  # Fill from KR below
                    "spot_ja": spot["name"] if jp_data else None,
                    "spot_en": None,
                    "spot_ko": None,
                    "scripts": len(quest.get("scripts", [])),
                    "dialogues": q_dialogues,
                })

        # Fill EN names from NA data
        if na_data:
            na_quests = {}
            for spot in na_data.get("spots", []):
                for quest in spot.get("quests", []):
                    na_quests[quest["id"]] = (quest["name"], spot["name"])
            for q in quests:
                if q["id"] in na_quests:
                    q["name_en"], q["spot_en"] = na_quests[q["id"]]

        # Fill KO names from KR data
        if kr_data:
            kr_quests = {}
            for spot in kr_data.get("spots", []):
                for quest in spot.get("quests", []):
                    kr_quests[quest["id"]] = (quest["name"], spot["name"])
            for q in quests:
                if q["id"] in kr_quests:
                    q["name_ko"], q["spot_ko"] = kr_quests[q["id"]]

        # Count KR dialogues
        kr_dialogues = 0
        kr_scripts = 0
        if kr_data:
            for spot in kr_data.get("spots", []):
                for q in spot.get("quests", []):
                    for s in q.get("scripts", []):
                        kr_scripts += 1
                        kr_dialogues += s.get("dialogue_count", 0)

        # Build story entry
        filename = f"{ctype}_{number}_{slug}.json"
        story = {
            "war_id": war_id,
            "slug": slug,
            "type": ctype,
            "number": number,
            "name": {
                "en": meta["name_en"],
                "ja": meta["name_ja"],
                "ko": meta["name_ko"],
            },
            "full_title": {
                "ja": primary.get("name_long", "") if jp_data else "",
                "en": na_data.get("name", "") if na_data else "",
                "ko": kr_data.get("name_long", "") if kr_data else "",
            },
            "year": meta["year"],
            "location": {
                "lat": meta["lat"],
                "lng": meta["lng"],
            },
            "stats": {
                "total_scripts": total_scripts,
                "total_dialogues": total_dialogues,
                "top_speakers": speakers[:15],
                "kr_scripts": kr_scripts,
                "kr_dialogues": kr_dialogues,
            },
            "languages": {
                "ja": jp_data is not None,
                "en": na_data is not None,
                "ko": kr_data is not None,
            },
            "quests": quests,
            # Raw scripts embedded (JP primary)
            "spots": primary.get("spots", []),
        }

        save_json(story, stories_dir / filename)
        kr_flag = f"  KR={kr_dialogues}" if kr_data else ""
        print(f"  {filename:45s} scripts={total_scripts:4d}  dialogues={total_dialogues:5d}{kr_flag}")

        # Index entry (without raw scripts)
        story_index.append({
            "war_id": war_id,
            "slug": slug,
            "type": ctype,
            "number": number,
            "name": story["name"],
            "full_title": story["full_title"],
            "year": meta["year"],
            "location": story["location"],
            "stats": story["stats"],
            "languages": story["languages"],
            "file": filename,
        })

    save_json(story_index, stories_dir / "index.json")
    print(f"\n  Story index: {len(story_index)} chapters → stories/index.json")
    return story_index


# ─── Servant Builder ───────────────────────────────────

def build_servants():
    """Build servant DB from profiles + basic info."""
    print("\n" + "=" * 60)
    print("Building servants...")
    print("=" * 60)

    servants_dir = OUTPUT_DIR / "servants"
    by_id_dir = servants_dir / "by_id"
    by_id_dir.mkdir(parents=True, exist_ok=True)

    # Load raw data
    basic_jp = load_json(RAW_DIR / "servants_basic_jp.json") or []
    basic_na = load_json(RAW_DIR / "servants_basic_na.json") or []
    basic_kr = load_json(RAW_DIR / "servants_basic_kr.json") or []
    profiles_jp = load_json(RAW_DIR / "servant_profiles_jp.json") or []
    # NA profiles are in materials/ subfolder (previously collected)
    profiles_na = load_json(RAW_DIR / "servant_profiles_na.json") or \
                  load_json(RAW_DIR / "materials" / "servant_profiles_na.json") or []
    profiles_kr = load_json(RAW_DIR / "servant_profiles_kr.json") or []
    person_mapping = load_json(RAW_DIR / "servant_person_mapping.json") or {}

    # Build lookups
    jp_lookup = {s["id"]: s for s in basic_jp}
    na_lookup = {s["id"]: s for s in basic_na}
    kr_lookup = {s["id"]: s for s in basic_kr}
    profiles_jp_lookup = {p["id"]: p for p in profiles_jp}
    profiles_na_lookup = {p["id"]: p for p in profiles_na}
    profiles_kr_lookup = {p["id"]: p for p in profiles_kr}

    # Build person mapping lookup: fgo_name → person data
    person_by_name = {}
    for m in person_mapping.get("matched", []):
        key = f"{m['fgo_name']}_{m['fgo_class']}"
        person_by_name[key] = {
            "person_id": m.get("person_id"),
            "person_name": m.get("person_name"),
            "person_name_ko": m.get("person_name_ko"),
            "wikidata_id": m.get("wikidata_id"),
            "birth_year": m.get("birth_year"),
            "death_year": m.get("death_year"),
        }

    # Merge all servant IDs
    all_ids = sorted(set(list(jp_lookup.keys()) + list(na_lookup.keys())))
    print(f"  Total servant IDs: {len(all_ids)}")

    index = []
    written = 0

    for sid in all_ids:
        jp_basic = jp_lookup.get(sid, {})
        na_basic = na_lookup.get(sid, {})
        kr_basic = kr_lookup.get(sid, {})
        jp_profile = profiles_jp_lookup.get(sid, {})
        na_profile = profiles_na_lookup.get(sid, {})
        kr_profile = profiles_kr_lookup.get(sid, {})

        # Skip non-playable
        stype = jp_basic.get("type") or na_basic.get("type", "")
        if stype not in ("normal", "heroine"):
            continue

        name_ja = jp_basic.get("name", "")
        name_en = na_basic.get("name", "")
        name_ko = kr_basic.get("name", "")
        class_name = jp_basic.get("className") or na_basic.get("className", "")
        rarity = jp_basic.get("rarity") or na_basic.get("rarity")
        collection_no = jp_basic.get("collectionNo") or na_basic.get("collectionNo")

        # Historical person link
        key = f"{name_en}_{class_name}"
        person = person_by_name.get(key)

        # Build individual file
        servant = {
            "id": sid,
            "collectionNo": collection_no,
            "name": {
                "ja": name_ja,
                "en": name_en,
                "ko": name_ko,
            },
            "className": class_name,
            "rarity": rarity,
            "gender": jp_basic.get("gender") or na_basic.get("gender", ""),
            "attribute": jp_basic.get("attribute") or na_basic.get("attribute", ""),
            "profile": {
                "cv": jp_profile.get("cv", ""),
                "illustrator": jp_profile.get("illustrator", ""),
                "stats": jp_profile.get("stats") or na_profile.get("stats", {}),
            },
            "bond_text": {
                "ja": [c.get("comment", "") for c in jp_profile.get("comments", [])],
                "en": [c.get("comment", "") for c in na_profile.get("comments", [])],
                "ko": [c.get("comment", "") for c in kr_profile.get("comments", [])],
            },
            "historical_person": person,
            # Face icon URL (for display)
            "icon_url": f"https://static.atlasacademy.io/JP/Faces/f_{sid // 100:07d}0.png",
        }

        save_json(servant, by_id_dir / f"{sid}.json")
        written += 1

        # Index entry
        index.append({
            "id": sid,
            "collectionNo": collection_no,
            "name_ja": name_ja,
            "name_en": name_en,
            "name_ko": name_ko,
            "className": class_name,
            "rarity": rarity,
            "has_jp_profile": len(jp_profile.get("comments", [])) > 0,
            "has_na_profile": len(na_profile.get("comments", [])) > 0,
            "has_kr_profile": len(kr_profile.get("comments", [])) > 0,
            "has_person_link": person is not None,
            "person_name": person.get("person_name") if person else None,
        })

    save_json(index, servants_dir / "index.json")
    print(f"  Written: {written} servant files → servants/by_id/")
    print(f"  Index: {len(index)} entries → servants/index.json")

    # Stats
    with_jp = sum(1 for e in index if e["has_jp_profile"])
    with_na = sum(1 for e in index if e["has_na_profile"])
    with_kr = sum(1 for e in index if e["has_kr_profile"])
    with_person = sum(1 for e in index if e["has_person_link"])
    print(f"  JP profiles: {with_jp}, NA profiles: {with_na}, KR profiles: {with_kr}, person links: {with_person}")

    return index


# ─── Mappings Builder ──────────────────────────────────

def build_mappings():
    """Build convenience mappings for cross-referencing."""
    print("\n" + "=" * 60)
    print("Building mappings...")
    print("=" * 60)

    mappings_dir = OUTPUT_DIR / "mappings"
    mappings_dir.mkdir(parents=True, exist_ok=True)

    # 1. Servant → Person mapping (cleaned up)
    raw_mapping = load_json(RAW_DIR / "servant_person_mapping.json") or {}
    matched = raw_mapping.get("matched", [])

    servant_to_person = []
    for m in matched:
        servant_to_person.append({
            "fgo_name_en": m.get("fgo_name"),
            "fgo_class": m.get("fgo_class"),
            "fgo_rarity": m.get("fgo_rarity"),
            "person_id": m.get("person_id"),
            "person_name": m.get("person_name"),
            "person_name_ko": m.get("person_name_ko"),
            "wikidata_id": m.get("wikidata_id"),
            "birth_year": m.get("birth_year"),
            "death_year": m.get("death_year"),
        })

    save_json(servant_to_person, mappings_dir / "servant_to_person.json")
    print(f"  servant_to_person.json: {len(servant_to_person)} mappings")

    # 2. Story locations mapping
    story_locations = []
    for war_id, meta in sorted(CHAPTER_META.items()):
        story_locations.append({
            "war_id": war_id,
            "slug": meta["slug"],
            "type": meta["type"],
            "number": meta["number"],
            "name_en": meta["name_en"],
            "name_ja": meta["name_ja"],
            "name_ko": meta["name_ko"],
            "year": meta["year"],
            "lat": meta["lat"],
            "lng": meta["lng"],
        })

    save_json(story_locations, mappings_dir / "story_locations.json")
    print(f"  story_locations.json: {len(story_locations)} chapters")


# ─── Main ───────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build FGO local database")
    parser.add_argument("--only", choices=["stories", "servants", "mappings"])
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    story_count = 0
    servant_count = 0

    if not args.only or args.only == "stories":
        story_index = build_stories()
        story_count = len(story_index)

    if not args.only or args.only == "servants":
        servant_index = build_servants()
        servant_count = len(servant_index)

    if not args.only or args.only == "mappings":
        build_mappings()

    # Meta file
    if not args.only:
        meta = {
            "version": "1.0",
            "built_at": datetime.now().isoformat(),
            "source": "Atlas Academy API (api.atlasacademy.io)",
            "primary_language": "ja",
            "secondary_languages": ["en", "ko"],
            "stories": story_count,
            "servants": servant_count,
            "structure": {
                "stories/": "각 특이점/이문대 스토리 (대사 포함)",
                "stories/index.json": "스토리 인덱스 (메타데이터만)",
                "servants/index.json": "서번트 인덱스 (요약)",
                "servants/by_id/": "개별 서번트 상세 (JP+NA 프로필)",
                "mappings/": "서번트↔역사인물, 스토리↔좌표 매핑",
            },
        }
        save_json(meta, OUTPUT_DIR / "meta.json")
        print(f"\n  meta.json saved")

    print(f"\nDone! Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
