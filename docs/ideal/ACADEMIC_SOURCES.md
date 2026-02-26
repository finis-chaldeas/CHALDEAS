# Academic Sources: 학술 논문 소싱 시스템

> **한 줄 요약**: 학술 논문의 초록을 항상 보여주고, 본문은 필요할 때만 가져오는 2단계 소스 시스템.
> 책을 가져오듯이 논문도 가져온다.

---

## 1. 왜 필요한가

히스토리 시프트를 작성할 때 **학술적 근거**가 필요하다.

- 잔다르크의 재판 → Sullivan (1999) *Interrogation of Joan of Arc*
- 로마 멸망 원인 → Ward-Perkins (2005) *The Fall of Rome*
- 흑사병 확산 경로 → Campbell (2016) *The Great Transition*

현재 CHALDEAS의 소스는 **책(Gutenberg)과 위키피디아** 중심이다.
학술 논문이 추가되면 **신뢰도 4~5 등급의 secondary source**가 대량으로 확보된다.

---

## 2. 핵심 원칙

### 2-Tier 로딩 전략

```
Tier 1: 초록 (Abstract)
  - 항상 저장, 항상 표시
  - 논문당 ~1-2 KB
  - 검색 시점에 즉시 확보
  - 용도: 관련성 판단, 요약 인용, LLM 컨텍스트

Tier 2: 본문 (Full Text)
  - 필요할 때만 가져옴 (lazy-load)
  - 논문당 ~50-200 KB (청킹 후)
  - OA(Open Access) 논문만 가능
  - 용도: 상세 인용, 엔티티 추출, 깊은 서사 작성
```

**비유**: 도서관에서 책 제목과 뒷표지 요약은 항상 볼 수 있다. 실제로 펼쳐 읽는 건 필요할 때만.

### 품질 우선 (Quality over Quantity)

검색 결과 전부를 저장하지 않는다. **스코어링 후 상위 논문만 선별**한다.

---

## 3. 데이터 소스

### 메인: OpenAlex

| 항목 | 값 |
|------|---|
| 총 논문 수 | 474M+ works |
| 인문학 커버리지 | 최고 수준 (타 서비스 대비 인문학/비영어권 강세) |
| 역사(History) 논문 | subfield ID 1202, 수십만 편 |
| 무료 일일 예산 | $1/day (검색 $0.001, 목록 $0.0001, ID조회 무료) |
| 초록 형식 | inverted_index → 복원 필요 (trivial) |
| 본문 접근 | OA URL 제공 + content 다운로드 ($0.01) |

**주요 역사 토픽 (OpenAlex taxonomy)**:
- European Political History Analysis: 285K+ works
- Reformation and Early Modern Christianity: 367K+ works
- Historical and Archaeological Studies: 수십만
- Classical Studies: 333K+ works

### 보조: Semantic Scholar

| 항목 | 값 |
|------|---|
| 총 논문 수 | 225M+ papers |
| 핵심 기능 | **influentialCitationCount** (실질적 인용수) |
| 인용 그래프 | references + citations 필드 |
| 초록 형식 | plaintext (바로 사용 가능) |
| 무료 한도 | API key 있으면 1 req/sec |

**역할**: 인용 관계 분석, 실질적 영향력 판별. 논문 간 인과 관계 구축.

### 보조: CORE

| 항목 | 값 |
|------|---|
| 풀텍스트 보유 | 46M+ papers |
| 무료 링크 | 323M+ free-to-read links |
| PDF 다운로드 | API로 직접 가능 |
| 무료 한도 | 5 req/10sec (검색), 10 req/10sec (조회) |

**역할**: Tier 2 본문 접근의 1차 소스. OA 논문 PDF 다운로드.

---

## 4. 품질 스코어링

### 가용 시그널

| 시그널 | 출처 | 설명 |
|--------|------|------|
| `cited_by_count` | OpenAlex | 총 인용수 |
| `cited_by_percentile_year` | OpenAlex | **동일 연도 대비 백분위** (핵심 지표) |
| `influentialCitationCount` | Semantic Scholar | **실질적 인용** (단순 언급 제외) |
| `primary_topic.score` | OpenAlex | 토픽 매칭 정확도 (0~1) |
| `primary_topic.subfield` | OpenAlex | 분야 분류 |
| `type` | OpenAlex | book / article / review 등 |
| `referenced_works_count` | OpenAlex | 참고문헌 수 (연구 깊이) |
| `is_retracted` | OpenAlex | 철회 논문 필터링 |
| `open_access.is_oa` | OpenAlex | 본문 접근 가능 여부 |

### 스코어링 공식 (0~100)

