# Phase 4: 크로스 링킹 + 컬렉션

**선행 조건**: Phase 1-3 (콘텐츠 생성 완료)
**비용**: $0
**예상 시간**: ~10분
**DB 반영**: No (YAML 수정만, DB는 카드 시스템 정리 때)

---

## 목표

모든 FGO 아티클에 엔티티 링크 삽입 + 컬렉션 구조 정의

## 작업

### 4-1. 엔티티 링킹

`link_article_entities.py --mode db` — Phase 1-3에서 생성된 모든 YAML에 적용.

```bash
cd backend
PYTHONPATH=. python scripts/link_article_entities.py --mode db
# 기존 30개 history 아티클 + 30 서번트 칼럼 + 15 특이점/LB = 75+ 파일
```

결과: `[Gilgamesh](entity:person:12345)` 형태 태그가 본문에 삽입됨.

### 4-2. 컬렉션 구조 정의

YAML로 컬렉션 정의 (DB 반영은 나중에):

```yaml
# collections/fgo-singularities.yaml
slug: fgo-singularities
collection_type: fgo_storyline
title: "FGO Main Story — Singularities"
title_ko: "FGO 메인 스토리 — 특이점"
tags: ["fgo", "singularity", "main-story"]
entries:
  - type: portal_item
    slug: singularity-f
    sort_order: 0
  - type: portal_item
    slug: singularity-1
    sort_order: 1
  # ... singularity-7

# collections/fgo-lostbelts.yaml
slug: fgo-lostbelts
collection_type: fgo_storyline
title: "FGO Main Story — Lostbelts"
title_ko: "FGO 메인 스토리 — 이문대"
tags: ["fgo", "lostbelt", "main-story"]
entries:
  - type: portal_item
    slug: lostbelt-1
    sort_order: 0
  # ... lostbelt-7

# collections/fgo-servant-columns.yaml
slug: fgo-servant-columns
collection_type: content
title: "Servant Columns — History Meets Fate"
title_ko: "서번트 칼럼 — 역사와 페이트"
tags: ["fgo", "servant", "history"]
entries:
  - type: portal_item
    slug: servant-gilgamesh
    sort_order: 0
  # ... 30명

# collections/fgo-history-bridge.yaml
slug: fgo-history-bridge
collection_type: theme
title: "Learn History Through FGO"
title_ko: "FGO로 배우는 역사"
tags: ["fgo", "history", "education"]
entries:
  - type: shift
    slug: mesopotamia-uruk-civilization
    note: "Singularity VII의 실제 역사"
  - type: shift
    slug: hundred-years-war
    note: "Singularity I의 실제 역사"
  # ...
```

### 4-3. related_servants 자동 채움

서번트 칼럼:
- 해당 서번트 + 같은 시대/신화 서번트 (본드 텍스트에서 언급된 인물)

특이점/LB:
- 스토리 요약의 key_characters에서 서번트 목록 추출
- 대사 빈도 상위 서번트

### 4-4. related_event_ids 자동 채움

```python
# 서번트 → person_id → event_persons → events
SELECT e.id FROM events e
JOIN event_persons ep ON ep.event_id = e.id
WHERE ep.person_id = {person_id}
AND e.importance >= 3
ORDER BY e.importance DESC
LIMIT 10;

# 특이점 → year + region → events
SELECT id FROM events
WHERE date_start BETWEEN {year-100} AND {year+100}
AND importance >= 4
ORDER BY importance DESC
LIMIT 10;
```

## 출력

- 모든 YAML 파일에 entity tag 삽입됨
- `backend/scripts/output/collections/*.yaml` — 컬렉션 정의 4개
- DB 직접 반영 안 함
