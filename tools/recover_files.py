"""
Recovery script: Extracts frontend file contents from Claude Code JSONL session logs.

After a `git checkout -- frontend/` wiped modified frontend files, this script
replays all Write and Edit tool calls from the session logs to reconstruct
the final state of each file.

Strategy:
1. Parse JSONL files in chronological order (by modification time)
2. For each session, collect ALL tool operations in order:
   - Read tool calls + their results (to understand what was on disk at that time)
   - Write tool calls (full file replacement)
   - Edit tool calls (incremental old_string -> new_string patches)
3. Build file state by replaying operations:
   - Write: set full content
   - Edit: if file not yet in state, load from disk (committed version) as baseline
   - Read results help validate but disk baseline is authoritative for Edit-only files
4. Detect and skip Read error results (file too large, etc.)
5. Write recovered files to C:/Projects/Chaldeas/recovered/

Usage:
    python tools/recover_files.py
"""

import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

# Ensure UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── Configuration ──────────────────────────────────────────────────────────

PROJECT_ROOT = Path("C:/Projects/Chaldeas")
RECOVERED_DIR = PROJECT_ROOT / "recovered"

JSONL_DIR = Path("C:/Users/ryuti/.claude/projects/C--Projects-Chaldeas")

JSONL_FILES = [
    JSONL_DIR / "5a89d307-85c8-4e50-b6ca-041cb760987a.jsonl",
    JSONL_DIR / "984a4d83-b062-43aa-80f5-c3aa9b0a0fb7.jsonl",
    JSONL_DIR / "bc4f85f4-f576-4a40-a773-4564f33618fd.jsonl",
    JSONL_DIR / "2c8980b5-3dea-4129-acf9-e8f70711d979.jsonl",
    JSONL_DIR / "a7f7efb8-e22c-4217-8bd0-1817e7695a62.jsonl",
    JSONL_DIR / "f95ec50b-1bcf-405d-beef-3d538c79f8a1.jsonl",
    JSONL_DIR / "7bcf85cd-ddbf-469a-9a6c-b69b48fac83c.jsonl",
]

# Target files to recover (relative to project root)
TARGET_FILES = [
    "frontend/src/App.tsx",
    "frontend/src/api/client.ts",
    "frontend/src/components/detail/EventDetailPanel.tsx",
    "frontend/src/components/landing/FeaturedPersons.tsx",
    "frontend/src/components/landing/Landing.css",
    "frontend/src/components/navigator/Navigator.tsx",
    "frontend/src/components/navigator/PeriodDetailPanel.tsx",
    "frontend/src/components/navigator/PersonTab.tsx",
    "frontend/src/components/navigator/navigator.css",
    "frontend/src/store/settingsStore.ts",
    "frontend/src/store/globeStore.ts",
    "frontend/src/styles/globals.css",
    "frontend/src/types/index.ts",
    "frontend/tailwind.config.js",
    "frontend/src/components/globe/CameraModeToggle.tsx",
    "frontend/src/components/globe/GlobeContainer.tsx",
    "frontend/src/components/globe/GlobeHeatmap.css",
    "frontend/src/components/map/MapContainer.tsx",
    "frontend/src/components/navigator/EraTab.tsx",
    "frontend/src/components/search/SearchAutocomplete.tsx",
    "frontend/src/components/showcase/ShowcaseModal.tsx",
    "frontend/src/components/showcase/showcase.css",
]

# Read error messages that should be detected and skipped
READ_ERROR_PATTERNS = [
    "File content",
    "exceeds maximum allowed tokens",
    "Please use offset and limit parameters",
]


def normalize_path(file_path: str) -> str:
    """Normalize a file path to use forward slashes and be relative to project root."""
    p = file_path.replace("\\", "/")
    root_variants = [
        "C:/Projects/Chaldeas/",
        "c:/Projects/Chaldeas/",
        "C:/projects/chaldeas/",
    ]
    for root in root_variants:
        if p.startswith(root):
            p = p[len(root):]
            break
    if p.startswith("Projects/Chaldeas/"):
        p = p[len("Projects/Chaldeas/"):]
    return p


