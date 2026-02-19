"""Test GPT-5-mini for event validation."""
import os
import time
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Test events (from Ollama results)
test_events = [
    ('New Silver Tax', 7, 0, 'REAL'),
    ('Bourbon Restoration of 1815', 7, 2, 'REAL'),
    ('Embroidery of a Coat', 7, 1, 'REAL'),
    ('Events Continued Until 1624', 7, 1, 'GARBAGE'),
    ('Royal Commission of 1868', 7, 1, 'REAL'),
    ('Battle of Hastings', 100, 20, 'REAL'),
    ('Publication', 5, 0, 'GARBAGE'),
    ('First', 3, 0, 'GARBAGE'),
]

prompt_template = '''You are validating historical event data. Determine if this is a REAL historical event or GARBAGE data.

Event: {title}
Connected persons: {persons}
Connected locations: {locations}

Respond in JSON: {{"is_real": true/false, "confidence": "high"/"medium"/"low", "reason": "brief reason"}}'''

print('Testing GPT-4o-mini...')
print('='*60)

total_time = 0
total_tokens = 0
results = []

for title, persons, locs, expected in test_events:
    prompt = prompt_template.format(title=title, persons=persons, locations=locs)

    start = time.time()
    response = client.chat.completions.create(
        model='gpt-5-mini',
        messages=[{'role': 'user', 'content': prompt}],
        response_format={'type': 'json_object'},
        max_tokens=100
    )
    elapsed = time.time() - start
    total_time += elapsed
    total_tokens += response.usage.total_tokens

    result = json.loads(response.choices[0].message.content)
    got = 'REAL' if result.get('is_real') else 'GARBAGE'
    match = 'O' if got == expected else 'X'

    print(f'{match} {title[:40]:<40} | Expected: {expected:<7} | Got: {got:<7} | {elapsed:.2f}s')
    results.append((expected, got))

print('='*60)
matches = sum(1 for e, g in results if e == g)
print(f'Accuracy: {matches}/{len(results)} ({matches/len(results)*100:.0f}%)')
print(f'Total time: {total_time:.2f}s ({total_time/len(results):.2f}s per event)')
print(f'Total tokens: {total_tokens} (~${total_tokens * 0.00015 / 1000:.4f})')
print(f'')
print(f'Estimated for 13,400 events:')
print(f'  Time: {13400 * total_time / len(results) / 60:.1f} minutes')
print(f'  Cost: ~${13400 * total_tokens / len(results) * 0.00015 / 1000:.2f}')
