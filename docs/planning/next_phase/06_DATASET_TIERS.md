# 06. 데이터셋 티어 & TRISMEGISTUS 확장

> 12.8M 인물 중 어디까지가 의미 있는가? 학술 연구 기반으로 최소 기동 데이터셋을 정의하고,
> TRISMEGISTUS를 FGO 넘어 모든 역사 미디어로 확장하는 아키텍처를 설계한다.

---

## 1. 학술 연구: "역사적으로 중요한 인물"은 몇 명인가?

### MIT Pantheon Project (2014~현재)

MIT Media Lab의 Pantheon은 **"세계적으로 기억되는 인물"**을 정량화한 연구.

| 기준 | 인원 | 설명 |
|------|------|------|
| L ≥ 25 (25개+ 위키 언어판) | **11,341명** | "Global Historical Significance" |
| L ≥ 15 (15개+ 위키 언어판) | **~85,000명** | "Broadly Notable" |
| HPI (Historical Popularity Index) 상위 | ~4,000명 | 다양한 지표 종합 |

- **논문**: Yu et al., "Pantheon 1.0" (Nature Scientific Data, 2016)
- **핵심 발견**: 25개 이상의 위키 언어판에 등장하는 인물은 **문화/언어 경계를 초월한 보편적 인지도**를 가진다.

### Cross-Verified Database (CVDB)

프랑스 INED 연구소의 역사 인물 크로스레퍼런스 DB:

| 항목 | 규모 |
|------|------|
| 전체 인물 | **2,290,000명** |
| 위키데이터 연결 | ~1,900,000명 |
| 출생-사망 데이터 완비 | ~1,500,000명 |

- BCE 3500 ~ 현재까지 커버
- 다중 출처 교차 검증 (위키데이터, 위키피디아, GND, VIAF 등)

### Charles Murray, "Human Accomplishment" (2003)

서양/동양 문명의 "중대한 업적을 남긴 인물" 4,002명:

| 분야 | 인원 |
|------|------|
| 과학 | ~1,500 |
| 예술/문학 | ~1,200 |
| 음악 | ~500 |
| 철학 | ~400 |
| 기타 | ~400 |

### EventKG (2019)

이벤트 중심 지식 그래프:

| 항목 | 규모 |
|------|------|
| 이벤트 | **690,000개** |
| 관계 | 979,000개 |
| 출처 | Wikipedia + Wikidata + YAGO |

### Wikipedia Vital Articles

위키피디아 자체의 "필수 문서" 계층:

| Level | 문서 수 | 인물 비중 |
|-------|---------|----------|
| Level 1 | 10 | - |
| Level 2 | 100 | ~20명 |
| Level 3 | 1,000 | ~200명 |
| Level 4 | 10,000 | ~2,000명 |
| Level 5 | 50,000 | ~10,000명 |

---

## 2. CHALDEAS 데이터 현황 vs 학술 기준

### 현재 데이터 감사

| 항목 | 현재 | "의미 있는" 비율 |
|------|------|-----------------|
| `persons` | **12,987,361** | 이벤트 연결: 90,710 (0.7%) |
| `events` | **28,331** | importance 전부 3 |
| `locations` | **2,387,834** | 이벤트 연결: 4,474 |
| `entity_properties` | **112,800,000+** | P106: 7M, P19: 2.1M, P569: 4.2M |
| `sources` | **400,516** | Wikipedia 2.5M |
| `event_persons` | **90,710 고유 인물** | 이것이 "의미 있는" 인물의 기준선 |

### 핵심 문제

```
12,987,361 persons 중 12,896,651명 (99.3%)은 어떤 이벤트에도 연결되지 않음.
→ 이들은 Wikidata에서 벌크 임포트된 것으로 추정
→ 대부분 현대인 (정치인, 스포츠 선수, 배우 등)
→ 역사 탐색 UX에서 노이즈
```

---

## 3. 인물 티어 시스템

QRank (Wikimedia 페이지뷰 기반 인기도 점수)와 entity_properties 데이터를 조합하여 분류.

### 티어 정의

| 티어 | 인원 (목표) | 기준 | 예시 |
|------|-----------|------|------|
| **S** | ~500 | QRank 상위 0.01%, Wikipedia Vital L3 수준 | 알렉산더, 카이사르, 나폴레옹, 공자, 셰익스피어 |
| **A** | ~15,000 | QRank 상위 0.1%, Pantheon L≥25 수준 | 레오니다스, 잔 다르크, 이븐 할둔, 무라사키 시키부 |
| **B** | ~85,000 | QRank 상위 1%, Pantheon L≥15 수준 | 사건에 연결된 대부분의 역사 인물 |
| **C** | ~500,000 | QRank 상위 5%, 기본 정보 있음 | 기본 Wikidata 정보 있는 인물 |
| **Archive** | 12M+ | 나머지 전체 | 쿼리 가능하지만 기본 UI에 미표시 |

