# 2026-02-28: Trismegistus Portal Data Layer

## 목적
트리스메기스토스를 정적 JSON 카탈로그에서 DB 기반 큐레이션 포털로 전환.
3개 신규 테이블 + fgo_servants 테이블 생성 + 시딩 + API.

## DB 위기 & 복원
- alembic_version이 200에 고정 — `import_compact.py`가 원인
- 300+ 테이블(historical_chains, event_details 등) 전부 미존재
- `pg_restore`로 2/27 백업 복원 → 601로 정상화
- `import_compact.py`에서 alembic_version import 제거 (재발 방지)

## 변경 파일

### 신규
| 파일 | 설명 |
|------|------|
| `backend/app/models/v2/portal.py` | PortalItem, Collection, CollectionEntry ORM |
| `backend/alembic/versions/602_trismegistus_portal.py` | 마이그레이션 (601→602) |
| `backend/scripts/seed_portal.py` | JSON→DB 시딩 (portal_items, fgo_servants, collections) |
| `backend/app/api/v1/portal.py` | Portal API (/api/v1/portal/*) |

### 수정
| 파일 | 설명 |
|------|------|
| `backend/app/models/v2/fgo.py` | FGOServant에 name_ko, dialogue_lines 등 추가 |
| `backend/app/models/v2/__init__.py` | Portal 모델 export |
| `backend/app/models/__init__.py` | Portal 모델 등록 (alembic metadata) |
| `backend/app/api/v1/router.py` | Portal 라우터 등록 |
| `backend/app/api/v1/showcases.py` | DB 읽기 + JSON fallback으로 리팩토링 |
| `backend/scripts/import_compact.py` | alembic_version import 제거 |

## 테이블 스키마

### portal_items (34 rows)
- showcase JSON 16개 항목 + servants.json 12개 + history/literature/music
- slug, item_type, 다국어 title/description, sections(JSONB), related_servants(JSONB)

### fgo_servants (449 rows, 82 person_id linked)
- Atlas Academy index.json 기반
- fgo_db_comparison.json으로 person_id 매핑

### collections (3개) + collection_entries (10개)
- FGO Main Story, Greece & Rome, Arts & Culture

## API 엔드포인트
```
GET /api/v1/portal/items              — 목록 (type, is_featured 필터)
GET /api/v1/portal/items/{slug}       — 단일 상세
GET /api/v1/portal/collections        — 컬렉션 목록
GET /api/v1/portal/collections/{slug} — 컬렉션 상세 (entries 포함)
GET /api/v1/portal/featured           — 피처드 아이템 + 컬렉션
```

기존 `/api/v1/showcases/*` 엔드포인트 — DB 읽기 + JSON fallback으로 하위 호환 유지.

## 다음 작업
- 프론트엔드 Portal UI (매거진 홈 + 컬렉션 포털)
- 더 많은 컬렉션 시딩 (전쟁의 역사, 동아시아 등)
- fgo_servants에 is_original, chapter_count 데이터 채우기
