# Database Schema

## 구현 상태: Migration 302 (head) — 2026-02-17

> **Location System Overhaul (Migration 300)**: locations 37→11컬럼 슬림화, territories/event_coords_cache 추가
>
> **Person System Overhaul (Migration 301)**: persons 44→18컬럼 슬림화, person_details/person_names/location_details 테이블 분리
>
> **Event System Overhaul (Migration 302)**: events 43→21컬럼 슬림화, event_details 테이블 분리, aggregate 로케이션 상속

## ER Diagram

```
┌─────────────┐       ┌─────────────────┐       ┌─────────────┐
│  Category   │◄──────│      Event      │───────►│  Location   │
├─────────────┤       ├─────────────────┤       ├─────────────┤
│ id          │       │ id              │       │ id          │
│ name        │       │ title           │       │ name        │
│ name_ko     │       │ title_ko        │       │ name_ko     │
│ slug        │       │ date_start (*)  │       │ name_ja     │
│ color       │       │ date_end        │       │ latitude    │
│ parent_id   │       │ importance      │       │ longitude   │
└─────────────┘       │ category_id     │       │ location_type│
                      │ location_id     │       │ parent_loc_id│
                      │ parent_event_id │       └──────┬──────┘
                      │ is_aggregate    │              │
                      │ hierarchy_level │     ┌────────┼────────┐
                      └───────┬─────────┘     ▼                 ▼
                              │        ┌──────────────┐ ┌──────────────┐
              ┌───────────────┼──────┐ │location_details│ │location_names│
              │               │      │ │(1:1 상세정보)   │ │(1:M 별칭)    │
              ▼               ▼      ▼ └──────────────┘ └──────────────┘
       event_persons  event_locations  event_sources
              │               │          │
              ▼               ▼          ▼
        ┌──────────┐   ┌─────────┐  ┌─────────┐
        │  Person  │   │Location │  │ Source  │
        └────┬─────┘   └─────────┘  └─────────┘
             │
    ┌────────┼────────┐
    ▼                 ▼
┌──────────────┐ ┌──────────────┐       ┌──────────────┐
│person_details│ │ person_names │       │event_details │
│(1:1 상세정보) │ │(1:M 별칭)    │       │(1:1 상세정보) │
└──────────────┘ └──────────────┘       └──────────────┘
```

## Compact DB 데이터 현황

| 테이블 | 행수 | 비고 |
|--------|------|------|
| events | 28,331 | 핵심 이벤트 노드 |
| event_details | 28,331 | description 24,989건, slug 28,331건 |
| persons | 190,710 | 핵심 인물 노드 |
| person_details | 156,417 | biography 이전 완료 |
| person_names | 0 | archive에서 재추출 필요 |
| locations | 17,723 | 핵심 장소 노드 |
| location_details | 0 | archive에서 재추출 필요 |
| location_names | 0 | archive에서 재추출 필요 |
| sources | 22,977 | 출처 |
| categories | 7 | 카테고리 |
| event_persons | 122,430 | 이벤트-인물 연결 |
| event_locations | 4,612 | 이벤트-장소 연결 |
| event_sources | 22,977 | 이벤트-출처 연결 |
| territories | 214 | 80 큐레이션 + 84 SPARQL + 50 현대국가 |
| territory_locations | 35,963 | 83.2% 커버리지 (14,738/17,723 locations), avg 2.4 per loc |

---

## 핵심 테이블

