# 백엔드에 뭐가 있는가 — 테이블 전체 목록

프론트엔드 개발자가 "백엔드에 뭐가 있지?"라고 물었을 때 이 문서 하나로 답한다.
각 테이블의 용도, 핵심 컬럼, 프론트엔드 관련성을 설명한다.
전체 컬럼 상세는 `docs/reference/DATABASE.md` 참조.

---

## 1. 핵심 엔티티 (Node + Detail 패턴)

### persons (18컬럼) — 역사적 인물
**핵심 컬럼**: id, wikidata_id, name/name_ko/name_ja, birth_year, death_year, floruit_start/end, birthplace_id, deathplace_id, role, certainty

**프론트엔드 관련성**:
- 글로브 인물 마커 (이름, 위치, 시간 범위)
- PersonTab 목록 (이름, 역할, 시대)
- 타임라인 필터링 (birth_year ≤ 현재 ≤ death_year)

### person_details (19컬럼) — 인물 상세 (1:1)
**핵심 컬럼**: person_id(PK), biography/biography_ko/biography_ja, biography_source, wikipedia_url, image_url, slug, category_id, era, birth_month/day, death_month/day

**프론트엔드 관련성**:
- NarrativePanel: biography 텍스트
- 인물 이미지 표시
- Wikipedia 링크
- 도메인 분류 (category_id)

### person_names (13컬럼) — 인물 별칭/다국어명 (1:M)
**핵심 컬럼**: person_id, name/name_ko/name_ja, valid_from, valid_until, language, is_primary, name_type

**프론트엔드 관련성**:
- 시간에 따른 이름 변화 (예: 출가 전/후 이름)
- 다국어 표시 (그리스어 원명, 로마식 이름 등)

---

### events (21컬럼) — 역사적 사건
**핵심 컬럼**: id, wikidata_id, title/title_ko/title_ja, date_start, date_end, date_precision, temporal_scale, importance(1-5), certainty, category_id, primary_location_id, period_id, parent_event_id, is_aggregate, hierarchy_level(0-4), aggregate_type

**프론트엔드 관련성**:
- 글로브 마커 (위치, 시간, 카테고리 색상)
- 줌 레벨별 필터링 (hierarchy_level, temporal_scale, importance)
- 이벤트 계층 (parent_event_id → 줌인 시 하위 이벤트 표시)
- 카테고리 색상 (category_id → color)

### event_details (18컬럼) — 이벤트 상세 (1:1)
**핵심 컬럼**: event_id(PK), slug, description/description_ko/description_ja, description_source, wikipedia_url, image_url, date_start_month/day, date_end_month/day, min_zoom_level

**프론트엔드 관련성**:
- NarrativePanel: description 텍스트
- 정밀 날짜 표시 (월/일까지)
- 이미지, Wikipedia 링크

---

### locations (12컬럼) — 지리적 장소 (불변 좌표)
**핵심 컬럼**: id, wikidata_id, name/name_ko/name_ja, latitude, longitude, location_type, country, parent_location_id

**프론트엔드 관련성**:
- 글로브 마커 좌표 (latitude, longitude — 절대 불변)
- 뷰포트 필터링 (lat/lng 범위)
- 장소 계층 (parent_location_id: 경복궁 → 서울)

### location_details (8컬럼) — 장소 상세 (1:1)
**핵심 컬럼**: location_id(PK), description/description_ko/description_ja, wikipedia_url

**프론트엔드 관련성**:
- 장소 카드 설명 텍스트
- Wikipedia 링크

### location_names (9컬럼) — 시대별 장소 이름 (1:M)
**핵심 컬럼**: location_id, name/name_ko/name_ja, valid_from, valid_until, language

**프론트엔드 관련성**:
- **시간 이동 핵심**: 타임라인 연도에 맞는 장소 이름 표시
- Byzantium(-667~330) → Constantinople(330~1930) → Istanbul(1930~)

---

## 2. 관계 테이블

### event_persons (4컬럼) — 사건-인물 참여
**컬럼**: event_id, person_id, role(commander/participant/...), certainty

**프론트엔드**: 이벤트 카드에 참여 인물 목록. 인물 카드에서 참여 사건 목록.

### event_relationships (8컬럼) — 사건 간 인과관계
**핵심 컬럼**: from_event_id, to_event_id, relationship_type(causes/enables/follows/opposes), certainty, evidence_type, strength

**프론트엔드**: 이벤트 카드 "원인←" / "결과→" 섹션. 글로브 위 인과관계 화살표.

### person_relationships (9컬럼) — 인물 간 관계
**핵심 컬럼**: person_id, related_person_id, relationship_type(teacher/family/rival/ally), strength(1-5), valid_from, valid_until, confidence

