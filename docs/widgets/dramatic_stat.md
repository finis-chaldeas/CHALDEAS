# dramatic_stat

수치 강조 위젯. 다큐멘터리 스타일의 숫자 임팩트.

## 슬롯

추천: `left` 또는 `bottom`

## 데이터 스키마

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `number` | string | O | 메인 숫자 |
| `label` | string | - | 숫자 설명 |
| `context` | string | - | 맥락 텍스트 |
| `prefix` | string | - | 숫자 앞 접두사 (예: ~) |
| `suffix` | string | - | 숫자 뒤 접미사 (예: km) |

## 렌더링

- 큰 모노스페이스 숫자 (cyan, 2.2rem)
- prefix/suffix는 작은 글씨
- 하단에 라벨 (uppercase) + 맥락 텍스트

## 예시 데이터

```json
{
  "number": "42",
  "suffix": "km",
  "label": "Marathon to Athens",
  "label_ko": "마라톤에서 아테네까지",
  "context": "The distance Pheidippides ran to announce victory"
}
```
