# 20260304 — Shift Camera Control + Highlight Markers

## Purpose

초한전쟁 시프트(id=2687) 프론트엔드 테스트 결과, 연속 페이지가 같은 좌표를 공유하면 글로브가 이동하지 않는 문제 발견. 사용자 피드백: "같은 위치면 줌 변경, 개관이면 복수 마커 표시".

## Changes

### Backend

| File | Change |
|------|--------|
| `alembic/versions/603_shift_camera_highlights.py` | 신규 마이그레이션: `camera_altitude` (Float), `highlight_locations` (JSONB) |
| `app/models/v1/chain.py` | ChainSegment 모델에 2개 칼럼 추가 |
| `app/api/v1/shifts.py` | `_serialize_page()`에 2개 필드 추가 |
| `scripts/create_shift.py` | GPT 프롬프트 + YAML 구조 + import SQL + 검증 함수 |

### Frontend

| File | Change |
|------|--------|
| `types/index.ts` | ShiftPage 인터페이스에 `camera_altitude`, `highlight_locations` 추가 |
| `store/globeStore.ts` | `goToPage()` — page.camera_altitude 사용 |
| `components/globe/GlobeContainer.tsx` | shiftHtmlElements에 highlight 마커 추가, htmlElementFn에 shift-highlight 렌더링, DOM 업데이트에 highlight visibility 토글 |
| `components/shift/ShiftPanel.css` | `.shift-highlight-marker`, `.shift-hl-dot`, `.shift-hl-label` 스타일 |

## Key Decisions

1. **camera_altitude**: 페이지별 Float (0.05~3.0). null이면 현재 altitude 유지.
2. **highlight_locations**: JSONB 배열. 최대 5개. 현재 페이지의 highlights만 표시 (DOM 토글).
3. highlight 마커를 useMemo deps에 activePageIndex 넣지 않음 — 대신 ref + DOM 조작으로 표시/숨김.
4. 기존 shift-page 마커와 별개 kind ('shift-highlight')로 분리.

## Validation Rules (create_shift.py)

- `camera_altitude`: 0.05~3.0 범위, 범위 밖이면 clamp + 경고
- `highlight_locations`: lat/lng 필수, label_ko 권장, 5개 초과 시 truncate
- 연속 동일 좌표 + camera_altitude 없음 → 경고 (에러 아님)

## Next Steps

- [ ] `alembic upgrade head` 실행
- [ ] 초한전쟁 YAML에 camera_altitude + highlight_locations 추가 → `--import --force`
- [ ] 새 시프트 `--generate` 테스트 → GPT가 camera_altitude 포함하는지 확인
- [ ] 세력도(faction_zone) 위젯 설계 → `docs/logs/sessions/20260303_faction_zone_design.md`
