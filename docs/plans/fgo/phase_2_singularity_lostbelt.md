# Phase 2: 특이점/로스트벨트 — 스토리 흐름 기반 아티클

**선행 조건**: Phase 0 (서번트 링킹)
**비용**: ~$8.00 (gpt-5.2-chat-latest)
**예상 시간**: ~25분
**DB 반영**: No (YAML 생성만)

---

## 목표

기존 15개 (특이점 8 + 로스트벨트 7) 전면 리라이트.
**스토리 흐름을 따라가면서** 역사적 배경과 등장인물을 자연스럽게 소개하고,
각 장면에서 관련 히스토리 시프트로 링크.

핵심 원칙: **"FGO 스토리를 읽다가 자연스럽게 실제 역사로 빠진다"**

---

## 기존 구조 vs 새 구조

### ❌ 기존 (정적 5섹션)
```
1. 실제 역사 배경
2. 등장인물 역사/신화
3. FGO가 맞춘 것/바꾼 것
4. 스토리 요약
5. 글로브에서 탐험하기
```
→ 역사와 스토리가 분리됨. 읽는 사람이 왔다갔다 해야 함.

### ✅ 새 구조 (스토리 흐름 기반)
```
1. 역사적 배경 (이 시대/장소는 어떤 곳이었나)
   → 관련 aggregate 시프트 링크

2. 스토리 파트 1: [파트 제목]
   등장인물: [캐릭터들]
   → 각 인물의 실제 역사 소개 (인라인)
   → 관련 person_story 시프트 링크
   → FGO vs 역사 비교 (인라인)

3. 스토리 파트 2: [파트 제목]
   등장인물: [캐릭터들]
   → (같은 패턴)

4. 스토리 파트 N: ...

5. 이 이야기가 다루는 것들
   → 주요 테마/역사적 의의 종합
   → 전체 관련 시프트 목록
```

---

## 콘텐츠 구조 (YAML)

### 바빌로니아 예시 (3파트 스토리)

