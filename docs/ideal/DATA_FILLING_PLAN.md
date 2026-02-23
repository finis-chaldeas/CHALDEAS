# 핵심 데이터 채우기 기획서

## 현황 한눈에

```
API 구조:     ████████████████████░  95%  — 거의 다 있음 (108+ 엔드포인트)
핵심 데이터:  ████░░░░░░░░░░░░░░░░  20%  — 줌/시간/내러티브 핵심 비어있음
```

| 자산 | 수량 | 상태 |
|------|------|------|
| Wikidata 덤프 | 1.8TB (E:\wikidata\) | 로컬, 무료 |
| Ollama (llama3.1:8b) | 로컬 | 무료 |
| 이벤트 (전부 QID 있음) | 28,331 | 100% Wikidata 매핑 |
| 인물 (전부 QID 있음) | 190,710 | 100% Wikidata 매핑 |
| 장소 (전부 QID 있음) | 17,723 | 100% Wikidata 매핑 |
| 기존 스크립트 | 80+ | poc/scripts/ |
| OpenAI 예산 | ~$7/월 | 필요시만 사용 |

---

## 네 개의 갭, 우선순위 순

### 갭 1: 이벤트 계층 (줌 = 서사 해상도의 전제조건)

**현재**: 28,331 이벤트가 전부 같은 레벨 (hierarchy_level=3, parent=NULL, temporal_scale=NULL)
**목표**: 각 이벤트가 자기 위치를 안다 — 나는 전쟁인가, 전투인가, 전투의 하루인가

#### 무엇을 채워야 하는가

| 컬럼 | 설명 | 채울 방법 |
|------|------|----------|
| `parent_event_id` | 이 이벤트의 부모 (전투 → 전쟁) | Wikidata P361 (part of) |
| `hierarchy_level` | 1=문명/시대, 2=전쟁/운동, 3=전투/사건, 4=세부 | P31 + 제목 패턴으로 분류 |
| `temporal_scale` | evenementielle / conjuncture / longue_duree | date_span + P31로 판정 |
| `is_aggregate` | 하위 이벤트를 포함하는가 | parent가 된 이벤트 = true |

#### 데이터 소스: Wikidata P361 (part of)

모든 이벤트에 QID가 있다.
Wikidata에서 각 이벤트의 P361 (part of) 속성을 조회하면:

```
Q42848 (Battle of Thermopylae) → P361 → Q57237 (Greco-Persian Wars)
Q47364 (Battle of Salamis)     → P361 → Q57237 (Greco-Persian Wars)
Q48314 (Battle of Plataea)     → P361 → Q57237 (Greco-Persian Wars)
```

Q57237이 우리 DB에 있으면 → parent_event_id를 설정.
Q57237이 우리 DB에 없으면 → 새 aggregate 이벤트로 생성.

#### 데이터 소스: Wikidata P31 (instance of) → 계층 레벨 + 시간 스케일

P31이 알려주는 것:

| Wikidata P31 값 | hierarchy_level | temporal_scale |
|-----------------|-----------------|----------------|
| Q178561 (battle) | 3 | evenementielle |
| Q188055 (siege) | 3 | evenementielle |
| Q131569 (treaty) | 3 | evenementielle |
| Q8065 (war) | 2 | conjuncture |
| Q10931 (revolution) | 2 | conjuncture |
| Q133156 (colony) | 2 | conjuncture |
| Q11514315 (historical period) | 1 | longue_duree |
| Q36279 (empire) | 1 | longue_duree |

#### 보조 판정: 제목 패턴 + date_span

P31이 없는 이벤트를 위한 폴백:

| 제목 패턴 | 현재 수량 | 판정 |
|-----------|----------|------|
| "Battle of ..." | 13,475 | level=3, evenementielle |
| "Siege of ..." | 3,254 | level=3, evenementielle |
| "Treaty of ..." | 820 | level=3, evenementielle |
| "...War" / "...Wars" | 1,763 | level=2, conjuncture |
| "...Revolution" | 168 | level=2, conjuncture |

date_span 기반 보조 판정:

| date_end - date_start | temporal_scale |
|----------------------|----------------|
| 0 또는 NULL (단일 시점) | evenementielle |
| 1~10년 | evenementielle |
| 11~50년 | conjuncture |
| 50년+ | longue_duree |

현재 분포: 25,408개 = 단일 시점, 2,243개 = 1~10년, 660개 = 10년+

#### 실행 방법

