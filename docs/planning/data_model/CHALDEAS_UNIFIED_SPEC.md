# CHALDEAS 통합 기획서

> **버전**: 4.0
> **작성일**: 2026-02-01
> **상태**: 확정

---

## 1. 비전

### 1.1 핵심 철학

> **"모든 역사는 누가(Person) 어디서(Location) 언제(Time) 무엇을(Event) 했는가로 결정된다."**

이 한 문장이 CHALDEAS의 전부다.

### 1.2 최종 목표

**3D 지구본에서 BCE 3000 ~ 현재까지의 역사를 탐색하는 시스템**

- 지구본을 돌리며 특정 시대/지역의 사건을 본다
- 클릭하면 누가 관여했는지, 어디서 일어났는지, 왜 일어났는지 알 수 있다
- **모든 정보에는 출처(근거)가 있다**

### 1.3 큐레이션 목표

**"Perfectly Curated" 데이터**

```
sources (원본들)                    엔티티 (정서된 설명)
─────────────────────────────────────────────────────────────
Wikipedia 본문                  →   description
Gutenberg 책 A                      "Richard I (1157-1199), known as
Gutenberg 책 B                       the Lionheart, was King of England
...                                  and a central figure in the Third
                                     Crusade..."
mentions로 연결                      ↑ 여러 출처 종합 + 정서
```

**워크플로우:**
1. **Wikipedia 있으면**: sources에 저장, mentions로 연결
2. **책 추가**: 같은 방식으로 sources + mentions 추가
3. **정서할 때**: 모든 mentions 합쳐서 description 생성
4. **정서 안 됐으면**: Wikipedia mentions에서 가져와 표시

### 1.4 핵심 원칙

| 원칙 | 설명 |
|------|------|
| **근거 필수** | 모든 정보에 출처 있어야 함 |
| **Wikidata QID = 정체성** | 모든 엔티티는 QID로 유일하게 식별 |
| **단순함** | 8개 핵심 테이블 |
| **출처 분리** | sources(원문) + mentions(연결) 분리 |
| **원본 보존** | sources.content_raw에 원본 보존 |
| **점진적 보강** | Wikipedia 초안 → 책으로 보강 → 정서 |

---

## 2. 데이터 모델

### 2.1 8대 핵심 테이블

```
┌─────────────────────────────────────────────────────────────┐
│                     CHALDEAS 데이터 모델                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────┐         ┌──────────┐         ┌──────────┐   │
│   │ persons  │◄───────►│  links   │◄───────►│  events  │   │
│   │  (누가)   │         │  (연결)   │         │ (무엇을)  │   │
│   └────┬─────┘         └────┬─────┘         └────┬─────┘   │
│        │                    │                    │         │
│        │               ┌────┴─────┐              │         │
│        │               │locations │              │         │
│        │               │ (어디서)  │              │         │
│        │               └────┬─────┘              │         │
│        │                    │                    │         │
│        └────────┬───────────┼───────────┬───────┘         │
│                 │           │           │                  │
│          ┌──────┴──────┐    │    ┌──────┴──────┐          │
│          │ entity_tags │    │    │  mentions   │          │
│          │  (태그부착)  │    │    │ (출처연결)  │          │
│          └──────┬──────┘    │    └──────┬──────┘          │
│                 │           │           │                  │
│          ┌──────┴──────┐    │    ┌──────┴──────┐          │
│          │    tags     │    │    │   sources   │          │
│          │  (태그정의)  │    │    │  (출처원문) │          │
│          └─────────────┘    │    └─────────────┘          │
│                             │                              │
└─────────────────────────────────────────────────────────────┘
```

**테이블 요약:**

| 테이블 | 역할 | 예시 |
|--------|------|------|
| persons | 인물 | 나폴레옹, 리처드 1세 |
| locations | 장소 | 파리, 워털루 |
| events | 사건 | 워털루 전투, 백년전쟁 |
| links | 엔티티 간 연결 | 나폴레옹→워털루 (지휘) |
| sources | 출처 원문 | Wikipedia 문서, 책 청크 |
| mentions | 출처→대상 연결 | 이 문서가 나폴레옹을 언급 |
| tags | 태그 정의 | #잉글랜드왕, #십자군 |
| entity_tags | 태그 부착 | 리처드 1세 + #잉글랜드왕 (1189-1199) |

