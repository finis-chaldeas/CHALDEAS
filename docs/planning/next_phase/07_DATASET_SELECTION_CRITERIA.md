# 07. 데이터셋 선정 기준: 학술적 근거

> "어떤 인물/사건/장소가 역사적으로 의미 있는가?"를 **자의적 판단이 아닌 학술적 근거**에 기반하여 정의한다.
> Full 버전(연구용 아카이브)과 Light 버전(탐색/교육용 핵심 데이터셋)의 선정 기준을 확립한다.

---

## 1. "역사적 중요성"의 학술적 정의

### 1.1 역사학 교육 프레임워크

역사적 중요성(Historical Significance)은 역사학 교육에서 가장 핵심적인 사고 개념 중 하나다.
세 가지 주요 프레임워크가 존재한다:

#### Partington의 5가지 기준 (1980)

> Partington, G. (1980). *The Idea of an Historical Education*. NFER Publishing.

| 기준 | 설명 | CHALDEAS 적용 |
|------|------|--------------|
| **Importance** | 당대 사람들에게 얼마나 중요했는가 | 이벤트 참여 인물 수, 영향 범위 |
| **Profundity** | 사람들의 삶에 얼마나 깊이 영향을 미쳤는가 | 사건의 질적 변화 (문명/정치체제 전환) |
| **Quantity** | 얼마나 많은 사람에게 영향을 미쳤는가 | 관련 지역의 인구 규모 |
| **Durability** | 영향이 얼마나 오래 지속되었는가 | 후속 사건과의 인과관계 수 |
| **Relevance** | 현재의 이해를 높이는 데 얼마나 관련 있는가 | 현대 교육과정에서의 다뤄짐 |

#### Counsell의 5R 기준 (2004)

> Counsell, C. (2004). "Looking through a Josephine-Butler-Shaped Window." *Teaching History*, 114, pp. 30-33.

| 기준 | 설명 | 판별 방법 |
|------|------|----------|
| **Remarkable** | 당시에 또는 이후에 주목할 만했는가 | Wikipedia 언어판 수 (L ≥ 15) |
| **Remembered** | 어떤 집단의 집단 기억에 중요했는가 | 다중 문화권 언급 빈도 |
| **Resulted in change** | 많은 사람에게 영향을 준 미래를 만들었는가 | event_connections 수 |
| **Resonant** | 시공간을 넘어 유비가 만들어지는가 | 문학/예술 작품에서의 인용 |
| **Revealing** | 그 시대를 흥미롭게 드러내는가 | 교육과정 포함 여부 |

#### Seixas & Morton의 4가지 지침 (2013)

> Seixas, P. and Morton, T. (2013). *The Big Six Historical Thinking Concepts*. Nelson Education.

1. **결과를 낳았는가**: 많은 사람에게, 오랜 기간, 깊은 결과를 가져온 것
2. **드러내는가**: 역사나 현대 생활의 지속적 쟁점에 빛을 비추는 것
3. **구성되는 것이다**: 서사 속에서 의미 있는 위치를 차지할 때만 중요해진다
4. **변한다**: 한 세대가 중요하게 여긴 것을 다른 세대는 아닐 수 있다

### 1.2 핵심 통찰

세 프레임워크를 종합하면, 역사적 중요성은 다음 **4가지 축**으로 측정 가능하다:

```
① 영향의 범위와 깊이 (Scope & Depth)
   → 연결된 이벤트/인물 수, 영향을 받은 지역 수

② 시간적 지속성 (Durability)
   → 후대에 미친 인과적 영향, 교육과정에서의 존재

③ 문화 횡단성 (Cross-cultural Reach)
   → 다수 문화권/언어에서 인지됨

④ 다영역 관련성 (Multi-domain Relevance)
   → 정치사뿐 아니라 철학/과학/예술/문학에도 영향
```

---

## 2. 디지털 인문학 프로젝트의 선정 방법론

### 2.1 MIT Pantheon (Yu et al., 2016)

> Yu, A.Z. et al. (2016). "Pantheon 1.0, a manually verified dataset of globally famous biographies." *Scientific Data*, 3, 150075.

