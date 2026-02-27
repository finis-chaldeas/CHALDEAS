# alliance_diagram

동맹 관계 위젯. 진영별 동맹/소속 세력을 시각적으로 표시.

## 슬롯

추천: `left` 또는 `right`

## 데이터 스키마

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `heading` | string | - | 제목 (기본: "Alliances") |
| `groups` | array | O | 동맹 그룹 배열 |
| `groups[].name` | string | - | 그룹명 |
| `groups[].members` | string[] | - | 소속 세력 목록 |
| `groups[].color` | string | - | CSS 색상 (기본: 순환 할당) |

## 렌더링

- 각 그룹: 좌측 컬러 보더 + 그룹명(bold) + 멤버 목록
- 기본 색상 순환: cyan → magenta → gold → green
- color 필드로 커스텀 색상 지정 가능

## 예시 데이터

```json
{
  "heading": "Alliance Structure",
  "heading_ko": "동맹 구조",
  "groups": [
    {
      "name": "Hellenic League",
      "name_ko": "헬라스 동맹",
      "members": ["Athens", "Sparta", "Corinth", "Aegina"],
      "members_ko": ["아테네", "스파르타", "코린토스", "아이기나"]
    },
    {
      "name": "Persian Empire",
      "name_ko": "페르시아 제국",
      "members": ["Persia", "Phoenicia", "Egypt", "Ionia (forced)"],
      "members_ko": ["페르시아", "페니키아", "이집트", "이오니아 (강제)"],
      "color": "var(--chaldea-magenta)"
    }
  ]
}
```
