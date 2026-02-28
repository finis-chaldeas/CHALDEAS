"""
FGO Story Summarizer
====================
FGO 메인 스토리 + 이벤트의 챕터 단위 요약 생성.

짧은 챕터는 원샷, 긴 챕터는 AI가 서사 구조를 분석해 파트 분할 후 합성.

Usage:
    cd backend
    python -m scripts.summarize_fgo_stories                          # 전체 실행
    python -m scripts.summarize_fgo_stories --chapter fuyuki         # 단일 챕터
    python -m scripts.summarize_fgo_stories --main-only              # 메인 스토리만
    python -m scripts.summarize_fgo_stories --events-only            # 이벤트만
    python -m scripts.summarize_fgo_stories --dry-run                # 비용 추정만
    python -m scripts.summarize_fgo_stories --stats                  # 진행률 확인
    python -m scripts.summarize_fgo_stories --test 3                 # 3챕터 테스트

Models:
    gpt-5.1-chat-latest — 요약/번역 (가성비)
"""
import argparse
import io
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)


def log(msg="", end="\n"):
    """Print with immediate flush for background execution."""
    print(msg, end=end)
    sys.stdout.flush()

# ─── Paths ──────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent
RAW_DIR = Path(r"E:\chaldeas_data\raw\atlas_academy")
OUTPUT_DIR = Path(r"E:\chaldeas_data\processed\fgo\summaries")
CHECKPOINT_FILE = OUTPUT_DIR / "checkpoint.jsonl"

# ─── Config ─────────────────────────────────────────────

MODEL = "gpt-5.1-chat-latest"
PRICE_INPUT = 1.25   # $/1M tokens
PRICE_OUTPUT = 10.0  # $/1M tokens
TOKEN_THRESHOLD = 40_000   # 이 이상이면 파트 분할 (추정 tok의 ~2배가 실제 입력)
MAX_COMPLETION = 4000
MAX_DIALOGUE_CHARS_PART = 80_000  # 파트별 대사 길이 제한 (파트 당)

# ─── .env ───────────────────────────────────────────────

env_path = ROOT_DIR / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())


# ─── Chapter metadata (from build_fgo_db.py) ───────────

CHAPTER_META = {
    100: {"slug": "fuyuki",    "type": "singularity", "number": "F",     "name_en": "Fuyuki"},
    101: {"slug": "orleans",   "type": "singularity", "number": "I",     "name_en": "Orleans"},
    102: {"slug": "septem",    "type": "singularity", "number": "II",    "name_en": "Septem"},
    103: {"slug": "okeanos",   "type": "singularity", "number": "III",   "name_en": "Okeanos"},
    104: {"slug": "london",    "type": "singularity", "number": "IV",    "name_en": "London"},
    105: {"slug": "america",   "type": "singularity", "number": "V",     "name_en": "E Pluribus Unum"},
    106: {"slug": "camelot",   "type": "singularity", "number": "VI",    "name_en": "Camelot"},
    107: {"slug": "babylonia", "type": "singularity", "number": "VII",   "name_en": "Babylonia"},
    108: {"slug": "solomon",   "type": "singularity", "number": "Final", "name_en": "Solomon"},
    201: {"slug": "shinjuku",  "type": "remnant",    "number": "I",      "name_en": "Shinjuku"},
    202: {"slug": "agartha",   "type": "remnant",    "number": "II",     "name_en": "Agartha"},
    203: {"slug": "shimosa",   "type": "remnant",    "number": "III",    "name_en": "Shimosa"},
    204: {"slug": "salem",     "type": "remnant",    "number": "IV",     "name_en": "Salem"},
    301: {"slug": "lb1",       "type": "lostbelt",   "number": "1",      "name_en": "Anastasia"},
    302: {"slug": "lb2",       "type": "lostbelt",   "number": "2",      "name_en": "Götterdämmerung"},
    303: {"slug": "lb3",       "type": "lostbelt",   "number": "3",      "name_en": "SIN"},
    304: {"slug": "lb4",       "type": "lostbelt",   "number": "4",      "name_en": "Yuga Kshetra"},
    305: {"slug": "lb5",       "type": "lostbelt",   "number": "5",      "name_en": "Atlantis/Olympus"},
    306: {"slug": "lb5.5",     "type": "lostbelt",   "number": "5.5",    "name_en": "Heian-kyo"},
    308: {"slug": "lb6",       "type": "lostbelt",   "number": "6",      "name_en": "Avalon le Fae"},
    311: {"slug": "lb7",       "type": "lostbelt",   "number": "7",      "name_en": "Nahui Mictlan"},
}

