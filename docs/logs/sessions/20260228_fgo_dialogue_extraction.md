# 20260228 — FGO 캐릭터별 대사 추출 + DB 비교

## 목적

FGO 스토리 데이터에서 캐릭터별 대사를 추출하고, CHALDEAS DB의 persons 테이블과 비교하여 누락 인물을 파악.

## 작업 내용

### Phase 1: 대사 추출 (`extract_fgo_dialogues.py`)

**수정 사항:**
- `STORIES_DIR` 경로 변경: `fgo_db/stories/` → `raw/atlas_academy/scripts_jp/`
  - 22개 → 36개 챕터로 확대 (Ordeal Call, Traum, Tunguska 등 15개 추가)
- 필드명 매핑: `slug→id`, `war_id→warId`, glob `*_jp.json`
- 중복 제거: `lb5_jp` = `lb5_atlantis_jp`, `lb5.5_jp` = `lb5_olympus_jp` (동일 quest set)
- Docstring 경로 업데이트

**실행 결과:**

| 항목 | 값 |
|------|-----|
| 메인 스토리 챕터 | 34개 |
| 이벤트 | 118개 |
| 총 캐릭터 대사 | 483,189줄 |
| 유니크 캐릭터 | 3,849명 (by_character 파일: 3,741개) |
| 내레이션 | 305줄 |
| 불명(？？？) | 11,888줄 |
| Alias 해소 | 22건 |

**Top 10 스피커:**

| 순위 | 캐릭터 | 대사 | 등장 챕터 |
|------|--------|------|-----------|
| 1 | マシュ・キリエライト | 36,878 | 147 |
| 2 | レオナルド・ダ・ヴィンチ | 18,738 | 124 |
| 3 | ゴルドルフ・ムジーク | 8,648 | 69 |
| 4 | シャーロック・ホームズ | 6,245 | 39 |
| 5 | ジャンヌ・ダルク〔オルタ〕 | 4,520 | 24 |
| 6 | シオン・エルトナム・ソカリス | 4,504 | 41 |
| 7 | カドック | 4,401 | 17 |
| 8 | ロマニ・アーキマン | 4,283 | 30 |
| 9 | エリザベート | 4,253 | 41 |
| 10 | カーマ | 3,934 | 11 |

### Phase 2: DB 비교 (`_compare_fgo_db.py`)

서번트 인덱스(449 서번트, 309 유니크 베이스)를 DB persons 테이블(12.9M행)과 대조.

**방법:** 영문 이름 기반 exact match + 이름 변환 매핑(Iskandar→Alexander the Great 등)

**결과:**

| 분류 | 수 |
|------|-----|
| 전체 유니크 서번트 | 309명 |
| DB에 존재 | 124명 (40%) |
| DB에 없음 — 역사/신화 인물 | 159명 |
| DB에 없음 — FGO 오리지널 | 26명 |

## 출력 파일

```
E:\chaldeas_data\processed\fgo\
  dialogues\
    by_chapter/       — 152개 JSON (챕터별 캐릭터 대사 통계)
    by_character/     — 3,741개 JSON (캐릭터별 크로스챕터 집계)
    stats.json        — 전체 통계 + Top 50 스피커
    alias_map.json    — alias 매핑 (22건 실사용)
  person_links\
    fgo_db_comparison.json  — 서번트 vs DB 비교 결과
```

## 변경 파일

- `backend/scripts/extract_fgo_dialogues.py` — 소스 경로 + 필드명 수정
- `backend/scripts/_compare_fgo_db.py` — 임시 비교 스크립트 (신규)

## 미해결 / 향후 작업

### DB에 없는 역사/신화 인물 활용 방안

159명의 역사/신화 인물이 DB에 없음. 이들을 어떻게 활용할지 결정 필요:

1. **persons 테이블 직접 추가**: Wikidata에서 가져오거나 수동 생성
   - 장점: 기존 시스템(이벤트 연결, 글로브 마커)과 자연스럽게 통합
   - 단점: 12.9M행 테이블에 ~160명 추가는 미미, 신화 인물은 Wikidata에 없을 수 있음

2. **별도 FGO 서번트 테이블**: `fgo_servants` 테이블을 만들어 persons와 FK 연결
   - 장점: FGO 고유 정보(클래스, 레어도, 프로필) 저장 가능
   - 단점: 추가 마이그레이션 + API 확장 필요

3. **entity_properties 활용**: 기존 persons에 `fgo_servant` 프로퍼티 추가
   - 장점: 스키마 변경 없음
   - 단점: 구조화된 쿼리 어려움

4. **대사 데이터 직접 활용**: DB 연결 없이 by_character JSON을 프론트에서 직접 참조
   - 장점: 즉시 사용 가능, 의존성 없음
   - 단점: 글로브/타임라인과 통합 불가

### 대사 0줄 문제

- 124명 중 46명이 0줄 → alias 매핑이 이름을 다른 variant로 합산했거나, 클래스명으로만 등장
- alias 매핑 개선 여지 있음 (특히 이벤트에서 약칭 사용 시)

### 이벤트 중복 가능성

- 이벤트 118개 중 일부가 리런(복각)이벤트일 수 있음 → quest ID 기반 중복 체크 필요
