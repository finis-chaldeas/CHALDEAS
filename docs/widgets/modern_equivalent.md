# modern_equivalent

현대 비유 위젯. 고대 개념을 현대 독자가 이해하기 쉽게 비유.

## 슬롯

추천: `left` 또는 `bottom`

## 데이터 스키마

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `ancient` | string | O | 고대 개념/사물 |
| `modern` | string | O | 현대 등가물 |
| `explanation` | string | - | 비유 설명 |

## 렌더링

- "In Today's Terms" 라벨 (cyan, uppercase)
- ancient &asymp; modern (가운데 근사 기호)
- 하단 설명 텍스트

## 예시 데이터

```json
{
  "ancient": "10,000 hoplites",
  "ancient_ko": "중장보병 1만명",
  "modern": "A modern infantry brigade",
  "modern_ko": "현대 보병 여단 1개",
  "explanation": "Athens committed roughly the equivalent of an entire modern brigade to a single battle — an enormous gamble for a city-state.",
  "explanation_ko": "아테네는 현대 보병 여단 하나에 해당하는 병력을 단일 전투에 투입했다 — 도시국가로서는 엄청난 도박."
}
```