### 티어별 데이터 풍부도

| 항목 | S | A | B | C | Archive |
|------|---|---|---|---|---------|
| name, birth/death year | O | O | O | O | O |
| role (occupation) | O | O | O | △ | X |
| biography (첫 문단) | O | O | △ | X | X |
| birthplace/deathplace | O | O | O | △ | X |
| event 연결 | O | O | O | △ | X |
| importance 점수 | 5 | 4-5 | 3-4 | 2-3 | 1 |
| 원전/소스 연결 | O | △ | X | X | X |
| 서번트 매핑 | O (해당 시) | O (해당 시) | X | X | X |

### 구현: QRank 기반 티어 분류

```sql
-- qrank 테이블이 임포트된 후 실행
-- persons에 tier 컬럼 추가
ALTER TABLE persons ADD COLUMN IF NOT EXISTS tier VARCHAR(10) DEFAULT 'archive';
CREATE INDEX IF NOT EXISTS idx_persons_tier ON persons(tier);

-- QRank 기반 티어 할당
WITH ranked AS (
    SELECT p.id, q.score,
           PERCENT_RANK() OVER (ORDER BY q.score DESC) as pct
    FROM persons p
    JOIN qrank q ON q.wikidata_id = p.wikidata_id
    WHERE q.score > 0
)
UPDATE persons p SET tier = CASE
    WHEN r.pct <= 0.0001 THEN 'S'    -- 상위 0.01%
    WHEN r.pct <= 0.001  THEN 'A'    -- 상위 0.1%
    WHEN r.pct <= 0.01   THEN 'B'    -- 상위 1%
    WHEN r.pct <= 0.05   THEN 'C'    -- 상위 5%
    ELSE 'archive'
END
FROM ranked r WHERE r.id = p.id;

-- 이벤트 연결된 인물은 최소 C 이상 보장
UPDATE persons SET tier = 'C'
WHERE tier = 'archive'
  AND id IN (SELECT DISTINCT person_id FROM event_persons);
```

### API 적용

```python
# Feed API에서 기본적으로 tier IN ('S', 'A', 'B')만 표시
# 검색에서는 모든 티어 접근 가능
# 상세 뷰에서는 Archive도 접근 가능

@router.get("/feed")
async def get_feed(
    tier_min: str = "B",  # 기본: B 이상만
    ...
):
    tier_order = {'S': 1, 'A': 2, 'B': 3, 'C': 4, 'archive': 5}
    ...
```

---

## 4. 최소 기동 데이터셋 (Minimum Viable Dataset)

### 학술 근거 기반 목표

| 항목 | 최소 목표 | 근거 |
|------|----------|------|
| **인물** | **15,000명** (Tier S+A) | MIT Pantheon: 25+ 언어판 = 세계적 인지도 |
| **이벤트** | **5,000개** | Tier S+A 인물의 주요 사건 커버 |
| **장소** | **3,000곳** | 이벤트 발생 장소 + 주요 도시 |
| **원전/소스** | **500개** | 서번트 연결 인물의 주요 출처 |

### "시작선" vs "완성선"

```
시작선 (MVP):     15K persons + 5K events + 3K locations
                   → "이거 꽤 볼 만하네"
                   → Pantheon에 있는 모든 인물 커버

중간선 (Phase 2):  85K persons + 15K events + 10K locations
                   → "웬만한 건 다 있네"
                   → 주요 문화권/시대 빈틈 없음

완성선 (Phase 3):  500K persons + 50K events + 50K locations
                   → "이거 백과사전급이다"
                   → 전문 연구에도 활용 가능

보관 (Archive):    12M+ persons → 검색/API로만 접근
```

### 현재 위치와 갭

```
                현재              시작선             갭
persons:     90,710 (이벤트)    15,000 (S+A)      이미 초과! → 정리가 필요
events:      28,331             5,000              이미 초과! → importance 분류 필요
locations:   4,474 (이벤트)     3,000              이미 초과! → 분류 필요
importance:  전부 3             1-5 분포           QRank + 재계산 필요
biography:   0건               15,000             Wikipedia 추출 필요
role:        2,305건            15,000             entity_properties 반영 (진행중)
```

