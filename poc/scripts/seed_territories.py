"""
Seed major historical territories into the territories table.

Phase A of the territories pipeline:
1. Query Wikidata SPARQL for major historical states/empires/kingdoms
2. Insert into territories table with name, name_ko, wikidata_id, type, dates

Usage:
    cd backend
    python ../poc/scripts/seed_territories.py
"""
import sys
import json
import time
import requests
import psycopg2

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_URL = 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas'
WIKIDATA_SPARQL = 'https://query.wikidata.org/sparql'

# Major historical territories to seed - curated list
# Format: (wikidata_id, name, name_ko, territory_type, valid_from, valid_until)
CURATED_TERRITORIES = [
    # Ancient Empires
    ("Q11768", "Ancient Egypt", "고대 이집트", "kingdom", -3100, -30),
    ("Q2362761", "Akkadian Empire", "아카드 제국", "empire", -2334, -2154),
    ("Q2325225", "Neo-Sumerian Empire", "우르 제3왕조", "empire", -2112, -2004),
    ("Q2277866", "Old Babylonian Empire", "고대 바빌로니아", "empire", -1894, -1595),
    ("Q178413", "Hittite Empire", "히타이트 제국", "empire", -1600, -1178),
    ("Q41137", "Neo-Assyrian Empire", "신아시리아 제국", "empire", -911, -609),
    ("Q5765609", "Neo-Babylonian Empire", "신바빌로니아 제국", "empire", -626, -539),
    ("Q389688", "Achaemenid Empire", "아케메네스 제국", "empire", -550, -330),
    ("Q11772", "Ancient Greece", "고대 그리스", "civilization", -800, -146),
    ("Q1439", "Ancient Athens", "고대 아테네", "city_state", -508, -322),
    ("Q40061", "Sparta", "스파르타", "city_state", -900, -192),
    ("Q2715164", "Macedonian Empire", "마케도니아 제국", "empire", -336, -323),
    ("Q17", "Japan", "일본", "empire", -660, None),

    # Hellenistic
    ("Q170571", "Ptolemaic Kingdom", "프톨레마이오스 왕조", "kingdom", -305, -30),
    ("Q187997", "Seleucid Empire", "셀레우코스 제국", "empire", -312, -63),
    ("Q188737", "Antigonid dynasty", "안티고노스 왕조", "kingdom", -306, -168),

    # Roman
    ("Q2277", "Roman Republic", "로마 공화국", "republic", -509, -27),
    ("Q2915", "Roman Empire", "로마 제국", "empire", -27, 476),
    ("Q12544", "Byzantine Empire", "비잔티움 제국", "empire", 330, 1453),

    # Asian
    ("Q7183", "Maurya Empire", "마우리아 왕조", "empire", -322, -185),
    ("Q8479", "Gupta Empire", "굽타 왕조", "empire", 320, 550),
    ("Q9683", "Mughal Empire", "무굴 제국", "empire", 1526, 1857),
    ("Q7462", "Qin dynasty", "진나라", "dynasty", -221, -206),
    ("Q7209", "Han dynasty", "한나라", "dynasty", -206, 220),
    ("Q7405", "Tang dynasty", "당나라", "dynasty", 618, 907),
    ("Q7525", "Song dynasty", "송나라", "dynasty", 960, 1279),
    ("Q12490", "Yuan dynasty", "원나라", "dynasty", 1271, 1368),
    ("Q9903", "Ming dynasty", "명나라", "dynasty", 1368, 1644),
    ("Q8733", "Qing dynasty", "청나라", "dynasty", 1636, 1912),
    ("Q7204", "Mongol Empire", "몽골 제국", "empire", 1206, 1368),
    ("Q487907", "Goryeo", "고려", "kingdom", 918, 1392),
    ("Q28179", "Joseon", "조선", "kingdom", 1392, 1897),
    ("Q170770", "Goguryeo", "고구려", "kingdom", -37, 668),
    ("Q172640", "Baekje", "백제", "kingdom", -18, 660),
    ("Q173399", "Silla", "신라", "kingdom", -57, 935),
    ("Q83090", "Unified Silla", "통일신라", "kingdom", 668, 935),
    ("Q8740", "Korean Empire", "대한제국", "empire", 1897, 1910),

    # Persian / Islamic
    ("Q11739", "Parthian Empire", "파르티아 제국", "empire", -247, 224),
    ("Q170596", "Sasanian Empire", "사산 제국", "empire", 224, 651),
    ("Q12486", "Rashidun Caliphate", "라시둔 칼리프국", "caliphate", 632, 661),
    ("Q8575", "Umayyad Caliphate", "우마이야 칼리프국", "caliphate", 661, 750),
    ("Q12490", "Abbasid Caliphate", "아바스 칼리프국", "caliphate", 750, 1258),  # Q12490 is correct for Abbasid
    ("Q12560", "Ottoman Empire", "오스만 제국", "empire", 1299, 1922),
    ("Q170495", "Safavid dynasty", "사파비 왕조", "dynasty", 1501, 1736),

    # Medieval Europe
    ("Q43287", "Holy Roman Empire", "신성 로마 제국", "empire", 962, 1806),
    ("Q71084", "Carolingian Empire", "카롤링거 제국", "empire", 800, 888),
    ("Q58296", "Kingdom of France", "프랑스 왕국", "kingdom", 987, 1792),
    ("Q179876", "Kingdom of England", "잉글랜드 왕국", "kingdom", 927, 1707),
    ("Q172579", "Kingdom of Scotland", "스코틀랜드 왕국", "kingdom", 843, 1707),
    ("Q380260", "Kievan Rus'", "키예프 루시", "principality", 882, 1240),
    ("Q133356", "Grand Duchy of Moscow", "모스크바 대공국", "duchy", 1263, 1547),
    ("Q159", "Russia", "러시아", "empire", 1547, None),
    ("Q180573", "Tsardom of Russia", "러시아 차르국", "tsardom", 1547, 1721),
    ("Q34266", "Russian Empire", "러시아 제국", "empire", 1721, 1917),
    ("Q15180", "Soviet Union", "소비에트 연방", "federation", 1922, 1991),
    ("Q11750", "Kingdom of Sicily", "시칠리아 왕국", "kingdom", 1130, 1816),
    ("Q172107", "Republic of Venice", "베네치아 공화국", "republic", 697, 1797),

    # Colonial & Modern
    ("Q29999", "Kingdom of the Netherlands", "네덜란드 왕국", "kingdom", 1815, None),
    ("Q174193", "United Kingdom of Great Britain and Ireland", "그레이트브리튼 아일랜드 연합왕국", "kingdom", 1801, 1922),
    ("Q145", "United Kingdom", "영국", "kingdom", 1922, None),
    ("Q30", "United States", "미국", "republic", 1776, None),
    ("Q142", "France", "프랑스", "republic", 1792, None),
    ("Q183", "Germany", "독일", "republic", 1871, None),
    ("Q38", "Italy", "이탈리아", "kingdom", 1861, None),
    ("Q148", "China", "중국", "republic", 1912, None),
    ("Q668", "India", "인도", "republic", 1947, None),
    ("Q884", "South Korea", "대한민국", "republic", 1948, None),
    ("Q423", "North Korea", "조선민주주의인민공화국", "republic", 1948, None),
    ("Q801", "Israel", "이스라엘", "republic", 1948, None),

    # Americas
    ("Q12542", "Aztec Empire", "아즈텍 제국", "empire", 1428, 1521),
    ("Q28573", "Inca Empire", "잉카 제국", "empire", 1438, 1533),
    ("Q48335", "Spanish Empire", "스페인 제국", "empire", 1492, 1975),
    ("Q172466", "Portuguese Empire", "포르투갈 제국", "empire", 1415, 1999),
    ("Q161885", "British Empire", "대영 제국", "empire", 1583, 1997),
    ("Q178550", "French colonial empire", "프랑스 식민제국", "empire", 1534, 1980),

    # African
    ("Q188913", "Kingdom of Kush", "쿠시 왕국", "kingdom", -1070, 350),
    ("Q133871", "Kingdom of Aksum", "악숨 왕국", "kingdom", 100, 940),
    ("Q193272", "Mali Empire", "말리 제국", "empire", 1235, 1600),
    ("Q214770", "Songhai Empire", "송가이 제국", "empire", 1464, 1591),
    ("Q187814", "Kingdom of Kongo", "콩고 왕국", "kingdom", 1390, 1914),
    ("Q271623", "Zulu Kingdom", "줄루 왕국", "kingdom", 1816, 1897),
]


