# conflicting_accounts

상충하는 기록 위젯. 같은 사건에 대한 서로 다른 사료의 주장을 병렬 표시.

## 슬롯

추천: `left` 또는 `bottom`

## 데이터 스키마

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `heading` | string | - | 제목 (기본: "Conflicting Accounts") |
| `accounts` | array | O | 최소 2개의 사료 주장 |
| `accounts[].source` | string | - | 사료/저자명 |
| `accounts[].claim` | string | O | 주장 내용 |
| `verdict` | string | - | 현대 학계 판단 (하단 이탤릭) |

## 렌더링

- 제목: magenta, uppercase
- 각 주장: 좌측 보더 + 출처(cyan) + 내용
- 판결: 하단 금색 이탤릭

## 디자인 의도

역사는 단일 사실이 아님을 보여줌. "이 사람은 이렇게 말했고, 저 사람은 저렇게 말했다."

## 예시 데이터

```json
{
  "heading": "Persian Army Size",
  "heading_ko": "페르시아 군대 규모",
  "accounts": [
    {
      "source": "Herodotus",
      "source_ko": "헤로도토스",
      "claim": "2,641,610 combatants plus an equal number of support",
      "claim_ko": "전투원 2,641,610명과 동수의 지원병"
    },
    {
      "source": "Modern estimates",
      "source_ko": "현대 추정",
      "claim": "70,000–300,000 total forces",
      "claim_ko": "총 병력 7만~30만명"
    }
  ],
  "verdict": "Ancient figures are almost certainly exaggerated; logistics alone make millions impossible.",
  "verdict_ko": "고대 수치는 거의 확실히 과장됨; 병참만으로도 수백만은 불가능."
}
```
