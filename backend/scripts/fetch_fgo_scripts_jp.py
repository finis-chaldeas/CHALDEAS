"""
FGO Script Fetcher & Parser (Multi-region)
============================================
Atlas Academy API에서 스크립트를 수집하고 구조화.
JP(일본어), NA(영어), KR(한국어), CN(중국어), TW(대만) 지원.

사용법:
    python -m scripts.fetch_fgo_scripts_jp                      # JP 메인 스토리
    python -m scripts.fetch_fgo_scripts_jp --region KR          # KR 메인 스토리
    python -m scripts.fetch_fgo_scripts_jp --region NA --events # NA 이벤트 스토리
    python -m scripts.fetch_fgo_scripts_jp --war-id 100         # 특정 war만
    python -m scripts.fetch_fgo_scripts_jp --list               # war 목록만 출력
    python -m scripts.fetch_fgo_scripts_jp --events --list      # 이벤트 war 목록

출력:
    E:/chaldeas_data/raw/atlas_academy/scripts_{region}/
        fuyuki_{region}.json
        ...
        main_story_{region}.json    — 메인 스토리 인덱스
        events_{region}.json        — 이벤트 인덱스 (--events 시)
"""

import argparse
import io
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

# Windows console: force UTF-8 output
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── Config ─────────────────────────────────────────────

API_BASE = "https://api.atlasacademy.io"
STATIC_BASE = "https://static.atlasacademy.io"
OUTPUT_BASE = Path(r"E:\chaldeas_data\raw\atlas_academy")

# warId → slug mapping (same as NA)
WAR_SLUGS = {
    # Part 1: Singularities
    100: "fuyuki",
    101: "orleans",
    102: "septem",
    103: "okeanos",
    104: "london",
    105: "america",
    106: "camelot",
    107: "babylonia",
    108: "solomon",
    # Part 1.5: Epic of Remnant
    201: "shinjuku",
    202: "agartha",
    203: "shimosa",
    204: "salem",
    # Part 2: Cosmos in the Lostbelt
    300: "lb_prologue",
    301: "lb1",
    302: "lb2",
    303: "lb3",
    304: "lb4",
    305: "lb5_atlantis",
    306: "lb5_olympus",
    307: "lb5.5_heian",
    308: "lb6",
    309: "tunguska",
    310: "traum",
    311: "lb7",
    # Part 2.5: Ordeal Call
    400: "ordeal_prologue",
    401: "ordeal_call",
    402: "ordeal1_papermoon",
    403: "ordeal2_id",
    404: "ordeal3_archetype",
    405: "ordeal4_trinity",
    406: "finale_prologue",
    407: "finale",
    # After Time
    500: "after_time",
}

# Rate limit: be polite to Atlas Academy
REQUEST_DELAY = 0.3  # seconds between requests


# ─── HTTP helpers ───────────────────────────────────────

def fetch_json(url: str) -> dict:
    """Fetch JSON from URL with retry."""
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": "CHALDEAS/1.0"})
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (HTTPError, URLError) as e:
            if attempt < 2:
                print(f"  Retry {attempt+1}/3 for {url}: {e}")
                time.sleep(2)
            else:
                raise
    return {}


def fetch_text(url: str) -> str:
    """Fetch raw text from URL."""
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": "CHALDEAS/1.0"})
            with urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8")
        except (HTTPError, URLError) as e:
            if attempt < 2:
                print(f"  Retry {attempt+1}/3: {e}")
                time.sleep(2)
            else:
                raise
    return ""


# ─── Script Parser ──────────────────────────────────────

