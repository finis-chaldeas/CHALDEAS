# 이 DB 구조가 존재하는 이유

## 원칙

DB의 모든 테이블은 유저가 지구본을 보면서 물을 수 있는 질문에 답하기 위해 존재한다.

테이블이 아무 질문에도 답하지 못하면, 그 테이블은 필요 없다.

---

## 핵심 엔티티: 역사의 네 기둥

### events — "여기서 무슨 일이 일어났는가?"

유저가 지구본에서 마커를 클릭하면 답해야 하는 질문.

| 컬럼 | 왜 존재하는가 |
|------|-------------|
| `title` / `title_ko` | 유저에게 보여줄 이름 |
| `date_start` / `date_end` | 시간축 위에 배치하기 위해. BCE는 음수 (-490 = 490 BCE) |
| `date_precision` | "480년"인지 "5세기"인지. 불확실한 역사에 거짓 정밀도를 부여하지 않기 위해 |
| `temporal_scale` | 브로델의 3단계. 줌 레벨에 따라 어떤 이벤트를 보여줄지 결정하는 핵심 |
| `importance` (1-5) | 같은 줌 레벨에서도 중요한 것을 크게, 덜 중요한 것을 작게 |
| `certainty` | fact/probable/legendary/mythological. 트로이 전쟁은 legendary, 테르모필레는 fact |
| `hierarchy_level` | 줌의 서사 해상도를 가능하게 하는 핵심. 1=문명, 2=전쟁, 3=전투, 4=전투의 하루 |
| `parent_event_id` | 전투 → 전쟁 → 시대. 줌아웃하면 부모로 클러스터링 |
| `is_aggregate` | 이 이벤트가 하위 이벤트를 포함하는지. 줌 레벨 전환의 트리거 |
| `primary_location_id` | 지구본 위 어디에 마커를 찍을지 |
| `category_id` | 마커 색상 결정. 전투=빨강, 정치=파랑, 문화=노랑 |
| `period_id` | 어느 시대에 속하는가. 시대별 탐색의 기반 |

### persons — "이 사람은 누구인가?"

유저가 인물 아이콘이나 카드를 클릭하면 답해야 하는 질문.

| 컬럼 | 왜 존재하는가 |
|------|-------------|
| `name` / `name_ko` | 유저에게 보여줄 이름 |
| `birth_year` / `death_year` | 이 사람이 시간축 위에 존재하는 범위. 타임라인 이동 시 보이거나 사라지게 |
| `floruit_start` / `floruit_end` | 생몰년 불명인 인물을 위한 활동기. 호메로스 같은 인물 |
| `birthplace_id` / `deathplace_id` | 인물의 공간적 앵커. 생애 플로우의 시작과 끝 |
| `role` | "왕", "철학자", "장군". 유저가 한눈에 이해하도록 |
| `domain` | science/philosophy/military/... 도메인별 필터링과 색상 구분 |
| `importance_score` | 줌 레벨에 따라 보여줄 인물 결정. 멀리서는 알렉산더만, 가까이서는 부관도 |
| `certainty` | 이 인물이 실존했는가. 아킬레우스는 mythological |

### locations — "이곳은 어떤 곳인가?"

유저가 지구본 위의 장소를 클릭하면 답해야 하는 질문.

| 컬럼 | 왜 존재하는가 |
|------|-------------|
| `name` / `name_ko` | 현재 시점의 대표 이름 |
| `latitude` / `longitude` | 지구본 위의 좌표. 불변. 좌표는 시간이 지나도 변하지 않는다 |
| `location_type` | point/natural/sea. 마커 표시 방식 결정 |
| `parent_location_id` | 물리적 계층. 경복궁 → 서울. 지리적 줌의 기반 |

**좌표는 불변이고, 이름과 소속은 시간에 따라 변한다.**
이것이 locations 테이블을 불변 좌표로만 유지하고,
이름은 `location_names`, 소속은 `territory_locations`로 분리한 이유다.

### sources — "이걸 어떻게 아는가?"

유저가 "이게 사실이야?"라고 의심하면 답해야 하는 질문.

| 컬럼 | 왜 존재하는가 |
|------|-------------|
| `name` / `author` | 누가 쓴 무슨 문서인가 |
| `type` | primary/secondary/digital_archive. 1차 사료인가 2차 해석인가 |
| `reliability` (1-5) | 이 출처를 얼마나 신뢰할 수 있는가 |
| `archive_type` | perseus/gutenberg/ctext/... 원본을 어디서 볼 수 있는가 |
| `original_year` | 이 문서가 언제 쓰여졌는가. 헤로도토스(~440 BCE)와 현대 학자의 차이 |

---

## 시간 변화 테이블: "시간이 바꾸는 것"

### location_names — "이 장소의 옛 이름은?"

```
location_id=42 (Istanbul의 좌표):
  Byzantium      (valid_from=-667, valid_until=330)
  Constantinople (valid_from=330,  valid_until=1930)
  Istanbul       (valid_from=1930, valid_until=NULL)
```

타임라인을 200 CE로 놓으면 → 이 좌표 위에 "Constantinople"이라고 뜬다.
타임라인을 200 BCE로 놓으면 → "Byzantium"이라고 뜬다.

### person_names — "이 사람의 다른 이름은?"