# Extra chapters not in CHAPTER_META (prologues, ordeal call, etc.)
EXTRA_SLUGS = [
    "lb_prologue", "ordeal_prologue", "ordeal_call",
    "ordeal1_papermoon", "ordeal2_id", "ordeal3_archetype", "ordeal4_trinity",
    "traum", "tunguska", "finale_prologue", "finale", "after_time",
    "lb5_atlantis", "lb5_olympus", "lb5.5_heian",
]


# ─── Helpers ────────────────────────────────────────────

def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_openai_client():
    from openai import OpenAI
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment")
    return OpenAI(api_key=api_key)


def calc_cost(input_tok, output_tok):
    return input_tok * PRICE_INPUT / 1e6 + output_tok * PRICE_OUTPUT / 1e6


# ─── Chapter data loading ──────────────────────────────

def find_chapter_files(main_only=False, events_only=False, chapter_filter=None):
    """Find all chapter JSON files to process."""
    chapters = []

    if not events_only:
        # Main story files
        jp_dir = RAW_DIR / "scripts_jp"
        if jp_dir.exists():
            for f in sorted(jp_dir.glob("*_jp.json")):
                slug = f.name.replace("_jp.json", "")
                if slug == "main_story":
                    continue
                if chapter_filter and slug != chapter_filter:
                    continue
                chapters.append({"slug": slug, "path": f, "category": "main"})

    if not main_only:
        # Event files
        ev_dir = RAW_DIR / "scripts_jp_events"
        if ev_dir.exists():
            for f in sorted(ev_dir.glob("event_*_jp.json")):
                slug = f.name.replace("_jp.json", "")
                if chapter_filter and slug != chapter_filter:
                    continue
                chapters.append({"slug": slug, "path": f, "category": "event"})

    return chapters


def analyze_chapter(data):
    """Extract quest info with dialogue counts and speakers."""
    quests = []
    total_chars = 0

    for spot in data.get("spots", []):
        for quest in spot.get("quests", []):
            dlg_count = 0
            char_count = 0
            speaker_counter = Counter()

            for script in quest.get("scripts", []):
                for dlg in script.get("dialogues", []):
                    speaker = dlg.get("speaker", "")
                    if not speaker.startswith("__"):
                        dlg_count += 1
                        char_count += len(dlg.get("text", ""))
                        speaker_counter[speaker] += 1

            total_chars += char_count
            quests.append({
                "id": quest["id"],
                "name": quest["name"],
                "spot": spot["name"],
                "dlg_count": dlg_count,
                "char_count": char_count,
                "est_tokens": char_count // 2,
                "top_speakers": speaker_counter.most_common(5),
            })

    return quests, total_chars // 2  # est total tokens


MAX_DIALOGUE_CHARS = 120_000  # ~60K tokens — prevent context overflow


def build_dialogue_text(data, quest_ids=None):
    """Build dialogue text from chapter data, optionally filtering by quest IDs."""
    lines = []
    for spot in data.get("spots", []):
        for quest in spot.get("quests", []):
            if quest_ids and quest["id"] not in quest_ids:
                continue
            lines.append(f"--- Quest: {quest['name']} ---")
            for script in quest.get("scripts", []):
                for dlg in script.get("dialogues", []):
                    speaker = dlg.get("speaker", "")
                    text = dlg.get("text", "")
                    if speaker.startswith("__"):
                        continue
                    lines.append(f"{speaker}: {text}")
    text = "\n".join(lines)

    # Truncate if too long to prevent context overflow
    # Use per-part limit when filtering by quest_ids, full limit otherwise
    max_chars = MAX_DIALOGUE_CHARS_PART if quest_ids else MAX_DIALOGUE_CHARS
    if len(text) > max_chars:
        half = max_chars * 2 // 3
        tail = max_chars // 3
        text = text[:half] + "\n\n[...中略...]\n\n" + text[-tail:]

    return text


# ─── Checkpoint ─────────────────────────────────────────

def load_checkpoint():
    done = set()
    if CHECKPOINT_FILE.exists():
        for line in CHECKPOINT_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    entry = json.loads(line)
                    key = entry.get("_key", "")
                    if key:
                        done.add(key)
                except json.JSONDecodeError:
                    pass
    return done


def save_checkpoint(entry):
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ─── AI calls ──────────────────────────────────────────