**방법**: Freebase 2,394,169명 → Wikipedia 연결 997,276명 → **L > 25 (25개+ 언어판)** → **11,341명**

**HPI (Historical Popularity Index) 구성요소**:
- **L**: Wikipedia 언어판 수
- **L***: 엔트로피 조정 (한 언어에 집중되면 감점)
- **A**: 생존 기간 (log₄ 스케일, 오래될수록 가산점)
- **CV**: 페이지뷰 변동계수 (일시적 인기 감점)
- **v_NE**: 비영어 페이지뷰 (영어 편향 보정)
- **최근 인물 감점**: 알려진 지 70년 미만이면 (70-A)/7 감산

**직업 분류**: 3단계 — 88 세부직업 / 27 산업 / 8 도메인

**CHALDEAS 적용**: L > 25 기준으로 "세계적 중요 인물"의 하한선을 설정.

### 2.2 Cross-Verified Database (Laouenan et al., 2022)

> Laouenan, M. et al. (2022). "A cross-verified database of notable people, 3500BC-2018AD." *Scientific Data*, 9, 290.

**방법**: 7개 유럽어 Wikipedia 중 1개 이상 + Wikidata → **2,291,817명**

**Notability Index 5차원**:
1. Wikipedia 언어판 수
2. 전 언어판 합산 글자 수
3. 2015-2018 평균 페이지뷰
4. 메타데이터 완결도 (생년, 성별, 분야)
5. Wikidata 외부 링크/참조 수

**CHALDEAS 적용**: 5차원 중 3개 이상 데이터 있는 인물 = "충분히 문서화된 인물".

### 2.3 EventKG (Gottschalk & Demidova, 2018-2019)

> Gottschalk, S. and Demidova, E. (2019). "EventKG -- the Hub of Event Knowledge." *Semantic Web*, 10(6).

**이벤트 선정**: Wikidata "event" 하위 클래스 + DBpedia `dbo:Event` → **690,247개**
**관계 강도**: Wikipedia 상호 링크 빈도 + 동시 언급 문장 수
**정확도**: 98% (KG 기반), 88-94% (휴리스틱 기반)

**CHALDEAS 적용**: 이벤트 수 목표의 근거. 현재 28K → 최소 50K 이상이 적절.

### 2.4 Seshat: Global History Databank (Turchin et al., 2015~)

> Turchin, P. et al. (2015). "Seshat: The Global History Databank." *Cliodynamics*, 6(1).

**방법**: 지구를 10 대지역 × 3 NGA = **30개 자연지리구역**으로 나눠서 균등 샘플링.
각 지역에서 초기/중기/후기 복합 사회를 하나씩 선택 → 편향 방지.

**CHALDEAS 적용**: 지역 균등 샘플링 원칙. 유럽 편향을 의식적으로 교정.

### 2.5 YAGO 4.5 (Suchanek et al., 2024)

> Suchanek, F. et al. (2024). "YAGO 4.5: A Large and Clean Knowledge Base." *SIGIR 2024*.

**방법**: Wikidata 103M 엔티티 → 수동 검증된 상위 분류 체계에 매핑되는 것만 → **49M** (52% 제거)
- 학술 논문 (39M), 언어학적 객체 (700K), 추상 개념, 위키미디어 메타 페이지 제거

**CHALDEAS 적용**: "사람이 아닌 것을 제거"하는 것만으로 절반 이상 줄일 수 있음.

---

## 3. 대학교 교양 커리큘럼 기반 범위 설정

### 3.1 왜 대학 교양인가?

CHALDEAS의 목표 수준은 **"대학교 교양 과목에서 다루는 범위"**이다.
이는 전문 연구보다는 넓고, 고등학교보다는 깊은 수준 — **"교양 있는 일반인"**이 알 만한 것.

### 3.2 주요 교양 도메인과 커리큘럼 매핑

