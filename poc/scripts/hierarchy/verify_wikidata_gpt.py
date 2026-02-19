"""
GPT-5-mini verification of Wikidata event matches.
"""
import sys
import os
import json
import time

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))

from openai import OpenAI
from sqlalchemy import text
from app.db.session import SessionLocal

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

BATCH_SIZE = 20


def verify_batch_gpt(candidates: list) -> list:
    """Verify a batch of event-wikidata matches with GPT-5-mini."""
    items_text = "\n".join([
        f'{i+1}. "{c["title"]}" ({c["year"]}) vs Wikidata "{c["wiki_name"]}" ({c["wiki_year"]})'
        for i, c in enumerate(candidates)
    ])

    prompt = f'''Are these event pairs referring to the SAME historical event?
Consider spelling variations, naming conventions, and whether they describe the same occurrence.

{items_text}

Return JSON: {{"results": [{{"index": 1, "same": true/false, "confidence": "high"/"medium"/"low"}}]}}
Only mark "same": true if you're confident they refer to the same event.'''

    try:
        response = client.chat.completions.create(
            model='gpt-5-mini',
            messages=[{'role': 'user', 'content': prompt}],
            response_format={'type': 'json_object'},
            max_completion_tokens=2000
        )
        data = json.loads(response.choices[0].message.content)
        return data.get('results', [])
    except Exception as e:
        print(f"GPT Error: {e}", flush=True)
        return []


def main():
    # Load candidates
    with open('poc/data/wikidata_llm_candidates.json', 'r', encoding='utf-8') as f:
        candidates = json.load(f)

    print(f"=== GPT-5-mini Wikidata Verification ===")
    print(f"Total candidates: {len(candidates)}")
    print()

    verified_matches = []
    rejected = []

    for i in range(0, len(candidates), BATCH_SIZE):
        batch = candidates[i:i + BATCH_SIZE]
        print(f"[{i+1}-{i+len(batch)}/{len(candidates)}] ", end="", flush=True)

        start = time.time()
        results = verify_batch_gpt(batch)
        elapsed = time.time() - start

        batch_yes = 0
        batch_no = 0

        for j, cand in enumerate(batch):
            result = None
            # Match by index
            for r in results:
                if r.get('index') == j + 1:
                    result = r
                    break
            # Fallback to position
            if not result and j < len(results):
                result = results[j]

            if result and result.get('same') and result.get('confidence') in ['high', 'medium']:
                verified_matches.append(cand)
                batch_yes += 1
            else:
                rejected.append(cand)
                batch_no += 1

        print(f"YES:{batch_yes} NO:{batch_no} ({elapsed:.1f}s)", flush=True)
        time.sleep(0.3)

    print()
    print(f"=== Results ===")
    print(f"Verified matches: {len(verified_matches)}")
    print(f"Rejected: {len(rejected)}")

    # Apply verified matches
    if verified_matches:
        print()
        print("Applying verified matches to database...")
        db = SessionLocal()
        for m in verified_matches:
            db.execute(text('UPDATE events SET wikidata_id = :qid WHERE id = :id'),
                       {'qid': m['qid'], 'id': m['event_id']})
        db.commit()
        db.close()
        print(f"Applied {len(verified_matches)} Wikidata IDs")

    # Save results
    with open('poc/data/wikidata_verified.json', 'w', encoding='utf-8') as f:
        json.dump(verified_matches, f, ensure_ascii=False, indent=2)
    with open('poc/data/wikidata_rejected.json', 'w', encoding='utf-8') as f:
        json.dump(rejected, f, ensure_ascii=False, indent=2)

    print()
    print("Done!")


if __name__ == "__main__":
    main()
