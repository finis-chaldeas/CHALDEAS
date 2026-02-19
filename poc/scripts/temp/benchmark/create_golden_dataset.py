"""
Create golden dataset for LLM benchmarking.

Creates 100 samples with known correct answers for:
1. Entity extraction (persons, locations, events from text)
2. Nature classification (war, battle, treaty, etc.)
3. Date parsing (various formats -> structured dates)
"""
import os
import sys
import json
import random
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()


def get_engine():
    db_url = os.getenv('DATABASE_URL', 'postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas')
    return create_engine(db_url)


def create_entity_extraction_samples(engine, count=34):
    """Create samples for entity extraction testing."""
    print(f"Creating {count} entity extraction samples...")

    samples = []

    with engine.connect() as conn:
        # Get events with descriptions and linked persons
        result = conn.execute(text("""
            SELECT
                e.id, e.title, e.description, e.date_start,
                ARRAY_AGG(DISTINCT p.name) FILTER (WHERE p.name IS NOT NULL) as person_names,
                ARRAY_AGG(DISTINCT l.name) FILTER (WHERE l.name IS NOT NULL) as location_names
            FROM events_v2 e
            LEFT JOIN person_event_roles per ON per.event_id = e.id
            LEFT JOIN persons p ON p.id = per.person_id
            LEFT JOIN locations l ON l.id = e.origin_location_id OR l.id = e.destination_location_id
            WHERE e.description IS NOT NULL
              AND LENGTH(e.description) > 100
            GROUP BY e.id, e.title, e.description, e.date_start
            HAVING COUNT(DISTINCT p.id) >= 1
            ORDER BY RANDOM()
            LIMIT :count
        """), {'count': count})

        for row in result:
            # Take first 500 chars of description as input text
            input_text = row[2][:500] if len(row[2]) > 500 else row[2]

            sample = {
                'id': f'entity_{row[0]}',
                'task': 'entity_extraction',
                'input': {
                    'text': input_text,
                    'context': f"This text is about the event: {row[1]} ({row[3]})"
                },
                'expected_output': {
                    'persons': row[4] if row[4] else [],
                    'locations': row[5] if row[5] else [],
                    'event_title': row[1]
                },
                'metadata': {
                    'event_id': row[0],
                    'source': 'events_v2'
                }
            }
            samples.append(sample)

    print(f"  Created {len(samples)} entity extraction samples")
    return samples


