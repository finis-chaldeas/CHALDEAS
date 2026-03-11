# FGO 서번트 ↔ 인물 링킹 — 연구 기획서

**생성일:** 2026-03-10
**목표:** FGO 서번트 → persons 테이블 매칭을 신뢰할 수 있는 수준으로 끌어올리기
**원칙:** DB 직접 수정 없음. YAML/JSON 구조로 출력 → 카드 시스템 DB 개편 시 일괄 반영

---

## 현황 요약

| 항목 | 수치 |
|------|------|
| 전체 서번트 | 449 |
| 링크됨 (person_id IS NOT NULL) | 389 (87%) |
| 미링크 | 60 (대부분 Fate 오리지널) |
| 배치 삽입 인물 (ID 14610600-14611000) | 142명 (certainty + 추정 연대 포함) |
| **오매칭 (확인된 틀린 링크)** | **~21건** |
| **미등재 인물 (DB에 없음)** | **~12명** |

### 핵심 발견

1. **389/449(87%)가 이미 링크됨** — `person_gaps.md`의 82명 분석은 과거 시점 기준
2. **142명 배치 삽입** (14610628-14610766) 대부분 정확하지만 일부 오매칭 존재
3. **비배치 링크에서 ~17건의 오매칭** — 동명이인/잘못된 자동 매칭
4. **배치 내 ~4건의 오매칭** — 서번트→배치 인물 연결 실수

---

## Phase A: 오매칭 수정 (21건)

### A-1. 비배치 오매칭 (17건)

동명이인 또는 완전히 다른 인물이 연결된 케이스.

| 서번트 | 잘못 연결된 인물 | person_id | 올바른 인물 | 조치 |
|--------|-----------------|-----------|-------------|------|
| Queen Medb | Andrei Zhdanov (1896) | 1631921 | Medb (아일랜드 신화 여왕) | 배치에 없음 → 신규 |
| Medb (Saber) | Andrei Zhdanov | 1631921 | 같은 Medb | 같이 수정 |
| Arash | Arash (1977, 현대인) | 12997894 | Ārash (페르시아 신화 궁수) | 배치에 없음 → 신규 |
| Geronimo | Thomas Gravesen (1976) | 13000183 | Geronimo (아파치 지도자, 1829-1909) | DB에 있을 수 있음 → 조회 |
| Ivan the Terrible | Ivan the Terrible (1911) | 11419598 | Ivan IV (1530-1584) | DB에 있을 수 있음 → 조회 |
| Hektor | Saadi (1210, 페르시아 시인) | 6502419 | Hector of Troy (트로이 왕자) | 배치에 없음 → 신규 |
| Don Quixote | Damiano Damiani (1922) | 8118577 | Don Quixote (소설 속 인물) | 배치에 없음 → 신규 |
| Edmond Dantes | Luis Enrique (1962) | 8129544 | Edmond Dantes (소설 속 인물) | 배치에 없음 → 신규 |
| Scheherazade | Agnes Varda (1928) | 9749685 | Scheherazade (1001야화 화자) | 배치에 없음 → 신규 |
| Sakata Kintoki | Felix Manalo (1886) | 6571295 | Sakata Kintoki (일본 전설) | 배치에 없음 → 신규 |
| Morgan | Morgan (1972, 현대인) | 4980550 | Morgan le Fay (아서왕 전설) | 배치에 없음 → 신규 |
| Nemo | Vladimir Vernadsky (1863) | 4884081 | Captain Nemo / Prince Dakkar | 배치에 없음 → 신규 |
| Percival | Percival (2000, 현대인) | 13029845 | Percival (원탁 기사) | 배치에 없음 → 신규 |
| William Tell | William Tell (1980) | 6663324 | William Tell (스위스 전설) | 배치에 없음 → 신규 |
| Astraea | C.S. Peirce (1839) | 8125368 | Astraea (그리스 여신) | 배치에 없음 → 신규 |
| Lady Avalon | Jennifer Granholm (1959) | 12997820 | Lady of Avalon (아서왕 전설) | 배치에 없음 → 신규 |
| James Moriarty (Ruler) | Laure Manaudou (1986) | 3250360 | Moriarty (이미 14610725에 있음) | 배치 연결 |

