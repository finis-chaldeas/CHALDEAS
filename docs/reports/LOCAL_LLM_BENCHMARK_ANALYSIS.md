# CHALDEAS V2 - Local LLM Benchmark Analysis Report

**생성일**: 2026-02-01
**테스트 환경**: RTX 3060 (6GB VRAM, 16GB Shared)
**테스트 데이터**: 93 샘플 (Entity 34, Nature 26, Date 33)
**총 테스트 시간**: ~1.5시간

---

## 1. Executive Summary

### 종합 결과

| 순위 | Model | Overall Accuracy | 추천 용도 |
|------|-------|------------------|-----------|
| 1 | **gemma2:9b** | **43.0%** | 범용 (특히 날짜 파싱) |
| 2 | qwen3:8b | 34.4% | 고품질 필요시 (매우 느림) |
| 3 | mistral:7b | 33.3% | Nature 분류 특화 |
| 4 | llama3.1:8b | 29.0% | 기존 기본 모델 |
| 5 | phi3:mini | 22.6% | 빠른 간단 작업 |

### 핵심 결론

1. **Entity Extraction은 로컬 모델로 불가능** - 최고 성능 6.5%
2. **Nature Classification은 로컬에서 충분** - mistral 84.6%
3. **Date Parsing은 gemma2가 압도적** - 70.5%
4. **gemma2:9b가 종합 최고** - 속도/성능 밸런스 우수

---

## 2. 태스크별 상세 분석

### 2.1 Entity Extraction (엔티티 추출)

| Model | F1 Score | 분석 |
|-------|----------|------|
| phi3:mini | 6.5% | 간혹 맞춤, 일관성 없음 |
| gemma2:9b | 4.4% | 부분 매칭 존재 |
| llama3.1:8b | 1.8% | 거의 실패 |
| mistral:7b | 0.5% | 실패 |
| qwen3:8b | 0.0% | 완전 실패 |

**분석**:
- 모든 로컬 모델이 **역사적 엔티티 추출에 실패**
- 원인: 역사적 인물/장소/이벤트 명칭의 복잡성
- 예: "Battle of Thermopylae"에서 "Thermopylae"를 장소로 추출 실패
- **해결책**: Entity extraction은 **API 에스컬레이션 필수** (gpt-5-mini 이상)

### 2.2 Nature Classification (이벤트 성격 분류)

| Model | Accuracy | 분석 |
|-------|----------|------|
| **mistral:7b** | **84.6%** | **최고 성능** |
| gemma2:9b | 80.8% | 준수 |
| llama3.1:8b | 80.8% | 준수 |
| qwen3:8b | 69.2% | "other" 오분류 많음 |
| phi3:mini | 65.4% | battle→war 혼동 |

**분석**:
- **mistral:7b가 명확한 1위** (84.6%)
- 대부분 모델이 80% 근처 달성 - 로컬에서 충분히 사용 가능
- 주요 실패 패턴:
  - `discovery` → `war` 오분류 (모든 모델)
  - `coronation` → `other` 오분류
  - `founding` → `treaty` 혼동

**분류별 정확도 (mistral:7b)**:
- war: 100%
- death: 100%
- birth: 100%
- treaty: 100%
- revolution: 100%
- battle: 100%
- coronation: 75%
- discovery: 50%
- founding: 50%

### 2.3 Date Parsing (날짜 파싱)

| Model | Accuracy | 분석 |
|-------|----------|------|
| **gemma2:9b** | **70.5%** | **압도적 1위** |
| mistral:7b | 47.5% | 2위 |
| qwen3:8b | 46.5% | 비슷하지만 느림 |
| llama3.1:8b | 40.2% | 기본 수준 |
| phi3:mini | 12.6% | 실패 |

**분석**:
- **gemma2가 날짜 파싱에서 압도적** (70.5% vs 2위 47.5%)
- BCE 날짜, 범위 날짜 처리 우수
- 주요 성공 패턴:
  - 정확한 연도 추출 (year 필드)
  - precision 올바른 판단 (exact/month/year/century)
  - 범위 날짜 year_start/year_end 추출

---

## 3. 속도 vs 품질 분석

### 테스트 시간 (93 샘플)

| Model | 시간 | 샘플당 평균 | 비고 |
|-------|------|-------------|------|
| mistral:7b | 405s (7분) | 4.4s | **가장 빠름** |
| phi3:mini | 422s (7분) | 4.5s | 빠름 |
| llama3.1:8b | 533s (9분) | 5.7s | 보통 |
| gemma2:9b | 968s (16분) | 10.4s | 다소 느림 |
| qwen3:8b | 3088s (51분) | 33.2s | **매우 느림** |

### 효율성 분석 (성능/시간)

| Model | Overall | Time | 효율 (acc/min) |
|-------|---------|------|----------------|
| **mistral:7b** | 33.3% | 7분 | **4.76%/min** |
| phi3:mini | 22.6% | 7분 | 3.23%/min |
| **gemma2:9b** | **43.0%** | 16분 | 2.69%/min |
| llama3.1:8b | 29.0% | 9분 | 3.22%/min |
| qwen3:8b | 34.4% | 51분 | 0.67%/min |

**결론**:
- 단순 작업: **mistral:7b** (빠르고 nature 분류 최고)
- 품질 중요: **gemma2:9b** (느리지만 종합 최고)
- **qwen3:8b은 비추천** (thinking mode가 너무 느림)

---

## 4. 모델별 특성 정리

### phi3:mini (2.2GB VRAM)
- **장점**: 가장 작고 빠름, Entity에서 유일하게 6% 달성
- **단점**: 전반적 품질 낮음
- **추천 용도**: 빠른 스크리닝, 간단한 분류

