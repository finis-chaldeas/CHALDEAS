# Session Log: 2026-02-17 Event Location Matching Pipeline

## Session Info
- **Purpose**: 전체 28,331 이벤트 중 위치 없는 23,857개에 대해 Wikidata 좌표 추출 + 최근접 로케이션 노드 매칭
- **원칙**: 유저 확정 규칙 - locations = 노드, 이벤트 → 가장 가까운 노드, 기존 매칭 보존, 새 노드 추가 시 재분배

## DB 현황 (작업 시작 시)
```
Total events:              28,331
With primary_location_id:   4,474 (15.8%)
WITHOUT LOCATION:          23,857 (84.2%)
All have wikidata_id:      28,331 (100% enrichable)
Total locations (nodes):   12,908
```

## Changes Made

### 1. match_event_locations.py 작성
- **File**: `poc/scripts/wikidata/match_event_locations.py`
- **설계**: 2단계 분리
  - Phase 1 (`--scan`): 1.8TB Wikidata 덤프 스트리밍 → 이벤트 좌표 추출
  - Phase 2 (`--match`): 수집된 좌표 → numpy 벡터화 haversine → 최근접 노드 매칭
- **최적화**:
  - QID 빠른 추출 (라인 첫 200자만 regex, JSON 파싱 스킵)
  - set lookup O(1) for 23,857 QIDs
  - 64MB 읽기 버퍼
  - 5분마다 체크포인트 저장 → `--resume` 지원
  - numpy 배치 haversine (1000개씩, 12,908 로케이션 × N events)
- **좌표 추출 우선순위**: P625(직접 좌표) → P276(위치 QID, DB 직접 매칭) → P17(국가 fallback)
- **노드 재분배**: `--reassign <location_id>` 커맨드 (스켈레톤)

### 2. 02_LOCATION_SYSTEM.md 업데이트
- 노드 기반 매칭 규칙 섹션 추가
- 새 노드 추가 시 재분배 프로토콜 문서화
- 좌표 추출 파이프라인 다이어그램

### 3. 테스트 결과 (API 버전, 50개)
- 49/50 매칭 성공 (98%)
- 평균 거리 45.1km, 중앙값 15.2km
- Battle of Kosovo → Kosovo Polje (2km), Battle of Gaugamela → Nineveh (9km) 등

## 현재 상태
- Phase 1 덤프 스캔: 백그라운드 실행 중
- 예상 완료: ~5-7시간 (HDD 67-194 MB/s)
- 체크포인트: poc/data/wikidata/event_coords_checkpoint.json

## 반성
- 처음에 API 버전으로 작성했다가 유저가 로컬 덤프 사용 지시 → 재작성
- 1.8TB 덤프 스캔은 시간이 오래 걸리지만, API 호출 없이 완전 로컬로 처리 가능
- 체크포인트 시스템 추가로 중단/재시작 가능

## 다음 작업
1. Phase 1 완료 후 `--match --dry-run` 검증
2. 검증 후 `--match` 실행 → DB 업데이트
3. `--stats`로 최종 현황 확인
4. 08_PENDING_IMPROVEMENTS.md B2 (서번트 person 6명 이관) 진행
