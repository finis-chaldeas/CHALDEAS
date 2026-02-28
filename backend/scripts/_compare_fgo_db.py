"""Temporary script: Compare FGO dialogue characters with DB persons."""
import io
import json
import re
import sys
from pathlib import Path

import psycopg2

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 1. Load servant index
servants = json.loads(Path(r"E:\chaldeas_data\fgo_db\servants\index.json").read_text(encoding="utf-8"))

def base_name(name_en):
    return re.sub(r"\s*\([^)]*\)\s*$", "", name_en).strip()

seen = {}
for s in servants:
    bn = base_name(s["name_en"])
    if bn not in seen:
        seen[bn] = s

print(f"Unique base servants: {len(seen)}")

# 2. Load dialogue line counts
by_char_dir = Path(r"E:\chaldeas_data\processed\fgo\dialogues\by_character")
all_lines = {}
for f in by_char_dir.glob("*.json"):
    data = json.loads(f.read_text(encoding="utf-8"))
    all_lines[data["name_ja"]] = data["total_lines"]

# 3. FGO English -> possible DB name variants
NAME_CORRECTIONS = {
    "Altria Pendragon": ["Artoria Pendragon", "King Arthur"],
    "Emiya": ["Shirou Emiya"],
    "Cu Chulainn": ["Cu Chulainn", "Cuchulainn", "Setanta"],
    "Scathach": ["Scathach"],
    "Gilgamesh": ["Gilgamesh"],
    "Jeanne d'Arc": ["Joan of Arc", "Jeanne d'Arc"],
    "Nero Claudius": ["Nero"],
    "Miyamoto Musashi": ["Miyamoto Musashi"],
    "Okita Souji": ["Okita Soji", "Okita Souji"],
    "Amakusa Shirou": ["Amakusa Shiro"],
    "Leonardo da Vinci": ["Leonardo da Vinci"],
    "Iskandar": ["Alexander the Great"],
    "Zhuge Liang": ["Zhuge Liang"],
    "Sakamoto Ryouma": ["Sakamoto Ryoma"],
    "Taigong Wang": ["Jiang Ziya"],
    "Abigail Williams": ["Abigail Williams"],
    "Yang Guifei": ["Yang Guifei"],
    "Qin Shi Huang": ["Qin Shi Huang"],
    "Katsushika Hokusai": ["Katsushika Hokusai", "Hokusai"],
    "Murasaki Shikibu": ["Murasaki Shikibu"],
    "Sei Shonagon": ["Sei Shonagon"],
    "Charlotte Corday": ["Charlotte Corday"],
    "Spartacus": ["Spartacus"],
    "Vlad III": ["Vlad III", "Vlad the Impaler"],
    "Arjuna": ["Arjuna"],
    "Karna": ["Karna"],
    "Rama": ["Rama"],
    "Romulus": ["Romulus"],
    "Caligula": ["Caligula"],
    "Caesar": ["Julius Caesar"],
    "Cleopatra": ["Cleopatra"],
    "Ozymandias": ["Ramesses II"],
    "Nitocris": ["Nitocris"],
    "Ushiwakamaru": ["Minamoto no Yoshitsune"],
    "Benkei": ["Benkei"],
    "Leonidas I": ["Leonidas I"],
    "Hektor": ["Hector"],
    "Achilles": ["Achilles"],
    "Paris": ["Paris"],
    "Orion": ["Orion"],
    "Europa": ["Europa"],
    "Medea": ["Medea"],
    "Medusa": ["Medusa"],
    "Heracles": ["Heracles", "Hercules"],
    "Asterios": ["Minotaur"],
    "Francis Drake": ["Francis Drake"],
    "Nikola Tesla": ["Nikola Tesla"],
    "Thomas Edison": ["Thomas Edison"],
    "Florence Nightingale": ["Florence Nightingale"],
    "Helena Blavatsky": ["Helena Blavatsky"],
    "Geronimo": ["Geronimo"],
    "Billy the Kid": ["Billy the Kid"],
    "Robin Hood": ["Robin Hood"],
    "William Tell": ["William Tell"],
    "Mori Nagayoshi": ["Mori Nagayoshi"],
    "Fuuma Kotarou": ["Fuma Kotaro"],
    "Sakata Kintoki": ["Sakata Kintoki"],
    "Tomoe Gozen": ["Tomoe Gozen"],
    "Nagao Kagetora": ["Uesugi Kenshin"],
    "Yagyu Munenori": ["Yagyu Munenori"],
    "Boudica": ["Boudica", "Boudicca"],
    "Semiramis": ["Semiramis"],
    "Penthesilea": ["Penthesilea"],
    "Enkidu": ["Enkidu"],
    "Ereshkigal": ["Ereshkigal"],
    "Ishtar": ["Ishtar", "Inanna"],
    "Quetzalcoatl": ["Quetzalcoatl"],
    "Hans Christian Andersen": ["Hans Christian Andersen"],
    "Shakespeare": ["William Shakespeare"],
    "Wolfgang Amadeus Mozart": ["Wolfgang Amadeus Mozart"],
    "Antonio Salieri": ["Antonio Salieri"],
    "Gilles de Rais": ["Gilles de Rais"],
    "Charles-Henri Sanson": ["Charles-Henri Sanson"],
    "Marie Antoinette": ["Marie Antoinette"],
    "Chevalier d'Eon": ["Chevalier d'Eon"],
    "Mordred": ["Mordred"],
    "Lancelot": ["Lancelot"],
    "Gawain": ["Gawain"],
    "Tristan": ["Tristan"],
    "Bedivere": ["Bedivere"],
    "Merlin": ["Merlin"],
    "Morgan le Fay": ["Morgan le Fay"],
    "Oberon": ["Oberon"],
    "Percival": ["Percival"],
    "Gareth": ["Gareth"],
    "Melusine": ["Melusine"],
    "Ashiya Douman": ["Ashiya Doman"],
    "Xu Fu": ["Xu Fu"],
    "Kriemhild": ["Kriemhild"],
    "Siegfried": ["Siegfried"],
    "Brynhild": ["Brynhild", "Brunhild"],
    "Sigurd": ["Sigurd"],
    "Napoleon": ["Napoleon"],
    "Ivan the Terrible": ["Ivan the Terrible", "Ivan IV"],
    "Anastasia": ["Anastasia Nikolaevna"],
    "Avicebron": ["Solomon ibn Gabirol"],
    "Atalante": ["Atalanta"],
    "Chiron": ["Chiron"],
    "Jason": ["Jason"],
    "Bartholomew Roberts": ["Bartholomew Roberts"],
    "Blackbeard": ["Blackbeard", "Edward Teach"],
    "Anne Bonny": ["Anne Bonny"],
    "Christopher Columbus": ["Christopher Columbus"],
    "Nezha": ["Nezha"],
    "Xuanzang Sanzang": ["Xuanzang"],
    "Li Shuwen": ["Li Shuwen"],
    "Consort Yu": ["Consort Yu"],
    "Xiang Yu": ["Xiang Yu"],
    "Chen Gong": ["Chen Gong"],
    "Jing Ke": ["Jing Ke"],
    "Kojirou": ["Sasaki Kojiro"],
    "Mata Hari": ["Mata Hari"],
    "Caster of the Nightless City": ["Scheherazade"],
    "Jack the Ripper": ["Jack the Ripper"],
    "David": ["David"],
    "Solomon": ["Solomon"],
    "Arash": ["Arash"],
    "Nobukatsu": ["Oda Nobukatsu"],
    "Oda Nobunaga": ["Oda Nobunaga"],
    "Okuni": ["Izumo no Okuni"],
    "Dioscuri": ["Castor", "Pollux"],
    "Vritra": ["Vritra"],
    "Aesc the Savior": [],
    "Dobrynya Nikitich": ["Dobrynya Nikitich"],
    "Ibuki-Douji": [],
    "Kijyo Koyo": [],
    "Watanabe no Tsuna": ["Watanabe no Tsuna"],
    "Minamoto-no-Raikou": ["Minamoto no Raiko", "Minamoto no Yorimitsu"],
    "Tamamo-no-Mae": ["Tamamo-no-Mae"],
    "Shuten-Douji": ["Shuten-doji"],
    "Ibaraki-Douji": ["Ibaraki-doji"],
    "Okita J Souji": [],
    "Nemo": ["Captain Nemo"],
    "Voyager": [],
    "Mash Kyrielight": [],
    "Sherlock Holmes": [],
    "BB": [],
    "Passionlip": [],
    "Meltryllis": [],
    "Sessyoin Kiara": [],
    "Koyanskaya of Light": [],
    "Koyanskaya of Darkness": [],
    "Osakabehime": [],
    "Space Ishtar": [],
    "Mysterious Heroine X": [],
    "Mysterious Heroine XX": [],
    "Jaguar Warrior": [],
    "Hassan of the Cursed Arm": [],
    "Hassan of the Hundred Faces": [],
    "Hassan of the Serenity": [],
    "King Hassan": [],
    "Phantom of the Opera": [],
    "Edmond Dantes": [],
    "Nursery Rhyme": [],
    "Angra Mainyu": [],
    "Baobhan Sith": [],
    "Habetrot": [],
    "Red Hare": [],
    "Mandricardo": [],
    "Caenis": ["Caeneus"],
    "Pretender": [],
    "Kingprotea": [],
    "Tamamovitch Koyanskaya": [],
    "Kama": [],
    "Bazett Fraga McRemitz": [],
    "Caren Hortensia": [],
    "Illyasviel von Einzbern": [],
    "Miyu Edelfelt": [],
    "Chloe von Einzbern": [],
    "Shiki Ryougi": [],
    "Fujino Asagami": [],
    "Arcueid Brunestud": [],
    "Aoko Aozaki": [],
}

