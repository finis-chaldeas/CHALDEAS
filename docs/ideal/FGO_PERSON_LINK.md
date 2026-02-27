# FGO ↔ 역사 인물 연결 기획서

## 한 문장

**"FGO 캐릭터를 누르면 실제 역사 인물이 나온다. 역사 인물을 보면 FGO에서 뭘로 나오는지 보인다."**

FGO를 역사로의 진입점으로 쓰려면, 게임 속 캐릭터와 실제 역사 인물을 연결하는 **양방향 링크**가 핵심이다.

---

## 현재 상태 (문제)

### 데이터 현황

| 데이터셋 | 규모 | 상태 |
|---------|------|------|
| CHALDEAS persons 테이블 | **190,710명** | Wikidata 기반, 잘 정비됨 |
| FGO 플레이어블 서번트 | **449명** | fgo_db 인덱스 완성 |
| FGO 대사 캐릭터 (추출 완료) | **3,462명** | 대사 429,149줄 |
| 기존 서번트↔인물 매핑 | **35건** | ~15건 오매칭, 사실상 **20건만 유효** |
| Wikidata QID는 있지만 DB에 없음 | **73건** | 신화/전설 인물이 DB에 미등록 |
| 매핑 시도 안 됨 | **274건** | 대부분 역사 인물인데 미연결 |

### 핵심 문제

1. **449명 서번트 중 20명만 제대로 연결** (4.5%)
2. **오매칭 15건** — Gilgamesh→Anastasius II 같은 황당한 오류
3. **73명은 Wikidata ID가 있는데 persons 테이블에 해당 인물이 없음** (주로 신화/전설)
4. **274명은 매핑 시도조차 안 됨** — 이 중 상당수가 역사 인물
5. **V2 모델 `FGOServant` 정의됨** but 마이그레이션 없음, DB 테이블 없음
6. **대사 캐릭터 3,462명** 중 서번트가 아닌 NPC/일반캐도 다수 → 전부 연결할 필요 없음

---

## 연결 대상 분류

### 3,462 대사 캐릭터의 계층

```
3,462 대사 캐릭터
  ├── 서번트 (플레이어블)              ~449명  ← 최우선 연결 대상
  │   ├── 역사 인물 기반               ~250명  ← 자동 매칭 가능
  │   ├── 신화/전설 기반               ~120명  ← 일부 persons에 있음
  │   └── FGO 오리지널                 ~80명   ← 연결 불가 (Mash, BB 등)
  ├── 스토리 고정 NPC                  ~50명   ← 선별 연결
  │   (올가마리, 키리슈타리아, 카도크 등)
  ├── 이벤트/스토리 일회성 NPC         ~500명  ← 불필요
  └── 몬스터/집단/기타                ~2,400명 ← 불필요
```

### 우선순위

| 순위 | 대상 | 규모 | 연결 방법 | 기대 효과 |
|------|------|------|----------|----------|
| **P0** | 역사 인물 서번트 (명확) | ~150명 | 자동(이름 매칭) + 수동 검증 | FGO→역사 진입점 |
| **P1** | 역사 인물 서번트 (애매) | ~100명 | 수동 큐레이션 | 커버리지 확대 |
| **P2** | 신화/전설 서번트 | ~120명 | persons 테이블 확장 필요 | 길가메시, 아서왕 등 |
| **P3** | 주요 스토리 NPC | ~30명 | 수동 | 올가마리, 키리슈타리아 등 |
| **P4** | FGO 오리지널 | ~80명 | 연결 불가, 별도 프로필 | BB, Mash 등 |

---

## Phase 1: 자동 매칭 파이프라인

**파일**: `backend/scripts/link_fgo_persons.py`
**비용**: $0 (로컬 매칭) + 소량 GPT (검증용, ~$1)

### 1.1 매칭 전략 (3단계)

```
Step 1: Wikidata ID 직접 매칭
  FGO 서번트의 wikidata_id → persons.wikidata_id
  이미 73건 보유, 대부분 맞을 것 → 매칭 후 수동 검증

Step 2: 이름 매칭 (EN/JA/KO)
  fgo_db/servants/ 의 name_en/ja/ko ↔ persons.name / name_ja / name_ko
  fuzzy matching + 수동 확인 대상 리스트 생성

Step 3: 수동 매핑 시드
  자동으로 안 잡히는 케이스를 수동 JSON으로 관리
  (gender swap, 이름 변경, 복합 캐릭터 등)
```

