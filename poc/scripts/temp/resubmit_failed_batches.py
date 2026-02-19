"""Resubmit failed batches when queue has space."""
import httpx
import json
import time
from pathlib import Path

API_KEY = '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'
OUTPUT_DIR = Path('C:/Projects/Chaldeas/poc/data/integrated_ner_full')

def main():
    headers = {'Authorization': f'Bearer {API_KEY}'}
    status_file = OUTPUT_DIR / 'minimal_submission_status.json'

    with open(status_file) as f:
        status = json.load(f)

    while True:
        # Check status
        in_progress = []
        completed = []
        failed = []

        for batch_name, info in sorted(status['batches'].items()):
            batch_id = info['batch_id']
            resp = httpx.get(f'https://api.openai.com/v1/batches/{batch_id}', headers=headers)
            data = resp.json()

            if data['status'] == 'completed':
                completed.append(batch_name)
            elif data['status'] == 'in_progress':
                in_progress.append((batch_name, data.get('request_counts', {})))
            elif data['status'] == 'failed':
                failed.append(batch_name)

        # Print status
        print(f'\n=== STATUS ===')
        print(f'Completed: {len(completed)}')
        for name in completed:
            print(f'  {name}')

        print(f'In Progress: {len(in_progress)}')
        for name, counts in in_progress:
            print(f'  {name}: {counts.get("completed", 0)}/{counts.get("total", 0)}')

        print(f'Failed (pending resubmit): {len(failed)}')
        for name in failed:
            print(f'  {name}')

        # All done?
        if not failed and not in_progress:
            print('\nAll batches completed!')
            break

        # Try to resubmit failed batches
        if failed and len(in_progress) < 2:  # Only resubmit if queue has space
            batch_name = failed[0]
            info = status['batches'][batch_name]
            file_id = info['file_id']

            print(f'\nResubmitting {batch_name}...')

            batch_data = {
                'input_file_id': file_id,
                'endpoint': '/v1/chat/completions',
                'completion_window': '24h'
            }
            resp = httpx.post('https://api.openai.com/v1/batches', headers=headers,
                            json=batch_data, timeout=30.0)

            if resp.status_code == 200:
                new_batch_id = resp.json()['id']
                print(f'  OK: {new_batch_id}')
                status['batches'][batch_name]['batch_id'] = new_batch_id

                # Save updated status
                with open(status_file, 'w') as f:
                    json.dump(status, f, indent=2)
            else:
                error = resp.json().get('error', {}).get('message', resp.text[:100])
                print(f'  Failed: {error}')

        # Wait before next check
        print(f'\nWaiting 60s...')
        time.sleep(60)

if __name__ == '__main__':
    main()
