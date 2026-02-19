"""
Duplicate Event Merger - 중복 이벤트 병합

1. Wikipedia 매칭으로 중복 발견
2. 더 좋은 데이터 가진 쪽을 메인으로
3. 관계들 (persons, locations, parents 등) 이전
4. 중복 삭제
"""
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
import argparse

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
SCRIPT_DIR = Path(__file__).parent.resolve()
BACKEND_PATH = SCRIPT_DIR.parent.parent.parent / "backend"
sys.path.insert(0, str(BACKEND_PATH))
os.chdir(BACKEND_PATH.parent)

from dotenv import load_dotenv
load_dotenv()

from libzim.reader import Archive
from sqlalchemy import text
from app.db.session import SessionLocal
import re

# ZIM
ZIM_PATH = Path("C:/Projects/Chaldeas/data/kiwix/wikipedia_en_nopic.zim")
_archive = None


def get_archive() -> Archive:
    global _archive
    if _archive is None:
        _archive = Archive(str(ZIM_PATH))
    return _archive


def get_article_html(title: str) -> Optional[str]:
    zim = get_archive()
    normalized = title.replace(' ', '_')
    for path in [f"A/{normalized}", f"A/{title}", normalized, title]:
        try:
            entry = zim.get_entry_by_path(path)
            if entry.is_redirect:
                entry = entry.get_redirect_entry()
            return bytes(entry.get_item().content).decode('utf-8')
        except (KeyError, RuntimeError):
            continue
    return None


def extract_wikidata_qid(html: str) -> Optional[str]:
    match = re.search(r'wikidata\.org/wiki/(Q\d+)', html)
    return match.group(1) if match else None


def extract_wikipedia_url(html: str) -> Optional[str]:
    match = re.search(r'<link rel="canonical" href="([^"]+)"', html)
    return match.group(1) if match else None


@dataclass
class MergeCandidate:
    orphan_id: int
    orphan_title: str
    target_id: int
    target_title: str
    wikidata_id: str


@dataclass
class EventStats:
    id: int
    title: str
    wikidata_id: Optional[str]
    wikipedia_url: Optional[str]
    has_sources: bool
    person_count: int
    location_count: int
    parent_count: int


def get_event_stats(db, event_id: int) -> EventStats:
    """이벤트의 상세 통계"""
    row = db.execute(text('''
        SELECT e.id, e.title, e.wikidata_id, e.wikipedia_url,
               EXISTS(SELECT 1 FROM event_sources es WHERE es.event_id = e.id) as has_sources,
               (SELECT COUNT(*) FROM event_persons ep WHERE ep.event_id = e.id) as person_count,
               (SELECT COUNT(*) FROM event_locations el WHERE el.event_id = e.id) as location_count,
               (SELECT COUNT(*) FROM event_parents epa WHERE epa.event_id = e.id) as parent_count
        FROM events e WHERE e.id = :id
    '''), {'id': event_id}).fetchone()

    return EventStats(
        id=row[0], title=row[1], wikidata_id=row[2], wikipedia_url=row[3],
        has_sources=row[4], person_count=row[5], location_count=row[6], parent_count=row[7]
    )


def choose_main_event(stats1: EventStats, stats2: EventStats) -> tuple[EventStats, EventStats]:
    """어떤 이벤트를 메인으로 할지 결정 (main, duplicate 반환)"""
    def score(s: EventStats) -> int:
        score = 0
        if s.wikidata_id: score += 100
        if s.wikipedia_url: score += 50
        if s.has_sources: score += 200
        score += s.person_count
        score += s.location_count * 2
        score += s.parent_count * 5
        return score

    s1, s2 = score(stats1), score(stats2)
    if s1 >= s2:
        return stats1, stats2
    return stats2, stats1


