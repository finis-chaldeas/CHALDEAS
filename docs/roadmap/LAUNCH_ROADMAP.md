# CHALDEAS 공개 런치 로드맵

## 현재 상태 (2026-03-05 기준)

| 항목 | 수치 | 비고 |
|------|------|------|
| 시프트 | 896개 (전부 aggregate) | person_story/place_story 없음 |
| 페이지 | 9,367개 | 평균 10.5p/shift |
| 위젯 보유 페이지 | 30 (0.3%) | 거의 비어있음 |
| 영문 내러티브 | 9,068p (96%) | OK |
| 한국어 내러티브 | 3,368p (36%) | imp5: 46%, imp4: 39% |
| 완전 번역 시프트 | 113/896 (12.6%) | |
| 포탈 아이템 | 34개 | history 3개뿐 |
| 이벤트 계층 (parent) | 35.3% (10,013/28,331) | 목표 70-85% |
| 모바일 레이아웃 | 비활성화 상태 | MobileLayout 존재하나 미사용 |
| 에러 바운더리 | 없음 | |
| 투어 시스템 | 18 에피소드 구현, 진입점 없음 | |

---

## 태스크 목록

| # | 문서 | 제목 | 난이도 | 예상 시간 |
|---|------|------|--------|-----------|
| 01 | [ERROR_BOUNDARY.md](01_ERROR_BOUNDARY.md) | React ErrorBoundary 추가 | 쉬움 | 30분 |
| 02 | [WIDGET_ENHANCEMENT.md](02_WIDGET_ENHANCEMENT.md) | 위젯 배치 강화 (400 시프트) | 대규모 | API 비용 + 대기 |
| 03 | [KOREAN_TRANSLATION.md](03_KOREAN_TRANSLATION.md) | 한국어 번역 커버리지 확대 | 대규모 | API 비용 + 대기 |
| 04 | [EVENT_HIERARCHY.md](04_EVENT_HIERARCHY.md) | 이벤트 계층구조 확장 | 중간 | 반나절 스크립트 + 실행 |
| 05 | [PORTAL_CONTENT.md](05_PORTAL_CONTENT.md) | 포탈 콘텐츠 배치 생성 | 중간 | API 비용 + 큐레이션 |
| 06 | [ONBOARDING.md](06_ONBOARDING.md) | 온보딩 + 투어 진입점 | 중간 | 반나절 |
| 07 | [MOBILE.md](07_MOBILE.md) | 모바일 경험 복구 | 어려움 | 1-2일 |

---

## 권장 실행 순서

```
Phase A — 즉시 (안정성)
  01. ErrorBoundary

Phase B — 콘텐츠 채우기 (병렬 실행 가능)
  02. 위젯 배치 enhance (imp5 → imp4 순)
  03. 한국어 번역 (enhance가 page_narrative_ko도 생성하므로 02와 동시 진행)
  04. 이벤트 계층구조 확장 (Wikidata P361)
  05. 포탈 아이템 배치 생성

Phase C — UX 개선
  06. 온보딩 + 투어 진입점
  07. 모바일 경험

Phase D — 공개 전 최종
  - 전체 QA (데스크톱 + 모바일)
  - 성능 프로파일링
  - 배포 + 도메인 최종 확인
```

02/03은 `--enhance`가 위젯 + 한국어 내러티브를 동시에 생성하므로 사실상 하나의 배치 작업.
04는 02/03과 독립적이라 병렬 가능.
