"""Test batch without max_completion_tokens limit."""
import httpx
import json
import time
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

def main():
    headers = {'Authorization': f'Bearer {API_KEY}'}

    # 100개 문서 수집
    docs = []
    for subdir in sorted(DATA_DIR.iterdir()):
        if subdir.is_dir():
            for p in list(subdir.rglob('*_text.json'))[:20] + list(subdir.rglob('*.txt'))[:20]:
                try:
                    text = load_doc(p)
                    if len(text) > 100:
                        docs.append((p.stem, text[:6000]))
                        if len(docs) >= 100:
                            break
                except:
                    pass
            if len(docs) >= 100:
                break

    print(f'Collected {len(docs)} docs')

    # 배치 요청 생성 (max_completion_tokens 없음!)
    requests = []
    for doc_id, text in docs:
        req = {
            'custom_id': doc_id,
            'method': 'POST',
            'url': '/v1/chat/completions',
            'body': {
                'model': 'gpt-5-nano',
                'messages': [
                    {'role': 'system', 'content': 'Extract historical entities. Return valid JSON.'},
                    {'role': 'user', 'content': PROMPT.format(text=text)}
                ],
                'response_format': {
                    'type': 'json_schema',
                    'json_schema': {'name': 'extraction', 'strict': True, 'schema': SCHEMA}
                }
                # NO max_completion_tokens - unlimited!
            }
        }
        requests.append(json.dumps(req, ensure_ascii=False))

    # 파일 저장
    test_file = OUTPUT_DIR / 'test_unlimited.jsonl'
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(requests))

    print(f'Created {test_file.name} with {len(requests)} requests')

    # 업로드
    print('Uploading...')
    with open(test_file, 'rb') as f:
        files = {'file': (test_file.name, f, 'application/jsonl')}
        data = {'purpose': 'batch'}
        resp = httpx.post('https://api.openai.com/v1/files', headers=headers, files=files, data=data, timeout=60.0)

    if resp.status_code != 200:
        print(f'Upload failed: {resp.text}')
        return

    file_id = resp.json()['id']
    print(f'File ID: {file_id}')

    # 배치 제출
    batch_data = {
        'input_file_id': file_id,
        'endpoint': '/v1/chat/completions',
        'completion_window': '24h'
    }
    resp = httpx.post('https://api.openai.com/v1/batches', headers=headers, json=batch_data, timeout=30.0)

    if resp.status_code != 200:
        print(f'Batch submit failed: {resp.text}')
        return

    batch_id = resp.json()['id']
    print(f'Batch ID: {batch_id}')

    # 상태 확인 (5분)
    print('Waiting for completion...')
    for i in range(30):
        time.sleep(10)
        resp = httpx.get(f'https://api.openai.com/v1/batches/{batch_id}', headers=headers)
        data = resp.json()
        counts = data.get('request_counts', {})
        print(f'  [{(i+1)*10}s] {data["status"]}: {counts.get("completed", 0)}/{counts.get("total", 0)} done, {counts.get("failed", 0)} failed')
        if data['status'] in ['completed', 'failed']:
            break

    print(f'\nFinal status: {data["status"]}')
    print(f'Batch ID: {batch_id}')

    # 완료되면 결과 분석
    if data['status'] == 'completed' and data.get('output_file_id'):
        print('\nDownloading results...')
        file_id = data['output_file_id']
        resp = httpx.get(f'https://api.openai.com/v1/files/{file_id}/content', headers=headers, timeout=120.0)

        lines = resp.text.strip().split('\n')
        success = 0
        truncated = 0
        total_persons = 0
        total_locations = 0

        for line in lines:
            result = json.loads(line)
            body = result.get('response', {}).get('body', {})
            choice = body.get('choices', [{}])[0]
            content = choice.get('message', {}).get('content', '')
            finish_reason = choice.get('finish_reason', '')
            usage = body.get('usage', {})

            if finish_reason == 'length':
                truncated += 1
            elif content:
                try:
                    ext = json.loads(content)
                    total_persons += len(ext.get('persons', []))
                    total_locations += len(ext.get('locations', []))
                    success += 1
                except:
                    pass

        print(f'\n=== RESULTS ===')
        print(f'Success: {success}/{len(lines)}')
        print(f'Truncated: {truncated}/{len(lines)}')
        print(f'Avg persons: {total_persons/max(success,1):.1f}')
        print(f'Avg locations: {total_locations/max(success,1):.1f}')

        # 첫 성공 결과 샘플
        for line in lines[:5]:
            result = json.loads(line)
            body = result.get('response', {}).get('body', {})
            content = body.get('choices', [{}])[0].get('message', {}).get('content', '')
            usage = body.get('usage', {})
            if content:
                try:
                    ext = json.loads(content)
                    print(f'\nSample: {result["custom_id"]}')
                    print(f'  Tokens: prompt={usage.get("prompt_tokens")}, completion={usage.get("completion_tokens")}, reasoning={usage.get("completion_tokens_details", {}).get("reasoning_tokens")}')
                    print(f'  Persons: {len(ext.get("persons", []))}')
                    if ext.get('persons'):
                        print(f'  First: {ext["persons"][0]["name"]}')
                    break
                except:
                    pass

if __name__ == '__main__':
    main()
