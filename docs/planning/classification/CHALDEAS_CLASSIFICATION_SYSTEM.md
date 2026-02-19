# CHALDEAS 분류 시스템 (CHALDEAS Classification System)

> "모든 역사는 **누가(Person)** **어디서(Location)** **언제(Time)** **무엇을(Event)** 했는가로 결정된다."

---

## 문서 상태

**버전**: 2.0 (Master Plan)
**상태**: 활성 개발 중
**이전 문서**: 아래 참조

### 통합된 기존 문서

이 문서는 다음 기존 계획들을 통합/대체합니다:

| 기존 문서 | 상태 | 통합 위치 |
|----------|------|----------|
| `event_hierarchy/00_OVERVIEW.md` | 통합됨 | 섹션 2-3 |
| `event_hierarchy/01_SCHEMA.md` | 통합됨 | 섹션 6 (데이터 모델) |
| `event_hierarchy/07_EVENT_RELATIONS.md` | 통합됨 | 섹션 2.2 |
| `event_hierarchy/08_VECTOR_MODEL.md` | 통합됨 | 섹션 5 |
| `MASTER_PLAN.md` | 대체됨 | 전체 |
| `future_plan/DATA_INGESTION_PIPELINE.md` | 통합됨 | 섹션 8 |
| `future_plan/CURATION_SYSTEM.md` | 통합됨 | 섹션 4, 15 |
| `event_hierarchy/13_FGO_DATA_LAYER.md` | 통합됨 | 섹션 15 |
| `PIPELINE_GUIDE.md` | 통합됨 | 섹션 7-8 |

### 참조 문서 (별도 유지)

| 문서 | 용도 |
|------|------|
| `CLASSIFICATION_METHODOLOGY_REPORT.md` | 학술적 배경 |
| `HIERARCHY_METHODOLOGY_REPORT.md` | 분류 방법론 조사 |
| `GPU_THERMAL_MANAGEMENT.md` | 운영 가이드 |
| `SOURCE_BOOK_MANAGEMENT.md` | 책 목록 관리 |

---

## 문서 개요

본 문서는 CHALDEAS 프로젝트의 궁극적인 분류 시스템을 정의한다. 기존의 단순 계층 구조를 넘어, **상호 연결된 클러스터**, **인물의 역사적 흐름**, **이벤트 벡터** 개념을 기반으로 한 새로운 패러다임을 제시한다.

---

## 1. 철학적 기반

### 1.1 세계 중심 역사관 (World-Centric History)

CHALDEAS는 개인이나 국가 중심이 아닌 **세계(World) 중심**의 역사관을 채택한다.

```
기존 역사관:
  국가 A의 역사 ──────────────────────▶
  국가 B의 역사 ──────────────────────▶
  인물 X의 전기 ──────────────────────▶

CHALDEAS 역사관:
                    ┌─────┐
              ┌────▶│Event│◀────┐
              │     └──┬──┘     │
         ┌────┴───┐    │    ┌───┴────┐
         │ Person │◀───┼───▶│Location│
         └────┬───┘    │    └───┬────┘
              │     ┌──┴──┐     │
              └────▶│Time │◀────┘
                    └─────┘
```

### 1.2 세 가지 핵심 존재 (Three Fundamental Entities)

| 존재 | 정의 | 특성 |
|------|------|------|
| **Person** | 역사의 행위자 | 출생~사망, 관계망, 역할 변화 |
| **Location** | 공간적 존재 | 좌표, 경계 변화, 중첩 가능 |
| **Event** | 시공간 속 변화 | Person과 Location을 연결하는 벡터 |

### 1.3 이벤트는 벡터다 (Event as Vector)

**핵심 개념**: 이벤트는 단순한 "사건"이 아니라, 상태의 변화를 나타내는 **벡터**다.

```
Event = Vector(
    from: State_A,
    to: State_B,
    participants: [Person...],
    space: Location,
    time: TimeRange
)
```

**예시**: 알렉산드로스의 동방원정
```
Event: 페르시아 정복
├── from: 마케도니아 왕국 (그리스 도시국가 패권)
├── to: 헬레니즘 제국 (동서 문명 융합)
├── participants: [알렉산드로스, 다리우스 3세, ...]
├── space: Vector(마케도니아 → 이집트 → 페르시아 → 인더스)
└── time: BCE 334 - BCE 323
```

---

## 2. 분류의 세 축 (Three Axes of Classification)

### 2.1 축 1: 시간 척도 (Temporal Scale) - Braudel 기반

```
┌─────────────────────────────────────────────────────────────┐
│  LONGUE DURÉE (장기 지속)                                   │
│  수백~수천 년 | 문명, 기후, 지리적 구조                      │
│  예: 지중해 문명권, 실크로드, 농경 사회                      │
├─────────────────────────────────────────────────────────────┤
│  CONJUNCTURE (중기 국면)                                    │
│  수십~수백 년 | 왕조, 제국, 경제 순환                        │
│  예: 로마 제국, 산업혁명, 냉전                               │
├─────────────────────────────────────────────────────────────┤
│  ÉVÉNEMENT (단기 사건)                                      │
│  일~수년 | 전투, 조약, 즉위, 사망                            │
│  예: 워털루 전투, 베스트팔렌 조약                            │
└─────────────────────────────────────────────────────────────┘
```

**중요**: 단기 사건(événement)이 중기 국면(conjuncture)에 속하고, 중기 국면이 장기 지속(longue durée)에 속하는 **포함 관계**

### 2.2 축 2: 연결 유형 (Connection Type)

이벤트 간의 관계를 정의하는 유형:

| 유형 | 코드 | 설명 | 예시 |
|------|------|------|------|
| **Part-Of** | `P361` | 포함 관계 | 워털루 전투 ⊂ 나폴레옹 전쟁 |
| **Cause-Effect** | `P1542` | 인과 관계 | 사라예보 사건 → 1차 세계대전 |
| **Succession** | `P1366` | 계승 관계 | 로마 공화정 → 로마 제정 |
| **Opposition** | `P180` | 대립 관계 | 그리스 vs 페르시아 |
| **Parallel** | `custom` | 동시대 관계 | 백년전쟁 ∥ 흑사병 |

### 2.3 축 3: 이벤트 본질 (Event Nature)

```
EVENT NATURE TAXONOMY
│
├── 충돌 (CONFLICT)
│   ├── 전쟁 (war)
│   ├── 전투 (battle)
│   ├── 포위 (siege)
│   ├── 반란 (rebellion)
│   └── 혁명 (revolution)
│
├── 정치 (POLITICAL)
│   ├── 통치 (reign)
│   ├── 왕조 (dynasty)
│   ├── 조약 (treaty)
│   ├── 동맹 (alliance)
│   └── 선거 (election)
│
├── 사회 (SOCIAL)
│   ├── 운동 (movement)
│   ├── 이주 (migration)
│   └── 종교 (religious)
│
├── 경제 (ECONOMIC)
│   ├── 무역 (trade)
│   ├── 위기 (crisis)
│   └── 혁신 (innovation)
│
├── 문화 (CULTURAL)
│   ├── 예술 (art)
│   ├── 학문 (science)
│   └── 발견 (discovery)
│
├── 재난 (DISASTER)
│   ├── 자연재해 (natural)
│   ├── 전염병 (epidemic)
│   └── 기근 (famine)
│
└── 구조 (STRUCTURE)
    ├── 시대 (era)
    ├── 세기 (century)
    └── 문명 (civilization)
```

---

## 3. 클러스터 시스템 (Cluster System)

### 3.1 클러스터란?

**클러스터(Cluster)**는 상호 연결된 이벤트, 인물, 장소의 집합이다. 단순한 계층 구조가 아닌 **그래프 구조**로 표현된다.

```
           ┌─────────────────────────────────────────┐
           │        CLUSTER: 헬레니즘 시대            │
           │                                         │
           │   ┌──────┐      ┌──────┐               │
           │   │알렉산│──────│페르시아│               │
           │   │드로스│      │ 정복  │               │
           │   └──┬───┘      └───┬──┘               │
           │      │    ┌─────────┤                  │
           │      ▼    ▼         ▼                  │
           │   ┌──────────┐  ┌──────┐              │
           │   │디아도코이│  │그리스-│              │
           │   │  전쟁    │  │박트리아│              │
           │   └────┬─────┘  └───┬──┘              │
           │        │            │                  │
           │   ┌────┴────────────┴────┐            │
           │   │    헬레니즘 문화      │            │
           │   └──────────────────────┘            │
           └─────────────────────────────────────────┘
```

### 3.2 클러스터 형성 규칙

클러스터는 다음 조건을 만족할 때 자동 생성:

1. **인물 공유**: 3개 이상의 이벤트가 동일 인물을 공유
2. **시공간 근접**: 동일 지역 + 50년 이내
3. **인과 연쇄**: 원인-결과로 3단계 이상 연결
4. **Wikidata 관계**: P361, P1542 등으로 연결

### 3.3 클러스터 시각화 (Globe View)

