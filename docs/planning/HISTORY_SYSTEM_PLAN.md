# CHALDEAS 콘텐츠 구조 종합 기획

**작성일**: 2026-02-23
**상태**: 기획 단계

---

## 1. 전체 콘텐츠 계층 (Big Picture)

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Raw Data (DB 엔티티)                               │
│  Events 28,331 · Persons 190,710 · Locations 17,723          │
│  Sources 163,706 (Wikipedia + Wikisource + IA)               │
│  → 이건 이미 있음. 건드릴 필요 없음.                          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: 엔티티별 큐레이션 (entity_narratives)              │
│  이벤트 요약 2,332건 · 인물 요약 1,524건 · 시대 요약 391건    │
│  각각 간결한 요약 (100~300단어). GPT-5.1 자동생성.            │
│  → 이것도 이미 있음. 간결하게 유지.                           │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: 히스토리 (NEW — histories 테이블)                   │
│  여러 엔티티를 엮는 서사. A4 1페이지 분량. 본문에 엔티티 태깅. │
│  계층적: 백년전쟁 히스토리 → 잔다르크 히스토리 (하위)          │
│  연계적: 히스토리 간 상호 링크 (관련 히스토리)                 │
│  작성자: system(큐레이션 자동) / user(수동 작성)              │
│  → 기존 SHEBA 투어의 DB 확장판. 같은 개념.                   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: 사용자 경험                                        │
│  글로브(공간) + 타임라인(시간) + 히스토리탭(서사)              │
│  히스토리 읽다가 태깅된 인물 클릭 → 인물 상세                  │
│  히스토리 읽다가 하위 히스토리 클릭 → 그 히스토리로 이동        │
│  히스토리 읽다가 관련 히스토리 클릭 → 다른 히스토리로 분기      │
└─────────────────────────────────────────────────────────────┘
```

### Layer 2 vs Layer 3 역할 분담

| | Layer 2 (엔티티 요약) | Layer 3 (히스토리) |
|---|---|---|
| **단위** | 개별 이벤트/인물 1개 | 여러 엔티티를 엮은 서사 |
| **분량** | 100~300단어 (간결) | ~4문단, A4 1페이지 |
| **목적** | "이게 뭔지" 빠른 설명 | "왜 중요한지, 어떻게 연결되는지" |
| **예시** | "테르모필레 전투: 480 BCE..." | "페르시아 전쟁: 다리우스~크세르크세스까지 흐름" |
| **생성** | LLM 자동 only | LLM 자동 + 사용자 작성 |
| **연계** | 없음 (독립) | 계층(부모↔자식) + 상호 링크 |

---

## 2. 히스토리 = 투어 (같은 개념, 확장)

**히스토리와 투어는 별개가 아니다.** 기존 하드코딩 투어(`shebaEpisodes.ts`, 18개)를 DB 기반으로 확장.

```
기존 SHEBA 투어:
  - 하드코딩 (shebaEpisodes.ts)
  - 코드 수정 없이 추가 불가
  - tourSteps[]로 글로브 자동 이동
  - 18개 고정

확장 히스토리:
  - DB 기반 (histories 테이블)
  - 무한 추가 가능
  - 본문 텍스트 + 엔티티 태깅
  - 계층 구조 (부모↔자식 히스토리)
  - 관련 히스토리 간 상호 링크
  - LLM 자동생성 + 사용자 수동 작성
