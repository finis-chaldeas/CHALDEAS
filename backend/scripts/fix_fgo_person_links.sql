-- Fix wrong FGO servant -> person links
-- Generated 2026-03-10

BEGIN;

-- === A. Re-link to correct existing person ===

-- Ivan the Terrible: wrong Ivan (1911) -> correct Ivan IV (1530-1584)
UPDATE fgo_servants SET person_id = 1623709
  WHERE person_id = 11419598;

-- James Moriarty (ruler): Laure Manaudou -> batch Moriarty
UPDATE fgo_servants SET person_id = 14610725
  WHERE person_id = 3250360 AND class_name = 'ruler';

-- Kawakami Gensai: was wrongly linked to Okada Izo
UPDATE fgo_servants SET person_id = 8142377
  WHERE person_id = 9826197 AND name = '';

-- === B. Set NULL (correct person not in DB yet) ===

-- Queen Medb + Medb (Saber): Andrei Zhdanov
UPDATE fgo_servants SET person_id = NULL WHERE person_id = 1631921;

-- Arash: modern person born 1977
UPDATE fgo_servants SET person_id = NULL WHERE name = 'Arash' AND person_id = 12997894;

-- Geronimo: Thomas Gravesen (footballer)
UPDATE fgo_servants SET person_id = NULL WHERE name = 'Geronimo' AND person_id = 13000183;

-- Hektor: Saadi (Persian poet)
UPDATE fgo_servants SET person_id = NULL WHERE name = 'Hektor' AND person_id = 6502419;

-- Don Quixote: Damiano Damiani (director)
UPDATE fgo_servants SET person_id = NULL WHERE name = 'Don Quixote' AND person_id = 8118577;

-- Edmond Dantes + Monte Cristo variant: Luis Enrique (footballer)
UPDATE fgo_servants SET person_id = NULL WHERE person_id = 8129544;

-- Scheherazade: Agnes Varda (director)
UPDATE fgo_servants SET person_id = NULL WHERE name = 'Scheherazade' AND person_id = 9749685;

-- Sakata Kintoki (berserker + rider): Felix Manalo
UPDATE fgo_servants SET person_id = NULL WHERE person_id = 6571295;

-- Morgan: modern person born 1972
UPDATE fgo_servants SET person_id = NULL WHERE name = 'Morgan' AND person_id = 4980550;

-- Nemo + Nemo Santa: Vladimir Vernadsky
UPDATE fgo_servants SET person_id = NULL WHERE person_id = 4884081;

-- Percival: modern person born 2000
UPDATE fgo_servants SET person_id = NULL WHERE name = 'Percival' AND person_id = 13029845;

-- William Tell: modern person born 1980
UPDATE fgo_servants SET person_id = NULL WHERE name = 'William Tell' AND person_id = 6663324;

-- Astraea: C.S. Peirce (philosopher)
UPDATE fgo_servants SET person_id = NULL WHERE name = 'Astraea' AND person_id = 8125368;

-- Lady Avalon: Jennifer Granholm (politician)
UPDATE fgo_servants SET person_id = NULL WHERE name = 'Lady Avalon' AND person_id = 12997820;

-- Manannan mac Lir: Roger Casement (Irish activist)
UPDATE fgo_servants SET person_id = NULL WHERE person_id = 11375508;

-- Odysseus: wrongly linked to Heracles in batch
UPDATE fgo_servants SET person_id = NULL WHERE name = 'Odysseus' AND person_id = 14610678;

-- Paris: wrongly linked to Europa in batch
UPDATE fgo_servants SET person_id = NULL WHERE name = 'Paris' AND person_id = 14610665;

-- Valkyrie: wrongly linked to Quetzalcoatl in batch
UPDATE fgo_servants SET person_id = NULL WHERE name = 'Valkyrie' AND person_id = 14610728;

-- Merlin: wrongly linked to King Arthur in batch
UPDATE fgo_servants SET person_id = NULL WHERE name = 'Merlin' AND person_id = 14610696;

-- Andromeda (JP-only): Zhu Rongji (Chinese politician)
UPDATE fgo_servants SET person_id = NULL WHERE person_id = 9741180;

-- Indra (JP-only): Eudoxus of Cnidus (Greek mathematician)
UPDATE fgo_servants SET person_id = NULL WHERE person_id = 12996594;

-- Solomon (pretender, JP-only): wrong Solomon (born 401 AD)
UPDATE fgo_servants SET person_id = NULL WHERE person_id = 4895157 AND class_name = 'pretender';

COMMIT;
