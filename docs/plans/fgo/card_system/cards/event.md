# Event Card

## 와이어프레임

### Compact (글로브 히어로 마커)
```
┌─────────────────────────┐
│ Battle of Thermopylae   │
│ 480 BCE · ★★★★★        │
└─────────────────────────┘
```

### Expanded
```
┌─────────────────────────┐
│ Battle of Thermopylae   │
│ 테르모필레 전투           │
│                         │
│ 480 BCE                 │
│ Thermopylae, Greece     │
│ ★★★★★                  │
│                         │
│ "스파르타 왕 레오니다스가  │  ← event_details.description 처음 200자
│  300명의 전사와 함께..."  │     이미 smart-markers API에서 truncate 중
│                         │
│ Key figures:            │
│  • Leonidas I           │  ← 클릭 시 Person Card 열림
│  • Xerxes I             │
│                         │
│ [시프트]                  │
└─────────────────────────┘
```

## 데이터 소스

| 필드 | 테이블.컬럼 | 비고 |
|------|------------|------|
| 제목 | `events.title` / `title_ko` / `title_ja` | loc() 폴백 |
| 연도 | `events.date_start`, `date_end` | BCE 음수 변환 |
| 장소명 | `event_locations` → `locations.name` | |
| 중요도 | `events.importance` | ★ 표시 |
| 본문 스니펫 | `event_details.description` | **처음 200자** (이미 API에서 제공) |
| 관련 인물 | `event_persons` JOIN | 상위 3명 |

## 현재 상태 — 이미 거의 다 있다

smart-markers API (`backend/app/api/v1_new/globe.py:954`)가 이미 `description[:200]`을 반환 중.
현재 GlobeContainer의 히어로 카드가 이걸 **안 쓰고 있을 뿐**.

→ Event Card는 히어로 카드를 React 컴포넌트로 교체하면서 description을 표시하면 끝.

## 트리거

- 글로브 히어로 마커 (현재 raw HTML → Event Card로 교체)
- `[Name](entity:event:id)` 엔티티 링크 클릭
- Location Card 내 이벤트 이름 클릭

## 액션 버튼

- **시프트** → 관련 시프트 열기 (있으면)
- **자세히** → EventDetailPanel 풀 패널 열기
- 인물 이름 클릭 → Person Card 열기

## 기존 코드 참고

- 현재 히어로 카드 HTML: `GlobeContainer.tsx:937-1047`
- EventDetailPanel: `frontend/src/components/detail/EventDetailPanel.tsx`
- smart-markers API description 제공: `globe.py:954`
