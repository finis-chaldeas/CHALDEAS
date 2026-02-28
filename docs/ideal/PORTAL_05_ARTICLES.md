# PORTAL 05 — 아티클 시스템: 엔티티 링크 + 에디터

> 아키텍처: `PORTAL_01_ARCHITECTURE.md` | 기존 History 시스템: `frontend/HISTORY_SYSTEM.md`

---

## 한 줄 요약

기존 `[Name](entity:type:id)` 문법을 **6가지 엔티티 타입**으로 확장하고,
**통합 검색 API**와 **링크 추천 API**를 제공하여 아티클 작성을 지원.

---

## 엔티티 링크 문법

### 포맷

```
[표시이름](entity:타입:ID)
```

기존 History 시스템에서 이미 사용하는 포맷을 그대로 확장. 신규 문법 없음.

### 지원 타입 (6종)

| 문법 | 타입 | ID 형태 | 클릭 시 동작 | 색상 |
|------|------|---------|------------|------|
| `[잔 다르크](entity:person:12345)` | 인물 | 숫자 | NarrativePanel (오른쪽) | orange `#ff9f43` |
| `[마라톤 전투](entity:event:67890)` | 이벤트 | 숫자 | 글로브 flyTo + NarrativePanel | cyan `#00d4ff` |
| `[아테네](entity:location:111)` | 장소 | 숫자 | 글로브 flyTo | green `#51cf66` |
| `[백년전쟁](entity:shift:222)` | 시프트 | 숫자 | ShiftPanel 열기 | cyan+bold |
| `[Singularity F](entity:item:singularity-f)` | 포털 아이템 | slug | pushDetail(slug) | gold `#e0c068` |
| `[그리스·로마](entity:collection:greece-rome)` | 컬렉션 | slug | pushCollection(slug) | magenta `#ff6b9d` |

> person/event/location/shift = 숫자 ID, item/collection = slug 문자열.

### 에디터 입력 흐름

```
1. 본문에서 [ 를 타이핑
2. → 자동완성 드롭다운 표시 (6종 엔티티 통합 검색)
3. 검색어 입력: [잔 다
4. → /portal/resolve API 결과 표시:
     ☾ 잔 다르크 (person · 1412 ~ 1431)
     ◎ 잔 다르크 처형 (event · 1431)
     ▶ 잔 다르크의 생애 (shift · 8 pages)
     📖 Singularity I: Orleans (item · singularity)
5. 결과 클릭
6. → 본문에 [잔 다르크](entity:person:12345) 삽입
```

---

## 백엔드 API

### 1. `GET /api/v1/portal/resolve` — 통합 엔티티 검색

자동완성용. 6종 엔티티를 한 번에 검색.

```
GET /api/v1/portal/resolve?q=잔다르크&type_filter=person&limit=10

Response:
{
  "query": "잔다르크",
  "results": [
    {
      "type": "person",
      "id": 12345,
      "name": "Joan of Arc",
      "name_ko": "잔 다르크",
      "meta": "1412 ~ 1431"
    }
  ]
}
```

| 파라미터 | 설명 |
|---------|------|
| `q` | 검색어 (필수, min 1자) |
| `type_filter` | person/event/location/shift/item/collection (선택) |
| `limit` | 최대 결과 수 (기본 10, 최대 30) |

**구현 위치**: `backend/app/api/v1/portal.py` (구현 완료)

### 2. `POST /api/v1/portal/suggest-links` — 링크 추천

텍스트를 분석해서 태깅되지 않은 엔티티 이름을 찾아 추천.

```
POST /api/v1/portal/suggest-links
{
  "text": "잔 다르크가 오를레앙에서 전투를 이끌었다.",
  "limit": 10
}

Response:
{
  "suggestions": [
    {
      "type": "person",
      "id": 12345,
      "name": "Joan of Arc",
      "name_ko": "잔 다르크",
      "matched_text": "잔 다르크",
      "tag": "[잔 다르크](entity:person:12345)",
      "importance": 8
    }
  ]
}
```

**알고리즘**:
1. 기존 `[Name](entity:type:id)` 태그에서 이미 태깅된 이름 추출
2. 태그 제거 후 순수 텍스트 추출
3. 중요도 높은 인물(≥5), 이벤트(≥5), 시프트(≥3) 로딩
4. 이름이 텍스트에 등장하지만 미태깅 → 추천
5. 중요도순 정렬

**구현 위치**: `backend/app/api/v1/portal.py` (구현 완료)

---

## 프론트엔드 컴포넌트

### HistoryEditor (수정)

기존 `searchApi.search()` → `portalApi.resolve()` 교체.

