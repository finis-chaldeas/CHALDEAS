# 남은 작업 정리

**작성일**: 2026-02-21
**기준**: Archive DB (E:\PostgreSQL\data) 상태

---

## 현재 상태 요약

### 데이터 (Archive DB)

| 항목 | 수량 | 비고 |
|------|------|------|
| Events | 28,331 | 100% 카테고리 분류됨 |
| Persons | 190,710 | 93.9% domain 분류됨 |
| Locations | 17,723 | 90% 상세 정보 있음 |
| Sources | 181,550 | 100% 원문(content_raw) 보유 |
| Entity Narratives (event) | 2,332 | GPT-5.1, 평균 1,130자 |
| Entity Narratives (person) | 1,524 | GPT-5.1, 평균 1,582자 |
| Period Narratives | 391 | GPT-5.1, 6개 지역별 포함 |
| Event Relationships | 16,463 | 257건 인과 설명 enriched |
| Event Hierarchy (parent_event_id) | 10,013 (35.3%) | Wikidata P361 기반 |

### 파이프라인 비용

- **지출**: ~$27 (4,541 LLM calls, ~13시간)
- **미실행**: Tier C 이벤트 ~$11, Tier B 인물 ~$57

---

## Track 1: 백엔드 — API 데이터 노출

**문제**: LLM 큐레이션으로 생성한 3,856개 서사가 **API에 노출되지 않는다.**

### 1-1. Events API에 entity_narratives 추가

| 파일 | 변경 |
|------|------|
| `backend/app/api/v1/events.py` | event_to_dict()에 entity_narratives JOIN |
| `backend/app/schemas/event.py` | narrative, significance, causes, consequences 필드 추가 |

현재: events/{id} 응답에 description(41자)만 있음
목표: narrative(1,130자), significance, causes[], consequences[] 포함

### 1-2. Persons API에 entity_narratives 추가

| 파일 | 변경 |
|------|------|
| `backend/app/api/v1/persons.py` | person detail에 entity_narratives JOIN |
| `backend/app/schemas/person.py` | narrative, significance, key_achievements 필드 추가 |

현재: persons/{id} 응답에 biography(32자)만 있음
목표: narrative(1,582자), significance, key_achievements[] 포함

### 1-3. Event Relationships 엔드포인트 생성

| 파일 | 변경 |
|------|------|
| `backend/app/api/v1/events.py` | GET /events/{id}/relationships 추가 |
| `backend/app/schemas/event.py` | EventRelationship 스키마 추가 |

현재: event_relationships 테이블에 16,463건 (257건 rich description) 있으나 **API 없음**
목표: relationship_type, description, strength, certainty 노출

### 1-4. Timeline API 보강

| 파일 | 변경 |
|------|------|
| `backend/app/api/v1/timeline.py` | causes, consequences 배열 포함 |

현재: narrative, significance만 반환
목표: causes[], consequences[], curated_status 추가

**예상 작업량**: 3~4시간

---

## Track 2: Compact DB 동기화

**문제**: LLM 큐레이션은 Archive DB(44GB, HDD)에서 실행됨. 개발/서빙용 Compact DB(150MB, SSD)는 **구 데이터**.

### 2-1. Archive → Compact Export/Import

```powershell
# Archive DB 시작
.\tools\switch-db.ps1 archive

# CSV 추출
cd backend
python scripts/export_compact.py

# Compact DB로 전환
.\tools\switch-db.ps1 compact

# 스키마 + 데이터 임포트
python -m alembic upgrade head
python scripts/import_compact.py
```

**주의**: export_compact.py가 entity_narratives, period_narratives 테이블을 포함하는지 확인 필요. 안 하면 추가해야 함.

**예상 작업량**: 30분~1시간

---

## Track 3: 프론트엔드 — V4 구현

`docs/planning/FRONTEND_VISION_V4.md` 참조.

### Phase 1: 데이터 표시 (Track 1 완료 후)

| 작업 | 컴포넌트 | 내용 |
|------|---------|------|
| 3-1 | NarrativeCard | 이벤트/인물 서사 카드 (EventDetailPanel 대체) |
| 3-2 | PersonNarrativeCard | 인물 서사 카드 (PersonDetailView 개선) |

기존 EventDetailPanel과 PersonDetailView에 narrative 데이터를 **추가 표시**하는 것부터 시작.
전면 재설계는 이후.

### Phase 2: 맥락 오버레이

| 작업 | 컴포넌트 | 내용 |
|------|---------|------|
| 3-3 | WorldBriefing | 시대/지역 맥락 오버레이 (period_narratives 활용) |
| 3-4 | ParallelWorlds | "같은 시대, 다른 곳" 패널 |