### 2.2 테이블 스키마

#### persons (누가)

```sql
CREATE TABLE persons (
    id SERIAL PRIMARY KEY,
    wikidata_id VARCHAR(20) UNIQUE NOT NULL,  -- Q12345
    name VARCHAR(500) NOT NULL,
    name_ko VARCHAR(500),
    birth_year INTEGER,      -- 음수 = BCE
    death_year INTEGER,
    image_url TEXT,

    -- 정서된 설명 (여러 출처 종합)
    description TEXT,
    description_model VARCHAR(50),  -- llama3.1:8b, gpt-5-mini, manual
    description_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW()
);
```

#### locations (어디서)

```sql
CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    wikidata_id VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(500) NOT NULL,
    name_ko VARCHAR(500),
    latitude FLOAT,
    longitude FLOAT,

    -- 정서된 설명
    description TEXT,
    description_model VARCHAR(50),
    description_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW()
);
```

#### events (무엇을 + 언제)

```sql
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    wikidata_id VARCHAR(20) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    title_ko VARCHAR(500),
    date_start INTEGER,      -- 음수 = BCE
    date_end INTEGER,
    importance INTEGER DEFAULT 3,  -- 1-5

    -- 계층 구조
    parent_id INTEGER REFERENCES events(id),
    hierarchy_level INTEGER DEFAULT 3,

    -- 정서된 설명
    description TEXT,
    description_model VARCHAR(50),
    description_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW()
);
```

#### links (연결)

```sql
CREATE TABLE links (
    id SERIAL PRIMARY KEY,

    -- 연결 (방향: from → to)
    from_type VARCHAR(20) NOT NULL,  -- person, location, event
    from_id INTEGER NOT NULL,
    to_type VARCHAR(20) NOT NULL,
    to_id INTEGER NOT NULL,

    -- 카테고리 (세부 관계는 evidence가 설명)
    category VARCHAR(20),  -- family, political, military, cultural, temporal, spatial

    -- 시간 범위 (선택, 시간적 관계에 사용)
    date_start INTEGER,  -- 음수 = BCE
    date_end INTEGER,

    -- 정서된 근거 (여러 출처 종합)
    evidence TEXT,
    evidence_model VARCHAR(50),
    evidence_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_links_from ON links(from_type, from_id);
CREATE INDEX ix_links_to ON links(to_type, to_id);
CREATE INDEX ix_links_category ON links(category);
```

#### sources (출처 원문)

```sql
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,

    -- 출처 정보
    source_type VARCHAR(20) NOT NULL,  -- wikipedia, book, wikidata
    title VARCHAR(500) NOT NULL,        -- 문서명, 책 제목
    author VARCHAR(200),                -- 저자 (책인 경우)
    year INTEGER,                       -- 출판년도

    -- 청크 정보 (책인 경우)
    chapter VARCHAR(100),
    chunk_index INTEGER,

    -- 원문 (핵심!)
    content_raw TEXT NOT NULL,

    -- 메타
    url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_sources_type ON sources(source_type);
CREATE INDEX ix_sources_title ON sources(title);
```

#### mentions (출처 → 대상 연결)

```sql
CREATE TABLE mentions (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id) NOT NULL,

    -- 언급 대상 (person, location, event, 또는 link)
    target_type VARCHAR(20) NOT NULL,  -- person, location, event, link
    target_id INTEGER NOT NULL,

    -- 언급 부분 (source 내에서 해당 텍스트)
    evidence_raw TEXT NOT NULL,

    -- 위치 정보 (선택)
    position_start INTEGER,
    position_end INTEGER,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_mentions_source ON mentions(source_id);
CREATE INDEX ix_mentions_target ON mentions(target_type, target_id);
```

#### tags (태그 정의)

