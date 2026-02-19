# 08: Pending Improvements & Backlog

> **작성**: 2026-02-17
> **목적**: 이 세션에서 구현된 것, 미구현된 것, 새 개선안 전부 정리

---

## A. 이번 세션에서 구현 완료 (2026-02-17)

### Frontend UX: 4 Entry Points + Globe Zoom
- [x] Navigator 탭 재구성 (Feed/People/Timeline/Servants)
- [x] SHEBA 에피소드 18개 정적 데이터 (shebaEpisodes.ts)
- [x] LAPLACE 타임라인 6 에라 57개 (laplaceTimeline.ts)
- [x] 4단계 Globe 줌 (cosmic/continental/regional/local)
- [x] 줌별 라벨 필터링 (importance 기반)
- [x] ServantPanel 모달 → 인라인 탭으로 이동
- [x] ServantTabDetail (상세 뷰, 책 언급, Wikidata 링크)

### 버그 수정
- [x] `Location.type: str` → `Optional[str]` (Person Detail API 500 에러 수정)
- [x] `flyToLocation` 실제 globe 카메라 이동 (`flyTarget` + `pointOfView()`)

---

## B. 미구현: 위치 매칭/데이터 품질 (원래 우선해야 했던 작업)

> **배경**: `DATA_QUALITY_REPORT.md`에서 이미 진단된 문제들. 8.3% 데이터 오염.

### B1. 전체 이벤트 위치 매칭 (진행 중!)

**현황 (2026-02-17 갱신)**:
```
Total events:              28,331
With primary_location_id:   4,474 (15%)
WITHOUT LOCATION:          23,857 (84%)  ← 노드 매칭으로 채우는 중
Total locations (nodes):   12,908
```

**확정된 규칙 (2026-02-17)**:
- locations = 고정 노드 (12,908개)
- 이벤트 → 가장 가까운 노드에 매칭 (haversine)
- 기존 primary_location_id 보존
- 새 노드 추가 시 → 인근 이벤트 재분배

#### Step 1: Wikidata 덤프 스캔 → 좌표/sitelinks 추출
- [~] **진행 중 (89%)**
  - 도구: `poc/scripts/wikidata/match_event_locations.py --scan`
  - 덤프: `E:\wikidata\latest-all.json` (1.8TB)
  - 결과: `data/compact_export/event_sitelinks.jsonl`
  - 24,132/28,331 QID 발견, P625 좌표 10,623개
  - 체크포인트: 5분 간격 자동 저장, `--resume` 지원

#### Step 2: 최근접 노드 매칭
- [ ] `--match --dry-run` → 검증
- [ ] `--match` → DB 반영 (primary_location_id UPDATE)
- [ ] numpy 벡터화 haversine (12,908 노드 × N 이벤트)

#### Step 3: 나머지 → LLM 지오코딩
- [ ] 좌표 없는 이벤트에 대해 gpt-5-mini Batch API
  - 예상 비용: $2-15

#### Step 4: Backend/Frontend 노드 시스템 (완료!)
- [x] **Backend**: `GET /globe/nodes` + `GET /globe/nodes/{id}/events` API
- [x] **Frontend**: 노드 마커 (이벤트 수 배지, 줌별 필터, active/inactive)
- [x] **문서**: `02_LOCATION_SYSTEM.md`에 노드 규칙 문서화

### B2. Compact DB 데이터 갭
- [ ] **서번트 person_id 6명 누락**
  - Leonidas (1873639), Anastasia (3375247), Robin Hood (7746082)
  - Lu Bu (3714900), Xiang Yu (2088636), Fionn mac Cumhaill (11637816)
  - Archive DB에서 Compact DB로 이관 필요
- [ ] **persons.biography 빈 항목**
  - 대부분 인물이 biography=NULL
  - Wikipedia 첫 문단 추출 스크립트 필요 (extract_biographies.py 패턴)
- [ ] **events.description 빈약**
  - Wikidata 한 줄 요약 → Wikipedia 2-3문장으로 교체

### B3. 위치 계층 시스템
- [ ] **location_names 테이블 데이터 채우기**
  - 마이그레이션 008 이미 존재, 테이블은 비어있음
  - Wikidata P1448 + 시기 한정자(P580/P582) 추출
  - 주요 50개 도시부터 수동 큐레이션
  - 예: Byzantium(BCE 667~330) → Constantinople(330~1453) → Istanbul(1930~)
- [ ] **location_polities 테이블 생성 + 데이터**
  - 시대별 소속 정치체 (Paris: 갈리아 → 로마 → 프랑크 → 프랑스)
  - Wikidata P17 (country) + 시기 한정자

---

## C. Frontend 시각 개선