### 1.2 매칭 난이도별 분류

| 난이도 | 예시 | 매칭 방법 |
|--------|------|----------|
| **쉬움** — 이름 거의 동일 | Napoleon, Cleopatra, Caesar, Tesla | 자동 이름 매칭 |
| **보통** — 이름 약간 다름 | Altria→Arthur, Ozymandias→Ramesses II | alias 테이블 |
| **어려움** — 성별/이름 변환 | Ushiwakamaru→Minamoto no Yoshitsune, Nero(♀)→Nero Claudius(♂) | 수동 매핑 |
| **불가능** — 실존 인물 아님 | Mash, BB, Fou, Space Ishtar | FGO 오리지널 태그 |

### 1.3 수동 매핑 시드 파일

```json
// E:\chaldeas_data\processed\fgo\manual_person_mapping.json
{
  "mappings": [
    {
      "servant_id": 100100,
      "name_en": "Altria Pendragon",
      "person_wikidata_id": "Q45556",
      "person_name": "King Arthur",
      "notes": "Gender swap. FGO는 여성 아서왕.",
      "category": "legendary"
    },
    {
      "servant_id": 200300,
      "name_en": "Ushiwakamaru",
      "person_wikidata_id": "Q317419",
      "person_name": "Minamoto no Yoshitsune",
      "notes": "유년기 이름. FGO는 여성화.",
      "category": "historical"
    },
    {
      "servant_id": 200100,
      "name_en": "Gilgamesh",
      "person_wikidata_id": "Q3057",
      "person_name": "Gilgamesh",
      "notes": "수메르 전설의 왕. Epic of Gilgamesh.",
      "category": "mythological"
    }
  ],
  "fgo_originals": [
    {"servant_id": 800100, "name_en": "Mash Kyrielight", "category": "fgo_original"},
    {"servant_id": 260200, "name_en": "BB", "category": "fgo_original"},
    {"servant_id": 100800, "name_en": "Tamamo Cat", "category": "fgo_original"}
  ]
}
```

### 1.4 매칭 프로세스

```
1. fgo_db/servants/index.json 로드 (449 서번트)
2. servant_person_mapping.json의 기존 매칭 로드 + 오류 필터링
3. Step 1: wikidata_id → persons.wikidata_id 직접 매칭
4. Step 2: name_en fuzzy match → persons.name (threshold 0.85)
5. Step 3: manual_person_mapping.json 적용
6. 결과 분류:
   - ✅ 확정 매칭 (confidence > 0.95)
   - ⚠️ 수동 확인 필요 (0.7 < confidence < 0.95)
   - ❌ 매칭 불가 (FGO 오리지널 or 너무 낮은 score)
   - 🔍 persons 테이블에 없음 (wikidata_id는 있는데 DB 미등록)
7. 결과 JSON 출력 + 리뷰용 리포트
```

### 1.5 출력

```
E:\chaldeas_data\processed\fgo\person_links\
  confirmed_links.json       — 확정 매칭 (서번트 → person_id)
  review_candidates.json     — 수동 검토 대상
  unmatched_servants.json    — 매칭 불가 (FGO 오리지널 포함)
  missing_persons.json       — persons 테이블에 추가 필요한 인물
  report.txt                 — 사람이 읽는 리포트
  enriched_index.json        — 서번트 인덱스 + person 연결 정보 통합
```

### 1.6 CLI

```bash
python -m scripts.link_fgo_persons                      # 전체 실행
python -m scripts.link_fgo_persons --step match          # 매칭만
python -m scripts.link_fgo_persons --step report         # 리포트만
python -m scripts.link_fgo_persons --step enrich         # 서번트 인덱스 enrichment
python -m scripts.link_fgo_persons --dry-run             # 미리보기
python -m scripts.link_fgo_persons --interactive         # 수동 확인 모드
```

---

## Phase 2: persons 테이블 확장

### 2.1 신화/전설 인물 추가

