# Session Log: 2026-02-14 Frontend Launch Plan Implementation

## Session Info
- **Plan**: Frontend Launch Plan (8 Phases)
- **Goal**: Make CHALDEAS usable for friends who love history by end of February
- **Approach**: Week 1 데이터 보강 + Week 2 킬러 피처 (Person Story) + 랜딩 경험

## 핵심 문제 & 해결

### 문제
1. 13M persons 있지만 biography, role 등 빈 필드 많음
2. 112.8M entity_properties (P569 생년, P570 몰년, P19 출생지, P106 직업) 있지만 **백엔드에서 전혀 사용 안 함**
3. Story API가 `event_connections`만 의존 → 대부분 인물에 빈 story 반환
4. 84% 이벤트에 위치 정보 없음

### 해결
1. SQL 스크립트로 entity_properties → persons 필드 채우기
2. Story API를 다중 소스 기반으로 재작성 (event_connections → event_persons → synthetic 노드)
3. Properties API로 Wikidata 속성 노출
4. Featured API + 랜딩 페이지로 첫 진입 경험 개선

---

## Work Done

### Phase 1: SQL Scripts (Data Enrichment)
- `backend/scripts/diagnostic_queries.sql` - 현재 데이터 갭 진단 (읽기전용)
- `backend/scripts/enrich_persons.sql` - persons 빈 필드 채우기 (P569→birth_year, P570→death_year, P19→birthplace_id, P20→deathplace_id, P106→role)
- `backend/scripts/enrich_events.sql` - event_locations → events.primary_location_id 채우기
- `backend/scripts/create_indexes.sql` - Featured/Story/Properties 쿼리 최적화 인덱스

### Phase 2: Story API Rewrite (핵심 변경)
- `backend/app/api/v1/story.py` 전체 재작성
- **다중 소스 Story Builder**:
  1. event_connections (기존)
  2. event_persons (fallback - event_connections < 3개일 때)
  3. 합성 birth/death 노드 (entity_properties P19/P20 + person fields)
- StoryNode.event_id → Optional[int] (합성 노드는 None)
- StoryNode.narrative 추가 (합성 노드용 서술문)
- `/check` 엔드포인트도 다중 소스 카운트

### Phase 3: Properties API
- `backend/app/api/v1/properties.py` - 범용 entity_properties 조회 엔드포인트
- `backend/app/api/v1/persons.py`에 `GET /{id}/properties` 추가 - P106, P27, P140 등 핵심 속성

### Phase 4: Featured Persons API
- `backend/app/api/v1/featured.py`
- `GET /featured/persons` - importance 점수 기반 랭킹 (connection_count×2 + event_count×5 + biography×10 + image×5)
- `GET /featured/random` - biography + birth_year 있는 인물 랜덤
- era 필터: ancient(-3000~476), medieval(476~1453), early_modern(1453~1789), modern(1789~)

### Phase 5: Landing Page
- `frontend/src/components/landing/FeaturedPersons.tsx` - 추천 인물 카드 그리드
- `frontend/src/components/landing/Landing.css` - FGO 다크 테마 스타일
- `frontend/src/components/landing/index.ts` - export barrel
- `frontend/src/App.tsx` - 랜딩 오버레이 통합 (localStorage로 첫 방문 감지)
- `frontend/src/api/client.ts` - featuredApi 추가

### Phase 6: PersonDetailView Improvements
- Story 버튼 항상 표시 (조건 `timelineEvents.length > 0` 제거)
- Facts 섹션 추가 (Wikidata properties: 직업, 국적, 종교 등)
- `EntityDetailView.css`에 facts-grid 스타일 추가

### Phase 7: StoryModal Improvements
- StoryNode 인터페이스: event_id → `number | null`, narrative 필드 추가
- narrative 필드 우선 표시 (합성 노드), description은 fallback
- "View Event Details" 버튼: event_id null이면 숨김
- timeline dot key: null event_id 처리 (`synthetic-${idx}`)
- StoryGlobe: event_id 대신 order로 노드 매칭
- 빈 상태 메시지 개선

### Phase 8: Validation
- **TypeScript: 0 errors** (`npx tsc --noEmit` PASS)

---

