# History Shift Narrative Problem

## 문제 상황

현재 히스토리 시프트(History Shift)의 하단 패널에 표시되는 텍스트는 **기존 이벤트의 description을 그대로 가져다 쓰고 있다.**

이것은 완전히 잘못된 접근이다.

### 왜 잘못되었나

1. **내러티브가 이미 오른쪽 패널(NarrativeCard)에 있다** — 기존 이벤트 설명을 아래에 또 보여줄 이유가 전혀 없음. 그냥 오른쪽 패널 쓰면 됨.

2. **히스토리 시프트의 목적은 "흐름"이다** — 개별 이벤트의 설명이 아니라, 이벤트 간의 **인과관계와 전환**을 설명해야 함.
   - 예: "사군툼 함락 후 한니발은 알프스를 넘어 이탈리아로 진군했다. 이것이 제2차 포에니 전쟁의 본격적인 시작이었다."
   - 현재: 각 이벤트의 독립적인 description만 나열

3. **시프트 전용 내러티브가 필요** — 각 시프트(~895개)에 대해 새로운 텍스트를 LLM으로 생성해야 함.

### 현재 데이터 상태

- `chain_segments.page_narrative`: seed 스크립트에서 `event_details.description`을 그대로 복사한 것
- `chain_segments.page_narrative_ko`: 한국어 description을 복사한 것
- 이것들은 **placeholder일 뿐**, 최종 콘텐츠가 아님

### 해결 방향 (장기 과제)

#### Phase 1: 하단 패널 텍스트를 "흐름 내러티브"로 교체
- LLM (GPT-5.1-chat)으로 각 시프트의 페이지별 흐름 내러티브 생성
- 입력: 해당 시프트의 전체 이벤트 목록 + 각 이벤트의 기존 description
- 출력: 이벤트 간 전환을 설명하는 연결 텍스트
- 예산: ~895 시프트 × ~10 pages avg × ~500 tokens = ~4.5M tokens ≈ $5-6

#### Phase 2: 시프트 구조 자체 재검토
- aggregate 이벤트 기반 자동 생성만으로는 한계
- 큐레이션된 시프트 (수동 편집) 기능 필요
- 챕터 구분, 중요도 조절 등

#### Phase 3: 다국어 확장
- 현재 `_ko` 필드만 있음 (`_ja` 없음)
- 일본어, 영어 흐름 내러티브 생성

### 임시 조치

하단 패널에서 기존 내러티브 텍스트를 보여주는 것을 유지하되, 이것이 placeholder임을 인지할 것.
실제로 중요한 것은:
- 글로브 위 마커의 위치와 순서
- 적절한 줌 레벨
- 매끄러운 전환 애니메이션
- 왼쪽 상단 특이점 오버레이

내러티브 텍스트 품질 개선은 별도 스크립트(`backend/scripts/enrich_shift_narratives.py`)로 진행.

### 관련 파일

| 파일 | 설명 |
|------|------|
| `backend/scripts/seed_aggregate_shifts.py` | 현재 시드: event description 복사 |
| `backend/app/models/v1/chain.py` | `page_narrative`, `page_narrative_ko` 컬럼 |
| `frontend/src/components/shift/ShiftPanel.tsx` | 하단 패널 (내러티브 표시) |
| `backend/scripts/enrich_shift_narratives.py` | TODO: LLM 내러티브 생성 스크립트 |
