# 세션 로그: 2026-02-23 — 프론트엔드 기획 기반 구축

## 세션 정보
- **목적**: 코드부터 고치는 접근이 실패 → ideal 문서 기반 체계적 기획서 작성
- **근본 원인**: ideal 문서가 비전 수준이지 구현 수준이 아님. 백엔드 구조 파악 없이 프론트엔드 기획 불가.

## 한 작업

### Phase 0: Navigator.tsx 빌드 에러 수정
- `frontend/src/components/navigator/Navigator.tsx`
  - Experience Level Toggle 섹션 (lines 156-172) 전체 제거
  - `useSettingsStore` import 제거
  - experienceLevel/setExperienceLevel 참조가 store에서 삭제되었는데 Navigator에 남아있던 문제
- `npx tsc --noEmit` 통과 확인

### Phase 1: `docs/ideal/frontend/` 백엔드 구조 문서화 (4개 문서)

1. **BACKEND_INVENTORY.md** (12,890 bytes)
   - 40+ 테이블 전체 목록, 핵심 컬럼, 프론트엔드 관련성
   - V0 Core (8), 관계 (10), 분류/계층 (4), 서사 (4), 출처 (3), V1 체인 (3), 사용자 (4), FGO/보조 (4+)
   - Compact DB 데이터 현황 포함

2. **DESIGN_RATIONALE.md** (8,173 bytes)
   - 7가지 핵심 설계 결정과 배경:
     - Node + Detail 패턴
     - Geography ≠ Politics
     - 시간-가변 이름
     - Braudel의 시간 스케일
     - AI 생성 서사 계층
     - Importance 스코어링
     - Certainty 레벨

3. **HISTORY_SYSTEM.md** (6,219 bytes)
   - History = 다중 엔티티 에세이 시스템
   - 인라인 엔티티 태깅, 역방향 조회, AI 자동 생성, 사용자 작성
   - Tour와의 관계 (미래 DB 기반 Tour)

4. **API_CAPABILITIES.md** (11,691 bytes)
   - ~70개 API 엔드포인트 전체 목록
   - 현재 사용 중 (~35개) vs 미사용 (~35개) 표시
   - 미사용이지만 반드시 연동해야 할 API 우선순위

### Phase 2: ideal 문서 사용자 피드백 반영

5. **EXPERIENCE.md** 업데이트
   - 5개 설계 원칙 추가:
     - 원칙 1: 랜딩은 1회성이 아니다
     - 원칙 2: ViewportFeed는 상시 컨텍스트
     - 원칙 3: 모드 분리 없음
     - 원칙 4: 글로브 회전 속도 ≠ 시간 이동 속도
     - 원칙 5: 백엔드 기능 전부 노출

6. **INDEX.md** 업데이트
   - frontend/ 폴더 문서 5개 링크 추가
   - 읽는 순서에 프론트엔드 구현 시 9-13번 추가

### Phase 3: FRONTEND_SPEC.md 작성

7. **FRONTEND_SPEC.md** (24,634 bytes)
   - 12개 섹션의 구현 수준 기획서:
     1. 화면 구성 (항상 보이는 6개 + 클릭 시 12개)
     2. 각 화면 상세 동작 (API 매핑 포함)
     3. 줌 레벨별 경험 (COSMIC/CONTINENTAL/REGIONAL/LOCAL)
     4. 시간 이동 경험 (6가지 변화)
     5. 인과 흐름 (글로브 비행 + 시간 이동)
     6. 인물 생애 흐름 (Person Flow)
     7. 관계 네트워크
     8. 랜딩/홈 화면
     9. 2-탭 규칙 검증 (10개 경로 전부 통과)
     10. 미사용 API 연동 우선순위 (14개)
     11. 컴포넌트-API 매핑 테이블
     12. 검증 체크리스트

## 결과
- **성공**: 모든 문서 작성 완료, 빌드 에러 수정, TypeScript 통과
- **목적 달성**: 코드를 쓰기 전에 참조할 수 있는 구현 수준 기획서 완성

## 변경 파일 목록
| 파일 | 변경 |
|------|------|
| `frontend/src/components/navigator/Navigator.tsx` | 빌드 에러 수정 |
| `docs/ideal/EXPERIENCE.md` | 사용자 피드백 5개 원칙 추가 |
| `docs/ideal/INDEX.md` | frontend/ 폴더 링크 추가 |
| `docs/ideal/frontend/BACKEND_INVENTORY.md` | 신규 |
| `docs/ideal/frontend/DESIGN_RATIONALE.md` | 신규 |
| `docs/ideal/frontend/HISTORY_SYSTEM.md` | 신규 |
| `docs/ideal/frontend/API_CAPABILITIES.md` | 신규 |
| `docs/ideal/frontend/FRONTEND_SPEC.md` | 신규 |

## Phase 4: FRONTEND_SPEC.md v2 완전 재작성

사용자 피드백 7개 포인트 + 추가 논의를 반영하여 FRONTEND_SPEC.md를 v1에서 v2로 완전히 새로 작성.

### v1 → v2 주요 변경사항
1. **모바일 동시 설계**: < 768px에서 2D 맵 + 피드 + 바텀시트
2. **로케이션 노드 시스템**: 이벤트 개별 마커 제거 → 로케이션 노드에 이벤트 귀속
3. **카메라 모드 버튼**: CHALDEAS(글로브) / SHEBA(맵) / Fly — 자동 전환 제거
4. **WorldBriefing 줌 연동**: COSMIC=시대이름, CONTINENTAL=시대요약, REGIONAL=지역요약, LOCAL=장소설명
5. **ViewportFeed 탭+정렬**: 전체/이벤트/인물 탭, 중요도/시간/거리 정렬
6. **Rayshift 순차 탐색**: 이전←현재→다음 (인과 체인, 생애 흐름, 가이드 투어)
7. **소스 모달**: 패널이 아닌 모달로 전환
8. **FGO 칼데아 명칭**: CHALDEAS/SHEBA/TRISMEGISTUS/LAPLACE/Rayshift
9. **FGO 서번트 전용 경험**: NarrativePanel FGO 섹션, TRISMEGISTUS FGO 아카이브, 서번트 상세 뷰
10. **사이드바 탈피**: 플로팅 버튼 (검색/TRISMEGISTUS/Rayshift/LAPLACE/메뉴) + 풀스크린 뷰

### 기획서 구조 (20개 섹션)
1. 설계 철학 (5개 핵심 원칙)
2. 데스크톱 레이아웃
3. 모바일 레이아웃
4. 카메라 모드
5. WorldBriefing
6. ViewportFeed
7. 글로브 마커 시스템
8. NarrativePanel
9. Rayshift 순차 탐색
10. 소스 모달
11. FGO 서번트 경험
12. TRISMEGISTUS 풀스크린 허브
13. 줌 레벨별 경험
14. 시간 이동 경험
15. 인과 흐름
16. 인물 생애 흐름
17. 랜딩/홈 화면
18. 2-탭 규칙 검증
19. 컴포넌트-API 매핑
20. 검증 체크리스트

## 다음 작업
- FRONTEND_SPEC.md v2 승인 후 구현 시작
- Rayshift 컴포넌트 신규 개발
- 로케이션 노드 시스템으로 글로브 마커 전환
- 카메라 모드 버튼 구현 (CHALDEAS/SHEBA/Fly)
- 모바일 레이아웃 구현