```
┌─────────────────────────────────────────────────────────────┐
│                     3D GLOBE VIEW                           │
│                                                             │
│                        .-"""-.                              │
│                      .'  ___  '.                            │
│                     /   (● ●)   \    ← 클러스터 노드        │
│                    |    \___/    |   (크기 = 연결 수)        │
│                    |  ──────────▶|   ← 이벤트 벡터          │
│                     \   '─────' /    (화살표 = 흐름 방향)    │
│                      '.  ___  .'                            │
│                        '-...-'                              │
│                                                             │
│  [Timeline Slider: BCE 500 ──●────── CE 2000]              │
└─────────────────────────────────────────────────────────────┘
```

**시각 요소**:
- **노드 크기**: 연결된 이벤트 수
- **노드 색상**: 이벤트 본질 (전쟁=빨강, 문화=파랑, ...)
- **엣지 굵기**: 관계 강도
- **화살표**: 흐름 방향 (원인→결과, 시간 순서)

---

## 4. 인물의 역사적 흐름 (Person's Historical Flow)

### 4.1 인물 타임라인

각 인물은 생애에 걸친 **이벤트 시퀀스**를 가진다.

```
PERSON: 율리우스 카이사르

BCE 100 ──┬── 출생 (로마)
          │
BCE 60  ──┼── 1차 삼두정치 [POLITICAL]
          │
BCE 58  ──┼── 갈리아 전쟁 시작 [CONFLICT]
          │       │
          │       ├── 알레시아 전투 (BCE 52)
          │       └── 갈리아 정복 완료 (BCE 50)
          │
BCE 49  ──┼── 루비콘 도하 [POLITICAL]
          │
BCE 48  ──┼── 파르살루스 전투 [CONFLICT]
          │
BCE 44  ──┴── 암살 (로마) [END]
```

### 4.2 인물 간 관계 네트워크

```
                    ┌─────────┐
              ┌────▶│ 폼페이우스│◀────┐
              │     └────┬────┘     │
         동맹 │          │ 적대     │ 동맹
              │          ▼          │
         ┌────┴───┐  ┌──────┐  ┌───┴────┐
         │카이사르│◀─│내전   │─▶│크라수스│
         └────┬───┘  └──────┘  └────────┘
              │
         계승 │
              ▼
         ┌────────┐
         │옥타비아누스│
         └────────┘
```

### 4.3 인물 기반 이벤트 분류

**원칙**: 인물의 주요 이벤트(P793)를 기준으로 관련 이벤트 분류

```python
# 의사 코드
for event in pending_events:
    persons = get_persons(event)
    for person in persons:
        major_events = wikidata.get_P793(person)  # significant event
        for major in major_events:
            if time_overlap(event, major):
                assign_parent(event, major)
```

---

## 5. 이벤트 벡터 시스템 (Event Vector System)

### 5.1 벡터의 구성 요소

모든 이벤트는 다음 벡터 속성을 가진다:

```
EventVector {
    // 공간 벡터
    spatial: {
        origin: Location,      // 시작점
        destination: Location, // 종료점 (선택)
        path: [Location...],   // 경로 (선택)
        scope: 'local' | 'regional' | 'global'
    },

    // 시간 벡터
    temporal: {
        start: Date,
        end: Date,
        scale: 'event' | 'conjuncture' | 'longue_duree'
    },

    // 인물 벡터
    personal: {
        actors: [Person...],      // 행위자
        affected: [Person...],    // 영향받은 자
        roles: {Person: Role}     // 역할 매핑
    },

    // 변화 벡터
    transformation: {
        from_state: State,
        to_state: State,
        nature: EventNature
    }
}
```

### 5.2 벡터 시각화

**공간 벡터**: 지구본 위 호(arc)로 표시
```
  마케도니아 ═══════════════════════▶ 인더스 강
            ↑                    ↑
        출발점               도착점

  (알렉산드로스 동방원정의 공간 벡터)
```

**시간 벡터**: 타임라인 위 막대로 표시
```
  BCE 334 ├──────────────────────┤ BCE 323
          │    알렉산드로스 원정    │
          └──────────────────────┘
```

**인물 벡터**: 관계 네트워크로 표시
```
  알렉산드로스 ──정복──▶ 다리우스
       │                   │
       └───계승───▶ 디아도코이
```

---

## 6. 데이터 모델

### 6.1 핵심 테이블 구조

```sql
-- 이벤트 (확장)
CREATE TABLE events_v2 (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    wikidata_id VARCHAR(20),

    -- 시간
    date_start INTEGER,          -- BCE는 음수
    date_end INTEGER,
    temporal_scale VARCHAR(20),  -- 'event', 'conjuncture', 'longue_duree'

    -- 공간
    origin_location_id INTEGER REFERENCES locations(id),
    destination_location_id INTEGER REFERENCES locations(id),
    scope VARCHAR(20),           -- 'local', 'regional', 'global'

    -- 본질
    nature VARCHAR(50),          -- 'war', 'treaty', 'dynasty', ...
    nature_detail VARCHAR(100),

    -- 변화
    from_state TEXT,
    to_state TEXT,

    -- 메타
    confidence FLOAT DEFAULT 0.5,
    source VARCHAR(50),          -- 'wikidata', 'gutenberg', 'manual'

    CONSTRAINT valid_dates CHECK (date_start <= date_end OR date_end IS NULL)
);

-- 클러스터
CREATE TABLE clusters (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    description TEXT,

    -- 시공간 범위
    time_start INTEGER,
    time_end INTEGER,
    center_lat FLOAT,
    center_lng FLOAT,
    radius_km FLOAT,

    -- 통계
    event_count INTEGER DEFAULT 0,
    person_count INTEGER DEFAULT 0,
    connection_strength FLOAT DEFAULT 0
);

-- 클러스터-이벤트 연결
CREATE TABLE cluster_events (
    cluster_id INTEGER REFERENCES clusters(id),
    event_id INTEGER REFERENCES events_v2(id),
    is_core BOOLEAN DEFAULT FALSE,  -- 핵심 이벤트 여부
    PRIMARY KEY (cluster_id, event_id)
);

-- 이벤트 관계 (벡터)
CREATE TABLE event_relations (
    id SERIAL PRIMARY KEY,
    source_event_id INTEGER REFERENCES events_v2(id),
    target_event_id INTEGER REFERENCES events_v2(id),

    relation_type VARCHAR(50),   -- 'part_of', 'caused', 'succeeded', 'opposed', 'parallel'
    wikidata_property VARCHAR(20), -- 'P361', 'P1542', ...

    strength FLOAT DEFAULT 0.5,
    source VARCHAR(50),

    UNIQUE (source_event_id, target_event_id, relation_type)
);

-- 인물 이벤트 역할
CREATE TABLE person_event_roles (
    person_id INTEGER REFERENCES persons(id),
    event_id INTEGER REFERENCES events_v2(id),

    role VARCHAR(100),           -- 'leader', 'participant', 'victim', 'witness'
    is_major BOOLEAN DEFAULT FALSE,

    PRIMARY KEY (person_id, event_id)
);
```

### 6.2 Wikidata 속성 매핑

| Wikidata 속성 | 용도 | CHALDEAS 매핑 |
|--------------|------|---------------|
| P31 | instance of | nature 결정 |
| P361 | part of | event_relations (part_of) |
| P1542 | has effect | event_relations (caused) |
| P1366 | replaced by | event_relations (succeeded) |
| P710 | participant | person_event_roles |
| P793 | significant event | 인물 주요 이벤트 |
| P276 | location | origin_location_id |
| P580/P582 | start/end time | date_start/date_end |

---

## 7. LLM 계층 시스템 (Tiered LLM System)

### 7.1 3단계 난이도 분류

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM TIER SYSTEM                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  TIER 3: 고난이도 (Complex)                         │   │
│  │  모델: gpt-5.1-chat-latest                          │   │
│  │  비용: ~$1.25/1M tokens                             │   │
│  │  용도:                                               │   │
│  │    - 복잡한 인과관계 추론                            │   │
│  │    - 모호한 역사적 맥락 해석                         │   │
│  │    - 다중 이벤트 클러스터 분석                       │   │
│  │    - 충돌하는 정보 해결                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ▲                                  │
│                          │ 실패 시 에스컬레이션             │
│                          │                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  TIER 2: 중난이도 (Moderate)                        │   │
│  │  모델: gpt-5-mini                                   │   │
│  │  비용: ~$0.25/1M tokens                             │   │
│  │  용도:                                               │   │
│  │    - 이벤트-부모 관계 분류                           │   │
│  │    - Wikipedia 제목 매칭                             │   │
│  │    - 인물 역할 추론                                  │   │
│  │    - 이벤트 nature 분류                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ▲                                  │
│                          │ 실패 시 에스컬레이션             │
│                          │                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  TIER 1: 저난이도 (Simple)                          │   │
│  │  모델: llama3.1:8b-instruct-q4_0 (Ollama 로컬)      │   │
│  │  비용: 무료                                          │   │
│  │  용도:                                               │   │
│  │    - 텍스트에서 엔티티 추출 (NER)                    │   │
│  │    - 단순 분류 (전쟁/조약/왕조 등)                   │   │
│  │    - 날짜 파싱 및 정규화                             │   │
│  │    - 명확한 Wikidata 매칭 검증                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 작업별 티어 배정