### events (21컬럼)
역사적 사건의 **핵심 정체성 + 계층 정보**만 저장 (슬림 노드). 콘텐츠는 `event_details`로 분리.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL | Primary Key |
| wikidata_id | VARCHAR(20) | Wikidata QID (UNIQUE) |
| title | VARCHAR(500) | 영문 제목 |
| title_ko | VARCHAR(500) | 한국어 제목 |
| title_ja | VARCHAR(500) | 일본어 제목 |
| date_start | INTEGER | 시작 연도 (음수 = BCE) |
| date_end | INTEGER | 종료 연도 |
| date_precision | VARCHAR(20) | exact/year/decade/century |
| temporal_scale | VARCHAR(20) | evenementielle/conjuncture/longue_duree |
| importance | INTEGER | 중요도 (1-5) |
| certainty | VARCHAR(20) | fact/probable/legendary/mythological |
| category_id | FK → categories | 카테고리 참조 |
| primary_location_id | FK → locations | 주요 장소 (개별 이벤트용, aggregate는 NULL 가능) |
| period_id | FK → periods | Period 참조 |
| parent_event_id | FK → events | 상위 이벤트 (계층 구조, self-ref) |
| is_aggregate | BOOLEAN | Aggregate 이벤트 여부 (전쟁, 운동 등) |
| hierarchy_level | INTEGER | 0=Era, 1=Mega, 2=Aggregate, 3=Major, 4=Minor |
| aggregate_type | VARCHAR(50) | war/movement/dynasty/period/... |
| parent_status | VARCHAR(20) | 계층 상태 |
| created_at | TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | 수정일 |

> **관계**: `details` (EventDetail 1:1, lazy="joined"), `category` (Category), `primary_location` (Location), `parent_event` (Event self-ref)
>
> **계층 구조**: Aggregate 이벤트는 자체 location 없이도 하위 이벤트들의 location을 재귀적으로 상속 (CTE).

### event_details (18컬럼)
이벤트의 부가 정보 (1:1). 콘텐츠, 외부 링크, 정밀 날짜, 디스플레이 힌트.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| event_id | FK (PK) → events | Event 참조 (ON DELETE CASCADE) |
| slug | VARCHAR(500) | URL 라우팅용 슬러그 |
| wikipedia_url | VARCHAR(500) | 위키피디아 링크 |
| image_url | VARCHAR(500) | 대표 이미지 URL |
| description | TEXT | 영문 설명 |
| description_ko | TEXT | 한국어 설명 |
| description_ja | TEXT | 일본어 설명 |
| description_source | VARCHAR(50) | wikipedia_en, llm, manual 등 |
| description_source_url | VARCHAR(500) | 출처 URL |
| date_start_month | INTEGER | 시작 월 (1-12) |
| date_start_day | INTEGER | 시작 일 (1-31) |
| date_end_month | INTEGER | 종료 월 |
| date_end_day | INTEGER | 종료 일 |
| source_reliability | INTEGER | 출처 신뢰도 (1-5, 기본 3) |
| default_collapsed | BOOLEAN | 기본 접힘 여부 |
| min_zoom_level | FLOAT | 최소 줌 레벨 (기본 1.0) |
| created_at | TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | 수정일 |

### persons (18컬럼)
역사적 인물의 **핵심 정체성**만 저장 (슬림 노드). 상세정보는 `person_details`, 별칭은 `person_names`.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL | Primary Key |
| wikidata_id | VARCHAR(20) | Wikidata QID (UNIQUE) |
| name | VARCHAR(255) | 대표명 (영문) |
| name_ko | VARCHAR(255) | 한국어 이름 |
| name_ja | VARCHAR(255) | 일본어 이름 |
| birth_year | INTEGER | 출생 연도 (음수 = BCE) |
| death_year | INTEGER | 사망 연도 |
| floruit_start | INTEGER | 활동 시작 연도 (fl., 생몰 불명 시) |
| floruit_end | INTEGER | 활동 종료 연도 |
| birthplace_id | FK → locations | 출생지 |
| deathplace_id | FK → locations | 사망지 |
| role | VARCHAR(255) | king, philosopher, general, prophet 등 |
| certainty | VARCHAR(20) | fact/probable/legendary/mythological |
| created_at | TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | 수정일 |
| description | TEXT | **레거시** — biography로 이전됨, 향후 삭제 예정 |
| description_model | VARCHAR(50) | **레거시** — 향후 삭제 예정 |
| description_at | TIMESTAMP | **레거시** — 향후 삭제 예정 |

> **관계**: `details` (PersonDetail 1:1), `names` (PersonName[] 1:M), `birthplace`/`deathplace` (Location)
>
> **레거시 컬럼 주의**: description/description_model/description_at은 DB에만 잔존. ORM 모델(`person.py`)에는 없음. person_details.biography로 이전 완료. 다음 마이그레이션에서 삭제 예정.

