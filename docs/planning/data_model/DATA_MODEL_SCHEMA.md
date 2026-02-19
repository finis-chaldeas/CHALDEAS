# CHALDEAS 데이터 모델 상세 스키마

## 개요

```
핵심 엔티티:     Person, Location, Event
확장 엔티티:     Group (Person 집합), Territory (Location 집합)
시간 추적:       valid_from, valid_until (BCE는 음수)
```

---

## 1. Location (점)

모든 역사적 지점. 항상 좌표가 있는 점.

```sql
CREATE TABLE locations (
    id SERIAL PRIMARY KEY,

    -- 대표 이름 (현재 기준)
    name VARCHAR(255) NOT NULL,
    name_ko VARCHAR(255),

    -- 좌표 (필수)
    latitude DECIMAL(10, 7) NOT NULL,
    longitude DECIMAL(10, 7) NOT NULL,

    -- 분류
    location_type VARCHAR(50) DEFAULT 'point',
        -- point: 도시, 건물, 전장
        -- natural: 산, 강, 호수
        -- sea: 바다, 해협

    -- 물리적 계층 (경복궁 → 한양, 불변)
    parent_location_id INTEGER REFERENCES locations(id),

    -- 동일 지점 통합 (500m 이내)
    canonical_id INTEGER REFERENCES locations(id),

    -- Wikidata 연결
    wikidata_id VARCHAR(50) UNIQUE,

    -- 메타
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_locations_coords ON locations(latitude, longitude);
CREATE INDEX idx_locations_wikidata ON locations(wikidata_id);
CREATE INDEX idx_locations_parent ON locations(parent_location_id);
```

### 1.1 Location Names (시대별 이름)

```sql
CREATE TABLE location_names (
    id SERIAL PRIMARY KEY,
    location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,

    -- 이름
    name VARCHAR(255) NOT NULL,
    name_ko VARCHAR(255),

    -- 시기 (BCE는 음수, NULL은 무한)
    valid_from INTEGER,  -- 시작 연도
    valid_until INTEGER, -- 종료 연도

    -- 언어/출처
    language VARCHAR(10) DEFAULT 'en',
    is_primary BOOLEAN DEFAULT FALSE,

    -- Wikidata (이름별 QID가 다를 수 있음)
    wikidata_id VARCHAR(50),
    source VARCHAR(100),

    created_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_location_names_location ON location_names(location_id);
CREATE INDEX idx_location_names_period ON location_names(valid_from, valid_until);
```

**예시: 서울**
```
locations:
  id: 1, name: "Seoul", latitude: 37.5665, longitude: 126.9780

location_names:
  location_id: 1, name: "위례성",  valid_from: NULL, valid_until: -18
  location_id: 1, name: "한성",    valid_from: -18,  valid_until: 475
  location_id: 1, name: "한양",    valid_from: 1394, valid_until: 1910
  location_id: 1, name: "경성",    valid_from: 1910, valid_until: 1945
  location_id: 1, name: "서울",    valid_from: 1945, valid_until: NULL, is_primary: true
```

**예시: 런던**
```
locations:
  id: 2, name: "London", latitude: 51.5074, longitude: -0.1278

location_names:
  location_id: 2, name: "Londinium", valid_from: 43,   valid_until: 410
  location_id: 2, name: "Lundenwic", valid_from: 600,  valid_until: 886
  location_id: 2, name: "London",    valid_from: 886,  valid_until: NULL, is_primary: true
```

---

## 2. Territory (점 집합 = 영역)

국가, 제국, 지역 등. Location들의 시기별 집합.

```sql
CREATE TABLE territories (
    id SERIAL PRIMARY KEY,

    -- 이름
    name VARCHAR(255) NOT NULL,
    name_ko VARCHAR(255),

    -- 분류
    territory_type VARCHAR(50) NOT NULL,
        -- country: 국가
        -- empire: 제국
        -- region: 지역 (Balkans, Middle East)
        -- continent: 대륙

    -- 존속 기간
    founded_year INTEGER,
    dissolved_year INTEGER,

    -- 상위 영역 (Roman Empire → Europe)
    parent_territory_id INTEGER REFERENCES territories(id),

    -- Wikidata
    wikidata_id VARCHAR(50) UNIQUE,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 2.1 Territory-Location 관계 (시기별 소속)

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
        -- major_city: 주요 도시

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(territory_id, location_id, valid_from)
);

-- 인덱스
CREATE INDEX idx_territory_locations_territory ON territory_locations(territory_id);
CREATE INDEX idx_territory_locations_location ON territory_locations(location_id);
CREATE INDEX idx_territory_locations_period ON territory_locations(valid_from, valid_until);
```

**예시: 알자스의 소속 변화**
```
locations:
  id: 100, name: "Strasbourg", latitude: 48.5734, longitude: 7.7521

territories:
  id: 10, name: "France", territory_type: "country"
  id: 11, name: "German Empire", territory_type: "empire"

territory_locations:
  territory_id: 10 (France), location_id: 100 (Strasbourg)
    valid_from: NULL, valid_until: 1871

  territory_id: 11 (German Empire), location_id: 100 (Strasbourg)
    valid_from: 1871, valid_until: 1918

  territory_id: 10 (France), location_id: 100 (Strasbourg)
    valid_from: 1918, valid_until: NULL
```

