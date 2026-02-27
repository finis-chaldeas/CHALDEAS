"""
FGO Catalog Builder
====================
수집된 JP/NA 스크립트 + 서번트 데이터를 합쳐서
트리스메기스토스 포털용 구조화된 카탈로그를 생성.

사용법:
    python -m scripts.build_fgo_catalog
    python -m scripts.build_fgo_catalog --only singularities
    python -m scripts.build_fgo_catalog --only servants

출력:
    E:/chaldeas_data/processed/fgo/
        catalog.json             — 전체 통합 카탈로그
        singularities.json       — 특이점 카탈로그
        lostbelts.json           — 이문대 카탈로그
        servants.json            — 서번트 카탈로그 (역사 인물 매핑 포함)
        story_summary.json       — 각 챕터별 스토리 요약 (대사 통계, 주요 캐릭터)
"""

import argparse
import io
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

# Windows UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── Paths ──────────────────────────────────────────────

RAW_DIR = Path(r"E:\chaldeas_data\raw\atlas_academy")
SCRIPTS_NA_DIR = RAW_DIR / "scripts"
SCRIPTS_JP_DIR = RAW_DIR / "scripts_jp"
OUTPUT_DIR = Path(r"E:\chaldeas_data\processed\fgo")

# ─── Chapter metadata (수동 큐레이션) ───────────────────