**참고:** Manannan mac Lir → Roger Casement은 FGO에서 바제트의 육체에 빙의한 설정이므로 의도적 매칭일 수 있음. 확인 필요.

### A-2. 배치 내 오매칭 (4건)

배치 삽입 인물(14610xxx) 자체는 맞지만 서번트 → 인물 연결이 틀린 케이스.

| 서번트 | 잘못 연결된 배치 인물 | 올바른 인물 | 조치 |
|--------|----------------------|-------------|------|
| Odysseus | Heracles (14610678) | Odysseus → 신규 필요 | 배치에 오디세우스 없음 |
| Paris | Europa (14610665) | Paris of Troy → 신규 필요 | 배치에 파리스 없음 |
| Valkyrie | Quetzalcoatl (14610728) | Valkyrie (북유럽 신화) → 신규 필요 | 배치에 발키리 없음 |
| Merlin | King Arthur (14610696) | Merlin (아서왕 전설 마법사) → 신규 필요 | 배치에 멀린 없음 |

### A-3. Mordred — 날짜 보충 필요

Mordred (3252242)은 올바른 인물이지만 `birth_year`, `death_year`, `certainty` 미입력 상태.
→ legendary, 추정 ~500-537 AD (아서왕 말기)

---

## Phase B: 미등재 인물 신규 생성 (~20명)

Phase A에서 올바른 인물이 DB에 없는 경우 + `person_gaps.md` Section 2에서 배치에도 없는 인물.

### B-1. Phase A에서 파생된 신규 인물 (15명)

| 인물명 | 분류 | 추정 시기 | 연구 난이도 |
|--------|------|-----------|-------------|
| Medb (Queen Medb) | mythological | 기원전 1세기~1세기 | 중 |
| Arash (Ārash-e Kamāngīr) | mythological | 기원전 2000~1000 | 중 |
| Hector of Troy | mythological | 기원전 1250~1180 | 하 |
| Odysseus | mythological | 기원전 1250~1180 | 하 |
| Paris of Troy | mythological | 기원전 1250~1180 | 하 |
| Merlin | legendary | 5~6세기 | 중 |
| Morgan le Fay | legendary | 5~6세기 | 중 |
| Percival (Knight) | legendary | 12~13세기 (문헌) | 중 |
| Valkyrie | mythological | 8~11세기 (문헌) | 중 |
| Astraea | mythological | 기원전 800~500 | 하 |
| Captain Nemo / Dakkar | fictional | 1870 (소설) | 하 |
| Edmond Dantes | fictional | 1844 (소설) | 하 |
| Don Quixote | fictional | 1605 (소설) | 하 |
| Scheherazade | legendary | 8~9세기 (문헌) | 중 |
| William Tell | legendary | 14세기 | 중 |

### B-2. DB 조회 결과 (확인 완료)

| 서번트 | 올바른 인물 | DB 존재 여부 | 조치 |
|--------|------------|-------------|------|
| Geronimo | Geronimo (Apache, 1829-1909) | **없음** (Sarah Geronimo만 있음) | 신규 생성 |
| Ivan the Terrible | Ivan IV (1530-1584) | **있음** (id=1623709, imp=70) | 링크 수정만 |
| Sakata Kintoki | 坂田金時 (일본 전설) | **없음** | 신규 생성 |
| Lady Avalon | Lady of the Lake / Vivian | **없음** | 신규 생성 |
| Chacha | Yodo-dono (1569) | ✅ 이미 수정됨 (id=12998193) | 완료 |

### B-3. person_gaps.md Section 3 분류 작업

112명 미분류 서번트 중 이미 389명이 링크된 상태이므로, **실제 미분류 잔여분**을 재확인해야 함.
현재 미링크 60명 중 대부분이 Fate 오리지널이므로 실질적으로 추가 필요한 인물은 거의 없을 수 있음.

---

## Phase C: 학술 논문 기반 연대 검증

### 대상

142명 배치 삽입 인물 + 신규 ~15명의 `birth_year`, `death_year` 검증.

### 검증 기준