**프론트엔드**: 인물 관계 네트워크. 선의 굵기=strength, 색상=type.

### event_locations (5컬럼) — 사건-장소 연결 (다중)
**컬럼**: event_id, location_id, role(location/origin/destination), match_method, distance_km

**프론트엔드**: 하나의 사건이 여러 장소에 걸칠 때 (알렉산더 원정의 경로).

### event_sources (4컬럼) — 사건-출처 연결
**컬럼**: event_id, source_id, page_reference, quote

**프론트엔드**: 이벤트 카드 "출처" 섹션.

### person_sources (3컬럼) — 인물-출처 연결
**컬럼**: person_id, source_id, page_reference

**프론트엔드**: 인물 카드 "출처" 섹션.

### event_parents (5컬럼) — 다중 부모 이벤트 맥락
**컬럼**: event_id, parent_event_id, context(war/religion/...), is_primary, confidence

**프론트엔드**: 하나의 사건이 여러 맥락에 속할 때 (잔 다르크 처형: 백년전쟁 + 종교재판).

### person_locations (4컬럼) — 인물-장소 연결
**컬럼**: person_id, location_id, role, confidence

**프론트엔드**: 인물의 주요 활동 장소 표시.

### location_relationships (5컬럼) — 장소 간 관계
**컬럼**: location_id, related_location_id, relationship_type, strength, confidence

**프론트엔드**: 장소 간 연결선 (현재 미사용).

### location_sources (3컬럼) — 장소-출처 연결
**컬럼**: location_id, source_id, page_reference

**프론트엔드**: 장소 카드 출처 섹션.

---

## 3. 계층/분류 구조

### categories (7컬럼) — 이벤트/인물 카테고리
**핵심 컬럼**: id, name/name_ko, slug, color, icon, parent_id

**프론트엔드**: 마커 색상, 필터 드롭다운. 7개 기본값 (Military, Political, Cultural, Religious, Scientific, Economic, Social).

### periods (8컬럼) — 시대/기간
**핵심 컬럼**: id, name/name_ko, slug, year_start, year_end, temporal_scale, parent_id

**프론트엔드**: 타임라인 시대 라벨. 시대별 탐색. 계층 구조 (고대→그리스→고전기).

### territories (9컬럼) — 정치 영역
**핵심 컬럼**: id, name/name_ko, territory_type(empire/kingdom/republic/...), founded_year, dissolved_year

**프론트엔드**: 영토 오버레이. 214개 (80 큐레이션 + 84 SPARQL + 50 현대국가).

### territory_locations (7컬럼) — 시대별 장소-영역 소속
**핵심 컬럼**: territory_id, location_id, valid_from, valid_until, relation_type(contains/capital)

**프론트엔드**: **시간 이동 핵심**: 타임라인 연도에 맞는 영토 오버레이. 14,738/17,723 locations 커버 (83.2%).

---

## 4. 서사/큐레이션

### entity_narratives — AI 생성 개별 서사
**핵심 컬럼**: entity_type(event/person), entity_id, narrative, significance, causes(JSON), consequences(JSON)

**프론트엔드**: 이벤트/인물 카드의 이야기 텍스트. description보다 우선 표시.

### period_narratives — 50년 단위 시대 개요
**핵심 컬럼**: period_start, period_end, headline, narrative, keywords(JSON), quote, region

**프론트엔드**: WorldBriefing "NOW OBSERVING" 배너. 타임라인 시대 클릭 시 표시. 6개 지역별.

### histories — 다중 엔티티 에세이 (A4 1페이지)
**핵심 컬럼**: id, title/title_ko, body(Markdown + entity tags), era_start, era_end, category, tags, author_type, importance, status

**프론트엔드**: HistoryTab 읽을거리. entity 태그로 글로브 연동. 사용자 작성 가능.

### history_entities — 히스토리 내 엔티티 참조
**핵심 컬럼**: history_id, entity_type, entity_id, entity_name, role(featured/mentioned/location)

**프론트엔드**: 히스토리 카드의 관련 엔티티 칩. 역방향 조회 (인물→등장 에세이).

---

## 5. 소스/출처 추적

### sources (11컬럼) — 출처 문서
**핵심 컬럼**: id, name, type(primary/secondary/digital_archive), archive_type(perseus/gutenberg/ctext), reliability(1-5), original_year, language

**프론트엔드**: SourceBrowser. 출처 카드. 신뢰도 배지.

### text_mentions — NER 추출 추적
**핵심 컬럼**: entity_type, entity_id, source_id, mention_text, context_text, confidence, extraction_model

