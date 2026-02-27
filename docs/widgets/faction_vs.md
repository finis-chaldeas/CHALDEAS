# faction_vs

진영 대결 위젯. 전쟁/전투 페이지의 핵심 위젯.

## 슬롯

추천: `right` (3-column 그리드가 넓은 공간 필요)

## 데이터 스키마

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `left_name` | string | O | 좌측 진영명 |
| `left_commander` | string | - | 좌측 지휘관 |
| `left_strength` | string | - | 좌측 병력 |
| `left_details` | string[] | - | 좌측 세부 (참전국 등) |
| `right_name` | string | O | 우측 진영명 |
| `right_commander` | string | - | 우측 지휘관 |
| `right_strength` | string | - | 우측 병력 |
| `right_details` | string[] | - | 우측 세부 |
| `outcome` | string | - | 결과 |

## 렌더링

- 3-column 그리드: 좌측(cyan) / VS / 우측(magenta)
- 하단에 결과 표시 (금색, 중앙 정렬)
- 배열 필드는 `locArray()` 사용

## 예시 데이터

```json
{
  "left_name": "Greek Alliance",
  "left_name_ko": "그리스 동맹",
  "left_commander": "Leonidas I",
  "left_details": ["Sparta", "Thespiae", "Thebes"],
  "left_details_ko": ["스파르타", "테스피아이", "테바이"],
  "right_name": "Persian Empire",
  "right_name_ko": "페르시아 제국",
  "outcome": "Persian victory, but heavy cost"
}
```