SINGULARITY_META = {
    "fuyuki": {
        "number": "F",
        "subtitle_en": "Flame Contaminated City: Fuyuki",
        "subtitle_ja": "炎上汚染都市 冬木",
        "subtitle_ko": "염상오염도시 후유키",
        "location": "Fuyuki, Japan",
        "location_ja": "冬木市、日本",
        "location_ko": "후유키시, 일본",
        "lat": 34.38, "lng": 131.60,
        "year": 2004,
        "historical_context": "Modern Japan (Fuyuki City — Holy Grail War site)",
        "historical_context_ja": "現代日本（冬木市 — 聖杯戦争の舞台）",
        "key_servants": ["Mash Kyrielight", "Cu Chulainn", "Medusa"],
        "key_servants_ja": ["マシュ・キリエライト", "クー・フーリン", "メドゥーサ"],
    },
    "orleans": {
        "number": "I",
        "subtitle_en": "Hundred Years' War of the Evil Dragons: Orleans",
        "subtitle_ja": "邪竜百年戦争 オルレアン",
        "subtitle_ko": "사룡백년전쟁 오를레앙",
        "location": "France",
        "location_ja": "フランス",
        "location_ko": "프랑스",
        "lat": 47.90, "lng": 1.90,
        "year": 1431,
        "historical_context": "Hundred Years' War — Trial and execution of Joan of Arc",
        "historical_context_ja": "百年戦争 — ジャンヌ・ダルクの裁判と処刑",
        "key_servants": ["Jeanne d'Arc", "Marie Antoinette", "Amadeus Mozart", "Gilles de Rais"],
        "key_servants_ja": ["ジャンヌ・ダルク", "マリー・アントワネット", "アマデウス・モーツァルト", "ジル・ド・レェ"],
    },
    "septem": {
        "number": "II",
        "subtitle_en": "Eternal Madness Empire: Septem",
        "subtitle_ja": "永続狂気帝国 セプテム",
        "subtitle_ko": "영속광기제국 세프템",
        "location": "Roman Empire",
        "location_ja": "ローマ帝国",
        "location_ko": "로마 제국",
        "lat": 41.89, "lng": 12.49,
        "year": 60,
        "historical_context": "Reign of Emperor Nero — Roman Empire at its peak",
        "historical_context_ja": "ネロ帝の治世 — ローマ帝国の最盛期",
        "key_servants": ["Nero Claudius", "Romulus", "Boudica", "Alexander"],
        "key_servants_ja": ["ネロ・クラウディウス", "ロムルス", "ブーディカ", "アレキサンダー"],
    },
    "okeanos": {
        "number": "III",
        "subtitle_en": "Sealed Ends of the Four Seas: Okeanos",
        "subtitle_ja": "封鎖終局四海 オケアノス",
        "subtitle_ko": "봉쇄종국사해 오케아노스",
        "location": "Atlantic Ocean / Caribbean",
        "location_ja": "大西洋 / カリブ海",
        "location_ko": "대서양 / 카리브해",
        "lat": 20.0, "lng": -60.0,
        "year": 1573,
        "historical_context": "Age of Exploration — Piracy and colonial expansion",
        "historical_context_ja": "大航海時代 — 海賊と植民地拡大",
        "key_servants": ["Francis Drake", "Euryale", "Asterios", "Hektor"],
        "key_servants_ja": ["フランシス・ドレイク", "エウリュアレ", "アステリオス", "ヘクトール"],
    },
    "london": {
        "number": "IV",
        "subtitle_en": "The Mist City: London",
        "subtitle_ja": "死界魔霧都市 ロンドン",
        "subtitle_ko": "사계마무도시 런던",
        "location": "London, England",
        "location_ja": "ロンドン、イギリス",
        "location_ko": "런던, 영국",
        "lat": 51.51, "lng": -0.12,
        "year": 1888,
        "historical_context": "Victorian Era — Jack the Ripper, Industrial Revolution",
        "historical_context_ja": "ヴィクトリア朝 — 切り裂きジャック、産業革命",
        "key_servants": ["Mordred", "Nikola Tesla", "Tamamo-no-Mae", "Kintoki"],
        "key_servants_ja": ["モードレッド", "ニコラ・テスラ", "玉藻の前", "坂田金時"],
    },
    "america": {
        "number": "V",
        "subtitle_en": "North American Myth War: E Pluribus Unum",
        "subtitle_ja": "北米神話大戦 イ・プルーリバス・ウナム",
        "subtitle_ko": "북미신화대전 이 플루리버스 우넘",
        "location": "North America",
        "location_ja": "北アメリカ",
        "location_ko": "북아메리카",
        "lat": 39.0, "lng": -98.0,
        "year": 1783,
        "historical_context": "American Revolution and Celtic mythology",
        "historical_context_ja": "アメリカ独立戦争とケルト神話",
        "key_servants": ["Cu Chulainn (Alter)", "Scathach", "Rama", "Nightingale"],
        "key_servants_ja": ["クー・フーリン〔オルタ〕", "スカサハ", "ラーマ", "ナイチンゲール"],
    },
    "camelot": {
        "number": "VI",
        "subtitle_en": "The Sacred Round Table Realm: Camelot",
        "subtitle_ja": "神聖円卓領域 キャメロット",
        "subtitle_ko": "신성원탁영역 캬멜롯",
        "location": "Jerusalem / Holy Land",
        "location_ja": "エルサレム / 聖地",
        "location_ko": "예루살렘 / 성지",
        "lat": 31.77, "lng": 35.23,
        "year": 1273,
        "historical_context": "Crusades Era — Fall of the Crusader States",
        "historical_context_ja": "十字軍時代 — 十字軍国家の陥落",
        "key_servants": ["Bedivere", "Ozymandias", "Nitocris", "Hassan of the Cursed Arm"],
        "key_servants_ja": ["ベディヴィエール", "オジマンディアス", "ニトクリス", "呪腕のハサン"],
    },
    "babylonia": {
        "number": "VII",
        "subtitle_en": "The Absolute Frontline in the War Against the Demonic Beasts: Babylonia",
        "subtitle_ja": "絶対魔獣戦線 バビロニア",
        "subtitle_ko": "절대마수전선 바빌로니아",
        "location": "Mesopotamia / Uruk",
        "location_ja": "メソポタミア / ウルク",
        "location_ko": "메소포타미아 / 우루크",
        "lat": 31.32, "lng": 45.64,
        "year": -2655,
        "historical_context": "Ancient Mesopotamia — Gilgamesh and the birth of civilization",
        "historical_context_ja": "古代メソポタミア — ギルガメシュと文明の誕生",
        "key_servants": ["Gilgamesh", "Enkidu", "Ishtar", "Merlin", "Ushiwakamaru"],
        "key_servants_ja": ["ギルガメッシュ", "エルキドゥ", "イシュタル", "マーリン", "牛若丸"],
    },
    "solomon": {
        "number": "Final",
        "subtitle_en": "The Grand Temple of Time: Solomon",
        "subtitle_ja": "冠位時間神殿 ソロモン",
        "subtitle_ko": "관위시간신전 솔로몬",
        "location": "Temple of Time",
        "location_ja": "時間神殿",
        "location_ko": "시간신전",
        "lat": 31.77, "lng": 35.23,
        "year": 2016,
        "historical_context": "King Solomon and the 72 Demon Gods of Ars Goetia",
        "historical_context_ja": "ソロモン王とアルス・ゴエティアの72柱の魔神",
        "key_servants": ["Solomon", "Goetia"],
        "key_servants_ja": ["ソロモン", "ゲーティア"],
    },
}

