# Session Log: 2026-02-24 i18n Translation Fix + Roadmap

## Session Info
- **Purpose**: Fix API not returning translation fields (ko/ja) + Create comprehensive i18n roadmap
- **Branch**: frontend-v4-recovered

---

## Part 1: Translation Delivery Fix (Completed)

### Problem
API endpoints were not returning `name_ko`, `name_ja`, `title_ko`, `title_ja` fields.
DB has the translations ($100+ invested), but API response builders omitted them.
Frontend `getLocalizedText()` already handles fallback (preferred → English → other lang), but had no data to work with.

### DB Translation Coverage (Current)

| Entity | Field | Total | KO | KO% | JA | JA% |
|--------|-------|-------|-----|------|-----|------|
| **events** | title | 28,331 | 11,386 | 40.2% | 10,280 | 36.3% |
| **persons** | name | 190,710 | 121,266 | 63.6% | 63,690 | 33.4% |
| **locations** | name | 17,723 | 17,120 | **96.6%** | 17,182 | **96.9%** |
| **event_details** | description | 28,331 | 10,280 | 36.3% | - | - |
| **person_details** | biography | 175,576 | 0 | **0.0%** | 0 | **0.0%** |
| **location_details** | description | 15,928 | 0 | **0.0%** | 0 | **0.0%** |

### By Importance (Events)

| Importance | Total | KO | KO% | JA | JA% |
|-----------|-------|-----|------|-----|------|
| 5 (최상) | 1,125 | 1,122 | **100%** | 1,122 | **100%** |
| 4 (상) | 2,299 | 2,299 | **100%** | 2,299 | **100%** |
| 3 (중) | 6,875 | 6,863 | **100%** | 6,859 | **100%** |
| 2 (하) | 12,393 | 900 | 7% | 0 | 0% |
| 1 (최하) | 5,639 | 202 | 4% | 0 | 0% |

### Files Modified

| # | File | Changes |
|---|------|---------|
| 1 | `backend/app/api/v1/events.py` | `_batch_fetch_persons`: +name_ko/ja, `event_to_dict`: +title_ja +location name_ko/ja, `get_event`: persons/locations/children +ko/ja |
| 2 | `backend/app/api/v1/feed.py` | events SQL: +title_ja +location_name_ko/ja, participants: +name_ko/ja, persons SQL: +name_ja +birthplace_name_ko/ja |
| 3 | `backend/app/api/v1/persons.py` | network: +name_ja |
| 4 | `backend/app/api/v1/locations.py` | Already had name_ko/ja (no changes needed) |
| 5 | `backend/app/api/v1_new/globe.py` | GlobeMarker: +title_ko/ja, AnchorLocation: +name_ja, LocationNode: +name_ja, node events: +title_ja, all SQL queries updated |
| 6 | `backend/app/schemas/person.py` | PersonBase: +name_ja, PersonRelation: +name_ja, FlowEvent: +title_ja, PersonFlow: +name_ja |
| 7 | `backend/app/services/person_service.py` | get_related_persons: +name_ja, get_person_flow: +title_ja +name_ja |

### Frontend Fallback (Already Working)

`frontend/src/store/settingsStore.ts` → `getLocalizedText()`:
1. Try preferred language (ko/ja)
2. Fallback to English
3. Fallback to other available language
4. Return empty string

---

## Part 2: Comprehensive i18n Roadmap

### Priority 1: IMMEDIATE (코드만 수정, 비용 $0)

#### 1-1. Backend 재시작 + 검증
- `uvicorn app.main:app --reload --port 8100`
- curl로 주요 API 응답에 `_ko`, `_ja` 필드 존재 확인
- 프론트엔드에서 실제로 한국어/일본어 표시 확인

#### 1-2. Frontend에서 `getLocalizedText` 미사용 컴포넌트 점검
일부 컴포넌트가 `getLocalizedText()` 대신 하드코딩으로 `entity.title` 또는 `entity.name`만 사용할 수 있음.
점검 대상:
- `GlobeContainer.tsx` — hero card 제목, location node 이름
- `ViewportFeed.tsx` — 피드 카드 제목/이름
- `NarrativePanel.tsx` — 이벤트/인물 이름
- `EventDetailPanel.tsx` — 상세 패널 제목
- `PersonDetailView.tsx` — 인물 상세
- `LocationDetailView.tsx` — 장소 상세
- `SourceBrowser.tsx` — 출처 목록
- `HeroCardDeck.tsx` (mobile) — 히어로 카드

---

