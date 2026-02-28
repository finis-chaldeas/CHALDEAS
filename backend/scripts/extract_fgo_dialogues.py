"""
FGO Character Dialogue Extractor
=================================
FGO 스토리 데이터에서 캐릭터별 대사를 추출.
AI 불필요, 로컬 처리만. 비용 $0.

입력:
    E:/chaldeas_data/raw/atlas_academy/scripts_jp/*_jp.json  — 메인 스토리 (Atlas Academy)
    E:/chaldeas_data/raw/atlas_academy/scripts_jp_events/event_*_jp.json  — JP 이벤트

출력:
    E:/chaldeas_data/processed/fgo/dialogues/
        by_chapter/
            fuyuki.json, event_9001.json, ...
        by_character/
            mash_kyrielight.json, gilgamesh.json, ...
        stats.json
        alias_map.json

사용법:
    python -m scripts.extract_fgo_dialogues                    # 전체 실행
    python -m scripts.extract_fgo_dialogues --main-only        # 메인 스토리만
    python -m scripts.extract_fgo_dialogues --events-only      # 이벤트만
    python -m scripts.extract_fgo_dialogues --chapter fuyuki   # 단일 챕터
    python -m scripts.extract_fgo_dialogues --stats            # 통계만 표시
    python -m scripts.extract_fgo_dialogues --dry-run          # 미리보기
"""

import argparse
import io
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# Windows UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── Paths ──────────────────────────────────────────────

STORIES_DIR = Path(r"E:\chaldeas_data\raw\atlas_academy\scripts_jp")
EVENTS_DIR = Path(r"E:\chaldeas_data\raw\atlas_academy\scripts_jp_events")
OUTPUT_DIR = Path(r"E:\chaldeas_data\processed\fgo\dialogues")

# ─── Helpers ────────────────────────────────────────────

def load_json(path: Path) -> list | dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ─── Text Cleanup ───────────────────────────────────────

def clean_dialogue_text(text: str) -> str:
    """Clean inline markup from dialogue text."""
    # [%1] → [主人公] (player name placeholder)
    text = text.replace("[%1]", "[主人公]")
    # [&male:female] → male/female
    text = re.sub(r"\[&([^:]+):([^\]]+)\]", r"\1/\2", text)
    # [#kanji:furigana] → kanji (remove ruby)
    text = re.sub(r"\[#([^:]+):[^\]]+\]", r"\1", text)
    # Remove visual effect tags: [f small], [f -], [s N], [shake ...], etc.
    text = re.sub(r"\[(f [^\]]*|s \d+|shake[^\]]*|wipein[^\]]*|wipeout[^\]]*|bgm[^\]]*|messageShake[^\]]*|charaMoveReturn[^\]]*|communicationCharaFace[^\]]*)\]", "", text)
    # Remove color tags: [FFFFFF]..[-]
    text = re.sub(r"\[[0-9A-Fa-f]{6}\]", "", text)
    text = text.replace("[-]", "")
    return text.strip()


def clean_speaker_name(speaker: str) -> str:
    """Clean color tags and whitespace from speaker names."""
    # Remove [FFFFFF]..[-] color wrapping
    speaker = re.sub(r"\[[0-9A-Fa-f]{6}\]", "", speaker)
    speaker = speaker.replace("[-]", "")
    return speaker.strip()


# ─── Speaker Classification ────────────────────────────

SKIP_SPEAKERS = {
    "__player_choice_1__",
    "__player_choice_2__",
    "__player_choice_3__",
    "__player_reaction__",
}

NARRATION_SPEAKERS = {"__narration__"}

PLAYER_SPEAKERS = {"[%1]", "[主人公]", "藤丸立香"}


def classify_speaker(speaker: str) -> str:
    """Classify a speaker: 'skip', 'narration', 'player', 'unknown', or 'character'."""
    if speaker in SKIP_SPEAKERS:
        return "skip"
    if speaker in NARRATION_SPEAKERS:
        return "narration"
    if speaker in PLAYER_SPEAKERS:
        return "player"
    if speaker == "？？？" or speaker == "???":
        return "unknown"
    if speaker == "":
        return "skip"
    return "character"


# ─── Alias Map ──────────────────────────────────────────
# 같은 캐릭터가 다른 이름으로 등장하는 케이스를 정규화.
# key=alias, value=canonical name (JP)

