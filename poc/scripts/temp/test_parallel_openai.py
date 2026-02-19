"""Test parallel OpenAI calls to measure throughput"""
import asyncio
import httpx
import time
import os

OPENAI_URL = 'https://api.openai.com/v1'
API_KEY = os.getenv('OPENAI_API_KEY')

async def call_one(client, i):
    try:
        response = await client.post(
            f'{OPENAI_URL}/chat/completions',
            headers={'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'},
            json={
                'model': 'gpt-5-nano',
                'messages': [{'role': 'user', 'content': f'Entity {i}: Is this the same? Answer YES or NO.'}],
                'max_completion_tokens': 10
            }
        )
        return response.status_code
    except Exception as e:
        return str(e)[:30]

async def test_parallel(n):
    async with httpx.AsyncClient(timeout=60.0) as client:
        start = time.time()
        tasks = [call_one(client, i) for i in range(n)]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start
        success = sum(1 for r in results if r == 200)
        rate = n / elapsed
        print(f'{n:3d} parallel: {elapsed:5.1f}s | {rate:6.1f}/sec | {success}/{n} success')
        return rate

async def main():
    print("Testing parallel OpenAI gpt-5-nano calls...")
    print("-" * 50)

    rates = []
    for n in [5, 10, 20, 30, 50]:
        rate = await test_parallel(n)
        rates.append((n, rate))
        await asyncio.sleep(1)  # Small pause between tests

    print("-" * 50)
    best_n, best_rate = max(rates, key=lambda x: x[1])
    print(f"Best: {best_n} parallel = {best_rate:.1f} calls/sec")
    print(f"At this rate: 300K items = {300000/best_rate/3600:.1f} hours")

if __name__ == "__main__":
    asyncio.run(main())
