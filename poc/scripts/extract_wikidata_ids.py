"""
Extract Wikidata IDs from Wikipedia URLs.

Many events have wikipedia_url but no wikidata_id.
This script fetches the Wikidata QID from Wikipedia pages.

Rate limit handling: backs off and retries on 403/429.
"""
import asyncio
import aiohttp
import re
import sys
import os
import random

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import SessionLocal

# Rate limit state
rate_limit_wait = 5  # Start with 5 seconds
consecutive_errors = 0


async def get_wikidata_id_from_wikipedia(session: aiohttp.ClientSession, wikipedia_url: str, retry: int = 0) -> tuple[str | None, bool]:
    """
    Extract Wikidata QID from a Wikipedia page.
    Returns (qid, rate_limited) tuple.
    """
    global rate_limit_wait, consecutive_errors

    if not wikipedia_url:
        return None, False

    try:
        # Extract article title from URL
        match = re.search(r'wikipedia\.org/wiki/(.+?)(?:\?|#|$)', wikipedia_url)
        if not match:
            return None, False

        title = match.group(1)
        lang = 'en'

        # Check for other language wikis
        lang_match = re.search(r'https?://(\w+)\.wikipedia\.org', wikipedia_url)
        if lang_match:
            lang = lang_match.group(1)

        # Use Wikipedia API to get Wikidata ID
        api_url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "titles": title,
            "prop": "pageprops",
            "format": "json",
        }

        headers = {
            "User-Agent": "ChaldeasBot/1.0 (Historical Knowledge System; contact@chaldeas.site)"
        }

        async with session.get(api_url, params=params, headers=headers, timeout=15) as response:
            # Rate limited
            if response.status in (403, 429):
                consecutive_errors += 1
                wait_time = rate_limit_wait * (2 ** min(consecutive_errors, 5))  # Exponential backoff, max 5 doublings
                print(f"  [RATE LIMITED] Status {response.status}, waiting {wait_time}s...")
                await asyncio.sleep(wait_time)

                if retry < 3:
                    return await get_wikidata_id_from_wikipedia(session, wikipedia_url, retry + 1)
                return None, True

            if response.status != 200:
                return None, False

            # Success - reset error counter
            consecutive_errors = 0

            data = await response.json()
            pages = data.get("query", {}).get("pages", {})

            for page_id, page_data in pages.items():
                if page_id == "-1":
                    continue
                props = page_data.get("pageprops", {})
                wikidata_id = props.get("wikibase_item")
                if wikidata_id:
                    return wikidata_id, False

    except asyncio.TimeoutError:
        print(f"  Timeout: {wikipedia_url}")
        return None, False
    except Exception as e:
        print(f"  Error fetching {wikipedia_url}: {e}")
        return None, False

    return None, False


async def process_single(db: Session, event_id: int, wikipedia_url: str, session: aiohttp.ClientSession) -> tuple[bool, bool]:
    """
    Process a single event.
    Returns (success, rate_limited) tuple.
    """
    wikidata_id, rate_limited = await get_wikidata_id_from_wikipedia(session, wikipedia_url)

    if rate_limited:
        return False, True

    if wikidata_id:
        db.execute(
            text("UPDATE events SET wikidata_id = :qid WHERE id = :id"),
            {"qid": wikidata_id, "id": event_id}
        )
        db.commit()
        title = wikipedia_url.split('/wiki/')[-1][:40]
        print(f"  [{event_id}] {title} -> {wikidata_id}")
        return True, False

    return False, False


async def main(limit: int = 1000, delay: float = 2.0):
    """
    Extract Wikidata IDs for events with wikipedia_url but no wikidata_id.

    Args:
        limit: Number of events to process
        delay: Base delay between requests (seconds)
    """
    db = SessionLocal()

    try:
        # Get events with actual wikipedia.org URL but no wikidata_id
        result = db.execute(text("""
            SELECT id, wikipedia_url
            FROM events
            WHERE wikipedia_url LIKE '%wikipedia.org%'
            AND wikidata_id IS NULL
            ORDER BY importance DESC
            LIMIT :limit
        """), {"limit": limit})

        events = [(row[0], row[1]) for row in result]
        print(f"Found {len(events)} events with Wikipedia URL but no Wikidata ID")
        print(f"Delay: {delay}s between requests")
        print("=" * 50)

        if not events:
            print("No events to process.")
            return

        total_updated = 0
        total_rate_limited = 0
        connector = aiohttp.TCPConnector(limit=1)  # Only 1 concurrent connection

        async with aiohttp.ClientSession(connector=connector) as session:
            for i, (event_id, wikipedia_url) in enumerate(events):
                success, rate_limited = await process_single(db, event_id, wikipedia_url, session)

                if success:
                    total_updated += 1
                if rate_limited:
                    total_rate_limited += 1

                # Progress every 50
                if (i + 1) % 50 == 0:
                    print(f"  Progress: {i + 1}/{len(events)} ({total_updated} updated)")

                # Add jitter to delay
                jitter = random.uniform(0.5, 1.5)
                await asyncio.sleep(delay * jitter)

        print("\n" + "=" * 50)
        print(f"Total updated: {total_updated}/{len(events)}")
        print(f"Rate limited: {total_rate_limited}")

    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract Wikidata IDs from Wikipedia URLs")
    parser.add_argument("--limit", type=int, default=1000, help="Number of events to process")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between requests (seconds)")

    args = parser.parse_args()
    asyncio.run(main(limit=args.limit, delay=args.delay))
