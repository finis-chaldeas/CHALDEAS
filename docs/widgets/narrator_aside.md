# narrator_aside

나레이터 코멘트 위젯. 다큐멘터리 나레이터 스타일의 짧은 코멘트.

## 슬롯

추천: `left` 또는 `bottom`

## 데이터 스키마

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `text` | string | O | 나레이터 코멘트 텍스트 |

## 렌더링

- 회색 좌측 보더 + 이탤릭 텍스트
- 의도적으로 낮은 opacity (0.75) — 보조적 톤
- 가장 미니멀한 위젯

## 디자인 의도

다큐멘터리의 나레이터 보이스오버. 사실보다 감상, 분석보다 공감. "잠깐, 여기서 생각해봅시다..." 느낌.

## 예시 데이터

```json
{
  "text": "Imagine standing on that beach. You're a farmer from Athens, holding a bronze shield, watching the largest empire on Earth land its ships on your shore.",
  "text_ko": "그 해변에 서 있다고 상상해보라. 당신은 아테네의 농부다. 청동 방패를 들고, 지구 최대의 제국이 당신의 해안에 배를 대는 것을 지켜보고 있다."
}
```