LOSTBELT_META = {
    "lb1": {
        "number": "1",
        "subtitle_en": "Permafrost Empire: Anastasia",
        "subtitle_ja": "永久凍土帝国 アナスタシア",
        "subtitle_ko": "영구동토제국 아나스타시아",
        "location": "Russia",
        "location_ja": "ロシア",
        "location_ko": "러시아",
        "lat": 55.75, "lng": 37.62,
        "year": 1570,
        "historical_context": "Ivan the Terrible's reign — Oprichnina terror",
        "historical_context_ja": "イヴァン雷帝の治世 — オプリーチニナの恐怖",
        "key_servants": ["Anastasia", "Atalante (Alter)", "Avicebron", "Ivan the Terrible"],
        "key_servants_ja": ["アナスタシア", "アタランテ〔オルタ〕", "アヴィケブロン", "イヴァン雷帝"],
    },
    "lb2": {
        "number": "2",
        "subtitle_en": "The Eternal Flame Century: Götterdämmerung",
        "subtitle_ja": "無間氷焔世紀 ゲッテルデメルング",
        "subtitle_ko": "무간빙염세기 괴터데머룽",
        "location": "Scandinavia",
        "location_ja": "スカンディナヴィア",
        "location_ko": "스칸디나비아",
        "lat": 63.0, "lng": 15.0,
        "year": -1000,
        "historical_context": "Norse mythology — Ragnarök and the Age of Gods",
        "historical_context_ja": "北欧神話 — ラグナロクと神代",
        "key_servants": ["Brynhildr", "Sigurd", "Napoleon", "Scathach-Skadi"],
        "key_servants_ja": ["ブリュンヒルデ", "シグルド", "ナポレオン", "スカサハ＝スカディ"],
    },
    "lb3": {
        "number": "3",
        "subtitle_en": "The Crimson Moon Over the Land of Unified Knowledge: SIN",
        "subtitle_ja": "人智統合真国 シン",
        "subtitle_ko": "인지통합진국 신",
        "location": "China",
        "location_ja": "中国",
        "location_ko": "중국",
        "lat": 34.26, "lng": 108.94,
        "year": -210,
        "historical_context": "Qin Shi Huang's era — First Emperor's unification of China",
        "historical_context_ja": "始皇帝の時代 — 中国統一",
        "key_servants": ["Qin Shi Huang", "Yu Mei-ren", "Xiang Yu", "Mordred"],
        "key_servants_ja": ["始皇帝", "虞美人", "項羽", "モードレッド"],
    },
    "lb4": {
        "number": "4",
        "subtitle_en": "The Final Dark God: Yuga Kshetra",
        "subtitle_ja": "創世滅亡輪廻 ユガ・クシェートラ",
        "subtitle_ko": "창세멸망윤회 유가 크셰트라",
        "location": "India",
        "location_ja": "インド",
        "location_ko": "인도",
        "lat": 20.59, "lng": 78.96,
        "year": 11900,
        "historical_context": "Hindu mythology — The cyclic ages (Yugas) and Arjuna",
        "historical_context_ja": "ヒンドゥー神話 — ユガの循環とアルジュナ",
        "key_servants": ["Arjuna (Alter)", "Karna", "Ganesha", "Ashwatthama"],
        "key_servants_ja": ["アルジュナ〔オルタ〕", "カルナ", "ガネーシャ", "アシュヴァッターマン"],
    },
    "lb5": {
        "number": "5",
        "subtitle_en": "Ancient Titans' Ocean: Atlantis / Interstellar Mountainous City: Olympus",
        "subtitle_ja": "神代巨神海洋 アトランティス / 星間都市山脈 オリュンポス",
        "subtitle_ko": "신대거신해양 아틀란티스 / 성간도시산맥 올림포스",
        "location": "Greece / Aegean Sea",
        "location_ja": "ギリシャ / エーゲ海",
        "location_ko": "그리스 / 에게해",
        "lat": 37.97, "lng": 23.73,
        "year": -12000,
        "historical_context": "Greek mythology — Olympian Gods and the age of heroes",
        "historical_context_ja": "ギリシャ神話 — オリュンポスの神々と英雄時代",
        "key_servants": ["Odysseus", "Europa", "Caenis", "Musashi (Berserker)"],
        "key_servants_ja": ["オデュッセウス", "エウロペ", "カイニス", "宮本武蔵〔バーサーカー〕"],
    },
    "lb5.5": {
        "number": "5.5",
        "subtitle_en": "Hell Realm Mandala: Heian-kyo",
        "subtitle_ja": "地獄界曼荼羅 平安京",
        "subtitle_ko": "지옥계만다라 헤이안쿄",
        "location": "Kyoto, Japan",
        "location_ja": "京都、日本",
        "location_ko": "교토, 일본",
        "lat": 35.01, "lng": 135.77,
        "year": -12000,
        "historical_context": "Heian period Japan — Onmyōdō, Abe no Seimei, Shuten-dōji",
        "historical_context_ja": "平安時代の日本 — 陰陽道、安倍晴明、酒呑童子",
        "key_servants": ["Kintoki", "Ibuki-douji", "Sei Shounagon", "Ashiya Douman"],
        "key_servants_ja": ["坂田金時", "伊吹童子", "清少納言", "蘆屋道満"],
    },
    "lb6": {
        "number": "6",
        "subtitle_en": "Fairy Round Table Domain: Avalon le Fae",
        "subtitle_ja": "妖精円卓領域 アヴァロン・ル・フェ",
        "subtitle_ko": "요정원탁영역 아발론 르 페",
        "location": "Britain (Fairy)",
        "location_ja": "ブリテン（妖精）",
        "location_ko": "브리튼 (요정)",
        "lat": 51.5, "lng": -2.0,
        "year": 500,
        "historical_context": "Arthurian legend — The Fall of Britain and Fairy realm",
        "historical_context_ja": "アーサー王伝説 — ブリテンの崩壊と妖精の国",
        "key_servants": ["Artoria Caster", "Oberon", "Morgan", "Melusine"],
        "key_servants_ja": ["アルトリア・キャスター", "オベロン", "モルガン", "メリュジーヌ"],
    },
    "lb7": {
        "number": "7",
        "subtitle_en": "Golden Sea of Trees: Nahui Mictlan",
        "subtitle_ja": "黄金樹海紀行 ナウイ・ミクトラン",
        "subtitle_ko": "황금수해기행 나우이 믹틀란",
        "location": "South America / Mesoamerica",
        "location_ja": "南米 / メソアメリカ",
        "location_ko": "남미 / 메소아메리카",
        "lat": 19.43, "lng": -99.13,
        "year": -2655,
        "historical_context": "Aztec/Mesoamerican mythology — Quetzalcoatl and the underworld",
        "historical_context_ja": "アステカ/メソアメリカ神話 — ケツァルコアトルと冥界",
        "key_servants": ["Kukulkan", "Nitocris (Alter)", "Tezcatlipoca", "Daybit"],
        "key_servants_ja": ["ククルカン", "ニトクリス〔オルタ〕", "テスカトリポカ", "デイビット"],
    },
}


