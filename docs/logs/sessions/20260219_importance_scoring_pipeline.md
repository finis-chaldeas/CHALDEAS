# 세션 로그: 2026-02-19 Importance Scoring Pipeline

## 세션 정보
- **목적**: 이벤트/인물에 AI 기반 중요도 점수(1-100) 부여하여 타임라인 재구축 기반 마련
- **소요 시간**: ~4시간 (프롬프트 테스트 + 28K 이벤트 스코어링 + 190K 인물 스코어링)
- **비용**: 이벤트 ~$4 + 인물 ~$15 = **총 ~$19** (gpt-5-mini)

---

## 배경

기존 타임라인(`laplaceTimeline.ts`)은 50개 하드코딩 엔트리. 실제 DB에는 28K 이벤트, 190K 인물이 있지만 중요도 구분이 없어 "어떤 사건/인물이 중요한가"를 판단할 기준이 없었음.

**목표**: 전체 이벤트/인물에 1-100 중요도 점수를 부여하여:
1. 타임라인에 실제 중요한 사건만 표시
2. 검색에서 중요 인물 우선 표시
3. 글로브에서 중요도 기반 필터링

---

## 1단계: 프롬프트 테스트

### 파일: `poc/scripts/test_importance_prompts.py`

3가지 프롬프트 전략을 12개 큐레이션된 이벤트로 테스트:

| 전략 | 설명 | 점수 범위 | 표준편차 |
|------|------|-----------|----------|
| **A (Simple)** | 직접 1-100 점수 요청 | 8-100 | 34.1 |
| **B (Rubric)** | 4기준×25점 루브릭 | 7-100 | **35.4** |
| **C (Anchor)** | 참조 이벤트 비교 | 10-100 | 34.7 |

**결과: Prompt B (Rubric) 채택** - 가장 넓은 점수 분포, 최고 식별력

### 루브릭 기준 (각 0-25점)
1. **GLOBAL REACH**: 여러 문명/대륙에 영향?
2. **LASTING LEGACY**: 결과가 얼마나 오래 지속?
3. **SCALE OF IMPACT**: 직접 영향받은 인원 수?
4. **PARADIGM SHIFT**: 정치/문화/사상을 근본적으로 변화?

### 기술적 문제 해결
- `max_tokens` → `max_completion_tokens` (gpt-5-mini는 reasoning model)
- `temperature=0.1` 지원 안 됨 → 제거 (기본값 1만 지원)
- 150 토큰으로 빈 응답 → reasoning 토큰 ~448개 소비 → 2000+ 필요

---

## 2단계: 대규모 스코어링 파이프라인

### 파일: `poc/scripts/score_importance.py`

**아키텍처:**
- 비동기 동시 API 호출 (`asyncio` + `Semaphore`)
- JSONL 체크포인트 (중단 시 재개 가능)
- 이벤트: 5개씩 배치 → ~5,600 API 호출
- 인물: 10명씩 배치 → ~19,000 API 호출
- 동시 요청: 500개 (OpenAI rate limit: 10K RPM)

**설정:**
```python
MODEL = "gpt-5-mini"
MAX_CONCURRENT = 500
CHECKPOINT_DIR = poc/data/importance_scores/
```

### 이벤트 스코어링 결과
- **총 28,331개** 이벤트, 28,275개 성공 (40 에러, 0.14%)
- **소요 시간**: 47분 (8.5/s)
- **점수 분포**: 평균 30.5, 범위 1-100

| 등급 | 점수 | 비율 |
|------|------|------|
| 1 (trivial) | 1-15 | 28% |
| 2 (minor) | 16-35 | 44% |
| 3 (notable) | 36-60 | 20% |
| 4 (major) | 61-80 | 4% |
| 5 (world-defining) | 81-100 | 4% |

### 인물 스코어링 결과
- **총 190,700개** 인물, 190,446개 성공 (254 에러, 0.13%)
- **소요 시간**: ~3.5시간 (15/s)
- **점수 분포**: 평균 15.7, 범위 1-100

