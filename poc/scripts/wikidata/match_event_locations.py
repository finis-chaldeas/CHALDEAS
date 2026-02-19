"""
이벤트 → 가장 가까운 기존 로케이션 매칭 스크립트

원칙:
  1. locations = 노드. 기존 12,908개 로케이션이 고정 노드
  2. 이미 primary_location_id 있는 이벤트 → 보존
  3. Wikidata 로컬 덤프에서 좌표 추출 (P625 직접 / P276 간접)
  4. 전체 locations 노드에서 가장 가까운 노드로 링크
  5. 새 노드 추가 시 기존 인근 노드의 이벤트 재분배 체크

방법:
  - E:\\wikidata\\latest-all.json (1.8TB) 스트리밍 스캔
  - QID 빠른 매칭 (JSON 파싱 없이 23,857개 set lookup)
  - numpy 벡터화 haversine 최근접 검색
  - 체크포인트 지원 (중단/재시작)

Usage:
    python match_event_locations.py --scan           # Phase 1: 덤프 스캔 → 좌표 추출
    python match_event_locations.py --scan --resume   # 중단된 스캔 재시작
    python match_event_locations.py --match           # Phase 2: 좌표 → 최근접 노드 매칭
    python match_event_locations.py --match --dry-run # 매칭 dry-run
    python match_event_locations.py --stats           # 현황 확인
"""

import os
import sys
import re
import time
import json
import argparse
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

# Windows UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'chaldeas',
    'user': 'chaldeas',
    'password': 'chaldeas_dev'
}

DUMP_PATH = r'E:\wikidata\latest-all.json'
CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'wikidata')
CHECKPOINT_FILE = os.path.join(CHECKPOINT_DIR, 'event_coords_checkpoint.json')
COORDS_FILE = os.path.join(CHECKPOINT_DIR, 'event_coords.json')

# QID 빠른 추출 패턴 (라인 시작 부분에서)
QID_PATTERN = re.compile(rb'"id"\s*:\s*"(Q\d+)"')


def extract_qid_fast(line: bytes) -> Optional[str]:
    """라인에서 QID 빠르게 추출 (첫 200바이트만 검색)."""
    m = QID_PATTERN.search(line[:200])
    if m:
        return m.group(1).decode('ascii')
    return None


def extract_p625(claims: dict) -> Optional[Tuple[float, float]]:
    """P625 (coordinate location) 추출."""
    for claim in claims.get('P625', []):
        mainsnak = claim.get('mainsnak', {})
        dv = mainsnak.get('datavalue', {})
        if dv.get('type') == 'globecoordinate':
            val = dv.get('value', {})
            lat = val.get('latitude')
            lng = val.get('longitude')
            if lat is not None and lng is not None:
                return (lat, lng)
    return None


def extract_p276(claims: dict) -> Optional[str]:
    """P276 (location) QID 추출."""
    for claim in claims.get('P276', []):
        mainsnak = claim.get('mainsnak', {})
        dv = mainsnak.get('datavalue', {})
        if dv.get('type') == 'wikibase-entityid':
            return dv.get('value', {}).get('id')
    return None


def extract_p17(claims: dict) -> Optional[str]:
    """P17 (country) QID 추출."""
    for claim in claims.get('P17', []):
        mainsnak = claim.get('mainsnak', {})
        dv = mainsnak.get('datavalue', {})
        if dv.get('type') == 'wikibase-entityid':
            return dv.get('value', {}).get('id')
    return None


