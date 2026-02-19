"""
Orphan Event Matcher - 출처 없는 이벤트를 Wikipedia에서 찾아 매칭

1. 출처 없는 이벤트 중 "진짜 같은 것" 추출
2. 로컬 Wikipedia ZIM에서 검색
3. wikidata_id 추출
4. 중복이면 병합, 아니면 업데이트
"""
import sys
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 프로젝트 경로
import os
SCRIPT_DIR = Path(__file__).parent.resolve()
BACKEND_PATH = SCRIPT_DIR.parent.parent.parent / "backend"
sys.path.insert(0, str(BACKEND_PATH))
os.chdir(BACKEND_PATH.parent)  # Change to project root for .env

from dotenv import load_dotenv
load_dotenv()

from libzim.reader import Archive
from sqlalchemy import text
from app.db.session import SessionLocal

# ZIM 파일
ZIM_PATH = Path("C:/Projects/Chaldeas/data/kiwix/wikipedia_en_nopic.zim")
_archive = None


def get_archive() -> Archive:
    global _archive
    if _archive is None:
        _archive = Archive(str(ZIM_PATH))
    return _archive


def get_article_html(title: str) -> Optional[str]:
    """Wikipedia 문서 HTML 가져오기"""
    zim = get_archive()

    # 제목 정규화
    normalized = title.replace(' ', '_')

    paths_to_try = [
        f"A/{normalized}",
        f"A/{title}",
        normalized,
        title,
    ]

    for path in paths_to_try:
        try:
            entry = zim.get_entry_by_path(path)
            if entry.is_redirect:
                entry = entry.get_redirect_entry()
            item = entry.get_item()
            return bytes(item.content).decode('utf-8')
        except (KeyError, RuntimeError):
            continue

    return None


def extract_wikidata_qid(html: str) -> Optional[str]:
    """HTML에서 Wikidata QID 추출"""
    match = re.search(r'wikidata\.org/wiki/(Q\d+)', html)
    return match.group(1) if match else None


def extract_wikipedia_url(html: str) -> Optional[str]:
    """HTML에서 canonical Wikipedia URL 추출"""
    match = re.search(r'<link rel="canonical" href="([^"]+)"', html)
    return match.group(1) if match else None


@dataclass
class MatchResult:
    event_id: int
    event_title: str
    wiki_found: bool
    wiki_qid: Optional[str] = None
    wiki_url: Optional[str] = None
    existing_event_id: Optional[int] = None  # 중복인 경우
    action: str = "none"  # none, update, merge


def match_event(event_id: int, event_title: str, db) -> MatchResult:
    """이벤트를 Wikipedia에서 찾기"""
    result = MatchResult(event_id=event_id, event_title=event_title, wiki_found=False)

    # Wikipedia에서 검색
    html = get_article_html(event_title)
    if not html:
        return result

    result.wiki_found = True
    result.wiki_qid = extract_wikidata_qid(html)
    result.wiki_url = extract_wikipedia_url(html)

    if not result.wiki_qid:
        return result

    # DB에서 같은 QID 가진 이벤트 있는지 확인
    existing = db.execute(text('''
        SELECT id, title FROM events
        WHERE wikidata_id = :qid AND id != :eid
    '''), {'qid': result.wiki_qid, 'eid': event_id}).fetchone()

    if existing:
        result.existing_event_id = existing[0]
        result.action = "merge"
    else:
        result.action = "update"

    return result


def run_matching(limit: int = 100, dry_run: bool = True):
    """출처 없는 이벤트 매칭 실행"""
    db = SessionLocal()

    try:
        # 1. 출처 없는 이벤트 중 "진짜 같은 것" 추출
        # - Battle of X, Siege of X, Treaty of X 등
        # - 인물 연결 있는 것 우선
        print("=== Orphan Event Matcher ===\n")

        events = db.execute(text('''
            SELECT e.id, e.title,
                   (SELECT COUNT(*) FROM event_persons ep WHERE ep.event_id = e.id) as person_count
            FROM events e
            WHERE e.wikidata_id IS NULL
              AND e.wikipedia_url IS NULL
              AND NOT EXISTS (SELECT 1 FROM event_sources es WHERE es.event_id = e.id)
              AND (
                  e.title LIKE 'Battle of %'
                  OR e.title LIKE 'Siege of %'
                  OR e.title LIKE 'Treaty of %'
                  OR e.title LIKE '% War'
                  OR e.title LIKE 'War of %'
                  OR e.title LIKE '% Revolution'
              )
            ORDER BY person_count DESC
            LIMIT :limit
        '''), {'limit': limit}).fetchall()

        print(f"Processing {len(events)} events...\n")

        stats = {"found": 0, "not_found": 0, "update": 0, "merge": 0}
        merge_candidates = []
        update_candidates = []

        for i, (eid, title, person_count) in enumerate(events):
            print(f"[{i+1}/{len(events)}] {title} (p={person_count})...", end=" ", flush=True)

            result = match_event(eid, title, db)

            if not result.wiki_found:
                print("NOT FOUND")
                stats["not_found"] += 1
            elif result.action == "merge":
                print(f"MERGE → #{result.existing_event_id} ({result.wiki_qid})")
                stats["merge"] += 1
                merge_candidates.append(result)
            elif result.action == "update":
                print(f"UPDATE ({result.wiki_qid})")
                stats["update"] += 1
                update_candidates.append(result)
            else:
                print(f"QID not found in Wikipedia")
                stats["found"] += 1

        # Summary
        print(f"\n=== Summary ===")
        print(f"Wikipedia found: {stats['found'] + stats['update'] + stats['merge']}")
        print(f"  - Update (new QID): {stats['update']}")
        print(f"  - Merge (duplicate): {stats['merge']}")
        print(f"Not found: {stats['not_found']}")

        if dry_run:
            print(f"\n[DRY RUN] No changes made.")
            print(f"\nTo apply changes, run with --apply")

            if merge_candidates:
                print(f"\n=== Merge Candidates ===")
                for m in merge_candidates[:20]:
                    print(f"  #{m.event_id} ({m.event_title}) → #{m.existing_event_id}")
        else:
            # Apply updates
            print(f"\n=== Applying Updates ===")

            for r in update_candidates:
                db.execute(text('''
                    UPDATE events
                    SET wikidata_id = :qid, wikipedia_url = :url
                    WHERE id = :id
                '''), {'qid': r.wiki_qid, 'url': r.wiki_url, 'id': r.event_id})
                print(f"  Updated #{r.event_id}: {r.wiki_qid}")

            db.commit()
            print(f"\nUpdated {len(update_candidates)} events.")

            if merge_candidates:
                print(f"\n=== Merge Candidates (manual review needed) ===")
                for m in merge_candidates:
                    print(f"  #{m.event_id} ({m.event_title}) → #{m.existing_event_id}")

    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Match orphan events to Wikipedia")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--apply", action="store_true", help="Actually apply changes")

    args = parser.parse_args()

    run_matching(limit=args.limit, dry_run=not args.apply)
