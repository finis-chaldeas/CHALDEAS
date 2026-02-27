# FGO Dialogue Extraction (Phase 1)

**Date**: 2026-02-27
**Status**: Complete

## 목적

FGO 메인 스토리 + 이벤트 스크립트 데이터에서 캐릭터별 대사를 추출하는 파이프라인 구축.

## 변경 파일

- `backend/scripts/extract_fgo_dialogues.py` — 새로 작성

## 결과

| 항목 | 값 |
|------|-----|
| 메인 챕터 | 21 |
| 이벤트 | 118 |
| 고유 캐릭터 | 3,462 |
| 캐릭터 대사 | 429,149 |
| 나레이션 | 283 |
| ？？？ (미확인) | 10,562 |
| alias 적용 | 22건 |
| 비용 | $0 (로컬 처리) |
| 소요 시간 | ~5초 |

### Top 10 스피커

| 순위 | 캐릭터 | 대사 수 | 등장 챕터 |
|------|--------|---------|----------|
| 1 | マシュ・キリエライト | 33,530 | 135 |
| 2 | レオナルド・ダ・ヴィンチ | 17,315 | 113 |
| 3 | ゴルドルフ・ムジーク | 7,642 | 59 |
| 4 | シャーロック・ホームズ | 4,759 | 33 |
| 5 | エリザベート | 4,249 | 40 |
| 6 | ロマニ・アーキマン | 4,083 | 26 |
| 7 | 刑部姫 | 3,386 | 28 |
| 8 | カーマ | 3,264 | 9 |
| 9 | ジャンヌ・ダルク〔オルタ〕 | 3,096 | 23 |
| 10 | ロビンフッド | 2,927 | 24 |

### 출력 구조

```
E:\chaldeas_data\processed\fgo\dialogues\
  by_chapter/    — 139 files (챕터/이벤트별)
  by_character/  — 3,462 files (캐릭터별)
  stats.json     — 전체 통계 + top 50 스피커
  alias_map.json — alias 매핑 정보
```

### 기능

- speaker alias 정규화 (글로벌 + 챕터별)
- 텍스트 마크업 클리닝 ([%1]→[主人公], [#ruby], [&gender], visual effect tags)
- `--main-only`, `--events-only`, `--chapter`, `--stats`, `--dry-run` CLI

## 다음 작업

- Phase 2: `summarize_fgo_stories.py` — AI 요약 (별도 세션, ~$8-10)