```

**향후**: 기존 18개 ShebaEpisode도 DB histories로 마이그레이션 가능 (tourSteps → body 변환)

---

## 3. 히스토리 흐름 예시

### 예: 백년전쟁

```
┌─────────────────────────────────────────┐
│ 📜 백년전쟁 (1337~1453)                  │  ← 최상위 히스토리
│                                         │
│ 📍 프랑스, 잉글랜드                      │
│ 👤 에드워드 3세 · 필리프 6세             │  ← featured entities
│                                         │
│ 1337년, [에드워드 3세](entity:person:XX) │  ← 본문 + 엔티티 태깅
│ 가 프랑스 왕위를 주장하며 전쟁이          │
│ 시작되었다. [크레시 전투](entity:event:XX)│
│ 에서 잉글랜드 장궁병이 프랑스 기사를      │
│ 압도했고...                              │
│                                         │
│ ────────────────────────────────────── │
│ 📎 하위 히스토리:                        │
│   📜 크레시-푸아티에 (1346~1356)         │  ← 클릭 → 하위 히스토리
│   📜 잔다르크와 오를레앙 (1429~1431)      │  ← 클릭 → 하위 히스토리
│   📜 전쟁의 종결 (1449~1453)             │
│                                         │
│ 🔗 관련 히스토리:                        │
│   📜 흑사병과 유럽의 변화 (1347~1353)     │  ← 클릭 → 연계 히스토리
│   📜 장미전쟁 (1455~1487)                │  ← 백년전쟁의 결과
└─────────────────────────────────────────┘
         │
         ├── 클릭: "잔다르크와 오를레앙"
         ↓
