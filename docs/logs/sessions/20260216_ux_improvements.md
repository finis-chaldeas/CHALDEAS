# UX 개선 세션: Next Phase Sprint 1-2 구현

## 세션 정보
- **날짜**: 2026-02-16
- **목적**: Next Phase Plan의 Sprint 1-2 UX 개선 사항 전부 구현
- **체크포인트**: NEXT_PHASE_PLAN.md → Sprint 1 (#1, #3, #5) + Sprint 2 (#2)

---

## 구현 완료 항목

### 1. 주요 사건 라벨 표시 (Plan #2 / 1A)

**변경 파일**: `backend/app/api/v1_new/globe.py`, `frontend/src/components/globe/GlobeContainer.tsx`

**무엇을 했나**:
- 백엔드 Globe API에 `importance` 필드 추가 (GlobeMarker 응답)
- 프론트엔드에서 `labelsData` 레이어 추가
- importance 4-5 이벤트는 지구본 위에 **제목 + 연도** 텍스트 라벨 표시
- 줌 레벨에 따라 적응: 글로벌 뷰(altitude > 2.0)에서는 importance 5만, 리전 뷰에서는 4+

**왜 좋은가**:
- 기존에는 모든 이벤트가 동일한 점(marker)으로 표시 → 어떤 사건이 중요한지 알 수 없었음
- 이제 "Battle of Marathon", "Fall of Rome" 같은 주요 사건이 **바로 눈에 들어옴**
- FGO 플레이어가 서번트 관련 사건을 찾을 때, 지구본만 봐도 주요 전투/사건을 즉시 인지 가능
- 줌 레벨 적응: 줌 아웃하면 세계사 핵심만, 줌 인하면 지역사 주요 사건도 표시

### 2. 로케이션 상시 표시 (Plan #3 / 2A)

**변경 파일**: `backend/app/api/v1_new/globe.py`, `frontend/src/components/globe/GlobeContainer.tsx`

**무엇을 했나**:
- 백엔드에 `/globe/anchor-locations` 엔드포인트 추가
  - 이벤트 연결 수 기반 Tier 시스템: Tier 1 (50+ events), Tier 2 (10+ events)
- 프론트엔드에서 `htmlElementsData` 레이어를 확장
  - 주요 도시가 **항상** 지구본에 표시됨 (타임라인 시대와 무관)
  - Tier 1 도시 (Rome, Athens, Paris 등)는 줌 아웃에서도 항상 보임
  - Tier 2 도시 (Alexandria, Sparta 등)는 리전 줌에서 표시
  - SHEBA 검색 결과가 있으면 그것이 우선 표시

**왜 좋은가**:
- 기존에는 해당 시대에 이벤트가 있는 위치만 표시 → 지구본이 텅 비어 보이는 시대가 많았음
- 이제 Rome, Athens, Constantinople, Jerusalem 등 **문명의 고정 앵커**가 항상 보임
- 사용자가 "이 시대에 여기서 뭐가 있었지?" 하고 도시를 클릭하면 바로 탐색 가능
- 지구본이 살아있는 느낌 — 도시 이름이 있으면 지도처럼 읽을 수 있음

### 3. 서번트 → 시대 탐색 버튼 (Plan #5 / 3D)

**변경 파일**: `frontend/src/components/servants/ServantPanel.tsx`, `frontend/src/components/servants/ServantPanel.css`, `frontend/src/App.tsx`

**무엇을 했나**:
- ServantPanel에 `onExploreEra` 콜백 추가
- 서번트 상세 뷰에서 Historical Connection 섹션 아래에 **"Explore this Era"** 버튼 추가
- 버튼 클릭 시: 인물의 활동 시기 중간점으로 타임라인 이동 + 패널 닫기
- App.tsx에서 `setCurrentYear`로 연결

**왜 좋은가**:
- FGO 플레이어의 **자연스러운 탐색 흐름** 완성:
  ```
  서번트 패널 → 이스칸다르 클릭 → "Explore this Era (356 BCE)"
  → 지구본이 BCE 300년대로 이동 → 마케도니아/페르시아 전쟁 사건들 표시
  ```
- 기존에는 서번트에서 역사로의 **다리(bridge)**가 "View in CHALDEAS" (인물 상세) 하나뿐
- 이제 인물이 아닌 **시대 자체**로 점프 가능 → 더 넓은 맥락에서 역사 탐색
- FGO에서 "이 시대에 무슨 일이 있었을까?" 하는 호기심을 즉시 해소

---

## 왜 이 개선들이 좋은가 (종합)

### 1. "빈 지구본" 문제 해결

기존 CHALDEAS의 가장 큰 UX 문제:
- 타임라인을 움직이면 대부분의 시대에서 지구본이 **거의 비어있음**
- 이벤트 마커만 있고, 도시 이름도 없고, 어디가 어딘지 알 수 없음

해결:
- **Anchor Locations**: Rome, Athens, Paris 등이 항상 보여서 지구본이 "읽힌다"
- **Event Labels**: 주요 사건이 이름으로 표시되어 "무엇이 일어났는지" 즉시 파악

### 2. FGO → 역사 탐색 흐름 완성

CHALDEAS의 핵심 가치: **FGO 팬이 역사에 관심을 갖게 만드는 것**

기존 흐름 (끊김):
```
서번트 패널 → 인물 상세 → ... (그다음은?)
```

개선된 흐름 (자연스러움):
```
서번트 패널 → "Explore this Era" → 지구본이 해당 시대로 이동
→ 주요 사건 라벨이 눈에 들어옴 → 클릭 → 사건 상세 탐색
→ 연결된 다른 사건/인물 발견 → 역사의 고리(Historical Chain) 탐색
```

### 3. 정보 밀도 증가 (Information Density)

기존: 지구본 위에 점(dot)만 있음 → 마우스를 올려야 뭔지 알 수 있음
개선: 중요한 것은 **바로 텍스트로 보임** → 한 눈에 시대 파악 가능

이것은 Google Maps가 줌 레벨에 따라 도시 이름을 보여주는 것과 같은 원리.
지도(globe)가 "읽을 수 있는 것"이 되면 탐색 의욕이 극적으로 올라감.

---

## 변경 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| `backend/app/api/v1_new/globe.py` | importance 필드 추가, anchor-locations 엔드포인트 |
| `frontend/src/components/globe/GlobeContainer.tsx` | labelsData(사건 라벨) + anchor locations(도시 상시표시) |
| `frontend/src/components/servants/ServantPanel.tsx` | "Explore this Era" 버튼 |
| `frontend/src/components/servants/ServantPanel.css` | 버튼 스타일 |
| `frontend/src/App.tsx` | onExploreEra 콜백 연결 |

## 검증
- TypeScript 컴파일: **에러 0**
- 백엔드: 서버 리스타트 후 자동 반영 (hot-reload)

## 다음 작업 (Sprint 2 나머지)
- **Highlight 큐레이션 30개** (3A) — 수동 데이터 작업 필요
- **시대별 로케이션 명칭** (2B) — Wikidata에서 데이터 추출 필요
