# Wikidata → CHALDEAS 매핑 가이드

## 개요

Wikidata의 엔티티와 속성(P)을 CHALDEAS 데이터 모델에 매핑하는 방법.

**CHALDEAS 모델:**
```
Location (점) + Territory (점 집합)
Person (개인) + Group (개인 집합)
Event (사건)
```

---

## 1. Location 매핑

### 1.1 Location 식별 (P31 instance of)

| Wikidata Type | QID | CHALDEAS location_type |
|---------------|-----|------------------------|
| city | Q515 | point |
| town | Q3957 | point |
| village | Q532 | point |
| capital | Q5119 | point |
| human settlement | Q486972 | point |
| archaeological site | Q839954 | point |
| battlefield | Q4895508 | point |
| building | Q41176 | point |
| palace | Q16560 | point |
| castle | Q23413 | point |
| mountain | Q8502 | natural |
| river | Q4022 | natural |
| lake | Q23397 | natural |
| island | Q23442 | natural |
| sea | Q165 | sea |
| ocean | Q9430 | sea |

### 1.2 Location 속성 매핑

| Wikidata Property | CHALDEAS Field |
|-------------------|----------------|
| rdfs:label (en) | name |
| rdfs:label (ko) | name_ko |
| P625 (coordinate) | latitude, longitude |
| P131 (located in admin) | parent_location_id 후보 |
| P17 (country) | territory_locations 연결용 |

### 1.3 Location 계층 (parent_location_id)

**P131 (located in administrative territorial entity)** 사용:
```
경복궁 (Q41089)
  P131 → 서울 (Q8684)
    P131 → 대한민국 (Q884)
```

**매핑 로직:**
```python
def get_parent_location(entity):
    # P131이 도시/건물이면 parent_location_id로
    p131 = get_claim(entity, 'P131')
    if p131 and is_point_location(p131):
        return p131  # parent_location_id
    else:
        return None  # territory_locations로 처리
```

### 1.4 Location Names (시대별 이름)

**방법 1: 다국어 레이블**
```
Q8684 (Seoul):
  label@en: "Seoul"
  label@ko: "서울"
  label@ja: "ソウル"
```

**방법 2: P1448 (official name) + qualifiers**
```
Q8684:
  P1448: "서울특별시"
    P580 (start time): 1946
  P1448: "경성부"
    P580: 1910
    P582 (end time): 1946
```

**방법 3: Historical name 검색**
- P1705 (native label)
- P1449 (nickname)
- description 파싱

**매핑:**
```python
def extract_location_names(entity):
    names = []

    # 현재 이름 (label)
    names.append({
        'name': entity['labels']['en'],
        'name_ko': entity['labels'].get('ko'),
        'is_primary': True
    })

    # 공식 명칭 이력 (P1448)
    for claim in entity['claims'].get('P1448', []):
        name = claim['mainsnak']['datavalue']['value']['text']
        qualifiers = claim.get('qualifiers', {})
        valid_from = parse_time(qualifiers.get('P580'))
        valid_until = parse_time(qualifiers.get('P582'))
        names.append({
            'name': name,
            'valid_from': valid_from,
            'valid_until': valid_until
        })

    return names
```

---

## 2. Territory 매핑

### 2.1 Territory 식별 (P31 instance of)

| Wikidata Type | QID | CHALDEAS territory_type |
|---------------|-----|-------------------------|
| country | Q6256 | country |
| sovereign state | Q3624078 | country |
| historical country | Q3024240 | country |
| empire | Q48349 | empire |
| kingdom | Q417175 | country |
| republic | Q7270 | country |
| duchy | Q28575 | country |
| principality | Q208500 | country |
| continent | Q5107 | continent |
| geographic region | Q82794 | region |
| subcontinent | Q855697 | region |

### 2.2 Territory 속성 매핑

| Wikidata Property | CHALDEAS Field |
|-------------------|----------------|
| rdfs:label | name, name_ko |
| P571 (inception) | founded_year |
| P576 (dissolved) | dissolved_year |
| P36 (capital) | territory_locations (capital 역할) |
| P150 (contains admin) | territory_locations 대상들 |

