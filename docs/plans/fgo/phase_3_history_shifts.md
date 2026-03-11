# Phase 3: 히스토리 시프트 — 빈 곳 채우기

**선행 조건**: Phase 2 (아티클에서 시프트 매칭 결과 확인 후)
**비용**: ~$3.50 (gpt-5.2-chat-latest)
**예상 시간**: ~20분
**DB 반영**: No (YAML 생성만)

---

## 목표

Phase 2 아티클에서 **매칭되지 않은 시프트만** 신규 생성.
기존 895개 시프트 + Phase 2에서 확인된 기존 매칭 결과를 바탕으로,
빈 곳만 정확히 채운다.

**변경점**: 기존 "10-15개 독립 생성" → **"Phase 2 결과 기반 갭 필링"**

---

## 기존 시프트 커버리지 (DB 확인 완료)

DB에서 86개 FGO 관련 시프트 확인됨. 주요 커버리지:

### ✅ 커버됨 (기존 시프트 활용)

| FGO 주제 | 기존 시프트 | importance |
|----------|-----------|-----------|
| 백년전쟁 (특이점 I) | shift-hundred-years-war 등 | 5 |
| 로마 제국 (특이점 II) | shift-roman-empire | 5 |
| 카이사르 내전 | shift-caesars-civil-war | 5 |
| 대항해시대 (특이점 III) | 스페인 아메리카 식민 등 | 5 |
| 산업혁명 (특이점 IV) | 관련 시프트 있음 | - |
| 미국 독립혁명 (특이점 V) | shift-american-revolution | 5 |
| 십자군 (특이점 VI) | 다수 crusade 시프트 | 2-4 |
| 나폴레옹 전쟁 | shift-napoleonic-wars | 5 |
| 프랑스 혁명 | shift-french-revolution | 5 |
| 러시아 혁명 | shift-russian-revolution | 5 |
| 진한 (-221~220) | shift-qin-han | 5 |
| 알렉산드로스 원정 | shift-alexanders-balkan-campaign | - |
| 프톨레마이오스 이집트 | shift-greco-roman-egypt | 5 |

### ❌ 미커버 (신규 생성 필요)

| 주제 | chain_type | FGO 연결 | 우선순위 |
|------|-----------|----------|---------|
| 메소포타미아 문명 (우루크/수메르) | aggregate | 특이점 VII | 높음 |
| 잔 다르크 일생 | person_story | 특이점 I | 높음 |
| 네로 클라우디우스 시대 | person_story | 특이점 II | 높음 |
| 드레이크 + 무적함대 | person_story | 특이점 III | 중간 |
| 이반 뇌제 러시아 | aggregate | LB1 | 높음 |
| 북유럽 신화 시대 | aggregate | LB2 | 중간 (신화 영역) |
| 마하바라타/라마야나 | aggregate | LB4 | 중간 (신화 영역) |
| 메소아메리카 문명 | aggregate | LB7 | 높음 |
| 오다 노부나가 천하통일 | person_story | 서번트 칼럼 | 중간 |
| 나이팅게일 + 크림전쟁 | person_story | 서번트 칼럼 | 낮음 |

→ **8-10개** 신규 시프트 (기존 예상 15개에서 축소)

---

## 작업 흐름

### Step 1: Phase 2 결과에서 갭 확인

Phase 2 아티클 생성 시 `find_matching_shifts()`가 매칭 실패한 목록 → 자동 수집.

```python
# Phase 2 실행 후 자동 생성되는 파일
# output/shift_gaps.json
{
  "unmatched_topics": [
    {
      "source_article": "singularity-7",
      "topic": "Mesopotamian civilization",
      "keywords": ["uruk", "sumer", "mesopotamia"],
      "year_range": [-3500, -539],
      "suggested_type": "aggregate",
      "priority": "high"
    },
    {
      "source_article": "singularity-1",
      "topic": "Joan of Arc",
      "keywords": ["jeanne", "orleans"],
      "person_id": ...,
      "suggested_type": "person_story",
      "priority": "high"
    }
  ]
}
```

### Step 2: 신규 시프트 생성

기존 `create_shift.py --generate` 파이프라인 사용. **GPT 프롬프트 전체 영어** (콘텐츠도 영어이므로 언어 혼동 방지):

```bash
# aggregate 시프트
python scripts/create_shift.py --generate "Mesopotamian Civilization" --type aggregate

# person_story 시프트
python scripts/create_shift.py --generate "Joan of Arc" --type person_story
```

### Step 3: 위젯 강화

```bash
python scripts/create_shift.py --enhance SHIFT_ID --model gpt-5.2
```

### Step 4: Phase 2 아티클에 시프트 slug 역삽입

신규 생성된 시프트의 slug을 Phase 2 YAML의 `related_shifts`에 추가.

---

## 콘텐츠 구조

기존 `create_shift.py` 파이프라인 그대로:

```yaml
slug: mesopotamia-uruk-civilization
chain_type: aggregate
title: "Mesopotamia — The Cradle of Civilization"
title_ko: ""
year_start: -3500
year_end: -539
globe_importance: 4

chapters:
  - chapter_title: "The First Cities"
    pages:
      - title: "Uruk — The World's First Megacity"
        event_id: ...
        location_id: ...
        importance: 5
        widget_hints: ["era_context", "dramatic_stat"]
```

person_story 시프트:

```yaml
slug: joan-of-arc
chain_type: person_story
title: "Joan of Arc — The Maid Who Saved France"
title_ko: ""
year_start: 1412
year_end: 1431
globe_importance: 4
person_id: ...

chapters:
  - chapter_title: "The Voice from Heaven"
    pages:
      - title: "A Peasant Girl from Domrémy"
        event_id: ...
        location_id: ...
```

---

## Phase 2와의 연결

```
Phase 2 실행
    ↓
각 아티클에서 find_matching_shifts()
    ↓
매칭 성공 → related_shifts에 기존 slug 삽입
매칭 실패 → shift_gaps.json에 기록
    ↓
Phase 3: shift_gaps.json 기반으로 신규 시프트 생성
    ↓
생성된 slug → Phase 2 YAML에 역삽입
```

---

## 출력

- `backend/scripts/output/{slug}.yaml` × 8-10개
- `backend/scripts/output/shift_gaps.json` (Phase 2에서 자동 생성)
- DB 직접 반영 안 함

## 비용

- Outline: 10 × ~$0.20 = $2.00
- Enhance: 10 × 12pages × ~$0.011 = $1.32
- **Total: ~$3.50** (기존 $5.50에서 축소 — 기존 시프트 활용)
