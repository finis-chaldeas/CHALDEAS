"""
Test batch LLM approach for Phase 2
Compare: 5 individual calls vs 1 batch call
"""
import asyncio
import httpx
import time
import json

OLLAMA_URL = "http://localhost:11434"

# Test data - 3 entities with candidates (reduced for faster testing)
TEST_ITEMS = [
    {"text": "Charles VII", "type": "person", "candidates": ["Charles VIII"]},
    {"text": "Rome", "type": "location", "candidates": ["Roman Empire"]},
    {"text": "Napoleon", "type": "person", "candidates": ["Napoleon III"]},
]


async def single_call(item: dict) -> str:
    """Individual LLM call for one item"""
    candidates_text = "\n".join([f"  {i+1}. {c}" for i, c in enumerate(item["candidates"])])
    prompt = f"""Entity: "{item['text']}" (type: {item['type']})
Similar existing entities:
{candidates_text}

If this entity refers to one of the candidates, respond: LINK <number>
If it's different from all candidates, respond: CREATE_NEW

Response:"""

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": "qwen3:8b",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.1}
            }
        )
        content = response.json().get("message", {}).get("content", "").strip()
        # Remove thinking tags
        if "<think>" in content:
            content = content.split("</think>")[-1].strip()
        return content


async def batch_call(items: list) -> list:
    """Single LLM call for multiple items"""

    # Build batch prompt
    entity_blocks = []
    for i, item in enumerate(items, 1):
        candidates_text = ", ".join([f"{j+1}.{c}" for j, c in enumerate(item["candidates"])])
        entity_blocks.append(f"[{i}] \"{item['text']}\" ({item['type']}) - Candidates: {candidates_text}")

    prompt = f"""You are an entity disambiguation expert. For EACH entity below, decide:
- LINK <num> if it matches a candidate
- NEW if it's different from all candidates

Entities:
{chr(10).join(entity_blocks)}

Respond with one decision per line, format: [number] LINK <num> or [number] NEW
Example:
[1] NEW
[2] LINK 1
[3] NEW

Your decisions:"""

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": "qwen3:8b",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.1}
            }
        )
        content = response.json().get("message", {}).get("content", "").strip()
        # Remove thinking tags
        if "<think>" in content:
            content = content.split("</think>")[-1].strip()

        # Parse responses
        results = []
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("["):
                results.append(line)

        return results if results else [content]


async def main():
    print("=" * 60)
    print("Batch LLM Test")
    print("=" * 60)

    # Test 1: Individual calls
    print("\n[Test 1] 5 Individual Calls")
    start = time.time()
    individual_results = []
    for item in TEST_ITEMS:
        result = await single_call(item)
        individual_results.append(result)
        print(f"  {item['text']}: {result[:50]}")
    individual_time = time.time() - start
    print(f"  Time: {individual_time:.1f}s ({individual_time/len(TEST_ITEMS):.1f}s per call)")

    # Test 2: Batch call
    print(f"\n[Test 2] 1 Batch Call ({len(TEST_ITEMS)} items)")
    start = time.time()
    batch_results = await batch_call(TEST_ITEMS)
    batch_time = time.time() - start
    for r in batch_results:
        print(f"  {r}")
    print(f"  Time: {batch_time:.1f}s ({batch_time/len(TEST_ITEMS):.1f}s per item)")

    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Individual: {individual_time:.1f}s total")
    print(f"  Batch:      {batch_time:.1f}s total")
    print(f"  Speedup:    {individual_time/batch_time:.1f}x faster")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