**결론**: 데이터 양은 이미 충분. **문제는 정리/분류/풍부화**.

---

## 5. TRISMEGISTUS 확장: FGO 너머로

### 현재: FGO Only

```
TRISMEGISTUS → FGO 서번트 → 역사 인물
```

### 목표: 모든 역사 미디어 커버

```
TRISMEGISTUS → 역사를 다루는 모든 미디어
               ├─ FGO Layer (게임)
               │    └─ 서번트, 특이점, 이종대전
               ├─ Literary Layer (문학)
               │    └─ 소설, 만화, 라이트노벨
               └─ Media Layer (기타)
                    └─ 영화, 드라마, 다큐, 게임
```

### 왜 확장하는가?

1. **FGO만으로는 진입점이 제한됨**: FGO 서번트는 ~300개, 대부분 서양/일본 편향
2. **역사를 다루는 미디어는 무수히 많음**: 킹덤(삼국지 아닌 전국시대), 빈란드 사가(바이킹), 히스토리에(알렉산더)...
3. **"이 만화/영화에 나오는 그 인물/사건"은 강력한 진입점**
4. **TRISMEGISTUS의 원래 의미**: "3배로 위대한 자" — 여러 세계관을 중재하는 오케스트레이터

### 예시: 다양한 미디어 진입점

| 미디어 | 작품 | 역사 연결 |
|--------|------|----------|
| 만화 | 킹덤 (Kingdom) | 진시황, 전국시대 (BCE 259-210) |
| 만화 | 빈란드 사가 (Vinland Saga) | 크누트, 토르핀, 바이킹 시대 (CE 1000경) |
| 만화 | 히스토리에 (Histori-e) | 에우메네스, 알렉산더, BCE 350 |
| 만화 | 체사레 (Cesare) | 체사레 보르자, 르네상스, 1490년대 |
| 영화 | 글래디에이터 (Gladiator) | 마르쿠스 아우렐리우스, 콤모두스 |
| 영화 | 트로이 (Troy) | 트로이 전쟁, BCE 1200경 |
| 드라마 | 三国演義 (삼국지) | 삼국시대, CE 220-280 |
| 게임 | Civilization | 모든 문명/지도자 |
| 게임 | Assassin's Creed | 각 시대별 역사적 배경 |
| 게임 | Total War | 시대별 전쟁/캠페인 |
| 소설 | 은하영웅전설 | 나폴레옹 전쟁 모티프 |
| 라노벨 | Fate/strange Fake | TYPE-MOON 세계관 |
| FGO | 서번트 전체 | 세계사 전반 |

---

## 6. TRISMEGISTUS 아키텍처

### 단기: 같은 DB, 별도 스키마

```sql
CREATE SCHEMA trismegistus;

-- 세계관 (universes)
CREATE TABLE trismegistus.universes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,    -- 'historical', 'fgo', 'kingdom', 'vinland'
    name VARCHAR(200) NOT NULL,
    name_ko VARCHAR(200),
    media_type VARCHAR(30),              -- 'game', 'manga', 'film', 'novel', 'tv'
    franchise VARCHAR(100),              -- 'Fate', 'Kingdom', NULL (독립 작품)
    is_canonical BOOLEAN DEFAULT FALSE,  -- true = historical
    color VARCHAR(7),
    icon_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 초기 데이터
INSERT INTO trismegistus.universes (code, name, name_ko, media_type, franchise, is_canonical) VALUES
('historical', 'Historical Canon', '역사 정사', NULL, NULL, TRUE),
('fgo', 'Fate/Grand Order', '페이트/그랜드 오더', 'game', 'Fate', FALSE),
('kingdom', 'Kingdom', '킹덤', 'manga', NULL, FALSE),
('vinland', 'Vinland Saga', '빈란드 사가', 'manga', NULL, FALSE),
('historie', 'Historie', '히스토리에', 'manga', NULL, FALSE);

-- 캐릭터 ↔ 역사 인물 매핑
CREATE TABLE trismegistus.character_mappings (
    id SERIAL PRIMARY KEY,
    universe_id INTEGER REFERENCES trismegistus.universes(id),
    character_name VARCHAR(200) NOT NULL,
    character_name_ko VARCHAR(200),
    person_id INTEGER REFERENCES public.persons(id),    -- 역사 인물
    mapping_type VARCHAR(30) NOT NULL,   -- 'direct', 'inspired', 'composite', 'alternate'
    accuracy_note TEXT,                   -- "게임에서는 여성으로 묘사"
    role_in_work VARCHAR(200),            -- "주인공", "적대자", "조력자"
    created_at TIMESTAMP DEFAULT NOW()
);

-- FGO 전용 확장 (기존 servant_profiles를 여기로)
CREATE TABLE trismegistus.servant_profiles (
    id SERIAL PRIMARY KEY,
    mapping_id INTEGER REFERENCES trismegistus.character_mappings(id),
    servant_class VARCHAR(50),
    rarity INTEGER,
    noble_phantasm_name VARCHAR(200),
    origin_type VARCHAR(50),             -- historical, legendary, divine, fictional
    atlas_id INTEGER,
    historical_fact TEXT,
    fate_interpretation TEXT,
    portrait_url TEXT
);

-- 원전/소스 매칭 (어떤 세계관이든)
CREATE TABLE trismegistus.source_references (
    id SERIAL PRIMARY KEY,
    universe_id INTEGER REFERENCES trismegistus.universes(id),
    character_mapping_id INTEGER REFERENCES trismegistus.character_mappings(id),
    source_id INTEGER REFERENCES public.sources(id),     -- 기존 sources 테이블
    source_type VARCHAR(30),             -- 'wikipedia', 'gutenberg', 'academic'
    excerpt TEXT,
    excerpt_translation TEXT,
    relevance VARCHAR(30) DEFAULT 'primary'
);
```

