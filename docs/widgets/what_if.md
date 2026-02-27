# what_if

반사실적 가정 위젯. "만약 ~했다면?" 상상력 자극하는 다큐 기법.

## 슬롯

추천: `left` 또는 `bottom`

## 데이터 스키마

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `hypothesis` | string | O | 가정 ("만약 ~했다면?") |
| `consequence` | string | - | 예상되는 결과 |

## 렌더링

- magenta 좌측 보더 + 연한 배경
- "What If?" 라벨 (magenta, bold)
- 가정(bold) + 결과 텍스트

## 디자인 의도

다큐멘터리의 "만약에" 기법. 역사의 분기점을 강조하고 인과관계를 깊이 생각하게 함.

## 예시 데이터

```json
{
  "hypothesis": "What if Athens had lost at Marathon?",
  "hypothesis_ko": "만약 아테네가 마라톤에서 졌다면?",
  "consequence": "Persia would have conquered Athens 10 years earlier. No golden age, no Parthenon, no Athenian democracy as we know it. Western philosophy might have developed very differently.",
  "consequence_ko": "페르시아가 10년 일찍 아테네를 정복했을 것이다. 황금시대도, 파르테논도, 우리가 아는 아테네 민주주의도 없었을 것. 서양 철학이 전혀 다르게 발전했을 수 있다."
}
```
