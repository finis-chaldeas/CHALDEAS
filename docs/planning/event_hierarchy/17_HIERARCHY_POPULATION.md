# 이벤트 계층화 데이터 구축 전략

**작성일**: 2026-01-28
**목적**: 46,000+ 이벤트를 현실적으로 계층 구조에 배치하는 단계별 전략

---

## 1. 문제 인식

### 왜 단순 매칭이 불가능한가

| 문제 | 예시 |
|------|------|
| **동명 이벤트** | "Treaty of Paris" - 1259, 1763, 1783, 1814, 1815, 1856, 1898, 1947... |
| **모호한 소속** | "Siege of Constantinople" - 어떤 포위전? (674, 717, 860, 1204, 1453...) |
| **범위 불명확** | "르네상스" 이벤트 범위? 1300-1600? 이탈리아만? |
| **데이터 품질** | 날짜 오류, 이름 불일치, 중복 |
| **규모** | 46,704개 이벤트 수동 검증 불가 |

### 목표 재정의

**완벽한 계층화 ❌** → **점진적 개선 ✅**

1차: 자동화로 70-80% 커버
2차: 학술 자료로 정제
3차: 사용자 피드백으로 지속 개선

---

## 2. 1차 자동 분류 (Automated First Pass)

### 2.1 데이터 소스 활용

```
┌─────────────────────────────────────────────────────────────┐
│                    1차 자동 분류 파이프라인                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   Wikidata   │    │   기존 DB    │    │     LLM      │   │
│  │   P361등     │    │  Category    │    │  분류기      │   │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘   │
│         │                   │                   │            │
│         ▼                   ▼                   ▼            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              통합 분류 엔진 (Classifier)              │    │
│  │   - 다수결 또는 가중 투표                             │    │
│  │   - 신뢰도 점수 산출                                  │    │
│  └─────────────────────────────────────────────────────┘    │
│                            │                                 │
│         ┌──────────────────┼──────────────────┐             │
│         ▼                  ▼                  ▼             │
│   [확실 (>0.8)]      [보통 (0.5-0.8)]    [불확실 (<0.5)]    │
│   자동 연결           검토 큐             미분류 유지        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Wikidata 관계 활용

**유용한 속성들:**

| Property | 설명 | 예시 |
|----------|------|------|
| `P361` | part of | "Battle of Agincourt" P361 "Hundred Years' War" |
| `P1269` | facet of | 관련 상위 개념 |
| `P921` | main subject | 주제 연결 |
| `P31` | instance of | "war", "battle", "treaty" 등 유형 |
| `P585` | point in time | 날짜 |
| `P580/P582` | start/end time | 기간 |

**구현:**

```python
# poc/scripts/fetch_wikidata_hierarchy.py

async def get_event_hierarchy(event_qid: str) -> dict:
    """Wikidata에서 이벤트의 상위 구조 조회"""
    query = """
    SELECT ?parent ?parentLabel WHERE {
        wd:""" + event_qid + """ wdt:P361 ?parent .
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en,ko". }
    }
    """
    # SPARQL 쿼리 실행
    results = await query_wikidata(query)
    return {
        "qid": event_qid,
        "parents": [r["parent"]["value"] for r in results]
    }
```

**예상 커버리지:**
- Wikidata에서 P361 있는 이벤트: ~30-40%
- 전쟁/전투 유형은 대부분 있음
- 문화/철학 운동은 적음

### 2.3 기존 Category 활용

현재 DB의 categories:

```sql
SELECT id, slug, name FROM categories;
-- 1, warfare, 전쟁
-- 2, politics, 정치
-- 3, religion, 종교
-- 4, philosophy, 철학
-- 5, science, 과학
-- 6, art, 예술
-- 7, literature, 문학
-- 8, exploration, 탐험
```

**Category → Aggregate 매핑:**

```python
CATEGORY_TO_AGGREGATE_TYPE = {
    "warfare": "war",
    "politics": "revolution",  # or dynasty
    "religion": "religious",
    "philosophy": "philosophical_school",
    "science": "scientific_era",
    "art": "artistic_period",
    "exploration": "expedition",
}
```

### 2.4 LLM 분류기

**역할:** Wikidata/Category로 분류 안 되는 이벤트 처리

```python
# poc/scripts/llm_event_classifier.py

