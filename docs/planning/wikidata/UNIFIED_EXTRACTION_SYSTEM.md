# 통합 추출 시스템 설계

> **작성일**: 2026-02-05
> **목적**: Wikidata + Wikipedia 통합 추출로 완전한 역사 데이터 구축

---

## 1. 개요

### 1.1 현재 문제

기존 추출 시스템:
- Wikidata에서 **일부 속성만** 추출 (P19, P20, P276 등 10개 미만)
- Wikipedia 본문 **미사용**
- 하이퍼링크 관계 **누락**
- source content_raw가 "Description: ..." 한 줄뿐

### 1.2 목표

- Wikidata의 **모든 유용한 속성** 추출
- Wikipedia **전체 본문** 연결
- 본문 내 **하이퍼링크 → 관계** 변환
- 모든 데이터에 **출처 추적** 가능

---

## 2. 데이터 소스

| 소스 | 파일 | 크기 | 내용 |
|------|------|------|------|
| Wikidata | `D:/project/wikidata/latest-all.json` | ~700GB | 구조화된 엔티티/관계 |
| Wikipedia | `data/kiwix/wikipedia_en_nopic.zim` | 48GB | 영문 본문 + 링크 |
| Wikisource | `data/kiwix/wikisource_en_nopic.zim` | 11GB | 1차 사료 원문 |

---

## 3. 추출 대상

### 3.1 Wikidata 속성 (Properties)

#### 인물 관계
| Property | 설명 | 용도 |
|----------|------|------|
| P22 | father | 가족 관계 |
| P25 | mother | 가족 관계 |
| P26 | spouse | 가족 관계 |
| P40 | child | 가족 관계 |
| P3373 | sibling | 가족 관계 |
| P451 | partner | 관계 |
| P1038 | relative | 친척 |

#### 소속/직위
| Property | 설명 | 용도 |
|----------|------|------|
| P106 | occupation | 직업 |
| P39 | position held | 직위 |
| P108 | employer | 고용주 |
| P463 | member of | 소속 단체 |
| P102 | political party | 정당 |
| P140 | religion | 종교 |
| P69 | educated at | 학력 |
| P512 | academic degree | 학위 |

#### 이벤트 참여
| Property | 설명 | 용도 |
|----------|------|------|
| P607 | conflict | 참전한 전쟁 |
| P1344 | participant in | 참여한 이벤트 |
| P793 | significant event | 주요 사건 |
| P1424 | topic's main template | 관련 주제 |

#### 시공간
| Property | 설명 | 용도 |
|----------|------|------|
| P625 | coordinate | 좌표 |
| P17 | country | 국가 |
| P131 | located in | 행정구역 |
| P276 | location | 장소 |
| P19 | birthplace | 출생지 |
| P20 | deathplace | 사망지 |
| P119 | burial place | 매장지 |
| P551 | residence | 거주지 |
| P937 | work location | 활동지 |

#### 시간
| Property | 설명 | 용도 |
|----------|------|------|
| P569 | birth date | 출생일 |
| P570 | death date | 사망일 |
| P580 | start time | 시작일 |
| P582 | end time | 종료일 |
| P585 | point in time | 시점 |
| P571 | inception | 설립일 |
| P576 | dissolved | 해산일 |

#### 계층/연결
| Property | 설명 | 용도 |
|----------|------|------|
| P361 | part of | 상위 개념 |
| P527 | has part | 하위 개념 |
| P155 | follows | 선행 |
| P156 | followed by | 후행 |
| P279 | subclass of | 하위 분류 |
| P31 | instance of | 인스턴스 |

#### 외부 참조
| Property | 설명 | 용도 |
|----------|------|------|
| P18 | image | 이미지 |
| P373 | Commons category | 위키미디어 |
| P214 | VIAF ID | 도서관 ID |
| P227 | GND ID | 독일 국립도서관 |
| P244 | LCNAF ID | 미국 의회도서관 |

### 3.2 Wikipedia 추출

#### 본문 텍스트
```
소스 HTML:
<p>Thomas Edison was an American <a href="/wiki/Inventor">inventor</a>
who competed with <a href="/wiki/Nikola_Tesla">Nikola Tesla</a>...</p>

추출 결과:
{
  "text": "Thomas Edison was an American inventor who competed with Nikola Tesla...",
  "links": [
    {"text": "inventor", "target": "Inventor", "position": [28, 36]},
    {"text": "Nikola Tesla", "target": "Nikola_Tesla", "position": [57, 69]}
  ]
}
```

#### 하이퍼링크 → 관계
```
Wikipedia 문서: Thomas Edison
링크 타겟: Nikola Tesla
문맥: "competed with Nikola Tesla in the War of Currents"

→ links 테이블:
  source_entity: Edison (Q8743)
  target_entity: Tesla (Q9036)
  link_type: "wikipedia_mention"
  context: "competed with Nikola Tesla in the War of Currents"
```