| 도메인 | 대표 커리큘럼 | 다루는 핵심 주제 수 | 핵심 인물 (예시) |
|--------|-------------|-------------------|----------------|
| **세계사** | AP World History, IB History | ~200 사건, ~500 인물 | 알렉산더, 칭기스 칸, 나폴레옹 |
| **철학사** | History of Philosophy (서양+동양) | ~100 주제 | 소크라테스, 공자, 칸트, 니체 |
| **수학사** | History of Mathematics | ~80 업적 | 유클리드, 알콰리즈미, 뉴턴, 오일러 |
| **과학사** | History of Science | ~100 발견 | 아리스토텔레스, 갈릴레오, 다윈, 아인슈타인 |
| **미술사** | Art History Survey | ~150 작품/운동 | 미켈란젤로, 렘브란트, 모네, 피카소 |
| **건축사** | History of Architecture | ~80 건물/양식 | 파르테논, 판테온, 고딕, 바우하우스 |
| **문학사** | World Literature Survey | ~100 작품 | 호메로스, 셰익스피어, 도스토예프스키, 카프카 |
| **음악사** | History of Music | ~80 작곡가/장르 | 바흐, 모차르트, 베토벤, 드뷔시 |
| **종교사** | World Religions | ~30 전통 | 붓다, 예수, 무함마드, 루터 |
| **정치사상사** | History of Political Thought | ~60 사상가 | 마키아벨리, 홉스, 루소, 마르크스 |
| **경제사** | Economic History | ~50 전환점 | 산업혁명, 대공황, 브레튼우즈 |
| **의학사** | History of Medicine | ~40 돌파구 | 히포크라테스, 파스퇴르, 플레밍 |

### 3.3 도메인별 예상 인물 수

| 도메인 | 핵심 (교과서 수준) | 확장 (전공 입문) | 전체 (전문 수준) |
|--------|-------------------|-----------------|----------------|
| 세계사 (정치/군사) | ~500 | ~3,000 | ~15,000 |
| 철학 | ~100 | ~500 | ~2,000 |
| 과학/수학 | ~150 | ~800 | ~3,000 |
| 문학 | ~150 | ~1,000 | ~5,000 |
| 미술/건축 | ~100 | ~600 | ~3,000 |
| 음악 | ~80 | ~400 | ~2,000 |
| 종교 | ~50 | ~300 | ~1,500 |
| 정치사상/경제 | ~100 | ~500 | ~2,000 |
| 의학/기술 | ~50 | ~300 | ~1,500 |
| **합계** | **~1,300** | **~7,400** | **~35,000** |

### 3.4 AP/IB 세계사 필수 주제 (이벤트 기준)

> College Board. (2017). *AP World History: Modern Course and Exam Description*.

AP World History의 5대 테마:
1. **ENV**: 인간과 환경의 상호작용
2. **CUL**: 문화의 발전과 상호작용
3. **SB**: 국가 건설, 팽창, 충돌
4. **ECON**: 경제 체계의 생성과 확장
5. **SOC**: 사회 구조의 발전과 변환

시대별 3-4개 핵심 개념 = 총 **~35개 핵심 주제**, 각 주제당 10-20개 사건 = **~500개 필수 사건**

---

## 4. 크로스 도메인 연결: 왜 중요한가

### 4.1 역사는 단일 분야가 아니다

하나의 인물/사건이 **여러 도메인에 동시에 중요**할 수 있다:

```
람세스 2세 (Ramesses II)
├── 정치사: 이집트 신왕국 최전성기, 카데시 전투
├── 건축사: 아부심벨 신전, 람세세움
├── 문학사: Percy Shelley, "Ozymandias" (1818) ← 역사와 문학의 교차
├── 고고학: 미라 발견 (1881), Howard Carter 시대
└── 대중문화: 출애굽기 전승, DreamWorks <이집트 왕자>
```

```
잔 다르크 (Joan of Arc)
├── 정치사: 백년전쟁 전환점, 오를레앙 해방
├── 종교사: 이단 재판, 1920년 시성
├── 문학사: Shakespeare "Henry VI Part 1" (1591)
│           Voltaire "La Pucelle d'Orléans" (1762)
│           Mark Twain "Personal Recollections" (1896)
│           George Bernard Shaw "Saint Joan" (1923)
├── 미술사: Jules Bastien-Lepage (1879), Ingres (1854)
├── 음악사: Verdi "Giovanna d'Arco" (1845), Tchaikovsky (1879)
└── FGO: Ruler 잔 다르크 ★★★★★
```