def deduplicate_territories(territories):
    """Remove duplicate wikidata_ids, keeping first occurrence."""
    seen = set()
    deduped = []
    for t in territories:
        qid = t[0]
        if qid not in seen:
            seen.add(qid)
            deduped.append(t)
        else:
            print(f"  [SKIP] Duplicate QID {qid}: {t[1]}")
    return deduped


def fetch_wikidata_territories_sparql():
    """Fetch additional territories from Wikidata SPARQL to supplement curated list."""
    query = """
    SELECT ?item ?itemLabel ?itemLabel_ko ?inception ?dissolved ?instanceLabel WHERE {
      {
        ?item wdt:P31/wdt:P279* wd:Q3024240 .  # historical country
      } UNION {
        ?item wdt:P31/wdt:P279* wd:Q3624078 .  # sovereign state
      }
      ?item wdt:P571 ?inception .
      OPTIONAL { ?item wdt:P576 ?dissolved . }
      OPTIONAL {
        ?item rdfs:label ?itemLabel_ko .
        FILTER(LANG(?itemLabel_ko) = "ko")
      }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
    }
    ORDER BY ?inception
    LIMIT 200
    """
    headers = {
        'Accept': 'application/sparql-results+json',
        'User-Agent': 'Chaldeas/1.0 (historical data project)'
    }
    try:
        resp = requests.get(WIKIDATA_SPARQL, params={'query': query}, headers=headers, timeout=60)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"SPARQL query failed: {resp.status_code}")
            return None
    except Exception as e:
        print(f"SPARQL query error: {e}")
        return None


