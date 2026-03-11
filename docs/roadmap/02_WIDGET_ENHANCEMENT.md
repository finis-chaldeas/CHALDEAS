# 02. 위젯 배치 강화 (--enhance)

## 문제

9,367 페이지 중 위젯이 있는 건 30개 (0.3%). 시프트를 열면 텍스트만 나온다.
위젯 시스템(15종)은 이미 완성되어 있고, `--enhance`가 GPT로 위젯을 생성하므로 배치 실행만 하면 된다.

## 현재 상태

| 중요도 | 시프트 수 | 위젯 없는 시프트 | 페이지 수 |
|--------|----------|----------------|----------|
| 5 | 175 | ~170 | 3,613 |
| 4 | 229 | ~230 | 2,562 |
| 3 | 171 | 171 | 1,310 |
| 2 | 313 | 313 | 1,860 |
| 1 | 8 | 8 | 22 |
| **합계** | **896** | **~400 (imp4+)** | **9,367** |

위젯 0인 imp4+ 시프트가 **400개**. 이것이 1차 대상.

## 실행 계획

### Phase 1: imp5 시프트 (175개)

```bash
cd backend

# 1. 대상 확인
python scripts/create_shift.py --batch-discover --min-importance 5

# 2. 개별 실행 (검증용, 첫 5개)
python scripts/create_shift.py --enhance 2524 --force     # Battle of Stalingrad
python scripts/create_shift.py --enhance 2539 --force     # Normandy landings
python scripts/create_shift.py --enhance 2540 --force     # Cold War
python scripts/create_shift.py --enhance 1921 --force     # Reconquista
python scripts/create_shift.py --enhance 2457 --force     # Battle of the Somme

# 3. 결과 확인 후 나머지 배치
# (배치 스크립트 필요 — 아래 참조)
```

### Phase 2: imp4 시프트 (229개)

Phase 1 결과 검증 후 같은 방식으로 진행.

### 배치 실행 스크립트 (필요시 작성)

```python
# scripts/batch_enhance.py
# --min-importance N 으로 대상 시프트 조회
# 각 시프트에 --enhance --force 실행
# 에러 발생 시 로그 남기고 다음으로
# 비용 누적 출력
```

## --enhance가 생성하는 것

한 번의 `--enhance` 호출로 페이지당:
- `page_narrative_ko` (200~400자 한국어 내러티브)
- `widgets` (2~3개 위젯 JSON)
- `camera_altitude` (카메라 줌 레벨)
- `highlight_locations` (개요 페이지용 하이라이트)
- **논문 컨텍스트** (paper_utils 통합 완료 — 학술적 근거)

→ 위젯 + 한국어 번역이 **동시에** 해결됨 (03번 태스크와 중복)

## 비용 추정

| 항목 | 수치 |
|------|------|
| GPT-5.2 가격 | $1.75/1M in, $14.00/1M out |
| 페이지당 비용 | ~$0.03-0.05 |
| imp5 시프트 (3,613p) | ~$110-180 |
| imp4 시프트 (2,562p) | ~$80-130 |
| **imp4+ 합계** | **~$190-310** |

## 우선순위 높은 시프트 (imp5, 위젯 없음)

| ID | 페이지 | Slug | 제목 |
|----|--------|------|------|
| 1921 | 100 | reconquista | Reconquista |
| 2540 | 40 | cold-war | Cold War |
| 2457 | 28 | battle-of-the-somme | Battle of the Somme |
| 2650 | 26 | libyan-civil-war | Libyan Civil War |
| 2448 | 19 | first-balkan-war | First Balkan War |
| 2665 | 17 | yemeni-civil-war | Yemeni civil war |
| 1913 | 15 | muslim-conquest-of-the-levant | Muslim conquest of the Levant |
| 2088 | 11 | italian-war-of-15511559 | Italian War of 1551–1559 |
| 1918 | 11 | second-fitna | Second Fitna |
| 2468 | 8 | interwar-period | Interwar period |

## 수정 파일

| 파일 | 변경 |
|------|------|
| `backend/scripts/batch_enhance.py` | **신규** (선택) — 배치 루프 스크립트 |

기존 `create_shift.py --enhance`는 이미 완성. 배치 래퍼만 필요할 수 있음.

## 검증

```bash
# enhance 후 확인
curl http://localhost:8100/api/v1/shifts/2524 | python -m json.tool | head -50
# → segments[].widgets 배열이 비어있지 않은지
# → segments[].page_narrative_ko가 채워져 있는지
```
