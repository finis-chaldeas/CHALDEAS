# 세션 로그: 2026-02-02 통합 스키마 추출

## 세션 정보
- **목적**: 통합 스키마로 Wikipedia/Gutenberg에서 이벤트 데이터 추출

## 통합 스키마 구조

```
sources      - 출처 (Wikipedia 문서, Gutenberg 책)
links        - 엔티티 간 연결 (event→person, event→location 등)
mentions     - 각 연결의 증거 텍스트
tags         - 그룹 태그 (French Revolution, Napoleonic Wars 등)
entity_tags  - 엔티티-태그 매핑
```

## 핵심 매칭 로직

1. Wikipedia 문서에서 링크 추출 (예: `[[Napoleon]]`)
2. sitelinks로 매칭: Wikipedia 제목 → Wikidata QID → DB entity ID
3. 매칭 실패 시 이름으로 fallback 시도
4. 모든 연결에 증거(evidence_raw) 필수 저장

## 추출 현황

### 이벤트 100개 파일 (events_100.txt)
| 단계 | 상태 |
|------|------|
| 스크립트 준비 | ✅ 완료 |
| 10개 테스트 | ✅ 완료 |
| 100개 전체 | 🔄 진행 중 |

### DB 현황 (2026-02-02 기준)
- sources: 36개
- links: 9,596개
- mentions: 17,660개
- tags: 55개
- entity_tags: 6,165개

### 이벤트별 mentions 수 (상위)
1. French Revolution: 2,360
2. American Revolutionary War: 1,458
3. Battle of Waterloo: 1,412
4. World War I: 1,328
5. War of 1812: 957
6. American Civil War: 951

## 사용 파일

- `poc/scripts/unified/extract_wikipedia.py` - Wikipedia 추출
- `poc/scripts/unified/extract_gutenberg_llm.py` - Gutenberg LLM 추출
- `poc/scripts/unified/fetch_wiki_sitelinks.py` - Wikidata sitelinks 수집
- `poc/data/wikipedia_extract/wiki_sitelinks.json` - sitelinks 매핑 (291,204개)
- `poc/data/events_100.txt` - 추출 대상 이벤트 100개

## 다음 작업

1. [ ] 100개 이벤트 추출 완료 확인
2. [ ] 전체 56,567개 이벤트 배치 추출 스크립트
3. [ ] Backend API 새 테이블 연동
4. [ ] 구 테이블 정리 (event_persons, event_relationships 등)