def seed_territories():
    """Insert curated territories into the database."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Deduplicate
    territories = deduplicate_territories(CURATED_TERRITORIES)
    print(f"\n=== Seeding {len(territories)} territories ===\n")

    inserted = 0
    skipped = 0

    for qid, name, name_ko, ttype, valid_from, valid_until in territories:
        # Check if already exists
        cur.execute("SELECT id FROM territories WHERE wikidata_id = %s", (qid,))
        if cur.fetchone():
            print(f"  [EXISTS] {name} ({qid})")
            skipped += 1
            continue

        cur.execute("""
            INSERT INTO territories (name, name_ko, wikidata_id, territory_type, founded_year, dissolved_year)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (name, name_ko, qid, ttype, valid_from, valid_until))
        tid = cur.fetchone()[0]
        print(f"  [INSERT] #{tid} {name} ({qid}) [{valid_from} ~ {valid_until}]")
        inserted += 1

    conn.commit()
    print(f"\n=== Done: {inserted} inserted, {skipped} skipped ===")

    # Verify
    cur.execute("SELECT COUNT(*) FROM territories")
    print(f"Total territories in DB: {cur.fetchone()[0]}")

    cur.close()
    conn.close()


def enrich_from_sparql():
    """Try to fetch additional territories from SPARQL and add if not already present."""
    print("\n=== Fetching additional territories from Wikidata SPARQL ===\n")
    data = fetch_wikidata_territories_sparql()
    if not data:
        print("SPARQL fetch failed, skipping enrichment")
        return

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    results = data.get('results', {}).get('bindings', [])
    print(f"SPARQL returned {len(results)} results")

    inserted = 0
    for r in results:
        uri = r.get('item', {}).get('value', '')
        qid = uri.split('/')[-1] if uri else None
        if not qid:
            continue

        # Skip if already exists
        cur.execute("SELECT id FROM territories WHERE wikidata_id = %s", (qid,))
        if cur.fetchone():
            continue

        name = r.get('itemLabel', {}).get('value', '')
        name_ko = r.get('itemLabel_ko', {}).get('value', None)
        inception = r.get('inception', {}).get('value', '')
        dissolved = r.get('dissolved', {}).get('value', None)
        instance_type = r.get('instanceLabel', {}).get('value', 'kingdom')

        # Parse year from datetime
        try:
            year_from = int(inception[:5]) if inception else None
            # Handle BCE (negative years in ISO 8601)
            if inception and inception.startswith('-'):
                year_from = int(inception[:5])
        except (ValueError, IndexError):
            year_from = None

        try:
            year_until = int(dissolved[:5]) if dissolved else None
            if dissolved and dissolved.startswith('-'):
                year_until = int(dissolved[:5])
        except (ValueError, IndexError):
            year_until = None

        # Map instance type
        ttype = 'kingdom'  # default
        if 'empire' in instance_type.lower():
            ttype = 'empire'
        elif 'republic' in instance_type.lower():
            ttype = 'republic'
        elif 'caliphate' in instance_type.lower():
            ttype = 'caliphate'
        elif 'dynasty' in instance_type.lower():
            ttype = 'dynasty'

        if not name or name == qid:
            continue

        cur.execute("""
            INSERT INTO territories (name, name_ko, wikidata_id, territory_type, founded_year, dissolved_year)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (name, name_ko, qid, ttype, year_from, year_until))
        tid = cur.fetchone()[0]
        print(f"  [SPARQL] #{tid} {name} ({qid}) [{year_from} ~ {year_until}]")
        inserted += 1

    conn.commit()
    print(f"\nSPARQL enrichment: {inserted} new territories added")

    cur.execute("SELECT COUNT(*) FROM territories")
    print(f"Total territories in DB: {cur.fetchone()[0]}")

    cur.close()
    conn.close()


if __name__ == '__main__':
    seed_territories()
    time.sleep(2)  # Be nice to Wikidata API
    enrich_from_sparql()
