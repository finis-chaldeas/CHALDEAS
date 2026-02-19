# 이벤트 확장 계획서

> **작성일**: 2026-02-12
> **현재 상태**: events 22,878개 (목표 20만 대비 11%)

---

## 문제 분석

### 현재 이벤트가 적은 이유

`poc/scripts/wikidata/extract_events_from_dump.py`의 `EVENT_TYPES` 필터가 **17개 군사/정치 이벤트**로 제한됨:

```python
EVENT_TYPES = {
    'Q178561': 'battle',
    'Q198': 'war',
    'Q180684': 'military_conflict',
    'Q188055': 'siege',
    'Q131569': 'treaty',
    'Q10931': 'revolution',
    'Q124734': 'rebellion',
    'Q45382': 'coup',
    'Q8465': 'civil_war',
    'Q13418847': 'historical_event',
    'Q173065': 'crusade',
    'Q192909': 'natural_disaster',
    'Q3199915': 'massacre',
    'Q2401485': 'expedition',
    'Q209480': 'coronation',
    'Q3882219': 'assassination',
}
```

### 누락된 주요 이벤트 타입들

| QID | 타입 | 예상 수량 | 우선순위 |
|-----|------|---------|---------|
| `Q1190554` | occurrence (발생 사건) | ~50만 | 높음 |
| `Q11514315` | historical period (역사적 시대) | ~5만 | 높음 |
| `Q40231` | election (선거) | ~10만 | 중간 |
| `Q132241` | festival (축제) | ~5만 | 낮음 |
| `Q7283` | terrorist attack | ~5천 | 중간 |
| `Q1656682` | event (일반 이벤트) | ~100만 | 높음 |
| `Q15275719` | recurring event | ~10만 | 중간 |
| `Q4830453` | business (설립/폐업) | ~50만 | 낮음 |
| `Q2627975` | award ceremony | ~5만 | 낮음 |
| `Q18536594` | trial (재판) | ~1만 | 중간 |
| `Q625994` | convention (회의) | ~5만 | 낮음 |
| `Q11862829` | academic conference | ~5만 | 낮음 |
| `Q5389` | earthquake | ~3만 | 중간 |
| `Q8065` | flood | ~1만 | 중간 |
| `Q8084` | volcanic eruption | ~5천 | 중간 |
| `Q8070` | hurricane | ~3만 | 중간 |

---

## 확장 계획

### Phase 1: 핵심 역사 이벤트 추가 (목표: +10만)

**추가할 타입:**
```python
EXPANDED_EVENT_TYPES = {
    # 기존 17개 유지
    ...

    # 핵심 추가 (역사적 중요도 높음)
    'Q1190554': 'occurrence',           # 발생 사건
    'Q11514315': 'historical_period',   # 역사적 시대
    'Q1656682': 'event',                # 일반 이벤트
    'Q15275719': 'recurring_event',     # 반복 이벤트
    'Q18536594': 'trial',               # 재판

    # 자연재해 확장
    'Q5389': 'earthquake',
    'Q8065': 'flood',
    'Q8084': 'volcanic_eruption',
    'Q8070': 'hurricane',
    'Q168983': 'epidemic',              # 전염병
}
```

### Phase 2: 정치/사회 이벤트 추가 (목표: +5만)

```python
POLITICAL_EVENT_TYPES = {
    'Q40231': 'election',
    'Q7283': 'terrorist_attack',
    'Q217327': 'political_scandal',
    'Q1348506': 'public_demonstration',
    'Q735': 'art_movement',
    'Q11514315': 'historical_period',
}
```

### Phase 3: 문화/스포츠 이벤트 (선택적)

```python
CULTURAL_EVENT_TYPES = {
    'Q132241': 'festival',
    'Q2627975': 'award_ceremony',
    'Q625994': 'convention',
    'Q476028': 'sports_competition',
}
```

---

## 구현 계획

### CP-E1: 이벤트 타입 분석 (1시간)

1. [ ] Wikidata에서 occurrence (Q1190554) 하위 타입 전체 추출
2. [ ] 각 타입별 예상 수량 확인
3. [ ] 최종 타입 목록 확정

### CP-E2: 추출 스크립트 수정 (2시간)

1. [ ] `config.py`의 `EVENT_TYPES` 확장
2. [ ] 필터링 로직 최적화 (속도)
3. [ ] 중복 제거 로직 추가

### CP-E3: 추출 실행 (6-12시간)

1. [ ] 1.6TB Wikidata JSON에서 이벤트 추출
2. [ ] 진행 상황 모니터링
3. [ ] 결과 검증

### CP-E4: DB 임포트 (2시간)

1. [ ] 기존 events 테이블에 추가 (UPSERT)
2. [ ] event_locations 연결
3. [ ] mentions 생성

### CP-E5: 검증 (1시간)

1. [ ] 총 이벤트 수 확인 (목표: 15-20만)
2. [ ] 타입별 분포 확인
3. [ ] 위치 연결률 확인

---

## 예상 결과

| 단계 | 추가 이벤트 | 누적 |
|------|-----------|------|
| 현재 | - | 22,878 |
| Phase 1 | +100,000 | ~123,000 |
| Phase 2 | +50,000 | ~173,000 |
| Phase 3 | +30,000 | ~203,000 |

---

## 리스크

1. **중복**: 같은 이벤트가 여러 타입으로 분류될 수 있음
   - 해결: wikidata_id 기준 UPSERT

2. **품질**: 너무 사소한 이벤트 포함
   - 해결: sitelink 수 기준 필터링 (최소 5개 언어)

3. **시간**: 1.6TB 스캔에 6-12시간 소요
   - 해결: 체크포인트/재시작 지원

---

## 다음 단계

1. 사용자 승인 후 CP-E1 시작
2. 우선순위 확정 (Phase 1만? 전체?)
