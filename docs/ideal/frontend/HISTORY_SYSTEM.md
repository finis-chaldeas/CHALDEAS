# 히스토리 시스템 — 왜 이렇게 기획되었는가

---

## 1. 문제: AI 생성 콘텐츠만으로는 부족하다

CHALDEAS에는 이미 두 가지 서사 레이어가 있다:
- **entity_narratives**: 개별 사건/인물 서사 (100-300단어). "테르모필레 전투란 무엇인가"
- **period_narratives**: 50년 단위 시대 개요 (200-500단어). "BCE 500-450년의 세계"

하지만 이것만으로는 **여러 엔티티를 엮는 이야기**가 없다.

"알렉산더가 아리스토텔레스에게 배우고, 페르시아를 정복하고, 헬레니즘 세계를 열었다"라는 이야기는 person narrative(알렉산더)에도, event narrative(가우가멜라 전투)에도, period narrative(BCE 350-300)에도 완전히 들어가지 않는다.

**이것이 History가 필요한 이유다.**

---

## 2. History = 다중 엔티티 서사

History는 **A4 1페이지 분량의 에세이**로, 여러 엔티티를 엮어 하나의 이야기를 만든다.

### 핵심: 인라인 엔티티 태깅

본문(body)은 Markdown이며, 엔티티 태그가 삽입된다:
```markdown
[Julius Caesar](entity:person:12345)가 루비콘 강을 건너
[Caesar's Civil War](entity:event:67890)를 시작했다.
이 전쟁은 [Rome](entity:location:11111)의 공화정을 끝장냈다.
```

이 태그는 자동으로 파싱되어 `history_entities` 테이블에 저장된다.

### 3가지 역할 (role)
| 역할 | 의미 | 예시 |
|------|------|------|
| `featured` | 에세이의 주인공 | Julius Caesar |
| `mentioned` | 본문에서 언급됨 (태그에서 자동 추출) | Caesar's Civil War |
| `location` | 공간적 배경 | Rome |

### 5가지 카테고리
| 카테고리 | 설명 |
|---------|------|
| `essay` | 일반 역사 에세이 |
| `biography` | 인물 전기 |
| `causal_chain` | 인과관계 사슬 |
| `era_overview` | 시대 개요 |
| `comparison` | 비교 분석 |

---

## 3. 역방향 조회

History의 강력한 점은 **엔티티에서 역방향으로 조회**할 수 있다는 것이다.

- `GET /persons/{id}/histories` → "이 인물이 등장하는 에세이들"
- `GET /events/{id}/histories` → "이 사건이 언급된 에세이들"

인물 카드나 이벤트 카드에서 "관련 읽을거리"로 표시할 수 있다.

---

## 4. AI 자동 생성

### Cluster Mode (사건 클러스터 → 에세이)
- 부모 이벤트 + 3개 이상 자식 이벤트가 있으면 자동 생성
- 예: "Hundred Years' War" → 하위 전투들을 엮는 에세이
- 예상: ~100개 클러스터 에세이

### Person Mode (중요 인물 → 전기)
- importance ≥ 80 + 3개 이상 이벤트 참여 인물
- 예: "Alexander the Great" → 생애 + 주요 사건을 엮는 전기
- 예상: ~200개 전기

### 비용
- LLM: gpt-5.1-chat-latest
- 비용: ~$0.01/에세이 → 총 ~$5 (500개)
- 체크포인트 시스템으로 중단/재개 가능

---

## 5. 사용자 작성

History는 AI만 만드는 것이 아니다. 사용자도 작성할 수 있다.

### 작성 흐름
1. HistoryEditor에서 제목, 시대 범위, 카테고리 입력
2. 본문에서 `[`를 타이핑하면 엔티티 자동완성 팝업
3. 엔티티 선택 → `[이름](entity:type:id)` 자동 삽입
4. 저장 시 본문의 태그가 자동 파싱 → history_entities 생성

### author_type 구분
- `system`: AI가 자동 생성 (gpt-5.1-auto)
- `user`: 사용자가 직접 작성

---

## 6. Tour와의 관계

### 현재: 하드코딩된 Tour
`shebaEpisodes`에 하드코딩된 가이드 투어가 있다 (그리스-페르시아 전쟁 7단계 등).

### 미래: DB 기반 Tour
History가 본질적으로 **DB 기반 Tour**다:
- entity 태그 → 글로브 위치 자동 추출
- era_start/era_end → 시간 범위 자동 설정
- featured entities → 투어의 주요 정거장

하드코딩된 shebaEpisodes를 History로 전환하면:
- DB에서 관리 가능
- AI로 자동 생성 가능
- 사용자가 자신만의 투어를 만들 수 있음

---

## 7. 데이터 모델

### histories 테이블
```
id, title/title_ko/title_ja, summary
body/body_ko/body_ja              -- Markdown + entity tags
era_start, era_end                -- 시간 범위
category, tags[]                  -- 분류
author_type, author_name          -- 작성자
status (draft/published/archived) -- 상태
importance (1-5)                  -- 피드 정렬용
```

### history_entities 테이블
```
history_id, entity_type(person/event/location), entity_id
entity_name                       -- 이름 스냅샷
role (featured/mentioned/location) -- 역할
UNIQUE(history_id, entity_type, entity_id)
```

### API
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | /histories | 목록 (필터: category, era, tag, status) |
| GET | /histories/{id} | 상세 (entities 포함) |
| POST | /histories | 생성 (entity 태그 자동 파싱) |
| PUT | /histories/{id} | 수정 (entity 재동기화) |
| DELETE | /histories/{id} | 삭제 |

---

## 8. 프론트엔드 컴포넌트

### HistoryTab (Navigator 사이드바)
- History 목록 카드 (제목, 시대, 엔티티 수, 카테고리)
- "+ New History" 버튼
- 카테고리 필터

### HistoryViewer (우측 패널)
- 제목 + 메타정보 (시대, 카테고리, 작성자)
- Featured 엔티티 칩 (클릭 → 해당 엔티티로 이동)
- Location 칩 (클릭 → 글로브 이동)
- 본문: entity 태그가 클릭 가능한 링크로 렌더링
- 태그 목록

### HistoryEditor (모달)
- 제목, 시대 범위, 카테고리 입력
- 본문 편집: `[` 입력 시 엔티티 자동완성
- Featured 엔티티/Location 칩 관리
- 태그 입력

---

## 9. 요약

```
entity_narratives: 개별 엔티티 이야기 (1개 주인공)
period_narratives: 시대 개요 (시간 범위 중심)
histories:        다중 엔티티 에세이 (여러 주인공, 여러 사건, 여러 장소)
```

History는 CHALDEAS의 **콘텐츠 레이어**다.
메타데이터(DB)와 서사(텍스트) 사이의 다리.
글로브 위의 점(마커)들을 선(이야기)으로 잇는 것.
