-- CHALDEAS Data Diagnostic Queries
-- Run these to understand the current data gaps before enrichment.
-- Usage: psql -U chaldeas -d chaldeas -f diagnostic_queries.sql

-- 1. Persons empty field summary
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE birth_year IS NULL) as no_birth,
  COUNT(*) FILTER (WHERE death_year IS NULL) as no_death,
  COUNT(*) FILTER (WHERE birthplace_id IS NULL) as no_birthplace,
  COUNT(*) FILTER (WHERE role IS NULL OR role = '') as no_role,
  COUNT(*) FILTER (WHERE biography IS NULL OR biography = '') as no_bio,
  COUNT(*) FILTER (WHERE image_url IS NULL) as no_image
FROM persons;

-- 2. event_connections (Story API dependency)
SELECT COUNT(*) as total_connections FROM event_connections;
SELECT COUNT(DISTINCT layer_entity_id) as persons_with_connections
FROM event_connections WHERE layer_type='person';

-- 3. event_persons (fallback story source)
SELECT COUNT(*) as total_event_persons FROM event_persons;
SELECT COUNT(DISTINCT person_id) as persons_with_events FROM event_persons;

-- 4. entity_properties key properties count
SELECT property, property_name, COUNT(*)
FROM entity_properties
WHERE entity_type='person' AND property IN ('P569','P570','P19','P20','P106','P27','P21')
GROUP BY property, property_name
ORDER BY count DESC;

-- 5. Events location coverage
SELECT
  COUNT(*) as total_events,
  COUNT(*) FILTER (WHERE primary_location_id IS NOT NULL) as with_location,
  COUNT(*) FILTER (WHERE primary_location_id IS NULL) as without_location
FROM events;

-- 6. event_locations available but not in events.primary_location_id
SELECT COUNT(DISTINCT el.event_id) as events_fixable
FROM event_locations el
JOIN events e ON e.id = el.event_id
WHERE e.primary_location_id IS NULL;