# ─── Processing ─────────────────────────────────────────

def analyze_chapter_scripts(jp_data: dict, na_data: Optional[dict]) -> dict:
    """Analyze a chapter's scripts to extract key info."""
    # Count speakers across all scripts
    speaker_counter: Counter = Counter()
    total_dialogues = 0
    total_scripts = 0

    for spot in jp_data.get("spots", []):
        for quest in spot.get("quests", []):
            for script in quest.get("scripts", []):
                total_scripts += 1
                for dlg in script.get("dialogues", []):
                    speaker = dlg.get("speaker", "")
                    if not speaker.startswith("__"):
                        speaker_counter[speaker] += 1
                    total_dialogues += 1

    # Top characters (by dialogue count, excluding meta speakers)
    top_characters = [
        {"name": name, "line_count": count}
        for name, count in speaker_counter.most_common(15)
        if not name.startswith("__")
    ]

    # Quest list (ordered)
    quest_list = []
    for spot in jp_data.get("spots", []):
        for quest in spot.get("quests", []):
            quest_scripts_count = len(quest.get("scripts", []))
            quest_dialogue_count = sum(
                s.get("dialogue_count", 0)
                for s in quest.get("scripts", [])
            )
            quest_list.append({
                "id": quest["id"],
                "name": quest["name"],
                "spot": spot["name"],
                "scripts": quest_scripts_count,
                "dialogues": quest_dialogue_count,
            })

    return {
        "total_scripts": total_scripts,
        "total_dialogues": total_dialogues,
        "top_characters": top_characters,
        "quest_list": quest_list,
    }


