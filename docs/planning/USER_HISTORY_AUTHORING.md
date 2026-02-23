# User History Authoring (사용자 히스토리 작성 기능)

**작성일**: 2026-02-23
**상태**: 기획 단계
**우선순위**: 중기 (Phase 3 큐레이션 완료 후)

---

## 개요

사용자가 기존 이벤트, 인물, 장소를 언급하면서 **자유롭게 역사 글(히스토리)을 작성**할 수 있는 기능.
위키피디아처럼 백과사전식이 아니라, **에세이/논문/스토리 형식**으로 역사를 서술하는 것이 핵심.

### 목적

1. 사용자가 CHALDEAS의 데이터를 활용해 **자신만의 역사 해석**을 기록
2. 기존 엔티티를 인라인 참조하면서 **맥락 있는 글쓰기** 가능
3. 작성된 글이 다른 사용자에게도 **탐색 경로**가 됨 (Guided Tour의 사용자 버전)

---

## 핵심 컨셉: "Historical Essay"

```
┌──────────────────────────────────────────────┐
│  "로마 공화정의 몰락"                          │
│  by User123 · 2026-03-15                     │
│                                              │
│  [기원전 2세기], [그라쿠스 형제]가 토지 개혁을   │
│  시도했을 때 이미 공화정의 균열은 시작되었다.     │
│  [마리우스]의 군제 개혁은 군대를 국가가 아닌      │
│  장군 개인에게 충성하게 만들었고, 이는 [술라]의    │
│  독재로 이어졌다.                              │
│                                              │
│  [율리우스 카이사르]가 [루비콘 강]을 건너며       │
│  "주사위는 던져졌다"고 말했을 때, 그것은 단지     │
│  한 장군의 반란이 아니라 500년 공화정 체제의      │
│  종언이었다...                                │
│                                              │
│  📎 언급된 엔티티: 6인물, 3이벤트, 2장소        │
│  📅 시간범위: BC 133 ~ BC 27                   │
│  🏷️ 태그: 로마, 공화정, 정치변동               │
└──────────────────────────────────────────────┘
```

**핵심**: `[엔티티명]`으로 기존 DB 엔티티를 인라인 링크. 클릭하면 해당 엔티티 상세로 이동.

---

## 데이터 모델

### user_histories 테이블

```sql
CREATE TABLE user_histories (
    id SERIAL PRIMARY KEY,

    -- 작성자
    author_id INTEGER REFERENCES users(id),
    author_name VARCHAR(100),  -- 익명 작성 허용 시

    -- 콘텐츠
    title VARCHAR(300) NOT NULL,
    title_ko VARCHAR(300),
    title_ja VARCHAR(300),
    body TEXT NOT NULL,              -- Markdown 본문 (엔티티 참조 포함)
    body_ko TEXT,
    body_ja TEXT,
    summary VARCHAR(500),            -- 200자 요약

    -- 분류
    era_start INTEGER,               -- 시작 연도 (BCE = 음수)
    era_end INTEGER,                 -- 종료 연도
    region VARCHAR(30),              -- 주요 지역
    tags TEXT[],                     -- 자유 태그
    category VARCHAR(50),            -- essay/analysis/biography/timeline/comparison

    -- 메타
    language VARCHAR(10) DEFAULT 'ko',  -- 원문 언어
    word_count INTEGER,
    read_time_minutes INTEGER,       -- 예상 읽기 시간

    -- 상태
    status VARCHAR(20) DEFAULT 'draft',  -- draft/published/archived
    visibility VARCHAR(20) DEFAULT 'public',  -- public/private/unlisted

    -- 통계
    view_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    published_at TIMESTAMP
);
```

### history_entity_mentions 테이블

```sql
CREATE TABLE history_entity_mentions (
    id SERIAL PRIMARY KEY,
    history_id INTEGER REFERENCES user_histories(id) ON DELETE CASCADE,

    -- 언급된 엔티티
    entity_type VARCHAR(10) NOT NULL,  -- 'person', 'event', 'location'
    entity_id INTEGER NOT NULL,
    entity_name VARCHAR(255),          -- 표시명 (글 작성 시점 기준)

    -- 본문 내 위치
    mention_offset INTEGER,            -- 본문에서의 문자 위치
    mention_context VARCHAR(500),      -- 주변 텍스트 (검색용)

    -- 역할
    role VARCHAR(50),                  -- protagonist/antagonist/setting/cause/effect

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_hem_history ON history_entity_mentions(history_id);
CREATE INDEX idx_hem_entity ON history_entity_mentions(entity_type, entity_id);
```