**프론트엔드**: 출처 상세 페이지에서 "이 문서에서 언급된 엔티티" 표시.

### entity_aliases — 엔티티 별칭 (중복 제거용)
**핵심 컬럼**: entity_type, entity_id, alias, alias_type(alternate/translation/misspelling/historical), language

**프론트엔드**: 검색 시 별칭 매칭. 현재 직접 노출 안 함.

---

## 6. V1 체인 시스템 (Historical Chain)

### historical_chains — 역사의 고리
**핵심 컬럼**: chain_type(person_story/place_story/era_story/causal_chain), title, focal_person_id/location_id/period_id/event_id, year_start, year_end, status

**프론트엔드**: 가이드 투어의 DB 기반 버전. 현재 프론트엔드 미연동.

### chain_segments — 체인 내 개별 노드
**핵심 컬럼**: chain_id, sequence_number, narrative, event_id/person_id/location_id, transition_type, is_keystone

**프론트엔드**: 투어의 각 정거장. 순서대로 글로브가 이동.

### chain_entity_roles — 체인 내 엔티티 역할
**핵심 컬럼**: chain_id, person_id/location_id/event_id, role(protagonist/antagonist/setting)

**프론트엔드**: 투어 내 주인공/적대자/배경 구분.

---

## 7. 사용자/시스템

### masters — 사용자 계정 (FGO 테마)
**핵심 컬럼**: id, master_number, nickname, session_token, search_count

**프론트엔드**: 세션 관리. 검색 이력.

### search_logs — 검색 기록
**핵심 컬럼**: master_id, query, search_type, intent, is_public

**프론트엔드**: 검색 분석. 공개 검색 로그.

### user_feedback — 사용자 피드백
**핵심 컬럼**: target_type, target_id, feedback_type, status

**프론트엔드**: 콘텐츠 품질 보고.

### content_reports — 콘텐츠 품질 신고
**핵심 컬럼**: entity_type, entity_id, field_name, report_type, status, reviewed_by

**프론트엔드**: "이 정보가 틀렸어요" 신고 기능.

---

## 8. 보조/캐시 테이블

### event_coords_cache — 이벤트 원본 좌표 캐시
**컬럼**: event_id, latitude, longitude, coord_source

**프론트엔드**: 직접 사용 안 함. 백엔드 내부용.

### polities — 정치 엔티티 (V1, territories의 확장)
**핵심 컬럼**: id, name, polity_type, start_year, end_year, capital_id, region, embedding

**프론트엔드**: territories와 유사하지만 벡터 임베딩 포함. 향후 시맨틱 검색 지원.

### fgo_servants — FGO 서번트 매핑
**핵심 컬럼**: servant_id(게임 ID), name, class_name, rarity, person_id(→persons)

**프론트엔드**: Trismegistus Archive (FGO 서번트 브라우징). 게임↔역사 연결.

### fgo_history_comparison — FGO vs 역사 비교
**핵심 컬럼**: servant_id, aspect, fgo_description, historical_description, accuracy_score

**프론트엔드**: FGO 서번트 상세에서 "게임 vs 역사" 비교 표시.

---

## 데이터 현황 (Compact DB)

| 테이블 | 행수 | 비고 |
|--------|------|------|
| events | 28,331 | |
| event_details | 28,331 | description 24,989건 |
| persons | 190,710 | |
| person_details | 156,417 | biography 이전 완료 |
| locations | 17,723 | |
| sources | 22,977 | |
| event_persons | 122,430 | |
| event_locations | 4,612 | |
| territories | 214 | |
| territory_locations | 35,963 | 83.2% 커버리지 |
| person_names | 0 | archive에서 재추출 필요 |
| location_names | 0 | archive에서 재추출 필요 |
| location_details | 0 | archive에서 재추출 필요 |

---

## 요약: 프론트엔드 관점 테이블 분류

| 카테고리 | 테이블 수 | 핵심 |
|---------|----------|------|
| 핵심 엔티티 (Node+Detail) | 8 | persons, events, locations + details/names |
| 관계 | 10 | event_persons, event_relationships, person_relationships 등 |
| 분류/계층 | 4 | categories, periods, territories, territory_locations |
| 서사/큐레이션 | 4 | entity_narratives, period_narratives, histories, history_entities |
| 출처 추적 | 3 | sources, text_mentions, entity_aliases |
| V1 체인 | 3 | historical_chains, chain_segments, chain_entity_roles |
| 사용자/시스템 | 4 | masters, search_logs, user_feedback, content_reports |
| FGO/보조 | 4+ | fgo_servants, fgo_history_comparison, event_coords_cache 등 |