GLOBAL_ALIASES = {
    # Core Chaldea staff
    "マシュ": "マシュ・キリエライト",
    "Dr.ロマン": "ロマニ・アーキマン",
    "Dr．ロマン": "ロマニ・アーキマン",
    "ドクター・ロマン": "ロマニ・アーキマン",
    "ロマン": "ロマニ・アーキマン",
    "ロマニ": "ロマニ・アーキマン",
    "ダ・ヴィンチ": "レオナルド・ダ・ヴィンチ",
    "ダ・ヴィンチちゃん": "レオナルド・ダ・ヴィンチ",
    "ホームズ": "シャーロック・ホームズ",
    "ゴルドルフ": "ゴルドルフ・ムジーク",
    "ゴルドルフ新所長": "ゴルドルフ・ムジーク",
    "新所長": "ゴルドルフ・ムジーク",
    "シオン": "シオン・エルトナム・ソカリス",
    "オルガマリー": "オルガマリー・アニムスフィア",
    "所長": "オルガマリー・アニムスフィア",
    "レフ": "レフ・ライノール",
    "フォウ": "フォウ",
    "フォウさん": "フォウ",
    # Common shortenings
    "ジャンヌ": "ジャンヌ・ダルク",
    "ジャンヌ・オルタ": "ジャンヌ・ダルク〔オルタ〕",
    "邪ンヌ": "ジャンヌ・ダルク〔オルタ〕",
    "エミヤ": "エミヤ",
    "ギル": "ギルガメッシュ",
    "アルトリア": "アルトリア・ペンドラゴン",
    "スカサハ": "スカサハ",
    "クー・フーリン": "クー・フーリン",
    "イシュタル": "イシュタル",
    "エレシュキガル": "エレシュキガル",
    "マーリン": "マーリン",
    "モードレッド": "モードレッド",
    "ベディヴィエール": "ベディヴィエール",
    "ガウェイン": "ガウェイン",
    "ランスロット": "ランスロット",
    "トリスタン": "トリスタン",
    "アーラシュ": "アーラシュ",
    "ニトクリス": "ニトクリス",
    "牛若丸": "牛若丸",
    "弁慶": "武蔵坊弁慶",
    "レオニダス": "レオニダス一世",
}

# Chapter-specific aliases (war_id → {alias: canonical})
CHAPTER_ALIASES = {
    # Fuyuki
    100: {
        "キャスター": "クー・フーリン",
        "セイバー": "アルトリア・ペンドラゴン〔オルタ〕",
        "ランサー": "メドゥーサ",
        "アーチャー": "エミヤ",
    },
    # Orleans
    101: {
        "ルーラー": "ジャンヌ・ダルク",
        "竜の魔女": "ジャンヌ・ダルク〔オルタ〕",
    },
    # Septem
    102: {
        "セイバー": "ネロ・クラウディウス",
    },
    # Okeanos
    103: {
        "ライダー": "フランシス・ドレイク",
    },
    # London
    104: {
        "モードレッド": "モードレッド",
    },
    # America
    105: {
        "ランサー": "エリザベート・バートリー",
    },
    # Camelot
    106: {
        "山の翁": "キングハサン",
        "獅子王": "アルトリア・ペンドラゴン",
    },
    # Babylonia
    107: {
        "キャスター": "ギルガメッシュ",
        "賢王": "ギルガメッシュ",
        "ケツァル・コアトル": "ケツァル・コアトル",
        "エルキドゥ": "エルキドゥ",
        "キングゥ": "キングゥ",
        "ジャガーマン": "ジャガーマン",
        "アナ": "アナ",
        "ゴルゴーン": "ゴルゴーン",
        "ティアマト": "ティアマト",
    },
    # Solomon
    108: {},
    # Shinjuku
    201: {
        "アーチャー": "ジェームズ・モリアーティ",
        "アサシン": "燕青",
        "バーサーカー": "ヘシアン・ロボ",
    },
    # Agartha
    202: {},
    # Shimosa
    203: {
        "セイバー": "宮本武蔵",
    },
    # Salem
    204: {},
    # LB1 Anastasia
    301: {
        "キャスター": "アナスタシア",
        "カドック": "カドック・ゼムルプス",
    },
    # LB2
    302: {
        "スカディ": "スカサハ＝スカディ",
        "オフェリア": "オフェリア・ファムルソローネ",
    },
    # LB3 SIN
    303: {
        "始皇帝": "始皇帝",
    },
    # LB4
    304: {},
    # LB5
    305: {
        "キリシュタリア": "キリシュタリア・ヴォーダイム",
    },
    # LB5.5
    306: {},
    # LB6
    308: {
        "キャストリア": "アルトリア・キャスター",
        "モルガン": "モルガン",
        "オベロン": "オベロン",
    },
    # LB7
    311: {},
}