### history_comments 테이블 (선택적)

```sql
CREATE TABLE history_comments (
    id SERIAL PRIMARY KEY,
    history_id INTEGER REFERENCES user_histories(id) ON DELETE CASCADE,
    author_id INTEGER,
    author_name VARCHAR(100),
    body TEXT NOT NULL,
    parent_comment_id INTEGER REFERENCES history_comments(id),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 기능 상세

### 1. 에디터 (작성 화면)

**Markdown 기반 WYSIWYG 에디터** + 엔티티 자동완성

```
┌──────────────────────────────────────────────┐
│ 제목: [로마 공화정의 몰락                     ]│
│ ─────────────────────────────────────────── │
│                                              │
│  [기원전 2세기], [그라                        │
│                 ┌─────────────────────┐      │
│                 │ 🔍 "그라"            │      │
│                 │ ─────────────────── │      │
│                 │ 👤 그라쿠스, 티베리우스│      │
│                 │ 👤 그라쿠스, 가이우스  │      │
│                 │ 📍 그라나다           │      │
│                 │ 📅 그라쿠스 토지개혁   │      │
│                 └─────────────────────┘      │
│                                              │
│ ─────────────────────────────────────────── │
│ 카테고리: [에세이 ▼]  시대: [BC 133 ~ BC 27] │
│ 태그: [로마] [공화정] [+추가]                 │
└──────────────────────────────────────────────┘
```

**핵심 UX**:
- `[` 입력 시 엔티티 검색 팝업 트리거 (Notion의 `/` 커맨드 방식)
- 검색은 기존 `/api/v1/search` 엔드포인트 활용
- 선택 시 `[엔티티명](entity://person/12345)` 형식으로 삽입
- 렌더링 시 클릭 가능한 인라인 링크로 표시

### 2. 뷰어 (읽기 화면)

```
┌──────────────────────────────────────────────┐
│  로마 공화정의 몰락                           │
│  by User123 · 15분 읽기 · 2026-03-15        │
│  ─────────────────────────────────────────── │
│                                              │
│  기원전 2세기, 그라쿠스 형제가 토지 개혁을     │
│              └── 클릭 → 인물 상세 팝업         │
│  시도했을 때 이미 공화정의 균열은...            │
│                                              │
│  ─────────────────────────────────────────── │
│  📎 언급된 엔티티                             │
│  ┌────────┬────────┬────────┐               │
│  │👤 카이사르│👤 마리우스│👤 술라  │               │
│  │👤 폼페이우스│📍 루비콘│📅 내전  │               │
│  └────────┴────────┴────────┘               │
│                                              │
│  🗺️ 지도: [글에 언급된 장소들이 글로브에 표시]   │
│  📅 타임라인: [BC 133 ─────── BC 27]         │
└──────────────────────────────────────────────┘
```

**특수 기능**:
- **글로브 연동**: 글에 언급된 장소들이 3D 글로브에 하이라이트
- **타임라인 연동**: 글의 시간 범위가 타임라인에 표시
- **엔티티 호버**: 인라인 링크에 마우스 올리면 미니 프리뷰 팝업

### 3. 탐색 (목록/검색)

- **최신순/인기순** 정렬
- **시대별/지역별** 필터
- **태그** 기반 탐색
- **엔티티 기반 탐색**: "카이사르를 언급한 글 모두 보기"
- **AI 추천**: "이 인물에 대해 읽어볼 만한 글"

### 4. AI 보조 기능 (선택적)

- **팩트체크**: 작성 중 날짜/사건 오류 자동 감지
- **관련 엔티티 제안**: "이 맥락에서 [폼페이우스]도 언급할 수 있습니다"
- **요약 자동생성**: 본문 작성 완료 시 summary 자동 생성
- **번역 지원**: 원문 → 다국어 자동 번역 (검수 후 게시)

---

## API 설계

### History CRUD

```
POST   /api/v1/histories                    # 새 글 작성
GET    /api/v1/histories                    # 목록 (필터: era, region, tag, author)
GET    /api/v1/histories/{id}               # 글 상세 (본문 + 엔티티 목록)
PUT    /api/v1/histories/{id}               # 수정
DELETE /api/v1/histories/{id}               # 삭제
```

### History 관련

```
GET    /api/v1/histories/{id}/entities      # 언급된 엔티티 목록
GET    /api/v1/histories/{id}/globe-data    # 글로브 표시용 좌표 데이터
GET    /api/v1/histories/{id}/timeline      # 타임라인 표시용 시간 데이터
POST   /api/v1/histories/{id}/like          # 좋아요
```

### Entity → History 역참조

```
GET    /api/v1/persons/{id}/histories       # 이 인물을 언급한 글 목록
GET    /api/v1/events/{id}/histories        # 이 이벤트를 언급한 글 목록
GET    /api/v1/locations/{id}/histories     # 이 장소를 언급한 글 목록
```

---

## 기술 스택

### 에디터

| 옵션 | 장점 | 단점 |
|------|------|------|
| **TipTap** (추천) | 커스텀 노드 쉬움, React 네이티브 | 번들 크기 |
| Slate.js | 완전 커스텀 가능 | 학습 곡선 높음 |
| MDXEditor | Markdown 네이티브 | 커스텀 노드 제한 |

**추천**: **TipTap** — `[` 커맨드로 엔티티 검색 팝업을 트리거하는 커스텀 노드를 쉽게 만들 수 있음.

### 인증

| 옵션 | 비용 | 특징 |
|------|------|------|
| **Firebase Auth** | 무료 (10K/월) | Google/GitHub 로그인 |
| Supabase Auth | 무료 (50K/월) | 오픈소스, PostgreSQL 직접 연동 |
| 자체 구현 | 무료 | JWT + bcrypt |

**추천**: 초기에는 **익명 + 간단한 닉네임** 방식으로 시작, 이후 OAuth 추가.

---

## 구현 단계

### Phase A: MVP (3-5일)

1. `user_histories` + `history_entity_mentions` 테이블 생성
2. 기본 CRUD API
3. 간단한 Markdown 에디터 (엔티티 참조는 `[[검색어]]` 수동 입력)
4. 읽기 뷰 (엔티티 링크 렌더링)

### Phase B: 에디터 강화 (5-7일)

1. TipTap 에디터 통합
2. `[` 트리거 엔티티 자동완성
3. 인라인 엔티티 프리뷰 (호버 팝업)
4. 글로브/타임라인 연동

### Phase C: 소셜 기능 (3-5일)

1. 좋아요/북마크
2. 댓글
3. "이 인물에 대한 글" 역참조
4. 추천 피드

### Phase D: AI 보조 (2-3일)

1. 팩트체크 (날짜/이벤트 검증)
2. 관련 엔티티 제안
3. 자동 요약/번역

---

## 의존관계

```
Phase 3 큐레이션 완료 (서사 데이터 풍부해야 참조할 엔티티가 의미 있음)
    ↓
Phase A: MVP
    ↓
Phase B: 에디터 강화
    ↓
Phase C + D: 소셜 + AI (병렬 가능)
```

---

## 예상 비용

| 항목 | 비용 |
|------|------|
| TipTap 라이선스 | 무료 (오픈소스) |
| 스토리지 (글 본문) | 무시 가능 (텍스트) |
| AI 팩트체크/제안 | ~$0.001/글 (gpt-5-mini) |
| **총 추가 인프라 비용** | **$0** |

---

## 참고

이 기능은 CHALDEAS의 **양방향 역사 탐색** 비전과 직결:
- 현재: CHALDEAS → 사용자 (읽기 전용)
- 목표: 사용자 → CHALDEAS (글쓰기) → 다른 사용자 (공유)

"모든 역사는 누군가의 이야기다" — 사용자가 그 이야기를 직접 쓸 수 있게.