# 4. Connect to DB - batch exact match
conn = psycopg2.connect(host="localhost", port=5432, dbname="chaldeas", user="chaldeas", password="chaldeas_dev")
cur = conn.cursor()

# Collect all search names
all_search_names = set()
for bn in seen:
    all_search_names.add(bn)
    if bn in NAME_CORRECTIONS:
        for v in NAME_CORRECTIONS[bn]:
            all_search_names.add(v)

print(f"Total search names: {len(all_search_names)}")

# Batch query: exact match
name_list = list(all_search_names)
placeholders = ",".join(["%s"] * len(name_list))
cur.execute(f"SELECT DISTINCT name FROM persons WHERE name IN ({placeholders})", name_list)
found_names = {row[0] for row in cur.fetchall()}
print(f"Names found in DB: {len(found_names)}")

cur.close()
conn.close()

# 5. Classify results
results = []
for bn, s in sorted(seen.items()):
    name_ja = s["name_ja"]
    base_ja = re.sub(r"〔[^〕]+〕", "", name_ja).strip()
    lines = all_lines.get(name_ja, all_lines.get(base_ja, 0))

    search_names = [bn]
    if bn in NAME_CORRECTIONS:
        search_names.extend(NAME_CORRECTIONS[bn])

    matched_name = None
    for sn in search_names:
        if sn in found_names:
            matched_name = sn
            break

    # Classify: fictional (FGO/Nasuverse original) vs historical/mythological
    is_fictional = bn in NAME_CORRECTIONS and len(NAME_CORRECTIONS[bn]) == 0

    results.append({
        "name_en": bn,
        "name_ja": name_ja,
        "dialogue_lines": lines,
        "in_db": matched_name is not None,
        "db_match": matched_name,
        "is_fictional": is_fictional,
    })

