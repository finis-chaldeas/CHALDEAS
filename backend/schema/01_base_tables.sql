-- CHALDEAS Schema: CP-1.1 기본 테이블
-- 의존성 없는 테이블들

-- ============================================
-- 1. LOCATIONS (점)
-- ============================================

CREATE TABLE IF NOT EXISTS locations (
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

CREATE INDEX IF NOT EXISTS idx_locations_wikidata ON locations(wikidata_id);
CREATE INDEX IF NOT EXISTS idx_locations_coords ON locations(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_locations_name ON locations(name);
CREATE INDEX IF NOT EXISTS idx_locations_parent ON locations(parent_location_id);

-- ============================================
-- 2. TERRITORIES (영역)
-- ============================================

CREATE TABLE IF NOT EXISTS territories (
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

CREATE INDEX IF NOT EXISTS idx_territories_wikidata ON territories(wikidata_id);
CREATE INDEX IF NOT EXISTS idx_territories_type ON territories(territory_type);
CREATE INDEX IF NOT EXISTS idx_territories_name ON territories(name);

-- ============================================
-- 3. SOURCES (출처 원문)
-- ============================================

CREATE TABLE IF NOT EXISTS sources (
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
    wikidata_id VARCHAR(20) UNIQUE,    -- 출처 자체의 QID
    gutenberg_id INTEGER,

    -- 신뢰도 (1-5)
    reliability INTEGER DEFAULT 3,

    -- 메타
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sources_type ON sources(source_type);
CREATE INDEX IF NOT EXISTS idx_sources_wikidata ON sources(wikidata_id);
CREATE INDEX IF NOT EXISTS idx_sources_title ON sources(title);