┌─────────────────────────────────────────┐
│ 📜 잔다르크와 오를레앙 (1429~1431)        │  ← 하위 히스토리
│ ← 백년전쟁 (상위로 돌아가기)              │
│                                         │
│ 📍 오를레앙, 랭스, 루앙                   │
│ 👤 잔다르크 · 샤를 7세                   │
│                                         │
│ 1429년, 17세의 [잔다르크](entity:person:XX)│
│ 가 신의 계시를 받았다고 주장하며           │
│ [오를레앙 포위전](entity:event:XX)에       │
│ 참전한다...                              │
│                                         │
│ 🔗 관련 히스토리:                        │
│   📜 잔다르크의 재판과 복권               │  ← 관련 히스토리
└─────────────────────────────────────────┘
```

### 핵심 네비게이션

1. **엔티티 태그 클릭** → `[잔다르크]` 클릭 → 인물 상세 패널 열림
2. **하위 히스토리 클릭** → 같은 뷰어에서 하위 히스토리로 전환 (뒤로가기 가능)
3. **관련 히스토리 클릭** → 연계된 다른 히스토리로 분기
4. **상위로 돌아가기** → breadcrumb 스타일 네비게이션

---

## 4. 엔티티 태깅 포맷

### 저장 형식

```
[나폴레옹](entity:person:12345)
[워털루 전투](entity:event:67890)
[파리](entity:location:11111)
```

### 작성 UX

1. 본문에서 `[` 입력
2. 다음 글자들로 `/api/v1/search?q=...&type=all` 검색 (debounce 300ms)
3. 드롭다운에 person/event/location 결과 표시 (아이콘으로 구분)
4. 선택 → `[선택된 이름](entity:type:id)` 삽입
5. 본문에서는 `[선택된 이름]` 부분만 하이라이트로 보임

### 렌더링 UX

- 본문의 `[이름](entity:type:id)` → 클릭 가능한 인라인 링크
- 클릭 → 해당 엔티티 상세 패널 열기 (person/event/location에 따라 다른 패널)
- 호버 → 간단한 프리뷰 (이름, 시대, 한줄 설명) — 선택적, 나중

---

## 5. DB 스키마

### histories 테이블

```sql
CREATE TABLE histories (
    id SERIAL PRIMARY KEY,

    -- 메타
    title VARCHAR(300) NOT NULL,
    title_ko VARCHAR(300),
    title_ja VARCHAR(300),
    summary VARCHAR(500),          -- 1-2줄 요약

    -- 시공간 범위
    era_start INTEGER,             -- BCE = 음수
    era_end INTEGER,

    -- 본문
    body TEXT NOT NULL,             -- Markdown + [name](entity:type:id) 태깅
    body_ko TEXT,
    body_ja TEXT,

    -- 분류
    category VARCHAR(50) DEFAULT 'essay',
    -- essay: 일반 서사
    -- biography: 인물 중심
    -- causal_chain: 인과관계 흐름
    -- era_overview: 시대 종합
    -- comparison: 비교 분석
    tags TEXT[],                    -- PostgreSQL 배열

    -- 계층 구조 (부모↔자식)
    parent_history_id INTEGER REFERENCES histories(id),
    sort_order INTEGER DEFAULT 0,   -- 같은 부모 내 정렬 순서

    -- 작성자
    author_type VARCHAR(20) DEFAULT 'system',  -- system/user
    author_name VARCHAR(100),

    -- 상태
    status VARCHAR(20) DEFAULT 'published',  -- draft/published/archived
    importance INTEGER DEFAULT 3,   -- 1-5 (피드 정렬용)

    -- 타임스탬프
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### history_entities 테이블

```sql
CREATE TABLE history_entities (
    id SERIAL PRIMARY KEY,
    history_id INTEGER REFERENCES histories(id) ON DELETE CASCADE,

    -- 연결된 엔티티
    entity_type VARCHAR(10) NOT NULL,  -- 'person', 'event', 'location'
    entity_id INTEGER NOT NULL,
    entity_name VARCHAR(255),          -- 표시명 (스냅샷)

    -- 역할
    role VARCHAR(20) DEFAULT 'mentioned',
    -- 'featured': 헤더에 표시되는 핵심 엔티티 (사전 확인용)
    -- 'mentioned': 본문 [태그]로 언급된 엔티티
    -- 'location': 히스토리의 공간 범위 지정

    UNIQUE(history_id, entity_type, entity_id)
);
```

### history_relations 테이블 (관련 히스토리 간 링크)

```sql
CREATE TABLE history_relations (
    id SERIAL PRIMARY KEY,
    from_history_id INTEGER REFERENCES histories(id) ON DELETE CASCADE,
    to_history_id INTEGER REFERENCES histories(id) ON DELETE CASCADE,
    relation_type VARCHAR(30) DEFAULT 'related',
    -- 'related': 일반 관련
    -- 'sequel': 후속
    -- 'prequel': 전편
    -- 'parallel': 같은 시대 다른 지역
    -- 'consequence': 결과/영향
    label VARCHAR(200),            -- 관계 설명 (예: "백년전쟁의 결과")

    UNIQUE(from_history_id, to_history_id)
);
```

### 인덱스

```sql
CREATE INDEX idx_he_history ON history_entities(history_id);
CREATE INDEX idx_he_entity ON history_entities(entity_type, entity_id);
CREATE INDEX idx_histories_era ON histories(era_start, era_end);
CREATE INDEX idx_histories_status ON histories(status);
CREATE INDEX idx_histories_parent ON histories(parent_history_id);
CREATE INDEX idx_hr_from ON history_relations(from_history_id);
CREATE INDEX idx_hr_to ON history_relations(to_history_id);
```

### 설계 포인트

- **history_entities**: locations + featured persons + mentioned entities 모두 통합 (role로 구분)
- **parent_history_id**: 계층 구조. 백년전쟁 → 잔다르크 세션 (자식)
- **history_relations**: 계층과 별개로 히스토리 간 상호 연계 (흑사병 ↔ 백년전쟁)
- **sort_order**: 같은 부모 하위의 자식들 순서 (크레시→푸아티에→잔다르크→종결)

---

## 6. API 설계

```
# CRUD
POST   /api/v1/histories                    # 생성
GET    /api/v1/histories                    # 목록 (필터: category, era, tag, parent_id)
GET    /api/v1/histories/{id}               # 상세 (body + entities + children + relations)
PUT    /api/v1/histories/{id}               # 수정
DELETE /api/v1/histories/{id}               # 삭제

# 역참조 (이 엔티티가 언급된 히스토리들)
GET    /api/v1/persons/{id}/histories       # 이 인물 관련 히스토리
GET    /api/v1/events/{id}/histories        # 이 이벤트 관련 히스토리
GET    /api/v1/locations/{id}/histories     # 이 장소 관련 히스토리
```

### GET /histories/{id} 응답 예시

```json
{
  "id": 1,
  "title": "Hundred Years' War",
  "title_ko": "백년전쟁",
  "summary": "1337~1453, 잉글랜드와 프랑스 간 116년 전쟁",
  "era_start": 1337,
  "era_end": 1453,
  "body": "[에드워드 3세](entity:person:XX)가 프랑스 왕위를 주장하며...",
  "category": "causal_chain",
  "tags": ["중세", "전쟁", "프랑스", "잉글랜드"],
  "author_type": "system",
  "importance": 5,

  "entities": [
    {"entity_type": "person", "entity_id": 123, "entity_name": "에드워드 3세", "role": "featured"},
    {"entity_type": "person", "entity_id": 456, "entity_name": "필리프 6세", "role": "featured"},
    {"entity_type": "location", "entity_id": 789, "entity_name": "프랑스", "role": "location"},
    {"entity_type": "event", "entity_id": 101, "entity_name": "크레시 전투", "role": "mentioned"}
  ],

  "parent": null,
  "children": [
    {"id": 2, "title": "크레시-푸아티에", "era_start": 1346, "era_end": 1356},
    {"id": 3, "title": "잔다르크와 오를레앙", "era_start": 1429, "era_end": 1431},
    {"id": 4, "title": "전쟁의 종결", "era_start": 1449, "era_end": 1453}
  ],

  "related_histories": [
    {"id": 10, "title": "흑사병과 유럽의 변화", "relation_type": "parallel", "label": "같은 시대"},
    {"id": 11, "title": "장미전쟁", "relation_type": "consequence", "label": "백년전쟁의 결과"}
  ]
}
```

---

## 7. 프론트엔드 설계

### 7-1. Navigator History 탭 (목록)

```
┌──────────────────────────┐
│ [+ 새 히스토리]            │
│ ─────────────────────── │
│ [카테고리 ▼] [시대 ▼]     │
│ ─────────────────────── │
│ 📜 페르시아 전쟁           │
│    BC 499 ~ BC 449 · 12개 │
│    └ 📜 테르모필레와 살라미스│
│    └ 📜 플라타이아         │
│ ─────────────────────── │
│ 📜 백년전쟁               │
│    1337 ~ 1453 · 15개     │
│    └ 📜 크레시-푸아티에    │
│    └ 📜 잔다르크와 오를레앙 │
│    └ 📜 전쟁의 종결        │
│ ─────────────────────── │
│ 📜 프랑스 혁명             │
│    1789 ~ 1799 · 20개     │
└──────────────────────────┘
```

- 최상위 히스토리만 기본 표시
- 하위 히스토리는 들여쓰기로 표시 (접기/펼치기)
- 클릭 → HistoryViewer 열기

### 7-2. HistoryViewer (읽기 패널)

오른쪽 오버레이. EventDetailPanel과 같은 위치.

```
┌──────────────────────────────────┐
│ ← 백년전쟁 (상위)         [편집] ✕│  ← breadcrumb + 닫기
│                                  │
│ 잔다르크와 오를레앙               │
│ 1429 ~ 1431 · biography         │
│ ────────────────────────────── │
│ 📍 오를레앙 · 랭스 · 루앙         │  ← location entities
│ 👤 잔다르크 · 샤를 7세            │  ← featured entities (클릭 가능)
│ ────────────────────────────── │
│                                  │
│ 1429년, 17세의 [잔다르크]가       │  ← 본문. [태그] = 클릭 링크
│ 신의 계시를 받았다고 주장하며      │
│ [오를레앙 포위전]에 참전한다.      │
│ ...                              │
│                                  │
│ ────────────────────────────── │
│ 📎 하위 히스토리: (없음)          │
│ 🔗 관련:                         │
│   📜 잔다르크의 재판과 복권       │  ← 클릭 → 해당 히스토리
│ ────────────────────────────── │
│ 🏷️ 중세, 프랑스, 잔다르크        │
│ 📎 8 엔티티 언급                  │
└──────────────────────────────────┘
```

**네비게이션**:
- `← 백년전쟁`: 상위 히스토리로 이동 (breadcrumb)
- 하위 히스토리 클릭: 같은 뷰어에서 전환
- 관련 히스토리 클릭: 같은 뷰어에서 전환
- 엔티티 태그 클릭: 인물/이벤트/장소 상세 패널 열기
- [편집] 버튼: HistoryEditor 열기

### 7-3. HistoryEditor (작성/편집 모달)

```
┌──────────────────────────────────────────┐
│ 히스토리 작성                    [저장] [✕]│
│ ──────────────────────────────────────── │
│ 제목: [                              ]   │
│ 시대: [     ] ~ [     ] (BCE=음수)       │
│ 카테고리: [essay ▼]                      │
│ 상위 히스토리: [백년전쟁 ✕] (선택)        │
│ ──────────────────────────────────────── │
│ 📍 장소: [오를레앙 ✕] [랭스 ✕] [+ 추가]   │
│ 👤 주요 엔티티: [잔다르크 ✕] [+ 추가]     │
│ ──────────────────────────────────────── │
│ 본문 (최대 4문단, A4 1페이지 권장):       │
│ ┌──────────────────────────────────────┐ │
│ │ 1429년, 17세의 [잔다                 │ │
│ │               ┌──────────────┐      │ │
│ │               │ 🔍 "잔다"     │      │ │
│ │               │ 👤 잔다르크   │      │ │
│ │               │ 📅 잔다르크처형│      │ │
│ │               └──────────────┘      │ │
│ └──────────────────────────────────────┘ │
│ 태그: [중세] [프랑스] [+ 추가]           │
│ ──────────────────────────────────────── │
│ 🔗 관련 히스토리: [잔다르크의 재판 ✕] [+] │
│ ──────────────────────────────────────── │
│ 💡 4문단 초과 시 분할을 권장합니다        │
└──────────────────────────────────────────┘
```

---

## 8. 큐레이션 파이프라인 연계

### 현재 파이프라인 (curate_with_llm.py)

```
Step 0: 소스 캐시
Step 1: 이벤트 내러티브 (entity_narratives)
Step 2: 이벤트 관계 강화 (event_relationships)
Step 3: 피리어드 내러티브 업그레이드 (period_narratives)
Step 4: 품질 리포트
Step 5: 인물 내러티브 (entity_narratives)
```

### 추가할 Step 6: 히스토리 자동생성

```
Step 6: 히스토리 생성
  입력:
    - parent_event 기준으로 이벤트 그룹핑
    - 해당 이벤트들의 entity_narratives 수집
    - 관련 인물들의 entity_narratives 수집
    - period_narratives로 시대 맥락 제공

  프롬프트:
    "다음 이벤트들과 인물들을 엮어 대학 교양 수준의 역사 에세이를 작성하세요.
     - 4문단 이내 (A4 1페이지)
     - 인물/이벤트/장소를 [이름](entity:type:id) 형식으로 태깅
     - 인과관계와 역사적 의의를 포함
     - 한국어로 작성"

  출력:
    - histories 테이블에 INSERT (author_type='system')
    - history_entities에 mentioned + featured 자동 추출
    - parent_history_id 자동 설정 (이벤트 계층에서 추론)

  대상 (우선순위):
    - importance 5 aggregate 이벤트 (전쟁, 혁명 등) → 최상위 히스토리
    - 그 하위 이벤트 그룹 → 자식 히스토리
    - importance 4+ 인물 → 인물 중심 biography 히스토리
```

### 예상 비용

| 대상 | 수량 | 비용/건 | 총 비용 |
|------|------|---------|---------|
| 최상위 히스토리 (aggregate events) | ~100 | ~$0.01 | ~$1 |
| 하위 히스토리 | ~300 | ~$0.008 | ~$2.4 |
| 인물 biography | ~200 | ~$0.01 | ~$2 |
| **합계** | **~600** | | **~$5.4** |

---

## 9. 다국어 지원 (한/영/일)

### 현재 상태

| 필드 | EN | KO | JA |
|------|----|----|-----|
| entity name | ✅ | ✅ | ✅ |
| entity_narrative | ✅ narrative | ✅ narrative_ko | ❌ 없음 |
| period_narrative | ✅ headline/narrative | ✅ _ko | ❌ 없음 |
| history body | ✅ body | ✅ body_ko | ✅ body_ja |

### 필요한 작업

1. `entity_narratives`에 `narrative_ja` 컬럼 추가 (마이그레이션)
2. `period_narratives`에 `headline_ja`, `narrative_ja` 컬럼 추가
3. 큐레이션 시 3개 언어로 생성 (또는 EN 먼저 → 번역 후처리)
4. 히스토리는 처음부터 body/body_ko/body_ja 3개 컬럼으로 설계됨

---

## 10. 파일 변경 목록

### Backend (7 파일)

| 파일 | 변경 | 설명 |
|------|------|------|
| `backend/alembic/versions/500_histories.py` | **NEW** | histories + history_entities + history_relations 마이그레이션 |
| `backend/app/models/history.py` | **NEW** | History, HistoryEntity, HistoryRelation 모델 |
| `backend/app/models/__init__.py` | EDIT | import 추가 |
| `backend/app/schemas/history.py` | **NEW** | Pydantic 스키마 |
| `backend/app/api/v1/histories.py` | **NEW** | CRUD + 역참조 API |
| `backend/app/api/v1/router.py` | EDIT | 라우터 등록 |
| `backend/app/api/v1/persons.py` | EDIT | /persons/{id}/histories 엔드포인트 추가 |

### Frontend (7 파일)

| 파일 | 변경 | 설명 |
|------|------|------|
| `frontend/src/types/index.ts` | EDIT | History 타입 추가 |
| `frontend/src/api/client.ts` | EDIT | historiesApi 추가 |
| `frontend/src/components/navigator/Navigator.tsx` | EDIT | History 탭 추가 |
| `frontend/src/components/navigator/HistoryTab.tsx` | **NEW** | 목록 (계층 표시, 필터) |
| `frontend/src/components/history/HistoryViewer.tsx` | **NEW** | 읽기 (breadcrumb, 엔티티 링크, 하위/관련 네비게이션) |
| `frontend/src/components/history/HistoryEditor.tsx` | **NEW** | 작성 (엔티티 자동완성, 장소/엔티티 chips) |
| `frontend/src/App.tsx` | EDIT | historyViewId, isHistoryEditorOpen state + 렌더링 |

---

## 11. 구현 순서

```
Phase A: 백엔드 (테이블 + API)
  1. 마이그레이션 (histories, history_entities, history_relations)
  2. 모델 + 스키마
  3. CRUD API + 엔티티 태그 파싱 로직
  4. 역참조 API (persons/{id}/histories)

Phase B: 프론트엔드 (읽기 우선)
  5. 타입 + API 클라이언트
  6. HistoryViewer (읽기 패널 — breadcrumb, 엔티티 링크, 하위/관련 네비)
  7. HistoryTab (목록 — 계층 표시, 필터)
  8. Navigator 탭 추가 + App.tsx 통합

Phase C: 프론트엔드 (작성)
  9. HistoryEditor (모달 — 엔티티 자동완성, 장소/엔티티 chips)
  10. 수동 테스트 (1-2개 샘플 히스토리 수동 생성)

Phase D: 큐레이션 (별도 세션)
  11. curate_with_llm.py --step 6 구현
  12. 100개 최상위 + 300개 하위 히스토리 자동생성
```

---

## 12. 검증

```bash
# 마이그레이션
cd backend && python -m alembic upgrade head

# API CRUD 테스트
curl http://localhost:8100/api/v1/histories
curl -X POST http://localhost:8100/api/v1/histories -H "Content-Type: application/json" -d '{...}'

# 프론트엔드 타입 체크
cd frontend && npx tsc --noEmit

# 브라우저 테스트
# Navigator → History 탭 → 목록 → 클릭 → Viewer
# Viewer에서 엔티티 태그 클릭 → 상세 패널
# Viewer에서 하위/관련 히스토리 클릭 → 네비게이션
# + 버튼 → Editor → 본문에서 [ 입력 → 자동완성 → 저장
```

## 비용: $0 (기존 인프라 활용, LLM 큐레이션은 Phase D에서 ~$5)
