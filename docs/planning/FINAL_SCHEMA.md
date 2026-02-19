# CHALDEAS 최종 스키마

> **버전**: 1.0
> **작성일**: 2026-02-05
> **상태**: 확정 대기

---

## 핵심 철학

> **"모든 역사는 누가(Person) 어디서(Location) 언제(Time) 무엇을(Event) 했는가로 결정된다."**
> **"모든 정보에는 출처(Source)가 있어야 한다."**

---

## 전체 구조

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CHALDEAS 데이터 모델                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐           │
│  │  SOURCES    │────►│  MENTIONS   │────►│  ENTITIES   │           │
│  │  (출처 원문) │     │ (출처→대상)  │     │ (모든 엔티티)│           │
│  └─────────────┘     └─────────────┘     └──────┬──────┘           │
│                                                  │                  │
│        ┌────────────────┬────────────────┬──────┴───────┐          │
│        ▼                ▼                ▼              ▼          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │
│  │ persons  │    │locations │    │  events  │    │  groups  │     │
│  │  (누가)   │    │ (어디서)  │    │ (무엇을)  │    │  (집단)   │     │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘     │
│       │               │               │               │            │
│       │          ┌────┴─────┐         │               │            │
│       │          │territories│        │               │            │
│       │          │  (영역)   │         │               │            │
│       │          └──────────┘         │               │            │
│       │                               │               │            │
│       └───────────────┬───────────────┴───────────────┘            │
│                       ▼                                             │
│                 ┌──────────┐                                        │
│                 │  LINKS   │                                        │
│                 │(엔티티관계)│                                        │
│                 └──────────┘                                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 테이블 목록 (13개)

### 핵심 엔티티 (5개)
| # | 테이블 | 설명 | 의존성 |
|---|--------|------|--------|
| 1 | `locations` | 점 (좌표가 있는 장소) | 없음 |
| 2 | `territories` | 영역 (점들의 집합, 국가/지역) | 없음 |
| 3 | `persons` | 개인 | locations |
| 4 | `groups` | 집단 (개인들의 집합) | territories |
| 5 | `events` | 사건 | locations |

### 출처 시스템 (2개)
| # | 테이블 | 설명 | 의존성 |
|---|--------|------|--------|
| 6 | `sources` | 출처 원문 | 없음 |
| 7 | `mentions` | 출처 → 엔티티 연결 | sources, 모든 엔티티 |

### 관계 테이블 (6개)
| # | 테이블 | 설명 | 의존성 |
|---|--------|------|--------|
| 8 | `links` | 엔티티 간 관계 | 모든 엔티티 |
| 9 | `location_names` | 장소의 시대별 이름 | locations |
| 10 | `territory_locations` | 영역 ↔ 장소 (시기별) | territories, locations |
| 11 | `group_members` | 집단 ↔ 개인 (시기별) | groups, persons |
| 12 | `event_participants` | 이벤트 참여자 | events, persons, groups, territories |
| 13 | `event_locations` | 이벤트 발생 장소 | events, locations |

---

## 상세 스키마

### 1. locations (점)

모든 역사적 지점. **좌표 필수**.

```sql
CREATE TABLE locations (
    id SERIAL PRIMARY KEY,

    -- 식별
    wikidata_id VARCHAR(20) UNIQUE,

    -- 이름 (현재 기준 대표명)
    name VARCHAR(255) NOT NULL,
    name_ko VARCHAR(255),

    -- 좌표 (필수!)
    latitude DECIMAL(10, 7) NOT NULL,
    longitude DECIMAL(10, 7) NOT NULL,

    -- 분류
    location_type VARCHAR(50) DEFAULT 'point',
        -- point: 도시, 건물, 전장
        -- natural: 산, 강, 호수
        -- sea: 바다, 해협

    -- 물리적 계층 (경복궁 → 서울, 불변)
    parent_location_id INTEGER REFERENCES locations(id),

    -- 메타
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_locations_wikidata ON locations(wikidata_id);
CREATE INDEX idx_locations_coords ON locations(latitude, longitude);
CREATE INDEX idx_locations_name ON locations(name);
```

### 1a. location_details (장소 상세 — 1:1)

장소의 부가 정보 (설명, 위키피디아 링크 등).

