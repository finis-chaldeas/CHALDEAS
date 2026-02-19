"""Generate and submit all batches with reasoning_effort: minimal."""
import httpx
import json
from pathlib import Path

API_KEY = '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'
DATA_DIR = Path('C:/Projects/Chaldeas/data/raw')
OUTPUT_DIR = Path('C:/Projects/Chaldeas/poc/data/integrated_ner_full')

SCHEMA = {
    'type': 'object',
    'properties': {
        'persons': {'type': 'array', 'items': {'type': 'object', 'properties': {'name': {'type': 'string'}, 'role': {'type': ['string', 'null']}, 'birth_year': {'type': ['integer', 'null']}, 'death_year': {'type': ['integer', 'null']}, 'era': {'type': ['string', 'null']}, 'confidence': {'type': 'number'}}, 'required': ['name', 'role', 'birth_year', 'death_year', 'era', 'confidence'], 'additionalProperties': False}},
        'locations': {'type': 'array', 'items': {'type': 'object', 'properties': {'name': {'type': 'string'}, 'location_type': {'type': ['string', 'null']}, 'modern_name': {'type': ['string', 'null']}, 'confidence': {'type': 'number'}}, 'required': ['name', 'location_type', 'modern_name', 'confidence'], 'additionalProperties': False}},
        'polities': {'type': 'array', 'items': {'type': 'object', 'properties': {'name': {'type': 'string'}, 'polity_type': {'type': ['string', 'null']}, 'start_year': {'type': ['integer', 'null']}, 'end_year': {'type': ['integer', 'null']}, 'confidence': {'type': 'number'}}, 'required': ['name', 'polity_type', 'start_year', 'end_year', 'confidence'], 'additionalProperties': False}},
        'periods': {'type': 'array', 'items': {'type': 'object', 'properties': {'name': {'type': 'string'}, 'start_year': {'type': ['integer', 'null']}, 'end_year': {'type': ['integer', 'null']}, 'region': {'type': ['string', 'null']}, 'confidence': {'type': 'number'}}, 'required': ['name', 'start_year', 'end_year', 'region', 'confidence'], 'additionalProperties': False}},
        'events': {'type': 'array', 'items': {'type': 'object', 'properties': {'name': {'type': 'string'}, 'year': {'type': ['integer', 'null']}, 'persons_involved': {'type': 'array', 'items': {'type': 'string'}}, 'locations_involved': {'type': 'array', 'items': {'type': 'string'}}, 'confidence': {'type': 'number'}}, 'required': ['name', 'year', 'persons_involved', 'locations_involved', 'confidence'], 'additionalProperties': False}}
    },
    'required': ['persons', 'locations', 'polities', 'periods', 'events'],
    'additionalProperties': False
}

PROMPT = '''Extract historical entities from this document.
RULES:
- Persons: Clear names only. Skip titles alone, abbreviations, partial names.
- Locations: Cities, regions, countries, landmarks.
- Polities: Empires, kingdoms, dynasties.
- Periods: Named eras (Renaissance, Victorian Era).
- Events: Battles, treaties, revolutions.
- Use negative years for BCE (-490 = 490 BCE).
- Confidence: 1.0=explicit, 0.5=inferred, 0.3=uncertain.

TEXT:
{text}'''

def load_doc(path):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        if path.suffix == '.txt':
            return f.read()
        data = json.load(f)
        if isinstance(data, list):
            return ' '.join(item[1] if len(item) > 1 else '' for item in data)
        return str(data)

def collect_docs():
    """Collect all document paths."""
    paths = []
    for subdir in sorted(DATA_DIR.iterdir()):
        if subdir.is_dir():
            for p in subdir.rglob('*_text.json'):
                paths.append(p)
            for p in subdir.rglob('*.txt'):
                paths.append(p)
    return paths

