# Gutenberg 책 병합 계획

## 현재 상태 (Wikipedia 추출 후)

```
sources:           ~16,000개 (events + persons + locations)
links:             ~3.3M개
mentions:          ~3.6M개
tentative_entities: ~5M개 (미분류)
```

---

## Gutenberg 추출 흐름

### 1. 책 처리

```
Gutenberg ZIM 파일
    ↓
책 청킹 (2500자 + 200자 오버랩)
    ↓
LLM 엔티티 추출 (Ollama/OpenAI)
    ↓
DB 매칭 시도
    ↓
sources + mentions 저장
```

### 2. 엔티티 매칭 우선순위

```
1. DB 기존 엔티티 (QID로 매칭)
2. entity_aliases (별칭 테이블)
3. tentative_entities (미분류 엔티티)
4. 새 tentative 생성
```

---

## 병합 로직

### Case 1: Wikipedia + Gutenberg 둘 다 같은 엔티티 언급

```sql
-- Napoleon이 Wikipedia에서도, Gutenberg 책에서도 언급됨

-- Wikipedia source
INSERT INTO mentions (source_id, target_type, target_id, evidence_raw)
VALUES (wiki_french_rev, 'link', napoleon_link, 'Napoleon seized power...');

-- Gutenberg source (같은 link에 다른 evidence)
INSERT INTO mentions (source_id, target_type, target_id, evidence_raw)
VALUES (gutenberg_napoleon_book, 'link', napoleon_link, 'The Emperor Napoleon...');
```

**결과:** 같은 link에 여러 mentions (다른 출처의 증거들)

### Case 2: Gutenberg에서 새 엔티티 발견

```
책: "Life of Admiral Nelson"
언급: "Captain Hardy" (DB에 없음)
    ↓
tentative_entities에 저장
    ↓
나중에 LLM이 분류 → persons 테이블에 생성
    ↓
기존 mentions 업데이트 (tentative → person)
```

### Case 3: 동명이인/동음이의어

```
"Washington" 언급됨
    ↓
컨텍스트 분석 필요:
- "President Washington" → George Washington (person)
- "Washington D.C." → Washington (location)
- "Washington crossed the Delaware" → person
- "marched to Washington" → location
```

**해결책:** LLM이 컨텍스트 보고 판단

---

## 데이터 구조 변경 (필요시)

### mentions 테이블 확장

```sql
ALTER TABLE mentions ADD COLUMN IF NOT EXISTS
    confidence FLOAT,           -- 매칭 확신도
    matched_by VARCHAR(50),     -- 'qid'/'name'/'llm'/'manual'
    context_window TEXT;        -- 주변 텍스트 (LLM 재분류용)
```

### tentative_entities 활용

```sql
-- 미분류 엔티티 조회 (많이 언급된 순)
SELECT wiki_title, mention_count, mentioned_in
FROM tentative_entities
WHERE status = 'pending'
ORDER BY mention_count DESC;

-- LLM 분류 후 업데이트
UPDATE tentative_entities
SET entity_type = 'person',
    llm_classification = 'person',
    llm_confidence = 0.95,
    llm_reviewed_at = NOW(),
    status = 'classified'
WHERE id = 123;
```

---

## LLM 분류 백그라운드 작업

### 스크립트: `classify_tentative_entities.py`

```python
"""
tentative_entities를 LLM으로 분류.

1. pending 상태인 엔티티 가져오기
2. Wikipedia 문서에서 첫 문단 추출
3. LLM에게 person/event/location 분류 요청
4. 확신도 높으면 실제 테이블에 생성
5. 낮으면 needs_review로 마킹
"""

CLASSIFY_PROMPT = """
Classify this Wikipedia article into one category:
- person: A human being (historical figure, politician, artist, etc.)
- event: A historical event (battle, war, treaty, revolution, etc.)
- location: A geographical place (city, country, region, etc.)
- other: None of the above

Title: {title}
First paragraph: {first_para}

Return JSON: {"type": "person|event|location|other", "confidence": 0.0-1.0}
"""
```

### 실행 계획

```bash
# 1단계: 많이 언급된 것부터 분류 (상위 10,000개)
python classify_tentative_entities.py --limit 10000 --min-mentions 5

# 2단계: 나머지 분류
python classify_tentative_entities.py --limit 100000

# 3단계: 낮은 확신도 검토
python classify_tentative_entities.py --review-low-confidence
```

---

## Gutenberg 추출 스크립트 수정

### `extract_gutenberg_llm.py` 변경점

```python
def match_entity(self, name, context, expected_type=None):
    """
    엔티티 매칭 (병합 로직 포함)
    """
    # 1. 기존 DB에서 찾기
    entity = self.find_in_db(name, expected_type)
    if entity:
        return entity

    # 2. 별칭에서 찾기
    entity = self.find_in_aliases(name)
    if entity:
        return entity

    # 3. tentative에서 찾기
    tentative = self.find_in_tentative(name)
    if tentative:
        return ('tentative', tentative['id'], None)

    # 4. 새 tentative 생성
    tentative_id = self.create_tentative(name, context)
    return ('tentative', tentative_id, None)
```

---

## 실행 순서

### Phase 1: Wikipedia 완료 (현재)
- [x] events 추출
- [x] locations 추출
- [ ] persons 추출 (진행 중)

### Phase 2: LLM 분류
- [ ] `classify_tentative_entities.py` 구현
- [ ] 상위 10,000개 tentative 분류
- [ ] 실제 테이블로 이동

### Phase 3: Gutenberg 추출
- [ ] `extract_gutenberg_llm.py` 병합 로직 추가
- [ ] 테스트 책 5권 추출
- [ ] 전체 책 추출

### Phase 4: 품질 검증
- [ ] 중복 엔티티 병합
- [ ] 잘못된 분류 수정
- [ ] API 연동 테스트

---

## 예상 데이터 규모

| 소스 | sources | links | mentions |
|------|---------|-------|----------|
| Wikipedia (현재) | ~16K | ~3.3M | ~3.6M |
| Gutenberg (예상) | ~60K 책 | ~10M+ | ~15M+ |
| **총합** | ~76K | ~13M+ | ~18M+ |

---

## 참고: 현재 파일 구조

```
poc/scripts/unified/
├── extract_wikipedia.py      # Wikipedia 추출 (완성)
├── extract_gutenberg_llm.py  # Gutenberg 추출 (수정 필요)
├── fetch_wiki_sitelinks.py   # sitelinks 수집 (완성)
├── run_full_extraction.py    # 배치 실행 (완성)
└── classify_tentative_entities.py  # TODO: 구현 필요
```