```sql
CREATE TABLE location_details (
    location_id INTEGER PRIMARY KEY REFERENCES locations(id) ON DELETE CASCADE,
    description TEXT,
    description_ko TEXT,
    description_ja TEXT,
    description_source VARCHAR(50),
    description_source_url VARCHAR(500),
    wikipedia_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 2. territories (영역)

국가, 제국, 지역 등. **점들의 시기별 집합**.

```sql
CREATE TABLE territories (
    id SERIAL PRIMARY KEY,

    -- 식별
    wikidata_id VARCHAR(20) UNIQUE,

    -- 이름
    name VARCHAR(255) NOT NULL,
    name_ko VARCHAR(255),

    -- 분류
    territory_type VARCHAR(50) NOT NULL,
        -- country: 국가
        -- empire: 제국
        -- region: 지역 (Balkans, Middle East)
        -- continent: 대륙

    -- 존속 기간 (BCE 음수)
    founded_year INTEGER,
    dissolved_year INTEGER,

    -- 메타
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_territories_wikidata ON territories(wikidata_id);
CREATE INDEX idx_territories_type ON territories(territory_type);
```

### 3. persons (개인) — 슬림 노드

역사적 인물의 **핵심 정체성**만 저장. 상세정보는 `person_details`, 별칭은 `person_names`.

> **원칙**: 인물은 이벤트를 시간순으로 꿰는 실(thread)이다. 핵심 노드는 불변.

```sql
CREATE TABLE persons (
    id SERIAL PRIMARY KEY,

    -- 식별
    wikidata_id VARCHAR(20) UNIQUE,

    -- 대표명 (현재 기준)
    name VARCHAR(255) NOT NULL,
    name_ko VARCHAR(255),
    name_ja VARCHAR(255),

    -- 시간축 북엔드 (흐름의 시작/끝)
    birth_year INTEGER,   -- BCE 음수. NULL = 불명
    death_year INTEGER,   -- NULL = 불명 또는 생존

    -- 활동기 (탄생/사망 불명 시 대체)
    floruit_start INTEGER,  -- fl. 시작
    floruit_end INTEGER,    -- fl. 종료

    -- 공간축 앵커
    birthplace_id INTEGER REFERENCES locations(id),
    deathplace_id INTEGER REFERENCES locations(id),

    -- 분류
    role VARCHAR(255),          -- king, philosopher, general, prophet 등
    certainty VARCHAR(20) DEFAULT 'fact',
        -- fact/probable/legendary/mythological

    -- 메타
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_persons_wikidata ON persons(wikidata_id);
CREATE INDEX idx_persons_name ON persons(name);
CREATE INDEX idx_persons_years ON persons(birth_year, death_year);
```

### 3a. person_details (인물 상세 — 1:1)

노드 정체성이 아닌 부가 정보.

```sql
CREATE TABLE person_details (
    person_id INTEGER PRIMARY KEY REFERENCES persons(id) ON DELETE CASCADE,
    slug VARCHAR(255),
    wikipedia_url VARCHAR(500),
    image_url VARCHAR(500),
    birth_month INTEGER, birth_day INTEGER,
    death_month INTEGER, death_day INTEGER,
    birth_date_precision VARCHAR(20) DEFAULT 'year',
    death_date_precision VARCHAR(20) DEFAULT 'year',
    biography TEXT,
    biography_ko TEXT,
    biography_ja TEXT,
    biography_source VARCHAR(50),
    biography_source_url VARCHAR(500),
    category_id INTEGER REFERENCES categories(id),
    era VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 3b. person_names (인물 별칭 — 1:M)

같은 인물의 다양한 이름 (언어/시대/문맥별).

```sql
CREATE TABLE person_names (
    id SERIAL PRIMARY KEY,
    person_id INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    name_ko VARCHAR(255),
    name_ja VARCHAR(255),
    valid_from INTEGER,
    valid_until INTEGER,
    language VARCHAR(10) DEFAULT 'en',
    is_primary BOOLEAN DEFAULT FALSE,
    name_type VARCHAR(30) DEFAULT 'official',
        -- official/regnal/epithet/religious/alternate/romanized/native
    source VARCHAR(100),
    wikidata_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_person_names_person ON person_names(person_id);
CREATE INDEX idx_person_names_name ON person_names(name);
```

### 4. groups (집단)

군대, 종교단체, 민족, 정치조직 등. **개인들의 집합**.

```sql
CREATE TABLE groups (
    id SERIAL PRIMARY KEY,

    -- 식별
    wikidata_id VARCHAR(20) UNIQUE,

    -- 이름
    name VARCHAR(255) NOT NULL,
    name_ko VARCHAR(255),

    -- 분류
    group_type VARCHAR(50) NOT NULL,
        -- military: 군대 (Roman Legion, Wehrmacht)
        -- religious: 종교단체 (Knights Templar)
        -- ethnic: 민족 (Gauls, Mongols)
        -- political: 정치조직 (Senate)

    -- 존속 기간
    founded_year INTEGER,
    dissolved_year INTEGER,

    -- 소속 영역 (Wehrmacht → Nazi Germany)
    territory_id INTEGER REFERENCES territories(id),

    -- 설명
    description TEXT,

    -- 메타
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_groups_wikidata ON groups(wikidata_id);
CREATE INDEX idx_groups_type ON groups(group_type);
```

### 5. events (사건)

역사적 사건.

```sql
CREATE TABLE events (
    id SERIAL PRIMARY KEY,

    -- 식별
    wikidata_id VARCHAR(20) UNIQUE,

    -- 제목
    title VARCHAR(500) NOT NULL,
    title_ko VARCHAR(500),

    -- 시기 (BCE 음수)
    date_start INTEGER NOT NULL,
    date_end INTEGER,
    date_precision VARCHAR(20) DEFAULT 'year',
        -- day, month, year, decade, century

    -- 분류
    event_type VARCHAR(100),
        -- battle, war, treaty, revolution, etc.

    -- 계층 (D-Day → Operation Overlord → WWII)
    parent_event_id INTEGER REFERENCES events(id),
    hierarchy_level INTEGER DEFAULT 3,
        -- 1: mega (세계대전)
        -- 2: aggregate (백년전쟁)
        -- 3: major (주요 전투)
        -- 4: minor (소규모)

    -- 주요 위치 (빠른 조회용)
    primary_location_id INTEGER REFERENCES locations(id),

    -- 설명 (여러 출처 종합 후 정서)
    description TEXT,
    description_model VARCHAR(50),
    description_at TIMESTAMP,

    -- 메타
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_events_wikidata ON events(wikidata_id);
CREATE INDEX idx_events_dates ON events(date_start, date_end);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_parent ON events(parent_event_id);
```

---

### 6. sources (출처 원문) ⭐ 핵심!

**모든 정보의 근거가 되는 원문.**

```sql
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,

    -- 출처 유형
    source_type VARCHAR(20) NOT NULL,
        -- wikidata: Wikidata 엔티티
        -- wikipedia: Wikipedia 문서
        -- book: 책 (Gutenberg 등)
        -- academic: 학술 자료
        -- primary: 1차 사료

    -- 출처 정보
    title VARCHAR(500) NOT NULL,
    author VARCHAR(255),
    publication_year INTEGER,
    original_year INTEGER,      -- 원저 작성년도 (BCE 음수)
    language VARCHAR(10) DEFAULT 'en',

    -- 원문 (핵심!)
    content_raw TEXT NOT NULL,

    -- 책인 경우 청크 정보
    chapter VARCHAR(200),
    chunk_index INTEGER,

    -- 외부 참조
    url TEXT,
    wikidata_id VARCHAR(20),    -- 출처 자체의 QID (책이면 책의 QID)
    gutenberg_id INTEGER,

    -- 신뢰도 (1-5)
    reliability INTEGER DEFAULT 3,

    -- 메타
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sources_type ON sources(source_type);
CREATE INDEX idx_sources_wikidata ON sources(wikidata_id);
CREATE INDEX idx_sources_title ON sources(title);
```

### 7. mentions (출처 → 엔티티 연결) ⭐ 핵심!

**출처에서 특정 엔티티를 언급하는 부분.**

```sql
CREATE TABLE mentions (
    id SERIAL PRIMARY KEY,

    -- 출처
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,

    -- 언급 대상 (polymorphic)
    target_type VARCHAR(20) NOT NULL,
        -- person, location, territory, group, event, link
    target_id INTEGER NOT NULL,

    -- 언급 내용 (핵심!)
    evidence_raw TEXT NOT NULL,

    -- 출처 내 위치 (선택)
    position_start INTEGER,
    position_end INTEGER,

    -- 메타
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_mentions_source ON mentions(source_id);
CREATE INDEX idx_mentions_target ON mentions(target_type, target_id);
```

**사용 예시:**

```
sources:
  id: 100
  source_type: wikipedia
  title: "Battle of Waterloo"
  content_raw: "The Battle of Waterloo was fought on 18 June 1815..."

mentions:
  source_id: 100
  target_type: event
  target_id: (워털루 전투 ID)
  evidence_raw: "The Battle of Waterloo was fought on 18 June 1815, near Waterloo..."

  source_id: 100
  target_type: person
  target_id: (나폴레옹 ID)
  evidence_raw: "Napoleon commanded the French forces..."
```

---

### 8. links (엔티티 간 관계)

**두 엔티티 사이의 관계. 출처(mentions)로 뒷받침.**

```sql
CREATE TABLE links (
    id SERIAL PRIMARY KEY,

    -- 연결 (from → to)
    from_type VARCHAR(20) NOT NULL,
    from_id INTEGER NOT NULL,
    to_type VARCHAR(20) NOT NULL,
    to_id INTEGER NOT NULL,

    -- 관계 분류
    category VARCHAR(20),
        -- family: 가족/혈연
        -- political: 정치적 (군주-신하, 동맹)
        -- military: 군사적 (지휘관, 참전)
        -- cultural: 문화적 (스승-제자)
        -- temporal: 시간적 (선행, 후속)
        -- spatial: 공간적 (발생 장소)

    -- 시간 범위 (선택)
    date_start INTEGER,
    date_end INTEGER,

    -- 근거 (여러 mentions 종합 후 정서)
    evidence TEXT,
    evidence_model VARCHAR(50),
    evidence_at TIMESTAMP,

    -- 메타
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_links_from ON links(from_type, from_id);
CREATE INDEX idx_links_to ON links(to_type, to_id);
CREATE INDEX idx_links_category ON links(category);
```

---

### 9. location_names (시대별 장소 이름)

```sql
CREATE TABLE location_names (
    id SERIAL PRIMARY KEY,
    location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,

    -- 이름
    name VARCHAR(255) NOT NULL,
    name_ko VARCHAR(255),

    -- 유효 기간 (BCE 음수)
    valid_from INTEGER,
    valid_until INTEGER,

    -- 언어
    language VARCHAR(10) DEFAULT 'en',
    is_primary BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_location_names_location ON location_names(location_id);
CREATE INDEX idx_location_names_period ON location_names(valid_from, valid_until);
```

### 10. territory_locations (영역 ↔ 장소)

**어떤 시기에 어떤 장소가 어떤 영역에 속했는지.**

```sql
CREATE TABLE territory_locations (
    id SERIAL PRIMARY KEY,
    territory_id INTEGER NOT NULL REFERENCES territories(id) ON DELETE CASCADE,
    location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,

    -- 소속 기간
    valid_from INTEGER,
    valid_until INTEGER,

    -- 관계 유형
    relation_type VARCHAR(50) DEFAULT 'contains',
        -- contains: 영토에 포함
        -- capital: 수도

    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(territory_id, location_id, valid_from)
);

CREATE INDEX idx_territory_locations_territory ON territory_locations(territory_id);
CREATE INDEX idx_territory_locations_location ON territory_locations(location_id);
```

### 11. group_members (집단 ↔ 개인)

**어떤 시기에 누가 어떤 집단에 속했는지.**

```sql
CREATE TABLE group_members (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,

    -- 소속 기간
    valid_from INTEGER,
    valid_until INTEGER,

    -- 역할
    role VARCHAR(100),
        -- leader, commander, founder, member, etc.

    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(group_id, person_id, valid_from)
);

CREATE INDEX idx_group_members_group ON group_members(group_id);
CREATE INDEX idx_group_members_person ON group_members(person_id);
```

### 12. event_participants (이벤트 참여자)

**이벤트에 누가/어떤 집단이/어떤 국가가 참여했는지.**

```sql
CREATE TABLE event_participants (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,

    -- 참여자 (polymorphic)
    participant_type VARCHAR(20) NOT NULL,
        -- person, group, territory
    participant_id INTEGER NOT NULL,

    -- 역할
    role VARCHAR(50) DEFAULT 'participant',
        -- participant, commander, victor, defeated, victim

    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, participant_type, participant_id, role)
);

CREATE INDEX idx_event_participants_event ON event_participants(event_id);
CREATE INDEX idx_event_participants_participant ON event_participants(participant_type, participant_id);
```

### 13. event_locations (이벤트 발생 장소)

```sql
CREATE TABLE event_locations (
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,

    role VARCHAR(50) DEFAULT 'location',
        -- location: 발생 장소
        -- origin: 출발지
        -- destination: 도착지

    PRIMARY KEY (event_id, location_id)
);

CREATE INDEX idx_event_locations_location ON event_locations(location_id);
```

---

## 데이터 흐름

### Wikidata 임포트 시

```
1. Wikidata 덤프 파싱
   │
   ├─► locations (좌표 있는 엔티티)
   ├─► territories (국가/지역 엔티티)
   ├─► persons (P31=Q5)
   ├─► groups (군대/단체 엔티티)
   └─► events (전투/전쟁 엔티티)

2. 관계 생성
   │
   ├─► territory_locations (P131, P36 기반)
   ├─► group_members (P463 기반)
   ├─► event_participants (P710 기반)
   └─► event_locations (P276 기반)

3. 출처 생성 (Wikidata 자체가 출처)
   │
   ├─► sources (source_type='wikidata', wikidata_id=Q...)
   └─► mentions (각 엔티티마다 Wikidata 출처 연결)
```

### Wikipedia 추가 시

```
1. Wikipedia 문서 → sources
   │
   └─► source_type='wikipedia', content_raw=본문

2. 본문 분석 → mentions
   │
   └─► 문서가 언급하는 person, event, location 연결
```

### 책 추가 시

```
1. 책 청크 → sources
   │
   └─► source_type='book', chapter, chunk_index

2. LLM 추출 → mentions
   │
   └─► 청크에서 언급된 엔티티 연결
```

---

## 구현 순서

| 단계 | 테이블 | 의존성 | 확인 방법 |
|------|--------|--------|----------|
| 1 | locations | 없음 | 좌표 조회 |
| 2 | territories | 없음 | 국가 목록 |
| 3 | persons | locations | 인물+출생지 |
| 4 | groups | territories | 집단+소속국가 |
| 5 | events | locations | 이벤트+장소 |
| 6 | sources | 없음 | 출처 목록 |
| 7 | mentions | sources + 모든 엔티티 | 출처→엔티티 연결 |
| 8 | links | 모든 엔티티 | 관계 조회 |
| 9 | location_names | locations | 시대별 이름 |
| 10 | territory_locations | territories, locations | 영역 소속 |
| 11 | group_members | groups, persons | 집단 구성원 |
| 12 | event_participants | events, persons, groups, territories | 참여자 |
| 13 | event_locations | events, locations | 발생 장소 |

---

## 품질 기준

### 필수 조건

| 항목 | 기준 |
|------|------|
| wikidata_id | NULL 허용 (있으면 UNIQUE) |
| 모든 엔티티에 최소 1개 mention | **필수!** (출처 없으면 쓰레기) |
| sources.content_raw | NOT NULL |
| mentions.evidence_raw | NOT NULL, 최소 50자 |

### wikidata_id 정책

| 출처 | wikidata_id |
|------|-------------|
| Wikidata 임포트 | 있음 |
| Wikipedia 추출 | 대부분 있음 |
| 책 추출 | 없을 수 있음 |
| 수동 입력 | 없을 수 있음 |
| FGO 데이터 | 없을 수 있음 |

**원칙**: wikidata_id 없어도 되지만, **mention은 반드시 있어야 함**

### 검증 쿼리

```sql
-- mention 없는 person (있으면 안 됨!)
SELECT p.id, p.name FROM persons p
WHERE NOT EXISTS (
    SELECT 1 FROM mentions m
    WHERE m.target_type = 'person' AND m.target_id = p.id
);

-- source 없는 데이터 = 출처 불명 = 쓰레기
```

---

## 변경 이력

| 날짜 | 버전 | 변경 |
|------|------|------|
| 2026-02-05 | 1.0 | UNIFIED_SPEC + DATA_MODEL_REDESIGN 통합 |