CLASSIFICATION_PROMPT = """
다음 역사적 이벤트를 분류해주세요:

이벤트: {title}
설명: {description}
날짜: {date_start} - {date_end}
장소: {location}

질문:
1. 이 이벤트가 속하는 상위 역사적 맥락은? (예: 백년전쟁, 르네상스, 냉전 등)
2. 분류 신뢰도는? (high/medium/low)
3. 이유는?

JSON 형식으로 응답:
{
    "parent_context": "Hundred Years' War",
    "parent_context_ko": "백년전쟁",
    "confidence": "high",
    "reasoning": "아쟁쿠르 전투는 1415년 영국-프랑스 간 전투로 백년전쟁의 일부"
}
"""

async def classify_event(event: dict) -> ClassificationResult:
    response = await openai.chat.completions.create(
        model="gpt-5.1-chat-latest",  # 고정확도
        messages=[{"role": "user", "content": CLASSIFICATION_PROMPT.format(**event)}],
        response_format={"type": "json_object"}
    )
    return parse_classification(response)
```

**비용 추정:**
- 46,704 이벤트 × ~500 tokens = ~23M tokens
- gpt-5.1-chat-latest: $2.50/1M input, $10/1M output
- 전체: ~$70, Wikidata로 50% 처리 시: ~$35
- 배치 API 50% 할인 적용 시: ~$17

### 2.5 통합 분류 로직

```python
async def classify_event_multi_source(event: Event) -> ClassificationResult:
    """다중 소스 통합 분류"""

    results = []

    # 1. Wikidata P361 확인 (가장 신뢰)
    if event.wikidata_id:
        wd_result = await get_wikidata_hierarchy(event.wikidata_id)
        if wd_result.parents:
            results.append(("wikidata", wd_result, 0.9))

    # 2. 기존 Category 기반 추론
    if event.category:
        cat_result = infer_from_category(event)
        results.append(("category", cat_result, 0.5))

    # 3. LLM 분류 (폴백)
    if not results or max(r[2] for r in results) < 0.7:
        llm_result = await classify_with_llm(event)
        confidence = {"high": 0.8, "medium": 0.6, "low": 0.3}[llm_result.confidence]
        results.append(("llm", llm_result, confidence))

    # 다수결/가중 투표
    return aggregate_results(results)
```

---

## 3. 2차 학술 자료 기반 정제 (Academic Refinement)

### 3.1 활용 가능한 자료

| 자료 유형 | 예시 | 활용 방법 |
|----------|------|----------|
| **역사 백과사전** | Britannica, World History Encyclopedia | 계층 구조 참조 |
| **학술 논문** | JSTOR, Google Scholar | 시대 구분 기준 |
| **역사학 교과서** | Western Civilization 등 | 표준 분류 체계 |
| **온톨로지** | CIDOC-CRM, HistoryOntology | 형식화된 관계 |
| **디지털 인문학** | Pelagios, Pleiades | 지리-역사 연결 |

### 3.2 시대 구분 표준화

**참조할 학술 체계:**

```
Braudel의 시간 구분:
├── Longue durée (장기지속) → hierarchy_level 0-1
├── Conjoncture (중기순환) → hierarchy_level 2
└── Événement (사건) → hierarchy_level 3-4

Annales 학파 분류:
├── 경제-사회 구조
├── 문명 (mentalité)
└── 정치적 사건
```

### 3.3 상위 이벤트 상태 구분

| 상태 | 의미 | DB 표현 |
|------|------|---------|
| **확정 없음** | 최상위 이벤트 (Era, 독립 사건) | `parent_event_id = NULL`, `parent_status = 'none'` |
| **미분류** | 아직 상위 못 찾음 | `parent_event_id = NULL`, `parent_status = 'unknown'` |
| **확정됨** | 상위 이벤트 연결됨 | `parent_event_id = 123`, `parent_status = 'confirmed'` |
| **검토 필요** | LLM 분류, 수동 확인 필요 | `parent_event_id = 123`, `parent_status = 'pending_review'` |

```python
# 스키마 추가 필요
class ParentStatus(str, Enum):
    NONE = "none"              # 상위 없음 (확정)
    UNKNOWN = "unknown"        # 미분류
    CONFIRMED = "confirmed"    # 확정
    PENDING_REVIEW = "pending" # 검토 대기
