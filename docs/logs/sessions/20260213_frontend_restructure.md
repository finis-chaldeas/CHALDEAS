# 세션 로그: 2026-02-13 Frontend 구조 개선

## 세션 정보
- **목적**: Frontend 구조 개선 (Phase 1-4)
- **기반 문서**: `docs/planning/FRONTEND_RESTRUCTURE.md`
- **결과**: Phase 1-4 완료, TypeScript 검증 통과

---

## 작업 요약

### Phase 1: 정리 (완료)

**삭제:**
- 플로팅 버튼 4개 제거 (explore, servant, hierarchy, settings)
- Chat 버튼은 유지
- 삭제된 폴더:
  - `components/explore/`
  - `components/servants/`
  - `components/showcase/`
  - `components/hierarchy/`
  - `data/showcaseData.ts`

**App.tsx 정리:**
- 불필요한 import 제거
- useState 5개 제거 (showcaseContent, isShowcaseOpen, isExploreOpen, isServantOpen, isHierarchyOpen)
- ShowcaseMenu JSX 제거

### Phase 2: 레이아웃 (완료)

**새 파일:**
- `layouts/MainLayout.tsx` - 3열 그리드 레이아웃
- `components/header/Header.tsx` - 상단 바
- CSS 스타일 추가 (globals.css)

**레이아웃 구조:**
```
┌─────────────────────────────────────────┐
│ Header (56px)                            │
├────────────┬─────────────┬──────────────┤
│ Navigator  │   Globe     │  StoryPanel  │
│ (280px)    │   (flex)    │  (400px)     │
├────────────┴─────────────┴──────────────┤
│ Timeline (100px)                         │
└─────────────────────────────────────────┘
```

### Phase 3: Navigator (완료)

**새 파일:**
- `Navigator.tsx` - 탭 컨테이너 (5개 탭)
- `EventTab.tsx` - VirtualEventList 활용
- `PersonTab.tsx` - 인물 검색 + 목록
- `LocationTab.tsx` - 장소 검색 + 목록
- `EraTab.tsx` - 시대 목록 (Ancient ~ Contemporary)
- `ChainTab.tsx` - 체인 통계 표시

### Phase 4: Story 뷰 (완료)

**새 파일:**
- `StoryPanel.tsx` - 스토리 뷰 컨테이너
- `StoryNode.tsx` - 개별 노드 (내러티브 + 위치 + 출처)
- `PersonStory.tsx` - 인물 생애 체인
- `PlaceStory.tsx` - 장소 연대기
- `EraStory.tsx` - 시대 종합 (이벤트/인물 탭)
- `SourceViewer.tsx` - Wikipedia 본문 표시

---

## 생성된 파일 목록

```
frontend/src/
├── layouts/
│   └── MainLayout.tsx           # NEW
├── components/
│   ├── header/
│   │   ├── Header.tsx           # NEW
│   │   └── index.ts             # NEW
│   ├── navigator/
│   │   ├── Navigator.tsx        # NEW
│   │   ├── EventTab.tsx         # NEW
│   │   ├── PersonTab.tsx        # NEW
│   │   ├── LocationTab.tsx      # NEW
│   │   ├── EraTab.tsx           # NEW
│   │   ├── ChainTab.tsx         # NEW
│   │   └── index.ts             # NEW
│   └── story/
│       ├── StoryPanel.tsx       # NEW
│       ├── StoryNode.tsx        # NEW
│       ├── PersonStory.tsx      # NEW
│       ├── PlaceStory.tsx       # NEW
│       ├── EraStory.tsx         # NEW
│       ├── SourceViewer.tsx     # NEW
│       └── index.ts             # UPDATED
└── styles/
    └── globals.css              # UPDATED (+300 lines CSS)
```

---

## 검증

### TypeScript
```bash
cd frontend && npx tsc --noEmit
# 결과: 에러 없음
```

### 삭제된 코드 확인
- `ShowcaseMenu`, `ShowcaseModal`, `ExplorePanel`, `ServantPanel`, `EventHierarchyPanel` - 모두 App.tsx에서 제거됨
- 관련 lazy import, useState 모두 제거됨

---

## 미완료 작업

### Phase 5: 글로브 연동
- [ ] ConnectionArcs 컴포넌트
- [ ] 스토리 노드 클릭 → 글로브 이동
- [ ] 글로브 마커 클릭 → 스토리 표시

### Phase 6: 백엔드 API
- [ ] `/api/v1/globe/arcs/{id}` - 연결 아크 데이터
- [ ] `/api/v1/story/person/{id}` - 인물 스토리 데이터

### App.tsx 통합
- [ ] 새 컴포넌트들을 실제 App.tsx에 적용
- [ ] 기존 레이아웃에서 새 MainLayout으로 전환

---

## 반성점

1. **컴포넌트 생성 vs 통합**: 컴포넌트를 먼저 생성하고 나중에 통합하는 방식 채택. 점진적 마이그레이션 가능.
2. **기존 코드 유지**: App.tsx의 기존 로직을 유지하면서 새 컴포넌트 추가. 한 번에 모든 것을 바꾸지 않음.

---

## 다음 작업

1. Phase 5-6 완료 (글로브 연동, API)
2. App.tsx에 새 레이아웃 적용 (점진적)
3. 테스트 및 버그 수정