```
레오나르도 다 빈치 (Leonardo da Vinci)
├── 미술사: 모나리자, 최후의 만찬
├── 과학사: 해부학, 광학, 유체역학
├── 기술사: 비행기계, 전차 설계
├── 건축사: 밀라노 대성당 돔 설계
├── 문학사: 노트북 7,000+ 페이지 (Codex Leicester)
└── FGO: Rider 레오나르도 다 빈치 ★★★★★
```

### 4.2 크로스 도메인이 CHALDEAS의 핵심 가치

**단순 역사 DB**: 람세스 2세 → "이집트 파라오, BCE 1279-1213 재위" (끝)

**CHALDEAS**: 람세스 2세 → 정치사 + 건축사 + 시(Ozymandias) + 고고학 + 대중문화
→ 유저가 "Ozymandias"를 읽고 "이게 람세스 2세였어?" → 아부심벨 신전 보기 → 카데시 전투 → 히타이트 제국

**이것이 "교양"이다**: 하나의 주제에서 여러 분야로 자연스럽게 넘어가는 경험.

### 4.3 도메인 연결 데이터 모델

```sql
-- 이미 있는 categories 테이블 확장 또는 태그 시스템
-- persons/events에 복수 도메인 태그 가능하게

-- 예: 람세스 2세의 도메인 태그
-- person_domains: (ramesses_id, 'political_history')
-- person_domains: (ramesses_id, 'architecture')
-- person_domains: (ramesses_id, 'literature')  -- Ozymandias 연결

-- 예: 잔 다르크의 도메인 태그
-- person_domains: (joan_id, 'political_history')
-- person_domains: (joan_id, 'religious_history')
-- person_domains: (joan_id, 'literature')  -- Shakespeare, Shaw 연결
-- person_domains: (joan_id, 'art_history')  -- 회화
-- person_domains: (joan_id, 'music_history')  -- 오페라
```

---

## 5. Wikipedia/Wikidata 기반 정량 지표

### 5.1 Wikipedia 자체의 "필수 문서" 계층

> Wikipedia:Vital articles. Community-maintained hierarchical list.

| Level | 문서 수 | 인물 비중 | 범위 |
|-------|---------|---------|------|
| 1 | 10 | 0 | 절대 필수 (Earth, History...) |
| 2 | 100 | ~20 | 핵심 주제 |
| 3 | 1,000 | ~200 | **교과서 수준** |
| 4 | 10,000 | ~2,000 | **교양 수준** |
| 5 | 50,000 | ~10,000 | 포괄적 커버 |

선정 기준: "인류의 진로에 물질적 영향을 미친, 해당 분야의 정점"
서양 편향 의식적 교정: "영어 Wikipedia이지만 초점은 세계"

### 5.2 Wikipedia 언어판 수 (L) 연구

> Eom, Y.-H. et al. (2015). "Interactions of Cultures and Top People of Wikipedia." *PLoS ONE*, 10(3).

- **L ≥ 18**: "글로벌 인물" — 24개 언어판에서 일관되게 높은 순위
- **L ≥ 25**: Pantheon의 "세계사적 중요 인물" 기준 (11,341명)
- **L < 5**: 지역적/일시적 중요성만 — 대부분 현대인

### 5.3 QRank의 가치와 한계

> Brawer, S. (2020~). "Wikidata QRank." Wikimedia Toolforge.

**가치**: 12개월 롤링 페이지뷰 합산, 일시적 트렌드 완화
**한계**:
- 최근 편향 (Recency bias) — 현대 인물 과대평가
- 영어권 편향 — 영미 인물 과대평가 (Callahan & Herring, 2011)
- 대중문화 편향 — 배우/운동선수가 철학자보다 높을 수 있음

**보정 방법**: Pantheon의 HPI처럼 **시간 보정** (log₄(나이)) + **비영어 비중** 가산 필요

### 5.4 Skiena & Ward의 "Who's Bigger?" (2014)

> Skiena, S. and Ward, C.B. (2014). *Who's Bigger?* Cambridge University Press.

