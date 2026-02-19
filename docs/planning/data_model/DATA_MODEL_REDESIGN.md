# CHALDEAS 데이터 모델 재설계 검토

## 1. 프로젝트 핵심 철학

> "모든 역사는 **누가(Person)** **어디서(Location)** **언제(Time)** **무엇을(Event)** 했는가로 결정된다."

### 4대 핵심 엔티티
```
Person   - 역사적 인물
Location - 장소
Time     - 시간 (연도, 시대)
Event    - 사건
```

### 프로젝트 목적
- 3D 글로브 인터페이스로 시간과 공간을 탐색
- BCE 3000년부터 현재까지의 역사 시각화
- 인물, 장소, 사건의 연결 관계 탐색

---

## 2. 현재 상태 (V0)

### 테이블 구조
```
persons    - 개인 인물
locations  - 단일 좌표 (latitude, longitude)
events     - 역사적 사건
```

### 문제점

#### A. Location 문제
| 문제 | 예시 |
|------|------|
| 점 좌표만 지원 | Italy 전체 = 로마 중심점 좌표? |
| 영역 표현 불가 | 지중해, 유럽 같은 넓은 지역 |
| 시대별 소속 변화 없음 | Alsace: 프랑스 → 독일 → 프랑스 |
| 시대별 명칭만 있음 | location_names 테이블 |

#### B. Person 문제
| 문제 | 예시 |
|------|------|
| 개인만 지원 | "로마군", "십자군" 같은 집단 표현 불가 |
| 집단 참여자 | 전쟁에 "로마"가 참전 - 이건 국가? 군대? |

#### C. Event-Location 연결
| 문제 | 현재 |
|------|------|
| 연결률 | 2.5%만 위치 연결됨 |
| Wikidata 임포트 버그 | location_qid 가져오지만 미사용 |

---

## 3. 핵심 질문

### Q1: Location은 무엇인가?

**현재 정의**: 좌표가 있는 지리적 위치

**실제 필요**:
- 점 (Point): 도시, 전장, 건물
- 영역 (Area): 국가, 지역, 바다
- 개념적 (Conceptual): "서양", "동방", "신대륙"

**시대별 변화**:
- 이름: 한양 → 경성 → 서울
- 소속: Alsace → France/Germany
- 영역: 국경선 변화

### Q2: Person 외에 "행위자"가 필요한가?

**현재 정의**: 개인 인물 (Hannibal, Napoleon)

**실제 필요**:
- 개인 (Person): Hannibal, Napoleon
- 집단 (Group): 로마군, 십자군, 바이킹
- 국가/조직 (Polity): 로마제국, 카르타고

**핵심 철학과의 관계**:
- "누가" = Person인가, Actor인가?
- Person은 개인에 한정하고 Group은 별도 개념?

### Q3: 시대별 변화를 어디까지 추적할 것인가?

**옵션 A: 단순 (현재)**
- location_names로 이름만 관리
- 소속 변화 없음

**옵션 B: 중간**
- 이름 + 소속 변화 추적
- places, actors 분리 유지

**옵션 C: 복잡**
- 모든 속성의 시대별 버전 관리
- 오버엔지니어링 위험

---

## 4. 제약 조건

### 유지해야 할 것
1. **4대 엔티티 분리**: Person, Location, Time, Event
2. **3D 글로브 시각화**: 좌표 기반 표시 필수
3. **Wikidata 호환**: QID 기반 연결

### 피해야 할 것
1. **오버엔지니어링**: 너무 복잡한 temporal 모델
2. **Actor/Place 통합**: 개념적으로 다른 것을 합치면 안 됨
3. **기존 데이터 손실**: 24만 인물, 1800 위치 마이그레이션 필요

---

## 5. 결정 필요 사항

### 5.1 Location 확장

**옵션 A: 기존 유지 + 타입 추가**
```sql
locations
  + location_type: point | area | conceptual
  + geometry: point | polygon | null
```

**옵션 B: 시대별 상태 추가**
```sql
location_states
  - location_id
  - valid_from, valid_until
  - name, belongs_to_id
```

### 5.2 집단/조직 처리

**옵션 A: persons 확장**
```sql
persons
  + person_type: individual | group | polity
```

**옵션 B: 별도 테이블**
```sql
groups (새 테이블)
  - id, name, group_type
  - founded_year, dissolved_year
```

**옵션 C: 무시**
- 집단은 이벤트 설명에만 포함
- DB 구조 변경 없음

---

## 6. 결정: Location = 점, Territory = 점 집합

### 핵심 아이디어

```
Location (점)
  - 모든 역사적 지점은 좌표를 가진 점
  - 너무 가까운 점은 동일 지점 취급 (500m 이내)
  - 또는 인근 2-3 지점의 중간값 = "근처"

Territory (영역)
  - 점들의 집합
  - 시기별로 어떤 점들이 포함되는지 정의
  - 국가, 제국, 지역 등
```

### 예시: 로마제국의 영토 변화

```
로마제국 (100 CE):
  점 집합: {Rome, Athens, Alexandria, Jerusalem, London, Lutetia, Carthage...}

로마제국 (400 CE):
  점 집합: {Rome, Constantinople, Alexandria, Antioch...}
  (Britain 상실, 동쪽 확장)
```

### 예시: Alsace의 소속 변화

```
Alsace (점: 48.5°N, 7.5°E)

1870년: France 영역에 포함
1871년: German Empire 영역에 포함
1918년: France 영역에 포함
```

### 스키마