```python
def quality_score(paper, s2_data=None):
    """논문 품질 점수 계산 (0~100)"""
    score = 0

    # 1. 인용 백분위 (최대 40점) — 가장 중요
    percentile_min = paper.get('cited_by_percentile_year', {}).get('min', 0)
    if percentile_min >= 95:
        score += 40   # 상위 5%
    elif percentile_min >= 90:
        score += 35   # 상위 10%
    elif percentile_min >= 75:
        score += 25   # 상위 25%
    elif percentile_min >= 50:
        score += 15   # 상위 50%

    # 2. 실질적 인용 (최대 25점) — Semantic Scholar
    if s2_data:
        influential = s2_data.get('influentialCitationCount', 0)
        score += min(influential * 2, 25)

    # 3. 토픽 관련성 (최대 15점)
    topic_score = paper.get('primary_topic', {}).get('score', 0)
    score += int(topic_score * 15)

    # 4. 분야 매칭 (최대 10점)
    subfield = paper.get('primary_topic', {}).get('subfield', {}).get('display_name', '')
    field = paper.get('primary_topic', {}).get('field', {}).get('display_name', '')
    if 'History' in subfield:
        score += 10
    elif field == 'Arts and Humanities':
        score += 7
    elif field == 'Social Sciences':
        score += 4

    # 5. 접근성 보너스 (최대 5점)
    if paper.get('open_access', {}).get('is_oa'):
        score += 3
    if paper.get('abstract_inverted_index'):
        score += 2

    # 6. 감점: 철회 논문
    if paper.get('is_retracted'):
        score = 0

    return score

# 등급 기준
# A급 (70+): 무조건 저장, 히스토리 시프트 핵심 소스
# B급 (50-69): 저장, 보조 소스
# C급 (30-49): 조건부 저장 (토픽 희소 시)
# D급 (0-29): 저장하지 않음
```

### 필터링 예시: 잔다르크

| 논문 | 인용 | 백분위 | 분야 | 스코어 | 등급 |
|------|------|--------|------|--------|------|
| Warner, *Image of Female Heroism* (1982) | 177 | 90th+ | Arts & Humanities | ~72 | **A** |
| Sullivan, *Interrogation of Joan of Arc* (1999) | 50 | ~85th | History | ~60 | **B** |
| DeVries, *Military Leader* (1999) | 44 | ~83th | History | ~55 | **B** |
| Feinberg, *Transgender Warriors* (1996) | 412 | 99th+ | Sociology | ~42 | **필터링** (토픽 불일치) |

---

## 5. 용량 계획

### 일일 수집 능력 (무료 한도 기준)

| API | 일일 검색 | 일일 메타데이터 수집 | 비용 |
|-----|----------|-------------------|------|
| OpenAlex | ~200,000 편 발견 | ~200,000 편 (ID조회 무료) | ~$0.40/day |
| Semantic Scholar | ~50,000 편 | ~80,000 편 | 무료 |
| CORE | ~100,000 편 | ~30,000 편 | 무료 |

### 목표별 소요 시간

> **모든 API는 무료**. 아래 "무료 한도 소요일"은 OpenAlex의 일일 무료 할당($1/day)을
> 며칠 쓰느냐의 의미이며, **실제 결제 금액은 $0**이다.

| 목표 | 소요 시간 | 무료 한도 소요일 | 저장 용량 (초록만) | 저장 용량 (본문 포함) |
|------|----------|----------------|------------------|-------------------|
| **10,000 편** | 1일 | 1일 | ~20 MB | ~1 GB |
| **50,000 편** | 3~4일 | 3~4일 | ~100 MB | ~5 GB |
| **100,000 편** | 1주 | ~3일 | ~200 MB | ~10 GB |
| **500,000 편** | 3~4주 | ~8일 | ~1 GB | ~50 GB |
| **900,000 편** | 2개월 | ~15일 | ~1.8 GB | ~90 GB |

### CHALDEAS 역사 토픽 커버리지 추정

| 카테고리 | 토픽 수 | 예시 |
|----------|---------|------|
| 주요 문명 | ~30 | 로마, 한나라, 이집트, 메소포타미아 |
| 주요 전쟁/갈등 | ~150 | 펠로폰네소스 전쟁, 백년전쟁, 세계대전 |
| 주요 사건 | ~500 | 로마 멸망, 흑사병, 프랑스 혁명 |
| 주요 인물 | ~2,000 | 알렉산드로스, 카이사르, 공자, 나폴레옹 |
| 지역 | ~100 | 지중해, 실크로드, 비옥한 초승달 |
| 주제 | ~200 | 무역로, 종교 운동, 기술 혁신 |
| 시대 | ~100 | 청동기, 헬레니즘, 르네상스 |
| **합계** | **~3,000 토픽** | |

