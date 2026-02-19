-- CHALDEAS Fresh Schema
-- 기존 테이블 전부 드랍 후 새로 생성

-- ============================================
-- DROP ALL TABLES
-- ============================================

DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO chaldeas;
GRANT ALL ON SCHEMA public TO public;

-- pgvector extension (superuser 권한 필요, 나중에 별도 추가)
-- CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- 1. LOCATIONS (점)
-- ============================================

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

CREATE INDEX idx_locations_coords ON locations(latitude, longitude);
CREATE INDEX idx_locations_wikidata ON locations(wikidata_id);
CREATE INDEX idx_locations_parent ON locations(parent_location_id);
CREATE INDEX idx_locations_name ON locations(name);

-- ============================================
-- 1.1 LOCATION_NAMES (시대별 이름)
-- ============================================

CREATE TABLE location_names (
    id SERIAL PRIMARY KEY,
    location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,

    -- 이름
    name VARCHAR(255) NOT NULL,
    name_ko VARCHAR(255),

    -- 시기 (BCE는 음수, NULL은 무한)
    valid_from INTEGER,
    valid_until INTEGER,

    -- 언어/출처
    language VARCHAR(10) DEFAULT 'en',
    is_primary BOOLEAN DEFAULT FALSE,

    -- Wikidata
    wikidata_id VARCHAR(50),
    source VARCHAR(100),

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_location_names_location ON location_names(location_id);
CREATE INDEX idx_location_names_period ON location_names(valid_from, valid_until);

-- ============================================
-- 2. TERRITORIES (점 집합 = 영역)
-- ============================================

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

CREATE INDEX idx_territories_wikidata ON territories(wikidata_id);
CREATE INDEX idx_territories_type ON territories(territory_type);
CREATE INDEX idx_territories_name ON territories(name);

-- ============================================
-- 2.1 TERRITORY_LOCATIONS (영역-점 관계)
-- ============================================

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

CREATE INDEX idx_territory_locations_territory ON territory_locations(territory_id);
CREATE INDEX idx_territory_locations_location ON territory_locations(location_id);
CREATE INDEX idx_territory_locations_period ON territory_locations(valid_from, valid_until);

-- ============================================
-- 2.2 TERRITORY_RELATIONS (영역 간 관계)
-- ============================================

CREATE TABLE territory_relations (
    id SERIAL PRIMARY KEY,
    child_territory_id INTEGER NOT NULL REFERENCES territories(id) ON DELETE CASCADE,
    parent_territory_id INTEGER NOT NULL REFERENCES territories(id) ON DELETE CASCADE,

    -- 관계 유형
    relation_type VARCHAR(50) NOT NULL,
        -- vassal: 조공국/속국
        -- province: 행정구역
        -- member: 연합 구성원
        -- colony: 식민지

    -- 소속 기간
    valid_from INTEGER,
    valid_until INTEGER,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(child_territory_id, parent_territory_id, valid_from)
);

CREATE INDEX idx_territory_relations_child ON territory_relations(child_territory_id);
CREATE INDEX idx_territory_relations_parent ON territory_relations(parent_territory_id);

-- ============================================
-- 3. PERSONS (개인)
-- ============================================

CREATE TABLE persons (
    id SERIAL PRIMARY KEY,

    -- 이름
    name VARCHAR(255) NOT NULL,
    name_ko VARCHAR(255),
    name_original VARCHAR(255),

    -- 식별자
    wikidata_id VARCHAR(50) UNIQUE,

    -- 생몰년 (BCE는 음수)
    birth_year INTEGER,
    death_year INTEGER,

    -- 설명
    biography TEXT,
    biography_ko TEXT,

    -- 출생지
    birthplace_id INTEGER REFERENCES locations(id),
    deathplace_id INTEGER REFERENCES locations(id),

    -- 메타
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_persons_wikidata ON persons(wikidata_id);
CREATE INDEX idx_persons_name ON persons(name);
CREATE INDEX idx_persons_years ON persons(birth_year, death_year);

-- ============================================
-- 4. GROUPS (개인 집합)
-- ============================================

CREATE TABLE groups (
    id SERIAL PRIMARY KEY,

    -- 이름
    name VARCHAR(255) NOT NULL,
    name_ko VARCHAR(255),

    -- 분류
    group_type VARCHAR(50) NOT NULL,
        -- military: 군대
        -- religious: 종교단체
        -- ethnic: 민족
        -- political: 정치조직
        -- state: 국가 행위자

    -- 존속 기간
    founded_year INTEGER,
    dissolved_year INTEGER,

    -- 상위 집단
    parent_group_id INTEGER REFERENCES groups(id),

    -- 소속 영역
    territory_id INTEGER REFERENCES territories(id),

    -- Wikidata
    wikidata_id VARCHAR(50) UNIQUE,

    -- 설명
    description TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_groups_wikidata ON groups(wikidata_id);
CREATE INDEX idx_groups_type ON groups(group_type);
CREATE INDEX idx_groups_name ON groups(name);

-- ============================================
-- 4.1 GROUP_MEMBERS (구성원)
-- ============================================

CREATE TABLE group_members (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,

    -- 소속 기간
    valid_from INTEGER,
    valid_until INTEGER,

    -- 역할
    role VARCHAR(100),

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(group_id, person_id, valid_from)
);

CREATE INDEX idx_group_members_group ON group_members(group_id);
CREATE INDEX idx_group_members_person ON group_members(person_id);

-- ============================================
-- 4.2 GROUP_RELATIONS (집단 간 관계)
-- ============================================

CREATE TABLE group_relations (
    id SERIAL PRIMARY KEY,
    child_group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    parent_group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,

    -- 관계 유형
    relation_type VARCHAR(50) NOT NULL,
        -- branch: 지부
        -- division: 부대
        -- affiliated: 제휴

    -- 소속 기간
    valid_from INTEGER,
    valid_until INTEGER,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(child_group_id, parent_group_id, valid_from)
);

CREATE INDEX idx_group_relations_child ON group_relations(child_group_id);
CREATE INDEX idx_group_relations_parent ON group_relations(parent_group_id);

-- ============================================
-- 5. EVENTS (사건)
-- ============================================

CREATE TABLE events (
    id SERIAL PRIMARY KEY,

    -- 제목
    title VARCHAR(500) NOT NULL,
    title_ko VARCHAR(500),

    -- 식별자
    wikidata_id VARCHAR(50) UNIQUE,

    -- 시기
    date_start INTEGER NOT NULL,  -- 연도 (BCE 음수)
    date_end INTEGER,
    date_precision VARCHAR(20) DEFAULT 'year',
        -- day, month, year, decade, century

    -- 설명
    description TEXT,
    description_ko TEXT,

    -- 주요 위치 (빠른 조회용)
    primary_location_id INTEGER REFERENCES locations(id),

    -- 분류
    event_type VARCHAR(100),

    -- 상위 이벤트 (D-Day → Operation Overlord)
    parent_event_id INTEGER REFERENCES events(id),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_events_wikidata ON events(wikidata_id);
CREATE INDEX idx_events_dates ON events(date_start, date_end);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_title ON events(title);
CREATE INDEX idx_events_parent ON events(parent_event_id);

-- ============================================
-- 5.1 EVENT_LOCATIONS (이벤트-점 관계)
-- ============================================

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

-- ============================================
-- 5.2 EVENT_TERRITORIES (이벤트-영역 관계)
-- ============================================

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

CREATE INDEX idx_event_territories_territory ON event_territories(territory_id);

-- ============================================
-- 5.3 EVENT_PERSONS (이벤트-개인 관계)
-- ============================================

CREATE TABLE event_persons (
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,

    role VARCHAR(100),
    description TEXT,

    PRIMARY KEY (event_id, person_id)
);

CREATE INDEX idx_event_persons_person ON event_persons(person_id);

-- ============================================
-- 5.4 EVENT_GROUPS (이벤트-집단 관계)
-- ============================================

CREATE TABLE event_groups (
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,

    role VARCHAR(50) DEFAULT 'participant',

    PRIMARY KEY (event_id, group_id, role)
);

CREATE INDEX idx_event_groups_group ON event_groups(group_id);

-- ============================================
-- 6. SOURCES (출처 추적)
-- ============================================

CREATE TABLE sources (
    id SERIAL PRIMARY KEY,

    -- 출처 정보
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50),
        -- wikidata, book, web, manual

    url TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- DONE
-- ============================================
