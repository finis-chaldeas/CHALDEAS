"""
이벤트 관계 + 시대(Periods) 채우기

3-Layer 전략으로 event_relationships 테이블 채우기 + periods 테이블 생성:
  Step 0: Periods 정의 (50년 단위) + events.period_id 매핑
  Step 1: Layer 1 — 형제 체인 (같은 parent 아래 이벤트를 날짜순 연결)
  Step 2: Layer 2 — 인물 경로 체인 (같은 인물 참여 이벤트를 날짜순 연결)
  Step 3: Layer 3 — Wikidata 인과관계 (P155/P156/P1542/P1478)
  Step 4: 결과 리포트

Usage:
    cd backend
    python ../poc/scripts/fill_event_relationships.py --dry-run
    python ../poc/scripts/fill_event_relationships.py
    python ../poc/scripts/fill_event_relationships.py --step 0
    python ../poc/scripts/fill_event_relationships.py --step 1 --dry-run
"""

import sys
import os
import json
import time
import argparse
import requests
import psycopg2
from pathlib import Path
from collections import defaultdict
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_URL = 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas'
CACHE_PATH = Path(r'C:\Projects\Chaldeas\poc\data\wikidata\event_causal_cache.json')
WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
BATCH_SIZE = 50
HEADERS = {
    'User-Agent': 'ChaldeasBot/1.0 (https://www.chaldeas.site; chaldeas.archive@gmail.com)',
    'Accept': 'application/json',
}


# ═══════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════

def get_conn():
    return psycopg2.connect(DB_URL)