### person_details (19컬럼)
인물의 부가 정보 (1:1). 노드 정체성이 아닌 콘텐츠 데이터.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| person_id | FK (PK) → persons | Person 참조 (ON DELETE CASCADE) |
| slug | VARCHAR(255) | URL 라우팅용 슬러그 |
| wikipedia_url | VARCHAR(500) | 위키피디아 링크 |
| image_url | VARCHAR(500) | 대표 이미지 URL |
| birth_month | INTEGER | 출생 월 (1-12) |
| birth_day | INTEGER | 출생 일 (1-31) |
| death_month | INTEGER | 사망 월 |
| death_day | INTEGER | 사망 일 |
| birth_date_precision | VARCHAR(20) | year/month/day |
| death_date_precision | VARCHAR(20) | year/month/day |
| biography | TEXT | 영문 전기 |
| biography_ko | TEXT | 한국어 전기 |
| biography_ja | TEXT | 일본어 전기 |
| biography_source | VARCHAR(50) | wikipedia_en, wikipedia_ko, llm, manual |
| biography_source_url | VARCHAR(500) | 출처 URL |
| category_id | FK → categories | 카테고리 참조 |
| era | VARCHAR(100) | Classical Antiquity, Medieval 등 |
| created_at | TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | 수정일 |

### person_names (13컬럼)
인물의 별칭/다국어명 (1:M). 같은 인물이 언어/시대/문맥에 따라 다른 이름.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL | Primary Key |
| person_id | FK → persons | Person 참조 (ON DELETE CASCADE) |
| name | VARCHAR(255) | 이름 |
| name_ko | VARCHAR(255) | 한국어 이름 |
| name_ja | VARCHAR(255) | 일본어 이름 |
| valid_from | INTEGER | 유효 시작 연도 |
| valid_until | INTEGER | 유효 종료 연도 |
| language | VARCHAR(10) | 언어 코드 (en, ko, ja, la 등) |
| is_primary | BOOLEAN | 대표명 여부 |
| name_type | VARCHAR(30) | official/regnal/epithet/religious/alternate/romanized/native |
| source | VARCHAR(100) | wikidata, manual, wikipedia |
| wikidata_id | VARCHAR(50) | 해당 명칭의 Wikidata QID |
| created_at | TIMESTAMP | 생성일 |

### locations (12컬럼)
지리적 장소의 핵심 정보만 저장. 설명은 `location_details`로 분리.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL | Primary Key |
| wikidata_id | VARCHAR(20) | Wikidata QID (UNIQUE) |
| name | VARCHAR(255) | 장소명 |
| name_ko | VARCHAR(255) | 한국어 지명 |
| name_ja | VARCHAR(255) | 일본어 지명 |
| latitude | DECIMAL(10,7) | 위도 |
| longitude | DECIMAL(10,7) | 경도 |
| location_type | VARCHAR(50) | point/natural/sea (NOT NULL, 기본 'point') |
| country | VARCHAR(100) | 현대 국가 (필터/그룹핑용) |
| parent_location_id | FK → locations | 상위 장소 (self-ref) |
| created_at | TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | 수정일 |

> **관계**: `details` (LocationDetail 1:1), `names` (LocationName[] 1:M), `parent_location` (self-ref)

### location_details (8컬럼)
장소의 부가 정보 (1:1). description, 외부 링크 등.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| location_id | FK (PK) → locations | Location 참조 (ON DELETE CASCADE) |
| description | TEXT | 영문 설명 |
| description_ko | TEXT | 한국어 설명 |
| description_ja | TEXT | 일본어 설명 |
| description_source | VARCHAR(50) | 출처 유형 |
| description_source_url | VARCHAR(500) | 출처 URL |
| wikipedia_url | VARCHAR(500) | 위키피디아 링크 |
| created_at | TIMESTAMP | 생성일 |