### 장기: 독립 서비스 분리

```
현재 (Phase 1):
┌──────────────────────────────────────┐
│          PostgreSQL                   │
│  ┌─── public ────┐ ┌─ trismegistus ┐│
│  │ persons       │ │ universes     ││
│  │ events        │ │ char_mappings ││
│  │ locations     │ │ servant_prof  ││
│  │ sources       │←┤ source_refs   ││
│  └───────────────┘ └───────────────┘│
└──────────────────────────────────────┘

미래 (Phase 3+):
┌─── CHALDEAS Core ──┐  ┌── TRISMEGISTUS ──┐
│ persons, events,    │  │ universes,       │
│ locations, sources  │←→│ char_mappings,   │
│ (FastAPI :8100)     │  │ servant_profiles │
└─────────────────────┘  │ (FastAPI :8200)  │
                          └──────────────────┘
```

**분리 기준**: TRISMEGISTUS 데이터가 1GB 이상 또는 별도 팀이 관리할 때.

### 기존 FGO 데이터 흡수

프로젝트에 이미 있는 FGO 관련 파일들:

| 파일 | 내용 | 흡수 방법 |
|------|------|----------|
| `data/raw/atlas_academy/fgo_historical_figures.json` | 75 서번트 역사 매핑 | → `character_mappings` |
| `data/raw/atlas_academy/servant_db_mapping.json` | 41 매핑 완료 | → `character_mappings` |
| `backend/app/data/showcases/servants.json` | 47KB 큐레이션 | → `servant_profiles` |
| `backend/app/data/showcases/singularities.json` | 9 특이점 | → `universes` 확장 |
| `backend/app/data/showcases/lostbelts.json` | 8 이종대전 | → `universes` 확장 |
| `tools/book_extractor/servant_book_matches.json` | 314 서번트, 119 매칭 | → `source_references` |
| `tools/book_extractor/servant_keywords_full.py` | ~300 키워드 | 검색용 |
| `backend/app/models/v2/fgo.py` | ORM 모델 | → `trismegistus` 스키마로 이전 |

### API 설계

```
# TRISMEGISTUS API (trismegistus router)
GET /api/v1/trismegistus/universes                       # 세계관 목록
GET /api/v1/trismegistus/universes/{code}                # 세계관 상세

GET /api/v1/trismegistus/characters?universe=fgo         # 캐릭터 목록
GET /api/v1/trismegistus/characters/{id}                 # 캐릭터 상세
GET /api/v1/trismegistus/characters/{id}/history         # 실제 역사 연결

GET /api/v1/trismegistus/persons/{person_id}/appearances # 인물의 미디어 등장
GET /api/v1/trismegistus/search?q=잔다르크              # 크로스 세계관 검색

# FGO 전용 (하위 호환)
GET /api/v1/trismegistus/servants?class=Saber            # FGO 서번트 목록
GET /api/v1/trismegistus/servants/{id}/compare           # 게임 vs 역사 비교
GET /api/v1/trismegistus/singularities                   # 특이점 목록
GET /api/v1/trismegistus/lostbelts                       # 이종대전 목록
```

