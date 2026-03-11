# 20260303 — History Shift 파이프라인 개선

## 세션 요약

`create_shift.py`에 안전장치 5개 추가 + `--enhance` 모드 설계.

---

## 완료된 작업 (이번 세션)

### 1. 좌표 → location_id 자동 매핑

**함수**: `find_nearest_location(db, lat, lng, max_distance_deg=1.0)`

GPT가 좌표만 알고 location_id를 모를 때, DB에서 1° 반경 내 가장 가까운 location을 찾아 매핑.
`segment_has_entity` 제약 때문에 모든 페이지에 엔티티가 필수인데, 이벤트/인물 없는 페이지도 location은 있으니 좌표로 해결.

### 2. Entity ID DB 검증

**함수**: `_validate_entity_ids(db, chapters, entity_roles)`

Import 전 모든 entity ID를 DB에서 일괄 확인:
- 존재하지 않는 ID → null 처리 + 경고
- entity가 전부 null이 된 페이지 → 좌표 fallback (위 함수 활용)
- entity_roles에서도 무효 ID → 제거
- GPT가 hallucinate한 ID로 인한 FK violation 방지

### 3. 위젯 스키마 검증

**상수**: `WIDGET_REQUIRED_FIELDS` (15개 위젯 타입별 필수 필드)
**함수**: `_validate_widgets(chapters)`

GPT가 생성한 위젯 JSON 구조 검증:
- `type` 필수, 미등록 타입은 경고 (프론트엔드가 무시)
- `slot` 유효성 (left/right/bottom/overlay)
- `priority` 없으면 자동 부여
- `data` 없거나 dict 아니면 제거
- 위젯별 필수 필드 누락 경고 (예: `faction_vs`에 `left_name_ko` 없음)

### 4. parent_shift_slug 지원

YAML에 `parent_shift_slug: "greco-persian-wars"` 지정 →
import 시 DB에서 slug로 조회 → `parent_shift_id` 자동 resolve.

Sub-shift 계층구조 연결용 (예: "그리스-페르시아 전쟁" → "마라톤 전투" 하위 시프트).

### 5. --batch-discover

위젯이 없는 시프트 + 시프트가 아예 없는 aggregate 이벤트를 자동 발견:

```bash
python scripts/create_shift.py --batch-discover --min-importance 4 --limit 10
```

테스트 결과:
- **위젯 없는 imp>=4 시프트**: 남북 전쟁(510p), WW2(340p), WW1(180p), 7년전쟁(129p) 등
- **시프트 없는 aggregate 이벤트**: 소련 이후 분쟁, 제네바 협약, 타타르의 멍에, 바이킹 확장 등

---

## 설계 완료 / 미구현: --enhance 모드

### 개요

기존 895개 시프트 대부분이 **위젯 없음, narrative는 이벤트 제목 복붙**. entity linking은 완료 상태.
→ GPT로 narrative + 위젯만 추가하는 모드. Step 1 (Outline) 불필요, Step 2 (Content) 만 실행.

### CLI

```bash
python scripts/create_shift.py --enhance 2228                     # 기본
python scripts/create_shift.py --enhance 2228 --max-pages 20      # 페이지 수 제한
python scripts/create_shift.py --enhance 2228 --page-range 0-19   # 범위 지정
python scripts/create_shift.py --enhance 2228 --dry-run            # 미리보기
```

### 동작 흐름

```
1. DB에서 shift + segments 로드
2. 각 segment에서 기존 entity 정보 추출
3. 관련 entity 상세 정보 조회 → GPT 컨텍스트
4. 대형 시프트는 importance 기준 상위 N개만 선택
5. 페이지별 Step 2 GPT 호출
   - page_narrative_ko 50자 미만 → 새로 생성
   - widgets 비어있음 → 새로 생성
   - 둘 다 있으면 → 스킵
6. DB 직접 UPDATE (이미 entity linking 완료이므로 YAML 불필요)
```

### 핵심 결정

| 항목 | 결정 | 이유 |
|------|------|------|
| 저장 방식 | DB 직접 UPDATE (기본) | entity linking 이미 완료, YAML 왕복 불필요 |
| 대형 시프트 | `--max-pages` + importance 우선순위 | 500p 전부 처리하면 $7/shift |
| 기존 내용 | 보존 (50자+ narrative 스킵) | `--force`로 덮어쓰기 가능 |
| YAML export | `--export-yaml` 옵션으로 선택적 | 검수가 필요한 경우에만 |

### 비용

- 1 페이지: ~$0.014 (Step 2 only)
- 20p 시프트: ~$0.28
- 상위 50개 시프트 × 15p: ~$10.50

### 구현 순서

1. `gather_segment_context()` — 세그먼트별 entity 상세 조회
2. `cmd_enhance()` — 메인 루프 (필터 → GPT → UPDATE)
3. `--page-range` 옵션
4. `--export-yaml` 옵션
5. argparse 추가

---

## 변경 파일 요약

| 파일 | 변경 | 라인 |
|------|------|------|
| `backend/scripts/create_shift.py` | 5개 기능 추가 | 1240 → 1663 |
| `docs/logs/sessions/20260303_shift_enhance_plan.md` | enhance 설계안 (신규) | — |
| `docs/logs/sessions/20260303_shift_pipeline_improvements.md` | 이 문서 (신규) | — |

### create_shift.py 추가된 함수/상수

```
find_nearest_location()        — 좌표 → location_id
_validate_entity_ids()         — entity ID 존재 확인 + 자동 수정
WIDGET_REQUIRED_FIELDS         — 15개 위젯 필수 필드 정의
_validate_widgets()            — 위젯 JSONB 구조 검증
cmd_batch_discover()           — 미완성 시프트/이벤트 발견
```

### cmd_import() 개선

```
Before: entity 제약 단순 체크 → 실패 시 에러
After:  entity ID DB 검증 → 좌표 fallback → 위젯 검증 → parent_shift_slug resolve
```

---

## 다음 작업

- [ ] `--enhance` 모드 구현 (위 설계안 기반)
- [ ] 실제 `--generate` 테스트 (마라톤 전투 등)
- [ ] 생성된 YAML → `--import --dry-run` 검증
- [ ] 프론트엔드에서 시프트 재생 확인
- [ ] `--batch-discover` 결과에서 우선순위 시프트 선정 → enhance
