# battle_stats

전투 통계 위젯. 피해, 기간, 지형 등 전투 수치 정보 표시.

## 슬롯

추천: `left` 또는 `right` (faction_vs와 반대쪽)

## 데이터 스키마

두 가지 방식 지원:

### 방식 1: stats 배열 (추천)

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `heading` | string | - | 제목 (기본: "Battle Statistics") |
| `stats` | array | O | 통계 행 배열 |
| `stats[].label` | string | O | 항목명 |
| `stats[].value` | string | O | 값 |
| `significance` | string | - | 전투 의의 (하단 이탤릭) |

### 방식 2: 플랫 필드 (간단)

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `casualties_left` | string | - | 좌측 피해 |
| `casualties_left_label` | string | - | 좌측 피해 라벨 |
| `casualties_right` | string | - | 우측 피해 |
| `casualties_right_label` | string | - | 우측 피해 라벨 |
| `duration` | string | - | 전투 기간 |
| `duration_label` | string | - | 기간 라벨 |
| `terrain` | string | - | 지형 |
| `terrain_label` | string | - | 지형 라벨 |

## 렌더링

- 제목: 금색, uppercase
- 통계 행: 라벨(좌, 회색) + 값(우, cyan 모노스페이스)
- 의의: 하단 이탤릭 텍스트

## 예시 데이터

```json
{
  "heading": "Battle Statistics",
  "heading_ko": "전투 통계",
  "stats": [
    {"label": "Greek casualties", "label_ko": "그리스 사상자", "value": "~192", "value_ko": "약 192명"},
    {"label": "Persian casualties", "label_ko": "페르시아 사상자", "value": "~6,400", "value_ko": "약 6,400명"},
    {"label": "Duration", "label_ko": "기간", "value": "1 day", "value_ko": "1일"},
    {"label": "Terrain", "label_ko": "지형", "value": "Coastal plain", "value_ko": "해안 평야"}
  ],
  "significance": "First major Greek victory against Persia; proved hoplite phalanx superiority",
  "significance_ko": "그리스의 첫 대규모 대페르시아 승리; 중장보병 밀집대형의 우위를 증명"
}
```