```sql
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    name_ko VARCHAR(100),
    wikidata_id VARCHAR(20),

    -- Wikipedia navbox 출처 (자동 생성용)
    navbox_template VARCHAR(500),  -- "Template:English_monarchs"

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_tags_name ON tags(name);
CREATE INDEX ix_tags_navbox ON tags(navbox_template);
```

#### entity_tags (태그 부착)

```sql
CREATE TABLE entity_tags (
    id SERIAL PRIMARY KEY,

    -- 대상 엔티티
    entity_type VARCHAR(20) NOT NULL,  -- person, location, event
    entity_id INTEGER NOT NULL,

    -- 태그
    tag_id INTEGER REFERENCES tags(id) NOT NULL,

    -- 시간 범위 (선택)
    date_start INTEGER,  -- 음수 = BCE
    date_end INTEGER,

    -- 출처 (선택)
    source_id INTEGER REFERENCES sources(id),

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_entity_tags_entity ON entity_tags(entity_type, entity_id);
CREATE INDEX ix_entity_tags_tag ON entity_tags(tag_id);
```

**태그 사용 예시:**

```
tags:
  #1: "Kings of England" (navbox: Template:English_monarchs)
  #2: "Knights of the Round Table"
  #3: "Third Crusade participants"
  #4: "House of Plantagenet"

entity_tags:
  Richard I + #1, date: 1189-1199  (왕위 기간)
  Richard I + #3                    (십자군 참여)
  Richard I + #4                    (왕조 소속)

  Paris + #5 ("Capitals of France"), date: 843-present
```

### 2.3 카테고리 (category)

관계의 세부 종류는 evidence가 설명. category는 대분류만:

| category | 설명 | 예시 |
|----------|------|------|
| `family` | 가족/혈연 관계 | 부모, 자녀, 형제 |
| `political` | 정치적 관계 | 군주-신하, 동맹, 적대 |
| `military` | 군사적 관계 | 지휘관, 전투 참여 |
| `cultural` | 문화적 관계 | 스승-제자, 영향, 전통 |
| `temporal` | 시간적 관계 | 선행, 후속, 동시대 |
| `spatial` | 공간적 관계 | 발생 장소, 출생지 |

### 2.4 데이터 흐름 예시

**Wikipedia "Battle of Waterloo" 문서 처리:**

```
1. sources에 저장
   ┌────────────────────────────────────────┐
   │ id: 100                                │
   │ source_type: wikipedia                 │
   │ title: "Battle of Waterloo"            │
   │ content_raw: (전체 본문)               │
   │ url: https://en.wikipedia.org/...      │
   └────────────────────────────────────────┘

2. mentions 생성 (이 문서가 언급하는 것들)
   ┌────────────────────────────────────────┐
   │ source_id: 100                         │
   │ target_type: event                     │
   │ target_id: (워털루 전투 ID)            │
   │ evidence_raw: "The Battle of Waterloo  │
   │               was fought on..."        │
   ├────────────────────────────────────────┤
   │ source_id: 100                         │
   │ target_type: person                    │
   │ target_id: (나폴레옹 ID)               │
   │ evidence_raw: "Napoleon commanded the  │
   │               French forces..."        │
   ├────────────────────────────────────────┤
   │ source_id: 100                         │
   │ target_type: link                      │
   │ target_id: (나폴레옹↔워털루 link ID)   │
   │ evidence_raw: "Napoleon commanded the  │
   │               French forces at..."     │
   └────────────────────────────────────────┘
```

**책 "Le Morte d'Arthur" Chapter 1 처리:**

