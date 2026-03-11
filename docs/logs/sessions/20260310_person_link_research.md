# 2026-03-10: FGO 서번트 인물 링크 연구 기획

## 목적

FGO 서번트 → persons 테이블 매칭의 정확성 감사 및 개선 기획서 작성.

## 주요 발견

### 현재 상태 (person_gaps.md 분석과 크게 다름)
- 449 서번트 중 **389명(87%) 이미 링크됨** (person_gaps.md의 82명은 과거 기준)
- 142명 배치 삽입 (ID 14610628-14610766) with certainty + 추정 연대
- 미링크 60명 = 대부분 Fate 오리지널 (Emiya, BB, Mash 등)

### 오매칭 21건 발견
비배치 17건:
- Queen Medb → Andrei Zhdanov, Arash → 현대인, Geronimo → Thomas Gravesen
- Ivan the Terrible → 잘못된 Ivan(1911), Hektor → Saadi, Don Quixote → Damiano Damiani
- Sakata Kintoki → Felix Manalo, Scheherazade → Agnes Varda, Morgan → 현대인
- Nemo → Vladimir Vernadsky, Percival → 현대인, William Tell → 현대인
- Astraea → C.S. Peirce, Lady Avalon → Jennifer Granholm 등

배치 내 4건:
- Odysseus → Heracles, Paris → Europa, Valkyrie → Quetzalcoatl, Merlin → King Arthur

### DB 조회 결과
- Ivan IV (1530-1584): **id=1623709로 존재** → 링크 수정만 하면 됨
- Geronimo (Apache): DB에 없음 → 신규 생성 필요
- Sakata Kintoki: DB에 없음 → 신규 생성 필요

## 생성/수정된 파일

| 파일 | 유형 | 내용 |
|------|------|------|
| `docs/plans/fgo/person_link_research.md` | **신규** | 연구 기획서 (Phase A-D) |
| `docs/plans/fgo/person_gaps.md` | 수정 | 상단에 현황 경고 노트 추가 |

## 다음 작업

1. Phase A 실행: 21건 오매칭 corrections YAML 생성
2. Phase B 실행: ~18명 신규 인물 YAML 생성
3. Phase C 실행: Semantic Scholar로 연대 검증
4. person_gaps.md 전면 재작성
