# CHALDEAS 스키마 구현 계획

> **작성일**: 2026-02-05
> **기준 문서**: `docs/planning/FINAL_SCHEMA.md`

---

## 목표

1. 기존 DB 완전 폐기
2. FINAL_SCHEMA.md 기준 새 테이블 13개 생성
3. Wikidata 덤프에서 데이터 추출/임포트
4. 모든 데이터에 출처(source/mention) 연결

---

## Phase 1: 스키마 구현

### CP-1.1: 기본 엔티티 테이블 (의존성 없음)
| 작업 | 테이블 | 확인 방법 |
|------|--------|----------|
| [ ] | locations | INSERT 1개 → SELECT 확인 |
| [ ] | territories | INSERT 1개 → SELECT 확인 |
| [ ] | sources | INSERT 1개 → SELECT 확인 |

### CP-1.2: 엔티티 테이블 (의존성 있음)
| 작업 | 테이블 | 의존성 | 확인 방법 |
|------|--------|--------|----------|
| [ ] | persons | locations | birthplace_id FK 확인 |
| [ ] | groups | territories | territory_id FK 확인 |
| [ ] | events | locations | primary_location_id FK 확인 |

### CP-1.3: 출처 연결 테이블
| 작업 | 테이블 | 확인 방법 |
|------|--------|----------|
| [ ] | mentions | source→person 연결 테스트 |

### CP-1.4: 관계 테이블
| 작업 | 테이블 | 확인 방법 |
|------|--------|----------|
| [ ] | links | person→event 관계 테스트 |
| [ ] | location_names | 시대별 이름 조회 |
| [ ] | territory_locations | 영역-장소 연결 |
| [ ] | group_members | 집단-개인 연결 |
| [ ] | event_participants | 이벤트 참여자 |
| [ ] | event_locations | 이벤트 장소 |

---

## Phase 2: 추출 스크립트

### CP-2.1: Wikidata 추출기 수정
| 작업 | 설명 |
|------|------|
| [ ] | 기존 fresh_extract.py에 source 정보 추가 |
| [ ] | 각 엔티티의 Wikidata description 추출 |
| [ ] | 참조(reference) 정보 추출 (P854 등) |

### CP-2.2: 임포트 스크립트 수정
| 작업 | 설명 |
|------|------|
| [ ] | sources 테이블에 Wikidata 출처 생성 |
| [ ] | mentions 테이블에 연결 생성 |
| [ ] | 모든 엔티티에 mention 있는지 검증 |

---

## Phase 3: 소규모 테스트

### CP-3.1: 100개 테스트
| 작업 | 기준 |
|------|------|
| [ ] | 각 타입 20개씩 추출 |
| [ ] | 임포트 |
| [ ] | 모든 엔티티에 mention 있는지 확인 |
| [ ] | 관계 테이블 데이터 확인 |

### CP-3.2: 1000개 테스트
| 작업 | 기준 |
|------|------|
| [ ] | 각 타입 200개씩 추출 |
| [ ] | 임포트 |
| [ ] | 성능 측정 |
| [ ] | 데이터 품질 검증 |

---

## Phase 4: 전체 임포트

### CP-4.1: 전체 추출
| 작업 | 예상 |
|------|------|
| [ ] | locations 전체 | ~50만개 |
| [ ] | territories 전체 | ~1만개 |
| [ ] | persons 전체 | ~500만개 (필터링 필요) |
| [ ] | groups 전체 | ~10만개 |
| [ ] | events 전체 | ~20만개 |

### CP-4.2: 전체 임포트
| 작업 | 확인 |
|------|------|
| [ ] | 순서대로 임포트 |
| [ ] | 관계 테이블 생성 |
| [ ] | mentions 전체 연결 |
| [ ] | 품질 검증 쿼리 실행 |

---

## Phase 5: 검증

### CP-5.1: 품질 검증
```sql
-- mention 없는 엔티티 (0이어야 함)
SELECT COUNT(*) FROM persons p
WHERE NOT EXISTS (SELECT 1 FROM mentions m WHERE m.target_type='person' AND m.target_id=p.id);

-- source 없는 mention (0이어야 함)
SELECT COUNT(*) FROM mentions WHERE source_id IS NULL;

-- content_raw 없는 source (0이어야 함)
SELECT COUNT(*) FROM sources WHERE content_raw IS NULL OR content_raw = '';
```

### CP-5.2: 통계
| 항목 | 목표 |
|------|------|
| 총 엔티티 | 기록 |
| mention 커버리지 | 100% |
| 평균 mention/엔티티 | 기록 |

---

## 현재 진행 상태

| Phase | 상태 | 시작일 | 완료일 |
|-------|------|--------|--------|
| Phase 1 | ✅ 완료 | 2026-02-05 | 2026-02-05 |
| Phase 2 | ✅ 완료 | 2026-02-05 | 2026-02-05 |
| Phase 3 | ✅ CP-3.1 완료 | 2026-02-05 | - |
| Phase 4 | ⏳ 대기 | - | - |
| Phase 5 | ⏳ 대기 | - | - |

---

## 작업 로그

### 2026-02-05
- 계획서 작성
- FINAL_SCHEMA.md 확정
- **Phase 1 완료**:
  - CP-1.1: locations, territories, sources ✅
  - CP-1.2: persons, groups, events ✅
  - CP-1.3: mentions ✅
  - CP-1.4: 6개 관계 테이블 ✅
  - 총 13개 테이블 생성 및 테스트 완료
- **Phase 2 완료**:
  - CP-2.1: extract_with_sources.py 작성 ✅
  - CP-2.2: import_with_sources.py 작성 ✅
  - sources.wikidata_id UNIQUE 제약 추가 (버그 수정)
- **Phase 3 진행 중**:
  - CP-3.1: 100개 테스트 ✅
    - 엔티티 100개, source 100개, mention 100개
    - **Mention Coverage: 100%** (모든 타입)

---