```

### 3.4 시간 기반 계층 (Period Hierarchy)

**핵심 원칙**: 직접 상위 이벤트의 기간은 하위 이벤트를 **포함**해야 함

```
영국 역사 예시:

Roman Britain (43-410 CE)
├── Claudian invasion (43 CE) ✅
├── Boudicca's Revolt (60-61 CE) ✅
├── Hadrian's Wall (122 CE) ✅
└── End of Roman rule (410 CE) ✅

Anglo-Saxon period (410-1066 CE)  ← Roman Britain과 겹치지 않음
├── Heptarchy (500-927 CE)
│   ├── Kingdom of Wessex events
│   └── Viking raids (793+)
├── Kingdom of England (927-1066)
│   └── Battle of Stamford Bridge (1066)
└── Norman Conquest (1066) ← 경계 이벤트

Norman England (1066-1154 CE)
├── Battle of Hastings (1066) ✅
├── Domesday Book (1086) ✅
└── ...
```

**경계 이벤트 처리**:
- 1066년 노르만 정복 → Anglo-Saxon 종료 & Norman 시작
- 양쪽 모두에 연결 가능 (다중 부모) 또는 "전환 이벤트"로 별도 분류

### 3.5 계층 구조 검증 규칙

```python
# 시간 허용 오차 (년)
TEMPORAL_TOLERANCE = 50  # ±50년 이내는 경계 이벤트로 허용
TEMPORAL_HARD_LIMIT = 50  # 50년 초과 벗어나면 완전 거부

VALIDATION_RULES = {
    # 시간 정합성 (필수, hard constraint)
    # ±50년 초과 벗어나면 완전 아웃
    "temporal_hard": lambda parent, child: (
        (parent.date_start - TEMPORAL_HARD_LIMIT) <= child.date_start and
        (parent.date_end is None or
         child.date_end is None or
         (parent.date_end + TEMPORAL_HARD_LIMIT) >= child.date_end)
    ),

    # 시간 정합성 (권장, soft constraint)
    # 정확히 범위 내인지
    "temporal_exact": lambda parent, child: (
        parent.date_start <= child.date_start and
        (parent.date_end is None or
         child.date_end is None or
         parent.date_end >= child.date_end)
    ),

    # 지리 정합성 (권장, 추천용)
    # 세계대전 같은 경우 location이 의미 없으므로 soft constraint
    "spatial_suggestion": lambda parent, child: (
        is_location_within(child.location, parent.locations)
    ),

    # 계층 레벨 정합성 (필수)
    "level_order": lambda parent, child: (
        parent.hierarchy_level < child.hierarchy_level
    ),
}

def validate_parent_child(parent: Event, child: Event) -> dict:
    """부모-자식 관계 검증"""
    result = {
        "valid": True,
        "hard_violations": [],    # 필수 위반 → 거부
        "soft_violations": [],    # 권장 위반 → 경고/추천
    }

    # Hard constraints (시간 ±50년, 레벨)
    if not VALIDATION_RULES["temporal_hard"](parent, child):
        result["valid"] = False
        result["hard_violations"].append("temporal_hard")

    if not VALIDATION_RULES["level_order"](parent, child):
        result["valid"] = False
        result["hard_violations"].append("level_order")

    # Soft constraints (정확한 시간, 공간)
    if not VALIDATION_RULES["temporal_exact"](parent, child):
        result["soft_violations"].append("temporal_exact")

    if not VALIDATION_RULES["spatial_suggestion"](parent, child):
        result["soft_violations"].append("spatial_suggestion")

    return result


def can_be_parent(parent: Event, child: Event) -> bool:
    """부모가 될 수 있는지 (hard constraint만 체크)"""
    result = validate_parent_child(parent, child)
    return result["valid"]


def get_parent_recommendation(parent: Event, child: Event) -> dict:
    """부모 추천 점수 및 경고"""
    result = validate_parent_child(parent, child)

    if not result["valid"]:
        return {"score": 0, "rejected": True, "reason": result["hard_violations"]}

    # Soft violation 개수에 따라 점수 감소
    score = 1.0
    warnings = []

    if "temporal_exact" in result["soft_violations"]:
        score -= 0.2
        warnings.append("시간 범위 경계 (±50년 이내)")

    if "spatial_suggestion" in result["soft_violations"]:
        score -= 0.1  # 공간은 가중치 낮게
        warnings.append("장소 불일치 (참고용)")

    return {"score": score, "rejected": False, "warnings": warnings}
