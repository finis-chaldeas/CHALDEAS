"""Check status of test batches and analyze results if complete."""
import httpx
import json

API_KEY = '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'

BATCHES = {
    'unlimited': 'batch_695c52c6bfcc81909bc227505c6a6b9f',
    'minimal': 'batch_695c6bd60988819097aeca72571322ec',
}

def analyze_results(headers, output_file_id, name):
    print(f'\n=== {name.upper()} RESULTS ===')
    resp = httpx.get(f'https://api.openai.com/v1/files/{output_file_id}/content', headers=headers, timeout=120.0)

    lines = resp.text.strip().split('\n')
    success = 0
    truncated = 0
    total_prompt = 0
    total_completion = 0
    total_reasoning = 0
    total_persons = 0
    total_locations = 0

    for line in lines:
        result = json.loads(line)
        body = result.get('response', {}).get('body', {})
        choice = body.get('choices', [{}])[0]
        content = choice.get('message', {}).get('content', '')
        finish_reason = choice.get('finish_reason', '')
        usage = body.get('usage', {})

        total_prompt += usage.get('prompt_tokens', 0)
        total_completion += usage.get('completion_tokens', 0)
        total_reasoning += usage.get('completion_tokens_details', {}).get('reasoning_tokens', 0)

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

    print(f'Docs: {len(lines)}')
    print(f'Success: {success} ({success*100//len(lines)}%)')
    print(f'Truncated: {truncated}')
    print(f'Avg persons: {total_persons/max(success,1):.1f}')
    print(f'Avg locations: {total_locations/max(success,1):.1f}')

    output_tokens = total_completion - total_reasoning
    print(f'\nTokens - prompt: {total_prompt:,}, completion: {total_completion:,}')
    print(f'         reasoning: {total_reasoning:,}, output: {output_tokens:,}')

    # 비용 계산
    input_cost = (total_prompt / 1_000_000) * 0.05
    output_cost = (total_completion / 1_000_000) * 0.20
    total_cost = input_cost + output_cost
    print(f'\nCost: ${total_cost:.4f} (${total_cost/len(lines):.6f}/doc)')
    print(f'76,019 docs estimate: ${total_cost/len(lines)*76019:.2f}')

    # 샘플
    print('\nSample:')
    for line in lines[:2]:
        result = json.loads(line)
        body = result.get('response', {}).get('body', {})
        content = body.get('choices', [{}])[0].get('message', {}).get('content', '')
        usage = body.get('usage', {})
        if content:
            try:
                ext = json.loads(content)
                r = usage.get('completion_tokens_details', {}).get('reasoning_tokens', 0)
                o = usage.get('completion_tokens', 0) - r
                print(f'  {result["custom_id"]}: {len(ext.get("persons",[]))}p/{len(ext.get("locations",[]))}l, r={r}/o={o}')
            except:
                pass

def main():
    headers = {'Authorization': f'Bearer {API_KEY}'}

    print('=== TEST BATCH STATUS ===\n')

    for name, batch_id in BATCHES.items():
        resp = httpx.get(f'https://api.openai.com/v1/batches/{batch_id}', headers=headers)
        data = resp.json()
        counts = data.get('request_counts', {})
        completed = counts.get('completed', 0)
        total = counts.get('total', 0)
        failed = counts.get('failed', 0)

        print(f'{name:12}: {data["status"]:12} | {completed}/{total} done, {failed} failed')

        if data['status'] == 'completed' and data.get('output_file_id'):
            analyze_results(headers, data['output_file_id'], name)

if __name__ == '__main__':
    main()
