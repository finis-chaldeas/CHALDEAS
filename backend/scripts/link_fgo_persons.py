"""
FGO Servant ↔ Historical Person Linker
=======================================
FGO 서번트를 CHALDEAS DB의 역사 인물(persons)과 연결.
AI 불필요, 로컬 매칭. 비용 $0.

매칭 전략:
  1. 수동 매핑 시드 (이름 기반, 최우선)
  2. 영문 이름 정확/부분 매칭
  3. 일본어 이름 매칭
  4. Fuzzy 이름 매칭 (threshold ≥ 0.88)

출력:
    E:/chaldeas_data/processed/fgo/person_links/
        confirmed_links.json       — 확정 매칭
        review_candidates.json     — 수동 검토 필요
        unmatched.json             — 매칭 불가
        missing_persons.json       — DB에 없는 인물 (추후 추가 대상)
        enriched_servants.json     — 서번트 + person 정보 통합
        report.txt                 — 리포트

사용법:
    python -m scripts.link_fgo_persons               # 전체 실행
    python -m scripts.link_fgo_persons --dry-run      # 미리보기
    python -m scripts.link_fgo_persons --report       # 리포트만
"""

import argparse
import io
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import psycopg2
import psycopg2.extras

# Windows UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── Paths ──────────────────────────────────────────────

SERVANTS_INDEX = Path(r"E:\chaldeas_data\fgo_db\servants\index.json")
EXISTING_MAPPING = Path(r"E:\chaldeas_data\raw\atlas_academy\servant_person_mapping.json")
DIALOGUE_STATS = Path(r"E:\chaldeas_data\processed\fgo\dialogues\stats.json")
OUTPUT_DIR = Path(r"E:\chaldeas_data\processed\fgo\person_links")

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "chaldeas",
    "user": "chaldeas",
    "password": "chaldeas_dev",
}

# ─── Helpers ────────────────────────────────────────────

def load_json(path: Path) -> list | dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_name(name: str) -> str:
    """Normalize a name for comparison."""
    if not name:
        return ""
    name = name.lower().strip()
    # Remove FGO class/variant suffixes
    name = re.sub(r"\s*\((?:saber|archer|lancer|rider|caster|assassin|berserker|ruler|avenger|alter|lily|santa|prototype|extra|summer|swimsuit|halloween|christmas|bride|alter ego|moon cancer|foreigner|pretender|beast|vacay|cinderella|brave)[^)]*\)", "", name, flags=re.IGNORECASE)
    # Remove parentheticals, brackets
    name = re.sub(r"\s*\([^)]*\)", "", name)
    name = re.sub(r"\s*（[^）]*）", "", name)
    name = re.sub(r"\s*〔[^〕]*〕", "", name)
    name = re.sub(r"\s*\[[^\]]*\]", "", name)
    # Normalize quotes
    name = name.replace('"', '').replace("'", "").replace(""", "").replace(""", "")
    # Normalize whitespace
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def strip_fgo_suffix(name: str) -> str:
    """Remove FGO-specific parenthetical suffixes like (Alter), (Rider) etc."""
    return re.sub(r"\s*\([^)]*\)$", "", name).strip()


