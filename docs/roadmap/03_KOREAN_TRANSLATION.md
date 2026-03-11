# 03. 한국어 번역 커버리지 확대

## 문제

한국 유저 대상 서비스인데 시프트 한국어 커버리지가 36%에 불과.

## 현재 상태

| 중요도 | 전체 페이지 | 번역됨 | 커버리지 |
|--------|-----------|--------|---------|
| 5 | 3,613 | 1,673 | 46.3% |
| 4 | 2,562 | 997 | 38.9% |
| 3 | 1,310 | 369 | 28.2% |
| 2 | 1,860 | 325 | 17.5% |
| 1 | 22 | 4 | 18.2% |
| **합계** | **9,367** | **3,368** | **36.0%** |

시프트 단위:
- 완전 번역 (모든 페이지): 113/896 (12.6%)
- 부분 번역: 569/896 (63.5%)
- 번역 없음: 214/896 (23.9%)

기타 번역 현황:
- `period_narratives` headline_ko: 42/391 (10.7%)
- `entity_narratives` significance_ko: 7,412/7,412 (100%)

## 02번과의 관계

**`--enhance`가 `page_narrative_ko`를 생성한다.** 따라서:
- imp4+ 시프트 → 02번 위젯 배치 enhance 실행 시 **동시에 해결**
- imp3 이하 → 별도 번역 작업 필요

## 실행 계획

### 1단계: --enhance로 커버 (imp4+)

02번 태스크와 동일. enhance가 page_narrative_ko + widgets를 동시에 생성.
- imp5: 3,613p 중 1,940p 미번역 → enhance로 해결
- imp4: 2,562p 중 1,565p 미번역 → enhance로 해결

### 2단계: 이미 위젯 있는 페이지의 누락 번역

위젯은 있는데 page_narrative_ko가 없는 페이지 (소수):

```sql
SELECT COUNT(*) FROM chain_segments
WHERE widgets IS NOT NULL AND jsonb_array_length(widgets) > 0
  AND (page_narrative_ko IS NULL OR LENGTH(page_narrative_ko) < 50);
```

이런 페이지는 `--enhance --force`로 재생성하거나, narrative만 별도 번역.

### 3단계: period_narratives 번역 (별도)

기존 `translate_period_narratives.py` 스크립트 사용:

```bash
cd backend
python scripts/translate_period_narratives.py --global-only --limit 55   # 나머지 global 55개
python scripts/translate_period_narratives.py --regional-only --limit 100  # regional 상위 100개
```

## 목표

| 항목 | 현재 | 목표 |
|------|------|------|
| imp5 페이지 번역 | 46% | 95%+ |
| imp4 페이지 번역 | 39% | 90%+ |
| 완전 번역 시프트 | 12.6% | 50%+ (imp4+) |
| period_narratives headline_ko | 10.7% | 50%+ |

## 비용 추정

enhance(02번)와 동시 실행이므로 추가 비용 없음.
period_narratives 번역만 별도: ~$5-10 (gpt-5.1-chat-latest 사용)