```yaml
slug: singularity-7
item_type: singularity

title: "Singularity VII: Babylonia — The Oldest City Fights Its Last Battle"
subtitle: "When Gilgamesh and Chaldea stood against the end of civilization"
description: "..."

year: -2655
location: "Uruk, Mesopotamia"
era: "Ancient Mesopotamia"

sections:
  # ── 역사적 배경 ──────────────────────────────
  - title: "The Real Uruk — World's First Megacity"
    section_type: historical_setting
    # 이 특이점이 배경으로 삼은 시대/장소의 실제 역사
    # 우루크 문명, 수메르, 메소포타미아 도시국가
    # DB events + 학술 논문 참조
    # 600-800 words
    content: "..."
    related_shifts:
      - slug: shift-mesopotamian-civilization  # aggregate
      - slug: shift-jewishbabylonian-war       # 기존 시프트

  # ── 스토리 파트 1 ────────────────────────────
  - title: "Rise of Uruk and the Divine Threat"
    section_type: story_part
    part_number: 1
    source: "summaries/by_chapter/babylonia/part_1.json"
    # 스토리 요약 (part_1.summary 기반)
    # 칼데아 도착 → 우루크 발견 → 세 여신 동맹 위협
    content: "..."

    characters_introduced:
      - name: "Gilgamesh"
        # 인라인 역사 소개: 실제 우루크의 왕, 길가메시 서사시
        # 본드 텍스트 인용 1개
        # FGO 해석 vs 실제 차이점
        history_note: "..."
        servant_id: 200300
        person_id: ...
        related_shift: shift-epic-of-gilgamesh  # person_story

      - name: "Enkidu"
        history_note: "..."
        servant_id: 200600
        related_shift: null  # 신화 인물, 별도 시프트 없음

      - name: "Mash Kyrielight"
        history_note: null  # FGO 오리지널, 역사 배경 없음

    key_dialogue: "先輩、見てください。あの城壁..."  # 핵심 대사 1개

  # ── 스토리 파트 2 ────────────────────────────
  - title: "The Three Goddess Alliance"
    section_type: story_part
    part_number: 2
    source: "summaries/by_chapter/babylonia/part_2.json"
    content: "..."

    characters_introduced:
      - name: "Ishtar"
        history_note: "메소포타미아 신화의 이난나/이슈타르..."
        servant_id: ...
        related_shift: null  # 신화 인물

      - name: "Ereshkigal"
        history_note: "..."

      - name: "Gorgon (Medusa)"
        history_note: "그리스 신화의 메두사..."
        related_shift: null

    key_dialogue: "..."

  # ── 스토리 파트 3 ────────────────────────────
  - title: "Tiamat's Awakening and the Last Stand"
    section_type: story_part
    part_number: 3
    source: "summaries/by_chapter/babylonia/part_3.json"
    content: "..."

    characters_introduced:
      - name: "Merlin"
        history_note: "아서왕 전설의 마법사 멀린..."
        related_shift: null  # 전설

      - name: "King Hassan"
        history_note: "하산이 사바의 '산의 노인'..."
        related_shift: shift-the-crusades  # 기존 aggregate

    key_dialogue: "..."

  # ── 종합: 이 이야기가 다루는 것들 ──────────────
  - title: "What This Story Is Really About"
    section_type: themes
    # 주요 테마: 문명의 시작, 인간 vs 신, 왕의 자격
    # FGO가 역사/신화에서 가져온 것 vs 창작한 것
    # 관련 시프트 전체 목록 + 글로브 안내
    # 400-600 words
    content: "..."

related_servants:
  - {name: "Gilgamesh", class: "Archer", rarity: 5}
  - {name: "Enkidu", class: "Lancer", rarity: 5}
  - {name: "Ishtar", class: "Archer", rarity: 5}
  - {name: "Ereshkigal", class: "Lancer", rarity: 5}
  - {name: "Merlin", class: "Caster", rarity: 5}

related_shifts:
  - shift-mesopotamian-civilization
  - shift-jewishbabylonian-war
  - shift-the-crusades

related_event_ids: [이벤트 ID들]
```

### 오를레앙 예시 (단일 파트 스토리)

단일 파트 스토리는 `key_plot_points`로 분할:

```yaml
slug: singularity-1
item_type: singularity

sections:
  - title: "France in 1431 — The Hundred Years' War"
    section_type: historical_setting
    content: "..."
    related_shifts:
      - slug: shift-hundred-years-war  # 기존 aggregate

  - title: "The Dragon Witch and the Fall of France"
    section_type: story_part
    part_number: 1
    source: "summaries/by_chapter/orleans.json"
    # key_plot_points 전반부 기반
    # 칼데아 도착 → 잔 다르크 오르타 등장 → 프랑스 함락
    content: "..."
    characters_introduced:
      - name: "Jeanne d'Arc"
        history_note: "실제 잔 다르크 (1412-1431)..."
        related_shift: shift-joan-of-arc  # person_story (신규 생성)
      - name: "Gilles de Rais"
        history_note: "잔 다르크의 전우에서 연쇄살인범으로..."
        related_shift: null

  - title: "Rally and Counterattack"
    section_type: story_part
    part_number: 2
    # key_plot_points 후반부 기반
    content: "..."
    characters_introduced:
      - name: "Marie Antoinette"
        history_note: "프랑스 혁명의 마지막 왕비..."
        related_shift: shift-french-revolution  # 기존 aggregate
      - name: "Chevalier d'Eon"
        history_note: "실존 스파이/외교관..."
        related_shift: null

  - title: "What This Story Is Really About"
    section_type: themes
    content: "..."
```

---

## 파트 분할 전략

| 스토리 유형 | 분할 방식 | 근거 |
|------------|----------|------|
| 멀티파트 (babylonia 등) | 기존 part 분할 그대로 사용 | `summaries/by_chapter/{slug}/part_N.json` |
| 싱글파트 (orleans 등) | `key_plot_points` 기반 2-3파트 | 전반/중반/후반 또는 위기/전환/해결 |
| 짧은 스토리 (fuyuki) | 1파트 | 스토리 자체가 짧음 |

