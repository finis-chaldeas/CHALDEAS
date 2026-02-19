"""
LLM-based Wikipedia title matching for pending events.
"""
import sys
import os
import json
import re

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))

import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

from libzim.reader import Archive
from openai import OpenAI
from sqlalchemy import text
from app.db.session import SessionLocal


def main():
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    zim = Archive('data/kiwix/wikipedia_en_nopic.zim')
    db = SessionLocal()

    # Get pending events
    events = db.execute(text('''
        SELECT id, title, date_start FROM events
        WHERE parent_status = 'pending' AND wikidata_id IS NULL
        ORDER BY RANDOM()
        LIMIT 500
    ''')).fetchall()

    print(f"=== LLM Wikipedia Mapping ({len(events)} events) ===")

    batch_size = 25
    all_mappings = []

    for i in range(0, len(events), batch_size):
        batch = events[i:i+batch_size]

        lines = []
        for j, e in enumerate(batch):
            year = e[2] if e[2] else "unknown"
            lines.append(f'{j+1}. "{e[1]}" ({year})')
        event_list = "\n".join(lines)

        prompt = f'''For each historical event below, suggest the Wikipedia article title that best matches it.
Return JSON: {{"results": [{{"index": 1, "wikipedia_title": "Article Title"}}]}}
Only include entries where you're confident. Use null for wikipedia_title if unsure.

{event_list}'''

        try:
            response = client.chat.completions.create(
                model='gpt-5-mini',
                messages=[{'role': 'user', 'content': prompt}],
                response_format={'type': 'json_object'},
                max_completion_tokens=3000
            )
            data = json.loads(response.choices[0].message.content)
            results = data.get('results', [])

            for r in results:
                idx = r.get('index', 0) - 1
                wiki = r.get('wikipedia_title')
                if wiki and wiki not in ('null', None) and 0 <= idx < len(batch):
                    all_mappings.append({
                        'id': batch[idx][0],
                        'title': batch[idx][1],
                        'wiki_title': wiki
                    })

            print(f"  Batch {i//batch_size + 1}/{(len(events)+batch_size-1)//batch_size}: {len(results)} suggestions")
        except Exception as e:
            print(f"  Batch {i//batch_size + 1} error: {e}")

    print(f"\nTotal suggestions: {len(all_mappings)}")

    # Verify in Wikipedia ZIM
    found = []
    for m in all_mappings:
        wiki_path = m['wiki_title'].replace(' ', '_')
        try:
            entry = zim.get_entry_by_path(f'A/{wiki_path}')
            if entry.is_redirect:
                entry = entry.get_redirect_entry()
            content = entry.get_item().content.tobytes().decode('utf-8', errors='ignore')
            match = re.search(r'wikidata\.org/wiki/(Q\d+)', content)
            if match:
                found.append({
                    'id': m['id'],
                    'title': m['title'],
                    'qid': match.group(1),
                    'wiki': entry.title
                })
        except:
            pass

    print(f"Verified in ZIM: {len(found)}")

    # Apply to database
    if found:
        for f in found:
            wiki_url = 'https://en.wikipedia.org/wiki/' + f['wiki'].replace(' ', '_')
            db.execute(text('UPDATE events SET wikidata_id = :qid, wikipedia_url = :url WHERE id = :id'),
                       {'qid': f['qid'], 'url': wiki_url, 'id': f['id']})
        db.commit()
        print(f"Applied: {len(found)}")

        print("\nSamples:")
        for f in found[:15]:
            title = f['title'][:45] if len(f['title']) > 45 else f['title']
            print(f"  {title} -> {f['wiki']}")

    db.close()


if __name__ == '__main__':
    main()