### 2.3 Territory Relations (영역 간 관계)

**P131 (located in administrative territorial entity):**
```
Bavaria (Q980)
  P131 → Germany (Q183)
```
→ `territory_relations (child: Bavaria, parent: Germany, type: province)`

**P361 (part of):**
```
Joseon (Q28179)
  P361 → Tributary system of China (Q848399)
```
→ `territory_relations (child: 조선, parent: 명 조공체제, type: vassal)`

**P1365/P1366 (replaces/replaced by):** 국가 승계
```
Russian Empire (Q34266)
  P1366 → Soviet Union (Q15180)
```

**매핑 로직:**
```python
def extract_territory_relations(entity):
    relations = []

    # P131: 행정 소속
    for p131 in get_claims(entity, 'P131'):
        parent_qid = p131['value']['id']
        qualifiers = p131.get('qualifiers', {})
        relations.append({
            'parent_qid': parent_qid,
            'relation_type': 'province',
            'valid_from': parse_time(qualifiers.get('P580')),
            'valid_until': parse_time(qualifiers.get('P582'))
        })

    # P361: 소속/일부
    for p361 in get_claims(entity, 'P361'):
        parent_qid = p361['value']['id']
        relations.append({
            'parent_qid': parent_qid,
            'relation_type': 'member',  # 또는 vassal 판단 필요
            'valid_from': parse_time(qualifiers.get('P580')),
            'valid_until': parse_time(qualifiers.get('P582'))
        })

    return relations
```

### 2.4 Territory-Location 연결

**P150 (contains administrative territorial entity):**
```
France (Q142)
  P150 → Paris (Q90)
  P150 → Lyon (Q456)
  ...
```

**P36 (capital):**
```
France (Q142)
  P36 → Paris (Q90)
    P580: 987  # 언제부터 수도인지
```

**매핑:**
```python
def extract_territory_locations(territory_entity):
    locations = []

    # P36: 수도
    for p36 in get_claims(territory_entity, 'P36'):
        loc_qid = p36['value']['id']
        qualifiers = p36.get('qualifiers', {})
        locations.append({
            'location_qid': loc_qid,
            'relation_type': 'capital',
            'valid_from': parse_time(qualifiers.get('P580')),
            'valid_until': parse_time(qualifiers.get('P582'))
        })

    # P150: 포함하는 도시들
    for p150 in get_claims(territory_entity, 'P150'):
        loc_qid = p150['value']['id']
        locations.append({
            'location_qid': loc_qid,
            'relation_type': 'contains'
        })

    return locations
```

---

## 3. Person 매핑

### 3.1 Person 식별

| Wikidata Property | 조건 |
|-------------------|------|
| P31 = Q5 (human) | 필수 |

### 3.2 Person 속성 매핑

| Wikidata Property | CHALDEAS Field |
|-------------------|----------------|
| rdfs:label | name, name_ko |
| P569 (date of birth) | birth_year |
| P570 (date of death) | death_year |
| P19 (place of birth) | birthplace_id |
| P20 (place of death) | deathplace_id |
| schema:description | biography (간략) |
| P735 (given name) | 이름 파싱 |
| P734 (family name) | 이름 파싱 |

---

## 4. Group 매핑

### 4.1 Group 식별 (P31 instance of)

| Wikidata Type | QID | CHALDEAS group_type |
|---------------|-----|---------------------|
| military unit | Q176799 | military |
| army | Q37726 | military |
| legion | Q189573 | military |
| religious order | Q1133779 | religious |
| knightly order | Q471195 | religious |
| ethnic group | Q41710 | ethnic |
| tribe | Q133311 | ethnic |
| political party | Q7278 | political |
| organization | Q43229 | political |

### 4.2 Group 속성 매핑

| Wikidata Property | CHALDEAS Field |
|-------------------|----------------|
| rdfs:label | name, name_ko |
| P571 (inception) | founded_year |
| P576 (dissolved) | dissolved_year |
| P17 (country) | territory_id |
| P361 (part of) | group_relations.parent |
| P527 (has part) | 하위 group 탐색 |