def merge_events(db, main_id: int, dup_id: int, dry_run: bool = True) -> dict:
    """두 이벤트 병합 - main으로 dup의 관계들 이전 후 dup 삭제"""
    result = {
        "main_id": main_id,
        "dup_id": dup_id,
        "relations_moved": {},
        "success": False
    }

    try:
        # Start fresh
        db.rollback()
        # 1. event_persons 이전 (중복 방지)
        moved = db.execute(text('''
            UPDATE event_persons
            SET event_id = :main_id
            WHERE event_id = :dup_id
            AND person_id NOT IN (
                SELECT person_id FROM event_persons WHERE event_id = :main_id
            )
        '''), {'main_id': main_id, 'dup_id': dup_id}).rowcount
        result["relations_moved"]["event_persons"] = moved

        # 중복되는 것들 삭제
        db.execute(text('DELETE FROM event_persons WHERE event_id = :dup_id'), {'dup_id': dup_id})

        # 2. event_locations 이전
        moved = db.execute(text('''
            UPDATE event_locations
            SET event_id = :main_id
            WHERE event_id = :dup_id
            AND location_id NOT IN (
                SELECT location_id FROM event_locations WHERE event_id = :main_id
            )
        '''), {'main_id': main_id, 'dup_id': dup_id}).rowcount
        result["relations_moved"]["event_locations"] = moved

        db.execute(text('DELETE FROM event_locations WHERE event_id = :dup_id'), {'dup_id': dup_id})

        # 3. event_parents 이전 (dup이 자식인 경우)
        moved = db.execute(text('''
            UPDATE event_parents
            SET event_id = :main_id
            WHERE event_id = :dup_id
            AND parent_event_id NOT IN (
                SELECT parent_event_id FROM event_parents WHERE event_id = :main_id
            )
        '''), {'main_id': main_id, 'dup_id': dup_id}).rowcount
        result["relations_moved"]["event_parents_as_child"] = moved

        db.execute(text('DELETE FROM event_parents WHERE event_id = :dup_id'), {'dup_id': dup_id})

        # 4. event_parents 이전 (dup이 부모인 경우)
        moved = db.execute(text('''
            UPDATE event_parents
            SET parent_event_id = :main_id
            WHERE parent_event_id = :dup_id
        '''), {'main_id': main_id, 'dup_id': dup_id}).rowcount
        result["relations_moved"]["event_parents_as_parent"] = moved

        # 5. event_sources 이전
        moved = db.execute(text('''
            UPDATE event_sources
            SET event_id = :main_id
            WHERE event_id = :dup_id
            AND source_id NOT IN (
                SELECT source_id FROM event_sources WHERE event_id = :main_id
            )
        '''), {'main_id': main_id, 'dup_id': dup_id}).rowcount
        result["relations_moved"]["event_sources"] = moved

        db.execute(text('DELETE FROM event_sources WHERE event_id = :dup_id'), {'dup_id': dup_id})

        # 6. event_relationships 이전 (양방향)
        # dup이 from인 경우
        moved1 = db.execute(text('''
            UPDATE event_relationships
            SET from_event_id = :main_id
            WHERE from_event_id = :dup_id
            AND NOT EXISTS (
                SELECT 1 FROM event_relationships er2
                WHERE er2.from_event_id = :main_id AND er2.to_event_id = event_relationships.to_event_id
            )
        '''), {'main_id': main_id, 'dup_id': dup_id}).rowcount

        # dup이 to인 경우
        moved2 = db.execute(text('''
            UPDATE event_relationships
            SET to_event_id = :main_id
            WHERE to_event_id = :dup_id
            AND NOT EXISTS (
                SELECT 1 FROM event_relationships er2
                WHERE er2.to_event_id = :main_id AND er2.from_event_id = event_relationships.from_event_id
            )
        '''), {'main_id': main_id, 'dup_id': dup_id}).rowcount
        result["relations_moved"]["event_relationships"] = moved1 + moved2

        db.execute(text('DELETE FROM event_relationships WHERE from_event_id = :dup_id OR to_event_id = :dup_id'), {'dup_id': dup_id})

        # 7. text_mentions 이전
        moved = db.execute(text('''
            UPDATE text_mentions
            SET entity_id = :main_id
            WHERE entity_type = 'event' AND entity_id = :dup_id
        '''), {'main_id': main_id, 'dup_id': dup_id}).rowcount
        result["relations_moved"]["text_mentions"] = moved

        # 8. events.parent_event_id 이전 (dup을 부모로 가진 이벤트들)
        moved = db.execute(text('''
            UPDATE events
            SET parent_event_id = :main_id
            WHERE parent_event_id = :dup_id
        '''), {'main_id': main_id, 'dup_id': dup_id}).rowcount
        result["relations_moved"]["children_reparented"] = moved

        # 9. 마지막으로 dup 이벤트 삭제
        db.execute(text('DELETE FROM events WHERE id = :dup_id'), {'dup_id': dup_id})

        result["success"] = True

    except Exception as e:
        result["error"] = str(e)[:200]
        db.rollback()

    return result