```
1. sources에 청크별 저장
   ┌────────────────────────────────────────┐
   │ id: 200                                │
   │ source_type: book                      │
   │ title: "Le Morte d'Arthur"             │
   │ author: "Thomas Malory"                │
   │ chapter: "Chapter 1"                   │
   │ chunk_index: 1                         │
   │ content_raw: "King Arthur rode forth   │
   │              with his knights..."      │
   └────────────────────────────────────────┘

2. mentions 생성
   ┌────────────────────────────────────────┐
   │ source_id: 200                         │
   │ target_type: person                    │
   │ target_id: (아서왕 ID)                 │
   │ evidence_raw: "King Arthur rode        │
   │               forth..."                │
   ├────────────────────────────────────────┤
   │ source_id: 200                         │
   │ target_type: person                    │
   │ target_id: (모드레드 ID)               │
   │ evidence_raw: "the traitor Mordred..." │
   ├────────────────────────────────────────┤
   │ source_id: 200                         │
   │ target_type: link                      │
   │ target_id: (아서↔모드레드 link ID)     │
   │ evidence_raw: "Arthur...Mordred at     │
   │               Camlann..."              │
   └────────────────────────────────────────┘
```

---

## 3. 데이터 파이프라인

### 3.1 데이터 소스

| 소스 | 설명 | 용도 | 우선순위 |
|------|------|------|----------|
| **Wikidata** | 1억+ 구조화된 엔티티 | QID, 기본 정보 | 1 (기반) |
| **Wikipedia ZIM** | `data/kiwix/wikipedia_en_nopic.zim` | 초안 텍스트, 링크 | 2 (초안) |
| **Gutenberg ZIM** | `data/kiwix/gutenberg_en_all.zim` | 책 언급으로 보강 | 3 (보강) |
| **기타 책/문서** | 추가 소스 | 계속 확장 | 4+ |

### 3.2 파이프라인 흐름

```
┌─────────────────────────────────────────────────────────────┐
│              Phase 1: Wikipedia 초안 (무료)                  │
└─────────────────────────────────────────────────────────────┘

1. Wikidata에서 엔티티 목록
   └─ P31 = battle, war, person, location 등
   └─ QID + 기본 정보 확보
   └─ persons/events/locations 테이블에 저장

2. Wikipedia에서 상세 추출
   └─ ZIM 파일에서 HTML 로드
   └─ 전체 본문 → sources 테이블
   └─ 본문 링크 분석 → mentions 생성
   └─ 링크 간 관계 → links 테이블

┌─────────────────────────────────────────────────────────────┐
│              Phase 2: 책으로 보강 (점진적)                    │
└─────────────────────────────────────────────────────────────┘

3. Gutenberg 책 처리
   └─ 청크별로 sources에 저장
   └─ LLM으로 엔티티 추출 (llama3.1)
   └─ QID 매칭 (기존 엔티티와 연결)
   └─ mentions 생성

4. 추가 소스 (반복)
   └─ 새 책/문서 추가될 때마다
   └─ 같은 방식으로 sources + mentions 추가

┌─────────────────────────────────────────────────────────────┐
│              Phase 3: 정서 (배치, 로컬 LLM)                   │
└─────────────────────────────────────────────────────────────┘

5. 설명 정서
   └─ 엔티티별 mentions 모아서
   └─ llama3.1로 종합 → description
   └─ description_model, description_at 기록

6. 근거 정서
   └─ link별 mentions 모아서
   └─ llama3.1로 종합 → evidence
   └─ evidence_model, evidence_at 기록
```

### 3.3 정서 로직

```python
def get_description(entity):
    """엔티티 설명 가져오기"""
    # 정서된 버전 있으면 반환
    if entity.description:
        return entity.description

    # 없으면 Wikipedia mention에서 가져오기
    wiki_mention = db.query(mentions).join(sources).filter(
        mentions.target_type == entity_type,
        mentions.target_id == entity.id,
        sources.source_type == 'wikipedia'
    ).first()

    return wiki_mention.evidence_raw if wiki_mention else None


def refine_description(entity):
    """여러 출처 합쳐서 설명 정서"""
    # 모든 mentions 가져오기
    all_mentions = db.query(mentions).filter(
        target_type == entity_type,
        target_id == entity.id
    ).all()

    # LLM으로 종합
    prompt = f"Summarize these mentions about {entity.name}:\n"
    for m in all_mentions:
        prompt += f"- {m.evidence_raw}\n"

    description = llm.generate(prompt)

    # 저장
    entity.description = description
    entity.description_model = "llama3.1:8b"
    entity.description_at = now()
```