5가지 Wikipedia 지표 조합 + **최근 편향 알고리즘 보정**:
1. 전체 Wikipedia 그래프 PageRank
2. 인물 전용 서브그래프 PageRank
3. 페이지뷰
4. 편집 횟수
5. 페이지 크기

---

## 6. Braudel의 시간 척도와 이벤트 선정

> Braudel, F. (1958). "Histoire et Sciences sociales: La longue durée." *Annales*, 13(4), 725-753.

| 척도 | 프랑스어 | 기간 | 예시 | 선정 기준 |
|------|---------|------|------|----------|
| **장기지속** | longue durée | 수세기~수천 년 | 기후 변화, 지리, 인구 변동 | 구조적 — 가장 본질적 |
| **국면** | conjoncture | 수년~수십 년 | 경제 순환, 무역 패턴 | 중기적 인과 설명 |
| **사건** | événementielle | 수일~수개월 | 전투, 조약, 암살 | 표면 현상 — "역사의 먼지" |

**CHALDEAS 적용**: 이벤트를 3 척도로 분류하면 "먼지"와 "본질"을 구분 가능.
- **Light 버전**: longue durée + conjoncture 중심 (구조적 변화)
- **Full 버전**: événementielle까지 포함 (모든 전투, 조약)

---

## 7. 장소 선정의 역사지리학적 근거

### 7.1 Pleiades (고대 세계)

> Elliott, T. and Gillies, S. (2009~). "Pleiades: A community-built gazetteer of ancient places." NYU.

**36,000+개 고대 장소**. 커뮤니티 큐레이션 기반, 공식 포함 기준 없음.
한계: 그리스-로마 중심 편향 ("고전학자들이 연구하는 것의 기록").

### 7.2 World Historical Gazetteer (1500~ 현재)

> Grossner, K. and Mostern, R. (2022). "World Historical Gazetteer." *Int. J. Digital Libraries*, 23.

**1500년 이후** 전 세계 주요 지명. **아프리카, 라틴아메리카, 동남아** 의식적 보완.
Linked Places Format (LPF) — 시간-공간 확장 GeoJSON.

### 7.3 역사 아틀라스 기준

DK Atlas of World History, Times Atlas of World History 등 주요 역사 아틀라스에 등장하는 장소 = **"지도에 나올 만한 곳"**. 일반적으로:
- 주요 도시: ~500개
- 전투/조약 장소: ~1,000개
- 종교/문화 중심지: ~300개
- 교역로 거점: ~200개

---

## 8. CHALDEAS Light 버전 선정 기준

위의 학술적 근거를 종합하여, **Full 버전과 Light 버전**을 다음과 같이 정의한다:

### 8.1 Full 버전 (연구용 아카이브)

현재 DB 그대로. 단, 정리 후:
- **인물**: ~500K (QRank 상위 5% + 이벤트 연결)
- **이벤트**: ~50K (Wikidata event 서브클래스 전체)
- **장소**: ~100K (이벤트 연결 + 주요 도시)
- **entity_properties**: 해당 인물/이벤트/장소의 것만

### 8.2 Light 버전 (교양 탐색용)

**"대학교 교양 수준에서 다루는 모든 것"**을 커버.

#### 인물 선정 기준 (4단계 필터)

```
필터 1: 문화 횡단성 (Counsell의 "Remarkable" + "Remembered")
   → Wikipedia 15개+ 언어판 등장 (Pantheon 확장 기준)
   → 또는 QRank 상위 0.5%
   → 예상: ~85,000명

필터 2: 교양 도메인 커버 (대학 커리큘럼)
   → entity_properties P106(직업)이 교양 도메인에 해당
   → philosopher, mathematician, composer, architect, painter, writer,
     physicist, astronomer, physician, theologian, economist, historian...
   → 필터 1에서 누락된 도메인 전문가 보충
   → 예상: +5,000명

필터 3: 이벤트 연결 보장
   → event_persons에 존재하는 모든 인물 포함
   → 현재 90,710명 — 이미 필터 1,2에 대부분 포함될 것
   → 예상: +10,000명 (필터 1,2에 없는 것만)

필터 4: 크로스 도메인 보충
   → "작품"을 통해 역사 인물과 연결되는 문학/예술 인물
   → 예: 셰익스피어(문학) → 잔다르크(역사), 리처드 3세(역사)
   →    셸리(문학) → 람세스2세(역사, Ozymandias)
   →    베르디(음악) → 잔다르크(역사, 오페라)
   → 예상: +2,000명
```

