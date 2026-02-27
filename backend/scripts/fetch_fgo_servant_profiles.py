"""
FGO Servant Profile Fetcher (JP + NA)
======================================
Atlas Academy API에서 서번트 프로필(본드 텍스트, 보이스 등) 수집.

이미 있는 것:
    servant_profiles_na.json — NA 본드 텍스트 (이전에 수집)

새로 수집:
    servant_profiles_jp.json — JP 본드 텍스트 (일본어 원문)

사용법:
    python -m scripts.fetch_fgo_servant_profiles              # JP 전체
    python -m scripts.fetch_fgo_servant_profiles --region NA   # NA 전체
    python -m scripts.fetch_fgo_servant_profiles --limit 5     # 테스트 (5명만)
    python -m scripts.fetch_fgo_servant_profiles --id 100100   # 특정 서번트만

출력:
    E:/chaldeas_data/raw/atlas_academy/
        servant_profiles_jp.json
"""

import argparse
import io
import json
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

# Windows UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── Config ─────────────────────────────────────────────

API_BASE = "https://api.atlasacademy.io"
OUTPUT_DIR = Path(r"E:\chaldeas_data\raw\atlas_academy")
REQUEST_DELAY = 0.5  # seconds between requests


def fetch_json(url: str) -> Optional[dict]:
    """Fetch JSON with retry."""
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": "CHALDEAS/1.0"})
            with urlopen(req, timeout=30) as resp:
                raw = resp.read()
                return json.loads(raw.decode("utf-8"))
        except (HTTPError, URLError) as e:
            if attempt < 2:
                print(f"    Retry {attempt+1}: {e}")
                time.sleep(2)
            else:
                print(f"    FAILED: {e}")
                return None
    return None


def fetch_servant_profile(servant_id: int, region: str = "JP") -> Optional[dict]:
    """Fetch a single servant's profile with lore=true."""
    url = f"{API_BASE}/nice/{region}/servant/{servant_id}?lore=true"
    data = fetch_json(url)
    if not data:
        return None

    profile = data.get("profile", {})
    if not profile:
        return None

    # Extract the useful parts
    return {
        "id": data.get("id"),
        "collectionNo": data.get("collectionNo"),
        "name": data.get("name", ""),
        "originalName": data.get("originalName", ""),
        "className": data.get("className", ""),
        "rarity": data.get("rarity"),
        "gender": data.get("gender", ""),
        "attribute": data.get("attribute", ""),
        "cv": profile.get("cv", ""),
        "illustrator": profile.get("illustrator", ""),
        "stats": profile.get("stats", {}),
        "comments": [
            {
                "id": c.get("id"),
                "priority": c.get("priority", 0),
                "condMessage": c.get("condMessage", ""),
                "condType": c.get("condType", ""),
                "comment": c.get("comment", ""),
            }
            for c in profile.get("comments", [])
            if c.get("comment")
        ],
        "costume": profile.get("costume", {}),
        # Voice lines (for reference, not for display)
        "voice_count": len(profile.get("voices", [])),
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch FGO servant profiles")
    parser.add_argument("--region", default="JP", choices=["JP", "NA", "KR"], help="Region (default: JP)")
    parser.add_argument("--limit", type=int, help="Limit number of servants")
    parser.add_argument("--id", type=int, help="Fetch specific servant ID only")
    parser.add_argument("--resume", action="store_true", help="Skip already-fetched servants")
    args = parser.parse_args()

    region = args.region
    output_path = OUTPUT_DIR / f"servant_profiles_{region.lower()}.json"

    # Load servant list for this region
    basic_path = OUTPUT_DIR / f"servants_basic_{region.lower()}.json"
    if not basic_path.exists():
        # Try full servants file
        basic_path = OUTPUT_DIR / f"servants_{region.lower()}.json"
    if not basic_path.exists():
        print(f"Error: No servant list found at {basic_path}")
        return

    servants = json.loads(basic_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(servants)} servants from {basic_path.name}")

    # Specific servant ID mode
    if args.id:
        print(f"\nFetching servant {args.id} ({region})...")
        profile = fetch_servant_profile(args.id, region)
        if profile:
            print(f"  {profile['name']} ({profile['className']}) — {len(profile['comments'])} comments")
            for c in profile["comments"][:3]:
                print(f"    [{c['id']}] {c['comment'][:80]}...")
        else:
            print("  Not found or no profile")
        return

    # Load existing profiles for resume mode
    existing = {}
    if args.resume and output_path.exists():
        existing_data = json.loads(output_path.read_text(encoding="utf-8"))
        existing = {p["id"]: p for p in existing_data}
        print(f"Resuming: {len(existing)} already fetched")

    # Filter to playable servants (exclude enemy-only, etc.)
    playable = [s for s in servants if s.get("type") in ("normal", "heroine")]
    print(f"Playable servants: {len(playable)}")

    if args.limit:
        playable = playable[:args.limit]
        print(f"Limited to first {args.limit}")

    # Fetch profiles
    profiles = list(existing.values()) if args.resume else []
    fetched = 0
    skipped = 0
    failed = 0

    for i, servant in enumerate(playable):
        sid = servant["id"]
        sname = servant.get("name", "?")

        if args.resume and sid in existing:
            skipped += 1
            continue

        print(f"  [{i+1}/{len(playable)}] {sname} (id={sid})...", end="", flush=True)
        profile = fetch_servant_profile(sid, region)

        if profile:
            profiles.append(profile)
            fetched += 1
            comment_count = len(profile["comments"])
            print(f" {comment_count} comments")
        else:
            failed += 1
            print(" FAILED")

        time.sleep(REQUEST_DELAY)

        # Save checkpoint every 50 servants
        if fetched > 0 and fetched % 50 == 0:
            output_path.write_text(
                json.dumps(profiles, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"    [checkpoint: {len(profiles)} saved]")

    # Final save
    output_path.write_text(
        json.dumps(profiles, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n{'='*50}")
    print(f"Done! Fetched={fetched}, Skipped={skipped}, Failed={failed}")
    print(f"Total profiles: {len(profiles)}")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