### C1. 애니메이션/폴리시
- [ ] 네비게이터 탭 전환 fade/slide 애니메이션
- [ ] SHEBA 에피소드 카드 hover 효과 강화 (glow, scale)
- [ ] 타임라인 에라 접힘/펼침 max-height 트랜지션
- [ ] 서번트 클래스 필터 active 상태 시각 피드백

### C2. Globe 시각 개선
- [ ] COSMIC 뷰 atmosphere glow 강화
- [ ] 줌 레벨 전환 시 라벨 fade-in/out
- [ ] 에피소드 클릭 시 도착점 ring pulse 효과
- [ ] CONTINENTAL 줌 인디케이터 표시 (현재 REGIONAL/LOCAL만)

### C3. 데이터 표시 개선
- [ ] Feed 탭 빈 구간에 SHEBA 에피소드 더 노출
- [ ] People 탭 기본 정렬: importance → connections 순
- [ ] 서번트 상세에서 missing person 대응 메시지
- [ ] PersonDetailView 빈 타임라인에 "Explore related events" 대안 제시

---

## D. 데이터 파이프라인 (NEXT_PHASE_PLAN.md Sprint 0 잔여)

### D1. 데이터 enrichment 미완료 항목
- [ ] entity_properties → persons.role 반영
- [ ] QRank 테이블 + importance 재계산
- [ ] Wikipedia biography 대량 추출 (persons)
- [ ] Wikipedia description 대량 추출 (events)

### D2. 서번트 데이터 확장
- [ ] servant_db_mapping.json 100개로 확장 (현재 41개)
- [ ] Atlas Academy에서 전체 서번트 데이터 임포트
- [ ] servant_profiles 테이블 생성 (게임 내 스킬/NP/대사)
- [ ] 비교 카드 데이터 (게임 vs 역사 차이점)

### D3. 새 데이터 수집
- [ ] Singularity/Lostbelt → 역사 시대 매핑 JSON
- [ ] 하이라이트 큐레이션 30개 추가 (SHEBA 에피소드 확장)
- [ ] Simple English Wikipedia 설명 추출

---

## E. 우선순위 제안

### 즉시 (이번 주) — 위치 매칭이 최우선!
| # | 항목 | 카테고리 | 이유 |
|---|------|----------|------|
| 1 | **전체 28,331 이벤트 Wikidata 좌표 추출** | B1 Step 1 | 84% 위치 없음, 가장 큰 데이터 갭 |
| 2 | **기존 매칭 오류 검증 + 수정** | B1 Step 2 | 오염 데이터 정리 |
| 3 | **새 location 엔티티 자동 생성** | B1 Step 4 | 좌표 추출 시 동시 처리 |
| 4 | **Compact DB 서번트 person 6명 이관** | B2 | 서번트 탭 데이터 완성 |

### 다음 (1-2주)
| # | 항목 | 카테고리 |
|---|------|----------|
| 5 | LLM 지오코딩 (Wikidata로 못 찾은 나머지) | B1 Step 3 |
| 6 | persons.biography Wikipedia 추출 | B2/D1 |
| 7 | events.description Wikipedia 교체 | B2/D1 |
| 8 | location_names 50개 큐레이션 | B3 |

### 이후 (2-4주)
| # | 항목 | 카테고리 |
|---|------|----------|
| 9 | servant_db_mapping 100개 확장 | D2 |
| 10 | QRank + importance 재계산 | D1 |
| 11 | 탭 전환 애니메이션 / Globe 폴리시 | C1/C2 |
| 12 | location_polities 데이터 | B3 |

### Backlog
| # | 항목 | 카테고리 |
|---|------|----------|
| 13 | 영토 폴리곤 시각화 (PostGIS) | 장기 |
| 14 | 페르소나 내러티브 시스템 | 장기 |
| 15 | Simple English Wikipedia | D3 |
| 16 | 사용자 기여 시스템 | 장기 |

---

## F. 참고 문서

| 문서 | 관련 항목 |
|------|----------|
| `NEXT_PHASE_PLAN.md` | Sprint 0 체크리스트, 구현 우선순위 |
| `next_phase/01_GLOBE_UX.md` | C2 Globe 개선 상세 |
| `next_phase/02_LOCATION_SYSTEM.md` | B3 위치 계층 상세 |
| `next_phase/03_FEED_UX.md` | C3 Feed 개선 상세 |
| `next_phase/04_FGO_BRIDGE.md` | D2 서번트 확장 상세 |
| `next_phase/05_DATA_REQUIREMENTS.md` | D1-D3 데이터 파이프라인 상세 |
| `completed/DATA_QUALITY_REPORT.md` | B1 위치 매칭 오류 진단 |
| `logs/sessions/20260217_frontend_ux_4_entry_points.md` | A. 이번 세션 상세 로그 |