def fetch_wikidata_batch(qids, props='claims', retries=3):
    """Wikidata API 배치 호출."""
    params = {
        'action': 'wbgetentities',
        'ids': '|'.join(qids),
        'props': props,
        'format': 'json',
    }
    for attempt in range(retries):
        try:
            resp = requests.get(WIKIDATA_API, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return resp.json().get('entities', {})
        except requests.exceptions.HTTPError:
            if resp.status_code in (429, 403):
                wait = (attempt + 1) * 2
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  API error: HTTP {resp.status_code}")
                return {}
        except Exception as e:
            print(f"  API error: {e}")
            if attempt < retries - 1:
                time.sleep(1)
    return {}


def extract_qid_claims(entity_data, prop):
    """엔티티에서 특정 속성의 QID 값 추출."""
    claims = entity_data.get('claims', {})
    values = []
    for claim in claims.get(prop, []):
        mainsnak = claim.get('mainsnak', {})
        datavalue = mainsnak.get('datavalue', {})
        if datavalue.get('type') == 'wikibase-entityid':
            qid = 'Q' + str(datavalue['value']['numeric-id'])
            values.append(qid)
    return values


def insert_relationships(cur, relationships, dry_run=False):
    """event_relationships 테이블에 배치 삽입. 중복 무시."""
    if not relationships:
        return 0

    inserted = 0
    for rel in relationships:
        if dry_run:
            inserted += 1
            continue
        try:
            cur.execute("""
                INSERT INTO event_relationships (from_event_id, to_event_id, relationship_type,
                                                  strength, confidence, certainty, evidence_type, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                rel['from_id'], rel['to_id'], rel['type'],
                rel.get('strength', 3), rel.get('confidence', 0.7),
                rel.get('certainty', 'probable'), rel.get('evidence_type', 'inference'),
                rel.get('description'),
            ))
            inserted += 1
        except psycopg2.errors.UniqueViolation:
            cur.connection.rollback()
        except psycopg2.errors.ForeignKeyViolation:
            cur.connection.rollback()

    return inserted


# ═══════════════════════════════════════════
# Step 0: Periods Definition
# ═══════════════════════════════════════════

def step0_create_periods(dry_run=False):
    """50년 단위로 periods 테이블 생성 + events.period_id 매핑."""
    print("\n" + "=" * 60)
    print("STEP 0: Create Periods (50-year buckets)")
    print("=" * 60)

    conn = get_conn()
    cur = conn.cursor()

    # Check existing periods
    cur.execute("SELECT COUNT(*) FROM periods")
    existing = cur.fetchone()[0]
    if existing > 0:
        print(f"  Already {existing} periods exist. Skipping creation.")
        print(f"  (Delete existing periods first if you want to recreate)")
        # Still map events to periods
    else:
        # Generate periods: BCE 3000 to CE 2050
        periods = []
        # BCE periods (negative years)
        for start in range(-3000, 0, 50):
            end = start + 49
            if start < -1000:
                name = f"{abs(start)}-{abs(end)} BCE"
                name_ko = f"기원전 {abs(start)}-{abs(end)}년"
            elif start < 0:
                name = f"{abs(start)}-{abs(end)} BCE"
                name_ko = f"기원전 {abs(start)}-{abs(end)}년"
            slug = f"bce-{abs(start)}-{abs(end)}"
            periods.append((name, name_ko, slug, start, end, 'longue_duree'))

        # CE periods
        for start in range(1, 2051, 50):
            end = start + 49
            name = f"{start}-{end} CE"
            name_ko = f"서기 {start}-{end}년"
            slug = f"ce-{start}-{end}"
            periods.append((name, name_ko, slug, start, end, 'longue_duree'))

        total = len(periods)
        print(f"  Generating {total} periods (BCE 3000 ~ CE 2050, 50yr each)")

        if not dry_run:
            for name, name_ko, slug, year_start, year_end, scale in periods:
                cur.execute("""
                    INSERT INTO periods (name, name_ko, slug, year_start, year_end, scale)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (slug) DO NOTHING
                """, (name, name_ko, slug, year_start, year_end, scale))
            conn.commit()
            print(f"  Inserted {total} periods")
        else:
            print(f"  [DRY RUN] Would insert {total} periods")
            print(f"  Samples: {periods[0][0]}, {periods[30][0]}, {periods[-1][0]}")

    # Map events to periods
    cur.execute("SELECT COUNT(*) FROM periods")
    period_count = cur.fetchone()[0]
    if period_count == 0:
        print("  No periods to map events to.")
        cur.close()
        conn.close()
        return {'periods_created': 0, 'events_mapped': 0}

    # Load periods for mapping
    cur.execute("SELECT id, year_start, year_end FROM periods ORDER BY year_start")
    period_ranges = cur.fetchall()  # [(id, start, end), ...]

    # Count events without period
    cur.execute("SELECT COUNT(*) FROM events WHERE period_id IS NULL AND date_start IS NOT NULL")
    unmapped = cur.fetchone()[0]
    print(f"\n  Events without period_id (with date_start): {unmapped:,}")

    if unmapped > 0:
        if not dry_run:
            # Map events to periods using date_start
            mapped = 0
            for period_id, p_start, p_end in period_ranges:
                cur.execute("""
                    UPDATE events SET period_id = %s
                    WHERE date_start >= %s AND date_start <= %s AND period_id IS NULL
                """, (period_id, p_start, p_end))
                mapped += cur.rowcount

            conn.commit()
            print(f"  Mapped {mapped:,} events to periods")
        else:
            print(f"  [DRY RUN] Would map ~{unmapped:,} events to periods")

    # Summary
    cur.execute("SELECT COUNT(*) FROM events WHERE period_id IS NOT NULL")
    total_mapped = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM events")
    total_events = cur.fetchone()[0]
    print(f"\n  --- Step 0 Results ---")
    print(f"    Periods: {period_count}")
    print(f"    Events with period_id: {total_mapped:,}/{total_events:,} ({total_mapped/total_events*100:.1f}%)")

    cur.close()
    conn.close()
    return {'periods_created': period_count, 'events_mapped': total_mapped}


# ═══════════════════════════════════════════
# Step 1: Sibling Chains (same parent, date-ordered)
# ═══════════════════════════════════════════

def step1_sibling_chains(dry_run=False):
    """같은 parent_event_id 아래 형제 이벤트를 날짜순으로 연결."""
    print("\n" + "=" * 60)
    print("STEP 1: Sibling Chains (hierarchy-based)")
    print("=" * 60)

    conn = get_conn()
    cur = conn.cursor()

    # Get all parent groups with 2+ children that have dates
    cur.execute("""
        SELECT parent_event_id, array_agg(id ORDER BY date_start, id) as children,
               array_agg(title ORDER BY date_start, id) as titles
        FROM events
        WHERE parent_event_id IS NOT NULL AND date_start IS NOT NULL
        GROUP BY parent_event_id
        HAVING COUNT(*) >= 2
        ORDER BY COUNT(*) DESC
    """)
    groups = cur.fetchall()

    total_groups = len(groups)
    print(f"  Parent groups with 2+ dated children: {total_groups:,}")

    relationships = []
    for parent_id, child_ids, child_titles in groups:
        # Create "follows" chain: child[0] → child[1] → child[2] → ...
        for i in range(len(child_ids) - 1):
            relationships.append({
                'from_id': child_ids[i],
                'to_id': child_ids[i + 1],
                'type': 'follows',
                'strength': 4,
                'confidence': 0.9,
                'certainty': 'certain',
                'evidence_type': 'structural',
                'description': 'Sequential events under same parent (hierarchy-based)',
            })

    total_rels = len(relationships)
    print(f"  Generated {total_rels:,} 'follows' relationships")

    if not dry_run:
        # Batch insert
        inserted = 0
        for i in range(0, len(relationships), 1000):
            batch = relationships[i:i + 1000]
            for rel in batch:
                try:
                    cur.execute("""
                        INSERT INTO event_relationships
                            (from_event_id, to_event_id, relationship_type, strength, confidence, certainty, evidence_type, description)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        rel['from_id'], rel['to_id'], rel['type'],
                        rel['strength'], rel['confidence'], rel['certainty'],
                        rel['evidence_type'], rel['description'],
                    ))
                    inserted += 1
                except (psycopg2.errors.UniqueViolation, psycopg2.errors.ForeignKeyViolation):
                    conn.rollback()

            conn.commit()
            if (i // 1000 + 1) % 5 == 0:
                print(f"    Inserted {inserted:,}/{total_rels:,}...")

        conn.commit()
        print(f"  Inserted {inserted:,} relationships")
    else:
        print(f"  [DRY RUN] Would insert {total_rels:,} relationships")
        # Show samples
        if groups:
            cur.execute("SELECT title FROM events WHERE id = %s", (groups[0][0],))
            parent_title = cur.fetchone()[0]
            print(f"\n  Sample: {parent_title}")
            for i, (cid, ctitle) in enumerate(zip(groups[0][1][:5], groups[0][2][:5])):
                arrow = " → " if i > 0 else "   "
                print(f"    {arrow}{ctitle}")

    print(f"\n  --- Step 1 Results ---")
    print(f"    Parent groups: {total_groups:,}")
    print(f"    Relationships: {total_rels:,}")

    cur.close()
    conn.close()
    return {'groups': total_groups, 'relationships': total_rels}


# ═══════════════════════════════════════════
# Step 2: Person Thread Chains
# ═══════════════════════════════════════════

def step2_person_chains(dry_run=False):
    """같은 인물이 참여한 이벤트를 시간순으로 연결 (교차 계층 연결)."""
    print("\n" + "=" * 60)
    print("STEP 2: Person Thread Chains")
    print("=" * 60)

    conn = get_conn()
    cur = conn.cursor()

    # Get existing relationships to avoid duplicates
    cur.execute("SELECT from_event_id, to_event_id FROM event_relationships")
    existing = set()
    for row in cur.fetchall():
        existing.add((row[0], row[1]))
    print(f"  Existing relationships (from Step 1): {len(existing):,}")

    # Get persons with 2+ dated events, ordered by importance
    cur.execute("""
        SELECT ep.person_id, p.name, p.importance_score,
               array_agg(DISTINCT ep.event_id ORDER BY ep.event_id) as event_ids
        FROM event_persons ep
        JOIN persons p ON p.id = ep.person_id
        JOIN events e ON e.id = ep.event_id
        WHERE e.date_start IS NOT NULL
        GROUP BY ep.person_id, p.name, p.importance_score
        HAVING COUNT(DISTINCT ep.event_id) >= 2
        ORDER BY p.importance_score DESC NULLS LAST
    """)
    person_groups = cur.fetchall()
    print(f"  Persons with 2+ dated events: {len(person_groups):,}")

    # For each person, get their events in date order and create chains
    relationships = []
    persons_with_chains = 0

    for person_id, person_name, importance, event_ids in person_groups:
        # Get events in date order
        cur.execute("""
            SELECT id, date_start, title FROM events
            WHERE id = ANY(%s) AND date_start IS NOT NULL
            ORDER BY date_start, id
        """, (list(event_ids),))
        events = cur.fetchall()

        if len(events) < 2:
            continue

        person_rels = []
        for i in range(len(events) - 1):
            from_id = events[i][0]
            to_id = events[i + 1][0]

            # Skip if already exists (from Layer 1 or previous)
            if (from_id, to_id) in existing:
                continue

            person_rels.append({
                'from_id': from_id,
                'to_id': to_id,
                'type': 'person_thread',
                'strength': min(3, max(1, (importance or 3) - 1)),  # Higher importance = stronger link
                'confidence': 0.6,
                'certainty': 'probable',
                'evidence_type': 'inference',
                'description': f'Shared participant: {person_name}',
            })
            existing.add((from_id, to_id))

        if person_rels:
            relationships.extend(person_rels)
            persons_with_chains += 1

    total_rels = len(relationships)
    print(f"  Generated {total_rels:,} new 'person_thread' relationships")
    print(f"  From {persons_with_chains:,} persons")

    if not dry_run:
        inserted = 0
        for i in range(0, len(relationships), 1000):
            batch = relationships[i:i + 1000]
            for rel in batch:
                try:
                    cur.execute("""
                        INSERT INTO event_relationships
                            (from_event_id, to_event_id, relationship_type, strength, confidence, certainty, evidence_type, description)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        rel['from_id'], rel['to_id'], rel['type'],
                        rel['strength'], rel['confidence'], rel['certainty'],
                        rel['evidence_type'], rel['description'],
                    ))
                    inserted += 1
                except (psycopg2.errors.UniqueViolation, psycopg2.errors.ForeignKeyViolation):
                    conn.rollback()

            conn.commit()
            if (i // 1000 + 1) % 10 == 0:
                print(f"    Inserted {inserted:,}/{total_rels:,}...")

        conn.commit()
        print(f"  Inserted {inserted:,} relationships")
    else:
        print(f"  [DRY RUN] Would insert {total_rels:,} relationships")

    print(f"\n  --- Step 2 Results ---")
    print(f"    Persons with chains: {persons_with_chains:,}")
    print(f"    New relationships: {total_rels:,}")

    cur.close()
    conn.close()
    return {'persons': persons_with_chains, 'relationships': total_rels}


# ═══════════════════════════════════════════
# Step 3: Wikidata Causal Relationships
# ═══════════════════════════════════════════

def step3_wikidata_causal(dry_run=False):
    """Wikidata P155/P156/P1542/P1478으로 직접 인과관계 추가."""
    print("\n" + "=" * 60)
    print("STEP 3: Wikidata Causal Relationships")
    print("=" * 60)

    conn = get_conn()
    cur = conn.cursor()

    # Load all events with QIDs
    cur.execute("SELECT id, wikidata_id FROM events WHERE wikidata_id IS NOT NULL")
    events = cur.fetchall()
    qid_to_id = {row[1]: row[0] for row in events}
    all_qids = list(qid_to_id.keys())
    print(f"  Events with QID: {len(all_qids):,}")

    # Load existing relationships
    cur.execute("SELECT from_event_id, to_event_id FROM event_relationships")
    existing = set((row[0], row[1]) for row in cur.fetchall())
    print(f"  Existing relationships: {len(existing):,}")

    # Load or fetch cache
    cache = {}
    if CACHE_PATH.exists():
        with open(CACHE_PATH, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        print(f"  Loaded cache: {len(cache):,} entries")

    to_fetch = [q for q in all_qids if q not in cache]
    print(f"  Need to fetch: {len(to_fetch):,}")

    if to_fetch:
        total_batches = (len(to_fetch) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  Fetching {len(to_fetch)} QIDs in {total_batches} batches...")

        for i in range(0, len(to_fetch), BATCH_SIZE):
            batch = to_fetch[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1

            if batch_num % 50 == 0 or batch_num == 1 or batch_num == total_batches:
                print(f"    Batch {batch_num}/{total_batches}...")

            entities = fetch_wikidata_batch(batch, props='claims')

            for qid in batch:
                entity = entities.get(qid, {})
                cache[qid] = {
                    'P155': extract_qid_claims(entity, 'P155'),  # follows
                    'P156': extract_qid_claims(entity, 'P156'),  # followed by
                    'P1542': extract_qid_claims(entity, 'P1542'),  # has effect
                    'P1478': extract_qid_claims(entity, 'P1478'),  # has immediate cause
                }

            time.sleep(0.2)

            if batch_num % 100 == 0:
                CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
                with open(CACHE_PATH, 'w', encoding='utf-8') as f:
                    json.dump(cache, f, ensure_ascii=False)

        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False)
        print(f"  Cache saved ({len(cache):,} entries)")

    # Build relationships from cache
    # P155: this event follows X → X causes/precedes this
    # P156: this event is followed by Y → this causes/precedes Y
    # P1542: this event has effect Y → this causes Y
    # P1478: this event has immediate cause X → X causes this

    relationships = []
    prop_stats = defaultdict(int)

    for qid, claims in cache.items():
        if qid not in qid_to_id:
            continue
        event_id = qid_to_id[qid]

        # P155: follows (A follows B → B → A)
        for target_qid in claims.get('P155', []):
            if target_qid in qid_to_id:
                from_id = qid_to_id[target_qid]
                to_id = event_id
                if (from_id, to_id) not in existing:
                    relationships.append({
                        'from_id': from_id, 'to_id': to_id,
                        'type': 'follows', 'strength': 5, 'confidence': 0.95,
                        'certainty': 'certain', 'evidence_type': 'wikidata',
                        'description': f'Wikidata P155 (follows)',
                    })
                    existing.add((from_id, to_id))
                    prop_stats['P155'] += 1

        # P156: followed by (A is followed by B → A → B)
        for target_qid in claims.get('P156', []):
            if target_qid in qid_to_id:
                from_id = event_id
                to_id = qid_to_id[target_qid]
                if (from_id, to_id) not in existing:
                    relationships.append({
                        'from_id': from_id, 'to_id': to_id,
                        'type': 'follows', 'strength': 5, 'confidence': 0.95,
                        'certainty': 'certain', 'evidence_type': 'wikidata',
                        'description': f'Wikidata P156 (followed by)',
                    })
                    existing.add((from_id, to_id))
                    prop_stats['P156'] += 1

        # P1542: has effect (A has effect B → A causes B)
        for target_qid in claims.get('P1542', []):
            if target_qid in qid_to_id:
                from_id = event_id
                to_id = qid_to_id[target_qid]
                if (from_id, to_id) not in existing:
                    relationships.append({
                        'from_id': from_id, 'to_id': to_id,
                        'type': 'causes', 'strength': 5, 'confidence': 0.95,
                        'certainty': 'certain', 'evidence_type': 'wikidata',
                        'description': f'Wikidata P1542 (has effect)',
                    })
                    existing.add((from_id, to_id))
                    prop_stats['P1542'] += 1

        # P1478: has immediate cause (A has cause B → B causes A)
        for target_qid in claims.get('P1478', []):
            if target_qid in qid_to_id:
                from_id = qid_to_id[target_qid]
                to_id = event_id
                if (from_id, to_id) not in existing:
                    relationships.append({
                        'from_id': from_id, 'to_id': to_id,
                        'type': 'causes', 'strength': 5, 'confidence': 0.95,
                        'certainty': 'certain', 'evidence_type': 'wikidata',
                        'description': f'Wikidata P1478 (has immediate cause)',
                    })
                    existing.add((from_id, to_id))
                    prop_stats['P1478'] += 1

    total_rels = len(relationships)
    print(f"\n  Generated {total_rels:,} Wikidata-based relationships")
    for prop, count in sorted(prop_stats.items()):
        print(f"    {prop}: {count:,}")

    if not dry_run and relationships:
        inserted = 0
        for rel in relationships:
            try:
                cur.execute("""
                    INSERT INTO event_relationships
                        (from_event_id, to_event_id, relationship_type, strength, confidence, certainty, evidence_type, description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    rel['from_id'], rel['to_id'], rel['type'],
                    rel['strength'], rel['confidence'], rel['certainty'],
                    rel['evidence_type'], rel['description'],
                ))
                inserted += 1
            except (psycopg2.errors.UniqueViolation, psycopg2.errors.ForeignKeyViolation):
                conn.rollback()

        conn.commit()
        print(f"  Inserted {inserted:,} relationships")
    elif dry_run:
        print(f"  [DRY RUN] Would insert {total_rels:,} relationships")

    print(f"\n  --- Step 3 Results ---")
    print(f"    Wikidata relationships: {total_rels:,}")
    for prop, count in sorted(prop_stats.items()):
        print(f"      {prop}: {count:,}")

    cur.close()
    conn.close()
    return {'relationships': total_rels, 'by_prop': dict(prop_stats)}


# ═══════════════════════════════════════════
# Step 4: Report
# ═══════════════════════════════════════════

def step4_report():
    """최종 결과 리포트."""
    print("\n" + "=" * 60)
    print("STEP 4: Final Report")
    print("=" * 60)

    conn = get_conn()
    cur = conn.cursor()

    # Periods
    cur.execute("SELECT COUNT(*) FROM periods")
    periods = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM events WHERE period_id IS NOT NULL")
    events_with_period = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM events")
    total_events = cur.fetchone()[0]

    # Event relationships
    cur.execute("SELECT COUNT(*) FROM event_relationships")
    total_rels = cur.fetchone()[0]
    cur.execute("""
        SELECT relationship_type, COUNT(*)
        FROM event_relationships GROUP BY relationship_type ORDER BY COUNT(*) DESC
    """)
    rel_types = cur.fetchall()

    cur.execute("""
        SELECT evidence_type, COUNT(*)
        FROM event_relationships GROUP BY evidence_type ORDER BY COUNT(*) DESC
    """)
    evidence_types = cur.fetchall()

    # Connected events
    cur.execute("""
        SELECT COUNT(DISTINCT event_id) FROM (
            SELECT from_event_id as event_id FROM event_relationships
            UNION
            SELECT to_event_id FROM event_relationships
        ) sub
    """)
    connected_events = cur.fetchone()[0]

    # Top events by connections
    cur.execute("""
        SELECT e.title, cnt FROM (
            SELECT event_id, COUNT(*) as cnt FROM (
                SELECT from_event_id as event_id FROM event_relationships
                UNION ALL
                SELECT to_event_id FROM event_relationships
            ) sub
            GROUP BY event_id ORDER BY cnt DESC LIMIT 10
        ) top
        JOIN events e ON e.id = top.event_id
        ORDER BY cnt DESC
    """)
    top_events = cur.fetchall()

    print(f"""
  === Event Relationships & Periods Report ===

  Periods:
    Defined: {periods}
    Events with period_id: {events_with_period:,}/{total_events:,} ({events_with_period/max(total_events,1)*100:.1f}%)

  Event Relationships:
    Total: {total_rels:,}
    Connected events: {connected_events:,}/{total_events:,} ({connected_events/max(total_events,1)*100:.1f}%)

  By type:""")
    for rtype, count in rel_types:
        print(f"    {rtype}: {count:,}")

    print(f"\n  By evidence:")
    for etype, count in evidence_types:
        print(f"    {etype}: {count:,}")

    print(f"\n  Most connected events:")
    for title, cnt in top_events:
        print(f"    {title}: {cnt} connections")

    cur.close()
    conn.close()


# ═══════════════════════════════════════════
# Main
# ═══════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='Fill event relationships and periods')
    parser.add_argument('--dry-run', action='store_true', help='Report only, no DB modifications')
    parser.add_argument('--step', type=int, choices=[0, 1, 2, 3, 4], help='Run specific step only')
    args = parser.parse_args()

    start_time = datetime.now()
    mode = "DRY RUN" if args.dry_run else "LIVE"
    step_desc = f"Step {args.step}" if args.step is not None else "All Steps"

    print(f"╔{'═' * 58}╗")
    print(f"║  Event Relationships + Periods - {mode} - {step_desc:<15}    ║")
    print(f"║  Started: {start_time.strftime('%Y-%m-%d %H:%M:%S'):<46} ║")
    print(f"╚{'═' * 58}╝")

    if args.step is not None:
        if args.step == 0:
            step0_create_periods(dry_run=args.dry_run)
        elif args.step == 1:
            step1_sibling_chains(dry_run=args.dry_run)
        elif args.step == 2:
            step2_person_chains(dry_run=args.dry_run)
        elif args.step == 3:
            step3_wikidata_causal(dry_run=args.dry_run)
        elif args.step == 4:
            step4_report()
    else:
        step0_create_periods(dry_run=args.dry_run)
        step1_sibling_chains(dry_run=args.dry_run)
        step2_person_chains(dry_run=args.dry_run)
        step3_wikidata_causal(dry_run=args.dry_run)
        step4_report()

    elapsed = datetime.now() - start_time
    print(f"\n{'=' * 60}")
    print(f"  Completed in {elapsed.total_seconds():.1f}s")
    if args.dry_run:
        print(f"  [DRY RUN] No changes were made to the database.")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