| 등급 | 점수 | 비율 |
|------|------|------|
| 1 (trivial) | 1-15 | 55% |
| 2 (minor) | 16-35 | 26% |
| 3 (notable) | 36-60 | 13% |
| 4 (major) | 61-80 | 4% |
| 5 (elite) | 81-100 | 2% |

---

## 3단계: DB 적용

### 파일: `poc/scripts/apply_importance_scores.py`

**스키마 변경:**
- `events` 테이블: `importance_score INTEGER` 컬럼 + 인덱스 추가
- `persons` 테이블: `importance_score INTEGER` 컬럼 + 인덱스 추가
- 기존 `importance` (1-5) 컬럼도 100점 기준으로 재계산

**매핑 (1-100 → 1-5):**
```
1-15  → 1 (trivial)
16-35 → 2 (minor)
36-60 → 3 (notable)
61-80 → 4 (major)
81-100 → 5 (world-defining)
```

---

## 4단계: 50년 단위 타임라인 픽업

### 파일: `poc/scripts/generate_timeline_pickup.py`

DB에서 50년 단위로 top N 이벤트/인물을 추출하여 구조화된 JSON 생성.

**출력 파일:**
| 파일 | 설명 |
|------|------|
| `poc/data/timeline/timeline_pickup.json` | 전체 상세 (91개 기간, top 3) |
| `poc/data/timeline/timeline_compact.json` | 간결 요약 (기간별 top 1) |
| `poc/data/timeline/generated_eras.ts` | TypeScript 파일 (프론트엔드 호환) |

**결과**: 3050 BCE ~ 2049 CE, 91개 50년 기간 생성 성공

---

## 발견된 품질 문제

