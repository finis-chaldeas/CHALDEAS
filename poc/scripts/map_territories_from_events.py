"""
Map locations to territories based on event associations and geographical proximity.

Phase C of the territories pipeline:
1. For locations already mapped by P17 → skip
2. For unmapped locations with events → infer territory from event dates + location region
3. For unmapped locations near mapped ones → use nearest neighbor's territory

Usage:
    cd backend
    python ../poc/scripts/map_territories_from_events.py
"""
import sys
import math
import psycopg2
from collections import defaultdict

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_URL = 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas'

# Region → Territory mapping rules
# Format: (country, year_range) → territory_id candidates
# This is a simplified heuristic; the real mapping comes from P17 data
REGION_TERRITORY_RULES = {
    # Europe
    ('Greece', (-800, -146)): 'Ancient Greece',
    ('Greece', (-146, 395)): 'Roman Empire',
    ('Greece', (395, 1453)): 'Byzantine Empire',
    ('Greece', (1453, 1821)): 'Ottoman Empire',
    ('Italy', (-509, -27)): 'Roman Republic',
    ('Italy', (-27, 476)): 'Roman Empire',
    ('Italy', (962, 1806)): 'Holy Roman Empire',
    ('Turkey', (-550, -330)): 'Achaemenid Empire',
    ('Turkey', (-27, 395)): 'Roman Empire',
    ('Turkey', (395, 1453)): 'Byzantine Empire',
    ('Turkey', (1299, 1922)): 'Ottoman Empire',
    ('France', (800, 888)): 'Carolingian Empire',
    ('France', (987, 1792)): 'Kingdom of France',
    ('United Kingdom', (927, 1707)): 'Kingdom of England',
    ('United Kingdom', (1801, 1922)): 'United Kingdom of Great Britain and Ireland',
    ('Russia', (882, 1240)): "Kievan Rus'",
    ('Russia', (1547, 1721)): 'Tsardom of Russia',
    ('Russia', (1721, 1917)): 'Russian Empire',
    ('Russia', (1922, 1991)): 'Soviet Union',

    # Middle East
    ('Iraq', (-2334, -2154)): 'Akkadian Empire',
    ('Iraq', (-911, -609)): 'Neo-Assyrian Empire',
    ('Iraq', (-626, -539)): 'Neo-Babylonian Empire',
    ('Iraq', (-550, -330)): 'Achaemenid Empire',
    ('Iraq', (632, 661)): 'Rashidun Caliphate',
    ('Iraq', (661, 750)): 'Umayyad Caliphate',
    ('Iraq', (1299, 1922)): 'Ottoman Empire',
    ('Iran', (-550, -330)): 'Achaemenid Empire',
    ('Iran', (-247, 224)): 'Parthian Empire',
    ('Iran', (224, 651)): 'Sasanian Empire',
    ('Iran', (1501, 1736)): 'Safavid dynasty',
    ('Egypt', (-3100, -30)): 'Ancient Egypt',
    ('Egypt', (-30, 395)): 'Roman Empire',
    ('Egypt', (632, 661)): 'Rashidun Caliphate',
    ('Egypt', (1299, 1922)): 'Ottoman Empire',
    ('Syria', (-550, -330)): 'Achaemenid Empire',
    ('Syria', (-312, -63)): 'Seleucid Empire',
    ('Syria', (-63, 395)): 'Roman Empire',
    ('Syria', (632, 661)): 'Rashidun Caliphate',
    ('Syria', (661, 750)): 'Umayyad Caliphate',
    ('Syria', (1299, 1922)): 'Ottoman Empire',

    # Asia
    ('India', (-322, -185)): 'Maurya Empire',
    ('India', (320, 550)): 'Gupta Empire',
    ('India', (1526, 1857)): 'Mughal Empire',
    ('China', (-221, -206)): 'Qin dynasty',
    ('China', (-206, 220)): 'Han dynasty',
    ('China', (618, 907)): 'Tang dynasty',
    ('China', (960, 1279)): 'Song dynasty',
    ('China', (1271, 1368)): 'Yuan dynasty',
    ('China', (1368, 1644)): 'Ming dynasty',
    ('China', (1636, 1912)): 'Qing dynasty',
    ('South Korea', (-57, 668)): 'Silla',
    ('South Korea', (668, 935)): 'Unified Silla',
    ('South Korea', (918, 1392)): 'Goryeo',
    ('South Korea', (1392, 1897)): 'Joseon',
    ('South Korea', (1897, 1910)): 'Korean Empire',
}