| 변경 전 | 변경 후 |
|---------|---------|
| person/event/location 3종만 | 6종 모두 자동완성 |
| `searchApi.search()` 호출 | `portalApi.resolve()` 호출 |
| 아이콘 3종 (☾◎📍) | 아이콘 6종 (☾◎📍▶📖🏛) |

**구현 위치**: `frontend/src/components/history/HistoryEditor.tsx` (구현 완료)

### HistoryViewer (수정)

파싱 패턴을 6종으로 확장. 새 entity type에 대한 클릭 핸들러 추가.

| 변경 전 | 변경 후 |
|---------|---------|
| `(person\|event\|location)` 매칭 | `(person\|event\|location\|shift\|item\|collection)` 매칭 |
| 3종 클릭 핸들러 | 6종 클릭 핸들러 |
| — | `onShiftClick`, `onItemClick`, `onCollectionClick` props 추가 |

**구현 위치**: `frontend/src/components/history/HistoryViewer.tsx` (구현 완료)

### API 클라이언트

```typescript
// frontend/src/api/client.ts
export const portalApi = {
  resolve: (q, params?) => api.get('/portal/resolve', { params: { q, ...params } }),
  suggestLinks: (text, limit?) => api.post('/portal/suggest-links', { text, limit }),
  // ... items, collections, featured
}
```

**구현 위치**: `frontend/src/api/client.ts` (구현 완료)

---

## history_entities 저장 규칙

`history_entities` 테이블의 `entity_id`는 Integer 컬럼.

| 엔티티 타입 | junction table 저장 | 본문 렌더링 |
|------------|-------------------|------------|
| person | O (숫자 ID) | O |
| event | O (숫자 ID) | O |
| location | O (숫자 ID) | O |
| shift | O (숫자 ID) | O |
| item | X (slug → 정수 불가) | O |
| collection | X (slug → 정수 불가) | O |

item/collection은 본문 텍스트에서 렌더링되지만 junction table에는 저장되지 않음.
이는 의도된 설계: item/collection은 포털 네비게이션이지 엔티티 관계가 아님.

---

## CSS 스타일

```css
/* 기존 entity-tag 색상에 추가 */
.entity-tag-shift { color: #00d4ff; font-weight: 600; }
.entity-tag-item { color: #e0c068; }
.entity-tag-collection { color: #ff6b9d; }

/* 자동완성 메타 텍스트 */
.autocomplete-meta {
  font-size: 0.65rem;
  color: var(--chaldea-text-dim, #888);
  margin-left: auto;
}
```

**구현 위치**: `frontend/src/components/history/history.css` (구현 완료)

---

## 아티클 에디터 (ArticleEditor) — 미래 작업

### 기존 HistoryEditor와의 관계

| 항목 | HistoryEditor | ArticleEditor (미래) |
|------|--------------|---------------------|
| 대상 | histories 테이블 | portal_items 테이블 |
| 작성자 | user (기본) | system + user |
| 링크 문법 | `[Name](entity:type:id)` | 동일 |
| 본문 | 단일 body 텍스트 | sections 배열 (JSONB) |
| 카테고리 | essay, biography, ... | singularity, history, ... |

**결정**: 두 에디터를 **별도 유지**. 용도가 다름.
- HistoryEditor → 짧은 에세이 (1~4 문단). 기존 유지.
- ArticleEditor → 긴 아티클 (섹션 단위). 포털 아이템 편집용. 별도 구현 예정.

---

## 파일 변경 목록

| 파일 | 작업 | 상태 |
|------|------|------|
| `backend/app/api/v1/portal.py` | `/resolve`, `/suggest-links` 엔드포인트 | 완료 |
| `backend/app/api/v1/histories.py` | 엔티티 태그 패턴 6종 확장 | 완료 |
| `backend/app/models/history.py` | entity_type 컬럼 길이 확장 | 완료 |
| `frontend/src/api/client.ts` | `portalApi` 추가 | 완료 |
| `frontend/src/components/history/HistoryEditor.tsx` | `/portal/resolve` 연동, 6종 아이콘 | 완료 |
| `frontend/src/components/history/HistoryViewer.tsx` | 6종 파싱+핸들러, 신규 props | 완료 |
| `frontend/src/components/history/history.css` | shift/item/collection 색상 | 완료 |

---

## 관련 문서

| 문서 | 내용 |
|------|------|
| `PORTAL_01_ARCHITECTURE.md` | 중첩 모달 (pushDetail, pushCollection) |
| `PORTAL_03_COLLECTIONS.md` | PortalItemDetail에서 엔티티 링크 렌더링 |
| `frontend/HISTORY_SYSTEM.md` | 기존 History 에디터/뷰어 설계 |