**토픽당 평균 논문**: ~300편 선별 → 총 **~900,000편**

---

## 6. DB 통합

### sources 테이블 활용

기존 `sources` 테이블에 그대로 저장한다. 새 테이블 불필요.

```sql
INSERT INTO sources (
    name,           -- 'Joan of Arc: The Image of Female Heroism'
    type,           -- 'secondary'
    archive_type,   -- 'openalex'  (신규 추가)
    author,         -- 'Marina Warner'
    publication_year, -- 1982
    description,    -- 초록 전문 (Tier 1: 항상 저장)
    url,            -- DOI URL
    reliability,    -- 4 (학술 논문 기본값)
    document_id,    -- OpenAlex ID ('W1500819822')
    original_year,  -- 논문이 다루는 시대 (BCE as negative, 해당 시)
    language        -- 'en'
) VALUES (...);
```

### 신규 archive_type 값

| archive_type | 설명 |
|-------------|------|
| `openalex` | OpenAlex에서 발견된 논문 |
| `semantic_scholar` | Semantic Scholar에서만 발견된 논문 |
| `core` | CORE에서 풀텍스트 확보된 논문 |

### Tier 2 본문 저장 시

기존 Book Extractor 파이프라인 재활용:

```
PDF 다운로드 → document_path에 저장
  → 청킹 (2500자 + 200 오버랩)
  → LLM 엔티티 추출
  → EntityMatcher로 DB 매칭
  → text_mentions에 결과 저장
  → event_sources / person_sources 링크 생성
```

### 추가 메타데이터 (JSONB 확장 또는 별도 테이블)

```sql
-- 옵션 A: sources 테이블에 JSONB 컬럼 추가
ALTER TABLE sources ADD COLUMN academic_meta JSONB;

-- 저장 예시:
{
    "openalex_id": "W1500819822",
    "s2_paper_id": "abc123...",
    "cited_by_count": 177,
    "cited_by_percentile": 90,
    "influential_citation_count": 15,
    "quality_score": 72,
    "quality_grade": "A",
    "primary_topic": "Shakespeare, Adaptation, and Literary Criticism",
    "subfield": "Literature and Literary Theory",
    "field": "Arts and Humanities",
    "doi": "10.2307/1870149",
    "open_access": true,
    "oa_url": "https://...",
    "abstract_source": "openalex",  -- or "semantic_scholar"
    "fulltext_source": null,         -- or "core"
    "fulltext_fetched_at": null,     -- Tier 2 가져온 시점
    "topics_searched": ["Joan of Arc", "Hundred Years War"]
}
```

---

## 7. 파이프라인 흐름

### 검색 & 수집 파이프라인

```
┌──────────────────────────────────────────────┐
│  1. 토픽 목록 준비                             │
│     events + persons 테이블에서 키워드 추출      │
│     예: "Joan of Arc", "Battle of Orleans"    │
└──────────────────┬───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────┐
│  2. OpenAlex 검색                             │
│     GET /works?search={keyword}               │
│     &filter=primary_topic.subfield.id:1202    │
│     &sort=cited_by_count:desc                 │
│     &per_page=200                             │
└──────────────────┬───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────┐
│  3. 품질 스코어링                              │
│     cited_by_percentile, topic.score,         │
│     subfield 매칭, is_retracted 체크           │
│     → B급 이상만 통과                          │
└──────────────────┬───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────┐
│  4. 초록 복원 & 저장                           │
│     abstract_inverted_index → plaintext       │
│     sources 테이블에 INSERT                    │
│     academic_meta JSONB에 메타데이터 저장       │
└──────────────────┬───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────┐
│  5. (선택) Semantic Scholar 교차 조회          │
│     DOI로 S2 검색 → influentialCitationCount  │
│     인용 그래프 (references, citations) 확보   │
│     quality_score 업데이트                     │
└──────────────────┬───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────┐
│  6. (선택) 엔티티 링크                         │
│     논문이 다루는 event/person과 자동 매칭      │
│     event_sources, person_sources에 링크      │
└──────────────────────────────────────────────┘
```

### 히스토리 시프트 작성 시 흐름

