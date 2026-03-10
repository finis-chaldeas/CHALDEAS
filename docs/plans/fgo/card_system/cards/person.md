# Person Card

## 와이어프레임

### Compact (글로브 인물 마커)
```
┌─────────────────────────┐
│ Alexander the Great     │
│ 356 — 323 BCE · King    │
└─────────────────────────┘
```

### Expanded
```
┌─────────────────────────┐
│ Alexander the Great     │
│ 알렉산드로스 대왕         │
│ 356 BCE — 323 BCE       │
│ King, Conqueror         │
│                         │
│ "마케도니아의 왕으로...    │  ← person_details.biography 처음 150자
│  페르시아 제국을 정복..."  │     또는 entity_narratives.significance
│                         │
│ ┌─── FGO ───────────┐   │  ← fgo_servants 매칭 시에만 표시
│ │ ★5 Rider Iskandar │   │
│ │ [서번트 칼럼 보기]   │   │
│ └───────────────────┘   │
│                         │
│ [글로브에서 보기] [시프트]  │
└─────────────────────────┘
```

## 데이터 소스

| 필드 | 테이블.컬럼 | 비고 |
|------|------------|------|
| 이름 | `persons.name` / `name_ko` / `name_ja` | loc() 폴백 |
| 수명 | `persons.birth_year`, `death_year` | BCE 음수 변환 |
| 역할 | `persons.role` | |
| 본문 스니펫 | `person_details.biography` | **처음 150자** 잘라서 표시 |
| 본문 스니펫 (대안) | `entity_narratives.significance` | biography 없으면 1문장 |
| FGO 서번트 | `fgo_servants` (person_id JOIN) | 매칭 있을 때만 |
| FGO 초상화 | `fgo_servants.portrait_url` | Atlas Academy |

## 트리거

- 글로브 인물 마커 클릭
- `[Name](entity:person:id)` 엔티티 링크 클릭
- 시프트 위젯 `person_card` 타입
- Event Card 내 인물 이름 클릭

## 액션 버튼

- **글로브에서 보기** → 해당 인물의 주요 이벤트 위치로 카메라 이동
- **시프트** → 관련 person_story 시프트 열기 (있으면)
- **서번트 칼럼 보기** → portal_items 연결 (FGO 매칭 시)
- **자세히** → PersonDetailView 풀 패널 열기

## 기존 코드 참고

- 현재 인물 표시: `frontend/src/components/detail/PersonDetailView.tsx`
- FGO 배지: PersonDetailView 130-143줄 (`servantsApi.getByPerson`)
- 시프트 위젯 PersonCard: `frontend/src/components/shift/widgets/PersonCard.tsx` (37줄, 교체 대상)
