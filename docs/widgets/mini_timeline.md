# mini_timeline

미니 타임라인 위젯. 이벤트 시퀀스를 세로 타임라인으로 표시.

## 슬롯

추천: `left` (세로로 길어지므로 사이드에 적합)

## 데이터 스키마

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `heading` | string | - | 타임라인 제목 |
| `events` | array | O | 이벤트 배열 |
| `events[].year` | number | - | 연도 (BCE = 음수) |
| `events[].label` | string | O | 이벤트 설명 |
| `events[].highlight` | boolean | - | 강조 표시 여부 |

## 렌더링

- 세로 선 + 점 (dot) 타임라인
- highlight된 이벤트: 금색 dot + glow + 금색 텍스트
- 일반 이벤트: 회색 dot + 기본 텍스트
- 연도: cyan 모노스페이스

## events 배열 i18n

events 내부 객체도 `loc()` 패턴 적용:
```json
{"year": -480, "label": "Battle of Thermopylae", "label_ko": "테르모필레 전투", "highlight": true}
```

## 예시 데이터

```json
{
  "heading": "Greco-Persian Wars",
  "heading_ko": "그리스-페르시아 전쟁",
  "events": [
    {"year": -490, "label": "Battle of Marathon", "label_ko": "마라톤 전투"},
    {"year": -480, "label": "Battle of Thermopylae", "label_ko": "테르모필레 전투", "highlight": true},
    {"year": -480, "label": "Battle of Salamis", "label_ko": "살라미스 해전"},
    {"year": -479, "label": "Battle of Plataea", "label_ko": "플라타이아 전투"}
  ]
}
```