def is_read_error(content: str) -> bool:
    """Check if a Read tool result is an error message rather than file content."""
    if not content or len(content) < 300:
        # Short content could be an error
        for pattern in READ_ERROR_PATTERNS:
            if pattern in content:
                return True
    return False


def parse_read_content(raw_content: str) -> str:
    """Parse the cat -n formatted Read tool output back to raw file content.

    The format is: spaces + line_number + separator_char + actual_content
    The separator appears to be a special unicode character in the JSONL.
    """
    if is_read_error(raw_content):
        return None

    lines = raw_content.split("\n")
    result_lines = []
    for line in lines:
        # Match: optional whitespace, digits, then a non-alnum separator, then content
        # The separator in JSONL is typically a tab or special unicode char
        m = re.match(r'^\s*\d+\t(.*)$', line)
        if m:
            result_lines.append(m.group(1))
            continue
        # Try unicode separator (the \uf0de chars seen in previews)
        m = re.match(r'^\s*\d+[\uf0de\ufffd]+(.*)$', line)
        if m:
            result_lines.append(m.group(1))
            continue
        # Generic: strip "spaces + digits + one non-alnum char"
        m = re.match(r'^\s*(\d+)([^\w\d])(.*)$', line)
        if m:
            result_lines.append(m.group(3))
            continue
        # No match - keep as is (empty lines, etc.)
        result_lines.append(line)

    content = "\n".join(result_lines)

    # Validate: if the parsed content looks like it still has line numbers everywhere,
    # something went wrong
    if content and all(re.match(r'^\s*\d+\s', l) for l in content.split("\n")[:10] if l.strip()):
        return None  # Parsing failed

    return content


def apply_edit(content: str, old_string: str, new_string: str, replace_all: bool = False) -> tuple[str, bool]:
    """Apply an Edit operation. Returns (new_content, success)."""
    if not old_string:
        return content, False

    if replace_all:
        if old_string in content:
            return content.replace(old_string, new_string), True
        # Try with normalized line endings
        content_norm = content.replace("\r\n", "\n")
        old_norm = old_string.replace("\r\n", "\n")
        if old_norm in content_norm:
            return content_norm.replace(old_norm, new_string), True
        return content, False

    # Single replacement
    idx = content.find(old_string)
    if idx != -1:
        return content[:idx] + new_string + content[idx + len(old_string):], True

    # Try with normalized line endings
    content_norm = content.replace("\r\n", "\n")
    old_norm = old_string.replace("\r\n", "\n")
    idx = content_norm.find(old_norm)
    if idx != -1:
        return content_norm[:idx] + new_string + content_norm[idx + len(old_norm):], True

    # Try stripping trailing whitespace on each line (whitespace-insensitive match)
    content_stripped = "\n".join(l.rstrip() for l in content.split("\n"))
    old_stripped = "\n".join(l.rstrip() for l in old_string.split("\n"))
    idx = content_stripped.find(old_stripped)
    if idx != -1:
        return content_stripped[:idx] + new_string + content_stripped[idx + len(old_stripped):], True

    return content, False


def load_disk_baseline(norm_path: str) -> str | None:
    """Load the current disk version of a file (committed/reverted state)."""
    disk_path = PROJECT_ROOT / norm_path
    if disk_path.exists():
        try:
            return disk_path.read_text(encoding="utf-8")
        except Exception:
            pass
    return None