def build_chapter_entry(slug: str, meta: dict, jp_data: Optional[dict], na_data: Optional[dict], chapter_type: str) -> dict:
    """Build a single chapter catalog entry."""
    analysis = analyze_chapter_scripts(jp_data, na_data) if jp_data else {}

    entry = {
        "id": slug,
        "type": chapter_type,
        "number": meta.get("number", ""),
        "title": {
            "en": f"{'Singularity' if chapter_type == 'singularity' else 'Lostbelt'} {meta['number']}",
            "ja": jp_data.get("name", slug) if jp_data else slug,
        },
        "subtitle": {
            "en": meta.get("subtitle_en", ""),
            "ja": meta.get("subtitle_ja", ""),
            "ko": meta.get("subtitle_ko", ""),
        },
        "year": meta.get("year"),
        "location": {
            "en": meta.get("location", ""),
            "ja": meta.get("location_ja", ""),
            "ko": meta.get("location_ko", ""),
            "lat": meta.get("lat"),
            "lng": meta.get("lng"),
        },
        "historical_context": {
            "en": meta.get("historical_context", ""),
            "ja": meta.get("historical_context_ja", ""),
        },
        "key_servants": {
            "en": meta.get("key_servants", []),
            "ja": meta.get("key_servants_ja", []),
        },
        "stats": {
            "total_scripts": analysis.get("total_scripts", 0),
            "total_dialogues": analysis.get("total_dialogues", 0),
        },
        "top_characters": analysis.get("top_characters", []),
        "quest_list": analysis.get("quest_list", []),
    }

    return entry


def build_servant_catalog() -> list[dict]:
    """Build servant catalog from existing mapping + profile data."""
    mapping_path = RAW_DIR / "servant_person_mapping.json"
    profiles_path = RAW_DIR / "materials" / "servant_profiles_na.json"
    basic_jp_path = RAW_DIR / "servants_basic_jp.json"

    # Load data
    mapping = json.loads(mapping_path.read_text(encoding="utf-8")) if mapping_path.exists() else {}
    profiles = json.loads(profiles_path.read_text(encoding="utf-8")) if profiles_path.exists() else []
    basic_jp = json.loads(basic_jp_path.read_text(encoding="utf-8")) if basic_jp_path.exists() else []

    # Build JP name lookup: collectionNo → JP name
    jp_names = {}
    for s in basic_jp:
        jp_names[s.get("collectionNo")] = s.get("name", "")

    # Build profile lookup: collectionNo → profile comments
    profile_lookup = {}
    for p in profiles:
        cno = p.get("collectionNo")
        profile_lookup[cno] = p

    # Process matched servants (ones linked to real historical figures)
    matched = mapping.get("matched", [])
    catalog = []

    for m in matched:
        fgo_name = m.get("fgo_name", "")
        fgo_class = m.get("fgo_class", "")
        person_id = m.get("person_id")
        person_name = m.get("person_name", "")
        person_name_ko = m.get("person_name_ko")
        birth_year = m.get("birth_year")
        death_year = m.get("death_year")

        # Find JP name via profiles
        jp_name = ""
        profile_comments = []
        for p in profiles:
            if p.get("name") == fgo_name:
                jp_name = jp_names.get(p.get("collectionNo"), "")
                # Extract lore comments (bond level stories)
                profile_comments = [
                    c.get("comment", "")
                    for c in p.get("comments", [])
                    if c.get("comment")
                ]
                break

        # Also try basic_jp match
        if not jp_name:
            for s in basic_jp:
                if s.get("name", "").lower() == fgo_name.lower():
                    jp_name = s.get("name", "")
                    break

        catalog.append({
            "fgo_name": {
                "en": fgo_name,
                "ja": jp_name,
            },
            "fgo_class": fgo_class,
            "person": {
                "id": person_id,
                "name_en": person_name,
                "name_ko": person_name_ko,
                "birth_year": birth_year,
                "death_year": death_year,
            },
            "profile_excerpts": profile_comments[:3],  # First 3 bond texts
        })

    return catalog