```sql
-- 점 (기본 위치) - 기존 locations 유지
locations
  - id
  - name, name_ko
  - latitude, longitude  -- 항상 점
  - wikidata_id
  - canonical_id  -- 동일 지점 통합용

-- 점의 시대별 이름 - 기존 location_names 유지
location_names
  - location_id
  - name, name_ko
  - valid_from, valid_until

-- 영역 (점들의 집합) - 신규
territories
  - id
  - name, name_ko
  - territory_type: country | empire | region | sea | continent
  - wikidata_id

-- 영역-점 관계 (시기별) - 신규
territory_locations
  - territory_id
  - location_id
  - valid_from, valid_until  -- 이 시기에 이 점이 이 영역에 속함
```

### 장점

1. **Location 단순**: 항상 점, 좌표만 있으면 됨
2. **영역 표현 자연스러움**: 점들의 집합
3. **시대별 변화 추적**: territory_locations의 valid_from/until
4. **3D 글로브 친화적**: 점들을 연결하면 영역 표시 가능
5. **기존 데이터 호환**: locations 테이블 구조 유지

### Event와의 연결

```sql
-- 이벤트는 점(location) 또는 영역(territory)과 연결
event_locations
  - event_id
  - location_id  -- 구체적 장소 (전투 위치)

event_territories
  - event_id
  - territory_id  -- 넓은 영역 (전쟁 범위)
```

**예시:**
```
Battle of Thermopylae (480 BCE)
  → location: Thermopylae (점)
  → territories: Greece, Persia (참여 영역)

Second Punic War (218-201 BCE)
  → locations: Cannae, Zama, Saguntum... (주요 전투 지점)
  → territories: Roman Republic, Carthage (참여 영역)
```

---

## 7. 결정: Person = 개인, Group = 개인 집합

### 핵심 아이디어

```
Person (개인)
  - 역사적 인물 개개인
  - 기존 persons 테이블 유지

Group (집단)
  - 개인들의 집합
  - 군대, 종교단체, 민족, 정치조직 등
  - 구성원은 점진적으로 추가
```

### 패턴 통일

```
Location : Territory = Person : Group

Location (점)     →  Territory (점 집합, 시기별)
Person (개인)     →  Group (개인 집합, 시기별)
```

### 스키마

```sql
-- 개인 (기존 persons 유지)
persons
  - id, name, name_ko
  - birth_year, death_year
  - biography, wikidata_id

-- 집단 (신규)
groups
  - id
  - name, name_ko
  - group_type: military | religious | ethnic | political | state
  - founded_year, dissolved_year
  - parent_group_id  -- 상위 집단 (Roman Legion X → Roman Army)
  - wikidata_id

-- 집단-개인 관계 (점진적 추가)
group_members
  - group_id
  - person_id
  - valid_from, valid_until
  - role: leader | member | founder | commander
```

### 예시

```
Knights Templar (group, type: religious)
  - founded: 1119, dissolved: 1312
  - members:
    - Jacques de Molay (leader, 1292-1314)
    - Hugues de Payens (founder, 1119-1136)

Wehrmacht (group, type: military)
  - founded: 1935, dissolved: 1945
  - parent: Nazi Germany
  - members: (2차대전 참전자 정보가 나오면 점진적으로 추가)
    - Erwin Rommel (commander, 1939-1944)
    - ...
```

### Event 연결

```sql
-- 개인 참여
event_persons
  - event_id, person_id, role

-- 집단 참여
event_groups
  - event_id, group_id, role
```

**예시:**
```
Battle of Hattin (1187)
  - persons: Saladin, Guy of Lusignan, Balian of Ibelin
  - groups: Knights Templar, Knights Hospitaller, Ayyubid Dynasty

D-Day (1944)
  - persons: Eisenhower, Rommel, Montgomery
  - groups: US Army, Wehrmacht, British Army
```

### 데이터 축적 방식

1. Event 임포트 시 참여 집단(group) 생성
2. 인물 정보 발견 시 → persons에 추가 + group_members 연결
3. 점진적으로 구성원 정보 축적

---

## 8. 전체 모델 요약

### 4대 핵심 엔티티 (유지)

```
Person   - 개인 인물
Location - 점 좌표
Time     - 연도/시대
Event    - 사건
```

### 확장 엔티티 (신규)

```
Territory - Location들의 집합 (국가, 영역)
Group     - Person들의 집합 (집단, 조직)
```

### 관계 테이블

```
territory_locations - 영역에 속한 점 (시기별)
group_members       - 집단에 속한 개인 (시기별)

event_locations     - 이벤트 발생 장소 (점)
event_territories   - 이벤트 관련 영역
event_persons       - 이벤트 참여 개인
event_groups        - 이벤트 참여 집단
```

### 시각화

```
3D Globe:
  - Location (점) → 마커로 표시
  - Territory (점 집합) → 점들을 연결한 영역으로 표시
  - Event → 해당 위치에 타임라인으로 표시
```

---

## 9. 다음 단계

1. [x] Location 개념 결정: **점 + Territory(점 집합)**
2. [x] Person/Group 개념 결정: **개인 + Group(개인 집합)**
3. [ ] 상세 스키마 확정 (컬럼, 인덱스, 제약조건)
4. [ ] 마이그레이션 계획 (기존 데이터)
5. [ ] Wikidata 임포트 수정 (territory, group 추출)
6. [ ] API 설계

---

## 작성일: 2026-02-05
## 상태: 핵심 모델 결정 완료, 상세 설계 필요