---

## 7. 문학/창작 작품 레이어

### 왜 별도 레이어인가?

| | Historical | FGO/Game | Literary |
|---|---|---|---|
| 정확도 요구 | 높음 (학술) | 낮음 (창작) | 중간 (해석) |
| 인물 동일성 | 1:1 | 1:N (클래스별) | 1:1~N |
| 소스 추적 | Wikipedia/논문 | Atlas Academy | 원작 텍스트 |
| 주 사용처 | 역사 탐색 | 서번트 브릿지 | 원전 읽기 |

### 원전 텍스트 연결 (Book Extractor 활용)

이미 `tools/book_extractor/`로 처리 중인 텍스트:

```
보유 원전:
- Epic of Gilgamesh → 길가메시, 엔키두
- Odyssey → 오디세우스, 키르케
- Plutarch's Lives → 알렉산더, 카이사르 등
- Herodotus Histories → 레오니다스, 다리우스
- Celtic Mythology → 쿠 훌린, 스카사하
- Mahabharata → 아르주나, 카르나
- Japanese Mythology → 타마모, 슈텐도우지

처리 예정:
- Iliad → 아킬레스, 헥토르
- Le Morte d'Arthur → 아서왕, 머린
- Volsunga Saga → 시구르드, 브뤼닐데
- Sherlock Holmes → 셜록, 모리아티
- Frankenstein → 프랑켄슈타인
- Count of Monte Cristo → 에드몽 당테스
```

### 만화/미디어 DB 확장 (장기)

처음부터 모든 미디어를 다루지 않음. 단계적 확장:

```
Phase 1: FGO 서번트 300개 (기존 데이터)
Phase 2: FGO + 원전 연결 (Book Extractor)
Phase 3: 역사 만화 3-5작품 (킹덤, 빈란드 사가, 히스토리에)
Phase 4: 영화/드라마 인기작 10개
Phase 5: 기타 게임 (Civilization, AC, Total War)
Phase 6: 사용자 기여 (커뮤니티가 세계관 추가)
```

---

## 8. 구현 우선순위

### 즉시 (Sprint 0 완료 후)

1. `persons.tier` 컬럼 추가 + QRank 기반 분류
2. Feed API에 `tier_min` 파라미터 추가
3. 기본 UI에서 Tier B+ 만 표시

### 단기 (Sprint 1-2)

4. `trismegistus` 스키마 생성
5. 기존 FGO JSON → `character_mappings` 임포트
6. `servant_profiles` 임포트 (기존 `servants.json` + Atlas Academy)
7. TRISMEGISTUS API 기본 엔드포인트

### 중기 (Sprint 3-4)

8. 원전 연결 (`source_references`)
9. 비교 카드 UI
10. 2-3개 만화 세계관 추가 (수동)

### 장기 (Backlog)

11. TRISMEGISTUS 독립 서비스 분리
12. 사용자 기여 세계관
13. 미디어 DB 자동 수집

---

## 9. 비용 영향

| 항목 | 비용 | 비고 |
|------|------|------|
| QRank 다운로드 + 임포트 | 무료 | CC0 라이센스 |
| tier 분류 SQL | 무료 | 로컬 |
| trismegistus 스키마 | 무료 | SQL |
| FGO 데이터 임포트 | 무료 | 기존 JSON |
| 만화 세계관 수동 입력 | 무료 | 수동 |
| 원전 처리 (Book Extractor) | ~$5 | Ollama 로컬 / OpenAI 소량 |
| **합계** | **~$5** | |

---

## 기존 문서 통합 참조

이 문서는 다음 논의/연구를 통합한 것:

| 소스 | 통합된 내용 |
|------|------------|
| MIT Pantheon (Nature Scientific Data, 2016) | 인물 중요도 정량화 기준 |
| Cross-Verified Database (INED) | 크로스레퍼런스 인물 규모 |
| Charles Murray, "Human Accomplishment" | 업적 기반 인물 선별 |
| EventKG (2019) | 이벤트 기반 지식 그래프 규모 |
| Wikipedia Vital Articles | 필수 문서 계층 구조 |
| `event_hierarchy/13_FGO_DATA_LAYER.md` | FGO 서번트 DB 구조 |
| `event_hierarchy/16_MULTIVERSE_MODEL.md` | 멀티버스 데이터 모델 |
| `04_FGO_BRIDGE.md` | 서번트 ↔ 역사 브릿지 UX |
| `05_DATA_REQUIREMENTS.md` | 데이터 현황 감사 결과 |