현재 persons 테이블은 **역사 인물 중심**. FGO 서번트의 상당수가 신화/전설 기반:

| 분류 | 예시 | persons 테이블 상태 |
|------|------|-------------------|
| 그리스 신화 | 헤라클레스, 아킬레우스, 메데이아 | 일부 있음 |
| 북유럽 신화 | 시구르드, 브륜힐드, 스카디 | 거의 없음 |
| 아서왕 전설 | 아서, 란슬롯, 모드레드, 모르간 | 거의 없음 |
| 인도 신화 | 아르주나, 카르나, 라마 | 거의 없음 |
| 일본 전설 | 슈텐도지, 이바라키도지, 타마모노마에 | 없음 |
| 메소포타미아 | 길가메시, 엔키두, 이슈타르 | 거의 없음 |

**스크립트**: `backend/scripts/seed_mythological_persons.py`

```
1. FGO 서번트 중 category=mythological/legendary인 목록 추출
2. Wikidata API로 기본 정보 수집 (이름, 출전, 설명)
3. persons 테이블에 INSERT (certainty='legendary' or 'mythological')
4. person_details에 FGO 연결 정보 기재
```

**이렇게 하면 persons 테이블이 "역사 인물" → "역사 + 전설 인물"로 확장됨.**
이는 CHALDEAS의 비전과도 맞음: FGO가 다루는 "영웅"은 역사와 전설의 경계에 있으니까.

### 2.2 확장 대상 추정

| 카테고리 | 대략적 수 | Wikidata 보유율 | 비고 |
|---------|----------|---------------|------|
| 그리스 신화 | ~30명 | 90%+ | 대부분 QID 있음 |
| 북유럽 신화 | ~10명 | 80%+ | |
| 아서왕 전설 | ~15명 | 90%+ | |
| 인도 신화 | ~15명 | 70%+ | |
| 일본 전설 | ~10명 | 60%+ | 일부 QID 없음 |
| 메소포타미아 | ~5명 | 80%+ | |
| 중국 전설 | ~5명 | 70%+ | |
| **합계** | **~90명** | | |

비용: Wikidata API = 무료, 소요 시간 ~5분

---

## Phase 3: 대사 캐릭터 ↔ 서번트 연결

### 3.1 문제

대사 추출의 캐릭터명(JP) ↔ 서번트 인덱스의 name_ja가 **완전 일치하지 않는다**.

| 대사 스피커명 | 서번트 name_ja | 같은 인물? |
|-------------|--------------|----------|
| `マシュ・キリエライト` | `マシュ・キリエライト` | ✅ 일치 |
| `ギルガメッシュ` | `ギルガメッシュ` | ✅ 일치 |
| `クー・フーリン` | `クー・フーリン` | ✅ 일치 (alias 적용 후) |
| `アルトリア・ペンドラゴン〔オルタ〕` | `アルトリア・ペンドラゴン〔オルタ〕` | ✅ 일치 (alias 적용 후) |
| `ロマニ・アーキマン` | — (서번트 아님) | NPC |
| `エリザベート` | `エリザベート・バートリー` | ⚠️ 부분 일치 |
| `ティアマト` | — (적 전용) | NPC/보스 |

### 3.2 연결 스크립트

**파일**: `backend/scripts/link_fgo_dialogue_speakers.py`

```
1. 대사 stats.json에서 top 200 스피커 로드
2. fgo_db/servants/index.json에서 name_ja 리스트 로드
3. 매칭:
   a. 정확 매칭 (name_ja == speaker_name)
   b. 포함 매칭 (speaker_name in servant_name or vice versa)
   c. alias 맵 참조
4. 결과: speaker → servant_id → person_id 3단계 링크
5. 출력: dialogue_person_links.json
```

### 3.3 최종 연결 체인

```
FGO 대사 스피커명 (JP)
    ↓ alias 맵 + fuzzy match
FGO 서번트 (servant_id)
    ↓ person_links
CHALDEAS Person (person_id)
    ↓ person → events, locations, biography
역사 콘텐츠 (시프트, 이벤트, 나레이션)
```

**이 체인이 완성되면**: 대사를 읽다가 "이 캐릭터의 실제 역사를 보기" 클릭 → NarrativePanel로 연결.