---

## 4. API 구조

### 4.1 핵심 엔드포인트

```
GET  /api/v1/persons              # 인물 목록
GET  /api/v1/persons/{id}         # 인물 상세 (description 포함)
GET  /api/v1/persons/{id}/links   # 인물의 연결들
GET  /api/v1/persons/{id}/sources # 인물 관련 출처들

GET  /api/v1/locations            # 장소 목록
GET  /api/v1/locations/{id}       # 장소 상세

GET  /api/v1/events               # 이벤트 목록
GET  /api/v1/events/{id}          # 이벤트 상세
GET  /api/v1/events/{id}/links    # 이벤트의 연결들
GET  /api/v1/events/hierarchy     # 이벤트 계층 트리

GET  /api/v1/links/{id}           # 연결 상세 (evidence 포함)
GET  /api/v1/links/{id}/sources   # 연결 관련 출처들

GET  /api/v1/sources              # 출처 목록
GET  /api/v1/sources/{id}         # 출처 상세 (content_raw)

GET  /api/v1/globe                # 글로브 표시용 데이터
GET  /api/v1/search?q=...         # 통합 검색
```

### 4.2 응답 형식

```json
// GET /api/v1/persons/{id}
{
  "id": 12345,
  "name": "Napoleon Bonaparte",
  "wikidata_id": "Q517",
  "description": "Napoleon Bonaparte (1769-1821) was a French military leader...",
  "description_model": "llama3.1:8b",
  "sources": [
    {
      "id": 100,
      "source_type": "wikipedia",
      "title": "Napoleon",
      "evidence_raw": "Napoleon Bonaparte was a French military commander..."
    },
    {
      "id": 201,
      "source_type": "book",
      "title": "War and Peace",
      "evidence_raw": "The great Napoleon led his armies..."
    }
  ]
}

// GET /api/v1/links/{id}
{
  "id": 456,
  "from": { "type": "person", "id": 12345, "name": "Napoleon" },
  "to": { "type": "event", "id": 789, "name": "Battle of Waterloo" },
  "category": "military",
  "evidence": "Napoleon commanded the French forces at Waterloo...",
  "sources": [
    {
      "id": 100,
      "source_type": "wikipedia",
      "evidence_raw": "Napoleon commanded the French forces..."
    }
  ]
}
```

---

## 5. 프론트엔드 UX

### 5.1 글로브 뷰

```
┌─────────────────────────────────────────────────────────────┐
│                         3D Globe                             │
│                                                              │
│            🔴 마커 = 이벤트 발생 위치                         │
│                                                              │
│   줌 레벨에 따른 표시:                                        │
│   - 멀리: 대사건만 (백년전쟁, 세계대전)                       │
│   - 중간: 주요 전투/사건                                      │
│   - 가까이: 모든 세부 사건                                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 사이드바 (출처 표시)

```
┌─────────────────────────────────────────────────────────────┐
│ ◀ Battle of Waterloo (1815)                                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ 📖 Description                                               │
│ The Battle of Waterloo was fought on 18 June 1815...        │
│                                                              │
│ 📚 Sources (3)                                               │
│ ├─ Wikipedia: Battle of Waterloo                            │
│ ├─ Book: "Waterloo" by Bernard Cornwell                     │
│ └─ Book: "The Campaigns of Napoleon"                        │
│                                                              │
│ ─────────────────────────────────────────────               │
│ 👤 Related People                                            │
│                                                              │
│ Napoleon Bonaparte                                           │
│ └─ "Napoleon commanded the French forces..."                │
│    📚 Wikipedia, "Campaigns of Napoleon"                    │
│                                                              │
│ Duke of Wellington                                           │
│ └─ "Wellington led the allied forces..."                    │
│    📚 Wikipedia                                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 출처 상세 보기