def collect_all_operations(jsonl_files: list[Path]) -> list[dict]:
    """Parse all JSONL files and collect frontend Write/Edit operations in chronological order.

    Also collects Read tool_use IDs and their results to provide baselines.

    Returns a list of operation dicts in chronological order across all sessions.
    """
    all_ops = []

    # Sort by modification time
    sorted_files = sorted(jsonl_files, key=lambda p: os.path.getmtime(p))

    for jsonl_path in sorted_files:
        session_name = jsonl_path.stem[:8]
        mt = datetime.fromtimestamp(os.path.getmtime(jsonl_path))
        print(f"\n  Scanning: {jsonl_path.name} ({mt.strftime('%H:%M:%S')})")

        pending_reads = {}  # tool_use_id -> normalized_path
        pending_edits = {}  # tool_use_id -> index in session_ops
        session_ops = []

        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line_text in f:
                try:
                    obj = json.loads(line_text)
                except (json.JSONDecodeError, ValueError):
                    continue

                msg_type = obj.get("type", "")
                message = obj.get("message", {})
                content = message.get("content", [])

                if not isinstance(content, list):
                    continue

                if msg_type == "assistant":
                    for block in content:
                        if not isinstance(block, dict) or block.get("type") != "tool_use":
                            continue
                        name = block.get("name", "")
                        inp = block.get("input", {})
                        tool_id = block.get("id", "")

                        if name == "Read":
                            fp = inp.get("file_path", "")
                            norm = normalize_path(fp)
                            if norm.startswith("frontend/"):
                                pending_reads[tool_id] = norm

                        elif name == "Write":
                            fp = inp.get("file_path", "")
                            file_content = inp.get("content", "")
                            norm = normalize_path(fp)
                            if norm.startswith("frontend/"):
                                session_ops.append({
                                    "type": "write",
                                    "path": norm,
                                    "content": file_content,
                                    "session": session_name,
                                    "tool_id": tool_id,
                                })

                        elif name == "Edit":
                            fp = inp.get("file_path", "")
                            norm = normalize_path(fp)
                            if norm.startswith("frontend/"):
                                op_idx = len(session_ops)
                                session_ops.append({
                                    "type": "edit",
                                    "path": norm,
                                    "old_string": inp.get("old_string", ""),
                                    "new_string": inp.get("new_string", ""),
                                    "replace_all": inp.get("replace_all", False),
                                    "session": session_name,
                                    "tool_id": tool_id,
                                    "originally_failed": False,  # default, may be updated
                                })
                                pending_edits[tool_id] = op_idx

                elif msg_type == "user":
                    for block in content:
                        if not isinstance(block, dict) or block.get("type") != "tool_result":
                            continue
                        tool_use_id = block.get("tool_use_id", "")

                        # Check if this is a result for an Edit tool call
                        if tool_use_id in pending_edits:
                            result_content = block.get("content", "")
                            raw = result_content if isinstance(result_content, str) else ""
                            is_error = ("tool_use_error" in raw or
                                        "not found" in raw.lower() or
                                        "not unique" in raw.lower() or
                                        "has not been read" in raw.lower())
                            if is_error:
                                op_idx = pending_edits[tool_use_id]
                                session_ops[op_idx]["originally_failed"] = True

                        # Check if this is a result for a Read tool call
                        if tool_use_id not in pending_reads:
                            continue

                        norm = pending_reads[tool_use_id]
                        result_content = block.get("content", "")

                        raw_text = None
                        if isinstance(result_content, str):
                            raw_text = result_content
                        elif isinstance(result_content, list):
                            for sub in result_content:
                                if isinstance(sub, dict) and sub.get("type") == "text":
                                    raw_text = sub.get("text", "")
                                    break

                        if raw_text and not is_read_error(raw_text):
                            parsed = parse_read_content(raw_text)
                            if parsed is not None:
                                session_ops.append({
                                    "type": "read_result",
                                    "path": norm,
                                    "content": parsed,
                                    "session": session_name,
                                })

        # Count ops per file in this session
        file_op_counts = {}
        for op in session_ops:
            key = f"{op['type']}:{op['path']}"
            file_op_counts[op['path']] = file_op_counts.get(op['path'], 0) + 1

        for path, count in sorted(file_op_counts.items()):
            types = [op['type'] for op in session_ops if op['path'] == path]
            type_summary = {}
            for t in types:
                type_summary[t] = type_summary.get(t, 0) + 1
            summary = ", ".join(f"{t}:{c}" for t, c in type_summary.items())
            print(f"    {path}: {summary}")

        all_ops.extend(session_ops)

    return all_ops