```

### 3.6 잘못된 상위 기간 수정

상위 이벤트의 기간이 잘못 지정된 경우:

```python
def fix_parent_period_and_reprocess(parent_id: int, new_start: int, new_end: int, db: Session):
    """상위 이벤트 기간 수정 후 자식들 재검증"""

    parent = db.query(Event).get(parent_id)
    parent.date_start = new_start
    parent.date_end = new_end

    # 기존 자식들 재검증
    children = db.query(Event).filter(Event.parent_event_id == parent_id).all()

    orphaned = []
    for child in children:
        if not can_be_parent(parent, child):
            # 시간 범위 벗어남 → 연결 해제, 재분류 필요
            child.parent_event_id = None
            child.parent_status = "unknown"
            orphaned.append(child.id)

    db.commit()

    if orphaned:
        print(f"재분류 필요: {len(orphaned)}개 이벤트")
        # 재분류 큐에 추가
        add_to_reclassification_queue(orphaned)

    return orphaned
```

### 3.6 Period 기반 자동 분류

```python
# 지역별 시대 정의
PERIOD_HIERARCHIES = {
    "britain": [
        {"name": "Roman Britain", "start": 43, "end": 410, "qid": "Q160732"},
        {"name": "Anglo-Saxon England", "start": 410, "end": 1066, "qid": "Q105313"},
        {"name": "Heptarchy", "start": 500, "end": 927, "parent": "Anglo-Saxon England"},
        {"name": "Kingdom of England", "start": 927, "end": 1066, "parent": "Anglo-Saxon England"},
        {"name": "Norman England", "start": 1066, "end": 1154, "qid": "Q327071"},
        # ...
    ],
    "france": [
        {"name": "Gaul", "start": -600, "end": 486},
        {"name": "Frankish Kingdom", "start": 486, "end": 843},
        {"name": "Kingdom of France", "start": 843, "end": 1792},
        # ...
    ],
    # 더 많은 지역...
}

def find_period_for_event(event: Event) -> Optional[str]:
    """이벤트의 장소와 시간으로 해당 Period 찾기"""
    location = event.primary_location
    if not location:
        return None

    region = get_region(location)  # britain, france, etc.
    if region not in PERIOD_HIERARCHIES:
        return None

    for period in PERIOD_HIERARCHIES[region]:
        if period["start"] <= event.date_start:
            if period.get("end") is None or period["end"] >= event.date_start:
                return period["name"]

    return None
```
```

### 3.4 리팩터링 프로세스

```
┌─────────────────────────────────────────────────────────────┐
│                    계층 구조 리팩터링                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 학술 자료 수집                                           │
│     └── 시대 구분, 전쟁 분류, 운동 체계 등                    │
│                                                              │
│  2. 표준 계층 템플릿 정의                                     │
│     └── "십자군 전쟁 > 제N차 십자군 > 개별 전투"              │
│                                                              │
│  3. 기존 분류와 비교                                          │
│     └── 불일치 항목 추출                                      │
│                                                              │
│  4. 자동 수정 + 검토 큐                                       │
│     └── 명확한 것은 자동, 애매한 것은 수동                    │
│                                                              │
│  5. 검증 규칙 실행                                            │
│     └── 시간/공간/유형 정합성 체크                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 3차 지속적 개선 (Continuous Improvement)

### 4.1 사용자 피드백 루프

```python
# API: 사용자가 잘못된 분류 신고
POST /api/v1/events/{id}/report-hierarchy
{
    "issue_type": "wrong_parent",  # wrong_parent, missing_parent, wrong_level
    "suggested_parent_id": 12345,
    "comment": "이 전투는 백년전쟁이 아니라 장미전쟁 소속"
}
```

### 4.2 품질 메트릭

```sql
-- 계층화 커버리지
SELECT
    COUNT(*) FILTER (WHERE parent_event_id IS NOT NULL) * 100.0 / COUNT(*) as coverage_pct,
    COUNT(*) FILTER (WHERE hierarchy_level = 2 AND is_aggregate = true) as aggregate_count,
    COUNT(*) FILTER (WHERE parent_event_id IS NULL AND importance >= 4) as orphan_important