### 4.3 Group Members (구성원)

**P463 (member of)** - Person → Group:
```
Jacques de Molay (Q212856)
  P463 → Knights Templar (Q42308)
    P580: 1265
    P582: 1314
    P39 (position held): Grand Master
```

**P488 (chairperson) / P35 (head of state)** - Group → Person:
```
Knights Templar (Q42308)
  P488 → Jacques de Molay (Q212856)
    P580: 1292
    P582: 1314
```

**매핑:**
```python
def extract_group_members_from_person(person_entity):
    """P463 (member of) 사용"""
    members = []
    for p463 in get_claims(person_entity, 'P463'):
        group_qid = p463['value']['id']
        qualifiers = p463.get('qualifiers', {})

        # P39 (position held) = 역할
        role = None
        if 'P39' in qualifiers:
            role = get_label(qualifiers['P39'][0]['value']['id'])

        members.append({
            'group_qid': group_qid,
            'role': role or 'member',
            'valid_from': parse_time(qualifiers.get('P580')),
            'valid_until': parse_time(qualifiers.get('P582'))
        })
    return members

def extract_group_members_from_group(group_entity):
    """P488, P35 등 사용"""
    members = []

    # P488: chairperson
    for claim in get_claims(group_entity, 'P488'):
        person_qid = claim['value']['id']
        qualifiers = claim.get('qualifiers', {})
        members.append({
            'person_qid': person_qid,
            'role': 'leader',
            'valid_from': parse_time(qualifiers.get('P580')),
            'valid_until': parse_time(qualifiers.get('P582'))
        })

    return members
```

### 4.4 Group Relations (집단 간 관계)

**P361 (part of):**
```
Legio X Equestris (Q749533)
  P361 → Roman army (Q191067)
```
→ `group_relations (child: Legion X, parent: Roman Army, type: division)`

**P749 (parent organization):**
```
Knights Templar (Q42308)
  P749 → Catholic Church (Q9592)
```
→ `group_relations (child: Templars, parent: Catholic Church, type: affiliated)`

---

## 5. Event 매핑

### 5.1 Event 식별 (P31 instance of)

| Wikidata Type | QID | CHALDEAS event_type |
|---------------|-----|---------------------|
| battle | Q178561 | battle |
| war | Q198 | war |
| siege | Q188055 | siege |
| treaty | Q131569 | treaty |
| revolution | Q41397 | revolution |
| massacre | Q1261499 | massacre |
| assassination | Q3882219 | assassination |

### 5.2 Event 속성 매핑

| Wikidata Property | CHALDEAS Field |
|-------------------|----------------|
| rdfs:label | title, title_ko |
| P585 (point in time) | date_start (단일 날짜) |
| P580 (start time) | date_start |
| P582 (end time) | date_end |
| schema:description | description |
| P276 (location) | event_locations |
| P17 (country) | event_territories |
| P710 (participant) | event_persons, event_groups |
| P361 (part of) | parent_event_id |

### 5.3 Event Hierarchy (parent_event_id)

**P361 (part of):**
```
D-Day (Q16471)
  P361 → Operation Overlord (Q182990)
    P361 → Battle of Normandy (Q217199)
      P361 → World War II (Q362)
```

**매핑:**
```python
def extract_event_parent(event_entity):
    for p361 in get_claims(event_entity, 'P361'):
        parent_qid = p361['value']['id']
        # 상위가 Event 타입인지 확인
        if is_event_type(parent_qid):
            return parent_qid
    return None
```

### 5.4 Event 참여자 (Person/Group 분류)

**P710 (participant):**
```
Battle of Hastings (Q12541)
  P710 → William the Conqueror (Q36096)  # Person
  P710 → Kingdom of England (Q842138)    # Territory/State
  P710 → Norman Army (Q...)              # Group
```

**매핑 로직:**
```python
def classify_participant(qid):
    entity = get_entity(qid)
    instance_of = get_claims(entity, 'P31')

    for p31 in instance_of:
        type_qid = p31['value']['id']

        if type_qid == 'Q5':  # human
            return 'person'
        elif type_qid in TERRITORY_TYPES:
            return 'territory'
        elif type_qid in GROUP_TYPES:
            return 'group'

    return 'unknown'
```

