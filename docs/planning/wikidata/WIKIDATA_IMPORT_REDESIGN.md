# Wikidata Import 재설계

## 현재 문제점 요약

### 1. 위치 데이터 무시
- P276 (location) 가져왔으나 저장 안 함
- `insert_event()`에서 location_qid 완전 무시
- 결과: 98.2% 이벤트가 위치 없음

### 2. 잘못된 Description
- 이벤트 제목과 description 불일치
- 예: "Treaty of Cusset" → Vichy 도시 설명
- 원인: Wikidata description이 관련 엔티티 것으로 대체됨

### 3. 비이벤트 임포트
- 531개 의심 항목 중 61개(11.5%) 오분류
- 장소, 개념, 물건이 이벤트로 임포트됨
- 예: Novgorod Republic (국가), Crete (섬), Illyrian Helmet (물건)

### 4. 관계 미구현
- P710 (participants) 호출 안 함
- P361 (part_of) 저장 안 함
- 이벤트 계층 구조 없음

---

## 재설계 원칙

### 1. 단일 책임 원칙
각 임포터는 하나의 엔티티 타입만 담당

```
WikidataLocationImporter  → locations 테이블
WikidataPersonImporter    → persons 테이블
WikidataEventImporter     → events 테이블 + 연결
```

### 2. 선 검증, 후 저장
```
1. Wikidata에서 가져오기
2. 타입 검증 (P31 instance of 확인)
3. 필수 데이터 검증 (날짜, 설명 등)
4. 연관 엔티티 먼저 생성 (location, person)
5. 메인 엔티티 저장
6. 관계 연결
```

### 3. 연관 엔티티 선생성
```
이벤트 저장 전:
  1. location_qid로 locations 조회/생성
  2. participant_qids로 persons 조회/생성
  3. part_of_qid로 parent event 조회
```

---

## 새 임포트 구조

### 파일 구조
```
poc/scripts/wikidata/
├── importers/
│   ├── __init__.py
│   ├── base.py              # BaseImporter 추상 클래스
│   ├── location_importer.py # 위치 임포트
│   ├── person_importer.py   # 인물 임포트
│   └── event_importer.py    # 이벤트 임포트 (위치/인물 의존)
├── validators/
│   ├── __init__.py
│   ├── event_validator.py   # 이벤트 타입 검증
│   └── quality_checker.py   # 데이터 품질 검사
├── import_all.py            # 전체 임포트 오케스트레이터
└── backfill_locations.py    # 기존 데이터 보완 (현재 작성됨)
```

### 클래스 설계

```python
# base.py
class BaseImporter(ABC):
    """모든 임포터의 기본 클래스"""

    def __init__(self, db_config: dict):
        self.conn = None
        self.stats = {'fetched': 0, 'inserted': 0, 'skipped': 0, 'errors': 0}

    @abstractmethod
    def fetch_from_wikidata(self, qid: str) -> dict:
        """Wikidata에서 엔티티 가져오기"""
        pass

    @abstractmethod
    def validate(self, entity: dict) -> bool:
        """엔티티 유효성 검증"""
        pass

    @abstractmethod
    def insert(self, entity: dict) -> int:
        """DB에 저장하고 ID 반환"""
        pass

    def get_or_create(self, qid: str) -> int:
        """조회 또는 생성"""
        existing = self.find_by_wikidata_id(qid)
        if existing:
            return existing
        entity = self.fetch_from_wikidata(qid)
        if not self.validate(entity):
            return None
        return self.insert(entity)
```

