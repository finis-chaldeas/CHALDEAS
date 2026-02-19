# Session Log: 2026-02-17 Next Phase 문서 갱신 + 프론트엔드 구조 개편 계획

## Session Info
- **Purpose**: next_phase 문서 현황 갱신 + 전문가/흥미 레벨 프론트엔드 구조 개편 계획 작성
- **이전 세션**: event_location_matching (노드 시스템 구축, Wikidata 스캔 진행 중)

## 한 작업

### 1. INDEX.md 갱신
- Sprint 0.7 추가 (위치 매칭 + 노드 시스템, 진행 중)
- Sprint 0.5 완료 표시
- Sprint 1에 프론트엔드 구조 개편 추가
- 유저 페르소나 → 흥미/전문가 레벨 2-tier 구조로 재작성
- 09_FRONTEND_RESTRUCTURE.md 문서 목록에 추가

### 2. 08_PENDING_IMPROVEMENTS.md 갱신
- B1 섹션: 스캔 89% 진행 현황 반영
- 노드 API/프론트엔드 완료 표시
- 확정된 노드 규칙 명시

### 3. 09_FRONTEND_RESTRUCTURE.md 신규 작성
- **현재 문제 진단** 7가지 (뭘 해야 할지 모름, 단조로운 지구본, 데이터 덤프 사이드바 등)
- **흥미 레벨 (Interest Level)**: 5분 안에 "역사 재밌네?" 경험
  - 랜딩: 3가지 시작 선택지 (서번트/에피소드/자유탐색)
  - 에피소드 투어 모드: 자동 지구본 이동 + 스토리 카드
  - 사이드바: 추천 3개 + 하이라이트 5개 (전체 목록 아님)
  - 서번트/에피소드 = 낚시바늘
- **전문가 레벨 (Expert Level)**: 깊이 파고들 수 있는 도구
  - 필터/정렬/검색/페이지네이션
  - 출처 표시, 네트워크 그래프
  - 지구본 = 분석 도구
- **전환 메커니즘**: 토글, URL 파라미터, localStorage 영속화
- **구현 방법**: 서브컴포넌트 분리 (FeedInterest/FeedExpert 등)
- **구현 순서**: 6 Phase (기반 → 흥미 피드 → 투어 → 랜딩 → 전문가 → 모바일)
- **핵심 비유**: 흥미=넷플릭스, 전문가=위키피디아

## 배경 작업 현황
- Wikidata 스캔 (b45682f): 98M/110M entities, 24,132/28,331 발견 (85%), coords 10,623
- 스캔 (b2bcf71 - 이전): 8.5% (초기 스캔, 느린 HDD)

## 다음 작업
1. Wikidata 스캔 완료 대기 → Phase 2 `--match` 실행
2. 프론트엔드 구조 개편 유저 논의 후 구현 착수
3. Compact DB 서번트 person 6명 이관 (B2)
