# 왜 이렇게 만들었는가 — 설계 결정의 배경

이 문서는 CHALDEAS 백엔드의 주요 설계 결정과 그 이유를 설명한다.
프론트엔드 개발자가 "왜 이렇게 되어 있지?"라고 물었을 때, 이 문서가 답한다.

---

## 1. Node + Detail 패턴

### 결정
Person, Event, Location 모두 **슬림 노드 + Detail 테이블**로 분리되어 있다.

- `persons` (18컬럼) + `person_details` (19컬럼)
- `events` (21컬럼) + `event_details` (18컬럼)
- `locations` (12컬럼) + `location_details` (8컬럼)

### 왜?
**90%의 쿼리는 이름+날짜만 필요하고, 10%만 biography/description이 필요하다.**

구체적 문제:
- Feed API가 28,000 이벤트를 반환할 때 매번 description(TEXT)을 JOIN하면 느리다
- 글로브에 마커를 찍을 때 필요한 건 title, date, location, importance뿐이다
- biography/description은 사용자가 클릭해서 상세를 볼 때만 필요하다

### 프론트엔드 영향
- **목록/마커 표시**: 노드 테이블만 사용 (가볍다)
- **상세 패널**: `details` 필드를 lazy-load (필요할 때만)
- API 응답에 `details` 객체가 중첩되어 온다 — 새 코드는 이것을 사용

---

## 2. Geography ≠ Politics (locations vs territories)

### 결정
장소(locations)와 영토(territories)가 완전히 분리되어 있다.

- `locations`: 불변 좌표 (latitude, longitude). "로마"는 항상 41.9°N, 12.5°E
- `territories`: 정치 영역 + 시간 범위. "로마 제국"은 -27~476년
- `territory_locations`: 어떤 장소가 어떤 시기에 어떤 영역에 속했는가

### 왜?
**좌표는 영원하지만, 그 위의 정치는 변한다.**

- 이스탄불의 좌표는 BCE 667부터 2026년까지 같다
- 하지만 비잔티움 → 콘스탄티노폴리스 → 이스탄불로 이름이 바뀌었고
- 그리스 식민지 → 로마 → 비잔틴 → 라틴 → 비잔틴 → 오스만 → 터키로 소속이 바뀌었다

이것을 하나의 테이블로 표현하면 시간 변화를 추적할 수 없다.

### 프론트엔드 영향
- **글로브 마커**: `locations.latitude/longitude` — 항상 같은 자리
- **영토 오버레이**: `territory_locations.valid_from/valid_until` — 시간에 따라 변화
- **장소 이름**: `location_names.valid_from/valid_until` — 시간에 따라 변화
- 타임라인을 움직이면 마커 위치는 그대로이지만 이름과 영토 색이 바뀌어야 한다

---

## 3. 시간-가변 이름 (location_names, person_names)

### 결정
장소와 인물의 이름이 별도 테이블에, 시간 범위(valid_from/valid_until)와 함께 저장된다.

```
Constantinople → location_names:
  Byzantium      (valid_from=-667, valid_until=330)
  Constantinople (valid_from=330,  valid_until=1930)
  Istanbul       (valid_from=1930, valid_until=NULL)
```

### 왜?
**시간은 필터가 아니라 차원이다.**

시간을 움직이면 세계의 상태가 변해야 한다. "지금 이 시대에 이 장소의 이름은 무엇인가?"라는 질문에 정확하게 답하려면, 이름 자체에 시간 범위가 필요하다.

이것이 `location_names`, `person_names`, `territory_locations` 모두에 `valid_from`/`valid_until` 패턴이 반복되는 이유다.

### 프론트엔드 영향
- 타임라인을 200 CE로 놓으면 → "Constantinople"
- 타임라인을 200 BCE로 놓으면 → "Byzantium"
- 현재 연도에 맞는 이름을 찾는 로직이 프론트엔드에 필요하다
- `WHERE valid_from <= :year AND (valid_until IS NULL OR valid_until >= :year)`

---

## 4. Braudel의 시간 스케일

### 결정
모든 이벤트에 `temporal_scale` 컬럼이 있다:
- `evenementielle`: 단기 (일~년). 전투, 조약, 암살
- `conjuncture`: 중기 (수십 년). 전쟁, 왕조, 혁명
- `longue_duree`: 장기 (수백 년). 문명, 기후, 종교

### 왜?
**줌 레벨과 시간 스케일이 1:1로 매핑된다.**

