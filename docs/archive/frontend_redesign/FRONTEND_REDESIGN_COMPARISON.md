# Frontend Redesign: 세 가지 플랜 비교

## 현재 문제 요약

1. **중복 경로**: 같은 데이터에 3~5개 진입점 (TimelineModal + HierarchyExplorer + TrismegistusHub 등)
2. **미사용 데이터**: DB/API에 있는 인과관계, 영토, 스레드 등이 프론트에서 미표시
3. **인지 부하**: 풀스크린 모달 6개, 사이드바 버튼 3개, 랜딩 진입점 5개

## 비교표

| 항목 | Plan A (완전 재설계) | Plan B (반반) | Plan C (최소 변경) |
|------|---------------------|---------------|-------------------|
| **모달 수** | 0 | 2 (Timeline, Showcase) | 2 (Timeline, Showcase) |
| **데이터 활용률** | 100% | 70% | 45% |
| **코드 변경량** | ~3,000줄 새 작성 | ~800줄 새 작성 | ~75줄 추가 |
| **deprecated 파일** | ~20개 | ~4개 | 4개 |
| **새 API 필요** | 3개 | 1개 수정 | 0개 |
| **리스크** | 높음 | 중간 | 낮음 |
| **아이 친화성** | ★★★★★ | ★★★☆☆ | ★★☆☆☆ |
| **글로브 중심성** | ★★★★★ | ★★★☆☆ | ★★☆☆☆ |
| **인물 관계 표시** | 네트워크 그래프 + 글로브 위 선 | 네트워크 그래프 (패널 내) | 이미 구현됨 (리스트) |
| **이벤트 인과관계** | 글로브 위 화살표 + 카드 내 | 카드 내 섹션 | 미구현 |
| **영토 시각화** | 글로브 위 오버레이 (시간 연동) | 미구현 | 미구현 |
| **스레드** | ContextDrawer 내 | EventDetail 내 | EventDetail 내 |
| **중복 제거율** | 100% | 80% | 60% |

## 각 플랜 문서
- [Plan A: Complete Rebuild](./FRONTEND_REDESIGN_PLAN_A.md)
- [Plan B: Hybrid Rebuild](./FRONTEND_REDESIGN_PLAN_B.md)
- [Plan C: Maximum Reuse](./FRONTEND_REDESIGN_PLAN_C.md)

## 참고: 이미 구현되어 있는 것들

코드 분석 결과, 아래 기능은 이미 구현 완료 상태:

| 기능 | 위치 | 상태 |
|------|------|------|
| 인물 관계 (grouped list + strength bar) | `PersonDetailView.tsx` line 112-118, 522-657 | 완성 |
| 영토/정치 역사 | `LocationDetailView.tsx` line 210-230 | 완성 |
| 역사적 지명 변화 | `LocationDetailView.tsx` line 186-207 | 완성 |
| Context Banner (NOW OBSERVING) | `FeedInterest.tsx` line 159-176, `FeedTab.tsx` line 89-148 | 완성 |
| 위키데이터 속성 표시 | `PersonDetailView.tsx` line 121-128, 478-493 | 완성 (9개) |
| 백엔드 domain 필터 | `persons.py` line 28 | 완성 |
| 백엔드 threads API | `threads.py` | 완성 |

---

## 주의: 현재 코드 상태

> Plan C에 해당하는 변경이 이미 적용된 상태입니다.
> 아직 플랜 선택 전인데 코드 변경이 됨 - 필요시 revert 가능합니다.
>
> 적용된 변경: deprecated 이동 4파일, App.tsx/Navigator/FeaturedPersons 간소화,
> PersonTab 도메인 필터, EventDetailPanel 스레드 섹션