```
┌──────────────────────────────────────────────┐
│  시프트 작성 시작                               │
│  주제: "잔다르크의 재판과 처형 (1431)"          │
└──────────────────┬───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────┐
│  Tier 1: 초록 자동 제공                        │
│                                              │
│  SELECT * FROM sources                        │
│  WHERE archive_type = 'openalex'              │
│  AND academic_meta->>'quality_grade'           │
│      IN ('A', 'B')                            │
│  AND (description ILIKE '%Joan of Arc%'       │
│       OR id IN (                              │
│         SELECT source_id FROM event_sources   │
│         WHERE event_id = {잔다르크_재판_id}    │
│       ))                                      │
│  ORDER BY (academic_meta->>'quality_score')    │
│           ::int DESC;                         │
│                                              │
│  → 초록 5~10편 LLM 컨텍스트로 제공             │
└──────────────────┬───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────┐
│  LLM 판단                                     │
│  "Sullivan의 재판 분석 본문이 필요하겠다"       │
│  → Tier 2 요청                                │
└──────────────────┬───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────┐
│  Tier 2: 본문 가져오기                         │
│                                              │
│  1. CORE API로 OA 여부 확인                   │
│  2. PDF 다운로드 → PyMuPDF 텍스트 추출         │
│  3. 2500자 청킹 + 오버랩                       │
│  4. 관련 청크만 선별 (키워드/임베딩 매칭)       │
│  5. text_mentions에 저장 (재사용)              │
└──────────────────┬───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────┐
│  시프트 작성 완료                               │
│  source attribution 포함:                     │
│  "Sullivan (1999), reliability: 4,            │
│   cited_by: 50, grade: B"                     │
└──────────────────────────────────────────────┘
```

---

## 8. 구현 단계

### Phase 1: POC (1~2일)

- `backend/scripts/search_academic_papers.py` 작성
- OpenAlex 검색 → 품질 스코어링 → 콘솔 출력
- 잔다르크로 테스트

### Phase 2: DB 통합 (2~3일)

- `sources` 테이블에 `academic_meta` JSONB 컬럼 추가 (Alembic 마이그레이션)
- `archive_type` 값 `openalex`, `semantic_scholar`, `core` 추가
- 검색 결과 → sources INSERT 스크립트

### Phase 3: 대량 수집 (1주)

- 토픽 목록 자동 생성 (events, persons 테이블 기반)
- 배치 스크립트: 토픽별 검색 → 스코어링 → 저장
- 무료 일일 한도 내에서 ~10,000편/일 수집
- 목표: 100,000편 확보

### Phase 4: Tier 2 본문 파이프라인 (1주)

- CORE API 연동
- PDF 다운로드 + PyMuPDF 텍스트 추출
- 기존 Book Extractor 청킹/추출 파이프라인 재활용
- text_mentions 저장

### Phase 5: 히스토리 시프트 연동 (Phase 4 이후)

- 시프트 작성 시 관련 논문 초록 자동 제공
- LLM이 본문 필요 판단 → Tier 2 트리거
- source attribution 자동 생성

---

## 9. 제약 사항

### 본문 접근 한계

- **OA 논문만** 본문 접근 가능 (전체의 ~30~40%)
- JSTOR, Springer 등 유료 저널은 초록만 가능
- 역사학의 핵심 저작이 유료 저널에 있는 경우 많음
- **대안**: DOI + 초록 + 인용 정보만으로도 source attribution은 가능

### 초록 가용률

- OpenAlex: ~80% 논문에 초록 있음 (inverted index)
- Semantic Scholar: ~85% (단, Springer 제외)
- 오래된 논문일수록 초록 누락률 높음
- **대안**: 초록 없는 논문은 제목 + 메타데이터로 최소한의 소스 역할

### 인문학 특수성

- 인문학은 STEM 대비 프리프린트 문화가 약함
- "역사판 arXiv"는 존재하지 않음
- OpenAlex가 인문학 커버리지 최고이므로 메인으로 사용
- 지역/시대별 편향 존재 (서양사 > 동양사, 근현대 > 고대)

---

## 10. 비용 요약

> **전부 무료.** OpenAlex는 무료 API 키에 일일 $1 한도를 제공한다.
> 이 한도 내에서 하루 수십만 편 처리 가능. 실제 결제 = $0.

| 항목 | 비용 |
|------|------|
| OpenAlex API | **무료** (일일 $1 무료 한도, 결제 없음) |
| Semantic Scholar API | **무료** |
| CORE API | **무료** |
| PyMuPDF (본문 추출) | **무료** (오픈소스, 로컬) |
| LLM 엔티티 추출 (Ollama) | **무료** (로컬) |
| LLM 엔티티 추출 (GPT-5-mini 폴백) | ~$0.001/논문 (선택사항) |
| DB 저장 (100K편, 초록만) | ~200 MB |
| **총 비용** | **$0** (Ollama 사용 시) |

---

## 관련 문서

- `docs/ideal/RELATIONSHIPS.md` — 사건 인과 관계 (논문 인용 그래프와 연결)
- `docs/ideal/HISTORY_SHIFT.md` — 히스토리 시프트 기획 (소스로 논문 사용)
- `docs/reference/DATABASE.md` — sources 테이블 스키마
- `CLAUDE.md` — Book Extractor 파이프라인 설명
