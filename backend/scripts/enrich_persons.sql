-- CHALDEAS Person Enrichment from entity_properties
-- Fills empty persons fields using Wikidata properties stored in entity_properties.
-- Run AFTER diagnostic_queries.sql to see what needs fixing.
-- Usage: psql -U chaldeas -d chaldeas -f enrich_persons.sql

BEGIN;

-- 1. birth_year from P569 (date of birth)
UPDATE persons p SET birth_year = ep.value_year
FROM entity_properties ep
WHERE ep.entity_type = 'person' AND ep.entity_id = p.id
  AND ep.property = 'P569' AND ep.value_year IS NOT NULL
  AND p.birth_year IS NULL;

-- 2. death_year from P570 (date of death)
UPDATE persons p SET death_year = ep.value_year
FROM entity_properties ep
WHERE ep.entity_type = 'person' AND ep.entity_id = p.id
  AND ep.property = 'P570' AND ep.value_year IS NOT NULL
  AND p.death_year IS NULL;

-- 3. birthplace_id from P19 (place of birth) via locations.wikidata_id
UPDATE persons p SET birthplace_id = l.id
FROM entity_properties ep
JOIN locations l ON l.wikidata_id = ep.value_qid
WHERE ep.entity_type = 'person' AND ep.entity_id = p.id
  AND ep.property = 'P19' AND ep.value_qid IS NOT NULL
  AND p.birthplace_id IS NULL;

-- 4. deathplace_id from P20 (place of death) via locations.wikidata_id
UPDATE persons p SET deathplace_id = l.id
FROM entity_properties ep
JOIN locations l ON l.wikidata_id = ep.value_qid
WHERE ep.entity_type = 'person' AND ep.entity_id = p.id
  AND ep.property = 'P20' AND ep.value_qid IS NOT NULL
  AND p.deathplace_id IS NULL;

-- 5. role from P106 (occupation) - first value only
UPDATE persons p SET role = sub.occ
FROM (
  SELECT DISTINCT ON (entity_id) entity_id,
    COALESCE(value_string, property_name) as occ
  FROM entity_properties
  WHERE entity_type = 'person' AND property = 'P106'
    AND (value_string IS NOT NULL OR property_name IS NOT NULL)
  ORDER BY entity_id, id
) sub
WHERE sub.entity_id = p.id AND (p.role IS NULL OR p.role = '');

COMMIT;
