-- CHALDEAS Performance Indexes
-- Run AFTER enrichment scripts to optimize query patterns.
-- Usage: psql -U chaldeas -d chaldeas -f create_indexes.sql

-- Featured persons: biography + birth_year + connection_count
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_persons_bio_birth
  ON persons(connection_count DESC NULLS LAST)
  WHERE wikidata_id IS NOT NULL AND biography IS NOT NULL AND birth_year IS NOT NULL;

-- Story API: event_persons lookup by person
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_event_persons_person
  ON event_persons(person_id);

-- Entity properties: person property lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ep_person_key
  ON entity_properties(entity_id, property)
  WHERE entity_type = 'person';