def parse_script(raw_text: str) -> list[dict]:
    """
    Parse FGO raw script text into structured dialogues.

    Format:
        ＠{speaker}          — speaker line (full-width ＠)
        {text}               — dialogue text
        [k]                  — end of dialogue block
        ？1：{text}          — player choice 1
        ？2：{text}          — player choice 2
        ？！                 — player reaction
        [r]                  — line break in dialogue
        [line N]             — line break
        [{command} ...]      — scene/audio/visual commands (ignored)
    """
    dialogues = []
    lines = raw_text.split("\n")

    current_speaker: Optional[str] = None
    current_text_parts: list[str] = []

    def flush():
        nonlocal current_speaker, current_text_parts
        if current_speaker and current_text_parts:
            text = clean_text("".join(current_text_parts)).strip()
            if text:
                dialogues.append({
                    "speaker": current_speaker,
                    "text": text,
                })
        current_speaker = None
        current_text_parts = []

    for line in lines:
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # Skip command lines (but handle inline [r] and [line N] in text)
        if stripped.startswith("[") and stripped.endswith("]"):
            if stripped == "[k]":
                flush()
            continue

        # Speaker line: ＠{speaker} or ＠{slot}：{name} or ＠{slot} : {name} (KR)
        if stripped.startswith("＠"):
            flush()
            speaker_raw = stripped[1:].strip()  # remove ＠
            # JP: "A：マシュ" → "マシュ", KR: "A : ???" → "???"
            # Try full-width colon first, then half-width with spaces
            if "：" in speaker_raw:
                parts = speaker_raw.split("：", 1)
                current_speaker = parts[1].strip() if len(parts) > 1 else speaker_raw
            elif " : " in speaker_raw:
                parts = speaker_raw.split(" : ", 1)
                current_speaker = parts[1].strip() if len(parts) > 1 else speaker_raw
            elif ":" in speaker_raw:
                parts = speaker_raw.split(":", 1)
                current_speaker = parts[1].strip() if len(parts) > 1 else speaker_raw
            else:
                current_speaker = speaker_raw.strip()
            continue

        # Player choices: ？1：{text}, ?1: {text}, etc.
        choice_match = re.match(r"^[？?](\d+)[：:]\s*(.+)$", stripped)
        if choice_match:
            flush()
            choice_num = choice_match.group(1)
            choice_text = choice_match.group(2).strip()
            dialogues.append({
                "speaker": f"__player_choice_{choice_num}__",
                "text": clean_text(choice_text),
            })
            continue

        # Player reaction: ？！ or ?!
        if stripped in ("？！", "?！", "？!", "?!"):
            flush()
            dialogues.append({
                "speaker": "__player_reaction__",
                "text": "",
            })
            continue

        # Scene commands within text (ignore but don't break dialogue)
        if stripped.startswith("["):
            # Inline command within dialogue block — skip it
            continue

        # Regular dialogue text
        if current_speaker is not None:
            current_text_parts.append(clean_text(stripped))
        else:
            # Narration (no speaker) — still capture it
            # Check if it looks like player choice without ？ prefix
            if stripped.startswith("？") and "：" in stripped:
                choice_match2 = re.match(r"^？(\d+)：(.+)$", stripped)
                if choice_match2:
                    dialogues.append({
                        "speaker": f"__player_choice_{choice_match2.group(1)}__",
                        "text": clean_text(choice_match2.group(2)),
                    })
                    continue
            # Otherwise treat as narration
            if stripped and not stripped.startswith("＄"):
                dialogues.append({
                    "speaker": "__narration__",
                    "text": clean_text(stripped),
                })

    flush()
    return dialogues


def clean_text(text: str) -> str:
    """Clean dialogue text: remove [r], [line N], and other inline tags."""
    text = text.replace("[r]", "")
    text = re.sub(r"\[line \d+\]", "", text)
    text = re.sub(r"\[ruby text=[^\]]*\]", "", text)
    text = re.sub(r"\[/ruby\]", "", text)
    # Remove other inline tags but be conservative
    text = re.sub(r"\[(?:wait|wt|se|messageOff|charaFace|charaTalk|charaFadein|charaFadeout|charaSet)[^\]]*\]", "", text)
    return text.strip()


# ─── War Fetcher ────────────────────────────────────────