def create_nature_classification_samples(engine, count=33):
    """Create samples for event nature classification testing."""
    print(f"Creating {count} nature classification samples...")

    # Define nature based on aggregate_type and title patterns
    nature_patterns = {
        'war': ['War', 'Campaign', 'Conflict', 'Crusade'],
        'battle': ['Battle of', 'Siege of', 'Attack on'],
        'treaty': ['Treaty of', 'Peace of', 'Agreement', 'Accord'],
        'revolution': ['Revolution', 'Uprising', 'Revolt', 'Rebellion'],
        'coronation': ['Coronation', 'Accession', 'Enthronement'],
        'death': ['Death of', 'Assassination of', 'Execution of'],
        'birth': ['Birth of'],
        'discovery': ['Discovery of', 'Expedition'],
        'founding': ['Founding of', 'Establishment of', 'Foundation of'],
    }

    samples = []

    with engine.connect() as conn:
        for nature, patterns in nature_patterns.items():
            # Get events matching patterns
            pattern_clause = ' OR '.join([f"title ILIKE '%{p}%'" for p in patterns])
            result = conn.execute(text(f"""
                SELECT id, title, description, date_start
                FROM events_v2
                WHERE ({pattern_clause})
                ORDER BY RANDOM()
                LIMIT :limit
            """), {'limit': max(1, count // len(nature_patterns))})

            for row in result:
                sample = {
                    'id': f'nature_{row[0]}',
                    'task': 'nature_classification',
                    'input': {
                        'title': row[1],
                        'description': row[2][:300] if row[2] else None,
                        'date': row[3]
                    },
                    'expected_output': {
                        'nature': nature,
                        'confidence': 'high'
                    },
                    'metadata': {
                        'event_id': row[0],
                        'matched_patterns': [p for p in patterns if p.lower() in row[1].lower()]
                    }
                }
                samples.append(sample)

    print(f"  Created {len(samples)} nature classification samples")
    return samples[:count]


def create_date_parsing_samples(count=33):
    """Create samples for date parsing testing."""
    print(f"Creating {count} date parsing samples...")

    # Various date formats and their structured representations
    date_samples = [
        # Standard formats
        ("January 15, 1066", {"year": 1066, "month": 1, "day": 15, "precision": "exact"}),
        ("15 January 1066", {"year": 1066, "month": 1, "day": 15, "precision": "exact"}),
        ("1066-01-15", {"year": 1066, "month": 1, "day": 15, "precision": "exact"}),
        ("January 1066", {"year": 1066, "month": 1, "day": None, "precision": "month"}),
        ("1066", {"year": 1066, "month": None, "day": None, "precision": "year"}),

        # BCE dates
        ("490 BCE", {"year": -490, "month": None, "day": None, "precision": "year"}),
        ("490 BC", {"year": -490, "month": None, "day": None, "precision": "year"}),
        ("c. 490 BCE", {"year": -490, "month": None, "day": None, "precision": "approximate"}),
        ("circa 500 BC", {"year": -500, "month": None, "day": None, "precision": "approximate"}),

        # Ranges
        ("1914-1918", {"year_start": 1914, "year_end": 1918, "precision": "range"}),
        ("1939 to 1945", {"year_start": 1939, "year_end": 1945, "precision": "range"}),
        ("between 1200 and 1300", {"year_start": 1200, "year_end": 1300, "precision": "range"}),

        # Centuries
        ("5th century BCE", {"year": -450, "century": -5, "precision": "century"}),
        ("12th century", {"year": 1150, "century": 12, "precision": "century"}),
        ("early 19th century", {"year": 1810, "century": 19, "precision": "century", "qualifier": "early"}),
        ("late 18th century", {"year": 1780, "century": 18, "precision": "century", "qualifier": "late"}),
        ("mid-20th century", {"year": 1950, "century": 20, "precision": "century", "qualifier": "mid"}),

        # Decades
        ("the 1920s", {"year": 1925, "decade": 1920, "precision": "decade"}),
        ("1960s", {"year": 1965, "decade": 1960, "precision": "decade"}),

        # Relative dates
        ("spring 1789", {"year": 1789, "season": "spring", "precision": "season"}),
        ("summer of 1969", {"year": 1969, "season": "summer", "precision": "season"}),
        ("winter 1941-1942", {"year_start": 1941, "year_end": 1942, "season": "winter", "precision": "season"}),

        # Complex
        ("August 6, 1945 at 8:15 AM", {"year": 1945, "month": 8, "day": 6, "precision": "exact"}),
        ("September 11, 2001", {"year": 2001, "month": 9, "day": 11, "precision": "exact"}),
        ("Christmas Day, 800", {"year": 800, "month": 12, "day": 25, "precision": "exact"}),

        # Approximate
        ("around 1500", {"year": 1500, "precision": "approximate"}),
        ("approximately 3000 BCE", {"year": -3000, "precision": "approximate"}),
        ("possibly 1453", {"year": 1453, "precision": "uncertain"}),

        # Historical eras
        ("during the Renaissance", {"era": "Renaissance", "year_start": 1400, "year_end": 1600, "precision": "era"}),
        ("in antiquity", {"era": "Antiquity", "year_start": -3000, "year_end": 500, "precision": "era"}),
        ("medieval period", {"era": "Medieval", "year_start": 500, "year_end": 1500, "precision": "era"}),

        # More edge cases
        ("AD 476", {"year": 476, "precision": "year"}),
        ("44 BC, March 15", {"year": -44, "month": 3, "day": 15, "precision": "exact"}),
    ]

    samples = []
    for i, (date_str, expected) in enumerate(date_samples):
        sample = {
            'id': f'date_{i+1}',
            'task': 'date_parsing',
            'input': {
                'date_string': date_str
            },
            'expected_output': expected,
            'metadata': {
                'complexity': 'high' if 'era' in expected or 'century' in expected else 'medium' if 'approximate' in str(expected) else 'low'
            }
        }
        samples.append(sample)

    print(f"  Created {len(samples)} date parsing samples")
    return samples[:count]


def main():
    engine = get_engine()

    print("Creating golden dataset for LLM benchmarking...")
    print("=" * 50)

    # Create samples for each task
    entity_samples = create_entity_extraction_samples(engine, 34)
    nature_samples = create_nature_classification_samples(engine, 33)
    date_samples = create_date_parsing_samples(33)

    # Combine all samples
    all_samples = entity_samples + nature_samples + date_samples
    random.shuffle(all_samples)

    # Create dataset structure
    dataset = {
        'version': '1.0',
        'created_at': datetime.now().isoformat(),
        'description': 'Golden dataset for CHALDEAS LLM benchmarking',
        'tasks': {
            'entity_extraction': len(entity_samples),
            'nature_classification': len(nature_samples),
            'date_parsing': len(date_samples)
        },
        'total_samples': len(all_samples),
        'samples': all_samples
    }

    # Save to file
    output_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'benchmark', 'golden_dataset.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print("=" * 50)
    print(f"Dataset saved to: {output_path}")
    print(f"Total samples: {len(all_samples)}")
    print(f"  - Entity extraction: {len(entity_samples)}")
    print(f"  - Nature classification: {len(nature_samples)}")
    print(f"  - Date parsing: {len(date_samples)}")


if __name__ == '__main__':
    main()
