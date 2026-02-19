-- CHALDEAS Schema: CP-1.3 출처 연결 테이블

-- ============================================
-- 7. MENTIONS (출처 → 엔티티 연결)
-- ============================================

CREATE TABLE IF NOT EXISTS mentions (
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

CREATE INDEX IF NOT EXISTS idx_mentions_source ON mentions(source_id);
CREATE INDEX IF NOT EXISTS idx_mentions_target ON mentions(target_type, target_id);