### 각 특이점/LB 예상 파트 수

| slug | 파트 수 | 근거 |
|------|---------|------|
| singularity-f (Fuyuki) | 1 | 프롤로그, 짧음 |
| singularity-1 (Orleans) | 2 | 싱글파트, plot_points 분할 |
| singularity-2 (Septem) | 2 | 싱글파트 |
| singularity-3 (Okeanos) | 2 | 싱글파트 |
| singularity-4 (London) | 2 | 싱글파트 |
| singularity-5 (E Pluribus Unum) | 2-3 | 확인 필요 |
| singularity-6 (Camelot) | 3 | 멀티파트 예상 |
| singularity-7 (Babylonia) | 3 | 멀티파트 확인됨 |
| lostbelt-1 (Anastasia) | 2-3 | 확인 필요 |
| lostbelt-2 (Gotterdammerung) | 2 | 확인 필요 |
| lostbelt-3 (SIN) | 2-3 | 확인 필요 |
| lostbelt-4 (Yuga Kshetra) | 3 | 확인 필요 |
| lostbelt-5 (Olympus) | 3 | 긴 스토리 |
| lostbelt-6 (Avalon le Fae) | 3 | 긴 스토리 |
| lostbelt-7 (Nahui Mictlan) | 3 | 긴 스토리 |

→ 총 섹션 수: 역사배경 15 + 스토리파트 ~35 + 테마 15 = **~65 섹션**

---

## 대상

### 특이점 (8개)

| slug | 제목 | 시대/장소 | 핵심 서번트 |
|------|------|----------|------------|
| singularity-f | Fuyuki | 2004 일본 | Caster (Cu), Saber |
| singularity-1 | Orleans | 1431 프랑스 | Jeanne d'Arc, Gilles |
| singularity-2 | Septem | 60 로마 | Nero, Romulus |
| singularity-3 | Okeanos | 1573 대서양 | Drake, Blackbeard |
| singularity-4 | London | 1888 런던 | Mordred, Tesla, Babbage |
| singularity-5 | E Pluribus Unum | 1783 미국 | Edison, Tesla, Nightingale |
| singularity-6 | Camelot | 1273 성지 | Ozymandias, Hassan, Bedivere |
| singularity-7 | Babylonia | -2655 메소포타미아 | Gilgamesh, Enkidu, Ishtar |

### 로스트벨트 (7개)

| slug | 제목 | 시대/장소 | 핵심 서번트 |
|------|------|----------|------------|
| lostbelt-1 | Anastasia | 1570 러시아 | Ivan, Anastasia, Atalante |
| lostbelt-2 | Gotterdammerung | -1000 북유럽 | Sigurd, Brynhildr, Skadi |
| lostbelt-3 | SIN | -210 중국 | Qin Shi Huang, Spartacus |
| lostbelt-4 | Yuga Kshetra | ?? 인도 | Arjuna Alter, Karna |
| lostbelt-5 | Olympus | ?? 그리스 | Europa, Caenis, Romulus |
| lostbelt-6 | Avalon le Fae | ?? 브리튼 | Artoria Caster, Morgan |
| lostbelt-7 | Nahui Mictlan | ?? 메소아메리카 | Quetzalcoatl, Tezcatlipoca |

---

## GPT 프롬프트 컨텍스트

각 아티클 생성 시 아래를 GPT에 투입. **프롬프트 전체 영어** (콘텐츠도 영어이므로 언어 혼동 방지):