**Light 인물 총계: ~100,000명** (현재의 1/130)

#### 이벤트 선정 기준

```
기준 1: Braudel longue durée + conjoncture
   → 문명 전환, 제국 흥망, 사상 운동, 기술 혁명
   → hierarchy_level 0-2 (Era, Mega, Aggregate)
   → 예상: ~500개

기준 2: AP/IB 세계사 필수 사건
   → 5대 테마 × 시대별 핵심 개념
   → 예상: ~500개

기준 3: 도메인별 전환점
   → 철학: 아카데미아 설립, 스콜라 철학 등장, 계몽주의...
   → 과학: 지동설, 만유인력, 진화론, 상대성이론...
   → 미술: 원근법 발명, 인상주의, 큐비즘...
   → 음악: 다성음악, 바로크, 고전주의, 낭만주의...
   → 건축: 고딕 양식, 르네상스 건축, 모더니즘...
   → 문학: 서사시 전통, 소설의 탄생, 근대 문학...
   → 예상: ~1,000개

기준 4: 이벤트 연결 인물의 주요 사건
   → Light 인물이 참여한 이벤트 (event_persons 기반)
   → 예상: ~20,000개

기준 5: QRank 상위 이벤트
   → QRank로 정렬한 상위 이벤트
   → 예상: ~10,000개
```

**Light 이벤트 총계: ~30,000개** (현재와 유사하지만 importance 분포 있음)

#### 장소 선정 기준

```
기준 1: 이벤트/인물 연결 장소
   → Light 이벤트의 primary_location + Light 인물의 birthplace/deathplace
   → 예상: ~20,000개

기준 2: 역사 아틀라스 수준 주요 장소
   → 수도, 전투지, 종교 중심, 교역 거점
   → 예상: ~2,000개

기준 3: 건축사/미술사 명소
   → 파르테논, 콜로세움, 타지마할, 자금성...
   → 예상: ~300개
```

**Light 장소 총계: ~20,000개** (현재의 1/120)

### 8.3 도메인별 커버 체크리스트

Light 버전이 아래 도메인을 **균등하게** 커버하는지 반드시 확인:

| 도메인 | 최소 인물 | 최소 이벤트 | 확인 방법 |
|--------|---------|-----------|----------|
| 정치/군사사 | 5,000 | 5,000 | P106: monarch, politician, military |
| 철학사 | 300 | 200 | P106: philosopher |
| 수학사 | 200 | 100 | P106: mathematician |
| 과학사 | 500 | 300 | P106: physicist, chemist, biologist... |
| 미술사 | 500 | 200 | P106: painter, sculptor |
| 건축사 | 200 | 100 | P106: architect |
| 문학사 | 800 | 300 | P106: writer, poet, playwright |
| 음악사 | 400 | 200 | P106: composer, musician |
| 종교사 | 300 | 200 | P106: theologian, religious leader |
| 경제사 | 200 | 200 | P106: economist + 경제 이벤트 |
| 의학사 | 200 | 100 | P106: physician, surgeon |
| 기술/발명 | 300 | 200 | P106: inventor, engineer |

### 8.4 편향 교정 체크리스트

Seshat의 지역 균등 샘플링 원칙을 적용:

| 지역 | 최소 인물 비중 | 현재 예상 편향 |
|------|-------------|--------------|
| 유럽 | ≤ 40% | Wikipedia/Wikidata 특성상 과다 |
| 동아시아 | ≥ 15% | 중국/일본/한국 |
| 남아시아 | ≥ 10% | 인도/동남아 |
| 중동/북아프리카 | ≥ 10% | 이슬람 문명권 |
| 사하라 이남 아프리카 | ≥ 5% | 과소대표 위험 |
| 아메리카 | ≥ 5% | 식민 이전 포함 |
| 중앙아시아 | ≥ 3% | 유목 문명 |
| 오세아니아 | ≥ 1% | |