```python
# location_importer.py
class LocationImporter(BaseImporter):
    """위치 임포터"""

    def fetch_from_wikidata(self, qid: str) -> dict:
        query = f"""
        SELECT ?label ?labelKo ?description ?coord ?typeLabel ?countryLabel WHERE {{
            BIND(wd:{qid} AS ?loc)
            ?loc rdfs:label ?label. FILTER(LANG(?label) = "en")
            OPTIONAL {{ ?loc rdfs:label ?labelKo. FILTER(LANG(?labelKo) = "ko") }}
            OPTIONAL {{ ?loc schema:description ?description. FILTER(LANG(?description) = "en") }}
            OPTIONAL {{ ?loc wdt:P625 ?coord. }}       # 좌표
            OPTIONAL {{ ?loc wdt:P31 ?type. }}         # instance of
            OPTIONAL {{ ?loc wdt:P17 ?country. }}      # country
            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """
        # ... 파싱 및 반환

    def validate(self, entity: dict) -> bool:
        # 최소한 이름은 있어야 함
        return bool(entity.get('label'))

    def insert(self, entity: dict) -> int:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO locations (
                name, name_ko, description,
                latitude, longitude, type,
                wikidata_id, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
        """, (
            entity['label'],
            entity.get('label_ko'),
            entity.get('description'),
            entity.get('latitude'),
            entity.get('longitude'),
            entity.get('type', 'place'),
            entity['qid']
        ))
        return cur.fetchone()[0]
```

```python
# event_importer.py
class EventImporter(BaseImporter):
    """이벤트 임포터 - 위치/인물 임포터 의존"""

    def __init__(self, db_config: dict):
        super().__init__(db_config)
        self.location_importer = LocationImporter(db_config)
        self.person_importer = PersonImporter(db_config)
        self.validator = EventValidator()

    def fetch_from_wikidata(self, qid: str) -> dict:
        query = f"""
        SELECT ?label ?labelKo ?description
               ?pointInTime ?startTime ?endTime
               ?location ?locationLabel
               ?partOf ?partOfLabel
               ?instanceOf ?instanceOfLabel
        WHERE {{
            BIND(wd:{qid} AS ?event)
            ?event rdfs:label ?label. FILTER(LANG(?label) = "en")
            OPTIONAL {{ ?event rdfs:label ?labelKo. FILTER(LANG(?labelKo) = "ko") }}
            OPTIONAL {{ ?event schema:description ?description. FILTER(LANG(?description) = "en") }}

            OPTIONAL {{ ?event wdt:P585 ?pointInTime. }}  # point in time
            OPTIONAL {{ ?event wdt:P580 ?startTime. }}    # start time
            OPTIONAL {{ ?event wdt:P582 ?endTime. }}      # end time

            OPTIONAL {{ ?event wdt:P276 ?location. }}     # location
            OPTIONAL {{ ?event wdt:P361 ?partOf. }}       # part of
            OPTIONAL {{ ?event wdt:P31 ?instanceOf. }}    # instance of (타입 검증용)

            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """
        # ... 파싱 및 반환

    def validate(self, entity: dict) -> bool:
        """이벤트인지 검증"""
        # 1. P31 (instance of) 확인
        instance_of = entity.get('instance_of_qid', '')

        # 비이벤트 타입 제외
        EXCLUDED_TYPES = {
            'Q515',      # city
            'Q6256',     # country
            'Q35657',    # state
            'Q82794',    # region
            'Q23442',    # island
            'Q8502',     # mountain
            'Q4022',     # river
            'Q23397',    # lake
            'Q5',        # human
            'Q16521',    # taxon (생물종)
            'Q35120',    # entity (너무 추상적)
        }

        if instance_of in EXCLUDED_TYPES:
            return False

        # 2. 날짜 필수
        if not (entity.get('point_in_time') or entity.get('start_time')):
            return False

        # 3. LLM 검증 (의심스러운 경우)
        if self.validator.is_suspicious(entity):
            return self.validator.llm_classify(entity) == 'EVENT'

        return True

    def insert(self, entity: dict) -> int:
        """이벤트 저장 (위치/인물 먼저 생성)"""

        # 1. 위치 먼저 생성
        location_id = None
        if entity.get('location_qid'):
            location_id = self.location_importer.get_or_create(entity['location_qid'])

        # 2. 이벤트 저장
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO events (
                title, title_ko, description,
                date_start, date_end,
                primary_location_id,
                wikidata_id,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
        """, (
            entity['label'],
            entity.get('label_ko'),
            entity.get('description'),
            entity.get('start_year'),
            entity.get('end_year'),
            location_id,  # ← 핵심: 위치 연결!
            entity['qid']
        ))
        event_id = cur.fetchone()[0]

        # 3. event_locations 브릿지 생성
        if location_id:
            cur.execute("""
                INSERT INTO event_locations (event_id, location_id, relationship_type)
                VALUES (%s, %s, 'occurred_at')
            """, (event_id, location_id))

        # 4. 참여자 연결
        participants = self.fetch_participants(entity['qid'])
        for p in participants:
            person_id = self.person_importer.get_or_create(p['qid'])
            if person_id:
                cur.execute("""
                    INSERT INTO event_persons (event_id, person_id, role)
                    VALUES (%s, %s, %s)
                """, (event_id, person_id, p.get('role', 'participant')))

        # 5. 부모 이벤트 연결 (있으면)
        if entity.get('part_of_qid'):
            cur.execute("""
                SELECT id FROM events WHERE wikidata_id = %s
            """, (entity['part_of_qid'],))
            parent = cur.fetchone()
            if parent:
                cur.execute("""
                    INSERT INTO event_relationships (source_id, target_id, relationship_type)
                    VALUES (%s, %s, 'part_of')
                """, (event_id, parent[0]))

        return event_id
```