### 2.2 Territory Relations (영역 간 소속, 시기별)

```sql
CREATE TABLE territory_relations (
    id SERIAL PRIMARY KEY,
    child_territory_id INTEGER NOT NULL REFERENCES territories(id) ON DELETE CASCADE,
    parent_territory_id INTEGER NOT NULL REFERENCES territories(id) ON DELETE CASCADE,

    -- 관계 유형
    relation_type VARCHAR(50) NOT NULL,
        -- vassal: 조공국/속국 (조선 → 명)
        -- province: 행정구역 (Bavaria → German Empire)
        -- member: 연합 구성원 (Prussia → German Confederation)
        -- colony: 식민지 (India → British Empire)

    -- 소속 기간
    valid_from INTEGER,
    valid_until INTEGER,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(child_territory_id, parent_territory_id, valid_from)
);

CREATE INDEX idx_territory_relations_child ON territory_relations(child_territory_id);
CREATE INDEX idx_territory_relations_parent ON territory_relations(parent_territory_id);
```

**예시: 조선의 조공 관계**
```
territories:
  id: 20, name: "조선", territory_type: "kingdom"
  id: 21, name: "명", territory_type: "empire"
  id: 22, name: "청", territory_type: "empire"

territory_relations:
  child: 조선, parent: 명
    relation_type: "vassal", valid_from: 1392, valid_until: 1644

  child: 조선, parent: 청
    relation_type: "vassal", valid_from: 1637, valid_until: 1897
```

---

## 3. Person (개인)

기존 persons 테이블 유지, 일부 정리.