---

## 4. 스키마 확장

### 4.1 새 테이블: entity_properties

```sql
-- Wikidata 속성 저장 (정규화 안 함, 유연성 확보)
CREATE TABLE entity_properties (
    id SERIAL PRIMARY KEY,

    -- 엔티티
    entity_type VARCHAR(20) NOT NULL,  -- person, location, event, etc.
    entity_id INTEGER NOT NULL,

    -- 속성
    property VARCHAR(10) NOT NULL,     -- P22, P26, P106, etc.
    property_name VARCHAR(100),        -- father, spouse, occupation

    -- 값
    value_type VARCHAR(20) NOT NULL,   -- qid, string, time, quantity, coordinate
    value_qid VARCHAR(20),             -- Q1234 (if type is qid)
    value_string TEXT,                 -- 문자열 값
    value_time TIMESTAMP,              -- 시간 값
    value_year INTEGER,                -- 연도 (BCE 음수)
    value_quantity DECIMAL,            -- 수량
    value_lat DECIMAL(10,7),           -- 좌표
    value_lon DECIMAL(10,7),

    -- Qualifier (한정자)
    qualifiers JSONB,                  -- {"P580": "1889", "P582": "1891"}

    -- 메타
    wikidata_id VARCHAR(20),           -- 원본 엔티티 QID
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ep_entity ON entity_properties(entity_type, entity_id);
CREATE INDEX idx_ep_property ON entity_properties(property);
CREATE INDEX idx_ep_value_qid ON entity_properties(value_qid);
```

### 4.2 sources 구조 (엔티티당 2개)

**하나의 엔티티에 sources 2개:**

```
Entity: Q8409 (Alexander the Great)

┌─────────────────────────────────────────────────────────┐
│ Source 1: Wikidata (한줄 요약)                          │
├─────────────────────────────────────────────────────────┤
│ source_type: "wikidata"                                 │
│ title: "Alexander the Great - Wikidata"                 │
│ content_raw: "King of Macedonia (356–323 BC)"           │
│ url: "https://www.wikidata.org/wiki/Q8409"              │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Source 2: Wikipedia (전체 본문)                         │
├─────────────────────────────────────────────────────────┤
│ source_type: "wikipedia"                                │
│ title: "Alexander the Great - Wikipedia"                │
│ content_raw: "Alexander III of Macedon, commonly known  │
│              as Alexander the Great, was a king of the  │
│              ancient Greek kingdom... [15,000 words]"   │
│ content_html: "<p>Alexander III of Macedon...</p>"      │
│ url: "https://en.wikipedia.org/wiki/Alexander_the_Great"│
│ word_count: 15420                                       │
│ link_count: 847                                         │
└─────────────────────────────────────────────────────────┘
```

**sources 테이블 확장:**

```sql
ALTER TABLE sources ADD COLUMN content_html TEXT;  -- 원본 HTML (Wikipedia)
ALTER TABLE sources ADD COLUMN word_count INTEGER;
ALTER TABLE sources ADD COLUMN link_count INTEGER;
```

### 4.3 mentions 테이블 확장

```sql
-- 하이퍼링크 정보 추가
ALTER TABLE mentions ADD COLUMN link_text VARCHAR(500);     -- 링크 텍스트
ALTER TABLE mentions ADD COLUMN position_start INTEGER;     -- 문자 위치
ALTER TABLE mentions ADD COLUMN position_end INTEGER;
ALTER TABLE mentions ADD COLUMN paragraph_index INTEGER;    -- 몇 번째 문단
```

---

## 5. 추출 파이프라인

### 5.1 Phase 1: Wikidata 전체 속성 추출

```
입력: D:/project/wikidata/latest-all.json (~700GB)

처리:
1. JSON 라인 단위 파싱
2. 엔티티 타입 분류 (person/location/territory/group/event)
3. 모든 claims(속성) 추출
4. entity_properties 형태로 저장

출력: wikidata_full.jsonl
- 엔티티 기본 정보
- 모든 속성 (property + value + qualifiers)
- sitelinks (Wikipedia 제목)
```

### 5.2 Phase 2: Wikipedia ↔ Wikidata 매핑

```
입력:
- wikidata_full.jsonl (sitelinks 포함)
- wikipedia_en_nopic.zim

처리:
1. Wikidata sitelinks.enwiki → Wikipedia 제목 추출
2. Wikipedia 제목 → ZIM entry 매핑
3. QID ↔ Wikipedia 문서 매핑 테이블 생성

출력: qid_wiki_map.json
{
  "Q8743": "Thomas_Edison",
  "Q9036": "Nikola_Tesla",
  ...
}
```

### 5.3 Phase 3: Wikipedia 본문 + 링크 추출