def fetch_war(war_id: int, slug: str, dry_run: bool = False, region: str = "JP") -> dict:
    """Fetch all scripts for a single war (singularity/lostbelt)."""
    print(f"\n{'='*60}")
    print(f"Fetching war {war_id}: {slug}")
    print(f"{'='*60}")

    # Get war metadata from API
    url = f"{API_BASE}/nice/{region}/war/{war_id}"
    print(f"  API: {url}")
    war_data = fetch_json(url)
    time.sleep(REQUEST_DELAY)

    war_name = war_data.get("name", slug)
    war_long_name = war_data.get("longName", "")
    war_age = war_data.get("age", "")

    # Parse year from age field (e.g. "AD:2004" → 2004, "BC:2655" → -2655)
    year = parse_year(war_age)

    result = {
        "id": slug,
        "name": war_name,
        "name_long": war_long_name,
        "year": year,
        "warId": war_id,
        "spots": [],
    }

    total_scripts = 0
    total_dialogues = 0

    # Process each spot
    for spot in war_data.get("spots", []):
        spot_name = spot.get("name", "Unknown")
        spot_id = spot.get("id", 0)

        spot_result = {
            "id": spot_id,
            "name": spot_name,
            "quests": [],
        }

        # Process each quest in the spot
        for quest in spot.get("quests", []):
            quest_id = quest.get("id", 0)
            quest_name = quest.get("name", "Unknown")
            quest_type = quest.get("type", "unknown")

            # Only main story quests (skip free quests, interludes, etc.)
            if quest_type not in ("main",):
                continue

            quest_result = {
                "id": quest_id,
                "name": quest_name,
                "type": quest_type,
                "scripts": [],
            }

            # Get script URLs from phaseScripts
            phase_scripts = quest.get("phaseScripts", [])
            for phase in phase_scripts:
                for script_info in phase.get("scripts", []) if isinstance(phase, dict) else []:
                    script_url = script_info.get("script", "")
                    if not script_url:
                        continue

                    if dry_run:
                        quest_result["scripts"].append({
                            "url": script_url,
                            "dialogue_count": 0,
                        })
                        total_scripts += 1
                        continue

                    # Fetch and parse the script
                    print(f"  [{total_scripts+1}] {quest_name} - {Path(script_url).stem}")
                    try:
                        raw = fetch_text(script_url)
                        dialogues = parse_script(raw)
                        quest_result["scripts"].append({
                            "url": script_url,
                            "dialogues": dialogues,
                            "dialogue_count": len(dialogues),
                        })
                        total_scripts += 1
                        total_dialogues += len(dialogues)
                        time.sleep(REQUEST_DELAY)
                    except Exception as e:
                        print(f"    ERROR: {e}")
                        quest_result["scripts"].append({
                            "url": script_url,
                            "dialogues": [],
                            "dialogue_count": 0,
                            "error": str(e),
                        })

            if quest_result["scripts"]:
                spot_result["quests"].append(quest_result)

        if spot_result["quests"]:
            result["spots"].append(spot_result)

    print(f"\n  Done: {total_scripts} scripts, {total_dialogues} dialogues")
    return result


def parse_year(age_str: str) -> Optional[int]:
    """Parse Atlas Academy age string to integer year."""
    if not age_str:
        return None
    # "AD:2004" → 2004, "BC:2655" → -2655
    match = re.match(r"(AD|BC):(\d+)", age_str)
    if match:
        era, num = match.group(1), int(match.group(2))
        return -num if era == "BC" else num
    # Try plain number
    try:
        return int(age_str)
    except ValueError:
        return None


# ─── phaseScripts extraction ────────────────────────────

def extract_script_urls(war_data: dict) -> list[str]:
    """Extract all script URLs from war data, handling nested phaseScripts."""
    urls = []
    for spot in war_data.get("spots", []):
        for quest in spot.get("quests", []):
            if quest.get("type") != "main":
                continue
            for phase_entry in quest.get("phaseScripts", []):
                # phaseScripts is a list of {phase: int, scripts: [...]}
                if isinstance(phase_entry, dict):
                    for script in phase_entry.get("scripts", []):
                        script_url = script.get("script", "")
                        if script_url:
                            urls.append(script_url)
    return urls


# ─── Main ───────────────────────────────────────────────