```sql
CREATE TABLE persons (
    id SERIAL PRIMARY KEY,

    -- 이름
    name VARCHAR(255) NOT NULL,
    name_ko VARCHAR(255),
    name_original VARCHAR(255),  -- 원어 이름

    -- 식별자
    slug VARCHAR(255) UNIQUE,
    wikidata_id VARCHAR(50) UNIQUE,

    -- 생몰년 (BCE는 음수)
    birth_year INTEGER,
    death_year INTEGER,

    -- 설명
    biography TEXT,
    biography_ko TEXT,

    -- 출생지
    birthplace_id INTEGER REFERENCES locations(id),

    -- 메타
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 4. Group (개인 집합)

군대, 종교단체, 민족 등. Person들의 집합.

```sql
CREATE TABLE groups (
    id SERIAL PRIMARY KEY,

    -- 이름
    name VARCHAR(255) NOT NULL,
    name_ko VARCHAR(255),

    -- 분류
    group_type VARCHAR(50) NOT NULL,
        -- military: 군대 (Roman Legion, Wehrmacht)
        -- religious: 종교단체 (Knights Templar)
        -- ethnic: 민족 (Gauls, Mongols)
        -- political: 정치조직 (Senate)
        -- state: 국가 행위자로서 (Republic of Venice)

    -- 존속 기간
    founded_year INTEGER,
    dissolved_year INTEGER,

    -- 상위 집단 (Legion X → Roman Army)
    parent_group_id INTEGER REFERENCES groups(id),

    -- 소속 영역 (Wehrmacht → Nazi Germany)
    territory_id INTEGER REFERENCES territories(id),

    -- Wikidata
    wikidata_id VARCHAR(50) UNIQUE,

    -- 설명
    description TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 4.1 Group Members (구성원)

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
```

**예시: Knights Templar**
```
groups:
  id: 1, name: "Knights Templar", group_type: "religious"
  founded_year: 1119, dissolved_year: 1312

group_members:
  group_id: 1, person_id: 501 (Hugues de Payens)
    valid_from: 1119, valid_until: 1136, role: "founder"

  group_id: 1, person_id: 502 (Jacques de Molay)
    valid_from: 1292, valid_until: 1314, role: "grand_master"
```

**예시: Richard I의 다중 소속**
```
persons:
  id: 600, name: "Richard I of England"

groups:
  id: 50, name: "Kingdom of England", group_type: "state"
  id: 51, name: "Duchy of Normandy", group_type: "state"
  id: 52, name: "Duchy of Aquitaine", group_type: "state"
  id: 53, name: "Third Crusade", group_type: "military"

group_members:
  person_id: 600, group_id: 50 (England)
    role: "king", valid_from: 1189, valid_until: 1199

  person_id: 600, group_id: 51 (Normandy)
    role: "duke", valid_from: 1189, valid_until: 1199

  person_id: 600, group_id: 52 (Aquitaine)
    role: "duke", valid_from: 1172, valid_until: 1199

  person_id: 600, group_id: 53 (Third Crusade)
    role: "commander", valid_from: 1189, valid_until: 1192
```

### 4.2 Group Relations (집단 간 소속, 시기별)

```sql
CREATE TABLE group_relations (
    id SERIAL PRIMARY KEY,
    child_group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    parent_group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,

    -- 관계 유형
    relation_type VARCHAR(50) NOT NULL,
        -- branch: 지부 (Templar England → Knights Templar)
        -- division: 부대 (Legion X → Roman Army)
        -- affiliated: 제휴 (Knights Templar → Catholic Church)

    -- 소속 기간
    valid_from INTEGER,
    valid_until INTEGER,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(child_group_id, parent_group_id, valid_from)
);

CREATE INDEX idx_group_relations_child ON group_relations(child_group_id);
CREATE INDEX idx_group_relations_parent ON group_relations(parent_group_id);
```

**예시: 로마 군단 구조**
```
groups:
  id: 100, name: "Roman Army", group_type: "military"
  id: 101, name: "Legio X Equestris", group_type: "military"
  id: 102, name: "Legio XIII Gemina", group_type: "military"

group_relations:
  child: Legio X, parent: Roman Army
    relation_type: "division", valid_from: -58, valid_until: -45

  child: Legio XIII, parent: Roman Army
    relation_type: "division", valid_from: -57, valid_until: 476
```

---

## 5. Event (사건)

기존 events 테이블 유지.

```sql
CREATE TABLE events (
    id SERIAL PRIMARY KEY,

    -- 제목
    title VARCHAR(500) NOT NULL,
    title_ko VARCHAR(500),

    -- 식별자
    slug VARCHAR(255) UNIQUE,
    wikidata_id VARCHAR(50) UNIQUE,

    -- 시기
    date_start INTEGER NOT NULL,  -- 연도 (BCE 음수)
    date_end INTEGER,

    -- 설명
    description TEXT,

    -- 주요 위치 (빠른 조회용)
    primary_location_id INTEGER REFERENCES locations(id),

    -- 분류
    event_type VARCHAR(100),
    temporal_scale VARCHAR(50) DEFAULT 'evenementielle',

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 5.1 Event-Location 관계

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
```

### 5.2 Event-Territory 관계

```sql
CREATE TABLE event_territories (
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    territory_id INTEGER NOT NULL REFERENCES territories(id) ON DELETE CASCADE,

    role VARCHAR(50) DEFAULT 'participant',
        -- participant: 참여 국가
        -- victor: 승리국
        -- defeated: 패배국
        -- location: 발생 영역

    PRIMARY KEY (event_id, territory_id, role)
);
```

### 5.3 Event-Person 관계

```sql
CREATE TABLE event_persons (
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,

    role VARCHAR(100),
        -- participant, commander, victim, etc.

    description TEXT,

    PRIMARY KEY (event_id, person_id)
);
```

### 5.4 Event-Group 관계

```sql
CREATE TABLE event_groups (
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,

    role VARCHAR(50) DEFAULT 'participant',
        -- participant, victor, defeated

    PRIMARY KEY (event_id, group_id, role)
);
```

---

## 6. 쿼리 예시

### 6.1 특정 연도의 위치 이름 조회

```sql
-- 1900년 서울의 이름은?
SELECT ln.name, ln.name_ko
FROM location_names ln
WHERE ln.location_id = 1  -- Seoul
  AND (ln.valid_from IS NULL OR ln.valid_from <= 1900)
  AND (ln.valid_until IS NULL OR ln.valid_until > 1900);
-- 결과: 한양
```

### 6.2 특정 연도의 영역 소속 조회

```sql
-- 1900년 Strasbourg는 어느 나라?
SELECT t.name
FROM territory_locations tl
JOIN territories t ON t.id = tl.territory_id
WHERE tl.location_id = 100  -- Strasbourg
  AND (tl.valid_from IS NULL OR tl.valid_from <= 1900)
  AND (tl.valid_until IS NULL OR tl.valid_until > 1900);
-- 결과: German Empire
```

### 6.3 이벤트와 모든 참여자 조회

```sql
-- Battle of Hattin의 모든 참여자
SELECT
    'person' as type, p.name, ep.role
FROM event_persons ep
JOIN persons p ON p.id = ep.person_id
WHERE ep.event_id = 123

UNION ALL

SELECT
    'group' as type, g.name, eg.role
FROM event_groups eg
JOIN groups g ON g.id = eg.group_id
WHERE eg.event_id = 123;
```

---

## 7. 마이그레이션 계획

### 기존 테이블
- `locations`: 유지, canonical_id 추가
- `location_names`: 유지 (이미 있음)
- `persons`: 유지
- `events`: 유지
- `event_locations`: 유지
- `event_persons`: 유지

### 신규 테이블
- `territories`: 생성
- `territory_locations`: 생성
- `groups`: 생성
- `group_members`: 생성
- `event_territories`: 생성
- `event_groups`: 생성

### 데이터 마이그레이션
1. 기존 locations에서 국가/영역 추출 → territories로 이동
2. Wikidata에서 territory, group 데이터 임포트

---

## 작성일: 2026-02-05