def replay_operations(all_ops: list[dict]) -> dict[str, str]:
    """Replay all operations to build final file states.

    Key insight: Each session operated on the disk state at its time.
    Since sessions ran sequentially, earlier sessions' writes/edits modified
    the disk, and later sessions read that modified state.

    For files that were only Read+Edit (never Written), we need to start
    from the disk baseline (committed version, now restored by git checkout)
    and apply all edits. But the edits from each session were made against
    the state that included all prior sessions' modifications.

    Strategy:
    - Process operations in order
    - Read results validate what the file looked like at that point
    - Write operations set the full content
    - Edit operations patch the current state
    - If an Edit is the first operation on a file, load from disk as baseline
    """
    file_states = {}
    stats = {"writes": 0, "edits": 0, "edit_failures": 0, "reads_used": 0}

    # Track which files have been modified (write/edit) within each session.
    # When a Read comes from a new session for a file, it reflects the actual
    # disk state at that time and should update the baseline.
    session_modified = {}  # (session, path) -> bool

    for op in all_ops:
        path = op["path"]
        op_type = op["type"]
        session = op["session"]
        session_key = (session, path)

        if op_type == "read_result":
            read_content = op["content"]
            disk_content = load_disk_baseline(path)

            # Detect partial reads: if disk file is much larger, read was truncated
            is_partial = (disk_content is not None and
                          len(disk_content) > len(read_content) * 2)

            # Only update baseline if this file hasn't been modified in this session yet
            already_modified_this_session = session_modified.get(session_key, False)

            if already_modified_this_session:
                # This Read comes after edits in the same session - it's just
                # re-reading the already modified file. Skip it.
                pass
            elif is_partial:
                if path not in file_states:
                    # No state yet and read is partial - use disk as baseline
                    file_states[path] = disk_content
                    stats["reads_used"] += 1
                    print(f"    READ partial ({len(read_content)} chars), "
                          f"using disk ({len(disk_content)} chars): {path}")
                # else: keep existing state from prior sessions
            else:
                # Full read from a new session - this reflects the actual disk
                # state which may include prior sessions' modifications.
                # Always update (this is authoritative for this session).
                file_states[path] = read_content
                stats["reads_used"] += 1

        elif op_type == "write":
            file_states[path] = op["content"]
            stats["writes"] += 1
            session_modified[session_key] = True

        elif op_type == "edit":
            # Skip edits that failed in the original session
            if op.get("originally_failed", False):
                stats["edit_failures"] += 1
                print(f"    SKIP (originally failed) [{session}] {path}")
                continue

            # Need existing content to apply edit
            if path not in file_states:
                # Load from disk (committed version)
                disk_content = load_disk_baseline(path)
                if disk_content is not None:
                    file_states[path] = disk_content
                    print(f"    BASELINE (disk): {path} ({len(disk_content)} chars)")
                else:
                    print(f"    WARNING: No baseline for {path}, skipping edit")
                    stats["edit_failures"] += 1
                    continue

            old_content = file_states[path]
            new_content, success = apply_edit(
                old_content,
                op["old_string"],
                op["new_string"],
                op.get("replace_all", False),
            )
            if success:
                file_states[path] = new_content
                stats["edits"] += 1
                session_modified[session_key] = True
            else:
                # Fallback: try to find where in the file the edit should go
                # by looking for a unique prefix of old_string
                old_str = op["old_string"]
                new_str = op["new_string"]
                fallback_applied = False

                # Try progressively shorter prefixes of old_string
                for prefix_len in [60, 40, 25]:
                    if prefix_len >= len(old_str):
                        continue
                    prefix = old_str[:prefix_len]
                    idx = old_content.find(prefix)
                    if idx != -1:
                        # Found the prefix - try to determine the extent to replace
                        # Count newlines in old_string to estimate where it ends
                        old_lines = old_str.count("\n")
                        # Find the end position by counting the same number of newlines
                        end_idx = idx
                        nl_count = 0
                        while end_idx < len(old_content) and nl_count <= old_lines:
                            if old_content[end_idx] == "\n":
                                nl_count += 1
                            end_idx += 1
                        # Apply the replacement
                        file_states[path] = old_content[:idx] + new_str + old_content[end_idx:]
                        stats["edits"] += 1
                        session_modified[session_key] = True
                        fallback_applied = True
                        print(f"    EDIT FALLBACK [{session}] {path}: "
                              f"prefix match at {idx}, replaced {end_idx - idx} chars")
                        break

                if not fallback_applied:
                    stats["edit_failures"] += 1
                    print(f"    EDIT FAIL [{session}] {path}: old_string not found "
                          f"(len={len(old_str)}, preview='{old_str[:60]}...')")

    return file_states, stats