FROM events;

-- 목표:
-- coverage_pct > 70%
-- orphan_important = 0 (중요 이벤트는 모두 분류)
```

### 4.3 자동 클러스터링 (향후)

```python
# 시간-공간 근접성 기반 자동 그룹화
def suggest_clusters(events: list[Event]) -> list[EventCluster]:
    """
    ML 기반 클러스터링으로 미분류 이벤트 그룹 제안
    - 시간: 10년 이내
    - 공간: 500km 이내
    - 주제: embedding 유사도
    """
    pass
```

---

## 5. 구현 계획

### Phase 2-A: 자동 분류 인프라 (1주)

```
[ ] DB 스키마 추가: parent_status 컬럼
[ ] Period 정의 테이블/데이터 (지역별 시대)
[ ] Wikidata P361 조회 스크립트
[ ] Category → Aggregate 매핑 테이블
[ ] LLM 분류 프롬프트 & 호출
[ ] 통합 분류기 구현
[ ] 시간 정합성 검증 로직
[ ] 신뢰도 기반 분류 실행
```

### Phase 2-B: Aggregate 이벤트 생성 (1주)

```
[ ] 주요 Aggregate 이벤트 50개 수동 생성
    - 00_OVERVIEW.md 목록 참조
    - 우선순위 1 먼저 (페르시아 전쟁, 십자군, 백년전쟁, 세계대전 등)
[ ] 자동 분류로 하위 이벤트 연결
[ ] 검증 규칙 실행 & 오류 수정
```

### Phase 2-C: 학술 자료 정제 (2주+)

```
[ ] 표준 시대 구분 자료 수집
[ ] 계층 템플릿 정의
[ ] 불일치 항목 리팩터링
[ ] 품질 메트릭 대시보드
```

### Phase 2-D: 지속 개선 (ongoing)

```
[ ] 사용자 피드백 API
[ ] 주간 품질 리포트
[ ] 자동 클러스터링 R&D
```

---

## 6. 예상 결과

### 1차 자동 분류 후

| 상태 | 예상 비율 | 개수 |
|------|----------|------|
| 확실 (>0.8) | 40% | ~18,700 |
| 보통 (0.5-0.8) | 30% | ~14,000 |
| 불확실 (<0.5) | 20% | ~9,300 |
| 미분류 | 10% | ~4,700 |

### 2차 정제 후

| 상태 | 예상 비율 | 개수 |
|------|----------|------|
| 분류 완료 | 75% | ~35,000 |
| 검토 필요 | 15% | ~7,000 |
| 미분류 (의도적) | 10% | ~4,700 |

---

## 7. 리스크 & 대응

| 리스크 | 확률 | 대응 |
|--------|------|------|
| Wikidata 커버리지 낮음 | 중 | LLM 비중 증가 |
| LLM 분류 정확도 낮음 | 중 | 프롬프트 개선, few-shot 예시 |
| 학술 자료 접근 어려움 | 저 | Wikipedia/공개 자료 우선 |
| 사용자 피드백 없음 | 중 | 능동적 샘플링 검토 |

---

## 8. 비용 추정

| 항목 | 비용 |
|------|------|
| LLM 분류 (gpt-5.1-chat-latest) | ~$17-35 (배치 API) |
| Wikidata API | 무료 |
| 개발 시간 | 2-3주 |
| 수동 검토 (선택) | 시간 투자 |

*gpt-5.1의 높은 정확도로 재분류 비용 절감 → 총 비용 효율적*

---

## 부록: 스크립트 위치

```
poc/scripts/
├── hierarchy/
│   ├── fetch_wikidata_hierarchy.py    # Wikidata P361 조회
│   ├── category_to_aggregate.py       # Category 기반 분류
│   ├── llm_event_classifier.py        # LLM 분류기
│   ├── unified_classifier.py          # 통합 분류
│   ├── create_aggregate_events.py     # Aggregate 이벤트 생성
│   ├── link_events_to_parents.py      # 하위 이벤트 연결
│   └── validate_hierarchy.py          # 검증 규칙
```