def phase_scan(resume: bool = False):
    """Phase 1: Wikidata 덤프 스캔 → 이벤트 좌표 추출."""

    print("=" * 60)
    print("  Phase 1: Wikidata 덤프 스캔")
    print("=" * 60)

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    # DB에서 필요한 QID 목록 로드
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT id, title, wikidata_id
        FROM events
        WHERE wikidata_id IS NOT NULL
          AND primary_location_id IS NULL
        ORDER BY id
    """)
    events = cur.fetchall()
    event_qid_map = {e['wikidata_id']: e for e in events}  # QID → event

    # 기존 로케이션의 wikidata_id도 필요 (P276 직접 매칭용)
    cur.execute("SELECT id, wikidata_id FROM locations WHERE wikidata_id IS NOT NULL")
    loc_qid_map = {r['wikidata_id']: r['id'] for r in cur.fetchall()}

    cur.execute("SELECT COUNT(*) as cnt FROM events WHERE primary_location_id IS NOT NULL")
    already_linked = cur.fetchone()['cnt']

    conn.close()

    event_qids: Set[str] = set(event_qid_map.keys())

    print(f"  이미 위치 연결됨: {already_linked} (보존)")
    print(f"  위치 필요 이벤트: {len(event_qids)}")
    print(f"  기존 로케이션: {len(loc_qid_map)}")
    print(f"  덤프 경로: {DUMP_PATH}")

    # 체크포인트 로드
    coords = {}  # QID → {lat, lng, source, location_qid}
    p276_needed: Dict[str, List[str]] = {}  # location_qid → [event_qids that need it]
    bytes_read = 0
    lines_read = 0

    if resume and os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            checkpoint = json.load(f)
        coords = checkpoint.get('coords', {})
        p276_needed = checkpoint.get('p276_needed', {})
        bytes_read = checkpoint.get('bytes_read', 0)
        lines_read = checkpoint.get('lines_read', 0)
        print(f"  체크포인트 로드: {len(coords)} coords, {bytes_read/1e9:.1f}GB 스캔됨")

    # 아직 찾지 못한 QID들
    remaining_event_qids = event_qids - set(coords.keys()) - {
        eq for eqs in p276_needed.values() for eq in eqs
    }

    # P276에서 참조하는 로케이션 QID들도 찾아야 함 (좌표 추출 위해)
    p276_qids_to_find: Set[str] = set(p276_needed.keys())

    all_qids_to_find = remaining_event_qids | p276_qids_to_find

    if not all_qids_to_find:
        print(f"  모든 QID 이미 수집됨! ({len(coords)}개)")
        # 결과 저장
        _save_coords(coords, p276_needed, loc_qid_map)
        return

    print(f"  찾아야 할 QID: {len(all_qids_to_find)} "
          f"(events: {len(remaining_event_qids)}, p276 locations: {len(p276_qids_to_find)})")

    # 덤프 스캔
    file_size = os.path.getsize(DUMP_PATH)
    print(f"  덤프 크기: {file_size/1e9:.1f} GB")
    print(f"  예상 시간: ~{file_size/100e6/60:.0f}분 (100MB/s 기준)")
    print()

    found_count = 0
    last_report = time.time()
    last_checkpoint = time.time()
    start_time = time.time()

    with open(DUMP_PATH, 'r', encoding='utf-8', buffering=64*1024*1024) as f:  # 64MB buffer
        # Resume: seek to position
        if bytes_read > 0:
            print(f"  {bytes_read/1e9:.1f}GB 위치로 이동 중...")
            f.seek(bytes_read)
            # 현재 줄 끝까지 읽기 (파일 위치가 줄 중간일 수 있으므로)
            f.readline()

        for line in f:
            lines_read += 1
            bytes_read += len(line.encode('utf-8'))

            # 빈 줄, 배열 시작/끝 건너뛰기
            stripped = line.strip()
            if not stripped or stripped in ('[', ']', ','):
                continue

            # QID 빠르게 추출 (첫 200자만)
            qid_match = re.search(r'"id"\s*:\s*"(Q\d+)"', line[:200])
            if not qid_match:
                continue

            qid = qid_match.group(1)

            # 우리가 찾는 QID인지 확인 (O(1) set lookup)
            if qid not in all_qids_to_find:
                continue

            # 매칭! JSON 파싱
            try:
                if stripped.endswith(','):
                    stripped = stripped[:-1]
                entity = json.loads(stripped)
            except json.JSONDecodeError:
                continue

            claims = entity.get('claims', {})

            # 이벤트 QID인 경우
            if qid in remaining_event_qids:
                remaining_event_qids.discard(qid)
                all_qids_to_find.discard(qid)

                # 1) P625 직접 좌표
                coord = extract_p625(claims)
                if coord:
                    coords[qid] = {
                        'lat': coord[0], 'lng': coord[1],
                        'source': 'P625', 'event_id': event_qid_map[qid]['id']
                    }
                    found_count += 1
                    continue

                # 2) P276 → 위치 QID
                loc_qid = extract_p276(claims)
                if loc_qid:
                    # 이미 DB에 있는 로케이션이면 바로 매칭
                    if loc_qid in loc_qid_map:
                        coords[qid] = {
                            'lat': 0, 'lng': 0,
                            'source': 'P276_direct',
                            'event_id': event_qid_map[qid]['id'],
                            'location_id': loc_qid_map[loc_qid]
                        }
                        found_count += 1
                    else:
                        # 나중에 이 위치의 좌표를 찾아야 함
                        if loc_qid not in p276_needed:
                            p276_needed[loc_qid] = []
                            all_qids_to_find.add(loc_qid)
                            p276_qids_to_find.add(loc_qid)
                        p276_needed[loc_qid].append(qid)
                    continue

                # 3) P17 → 국가 fallback
                country_qid = extract_p17(claims)
                if country_qid:
                    if country_qid in loc_qid_map:
                        coords[qid] = {
                            'lat': 0, 'lng': 0,
                            'source': 'P17_direct',
                            'event_id': event_qid_map[qid]['id'],
                            'location_id': loc_qid_map[country_qid]
                        }
                        found_count += 1
                    else:
                        if country_qid not in p276_needed:
                            p276_needed[country_qid] = []
                            all_qids_to_find.add(country_qid)
                            p276_qids_to_find.add(country_qid)
                        p276_needed[country_qid].append(qid)

            # P276/P17에서 참조한 위치 QID인 경우
            elif qid in p276_qids_to_find:
                p276_qids_to_find.discard(qid)
                all_qids_to_find.discard(qid)

                coord = extract_p625(claims)
                if coord and qid in p276_needed:
                    for event_qid in p276_needed[qid]:
                        coords[event_qid] = {
                            'lat': coord[0], 'lng': coord[1],
                            'source': 'P276',
                            'event_id': event_qid_map[event_qid]['id'],
                            'location_qid': qid
                        }
                        found_count += 1
                    del p276_needed[qid]

            # 진행 상황 보고 (30초마다)
            now = time.time()
            if now - last_report > 30:
                elapsed = now - start_time
                speed = bytes_read / elapsed / 1e6 if elapsed > 0 else 0
                pct = bytes_read / file_size * 100
                remaining_time = (file_size - bytes_read) / (speed * 1e6) if speed > 0 else 0
                print(f"  [{pct:5.1f}%] {bytes_read/1e9:.1f}/{file_size/1e9:.0f}GB | "
                      f"{speed:.0f}MB/s | "
                      f"found: {found_count} | "
                      f"remaining: {len(all_qids_to_find)} | "
                      f"ETA: {remaining_time/60:.0f}min")
                last_report = now

            # 체크포인트 저장 (5분마다)
            if now - last_checkpoint > 300:
                _save_checkpoint(coords, p276_needed, bytes_read, lines_read)
                last_checkpoint = now

            # 모든 QID를 찾았으면 조기 종료
            if not all_qids_to_find:
                print(f"\n  모든 QID 발견! 조기 종료 ({bytes_read/1e9:.1f}GB 스캔)")
                break

    # 최종 결과 저장
    elapsed = time.time() - start_time
    print(f"\n  스캔 완료: {elapsed/60:.1f}분, {bytes_read/1e9:.1f}GB 스캔")
    print(f"  좌표 수집: {len(coords)}")
    print(f"  미해결 P276: {sum(len(v) for v in p276_needed.values())}")
    print(f"  미발견 이벤트: {len(remaining_event_qids)}")

    _save_coords(coords, p276_needed, loc_qid_map)
    _save_checkpoint(coords, p276_needed, bytes_read, lines_read)


def _save_checkpoint(coords, p276_needed, bytes_read, lines_read):
    """체크포인트 저장."""
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'coords': coords,
            'p276_needed': p276_needed,
            'bytes_read': bytes_read,
            'lines_read': lines_read,
            'timestamp': datetime.now().isoformat()
        }, f, ensure_ascii=False)
    print(f"  [checkpoint saved: {len(coords)} coords at {bytes_read/1e9:.1f}GB]")


def _save_coords(coords, p276_needed, loc_qid_map):
    """최종 좌표 결과 저장."""
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    result = {
        'timestamp': datetime.now().isoformat(),
        'total_coords': len(coords),
        'coords': coords,
        'unresolved_p276': {k: v for k, v in p276_needed.items()},
        'source_breakdown': {},
    }

    # 소스별 통계
    for qid, data in coords.items():
        src = data.get('source', 'unknown')
        result['source_breakdown'][src] = result['source_breakdown'].get(src, 0) + 1

    with open(COORDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  좌표 저장: {COORDS_FILE} ({len(coords)}개)")


def phase_match(dry_run: bool = False, max_distance: float = 500):
    """Phase 2: 수집된 좌표 → 최근접 노드 매칭."""

    print("=" * 60)
    print("  Phase 2: 최근접 노드 매칭")
    print(f"  Dry-run: {dry_run} | Max distance: {max_distance}km")
    print("=" * 60)

    # 좌표 데이터 로드
    if not os.path.exists(COORDS_FILE):
        print(f"  좌표 파일 없음: {COORDS_FILE}")
        print(f"  먼저 --scan을 실행하세요.")
        return

    with open(COORDS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    coords = data['coords']
    print(f"  좌표 데이터: {len(coords)}개")
    print(f"  소스별: {data.get('source_breakdown', {})}")

    # DB에서 전체 로케이션 로드
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT id, name, latitude, longitude, wikidata_id FROM locations")
    all_locations = cur.fetchall()

    print(f"  전체 로케이션 노드: {len(all_locations)}")

    # numpy 인덱스 구축
    loc_ids = np.array([loc['id'] for loc in all_locations])
    loc_lats = np.radians(np.array([float(loc['latitude']) for loc in all_locations]))
    loc_lngs = np.radians(np.array([float(loc['longitude']) for loc in all_locations]))
    cos_loc_lats = np.cos(loc_lats)
    loc_names = {loc['id']: loc['name'] for loc in all_locations}

    # 이벤트 제목 맵
    cur.execute("SELECT id, title FROM events WHERE primary_location_id IS NULL AND wikidata_id IS NOT NULL")
    event_titles = {r['id']: r['title'] for r in cur.fetchall()}

    # 분류: 직접 매칭 vs 좌표 기반 매칭
    direct_matches = []  # (event_id, location_id, source)
    coord_events = []    # (event_id, lat, lng, source)

    for qid, info in coords.items():
        event_id = info.get('event_id')
        if not event_id:
            continue

        source = info.get('source', 'unknown')

        if 'location_id' in info:
            # P276_direct / P17_direct: 이미 location_id를 알고 있음
            direct_matches.append((event_id, info['location_id'], source))
        elif info.get('lat') and info.get('lng'):
            coord_events.append((event_id, info['lat'], info['lng'], source))

    print(f"\n  직접 매칭: {len(direct_matches)}")
    print(f"  좌표 기반 매칭 필요: {len(coord_events)}")

    # 좌표 기반 배치 최근접 매칭
    updates = list(direct_matches)  # (event_id, location_id, source)로 시작
    unmatched = []

    if coord_events:
        print(f"  numpy 배치 매칭 중...")
        t0 = time.time()

        R = 6371.0
        query_lats = np.radians(np.array([c[1] for c in coord_events]))
        query_lngs = np.radians(np.array([c[2] for c in coord_events]))

        # 1000개씩 배치
        BATCH = 1000
        for start in range(0, len(coord_events), BATCH):
            end = min(start + BATCH, len(coord_events))
            q_lats = query_lats[start:end, np.newaxis]
            q_lngs = query_lngs[start:end, np.newaxis]

            dlat = loc_lats[np.newaxis, :] - q_lats
            dlng = loc_lngs[np.newaxis, :] - q_lngs

            a = np.sin(dlat/2)**2 + np.cos(q_lats) * cos_loc_lats[np.newaxis, :] * np.sin(dlng/2)**2
            distances = R * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))

            min_indices = np.argmin(distances, axis=1)
            min_dists = distances[np.arange(len(min_indices)), min_indices]

            for i in range(len(min_indices)):
                idx = start + i
                event_id = coord_events[idx][0]
                source = coord_events[idx][3]
                dist = float(min_dists[i])

                if dist <= max_distance:
                    updates.append((event_id, int(loc_ids[min_indices[i]]), source))
                else:
                    unmatched.append((event_id, dist))

        t1 = time.time()
        print(f"  매칭 완료: {t1-t0:.1f}s")

    print(f"\n  총 매칭: {len(updates)}")
    print(f"  미매칭 (>{max_distance}km): {len(unmatched)}")

    # 거리 통계 (좌표 기반만)
    if coord_events and updates:
        # 다시 계산 (통계용)
        matched_coords = [(u[0], u[1]) for u in updates if u[0] in {c[0] for c in coord_events}]
        if matched_coords:
            # 간단 통계
            print(f"  소스별 매칭:")
            src_counts = {}
            for _, _, src in updates:
                src_counts[src] = src_counts.get(src, 0) + 1
            for src, cnt in sorted(src_counts.items()):
                print(f"    {src}: {cnt}")

    # DB 업데이트
    if dry_run:
        print(f"\n  [DRY-RUN] 변경 없음")
        print(f"\n  상위 30개 매칭 결과:")
        for event_id, loc_id, source in updates[:30]:
            ev_title = event_titles.get(event_id, f'Event#{event_id}')
            loc_name = loc_names.get(loc_id, f'Loc#{loc_id}')
            print(f"    [{source:12s}] {ev_title[:40]:40s} → {loc_name[:30]}")
    else:
        print(f"\n  DB 업데이트 중...")
        batch = []
        update_count = 0
        for event_id, loc_id, source in updates:
            batch.append((loc_id, event_id))
            if len(batch) >= 500:
                cur.executemany(
                    "UPDATE events SET primary_location_id = %s, updated_at = NOW() WHERE id = %s",
                    batch
                )
                conn.commit()
                update_count += len(batch)
                print(f"  {update_count}/{len(updates)} updated...")
                batch = []

        if batch:
            cur.executemany(
                "UPDATE events SET primary_location_id = %s, updated_at = NOW() WHERE id = %s",
                batch
            )
            conn.commit()
            update_count += len(batch)

        print(f"  총 {update_count}개 이벤트 업데이트 완료")

    # 최종 현황
    _print_stats(cur)
    conn.close()


def phase_reassign(new_location_id: int):
    """새 노드 추가 시 인근 이벤트 재분배."""
    print("=" * 60)
    print(f"  노드 재분배: location_id={new_location_id}")
    print("=" * 60)

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 새 노드 정보
    cur.execute("SELECT id, name, latitude, longitude FROM locations WHERE id = %s", (new_location_id,))
    new_loc = cur.fetchone()
    if not new_loc:
        print(f"  Location {new_location_id} not found!")
        conn.close()
        return

    new_lat = float(new_loc['latitude'])
    new_lng = float(new_loc['longitude'])
    print(f"  새 노드: {new_loc['name']} ({new_lat:.4f}, {new_lng:.4f})")

    # 이 노드와 가장 가까운 기존 노드들의 이벤트 확인
    cur.execute("""
        SELECT e.id, e.title, e.primary_location_id,
               l.name as current_loc_name, l.latitude, l.longitude
        FROM events e
        JOIN locations l ON e.primary_location_id = l.id
        WHERE e.primary_location_id IS NOT NULL
    """)
    events_with_loc = cur.fetchall()

    reassign = []
    for ev in events_with_loc:
        ev_loc_lat = float(ev['latitude'])
        ev_loc_lng = float(ev['longitude'])

        # 현재 노드까지 거리
        R = 6371.0
        lat1, lat2 = math.radians(new_lat), math.radians(ev_loc_lat)
        dlat = lat2 - lat1
        dlng = math.radians(float(ev['longitude']) - new_lng)
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        dist_to_new = R * 2 * math.asin(math.sqrt(a))

        # 기존 노드까지 거리 (이벤트의 "실제 좌표"가 없으므로 기존 노드 = 0)
        # → 기존 노드까지 거리 = 0 (이미 그 노드에 할당됨)
        # → 새 노드가 더 가까우려면... 이벤트의 "원래 좌표"가 필요

        # 참고: 이벤트에 직접 좌표가 없으므로, 좌표 파일에서 가져와야 함
        pass

    print(f"  (이벤트 원래 좌표 필요 — coords 파일 참조)")
    print(f"  reassign 대상: {len(reassign)}개")

    conn.close()


def phase_stats():
    """현황 통계."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    _print_stats(cur)

    # 좌표 파일 상태
    if os.path.exists(COORDS_FILE):
        with open(COORDS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"\n  좌표 파일: {len(data.get('coords', {}))}개")
        print(f"  소스별: {data.get('source_breakdown', {})}")
        print(f"  미해결 P276: {sum(len(v) for v in data.get('unresolved_p276', {}).values())}")

    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            cp = json.load(f)
        print(f"\n  체크포인트: {cp.get('bytes_read', 0)/1e9:.1f}GB 스캔됨")
        print(f"  시간: {cp.get('timestamp', 'unknown')}")

    conn.close()


