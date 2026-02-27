# FGO 로컬 DB 구축 세션

**날짜**: 2026-02-26 ~ 02-27 (2세션에 걸쳐 진행)
**목적**: Atlas Academy API에서 FGO 전체 데이터를 수집하여 3개국어(JP/EN/KR) 로컬 DB 구축
**용도**: 트리스메기스토스 포털에서 활용할 FGO 원작 데이터 아카이브

---

## 완료된 작업

### 1. 메인스토리 스크립트 수집 (JP/NA/KR)

21개 챕터 x 3개국어 = 63개 파일 수집 완료.

| 구분 | 챕터 수 | JP 대사 | KR 대사 |
|------|---------|---------|---------|
| 특이점 (Part 1) | 9 | 32,484 | 32,641 |
| Epic of Remnant (Part 1.5) | 4 | 22,623 | 22,623 |
| 이문대 (Part 2) | 8 | 82,388 | 82,436 |
| **합계** | **21** | **137,495** | **137,700** |

전 챕터 3개국어(JP+EN+KR) 완비.

**챕터 목록**:
- Part 1: 후유키, 오를레앙, 세프템, 오케아노스, 런던, 이 플루리버스 우넘, 캬멜롯, 바빌로니아, 솔로몬
- Part 1.5: 신주쿠, 아가르타, 시모사, 세일럼
- Part 2: LB1~LB7 (아나스타시아 ~ 나우이 믹틀란) + LB5.5 헤이안쿄

### 2. 서번트 데이터 수집

| 항목 | 수량 |
|------|------|
| 서번트 총 수 | 449기 (플레이어블) |
| JP 프로필 (본드 텍스트) | 449 |
| NA 프로필 | 398 |
| KR 프로필 | 407 |
| 역사인물 링크 | 35 |

**수집 파일**:
- `servants_basic_jp.json`, `servants_basic_na.json`, `servants_basic_kr.json`
- `servant_profiles_jp.json`, `servant_profiles_na.json`, `servant_profiles_kr.json`

### 3. 이벤트 스토리 수집 (JP, 진행 중)

156/189 JP 이벤트 수집 (war 9130까지). 재부팅으로 중단, 이어서 수집 가능.

| 항목 | 수치 |
|------|------|
| 수집 완료 | 156/189 JP 이벤트 |
| 스토리 있는 이벤트 | 92개 |
| 이벤트 대사 합계 | 269,829 |
| NA/KR 이벤트 | 미수집 (JP 완료 후 진행 예정) |

**수집된 주요 스토리 이벤트** (9000번대):
- SE.RA.PH (深海電脳楽土)
- 서번트 페스
- 대소설 등

### 4. FGO 로컬 DB 빌드

`build_fgo_db.py`로 정제된 DB 생성 완료.

```
E:/chaldeas_data/fgo_db/
├── meta.json                    — DB 메타정보
├── stories/
│   ├── index.json               — 21개 챕터 인덱스
│   ├── singularity_F_fuyuki.json
│   ├── ...
│   ├── remnant_I_shinjuku.json
│   ├── ...
│   └── lostbelt_7_lb7.json
├── servants/
│   ├── index.json               — 449기 인덱스 (JP+EN+KR 이름)
│   └── by_id/
│       ├── 100100.json          — 개별 서번트 (3개국어 본드 텍스트)
│       └── ...
└── mappings/
    ├── servant_to_person.json   — 서번트 ↔ 역사인물 매핑
    └── story_locations.json     — 21개 챕터 좌표/시대
```

---

## 디스크 사용량

| 경로 | 크기 |
|------|------|
| `E:/chaldeas_data/raw/atlas_academy/` | ~410 MB |
| `E:/chaldeas_data/fgo_db/` | ~32 MB |

---

## 수정한 파일

### `backend/scripts/fetch_fgo_scripts_jp.py`
- Epic of Remnant(warId 201-204)를 WAR_SLUGS에 추가
- 이벤트 필터 수정: `1000 <= id < 9000` → `1000 <= id <= 9999` (9000+ 스토리 이벤트 포함)
- 기존 94개 → 189개 이벤트 수집 가능

### `backend/scripts/fetch_fgo_servant_profiles.py`
- `--region` 선택지에 KR 추가

### `backend/scripts/build_fgo_db.py`
- Epic of Remnant 4챕터를 CHAPTER_META에 추가 (신주쿠/아가르타/시모사/세일럼)
- KR 스크립트 로딩 + 대사 카운트 + 언어 플래그
- NA 경로 폴백: `scripts/` → `scripts_na/` (EoR용)
- KR 서번트 지원: `servants_basic_kr.json`, `servant_profiles_kr.json`
- 서번트 name.ko, bond_text.ko, has_kr_profile 필드 추가

---

## 버그 수정

### 이벤트 필터 누락 (중대)
- **문제**: `fetch_event_wars()`가 `1000 <= id < 9000`으로 필터링하여 9000~9999 범위의 스토리 이벤트(SE.RA.PH, 오오쿠, 루루하와 등)가 전부 누락
- **원인**: 9000번대가 게임플레이 이벤트가 아닌 스토리 이벤트인 줄 몰랐음
- **수정**: 상한을 `<= 9999`로 변경 → 94개 → 189개 이벤트

### NA EoR 경로
- **문제**: 기존 NA 메인스토리는 `scripts/`에, 새로 수집한 EoR은 `scripts_na/`에 저장됨
- **수정**: `build_fgo_db.py`에서 `scripts/` 없으면 `scripts_na/` 폴백

---

## 남은 작업

1. **이벤트 수집 완료**: JP 나머지 33개 → NA 189개 → KR 189개
   ```bash
   cd backend
   python -m scripts.fetch_fgo_scripts_jp --region JP --events
   python -m scripts.fetch_fgo_scripts_jp --region NA --events
   python -m scripts.fetch_fgo_scripts_jp --region KR --events
   ```
   예상 소요: ~5시간 (이미 받은 파일은 자동 스킵)

2. **이벤트 DB 빌드**: `build_fgo_db.py`에 이벤트 빌더 추가
   - 현재는 메인스토리만 빌드
   - 이벤트도 `fgo_db/events/` 디렉토리에 정리 필요

3. **트리스메기스토스 포털 연동**: 수집된 FGO DB를 프론트엔드에서 접근 가능하게 API 구성

---

## 데이터 출처

- **Atlas Academy API**: `api.atlasacademy.io` (서번트 메타, 프로필, 워 구조)
- **Atlas Academy Static**: `static.atlasacademy.io` (원문 스크립트 .txt)
- **리전**: JP (일본), NA (북미/영어), KR (한국)
