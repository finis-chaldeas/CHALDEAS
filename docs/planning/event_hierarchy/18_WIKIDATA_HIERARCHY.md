# Wikidata 기반 이벤트 계층화

**작성일**: 2026-01-28
**목적**: Wikidata의 기존 관계 데이터를 활용한 이벤트 계층 구조 구축

---

## 1. 개요

### 왜 Wikidata인가?

| 장점 | 설명 |
|------|------|
| **이미 구조화됨** | 수백만 편집자가 이미 관계 정의 |
| **표준화** | QID로 중복 없이 식별 |
| **다국어** | 한국어 라벨 포함 |
| **무료** | API 무제한 (rate limit만 주의) |
| **신뢰도** | 커뮤니티 검증된 데이터 |

### 현재 DB 상태

```sql
-- Wikidata QID가 있는 이벤트
SELECT COUNT(*) FROM events WHERE wikidata_id IS NOT NULL;
-- 예상: ~15,000-20,000개 (30-40%)

-- QID 없는 이벤트는 LLM 분류로 폴백
```

---

## 2. 활용할 Wikidata 속성

### 2.1 핵심 속성

| Property | 이름 | 설명 | 예시 |
|----------|------|------|------|
| **P361** | part of | 상위 개념/이벤트 | Battle of Agincourt → Hundred Years' War |
| **P31** | instance of | 유형 | Q178561 (battle), Q198 (war) |
| **P585** | point in time | 단일 날짜 | 1415-10-25 |
| **P580** | start time | 시작일 | |
| **P582** | end time | 종료일 | |
| **P17** | country | 관련 국가 | |
| **P276** | location | 발생 장소 | |

### 2.2 보조 속성

| Property | 이름 | 활용 |
|----------|------|------|
| P1269 | facet of | 관련 상위 주제 |
| P921 | main subject | 주요 주제 |
| P1343 | described by source | 출처 문헌 |
| P910 | topic's main category | Wikipedia 카테고리 |
| P527 | has part | 하위 구성요소 (역방향) |

### 2.3 이벤트 유형 분류 (P31)

```python
EVENT_TYPE_MAPPING = {
    # 전쟁 관련
    "Q198": "war",           # war
    "Q178561": "war",        # battle
    "Q188055": "war",        # siege
    "Q645883": "war",        # military operation
    "Q1261499": "war",       # naval battle

    # 정치/사회
    "Q8016240": "revolution",  # political revolution
    "Q124734": "revolution",   # revolution
    "Q7278": "revolution",     # political revolution
    "Q28640": "movement",      # social movement

    # 문화/예술
    "Q968159": "artistic_period",   # art movement
    "Q3326717": "artistic_period",  # cultural movement

    # 철학/사상
    "Q5891": "philosophical_school",  # philosophy
    "Q1387659": "philosophical_school",  # philosophical movement

    # 종교
    "Q9174": "religious",      # religion
    "Q1068640": "religious",   # religious movement

    # 과학
    "Q1297532": "scientific_era",  # scientific revolution

    # 탐험
    "Q2401485": "expedition",  # expedition
    "Q150388": "expedition",   # exploration

    # 왕조
    "Q164950": "dynasty",      # dynasty
    "Q7269": "dynasty",        # monarch (치세)
}
```

---

## 3. SPARQL 쿼리

### 3.1 단일 이벤트의 상위 구조 조회

```sparql
# 특정 이벤트(Q215380 = Battle of Agincourt)의 상위 이벤트
SELECT ?parent ?parentLabel ?parentDescription WHERE {
  wd:Q215380 wdt:P361 ?parent .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,ko". }
}
```

**결과 예시:**
```json
{
  "parent": "Q12544",
  "parentLabel": "Hundred Years' War",
  "parentDescription": "series of conflicts between England and France (1337–1453)"
}
```

### 3.2 상위 이벤트의 모든 하위 이벤트 조회

```sparql
# 백년전쟁(Q12544)에 속하는 모든 이벤트
SELECT ?event ?eventLabel ?date WHERE {
  ?event wdt:P361 wd:Q12544 .
  OPTIONAL { ?event wdt:P585 ?date . }
  OPTIONAL { ?event wdt:P580 ?date . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,ko". }
}
ORDER BY ?date
```

### 3.3 계층 깊이 탐색 (재귀)

```sparql
# 이벤트의 전체 상위 계층 (최대 3단계)
SELECT ?event ?eventLabel ?parent1 ?parent1Label ?parent2 ?parent2Label WHERE {
  VALUES ?event { wd:Q215380 }  # Battle of Agincourt

  OPTIONAL { ?event wdt:P361 ?parent1 . }
  OPTIONAL { ?parent1 wdt:P361 ?parent2 . }

  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,ko". }
}
```