---

## 6. 임포트 순서

데이터 의존성을 고려한 임포트 순서:

```
1. Locations (점)
   - 좌표가 있는 모든 지점
   - parent_location_id 연결

2. Territories (영역)
   - 국가, 제국, 지역
   - territory_relations 연결

3. Territory-Location 관계
   - territory_locations 채우기

4. Persons (개인)
   - birthplace_id 연결

5. Groups (집단)
   - territory_id 연결
   - group_relations 연결

6. Group Members
   - group_members 채우기

7. Events (사건)
   - parent_event_id 연결
   - event_locations 연결
   - event_territories 연결
   - event_persons 연결
   - event_groups 연결
```

---

## 7. SPARQL 쿼리 예시

### 7.1 Location + 시대별 이름

```sparql
SELECT ?location ?label ?officialName ?startTime ?endTime
WHERE {
  ?location wdt:P31/wdt:P279* wd:Q486972.  # human settlement
  ?location wdt:P625 ?coord.
  ?location rdfs:label ?label. FILTER(LANG(?label) = "en")

  OPTIONAL {
    ?location p:P1448 ?nameStmt.
    ?nameStmt ps:P1448 ?officialName.
    OPTIONAL { ?nameStmt pq:P580 ?startTime. }
    OPTIONAL { ?nameStmt pq:P582 ?endTime. }
  }
}
LIMIT 1000
```

### 7.2 Territory + 소속 관계

```sparql
SELECT ?territory ?label ?parent ?parentLabel ?startTime ?endTime
WHERE {
  ?territory wdt:P31/wdt:P279* wd:Q6256.  # country
  ?territory rdfs:label ?label. FILTER(LANG(?label) = "en")

  OPTIONAL {
    ?territory p:P131 ?stmt.
    ?stmt ps:P131 ?parent.
    ?parent rdfs:label ?parentLabel. FILTER(LANG(?parentLabel) = "en")
    OPTIONAL { ?stmt pq:P580 ?startTime. }
    OPTIONAL { ?stmt pq:P582 ?endTime. }
  }
}
LIMIT 1000
```

### 7.3 Person + Group 소속

```sparql
SELECT ?person ?personLabel ?group ?groupLabel ?role ?startTime ?endTime
WHERE {
  ?person wdt:P31 wd:Q5.  # human
  ?person rdfs:label ?personLabel. FILTER(LANG(?personLabel) = "en")

  ?person p:P463 ?memberStmt.
  ?memberStmt ps:P463 ?group.
  ?group rdfs:label ?groupLabel. FILTER(LANG(?groupLabel) = "en")

  OPTIONAL {
    ?memberStmt pq:P39 ?position.
    ?position rdfs:label ?role. FILTER(LANG(?role) = "en")
  }
  OPTIONAL { ?memberStmt pq:P580 ?startTime. }
  OPTIONAL { ?memberStmt pq:P582 ?endTime. }
}
LIMIT 1000
```

---

## 8. 덤프 파일 처리

### 8.1 엔티티 타입 판별

```python
def classify_entity(entity):
    """Wikidata 엔티티를 CHALDEAS 타입으로 분류"""
    p31_values = get_claim_values(entity, 'P31')

    for qid in p31_values:
        if qid == 'Q5':
            return 'person'
        if qid in LOCATION_TYPE_QIDS:
            return 'location'
        if qid in TERRITORY_TYPE_QIDS:
            return 'territory'
        if qid in GROUP_TYPE_QIDS:
            return 'group'
        if qid in EVENT_TYPE_QIDS:
            return 'event'

    return None
```

### 8.2 추출 파이프라인

```
Wikidata Dump (93GB bz2)
    │
    ├─→ locations.jsonl (점)
    ├─→ territories.jsonl (영역)
    ├─→ persons.jsonl (개인)
    ├─→ groups.jsonl (집단)
    └─→ events.jsonl (사건)

각 파일:
    │
    └─→ DB Import (순서대로)
```

---

## 작성일: 2026-02-05
