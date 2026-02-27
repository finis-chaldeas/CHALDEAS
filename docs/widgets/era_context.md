# era_context

시대 맥락 위젯. "그 무렵 세계는..." 동시대 다른 지역의 상황을 보여줌.

## 슬롯

추천: `bottom` (넓은 가로 공간 활용)

## 데이터 스키마

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `heading` | string | - | 제목 (기본값: "Meanwhile...") |
| `items` | array | O | 지역별 맥락 배열 |
| `items[].region` | string | - | 지역명 |
| `items[].text` | string | O | 맥락 텍스트 |

## 렌더링

- 제목: 금색, uppercase
- 각 항목: 지역명(cyan, uppercase) + 텍스트
- heading 미지정 시 "Meanwhile..." 기본 표시

## items 배열 i18n

items 내부 객체도 `loc()` 패턴 적용:
```json
{"region": "China", "region_ko": "중국", "text": "Spring and Autumn period...", "text_ko": "춘추시대가..."}
```

## 예시 데이터

```json
{
  "heading": "Meanwhile in 490 BCE",
  "heading_ko": "그 무렵, 기원전 490년",
  "items": [
    {
      "region": "China",
      "region_ko": "중국",
      "text": "Confucius is alive, traveling between states.",
      "text_ko": "공자가 살아 있으며, 여러 나라를 돌아다니고 있다."
    },
    {
      "region": "India",
      "region_ko": "인도",
      "text": "The Buddha passed away roughly a decade ago.",
      "text_ko": "부처가 대략 10년 전 입멸했다."
    }
  ]
}
```
