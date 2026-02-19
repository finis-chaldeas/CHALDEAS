# 역사 이벤트 분류 방법론 조사 보고서

## 목차
1. [개요](#1-개요)
2. [학술적 분류 체계](#2-학술적-분류-체계)
3. [온톨로지 기반 접근법](#3-온톨로지-기반-접근법)
4. [위키 기반 분류 체계](#4-위키-기반-분류-체계)
5. [NLP/AI 이벤트 분류](#5-nlpai-이벤트-분류)
6. [CHALDEAS 적용 제안](#6-chaldeas-적용-제안)
7. [참고문헌](#7-참고문헌)

---

## 1. 개요

역사 이벤트 분류는 여러 학문 분야에서 다양한 접근법으로 연구되어 왔다. 본 보고서는 학술 논문, 온톨로지 표준, 위키 시스템, NLP 연구 등에서 사용하는 분류 방법론을 조사하여 CHALDEAS 프로젝트에 적합한 분류 체계를 제안한다.

### 핵심 질문
- 역사 이벤트를 어떤 기준으로 대분류할 것인가?
- 계층 구조는 어떻게 설계할 것인가?
- 여러 분류 체계를 어떻게 통합할 것인가?

---

## 2. 학술적 분류 체계

### 2.1 Braudel의 시간 척도 (Annales 학파)

Fernand Braudel은 역사를 **세 가지 시간 척도**로 구분했다:

| 시간 척도 | 프랑스어 | 기간 | 특성 |
|----------|---------|------|------|
| **단기** | événementielle | 일~수년 | 사건 중심, 연대기적 역사 |
| **중기** | conjoncture | 수십~수백 년 | 경제 순환, 사회 변동 |
| **장기** | longue durée | 수백~수천 년 | 지리, 기후, 문명 구조 |

**적용 예시**:
- 단기: 워털루 전투 (1815년 6월 18일)
- 중기: 나폴레옹 전쟁 (1803-1815)
- 장기: 근대 국민국가의 형성 (18-20세기)

> "역사가는 시간의 질문에서 벗어날 수 없다. 시간은 정원사의 삽에 붙은 흙처럼 그의 사고에 달라붙는다." - Braudel (1958)

**참고**: [Longue durée - Wikipedia](https://en.wikipedia.org/wiki/Longue_dur%C3%A9e)

---

### 2.2 역사적 시대 구분 (Periodization)

#### 전통적 서양 시대 구분
페트라르카(Petrarch)가 제안한 3분법:

```
고대 (Ancient)     : ~500 CE
중세 (Medieval)    : 500-1500 CE
근대 (Modern)      : 1500~현재
```

#### 확장된 시대 구분
```
선사시대 (Prehistory)    : ~3000 BCE
고대 (Ancient)           : 3000 BCE - 500 CE
중세 (Medieval)          : 500 - 1500 CE
근세 (Early Modern)      : 1500 - 1800 CE
근대 (Modern)            : 1800 - 1945 CE
현대 (Contemporary)      : 1945~현재
```

#### 대안적 시대 구분 방법
| 방법 | 기준 | 예시 |
|------|------|------|
| **물질문화** | 기술/재료 | 석기시대, 청동기, 철기시대 |
| **경제사** | 경제 체제 | 봉건제, 산업혁명, 정보화시대 |
| **환경사** | 인간-환경 관계 | 농업혁명, 인류세 |
| **문화사** | 사상/예술 | 르네상스, 계몽주의, 낭만주의 |

#### 시대 구분의 한계
- **유럽 중심성**: "중세", "근대" 등의 개념은 서유럽 역사에 기반
- **자의성**: 모든 시대 구분은 본질적으로 자의적
- **연속성**: 역사는 실제로 연속적이며 명확한 경계가 없음

**참고**: [Periodization - Wikipedia](https://en.wikipedia.org/wiki/Periodization)

---

### 2.3 지역별 접근법

세계사 연구자들의 **주제적 접근**:

| 축 | 초점 | 설명 |
|----|------|------|
| **통합** | 연결성 | 문명 간 교류, 무역로, 이주 |
| **다양성** | 차이 | 각 문명의 독자적 발전 경로 |

**문명권별 구분**:
- 서유럽 / 동유럽 / 비잔틴
- 이슬람 세계
- 동아시아 (중국, 한국, 일본)
- 남아시아 (인도)
- 아메리카 / 아프리카 / 오세아니아

---

## 3. 온톨로지 기반 접근법

### 3.1 CIDOC-CRM (ISO 21127:2023)

문화유산 정보 통합을 위한 국제 표준 온톨로지.

#### 핵심 특징
- **이벤트 중심 설계**: 모든 것을 시공간 속 이벤트로 모델링
- **두 가지 최상위 클래스**:
  - `E2 Temporal Entity` (시간적 존재): 이벤트, 시대, 상태
  - `E77 Persistent Item` (지속적 존재): 물체, 개념

#### 이벤트 계층 구조
```
E2 Temporal Entity
├── E4 Period (시대/기간)
├── E5 Event (이벤트)
│   ├── E7 Activity (활동)
│   │   ├── E8 Acquisition
│   │   ├── E9 Move
│   │   ├── E10 Transfer of Custody
│   │   ├── E11 Modification
│   │   ├── E12 Production
│   │   ├── E13 Attribute Assignment
│   │   └── E65 Creation
│   ├── E63 Beginning of Existence
│   └── E64 End of Existence
└── E3 Condition State
```

#### 장점
- ISO 국제 표준
- 문화유산 분야에서 광범위하게 사용
- 확장 가능한 모듈형 구조

**참고**: [CIDOC CRM Official](https://cidoc-crm.org/), [CIDOC-CRM - Wikipedia](https://en.wikipedia.org/wiki/CIDOC_Conceptual_Reference_Model)

---

### 3.2 LODE (Linking Open Descriptions of Events)

Linked Data로 역사 이벤트를 기술하기 위한 온톨로지.

#### 4W 프레임워크
| 질문 | 속성 | 설명 |
|------|------|------|
| **What** | Event | 무슨 일이 일어났는가 |
| **When** | atTime | 언제 일어났는가 |
| **Where** | atPlace | 어디서 일어났는가 |
| **Who** | involvedAgent | 누가 관여했는가 |

#### 특징
- DOLCE Ultra-Lite 기반
- 7개의 핵심 속성만 정의 (최소주의)
- 다른 이벤트 온톨로지와 매핑 가능

**참고**: [LODE Ontology](https://linkedevents.org/ontology/), [LODE GitHub](https://github.com/wouterbeek/lode)

---

### 3.3 SEM (Simple Event Model)

다양한 도메인에서 이벤트를 모델링하기 위한 범용 온톨로지.

#### 핵심 클래스
```
sem:Event (이벤트)
├── sem:Actor (참여자)
├── sem:Place (장소)
├── sem:Time (시간)
└── sem:Role (역할)
```

#### 특징
- 도메인 중립적 설계
- 최소한의 의미론적 약속
- 역할(Role) 개념으로 동일 참여자의 다중 역할 표현 가능

**참고**: [SEM Ontology](https://semanticweb.cs.vu.nl/2009/11/sem/)

---

### 3.4 DBpedia 온톨로지

Wikipedia 기반 지식 그래프의 이벤트 분류.

#### Event 클래스 계층
```
Event
├── SocietalEvent
│   ├── HistoricalEvent (역사적 사건)
│   ├── MilitaryConflict (군사 충돌)
│   ├── Election (선거)
│   ├── Rebellion (반란)
│   └── Convention (회의)
├── NaturalEvent
│   ├── Earthquake
│   ├── SolarEclipse
│   └── Outbreak
├── SportsEvent
├── MusicFestival
├── FilmFestival
└── SpaceMission
```

#### HistoricalEvent 정의
> "단순히 개인적인 사건과 명확히 구분되며 역사적 영향을 미친 사건"

**참고**: [DBpedia Ontology](https://www.dbpedia.org/resources/ontology/), [DBpedia HistoricalEvent](https://dbpedia.org/ontology/HistoricalEvent)

---

## 4. 위키 기반 분류 체계

### 4.1 Wikipedia 영어판

#### 역사 콘텐츠 조직 방식
| 축 | 예시 |
|----|------|
| **시대별** | Prehistory, Ancient, Classical, Medieval, Modern |
| **지역별** | Ancient Egypt, Ancient Greece, History of China |
| **주제별** | Political history, Social history, Economic history |

#### 카테고리 특성
- **비엄격 계층**: 하나의 문서가 여러 카테고리에 속함
- **DAG 구조**: 이론상 방향성 비순환 그래프이나, 실제로는 순환 발생
- **명명 규칙**: 구조를 표시하지 않음 (예: `History of London` O, `History - Europe - UK - London` X)

**참고**: [Wikipedia:Categorization](https://en.wikipedia.org/wiki/Wikipedia:Categorization)

---

### 4.2 Wikidata

#### P31 (instance of) / P279 (subclass of) 시스템

| 속성 | 의미 | 예시 |
|------|------|------|
| **P31** | ~의 인스턴스 | K2 → instance of → mountain |
| **P279** | ~의 하위 클래스 | volcano → subclass of → mountain |

#### 특징
- 99% 이상의 엔티티가 P31/P279로 연결
- 메타모델링 허용 (인스턴스가 동시에 클래스가 될 수 있음)
- 대규모 개념적 혼란 존재 (특히 생물학 분야)

**참고**: [Wikidata P31](https://www.wikidata.org/wiki/Property:P31), [Wikidata Item Classification](https://www.wikidata.org/wiki/Wikidata:Item_classification)

---

### 4.3 나무위키

#### 역사 분류 구조
```
분류:역사 (상위: 사회, 학문)
├── 기록
├── 분야별 역사
├── 사건 사고
├── 사학
├── 세기별 역사
├── 신화
├── 역사 교과
├── 역사물
├── 역사적 사상
├── 연표
├── 자연사박물관
└── 장소별 역사
```

#### 분류 존치 기준
1. **포괄성**: 복수의 것들을 포괄
2. **학술성**: 학계에 존재하는 개념
3. **필요성**: 존재 이유가 있어야 함
4. **활용성**: 활용 가능성
5. **체계성**: 상하위/관련 분류와의 일관성

#### 한계
- 주관적 분류 적용
- 분류 변경 이력 추적 어려움

**참고**: [나무위키:분류](https://namu.wiki/w/%EB%82%98%EB%AC%B4%EC%9C%84%ED%82%A4:%EB%B6%84%EB%A5%98), [분류:역사](https://namu.wiki/w/%EB%B6%84%EB%A5%98:%EC%97%AD%EC%82%AC)

---

## 5. NLP/AI 이벤트 분류

### 5.1 ACE/ERE 이벤트 타입

자연어 처리에서 사용하는 이벤트 어노테이션 스키마.

#### ACE 이벤트 타입 (8개 대분류)
```
Life          : 출생, 사망, 결혼, 이혼
Movement      : 이동, 운송
Transaction   : 거래, 이전
Business      : 창업, 합병, 파산
Conflict      : 공격, 시위
Contact       : 만남, 통신
Personnel     : 임명, 해임, 선출
Justice       : 체포, 재판, 석방
```

#### Rich ERE (2016) - 8 타입, 18 서브타입
확장된 이벤트 온톨로지 + realis 속성 (ACTUAL/GENERIC/OTHER)

**참고**: [ACE/ERE Comparison](https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/acl2014-comparison-events-relations.pdf)

---

### 5.2 뉴스 이벤트 분류 (Wikipedia Current Events)

WWW 2015 논문에서 제안된 **9개 대분류**:

| 코드 | 분류 | 설명 |
|------|------|------|
| AA | Armed Conflicts & Attacks | 전쟁, 테러, 군사 충돌 |
| AC | Arts & Culture | 문화, 예술, 엔터테인먼트 |
| BE | Business & Economy | 경제, 기업, 금융 |
| DA | Disasters & Accidents | 자연재해, 사고 |
| HE | Health & Environment | 보건, 환경 |
| LC | Law & Crime | 법률, 범죄 |
| PE | Politics & Elections | 정치, 선거 |
| ST | Science & Technology | 과학, 기술 |
| SP | Sports | 스포츠 |

**참고**: [Towards a Complete Event Type Taxonomy](https://dl.acm.org/doi/10.1145/2740908.2742005)

---

### 5.3 역사 텍스트 이벤트 분류

MIT Press (2019) 연구에서 제안된 **22개 이벤트 클래스**:
- 역사 텍스트에 특화된 어노테이션 가이드라인
- CRF와 신경망 기반 자동 분류 시스템 개발

**참고**: [Novel Event Detection for Historical Texts](https://direct.mit.edu/coli/article/45/2/229/1630/Novel-Event-Detection-and-Classification-for)

---

## 6. CHALDEAS 적용 제안

### 6.1 분류 축 정의

CHALDEAS는 다음 **4가지 축**을 조합하여 이벤트를 분류할 것을 제안한다:

| 축 | 설명 | 예시 값 |
|----|------|---------|
| **시간** | Braudel의 시간 척도 | longue_duree, conjuncture, evenementielle |
| **유형** | 이벤트 본질 | war, treaty, revolution, dynasty, movement |
| **지역** | 지리적 범위 | europe, asia, global, regional |
| **규모** | 영향 범위 | world, civilization, national, local |

---

### 6.2 이벤트 유형 대분류 (제안)

```
1. 군사/충돌 (Military/Conflict)
   ├── 전쟁 (War)
   ├── 전투 (Battle)
   ├── 포위전 (Siege)
   ├── 반란 (Rebellion)
   └── 정복 (Conquest)

2. 정치/외교 (Political/Diplomatic)
   ├── 조약 (Treaty)
   ├── 동맹 (Alliance)
   ├── 왕조/통치 (Dynasty/Reign)
   ├── 혁명 (Revolution)
   └── 선거/즉위 (Election/Coronation)

3. 사회/문화 (Social/Cultural)
   ├── 운동 (Movement)
   ├── 종교 (Religion)
   ├── 예술 (Art)
   └── 학문 (Science)

4. 경제 (Economic)
   ├── 무역 (Trade)
   ├── 산업 (Industry)
   └── 위기 (Crisis)

5. 재난 (Disaster)
   ├── 자연재해 (Natural)
   ├── 전염병 (Epidemic)
   └── 기근 (Famine)

6. 시대/기간 (Period)
   ├── 세기 (Century)
   ├── 시대 (Era)
   └── 왕조 (Dynasty)
```

---

### 6.3 계층 구조 설계 원칙

#### 원칙 1: 다중 부모 허용
- 하나의 이벤트가 여러 상위 이벤트에 속할 수 있음
- 예: "워털루 전투" → 나폴레옹 전쟁 / 제7차 대불동맹전쟁

#### 원칙 2: 시간적 포함 관계 우선
- 자식 이벤트의 시간 범위는 부모의 시간 범위 내에 있어야 함
- 예외: 원인-결과 관계 (선행 이벤트가 후행 이벤트의 부모가 될 수 있음)

#### 원칙 3: 분류 소스 명시
```
source: 'wikidata'    # Wikidata P361 관계
source: 'period'      # 시대 기반 자동 분류
source: 'llm'         # LLM 기반 분류
source: 'manual'      # 수동 분류
```

#### 원칙 4: 광범위 카테고리 제한
- "16th century" 같은 단순 시대는 최상위 분류로만 사용
- 구체적 이벤트(전쟁, 왕조 등)를 중간 계층으로 우선 배치

---

### 6.4 구현 전략

#### Phase 1: 상위 이벤트 확립
1. Wikidata에서 주요 전쟁/왕조/운동 이벤트 가져오기
2. P361 관계로 계층 구조 구축
3. 시대 이벤트는 최상위로만 사용

#### Phase 2: 인물 기반 분류
1. 인물의 주요 이벤트 조회 (Wikidata P793 significant event)
2. 해당 인물 관련 이벤트를 주요 이벤트 하위로 배치

#### Phase 3: 시공간 군집화
1. 시간 + 장소가 유사한 이벤트 그룹화
2. 그룹 내 대표 이벤트를 부모로 지정

#### Phase 4: LLM 보완
1. 미분류 이벤트에 대해 LLM 분류
2. 구체적 부모 후보만 제공 (세기 제외)

---

## 7. 참고문헌

### 학술 논문
- [Novel Event Detection and Classification for Historical Texts](https://direct.mit.edu/coli/article/45/2/229/1630/Novel-Event-Detection-and-Classification-for) (MIT Press, 2019)
- [Towards a Complete Event Type Taxonomy](https://dl.acm.org/doi/10.1145/2740908.2742005) (WWW 2015)
- [A Comparison of ACE, ERE, TAC-KBP, and FrameNet](https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/acl2014-comparison-events-relations.pdf)
- [Design and use of the Simple Event Model (SEM)](https://www.sciencedirect.com/science/article/abs/pii/S1570826811000199)
- [Extraction of Historical Events from Wikipedia](https://arxiv.org/pdf/1205.4138)

### 온톨로지/표준
- [CIDOC-CRM Official](https://cidoc-crm.org/)
- [LODE Ontology](https://linkedevents.org/ontology/)
- [SEM Ontology](https://semanticweb.cs.vu.nl/2009/11/sem/)
- [DBpedia Ontology](https://www.dbpedia.org/resources/ontology/)

### 백과사전/위키
- [Longue durée - Wikipedia](https://en.wikipedia.org/wiki/Longue_dur%C3%A9e)
- [Periodization - Wikipedia](https://en.wikipedia.org/wiki/Periodization)
- [Wikipedia:Categorization](https://en.wikipedia.org/wiki/Wikipedia:Categorization)
- [Wikidata:Item classification](https://www.wikidata.org/wiki/Wikidata:Item_classification)
- [나무위키:분류](https://namu.wiki/w/%EB%82%98%EB%AC%B4%EC%9C%84%ED%82%A4:%EB%B6%84%EB%A5%98)

### 추가 자료
- [Taxonomies for Big History](https://jasonmkelly.com/jason-m-kelly/2015/09/14/taxonomies-for-big-history/)
- [Evolution of Wikipedia's Category Structure](https://www.researchgate.net/publication/221668608_Evolution_of_Wikipedia's_Category_Structure)

---

*작성일: 2026-01-31*
*CHALDEAS Project*