```
┌─────────────────────────────────────────────────────────────┐
│ 📚 Source: Wikipedia - Battle of Waterloo                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Type: Wikipedia                                              │
│ URL: https://en.wikipedia.org/wiki/Battle_of_Waterloo       │
│                                                              │
│ ─────────────────────────────────────────────               │
│ 📝 Full Text (excerpt)                                       │
│                                                              │
│ "The Battle of Waterloo was fought on Sunday 18 June        │
│ 1815, near Waterloo in the United Kingdom of the            │
│ Netherlands, now in Belgium. A French army under the        │
│ command of Napoleon was defeated by two of the armies       │
│ of the Seventh Coalition..."                                │
│                                                              │
│ ─────────────────────────────────────────────               │
│ 🔗 Entities mentioned in this source (15)                   │
│ ├─ Napoleon Bonaparte (person)                              │
│ ├─ Duke of Wellington (person)                              │
│ ├─ Waterloo, Belgium (location)                             │
│ └─ ... more                                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. 이벤트 계층 구조

### 6.1 계층 레벨

| Level | 이름 | 설명 | 예시 |
|-------|------|------|------|
| 0 | Era | 시대 | 고대, 중세, 근대 |
| 1 | Mega-Event | 대사건 | 로마 제국의 흥망 |
| 2 | Aggregate | 집합 사건 | 백년전쟁, 십자군 전쟁 |
| 3 | Major | 주요 사건 | 아쟁쿠르 전투 |
| 4 | Minor | 세부 사건 | 조약, 소규모 교전 |

### 6.2 계층 구조 예시

```
Level 1: Napoleonic Wars (1803-1815)
├── Level 2: War of the Third Coalition (1803-1806)
│   ├── Level 3: Battle of Austerlitz (1805)
│   └── Level 3: Battle of Trafalgar (1805)
├── Level 2: French Invasion of Russia (1812)
│   ├── Level 3: Battle of Borodino (1812)
│   └── Level 3: Retreat from Moscow (1812)
└── Level 2: War of the Seventh Coalition (1815)
    └── Level 3: Battle of Waterloo (1815)
```

---

## 7. 데이터 품질 기준

### 7.1 필수 조건

| 항목 | 기준 |
|------|------|
| *.wikidata_id | NOT NULL (모든 엔티티) |
| sources.content_raw | NOT NULL |
| mentions.evidence_raw | NOT NULL, 최소 50자 |

### 7.2 품질 지표

| 지표 | 목표 |
|------|------|
| 모든 엔티티에 최소 1개 mention | 100% |
| 모든 link에 최소 1개 mention | 100% |
| QID 있는 비율 | 100% |
| 고아 엔티티 (mention 없는) | 0개 |

### 7.3 검증 쿼리

```sql
-- mention 없는 person (있으면 안 됨!)
SELECT p.id, p.name FROM persons p
WHERE NOT EXISTS (
    SELECT 1 FROM mentions m
    WHERE m.target_type = 'person' AND m.target_id = p.id
);

-- mention 없는 link (있으면 안 됨!)
SELECT l.id FROM links l
WHERE NOT EXISTS (
    SELECT 1 FROM mentions m
    WHERE m.target_type = 'link' AND m.target_id = l.id
);