```
person_id=15 (Alexander):
  Alexandros    (language=gr, type=native)
  Alexander III (language=en, type=official)
  Iskander      (language=ar, type=alternate)
  알렉산드로스  (language=ko, type=official)
```

같은 사람이 문화권에 따라 다른 이름으로 불린다.

### territories — "이 땅은 누구 것이었나?"

```
territory: Roman Empire (founded=-27, dissolved=476)
territory: Byzantine Empire (founded=395, dissolved=1453)
territory: Ottoman Empire (founded=1299, dissolved=1922)
```

### territory_locations — "이 도시는 언제 어느 제국에 속했나?"

```
Constantinople → Roman Empire    (valid_from=330, valid_until=395)
Constantinople → Byzantine Empire (valid_from=395, valid_until=1204)
Constantinople → Latin Empire     (valid_from=1204, valid_until=1261)
Constantinople → Byzantine Empire (valid_from=1261, valid_until=1453)
Constantinople → Ottoman Empire   (valid_from=1453, valid_until=1922)
```

타임라인을 움직이면 영토 오버레이의 색이 바뀐다.
같은 도시가 다른 제국의 색으로 칠해진다.

---

## 연결 테이블: "어떻게 연결되는가"

### event_persons — "이 사건에 누가 참여했나?"

```
Battle of Thermopylae:
  Leonidas I  (role=commander)
  Xerxes I    (role=invader)
```

마커를 클릭하면 참여 인물이 보인다. 인물을 클릭하면 그 인물의 다른 사건이 보인다.

### event_relationships — "이 사건의 원인과 결과는?"

```
from: Marathon → to: Thermopylae (type=causes, certainty=certain)
from: Thermopylae → to: Salamis (type=enables, certainty=certain)
```

이벤트 카드에서 "왜?"와 "그래서?"를 보여준다.
지구본 위에서 화살표로 시각화한다.

### person_relationships — "이 사람들은 어떤 관계인가?"

```
Socrates → Plato    (type=teacher, strength=5)
Plato → Aristotle   (type=teacher, strength=5)
Aristotle → Alexander (type=teacher, strength=4)
Leonidas ↔ Gorgo    (type=family, bidirectional=1)
```

인물 카드에서 관계 네트워크를 보여준다.

### event_parents — "이 사건은 어떤 맥락에 속하는가?"

```
Joan of Arc's Execution:
  → Hundred Years' War (context=war, is_primary=true)
  → Medieval Inquisition (context=religion, is_primary=false)
```

하나의 사건이 여러 맥락에 속할 수 있다.
전쟁 맥락에서 보면 백년전쟁의 일부, 종교 맥락에서 보면 이단 심판의 일부.

### event_locations — "이 사건은 어디서 일어났나?"

```
Alexander's Conquest:
  Granicus (role=location)
  Issus (role=location)
  Gaugamela (role=location)
  Persepolis (role=destination)
```

하나의 이벤트가 여러 장소와 연결될 수 있다. 원정은 여러 도시를 거친다.

---

## 서사 테이블: "이야기를 들려줘"

### entity_narratives — "이 사건/인물의 이야기는?"

```
Battle of Thermopylae:
  narrative: "In August 480 BCE, King Leonidas I led 300 Spartans..."
  significance: "The delay allowed Athens to prepare its navy..."
  causes: ["Persian desire for revenge after Marathon", "Greek refusal to submit"]
  consequences: ["Battle of Salamis", "Greek unity against Persia"]
```

단순한 데이터가 아닌 **이야기**. 원인과 결과가 자연어로 설명된다.

### period_narratives — "이 시대는 어떤 시대인가?"

```
period: -500 ~ -451
  headline: "The Birth of Western Civilization"
  narrative: "In the 5th century BCE, the Greek world stood at a crossroads..."
  keywords: ["democracy", "philosophy", "Persian Wars"]
  defining_moment: "The Battle of Salamis, where Athens' navy saved Greece"
  region: "europe"
```

50년 단위로 세계의 상태를 요약한다. 타임라인 시대 라벨을 클릭하면 이것이 보인다.

---

## 모든 것은 유저 경험을 위해

```
유저: 지구본을 본다
  → locations (좌표)
  → location_names (시간에 맞는 이름)
  → territories (시간에 맞는 영토 오버레이)

유저: 마커를 누른다
  → events (사건 정보)
  → event_persons (참여 인물)
  → event_relationships (인과관계)
  → entity_narratives (이야기)

유저: 인물을 누른다
  → persons (인물 정보)
  → person_relationships (관계 네트워크)
  → person_names (다른 이름)
  → event_persons (참여 사건 → 스레드)

유저: 시간을 움직인다
  → events.date_start/date_end (마커 갱신)
  → persons.birth_year/death_year (인물 갱신)
  → location_names.valid_from/until (이름 갱신)
  → territory_locations.valid_from/until (영토 갱신)
  → period_narratives (시대 설명 갱신)

유저: 줌을 바꾼다
  → events.hierarchy_level (계층별 표시)
  → events.temporal_scale (시간 스케일별 필터)
  → persons.importance_score (중요도별 필터)
  → events.importance (중요도별 마커 크기)
```

**DB의 모든 컬럼은 유저 경험의 어딘가에 연결된다.**
연결되지 않는 컬럼은 존재할 이유가 없다.