def main():
    print("=" * 70)
    print("CHALDEAS Frontend File Recovery")
    print("=" * 70)

    # Phase 1: Collect all operations from JSONL files
    print("\nPhase 1: Collecting operations from JSONL files...")
    all_ops = collect_all_operations(JSONL_FILES)

    frontend_ops = [op for op in all_ops if op["path"].startswith("frontend/")]
    print(f"\nTotal frontend operations collected: {len(frontend_ops)}")

    # Phase 2: Replay operations to build file states
    print("\nPhase 2: Replaying operations...")
    file_states, stats = replay_operations(all_ops)

    print(f"\nReplay stats: {stats['writes']} writes, {stats['edits']} edits, "
          f"{stats['reads_used']} read baselines, {stats['edit_failures']} edit failures")

    # Phase 3: Write recovered files
    print("\n" + "=" * 70)
    print("Phase 3: Writing recovered files")
    print("=" * 70)

    recovered_count = 0
    not_found = []
    unchanged = []

    print(f"\nTarget files ({len(TARGET_FILES)}):")
    for target in TARGET_FILES:
        if target in file_states:
            content = file_states[target]

            # Check if recovered content differs from disk
            disk_content = load_disk_baseline(target)
            if disk_content is not None and content == disk_content:
                unchanged.append(target)
                status = "UNCHANGED"
            else:
                status = "RECOVERED"

            out_path = RECOVERED_DIR / target
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
            recovered_count += 1

            disk_size = len(disk_content) if disk_content else 0
            delta = len(content) - disk_size
            print(f"  [{status}] {target} ({len(content)} chars, delta={delta:+d})")
        else:
            not_found.append(target)
            print(f"  [MISSING] {target}")

    # Also write any other frontend files we found
    other_frontend = [k for k in file_states if k.startswith("frontend/") and k not in TARGET_FILES]
    if other_frontend:
        print(f"\nAdditional frontend files found ({len(other_frontend)}):")
        for path in sorted(other_frontend):
            content = file_states[path]
            out_path = RECOVERED_DIR / path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
            print(f"  [BONUS] {path} ({len(content)} chars)")

    print(f"\n{'=' * 70}")
    print(f"FINAL SUMMARY")
    print(f"{'=' * 70}")
    print(f"Recovered: {recovered_count}/{len(TARGET_FILES)} target files")
    if unchanged:
        print(f"Unchanged from disk: {len(unchanged)} files (no modifications found)")
        for uf in unchanged:
            print(f"  - {uf}")
    if not_found:
        print(f"Missing: {len(not_found)} files")
        for nf in not_found:
            print(f"  - {nf}")
    print(f"Output directory: {RECOVERED_DIR}")
    print(f"{'=' * 70}")

    return 0 if not not_found else 1


if __name__ == "__main__":
    sys.exit(main())