| certainty 분류 | 검증 방법 | 예시 |
|---------------|-----------|------|
| `fact` | 사서/연대기 기반 정확한 연도 | Miyamoto Musashi: 1584-1645 |
| `probable` | 사서에 언급되나 정확한 연도 불확실 | Fuma Kotaro: 1565?-1603 |
| `legendary` | 문헌 최초 등장 시기 또는 전설 내 추정 시기 | King Arthur: 470-537 (사서 기반 추정) |
| `mythological` | 신화 텍스트의 문헌학적 연대 또는 신화 내 시대 설정 | Gilgamesh: -2700~-2600 (역사적 왕조 기반) |
| `fictional` | 작품 출판 연도 또는 작품 내 시대 설정 | Sherlock Holmes: 1887-1927 (작품 연대) |

### 검증 워크플로우

```
1. Semantic Scholar API로 인물명 + 관련 키워드 검색
   예: "Gilgamesh historical king Uruk dating"
   예: "King Arthur historicity archaeological evidence"
   예: "Trojan War dating Bronze Age"

2. 상위 논문 5편의 abstract에서 연대 정보 추출

3. 기존 배치 데이터와 비교:
   - 일치 → 검증 완료 (verified: true)
   - 불일치 → 학술적 근거가 더 강한 쪽 채택
   - 범위 차이 → 더 넓은/좁은 범위 결정 (논문 근거)

4. 출력: 검증 결과 YAML
```

### 검증 우선순위

**Tier 1 — 서번트 칼럼 대상 (30명, Phase 1과 연동)**
역사 인물 20 + 신화/전설 10명의 연대가 가장 중요.

| 그룹 | 인물 | 현재 상태 |
|------|------|-----------|
| 메소포타미아 | Gilgamesh, Enkidu, Ishtar, Ereshkigal | 배치에 있음, 검증 필요 |
| 그리스 신화 | Achilles, Heracles, Medea, Jason, Odysseus, Hector, Paris | 일부 배치, 일부 미등재 |
| 켈트 신화 | Cu Chulainn, Scathach, Fionn, Medb, Diarmuid | 대부분 배치, Medb 미등재 |
| 아서왕 전설 | Arthur, Mordred, Merlin, Morgan, Lancelot, Gawain, Percival | 일부 배치, 일부 미등재 |
| 인도 서사시 | Karna, Arjuna, Rama | 배치에 있음 |
| 북유럽 신화 | Sigurd, Brynhildr, Valkyrie | 일부 배치 |

**Tier 2 — 특이점/LB 등장 인물**
Phase 2 아티클에 필요한 인물들의 연대 정확성.

**Tier 3 — 나머지 배치 인물**
Phase 3 시프트 연동 시 활용.

### 비용 추정

- Semantic Scholar API: 무료 (rate limit 100/5min)
- GPT로 논문 abstract 분석: ~$0 (Ollama 로컬 가능) 또는 gpt-5.1-chat-latest ~$2-3
- 총 비용: **$0~3**

---

## Phase D: 출력 형식

### D-1. 수정 사항 YAML

```yaml
# fgo_person_corrections.yaml
corrections:
  - servant_name: "Queen Medb"
    servant_class: "rider"
    current_person_id: 1631921          # Andrei Zhdanov (WRONG)
    correct_person_id: null             # 신규 생성 필요
    correct_person_name: "Medb"
    action: "create_and_link"

  - servant_name: "Arash"
    servant_class: "archer"
    current_person_id: 12997894         # Arash (1977, WRONG)
    correct_person_id: null
    correct_person_name: "Ārash-e Kamāngīr"
    action: "create_and_link"

  # ... (21건)
```

### D-2. 신규 인물 YAML

```yaml
# fgo_new_persons.yaml
persons:
  - name: "Medb"
    name_ko: "메이브"
    name_ja: "メイヴ"
    certainty: "mythological"
    birth_year: -100
    death_year: 100
    date_source: "Ulster Cycle dating based on..."
    date_papers:
      - doi: "..."
        title: "..."
        relevant_excerpt: "..."
    role: "queen"
    category: "mythology"
    related_servants:
      - "Queen Medb (rider)"
      - "Medb (Saber)"

  - name: "Hector of Troy"
    name_ko: "헥토르"
    name_ja: "ヘクトール"
    certainty: "mythological"
    birth_year: -1250
    death_year: -1180
    date_source: "Trojan War conventional dating"
    date_papers:
      - doi: "..."
      # ...
```

