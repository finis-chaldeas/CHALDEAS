# Phase 1: 서번트 칼럼 리라이트 + 확장

**선행 조건**: Phase 0 (서번트 링킹)
**비용**: ~$10.50 (gpt-5.2-chat-latest)
**예상 시간**: ~30분
**DB 반영**: No (YAML 생성만, DB 반영은 카드 시스템 정리 때)

---

## 목표

기존 12개 서번트 칼럼 (스켈레톤 상태, 섹션당 ~250자) → 30개 풍부한 에세이 (섹션당 500-700 words)

## 대상 서번트 (30명)

### Tier 1 — 역사 인물 (20명)

person_id 매칭 가능. 역사적 사실 + FGO 해석 양면 구성.

| 서번트 | 실제 인물 | 시대 | 기존 칼럼 |
|--------|----------|------|----------|
| Gilgamesh | 길가메시 | 메소포타미아 | 있음 (97자) |
| Iskandar | 알렉산드로스 대왕 | 고대 그리스 | 있음 |
| Nero Claudius | 네로 | 로마 | 있음 |
| Jeanne d'Arc | 잔 다르크 | 백년전쟁 | 있음 |
| Francis Drake | 프랜시스 드레이크 | 대항해시대 | 있음 |
| Nikola Tesla | 니콜라 테슬라 | 근현대 | 있음 |
| Leonidas I | 레오니다스 | 고대 그리스 | 있음 |
| Ivan the Terrible | 이반 뇌제 | 러시아 | 있음 |
| Oda Nobunaga | 오다 노부나가 | 센고쿠 | 있음 |
| Mordred | 모드레드 | 아서왕 전설 | 있음 |
| Julius Caesar | 율리우스 카이사르 | 로마 | 신규 |
| Cleopatra | 클레오파트라 | 이집트/로마 | 신규 |
| Leonardo da Vinci | 레오나르도 다 빈치 | 르네상스 | 신규 |
| Napoleon | 나폴레옹 | 근대 | 신규 |
| Ozymandias | 람세스 2세 | 이집트 | 신규 |
| Qin Shi Huang | 진시황 | 중국 | 신규 |
| Florence Nightingale | 나이팅게일 | 근대 | 신규 |
| Zhuge Liang | 제갈량 | 삼국시대 | 신규 |
| Marie Antoinette | 마리 앙투아네트 | 프랑스 혁명 | 신규 |
| Spartacus | 스파르타쿠스 | 로마 | 신규 |

### Tier 2 — 신화/전설 (10명)

persons 테이블 미등재 가능성. 본드 텍스트 + 신화 원전 기반.

| 서번트 | 모티프 | 신화/전설 |
|--------|--------|----------|
| Artoria Pendragon | 아서왕 | 아서왕 전설 |
| Cu Chulainn | 쿠 훌린 | 켈트 신화 |
| Achilles | 아킬레우스 | 그리스 신화 |
| Heracles | 헤라클레스 | 그리스 신화 |
| Karna | 카르나 | 인도 신화 |
| Arjuna | 아르주나 | 인도 신화 |
| Medea | 메데이아 | 그리스 신화 |
| Ushiwakamaru | 미나모토노 요시쓰네 | 일본 전설 |
| Miyamoto Musashi | 미야모토 무사시 | 일본 역사 |
| Sigurd | 시구르드 | 북유럽 신화 |

## 콘텐츠 구조

각 서번트 칼럼 = 5섹션, 총 ~2,500 words