```
Step 1: Wikidata 덤프에서 P361, P31 추출
  - 입력: events 테이블의 28,331 QID
  - 처리: 1.8TB 덤프를 한 번 스캔, 해당 QID의 P361/P31 수집
  - 출력: {qid: {part_of: [...], instance_of: [...]}} JSON
  - 비용: 무료 (로컬). 시간: ~2-4시간 (HDD)
  - 기존 참고: poc/scripts/wikidata/extract_events_core.py

Step 2: parent_event_id 매핑
  - P361 대상 QID가 DB에 있으면 → parent_event_id 설정
  - DB에 없으면 → Wikidata에서 기본 정보 가져와서 새 aggregate 이벤트 생성
  - 비용: 무료

Step 3: hierarchy_level + temporal_scale 판정
  - P31 기반 1차 판정
  - 제목 패턴 2차 판정
  - date_span 3차 판정
  - 비용: 무료

Step 4: is_aggregate 마킹
  - parent_event_id의 대상이 된 이벤트 = is_aggregate = true
  - 비용: 무료
```

**예상 커버리지: 70~85%** (Wikidata P361이 모든 이벤트에 있진 않지만, P31 + 제목 패턴으로 hierarchy_level/temporal_scale은 거의 전부 채울 수 있음)

**비용: $0**

---

### 갭 2: 장소 이름 시간 범위 (시간 = 차원의 전제조건)

**현재**: 248,761 location_names 중 1% (978건)만 valid_from/until 있음
**목표**: 주요 장소의 이름이 시간에 따라 바뀜

#### 왜 99%가 비어있는가

대부분의 location_names는 다국어 번역(영어/한국어/일본어)이다.
"Athens"의 한국어 이름 "아테네"에는 시간 범위가 필요 없다 (항상 아테네).

**실제로 시간 범위가 필요한 것은 "이름이 바뀐 장소"뿐이다.**

```
Istanbul: Byzantium → Constantinople → Istanbul (3개 이름, 각각 시간 범위 필요)
Mumbai: Bombay → Mumbai (2개)
Beijing: Khanbaliq → Beiping → Beijing (3개)
```

이런 장소는 전체 17,723개 중 **소수**다. 하지만 가장 유명한 도시들이다.

#### 데이터 소스: Wikidata P1448 (official name) + time qualifiers

Wikidata에서 장소의 P1448 속성에는 시간 한정자가 붙어있다:

```
Q406 (Istanbul):
  P1448: "Byzantium"
    P580 (start time): -667
    P582 (end time): 330
  P1448: "Constantinople"
    P580: 330
    P582: 1930
  P1448: "Istanbul"
    P580: 1930
```

#### 실행 방법

```
Step 1: 이름이 바뀐 장소 후보 식별
  - location_names에서 같은 location_id에 2개 이상 이름이 있는 장소 추출
  - 또는: Wikidata 덤프에서 P1448에 time qualifier가 있는 QID 추출
  - 기존 참고: poc/scripts/populate_location_names.py

Step 2: Wikidata 덤프에서 P1448 + P580/P582 추출
  - 입력: 17,723 location QID
  - 출력: {qid: [{name, valid_from, valid_until}, ...]}
  - 비용: 무료. 시간: ~2시간

Step 3: DB 업데이트
  - 기존 location_names 행에 valid_from/valid_until 채우기
  - 새 이름이 발견되면 행 추가
  - 비용: 무료

Step 4: location.get_name_at(year) 검증
  - 모델에 이미 get_name_at() 메서드가 구현되어 있음
  - 프론트엔드에서 현재 연도에 맞는 이름을 표시하도록 연동
```

**예상 커버리지**: 이름이 바뀐 주요 도시 500~1,000곳의 시간 범위 확보.
전체 248K 중 %로는 작지만, **유저가 실제로 보는 유명 장소는 거의 다 커버.**

**비용: $0**

---

### 갭 3: 시대 내러티브 (시간을 움직일 때 이야기가 나오는 것)

**현재**: 7건 (600~500 BCE, 3개 지역 + 2개 글로벌)
**목표**: ~530건 (89개 시대 × 6개 지역)

#### 시대 구분

BCE 3000 ~ CE 2024를 50년 단위로 나누면 약 100개 기간.
데이터가 있는 기간만 하면 약 89개.

각 기간에 대해:
- 글로벌 1개
- 지역별 최대 6개 (europe, east_asia, south_asia, near_east, africa, americas)
- 데이터가 있는 지역만 생성