### D-3. 검증 결과 YAML

```yaml
# fgo_date_verification.yaml
verified_persons:
  - person_id: 14610675
    name: "Gilgamesh"
    current_dates: { birth: -2700, death: -2600 }
    verified_dates: { birth: -2700, death: -2600 }
    status: "confirmed"
    papers:
      - doi: "10.xxxx/..."
        title: "..."
        relevant_finding: "..."

  - person_id: 14610696
    name: "King Arthur"
    current_dates: { birth: 470, death: 537 }
    verified_dates: { birth: 470, death: 537 }
    status: "confirmed_with_uncertainty"
    notes: "Based on Annales Cambriae, Battle of Camlann c.537"
    papers:
      - doi: "..."
```

---

## 실행 순서

```
Phase A (30분)     → Phase B (1시간)     → Phase C (2-3시간)    → Phase D (30분)
오매칭 21건 정리     DB 조회 + 신규 목록    논문 검색 + 연대 검증    YAML 출력
```

### Phase A 상세 절차

1. 21건 오매칭 목록 확정 (위 표 기준)
2. 각 케이스별 올바른 person_id 조회 (DB에 있는지 확인)
3. 없으면 Phase B 대상으로 이관
4. `fgo_person_corrections.yaml` 출력

### Phase B 상세 절차

1. DB 조회로 올바른 인물 존재 여부 확인 (Geronimo, Ivan IV 등)
2. 존재하면 → corrections에 추가 (link 수정만)
3. 없으면 → new_persons에 추가
4. 각 신규 인물의 기본 정보 채움 (이름 3개국어, 추정 certainty)
5. `fgo_new_persons.yaml` 출력

### Phase C 상세 절차

1. Tier 1 인물 (30명) 우선 처리
2. Semantic Scholar API로 인물별 논문 5편 검색
3. 논문 abstract 분석 → 연대 정보 추출
4. 기존 데이터와 비교 → 검증/수정
5. `fgo_date_verification.yaml` 출력

### Phase D 상세 절차

1. Phase A-C 결과 통합
2. 최종 YAML 3개 파일 출력
3. `person_gaps.md` 업데이트 (현재 기준으로 재작성)

---

## 참고: 현재 person_gaps.md의 문제점

`person_gaps.md`는 이전 시점(링크 82건) 기준으로 작성되어 현재와 크게 괴리됨:

1. **Section 1 (즉시 링킹 38명)**: 이미 대부분 링크됨. 남은 것은 오매칭 수정 대상.
   - Martha → Martha Graham (오매칭) → 이미 배치 14610733(Martha of Bethany)으로 수정됨 ✅
   - Sieg, Amor, Georgios 등 → 이미 배치 인물로 연결됨 ✅
   - Medb → Andrei Zhdanov ❌ → 여전히 오매칭

2. **Section 2 (미등재 97명)**: 대부분 배치 삽입으로 이미 DB에 있음.
   - 40명 신화 → ~35명 이미 배치에 존재
   - 35명 전설 → ~30명 이미 배치에 존재
   - 14명 역사 → ~10명 이미 배치/DB에 존재
   - 실제 미등재 잔여: ~12명

3. **Section 3 (미분류 112명)**: 현재 미링크 60명 대부분 Fate 오리지널.
   실질적으로 분류+링크 필요한 인물은 거의 없음.

→ **결론: `person_gaps.md`는 Phase D 완료 후 전면 재작성 필요**

---

## 카드 시스템과의 연동

이 작업의 출력물(YAML)은 카드 시스템 DB 개편 시 다음과 같이 활용:

1. `fgo_person_corrections.yaml` → `fgo_servants.person_id` UPDATE 쿼리 생성
2. `fgo_new_persons.yaml` → `persons` INSERT + `fgo_servants.person_id` UPDATE
3. `fgo_date_verification.yaml` → `persons.birth_year/death_year` UPDATE (변경분만)
4. 신규 인물의 `certainty` 필드 → Person Card에서 "신화적 인물" / "전설적 인물" 표시에 활용
5. `date_papers` → Person Card "학술 근거" 섹션에 인용
