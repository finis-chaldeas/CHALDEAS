# territory_change

영토 변화 위젯. 사건 전후의 영토/세력 변화를 before → after로 표시.

## 슬롯

추천: `bottom` 또는 `right`

## 데이터 스키마

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `heading` | string | - | 제목 (기본: "Territory Change") |
| `changes` | array | O | 변화 항목 배열 |
| `changes[].label` | string | - | 항목명 (예: "Aegean Coast") |
| `changes[].before` | string | O | 변화 전 상태 |
| `changes[].after` | string | O | 변화 후 상태 |

## 렌더링

- 제목: 금색, uppercase
- 각 항목: 라벨 + before(magenta) → after(cyan, bold)
- 화살표로 변화 방향 시각화

## 예시 데이터

```json
{
  "heading": "After Marathon",
  "heading_ko": "마라톤 이후",
  "changes": [
    {
      "label": "Persian influence",
      "label_ko": "페르시아 영향력",
      "before": "Expanding into Greece",
      "before_ko": "그리스로 확장 중",
      "after": "Halted for 10 years",
      "after_ko": "10년간 저지됨"
    }
  ]
}
```