### 3.4 벌크 조회 (우리 DB 이벤트들)

```sparql
# 여러 QID 한번에 조회
SELECT ?event ?eventLabel ?parent ?parentLabel ?eventType WHERE {
  VALUES ?event { wd:Q215380 wd:Q12544 wd:Q8740 }

  OPTIONAL { ?event wdt:P361 ?parent . }
  OPTIONAL { ?event wdt:P31 ?eventType . }

  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,ko". }
}
```

---

## 4. 구현 설계

### 4.1 파일 구조

```
poc/scripts/hierarchy/
├── wikidata_client.py          # Wikidata API 클라이언트
├── fetch_event_hierarchy.py    # 계층 정보 수집
├── map_to_db.py                # DB 매핑
└── validate_mapping.py         # 검증
```

### 4.2 Wikidata 클라이언트

```python
# poc/scripts/hierarchy/wikidata_client.py

import httpx
import asyncio
from typing import Optional
from dataclasses import dataclass

WIKIDATA_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
WIKIDATA_API_ENDPOINT = "https://www.wikidata.org/w/api.php"

@dataclass
class WikidataEvent:
    qid: str
    label: str
    label_ko: Optional[str]
    parent_qid: Optional[str]
    parent_label: Optional[str]
    event_type: Optional[str]
    start_date: Optional[int]
    end_date: Optional[int]


class WikidataClient:
    def __init__(self, rate_limit: float = 1.0):
        """
        Args:
            rate_limit: 초당 요청 수 (Wikidata는 초당 1-2회 권장)
        """
        self.rate_limit = rate_limit
        self.last_request = 0
        self.client = httpx.AsyncClient(timeout=30.0)

    async def _throttle(self):
        """Rate limiting"""
        now = asyncio.get_event_loop().time()
        wait = (1.0 / self.rate_limit) - (now - self.last_request)
        if wait > 0:
            await asyncio.sleep(wait)
        self.last_request = asyncio.get_event_loop().time()

    async def query_sparql(self, query: str) -> list[dict]:
        """SPARQL 쿼리 실행"""
        await self._throttle()

        response = await self.client.get(
            WIKIDATA_SPARQL_ENDPOINT,
            params={"query": query, "format": "json"},
            headers={"User-Agent": "CHALDEAS/1.0 (https://chaldeas.site)"}
        )
        response.raise_for_status()

        data = response.json()
        return data.get("results", {}).get("bindings", [])

    async def get_event_hierarchy(self, qid: str) -> WikidataEvent:
        """단일 이벤트의 계층 정보 조회"""
        query = f"""
        SELECT ?label ?labelKo ?parent ?parentLabel ?eventType ?startDate ?endDate WHERE {{
          OPTIONAL {{ wd:{qid} rdfs:label ?label . FILTER(LANG(?label) = "en") }}
          OPTIONAL {{ wd:{qid} rdfs:label ?labelKo . FILTER(LANG(?labelKo) = "ko") }}
          OPTIONAL {{ wd:{qid} wdt:P361 ?parent . }}
          OPTIONAL {{ ?parent rdfs:label ?parentLabel . FILTER(LANG(?parentLabel) = "en") }}
          OPTIONAL {{ wd:{qid} wdt:P31 ?eventType . }}
          OPTIONAL {{ wd:{qid} wdt:P580 ?startDate . }}
          OPTIONAL {{ wd:{qid} wdt:P582 ?endDate . }}
          OPTIONAL {{ wd:{qid} wdt:P585 ?startDate . }}
        }}
        LIMIT 1
        """

        results = await self.query_sparql(query)
        if not results:
            return WikidataEvent(qid=qid, label="", label_ko=None,
                                parent_qid=None, parent_label=None,
                                event_type=None, start_date=None, end_date=None)

        r = results[0]
        return WikidataEvent(
            qid=qid,
            label=r.get("label", {}).get("value", ""),
            label_ko=r.get("labelKo", {}).get("value"),
            parent_qid=self._extract_qid(r.get("parent", {}).get("value")),
            parent_label=r.get("parentLabel", {}).get("value"),
            event_type=self._extract_qid(r.get("eventType", {}).get("value")),
            start_date=self._parse_date(r.get("startDate", {}).get("value")),
            end_date=self._parse_date(r.get("endDate", {}).get("value")),
        )

    async def get_events_bulk(self, qids: list[str]) -> list[WikidataEvent]:
        """벌크 조회 (최대 50개씩)"""
        results = []
        for i in range(0, len(qids), 50):
            batch = qids[i:i+50]
            batch_results = await self._query_batch(batch)
            results.extend(batch_results)
        return results

    async def _query_batch(self, qids: list[str]) -> list[WikidataEvent]:
        """배치 SPARQL 쿼리"""
        values = " ".join(f"wd:{qid}" for qid in qids)
        query = f"""
        SELECT ?event ?label ?labelKo ?parent ?parentLabel ?eventType WHERE {{
          VALUES ?event {{ {values} }}
          OPTIONAL {{ ?event rdfs:label ?label . FILTER(LANG(?label) = "en") }}
          OPTIONAL {{ ?event rdfs:label ?labelKo . FILTER(LANG(?labelKo) = "ko") }}
          OPTIONAL {{ ?event wdt:P361 ?parent . }}
          OPTIONAL {{ ?parent rdfs:label ?parentLabel . FILTER(LANG(?parentLabel) = "en") }}
          OPTIONAL {{ ?event wdt:P31 ?eventType . }}
        }}
        """

        rows = await self.query_sparql(query)

        # QID별로 그룹화 (여러 parent가 있을 수 있음)
        by_qid = {}
        for r in rows:
            qid = self._extract_qid(r.get("event", {}).get("value"))
            if qid not in by_qid:
                by_qid[qid] = r

        return [
            WikidataEvent(
                qid=qid,
                label=r.get("label", {}).get("value", ""),
                label_ko=r.get("labelKo", {}).get("value"),
                parent_qid=self._extract_qid(r.get("parent", {}).get("value")),
                parent_label=r.get("parentLabel", {}).get("value"),
                event_type=self._extract_qid(r.get("eventType", {}).get("value")),
                start_date=None,
                end_date=None,
            )
            for qid, r in by_qid.items()
        ]

    @staticmethod
    def _extract_qid(uri: Optional[str]) -> Optional[str]:
        """http://www.wikidata.org/entity/Q12345 -> Q12345"""
        if not uri:
            return None
        if uri.startswith("http://www.wikidata.org/entity/"):
            return uri.split("/")[-1]
        return uri

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[int]:
        """ISO 날짜 -> 연도 정수"""
        if not date_str:
            return None
        try:
            # +1415-10-25T00:00:00Z -> 1415
            # -0490-01-01T00:00:00Z -> -490
            if date_str.startswith("+"):
                return int(date_str[1:5])
            elif date_str.startswith("-"):
                return -int(date_str[1:5])
            return int(date_str[:4])
        except:
            return None
```