---

## 9. 구현: Full → Light 분리 전략

### 9.1 방법: 별도 DB가 아닌 `is_light` 플래그

```sql
-- persons 테이블에 플래그 추가
ALTER TABLE persons ADD COLUMN is_light BOOLEAN DEFAULT FALSE;
CREATE INDEX idx_persons_light ON persons(is_light) WHERE is_light = TRUE;

-- events 테이블에 플래그 추가
ALTER TABLE events ADD COLUMN is_light BOOLEAN DEFAULT FALSE;
CREATE INDEX idx_events_light ON events(is_light) WHERE is_light = TRUE;

-- locations 테이블에 플래그 추가
ALTER TABLE locations ADD COLUMN is_light BOOLEAN DEFAULT FALSE;
CREATE INDEX idx_locations_light ON locations(is_light) WHERE is_light = TRUE;
```

### 9.2 Light 플래그 설정 SQL (QRank 임포트 후 실행)

```sql
-- 인물: 필터 1 (QRank 상위 0.5%)
WITH ranked AS (
    SELECT p.id, PERCENT_RANK() OVER (ORDER BY q.score DESC) as pct
    FROM persons p
    JOIN qrank q ON q.wikidata_id = p.wikidata_id
)
UPDATE persons SET is_light = TRUE
FROM ranked r WHERE r.id = persons.id AND r.pct <= 0.005;

-- 인물: 필터 2 (교양 도메인 직업)
UPDATE persons SET is_light = TRUE
WHERE role IN (
    'philosopher', 'mathematician', 'physicist', 'chemist', 'biologist',
    'astronomer', 'geographer', 'physician', 'surgeon',
    'painter', 'sculptor', 'architect', 'composer', 'musician',
    'writer', 'poet', 'playwright', 'novelist', 'historian',
    'theologian', 'economist', 'political scientist',
    'inventor', 'engineer', 'explorer',
    'monarch', 'emperor', 'pharaoh', 'pope'
) AND is_light = FALSE;

-- 인물: 필터 3 (이벤트 연결)
UPDATE persons SET is_light = TRUE
WHERE id IN (SELECT DISTINCT person_id FROM event_persons)
  AND is_light = FALSE;

-- 이벤트: QRank 상위 + importance 3+
UPDATE events SET is_light = TRUE
WHERE importance >= 3
   OR id IN (SELECT DISTINCT event_id FROM event_persons);

-- 장소: Light 이벤트/인물과 연결된 장소
UPDATE locations SET is_light = TRUE
WHERE id IN (
    SELECT primary_location_id FROM events WHERE is_light = TRUE AND primary_location_id IS NOT NULL
    UNION
    SELECT birthplace_id FROM persons WHERE is_light = TRUE AND birthplace_id IS NOT NULL
    UNION
    SELECT deathplace_id FROM persons WHERE is_light = TRUE AND deathplace_id IS NOT NULL
);
```

### 9.3 API에서의 사용

```python
# 기본 모드: Light만 표시
@router.get("/persons")
async def get_persons(
    mode: str = "light",  # "light" | "full"
    ...
):
    if mode == "light":
        query = query.filter(Person.is_light == True)
    ...
```

### 9.4 DB 크기 예상

| | Full | Light | 비율 |
|---|------|-------|-----|
| persons | 12,987,361 | ~100,000 | 0.8% |
| events | 28,331 | ~28,000 | ~100% |
| locations | 2,387,834 | ~20,000 | 0.8% |
| entity_properties | 112,800,000 | ~5,000,000 | 4.4% |
| **예상 DB 크기** | **43 GB** | **~5-8 GB** | **~15%** |

---

## 10. 검증 프로세스

Light 버전 생성 후 반드시 검증:

### 10.1 도메인 커버 검증

```sql
-- 도메인별 인물 수 확인
SELECT role, COUNT(*) FROM persons
WHERE is_light = TRUE AND role IS NOT NULL
GROUP BY role ORDER BY COUNT(*) DESC LIMIT 30;
```

