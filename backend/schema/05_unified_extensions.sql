-- CHALDEAS Schema: 통합 추출 시스템 확장
-- 2026-02-05

-- ============================================
-- 1. ENTITY_PROPERTIES (Wikidata 전체 속성)
-- ============================================

CREATE TABLE IF NOT EXISTS entity_properties (
    id SERIAL PRIMARY KEY,

    -- 엔티티 참조
    entity_type VARCHAR(20) NOT NULL,  -- person, location, territory, group, event
    entity_id INTEGER NOT NULL,

    -- Wikidata 속성
    property VARCHAR(10) NOT NULL,     -- P22, P26, P106, etc.
    property_name VARCHAR(100),        -- father, spouse, occupation (캐시용)

    -- 값 (타입별로 하나만 사용)
    value_type VARCHAR(20) NOT NULL,   -- qid, string, time, quantity, coordinate, url
    value_qid VARCHAR(20),             -- Q1234 (엔티티 참조)
    value_string TEXT,                 -- 문자열
    value_year INTEGER,                -- 연도 (BCE 음수)
    value_quantity DECIMAL,            -- 수량
    value_lat DECIMAL(10,7),           -- 좌표 위도
    value_lon DECIMAL(10,7),           -- 좌표 경도

    -- Qualifier (한정자) - 시작/종료 시점 등
    qualifier_start_year INTEGER,      -- P580 start time
    qualifier_end_year INTEGER,        -- P582 end time
    qualifiers_json JSONB,             -- 기타 한정자

    -- 원본 참조
    wikidata_id VARCHAR(20) NOT NULL,  -- 엔티티의 QID

    created_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_ep_entity ON entity_properties(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_ep_wikidata ON entity_properties(wikidata_id);
CREATE INDEX IF NOT EXISTS idx_ep_property ON entity_properties(property);
CREATE INDEX IF NOT EXISTS idx_ep_value_qid ON entity_properties(value_qid) WHERE value_qid IS NOT NULL;

-- ============================================
-- 2. SOURCES 확장 (Wikipedia 본문용)
-- ============================================

-- Wikipedia HTML 원본
ALTER TABLE sources ADD COLUMN IF NOT EXISTS content_html TEXT;

-- 통계
ALTER TABLE sources ADD COLUMN IF NOT EXISTS word_count INTEGER;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS link_count INTEGER;

-- ============================================
-- 3. MENTIONS 확장 (하이퍼링크 정보)
-- ============================================

-- 링크 텍스트
ALTER TABLE mentions ADD COLUMN IF NOT EXISTS link_text VARCHAR(500);

-- 위치 정보
ALTER TABLE mentions ADD COLUMN IF NOT EXISTS position_start INTEGER;
ALTER TABLE mentions ADD COLUMN IF NOT EXISTS position_end INTEGER;
ALTER TABLE mentions ADD COLUMN IF NOT EXISTS paragraph_index INTEGER;

-- 추가 인덱스 (역링크 조회용)
CREATE INDEX IF NOT EXISTS idx_mentions_source_qid ON mentions(source_id);
CREATE INDEX IF NOT EXISTS idx_mentions_target ON mentions(target_type, target_id);