def create_request(doc_id, text):
    """Create a batch request with minimal reasoning."""
    return {
        'custom_id': doc_id,
        'method': 'POST',
        'url': '/v1/chat/completions',
        'body': {
            'model': 'gpt-5-nano',
            'reasoning_effort': 'minimal',  # KEY!
            'messages': [
                {'role': 'system', 'content': 'Extract historical entities. Return valid JSON.'},
                {'role': 'user', 'content': PROMPT.format(text=text[:6000])}
            ],
            'response_format': {
                'type': 'json_schema',
                'json_schema': {'name': 'extraction', 'strict': True, 'schema': SCHEMA}
            }
        }
    }

def main():
    headers = {'Authorization': f'Bearer {API_KEY}'}

    # 1. Collect documents
    print('Collecting documents...')
    doc_paths = collect_docs()
    print(f'Found {len(doc_paths)} documents')

    # 2. Create batch files
    print('\nCreating batch files with reasoning_effort: minimal...')
    batch_size = 10000
    batches = []
    current = []
    skip = 0

    for i, path in enumerate(doc_paths):
        try:
            text = load_doc(path)
            if len(text) < 50:
                skip += 1
                continue
            current.append(create_request(path.stem, text))
            if len(current) >= batch_size:
                batch_file = OUTPUT_DIR / f'minimal_batch_{len(batches):02d}.jsonl'
                with open(batch_file, 'w', encoding='utf-8') as f:
                    for req in current:
                        f.write(json.dumps(req, ensure_ascii=False) + '\n')
                print(f'  Created {batch_file.name} ({len(current):,} requests)')
                batches.append(batch_file)
                current = []
        except Exception as e:
            skip += 1

        if (i + 1) % 10000 == 0:
            print(f'  Processed {i+1:,}/{len(doc_paths):,}...')

    # Last batch
    if current:
        batch_file = OUTPUT_DIR / f'minimal_batch_{len(batches):02d}.jsonl'
        with open(batch_file, 'w', encoding='utf-8') as f:
            for req in current:
                f.write(json.dumps(req, ensure_ascii=False) + '\n')
        print(f'  Created {batch_file.name} ({len(current):,} requests)')
        batches.append(batch_file)

    print(f'\nTotal: {len(batches)} batch files, {skip:,} skipped')

    # 3. Upload and submit
    print('\nUploading and submitting batches...')
    status = {'batches': {}, 'settings': {'reasoning_effort': 'minimal'}}

    for batch_file in batches:
        print(f'\n  {batch_file.name}:')

        # Upload
        print('    Uploading...', end=' ')
        with open(batch_file, 'rb') as f:
            files = {'file': (batch_file.name, f, 'application/jsonl')}
            data = {'purpose': 'batch'}
            resp = httpx.post('https://api.openai.com/v1/files', headers=headers,
                            files=files, data=data, timeout=300.0)

        if resp.status_code != 200:
            print(f'FAILED: {resp.text[:100]}')
            continue

        file_id = resp.json()['id']
        print(f'OK ({file_id})')

        # Submit batch
        print('    Submitting...', end=' ')
        batch_data = {
            'input_file_id': file_id,
            'endpoint': '/v1/chat/completions',
            'completion_window': '24h'
        }
        resp = httpx.post('https://api.openai.com/v1/batches', headers=headers,
                         json=batch_data, timeout=30.0)

        if resp.status_code != 200:
            print(f'FAILED: {resp.text[:100]}')
            continue

        batch_id = resp.json()['id']
        print(f'OK ({batch_id})')

        status['batches'][batch_file.name] = {
            'file_id': file_id,
            'batch_id': batch_id,
            'status': 'submitted'
        }

    # Save status
    status_file = OUTPUT_DIR / 'minimal_submission_status.json'
    with open(status_file, 'w') as f:
        json.dump(status, f, indent=2)

    print(f'\n=== DONE ===')
    print(f'Submitted {len(status["batches"])} batches')
    print(f'Status saved to: {status_file}')

if __name__ == '__main__':
    main()
