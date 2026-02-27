# historian_note

역사가 주석 위젯. 학술적 코멘트, 사료 평가, 연구 맥락 표시.

## 슬롯

추천: `left` 또는 `bottom`

## 데이터 스키마

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `note` | string | O | 주석 텍스트 |
| `historian` | string | - | 역사가/학자명 |
| `work` | string | - | 출처 작품명 |
| `tone` | string | - | `neutral` (기본) / `caution` / `praise` |

## tone별 스타일

| tone | 아이콘 | 보더 | 용도 |
|------|--------|------|------|
| `neutral` | memo | 없음 | 일반 학술 주석 |
| `caution` | warning | 금색 | 사료 신뢰도 경고, 논쟁적 해석 |
| `praise` | star | cyan | 긍정적 평가, 중요한 발견 |

## 예시 데이터

```json
{
  "note": "Herodotus' casualty figures are likely exaggerated. Modern estimates suggest 20,000–60,000 Persian troops.",
  "note_ko": "헤로도토스의 피해 수치는 과장되었을 가능성이 높다. 현대 추정치는 페르시아군 2만~6만명.",
  "historian": "Peter Green",
  "work": "The Greco-Persian Wars (1996)",
  "tone": "caution"
}
```