def ai_split_chapter(client, slug, chapter_name, quests, total_tokens):
    """Ask AI to find natural narrative break points."""
    quest_lines = []
    for i, q in enumerate(quests):
        speakers = ", ".join(f"{name}({count})" for name, count in q["top_speakers"])
        quest_lines.append(
            f"  {i+1}. {q['name']} | spot: {q['spot']} | "
            f"{q['dlg_count']} lines, ~{q['est_tokens']:,} tok | "
            f"speakers: {speakers}"
        )

    prompt = f"""Fate/Grand Order chapter: {chapter_name}
Total: {len(quests)} quests, ~{total_tokens:,} tokens

Quest list with details (in story order):
{chr(10).join(quest_lines)}

Based on quest names, dialogue volume, speaker pattern changes, and spot transitions,
find natural narrative break points to split this into parts.

Rules:
- Each part should be roughly 30K-60K tokens (but narrative flow > even size)
- Look for: story arc transitions, new major characters appearing, named sections
- "断章" = interlude/chapter break, "決戦" = decisive battle
- Speaker pattern changes often indicate new arcs

Respond as JSON:
{{"parts": [{{"part": 1, "start": 1, "end": N, "title_en": "...", "title_ja": "...", "key_characters": ["..."], "reason": "..."}}]}}"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a Fate/Grand Order story structure analyst. Output valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        max_completion_tokens=3000,
        response_format={"type": "json_object"},
    )

    usage = response.usage
    result = json.loads(response.choices[0].message.content)
    return result["parts"], usage


def ai_summarize(client, slug, chapter_name, dialogue_text, part_info=None):
    """Summarize dialogue text (full chapter or a part)."""
    if part_info:
        context = f"Part {part_info['part']}: {part_info['title_en']} ({part_info['title_ja']})"
        instruction = (
            f"Summarize this part of {chapter_name}. "
            "Write 1-3 paragraphs proportional to content length. "
            "Cover all key events, characters, and revelations in this section."
        )
    else:
        context = f"Full chapter: {chapter_name}"
        instruction = (
            f"Summarize the entire story of {chapter_name}. "
            "Write 2-4 paragraphs proportional to story complexity. "
            "Cover all key plot points from beginning to end."
        )

    prompt = f"""You are summarizing a Fate/Grand Order story chapter.
{context}

Dialogue:
{dialogue_text}

{instruction}

Respond as JSON:
{{
  "summary": "(story summary)",
  "key_characters": [{{"name": "...", "role": "brief role description"}}],
  "themes": ["theme1", "theme2"],
  "key_plot_points": ["point1", "point2"]
}}"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a Fate/Grand Order story analyst. Output valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        max_completion_tokens=MAX_COMPLETION,
        response_format={"type": "json_object"},
    )

    usage = response.usage
    result = json.loads(response.choices[0].message.content)
    return result, usage