---

## 데이터 검증 흐름

```
┌─────────────────────────────────────────────────────────────┐
│  1. Wikidata SPARQL 쿼리                                    │
│     - 이벤트 기본 정보                                      │
│     - P31 (instance of) - 타입 검증용                       │
│     - P276 (location)                                       │
│     - P710 (participants)                                   │
│     - P361 (part of)                                        │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  2. 타입 검증                                               │
│     - P31이 제외 목록에 있으면 스킵 (city, country, etc.)   │
│     - 날짜 없으면 스킵                                      │
│     - 의심스러우면 LLM 분류                                 │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  3. 연관 엔티티 선생성                                      │
│     - location_qid → LocationImporter.get_or_create()       │
│     - participant_qids → PersonImporter.get_or_create()     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  4. 이벤트 저장                                             │
│     - events 테이블 (primary_location_id 포함!)             │
│     - event_locations 브릿지                                │
│     - event_persons 연결                                    │
│     - event_relationships (part_of)                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 구현 우선순위

### Phase 1: 기존 데이터 정리 (즉시)
1. [x] 백필 스크립트로 위치 데이터 보완
2. [ ] 오분류 61개 이벤트 처리 (삭제 또는 이동)
3. [ ] 잘못된 description 수정

### Phase 2: 새 임포터 구현 (단기)
1. [ ] BaseImporter 추상 클래스
2. [ ] LocationImporter 구현
3. [ ] EventImporter 구현 (위치 연결 포함)
4. [ ] EventValidator (타입 검증)

### Phase 3: 관계 구현 (중기)
1. [ ] PersonImporter 구현
2. [ ] 참여자 연결 (P710)
3. [ ] 이벤트 계층 (P361)

### Phase 4: 품질 개선 (장기)
1. [ ] LLM 기반 분류 검증
2. [ ] Description 일치 검사
3. [ ] 중복 탐지

---

## 테스트 계획

### 단위 테스트
- LocationImporter: 좌표 있는/없는 위치 처리
- EventImporter: 위치 연결 확인
- EventValidator: 비이벤트 필터링

### 통합 테스트
- 100개 이벤트 임포트 후:
  - 위치 연결률 > 50%
  - 오분류율 < 5%
  - 참여자 연결 존재

---

*작성: 2026-02-05*