### Phase 3: 흐름 경험

| 작업 | 컴포넌트 | 내용 |
|------|---------|------|
| 3-5 | CausalFlow | 인과관계 시각화 + 자동 흐름 |
| 3-6 | DeepRead | 읽기 모드 (독자용) |

### Phase 4: 구조 전환

| 작업 | 내용 |
|------|------|
| 3-7 | 사이드바 제거, 글로브 전체화면화 |
| 3-8 | 진입점 2가지로 단순화 |
| 3-9 | 모바일 최적화 |

**예상 작업량**: Phase 1은 2~3일, 전체는 1~2주

---

## Track 4: 데이터 보강 (선택)

### 4-1. LLM 큐레이션 Tier 확장

| 작업 | 대상 | 비용 | 우선순위 |
|------|------|------|---------|
| Step 1 Tier C | 이벤트 3,508건 (importance 50~70) | ~$11 | 낮음 |
| Step 5 Tier B | 인물 7,182명 (importance 70~90) | ~$57 | 중간 |

```bash
cd backend
python ../poc/scripts/curate_with_llm.py --step 1 --tier C
python ../poc/scripts/curate_with_llm.py --step 5 --tier B
```

### 4-2. Event Hierarchy 보강

현재 35.3% (10,013/28,331) parent_event_id 할당됨.
나머지 64.7%는 Wikidata에 P361 데이터가 없는 이벤트.

| 방법 | 대상 | 비용 |
|------|------|------|
| LLM 분류 | 상위 이벤트 매칭 | ~$5~10 |
| 수동 큐레이션 | 중요 이벤트만 | 무료 |

### 4-3. Person-Event 연결 보강

현재 20.5% 연결. 79.5% 미연결.

| 방법 | 대상 | 비용 |
|------|------|------|
| Source text 기반 추출 | 기존 스크립트 실행 | 무료 |
| Wikidata P793 매칭 | significant event | 무료 |

### 4-4. 큐레이션 콘텐츠 제작

| 콘텐츠 | 현재 | 목표 | 방법 |
|--------|------|------|------|
| SHEBA Guided Tours | 18개 | 50개 | GPT-5.1 + 검수 |
| Domain Stories | 0개 | 10개 | GPT-5.1 + 검수 |
| Person Stories | 0개 | 20개 | GPT-5.1 + 검수 |

---

## Track 5: 문서 정리 (완료)

### 완료된 정리

| 작업 | 상태 |
|------|------|
| Frontend 재설계 문서 5개 → archive | ✅ 완료 |
| MASTER_PLAN 구버전 → archive | ✅ 완료 |
| completed/ 21개 → archive | ✅ 완료 |
| deprecated/ 31개 → archive | ✅ 완료 |
| Frontend Vision V4 작성 | ✅ 완료 |
| 세션 로그 업데이트 | ✅ 완료 |

### 남은 정리

| 작업 | 우선순위 |
|------|---------|
| data_model/ 6개 → FINAL_SCHEMA에 통합 or archive | 낮음 |
| wikidata/ 5개 → 1개로 통합 | 낮음 |
| classification/ 5개 → 1개로 통합 | 낮음 |
| future_plan/ 중 next_phase와 중복분 archive | 낮음 |

---

## 우선순위 정리

### 즉시 (오늘)

```
1. Track 1 (백엔드 API 노출) — entity_narratives를 API에 추가
2. Track 2 (Compact DB 동기화) — enriched 데이터를 개발 DB에 반영
```

이 두 개가 끝나면 **프론트엔드에서 바로 서사 데이터를 볼 수 있다.**

### 단기 (이번 주)

```
3. Track 3 Phase 1 (프론트엔드 서사 표시) — 기존 UI에 narrative 추가
4. Track 3 Phase 2 (WorldBriefing) — 시대 맥락 오버레이
```

### 중기 (다음 주)

```
5. Track 3 Phase 3~4 (흐름 경험 + 구조 전환)
6. Track 4-1 (Tier B 인물 ~$57 — 결정 필요)
```

### 장기 (월 단위)

```
7. Track 4-2~3 (Hierarchy/Person-Event 보강)
8. Track 4-4 (큐레이션 콘텐츠 50+개)
```

---

## 의존관계

```
Track 1 (API 노출)
    ↓
Track 2 (DB 동기화)
    ↓
Track 3 Phase 1 (서사 표시) ←── 여기서 처음으로 유저가 enriched 데이터를 봄
    ↓
Track 3 Phase 2~4 (새 경험)
    ↑
Track 4 (데이터 보강) ←── 독립적, 언제든 실행 가능
```