## Files Changed

### New Files (10)
| # | File | Description |
|---|------|-------------|
| 1 | `backend/scripts/diagnostic_queries.sql` | 데이터 갭 진단 SQL |
| 2 | `backend/scripts/enrich_persons.sql` | persons 필드 보강 SQL |
| 3 | `backend/scripts/enrich_events.sql` | events 위치 보강 SQL |
| 4 | `backend/scripts/create_indexes.sql` | 성능 인덱스 SQL |
| 5 | `backend/app/api/v1/properties.py` | Entity Properties API |
| 6 | `backend/app/api/v1/featured.py` | Featured Persons API |
| 7 | `frontend/src/components/landing/FeaturedPersons.tsx` | 랜딩 페이지 컴포넌트 |
| 8 | `frontend/src/components/landing/Landing.css` | 랜딩 스타일 |
| 9 | `frontend/src/components/landing/index.ts` | 랜딩 exports |
| 10 | `docs/logs/sessions/20260214_frontend_launch.md` | 이 세션 로그 |

### Modified Files (10)
| # | File | Change |
|---|------|--------|
| 1 | `backend/app/api/v1/story.py` | 다중 소스 Story Builder로 전체 재작성 |
| 2 | `backend/app/api/v1/router.py` | properties, featured 라우터 등록 |
| 3 | `backend/app/api/v1/persons.py` | /properties 엔드포인트 추가 |
| 4 | `frontend/src/App.tsx` | 랜딩 컴포넌트 + FeaturedPersons import |
| 5 | `frontend/src/api/client.ts` | featuredApi 추가 |
| 6 | `frontend/src/components/detail/PersonDetailView.tsx` | Story 버튼 상시 표시, Facts 섹션 |
| 7 | `frontend/src/components/detail/EntityDetailView.css` | facts-grid 스타일 |
| 8 | `frontend/src/components/story/StoryModal.tsx` | 합성 노드 처리, narrative |
| 9 | `frontend/src/components/story/StoryGlobe.tsx` | null event_id 지원 |
| 10 | `frontend/src/components/story/story.css` | .node-narrative 스타일 |

---

## 검증 상태
- [x] TypeScript: 0 errors
- [x] SQL diagnostic 실행 (birth_year/death_year 이미 보강됨, biography 0개)
- [x] SQL enrichment: connection_count (4,377명), role (2,303명)
- [x] Backend 기동 테스트 (port 8101 - 8100 ghost process 이슈)
- [x] Frontend 기동 테스트 (port 5200)
- [ ] 랜딩 → 인물 → Story 플로우 테스트 (브라우저)
- [ ] GCP 배포

## API 테스트 결과
| Endpoint | Status | Sample |
|----------|--------|--------|
| `GET /featured/persons` | OK | 4,161명, top: Oda Nobunaga (306 connections) |
| `GET /featured/persons?era=medieval` | OK | 270명, top: Saladin (83) |
| `GET /featured/random` | OK | Random person returned |
| `GET /story/person/6502433` | OK | 27 nodes (25 conn + 26 ep + 2 synthetic) |
| `GET /story/person/6502433/check` | OK | Multi-source counts |
| `GET /persons/6502433/properties` | OK | P106, P140, P27 등 |

## 데이터 보강 결과
- `connection_count`: 4,377명 업데이트 (event_connections 기반)
- `role`: 2,303명 업데이트 (P106 QID → 영문 라벨 매핑)
- `birth_year`/`death_year`: 이미 보강 완료
- `birthplace_id`/`deathplace_id`: 대규모 UPDATE 보류 (1h+ 소요, DB 락 문제)

## Featured API 변경사항
- 원래: `connection_count > 0` 조건 → 모든 persons가 0이라 결과 없음
- 변경: `event_connections` JOIN으로 실제 story 데이터 있는 인물만 반환
- importance = event_connections 개수 기반

## Next Steps
1. 브라우저에서 `http://localhost:5200` 열어서 UI 플로우 테스트
2. 랜딩 → 인물 선택 → Story 확인
3. 문제 없으면 GCP 배포 (sync-db + cloudbuild)
4. (선택) birthplace/deathplace 대규모 UPDATE - 서버 idle 시
