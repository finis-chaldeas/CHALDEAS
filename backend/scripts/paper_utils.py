"""
Shared utilities for loading and formatting academic papers from OpenAlex JSON exports.

Data source: C:/Projects/Chaldeas/data/compact_export/academic_papers/
Files: events_imp{3,4,5}_YYYYMMDD_HHMMSS.json

Used by:
  - create_shift.py (--enhance: inject paper context per page)
  - create_portal_article.py (--generate: inject paper context into outline + sections)
"""
import json
import re
from pathlib import Path

PAPER_DIR = Path("C:/Projects/Chaldeas/data/compact_export/academic_papers")

# Module-level cache
_paper_index: dict[int, list[dict]] | None = None

GRADE_ORDER = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'F': 4}


def load_paper_index(paper_dir: Path | str | None = None, min_grade: str = 'B') -> dict[int, list[dict]]:
    """
    Load JSON files and return {event_id: [paper, ...]} dict.

    - min_grade: 'A' or 'B' — only include papers at or above this grade
    - Uses the latest file per imp level (by filename date)
    - Merges across imp levels, deduplicates by openalex_id
    - Sorts by quality_score descending
    - Cached after first call
    """
    global _paper_index
    if _paper_index is not None:
        return _paper_index

    paper_path = Path(paper_dir) if paper_dir else PAPER_DIR
    if not paper_path.exists():
        print(f"  WARNING: Paper directory not found: {paper_path}")
        _paper_index = {}
        return _paper_index

    min_grade_val = GRADE_ORDER.get(min_grade, 1)

    # Find latest file per imp level
    latest_files: dict[str, Path] = {}
    for f in paper_path.glob("events_imp*_*.json"):
        # Skip test files
        if "_test_" in f.name:
            continue
        # Extract imp level: events_imp3_20260227_101952.json → "imp3"
        match = re.match(r'events_(imp\d+)_(\d{8}_\d{6})\.json', f.name)
        if not match:
            continue
        imp_key = match.group(1)
        date_str = match.group(2)
        if imp_key not in latest_files or date_str > latest_files[imp_key].stem.split('_', 1)[1]:
            latest_files[imp_key] = f

    if not latest_files:
        print(f"  WARNING: No paper JSON files found in {paper_path}")
        _paper_index = {}
        return _paper_index

    # Load and merge
    index: dict[int, dict[str, dict]] = {}  # event_id → {openalex_id → paper}

    for imp_key, fpath in sorted(latest_files.items()):
        try:
            data = json.loads(fpath.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError) as e:
            print(f"  WARNING: Failed to load {fpath.name}: {e}")
            continue

        results = data.get("results", [])
        for entry in results:
            event_id = entry.get("event_id")
            if not event_id:
                continue
            papers = entry.get("papers", [])
            if event_id not in index:
                index[event_id] = {}
            for p in papers:
                grade = p.get("quality_grade", "C")
                if GRADE_ORDER.get(grade, 4) > min_grade_val:
                    continue
                oa_id = p.get("openalex_id", "")
                if oa_id and oa_id not in index[event_id]:
                    index[event_id][oa_id] = p

    # Convert to sorted lists
    _paper_index = {}
    for event_id, papers_dict in index.items():
        papers_list = sorted(
            papers_dict.values(),
            key=lambda p: p.get("quality_score", 0),
            reverse=True,
        )
        if papers_list:
            _paper_index[event_id] = papers_list

    return _paper_index


def get_papers_for_events(event_ids: list[int], max_per_event: int = 3) -> dict[int, list[dict]]:
    """Get papers for multiple event IDs. Returns {event_id: [paper, ...]}."""
    idx = load_paper_index()
    result = {}
    for eid in event_ids:
        papers = idx.get(eid, [])
        if papers:
            result[eid] = papers[:max_per_event]
    return result


def format_papers_for_prompt(papers: list[dict], max_chars: int = 3000) -> str:
    """
    Format paper list into GPT prompt text.

    Format:
      [1] "Title" (Author, Year) — cited: N
          Abstract: first 400 chars...

    Truncates at max_chars.
    """
    if not papers:
        return "(No academic papers available for this event)"

    lines = []
    total_len = 0

    for i, p in enumerate(papers, 1):
        title = p.get("title", "Untitled")
        authors = p.get("authors", [])
        author_str = authors[0] if authors else "Unknown"
        if len(authors) > 1:
            author_str += " et al."
        year = p.get("year", "?")
        cited = p.get("cited_by_count", 0)
        abstract = (p.get("abstract") or "")[:400]
        if len(p.get("abstract") or "") > 400:
            abstract += "..."

        entry = f'[{i}] "{title}" ({author_str}, {year}) — cited: {cited}'
        if abstract:
            entry += f'\n    Abstract: {abstract}'

        if total_len + len(entry) > max_chars:
            break
        lines.append(entry)
        total_len += len(entry) + 1  # +1 for newline

    return "\n\n".join(lines)


def format_papers_as_sources(papers: list[dict]) -> list[str]:
    """
    Convert paper list to source strings for article sources field.

    Format: "Author (Year). Title. DOI or OA URL"
    """
    sources = []
    for p in papers:
        authors = p.get("authors", [])
        author_str = authors[0] if authors else "Unknown"
        if len(authors) > 1:
            author_str += " et al."
        year = p.get("year", "?")
        title = p.get("title", "Untitled")
        doi = p.get("doi", "")
        oa_url = p.get("oa_url", "")
        ref_url = doi or oa_url or ""

        source = f"{author_str} ({year}). {title}."
        if ref_url:
            source += f" {ref_url}"
        sources.append(source)
    return sources