| 작업 | 티어 | 이유 |
|------|------|------|
| 텍스트 엔티티 추출 | T1 | 패턴 매칭, 명확한 규칙 |
| 날짜 파싱 (BCE/CE) | T1 | 정규식 + 간단한 추론 |
| 이벤트 nature 분류 | T1→T2 | 대부분 T1, 모호하면 T2 |
| Wikidata QID 매칭 | T1→T2 | 정확 매칭 T1, 유사 매칭 T2 |
| 부모 이벤트 분류 | T2 | 컨텍스트 이해 필요 |
| 인물 역할 추론 | T2 | 관계 이해 필요 |
| 인과관계 추론 | T2→T3 | 복잡한 맥락 필요 |
| 클러스터 분석 | T3 | 다중 이벤트 종합 |
| 충돌 정보 해결 | T3 | 판단력 필요 |

### 7.3 에스컬레이션 규칙

```python
class TieredLLM:
    def process(self, task, context):
        # Tier 1 시도
        result = self.tier1_local(task, context)

        if result.confidence >= 0.8:
            return result

        # Tier 2로 에스컬레이션
        result = self.tier2_mini(task, context, tier1_result=result)

        if result.confidence >= 0.7:
            return result

        # Tier 3로 에스컬레이션 (비용 높음, 신중하게)
        if task.importance >= 'high' or context.is_anchor_event:
            result = self.tier3_chat(task, context,
                                     tier1_result=tier1_result,
                                     tier2_result=result)
            return result

        # Tier 3 건너뛰고 "uncertain" 반환
        return Result(status='uncertain', needs_review=True)
```

### 7.4 비용 최적화 전략

```
예상 처리량 (47,000 이벤트 기준):

Tier 1 (로컬): 80% = 37,600건 → $0
Tier 2 (미니): 15% = 7,050건 → ~$5-10
Tier 3 (챗):   5% = 2,350건 → ~$15-25

총 예상 비용: $20-35 (전체 처리)
```

**최적화 규칙**:
1. 배치 처리로 API 호출 최소화
2. 캐싱으로 중복 요청 방지
3. 앵커 이벤트만 Tier 3 사용
4. 야간/주말에 대량 처리 (rate limit 회피)

---

## 8. 신규 책 처리 파이프라인 (Book Ingestion Pipeline)

### 8.1 책 처리 흐름

