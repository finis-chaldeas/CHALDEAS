# Frontend Redesign Plan B: Hybrid Rebuild

> "기존 인프라(stores, API client, globe, timeline)는 살리고, 네비게이션과 콘텐츠 표현만 재설계한다."

## 철학

작동하는 기존 코드를 유지하면서, 중복 경로를 제거하고 미사용 데이터를 기존 UI에 통합한다.

---

## 유지하는 것
- GlobeContainer + 4단계 줌 + WASD fly
- Zustand stores (globeStore, timelineStore, settingsStore, observationStore)
- API client (client.ts)
- UnifiedTimeline (하단 바)
- TourOverlay (가이드 투어)
- SearchAutocomplete
- ChatPanel

## 재설계하는 것

### Navigator 간소화: 3버튼 -> 2버튼

**Before:**
```
[Timeline] [Domains] [Trismegistus]
```

**After:**
```
[Timeline] [Trismegistus]
```

- Domains 버튼 삭제 -> PersonTab 내 도메인 드롭다운으로 대체
- Trismegistus -> ShowcaseModal 직접 열기 (Hub 중간 단계 삭제)

### FeaturedPersons 간소화: 5개 -> 2개 진입점

**Before:**
```
[Free Explore] [Guided Tour] [Timeline] [By Subject] [Browse Figures]
```

**After:**
```
[Guided Tour] [Free Explore]
```

- Timeline/By Subject 카드 삭제 (Navigator에서 접근 가능)
- Browse Figures 삭제 (People 탭으로 충분)

### 글로브 위 "Explore Eras" 버튼 삭제
- TimelineModal과 완전 중복 -> 제거

---

## 중복 모달 deprecated 처리

| 컴포넌트 | 처리 | 대체 |
|---------|------|------|
| TrismegistusHub | -> `_deprecated/` | Feed탭(투어), People탭(도메인), ShowcaseModal(FGO) |
| DomainTimelineModal | -> `_deprecated/` | People탭 도메인 드롭다운 |
| HierarchyExplorer | 유지 (EventDetail에서 접근) | 글로브 위 "Explore Eras" 버튼만 제거 |
| StoryModal | 유지 | PersonDetail 탭에서도 접근 가능 (두 경로 유지) |

---

## EventDetailPanel 개선

### 인과관계 섹션 (NEW)
```tsx
<CausalChainSection eventId={event.id} />
// GET /events/{id} -> event_relationships 조인 필요 (백엔드 수정)
// UI: "원인 -> 이 사건 -> 결과" 가로 타임라인
```

### 하위 이벤트 인라인 (기존 children API 활용, 이미 부분 구현)
```tsx
// 이미 api.get('/events/{id}/children') 호출 중
// 개선: 펼침/접힘 UI 추가, 각 child 클릭 -> 글로브 fly
```

### 인물 스레드 섹션 (NEW)
```tsx
// 이벤트의 주요 인물이 참여한 다른 이벤트들
// GET /threads/{personId}/events -> 시간순 이벤트 목록
// "이 인물의 다른 사건들" 섹션으로 표시
```

---

## PersonDetailView 개선

### 관계 네트워크 탭 (NEW)
```tsx
// 새 탭: Relations
// GET /persons/{id}/relations -> 미니 네트워크 그래프
// teacher/student/rival/ally 색상 구분
// 클릭 -> 해당 인물로 이동
```

> **참고**: 현재 PersonDetailView에 이미 관계 데이터가 그룹별 리스트로 표시됨
> (family/spouse/academic/other + strength bar). 그래프 시각화가 추가 개선점.

### 위키데이터 속성 확장
```tsx
// 기존: 9개 속성만 표시
// 개선: 주요 25개 속성, 카테고리별 그룹핑
```

### 스토리 인라인
```tsx
// 기존 StoryModal의 로직을 PersonDetailView의 "Story" 탭으로도 접근 가능
// 별도 모달 유지 + 인라인 탭 추가 (두 경로)
```

---

## LocationDetailView 개선

### 역사적 이름 (기존 구현 확인 필요)
```tsx
// GET /locations/{id} -> names 필드
// "Byzantium -> Constantinople -> Istanbul" 타임라인
```

> **참고**: 현재 LocationDetailView에 이미 Historical Names, Political History(territories) 섹션 구현됨.

---

## PersonTab 도메인 필터 추가

```tsx
const DOMAIN_OPTIONS = [
  { value: '', label: 'All Fields' },
  { value: 'science', label: 'Science' },
  { value: 'philosophy', label: 'Philosophy' },
  { value: 'literature', label: 'Literature' },
  { value: 'military', label: 'Military' },
  { value: 'statecraft', label: 'Statecraft' },
  { value: 'visual_arts', label: 'Visual Arts' },
  { value: 'music', label: 'Music' },
  { value: 'religion', label: 'Religion' },
]
// 백엔드 /persons API에 이미 domain 쿼리 파라미터 지원됨
```

---

## 새로 활용하는 데이터

| 데이터 | 활용 방식 | 필요 작업 |
|--------|----------|----------|
| person_relationships | PersonDetail 관계 네트워크 탭 | 프론트 NEW 컴포넌트 (~150줄) |
| event_relationships | EventDetail 인과관계 섹션 | 백엔드: events/{id} 응답에 relationships 포함 + 프론트 (~100줄) |
| threads | EventDetail 내 "스레드" 섹션 | 프론트: threads API 호출 + 카드 (~80줄) |
| wikidata 속성 확장 | PersonDetail 속성 섹션 | 프론트 수정 (~40줄) |
| domain 필터 | People탭 드롭다운 | 프론트 수정 (~25줄) |

---

## 작업량

| 항목 | 수량 |
|------|------|
| 새 컴포넌트 | ~5개 (800줄) |
| 수정 컴포넌트 | ~8개 |
| deprecated 이동 | ~4개 파일 |
| 새 API | 1개 수정 (events/{id}에 relationships 추가) |

---

## 장점
- 기존 인프라 100% 재활용 (stores, globe, timeline, API client)
- 리스크 낮음 (작동하는 코드 안 건드림)
- 데이터 모델 주요 부분 활용 (관계, 인과, 스레드)
- 중복 80% 제거

## 단점
- 영토 오버레이, 관계선 등 글로브 시각화는 못 함
- 완전한 "Globe-First" 경험은 아님 (여전히 사이드바 의존)
- 일부 중복 남음 (StoryModal 두 경로)

## 지표

| 항목 | 값 |
|------|-----|
| 모달 수 | 2 (Timeline, Showcase) |
| 데이터 활용률 | 70% |
| 중복 제거율 | 80% |
| 아이 친화성 | ★★★☆☆ |
| 글로브 중심성 | ★★★☆☆ |
| 리스크 | 중간 |