in_db = [r for r in results if r["in_db"]]
not_in_db = [r for r in results if not r["in_db"]]
not_in_db_real = [r for r in not_in_db if not r["is_fictional"]]
not_in_db_fictional = [r for r in not_in_db if r["is_fictional"]]

print(f"\n{'='*70}")
print(f"  Total unique servants:          {len(results)}")
print(f"  Found in DB:                    {len(in_db)}")
print(f"  NOT in DB (total):              {len(not_in_db)}")
print(f"    - Historical/Mythological:    {len(not_in_db_real)}")
print(f"    - Fictional (FGO original):   {len(not_in_db_fictional)}")
print(f"{'='*70}")

not_in_db_real.sort(key=lambda x: -x["dialogue_lines"])

print(f"\n=== NOT in DB - Historical/Mythological ({len(not_in_db_real)}명) ===")
print(f"  (These could potentially be added to the persons DB)")
for i, r in enumerate(not_in_db_real, 1):
    lines_str = f"{r['dialogue_lines']:,}" if r["dialogue_lines"] > 0 else "0"
    print(f"  {i:3d}. {r['name_en']:45s} {r['name_ja']:30s} {lines_str:>8s} lines")

print(f"\n=== NOT in DB - Fictional/FGO Original ({len(not_in_db_fictional)}명) ===")
print(f"  (These are Nasuverse originals, not expected in historical DB)")
not_in_db_fictional.sort(key=lambda x: -x["dialogue_lines"])
for i, r in enumerate(not_in_db_fictional, 1):
    lines_str = f"{r['dialogue_lines']:,}" if r["dialogue_lines"] > 0 else "0"
    print(f"  {i:3d}. {r['name_en']:45s} {r['name_ja']:30s} {lines_str:>8s} lines")

print(f"\n=== Found in DB ({len(in_db)}명) ===")
in_db.sort(key=lambda x: -x["dialogue_lines"])
for i, r in enumerate(in_db, 1):
    lines_str = f"{r['dialogue_lines']:,}" if r["dialogue_lines"] > 0 else "0"
    alias = f" -> {r['db_match']}" if r["db_match"] != r["name_en"] else ""
    print(f"  {i:3d}. {r['name_en']:45s} {lines_str:>8s} lines{alias}")

# 6. Save results as JSON
from datetime import datetime

OUTPUT_DIR = Path(r"E:\chaldeas_data\processed\fgo\person_links")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

report = {
    "generated_at": datetime.now().isoformat(),
    "summary": {
        "total_unique_servants": len(results),
        "found_in_db": len(in_db),
        "not_in_db_total": len(not_in_db),
        "not_in_db_historical": len(not_in_db_real),
        "not_in_db_fictional": len(not_in_db_fictional),
    },
    "found_in_db": sorted(
        [{"name_en": r["name_en"], "name_ja": r["name_ja"], "db_match": r["db_match"], "dialogue_lines": r["dialogue_lines"]} for r in in_db],
        key=lambda x: -x["dialogue_lines"],
    ),
    "missing_historical": sorted(
        [{"name_en": r["name_en"], "name_ja": r["name_ja"], "dialogue_lines": r["dialogue_lines"]} for r in not_in_db_real],
        key=lambda x: -x["dialogue_lines"],
    ),
    "missing_fictional": sorted(
        [{"name_en": r["name_en"], "name_ja": r["name_ja"], "dialogue_lines": r["dialogue_lines"]} for r in not_in_db_fictional],
        key=lambda x: -x["dialogue_lines"],
    ),
}

out_path = OUTPUT_DIR / "fgo_db_comparison.json"
out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nResults saved to: {out_path}")
