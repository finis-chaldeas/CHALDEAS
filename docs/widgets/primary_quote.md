# primary_quote

인용문 위젯. 역사적 인물/문헌의 원문을 인용.

## 슬롯

추천: `left` (사이드 패널에 자연스러움)

## 데이터 스키마

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `text` | string | O | 인용 텍스트 |
| `source` | string | - | 출처 (책/문헌명) |
| `speaker` | string | - | 발화자 |
| `year` | number | - | 연도 (BCE = 음수) |

## 렌더링

- 좌측 금색 보더 + 이탤릭 인용 텍스트
- 하단에 발화자, 출처, 연도 표시
- 연도: 음수 → "480 BCE", 양수 → "1453 CE"

## 예시 데이터

```json
{
  "text": "Go tell the Spartans, stranger passing by...",
  "text_ko": "지나가는 나그네여, 스파르타인들에게 전하라...",
  "source": "Histories",
  "speaker": "Simonides of Ceos",
  "year": -480
}
```
