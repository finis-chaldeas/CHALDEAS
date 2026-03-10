# Location Card

## 와이어프레임

### Compact (글로브 노드)
```
┌─────────────────────────┐
│ Athens · Greece          │
│ 아테네                   │
└─────────────────────────┘
```

### Expanded
```
┌─────────────────────────┐
│ Athens                  │
│ 아테네                   │
│                         │
│ Greece                  │
│ 37.97°N, 23.72°E       │
│                         │
│ "고대 그리스의 중심 도시로 │  ← locations.description 처음 150자
│  민주주의의 발상지..."    │     (생성 예정)
│                         │
│ Major events:           │
│  • Battle of Marathon   │  ← 클릭 시 Event Card
│  • Peloponnesian War    │
│  • Golden Age of Athens │
│                         │
│ [글로브에서 보기]         │
└─────────────────────────┘
```

## 데이터 소스

| 필드 | 테이블.컬럼 | 비고 |
|------|------------|------|
| 이름 | `locations.name` / `name_ko` / `name_ja` | loc() 폴백 |
| 국가/지역 | `locations.country` | |
| 좌표 | `locations.lat`, `lng` | |
| 본문 스니펫 | `locations.description` / `description_ko` | **현재 없음 — 생성 예정** |
| 주요 이벤트 | `event_locations` → `events` | importance 상위 3개 |

## 본문 소스 — 생성 계획

현재 `locations` 테이블에 description 컬럼 없음.

### 필요 작업:
1. **마이그레이션**: `locations`에 `description`, `description_ko`, `description_ja` 컬럼 추가
2. **생성 스크립트**: 주요 location에 대해 description 배치 생성
   - 소스: 해당 장소의 이벤트 목록 + Wikipedia 등
   - 모델: `gpt-5.1-chat-latest` (요약/생성 용도)
   - 우선순위: importance 높은 장소부터
3. **폴백**: description 없으면 이벤트 목록만 표시 (현재와 동일)

## 트리거

- 글로브 노드(도시) 클릭 → Compact 표시, 클릭 시 Expanded
- `[Name](entity:location:id)` 엔티티 링크 클릭 → 바로 Expanded

## 액션 버튼

- **글로브에서 보기** → 해당 좌표로 카메라 이동
- 이벤트 이름 클릭 → Event Card 열기

## 기존 코드 참고

- 현재 노드 클릭: `GlobeContainer.tsx:1179`
- LocationDetailView: `frontend/src/components/detail/LocationDetailView.tsx`
