"""
Gap 3: 시대 내러티브 생성

각 50년 기간 × 지역에 대해:
1. DB에서 해당 기간의 top 이벤트/인물 쿼리
2. Ollama (llama3.1:8b)로 내러티브 생성
3. period_narratives 테이블에 삽입

Usage:
    cd backend
    python ../poc/scripts/fill_period_narratives.py
    python ../poc/scripts/fill_period_narratives.py --limit 5  # 테스트
"""

import sys
import os
import json
import time
import argparse
import requests
import psycopg2
from collections import defaultdict

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_URL = 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas'
OLLAMA_URL = 'http://localhost:11434/api/generate'
OLLAMA_MODEL = 'llama3.1:8b-instruct-q4_0'

# 지역별 경도/위도 범위
REGIONS = {
    'europe': {'lat_min': 35, 'lat_max': 72, 'lng_min': -25, 'lng_max': 45, 'label': 'Europe'},
    'near_east': {'lat_min': 20, 'lat_max': 45, 'lng_min': 25, 'lng_max': 65, 'label': 'Near East'},
    'east_asia': {'lat_min': 18, 'lat_max': 55, 'lng_min': 100, 'lng_max': 150, 'label': 'East Asia'},
    'south_asia': {'lat_min': 5, 'lat_max': 40, 'lng_min': 60, 'lng_max': 100, 'label': 'South Asia'},
    'africa': {'lat_min': -35, 'lat_max': 20, 'lng_min': -20, 'lng_max': 55, 'label': 'Africa'},
    'americas': {'lat_min': -55, 'lat_max': 70, 'lng_min': -170, 'lng_max': -30, 'label': 'Americas'},
}

# 50년 기간 목록 (BCE 3000 ~ CE 2024)
def generate_periods():
    periods = []
    for start in range(-3000, 2001, 50):
        end = start + 49
        periods.append((start, end))
    return periods


def get_period_data(cur, period_start, period_end, region=None):
    """해당 기간+지역의 top 이벤트/인물 가져오기."""
    # Events
    if region:
        r = REGIONS[region]
        cur.execute("""
            SELECT e.title, e.date_start, e.importance
            FROM events e
            JOIN locations l ON e.primary_location_id = l.id
            WHERE e.date_start >= %s AND e.date_start <= %s
              AND l.latitude BETWEEN %s AND %s
              AND l.longitude BETWEEN %s AND %s
            ORDER BY e.importance DESC NULLS LAST, e.date_start
            LIMIT 10
        """, (period_start, period_end, r['lat_min'], r['lat_max'], r['lng_min'], r['lng_max']))
    else:
        cur.execute("""
            SELECT title, date_start, importance
            FROM events
            WHERE date_start >= %s AND date_start <= %s
            ORDER BY importance DESC NULLS LAST, date_start
            LIMIT 10
        """, (period_start, period_end))

    events = [{'title': r[0], 'year': r[1], 'importance': r[2]} for r in cur.fetchall()]

    # Persons
    if region:
        r = REGIONS[region]
        cur.execute("""
            SELECT p.name, p.role, p.birth_year, p.death_year, p.importance_score
            FROM persons p
            JOIN locations l ON p.birthplace_id = l.id
            WHERE ((p.birth_year >= %s AND p.birth_year <= %s)
                OR (p.death_year >= %s AND p.death_year <= %s))
              AND l.latitude BETWEEN %s AND %s
              AND l.longitude BETWEEN %s AND %s
            ORDER BY p.importance_score DESC NULLS LAST
            LIMIT 10
        """, (period_start, period_end, period_start, period_end,
              r['lat_min'], r['lat_max'], r['lng_min'], r['lng_max']))
    else:
        cur.execute("""
            SELECT name, role, birth_year, death_year, importance_score
            FROM persons
            WHERE (birth_year >= %s AND birth_year <= %s)
               OR (death_year >= %s AND death_year <= %s)
            ORDER BY importance_score DESC NULLS LAST
            LIMIT 10
        """, (period_start, period_end, period_start, period_end))

    persons = [{'name': r[0], 'role': r[1], 'birth': r[2], 'death': r[3]} for r in cur.fetchall()]

    return events, persons