### 10.2 시대별 분포 검증

```sql
-- 시대별 인물 분포 (고르게 분포되어야 함)
SELECT
    CASE
        WHEN birth_year < -3000 THEN 'Ancient (pre-3000 BCE)'
        WHEN birth_year < -500 THEN 'Classical (-3000 to -500)'
        WHEN birth_year < 500 THEN 'Late Antiquity (-500 to 500)'
        WHEN birth_year < 1000 THEN 'Early Medieval (500-1000)'
        WHEN birth_year < 1500 THEN 'Late Medieval (1000-1500)'
        WHEN birth_year < 1800 THEN 'Early Modern (1500-1800)'
        ELSE 'Modern (1800+)'
    END as era,
    COUNT(*)
FROM persons WHERE is_light = TRUE AND birth_year IS NOT NULL
GROUP BY era ORDER BY MIN(birth_year);
```

### 10.3 지역별 분포 검증

```sql
-- 지역별 분포 (유럽 ≤ 40% 확인)
SELECT l.region, COUNT(DISTINCT p.id)
FROM persons p
JOIN locations l ON l.id = p.birthplace_id
WHERE p.is_light = TRUE
GROUP BY l.region ORDER BY COUNT(*) DESC;
```

### 10.4 "교과서 인물" 스팟 체크

아래 인물이 **반드시** Light에 포함되어 있는지 확인:

**세계사**: 알렉산더 대왕, 진시황, 카이사르, 칭기스 칸, 나폴레옹
**철학**: 소크라테스, 공자, 칸트, 니체, 데카르트
**과학**: 아리스토텔레스, 갈릴레오, 뉴턴, 다윈, 아인슈타인
**수학**: 유클리드, 알콰리즈미, 라이프니츠, 오일러, 가우스
**문학**: 호메로스, 셰익스피어, 괴테, 도스토예프스키, 톨스토이
**미술**: 미켈란젤로, 레오나르도, 렘브란트, 모네, 피카소
**음악**: 바흐, 모차르트, 베토벤, 쇼팽, 스트라빈스키
**건축**: 임호텝, 비트루비우스, 브루넬레스키, 가우디, 르 코르뷔지에
**종교**: 붓다, 예수, 무함마드, 루터, 칼뱅
**의학**: 히포크라테스, 갈레노스, 이븐 시나, 파스퇴르, 플레밍

---

## 참고문헌

### 역사학 교육
- Partington, G. (1980). *The Idea of an Historical Education*. NFER Publishing.
- Counsell, C. (2004). "Looking through a Josephine-Butler-Shaped Window." *Teaching History*, 114.
- Seixas, P. and Morton, T. (2013). *The Big Six Historical Thinking Concepts*. Nelson Education.
- College Board. (2017). *AP World History: Modern Course and Exam Description*.

### 디지털 인문학 데이터셋
- Yu, A.Z. et al. (2016). "Pantheon 1.0." *Scientific Data*, 3, 150075.
- Laouenan, M. et al. (2022). "A cross-verified database of notable people." *Scientific Data*, 9, 290.
- Gottschalk, S. and Demidova, E. (2019). "EventKG." *Semantic Web*, 10(6).
- Turchin, P. et al. (2015). "Seshat: The Global History Databank." *Cliodynamics*, 6(1).
- Suchanek, F. et al. (2024). "YAGO 4.5." *SIGIR 2024*.

### Wikipedia/Wikidata 연구
- Eom, Y.-H. et al. (2015). "Interactions of Cultures and Top People of Wikipedia." *PLoS ONE*, 10(3).
- Skiena, S. and Ward, C.B. (2014). *Who's Bigger?* Cambridge University Press.
- Callahan, E.S. and Herring, S.C. (2011). "Cultural bias in Wikipedia." *JASIST*, 62(10).

### 역사학 방법론
- Braudel, F. (1958). "La longue durée." *Annales*, 13(4), 725-753.

### 역사 지리
- Elliott, T. and Gillies, S. (2009~). "Pleiades." NYU.
- Grossner, K. and Mostern, R. (2022). "World Historical Gazetteer." *Int. J. Digital Libraries*, 23.