def ai_synthesize(client, slug, chapter_name, part_summaries):
    """Synthesize part summaries into an overall chapter summary."""
    parts_text = []
    for ps in part_summaries:
        summary = ps.get('summary', ps.get('error', '(no summary available)'))
        parts_text.append(
            f"Part {ps['part']}: {ps['title_en']}\n"
            f"Characters: {', '.join(ps.get('key_characters_names', []))}\n"
            f"Summary: {summary}"
        )

    prompt = f"""You are creating an overall summary for {chapter_name} from its part summaries.

Part-by-part summaries:
{chr(10).join(parts_text)}

Write a comprehensive 2-4 paragraph summary that covers the entire chapter story arc.
Synthesize, don't just concatenate — create a flowing narrative.

Respond as JSON:
{{
  "summary": "(overall summary, 2-4 paragraphs)",
  "key_characters": [{{"name": "...", "role": "brief role description"}}],
  "themes": ["theme1", "theme2"],
  "key_plot_points": ["point1", "point2"]
}}"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a Fate/Grand Order story analyst. Output valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        max_completion_tokens=MAX_COMPLETION,
        response_format={"type": "json_object"},
    )

    usage = response.usage
    result = json.loads(response.choices[0].message.content)
    return result, usage


# ─── Main processing ───────────────────────────────────

def process_chapter(client, chapter_info, data, done_keys, dry_run=False):
    """Process one chapter: analyze → split if needed → summarize → save."""
    slug = chapter_info["slug"]
    chapter_name = data.get("name", slug)
    chapter_key = f"chapter:{slug}"

    if chapter_key in done_keys:
        log(f"  SKIP {slug} (already done)")
        return 0, 0, 0.0  # input_tok, output_tok, cost

    quests, total_tokens = analyze_chapter(data)

    if not quests:
        log(f"  SKIP {slug} (no quests)")
        return 0, 0, 0.0

    total_input = 0
    total_output = 0

    # Determine: one-shot or split
    if total_tokens < TOKEN_THRESHOLD:
        # ─── One-shot summary ───
        if dry_run:
            est_cost = calc_cost(total_tokens + 500, 1200)
            log(f"  {slug}: ONE-SHOT ~{total_tokens:,} tok → ~${est_cost:.4f}")
            return total_tokens + 500, 1200, est_cost

        log(f"  {slug}: ONE-SHOT ({total_tokens:,} tok)...", end=" ")
        t0 = time.time()
        dialogue = build_dialogue_text(data)
        result, usage = ai_summarize(client, slug, chapter_name, dialogue)
        elapsed = time.time() - t0
        total_input += usage.prompt_tokens
        total_output += usage.completion_tokens
        cost = calc_cost(total_input, total_output)

        # Save
        output = {
            "war_id": data.get("warId"),
            "slug": slug,
            "chapter_name": chapter_name,
            "model": MODEL,
            "total_tokens": total_tokens,
            "parts": None,
            **result,
        }
        save_json(output, OUTPUT_DIR / "by_chapter" / f"{slug}.json")
        save_checkpoint({"_key": chapter_key, "slug": slug, "type": "one_shot",
                         "cost": cost, "timestamp": datetime.now().isoformat()})

        log(f"OK ({elapsed:.1f}s, ${cost:.4f})")
        return total_input, total_output, cost

    else:
        # ─── Multi-part summary ───
        if dry_run:
            n_parts = max(2, total_tokens // 50_000)
            est_split = calc_cost(2000, 1500)
            est_parts = calc_cost(50_000, 1500) * n_parts
            est_synth = calc_cost(3000, 1500)
            est_total = est_split + est_parts + est_synth
            log(f"  {slug}: SPLIT ~{total_tokens:,} tok → ~{n_parts} parts → ~${est_total:.4f}")
            return total_tokens + 5000, 1500 * (n_parts + 2), est_total

        # Step 0: AI split analysis
        log(f"  {slug}: SPLIT ({total_tokens:,} tok)...")
        t0 = time.time()
        parts_plan, usage = ai_split_chapter(client, slug, chapter_name, quests, total_tokens)
        total_input += usage.prompt_tokens
        total_output += usage.completion_tokens

        # Validate split ranges (fix inverted ranges from AI)
        for part in parts_plan:
            if part["start"] > part["end"]:
                part["start"], part["end"] = part["end"], part["start"]

        log(f"Split → {len(parts_plan)} parts ({time.time()-t0:.1f}s)")

        # Step 1: Summarize each part
        part_summaries = []
        for part in parts_plan:
            part_key = f"part:{slug}:{part['part']}"
            if part_key in done_keys:
                # Load from saved file
                saved = load_json(OUTPUT_DIR / "by_chapter" / slug / f"part_{part['part']}.json")
                if saved:
                    part_summaries.append(saved)
                    log(f"Part {part['part']}: SKIP (cached)")
                    continue

            start_idx = part["start"] - 1
            end_idx = part["end"]
            part_quests = quests[start_idx:end_idx]
            part_quest_ids = {q["id"] for q in part_quests}
            part_tokens = sum(q["est_tokens"] for q in part_quests)

            dialogue = build_dialogue_text(data, quest_ids=part_quest_ids)

            t0 = time.time()
            result, usage = ai_summarize(client, slug, chapter_name, dialogue, part_info=part)
            elapsed = time.time() - t0
            total_input += usage.prompt_tokens
            total_output += usage.completion_tokens

            part_data = {
                "part": part["part"],
                "title_en": part["title_en"],
                "title_ja": part.get("title_ja", ""),
                "quests_range": f"{part['start']}-{part['end']}",
                "quest_names": [q["name"] for q in part_quests],
                "est_tokens": part_tokens,
                "key_characters_names": part.get("key_characters", []),
                **result,
            }
            part_summaries.append(part_data)

            # Save part
            save_json(part_data, OUTPUT_DIR / "by_chapter" / slug / f"part_{part['part']}.json")
            save_checkpoint({"_key": part_key, "slug": slug, "part": part["part"],
                             "timestamp": datetime.now().isoformat()})

            pcost = calc_cost(usage.prompt_tokens, usage.completion_tokens)
            log(f"Part {part['part']}: {part['title_en']} ({part_tokens:,} tok, {elapsed:.1f}s, ${pcost:.4f})")

        # Step 2: Synthesize
        t0 = time.time()
        synth_result, usage = ai_synthesize(client, slug, chapter_name, part_summaries)
        elapsed = time.time() - t0
        total_input += usage.prompt_tokens
        total_output += usage.completion_tokens
        log(f"Synthesis: ({elapsed:.1f}s)")

        # Save full chapter
        cost = calc_cost(total_input, total_output)
        output = {
            "war_id": data.get("warId"),
            "slug": slug,
            "chapter_name": chapter_name,
            "model": MODEL,
            "total_tokens": total_tokens,
            "parts": part_summaries,
            **synth_result,
        }
        save_json(output, OUTPUT_DIR / "by_chapter" / f"{slug}.json")
        save_checkpoint({"_key": chapter_key, "slug": slug, "type": "multi_part",
                         "n_parts": len(parts_plan), "cost": cost,
                         "timestamp": datetime.now().isoformat()})

        log(f"DONE ${cost:.4f}")
        return total_input, total_output, cost


# ─── CLI ────────────────────────────────────────────────

def show_stats():
    done = load_checkpoint()
    chapter_keys = {k for k in done if k.startswith("chapter:")}
    part_keys = {k for k in done if k.startswith("part:")}
    log(f"=== Summarization Progress ===")
    log(f"  Completed chapters: {len(chapter_keys)}")
    log(f"  Completed parts: {len(part_keys)}")
    log(f"  Checkpoint: {CHECKPOINT_FILE}")

    # List completed
    if chapter_keys:
        log(f"\n  Done:")
        for k in sorted(chapter_keys):
            log(f"{k}")

    # Check output files
    out_dir = OUTPUT_DIR / "by_chapter"
    if out_dir.exists():
        files = list(out_dir.glob("*.json"))
        log(f"\n  Output files: {len(files)} in {out_dir}")


def main():
    parser = argparse.ArgumentParser(description="FGO Story Summarizer")
    parser.add_argument("--chapter", type=str, help="Process single chapter (slug)")
    parser.add_argument("--main-only", action="store_true", help="Main story only")
    parser.add_argument("--events-only", action="store_true", help="Events only")
    parser.add_argument("--dry-run", action="store_true", help="Estimate cost only")
    parser.add_argument("--stats", action="store_true", help="Show progress")
    parser.add_argument("--test", type=int, help="Process N chapters only")
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    # Find chapters
    chapters = find_chapter_files(
        main_only=args.main_only,
        events_only=args.events_only,
        chapter_filter=args.chapter,
    )

    if args.test:
        chapters = chapters[:args.test]

    if not chapters:
        log("No chapters found to process.")
        return

    log(f"Found {len(chapters)} chapters to process")
    log(f"Model: {MODEL}")
    log(f"Output: {OUTPUT_DIR}")
    log()

    # Load checkpoint
    done_keys = load_checkpoint()
    if done_keys:
        chapter_done = sum(1 for k in done_keys if k.startswith("chapter:"))
        log(f"Checkpoint: {chapter_done} chapters already done")
        log()

    # Client
    client = None
    if not args.dry_run:
        client = get_openai_client()

    # Process
    grand_input = 0
    grand_output = 0
    grand_cost = 0.0
    processed = 0
    skipped = 0
    errors = []
    t_start = time.time()

    for i, ch in enumerate(chapters):
        slug = ch["slug"]
        data = load_json(ch["path"])
        if not data:
            log(f"  SKIP {slug} (no data)")
            skipped += 1
            continue

        # Skip empty
        has_quests = any(
            spot.get("quests") for spot in data.get("spots", [])
        )
        if not has_quests:
            skipped += 1
            continue

        try:
            inp, out, cost = process_chapter(client, ch, data, done_keys, dry_run=args.dry_run)
            grand_input += inp
            grand_output += out
            grand_cost += cost
            if cost > 0:
                processed += 1
        except Exception as e:
            errors.append((slug, str(e)))
            log(f"  ERROR {slug}: {e}")

    # Summary
    elapsed = time.time() - t_start
    log()
    log("=" * 60)
    log(f"{'DRY RUN ' if args.dry_run else ''}SUMMARY")
    log(f"  Processed: {processed}, Skipped: {skipped}, Errors: {len(errors)}")
    log(f"  Input tokens:  {grand_input:,}")
    log(f"  Output tokens: {grand_output:,}")
    log(f"  Total cost:    ${grand_cost:.2f}")
    log(f"  Time:          {elapsed:.0f}s")

    if errors:
        log(f"\n  Errors:")
        for slug, err in errors:
            log(f"{slug}: {err}")


if __name__ == "__main__":
    main()