-- 출처 없는 source (content_raw 필수)
SELECT COUNT(*) FROM sources WHERE content_raw IS NULL OR content_raw = '';
```

---

## 8. 마이그레이션 계획

### 8.1 기존 테이블 처리

#### 유지 (스키마 정리)
- `persons` - QID 있는 것만 유지
- `locations` - QID 있는 것만 유지
- `events` - QID 있는 것만 유지

#### 신규 생성
- `links` - 새 스키마
- `sources` - 새 테이블
- `mentions` - 새 테이블

#### 삭제 대상
| 테이블 | 이유 |
|--------|------|
| `event_persons` | links + mentions로 대체 |
| `event_locations` | links + mentions로 대체 |
| `event_relationships` | links + mentions로 대체 |
| `connections` | links + mentions로 대체 |
| `entity_sources` | mentions로 대체 |
| `text_mentions` | mentions로 통합 |
| `*_v2` 모든 테이블 | 폐기 |
| `*_backup_*` 모든 테이블 | 정리 |

### 8.2 마이그레이션 순서

```
1. 새 테이블 생성 (links, sources, mentions)
2. Wikipedia 파이프라인으로 데이터 채우기
3. 검증 (모든 엔티티에 mention 있는지)
4. 백엔드 API 수정
5. 프론트엔드 수정 (출처 표시)
6. 기존 쓰레기 테이블 삭제
```

---

## 9. 구현 체크리스트

### Phase 1: 스키마 구현
- [ ] links 테이블 생성
- [ ] sources 테이블 생성
- [ ] mentions 테이블 생성
- [ ] 기존 persons/locations/events 스키마 정리

### Phase 2: 데이터 파이프라인
- [ ] Wikipedia → sources 저장 스크립트
- [ ] Wikipedia → mentions 생성 스크립트
- [ ] Wikipedia → links 생성 스크립트
- [ ] 주요 이벤트 1,000개 처리

### Phase 3: API 수정
- [ ] /sources 엔드포인트
- [ ] /*/sources 엔드포인트 (엔티티별 출처)
- [ ] 기존 엔드포인트에 sources 연동

### Phase 4: 프론트엔드
- [ ] 사이드바에 출처 목록 표시
- [ ] 출처 상세 보기 모달
- [ ] 연결에 근거 표시

### Phase 5: 책 보강
- [ ] Gutenberg 책 파이프라인
- [ ] sources + mentions 추가
- [ ] 정서 배치 스크립트

### Phase 6: 정리
- [ ] 쓰레기 테이블 삭제
- [ ] 문서 정리
- [ ] 배포

---

## 10. 예상 결과

| 항목 | 현재 | 목표 |
|------|------|------|
| persons | 275,343 (67% QID 없음) | ~90,000 (100% QID) |
| locations | 40,613 (96% QID 없음) | ~1,600 (100% QID) |
| events | 56,567 (75% QID 없음) | ~14,000 (100% QID) |
| links | 1,689,024 (출처 0%) | ~50,000 (출처 100%) |
| sources | 0 | ~100,000+ |
| mentions | 0 | ~500,000+ |
| tags | 0 | ~10,000+ |
| entity_tags | 0 | ~200,000+ |
| 테이블 수 | 50+ | 8 |

**핵심**: 양은 줄지만 **품질 있고 출처 있는** 데이터

---

## 부록 A: 파일 구조

```
backend/
├── app/
│   ├── models/
│   │   ├── person.py
│   │   ├── location.py
│   │   ├── event.py
│   │   ├── link.py        ← NEW
│   │   ├── source.py      ← NEW
│   │   └── mention.py     ← NEW
│   ├── schemas/
│   │   ├── link.py        ← NEW
│   │   ├── source.py      ← NEW
│   │   └── mention.py     ← NEW
│   └── api/v1/
│       ├── links.py       ← NEW
│       └── sources.py     ← NEW

poc/scripts/
├── wiki_to_sources.py      # Wikipedia → sources
├── wiki_to_mentions.py     # Wikipedia → mentions
├── wiki_to_links.py        # Wikipedia → links
├── book_to_sources.py      # 책 → sources
├── refine_descriptions.py  # 정서 배치
└── validate_data.py        # 품질 검증

docs/planning/
└── CHALDEAS_UNIFIED_SPEC.md  ← 이 문서 (유일한 기획서)
```

---

## 부록 B: 용어 정의

| 용어 | 정의 |
|------|------|
| **QID** | Wikidata 엔티티 ID (예: Q517 = 나폴레옹) |
| **Source** | 출처 원문 (Wikipedia 문서, 책 청크 등) |
| **Mention** | 출처에서 특정 대상을 언급하는 부분 |
| **Link** | 두 엔티티 간의 연결 |
| **Evidence** | 연결/설명의 근거가 되는 텍스트 |

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2026-02-01 | 1.0 | 초안 작성 |
| 2026-02-01 | 2.0 | 원본/정서 분리 패턴 추가 |
| 2026-02-01 | 3.0 | sources + mentions 구조로 전면 개편 |
| 2026-02-01 | 4.0 | tags + entity_tags 추가, links에 date_start/end 추가 |
