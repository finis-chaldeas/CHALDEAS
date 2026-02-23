# 세션 로그: 2026-02-20

## 세션 정보
- **목적**: LLM 큐레이션 파이프라인 구현 (GPT-5.1-chat-latest)
- **배경**: DB에 28,331 events와 181,550 sources가 있지만 descriptions 평균 41자, entity_narratives 0건, period_narratives 384건 중 대부분 llama 생성으로 품질 낮음. Wikipedia 원문(sources.content_raw)을 GPT-5.1로 읽고 풍부한 내러티브 생성.

## 한 작업

### 생성한 파일
- `poc/scripts/curate_with_llm.py` - 메인 큐레이션 파이프라인 스크립트 (NEW)
- `poc/data/curation/` - 캐시 및 체크포인트 디렉토리 (NEW)

### 스크립트 구성 (6단계)

| Step | 설명 | API 호출 |
|------|------|----------|
| 0 | 소스 텍스트 캐시 구축 (DB → JSONL) | 없음 |
| 1 | 이벤트 내러티브 생성 (entity_narratives + event_details) | GPT-5.1 |
| 2 | 이벤트 관계 설명 강화 (event_relationships) | GPT-5.1 |
| 3 | Period narrative 업그레이드 (llama → GPT-5.1) | GPT-5.1 |
| 4 | 품질 리포트 | 없음 |
| 5 | 인물 내러티브 생성 (entity_narratives + persons.description) | GPT-5.1 |

### 참조한 기존 코드 패턴
- `poc/scripts/generate_era_narratives.py` - OpenAI 클라이언트, LLM JSON 호출, JSONL 체크포인트
- `poc/scripts/fill_event_relationships.py` - psycopg2 DB 연결, 배치 처리
- `backend/app/models/entity_narrative.py` - EntityNarrative 스키마
- `backend/app/models/associations.py` - event_relationships 스키마
- `backend/app/models/period_narrative.py` - PeriodNarrative 스키마

### 주요 설계 결정
1. **importance 컬럼 자동 감지**: archive DB (importance_score 0-100) vs compact DB (importance 1-5) 모두 지원
2. **스마트 트렁케이션**: 긴 Wikipedia 텍스트는 앞쪽 8,000자 + 뒤쪽 2,000자 유지
3. **JSONL 체크포인트**: 각 단계별 체크포인트로 중단/재개 지원
4. **티어 시스템**: A(>=90), B(>=70), C(>=50) 중요도 기반 처리
5. **양쪽 description 업데이트**: event_details.description과 events.description 모두 업데이트 시도

## 실행 결과 (2026-02-21 완료)

### 전체 실행 요약

| Step | 설명 | 처리 건수 | 성공률 | 비용 | 소요 시간 |
|------|------|----------|--------|------|----------|
| 0 | 소스 캐시 구축 | 5,862 events | 100% | $0 | ~1분 |
| 1 Tier A | 이벤트 내러티브 (importance>=90) | 520 | 98% (511 saved) | ~$4.12 | ~81분 |
| 1 Tier B | 이벤트 내러티브 (importance>=70) | 1,834 | 99% (1,820 saved) | ~$14.67 | ~5.2시간 |
| 2 | 관계 설명 강화 | 296 | 87% (257 updated) | ~$0.59 | ~16분 |
| 3 | Period narrative 업그레이드 | 384 | 100% (384 upgraded) | ~$2.30 | ~62분 |
| 5 Tier A | 인물 내러티브 (importance>=90) | 1,525 | 100% (1,520 saved) | ~$12.16 | ~4.5시간 |
| 4 | 품질 리포트 | - | - | $0 | <1초 |
| **합계** | | **4,541 LLM calls** | | **~$27** | **~13시간** |

### DB 품질 개선 비교

| 지표 | Before | After |
|------|--------|-------|
| entity_narratives (event) | **0건** | **2,332건** (평균 1,130자) |
| entity_narratives (person) | **0건** | **1,524건** (평균 1,582자) |
| event descriptions (gpt-5.1) | 0건 | **2,013건** (평균 386자 vs wikidata 40자) |
| person descriptions (enriched) | 평균 32자 | **1,520건 업데이트** |
| event_relationships (rich) | 0건 | **257건** (100자 이상) |
| period_narratives 모델 | llama3.1 384건 | **gpt-5.1 391건** (평균 1,705자) |

### 에러 분석
- **JSON parse errors** (~1%): 비라틴 문자 제목(그리스어, 체코어, 폴란드어)에서 주로 발생. "Expecting value: line 1 column 1 (char 0)"
- **varchar 오버플로** (3건): events.description_source_url varchar(500) 초과. entity_narratives에는 정상 저장됨
- **max_tokens 에러** (1건): Step 2에서 max_tokens=200 부족

### 생략된 항목
- **이벤트 Tier C** (`--step 1 --tier C`): ~3,508건, ~$10.88 — 비용 절감 위해 생략
- **인물 Tier B** (`--step 5 --tier B`): ~7,182건, ~$57 — 비용 절감 위해 생략
- 필요 시 추후 실행 가능

## 다음 작업
- Compact DB로 데이터 동기화 (export/import) 후 프론트엔드에서 확인
- 프론트엔드에서 enriched descriptions/narratives 표시 구현
- 인물 Tier B 실행 여부 결정 (~$57)
- 실패한 항목 재처리 고려 (--resume 옵션)