def resolve_speaker(speaker: str, war_id: int | None = None) -> str:
    """Resolve a speaker name through alias maps."""
    speaker = clean_speaker_name(speaker)

    # Chapter-specific alias first (higher priority)
    if war_id and war_id in CHAPTER_ALIASES:
        if speaker in CHAPTER_ALIASES[war_id]:
            return CHAPTER_ALIASES[war_id][speaker]

    # Global alias
    if speaker in GLOBAL_ALIASES:
        return GLOBAL_ALIASES[speaker]

    return speaker


def speaker_to_filename(name_ja: str) -> str:
    """Convert JP speaker name to a safe filename slug."""
    # Try to romanize common names; fallback to sanitized JP
    slug = name_ja.lower()
    # Remove special chars
    slug = re.sub(r"[・〔〕（）\[\]【】「」『』\s]+", "_", slug)
    slug = re.sub(r"[^\w]", "", slug, flags=re.UNICODE)
    slug = slug.strip("_")
    return slug or "unknown"


# ─── Core Extraction ───────────────────────────────────

def extract_chapter_dialogues(data: dict, war_id: int | None = None) -> dict:
    """Extract all dialogues from a chapter/event, organized by speaker."""

    characters = defaultdict(lambda: {
        "lines": 0,
        "word_count": 0,
        "quests": set(),
        "sample_lines": [],
    })
    narration_count = 0
    unknown_count = 0
    player_count = 0
    skip_count = 0
    total_lines = 0
    alias_used = {}  # original → resolved

    for spot in data.get("spots", []):
        for quest in spot.get("quests", []):
            quest_id = quest.get("id", 0)
            quest_name = quest.get("name", "")

            for script in quest.get("scripts", []):
                for dlg in script.get("dialogues", []):
                    total_lines += 1
                    raw_speaker = dlg.get("speaker", "")
                    text = dlg.get("text", "")

                    classification = classify_speaker(raw_speaker)

                    if classification == "skip":
                        skip_count += 1
                        continue
                    if classification == "narration":
                        narration_count += 1
                        continue
                    if classification == "player":
                        player_count += 1
                        continue
                    if classification == "unknown":
                        unknown_count += 1
                        # Still track ？？？ under a generic key per quest
                        # (they often get revealed later but we can't auto-resolve)
                        continue

                    # Resolve alias
                    cleaned = clean_speaker_name(raw_speaker)
                    resolved = resolve_speaker(raw_speaker, war_id)

                    if cleaned != resolved:
                        alias_used[cleaned] = resolved

                    # Clean text
                    cleaned_text = clean_dialogue_text(text)

                    # Accumulate
                    char = characters[resolved]
                    char["lines"] += 1
                    char["word_count"] += len(cleaned_text)
                    char["quests"].add(quest_id)
                    if len(char["sample_lines"]) < 5:
                        char["sample_lines"].append({
                            "quest_id": quest_id,
                            "quest_name": quest_name,
                            "text": cleaned_text[:200],  # Truncate for samples
                        })

    # Convert sets to sorted lists for JSON serialization
    result_characters = []
    for name, info in sorted(characters.items(), key=lambda x: -x[1]["lines"]):
        result_characters.append({
            "name_ja": name,
            "lines": info["lines"],
            "word_count": info["word_count"],
            "quest_count": len(info["quests"]),
            "quests": sorted(info["quests"]),
            "sample_lines": info["sample_lines"],
        })

    return {
        "characters": result_characters,
        "stats": {
            "total_lines": total_lines,
            "character_lines": sum(c["lines"] for c in result_characters),
            "narration_lines": narration_count,
            "unknown_lines": unknown_count,
            "player_lines": player_count,
            "skipped_lines": skip_count,
            "unique_characters": len(result_characters),
        },
        "aliases_used": alias_used,
    }


# ─── Data Loading ──────────────────────────────────────

def load_main_stories(chapter_filter: str | None = None) -> list[tuple[str, int | None, dict]]:
    """Load main story files. Returns list of (slug, war_id, data)."""
    stories = []
    if not STORIES_DIR.exists():
        print(f"  WARNING: Stories directory not found: {STORIES_DIR}")
        return stories

    # lb5_jp = lb5_atlantis_jp (same quests), lb5.5_jp = lb5_olympus_jp (same quests)
    skip_dupes = {"main_story_jp.json", "lb5_jp.json", "lb5.5_jp.json"}
    for path in sorted(STORIES_DIR.glob("*_jp.json")):
        if path.name in skip_dupes:
            continue
        data = load_json(path)
        if not data:
            continue

        slug = data.get("id", path.stem.replace("_jp", ""))
        war_id = data.get("warId")

        if chapter_filter and slug != chapter_filter:
            continue

        stories.append((slug, war_id, data))

    return stories