### location_names (9컬럼)
장소의 시대별/다국어 명칭 (1:M).

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL | Primary Key |
| location_id | FK → locations | Location 참조 (ON DELETE CASCADE) |
| name | VARCHAR(255) | 이름 |
| name_ko | VARCHAR(255) | 한국어 이름 |
| name_ja | VARCHAR(255) | 일본어 이름 |
| valid_from | INTEGER | 유효 시작 연도 |
| valid_until | INTEGER | 유효 종료 연도 |
| language | VARCHAR(10) | 언어 코드 |
| created_at | TIMESTAMP | 생성일 |

### sources (18컬럼)
출처 정보를 저장합니다 (LAPLACE용).

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL | Primary Key |
| name | VARCHAR(255) | 출처명 |
| type | VARCHAR(50) | primary/secondary/digital_archive |
| url | VARCHAR(500) | URL |
| archive_type | VARCHAR(50) | perseus/ctext/gutenberg 등 |
| reliability | INTEGER | 신뢰도 (1-5) |
| document_id | VARCHAR(255) | 원본 문서 ID |
| document_path | VARCHAR(500) | 파일 경로 |
| title | VARCHAR(500) | 문서 제목 |
| original_year | INTEGER | 원본 작성 연도 |
| language | VARCHAR(10) | 언어 코드 |

### categories (10컬럼)
이벤트/인물 분류 카테고리 (계층 구조).

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL | Primary Key |
| name | VARCHAR(100) | 카테고리명 |
| name_ko | VARCHAR(100) | 한국어명 |
| slug | VARCHAR(100) | URL 슬러그 |
| color | VARCHAR(20) | 표시 색상 |
| icon | VARCHAR(50) | 아이콘 |
| parent_id | FK → categories | 상위 카테고리 (self-ref) |

---

## 연관 테이블

### event_persons (4컬럼)
| 컬럼 | 설명 |
|------|------|
| event_id | FK → events |
| person_id | FK → persons |
| role | VARCHAR — commander, participant 등 |
| certainty | VARCHAR — fact/probable/legendary |

### event_locations (5컬럼)
| 컬럼 | 설명 |
|------|------|
| event_id | FK → events |
| location_id | FK → locations |
| role | VARCHAR — location/origin/destination |
| match_method | VARCHAR(30) — 매칭 방법 |
| distance_km | FLOAT — 거리 |

### event_sources (4컬럼)
| 컬럼 | 설명 |
|------|------|
| event_id | FK → events |
| source_id | FK → sources |
| page_reference | VARCHAR |
| quote | TEXT |

---

## 보조 테이블

### event_coords_cache (6컬럼)
이벤트의 원본 좌표 캐시 (location 재할당용).

| 컬럼 | 타입 | 설명 |
|------|------|------|
| event_id | FK (PK) → events | ON DELETE CASCADE |
| latitude | DECIMAL(10,7) | 위도 |
| longitude | DECIMAL(10,7) | 경도 |
| coord_source | VARCHAR(30) | p625, p276_resolved, inherited 등 |
| source_qid | VARCHAR(20) | 소스 Wikidata QID |
| created_at | TIMESTAMP | 생성일 |

### territories (9컬럼)
정치 영역 (제국, 왕국 등). 164개 시드 완료 (고대 이집트 ~ 현대 한국).

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL | Primary Key |
| wikidata_id | VARCHAR(20) | UNIQUE |
| name | VARCHAR(255) | 명칭 |
| name_ko | VARCHAR(255) | 한국어명 |
| territory_type | VARCHAR(50) | empire/kingdom/republic/caliphate/dynasty/civilization/city_state 등 |
| founded_year | INTEGER | 건국 연도 (음수 = BCE) |
| dissolved_year | INTEGER | 멸망 연도 (NULL = 현존) |
| created_at | TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | 수정일 |

### territory_locations (7컬럼)
시대별 장소-영역 소속.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL | Primary Key |
| territory_id | FK → territories | ON DELETE CASCADE |
| location_id | FK → locations | ON DELETE CASCADE |
| valid_from | INTEGER | 소속 시작 연도 |
| valid_until | INTEGER | 소속 종료 연도 |
| relation_type | VARCHAR(50) | contains/capital |
| created_at | TIMESTAMP | 생성일 |

---

## BCE 날짜 처리

