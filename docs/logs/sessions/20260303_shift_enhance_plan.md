# --enhance 모드 설계안

## 목적

기존 895개 시프트 중 대부분이 `seed_aggregate_shifts.py`로 생성되어 **위젯 없음, narrative는 이벤트 제목 복붙** 상태.
이미 entity linking이 완료된 페이지들에 GPT로 narrative + 위젯을 추가하는 모드.

## 현황 (`--batch-discover` 결과)

위젯 없는 imp>=4 시프트 예시:
- 남북 전쟁: 510p, narrative 82p
- 제2차 세계 대전: 340p, narrative 152p
- 제1차 세계 대전: 180p, narrative 78p
- 7년 전쟁: 129p, narrative 45p

## CLI

```bash
# 특정 시프트 enhance
python scripts/create_shift.py --enhance 2228 --max-pages 20

# dry-run으로 미리보기
python scripts/create_shift.py --enhance 2228 --dry-run

# 페이지 범위 지정 (대형 시프트에서 일부만)
python scripts/create_shift.py --enhance 2228 --page-range 0-19
```

## 동작 흐름

```
1. DB에서 shift(historical_chains) + segments(chain_segments) 로드
2. 각 segment에서 기존 entity 정보 추출 (event_id, person_id, location_id)
3. 관련 events/persons/locations 상세 정보 조회 → GPT 컨텍스트 구성
4. 페이지 수가 max-pages보다 많으면 importance 기준 상위 N개만 선택
5. 선택된 페이지들에 대해 Step 2 (Content) GPT 호출
   - 기존 page_narrative_ko가 50자 미만이면 → 새로 생성
   - 기존 widgets가 비어있으면 → 새로 생성
   - 이미 둘 다 있으면 → 스킵
6. 결과를 DB에 직접 UPDATE (YAML 중간 파일 없음 — 이미 entity linking 완료이므로)
   OR YAML로 export → 수동 검수 → re-import
```

## 핵심 설계 결정

### A. DB 직접 업데이트 vs YAML export

| 방식 | 장점 | 단점 |
|------|------|------|
| DB 직접 UPDATE | 빠름, 배치에 적합 | 검수 없이 바로 반영 |
| YAML export → 검수 → import | 안전, 품질 관리 | 대형 시프트(500p)에 비현실적 |

**권장**: 기본 DB 직접 UPDATE + `--dry-run`으로 미리보기 + `--export-yaml`로 선택적 YAML 출력

### B. 대형 시프트 처리 (100+ 페이지)

- 전부 enhance하면 비용 폭발 (500p × $0.014 = $7/shift)
- **해결**: `--max-pages`로 상위 N개만 선택 + is_keystone/importance 기준 우선순위
- 또는 `--page-range 0-19`로 수동 범위 지정

### C. 기존 내용 보존

- `page_narrative_ko`가 50자 이상이면 스킵 (이미 작성된 것)
- `widgets`가 비어있지 않으면 스킵
- `--force`면 전부 덮어쓰기

## GPT 호출 전략

enhance 모드에서는 Step 1 (Outline)이 **필요 없음** — 구조(페이지 순서, 엔티티 링크)가 이미 DB에 있음.
Step 2 (Content) 만 실행:

```python
def cmd_enhance(args):
    shift_id = args.enhance

    # 1. Load shift + segments from DB
    chain = db.query(HistoricalChain).get(shift_id)
    segments = db.query(ChainSegment).filter_by(chain_id=shift_id).order_by(sequence_number).all()

    # 2. Filter segments needing enhancement
    targets = []
    for seg in segments:
        needs_narrative = not seg.page_narrative_ko or len(seg.page_narrative_ko) < 50
        needs_widgets = not seg.widgets or len(seg.widgets) == 0
        if needs_narrative or needs_widgets:
            targets.append(seg)

    # 3. Select top N by importance
    if len(targets) > max_pages:
        targets.sort(key=lambda s: (s.is_keystone or False, s.importance or 0), reverse=True)
        targets = targets[:max_pages]

    # 4. Gather entity context for GPT
    for seg in targets:
        context = gather_segment_context(db, seg)  # event details, person bio, location

        # 5. Call Step 2 GPT per page
        response = generate_page_content(client, chain, seg, context)

        # 6. UPDATE segment in DB
        seg.page_narrative_ko = response["page_narrative_ko"]
        seg.widgets = response["widgets"]

    db.commit()
```

## 비용 추정

- 1 페이지 enhance: ~$0.014 (Step 2 only, gpt-5.2-chat-latest)
- 20페이지 시프트: ~$0.28
- imp>=4 시프트 전부 (top 20p each): ~$70
- 실질적으로 상위 50개 시프트 × 15p = ~$10.50

## 구현 순서 (향후)

1. `gather_segment_context()` — 세그먼트별 entity 상세 조회
2. `cmd_enhance()` — 메인 루프 (필터 → GPT → UPDATE)
3. `--page-range` 옵션
4. `--export-yaml` 옵션 (YAML로 뽑아서 검수)
5. argparse에 `--enhance SHIFT_ID` 추가