```yaml
slug: servant-gilgamesh
item_type: servant_column

title: "Gilgamesh — The King Who Searched for Immortality"
subtitle: "From historical king of Uruk to FGO's King of Heroes"
description: "..."

sections:
  - title: "Who Was the Real Gilgamesh?"
    # 역사/신화적 배경. 학술 논문 + DB 이벤트 참조.
    # 500-700 words. 다큐멘터리 스타일.
    content: "..."

  - title: "FGO's King of Heroes"
    # FGO에서의 해석. 본드 텍스트 분석, 보구, 스킬의 역사적 근거.
    # 본드 텍스트 직접 인용 1-2개.
    # 400-600 words.
    content: "..."

  - title: "History vs. Fate — What Changed?"
    # 비교표 형태. 외모, 성격, 능력, 관계, 보구.
    # 정확한 것 / 아티스틱 라이선스 / 완전 창작 구분.
    # 400-600 words.
    content: "..."

  - title: "Uruk and the Dawn of Civilization"
    # 시대 배경. 해당 시대/지역의 역사적 맥락.
    # 이 인물이 왜 중요한지.
    # 400-600 words.
    content: "..."

  - title: "The Servant Network"
    # 관련 서번트. 같은 시대/신화/스토리에 등장하는 서번트들.
    # 예: 길가메시 → 엔키두, 이슈타르, 킹 하산
    # 300-400 words.
    content: "..."

related_servants:
  - {name: "Gilgamesh", class: "Archer", rarity: 5}
  - {name: "Enkidu", class: "Lancer", rarity: 5}
  - {name: "Ishtar", class: "Archer", rarity: 5}
related_event_ids: []
```

## GPT 프롬프트 컨텍스트

각 서번트 칼럼 생성 시 아래를 GPT에 투입:

```
[1] 서번트 본드 텍스트 (EN + JP 원문)
    소스: E:\chaldeas_data\fgo_db\servants\by_id\{atlas_id}.json
    → bond_text.en[0..6] + bond_text.ja[0..6]
    → profile.stats, noble_phantasm 등

[2] DB 인물 정보
    소스: SELECT name, name_ko, birth_year, death_year, role, domain
          FROM persons WHERE id = {person_id}
    → event_persons JOIN events → 주요 이벤트 목록

[3] 학술 논문 초록 (있으면)
    소스: paper_utils.get_papers_for_events(event_ids)
    → 상위 3-5개 논문 제목 + 초록

[4] FGO 스토리 등장 요약
    소스: E:\chaldeas_data\processed\fgo\summaries\by_chapter\*.json
    → key_characters에 해당 서번트가 포함된 챕터 요약

[5] 관련 서번트 목록
    소스: fgo_servants 테이블에서 같은 시대/신화 서번트
```

## 구현

### create_portal_article.py 수정

`--servant-id ID` 옵션 추가:

```python
def cmd_generate_servant(args):
    servant_id = args.servant_id

    # 1. FGO 서번트 데이터 로드
    servant = load_fgo_servant(servant_id)  # fgo_data_utils.py
    bond_text = servant['bond_text']

    # 2. DB 인물 조회
    person = db.query(Person).get(servant['person_id'])
    events = get_person_events(person.id)

    # 3. 학술 논문
    papers = get_papers_for_events([e.id for e in events])

    # 4. 스토리 등장
    story_appearances = find_story_appearances(servant['name_ja'])

    # 5. GPT 호출 (outline → sections)
    outline = generate_servant_outline(servant, person, events, papers)
    for section in outline['sections']:
        content = generate_servant_section(section, bond_text, ...)
```

### fgo_data_utils.py 신규

```python
def load_fgo_servant(servant_id: int) -> dict:
    """E:\chaldeas_data\fgo_db\servants\by_id\{id}.json 로드"""

def find_story_appearances(name_ja: str) -> list[dict]:
    """summaries/by_chapter/*.json에서 해당 캐릭터 등장 챕터 검색"""

def get_servant_dialogues(name_ja: str, limit: int = 50) -> list[str]:
    """dialogues/by_character/{name}.json에서 대사 추출"""
```

### 배치 실행

```python
# create_fgo_content.py
SERVANT_TARGETS = [
    {"servant_id": 200300, "slug": "servant-gilgamesh"},
    {"servant_id": 301300, "slug": "servant-iskandar"},
    # ... 30명
]
```

## 출력

- `backend/scripts/output/servant-{name}.yaml` × 30개
- DB 직접 반영 안 함 (카드 시스템 정리 때 import)

## 비용

- Outline: 30 × ~$0.05 = $1.50
- Sections: 30 × 5 × ~$0.06 = $9.00
- **Total: ~$10.50**