### 4.3 DB 연동 스크립트

```python
# poc/scripts/hierarchy/fetch_event_hierarchy.py

import asyncio
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.event import Event
from wikidata_client import WikidataClient, WikidataEvent

# Aggregate 이벤트 QID -> DB ID 캐시
AGGREGATE_CACHE: dict[str, int] = {}


async def fetch_and_update_hierarchies(batch_size: int = 100):
    """DB의 모든 이벤트에 대해 Wikidata 계층 정보 업데이트"""

    client = WikidataClient(rate_limit=2.0)  # 초당 2회
    db = SessionLocal()

    try:
        # 1. QID가 있는 이벤트 조회
        events = db.query(Event).filter(
            Event.wikidata_id.isnot(None),
            Event.parent_event_id.is_(None)  # 아직 부모 없는 것만
        ).all()

        print(f"처리할 이벤트: {len(events)}개")

        # 2. 배치 처리
        for i in range(0, len(events), batch_size):
            batch = events[i:i+batch_size]
            qids = [e.wikidata_id for e in batch]

            # Wikidata 조회
            wd_events = await client.get_events_bulk(qids)

            # 3. DB 업데이트
            for event, wd_event in zip(batch, wd_events):
                await update_event_hierarchy(db, event, wd_event)

            db.commit()
            print(f"진행: {min(i+batch_size, len(events))}/{len(events)}")

    finally:
        db.close()


async def update_event_hierarchy(db: Session, event: Event, wd_event: WikidataEvent):
    """단일 이벤트의 계층 정보 업데이트"""

    if not wd_event.parent_qid:
        return  # 상위 이벤트 없음

    # 1. 부모 이벤트 찾기/생성
    parent_id = await get_or_create_parent(db, wd_event.parent_qid, wd_event.parent_label)

    if parent_id:
        event.parent_event_id = parent_id

        # 2. hierarchy_level 설정
        parent = db.query(Event).get(parent_id)
        if parent:
            event.hierarchy_level = parent.hierarchy_level + 1
        else:
            event.hierarchy_level = 3  # 기본값

        # 3. aggregate_type 추론
        if wd_event.event_type:
            event.aggregate_type = EVENT_TYPE_MAPPING.get(wd_event.event_type)


async def get_or_create_parent(db: Session, parent_qid: str, parent_label: str) -> Optional[int]:
    """부모 이벤트 조회 또는 생성"""

    # 캐시 확인
    if parent_qid in AGGREGATE_CACHE:
        return AGGREGATE_CACHE[parent_qid]

    # DB에서 찾기
    parent = db.query(Event).filter(Event.wikidata_id == parent_qid).first()

    if parent:
        AGGREGATE_CACHE[parent_qid] = parent.id
        return parent.id

    # 없으면 새로 생성 (Aggregate 이벤트)
    # 주의: Wikidata에서 추가 정보 조회 필요
    client = WikidataClient()
    wd_parent = await client.get_event_hierarchy(parent_qid)

    new_parent = Event(
        title=parent_label or wd_parent.label,
        title_ko=wd_parent.label_ko,
        slug=f"aggregate-{parent_qid.lower()}",
        wikidata_id=parent_qid,
        date_start=wd_parent.start_date or 0,
        date_end=wd_parent.end_date,
        is_aggregate=True,
        hierarchy_level=2,  # Aggregate
        importance=4,  # 상위 이벤트는 중요도 높게
    )

    db.add(new_parent)
    db.flush()  # ID 생성

    AGGREGATE_CACHE[parent_qid] = new_parent.id
    return new_parent.id


if __name__ == "__main__":
    asyncio.run(fetch_and_update_hierarchies())
```