def load_events(chapter_filter: str | None = None) -> list[tuple[str, int | None, dict]]:
    """Load event script files. Returns list of (slug, war_id, data)."""
    events = []
    if not EVENTS_DIR.exists():
        print(f"  WARNING: Events directory not found: {EVENTS_DIR}")
        return events

    for path in sorted(EVENTS_DIR.glob("event_*_jp.json")):
        data = load_json(path)
        if not data:
            continue

        war_id = data.get("warId")
        slug = data.get("id", f"event_{war_id}")

        # Skip empty events (no dialogues)
        has_dialogues = False
        for spot in data.get("spots", []):
            for quest in spot.get("quests", []):
                for script in quest.get("scripts", []):
                    if script.get("dialogue_count", 0) > 0:
                        has_dialogues = True
                        break
                if has_dialogues:
                    break
            if has_dialogues:
                break
        if not has_dialogues:
            continue

        if chapter_filter and slug != chapter_filter:
            continue

        events.append((slug, war_id, data))

    return events


# ─── Cross-Character Aggregation ───────────────────────

def aggregate_by_character(all_chapters: dict) -> dict:
    """Aggregate character data across all chapters."""
    characters = defaultdict(lambda: {
        "total_lines": 0,
        "total_word_count": 0,
        "chapters": [],
    })

    for chapter_slug, chapter_data in all_chapters.items():
        for char in chapter_data["characters"]:
            name = char["name_ja"]
            characters[name]["total_lines"] += char["lines"]
            characters[name]["total_word_count"] += char["word_count"]
            characters[name]["chapters"].append({
                "slug": chapter_slug,
                "lines": char["lines"],
                "word_count": char["word_count"],
                "quest_count": char["quest_count"],
            })

    return dict(characters)


# ─── Main Pipeline ─────────────────────────────────────