def find_and_merge(limit: int = 100, dry_run: bool = True):
    """출처 없는 이벤트 찾아서 Wikipedia 매칭 후 병합"""
    db = SessionLocal()

    try:
        print("=== Duplicate Event Merger ===\n")

        # 1. 출처 없는 "진짜 같은" 이벤트 추출
        events = db.execute(text('''
            SELECT e.id, e.title,
                   (SELECT COUNT(*) FROM event_persons ep WHERE ep.event_id = e.id) as person_count
            FROM events e
            WHERE e.wikidata_id IS NULL
              AND e.wikipedia_url IS NULL
              AND NOT EXISTS (SELECT 1 FROM event_sources es WHERE es.event_id = e.id)
              AND (
                  e.title LIKE 'Battle of %%'
                  OR e.title LIKE 'Siege of %%'
                  OR e.title LIKE 'Treaty of %%'
                  OR e.title LIKE '%% War'
                  OR e.title LIKE 'War of %%'
                  OR e.title LIKE '%% Revolution'
              )
            ORDER BY person_count DESC
            LIMIT :limit
        '''), {'limit': limit}).fetchall()

        print(f"Scanning {len(events)} orphan events...\n")

        merge_candidates: List[MergeCandidate] = []
        update_candidates = []

        for eid, title, _ in events:
            html = get_article_html(title)
            if not html:
                continue

            qid = extract_wikidata_qid(html)
            if not qid:
                continue

            # DB에서 같은 QID 가진 이벤트 찾기
            existing = db.execute(text('''
                SELECT id, title FROM events
                WHERE wikidata_id = :qid AND id != :eid
            '''), {'qid': qid, 'eid': eid}).fetchone()

            if existing:
                merge_candidates.append(MergeCandidate(
                    orphan_id=eid, orphan_title=title,
                    target_id=existing[0], target_title=existing[1],
                    wikidata_id=qid
                ))
            else:
                wiki_url = extract_wikipedia_url(html)
                update_candidates.append({
                    'id': eid, 'title': title, 'qid': qid, 'url': wiki_url
                })

        print(f"Found {len(merge_candidates)} duplicates to merge")
        print(f"Found {len(update_candidates)} new events to update\n")

        # 2. 병합 실행
        if merge_candidates:
            print("=== Merging Duplicates ===\n")

            merged = 0
            for mc in merge_candidates:
                # 어떤 걸 메인으로 할지 결정
                stats_orphan = get_event_stats(db, mc.orphan_id)
                stats_target = get_event_stats(db, mc.target_id)
                main, dup = choose_main_event(stats_orphan, stats_target)

                print(f"[{mc.wikidata_id}] {mc.orphan_title}")
                print(f"  Main: #{main.id} ({main.title}) - p:{main.person_count} l:{main.location_count} src:{main.has_sources}")
                print(f"  Dup:  #{dup.id} ({dup.title}) - p:{dup.person_count} l:{dup.location_count} src:{dup.has_sources}")

                if dry_run:
                    print(f"  → [DRY RUN] Would merge #{dup.id} into #{main.id}")
                else:
                    result = merge_events(db, main.id, dup.id, dry_run=False)
                    if result["success"]:
                        print(f"  → Merged! Moved: {result['relations_moved']}")
                        merged += 1
                    else:
                        print(f"  → ERROR: {result.get('error', 'unknown')}")
                print()

            if not dry_run:
                db.commit()
                print(f"\nMerged {merged} duplicate events.")

        # 3. 새 이벤트 업데이트
        if update_candidates:
            print("\n=== Updating New Events ===\n")

            for uc in update_candidates:
                print(f"[{uc['qid']}] {uc['title']}")

                if dry_run:
                    print(f"  → [DRY RUN] Would update with QID")
                else:
                    db.execute(text('''
                        UPDATE events SET wikidata_id = :qid, wikipedia_url = :url
                        WHERE id = :id
                    '''), {'qid': uc['qid'], 'url': uc['url'], 'id': uc['id']})
                    print(f"  → Updated")

            if not dry_run:
                db.commit()
                print(f"\nUpdated {len(update_candidates)} events.")

        # Summary
        print("\n" + "="*50)
        if dry_run:
            print("[DRY RUN] No changes made.")
            print("Run with --apply to execute changes.")
        else:
            print("DONE!")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge duplicate events")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--apply", action="store_true", help="Actually apply changes")

    args = parser.parse_args()
    find_and_merge(limit=args.limit, dry_run=not args.apply)