def _print_stats(cur):
    """DB 현황 출력."""
    cur.execute("SELECT COUNT(*) as cnt FROM events")
    total = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(*) as cnt FROM events WHERE primary_location_id IS NOT NULL")
    with_loc = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(*) as cnt FROM events WHERE primary_location_id IS NULL AND wikidata_id IS NOT NULL")
    without_loc = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(*) as cnt FROM events WHERE wikidata_id IS NULL")
    no_wikidata = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(*) as cnt FROM locations")
    total_locs = cur.fetchone()['cnt']

    print(f"\n{'='*60}")
    print(f"  DB 현황")
    print(f"  전체 이벤트: {total}")
    print(f"  위치 연결됨: {with_loc} ({100*with_loc/total:.1f}%)")
    print(f"  위치 없음:   {without_loc} ({100*without_loc/total:.1f}%)")
    print(f"  Wikidata 없음: {no_wikidata}")
    print(f"  전체 로케이션 노드: {total_locs}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description='Event → Nearest Location Node Matching')
    parser.add_argument('--scan', action='store_true', help='Phase 1: 덤프 스캔 → 좌표 추출')
    parser.add_argument('--match', action='store_true', help='Phase 2: 좌표 → 최근접 노드 매칭')
    parser.add_argument('--reassign', type=int, default=None, help='새 노드 추가 시 재분배 (location_id)')
    parser.add_argument('--stats', action='store_true', help='현황 확인')
    parser.add_argument('--resume', action='store_true', help='체크포인트에서 재시작')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--max-distance', type=float, default=500, help='최대 매칭 거리 (km)')

    args = parser.parse_args()

    if args.stats:
        phase_stats()
    elif args.scan:
        phase_scan(resume=args.resume)
    elif args.match:
        phase_match(dry_run=args.dry_run, max_distance=args.max_distance)
    elif args.reassign is not None:
        phase_reassign(args.reassign)
    else:
        print("사용법:")
        print("  python match_event_locations.py --scan           # Phase 1: 덤프 스캔")
        print("  python match_event_locations.py --scan --resume   # 중단 후 재시작")
        print("  python match_event_locations.py --match           # Phase 2: 노드 매칭")
        print("  python match_event_locations.py --match --dry-run # 매칭 dry-run")
        print("  python match_event_locations.py --stats           # 현황")
        print("  python match_event_locations.py --reassign 123    # 노드 재분배")


if __name__ == '__main__':
    main()
