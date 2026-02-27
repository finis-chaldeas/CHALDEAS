# person_card

인물 카드 위젯. 역사적 인물의 핵심 정보를 간결하게 표시.

## 슬롯

추천: `left` 또는 `right`

## 데이터 스키마

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `name` | string | O | 인물명 |
| `role` | string | - | 역할/직위 |
| `birth_year` | number | - | 출생년 (BCE = 음수) |
| `death_year` | number | - | 사망년 (BCE = 음수) |
| `summary` | string | - | 1-2문장 요약 |

## 렌더링

- 이름: 금색, 굵게
- 역할: cyan, uppercase, 작은 글씨
- 생몰년: 모노스페이스 (예: "540 BCE – 480 BCE")
- 요약: 본문 텍스트

## 생몰년 표시 로직

- 출생+사망: "540 BCE – 480 BCE"
- 출생만: "b. 540 BCE"
- 사망만: "d. 480 BCE"

## 예시 데이터

```json
{
  "name": "Leonidas I",
  "name_ko": "레오니다스 1세",
  "role": "King of Sparta",
  "role_ko": "스파르타의 왕",
  "birth_year": -540,
  "death_year": -480,
  "summary": "Chose to stay with 300 Spartans at the narrow pass..."
}
```