def build_territory_name_map():
    """Build name → territory_id mapping."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM territories")
    mapping = {row[1]: row[0] for row in cur.fetchall()}
    cur.close()
    conn.close()
    return mapping


def get_unmapped_locations():
    """Get locations that don't have any territory_locations entries."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT l.id, l.name, l.country, l.latitude, l.longitude
        FROM locations l
        LEFT JOIN territory_locations tl ON tl.location_id = l.id
        WHERE tl.id IS NULL
          AND l.country IS NOT NULL
    """)
    locations = cur.fetchall()
    cur.close()
    conn.close()
    return locations


def get_events_for_locations(location_ids):
    """Get event dates for locations."""
    if not location_ids:
        return {}

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Get events via primary_location_id
    placeholders = ','.join(['%s'] * len(location_ids))
    cur.execute(f"""
        SELECT primary_location_id, date_start, date_end
        FROM events
        WHERE primary_location_id IN ({placeholders})
          AND date_start IS NOT NULL
        ORDER BY primary_location_id, date_start
    """, location_ids)

    events_by_location = defaultdict(list)
    for loc_id, date_start, date_end in cur.fetchall():
        events_by_location[loc_id].append((date_start, date_end))

    # Also check event_locations association
    cur.execute(f"""
        SELECT el.location_id, e.date_start, e.date_end
        FROM event_locations el
        JOIN events e ON e.id = el.event_id
        WHERE el.location_id IN ({placeholders})
          AND e.date_start IS NOT NULL
        ORDER BY el.location_id, e.date_start
    """, location_ids)

    for loc_id, date_start, date_end in cur.fetchall():
        events_by_location[loc_id].append((date_start, date_end))

    cur.close()
    conn.close()
    return events_by_location


def map_location_to_territory(country, event_years, territory_name_map):
    """Given a country and event years, find matching territories."""
    matches = []

    for (rule_country, (year_from, year_to)), territory_name in REGION_TERRITORY_RULES.items():
        if country != rule_country:
            continue

        territory_id = territory_name_map.get(territory_name)
        if territory_id is None:
            continue

        # Check if any event falls within this territory's time range
        for year_start, year_end in event_years:
            if year_start is not None and year_from <= year_start <= year_to:
                matches.append({
                    'territory_id': territory_id,
                    'territory_name': territory_name,
                    'valid_from': year_from,
                    'valid_until': year_to,
                })
                break  # One match per rule is enough

    return matches


def run_event_based_mapping():
    """Map unmapped locations to territories using event dates."""
    print("=== Phase C: Event-based Territory Mapping ===\n")

    territory_name_map = build_territory_name_map()
    print(f"Territory name map: {len(territory_name_map)} entries")

    unmapped = get_unmapped_locations()
    print(f"Unmapped locations: {len(unmapped)}")

    if not unmapped:
        print("All locations already mapped!")
        return

    # Get event dates for unmapped locations
    location_ids = [loc[0] for loc in unmapped]
    events_by_location = get_events_for_locations(location_ids)
    print(f"Locations with events: {len(events_by_location)}")

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    inserted = 0
    mapped_by_rule = 0
    no_events = 0
    no_match = 0

    for loc_id, loc_name, country, lat, lng in unmapped:
        event_years = events_by_location.get(loc_id, [])

        if not event_years:
            no_events += 1
            continue

        matches = map_location_to_territory(country, event_years, territory_name_map)

        if not matches:
            no_match += 1
            continue

        for match in matches:
            try:
                cur.execute("""
                    INSERT INTO territory_locations (territory_id, location_id, valid_from, valid_until, relation_type)
                    VALUES (%s, %s, %s, %s, 'contains')
                    ON CONFLICT ON CONSTRAINT territory_locations_territory_id_location_id_valid_from_key DO NOTHING
                """, (match['territory_id'], loc_id, match['valid_from'], match['valid_until']))
                if cur.rowcount > 0:
                    inserted += 1
                    mapped_by_rule += 1
            except Exception as e:
                print(f"  ERROR: {loc_name} -> {match['territory_name']}: {e}")
                conn.rollback()

    conn.commit()

    print(f"\n=== Event-based mapping results ===")
    print(f"Mapped by rules: {mapped_by_rule}")
    print(f"Inserted: {inserted} territory_location entries")
    print(f"No events: {no_events}")
    print(f"No rule match: {no_match}")

    cur.execute("SELECT COUNT(*) FROM territory_locations")
    print(f"\nTotal territory_locations in DB: {cur.fetchone()[0]}")

    cur.close()
    conn.close()


def run_modern_country_mapping():
    """For locations with a modern country, map to the modern nation-state territory."""
    print("\n=== Phase C-2: Modern Country Mapping ===\n")

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Map modern countries to territories
    MODERN_COUNTRY_MAP = {
        'United States': ('United States', 1776),
        'United Kingdom': ('United Kingdom', 1922),
        'France': ('France', 1792),
        'Germany': ('Germany', 1871),
        'Italy': ('Italy', 1861),
        'Russia': ('Russia', 1547),
        'China': ('China', 1912),
        'Japan': ('Japan', -660),
        'India': ('India', 1947),
        'South Korea': ('South Korea', 1948),
        'North Korea': ('North Korea', 1948),
        'Israel': ('Israel', 1948),
    }

    # Get territory IDs
    territory_name_map = {}
    cur.execute("SELECT id, name FROM territories")
    for tid, name in cur.fetchall():
        territory_name_map[name] = tid

    inserted = 0
    for country_name, (territory_name, founded_year) in MODERN_COUNTRY_MAP.items():
        territory_id = territory_name_map.get(territory_name)
        if territory_id is None:
            print(f"  WARNING: Territory not found: {territory_name}")
            continue

        # Map all locations in this country that don't have a modern mapping
        cur.execute("""
            INSERT INTO territory_locations (territory_id, location_id, valid_from, valid_until, relation_type)
            SELECT %s, l.id, %s, NULL, 'contains'
            FROM locations l
            WHERE l.country = %s
              AND NOT EXISTS (
                  SELECT 1 FROM territory_locations tl
                  WHERE tl.location_id = l.id
                    AND tl.territory_id = %s
              )
        """, (territory_id, founded_year, country_name, territory_id))

        count = cur.rowcount
        if count > 0:
            print(f"  {country_name} -> {territory_name}: {count} locations")
            inserted += count

    conn.commit()

    print(f"\nModern country mapping: {inserted} entries inserted")

    cur.execute("SELECT COUNT(*) FROM territory_locations")
    print(f"Total territory_locations in DB: {cur.fetchone()[0]}")

    cur.close()
    conn.close()


if __name__ == '__main__':
    run_event_based_mapping()
    run_modern_country_mapping()