| 줌 | temporal_scale | 보이는 것 |
|----|---------------|----------|
| COSMIC | longue_duree | 문명의 흥망 |
| CONTINENTAL | conjuncture | 전쟁과 운동 |
| REGIONAL | evenementielle | 개별 전투와 사건 |
| LOCAL | evenementielle | 사건의 하루하루 |

멀리서 보면 큰 흐름만 보이고, 가까이 가면 개별 사건이 보인다. 이것이 "줌 = 서사의 해상도"를 DB 레벨에서 지원하는 방법이다.

### 프론트엔드 영향
- 줌 레벨이 변하면 `temporal_scale` 필터가 달라져야 한다
- COSMIC에서는 longue_duree 이벤트만 쿼리
- REGIONAL에서는 모든 스케일의 이벤트를 쿼리
- 같은 시간 범위라도 줌에 따라 다른 마커가 보인다

---

## 5. AI 생성 서사 계층

### 결정
서사(narrative) 데이터가 3개 레벨로 구분된다:

| 레벨 | 테이블 | 단위 | 길이 |
|------|--------|------|------|
| Entity | `entity_narratives` | 개별 사건/인물 | 100-300단어 |
| Period | `period_narratives` | 50년 단위 × 6개 지역 | 200-500단어 |
| History | `histories` | 다중 엔티티 에세이 | A4 1페이지 |

### 왜?
**서사가 UI를 대체한다.** 메타데이터 나열이 아니라 이야기 텍스트가 먼저 보여야 한다.

- `entity_narratives`: 마커를 클릭하면 나오는 이야기. 원인, 결과, 의의가 자연어로 설명된다.
- `period_narratives`: 타임라인에서 시대를 클릭하면 나오는 시대 개요. 지역별로 다른 관점.
- `histories`: 여러 엔티티를 엮는 에세이. "알렉산더의 정복이 헬레니즘 세계를 만들다" 같은 글.

### 프론트엔드 영향
- **이벤트 카드**: entity_narrative를 description보다 우선 표시
- **시대 브리핑**: period_narrative를 WorldBriefing/PeriodDrawer에 표시
- **히스토리 탭**: histories를 읽을거리로 제공
- 서사가 있으면 서사를, 없으면 description을, 둘 다 없으면 메타데이터만 표시

---

## 6. Importance 스코어링

### 결정
이벤트와 인물 모두에 importance 점수가 있다:
- `events.importance`: 1-5 스케일
- `persons.importance_score`: 1-100 스케일 (rubric 기반 AI 채점)
- `person_details.category_id` + domain weight로 보정

### 왜?
**모든 사건이 동등하지 않다. 줌 레벨에 따라 보여줄 것을 결정해야 한다.**

- COSMIC에서는 importance 5인 이벤트만 보인다 (문명 수준의 사건)
- REGIONAL에서는 importance 2 이상이 보인다 (지역 전투까지)
- LOCAL에서는 모든 이벤트가 보인다

인물도 마찬가지:
- 멀리서는 알렉산더만 보인다 (importance_score ≥ 80)
- 가까이 가면 부관 장군들도 보인다 (importance_score ≥ 40)
- 더 가까이 가면 모든 인물이 보인다

### 프론트엔드 영향
- 줌 레벨에 따라 `importance_min` 파라미터를 조절해야 한다
- 마커 크기를 importance에 비례하게 표시한다
- 인물 아이콘도 importance_score에 따라 필터링/크기 조절

---

## 7. Certainty 레벨

### 결정
이벤트, 인물 모두에 `certainty` 컬럼이 있다:
- `fact`: 역사적 사실 (테르모필레 전투)
- `probable`: 거의 확실하지만 논쟁 가능 (소크라테스의 정확한 출생년)
- `legendary`: 전설 (트로이 전쟁)
- `mythological`: 신화 (길가메시)

### 왜?
**신화에서 역사로의 다리.**

- 길가메시는 mythological이지만, 우루크는 fact
- 트로이 전쟁은 legendary이지만, 트로이 유적은 fact
- FGO 서번트의 원본 캐릭터 중 상당수가 legendary/mythological

CHALDEAS는 역사만 다루는 것이 아니다. 사람들이 **아는 이름**에서 시작해서 **실제 역사**로 이어지게 한다. 그 다리가 certainty 레벨이다.

### 프론트엔드 영향
- certainty에 따른 시각적 구분 (fact=실선, legendary=점선, mythological=반투명)
- 카드에 certainty 배지 표시
- 필터로 "fact만 보기" 옵션 제공 가능
- FGO 연동 시 mythological 인물도 자연스럽게 포함
