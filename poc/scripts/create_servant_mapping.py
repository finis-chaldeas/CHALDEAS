"""
FGO Servant -> DB persons mapping generation.

Produces servant_db_mapping.json in the format expected by backend/app/api/v1/servants.py:
  { "mapped": [...], "fgo_original": [...], "not_found": [...] }

Usage:
    cd C:/Projects/Chaldeas
    python poc/scripts/create_servant_mapping.py
"""
import json
import sys
import psycopg2
from pathlib import Path

# Windows UTF-8 console fix
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).parent.parent.parent

# FGO servant name -> Wikidata QID (manually verified)
SERVANT_QIDS = {
    # Saber
    "Artoria Pendragon": "Q45556",
    "Nero Claudius": "Q1413",
    "Julius Caesar": "Q1048",
    "Gawain": "Q193969",
    "Lancelot": "Q214963",
    "Mordred": "Q1087720",
    "Fergus mac Roich": "Q1307208",
    "Miyamoto Musashi": "Q319824",
    "Sigurd": "Q152952",
    "Rama": "Q170596",
    "Jason": "Q191921",
    "Attila": "Q36724",

    # Archer
    "Gilgamesh": "Q41620",
    "Robin Hood": "Q122756",
    "Arjuna": "Q623218",
    "Nikola Tesla": "Q9036",
    "Napoleon Bonaparte": "Q517",
    "Oda Nobunaga": "Q169124",
    "Tristan": "Q208385",

    # Lancer
    "Cu Chulainn": "Q212903",
    "Leonidas I": "Q152619",
    "Romulus": "Q6116",
    "Hector": "Q168395",
    "Scathach": "Q1062699",
    "Karna": "Q732622",
    "Brynhildr": "Q152983",
    "Vlad III": "Q43718",
    "Enkidu": "Q155826",
    "Diarmuid Ua Duibhne": "Q1129108",
    "Fionn mac Cumhaill": "Q519148",
    "Parvati": "Q271099",

    # Rider
    "Iskandar": "Q8409",
    "Medusa": "Q38143",
    "Boudica": "Q130746",
    "Francis Drake": "Q36517",
    "Achilles": "Q41746",
    "Ivan the Terrible": "Q7994",
    "Marie Antoinette": "Q47365",
    "Ozymandias": "Q1279",
    "Blackbeard": "Q193489",
    "Odysseus": "Q47108",

    # Caster
    "Medea": "Q188836",
    "Hans Christian Andersen": "Q5673",
    "William Shakespeare": "Q692",
    "Tamamo-no-Mae": "Q1264785",
    "Merlin": "Q188958",
    "Leonardo da Vinci": "Q762",
    "Paracelsus": "Q83428",
    "Thomas Edison": "Q8743",
    "Helena Blavatsky": "Q179991",
    "Circe": "Q134762",
    "Scheherazade": "Q1186638",
    "Anastasia": "Q159544",
    "Zhuge Liang": "Q207929",
    "Charles Babbage": "Q4588",
    "Wolfgang Amadeus Mozart": "Q254",
    "Skadi": "Q679972",
    "Nitocris": "Q553939",
    "Qin Shi Huang": "Q7192",

    # Assassin
    "Shuten-Douji": "Q2370889",
    "Cleopatra": "Q635",

    # Berserker
    "Heracles": "Q122248",
    "Spartacus": "Q46405",
    "Caligula": "Q1409",
    "Darius III": "Q130368",
    "Florence Nightingale": "Q37103",
    "Lu Bu": "Q313618",
    "Xiang Yu": "Q180662",
    "Minamoto-no-Raikou": None,

    # Ruler
    "Jeanne d'Arc": "Q7226",

    # Avenger
    "Antonio Salieri": "Q51088",

    # FGO Original (explicitly None)
    "Medb": None,
}

FGO_DATA_PATH = PROJECT_ROOT / "data/raw/atlas_academy/fgo_historical_figures.json"
OUTPUT_PATH = PROJECT_ROOT / "data/raw/atlas_academy/servant_db_mapping.json"


def create_mapping():
    """Generate servant-to-person mapping in the format expected by servants API."""
    with open(FGO_DATA_PATH, encoding='utf-8') as f:
        fgo_data = json.load(f)

    conn = psycopg2.connect(
        host='localhost', port=5432, dbname='chaldeas',
        user='chaldeas', password='chaldeas_dev'
    )
    cur = conn.cursor()

    mapped = []
    fgo_original = []
    not_found = []

    for servant in fgo_data:
        fgo_name = servant['fgo_name']
        hist_name = servant.get('historical_name', fgo_name)

        # Check if we have a QID mapping
        qid = SERVANT_QIDS.get(fgo_name)

        if qid is not None:
            # Look up by Wikidata QID
            cur.execute(
                "SELECT id, name, name_ko, wikidata_id FROM persons WHERE wikidata_id = %s",
                (qid,)
            )
            person = cur.fetchone()

            if person:
                mapped.append({
                    "fgo_name": fgo_name,
                    "person_id": person[0],
                    "person_name": person[1],
                    "person_name_ko": person[2],
                    "qid": person[3],
                })
                print(f"  MATCHED: {fgo_name} -> {person[1]} (id={person[0]})")
            else:
                # QID not in DB, try name match
                cur.execute(
                    "SELECT id, name, name_ko, wikidata_id FROM persons WHERE name ILIKE %s LIMIT 1",
                    (f"%{hist_name}%",)
                )
                person = cur.fetchone()
                if person:
                    mapped.append({
                        "fgo_name": fgo_name,
                        "person_id": person[0],
                        "person_name": person[1],
                        "person_name_ko": person[2],
                        "qid": person[3],
                    })
                    print(f"  MATCHED (name): {fgo_name} -> {person[1]} (id={person[0]})")
                else:
                    not_found.append(fgo_name)
                    print(f"  NOT FOUND: {fgo_name} (QID {qid} not in DB)")

        elif fgo_name in SERVANT_QIDS and qid is None:
            # Explicitly marked as no historical counterpart
            fgo_original.append(fgo_name)
            print(f"  FGO ORIGINAL: {fgo_name}")
        else:
            # No QID mapping defined, try name match
            cur.execute(
                "SELECT id, name, name_ko, wikidata_id FROM persons WHERE name ILIKE %s LIMIT 1",
                (f"%{hist_name}%",)
            )
            person = cur.fetchone()
            if person:
                mapped.append({
                    "fgo_name": fgo_name,
                    "person_id": person[0],
                    "person_name": person[1],
                    "person_name_ko": person[2],
                    "qid": person[3],
                })
                print(f"  MATCHED (fallback): {fgo_name} -> {person[1]} (id={person[0]})")
            else:
                not_found.append(fgo_name)
                print(f"  NOT FOUND: {fgo_name}")

    conn.close()

    output = {
        "mapped": mapped,
        "fgo_original": fgo_original,
        "not_found": not_found
    }

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nResults: {len(mapped)} mapped, {len(fgo_original)} FGO original, {len(not_found)} not found")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    create_mapping()
