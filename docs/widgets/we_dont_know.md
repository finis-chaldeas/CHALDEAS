# we_dont_know

불확실한 사실 위젯. 역사적 미스터리, 증거 부족, 논쟁적 해석을 솔직하게 표시.

## 슬롯

추천: `left` 또는 `bottom`

## 데이터 스키마

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `question` | string | O | 불확실한 질문/주제 |
| `detail` | string | - | 왜 모르는지 설명 |
| `theories` | string | - | 주요 이론/가설 요약 |

## 렌더링

- 점선 금색 보더 + 연한 금색 배경
- "?" 아이콘 + "We Don't Know" 라벨
- 질문(bold) + 설명 + 이론(이탤릭)

## 디자인 의도

역사의 불확실성을 투명하게 인정. "모른다"를 숨기지 않고 다큐멘터리처럼 솔직하게 표현.

## 예시 데이터

```json
{
  "question": "How many Persians actually fought at Marathon?",
  "question_ko": "마라톤에서 실제로 싸운 페르시아군은 몇 명이었을까?",
  "detail": "Ancient sources range wildly from 20,000 to 600,000. No Persian records survive.",
  "detail_ko": "고대 사료의 기록은 2만에서 60만까지 크게 다르다. 페르시아 측 기록은 남아 있지 않다.",
  "theories": "Modern consensus: likely 20,000–30,000 including cavalry and naval forces.",
  "theories_ko": "현대 학계 합의: 기병과 해군력 포함 2만~3만명으로 추정."
}
```
