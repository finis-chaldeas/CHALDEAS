-- CHALDEAS Schema: CP-1.4 관계 테이블

-- ============================================
-- 8. LINKS (엔티티 간 관계)
-- ============================================

CREATE TABLE IF NOT EXISTS links (
    id SERIAL PRIMARY KEY,

    -- 연결 (from → to)
    from_type VARCHAR(20) NOT NULL,
    from_id INTEGER NOT NULL,
    to_type VARCHAR(20) NOT NULL,
    to_id INTEGER NOT NULL,

    -- 관계 분류
    category VARCHAR(20),
        -- family, political, military, cultural, temporal, spatial

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

CREATE INDEX IF NOT EXISTS idx_links_from ON links(from_type, from_id);
CREATE INDEX IF NOT EXISTS idx_links_to ON links(to_type, to_id);
CREATE INDEX IF NOT EXISTS idx_links_category ON links(category);

-- ============================================
-- 9. LOCATION_NAMES (시대별 장소 이름)
-- ============================================

CREATE TABLE IF NOT EXISTS location_names (
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

CREATE INDEX IF NOT EXISTS idx_location_names_location ON location_names(location_id);
CREATE INDEX IF NOT EXISTS idx_location_names_period ON location_names(valid_from, valid_until);

-- ============================================
-- 10. TERRITORY_LOCATIONS (영역 ↔ 장소)
-- ============================================

CREATE TABLE IF NOT EXISTS territory_locations (
    id SERIAL PRIMARY KEY,
    territory_id INTEGER NOT NULL REFERENCES territories(id) ON DELETE CASCADE,
    location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,

    -- 소속 기간
    valid_from INTEGER,
    valid_until INTEGER,

    -- 관계 유형
    relation_type VARCHAR(50) DEFAULT 'contains',
        -- contains, capital

    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(territory_id, location_id, valid_from)
);

CREATE INDEX IF NOT EXISTS idx_territory_locations_territory ON territory_locations(territory_id);
CREATE INDEX IF NOT EXISTS idx_territory_locations_location ON territory_locations(location_id);

-- ============================================
-- 11. GROUP_MEMBERS (집단 ↔ 개인)
-- ============================================

CREATE TABLE IF NOT EXISTS group_members (
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

CREATE INDEX IF NOT EXISTS idx_group_members_group ON group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_group_members_person ON group_members(person_id);

-- ============================================
-- 12. EVENT_PARTICIPANTS (이벤트 참여자)
-- ============================================

CREATE TABLE IF NOT EXISTS event_participants (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,

    -- 참여자 (polymorphic)
    participant_type VARCHAR(20) NOT NULL,
        -- person, group, territory
    participant_id INTEGER NOT NULL,

    -- 역할
    role VARCHAR(50) DEFAULT 'participant',

    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, participant_type, participant_id, role)
);

CREATE INDEX IF NOT EXISTS idx_event_participants_event ON event_participants(event_id);
CREATE INDEX IF NOT EXISTS idx_event_participants_participant ON event_participants(participant_type, participant_id);

-- ============================================
-- 13. EVENT_LOCATIONS (이벤트 발생 장소)
-- ============================================

CREATE TABLE IF NOT EXISTS event_locations (
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,

    role VARCHAR(50) DEFAULT 'location',

    PRIMARY KEY (event_id, location_id)
);

CREATE INDEX IF NOT EXISTS idx_event_locations_location ON event_locations(location_id);