---

## Phase 4: DB 마이그레이션 + API

### 4.1 마이그레이션 (기존 V2 모델 활용)

기존 `FGOServant` 모델을 약간 수정:

```python
class FGOServant(Base):
    __tablename__ = "fgo_servants"

    id = Column(Integer, primary_key=True)
    servant_id = Column(Integer, unique=True, nullable=False)  # FGO game ID
    collection_no = Column(Integer)                             # 도감 번호
    name = Column(String(200), nullable=False)                  # EN name
    name_ja = Column(String(200))
    name_ko = Column(String(200))
    class_name = Column(String(50), nullable=False)
    rarity = Column(Integer)

    # 역사 인물 연결
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=True)
    link_confidence = Column(String(20))    # confirmed / probable / speculative
    link_category = Column(String(30))      # historical / mythological / legendary / fgo_original
    link_notes = Column(Text)               # "Gender swap", "Youth name" 등

    # 대사 통계
    total_dialogue_lines = Column(Integer, default=0)
    chapter_appearances = Column(Integer, default=0)

    # 메타
    portrait_url = Column(String(500))
    icon_url = Column(String(500))

    # 관계
    person = relationship("Person", backref="fgo_servants")
```

### 4.2 API

```
GET /api/v1/fgo/servants
  → 서번트 목록 (person 연결 정보 포함)
  query: ?linked_only=true, ?class=saber, ?sort=dialogue_lines

GET /api/v1/fgo/servants/{servant_id}
  → 서번트 상세 (person 프로필 + 대사 통계 + 챕터별 등장)

GET /api/v1/fgo/servants/{servant_id}/dialogues
  → 서번트 대사 샘플 (챕터별)

GET /api/v1/persons/{id}/fgo
  → 해당 인물의 FGO 서번트 정보 (역방향 조회)
  → { servants: [{ name, class, rarity, dialogue_lines, portrait_url }] }
```

### 4.3 TRISMEGISTOS 연동

```
서번트 카드 클릭
  → FGO 서번트 정보 표시
  → "실제 역사 인물 보기" 버튼
  → persons의 NarrativePanel 열기 + 글로브 flyTo(생애 시작 위치)

역사 인물 NarrativePanel
  → 하단에 "FGO에서는?" 섹션
  → 서번트 아이콘 + 클래스 + 대사 수 표시
  → "FGO 대사 보기" → 원문 대사 뷰어
```

---

## Phase 5: FGO vs 역사 비교 콘텐츠 (AI 생성)

### 5.1 FGO ↔ 역사 비교 카드

기존 `FGOHistoryComparison` 모델 활용. 각 서번트에 대해:

| 비교 항목 | FGO 설정 | 실제 역사 | 평가 |
|----------|---------|---------|------|
| 전기(biography) | 게임 내 설명 | DB biography | accurate / artistic_license / fictional |
| 외모(appearance) | 금발 소녀 | 중세 남성 기사 | gender_swap |
| 능력(abilities) | 엑스칼리버 | 전설의 검 | legendary |
| 성격(personality) | 명랑, 식탐 | 전설상 고결한 왕 | artistic_license |

**생성 방법**: GPT-5.1로 비교 텍스트 자동 생성
- 입력: 서번트 본드 텍스트(JP+EN) + persons biography
- 출력: 6개 aspect별 비교 JSON

**이건 Phase 2(스토리 요약)와 함께 돌리면 비용 효율적.**

### 5.2 비용 추정

| 단계 | 대상 | 모델 | 추정 비용 |
|------|------|------|----------|
| 비교 생성 | ~200 서번트 | gpt-5.1 | ~$3 |
| 비교 번역 (한/일) | ~200 × 2 | gpt-5-mini | ~$1.5 |
| **합계** | — | — | **~$4.5** |

---

## 실행 순서