#### 데이터 소스: 우리 DB + LLM

이미 각 기간에 어떤 이벤트와 인물이 있는지 DB에 있다.
이것을 LLM에 주고 내러티브를 생성한다.

```
프롬프트:
  "Period: 480-431 BCE, Region: Europe
   Top events: Battle of Thermopylae, Battle of Salamis, Battle of Plataea, ...
   Top persons: Pericles, Socrates, Herodotus, ...

   Write:
   1. headline (1 sentence, dramatic)
   2. narrative (200-300 words, storytelling tone)
   3. keywords (5-8 themes)
   4. defining_moment (1 sentence)
   5. quote (a real historical quote from this period)
   6. Also provide Korean translations for headline and narrative."
```

#### 실행 방법

```
Step 1: 기간별 이벤트/인물 집계
  - SQL: 각 50년 구간 × 지역별 top 10 이벤트, top 10 인물
  - 비용: 무료

Step 2: LLM 내러티브 생성
  방법 A: Ollama (llama3.1:8b) — 무료, 품질 중간
    - 530건 × ~500 토큰 = ~265K 토큰
    - 시간: ~2-3시간 (로컬)
    - 비용: $0

  방법 B: GPT-5-mini — 유료, 품질 높음
    - 530건 × ~800 토큰 (입력+출력)
    - 비용: ~$0.50 (0.25/1M tokens × ~2M tokens)

  추천: 방법 B (품질이 유저에게 직접 보이는 텍스트이므로)

Step 3: DB 삽입
  - period_narratives 테이블에 일괄 삽입
  - curated_status = 'auto'로 마킹 (나중에 리뷰 가능)

Step 4: 한국어 번역
  - narrative_ko, headline_ko 컬럼
  - Ollama로 번역하면 무료, GPT로 하면 ~$0.30 추가
```

**예상 커버리지: 100%** (데이터가 있는 모든 기간에 대해 생성 가능)

**비용: ~$1** (GPT-5-mini 사용 시)

---

### 갭 4: 이벤트-장소 연결 보강

**현재**: primary_location_id 있는 이벤트 = 21,271 (75%), event_locations 테이블 = 4,612 (16%)
**목표**: 위치 없는 7,060개 이벤트에 위치 부여

#### 상황 정리

사실 75%의 이벤트는 이미 primary_location_id가 있다.
지구본 마커 표시에는 이것으로 충분하다.

진짜 문제는 나머지 **25% (7,060개)가 지구본에 안 뜨는 것**.

#### 데이터 소스: Wikidata P276 (location)

```
Q12548 (Battle of Hastings) → P276 → Q202143 (Hastings, East Sussex)
```

P276이 없으면:
- P625 (coordinate location) 직접 사용
- P17 (country) → 국가 수도 좌표로 대체

#### 실행 방법

```
Step 1: 위치 없는 7,060개 이벤트의 QID 추출

Step 2: Wikidata 덤프에서 P276, P625, P17 추출
  - 기존 참고: poc/scripts/wikidata/match_event_locations.py (이미 존재!)
  - 비용: 무료

Step 3: 매칭
  - P276 대상 QID가 locations 테이블에 있으면 → primary_location_id 설정
  - 없으면 → Wikidata에서 좌표 가져와서 새 location 생성
  - P276도 P625도 없으면 → P17 (국가) 수도로 대체

Step 4: event_locations 테이블 보강 (다중 위치 이벤트)
  - aggregate 이벤트 (전쟁 등)의 자식들 위치를 모아서 부모에도 연결
  - 갭 1의 parent_event_id 작업이 선행되어야 함
```

**예상 커버리지: 75% → 90%+**

**비용: $0**

---

## 실행 순서와 의존관계

```
               ┌──────────────────────┐
               │ 갭 1: 이벤트 계층     │ ← 가장 먼저. 줌 = 서사의 전제조건.
               │ Wikidata P361 + P31  │
               │ 비용: $0, 시간: 1일   │
               └──────────┬───────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌─────────────────┐ ┌──────────────┐ ┌──────────────────┐
│ 갭 2: 장소 이름  │ │ 갭 3: 내러티브│ │ 갭 4: 이벤트 위치 │
│ Wikidata P1448  │ │ DB + LLM     │ │ Wikidata P276    │
│ $0, 반나절      │ │ ~$1, 반나절   │ │ $0, 반나절        │
│                 │ │              │ │ (갭1 필요)         │
└─────────────────┘ └──────────────┘ └──────────────────┘
```