```
[1] 스토리 요약 (파트별)
    소스: E:\chaldeas_data\processed\fgo\summaries\by_chapter\{slug}.json
    → 멀티파트: parts[] + 각 part_N.json의 summary, key_characters, themes
    → 싱글파트: summary + key_plot_points (파트 분할 기준)

[2] 핵심 대사 추출 (파트별 등장인물)
    소스: E:\chaldeas_data\processed\fgo\dialogues\by_chapter\{slug}\
    → 해당 파트 quest_range의 주요 캐릭터 대사 상위 10줄

[3] 등장 서번트 본드 텍스트
    소스: fgo_db/servants/by_id/{각 서번트}.json
    → 해당 파트에서 등장하는 서번트들의 bond_text
    → FGO 해석/역사 비교용

[4] 기존 히스토리 시프트 매칭
    소스: DB historical_chains (키워드 매칭)
    → 해당 시대/인물과 매칭되는 기존 시프트 slug 목록
    → 아티클 내 시프트 링크용

[5] 실제 역사 이벤트
    소스: DB events (시대/지역 필터)
    → 특이점 시대에 해당하는 주요 이벤트 목록

[6] 학술 논문 (있으면)
    소스: paper_utils
```

---

## 구현

### create_portal_article.py 수정

`--singularity "VII"` / `--lostbelt 3` 옵션:

```python
def cmd_generate_story_article(args):
    slug = resolve_chapter_slug(args)  # "VII" → "babylonia"

    # 1. 스토리 요약 로드 (파트 분할 포함)
    summary = load_story_summary(slug)
    parts = get_story_parts(summary)  # 멀티파트 or key_plot_points 분할

    # 2. 기존 시프트 매칭
    matched_shifts = find_matching_shifts(summary['year'], summary['location'])

    # 3. historical_setting 섹션 생성
    setting_section = generate_historical_setting(
        year=summary['year'],
        location=summary['location'],
        matched_shifts=matched_shifts,
    )

    # 4. 파트별 story_part 섹션 생성
    story_sections = []
    for part in parts:
        characters = part['key_characters']
        bond_texts = load_servant_bonds(characters)
        dialogues = load_part_dialogues(slug, part)
        person_shifts = find_person_shifts(characters)

        section = generate_story_part(
            part_summary=part['summary'],
            characters=characters,
            bond_texts=bond_texts,
            dialogues=dialogues,
            person_shifts=person_shifts,
        )
        story_sections.append(section)

    # 5. themes 섹션 생성
    themes_section = generate_themes(summary, matched_shifts)

    # 6. YAML 출력
    ...
```

### fgo_data_utils.py 추가 함수

```python
def get_story_parts(summary: dict) -> list[dict]:
    """멀티파트면 part 파일 로드, 싱글이면 key_plot_points로 분할"""

def find_matching_shifts(year: int, location: str) -> list[dict]:
    """DB historical_chains에서 시대/키워드로 기존 시프트 매칭"""

def find_person_shifts(characters: list[dict]) -> dict[str, str]:
    """캐릭터별 관련 person_story 시프트 검색"""

def load_part_dialogues(slug: str, part: dict) -> list[str]:
    """해당 파트의 quest_range에 해당하는 대사 추출"""
```

---

## Phase 3과의 관계

기존 Phase 3 (히스토리 시프트 생성)은 이 Phase 2에 **통합**:

1. 아티클 생성 시 `find_matching_shifts()` → 기존 시프트 자동 연결
2. 매칭 안 되는 주제만 Phase 3에서 신규 생성
3. Phase 3의 역할이 "전부 새로 만들기" → **"빈 곳만 채우기"**로 축소

→ Phase 3 참조: `phase_3_history_shifts.md`

---

## 출력

- `backend/scripts/output/singularity-{n}-{slug}.yaml` × 8
- `backend/scripts/output/lostbelt-{n}-{slug}.yaml` × 7
- DB 직접 반영 안 함

## 비용

- Setting 섹션: 15 × ~$0.07 = $1.05
- Story Part 섹션: ~35 × ~$0.10 = $3.50  (파트당 컨텍스트 더 큼)
- Themes 섹션: 15 × ~$0.07 = $1.05
- Outline: 15 × ~$0.07 = $1.05
- **Total: ~$6.65**
