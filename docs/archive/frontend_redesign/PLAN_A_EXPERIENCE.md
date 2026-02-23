# Plan A: 유저 경험 기획서 — "지구본이 곧 UI"

## 본질

유저는 **타임머신의 관측자**다. 지구본이 창문이고, 줌이 해상도다.
멀리서 보면 시대가 보이고, 가까이 가면 사람이 보인다.
사이드바는 없다. 지구본 위에 모든 것이 떠있다.

---

## 첫 방문: 착륙

화면 전체가 지구본이다. 아무것도 없다. 지구본만 천천히 돈다.

가운데 두 줄:
```
C H A L D E A S
[시작하기]
```

시작하기를 누르면 지구본이 지중해로 날아간다. 480 BCE.
마커들이 하나둘 떠오른다. 아래쪽에 타임라인 바가 스르륵 나타난다.

이게 전부다. 메뉴 없음. 탭 없음. 버튼 없음.

---

## 줌 레벨별 경험: 핵심

### COSMIC (가장 멀리)
지구 전체가 보인다.

**보이는 것:**
- 대륙별로 색이 다른 큰 원 2~3개 (이 시대에 문명이 있는 곳)
- 각 원 위에 시대 이름: "Classical Greece", "Warring States", "Maurya Empire"
- 원의 크기 = 이 시대 이벤트 밀도
- 원끼리 연결선 = 문명 간 교류 (실크로드, 해상 무역)

**느낌:** "아, 이 시대에 세계는 이렇게 생겼구나"

**클릭하면:** 해당 문명권으로 줌인 (-> CONTINENTAL)

**타임라인 바:** 시대 이름만 보임 (Ancient / Classical / Medieval / ...)

---

### CONTINENTAL (대륙 수준)
지중해 전체가 보인다.

**보이는 것:**
- 그리스, 페르시아, 이집트 지역에 마커 클러스터
- 클러스터 위에 숫자가 아니라 **이름**: "Greco-Persian Wars", "Rise of Athens"
- 영토 오버레이: 페르시아 제국 영역이 반투명 빨간색으로 깔림, 그리스 도시국가들이 파란 점으로 흩어져있음
- 시대를 움직이면 영토가 줄었다 늘었다 함

**느낌:** "이 지역에서 이 시대에 이런 일들이 일어났구나. 페르시아가 이렇게 컸어?"

**사이드에 뜨는 것 (Context Drawer):**
```
NOW OBSERVING
Mediterranean · 480 BCE

"페르시아 전쟁의 절정기. 크세르크세스 1세가
100만 대군을 이끌고 그리스를 침공한다."

주요 사건:
  ├─ Battle of Thermopylae (480 BCE)
  ├─ Battle of Salamis (480 BCE)
  └─ Battle of Plataea (479 BCE)

주요 인물:
  Leonidas I · Xerxes I · Themistocles
```

이건 자동으로 뜨는 게 아니다. **지구본에 뜬 클러스터 이름을 클릭하면** 왼쪽에서 스르륵 나온다.

**타임라인 바:** 50년 단위 마디가 보임, 각 마디에 이벤트 밀도 히트맵

---

### REGIONAL (지역 수준)
그리스 본토가 화면을 채운다.

**보이는 것:**
- 개별 이벤트 마커가 보인다 (클러스터 해제)
- 각 마커 옆에 짧은 이름: "Thermopylae", "Salamis"
- 마커 크기 = importance
- 마커 색상 = 카테고리 (전투=빨강, 정치=파랑, 문화=노랑)
- 마커 사이에 **화살표**: Thermopylae -> Salamis -> Plataea (인과관계)
- 인물 아이콘이 마커 위에 떠있음: 레오니다스 아이콘이 Thermopylae에, 테미스토클레스가 Salamis에

**느낌:** "여기서 이 순서로 전투가 벌어졌구나. 이 사람이 여기 있었구나."