```
┌─────────────────────────────────────────────────────────────┐
│                  NEW BOOK INGESTION                         │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: 책 메타데이터 추출                                 │
│                                                             │
│  ZIM 파일에서:                                              │
│  - 제목, 저자, 출판년도                                     │
│  - 언어, 장르                                               │
│  - Gutenberg ID                                             │
│                                                             │
│  LLM Tier: N/A (메타데이터 파싱)                           │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: 역사적 관련성 판단                                 │
│                                                             │
│  질문: "이 책이 역사적 이벤트/인물을 다루는가?"             │
│                                                             │
│  - 역사서/전기 → 높음                                       │
│  - 역사 소설 → 중간                                         │
│  - 현대 소설 → 낮음                                         │
│  - 기술/과학 → 맥락에 따라                                  │
│                                                             │
│  LLM Tier: T1 (제목/저자 기반 분류)                        │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: 청킹 (Chunking)                                   │
│                                                             │
│  구조:                                                      │
│  BOOK                                                       │
│  ├── CHAPTER 1                                              │
│  │   ├── chunk_1 (2500자)                                  │
│  │   ├── chunk_2 (2500자, 200자 오버랩)                    │
│  │   └── ...                                               │
│  └── CHAPTER 2                                              │
│      └── ...                                               │
│                                                             │
│  LLM Tier: N/A (규칙 기반)                                 │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: 엔티티 추출                                        │
│                                                             │
│  각 청크에서:                                               │
│  - 인물명 (Person)                                          │
│  - 장소명 (Location)                                        │
│  - 이벤트 멘션 (Event)                                      │
│  - 날짜/시기 (Time)                                         │
│                                                             │
│  LLM Tier: T1 (로컬 llama3.1)                              │
│                                                             │
│  출력 예시:                                                 │
│  {                                                          │
│    "persons": ["Napoleon", "Wellington"],                   │
│    "locations": ["Waterloo", "Belgium"],                    │
│    "events": ["battle", "defeat"],                          │
│    "dates": ["June 18, 1815"]                               │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 5: 엔티티 매칭                                        │
│                                                             │
│  추출된 엔티티를 기존 DB와 매칭:                            │
│                                                             │
│  5a. 정확 매칭 (Exact Match)                               │
│      "Napoleon" → persons.name = 'Napoleon Bonaparte'       │
│      LLM Tier: N/A (DB 쿼리)                               │
│                                                             │
│  5b. 유사 매칭 (Fuzzy Match)                               │
│      "Napolean" (오타) → 유사도 검사                        │
│      LLM Tier: T1                                          │
│                                                             │
│  5c. 신규 엔티티 판단                                       │
│      매칭 실패 → 새 인물/장소인가?                          │
│      LLM Tier: T2                                          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 6: 이벤트 연결                                        │
│                                                             │
│  청크 내 co-occurrence 분석:                                │
│  "Napoleon과 Wellington이 Waterloo에서 1815년에"            │
│  → 워털루 전투와 연결                                       │
│                                                             │
│  6a. 명시적 이벤트 멘션                                     │
│      "Battle of Waterloo" → events.title 매칭              │
│      LLM Tier: T1                                          │
│                                                             │
│  6b. 암시적 이벤트 추론                                     │
│      "Napoleon's final defeat" → 어떤 이벤트?              │
│      LLM Tier: T2                                          │
│                                                             │
│  6c. 신규 이벤트 생성                                       │
│      DB에 없는 이벤트 발견 시                               │
│      LLM Tier: T2 (검증) → T3 (생성)                       │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 7: 관계 추론                                          │
│                                                             │
│  동일 청크 내 엔티티 간 관계:                               │
│  - 인물-인물: "fought against", "allied with"               │
│  - 인물-이벤트: "led", "participated in", "witnessed"       │
│  - 이벤트-이벤트: "caused", "part of", "followed"           │
│                                                             │
│  LLM Tier: T2 (대부분) / T3 (복잡한 관계)                  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 8: 출처 기록                                          │
│                                                             │
│  모든 추출/연결에 출처 명시:                                │
│  {                                                          │
│    "source_type": "gutenberg",                              │
│    "source_id": "pg12345",                                  │
│    "book_title": "A History of the Napoleonic Wars",       │
│    "chapter": "Chapter 15",                                 │
│    "chunk_index": 42,                                       │
│    "text_snippet": "...the decisive battle at Waterloo..." │
│  }                                                          │
│                                                             │
│  LLM Tier: N/A (메타데이터)                                │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 9: 품질 검증                                          │
│                                                             │
│  자동 검증:                                                 │
│  - 시간 일관성 (1815년 인물이 1700년 이벤트 참여?)          │
│  - 공간 일관성 (유럽 인물이 아메리카 이벤트?)               │
│  - 중복 검사 (이미 연결된 관계?)                            │
│                                                             │
│  의심스러운 경우:                                           │
│  LLM Tier: T3 (검증)                                       │
│                                                             │
│  확인 필요 시 → review_queue에 추가                        │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 책 처리 작업 테이블

```sql
-- 책 처리 상태 추적
CREATE TABLE book_processing (
    id SERIAL PRIMARY KEY,
    gutenberg_id VARCHAR(50) UNIQUE,

    -- 메타데이터
    title VARCHAR(500),
    author VARCHAR(300),
    language VARCHAR(10),
    publish_year INTEGER,

    -- 처리 상태
    status VARCHAR(20) DEFAULT 'pending',
    -- 'pending', 'chunking', 'extracting', 'matching',
    -- 'connecting', 'validating', 'done', 'failed'

    -- 통계
    total_chunks INTEGER,
    processed_chunks INTEGER DEFAULT 0,
    extracted_persons INTEGER DEFAULT 0,
    extracted_locations INTEGER DEFAULT 0,
    extracted_events INTEGER DEFAULT 0,
    new_connections INTEGER DEFAULT 0,

    -- 비용 추적
    tier1_calls INTEGER DEFAULT 0,
    tier2_calls INTEGER DEFAULT 0,
    tier3_calls INTEGER DEFAULT 0,
    estimated_cost DECIMAL(10,4) DEFAULT 0,

    -- 타임스탬프
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 청크별 추출 결과
CREATE TABLE book_chunks (
    id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES book_processing(id),

    chapter_num INTEGER,
    chunk_index INTEGER,
    content_preview TEXT,  -- 처음 200자

    -- 추출 결과
    extracted_entities JSONB,
    -- {"persons": [...], "locations": [...], "events": [...], "dates": [...]}

    matched_persons INTEGER[],   -- person_id 배열
    matched_locations INTEGER[], -- location_id 배열
    matched_events INTEGER[],    -- event_id 배열

    -- LLM 처리 정보
    llm_tier_used INTEGER,
    processing_notes TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

-- 텍스트 멘션 (출처 추적용)
CREATE TABLE text_mentions (
    id SERIAL PRIMARY KEY,

    -- 출처
    book_id INTEGER REFERENCES book_processing(id),
    chunk_id INTEGER REFERENCES book_chunks(id),

    -- 대상
    entity_type VARCHAR(20),  -- 'person', 'location', 'event'
    entity_id INTEGER,

    -- 멘션 정보
    mention_text VARCHAR(500),
    context_snippet TEXT,
    confidence FLOAT,

    created_at TIMESTAMP DEFAULT NOW()
);
```

### 8.3 책 우선순위 큐

```sql
-- 책 처리 우선순위
CREATE TABLE book_queue (
    id SERIAL PRIMARY KEY,
    gutenberg_id VARCHAR(50),

    priority INTEGER DEFAULT 5,  -- 1 (highest) to 10

    -- 우선순위 결정 요소
    is_history_book BOOLEAN DEFAULT FALSE,
    is_biography BOOLEAN DEFAULT FALSE,
    covers_anchor_events BOOLEAN DEFAULT FALSE,  -- 주요 이벤트 다룸
    language VARCHAR(10) DEFAULT 'en',

    status VARCHAR(20) DEFAULT 'queued',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 우선순위 자동 계산
CREATE OR REPLACE FUNCTION calculate_book_priority(
    is_history BOOLEAN,
    is_bio BOOLEAN,
    covers_anchors BOOLEAN,
    lang VARCHAR
) RETURNS INTEGER AS $$
BEGIN
    RETURN
        CASE WHEN is_history THEN 0 ELSE 3 END +
        CASE WHEN is_bio THEN 0 ELSE 2 END +
        CASE WHEN covers_anchors THEN 0 ELSE 2 END +
        CASE WHEN lang = 'en' THEN 0 ELSE 1 END +
        1;  -- 최소 1
END;
$$ LANGUAGE plpgsql;
```

### 8.4 처리 예시 (실제 플로우)

```
예시: "The Decline and Fall of the Roman Empire" by Edward Gibbon

1. 메타데이터 추출
   - 제목: The Decline and Fall of the Roman Empire
   - 저자: Edward Gibbon
   - 언어: en
   - 장르: History
   - 우선순위: 1 (역사서 + 앵커 이벤트 다수)

2. 역사적 관련성: HIGH (T1 판단)

3. 청킹: 총 3,500 청크 생성

4. 엔티티 추출 (청크 #42 예시)
   T1 결과:
   {
     "persons": ["Augustus", "Tiberius", "Caligula"],
     "locations": ["Rome", "Capri"],
     "events": ["succession", "reign"],
     "dates": ["14 AD", "37 AD"]
   }

5. 엔티티 매칭
   - "Augustus" → person_id: 1234 (정확 매칭)
   - "Tiberius" → person_id: 1235 (정확 매칭)
   - "Caligula" → person_id: 1236 (정확 매칭)
   - "Rome" → location_id: 1 (정확 매칭)

6. 이벤트 연결
   - "succession" + "14 AD" + "Augustus" + "Tiberius"
     → event_id: 5678 "Death of Augustus" (T2 매칭)
   - "reign" + "Tiberius" + "37 AD"
     → event_id: 5679 "Reign of Tiberius" (T2 매칭)

7. 관계 추론
   - Augustus → Tiberius: "succeeded_by" (T2)
   - Tiberius → Reign of Tiberius: "actor" (T1)

8. 출처 기록
   {
     "source_type": "gutenberg",
     "source_id": "pg25717",
     "book_title": "The Decline and Fall of the Roman Empire",
     "chapter": "Chapter III",
     "mention": "...the death of Augustus in 14 AD..."
   }

9. 품질 검증
   - 시간 일관성: OK (14 AD, 37 AD는 로마 제정기)
   - 공간 일관성: OK (모두 로마 제국 범위)
   - 중복 검사: 3건 중복 발견 → 병합

처리 결과:
- 새 연결: 847건
- 새 멘션: 2,341건
- 비용: T1 $0 + T2 $2.50 + T3 $0.80 = $3.30
- 처리 시간: 4시간
```

---

## 9. 기존 데이터 재활용 전략 (Legacy Data Reuse)

### 9.1 재활용 가능 데이터 상세

```
┌─────────────────────────────────────────────────────────────┐
│                 REUSABLE DATA INVENTORY                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✅ 완전 재활용 (As-Is)                                     │
│  ├── events.wikidata_id IS NOT NULL      : 4,825건        │
│  ├── persons (Wikidata 연결)             : ~3,000건        │
│  ├── locations (좌표 있음)               : ~2,000건        │
│  └── event_parents (source='wikidata')   : 2,424건        │
│                                                             │
│  ⚠️ 검증 후 재활용                                          │
│  ├── events.parent_status='confirmed'    : 2,627건        │
│  │   → Wikidata 없어도 품질 확인됨                          │
│  ├── event_persons (강한 연결)           : ~15,000건       │
│  │   → connection_count >= 3                               │
│  └── event_parents (source='llm', conf>=0.8) : ~400건     │
│                                                             │
│  ❌ 폐기 또는 재검토                                         │
│  ├── events.parent_status='garbage'      : 9,163건        │
│  ├── events.parent_status='unknown'      : 12,067건       │
│  │   → 일부는 살릴 수 있음 (재검토 큐)                      │
│  └── event_parents (source='llm', conf<0.7) : ~300건      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 마이그레이션 스크립트 상세

```python
# poc/scripts/migration/migrate_to_v2.py

def migrate_events():
    """Phase 1: 이벤트 마이그레이션"""

    # 1a. Wikidata 있는 이벤트 (완전 신뢰)
    wikidata_events = db.query("""
        SELECT * FROM events
        WHERE wikidata_id IS NOT NULL
    """)

    for event in wikidata_events:
        nature = fetch_nature_from_wikidata(event.wikidata_id)
        temporal_scale = infer_temporal_scale(event)

        insert_events_v2(
            id=event.id,  # ID 유지
            title=event.title,
            wikidata_id=event.wikidata_id,
            date_start=event.date_start,
            date_end=event.date_end,
            nature=nature,
            temporal_scale=temporal_scale,
            confidence=1.0,
            source='wikidata'
        )

    # 1b. confirmed 이벤트 (검증 후 이전)
    confirmed_events = db.query("""
        SELECT * FROM events
        WHERE parent_status = 'confirmed'
          AND wikidata_id IS NULL
    """)

    for event in confirmed_events:
        # T1으로 nature 추론
        nature = tier1_classify_nature(event.title)

        insert_events_v2(
            id=event.id,
            title=event.title,
            date_start=event.date_start,
            date_end=event.date_end,
            nature=nature,
            confidence=0.8,
            source='legacy_confirmed'
        )

def migrate_relations():
    """Phase 2: 관계 마이그레이션"""

    # Wikidata P361 관계
    wikidata_relations = db.query("""
        SELECT * FROM event_parents
        WHERE source = 'wikidata'
    """)

    for rel in wikidata_relations:
        insert_event_relations(
            source_event_id=rel.event_id,
            target_event_id=rel.parent_event_id,
            relation_type='part_of',
            wikidata_property='P361',
            strength=1.0,
            source='wikidata'
        )

    # 고신뢰 LLM 관계
    llm_relations = db.query("""
        SELECT * FROM event_parents
        WHERE source = 'llm' AND confidence >= 0.8
    """)

    for rel in llm_relations:
        insert_event_relations(
            source_event_id=rel.event_id,
            target_event_id=rel.parent_event_id,
            relation_type='part_of',
            strength=rel.confidence,
            source='llm_legacy'
        )

def create_review_queue():
    """Phase 3: 재검토 큐 생성"""

    # unknown 이벤트 중 인물 연결 있는 것
    reviewable = db.query("""
        SELECT e.* FROM events e
        WHERE e.parent_status = 'unknown'
          AND EXISTS (
              SELECT 1 FROM event_persons ep
              WHERE ep.event_id = e.id
          )
    """)

    for event in reviewable:
        insert_fill_queue(
            event_id=event.id,
            task_type='review_unknown',
            priority=6,  # 낮은 우선순위
            source='migration'
        )
```

### 9.3 데이터 품질 업그레이드 경로

```
┌─────────────────────────────────────────────────────────────┐
│              DATA QUALITY UPGRADE PATH                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Level 0: Raw (garbage/unknown)                             │
│     │                                                       │
│     │ [T1] 기본 검증                                        │
│     ▼                                                       │
│  Level 1: Validated                                         │
│     │  - 제목 유효                                          │
│     │  - 날짜 파싱 성공                                     │
│     │                                                       │
│     │ [T1/T2] Wikidata 매칭 시도                           │
│     ▼                                                       │
│  Level 2: Matched                                           │
│     │  - Wikidata ID 또는 Wikipedia 연결                   │
│     │  - nature 분류됨                                      │
│     │                                                       │
│     │ [T2] 부모 이벤트 연결                                 │
│     ▼                                                       │
│  Level 3: Connected                                         │
│     │  - 최소 1개 부모 연결                                 │
│     │  - 최소 1명 인물 연결                                 │
│     │                                                       │
│     │ [T2/T3] 클러스터 배정                                │
│     ▼                                                       │
│  Level 4: Clustered                                         │
│     │  - 클러스터에 속함                                    │
│     │  - 관계망 내 위치 확정                                │
│     │                                                       │
│     │ [Book/Manual] 출처 추가                              │
│     ▼                                                       │
│  Level 5: Sourced (최고 품질)                               │
│       - 텍스트 멘션 있음                                    │
│       - 다중 출처 확인                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 10. 구축 파이프라인 (Build Pipeline)

**소스**: Wikidata 로컬 덤프 + Wikipedia ZIM

```
┌─────────────────────────────────────────────────────────────┐
│  1. Wikidata에서 주요 이벤트 추출                           │
│     - P31 = war, battle, treaty, dynasty, ...              │
│     - 각 이벤트의 P361 (part of) 관계 추출                  │
│     - 각 이벤트의 P710 (participant) 추출                   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  2. 계층 구조 구축                                          │
│     - P361 체인 따라가기                                    │
│     - 최상위 이벤트 = longue_duree                          │
│     - 중간 이벤트 = conjuncture                             │
│     - 말단 이벤트 = événement                               │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  3. 클러스터 자동 생성                                      │
│     - 시공간 근접 이벤트 군집화                             │
│     - 공유 인물 기반 연결                                   │
│     - 인과 관계 기반 연결                                   │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Phase 2: 텍스트 기반 확장 (Enrichment)

**소스**: Gutenberg ZIM + 기타 텍스트

```
┌─────────────────────────────────────────────────────────────┐
│  1. 텍스트에서 이벤트 멘션 추출                             │
│     - Book Extractor 파이프라인 사용                        │
│     - 인물/장소 co-occurrence 분석                          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  2. 기존 이벤트와 매칭                                      │
│     - EntityMatcher로 Wikidata 이벤트 연결                  │
│     - 새 이벤트는 클러스터에 자동 배치                      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  3. 관계 추론                                               │
│     - 동일 텍스트 내 멘션 = 관계 후보                       │
│     - LLM으로 관계 유형 판단                                │
└─────────────────────────────────────────────────────────────┘
```

### 7.3 Phase 3: 검증 및 정제 (Validation)

```
┌─────────────────────────────────────────────────────────────┐
│  1. 시간 일관성 검증                                        │
│     - 자식 이벤트 ⊂ 부모 이벤트 시간 범위                   │
│     - 원인 이벤트 < 결과 이벤트 시간                        │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  2. 공간 일관성 검증                                        │
│     - 인물 이동 경로 검증                                   │
│     - 지역 이벤트의 장소 일치 여부                          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  3. 중복 제거 및 병합                                       │
│     - 동일 Wikidata ID → 병합                               │
│     - 유사 제목 + 동일 시공간 → 후보 검토                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. 시각화 인터페이스

### 8.1 Globe View (기본 뷰)

```
┌─────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  │                    🌍 GLOBE                         │   │
│  │                                                     │   │
│  │         ●━━━━━━━━━━━━━━━━━━▶●                       │   │
│  │        로마                 이집트                   │   │
│  │                                                     │   │
│  │              ● 카르타고                              │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ BCE 300 ────────●───────────────────────── CE 100   │   │
│  │              현재: BCE 146 (카르타고 멸망)           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [▶ Play] [⏸ Pause] [🔍 Clusters] [👤 Persons] [📍 Events] │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Cluster View (클러스터 상세)

```
┌─────────────────────────────────────────────────────────────┐
│  CLUSTER: 포에니 전쟁 (BCE 264 - BCE 146)                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│     ┌─────────┐         ┌─────────┐         ┌─────────┐    │
│     │1차 전쟁 │────────▶│2차 전쟁 │────────▶│3차 전쟁 │    │
│     │BCE 264  │         │BCE 218  │         │BCE 149  │    │
│     └────┬────┘         └────┬────┘         └────┬────┘    │
│          │                   │                   │          │
│     ┌────┴────┐         ┌────┴────┐         ┌────┴────┐    │
│     │시칠리아 │         │칸나에   │         │카르타고 │    │
│     │ 전투들  │         │ 전투    │         │ 포위    │    │
│     └─────────┘         └─────────┘         └─────────┘    │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  주요 인물: 한니발, 스키피오, 하밀카르                      │
│  주요 장소: 로마, 카르타고, 시칠리아, 히스파니아            │
└─────────────────────────────────────────────────────────────┘
```

### 8.3 Person Flow View (인물 흐름)

```
┌─────────────────────────────────────────────────────────────┐
│  PERSON: 한니발 바르카 (BCE 247 - BCE 183)                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  BCE 247 ─●─ 출생 (카르타고)                               │
│           │                                                 │
│  BCE 218 ─●━━━━━━━━━━━━━━●─ 알프스 횡단                     │
│           │   히스파니아    이탈리아                        │
│           │                                                 │
│  BCE 216 ─●─ 칸나에 전투 (승리)                            │
│           │                                                 │
│  BCE 202 ─●━━━━━━━●─ 자마 전투 (패배)                      │
│           │   이탈리아  아프리카                            │
│           │                                                 │
│  BCE 183 ─●─ 사망 (비티니아)                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. 기존 데이터 마이그레이션

### 9.1 재활용 가능한 데이터

| 현재 데이터 | 건수 | 재활용 방법 |
|------------|------|-------------|
| events (wikidata_id 있음) | 4,825 | 그대로 사용, nature 추가 |
| event_parents (wikidata) | 2,424 | event_relations로 변환 |
| event_persons | 다수 | person_event_roles로 확장 |
| event_locations | 다수 | origin_location_id로 매핑 |

### 9.2 폐기할 데이터

| 현재 데이터 | 이유 |
|------------|------|
| event_parents (llm, confidence < 0.8) | 정확도 낮음 |
| event_parents (period) | 새 시스템에서 재계산 |
| events (parent_status = garbage) | 품질 미달 |

### 9.3 마이그레이션 스크립트 (개요)

```python
def migrate_to_v2():
    # 1. 양질의 이벤트 복사
    good_events = db.query("""
        SELECT * FROM events
        WHERE wikidata_id IS NOT NULL
           OR parent_status = 'confirmed'
    """)

    for event in good_events:
        # nature 추론
        nature = infer_nature_from_wikidata(event.wikidata_id)

        # events_v2에 삽입
        insert_event_v2(event, nature)

    # 2. Wikidata 관계 변환
    wikidata_relations = db.query("""
        SELECT * FROM event_parents WHERE source = 'wikidata'
    """)

    for rel in wikidata_relations:
        insert_event_relation(
            source=rel.event_id,
            target=rel.parent_event_id,
            type='part_of',
            property='P361'
        )

    # 3. 클러스터 자동 생성
    generate_clusters()
```

---

## 10. 성공 지표

### 10.1 데이터 품질 지표

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| Wikidata 연결률 | > 30% | wikidata_id NOT NULL |
| 클러스터 커버리지 | > 80% | cluster_events 존재 |
| 관계 밀도 | > 2.0 | 이벤트당 평균 관계 수 |
| 시간 일관성 | > 95% | 자식 ⊂ 부모 시간 |

### 10.2 사용자 경험 지표

| 지표 | 목표 | 설명 |
|------|------|------|
| 탐색 깊이 | > 5 클릭 | 사용자가 연결을 따라 탐색하는 깊이 |
| 클러스터 발견 | > 3개/세션 | 세션당 발견하는 클러스터 수 |
| 인물 흐름 완성도 | > 70% | 주요 인물의 타임라인 완성도 |

---

## 11. 로드맵

### Phase 1: 기반 구축 (2주)
- [ ] events_v2 테이블 생성
- [ ] Wikidata에서 주요 전쟁/왕조 이벤트 임포트
- [ ] P361 관계로 기본 계층 구축
- [ ] 기존 양질 데이터 마이그레이션

### Phase 2: 클러스터 시스템 (2주)
- [ ] 클러스터 자동 생성 알고리즘
- [ ] 시공간 근접 기반 군집화
- [ ] 인물 공유 기반 연결

### Phase 3: 벡터 시스템 (2주)
- [ ] 이벤트 벡터 속성 추가
- [ ] 공간 벡터 (origin/destination) 추출
- [ ] 인물 역할 추출

### Phase 4: 시각화 (2주)
- [ ] Globe View 클러스터 표시
- [ ] 이벤트 벡터 화살표
- [ ] Person Flow View

### Phase 5: 확장 및 정제 (지속)
- [ ] Gutenberg 텍스트 기반 확장
- [ ] LLM 기반 관계 추론
- [ ] 사용자 피드백 반영

---

## 12. 결론

CHALDEAS 분류 시스템은 단순한 계층 구조를 넘어, **이벤트를 벡터로**, **역사를 그래프로**, **탐색을 여행으로** 만드는 새로운 패러다임이다.

핵심 원칙:
1. **모든 것은 연결되어 있다** - 고립된 이벤트는 없다
2. **이벤트는 변화다** - 정적 사실이 아닌 동적 벡터
3. **인물이 역사를 만든다** - 인물 중심 네비게이션
4. **시간은 다층적이다** - Braudel의 세 척도

이 시스템이 완성되면, 사용자는 마치 **시간 여행자**처럼 역사를 탐험할 수 있다.

---

## 13. 점진적 구축 전략 (Incremental Build Strategy)

### 13.1 핵심 철학: 프레임워크 우선

```
┌─────────────────────────────────────────────────────────────┐
│                    완전한 프레임워크                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  □ □ □ □ □ □ □ □ □ □ □ □ □ □ □ □ □ □ □ □ □ □ □ □  │   │
│  │  □ ■ ■ □ □ ■ □ □ □ ■ ■ ■ □ □ □ ■ □ □ ■ ■ □ □ □ □  │   │
│  │  □ ■ □ □ □ □ □ ■ □ □ □ □ □ ■ □ □ □ □ □ □ □ ■ □ □  │   │
│  │  □ □ □ ■ □ □ □ □ □ □ ■ □ □ □ □ □ ■ □ □ □ □ □ □ □  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ■ = 채워진 데이터    □ = 빈 슬롯 (나중에 채움)            │
└─────────────────────────────────────────────────────────────┘
```

**원칙**: 데이터가 없어도 구조는 완전해야 한다.
- 모든 테이블, 관계, 제약조건을 먼저 정의
- 빈 슬롯은 `NULL` 또는 플레이스홀더로 유지
- 새 데이터는 기존 프레임워크에 삽입

### 13.2 채우기 우선순위 (Fill Priority)

```
Priority 1: 앵커 (Anchors)
├── 주요 전쟁 (100대 전쟁)
├── 주요 왕조 (100대 왕조)
├── 주요 인물 (1000명)
└── 주요 장소 (500곳)

Priority 2: 연결 (Connections)
├── 앵커 간 P361 관계
├── 앵커 간 인과 관계
└── 인물-이벤트 연결

Priority 3: 확장 (Expansion)
├── 앵커 하위 이벤트
├── 2차 인물
└── 세부 장소

Priority 4: 풍부화 (Enrichment)
├── 텍스트 기반 멘션
├── 상세 설명
└── 출처 추가
```

### 13.3 점진적 채우기 파이프라인

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: 스켈레톤 생성                                      │
│                                                             │
│  Wikidata SPARQL:                                           │
│  "P31 = war AND P361 exists" → 주요 전쟁 목록               │
│                                                             │
│  결과: 전쟁 이름, QID, 시작/종료, 부모 이벤트               │
│        (상세 정보는 NULL)                                   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: 앵커 상세화                                        │
│                                                             │
│  각 앵커에 대해:                                            │
│  - Wikipedia ZIM에서 본문 추출                              │
│  - 참여 인물 (P710) 추가                                    │
│  - 장소 정보 추가                                           │
│  - nature 분류                                              │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: 하위 이벤트 연결                                   │
│                                                             │
│  기존 DB 이벤트 중:                                         │
│  - 시간 범위가 앵커 내에 있고                               │
│  - 참여 인물이 겹치고                                       │
│  - 장소가 근접한 것 → 후보로 연결                           │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: 반복 (Iterate)                                     │
│                                                             │
│  - 새 소스 발견 시 → STEP 2로                               │
│  - 중복 발견 시 → 병합                                      │
│  - 오류 발견 시 → 수정                                      │
└─────────────────────────────────────────────────────────────┘
```

### 13.4 중복 탐지 및 병합 (Deduplication & Merge)

#### 중복 탐지 규칙

```python
def is_duplicate(event_a, event_b):
    # Rule 1: 동일 Wikidata ID
    if event_a.wikidata_id == event_b.wikidata_id:
        return DEFINITE_DUPLICATE

    # Rule 2: 제목 유사도 + 시간 일치
    title_sim = fuzzy_ratio(event_a.title, event_b.title)
    time_overlap = calculate_time_overlap(event_a, event_b)

    if title_sim > 0.9 and time_overlap > 0.8:
        return LIKELY_DUPLICATE

    # Rule 3: 동일 인물 + 동일 장소 + 근접 시간
    shared_persons = get_shared_persons(event_a, event_b)
    same_location = event_a.location_id == event_b.location_id
    time_diff = abs(event_a.date_start - event_b.date_start)

    if len(shared_persons) >= 2 and same_location and time_diff < 5:
        return POSSIBLE_DUPLICATE

    return NOT_DUPLICATE
```

#### 병합 전략

```
MERGE STRATEGY
│
├── DEFINITE_DUPLICATE → 자동 병합
│   - Wikidata ID 있는 쪽 우선
│   - 상세 정보가 많은 쪽 우선
│   - 관계는 합집합
│
├── LIKELY_DUPLICATE → 반자동 병합
│   - 후보로 표시
│   - 주기적 검토
│   - 확인 후 병합
│
└── POSSIBLE_DUPLICATE → 수동 검토
    - 플래그 표시
    - UI에서 검토
    - 사용자 판단
```

### 13.5 데이터 품질 상태 추적

```sql
-- 이벤트별 완성도 추적
CREATE TABLE event_completeness (
    event_id INTEGER REFERENCES events_v2(id) PRIMARY KEY,

    -- 기본 정보
    has_title BOOLEAN DEFAULT TRUE,
    has_wikidata BOOLEAN DEFAULT FALSE,
    has_dates BOOLEAN DEFAULT FALSE,
    has_location BOOLEAN DEFAULT FALSE,

    -- 관계 정보
    has_parent BOOLEAN DEFAULT FALSE,
    has_persons BOOLEAN DEFAULT FALSE,
    has_nature BOOLEAN DEFAULT FALSE,

    -- 상세 정보
    has_description BOOLEAN DEFAULT FALSE,
    has_sources BOOLEAN DEFAULT FALSE,

    -- 점수 (0-100)
    completeness_score INTEGER GENERATED ALWAYS AS (
        (has_title::int * 10) +
        (has_wikidata::int * 20) +
        (has_dates::int * 15) +
        (has_location::int * 10) +
        (has_parent::int * 15) +
        (has_persons::int * 10) +
        (has_nature::int * 5) +
        (has_description::int * 10) +
        (has_sources::int * 5)
    ) STORED,

    last_updated TIMESTAMP DEFAULT NOW()
);

-- 전체 시스템 완성도 뷰
CREATE VIEW system_completeness AS
SELECT
    COUNT(*) as total_events,
    AVG(completeness_score) as avg_completeness,
    COUNT(*) FILTER (WHERE completeness_score >= 80) as high_quality,
    COUNT(*) FILTER (WHERE completeness_score >= 50 AND completeness_score < 80) as medium_quality,
    COUNT(*) FILTER (WHERE completeness_score < 50) as low_quality,
    COUNT(*) FILTER (WHERE has_wikidata) as with_wikidata,
    COUNT(*) FILTER (WHERE has_parent) as with_parent
FROM event_completeness;
```

### 13.6 작업 큐 시스템

```sql
-- 채워야 할 작업 큐
CREATE TABLE fill_queue (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events_v2(id),

    task_type VARCHAR(50),  -- 'add_wikidata', 'add_parent', 'add_persons', ...
    priority INTEGER DEFAULT 5,  -- 1 (highest) to 10 (lowest)

    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'in_progress', 'done', 'failed'
    source VARCHAR(50),  -- 'auto', 'manual', 'llm'

    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,

    notes TEXT
);

-- 자동으로 큐 생성하는 트리거
CREATE OR REPLACE FUNCTION generate_fill_tasks()
RETURNS TRIGGER AS $$
BEGIN
    -- Wikidata 없으면 찾기 작업 추가
    IF NEW.wikidata_id IS NULL THEN
        INSERT INTO fill_queue (event_id, task_type, priority)
        VALUES (NEW.id, 'find_wikidata', 3);
    END IF;

    -- 부모 없으면 찾기 작업 추가
    IF NOT EXISTS (SELECT 1 FROM event_relations WHERE source_event_id = NEW.id) THEN
        INSERT INTO fill_queue (event_id, task_type, priority)
        VALUES (NEW.id, 'find_parent', 4);
    END IF;

    -- 인물 연결 없으면 찾기 작업 추가
    IF NOT EXISTS (SELECT 1 FROM person_event_roles WHERE event_id = NEW.id) THEN
        INSERT INTO fill_queue (event_id, task_type, priority)
        VALUES (NEW.id, 'find_persons', 5);
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### 13.7 버전 관리 및 이력

```sql
-- 변경 이력 추적
CREATE TABLE event_history (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events_v2(id),

    field_changed VARCHAR(100),
    old_value TEXT,
    new_value TEXT,

    change_source VARCHAR(50),  -- 'wikidata', 'gutenberg', 'llm', 'manual'
    change_reason TEXT,

    changed_at TIMESTAMP DEFAULT NOW()
);

-- 병합 이력
CREATE TABLE merge_history (
    id SERIAL PRIMARY KEY,

    kept_event_id INTEGER REFERENCES events_v2(id),
    merged_event_id INTEGER,  -- 삭제되므로 FK 없음

    merge_reason TEXT,
    merge_type VARCHAR(20),  -- 'definite', 'likely', 'manual'

    merged_at TIMESTAMP DEFAULT NOW()
);
```

### 13.8 점진적 구축 대시보드 (개념)

```
┌─────────────────────────────────────────────────────────────┐
│                  CHALDEAS BUILD DASHBOARD                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  전체 완성도: ████████░░░░░░░░░░░░ 42%                      │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 카테고리          │ 완료   │ 진행중 │ 대기   │ 점수 │   │
│  ├───────────────────┼────────┼────────┼────────┼──────┤   │
│  │ 앵커 이벤트       │  847   │  153   │   0    │ 85%  │   │
│  │ P361 관계         │ 2,424  │  500   │ 1,000  │ 62%  │   │
│  │ 인물 연결         │ 15,000 │ 5,000  │ 27,000 │ 32%  │   │
│  │ 클러스터          │   120  │   30   │   50   │ 60%  │   │
│  │ 이벤트 벡터       │  500   │ 1,000  │ 45,000 │ 3%   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  오늘의 작업 큐: 342건                                      │
│  ├── find_wikidata: 150건                                  │
│  ├── find_parent: 120건                                    │
│  └── find_persons: 72건                                    │
│                                                             │
│  [▶ 자동 채우기 시작] [📊 상세 통계] [🔄 중복 검토]        │
└─────────────────────────────────────────────────────────────┘
```

---

## 14. 결론 (최종)

CHALDEAS 분류 시스템은:

1. **완전한 프레임워크를 먼저 구축**한다
2. **점진적으로 데이터를 채워나간다**
3. **중복은 발견 즉시 병합**한다
4. **부족한 부분은 큐에 등록**하고 처리한다
5. **모든 변경은 이력으로 추적**한다

이 시스템이 완성되면, 사용자는 마치 **시간 여행자**처럼 역사를 탐험할 수 있고,
개발자는 **점진적으로 세계를 구축**해 나갈 수 있다.

> "로마는 하루아침에 지어지지 않았다. CHALDEAS도 마찬가지다."

---

---

## 15. 역사성 분류 시스템 (Historicity Classification)

### 15.1 존재의 역사성 수준

모든 Person/Event는 **역사적 진실도**에 따라 분류됩니다.

```
┌─────────────────────────────────────────────────────────────┐
│              HISTORICITY LEVELS                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Level 5: DOCUMENTED (문서화된 역사)                        │
│  ├── 정의: 1차 사료로 확인된 존재                           │
│  ├── 예시: 율리우스 카이사르, 나폴레옹, 2차 세계대전        │
│  └── 신뢰도: 95-100%                                        │
│                                                             │
│  Level 4: ATTESTED (증거가 있는 역사)                       │
│  ├── 정의: 고고학/간접 사료로 확인, 일부 불확실             │
│  ├── 예시: 트로이 전쟁 (도시는 실존), 투탕카멘              │
│  └── 신뢰도: 70-95%                                         │
│                                                             │
│  Level 3: SEMI-HISTORICAL (반역사적)                        │
│  ├── 정의: 역사적 핵심 + 전설적 윤색                        │
│  ├── 예시: 샤를마뉴 (실존 + 롤랑의 노래),                  │
│  │         아서왕 (역사적 원형 가능성 + 전설)               │
│  └── 신뢰도: 30-70%                                         │
│                                                             │
│  Level 2: LEGENDARY (전설적)                                │
│  ├── 정의: 역사적 근거 희박, 문화적 실재                    │
│  ├── 예시: 길가메시, 로물루스와 레무스, 쿠훌린             │
│  └── 신뢰도: 5-30%                                          │
│                                                             │
│  Level 1: MYTHOLOGICAL (신화적)                             │
│  ├── 정의: 신화/종교적 존재, 역사적 실재 아님               │
│  ├── 예시: 제우스, 오딘, 아마테라스                         │
│  └── 신뢰도: 0-5% (문화적 실재로만)                         │
│                                                             │
│  Level 0: FICTIONAL (창작물)                                │
│  ├── 정의: 명확히 현대 창작물                               │
│  ├── 예시: 셜록 홈즈, 캡틴 아메리카                         │
│  └── 신뢰도: 0% (메타데이터로만 존재)                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 15.2 역사성 판정 기준

```python
def determine_historicity(entity):
    """엔티티의 역사성 수준 판정"""

    # 1. Wikidata P31 (instance of) 확인
    instance_of = get_wikidata_p31(entity.wikidata_id)

    if 'mythological character' in instance_of:
        return Level.MYTHOLOGICAL

    if 'legendary character' in instance_of:
        return Level.LEGENDARY

    if 'fictional character' in instance_of:
        return Level.FICTIONAL

    # 2. 1차 사료 존재 여부
    primary_sources = count_primary_sources(entity)

    if primary_sources >= 3:
        return Level.DOCUMENTED

    if primary_sources >= 1:
        return Level.ATTESTED

    # 3. 시대 기반 추정
    if entity.date_start and entity.date_start < -1000:
        # BCE 1000년 이전 = 대부분 전설/신화
        if has_archaeological_evidence(entity):
            return Level.ATTESTED
        return Level.LEGENDARY

    # 4. 출처 다양성
    source_types = get_source_types(entity)

    if 'chronicle' in source_types or 'inscription' in source_types:
        return Level.ATTESTED

    if only_literary_sources(source_types):
        return Level.SEMI_HISTORICAL

    return Level.ATTESTED  # 기본값
```

### 15.3 데이터베이스 스키마 추가

```sql
-- 역사성 레벨 ENUM
CREATE TYPE historicity_level AS ENUM (
    'fictional',      -- Level 0
    'mythological',   -- Level 1
    'legendary',      -- Level 2
    'semi_historical', -- Level 3
    'attested',       -- Level 4
    'documented'      -- Level 5
);

-- persons 테이블 확장
ALTER TABLE persons ADD COLUMN historicity historicity_level DEFAULT 'attested';
ALTER TABLE persons ADD COLUMN historicity_notes TEXT;

-- events 테이블 확장
ALTER TABLE events_v2 ADD COLUMN historicity historicity_level DEFAULT 'attested';
ALTER TABLE events_v2 ADD COLUMN historicity_notes TEXT;

-- 역사성 출처
CREATE TABLE historicity_sources (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(20),  -- 'person', 'event'
    entity_id INTEGER,

    source_type VARCHAR(50),  -- 'primary', 'archaeological', 'literary', 'legendary'
    source_name VARCHAR(300),
    source_date INTEGER,      -- 출처 작성 시기

    supports_historicity BOOLEAN,  -- 역사성 지지/반박
    notes TEXT
);
```

---

## 16. FGO 연동 시스템 (Fate/Grand Order Integration)

### 16.1 FGO 연동 목적

1. **사용자 친밀도**: FGO 플레이어가 익숙한 캐릭터로 진입점 제공
2. **시각적 참조**: 서번트 일러스트를 썸네일로 활용 (저작권 주의)
3. **재미 요소**: "이 서번트의 실제 역사" 탐색 유도
4. **데이터 크로스체크**: FGO 설정 vs 실제 역사 비교

### 16.2 FGO 서번트 분류 체계

FGO의 서번트 클래스와 CHALDEAS 매핑:

| FGO 클래스 | 주요 특성 | CHALDEAS 매핑 |
|-----------|----------|---------------|
| Saber | 검사, 기사 | 군사 지도자, 기사 |
| Archer | 궁수, 저격수 | 군사 지도자, 사냥꾼 |
| Lancer | 창병 | 군사 지도자 |
| Rider | 탑승자 | 정복자, 탐험가 |
| Caster | 마술사 | 학자, 종교인, 작가 |
| Assassin | 암살자 | 첩보원, 암살자 |
| Berserker | 광전사 | 군사 지도자 (비정상 상태) |
| Ruler | 통치자 | 종교 지도자, 성인 |
| Avenger | 복수자 | 비극적 인물 |

### 16.3 FGO 데이터 테이블

```sql
-- FGO 서번트 정보
CREATE TABLE fgo_servants (
    id SERIAL PRIMARY KEY,
    servant_id INTEGER UNIQUE,  -- FGO 내부 ID

    name_en VARCHAR(200),
    name_jp VARCHAR(200),
    name_ko VARCHAR(200),

    class VARCHAR(50),
    rarity INTEGER,  -- 1-5

    -- CHALDEAS 연결
    person_id INTEGER REFERENCES persons(id),

    -- 역사성 비교
    fgo_setting TEXT,           -- FGO 내 설정
    historical_accuracy FLOAT,  -- 역사적 정확도 (0-1)
    major_differences TEXT,     -- 주요 차이점

    -- 메타
    fgo_wiki_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);

-- FGO vs 역사 비교 노트
CREATE TABLE fgo_history_comparison (
    id SERIAL PRIMARY KEY,
    servant_id INTEGER REFERENCES fgo_servants(id),

    aspect VARCHAR(100),       -- 'appearance', 'personality', 'abilities', 'events'
    fgo_description TEXT,
    historical_description TEXT,
    accuracy_score FLOAT,      -- 0 (완전 허구) ~ 1 (정확)

    source_reference TEXT
);
```

### 16.4 FGO 연동 예시

```
┌─────────────────────────────────────────────────────────────┐
│  PERSON: 잔 다르크 (Jeanne d'Arc)                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  역사성: DOCUMENTED (Level 5)                               │
│  ├── 재판 기록 존재                                         │
│  ├── 동시대 연대기                                          │
│  └── 복권 재판 기록                                         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  📱 FGO 서번트 정보                                  │   │
│  │                                                      │   │
│  │  클래스: Ruler (☆5)                                  │   │
│  │  진명: ジャンヌ・ダルク                               │   │
│  │                                                      │   │
│  │  FGO 설정 vs 역사:                                   │   │
│  │  ├── 외모: 창작 (실제 초상화 없음)                   │   │
│  │  ├── 성격: 부분 정확 (신앙심, 용기)                  │   │
│  │  ├── 능력: 창작 (성녀 계시 등)                       │   │
│  │  └── 사건: 정확 (오를레앙, 화형)                     │   │
│  │                                                      │   │
│  │  역사 정확도: 65%                                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  관련 이벤트:                                               │
│  ├── 오를레앙 공방전 (1429)                                │
│  ├── 샤를 7세 대관식 (1429)                                │
│  └── 루앙 화형 (1431)                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 16.5 FGO 서번트 우선 처리

FGO 서번트가 있는 인물은 데이터 품질 우선 처리:

```python
FGO_SERVANT_PRIORITY = {
    'アルトリア・ペンドラゴン': 'King Arthur',
    'ギルガメッシュ': 'Gilgamesh',
    'イスカンダル': 'Alexander the Great',
    'ジャンヌ・ダルク': 'Joan of Arc',
    'レオナルド・ダ・ヴィンチ': 'Leonardo da Vinci',
    ' 諸葛孔明': 'Zhuge Liang',
    'クー・フーリン': 'Cú Chulainn',
    '宮本武蔵': 'Miyamoto Musashi',
    'ナポレオン': 'Napoleon Bonaparte',
    # ... 300+ 서번트
}

def prioritize_fgo_persons():
    for servant_name, historical_name in FGO_SERVANT_PRIORITY.items():
        person = find_person_by_name(historical_name)
        if person:
            # 우선순위 상향
            update_fill_queue(person.id, priority=1)
            # 역사성 레벨 검증
            verify_historicity(person)
            # FGO 연결
            link_to_fgo_servant(person, servant_name)
```

---

## 17. 로컬 LLM 벤치마크 계획 (Local LLM Benchmarking)

### 17.1 테스트 목적

Book Extractor 8권 처리 후 로컬 모델(llama3.1:8b) 성능 평가:

```
┌─────────────────────────────────────────────────────────────┐
│              LOCAL LLM BENCHMARK PLAN                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  목표: Tier 1 작업의 로컬 처리 가능 범위 확인               │
│                                                             │
│  테스트 항목:                                               │
│  1. 엔티티 추출 정확도                                      │
│  2. 날짜 파싱 정확도                                        │
│  3. Nature 분류 정확도                                      │
│  4. Wikidata 매칭 검증 정확도                               │
│  5. 처리 속도 (tokens/sec)                                  │
│  6. 메모리 사용량                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 17.2 벤치마크 데이터셋

```python
# 테스트용 골든 데이터셋 (수동 검증됨)
BENCHMARK_DATASET = {
    'entity_extraction': [
        {
            'text': "Napoleon Bonaparte led the French army at Waterloo in 1815.",
            'expected': {
                'persons': ['Napoleon Bonaparte'],
                'locations': ['Waterloo'],
                'events': ['battle'],
                'dates': ['1815']
            }
        },
        # ... 100개 샘플
    ],

    'nature_classification': [
        {'title': 'Battle of Waterloo', 'expected': 'battle'},
        {'title': 'Treaty of Westphalia', 'expected': 'treaty'},
        {'title': 'Tang Dynasty', 'expected': 'dynasty'},
        # ... 200개 샘플
    ],

    'date_parsing': [
        {'text': 'June 18, 1815', 'expected': 1815},
        {'text': '44 BC', 'expected': -44},
        {'text': 'circa 500 BCE', 'expected': -500},
        # ... 100개 샘플
    ]
}
```

### 17.3 벤치마크 실행 스크립트

```python
# poc/scripts/benchmark/local_llm_benchmark.py

def run_benchmark():
    results = {}

    # 1. 엔티티 추출 테스트
    print("Testing Entity Extraction...")
    extraction_results = []
    for sample in BENCHMARK_DATASET['entity_extraction']:
        start = time.time()
        result = tier1_extract_entities(sample['text'])
        elapsed = time.time() - start

        accuracy = calculate_extraction_accuracy(result, sample['expected'])
        extraction_results.append({
            'accuracy': accuracy,
            'time': elapsed
        })

    results['entity_extraction'] = {
        'avg_accuracy': mean([r['accuracy'] for r in extraction_results]),
        'avg_time': mean([r['time'] for r in extraction_results]),
        'min_accuracy': min([r['accuracy'] for r in extraction_results]),
    }

    # 2. Nature 분류 테스트
    print("Testing Nature Classification...")
    nature_results = []
    for sample in BENCHMARK_DATASET['nature_classification']:
        result = tier1_classify_nature(sample['title'])
        correct = result == sample['expected']
        nature_results.append(correct)

    results['nature_classification'] = {
        'accuracy': sum(nature_results) / len(nature_results)
    }

    # 3. 결과 리포트
    print("\n=== BENCHMARK RESULTS ===")
    print(f"Entity Extraction Accuracy: {results['entity_extraction']['avg_accuracy']:.2%}")
    print(f"Nature Classification Accuracy: {results['nature_classification']['accuracy']:.2%}")

    # 4. Tier 승격 기준 판단
    if results['entity_extraction']['avg_accuracy'] < 0.7:
        print("⚠️ Entity extraction needs Tier 2 fallback")

    if results['nature_classification']['accuracy'] < 0.8:
        print("⚠️ Nature classification needs Tier 2 fallback")

    return results
```

### 17.4 성능 임계값

| 작업 | T1 최소 정확도 | 미달 시 조치 |
|------|---------------|-------------|
| 엔티티 추출 | 70% | T2 폴백 활성화 |
| Nature 분류 | 80% | T2 폴백 활성화 |
| 날짜 파싱 | 90% | 규칙 기반으로 전환 |
| Wikidata 검증 | 85% | T2 재검증 |

### 17.5 GPU 열 관리 연동

```python
# GPU 온도 모니터링 (GPU_THERMAL_MANAGEMENT.md 참조)
def run_with_thermal_protection():
    while tasks_remaining():
        temp = get_gpu_temperature()

        if temp > 80:
            print(f"⚠️ GPU temp {temp}°C - cooling down...")
            time.sleep(60)
            continue

        if temp > 70:
            # 배치 사이즈 축소
            batch_size = max(1, batch_size // 2)

        process_batch(batch_size)
```

---

## 18. 최종 아키텍처 요약

```
┌─────────────────────────────────────────────────────────────┐
│                 CHALDEAS COMPLETE ARCHITECTURE              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  데이터 소스                                                │
│  ├── Wikidata (기본, 구조화)                               │
│  ├── Wikipedia ZIM (상세, 텍스트)                          │
│  ├── Gutenberg ZIM (책, 맥락)                              │
│  └── FGO (사용자 친밀도)                                   │
│                                                             │
│  처리 계층                                                  │
│  ├── Tier 1: llama3.1 로컬 (80%, 무료)                     │
│  ├── Tier 2: gpt-5-mini (15%, 저비용)                      │
│  └── Tier 3: gpt-5.1-chat (5%, 고품질)                     │
│                                                             │
│  핵심 개념                                                  │
│  ├── Event as Vector (이벤트 = 변화의 벡터)                │
│  ├── Cluster System (상호 연결된 클러스터)                 │
│  ├── Person Flow (인물의 역사적 흐름)                      │
│  └── Historicity Levels (역사성 5단계)                     │
│                                                             │
│  점진적 구축                                                │
│  ├── 프레임워크 우선 (구조 완전, 데이터 빈칸)              │
│  ├── 앵커부터 채우기 (주요 1000개 먼저)                    │
│  ├── 품질 추적 (완성도 점수)                               │
│  └── 작업 큐 (자동 탐지, 처리)                             │
│                                                             │
│  시각화                                                     │
│  ├── Globe View (3D 지구본)                                │
│  ├── Cluster View (관계망)                                 │
│  └── Person Flow (타임라인)                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

*문서 버전: 2.0 (Master Plan)*
*작성일: 2026-01-31*
*최종 수정: 2026-01-31*
*CHALDEAS Project*