### 스코어링 문제
1. **100점 인플레이션**: 현대 구간(1900+)에서 너무 많은 인물이 100점 → 차별화 불가
   - Shigeru Miyamoto = 100 (1950-1999 #1)
   - Francis Crick = 100 (1900-1949 #1)
   - 같은 시대 Einstein, Churchill도 100이라 식별 불가
2. **도메인 편향**: 단일 "세계사 중요도" 축으로 과학자, 철학자, 게임개발자를 평가 → 부적절
3. **role 필드 빈약**: 98,292명이 "occupation"이라는 무의미한 값

### 이벤트 데이터 문제
1. **Wikidata QID 타이틀**: `Q102885246`, `Q6151929` 등 제목 없는 이벤트가 상위
2. **시대성 이벤트 혼입**: "modern period", "Qin Han" 같은 `is_aggregate=true` 이벤트가 개별 사건과 섞임

---

## 5단계: 도메인 분류 (Domain Classification)

### 파일: `poc/scripts/classify_person_domains.py`

**목적**: 단일 "세계사 중요도" 척도의 한계 해결. 게임개발자와 대통령이 같은 100점이 되는 문제.

**도메인 체계**: 역사학 분과 기반 16개 도메인

| 도메인 | 분야 | 글로벌 가중치 | 인원 |
|--------|------|-------------|------|
| statecraft | Political History | 1.00 | 23,582 (12.4%) |
| military | Military History | 0.95 | 54,209 (28.4%) |
| religion | Religious History | 1.00 | 2,551 (1.3%) |
| philosophy | Intellectual History | 0.90 | 567 (0.3%) |
| science | History of Science | 0.90 | 2,069 (1.1%) |
| medicine | History of Medicine | 0.80 | 1,302 (0.7%) |
| technology | History of Technology | 0.85 | 1,210 (0.6%) |
| literature | Literary History | 0.80 | 6,042 (3.2%) |
| visual_arts | Art History | 0.75 | 2,667 (1.4%) |
| music | History of Music | 0.70 | 12,154 (6.4%) |
| exploration | History of Exploration | 0.85 | 1,002 (0.5%) |
| economy | Economic History | 0.65 | 3,320 (1.7%) |
| law | Legal History | 0.70 | 2,090 (1.1%) |
| reform | Social History | 0.80 | 3,443 (1.8%) |
| scholarship | Historiography | 0.60 | 4,459 (2.3%) |
| entertainment | Cultural History | 0.35 | 58,643 (30.7%) |

**설정**: gpt-5-mini, 50명/배치, 500 동시 호출

**결과**: 179,046명 분류 성공, 11,564 에러 (6.1%), ~74분

### 파일: `poc/scripts/apply_person_domains.py`

**DB 스키마 변경:**
- `persons.domain VARCHAR(20)` 컬럼 + 인덱스 추가
- `persons.global_score INTEGER` 컬럼 + 인덱스 추가
- `global_score = importance_score × domain_weight`

**핵심 효과 (글로벌 스코어):**
- Shigeru Miyamoto: 100 × 0.35 = **35** (타임라인에서 탈락)
- Einstein: 100 × 0.90 = **90** (높지만 정치 지도자보다 낮음)
- Winston Churchill: 99 × 1.0 = **99** (1900-1949 구간 #1로 승격)
- Julius Caesar: 100 × 1.0 = **100** (그대로 유지)

**비용**: ~$3 (gpt-5-mini, 3,800 API 호출)

---

## 다음 단계 (미구현)

### 즉시 개선 가능
- [ ] Wikidata QID만 있는 이벤트 필터링 (Q-번호 타이틀)
- [ ] `is_aggregate=true` 이벤트 제외 (시대명이 개별 사건으로 나오는 문제)
- [ ] 현대 구간 세분화 (1900+ → 25년/10년 단위)
- [ ] 분류 에러 11,564건 재시도
- [ ] 현대 인물 글로벌 스코어 추가 검증 (Katalin Karikó, Erling Haaland 등)

### 도메인별 재스코어링 (선택)
- 도메인 분류는 완료 → 도메인 내 상대평가로 재스코어링하면 더 정밀해짐
- 예: 과학사 내에서 Newton=100, 특정 물리학자=30 (현재는 둘 다 높은 점수)
- 비용: ~$15-20 (gpt-5-mini, 190K 재스코어링)

### 내러티브 생성 (Step 2)
- gpt-5.1-chat-latest로 Wikipedia 참조하여 각 타임라인 항목의 서술 생성
- `laplaceTimeline.ts` 교체

---

## 생성/수정 파일 목록

| 파일 | 작업 | 설명 |
|------|------|------|
| `poc/scripts/test_importance_prompts.py` | 신규 | 프롬프트 비교 테스트 |
| `poc/scripts/score_importance.py` | 신규 | 비동기 스코어링 파이프라인 |
| `poc/scripts/apply_importance_scores.py` | 신규 | DB 적용 스크립트 |
| `poc/scripts/classify_person_domains.py` | 신규 | 도메인 분류 파이프라인 (16개 역사학 도메인) |
| `poc/scripts/apply_person_domains.py` | 신규 | 도메인 + global_score DB 적용 |
| `poc/scripts/generate_timeline_pickup.py` | 신규 | 50년 단위 타임라인 생성 (global_score 기반) |
| `poc/data/importance_scores/events_scores.jsonl` | 데이터 | 이벤트 스코어 체크포인트 (28K) |
| `poc/data/importance_scores/persons_scores.jsonl` | 데이터 | 인물 스코어 체크포인트 (190K) |
| `poc/data/importance_scores/persons_domains.jsonl` | 데이터 | 인물 도메인 분류 (179K) |
| `poc/data/timeline/timeline_pickup.json` | 데이터 | 전체 타임라인 픽업 |
| `poc/data/timeline/timeline_compact.json` | 데이터 | 간결 타임라인 요약 |
| `poc/data/timeline/generated_eras.ts` | 데이터 | TypeScript 호환 파일 |
| DB: `events.importance_score` | 스키마 | 1-100 중요도 점수 컬럼 추가 |
| DB: `persons.importance_score` | 스키마 | 1-100 중요도 점수 컬럼 추가 |
| DB: `persons.domain` | 스키마 | 역사학 도메인 분류 (16개 중 1개) |
| DB: `persons.global_score` | 스키마 | 도메인 가중 글로벌 점수 |

---

## 체크포인트 파일

스코어링 결과는 JSONL 체크포인트로 보존되어 재실행 시 이미 완료된 항목은 건너뜀:
```
poc/data/importance_scores/
  ├── events_scores.jsonl   (28,331 lines, ~4MB)
  └── persons_scores.jsonl  (190,700 lines, ~30MB)
```