- 내부적으로 음수로 저장 (490 BCE → -490)
- 표시 시 변환: `date_display` property 사용

```python
# 예시
event.date_start = -490  # 490 BCE
event.date_display  # "490 BCE"
```

---

## V1 확장 테이블 (Historical Chain System)

### periods (13컬럼)
시대/기간을 저장합니다 (Braudel의 시간 척도 지원).

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL | Primary Key |
| name | VARCHAR(255) | 시대명 (영문) |
| name_ko | VARCHAR(255) | 시대명 (한국어) |
| slug | VARCHAR(255) | URL 슬러그 (UNIQUE) |
| year_start | INTEGER | 시작 연도 (음수 = BCE) |
| year_end | INTEGER | 종료 연도 |
| temporal_scale | VARCHAR(20) | evenementielle/conjuncture/longue_duree |
| parent_id | FK | 상위 시대 참조 (계층 구조) |

### historical_chains
역사의 고리 (4가지 큐레이션 유형).

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL | Primary Key |
| chain_type | VARCHAR(20) | person_story/place_story/era_story/causal_chain |
| slug | VARCHAR(255) | URL 슬러그 (UNIQUE) |
| title | VARCHAR(500) | 제목 |
| summary | TEXT | 요약 |
| focal_person_id | FK | Person Story용 인물 |
| focal_location_id | FK | Place Story용 장소 |
| focal_period_id | FK | Era Story용 시대 |
| focal_event_id | FK | Causal Chain용 핵심 사건 |

### text_mentions
NER 추출 출처 추적.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL | Primary Key |
| entity_type | VARCHAR(50) | person/location/event |
| entity_id | INTEGER | 엔티티 ID |
| source_id | FK → sources | 출처 |
| mention_text | VARCHAR(500) | 언급 텍스트 |
| context_text | TEXT | 문맥 |
| confidence | FLOAT | 추출 신뢰도 |
| extraction_model | VARCHAR(100) | 추출 모델 |

### entity_aliases
엔티티 별칭 (중복 제거용).

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL | Primary Key |
| entity_type | VARCHAR(50) | person/location/event |
| entity_id | INTEGER | 정규 엔티티 ID |
| alias | VARCHAR(500) | 별칭 |
| alias_type | VARCHAR(50) | alternate/translation/misspelling/historical |
| language | VARCHAR(10) | en/ko/la/gr 등 |

---

## Alembic 마이그레이션

```bash
cd backend
python -m alembic upgrade head    # 최신으로 업그레이드
python -m alembic current         # 현재 버전 확인
```

### 마이그레이션 체인
```
001_v1_schema → ... → 200_connections → 300_location_system → 301_person_system → 302_event_system (HEAD)
```

| 마이그레이션 | 설명 |
|------------|------|
| `001_v1_schema_initial.py` | V1 스키마 초기 (periods, chains, text_mentions 등) |
| `300_location_system_overhaul.py` | Location 슬림화 (37→11), territories, event_coords_cache |
| `301_person_system_overhaul.py` | Person 슬림화 (44→18), person_details, person_names, location_details |
| `302_event_system_overhaul.py` | Event 슬림화 (43→21), event_details |

> **Idempotent**: 300, 302는 컬럼/테이블 존재 여부 체크 후 실행 (compact DB 혼합 상태 대응).

---

## 구현 파일

**핵심 모델:**
- `backend/app/models/event.py` (21컬럼 슬림 노드)
- `backend/app/models/event_detail.py` (1:1 상세정보)
- `backend/app/models/person.py` (15컬럼 슬림 노드, DB에는 레거시 3컬럼 잔존)
- `backend/app/models/person_detail.py` (1:1 상세정보)
- `backend/app/models/person_name.py` (1:M 별칭)
- `backend/app/models/location.py` (12컬럼 슬림 노드, country 포함)
- `backend/app/models/location_detail.py` (1:1 상세정보)
- `backend/app/models/location_name.py` (1:M 별칭)
- `backend/app/models/source.py`
- `backend/app/models/category.py`
- `backend/app/models/associations.py`
- `backend/app/models/territory.py`
- `backend/app/models/event_coords_cache.py`