```
입력:
- wikipedia_en_nopic.zim
- qid_wiki_map.json

처리:
1. ZIM에서 HTML 추출
2. HTML → 텍스트 변환 (본문)
3. <a href="/wiki/..."> 파싱 (링크)
4. 링크 타겟 → QID 역매핑
5. sources + mentions 생성

출력: wikipedia_extracted.jsonl
{
  "type": "source",
  "data": {
    "qid": "Q8743",
    "source_type": "wikipedia",
    "title": "Thomas Edison - Wikipedia",
    "content_raw": "Thomas Alva Edison was an American inventor...",
    "content_html": "<p>Thomas Alva Edison was...",
    "word_count": 15420,
    "link_count": 847
  }
}
{
  "type": "mention",
  "data": {
    "source_qid": "Q8743",
    "target_qid": "Q9036",
    "target_type": "person",
    "link_text": "Nikola Tesla",
    "evidence_raw": "competed with Nikola Tesla in the War of Currents",
    "position_start": 1547,
    "position_end": 1559,
    "paragraph_index": 3
  }
}
```

### 5.4 Phase 4: 임포트

```
순서:
1. locations (좌표 있는 점)
2. territories (국가, 영역)
3. persons
4. groups
5. events
6. entity_properties (모든 속성)
7. sources (Wikidata + Wikipedia)
8. mentions (관계 + 하이퍼링크)
9. links (entity_properties에서 QID 관계 → links로 변환)
```

---

## 6. 예상 데이터 규모

| 항목 | 예상 수량 | 비고 |
|------|----------|------|
| Wikidata 엔티티 | ~100M | 전체 |
| 우리가 쓸 엔티티 | ~10M | 필터링 후 |
| entity_properties | ~500M | 엔티티당 평균 50개 |
| Wikipedia 문서 | ~6.7M | 영문 |
| Wikipedia 링크 | ~200M | 문서당 평균 30개 |
| **sources (Wikidata)** | ~10M | 엔티티당 1개 (한줄 요약) |
| **sources (Wikipedia)** | ~6.7M | Wikipedia 있는 엔티티만 (전체 본문) |
| **sources 총합** | ~17M | |
| mentions (Wikidata) | ~10M | 엔티티-source 연결 |
| mentions (Wikipedia) | ~200M | 하이퍼링크 (문맥 포함) |
| **mentions 총합** | ~210M | |

### 저장 공간
- PostgreSQL: ~100GB (인덱스 포함)
- JSONL 중간 파일: ~50GB

---

## 7. 구현 순서

### CP-1: 스키마 확장
- [ ] entity_properties 테이블 생성
- [ ] sources 컬럼 추가
- [ ] mentions 컬럼 추가

### CP-2: Wikidata 전체 추출기
- [ ] 모든 속성 추출 로직
- [ ] 병렬 처리 (압축 해제 후)
- [ ] 진행률 저장/복구

### CP-3: Wikipedia 매핑
- [ ] QID ↔ Wikipedia 제목 매핑
- [ ] ZIM 접근 라이브러리 설정

### CP-4: Wikipedia 추출기
- [ ] HTML → 텍스트 변환
- [ ] 하이퍼링크 파싱
- [ ] 문맥 추출 (링크 주변 텍스트)

### CP-5: 임포트
- [ ] 의존성 순서 임포트
- [ ] 중복 처리
- [ ] 검증

### CP-6: 검증
- [ ] mention coverage 100%
- [ ] link 양방향 확인
- [ ] 샘플 품질 검사

---

## 8. 파일 구조

```
poc/scripts/unified/
├── extract_wikidata_full.py    # Wikidata 전체 속성 추출
├── build_wiki_mapping.py       # QID ↔ Wikipedia 매핑
├── extract_wikipedia.py        # Wikipedia 본문 + 링크 추출
├── import_unified.py           # 통합 임포트
├── verify.py                   # 검증
└── config.py                   # 설정 (경로, 속성 목록)

poc/data/unified/
├── wikidata_full.jsonl         # Wikidata 추출 결과
├── qid_wiki_map.json           # QID ↔ Wikipedia 매핑
├── wikipedia_extracted.jsonl   # Wikipedia 추출 결과
└── checkpoints/                # 진행률 저장
```

---

## 9. 의존성

```
pip install libzim        # ZIM 파일 읽기
pip install beautifulsoup4  # HTML 파싱
pip install lxml          # 빠른 HTML 파싱
pip install orjson        # 빠른 JSON 파싱
```

---

## 10. 일정

| Phase | 작업 | 예상 시간 |
|-------|------|----------|
| 압축 해제 | Wikidata bz2 → json | ~10시간 (진행 중) |
| CP-1 | 스키마 확장 | 30분 |
| CP-2 | Wikidata 추출 | 2-3시간 (병렬) |
| CP-3 | Wikipedia 매핑 | 1시간 |
| CP-4 | Wikipedia 추출 | 3-4시간 |
| CP-5 | 임포트 | 2-3시간 |
| CP-6 | 검증 | 1시간 |

**총 예상**: 압축 해제 후 ~12시간

---