### Priority 2: SHORT-TERM (비용 ~$5-15)

#### 2-1. Importance 2-1 이벤트 번역 (17,000개)
현재 importance 3+ 이벤트는 100% 번역 완료.
importance 2 (12,393개)와 1 (5,639개)은 거의 미번역.

**방법**: GPT-5-mini 배치 번역
```
비용 추정:
- 18,032 events × ~50 tokens/title × 2 languages
- ≈ 1.8M tokens → ~$0.45 (GPT-5-mini input+output)
```

#### 2-2. Person biography 번역 (175,576개 중 상위만)
biography_ko, biography_ja가 전부 0%.
전부 번역은 비현실적 → **상위 인물만 선택적 번역**.

**추천 전략**:
- QRank top 10,000 인물의 biography만 번역
- 나머지는 영어 그대로 (fallback)

```
비용 추정:
- 10,000 persons × ~300 tokens/bio × 2 languages
- ≈ 6M tokens → ~$1.50 (GPT-5-mini)
```

#### 2-3. Location description 번역 (15,928개)
location_details.description_ko가 전부 0%.

**추천 전략**:
- 이벤트가 5개 이상인 주요 도시만 (~500개)
- 나머지는 영어 fallback

```
비용 추정:
- 500 locations × ~500 tokens/desc × 2 languages
- ≈ 500K tokens → ~$0.13
```

---

### Priority 3: MEDIUM-TERM (비용 ~$10-20)

#### 3-1. UI 문자열 번역 완성
`frontend/src/i18n/locales/` 파일들 (en.json, ko.json, ja.json)에서
누락된 키 확인 + 번역 추가.

현재 있는 주요 키:
- common, globe, navigator, detail, narrative, sources 등

필요한 추가 키:
- Hero card labels ("Battle", "Treaty" 등 카테고리 이름)
- Feed 컨텍스트 문자열 ("X events", "Notable figure" 등)
- Error messages, empty states

#### 3-2. Event description 일본어 번역
event_details.description은 한국어 10,280개 있지만 일본어 컬럼 자체가 없을 수 있음.
(DB 스키마 확인 필요 → `description_ja` 컬럼 존재 여부)

#### 3-3. Entity Narrative 번역
entity_narratives 테이블의 narrative, significance, causes, consequences.
현재 영어만. LLM 생성이므로 다국어 생성으로 전환 가능.

---

### Priority 4: LONG-TERM (아키텍처)

#### 4-1. 검색 다국어 지원
현재 검색은 영어 title만 매칭.
- BM25 인덱스에 title_ko, title_ja 추가
- 한국어/일본어 쿼리 → 해당 언어 필드 우선 검색

#### 4-2. 자동 번역 파이프라인
새로운 이벤트/인물 추가 시 자동으로 ko/ja 번역.
- DB trigger or post-insert hook
- GPT-5-mini 비동기 번역

#### 4-3. 번역 품질 검수
LLM 번역이므로 오류 가능. 커뮤니티 리뷰 시스템 고려.

---

## Summary: 비용 대비 효과

| 작업 | 비용 | 효과 | 우선순위 |
|------|------|------|---------|
| API 번역 필드 전달 (완료) | $0 | **즉시 반영** — imp 3+ 이벤트, 인물, 장소 모두 한국어 표시 | ✅ 완료 |
| Frontend 컴포넌트 점검 | $0 | getLocalizedText 누락 수정 | P1 |
| Imp 2-1 이벤트 제목 번역 | ~$0.50 | 나머지 18,000 이벤트 한국어/일본어 | P2 |
| Person biography 번역 (top 10k) | ~$1.50 | 주요 인물 전기 다국어 | P2 |
| Location description 번역 (top 500) | ~$0.13 | 주요 도시 설명 다국어 | P2 |
| UI 문자열 번역 | $0 | 인터페이스 완전 다국어 | P3 |
| Entity narrative 번역 | ~$5 | AI 서사 다국어 | P3 |
| 검색 다국어 | $0 | 한국어/일본어 검색 가능 | P4 |
| 자동 번역 파이프라인 | ~$2/month | 신규 데이터 자동 번역 | P4 |

**총 예상 비용**: ~$10-15 (일회성) + ~$2/month (자동 번역)

---

## Next Immediate Steps

1. **백엔드 재시작** → 번역 필드 전달 확인
2. **프론트엔드 컴포넌트 점검** → `getLocalizedText` 미사용 곳 수정
3. **imp 2-1 이벤트 배치 번역 스크립트 작성** (optional, 유저 결정)
