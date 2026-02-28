# FGO Servant ↔ Person Linking

**Date**: 2026-02-27
**Status**: Phase 1 완료 (데이터 생성)

## 목적

FGO 서번트 449명을 CHALDEAS DB의 역사 인물(persons 190K)과 연결하는 매칭 파이프라인 구축.

## 변경 파일

- `backend/scripts/link_fgo_persons.py` — 새로 작성
- `docs/ideal/FGO_PERSON_LINK.md` — 기획서

## 결과

| 카테고리 | 수 | 비율 | 설명 |
|---------|------|------|------|
| ✅ Confirmed | **121** | 26.9% | DB 인물과 확정 연결 |
| ⚠️ Review | 5 | 1.1% | 수동 확인 필요 |
| 🔍 Categorized/NoDB | **128** | 28.5% | 신화/전설/허구, DB 미등재 |
| 🎮 FGO Original | 23 | 5.1% | Fate 시리즈 오리지널 캐릭터 |
| ❌ Unmatched | 172 | 38.3% | 추가 매핑 필요 |

### 매칭 방법 분포

| 방법 | 수 |
|------|------|
| manual_seed (수동 시드 → DB 검색) | 72 |
| en_name_exact (영문명 정확 매칭) | 43 |
| manual_no_search (신화/전설, DB에 해당 없음) | 98 |
| manual_not_in_db (검색명은 있지만 DB 미등재) | 30 |
| manual_fgo_original (FGO 오리지널) | 23 |
| ja_name_exact (일본어명 매칭) | 6 |

### 주요 DB 이슈 발견

persons 테이블의 일부 wikidata_id가 잘못된 인물에 할당:
- Q46405 (Spartacus) → Bjørnstjerne Bjørnson
- Q43718 (Vlad III) → Nikolai Gogol
- Q177903 (Quetzalcoatl) → Stephen I of Hungary

→ 이름 기반 매칭으로 우회함

### 출력

```
E:\chaldeas_data\processed\fgo\person_links\
  confirmed_links.json     — 121건 (확정)
  review_candidates.json   — 5건 (검토)
  unmatched.json           — 172건
  missing_persons.json     — 128건 (신화/전설/허구)
  fgo_originals.json       — 23건
  enriched_servants.json   — 449건 (전체 + 연결 정보)
  report.txt               — 리포트
```

## 다음 작업

1. **unmatched 172명** 중 역사 인물 추가 매핑 (수동 시드 확장)
2. **missing 128명** 중 신화/전설 인물을 persons 테이블에 추가 (Phase 2)
3. DB 마이그레이션 + API (Phase 4)
4. TRISMEGISTOS 프론트엔드 연동