```
Phase 1: 자동 매칭 (비용 $0, ~10분)
  1-1. link_fgo_persons.py 작성
  1-2. 기존 매핑 정리 (오매칭 수정)
  1-3. Wikidata ID + 이름 매칭 실행
  1-4. 수동 매핑 시드 작성 (주요 캐릭터 50명)
  1-5. 결과 리포트 → 수동 검증
    ↓
Phase 2: persons 확장 (비용 $0, ~5분)
  2-1. seed_mythological_persons.py 작성
  2-2. 신화/전설 인물 ~90명 Wikidata에서 수집
  2-3. persons 테이블에 INSERT
  2-4. Phase 1 재실행 (새 인물과 매칭)
    ↓
Phase 3: 대사 ↔ 서번트 연결 (비용 $0, ~2분)
  3-1. link_fgo_dialogue_speakers.py 작성
  3-2. top 200 스피커 → 서번트 매칭
  3-3. 서번트 → person 체인 완성
    ↓
Phase 4: DB + API (비용 $0, ~30분 개발)
  4-1. Alembic 마이그레이션 (fgo_servants 테이블)
  4-2. link 결과 → fgo_servants 시딩
  4-3. API 엔드포인트 구현
  4-4. TRISMEGISTOS 프론트엔드 연동
    ↓
Phase 5: 비교 콘텐츠 (비용 ~$4.5, 별도 세션)
  5-1. GPT로 FGO vs 역사 비교 텍스트 생성
  5-2. fgo_history_comparison 테이블 시딩
  5-3. 프론트엔드에 비교 뷰 추가
```

---

## 기대 결과

### 커버리지 목표

| 단계 | 연결된 서번트 | 비율 (449 중) |
|------|-------------|-------------|
| 현재 | ~20명 | 4.5% |
| Phase 1 완료 | ~180명 | 40% |
| Phase 2 완료 | ~300명 | 67% |
| Phase 3 완료 | 300명 + 대사 통계 | — |
| Phase 4 완료 | API 제공 | — |
| Phase 5 완료 | 비교 콘텐츠 | — |

### 사용자 경험

**FGO 유저** (TRISMEGISTOS에서):
```
특이점 VII 바빌로니아 카드 클릭
  → "길가메시, 이슈타르, 엔키두가 등장"
  → 길가메시 클릭
  → FGO 서번트 정보 + "실제 길가메시 서사시 보기"
  → 글로브: 메소포타미아로 이동, 길가메시 서사시 NarrativePanel
  → 관련 시프트: "메소포타미아 문명" 시작
```

**역사 덕후** (NarrativePanel에서):
```
글로브에서 잔 다르크 클릭
  → NarrativePanel: 잔 다르크 전기, 백년전쟁 맥락
  → 하단 "FGO에서는?" 섹션
  → FGO 룰러 잔 다르크 아이콘 + "1,484줄 대사, 20개 챕터 등장"
  → "FGO vs 역사 비교" 펼치기
  → "외모: 금발 장발 소녀 (FGO) vs 검은 단발 (역사 기록)"
```

---

## 재사용 리소스

| 리소스 | 용도 |
|--------|------|
| `fgo_db/servants/index.json` | 449 서번트 기본 정보 (name_en/ja/ko, class, rarity) |
| `fgo_db/servants/by_id/*.json` | 서번트 상세 (본드 텍스트, 프로필) |
| `servant_person_mapping.json` | 기존 매핑 (정리 후 재사용) |
| `processed/fgo/dialogues/stats.json` | top 50 스피커 + 대사 통계 |
| `processed/fgo/dialogues/by_character/*.json` | 캐릭터별 대사 데이터 |
| `processed/fgo/dialogues/alias_map.json` | 스피커 alias 매핑 |
| `models/v2/fgo.py` | FGOServant, FGOHistoryComparison 모델 |
| persons 테이블 (190,710명) | 매칭 대상 |

---

## 검증

```bash
# Phase 1 검증
python -m scripts.link_fgo_persons --dry-run
# → "449 servants: 180 matched, 73 need person creation, 116 FGO-original, 80 review needed"

# Phase 2 검증
python -m scripts.seed_mythological_persons --dry-run
# → "90 mythological persons to add from Wikidata"

# Phase 3 검증
python -m scripts.link_fgo_dialogue_speakers --dry-run
# → "Top 200 speakers: 120 linked to servants, 30 NPC, 50 unmatched"

# 최종 검증
# TRISMEGISTOS에서 바빌로니아 → 길가메시 → NarrativePanel 이동 확인
```
