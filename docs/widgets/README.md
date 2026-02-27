# Widget Catalog

위젯 시스템 기획서. 각 위젯별 spec 파일로 관리.

## 위젯 추가 방법

1. `frontend/src/components/shift/widgets/YourWidget.tsx` 생성
2. `registerWidget('your_widget', YourWidget)` 호출
3. `widgets/index.ts`에 `import './YourWidget'` 한 줄 추가
4. `docs/widgets/your_widget.md` 기획서 작성

## 데이터 흐름

```
PostgreSQL JSONB → FastAPI → WidgetSlot → WidgetRenderer → Component
```

## i18n 규칙

- 영어 기본 (`text`, `label`)
- `_ko`, `_ja` 접미사로 한/일 번역 (`text_ko`, `text_ja`)
- `loc(data, key, lang)` — 현재 언어 → 영어 폴백
- `locArray(data, key, lang)` — 배열 필드용

## 등록된 위젯

| type | 파일 | 배치 | 설명 |
|------|------|------|------|
| `primary_quote` | PrimaryQuote.tsx | 기본 | 인용문 + 출처 |
| `faction_vs` | FactionVs.tsx | 기본 | 진영 대결 비교 |
| `dramatic_stat` | DramaticStat.tsx | 기본 | 수치 강조 |
| `person_card` | PersonCard.tsx | D1 | 인물 카드 |
| `mini_timeline` | MiniTimeline.tsx | D1 | 이벤트 시퀀스 |
| `era_context` | EraContext.tsx | D1 | 동시대 맥락 |
| `battle_stats` | BattleStats.tsx | D2 | 전투 통계 |
| `territory_change` | TerritoryChange.tsx | D2 | 영토 변화 (before→after) |
| `alliance_diagram` | AllianceDiagram.tsx | D2 | 동맹 관계도 |
| `historian_note` | HistorianNote.tsx | D3 | 역사가 주석 |
| `we_dont_know` | WeDontKnow.tsx | D3 | 불확실한 사실 |
| `conflicting_accounts` | ConflictingAccounts.tsx | D3 | 상충하는 기록 |
| `modern_equivalent` | ModernEquivalent.tsx | D4 | 현대 비유 |
| `what_if` | WhatIf.tsx | D4 | 반사실적 가정 |
| `narrator_aside` | NarratorAside.tsx | D4 | 나레이터 코멘트 |