1. **갭 1 먼저** — 다른 모든 것의 기반. 이벤트 계층이 없으면 줌이 안 되고, 갭 4의 aggregate 위치 집계도 안 됨.
2. **갭 2, 3, 4는 병렬** — 서로 독립적. 갭 1 완료 후 동시 진행 가능. 단, 갭 4는 갭 1의 parent_event_id에 의존.

---

## 비용 총정리

| 작업 | 데이터 소스 | 비용 |
|------|-----------|------|
| 갭 1: 이벤트 계층 | Wikidata 덤프 (로컬) | $0 |
| 갭 2: 장소 이름 시간 | Wikidata 덤프 (로컬) | $0 |
| 갭 3: 시대 내러티브 | DB + GPT-5-mini | ~$1 |
| 갭 4: 이벤트 위치 | Wikidata 덤프 (로컬) | $0 |
| **합계** | | **~$1** |

Ollama만 쓰면 $0. 내러티브 품질을 위해 GPT를 쓰면 ~$1.

---

## 기존 스크립트 활용

이미 있는 관련 스크립트:

| 스크립트 | 용도 | 재활용 |
|---------|------|--------|
| `poc/scripts/wikidata/extract_events_core.py` | Wikidata에서 이벤트 데이터 추출 | 갭 1에 확장 |
| `poc/scripts/populate_location_names.py` | 장소 이름 채우기 | 갭 2에 확장 (시간 범위 추가) |
| `poc/scripts/wikidata/match_event_locations.py` | 이벤트-장소 매칭 | 갭 4에 직접 사용 |
| `poc/scripts/extract_p17_from_dump.py` | P17 (국가) 추출 | 갭 4 폴백으로 사용 |
| `poc/scripts/seed_territories.py` | 영토 시딩 | 참고 |
| `poc/scripts/import_territory_locations.py` | 영토-장소 매핑 | 참고 |
| `poc/scripts/classify_connections.py` | 연결 분류 | 갭 1 인과관계 참고 |

---

## 검증 방법

### 갭 1 검증 (이벤트 계층)
```sql
-- parent가 설정된 이벤트 비율
SELECT count(*) FILTER (WHERE parent_event_id IS NOT NULL) * 100.0 / count(*)
FROM events;
-- 목표: 30% 이상

-- hierarchy_level 분포
SELECT hierarchy_level, count(*) FROM events GROUP BY hierarchy_level ORDER BY 1;
-- 기대: level 1 < level 2 < level 3 (피라미드)

-- temporal_scale 분포
SELECT temporal_scale, count(*) FROM events GROUP BY temporal_scale;
-- 기대: evenementielle >> conjuncture >> longue_duree
```

### 갭 2 검증 (장소 이름)
```sql
-- 시간 범위가 있는 이름 수
SELECT count(*) FROM location_names WHERE valid_from IS NOT NULL;
-- 목표: 2,000+ (주요 도시들)

-- 실제 이름 변화 테스트
SELECT ln.name, ln.valid_from, ln.valid_until
FROM location_names ln JOIN locations l ON ln.location_id = l.id
WHERE l.name = 'Istanbul' ORDER BY ln.valid_from;
-- 기대: Byzantium → Constantinople → Istanbul
```

### 갭 3 검증 (내러티브)
```sql
SELECT count(*) FROM period_narratives;
-- 목표: 400+

SELECT period_start, region, LEFT(headline, 50) FROM period_narratives
ORDER BY period_start, region LIMIT 20;
-- 기대: 다양한 시대와 지역
```

### 갭 4 검증 (위치)
```sql
SELECT count(*) FILTER (WHERE primary_location_id IS NOT NULL) * 100.0 / count(*)
FROM events;
-- 목표: 90%+
```

---

## 달성 후 상태

```
                          Before    After
이벤트 계층:              0%        70~85%
장소 이름 시간 범위:      1%        주요 도시 90%+
시대 내러티브:            7건       400~530건
이벤트 위치:              75%       90%+
```

이것이 채워지면 ideal 문서에서 말한:
- **줌 = 서사 해상도** → hierarchy_level로 줌별 다른 이벤트 표시 가능
- **시간 = 세계의 차원** → 장소 이름 변화 + 시대 내러티브 작동
- **"그래서 어떻게 된 거야?"** → event_connections 20K + 계층 구조로 인과/포함 탐색

가 **데이터 수준에서 가능해진다.**