def run_extraction(
    main_only: bool = False,
    events_only: bool = False,
    chapter_filter: str | None = None,
    dry_run: bool = False,
    stats_only: bool = False,
):
    print("=" * 60)
    print("FGO Dialogue Extraction")
    print("=" * 60)

    # Load sources
    sources = []

    if not events_only:
        print(f"\nLoading main stories from {STORIES_DIR}...")
        main_stories = load_main_stories(chapter_filter)
        print(f"  Found {len(main_stories)} main story chapters")
        sources.extend(("main", s, w, d) for s, w, d in main_stories)

    if not main_only:
        print(f"\nLoading events from {EVENTS_DIR}...")
        events = load_events(chapter_filter)
        print(f"  Found {len(events)} events with dialogues")
        sources.extend(("event", s, w, d) for s, w, d in events)

    if not sources:
        print("\nNo data sources found!")
        return

    print(f"\nTotal sources: {len(sources)}")

    if dry_run:
        # Quick preview
        total_dialogues = 0
        for source_type, slug, war_id, data in sources:
            count = sum(
                s.get("dialogue_count", 0)
                for spot in data.get("spots", [])
                for q in spot.get("quests", [])
                for s in q.get("scripts", [])
            )
            total_dialogues += count
            print(f"  [{source_type:5s}] {slug:40s} ~{count:,} lines")
        print(f"\n  Total: ~{total_dialogues:,} dialogue lines to process")
        print("  (dry-run, no files written)")
        return

    # Extract per-chapter
    all_chapters = {}
    all_aliases = {}

    print(f"\nExtracting dialogues...")
    for source_type, slug, war_id, data in sources:
        result = extract_chapter_dialogues(data, war_id)
        all_chapters[slug] = result

        stats = result["stats"]
        char_count = stats["unique_characters"]
        line_count = stats["character_lines"]
        print(f"  [{source_type:5s}] {slug:40s} {char_count:3d} characters, {line_count:6,} lines")

        # Collect aliases
        all_aliases.update(result["aliases_used"])

    # Stats summary
    total_chars = len(set(
        c["name_ja"]
        for ch in all_chapters.values()
        for c in ch["characters"]
    ))
    total_lines = sum(ch["stats"]["character_lines"] for ch in all_chapters.values())
    total_narration = sum(ch["stats"]["narration_lines"] for ch in all_chapters.values())
    total_unknown = sum(ch["stats"]["unknown_lines"] for ch in all_chapters.values())

    print(f"\n{'─' * 60}")
    print(f"  Unique characters: {total_chars:,}")
    print(f"  Character lines:   {total_lines:,}")
    print(f"  Narration lines:   {total_narration:,}")
    print(f"  Unknown (？？？):   {total_unknown:,}")
    print(f"  Aliases resolved:  {len(all_aliases)}")

    if stats_only:
        # Print top speakers
        char_agg = aggregate_by_character(all_chapters)
        top = sorted(char_agg.items(), key=lambda x: -x[1]["total_lines"])[:30]
        print(f"\n  Top 30 speakers:")
        for i, (name, info) in enumerate(top, 1):
            ch_count = len(info["chapters"])
            print(f"    {i:2d}. {name:30s} {info['total_lines']:6,} lines  ({ch_count} chapters)")
        return

    # ─── Write output ──────────────────────────────────

    print(f"\nWriting output to {OUTPUT_DIR}...")

    # 1. by_chapter/
    by_chapter_dir = OUTPUT_DIR / "by_chapter"
    for slug, chapter_data in all_chapters.items():
        save_json({
            "slug": slug,
            "extracted_at": datetime.now().isoformat(),
            "stats": chapter_data["stats"],
            "characters": chapter_data["characters"],
        }, by_chapter_dir / f"{slug}.json")
    print(f"  by_chapter/: {len(all_chapters)} files")

    # 2. by_character/
    by_char_dir = OUTPUT_DIR / "by_character"
    char_agg = aggregate_by_character(all_chapters)
    for name_ja, info in char_agg.items():
        filename = speaker_to_filename(name_ja) + ".json"
        save_json({
            "name_ja": name_ja,
            "total_lines": info["total_lines"],
            "total_word_count": info["total_word_count"],
            "chapter_count": len(info["chapters"]),
            "chapters": sorted(info["chapters"], key=lambda x: -x["lines"]),
        }, by_char_dir / filename)
    print(f"  by_character/: {len(char_agg)} files")

    # 3. stats.json
    top_speakers = sorted(char_agg.items(), key=lambda x: -x[1]["total_lines"])
    save_json({
        "extracted_at": datetime.now().isoformat(),
        "sources": {
            "main_chapters": sum(1 for t, *_ in sources if t == "main"),
            "events": sum(1 for t, *_ in sources if t == "event"),
        },
        "totals": {
            "unique_characters": total_chars,
            "character_lines": total_lines,
            "narration_lines": total_narration,
            "unknown_lines": total_unknown,
            "aliases_resolved": len(all_aliases),
        },
        "top_speakers": [
            {
                "rank": i,
                "name_ja": name,
                "total_lines": info["total_lines"],
                "total_word_count": info["total_word_count"],
                "chapter_count": len(info["chapters"]),
            }
            for i, (name, info) in enumerate(top_speakers[:50], 1)
        ],
    }, OUTPUT_DIR / "stats.json")
    print(f"  stats.json")

    # 4. alias_map.json
    save_json({
        "description": "Speaker alias resolutions applied during extraction",
        "global_aliases": dict(GLOBAL_ALIASES),
        "chapter_aliases": {str(k): v for k, v in CHAPTER_ALIASES.items()},
        "aliases_actually_used": all_aliases,
    }, OUTPUT_DIR / "alias_map.json")
    print(f"  alias_map.json ({len(all_aliases)} aliases used)")

    print(f"\nDone! Output: {OUTPUT_DIR}")

    # Print top 10 for quick verification
    print(f"\n  Top 10 speakers (across all sources):")
    for i, (name, info) in enumerate(top_speakers[:10], 1):
        ch_count = len(info["chapters"])
        print(f"    {i:2d}. {name:30s} {info['total_lines']:6,} lines  ({ch_count} chapters)")


# ─── CLI ────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Extract FGO character dialogues")
    parser.add_argument("--main-only", action="store_true", help="Main stories only")
    parser.add_argument("--events-only", action="store_true", help="Events only")
    parser.add_argument("--chapter", type=str, help="Single chapter slug (e.g. fuyuki, event_9001)")
    parser.add_argument("--stats", action="store_true", help="Show stats only, don't write files")
    parser.add_argument("--dry-run", action="store_true", help="Preview without processing")
    args = parser.parse_args()

    run_extraction(
        main_only=args.main_only,
        events_only=args.events_only,
        chapter_filter=args.chapter,
        dry_run=args.dry_run,
        stats_only=args.stats,
    )


if __name__ == "__main__":
    main()