def list_wars(region: str = "JP", events: bool = False):
    """Print available wars."""
    if not events:
        print(f"Main Story Wars ({region}):")
        for wid, slug in sorted(WAR_SLUGS.items()):
            print(f"  {wid}: {slug}")
    else:
        # Fetch event wars from API
        print(f"Fetching event war list from API ({region})...")
        url = f"{API_BASE}/basic/{region}/war?type=event"
        try:
            wars = fetch_json(url)
            if isinstance(wars, list):
                print(f"Event wars: {len(wars)}")
                for w in wars[:50]:
                    print(f"  {w.get('id', '?'):>6d}  {w.get('name', '?')}")
                if len(wars) > 50:
                    print(f"  ... and {len(wars)-50} more")
        except Exception as e:
            print(f"Error: {e}")


def fetch_event_wars(region: str) -> list[dict]:
    """Fetch list of event wars from export endpoint."""
    url = f"{API_BASE}/export/{region}/basic_war.json"
    all_wars = fetch_json(url)
    if not isinstance(all_wars, list):
        return []
    # Event wars: ID 1000~9999 (main story < 1000)
    # 1000-8999: gameplay events, reruns, gates
    # 9000-9999: story events (SE.RA.PH, Ooku, Luluhawa, etc.)
    main_ids = set(WAR_SLUGS.keys())
    event_wars = [
        w for w in all_wars
        if 1000 <= w.get("id", 0) <= 9999
        and w.get("id", 0) not in main_ids
    ]
    return event_wars


def main():
    parser = argparse.ArgumentParser(description="Fetch FGO scripts from Atlas Academy")
    parser.add_argument("--region", default="JP", choices=["JP", "NA", "KR", "CN", "TW"],
                        help="Region (default: JP)")
    parser.add_argument("--war-id", type=int, help="Fetch specific war only")
    parser.add_argument("--list", action="store_true", help="List available wars")
    parser.add_argument("--events", action="store_true", help="Fetch event stories instead of main story")
    parser.add_argument("--dry-run", action="store_true", help="Don't download scripts, just show structure")
    parser.add_argument("--output", type=str, help="Output directory override")
    args = parser.parse_args()

    region = args.region.upper()

    if args.list:
        list_wars(region, args.events)
        return

    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        suffix = f"scripts_{region.lower()}"
        if args.events:
            suffix += "_events"
        output_dir = OUTPUT_BASE / suffix

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Region: {region}")
    print(f"Output: {output_dir}")

    region_suffix = region.lower()

    # Determine which wars to fetch
    if args.war_id:
        wars = {args.war_id: WAR_SLUGS.get(args.war_id, f"war_{args.war_id}")}
    elif args.events:
        print("Fetching event war list...")
        event_wars = fetch_event_wars(region)
        print(f"Found {len(event_wars)} event wars")
        wars = {w["id"]: f"event_{w['id']}" for w in event_wars}
        time.sleep(REQUEST_DELAY)
    else:
        wars = WAR_SLUGS

    # Fetch each war
    all_results = []
    skipped = []
    for war_id, slug in sorted(wars.items()):
        try:
            result = fetch_war(war_id, slug, dry_run=args.dry_run, region=region)
        except Exception as e:
            print(f"  SKIPPED war {war_id} ({slug}): {e}")
            skipped.append((war_id, slug, str(e)))
            continue
        all_results.append(result)

        # Save individual file
        out_path = output_dir / f"{slug}_{region_suffix}.json"
        out_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  Saved: {out_path}")

    # Save combined index
    index_name = f"events_{region_suffix}.json" if args.events else f"main_story_{region_suffix}.json"
    index_path = output_dir / index_name
    index_path.write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved combined index: {index_path}")

    # Print summary
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    for r in all_results:
        total_scripts = sum(
            len(q["scripts"])
            for s in r["spots"]
            for q in s["quests"]
        )
        total_dialogues = sum(
            sc["dialogue_count"]
            for s in r["spots"]
            for q in s["quests"]
            for sc in q["scripts"]
        )
        print(f"  {r['id']:20s}  scripts={total_scripts:4d}  dialogues={total_dialogues:5d}")

    if skipped:
        print(f"\nSkipped {len(skipped)} wars:")
        for wid, wslug, err in skipped:
            print(f"  {wid} ({wslug}): {err}")


if __name__ == "__main__":
    main()