### mistral:7b-instruct-q4_0 (4.1GB VRAM)
- **장점**: Nature 분류 최고 (84.6%), 빠른 속도
- **단점**: Entity 추출 실패
- **추천 용도**: **Nature Classification 전용**, 빠른 배치 처리

### llama3.1:8b-instruct-q4_0 (4.7GB VRAM)
- **장점**: 균형잡힌 성능
- **단점**: 특출난 부분 없음
- **추천 용도**: 범용 백업 모델

### qwen3:8b (5.2GB VRAM)
- **장점**: 고품질 추론 (thinking mode)
- **단점**: **극도로 느림** (7배 느림)
- **추천 용도**: **비추천** (thinking mode 끄는 옵션 필요)

### gemma2:9b-instruct-q4_0 (5.4GB VRAM)
- **장점**: 종합 1위 (43%), Date parsing 압도적 (70.5%)
- **단점**: 다소 느림 (16분)
- **추천 용도**: **기본 모델**, Date parsing 전용

---

## 5. CHALDEAS V2 추천 구성

### TieredLLM 최적 설정

```python
# poc/scripts/v2/tiered_llm.py 권장 설정

TASK_MODEL_OVERRIDE = {
    # Entity extraction은 반드시 API로
    'entity_extraction': {
        'local_model': None,  # 로컬 불가
        'escalate_to': LLMTier.MINI,
        'confidence_threshold': 0.7
    },

    # Nature classification은 mistral로
    'nature_classification': {
        'local_model': 'mistral:7b-instruct-q4_0',
        'escalate_to': LLMTier.MINI,
        'confidence_threshold': 0.8
    },

    # Date parsing은 gemma2로
    'date_parsing': {
        'local_model': 'gemma2:9b-instruct-q4_0',
        'escalate_to': LLMTier.MINI,
        'confidence_threshold': 0.7
    },

    # 복잡한 분석은 API로
    'complex_analysis': {
        'local_model': None,
        'escalate_to': LLMTier.ADVANCED,
        'confidence_threshold': 0.5
    }
}
```

### 예상 비용 영향

**기존 (모든 작업 API)**:
- 10,000 이벤트 처리: ~$50

**최적화 후**:
- Entity extraction (API): ~$20
- Nature classification (로컬): $0
- Date parsing (로컬): $0
- **총 예상**: ~$20 (**60% 절감**)

---

## 6. 향후 개선 방안

### 6.1 Entity Extraction 개선
1. **프롬프트 엔지니어링**: 더 명확한 지시문
2. **Few-shot examples**: 예시 추가
3. **후처리 파이프라인**: LLM 출력 정제
4. **하이브리드**: 로컬 1차 추출 → API 검증

### 6.2 qwen3:8b 속도 개선
1. **thinking mode 비활성화** 옵션 탐색
2. `/no_think` 프롬프트 접두어 테스트
3. 대안: qwen2 또는 다른 non-thinking 모델

### 6.3 추가 모델 테스트 후보
- `deepseek-coder:6.7b` - 코드/구조화 출력
- `neural-chat:7b` - Intel 최적화
- `solar:10.7b` - 한국어 지원

---

## 7. 작업 이력 추적 시스템 제안

사용자 요청: "어느 모델이 했는지 작업 이력 남겨두면 나중에 더 좋은걸로 재부뉼하 할 수 있을 거 같거든"

### 제안 스키마

```sql
-- work_logs 테이블에 추가
ALTER TABLE work_logs ADD COLUMN model_used VARCHAR(100);
ALTER TABLE work_logs ADD COLUMN model_version VARCHAR(50);
ALTER TABLE work_logs ADD COLUMN task_type VARCHAR(50);

-- 또는 새 테이블
CREATE TABLE llm_work_history (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(20),  -- 'event', 'person', 'location'
    entity_id INTEGER,
    task_type VARCHAR(50),    -- 'entity_extraction', 'nature_classification', etc.
    model_used VARCHAR(100),
    model_tier VARCHAR(10),   -- 'local', 'mini', 'advanced'
    result_quality FLOAT,     -- 0.0 ~ 1.0
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    can_rerun BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_llm_work_model ON llm_work_history(model_used);
CREATE INDEX idx_llm_work_entity ON llm_work_history(entity_type, entity_id);
```

### 재처리 워크플로우

```python
# 나중에 더 좋은 모델로 재처리
def rerun_with_better_model(old_model: str, new_model: str, task_type: str):
    """이전에 특정 모델로 처리한 항목들을 새 모델로 재처리"""

    # 이전 작업 찾기
    items = db.query(
        "SELECT entity_id FROM llm_work_history "
        "WHERE model_used = ? AND task_type = ? AND can_rerun = TRUE",
        [old_model, task_type]
    )

    # 새 모델로 재처리
    for item in items:
        result = new_model.process(item)
        if result.quality > old_quality:
            update_entity(item, result)
            mark_as_rerun(item, new_model)
```

---

## 8. 결론

### 최종 권장 사항

1. **기본 로컬 모델**: `gemma2:9b-instruct-q4_0`
   - 종합 성능 최고, 날짜 파싱 압도적

2. **Nature 분류 전용**: `mistral:7b-instruct-q4_0`
   - 84.6% 정확도, 가장 빠름

3. **Entity 추출**: API 에스컬레이션 필수
   - 로컬 모델로는 불가능 (모두 <7%)

4. **qwen3:8b**: 사용 비추천
   - thinking mode로 인한 51분 소요

5. **비용 최적화**: 60% 절감 가능
   - Nature/Date는 로컬, Entity만 API

---

**Report Generated**: 2026-02-01 02:15
**Test Duration**: ~1.5 hours
**Total Cost**: $0 (all local models)