# ─── Main ───────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build FGO catalog for Trismegistos")
    parser.add_argument("--only", choices=["singularities", "lostbelts", "servants"], help="Build only specific section")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = {}

    # ─── Singularities ──────────────────────────────────
    if not args.only or args.only == "singularities":
        print("Building singularity catalog...")
        singularities = []
        for slug, meta in SINGULARITY_META.items():
            jp_path = SCRIPTS_JP_DIR / f"{slug}_jp.json"
            na_path = SCRIPTS_NA_DIR / f"{slug}_na.json"
            jp_data = json.loads(jp_path.read_text(encoding="utf-8")) if jp_path.exists() else None
            na_data = json.loads(na_path.read_text(encoding="utf-8")) if na_path.exists() else None

            if not jp_data and not na_data:
                print(f"  SKIP {slug} (no data)")
                continue

            entry = build_chapter_entry(slug, meta, jp_data, na_data, "singularity")
            singularities.append(entry)
            total = entry["stats"]["total_dialogues"]
            print(f"  {slug:12s} → {total:5d} dialogues, {len(entry['top_characters'])} characters")

        out = OUTPUT_DIR / "singularities.json"
        out.write_text(json.dumps(singularities, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Saved: {out}")
        results["singularities"] = singularities

    # ─── Lostbelts ──────────────────────────────────────
    if not args.only or args.only == "lostbelts":
        print("\nBuilding lostbelt catalog...")
        lostbelts = []
        for slug, meta in LOSTBELT_META.items():
            jp_path = SCRIPTS_JP_DIR / f"{slug}_jp.json"
            na_path = SCRIPTS_NA_DIR / f"{slug}_na.json"
            jp_data = json.loads(jp_path.read_text(encoding="utf-8")) if jp_path.exists() else None
            na_data = json.loads(na_path.read_text(encoding="utf-8")) if na_path.exists() else None

            if not jp_data and not na_data:
                print(f"  SKIP {slug} (no data)")
                continue

            entry = build_chapter_entry(slug, meta, jp_data, na_data, "lostbelt")
            lostbelts.append(entry)
            total = entry["stats"]["total_dialogues"]
            print(f"  {slug:12s} → {total:5d} dialogues, {len(entry['top_characters'])} characters")

        out = OUTPUT_DIR / "lostbelts.json"
        out.write_text(json.dumps(lostbelts, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Saved: {out}")
        results["lostbelts"] = lostbelts

    # ─── Servants ───────────────────────────────────────
    if not args.only or args.only == "servants":
        print("\nBuilding servant catalog...")
        servants = build_servant_catalog()
        out = OUTPUT_DIR / "servants.json"
        out.write_text(json.dumps(servants, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {len(servants)} servants with historical matches")
        print(f"  Saved: {out}")
        results["servants"] = servants

    # ─── Combined catalog ──────────────────────────────
    if not args.only:
        print("\nBuilding combined catalog...")
        catalog = {
            "version": "1.0",
            "description": "FGO story catalog for CHALDEAS Trismegistos portal",
            "singularities": results.get("singularities", []),
            "lostbelts": results.get("lostbelts", []),
            "servant_count": len(results.get("servants", [])),
        }
        out = OUTPUT_DIR / "catalog.json"
        out.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Saved: {out}")

    print("\nDone!")


if __name__ == "__main__":
    main()