---

## 5. 실행 계획

### 5.1 단계별 실행

```bash
# 1단계: 테스트 (100개)
python poc/scripts/hierarchy/fetch_event_hierarchy.py --limit 100 --dry-run

# 2단계: 소규모 (1,000개)
python poc/scripts/hierarchy/fetch_event_hierarchy.py --limit 1000

# 3단계: 전체 실행
python poc/scripts/hierarchy/fetch_event_hierarchy.py

# 4단계: 검증
python poc/scripts/hierarchy/validate_mapping.py
```

### 5.2 예상 소요 시간

| 이벤트 수 | Rate (2/초) | 예상 시간 |
|----------|-------------|----------|
| 1,000 | 500 req | ~8분 |
| 10,000 | 5,000 req | ~80분 |
| 20,000 | 10,000 req | ~160분 |

**최적화:**
- 배치 쿼리로 50개씩 묶음 → 시간 50배 단축
- 실제: 20,000개 ≈ 3-4분

### 5.3 Rate Limit 주의

```python
# Wikidata 권장사항
# - User-Agent 헤더 필수
# - 초당 1-2회 권장 (burst 가능)
# - 대량 조회시 배치 SPARQL 사용

headers = {
    "User-Agent": "CHALDEAS/1.0 (https://chaldeas.site; contact@chaldeas.site)"
}
```

---

## 6. 예상 결과

### 6.1 커버리지

| 항목 | 예상 |
|------|------|
| QID 있는 이벤트 | ~20,000 (43%) |
| P361 있는 이벤트 | ~8,000 (40% of QID) |
| 자동 연결 가능 | ~8,000 (17% of 전체) |

### 6.2 생성될 Aggregate 이벤트

| 카테고리 | 예상 개수 | 예시 |
|----------|----------|------|
| 전쟁 | ~100 | Hundred Years' War, World War I |
| 혁명 | ~30 | French Revolution, Industrial Revolution |
| 문화운동 | ~20 | Renaissance, Enlightenment |
| 탐험 | ~15 | Age of Discovery |
| 종교 | ~20 | Crusades, Reformation |

---

## 7. 제한사항 및 대응

| 제한 | 대응 |
|------|------|
| P361 없는 이벤트 | LLM 분류로 폴백 (19_LLM_CLASSIFIER.md) |
| 다중 부모 (P361 여러 개) | 첫 번째만 사용 또는 가장 구체적인 것 선택 |
| 순환 참조 | 검증 스크립트로 탐지 & 수정 |
| 잘못된 관계 | 사용자 피드백으로 수정 |

---

## 8. 모니터링 쿼리

```sql
-- Wikidata 연결 현황
SELECT
    COUNT(*) FILTER (WHERE wikidata_id IS NOT NULL) as has_qid,
    COUNT(*) FILTER (WHERE parent_event_id IS NOT NULL) as has_parent,
    COUNT(*) FILTER (WHERE is_aggregate = true) as aggregates
FROM events;

-- 부모별 자식 수
SELECT
    p.title as parent_title,
    COUNT(c.id) as child_count
FROM events p
JOIN events c ON c.parent_event_id = p.id
WHERE p.is_aggregate = true
GROUP BY p.id, p.title
ORDER BY child_count DESC
LIMIT 20;

-- 고아 이벤트 (중요도 높은데 부모 없음)
SELECT title, importance, wikidata_id
FROM events
WHERE parent_event_id IS NULL
AND importance >= 4
ORDER BY importance DESC;
```
