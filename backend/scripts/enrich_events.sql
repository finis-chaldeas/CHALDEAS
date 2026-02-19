-- CHALDEAS Event Location Enrichment
-- Fills events.primary_location_id from event_locations junction table.
-- Usage: psql -U chaldeas -d chaldeas -f enrich_events.sql

BEGIN;

UPDATE events e SET primary_location_id = el.location_id
FROM (
  SELECT DISTINCT ON (event_id) event_id, location_id
  FROM event_locations
  ORDER BY event_id, location_id
) el
WHERE el.event_id = e.id AND e.primary_location_id IS NULL;

COMMIT;