**마커 클릭하면 (오른쪽 Detail Slide):**
```
Battle of Thermopylae
480 BCE · Thermopylae, Greece

레오니다스 1세가 300명의 스파르타 병사와 함께
크세르크세스의 대군을 3일간 저지했다.

원인 ← Battle of Marathon (490 BCE)
결과 → Battle of Salamis (480 BCE)

참여 인물:
  ⚔️ Leonidas I (지휘관)
  🎯 Xerxes I (침략자)

  Leonidas I의 다른 사건들:
  · 490 BCE  Ascension as King
  · 480 BCE  March to Thermopylae
  · 480 BCE  Battle of Thermopylae ← 지금 여기
```

**인물 아이콘 클릭하면:**
```
Leonidas I
스파르타 왕 · 540 BCE — 480 BCE

[생애 플로우를 지도 위에 표시]
  540 BCE  Sparta (출생)
    ↓
  490 BCE  Sparta (왕위 계승)
    ↓
  480 BCE  Thermopylae (최후)

관계:
  🔵 Gorgo (아내)
  🔴 Xerxes I (적)
  🟢 Themistocles (동맹)
```

---

### LOCAL (가장 가까이)
Thermopylae 협곡이 화면에 가득 찬다.

**보이는 것:**
- 지형이 자세히 보인다
- 하위 이벤트 마커: "Day 1: Initial Defense", "Day 2: Ephialtes' Betrayal", "Day 3: Last Stand"
- 마커를 시간순으로 연결하는 점선

**느낌:** "이 좁은 협곡에서 3일 동안 이런 일이 벌어졌구나"

**타임라인 바:** 일 단위까지 내려감

---

## 시간을 움직이면

타임라인 바를 480 BCE에서 400 BCE로 드래그한다.

**지구본에서 벌어지는 일:**
- 페르시아 영토 오버레이가 서서히 줄어든다
- 아테네 주변에 새 마커 떠오름: "Peloponnesian War", "Age of Pericles"
- 기존 마커(Thermopylae)가 희미해진다
- 새 인물 아이콘 등장: Socrates, Pericles

**Context Drawer가 자동 업데이트:**
```
NOW OBSERVING
Greece · 400 BCE

"아테네의 황금기가 저물고, 펠로폰네소스 전쟁이
그리스 세계를 갈라놓는다."
```

---

## 글로브를 안 만지는 사람 (Reader Path)

하단 타임라인 바에서 시대 라벨("Classical")을 클릭한다.

왼쪽 Context Drawer가 열린다:
```
Classical Era (500 BCE — 323 BCE)

목차:
  By Region:
    ├─ Greece: Democracy & Philosophy
    ├─ Persia: Imperial Expansion
    ├─ India: Maurya Empire
    └─ China: Warring States

  By Theme:
    ├─ Military: The Great Battles
    ├─ Philosophy: Socrates → Plato → Aristotle
    └─ Politics: Democracy vs Empire

  Curated Tours:
    ├─ "Greco-Persian Wars" (7 steps)
    └─ "Alexander's Conquest" (12 steps)
```

아무 항목이나 클릭하면 → 글로브가 해당 위치로 날아감 + 해당 이벤트 Detail 열림.

---

## 핵심 차별점

1. **사이드바가 없다** — 모든 것이 지구본 위 또는 지구본에 반응하는 슬라이드
2. **줌 = 해상도** — 멀리 보면 문명, 가까이 보면 전투, 더 가까이 보면 전투의 하루하루
3. **영토가 숨 쉰다** — 타임라인 움직이면 제국이 커졌다 작아졌다
4. **인과관계가 보인다** — 마커 사이 화살표로 "왜?"와 "그래서?"가 시각적
5. **인물이 지도 위에 있다** — 데이터베이스가 아니라 "여기 이 사람이 있었다"

## 필요한 것

- 영토 폴리곤 데이터 (GeoJSON)
- event_relationships 데이터 채우기
- hierarchy_level / parent_event_id 데이터 채우기
- period narrative 89개 작성
- 새 API 3개 (territories, event_relationships, location_names)
- 새 컴포넌트 ~15개

## 리스크

- 영토 데이터가 없으면 빈 지구본
- hierarchy 데이터가 없으면 줌해도 달라지는 게 없음
- 작업량 최대, 기존 코드 대부분 재작성
