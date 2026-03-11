# Phase 0: 서번트 링킹 보강

**선행 조건**: 없음
**비용**: $0
**예상 시간**: 5분
**DB 반영**: Yes (fgo_servants.person_id UPDATE만)

---

## 현재 상태

- DB에 82/449 (18%) 서번트만 person_id 연결됨
- `E:\chaldeas_data\processed\fgo\person_links\confirmed_links.json`에 121명 confirmed
- `person_gaps.md` Section 1에 38명 추가 매칭 가능 (DB 검색으로 확인됨)

## 작업

### Step 1: confirmed_links 반영 (121명)

```sql
-- confirmed_links.json의 각 항목에 대해:
UPDATE fgo_servants SET person_id = {person_id}
WHERE servant_id = {servant_id} AND person_id IS NULL;
```

`backend/scripts/link_fgo_persons.py` 수정:
- `confirmed_links.json` 읽기
- person_id가 있는 항목만 DB 업데이트
- dry-run 모드 지원

### Step 2: 추가 38명 매칭 반영

`person_gaps.md` Section 1 리스트 기반.
DB 이름 매칭이 정확한지 수동 검증 필요한 항목:
- Altera → Attila (동일 인물이지만 이름이 다름)
- Amakusa Shirou → 실존 아마쿠사 시로?
- 기타 이름 차이가 큰 매칭

→ 검증 후 `link_fgo_persons.py`에 수동 매핑 추가

### Step 3: 검증

```sql
SELECT count(*) FROM fgo_servants WHERE person_id IS NOT NULL;
-- 기대값: 121 + α (추가 매칭분)
```

## 수정 파일

| 파일 | 변경 |
|------|------|
| `backend/scripts/link_fgo_persons.py` | confirmed_links.json 읽기 + 반영 로직 |

## 주의사항

- persons 테이블에 없는 인물 (신화/전설 128명)은 이 Phase에서 추가 안 함
- 인물 추가는 별도 DB 정리 작업에서 진행 (person_gaps.md 참고)
