-- CHALDEAS Schema: CP-1.2 엔티티 테이블
-- 의존성 있는 테이블들

-- ============================================
-- 4. PERSONS (개인)
-- ============================================

CREATE TABLE IF NOT EXISTS persons (
    id SERIAL PRIMARY KEY,

    -- 식별
    wikidata_id VARCHAR(20) UNIQUE,

    -- 이름
    name VARCHAR(255) NOT NULL,
    name_ko VARCHAR(255),
    name_original VARCHAR(255),  -- 원어 이름

    -- 생몰년 (BCE 음수)
    birth_year INTEGER,
    death_year INTEGER,

    -- 출생/사망지
    birthplace_id INTEGER REFERENCES locations(id),
    deathplace_id INTEGER REFERENCES locations(id),

    -- 설명 (여러 출처 종합 후 정서)
    description TEXT,
    description_model VARCHAR(50),
    description_at TIMESTAMP,

    -- 메타
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_persons_wikidata ON persons(wikidata_id);
CREATE INDEX IF NOT EXISTS idx_persons_name ON persons(name);
CREATE INDEX IF NOT EXISTS idx_persons_years ON persons(birth_year, death_year);
CREATE INDEX IF NOT EXISTS idx_persons_birthplace ON persons(birthplace_id);

-- ============================================
-- 5. GROUPS (집단)
-- ============================================

CREATE TABLE IF NOT EXISTS groups (
    id SERIAL PRIMARY KEY,

    -- 식별
    wikidata_id VARCHAR(20) UNIQUE,

    -- 이름
    name VARCHAR(255) NOT NULL,
    name_ko VARCHAR(255),

    -- 분류
    group_type VARCHAR(50) NOT NULL,
        -- military: 군대
        -- religious: 종교단체
        -- ethnic: 민족
        -- political: 정치조직

    -- 존속 기간
    founded_year INTEGER,
    dissolved_year INTEGER,

    -- 소속 영역
    territory_id INTEGER REFERENCES territories(id),

    -- 설명
    description TEXT,

    -- 메타
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_groups_wikidata ON groups(wikidata_id);
CREATE INDEX IF NOT EXISTS idx_groups_type ON groups(group_type);
CREATE INDEX IF NOT EXISTS idx_groups_name ON groups(name);
CREATE INDEX IF NOT EXISTS idx_groups_territory ON groups(territory_id);

-- ============================================
-- 6. EVENTS (사건)
-- ============================================

CREATE TABLE IF NOT EXISTS events (
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

    -- 분류
    event_type VARCHAR(100),

    -- 계층
    parent_event_id INTEGER REFERENCES events(id),
    hierarchy_level INTEGER DEFAULT 3,

    -- 주요 위치
    primary_location_id INTEGER REFERENCES locations(id),

    -- 설명
    description TEXT,
    description_model VARCHAR(50),
    description_at TIMESTAMP,

    -- 메타
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_wikidata ON events(wikidata_id);
CREATE INDEX IF NOT EXISTS idx_events_dates ON events(date_start, date_end);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_parent ON events(parent_event_id);
CREATE INDEX IF NOT EXISTS idx_events_location ON events(primary_location_id);
