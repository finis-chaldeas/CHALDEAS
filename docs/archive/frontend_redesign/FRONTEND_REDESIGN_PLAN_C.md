# Frontend Redesign Plan C: Maximum Reuse (최소 변경)

> "기존에 잘 되어있는 걸 방해하는 중복만 제거하고, 숨어있는 데이터를 기존 UI에 끼워넣는다."

## 철학

코드를 최소한으로 건드린다. 기존 컴포넌트의 구조는 유지하되,
(1) 중복 진입점 제거, (2) 미사용 API 호출 추가만 한다.

---

## 변경 사항

### 1. 중복 제거 (코드 보존, deprecated 처리)

**deprecated 처리할 파일:**
- `showcase/TrismegistusHub.tsx` + `.css` -> `_deprecated/`
- `navigator/DomainTimelineModal.tsx` + `.css` -> `_deprecated/`

**App.tsx 수정:**
- TrismegistusHub import/state/JSX 삭제
- DomainTimelineModal import/state/JSX 삭제
- Navigator의 `onOpenShowcase` -> ShowcaseModal 직접 열기
- Navigator의 `onOpenDomainTimeline` prop 삭제
- 글로브 위 "Explore Eras" 버튼 삭제 (TimelineModal과 중복)

**Navigator.tsx 수정:**
- "Domains" 트리거 버튼 삭제
- 2버튼: [Timeline] [Trismegistus] (Trismegistus -> ShowcaseModal 직접)

**FeaturedPersons.tsx 수정:**
- 5개 -> 2개 진입점 (투어/탐험)
- persons 그리드 뷰 삭제
- `WelcomeView` = `'welcome' | 'guided-tours'`

---

### 2. 미사용 데이터 API 호출 추가

#### PersonDetailView.tsx (기존 715줄에 추가)

```tsx
// 관계 데이터 가져오기 (API 이미 존재)
// ** 확인 결과: 이미 구현되어 있음 **
// - GET /persons/{id}/relations 호출 중 (line 112-118)
// - family/spouse/academic/other 그룹별 표시 (line 522-657)
// - strength bar 표시 완료
// -> 추가 작업 불필요
```

#### EventDetailPanel.tsx (기존 973줄에 추가)

```tsx
// 스레드 데이터 (이 이벤트의 주요 인물의 관련 이벤트들)
const { data: thread } = useQuery({
  queryKey: ['thread-events', mainPersonId],
  queryFn: () => api.get(`/threads/${mainPersonId}/events`),
  enabled: !!mainPersonId,
})

// 렌더링: "이 인물의 다른 사건들" 섹션
// 시간순 카드 리스트, 클릭 -> 해당 이벤트로 fly
```
**추가량: ~50줄**

#### PersonTab.tsx (기존 173줄에 추가)

```tsx
// 도메인 필터 드롭다운 (DomainTimelineModal 대체)
const DOMAIN_OPTIONS = [
  { value: '', label: 'All Fields' },
  { value: 'science', label: 'Science' },
  { value: 'philosophy', label: 'Philosophy' },
  // ...
]

const [domainFilter, setDomainFilter] = useState('')
// queryParams에 domain 추가
```
**추가량: ~25줄**

#### LocationDetailView.tsx
```tsx
// ** 확인 결과: 이미 구현되어 있음 **
// - Historical Names 섹션 (line 186-207)
// - Political History (territories) 섹션 (line 210-230)
// -> 추가 작업 불필요
```

---

### 3. 기존 컴포넌트 미세 개선

#### FeedInterest.tsx - Context Banner 강화
```tsx
// ** 확인 결과: 이미 구현되어 있음 **
// - 현재 "NOW OBSERVING: Europe · 480 BCE" + headline 표시 중
// - "View in Timeline ->" 링크 이미 있음
// -> 추가 작업 불필요
```

---

## 수정 파일 요약

| 파일 | 작업 | 변경량 |
|------|------|--------|
| TrismegistusHub.tsx/css | `_deprecated/`로 이동 | 0 (이동만) |
| DomainTimelineModal.tsx/css | `_deprecated/`로 이동 | 0 (이동만) |
| App.tsx | import/state/JSX 삭제, props 수정 | ~-80줄 |
| FeaturedPersons.tsx | 5 -> 2 진입점, persons 뷰 삭제 | ~-130줄 |
| Navigator.tsx | Domains 버튼 삭제 | ~-15줄 |
| EventDetailPanel.tsx | thread 섹션 추가 | ~+50줄 |
| PersonTab.tsx | domain 드롭다운 추가 | ~+25줄 |
| navigator.css | .trigger-domain 삭제 | ~-10줄 |

**총: ~235줄 삭제, ~75줄 추가. 4파일 deprecated 이동, 6파일 수정.**

---

## 장점
- 리스크 최소 (기존 코드 거의 안 건드림)
- 작업량 최소
- 즉시 테스트 가능
- 가장 중요한 미사용 데이터(스레드, 도메인)가 노출됨
- 중복 진입점 60% 제거

## 단점
- 글로브 시각화 개선 없음 (영토 오버레이, 관계선 등)
- 인과관계(event_relationships) 미활용 (API 미노출)
- "아이도 이해하는 UI" 수준까지는 도달 못함 (구조적으로 여전히 사이드바 + 탭)
- 근본적 UX 개선이 아닌 땜빵

## 지표

| 항목 | 값 |
|------|-----|
| 모달 수 | 2 (Timeline, Showcase) |
| 데이터 활용률 | 45% |
| 중복 제거율 | 60% |
| 아이 친화성 | ★★☆☆☆ |
| 글로브 중심성 | ★★☆☆☆ |
| 리스크 | 낮음 |