def name_similarity(a: str, b: str) -> float:
    """Compute similarity between two names (0-1)."""
    a, b = normalize_name(a), normalize_name(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


# ─── Manual Mapping (name_en → person search name) ─────
# FGO 이름이 DB 인물명과 다른 경우의 수동 매핑.
# key = FGO name_en (strip_fgo_suffix 적용 후 매칭), value = DB 검색용 이름 or 메타데이터
#
# category: historical | mythological | legendary | fgo_original | fictional

MANUAL_NAME_MAP = {
    # ── 이름이 다른 역사 인물 ──
    "Altria Pendragon":         {"search": "King Arthur",              "category": "legendary"},
    "Arthur Pendragon":         {"search": "King Arthur",              "category": "legendary"},
    "Ozymandias":               {"search": "Ramesses II",              "category": "historical"},
    "Iskandar":                 {"search": "Alexander the Great",      "category": "historical"},
    "Ushiwakamaru":             {"search": "Minamoto no Yoshitsune",   "category": "historical"},
    "Nero Claudius":            {"search": "Nero",                     "category": "historical"},
    "Gaius Julius Caesar":      {"search": "Julius Caesar",            "category": "historical"},
    "Alexander":                {"search": "Alexander the Great",      "category": "historical"},
    "Zhuge Liang":              {"search": "Zhuge Liang",              "category": "historical"},
    "Sima Yi":                  {"search": "Sima Yi",                  "category": "historical"},
    "Ivan the Terrible":        {"search": "Ivan IV",                  "category": "historical"},
    "Edmond Dantès":            {"search": None,                       "category": "fictional",   "notes": "Count of Monte Cristo, Alexandre Dumas novel"},
    "Chevalier d'Eon":          {"search": "Chevalier d'Eon",          "category": "historical"},
    "Paracelsus von Hohenheim": {"search": "Paracelsus",               "category": "historical"},
    "Amakusa Shirou":           {"search": "Amakusa Shiro",            "category": "historical"},
    "Lu Bu Fengxian":           {"search": "Lü Bu",                    "category": "historical"},
    "Wolfgang Amadeus Mozart":  {"search": "Wolfgang Amadeus Mozart",  "category": "historical"},
    "Hans Christian Andersen":  {"search": "Hans Christian Andersen",   "category": "historical"},
    "William Shakespeare":      {"search": "William Shakespeare",      "category": "historical"},
    "Edward Teach":             {"search": "Blackbeard",               "category": "historical"},
    "Musashibou Benkei":        {"search": "Benkei",                   "category": "legendary"},
    "Charles-Henri Sanson":     {"search": "Charles-Henri Sanson",     "category": "historical"},
    "Phantom of the Opera":     {"search": None,                       "category": "fictional",   "notes": "Gaston Leroux novel"},
    "Nursery Rhyme":            {"search": None,                       "category": "fgo_original", "notes": "Concept given form"},
    "Henry Jekyll & Hyde":      {"search": None,                       "category": "fictional",   "notes": "Robert Louis Stevenson novel"},
    "Jack the Ripper":          {"search": "Jack the Ripper",          "category": "historical"},
    "Sherlock Holmes":          {"search": None,                       "category": "fictional",   "notes": "Arthur Conan Doyle creation"},
    "Frankenstein":             {"search": None,                       "category": "fictional",   "notes": "Mary Shelley novel"},
    "Don Quixote":              {"search": None,                       "category": "fictional",   "notes": "Cervantes novel"},
    "Voyager":                  {"search": None,                       "category": "fictional",   "notes": "Le Petit Prince = The Little Prince"},
    "Prince of Lan Ling":       {"search": "Gao Changgong",            "category": "historical"},
    "Qin Liangyu":              {"search": "Qin Liangyu",              "category": "historical"},
    "Sei Shounagon":            {"search": "Sei Shōnagon",             "category": "historical"},
    "Red Hare":                 {"search": None,                       "category": "legendary",   "notes": "Lu Bu's horse in Romance of Three Kingdoms"},
    "Okita Souji":              {"search": "Okita Soji",               "category": "historical"},
    "Saito Hajime":             {"search": "Saitō Hajime",             "category": "historical"},
    "Hijikata Toshizo":         {"search": "Hijikata Toshizō",         "category": "historical"},
    "Sakamoto Ryouma":          {"search": "Sakamoto Ryōma",           "category": "historical"},
    "Miyamoto Musashi":         {"search": "Miyamoto Musashi",         "category": "historical"},
    "Takasugi Shinsaku":        {"search": "Takasugi Shinsaku",        "category": "historical"},
    "Oda Nobunaga":             {"search": "Oda Nobunaga",             "category": "historical"},
    "Oda Nobukatsu":            {"search": "Oda Nobukatsu",            "category": "historical"},
    "Yagyu Tajima-no-kami Munenori": {"search": "Yagyū Munenori",      "category": "historical"},
    "Katsushika Hokusai":       {"search": "Katsushika Hokusai",       "category": "historical"},
    "Anastasia":                {"search": "Grand Duchess Anastasia",  "category": "historical"},
    "Florence Nightingale":     {"search": "Florence Nightingale",     "category": "historical"},
    "Queen Medb":               {"search": None,                       "category": "mythological", "notes": "Irish mythology queen"},
    "Scáthach":                 {"search": None,                       "category": "mythological", "notes": "Irish mythology warrior"},
    "Queen of Sheba":           {"search": "Queen of Sheba",           "category": "legendary"},
    "Izumo-no-Okuni":           {"search": "Izumo no Okuni",           "category": "historical"},
    "Sen-no-Rikyu":             {"search": "Sen no Rikyū",             "category": "historical"},
    "Minamoto-no-Tametomo":     {"search": "Minamoto no Tametomo",     "category": "historical"},
    "Kōnstantînos XI":         {"search": "Constantine XI",           "category": "historical"},
    "Ptolemaîos":              {"search": "Ptolemy I Soter",           "category": "historical"},
    "Taira-no-Kagekiyo":        {"search": "Taira no Kagekiyo",        "category": "historical"},
    "Houzouin Inshun":          {"search": "Hōzōin In'ei",            "category": "historical"},
    "Tawara Touta":             {"search": "Fujiwara no Hidesato",     "category": "legendary"},
    "Saika Magoichi":           {"search": "Suzuki Magoichi",          "category": "historical"},
    "Takeda Harunobu":          {"search": "Takeda Shingen",           "category": "historical"},

    # ── 그리스 신화 ──
    "Heracles":                 {"search": None, "category": "mythological", "notes": "Greek demigod"},
    "Achilles":                 {"search": None, "category": "mythological", "notes": "Iliad hero"},
    "Medea":                    {"search": None, "category": "mythological", "notes": "Colchis sorceress"},
    "Medusa":                   {"search": None, "category": "mythological", "notes": "Gorgon"},
    "Stheno":                   {"search": None, "category": "mythological", "notes": "Gorgon sister"},
    "Gorgon":                   {"search": None, "category": "mythological", "notes": "Gorgon form of Medusa"},
    "Circe":                    {"search": None, "category": "mythological", "notes": "Odyssey sorceress"},
    "Odysseus":                 {"search": None, "category": "mythological", "notes": "King of Ithaca"},
    "Paris":                    {"search": None, "category": "mythological", "notes": "Prince of Troy"},
    "Hektor":                   {"search": None, "category": "mythological", "notes": "Prince of Troy"},
    "Jason":                    {"search": None, "category": "mythological", "notes": "Argonauts leader"},
    "Atalante":                 {"search": None, "category": "mythological", "notes": "Arcadian huntress"},
    "Chiron":                   {"search": None, "category": "mythological", "notes": "Wise centaur"},
    "Asterios":                 {"search": None, "category": "mythological", "notes": "Minotaur"},
    "Penthesilea":              {"search": None, "category": "mythological", "notes": "Amazon queen"},
    "Orion":                    {"search": None, "category": "mythological", "notes": "Greek hunter"},
    "Romulus":                  {"search": None, "category": "mythological", "notes": "Founder of Rome"},
    "Thēseus":                 {"search": None, "category": "mythological", "notes": "Athenian hero"},
    "Galatea":                  {"search": None, "category": "mythological", "notes": "Pygmalion's creation"},
    "Fergus mac Róich":        {"search": None, "category": "mythological", "notes": "Irish mythology"},
    "Mandricardo":              {"search": None, "category": "legendary",    "notes": "Orlando Furioso character"},

    # ── 메소포타미아 ──
    "Gilgamesh":                {"search": None, "category": "mythological", "notes": "King of Uruk, Epic of Gilgamesh"},
    "Enkidu":                   {"search": None, "category": "mythological", "notes": "Gilgamesh's companion"},
    "Ishtar":                   {"search": None, "category": "mythological", "notes": "Mesopotamian goddess"},
    "Ereshkigal":               {"search": None, "category": "mythological", "notes": "Mesopotamian underworld goddess"},

    # ── 인도 신화 ──
    "Arjuna":                   {"search": None, "category": "mythological", "notes": "Mahabharata hero"},
    "Karna":                    {"search": None, "category": "mythological", "notes": "Mahabharata hero"},
    "Rama":                     {"search": None, "category": "mythological", "notes": "Ramayana hero"},
    "Parvati":                  {"search": None, "category": "mythological", "notes": "Hindu goddess"},
    "Nezha":                    {"search": None, "category": "mythological", "notes": "Chinese/Buddhist deity"},
    "Duryodhana":               {"search": None, "category": "mythological", "notes": "Mahabharata antagonist"},

    # ── 북유럽 신화 ──
    "Siegfried":                {"search": None, "category": "legendary",    "notes": "Nibelungenlied hero"},
    "Kriemhild":                {"search": None, "category": "legendary",    "notes": "Nibelungenlied"},
    "Brynhildr":                {"search": None, "category": "mythological", "notes": "Norse mythology"},
    "Sigurd":                   {"search": None, "category": "mythological", "notes": "Norse mythology"},
    "Valkyrie":                 {"search": None, "category": "mythological", "notes": "Norse mythology"},
    "Beowulf":                  {"search": None, "category": "legendary",    "notes": "Anglo-Saxon epic hero"},
    "Eric Bloodaxe":            {"search": "Eric Bloodaxe",                  "category": "historical"},

    # ── 아서왕 전설 ──
    "Gawain":                   {"search": None, "category": "legendary",    "notes": "Knight of the Round Table"},
    "Lancelot":                 {"search": None, "category": "legendary",    "notes": "Knight of the Round Table"},
    "Mordred":                  {"search": None, "category": "legendary",    "notes": "Arthurian legend"},
    "Tristan":                  {"search": None, "category": "legendary",    "notes": "Arthurian legend"},
    "Bedivere":                 {"search": None, "category": "legendary",    "notes": "Knight of the Round Table"},
    "Gareth":                   {"search": None, "category": "legendary",    "notes": "Knight of the Round Table"},
    "Percival":                 {"search": None, "category": "legendary",    "notes": "Knight of the Round Table"},
    "Morgan":                   {"search": None, "category": "legendary",    "notes": "Morgan le Fay"},
    "Merlin":                   {"search": None, "category": "legendary",    "notes": "Arthurian wizard"},
    "Lady Avalon":              {"search": None, "category": "legendary",    "notes": "Arthurian legend"},
    "Oberon":                   {"search": None, "category": "legendary",    "notes": "A Midsummer Night's Dream king"},
    "Habetrot":                 {"search": None, "category": "legendary",    "notes": "British folklore"},
    "Britomart":                {"search": None, "category": "legendary",    "notes": "The Faerie Queene character"},
    "Astolfo":                  {"search": None, "category": "legendary",    "notes": "Orlando Furioso paladin"},
    "Bradamante":               {"search": None, "category": "legendary",    "notes": "Orlando Furioso character"},
    "Roland":                   {"search": None, "category": "legendary",    "notes": "Song of Roland paladin"},
    "Hephaistíon":             {"search": "Hephaestion",                    "category": "historical"},

    # ── 일본 전설 ──
    "Tamamo-no-Mae":            {"search": None, "category": "mythological", "notes": "Nine-tailed fox legend"},
    "Shuten-Douji":             {"search": None, "category": "mythological", "notes": "Oni leader"},
    "Ibaraki-Douji":            {"search": None, "category": "mythological", "notes": "Oni"},
    "Kiyohime":                 {"search": None, "category": "legendary",    "notes": "Kiyohime legend"},
    "Sakata Kintoki":           {"search": None, "category": "legendary",    "notes": "Kintarō"},
    "Watanabe-no-Tsuna":        {"search": None, "category": "legendary",    "notes": "Minamoto retainer"},
    "Kiichi Hogen":             {"search": None, "category": "legendary",    "notes": "Legendary figure"},
    "Beni-Enma":                {"search": None, "category": "mythological", "notes": "Sparrow spirit"},
    "Fuuma \"Evil-wind\" Kotarou": {"search": "Fuma Kotaro",                 "category": "historical"},

    # ── 중국/아즈텍 신화 ──
    "Quetzalcoatl":             {"search": None, "category": "mythological", "notes": "Aztec deity"},
    "Kukulcan":                 {"search": None, "category": "mythological", "notes": "Maya deity"},
    "Xuanzang Sanzang":         {"search": "Xuanzang",                       "category": "historical"},
    "Taigong Wang":             {"search": "Jiang Ziya",                     "category": "legendary"},
    "Huang Feihu":              {"search": None, "category": "legendary",    "notes": "Fengshen Yanyi character"},
    "Huyan Zhuo":               {"search": None, "category": "legendary",    "notes": "Water Margin character"},

    # ── 기타 역사 인물 ──
    "Mata Hari":                {"search": "Mata Hari",                "category": "historical"},
    "Carmilla":                 {"search": "Elizabeth Báthory",        "category": "historical", "notes": "Older Elizabeth Bathory"},
    "Elisabeth Báthory":        {"search": "Elizabeth Báthory",        "category": "historical"},
    "Geronimo":                 {"search": "Geronimo",                 "category": "historical"},
    "Billy the Kid":            {"search": "Billy the Kid",            "category": "historical"},
    "Calamity Jane":            {"search": "Calamity Jane",            "category": "historical"},
    "Darius III":               {"search": "Darius III",               "category": "historical"},
    "Boudica":                  {"search": "Boudica",                  "category": "historical"},
    "Spartacus":                {"search": "Spartacus",                "category": "historical"},
    "Avicebron":                {"search": "Solomon ibn Gabirol",      "category": "historical"},
    "Charlotte Corday":         {"search": "Charlotte Corday",         "category": "historical"},
    "Paul Bunyan":              {"search": None,                       "category": "legendary",    "notes": "American folklore"},
    "Semiramis":                {"search": "Semiramis",                "category": "legendary"},
    "Helena Blavatsky":         {"search": "Helena Blavatsky",         "category": "historical"},
    "Scheherazade":             {"search": None,                       "category": "legendary",    "notes": "One Thousand and One Nights"},
    "Abigail Williams":         {"search": "Abigail Williams",         "category": "historical", "notes": "Salem witch trials"},
    "Pope Johanna":             {"search": "Pope Joan",                "category": "legendary"},
    "Mephistopheles":           {"search": None,                       "category": "fictional",   "notes": "Faust legend"},
    "Wu Zetian":                {"search": "Wu Zetian",                "category": "historical"},
    "Okada Izo":                {"search": "Okada Izo",                "category": "historical"},
    "Gilles de Rais":           {"search": "Gilles de Rais",           "category": "historical"},
    "Marie Antoinette":         {"search": "Marie Antoinette",         "category": "historical"},
    "Cleopatra":                {"search": "Cleopatra",                "category": "historical"},
    "Thomas Edison":            {"search": "Thomas Edison",            "category": "historical"},

    # ── FGO 오리지널 (연결 불가) ──
    "Mash Kyrielight":          {"search": None, "category": "fgo_original"},
    "BB":                       {"search": None, "category": "fgo_original"},
    "Passionlip":               {"search": None, "category": "fgo_original"},
    "Meltryllis":               {"search": None, "category": "fgo_original"},
    "Tamamo Cat":               {"search": None, "category": "fgo_original"},
    "Sessyoin Kiara":           {"search": None, "category": "fgo_original", "notes": "Fate/EXTRA CCC original"},
    "Emiya":                    {"search": None, "category": "fgo_original", "notes": "Fate/stay night original"},
    "Illyasviel von Einzbern":  {"search": None, "category": "fgo_original", "notes": "Fate series original"},
    "Chloe von Einzbern":       {"search": None, "category": "fgo_original", "notes": "Fate/Prisma Illya"},
    "Miyu Edelfelt":            {"search": None, "category": "fgo_original", "notes": "Fate/Prisma Illya"},
    "Ryougi Shiki":             {"search": None, "category": "fgo_original", "notes": "Kara no Kyoukai"},
    "Asagami Fujino":           {"search": None, "category": "fgo_original", "notes": "Kara no Kyoukai"},
    "Gray":                     {"search": None, "category": "fgo_original", "notes": "Lord El-Melloi II Case Files"},
    "Bazett Fraga McRemitz":    {"search": None, "category": "fgo_original", "notes": "Fate/hollow ataraxia"},
    "Aŋra Mainiiu":            {"search": None, "category": "mythological", "notes": "Zoroastrian spirit"},
    "Miss Crane":               {"search": None, "category": "fgo_original"},
    "Hessian Lobo":             {"search": None, "category": "fgo_original", "notes": "Composite character"},
}

# ─── DB Queries ─────────────────────────────────────────

def load_persons_from_db() -> dict:
    """Load persons from PostgreSQL, returning lookup tables."""
    print("  Connecting to PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Top persons by importance for name matching
    print("  Loading persons (importance >= 20)...")
    cur.execute("""
        SELECT id, wikidata_id, name, name_ko, name_ja,
               birth_year, death_year, importance_score, certainty
        FROM persons
        WHERE importance_score >= 20
        ORDER BY importance_score DESC
    """)
    top_persons = [dict(row) for row in cur]

    # Build name indexes
    en_name_index = {}  # normalized_name → person
    en_name_index_exact = {}  # exact lowercase → person
    ja_name_index = {}

    for p in top_persons:
        # EN name index
        key = normalize_name(p["name"])
        if key and key not in en_name_index:
            en_name_index[key] = p
        exact_key = p["name"].lower().strip()
        if exact_key and exact_key not in en_name_index_exact:
            en_name_index_exact[exact_key] = p

        # JA name index
        if p.get("name_ja"):
            ja_key = normalize_name(p["name_ja"])
            if ja_key and ja_key not in ja_name_index:
                ja_name_index[ja_key] = p

    cur.close()
    conn.close()

    print(f"  Loaded: {len(top_persons):,} persons, {len(en_name_index):,} EN names, {len(ja_name_index):,} JA names")
    return {
        "top_persons": top_persons,
        "en_name_index": en_name_index,
        "en_name_index_exact": en_name_index_exact,
        "ja_name_index": ja_name_index,
    }


# ─── Matching Engine ────────────────────────────────────

def find_person_by_name(search_name: str, persons: dict) -> dict | None:
    """Search for a person by name using multiple strategies."""
    if not search_name:
        return None

    en_index = persons["en_name_index"]
    en_exact = persons["en_name_index_exact"]
    ja_index = persons["ja_name_index"]

    # 1. Exact match
    key = normalize_name(search_name)
    if key in en_index:
        return en_index[key]

    # 2. Exact lowercase match
    exact_key = search_name.lower().strip()
    if exact_key in en_exact:
        return en_exact[exact_key]

    # 3. JA name match
    if key in ja_index:
        return ja_index[key]

    # 4. Fuzzy match against top persons
    best_sim = 0.0
    best_person = None
    for p in persons["top_persons"][:5000]:
        sim = name_similarity(search_name, p["name"])
        if sim > best_sim:
            best_sim = sim
            best_person = p
        # Also try JA
        if p.get("name_ja"):
            ja_sim = name_similarity(search_name, p["name_ja"])
            if ja_sim > best_sim:
                best_sim = ja_sim
                best_person = p

    if best_sim >= 0.88:
        return best_person

    return None


def match_servants(servants: list[dict], persons: dict, dialogue_stats: dict | None) -> dict:
    """Run the full matching pipeline."""

    # Build dialogue stats lookup
    dialogue_lookup = {}
    if dialogue_stats:
        for sp in dialogue_stats.get("top_speakers", []):
            dialogue_lookup[sp["name_ja"]] = sp

    # Results
    confirmed = []
    review = []
    unmatched = []
    missing = []       # has a category/notes but no DB match
    fgo_originals = []

    for servant in servants:
        sid = servant["id"]
        name_en = servant.get("name_en", "")
        name_ja = servant.get("name_ja", "")
        name_ko = servant.get("name_ko", "")
        class_name = servant.get("className", "")
        rarity = servant.get("rarity", 0)

        result = {
            "servant_id": sid,
            "collection_no": servant.get("collectionNo"),
            "name_en": name_en,
            "name_ja": name_ja,
            "name_ko": name_ko,
            "class_name": class_name,
            "rarity": rarity,
            "match_method": None,
            "person_id": None,
            "person_name": None,
            "person_wikidata_id": None,
            "person_birth_year": None,
            "person_death_year": None,
            "confidence": 0.0,
            "category": None,
            "notes": None,
        }

        # Add dialogue stats
        if name_ja in dialogue_lookup:
            ds = dialogue_lookup[name_ja]
            result["dialogue_lines"] = ds.get("total_lines", 0)
            result["dialogue_chapters"] = ds.get("chapter_count", 0)

        # ─── Step 0: Manual mapping (highest priority) ──
        # Try base name first, then full name
        base_name = strip_fgo_suffix(name_en)
        manual = MANUAL_NAME_MAP.get(name_en) or MANUAL_NAME_MAP.get(base_name)

        if manual:
            result["category"] = manual["category"]
            result["notes"] = manual.get("notes", "")
            search_name = manual.get("search")

            if manual["category"] == "fgo_original":
                result["match_method"] = "manual_fgo_original"
                fgo_originals.append(result)
                continue

            if search_name:
                person = find_person_by_name(search_name, persons)
                if person:
                    result["match_method"] = "manual_seed"
                    result["person_id"] = person["id"]
                    result["person_name"] = person["name"]
                    result["person_wikidata_id"] = person.get("wikidata_id")
                    result["person_birth_year"] = person.get("birth_year")
                    result["person_death_year"] = person.get("death_year")
                    result["confidence"] = 0.95
                    confirmed.append(result)
                    continue
                else:
                    # Manual mapping says search X but X not found in DB
                    result["match_method"] = "manual_not_in_db"
                    result["confidence"] = 0.0
                    missing.append(result)
                    continue
            else:
                # No search name (mythological/legendary/fictional with no DB entry)
                result["match_method"] = "manual_no_search"
                missing.append(result)
                continue

        # ─── Step 1: EN name exact match ──
        if name_en:
            # Try full name
            key = normalize_name(name_en)
            person = persons["en_name_index"].get(key)
            if not person:
                # Try base name (without class suffix)
                base_key = normalize_name(base_name)
                person = persons["en_name_index"].get(base_key)

            if person:
                result["match_method"] = "en_name_exact"
                result["person_id"] = person["id"]
                result["person_name"] = person["name"]
                result["person_wikidata_id"] = person.get("wikidata_id")
                result["person_birth_year"] = person.get("birth_year")
                result["person_death_year"] = person.get("death_year")
                result["confidence"] = 0.90
                result["category"] = "historical"
                confirmed.append(result)
                continue

        # ─── Step 2: JA name exact match ──
        if name_ja:
            ja_base = normalize_name(name_ja)
            person = persons["ja_name_index"].get(ja_base)
            if person:
                result["match_method"] = "ja_name_exact"
                result["person_id"] = person["id"]
                result["person_name"] = person["name"]
                result["person_wikidata_id"] = person.get("wikidata_id")
                result["person_birth_year"] = person.get("birth_year")
                result["person_death_year"] = person.get("death_year")
                result["confidence"] = 0.85
                result["category"] = "historical"
                confirmed.append(result)
                continue

        # ─── Step 3: Fuzzy EN match ──
        if name_en:
            best_sim = 0.0
            best_person = None
            search = normalize_name(base_name)
            for p in persons["top_persons"][:3000]:
                sim = name_similarity(search, p["name"])
                if sim > best_sim:
                    best_sim = sim
                    best_person = p

            if best_sim >= 0.88:
                result["match_method"] = "en_name_fuzzy"
                result["person_id"] = best_person["id"]
                result["person_name"] = best_person["name"]
                result["person_wikidata_id"] = best_person.get("wikidata_id")
                result["person_birth_year"] = best_person.get("birth_year")
                result["person_death_year"] = best_person.get("death_year")
                result["confidence"] = best_sim
                result["category"] = "historical"
                confirmed.append(result)
                continue
            elif best_sim >= 0.75:
                result["match_method"] = "en_name_fuzzy_low"
                result["person_name"] = best_person["name"] if best_person else None
                result["confidence"] = best_sim
                review.append(result)
                continue

        # ─── No match ──
        result["match_method"] = "none"
        unmatched.append(result)

    return {
        "confirmed": confirmed,
        "review": review,
        "unmatched": unmatched,
        "missing": missing,
        "fgo_originals": fgo_originals,
    }


# ─── Report ────────────────────────────────────────────

def generate_report(results: dict, servants: list) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("FGO Servant ↔ Historical Person Matching Report")
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append("=" * 70)

    total = len(servants)
    confirmed = results["confirmed"]
    review = results["review"]
    unmatched = results["unmatched"]
    missing_list = results["missing"]
    originals = results["fgo_originals"]

    lines.append(f"\nTotal servants: {total}")
    lines.append(f"  ✅ Confirmed:       {len(confirmed):3d} ({100*len(confirmed)/total:.1f}%)")
    lines.append(f"  ⚠️  Review:          {len(review):3d} ({100*len(review)/total:.1f}%)")
    lines.append(f"  🔍 Categorized/NoDB: {len(missing_list):3d} ({100*len(missing_list)/total:.1f}%) — mythological/legendary/fictional, DB에 미등재")
    lines.append(f"  🎮 FGO Original:    {len(originals):3d} ({100*len(originals)/total:.1f}%)")
    lines.append(f"  ❌ Unmatched:       {len(unmatched):3d} ({100*len(unmatched)/total:.1f}%)")

    # Match method breakdown
    methods = defaultdict(int)
    for r in confirmed + review + missing_list + originals:
        methods[r["match_method"]] += 1
    lines.append(f"\nMatch methods:")
    for method, count in sorted(methods.items(), key=lambda x: -x[1]):
        lines.append(f"  {method:35s} {count:3d}")

    # Confirmed matches
    lines.append(f"\n{'─' * 70}")
    lines.append(f"CONFIRMED MATCHES ({len(confirmed)})")
    lines.append(f"{'─' * 70}")
    for r in sorted(confirmed, key=lambda x: -(x.get("rarity", 0))):
        dlg = f" [{r.get('dialogue_lines', 0):,}줄]" if r.get("dialogue_lines") else ""
        lines.append(
            f"  ★{r['rarity']} {r['name_en'] or r['name_ja']:35s} → "
            f"{r['person_name']:30s} "
            f"[{r['match_method']}]{dlg}"
        )

    # Review candidates
    if review:
        lines.append(f"\n{'─' * 70}")
        lines.append(f"REVIEW NEEDED ({len(review)})")
        lines.append(f"{'─' * 70}")
        for r in review:
            lines.append(
                f"  ★{r['rarity']} {r['name_en'] or r['name_ja']:35s} → "
                f"{r['person_name'] or '?':30s} "
                f"sim={r['confidence']:.2f}"
            )

    # Categorized but not in DB
    if missing_list:
        by_cat = defaultdict(list)
        for r in missing_list:
            by_cat[r.get("category", "unknown")].append(r)

        lines.append(f"\n{'─' * 70}")
        lines.append(f"CATEGORIZED BUT NOT IN DB ({len(missing_list)})")
        lines.append(f"{'─' * 70}")
        for cat, items in sorted(by_cat.items()):
            lines.append(f"\n  [{cat}] ({len(items)})")
            for r in items:
                notes = f" — {r['notes']}" if r.get("notes") else ""
                lines.append(f"    {r['name_en'] or r['name_ja']:40s}{notes}")

    # FGO Originals
    if originals:
        lines.append(f"\n{'─' * 70}")
        lines.append(f"FGO ORIGINALS ({len(originals)})")
        lines.append(f"{'─' * 70}")
        for r in originals:
            notes = f" — {r['notes']}" if r.get("notes") else ""
            lines.append(f"  {r['name_en'] or r['name_ja']:40s}{notes}")

    # Fully unmatched
    if unmatched:
        lines.append(f"\n{'─' * 70}")
        lines.append(f"FULLY UNMATCHED ({len(unmatched)}) — need manual mapping or investigation")
        lines.append(f"{'─' * 70}")
        for r in sorted(unmatched, key=lambda x: -(x.get("rarity", 0))):
            lines.append(f"  ★{r['rarity']} {r['name_en'] or r['name_ja']:35s} {r.get('class_name', '')}")

    return "\n".join(lines)


# ─── Main ───────────────────────────────────────────────

def run(dry_run: bool = False, report_only: bool = False):
    print("=" * 60)
    print("FGO Servant ↔ Person Linker")
    print("=" * 60)

    # Load data
    print("\nLoading servants index...")
    servants = load_json(SERVANTS_INDEX) or []
    print(f"  {len(servants)} servants")

    print("Loading dialogue stats...")
    dialogue_stats = load_json(DIALOGUE_STATS)
    if dialogue_stats:
        print(f"  {len(dialogue_stats.get('top_speakers', []))} top speakers loaded")

    if dry_run:
        manual_count = len(MANUAL_NAME_MAP)
        cat_counts = defaultdict(int)
        for v in MANUAL_NAME_MAP.values():
            cat_counts[v["category"]] += 1
        print(f"\n[DRY RUN] Would match {len(servants)} servants against persons DB.")
        print(f"  Manual mappings: {manual_count}")
        for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
            print(f"    {cat}: {count}")
        return

    print("\nLoading persons from DB...")
    persons = load_persons_from_db()

    print("\nRunning matching pipeline...")
    results = match_servants(servants, persons, dialogue_stats)

    # Generate report
    report = generate_report(results, servants)
    print(f"\n{report}")

    if report_only:
        return

    # Write outputs
    print(f"\nWriting output to {OUTPUT_DIR}...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    save_json(results["confirmed"], OUTPUT_DIR / "confirmed_links.json")
    print(f"  confirmed_links.json: {len(results['confirmed'])} entries")

    save_json(results["review"], OUTPUT_DIR / "review_candidates.json")
    print(f"  review_candidates.json: {len(results['review'])} entries")

    save_json(results["unmatched"], OUTPUT_DIR / "unmatched.json")
    print(f"  unmatched.json: {len(results['unmatched'])} entries")

    save_json(results["missing"], OUTPUT_DIR / "missing_persons.json")
    print(f"  missing_persons.json: {len(results['missing'])} entries")

    save_json(results["fgo_originals"], OUTPUT_DIR / "fgo_originals.json")
    print(f"  fgo_originals.json: {len(results['fgo_originals'])} entries")

    # Enriched servants (all results merged)
    all_results = (
        results["confirmed"] + results["review"] +
        results["unmatched"] + results["missing"] +
        results["fgo_originals"]
    )
    all_by_sid = {r["servant_id"]: r for r in all_results}
    enriched = []
    for s in servants:
        r = all_by_sid.get(s["id"], {})
        enriched.append({
            **s,
            "person_id": r.get("person_id"),
            "person_name": r.get("person_name"),
            "person_wikidata_id": r.get("person_wikidata_id"),
            "match_method": r.get("match_method"),
            "confidence": r.get("confidence", 0),
            "category": r.get("category"),
            "notes": r.get("notes"),
            "dialogue_lines": r.get("dialogue_lines", 0),
            "dialogue_chapters": r.get("dialogue_chapters", 0),
        })
    save_json(enriched, OUTPUT_DIR / "enriched_servants.json")
    print(f"  enriched_servants.json: {len(enriched)} entries")

    # Report file
    report_path = OUTPUT_DIR / "report.txt"
    report_path.write_text(report, encoding="utf-8")
    print(f"  report.txt")

    print(f"\nDone! Output: {OUTPUT_DIR}")


def apply_db(dry_run: bool = False):
    """Apply confirmed_links.json → fgo_servants.person_id in DB.

    Reads the confirmed links file and updates fgo_servants table
    for each servant that has a person_id match.
    """
    confirmed_path = OUTPUT_DIR / "confirmed_links.json"
    if not confirmed_path.exists():
        print(f"ERROR: {confirmed_path} not found. Run matching first.")
        return

    confirmed = load_json(confirmed_path) or []
    print(f"=== Apply Confirmed Links → DB ===")
    print(f"  Source: {confirmed_path}")
    print(f"  Entries: {len(confirmed)}")

    # Filter to those with valid person_id
    linkable = [c for c in confirmed if c.get("person_id")]
    print(f"  With person_id: {len(linkable)}")

    if not linkable:
        print("  Nothing to apply.")
        return

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Check current state
    cur.execute("SELECT count(*) FROM fgo_servants WHERE person_id IS NOT NULL")
    before_count = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM fgo_servants")
    total_count = cur.fetchone()[0]
    print(f"  Current DB: {before_count}/{total_count} linked")

    updated = 0
    skipped = 0
    not_found = 0

    for link in linkable:
        sid = link["servant_id"]
        pid = link["person_id"]
        name = link.get("name_en", "?")

        # Check if servant exists in fgo_servants
        cur.execute(
            "SELECT id, person_id FROM fgo_servants WHERE servant_id = %s",
            (sid,)
        )
        row = cur.fetchone()

        if not row:
            # Try by atlas_id
            cur.execute(
                "SELECT id, person_id FROM fgo_servants WHERE atlas_id = %s",
                (sid,)
            )
            row = cur.fetchone()

        if not row:
            not_found += 1
            continue

        current_pid = row[1]
        if current_pid == pid:
            skipped += 1
            continue

        if dry_run:
            status = "NEW" if current_pid is None else f"CHANGE {current_pid}→{pid}"
            print(f"    [DRY] {name:35s} → person_id={pid} ({status})")
            updated += 1
        else:
            cur.execute(
                "UPDATE fgo_servants SET person_id = %s, updated_at = NOW() WHERE id = %s",
                (pid, row[0])
            )
            updated += 1

    if not dry_run:
        conn.commit()

    cur.execute("SELECT count(*) FROM fgo_servants WHERE person_id IS NOT NULL")
    after_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    print(f"\n  Results:")
    print(f"    Updated: {updated}")
    print(f"    Already correct: {skipped}")
    print(f"    Not in fgo_servants: {not_found}")
    print(f"    DB linked: {before_count} → {after_count}")
    if dry_run:
        print("  (DRY RUN — no changes written)")


def main():
    parser = argparse.ArgumentParser(description="Link FGO servants to historical persons")
    parser.add_argument("--dry-run", action="store_true", help="Preview without DB access")
    parser.add_argument("--report", action="store_true", help="Generate report only (no file output)")
    parser.add_argument("--apply-db", action="store_true",
                        help="Apply confirmed_links.json → fgo_servants.person_id")
    args = parser.parse_args()

    if args.apply_db:
        apply_db(dry_run=args.dry_run)
    else:
        run(dry_run=args.dry_run, report_only=args.report)


if __name__ == "__main__":
    main()