def generate_narrative(period_start, period_end, region_label, events, persons):
    """Ollama로 내러티브 생성."""
    era_suffix = "BCE" if period_start < 0 else "CE"
    start_display = f"{abs(period_start)} {era_suffix}"
    end_display = f"{abs(period_end)} {era_suffix}"

    events_text = "\n".join([
        f"  - {e['title']} ({abs(e['year'])} {'BCE' if e['year'] < 0 else 'CE'})"
        for e in events[:8]
    ]) or "  (no major events recorded)"

    persons_text = "\n".join([
        f"  - {p['name']} ({p['role'] or 'unknown role'})"
        for p in persons[:8]
    ]) or "  (no major figures recorded)"

    region_context = f" in {region_label}" if region_label else " globally"

    prompt = f"""You are a historian writing concise period summaries for an interactive globe application.

Period: {start_display} to {end_display}{region_context}

Key events:
{events_text}

Key figures:
{persons_text}

Write a JSON object with these fields:
1. "headline": A dramatic one-sentence headline (max 100 chars)
2. "narrative": A 150-200 word narrative in storytelling tone, explaining what defined this period
3. "keywords": Array of 5-7 theme keywords
4. "defining_moment": One sentence describing the single most important moment

Rules:
- Be factual and historically accurate
- Use vivid but concise language
- If no events/persons are listed, write about the general state of the region in this period
- Output ONLY valid JSON, no markdown

JSON:"""

    try:
        resp = requests.post(OLLAMA_URL, json={
            'model': OLLAMA_MODEL,
            'prompt': prompt,
            'stream': False,
            'options': {'temperature': 0.7, 'num_predict': 600}
        }, timeout=120)
        resp.raise_for_status()
        text = resp.json().get('response', '').strip()

        # Clean up JSON
        if text.startswith('```'):
            text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()

        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        try:
            start_idx = text.index('{')
            end_idx = text.rindex('}') + 1
            return json.loads(text[start_idx:end_idx])
        except:
            return None
    except Exception as e:
        print(f"    Ollama error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=0, help='Max periods to process (0=all)')
    args = parser.parse_args()

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # 기존 내러티브 확인
    cur.execute("SELECT period_start, region FROM period_narratives")
    existing = set((r[0], r[1]) for r in cur.fetchall())
    print(f"Existing narratives: {len(existing)}")

    periods = generate_periods()
    total_generated = 0
    total_skipped = 0
    total_empty = 0

    # 글로벌 + 6 지역
    region_keys = [None] + list(REGIONS.keys())

    for period_start, period_end in periods:
        for region_key in region_keys:
            region_db_value = region_key  # None for global
            existing_key = (period_start, region_db_value)

            if existing_key in existing:
                total_skipped += 1
                continue

            region_label = REGIONS[region_key]['label'] if region_key else None
            events, persons = get_period_data(cur, period_start, period_end, region_key)

            # 데이터가 없으면 스킵
            if not events and not persons:
                total_empty += 1
                continue

            if args.limit and total_generated >= args.limit:
                break

            display_region = region_label or "Global"
            era = "BCE" if period_start < 0 else "CE"
            print(f"  {abs(period_start)}-{abs(period_end)} {era} | {display_region} "
                  f"({len(events)} events, {len(persons)} persons)...", end=" ")

            result = generate_narrative(period_start, period_end, region_label, events, persons)

            if not result:
                print("FAILED")
                continue

            # DB 삽입
            era_id = 'ancient' if period_start < -800 else \
                     'classical' if period_start < -200 else \
                     'late_classical' if period_start < 500 else \
                     'medieval' if period_start < 1500 else \
                     'early_modern' if period_start < 1800 else 'modern'

            cur.execute("""
                INSERT INTO period_narratives
                    (period_start, period_end, era_id, region, headline, narrative,
                     keywords, defining_moment, model_used, event_count, person_count,
                     curated_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'auto')
                ON CONFLICT DO NOTHING
            """, (
                period_start, period_end, era_id, region_db_value,
                result.get('headline', '')[:200],
                result.get('narrative', ''),
                result.get('keywords', []),
                result.get('defining_moment', '')[:500],
                OLLAMA_MODEL,
                len(events),
                len(persons),
            ))
            conn.commit()

            total_generated += 1
            print(f"OK ({result.get('headline', '')[:50]}...)")

        if args.limit and total_generated >= args.limit:
            break

    cur.close()
    conn.close()

    print(f"\n{'='*50}")
    print(f"SUMMARY")
    print(f"  Generated: {total_generated}")
    print(f"  Skipped (existing): {total_skipped}")
    print(f"  Skipped (no data): {total_empty}")


if __name__ == '__main__':
    main()
